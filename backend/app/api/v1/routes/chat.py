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
_BACKGROUND_TASKS: set = set()
# ── Intent patterns (checked in this priority order) ──────────────────────────

SAVE_PATTERNS = [
    r'\bsave it\b', r'\bremember this\b', r'\bsave this\b',
    r'\bkeep this\b', r'\bstore this\b', r'\bnote this\b',
    r'মনে রাখো', r'সেভ করো', r'সংরক্ষণ করো',
]

DELETE_PATTERNS = [
    r'\bdelete it\b', r'\bremove\b', r'\bforget\b', r'\berase\b',
    r'মুছে', r'ভুলে', r'ডিলিট',
]

SYSTEM_PATTERNS = [
    r'\bcheck cpu\b', r'\bcpu usage\b', r'\bcpu status\b',
    r'\bram status\b', r'\bram usage\b', r'\bmemory usage\b',
    r'\bdisk usage\b', r'\bdisk status\b',
    r'\bsystem info\b', r'\bsystem status\b', r'\bpc status\b',
    r'\bhow.?s (my |the )?(pc|computer|system)\b',
]
COMPUTER_PATTERNS = [
    r'\btake.*screenshot\b', r'\bscreenshot\b',
    r'\bclipboard\b', r'\bopen.*browser\b',
    r'\bopen\s+https?://\b',
    r'\brun.*command\b', r'\bpowershell\b',
    r'\blist.*windows\b', r'\bopen.*windows\b',
]

CODE_AGENT_PATTERNS = [
    r'\bwrite.*code\b', r'\bgenerate.*code\b',
    r'\bfix.*code\b', r'\bfix.*bug\b',
    r'\bexplain.*code\b', r'\breview.*code\b',
    r'\bwrite.*function\b', r'\bwrite.*class\b',
    r'\bgenerate.*test\b',
]

SUB_AGENT_CREATE_PATTERNS = [r'^(create|make|build)\s+sub[- ]?agent\s*:', r'^sub[- ]?agent\s*banao\s*:']
SUB_AGENT_TEACH_PATTERNS  = [r'^teach\s+sub[- ]?agent\s+\S+\s*:', r'^sub[- ]?agent\s+\S+\s+(ke\s+)?shikhao\s*:']
SUB_AGENT_ASK_PATTERNS    = [r'^ask\s+sub[- ]?agent\s+\S+\s*:', r'^sub[- ]?agent\s+\S+\s*:']
SUB_AGENT_LIST_PATTERNS   = [r'^list\s+sub[- ]?agents?\s*$', r'^sub[- ]?agent\s*list\s*$']


IMAGE_GEN_PATTERNS = [
    r'\b(generate|genarate|create|draw|make|render)\b.*\b(image|picture|photo|pic)\b',
    r'\b(image|picture|photo)\s+of\b',
    r'ছবি\s*(বানাও|তৈরি করো|আঁকো|জেনারেট)',
    r'\b(photorealistic|highly detailed|depth of field|film grain|'
    r'shallow focus|cinematic lighting|natural daylight|8k|dslr)\b',
    r'\b(image|picture|photo|photograph)\s+of\b',
]

IMAGE_GEN_STRIP_PATTERNS = [
    r'\b(please\s+)?(generate|genarate|create|draw|make|render)\b\s*(an?|the)?\s*(image|picture|photo|pic)\b\s*(of|showing|depicting)?\s*',
    r'ছবি\s*(বানাও|তৈরি করো|আঁকো|জেনারেট করো)\s*',
]

VIDEO_GEN_PATTERNS = [
    r'\b(generate|create|make)\b.*\bvideo\b',
    r'ভিডিও\s*(বানাও|তৈরি করো)',
]

VIDEO_GEN_STRIP_PATTERNS = [
    r'\b(please\s+)?(generate|create|make)\b\s*(an?|the)?\s*video\b\s*(of|showing|depicting)?\s*',
    r'ভিডিও\s*(বানাও|তৈরি করো)\s*',
]
LEARN_URL_PATTERNS = [r'^learn\s+from\s+url\s*:', r'^url\s+theke\s+shikho\s*:']
LEARN_YOUTUBE_PATTERNS = [r'^learn\s+from\s+youtube\s*:', r'^youtube\s+theke\s+shikho\s*:']
THINK_PATTERNS = [r'^think\s+critically\s+about\s*:', r'^analyze\s*:', r'^critically\s+analyze\s*:']
SOLVE_PATTERNS = [r'^solve\s*:', r'^help\s+me\s+solve\s*:']
SYNTHESIZE_PATTERNS = [r'^synthesize\s*:', r'^what\s+do\s+you\s+know\s+about\s*:', r'^summarize\s+everything\s+about\s*:']

