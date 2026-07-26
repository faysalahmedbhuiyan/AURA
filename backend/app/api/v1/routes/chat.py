"""
AURA Backend — Chat Routes.

Module: app.api.v1.routes.chat
Purpose: Main chat endpoint. Deterministic command intents (web search,
         system info, memory save/delete) are executed directly in code
         and returned as the response WITHOUT going through the LLM —
         a small local model (qwen2.5:3b) reliably hallucinates when
         asked to summarize/relay search results or system data, so
         those intents bypass the LLM entirely. Only genuine
         conversational messages go through Ollama, with RAG context.

File attach flow (Tier 3): if a file is staged for this conversation
(via POST /api/v1/ingestion/stage), a normal chat message is answered
using the file's real extracted text as context. "save it" while a
file is staged ingests the FULL file into the Tier 2 Intelligence
Layer (chunked); "forget/delete it" while a file is staged detaches it
without saving anything. Staged files persist across multiple turns
until saved, removed, or replaced.

Bangla/Banglish auto-translation is intentionally OUT OF SCOPE for this
fix — tracked separately, not touched here.
"""

import asyncio
import logging
import re
from datetime import timezone
from pathlib import Path

from app.repositories.vault_repository import vault_repository

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.ingestion.staging_store import staging_store
from app.intelligence.intelligence_service import intelligence_service
from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.conversation_repository import conversation_repository
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryItem,
    ConversationHistoryResponse,
)
from app.services.memory_service import memory_service
from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Intent patterns (checked in this priority order) ──────────────────────────

SAVE_PATTERNS = [
    r'\bsave it\b', r'\bremember this\b', r'\bsave this\b',
    r'\bkeep this\b', r'\bstore this\b', r'\bnote this\b',
    r'মনে রাখো', r'সেভ করো', r'সংরক্ষণ করো',
]

DELETE_PATTERNS = [
    r'\bdelete\b', r'\bremove\b', r'\bforget\b', r'\berase\b',
    r'মুছে', r'ভুলে', r'ডিলিট',
]

SYSTEM_PATTERNS = [
    r'\bcheck cpu\b', r'\bcpu usage\b', r'\bcpu status\b',
    r'\bram status\b', r'\bram usage\b', r'\bmemory usage\b',
    r'\bdisk usage\b', r'\bdisk status\b',
    r'\bsystem info\b', r'\bsystem status\b', r'\bpc status\b',
    r'\bhow.?s (my |the )?(pc|computer|system)\b',
]
INGESTION_STATUS_PATTERNS = [
    r'\bis it saved\b', r'\bsaved yet\b', r'\bsaving status\b', r'\bis it done\b',
    r'সংরক্ষণ হয়েছে', r'হয়েছে কিনা', r'সেভ হয়েছে',
]

SEARCH_PATTERNS = [
    r'\bsearch\b', r'\bcheck\b', r'\bfind\b(?!.*\bfile\b)', r'\block up\b',
    r'\bcheck online\b', r'\bnews\b', r'\blatest\b',
    r'\bwhat is\b', r'\bwho is\b', r'\bwhere is\b',
    r'\bgo to\b', r'\bresearch\b', r'\block into\b', r'\bgoogle\b',
    r'\b(20[2-9]\d)\b',
    r'\bখবর\b', r'\bসংবাদ\b', r'\bখোঁজ\b', r'\bআজকের\b', r'\bচেক করো\b',
]

# When a file is staged, "what is"/"who is" almost always refers to the
# attached document, not a web lookup — so this narrower list is used
# instead when staged=True in _detect_intent(). Explicit web-intent
# verbs still force a real search even with a file staged.
SEARCH_PATTERNS_WITH_STAGED_FILE = [
    r'\bsearch\b', r'\bcheck online\b', r'\bnews\b', r'\blatest\b',
    r'\bgo to\b', r'\bresearch\b', r'\block into\b', r'\bgoogle\b',
    r'\bwebsite\b', r'\block up\b',
    r'\b(20[2-9]\d)\b',
    r'\bখবর\b', r'\bসংবাদ\b', r'\bখোঁজ\b', r'\bআজকের\b', r'\bচেক করো\b',
]

