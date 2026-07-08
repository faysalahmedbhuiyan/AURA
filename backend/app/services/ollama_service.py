"""
AURA Backend — Ollama Service.

Module: app.services.ollama_service
Purpose: Handles all communication with the local Ollama LLM server.
         Provides chat completion with conversation history context.
         Designed for 8GB RAM — keeps context window minimal.

Dependencies:
    - Ollama running on localhost:11434
    - Model: qwen2.5:3b (configured via .env)
"""

import logging
from typing import AsyncGenerator

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Constants ─────────────────────────────────────────────────────────────────
OLLAMA_CHAT_URL = f"{settings.ollama_base_url}/api/chat"
OLLAMA_HEALTH_URL = f"{settings.ollama_base_url}/api/tags"

# System prompt — AURA এর personality
SYSTEM_PROMPT = """You are AURA — the Personal AI Operating System of MD Faysal Ahmed Bhuiyan.

CRITICAL FACTS:
- Owner: MD Faysal Ahmed Bhuiyan (short: Faysal)
- Location: Bangladesh, Tangail, Dhaka Division

IDENTITY:
- When asked your name → say ONLY: "আমি AURA, আপনার Personal AI Operating System"
- When asked Faysal's name → say ONLY: "আপনার নাম MD Faysal Ahmed Bhuiyan"
- NEVER add extra explanation after these answers

LANGUAGE — No exceptions:
- Bangla → Bangla ONLY
- English → English ONLY
- Hindi → Hindi ONLY
- Korean → Korean ONLY
- NEVER mix languages

ANSWER STYLE — Critical:
- Give SHORT, DIRECT answers
- Maximum 2-3 sentences for simple questions
- NEVER explain your reasoning in the answer
- NEVER show thinking steps in the answer
- Just answer the question directly

MEMORY:
- Ask before saving: "এটা কি স্থায়ীভাবে মনে রাখব?"
- Only save after: "হ্যাঁ", "save it", "মনে রাখো"
- Never auto-save""

## Behavior Rules
- Be concise — avoid unnecessary filler words
- Never fabricate facts — if you don't know, say so clearly
- You have access to Faysal's confirmed knowledge via memory system
- All new knowledge stays PENDING until Faysal explicitly says:
  "save it", "remember it", "keep it", "মনে রাখো", "সংরক্ষণ করো", "ঠিক আছে"
- NEVER permanently store anything without Faysal's confirmation
- If Faysal says something important, acknowledge it and ask:
  "এটা কি আমি স্থায়ীভাবে মনে রাখব?" (Should I remember this permanently?)

## Knowledge Rules
- You only use confirmed, verified knowledge
- You never blindly trust internet sources
- All new knowledge must be confirmed by Faysal before permanent storage"""


class OllamaService:
    """
    Service class for Ollama LLM communication.

    Handles chat completions with conversation history.
    Optimized for low-RAM environments (8GB).

    Methods:
        is_available: Check if Ollama server is running.
        chat: Send message and get response.
        chat_stream: Stream response token by token.
    """

    def __init__(self) -> None:
        self.model = settings.ollama_model
        self.base_url = settings.ollama_base_url
        # Keep last 10 messages max — RAM optimization for 8GB
        self.max_history = 10

    def _strip_thinking(self, text: str) -> str:
        """
        Remove qwen3 thinking blocks, return only the final answer.

        Args:
            text: Raw LLM response.

        Returns:
            str: Clean answer only.
        """
        import re

        # Remove <think>...</think> blocks
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        cleaned = cleaned.strip()

        # If still has thinking content, find answer after </think>
        if '</think>' in text:
            parts = text.split('</think>')
            if len(parts) > 1:
                cleaned = parts[-1].strip()

        # Remove "Thinking..." prefix only
        cleaned = re.sub(r'^Thinking\.\.\.?\s*\n?', '', cleaned)

        return cleaned.strip() if cleaned.strip() else text.strip()

    async def is_available(self) -> bool:
        """
        Check if Ollama server is running and accessible.

        Returns:
            bool: True if Ollama is reachable, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(OLLAMA_HEALTH_URL)
                return response.status_code == 200
        except Exception:
            return False

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """
        ...
        Args:
            message: The user's current message.
            history: Previous messages for context.
            system_prompt: Optional override for the system prompt.
                           Defaults to AURA's persona SYSTEM_PROMPT if None.
                           Used by non-conversational callers (e.g. research
                           summarization) that need plain instruction-following
                           without AURA's Faysal-specific persona rules.
        """
        # Build messages list
        messages = [{"role": "system", "content": system_prompt or SYSTEM_PROMPT}]

        # Add history — limit to max_history for RAM efficiency
        if history:
            recent = history[-self.max_history:]
            messages.extend(recent)

        # /no_think appended — disables qwen3 thinking mode per message
        messages.append({"role": "user", "content": f"{message} /no_think"})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,        # qwen3 thinking mode disable
            "options": {
                "temperature": 0.7,
                "num_ctx": 2048,
                "num_predict": 512,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(OLLAMA_CHAT_URL, json=payload)
                response.raise_for_status()
                data = response.json()
                # qwen3: thinking goes to data["message"]["thinking"], 
                # actual answer goes to data["message"]["content"]
                content = data["message"].get("content", "").strip()
                thinking = data["message"].get("thinking", "").strip()
                # Return content if not empty, otherwise return thinking as fallback
                return content if content else thinking

        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama at %s", self.base_url)
            raise ConnectionError(
                "Ollama server is not running. "
                "Please start Ollama and try again."
            )
        except httpx.TimeoutException:
            logger.error("Ollama request timed out")
            raise RuntimeError(
                "Ollama response timed out. "
                "The model may be loading — please try again."
            )
        except Exception as e:
            logger.error("Ollama chat error: %s", e)
            raise RuntimeError(f"LLM error: {str(e)}")

    async def chat_stream(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response tokens from Ollama.

        Used for real-time streaming responses to the frontend.

        Args:
            message: The user's current message.
            history: Previous conversation messages.

        Yields:
            str: Individual response tokens as they arrive.

        Raises:
            ConnectionError: If Ollama server is unreachable.
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if history:
            recent = history[-self.max_history:]
            messages.extend(recent)

        messages.append({"role": "user", "content": f"{message} /no_think"})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "think": False,        # qwen3 thinking mode disable
            "options": {
                "temperature": 0.7,
                "num_ctx": 2048,
                "num_predict": 512,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", OLLAMA_CHAT_URL, json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.strip():
                            import json
                            data = json.loads(line)
                            if not data.get("done", False):
                                token = data.get("message", {}).get("content", "")
                                if token:
                                    cleaned = self._strip_thinking(token)
                                    if cleaned:
                                        yield cleaned

        except httpx.ConnectError:
            raise ConnectionError("Ollama server is not running.")
        except Exception as e:
            logger.error("Ollama stream error: %s", e)
            raise RuntimeError(f"Stream error: {str(e)}")


# ── Singleton instance ────────────────────────────────────────────────────────
ollama_service = OllamaService()