SECURITY_STATUS_PATTERNS = [r'^security\s+status\s*$', r'^security\s+report\s*$']
TRANSFORM_IMAGE_PATTERNS = [r'^transform\s+image\s*:']

TRANSFORM_IMAGE_PATTERNS = [r'^transform\s+image\s*:', r'^style\s+it\s*:']

# CODING role trigger — routes through CodingAgent's existing
# Plan → Code → Self-review pipeline, but with BrainRole.CODING
# instead of the default aura-brain for all three stages
CODING_TRIGGERS = ["write code for", "implement:", "build a function", ...]

# BUSINESS role trigger — new, simpler single-call flow (no need for
# CodingAgent's 3-stage pipeline; a decision-analysis flow is closer to
# the existing Tier 6A "think critically about" / "solve:" pattern —
# reuse reasoning_service.py's structure, just swap which model it calls)
BUSINESS_TRIGGERS = ["business decision:", "analyze this for my business:", "marketing:", ...]

def _extract_image_prompt(message: str) -> str:
    """Strip the trigger phrase, leave the actual image description."""
    cleaned = message
    for p in IMAGE_GEN_STRIP_PATTERNS:
        cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" .,!?।\n")
def _looks_like_long_image_prompt(message: str) -> bool:
    """
    Long, descriptive scene prompts starting with Generate/Create are
    almost always meant as image prompts, even without the exact word
    'image'/'picture'/'photo' — length + trigger verb is signal enough.
    """
    if "video" in message.lower() or "ভিডিও" in message:
        return False
    starts_right = bool(re.match(r'^\s*(generate|genarate|create)\b', message, re.IGNORECASE))
    return starts_right and len(message) > 120

def _extract_video_prompt(message: str) -> str:
    """Strip the trigger phrase, leave the actual video description."""
    cleaned = message
    for p in VIDEO_GEN_STRIP_PATTERNS:
        cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" .,!?।\n")

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
    if _matches(message, COMPUTER_PATTERNS):
     return "computer"
    if _matches(message, SUB_AGENT_LIST_PATTERNS):
        return "sub_agent_list"
    if _matches(message, SUB_AGENT_CREATE_PATTERNS):
        return "sub_agent_create"
    if _matches(message, SUB_AGENT_TEACH_PATTERNS):
        return "sub_agent_teach"
    if _matches(message, SUB_AGENT_ASK_PATTERNS):
        return "sub_agent_ask"
    if _matches(message, CODE_AGENT_PATTERNS):
        return "code_agent"
    if _matches(message, IMAGE_GEN_PATTERNS) or _looks_like_long_image_prompt(message):
        return "image_gen"
    if _matches(message, VIDEO_GEN_PATTERNS):
        return "video_gen"
    if _matches(message, LEARN_URL_PATTERNS):
         return "learn_url"
    if _matches(message, LEARN_YOUTUBE_PATTERNS):
         return "learn_youtube"
    if _matches(message, THINK_PATTERNS):
         return "think"
    if _matches(message, SOLVE_PATTERNS):
         return "solve"
    if _matches(message, SYNTHESIZE_PATTERNS):
         return "synthesize"
    if _matches(message, SECURITY_STATUS_PATTERNS):
         return "security_status"
    if _matches(message, TRANSFORM_IMAGE_PATTERNS):
        return "transform_image"
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