NEWS_WORDS = {
    "news", "খবর", "সংবাদ", "today", "আজকের",
    "latest", "current", "breaking", "headlines",
}

SAVE_AS_NAME_PATTERN = re.compile(
    r'\bsave\s+(?:it|this)?\s*as\s+["\']?([^"\'\n.]{2,80})', re.IGNORECASE
)


def _extract_save_name(message: str) -> str | None:
    """Extract an explicit name from 'save it as X' / 'save as X'."""
    m = SAVE_AS_NAME_PATTERN.search(message)
    return m.group(1).strip() if m else None

SHOW_IMAGE_WORDS = [
    r'\bpic\b', r'\bpicture\b', r'\bimage\b', r'\bphoto\b', r'\bshow\b',
    r'ছবি', r'দেখাও',
]


def _extract_page_number(message: str) -> int | None:
    """Extract a page number from 'page 4' or 'পৃষ্ঠা ৪'."""
    m = re.search(r'\bpage\s+(\d+)\b', message, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'পৃষ্ঠা\s*(\d+)', message)
    return int(m.group(1)) if m else None


def _is_show_page_request(message: str) -> bool:
    """A message asks to see a specific page image if it mentions a page number AND a 'show/image' word."""
    has_page = bool(re.search(r'\bpage\s+\d+\b', message, re.IGNORECASE)) or bool(re.search(r'পৃষ্ঠা\s*\d+', message))
    has_show = any(re.search(p, message, re.IGNORECASE) for p in SHOW_IMAGE_WORDS)
    return has_page and has_show

FILE_QA_SYSTEM_PROMPT = (
    "You are a document question-answering assistant. You are NOT AURA "
    "and this is NOT a general conversation — answer ONLY using the "
    "attached document content given in the message below. Extract "
    "names, numbers, dates, and facts EXACTLY as written in the "
    "document. NEVER substitute a name or fact you recognize from "
    "elsewhere (including your own assistant identity, your owner's "
    "name, or any other prior knowledge) for what the document actually "
    "says — if the document names a specific person for a role, use "
    "that exact name, even if it differs from names you know. If the "
    "document doesn't contain the answer, say so honestly rather than "
    "guessing. Respond in the requested language."
)


def _matches(text: str, patterns: list[str]) -> bool:
    """Check if any pattern matches the text."""
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _is_news_query(message: str) -> bool:
    return any(w in message.lower() for w in NEWS_WORDS)


def _detect_intent(message: str, staged: bool = False) -> str:
    """
    Classify a message into exactly one deterministic intent.

    Args:
        message: The user's message.
        staged: Whether a file is currently staged for this conversation.

    Returns:
        str: 'save' | 'show_page' | 'delete' | 'ingestion_status' | 'system' | 'search' | 'chat'
    """
    if _matches(message, SAVE_PATTERNS):
        return "save"
    if _is_show_page_request(message):
        return "show_page"
    if _matches(message, DELETE_PATTERNS):
        return "delete"
    if _matches(message, INGESTION_STATUS_PATTERNS):
        return "ingestion_status"
    if _matches(message, SYSTEM_PATTERNS):
        return "system"
    search_patterns = SEARCH_PATTERNS_WITH_STAGED_FILE if staged else SEARCH_PATTERNS
    if _matches(message, search_patterns):
        return "search"
    return "chat"


