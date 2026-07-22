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

Bangla/Banglish auto-translation is intentionally OUT OF SCOPE for this
fix — tracked separately, not touched here.

Special commands AURA understands from chat (English only for now):
    "search X" / "find X" / "news"      -> deterministic web search reply
    "check cpu" / "ram status"           -> deterministic system info reply
    "save it" / "remember this"          -> saves the previous AI reply to memory
    "delete from memory" / "forget this" -> removes matching memory entries
    (anything else)                      -> normal LLM conversation + RAG
"""

import asyncio
import logging
import re
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
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
# NOTE: "how to X" was removed from search patterns — it matched almost
# every question and forced normal conversation into web search.

SAVE_PATTERNS = [
    r'^save it\b', r'^remember this\b', r'^save this\b',
    r'^keep this\b', r'^store this\b', r'^note this\b',
    r'^মনে রাখো', r'^সেভ করো', r'^সংরক্ষণ করো',
]
# "delete"/"forget"/"remove" almost never come up in casual conversation,
# so ANY message containing one of these verbs is treated as a delete
# intent — far more reliable than trying to enumerate every phrasing
# ("delete it", "no delete it", "forget that", "please remove it" etc).

DELETE_PATTERNS = [
    r'\bdelete from memory\b', r'\bremove from memory\b',
    r'\bforget this\b', r'\bforget that\b',r'\bdelete\b', 
    r'\bমেমরি থেকে মুছে দাও\b', r'\bভুলে যাও\b',
]

SYSTEM_PATTERNS = [
    r'\bcheck cpu\b', r'\bcpu usage\b', r'\bcpu status\b',
    r'\bram status\b', r'\bram usage\b', r'\bmemory usage\b',
    r'\bdisk usage\b', r'\bdisk status\b',
    r'\bsystem info\b', r'\bsystem status\b', r'\bpc status\b',
    r'\bhow.?s (my |the )?(pc|computer|system)\b',
]
# Action verb (search/check/find/lookup/go to/research) + the message is
# not trivially short = treat as a search intent. This is deliberately
# broad because a 3B local model cannot be trusted to answer factual/
# current-info questions from its own memory without hallucinating.

SEARCH_PATTERNS = [
    r'\bsearch\b','\bcheck\b', r'\bfind\b(?!.*\bfile\b)', r'\block up\b',
    r'\bcheck online\b', r'\bnews\b', r'\blatest\b',
    r'\bwhat is\b', r'\bwho is\b', r'\bwhere is\b',
    r'\b(20[2-9]\d)\b',
    r'\bখবর\b', r'\bসংবাদ\b', r'\bখোঁজ\b', r'\bআজকের\b',
]

NEWS_WORDS = {
    "news", "খবর","info", "সংবাদ", "today", "আজকের",
    "latest", "current", "breaking", "headlines",
}


def _matches(text: str, patterns: list[str]) -> bool:
    """Check if any pattern matches the text."""
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _is_news_query(message: str) -> bool:
    return any(w in message.lower() for w in NEWS_WORDS)


def _detect_intent(message: str) -> str:
    """
    Classify a message into exactly one deterministic intent, checked
    in a fixed priority order so overlapping matches don't collide.

    'save' is checked first since it's the narrowest/most explicit
    pattern set (anchored to the start of the message). 'delete' is
    checked next since delete verbs almost never appear in casual
    conversation, making false positives unlikely even with a broad
    pattern.

    Returns:
        str: 'save' | 'delete' | 'system' | 'search' | 'chat'
    """
    if _matches(message, SAVE_PATTERNS):
        return "save"
    if _matches(message, DELETE_PATTERNS):
        return "delete"
    if _matches(message, SYSTEM_PATTERNS):
        return "system"
    if _matches(message, SEARCH_PATTERNS):
        return "search"
    return "chat"


# ── Deterministic handlers — each returns the FULL final reply text ──────────
# None of these call the LLM. This is the fix for F2/F3/F4: a 3B model
# cannot reliably relay search/system/memory results without inventing
# details, so the code builds the final answer directly.

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
    """
    Run a SearXNG search and return a fully-formatted reply.
    Never touches the LLM — avoids hallucinated sources.
    """
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
) -> str:
    """
    Save the most recent assistant reply to permanent-pending memory.

    Saves the LAST ASSISTANT MESSAGE (what AURA just said), not an
    arbitrary earlier user message — this is the content the user is
    almost always referring to when they say "save it" / "remember this"
    right after AURA answers something.

    Args:
        db: Async database session.
        history: Conversation history (list of {"role", "content"}).
        language: Language code.

    Returns:
        str: Confirmation or error message.
    """
    last_assistant_content = None
    for h in reversed(history):
        if h.get("role") == "assistant":
            last_assistant_content = h.get("content", "")
            break

    if not last_assistant_content:
        return "There's nothing recent to save yet — ask me something first."

    try:
        from app.repositories.knowledge_repository import knowledge_repository

        entry = await knowledge_repository.create_entry(
            db,
            title=last_assistant_content[:80],
            summary=last_assistant_content,
            source_name="chat_confirmation",
            confidence=0.8,
            language=language,
        )
        # User explicitly said "save it" — that IS the confirmation gate,
        # so confirm immediately rather than leaving it pending again.
        await knowledge_repository.confirm_entry(db, entry.id)

        return f"✅ Saved to permanent memory (id: {entry.id[:8]})."
    except Exception as e:
        logger.error("Memory save failed: %s", e)
        return "Sorry, I couldn't save that due to an internal error."


# Words to strip out of a delete request to find the actual search
# keyword the user means (e.g. "forget the note about RJSC" -> "RJSC").
DELETE_STOPWORDS = {
    "delete", "remove", "forget", "erase", "no", "not", "it", "that",
    "this", "the", "a", "an", "note", "about", "from", "memory", "please",
    "মুছে", "দাও", "ভুলে", "যাও", "ডিলিট", "করো", "এই", "সেই", "তথ্য",
}


def _extract_delete_keyword(message: str) -> str:
    """
    Extract the likely subject keyword from a delete request by
    stripping known command/filler words, keeping whatever remains.

    Args:
    message: The user's delete request.

    Returns:
        str: A best-effort keyword, or empty string if nothing remains.
    """
    words = re.findall(r"[^\W\d_]+", message, re.UNICODE)
    kept = [w for w in words if w.lower() not in DELETE_STOPWORDS]
    return " ".join(kept).strip()


async def _handle_memory_delete(
    db: AsyncSession,
    message: str,
    history: list[dict],
) -> str:
    """
    Delete confirmed knowledge entries matching keywords from the message.

    If the message alone has no usable keyword (e.g. just "no delete it"),
    falls back to matching against the title/summary of the most recently
    saved memory — since that's almost always what "delete it" refers to
    right after a "save it".

    Args:
        db: Async database session.
        message: The user's delete request.
        history: Conversation history, used as a fallback subject source.

    Returns:
    str: Confirmation or error message.
    """
    try:
        from app.repositories.knowledge_repository import knowledge_repository

        keyword = _extract_delete_keyword(message)
        confirmed = await knowledge_repository.get_confirmed(db)

        if not confirmed:
            return "There's nothing saved in permanent memory to delete."

        matches = []
        if keyword:
            matches = [
                e for e in confirmed
                if keyword.lower() in e.title.lower() or keyword.lower() in e.summary.lower()
             ]

        if not matches:
            # Fallback: "delete it" with no clear keyword right after a
            # save — assume they mean the most recently saved entry.
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
async def list_conversations(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all conversations for sidebar history."""
    result = await db.execute(
        select(Conversation)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    conversations = result.scalars().all()

    conv_list = []
    for conv in conversations:
        count_result = await db.execute(
            select(func.count(Message.id)).where(
                Message.conversation_id == conv.id
            )
        )
        msg_count = count_result.scalar() or 0

        first_msg_result = await db.execute(
            select(Message.content)
            .where(
                Message.conversation_id == conv.id,
                Message.role == "user",
            )
            .order_by(Message.created_at)
            .limit(1)
        )
        first_msg = first_msg_result.scalar()

        conv_list.append({
            "id": conv.id,
            "title": conv.title,
            "first_message": first_msg,
            "language": conv.language,
            "message_count": msg_count,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        })

    return conv_list


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with AURA",
    tags=["Chat"],
    status_code=status.HTTP_200_OK,
)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Main chat endpoint.

    Deterministic intents (search/system/save/delete) are handled
    directly in code and NEVER touch the LLM — this is what fixes
    F2/F3/F4: a small local model cannot reliably relay factual data
    without inventing details. Only genuine conversation goes to Ollama.
    """
    # ── Get or create conversation ────────────────────────────────────────────
    if request.conversation_id:
        conversation = await conversation_repository.get_conversation(
            db, request.conversation_id
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {request.conversation_id} not found.",
            )
    else:
        conversation = await conversation_repository.create_conversation(
            db, language=request.language,
        )

    history = await conversation_repository.get_history(db, conversation.id)
    intent = _detect_intent(request.message)
    model_used = "aura-system"

    # ── Deterministic intents — never call the LLM ────────────────────────────
    if intent == "search":
        ai_response = await _handle_search(request.message, request.language)
    elif intent == "system":
        ai_response = await _handle_system_info()
    elif intent == "save":
        ai_response = await _handle_memory_save(db, history, request.language)
    elif intent == "delete":
        ai_response = await _handle_memory_delete(db, request.message, history)

    # ── Normal conversation — LLM with RAG context ────────────────────────────
    else:
        if not await ollama_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AURA LLM is not available. Please ensure Ollama is running.",
            )

        rag_context = ""
        try:
            rag_context = await memory_service.get_relevant_context(
                query=request.message,
                conversation_id=conversation.id,
            )
        except Exception as e:
            logger.warning("RAG context failed: %s", e)

        enriched_message = request.message
        if rag_context:
            enriched_message += f"\n\n[Relevant context from memory:\n{rag_context[:500]}]"

        try:
            ai_response = await ollama_service.chat(
                message=enriched_message,
                history=history,
            )
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
        "Chat done | conv=%s | intent=%s | model=%s",
        conversation.id[:8], intent, model_used,
    )

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        response=ai_response,
        model=model_used,
        language=request.language,
    )


@router.get(
    "/chat/{conversation_id}",
    response_model=ConversationHistoryResponse,
    summary="Get Conversation History",
    tags=["Chat"],
)
async def get_conversation_history(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
) -> ConversationHistoryResponse:
    """Get full conversation history."""
    conversation = await conversation_repository.get_conversation(
        db, conversation_id
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found.",
        )

    messages = [
        ConversationHistoryItem(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            timestamp=msg.created_at.replace(tzinfo=timezone.utc).isoformat(),
        )
        for msg in conversation.messages
    ]

    return ConversationHistoryResponse(
        conversation_id=conversation.id,
        language=conversation.language,
        messages=messages,
        total=len(messages),
    )