async def _handle_image_gen(message: str, language: str) -> str:
    """Generate a local image via SD Turbo/Realistic Vision and return an [[IMAGE:url]] reply."""
    from app.services.image_service import image_service

    prompt = _extract_image_prompt(message)
    if not prompt:
        return (
            "দয়া করে বলুন কী ছবি বানাতে চান, যেমন: 'একটা লাল বাইসাইকেলের ছবি বানাও'"
            if language == "bn" else
            "Tell me what to draw — e.g. 'generate an image of a red bicycle'."
        )

    realistic_keywords = ("realistic", "photorealistic", "photo", "বাস্তব", "রিয়েলিস্টিক")
    quality = "realistic" if any(k in message.lower() for k in realistic_keywords) else "fast"

    if quality == "realistic":
        wait_notice = (
            "⏳ Realistic mode — এটা ১৫-২০ মিনিট সময় নেবে, অপেক্ষা করো...\n\n"
            if language == "bn" else
            "⏳ Realistic mode — this will take about 15-20 minutes, please wait...\n\n"
        )
    else:
        wait_notice = ""

    result = await image_service.generate(prompt=prompt, quality=quality)
    if not result.get("success"):
        err = result.get("error", "unknown error")
        return (
            f"❌ ছবি বানাতে ব্যর্থ হয়েছে: {err}" if language == "bn"
            else f"❌ Image generation failed: {err}"
        )

    image_url = f"/api/v1/image/file/{result['file_name']}"
    took_s = result.get("duration_ms", 0) / 1000
    caption = (
        f"🎨 তৈরি হয়েছে ({took_s:.0f}s, {quality}):" if language == "bn"
        else f"🎨 Generated in {took_s:.0f}s ({quality}):"
    )
    return f"{wait_notice}{caption}\n\n[[IMAGE:{image_url}]]"

async def _handle_video_gen(message: str, language: str) -> str:
    """Generate a short video via Hugging Face (free tier) and return a link."""
    from app.services.video_service import video_service

    prompt = _extract_video_prompt(message)
    if not prompt:
        return (
            "দয়া করে বলুন কী ভিডিও বানাতে চান।" if language == "bn"
            else "Tell me what video to make — e.g. 'generate a video of a cat playing'."
        )

    wait_notice = (
        "⏳ Video তৈরি হতে কয়েক মিনিট লাগতে পারে (Hugging Face free tier), অপেক্ষা করো...\n\n"
        if language == "bn" else
        "⏳ This may take a few minutes (Hugging Face free tier), please wait...\n\n"
    )

    result = await video_service.generate_text_to_video(prompt)
    if not result.get("success"):
        err = result.get("error", "unknown error")
        return (
            f"❌ ভিডিও বানাতে ব্যর্থ হয়েছে: {err}" if language == "bn"
            else f"❌ Video generation failed: {err}"
        )

    video_url = f"http://127.0.0.1:8000/api/v1/video/file/{result['file_name']}"
    took_s = result.get("duration_ms", 0) / 1000
    caption = (
        f"🎬 ভিডিও তৈরি হয়েছে ({took_s:.0f}s):\n{video_url}" if language == "bn"
        else f"🎬 Video generated in {took_s:.0f}s:\n{video_url}"
    )
    return f"{wait_notice}{caption}"

async def _handle_learn_url(message: str, db, language: str) -> str:
    """Read a URL's real content and feed it into the Tier 2 knowledge pipeline."""
    from app.intelligence.intelligence_service import intelligence_service
    from app.services.deep_reader_service import deep_reader_service

    url = message.split(":", 1)[1].strip() if ":" in message else ""
    if not url:
        return "কোন URL পড়তে হবে?" if language == "bn" else "Which URL should I read?"

    result = await deep_reader_service.read_url(url)
    if not result.get("success"):
        return (
            f"❌ পড়তে ব্যর্থ: {result.get('error')}" if language == "bn"
            else f"❌ Failed to read: {result.get('error')}"
        )

    outcome = await intelligence_service.process(
        db=db, title=result["title"], content=result["content"],
        source=result["source"], source_type="url", language=language,
        auto_confirm=True,
    )
    return (
        f"📖 পড়া হয়েছে: '{result['title']}' — knowledge base-এ যোগ হয়েছে।"
        if language == "bn" else
        f"📖 Learned from: '{result['title']}' — added to the knowledge base."
    )


async def _handle_learn_youtube(message: str, db, language: str) -> str:
    """Read a YouTube video's transcript and feed it into the Tier 2 knowledge pipeline."""
    from app.intelligence.intelligence_service import intelligence_service
    from app.services.deep_reader_service import deep_reader_service

    url = message.split(":", 1)[1].strip() if ":" in message else ""
    if not url:
        return "কোন YouTube ভিডিও থেকে শিখব?" if language == "bn" else "Which YouTube video should I learn from?"

    result = await deep_reader_service.read_youtube(url)
    if not result.get("success"):
        return (
            f"❌ পড়তে ব্যর্থ: {result.get('error')}" if language == "bn"
            else f"❌ Failed to read: {result.get('error')}"
        )

    outcome = await intelligence_service.process(
        db=db, title=result["title"], content=result["content"],
        source=result["source"], source_type="youtube", language=language,
        auto_confirm=True,
    )
    return (
        f"📺 ভিডিও থেকে শেখা হয়েছে — knowledge base-এ যোগ হয়েছে।"
        if language == "bn" else
        f"📺 Learned from the video transcript — added to the knowledge base."
    )