async def _handle_show_page(message: str, staged: dict, language: str) -> str:
    """
    Return a reply containing an [[IMAGE:url]] marker for a specific
    page — the frontend renders this as an actual image, not text.
    Only works for already-vaulted (named+saved) files, since page
    images are permanent vault assets.
    """
    page_num = _extract_page_number(message)
    if not page_num:
        return "কোন পৃষ্ঠা নম্বর দেখতে চান?" if language == "bn" else "Which page number would you like to see?"

    vault_id = staged.get("vault_item_id")
    if not vault_id:
        return (
            "আগে ফাইলটি সংরক্ষণ করুন ('save it as <name>' বলুন), তারপর নির্দিষ্ট পৃষ্ঠা দেখাতে পারব।"
            if language == "bn" else
            "Save this file first (say 'save it as <name>'), then I can show you specific pages."
        )
    pages = staged.get("page_image_paths") or []
    if not pages:
        return (
            "এই ফাইলের জন্য পেজ ইমেজ নেই (Word ডকুমেন্টে এটা সাপোর্ট করে না)।"
            if language == "bn" else
            "I don't have page images for this file (not available for Word documents)."
        )
    if page_num < 1 or page_num > len(pages):
        return f"এই ফাইলে মাত্র {len(pages)}টি পৃষ্ঠা আছে।" if language == "bn" else f"This file only has {len(pages)} page(s)."

    image_url = f"/api/v1/vault/{vault_id}/page/{page_num}"
    caption = f"'{staged['filename']}' এর পৃষ্ঠা {page_num}:" if language == "bn" else f"Page {page_num} of '{staged['filename']}':"
    return f"{caption}\n\n[[IMAGE:{image_url}]]"

async def _handle_ingestion_status(conversation_id: str, language: str) -> str:
    """Report progress of a background file-save job, if one is running."""
    from app.ingestion.job_store import ingestion_job_store

    job = ingestion_job_store.get(conversation_id)
    if not job:
        return (
            "No file save is in progress right now."
            if language == "en" else "এখন কোনো ফাইল সংরক্ষণ প্রক্রিয়াধীন নেই।"
        )

    if job["status"] == "processing":
        return (
            f"⏳ Still saving '{job['filename']}': {job['processed']}/{job['total_chunks']} "
            f"section(s) done ({job['created']} new, {job['evolved']} updated so far)."

            if language == "en" else
            f"⏳ '{job['filename']}' এখনো সংরক্ষণ হচ্ছে: {job['processed']}/{job['total_chunks']}টি অংশ শেষ।"
        )
    if job["status"] == "done":
        return (
            f"✅ '{job['filename']}' fully saved — {job['created']} new, {job['evolved']} updated, "
            f"{job['failed']} failed out of {job['total_chunks']} section(s)."
            if language == "en" else
            f"✅ '{job['filename']}' সম্পূর্ণ সংরক্ষণ হয়েছে — {job['created']} নতুন, {job['evolved']} আপডেট।"
        )
    return (
        f"❌ Saving '{job['filename']}' failed: {job.get('error', 'unknown error')}"
        if language == "en" else f"❌ '{job['filename']}' সংরক্ষণ ব্যর্থ হয়েছে।"
    )


def _strip_save_trigger(message: str) -> str:
    """Remove the save-command phrase from a message, keep the rest."""
    cleaned = message
    for p in SAVE_PATTERNS:
        cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" .,!?।\n")


# ── Deterministic handlers — each returns the FULL final reply text ──────────

def _format_search_results(results: list, is_news: bool, language: str) -> str:
    """Build a markdown reply directly from real SearXNG results."""
    header = "Today's relevant news:" if is_news else "Here's what I found:"
    lines = [header, ""]
    for i, r in enumerate(results[:5], 1):
        snippet = (r.snippet or "").strip()
        if len(snippet) > 180:
            snippet = snippet[:180].rsplit(" ", 1)[0] + "..."
        lines.append(f"**{i}. [{r.title}]({r.url})**")
        if snippet:
            lines.append(snippet)
        lines.append("")
    lines.append("_Results are from a live web search — click a source for details._")
    return "\n".join(lines).strip()


async def _handle_search(message: str, language: str) -> str:
    """Run a SearXNG search and return a fully-formatted reply. Never touches the LLM."""
    try:
        from app.research_engine.searcher import web_searcher

        if not await web_searcher.is_available():
            return (
                "Web search is currently unavailable (SearXNG is not "
                "reachable). Please check that it's running."
            )

        is_news = _is_news_query(message)
        if is_news:
            results = await asyncio.get_event_loop().run_in_executor(
                None, lambda: web_searcher.search_news(message, max_results=5, language=language)
            )
        else:
            results = await asyncio.get_event_loop().run_in_executor(
                None, lambda: web_searcher.search(message, max_results=5, language=language)
            )

        if not results:
            return "Sorry, the web search returned no results. Try rephrasing your query."

        logger.info("Web search: %d results for '%s'", len(results), message[:50])
        return _format_search_results(results, is_news, language)

    except Exception as e:
        logger.error("Web search failed: %s", e)
        return "Web search failed due to an internal error. Please try again."