async def _handle_think(message: str, language: str) -> str:
    """A2: Critical thinking — analyze a topic with evidence, structured."""
    from app.services.reasoning_service import reasoning_service

    topic = message.split(":", 1)[1].strip() if ":" in message else ""
    if not topic:
        return "কোন বিষয়ে critically think করব?" if language == "bn" else "What topic should I think critically about?"

    result = await reasoning_service.critical_think(topic, language)
    return f"🧠 {result['analysis']}"


async def _handle_solve(message: str, language: str) -> str:
    """A3: Problem solving — decompose, weigh options, recommend."""
    from app.services.reasoning_service import reasoning_service

    problem = message.split(":", 1)[1].strip() if ":" in message else ""
    if not problem:
        return "কোন সমস্যা সমাধান করব?" if language == "bn" else "What problem should I help solve?"

    result = await reasoning_service.solve_problem(problem, language)
    return f"🔧 **Breakdown:**\n{result['breakdown']}\n\n**Solution:**\n{result['solution']}"


async def _handle_synthesize(message: str, language: str) -> str:
    """A4: Knowledge synthesis — combine what's been taught into one answer."""
    from app.services.reasoning_service import reasoning_service

    topic = message.split(":", 1)[1].strip() if ":" in message else ""
    if not topic:
        return "কোন বিষয়ে জানা সব কিছু একসাথে করব?" if language == "bn" else "What topic should I synthesize known information about?"

    result = await reasoning_service.synthesize_knowledge(topic, language)
    if not result.get("success"):
        return f"❌ {result.get('error')}"
    return f"🔗 {result['synthesis']}\n\n_({result['sources_used']} sources used)_"

async def _handle_security_status(language: str) -> str:
    """Report the security monitor's running state and recent alerts."""
    from app.security.security_service import security_service

    status = security_service.status()
    running = status["running"]
    alerts = status["recent_alerts"]

    lines = [
        f"🛡️ Security monitor: {'🟢 running' if running else '🔴 stopped'}",
    ]
    if not alerts:
        lines.append("No alerts recorded.")
    else:
        lines.append(f"\nRecent alerts ({len(alerts)}):")
        for a in alerts[:10]:
            lines.append(f"• [{a['level'].upper()}] {a['ip']} — {'; '.join(a['reasons'])}")

    return "\n".join(lines)

async def _handle_transform_image(message: str, staged: dict | None, language: str) -> str:
    """Apply an AI style transform to the currently staged/attached image."""
    from app.services.image_service import image_service

    if not staged or not staged.get("original_path"):
        return (
            "প্রথমে একটা ছবি upload/attach করো (📎 দিয়ে), তারপর 'transform image: <style>' লিখো।"
            if language == "bn" else
            "Attach an image first (📎), then say 'transform image: <style>'."
        )

    style = message.split(":", 1)[1].strip() if ":" in message else ""
    if not style:
        return (
            "কোন style চাও? (cartoon, anime, watercolor painting, pencil sketch, বা নিজের prompt)"
            if language == "bn" else
            "What style? (cartoon, anime, watercolor painting, pencil sketch, or your own description)"
        )

    wait_notice = (
        "⏳ Best quality transform হতে ১৫-২৫ মিনিট লাগতে পারে (ধৈর্য ধরো)...\n\n" if language == "bn"
        else "⏳ Best-quality transform can take 15-25 minutes — please be patient...\n\n"
    )

    logger.warning("TRANSFORM DEBUG: using source image path = %s", staged["original_path"])

    result = await image_service.transform_image(
        image_path=staged["original_path"], style_prompt=style,
        quality="realistic", strength=0.55,
    )
    if not result.get("success"):
        return f"❌ {result.get('error')}"

    image_url = f"/api/v1/image/file/{result['file_name']}"
    return f"{wait_notice}🎨 Done (source: `{staged['original_path']}`):\n\n[[IMAGE:{image_url}]]"


async def _handle_sub_agent_list(db) -> str:
    from app.agents_v2.sub_agent_factory import sub_agent_factory

    agents = await sub_agent_factory.list_sub_agents(db)
    if not agents:
        return "এখনো কোনো sub-agent তৈরি হয়নি। 'create sub agent: <task>' লিখে একটা বানাও।"

    lines = ["তোমার sub-agents:"]
    for a in agents:
        lines.append(f"• **{a['name']}** — {a['task_description']} ({a['knowledge_count']} things taught)")
    return "\n".join(lines)


async def _handle_sub_agent_create(message: str, db) -> str:
    from app.agents_v2.sub_agent_factory import sub_agent_factory

    task_description = message.split(":", 1)[1].strip() if ":" in message else ""
    if not task_description:
        return "কী কাজের জন্য sub-agent বানাতে চাও? যেমন: 'create sub agent: writing Python code'"

    result = await sub_agent_factory.create_sub_agent(db, task_description)
    return (
        f"✅ Sub-agent **{result['name']}** তৈরি হয়েছে, কাজ: {task_description}\n\n"
        f"এখন শেখাতে পারো: 'teach sub agent {result['name']}: <কিছু তথ্য>'\n"
        f"জিজ্ঞেস করতে পারো: 'ask sub agent {result['name']}: <প্রশ্ন>'"
    )


async def _handle_sub_agent_teach(message: str, db) -> str:
    from app.agents_v2.sub_agent_factory import sub_agent_factory

    m = re.match(r'^(?:teach\s+sub[- ]?agent|sub[- ]?agent)\s+(\S+)', message, re.IGNORECASE)
    name = m.group(1) if m else ""
    content = message.split(":", 1)[1].strip() if ":" in message else ""

    if not name or not content:
        return "সঠিক format: 'teach sub agent <name>: <শেখানোর তথ্য>'"

    result = await sub_agent_factory.teach(db, name, content)
    if not result.get("success"):
        return f"❌ {result.get('error')}"
    return f"✅ **{name}**-কে শেখানো হয়েছে।"