async def _handle_system_info() -> str:
    """Get PC system info via SystemAgent and return a formatted reply."""
    try:
        from app.agents.system_agent import system_agent
        result = await system_agent.execute("health", {})
        if not result.success or not result.data:
            return "Could not retrieve system info right now."

        d = result.data
        cpu = d.get("cpu", {}).get("used_percent", "?")
        ram_used = d.get("ram", {}).get("used_percent", "?")
        ram_free = d.get("ram", {}).get("available_gb", "?")
        overall = d.get("overall", "unknown")

        return (
            f"**System Status: {overall}**\n\n"
            f"- CPU usage: {cpu}%\n"
            f"- RAM usage: {ram_used}% ({ram_free} GB free)\n"
        )
    except Exception as e:
        logger.error("System info failed: %s", e)
        return "Could not retrieve system info due to an internal error."


async def _handle_memory_save(
    db: AsyncSession,
    history: list[dict],
    language: str,
    raw_message: str,
) -> str:
    """
    Save to the Tier 2 Intelligence Layer (no staged file case).

    1. "<some fact>. save it" — content written IN THIS message is saved.
    2. A bare "save it" — falls back to AURA's most recent reply.

    auto_confirm=True because the user's "save it" IS the confirmation gate.
    """
    inline_content = _strip_save_trigger(raw_message)

    if len(inline_content) >= 8:
        save_content = inline_content
        title_source = inline_content
    else:
        last_user_content = None
        last_assistant_content = None
        for h in reversed(history):
            if h.get("role") == "assistant" and last_assistant_content is None:
                last_assistant_content = h.get("content", "")
            if (
                h.get("role") == "user"
                and last_user_content is None
                and not _matches(h.get("content", ""), SAVE_PATTERNS)
            ):
                last_user_content = h.get("content", "")
            if last_user_content is not None and last_assistant_content is not None:
                break

        if not last_assistant_content:
            return (
                "There's nothing recent to save yet — ask me something first."
                if language == "en" else
                "সংরক্ষণ করার মতো কিছু নেই এখনো, আগে কিছু জিজ্ঞেস করুন।"
            )

        save_content = last_assistant_content
        if last_user_content:
            save_content = f"Q: {last_user_content}\nA: {last_assistant_content}"
        title_source = last_user_content or last_assistant_content

    try:
        result = await intelligence_service.process(
            db=db, title=title_source[:100], content=save_content,
            source="chat", source_type="chat", language=language, auto_confirm=True,
        )
    except Exception as e:
        logger.error("Intelligence save failed: %s", e)
        return (
            "Sorry, I couldn't save that due to an internal error."
            if language == "en" else "দুঃখিত, সংরক্ষণ করতে সমস্যা হয়েছে।"
        )

    item = result.get("item", {})
    if result.get("action") == "evolved":
        return (
            f"✅ Updated existing memory to version {item.get('version', '?')}."
            if language == "en" else
            f"✅ বিদ্যমান তথ্য হালনাগাদ করা হয়েছে (ভার্সন {item.get('version', '?')})।"
        )
    return (
        f"✅ Saved as {item.get('knowledge_type', 'Knowledge')} "
        f"under {item.get('category', 'General')}."
        if language == "en" else "✅ মেমরিতে সংরক্ষণ করা হয়েছে।"
    )


SYNC_CHUNK_THRESHOLD = 3  # small files save inline; larger ones go to background