async def _handle_sub_agent_ask(message: str, db) -> str:
    from app.agents_v2.sub_agent_factory import sub_agent_factory

    m = re.match(r'^(?:ask\s+sub[- ]?agent|sub[- ]?agent)\s+(\S+)', message, re.IGNORECASE)
    name = m.group(1) if m else ""
    question = message.split(":", 1)[1].strip() if ":" in message else ""

    if not name or not question:
        return "সঠিক format: 'ask sub agent <name>: <প্রশ্ন>'"

    result = await sub_agent_factory.ask(db, name, question)
    if not result.get("success"):
        return f"❌ {result.get('error')}"
    return f"🤖 **{name}**:\n\n{result['answer']}"


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
    bg_task = asyncio.create_task(
        vault_service.save_to_vault_background(conversation_id, name, staged, language)
    )
    _BACKGROUND_TASKS.add(bg_task)
    bg_task.add_done_callback(_BACKGROUND_TASKS.discard)

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
    # ── Vault name auto-recall ────────────────────────────────────────────────────
    if not staged:
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
    # ── If staged is an image and user asking to see it ───────────────────────────
    if staged and staged.get("kind") == "image" and intent == "chat":
        # Check if user wants to see the image
        show_words = ["show", "see", "view", "display", "দেখাও", "দেখতে চাই"]
        if any(w in request.message.lower() for w in show_words) or \
        any(name in request.message.lower()
            for name in [staged.get("vault_name", "").lower(),
                            staged.get("filename", "").lower()]):
            vault_id = staged.get("vault_item_id")
            if vault_id:
                filename = staged.get("filename", "image")
                image_url = f"/api/v1/vault/{vault_id}/image"
                ai_response = (
                    f"📸 Here is your saved image '{staged.get('vault_name', filename)}':\n\n"
                    f"[[IMAGE:{image_url}]]"
                )
                # Skip LLM call — go directly to save messages
                user_message = await conversation_repository.add_message(
                    db, conversation_id=conversation.id,
                    role="user", content=request.message,
                )
                try:
                    await memory_service.store_message(
                        message_id=user_message.id,
                        conversation_id=conversation.id,
                        role="user", content=request.message,
                        language=request.language,
                    )
                except Exception:
                    pass

                assistant_message = await conversation_repository.add_message(
                    db, conversation_id=conversation.id,
                    role="assistant", content=ai_response,
                    model_used="aura-system",
                )
                return ChatResponse(
                    conversation_id=conversation.id,
                    message_id=assistant_message.id,
                    response=ai_response,
                    model="aura-system",
                    language=request.language,
                )
    elif intent == "ingestion_status":
        pass  # already handled correctly by the first if/elif chain above

    elif intent == "computer":
        try:
            from app.computer_control.computer_service import computer_service
            action = computer_service.detect_action(request.message)
            if action:
                result = await computer_service.execute(
                    action=action,
                    params={"message": request.message},
                    confirmed=False,
                )
                if result.get("success"):
                    if action == "screenshot":
                        ai_response = f"✅ Screenshot taken: `{result.get('file_path', '')}`"
                    elif action == "screenshot_ocr":
                        ocr = result.get("ocr_text", "")
                        ai_response = f"📷 Screen text:\n\n{ocr[:1000]}" if ocr else "No text found on screen."
                    elif action == "clipboard_read":
                        content = result.get("content", "")
                        ai_response = f"📋 Clipboard:\n\n{content[:500]}" if content else "Clipboard is empty."
                    elif action == "window_list":
                        windows = result.get("windows", [])
                        titles = [w["title"] for w in windows[:10]]
                        ai_response = "🪟 Open windows:\n" + "\n".join(f"- {t}" for t in titles)
                    elif action == "open_url":
                        ai_response = f"🌐 {result.get('message', 'Opened in browser.')}"
                    else:
                        ai_response = f"✅ Done: {result.get('message', 'Action completed.')}"
                else:
                    ai_response = f"❌ {result.get('error', 'Action failed.')}"
            else:
                ai_response = "I couldn't identify a specific computer action. Try: 'take screenshot', 'read clipboard', 'list windows'."
        except Exception as e:
            logger.warning("Computer control failed: %s", e)
            ai_response = "Computer control encountered an error."

    elif intent == "learn_url":
         ai_response = await _handle_learn_url(request.message, db, request.language)
         model_used = "deep-reader"
    elif intent == "learn_youtube":
         ai_response = await _handle_learn_youtube(request.message, db, request.language)
         model_used = "deep-reader"

    elif intent == "think":
         ai_response = await _handle_think(request.message, request.language)
         model_used = "reasoning"
    elif intent == "solve":
         ai_response = await _handle_solve(request.message, request.language)
         model_used = "reasoning"
    elif intent == "synthesize":
         ai_response = await _handle_synthesize(request.message, request.language)
         model_used = "reasoning"
    elif intent == "security_status":
         ai_response = await _handle_security_status(request.language)
         model_used = "security"
    elif intent == "transform_image":
        ai_response = await _handle_transform_image(request.message, staged, request.language)
        model_used = "image-transform"
    elif intent == "code_agent":
        try:
            from app.agents_v2.agent_service import agent_service
            from app.agents_v2.coordinator import agent_coordinator
            task_type = agent_coordinator.detect_task_type(request.message)
            result = await agent_service.run(
                task=request.message,
                context={"task_type": task_type},
                agent_id="coding",
            )
            ai_response = result["output"] if result["success"] else f"❌ {result['error']}"
            model_used = "coding-agent"
        except Exception as e:
            logger.warning("Code agent failed: %s", e)
            ai_response = "Code agent encountered an error."
    elif intent == "image_gen":
        ai_response = await _handle_image_gen(request.message, request.language)
        model_used = "image-gen"
    elif intent == "video_gen":
        ai_response = await _handle_video_gen(request.message, request.language)
        model_used = "video-gen"

    elif intent == "sub_agent_list":
        ai_response = await _handle_sub_agent_list(db)
        model_used = "sub-agent"
    elif intent == "sub_agent_create":
        ai_response = await _handle_sub_agent_create(request.message, db)
        model_used = "sub-agent"
    elif intent == "sub_agent_teach":
        ai_response = await _handle_sub_agent_teach(request.message, db)
        model_used = "sub-agent"
    elif intent == "sub_agent_ask":
        ai_response = await _handle_sub_agent_ask(request.message, db)
        model_used = "sub-agent"

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
@router.delete("/chat/{conversation_id}", summary="Delete a Conversation", tags=["Chat"])
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Permanently delete a conversation and all its messages."""
    deleted = await conversation_repository.delete_conversation(db, conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found.",
        )
    return {"deleted": True, "conversation_id": conversation_id}