async def _handle_save_staged_file(
    db: AsyncSession, staged: dict, conversation_id: str, language: str, raw_message: str,
) -> str:
    """
    Save the currently staged file into the File Vault (permanent
    original + full text + page images) AND the Tier 2 Intelligence
    Layer (classified knowledge). Supports "save it as <name>" for
    cross-conversation recall by name; falls back to the filename.

    Does NOT clear staging after saving — follow-up questions keep
    working. Repeating "save it" is a safe no-op.

    Small files save synchronously (immediate confirmation); larger
    files run in the background to avoid exceeding HTTP timeouts.
    """
    if staged.get("saved"):
        vault_name = staged.get("vault_name") or staged["filename"]
        return (
            f"✅ '{staged['filename']}' is already saved as \"{vault_name}\". "
            f"Ask me anything else about it, or attach a new file."
            if language == "en" else
            f"✅ '{staged['filename']}' ইতিমধ্যে \"{vault_name}\" নামে সংরক্ষিত।"
        )

    name = _extract_save_name(raw_message) or Path(staged["filename"]).stem

    from app.ingestion.chunker import chunker
    from app.vault.vault_service import vault_service

    chunk_count = len(chunker.split(staged["text"]))

    if chunk_count <= SYNC_CHUNK_THRESHOLD:
        try:
            result = await vault_service.save_to_vault(db, name, staged, language, auto_confirm_tier2=True)
            staging_store.mark_saved(conversation_id, vault_item_id=result["vault_item_id"])
            record = staging_store.get(conversation_id)
            if record:
                record["vault_name"] = name
            tier2 = result["tier2"]
            return (
                f"✅ Saved as \"{name}\" ({tier2['created']} new, {tier2['evolved']} updated, "
                f"{tier2['failed']} failed, out of {tier2['chunks_processed']} section(s)). "
                f"Recall it anytime from any chat by mentioning \"{name}\"."
                if language == "en" else
                f"✅ \"{name}\" নামে সংরক্ষণ করা হয়েছে ({tier2['created']} নতুন, {tier2['evolved']} "
                f"আপডেট) — যেকোনো চ্যাটে \"{name}\" বললেই আবার খুঁজে পাবেন।"
            )
        except Exception as e:
            logger.error("Vault save failed: %s", e)
            return (
                "Sorry, I couldn't save that file due to an internal error."
                if language == "en" else "দুঃখিত, ফাইলটি সংরক্ষণ করতে সমস্যা হয়েছে।"
            )

    import asyncio
    from app.ingestion.job_store import ingestion_job_store

    ingestion_job_store.start(conversation_id, staged["filename"], chunk_count)
    asyncio.create_task(
        vault_service.save_to_vault_background(conversation_id, name, staged, language)
    )

    return (
        f"⏳ Saving \"{name}\" in the background ({chunk_count} sections) — "
        f"you can keep asking about it now, or ask \"is it saved?\" to check progress."
        if language == "en" else
        f"⏳ \"{name}\" ব্যাকগ্রাউন্ডে সংরক্ষণ হচ্ছে ({chunk_count}টি অংশ)। "
        f"এখনই এটা নিয়ে প্রশ্ন করতে পারেন, বা 'সংরক্ষণ হয়েছে কিনা' জিজ্ঞেস করুন।"
    )

DELETE_STOPWORDS = {
    "delete", "remove", "forget", "erase", "no", "not", "it", "that",
    "this", "the", "a", "an", "note", "about", "from", "memory", "please",
    "মুছে", "দাও", "ভুলে", "যাও", "ডিলিট", "করো", "এই", "সেই", "তথ্য",
}


def _extract_delete_keyword(message: str) -> str:
    """Extract the likely subject keyword from a delete request."""
    words = re.findall(r"[^\W\d_]+", message, re.UNICODE)
    kept = [w for w in words if w.lower() not in DELETE_STOPWORDS]
    return " ".join(kept).strip()


async def _handle_memory_delete(db: AsyncSession, message: str, history: list[dict]) -> str:
    """Delete confirmed KnowledgeItem entries (Tier 2) matching keywords."""
    try:
        from app.intelligence.models.knowledge_item import KnowledgeItem

        keyword = _extract_delete_keyword(message)

        result = await db.execute(
            select(KnowledgeItem)
            .where(KnowledgeItem.is_confirmed == True)  # noqa: E712
            .order_by(KnowledgeItem.created_at.desc())
        )
        confirmed = list(result.scalars().all())

        if not confirmed:
            return "There's nothing saved in permanent memory to delete."

        matches = []
        if keyword:
            matches = [
                e for e in confirmed
                if keyword.lower() in e.title.lower() or keyword.lower() in (e.summary or "").lower()
            ]
        if not matches:
            matches = [confirmed[0]]

        deleted_titles = [e.title[:60] for e in matches[:5]]
        for entry in matches[:5]:
            await db.delete(entry)
        await db.flush()

        listing = "\n".join(f"- {t}" for t in deleted_titles)
        return f"🗑️ Deleted {len(matches[:5])} memory entrie(s):\n{listing}"
    except Exception as e:
        logger.error("Memory delete failed: %s", e)
        return "Sorry, I couldn't delete that due to an internal error."


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/chat", summary="List Conversations", tags=["Chat"])
async def list_conversations(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[dict]:
    """List all conversations for sidebar history."""
    result = await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc()).limit(limit)
    )
    conversations = result.scalars().all()

    conv_list = []
    for conv in conversations:
        count_result = await db.execute(
            select(func.count(Message.id)).where(Message.conversation_id == conv.id)
        )
        msg_count = count_result.scalar() or 0

        first_msg_result = await db.execute(
            select(Message.content)
            .where(Message.conversation_id == conv.id, Message.role == "user")
            .order_by(Message.created_at).limit(1)
        )
        first_msg = first_msg_result.scalar()

        conv_list.append({
            "id": conv.id, "title": conv.title, "first_message": first_msg,
            "language": conv.language, "message_count": msg_count,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        })
    return conv_list


@router.post("/chat/new", summary="Create an Empty Conversation", tags=["Chat"])
async def create_conversation(language: str = "en", db: AsyncSession = Depends(get_db)) -> dict:
    """
    Create an empty conversation ahead of the first message.

    Used by the frontend when attaching a file BEFORE any message has
    been sent, so the file can be staged against a real conversation_id
    instead of requiring text first.
    """
    conversation = await conversation_repository.create_conversation(db, language=language)
    return {"conversation_id": conversation.id}


@router.post(
    "/chat", response_model=ChatResponse, summary="Chat with AURA",
    tags=["Chat"], status_code=status.HTTP_200_OK,
)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    """
    Main chat endpoint.

    Deterministic intents (search/system/save/delete) are handled
    directly in code and NEVER touch the LLM for their final text.
    If a file is staged for this conversation, general chat messages
    are answered using that file's real content as context.
    """
    if request.conversation_id:
        conversation = await conversation_repository.get_conversation(db, request.conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {request.conversation_id} not found.",
            )
    else:
        conversation = await conversation_repository.create_conversation(db, language=request.language)

    history = await conversation_repository.get_history(db, conversation.id)

    staged = staging_store.get(conversation.id)
    if not staged:
        # No file attached in THIS conversation — check if the message
        # mentions an already-saved vault item by name, and auto-attach
        # it. This is what makes recall work across different chats.
        vault_match = await vault_repository.find_matching_name(db, request.message)
        if vault_match:
            staged = staging_store.stage_from_vault(conversation.id, vault_match)

    intent = _detect_intent(request.message, staged=bool(staged))
    model_used = "aura-system"

    # ── Deterministic intents — never call the LLM ────────────────────────────
    if intent == "search":
        ai_response = await _handle_search(request.message, request.language)
    elif intent == "system":
        ai_response = await _handle_system_info()
    elif intent == "ingestion_status":
        ai_response = await _handle_ingestion_status(conversation.id, request.language)
    elif intent == "show_page" and staged:
        ai_response = await _handle_show_page(request.message, staged, request.language)
    elif intent == "show_page":
        ai_response = (
            "এখন কোনো ফাইল খোলা নেই — আগে সংযুক্ত করুন বা নাম উল্লেখ করুন।"
            if request.language == "bn" else
            "No file is open right now — attach a file or mention a saved file's name first."
        )
    elif intent == "save" and staged:
        ai_response = await _handle_save_staged_file(db, staged, conversation.id, request.language, request.message)
    elif intent == "save":
        ai_response = await _handle_memory_save(db, history, request.language, request.message)
    elif intent == "delete" and staged:
        staging_store.clear(conversation.id)
        ai_response = (
            f"🗑️ Removed the attached file ({staged['filename']}) — nothing was saved."
            if request.language == "en" else
            f"📎 সংযুক্ত ফাইল ({staged['filename']}) সরিয়ে দেওয়া হয়েছে, কিছু সংরক্ষণ করা হয়নি।"
        )
    elif intent == "delete":
        ai_response = await _handle_memory_delete(db, request.message, history)

    # ── Normal conversation — LLM with RAG, OR isolated file Q&A ─────────────
    else:
        if not await ollama_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AURA LLM is not available. Please ensure Ollama is running.",
            )

        file_context = staging_store.context_snippet(conversation.id) if staged else None
        enriched_message = request.message
        if file_context:
            # File Q&A uses a hyper-focused prompt: no AURA persona (which
            # strongly associates "MD Faysal Ahmed Bhuiyan" with identity
            # questions and was observed bleeding into document answers —
            # e.g. reporting Faysal as "chairman" when the document
            # actually named someone else), no chat history, no RAG
            # context. Just the document and the question, so a small
            # local model isn't pulled toward unrelated but
            # strongly-weighted associations.
            enriched_message += (
                f"\n\n[Attached file '{staged['filename']}' content:\n{file_context}]"
            )
            try:
                ai_response = await ollama_service.chat(
                    message=enriched_message, history=None,
                    system_prompt=FILE_QA_SYSTEM_PROMPT,
                )
            except ConnectionError as e:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
            except RuntimeError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        else:
            rag_context = ""
            try:
                rag_context = await memory_service.get_relevant_context(
                    query=request.message, conversation_id=conversation.id,
                )
            except Exception as e:
                logger.warning("RAG context failed: %s", e)

            if rag_context:
                enriched_message += f"\n\n[Relevant context from memory:\n{rag_context[:500]}]"

            try:
                ai_response = await ollama_service.chat(message=enriched_message, history=history)
            except ConnectionError as e:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
            except RuntimeError as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        model_used = ollama_service.model
        

    # ── Save both messages ────────────────────────────────────────────────────
    user_message = await conversation_repository.add_message(
        db, conversation_id=conversation.id, role="user", content=request.message,
    )
    try:
        await memory_service.store_message(
            message_id=user_message.id, conversation_id=conversation.id,
            role="user", content=request.message, language=request.language,
        )
    except Exception as e:
        logger.warning("ChromaDB store failed: %s", e)

    assistant_message = await conversation_repository.add_message(
        db, conversation_id=conversation.id, role="assistant",
        content=ai_response, model_used=model_used,
    )
    try:
        await memory_service.store_message(
            message_id=assistant_message.id, conversation_id=conversation.id,
            role="assistant", content=ai_response, language=request.language,
        )
    except Exception as e:
        logger.warning("ChromaDB assistant store failed: %s", e)

    logger.info(
        "Chat done | conv=%s | intent=%s | model=%s | staged=%s",
        conversation.id[:8], intent, model_used, bool(staged),
    )

    return ChatResponse(
        conversation_id=conversation.id, message_id=assistant_message.id,
        response=ai_response, model=model_used, language=request.language,
    )


@router.get(
    "/chat/{conversation_id}", response_model=ConversationHistoryResponse,
    summary="Get Conversation History", tags=["Chat"],
)
async def get_conversation_history(
    conversation_id: str, db: AsyncSession = Depends(get_db)
) -> ConversationHistoryResponse:
    """Get full conversation history."""
    conversation = await conversation_repository.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found.",
        )

    messages = [
        ConversationHistoryItem(
            id=msg.id, role=msg.role, content=msg.content,
            timestamp=msg.created_at.replace(tzinfo=timezone.utc).isoformat(),
        )
        for msg in conversation.messages
    ]

    return ConversationHistoryResponse(
        conversation_id=conversation.id, language=conversation.language,
        messages=messages, total=len(messages),
    )