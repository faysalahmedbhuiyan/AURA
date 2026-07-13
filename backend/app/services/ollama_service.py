"""
AURA Backend — Ollama Service.

Module: app.services.ollama_service
Purpose: Handles all communication with the local Ollama LLM server.
         Uses aura-brain custom model (qwen3:8b base, thinking disabled).
         Optimized for 8GB RAM with context window management.
"""

import logging
import re
from typing import AsyncGenerator

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

OLLAMA_CHAT_URL = f"{settings.ollama_base_url}/api/chat"
OLLAMA_HEALTH_URL = f"{settings.ollama_base_url}/api/tags"

SYSTEM_PROMPT = ""  # Baked into aura-brain Modelfile


class OllamaService:
    """
    Service class for Ollama LLM communication.

    Uses aura-brain custom model with thinking mode disabled.
    Optimized for 8GB RAM — context window limited to 8192 tokens.

    Methods:
        is_available: Check if Ollama server is running.
        chat: Send message and get complete response.
        chat_stream: Stream response token by token.
    """

    def __init__(self) -> None:
        self.model = settings.ollama_model
        self.base_url = settings.ollama_base_url
        self.max_history = 20  # Keep last 20 messages for context

    def _strip_thinking(self, text: str) -> str:
        """
        Strip any leaked thinking content from qwen3 response.

        Args:
            text: Raw LLM response.

        Returns:
            str: Clean response without thinking blocks.
        """
        # Remove <think>...</think> blocks
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

        # Remove "Thinking..." prefix
        cleaned = re.sub(r'^Thinking\.\.\.?\s*\n?', '', cleaned, flags=re.MULTILINE)

        # Remove lines that look like internal reasoning
        lines = cleaned.split('\n')
        filtered = []
        skip_patterns = [
            r'^(Okay|Alright|Let me|Wait|Hmm|So,|First,|Now,)',
            r'^(The user|I need to|I should|I must|I will)',
        ]
        combined = '|'.join(skip_patterns)

        in_answer = False
        for line in lines:
            if re.match(combined, line.strip()):
                if not in_answer:
                    continue
            else:
                in_answer = True
            filtered.append(line)

        result = '\n'.join(filtered).strip()
        return result if result else text.strip()

    async def is_available(self) -> bool:
        """
        Check if Ollama server is running and accessible.

        Returns:
            bool: True if Ollama is reachable.
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
        Send a message to Ollama and get a complete response.

        Args:
            message: The user's current message.
            history: Previous messages as [{"role": ..., "content": ...}]
            system_prompt: Optional override system prompt.

        Returns:
            str: The assistant's response text (thinking stripped).

        Raises:
            ConnectionError: If Ollama server is unreachable.
            RuntimeError: If Ollama returns an error.
        """
        messages = []

        # Add system prompt override if provided
        active_system = system_prompt or SYSTEM_PROMPT
        if active_system:
            messages.append({"role": "system", "content": active_system})

        # Add history — limit for RAM efficiency
        if history:
            recent = history[-self.max_history:]
            messages.extend(recent)

        # Add user message with /no_think suffix for qwen3
        messages.append({"role": "user", "content": f"{message} /no_think"})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.7,
                "num_ctx": 8192,
                "num_predict": 2048,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(OLLAMA_CHAT_URL, json=payload)
                response.raise_for_status()
                data = response.json()

                # qwen3: actual answer in content, thinking in thinking field
                content = data["message"].get("content", "").strip()
                thinking = data["message"].get("thinking", "").strip()

                # Use content if not empty, else fall back to stripped thinking
                if content:
                    return self._strip_thinking(content)
                elif thinking:
                    return self._strip_thinking(thinking)
                else:
                    return "আমি এই মুহূর্তে উত্তর দিতে পারছি না।"

        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama at %s", self.base_url)
            raise ConnectionError(
                "Ollama চালু নেই। Ollama start করুন এবং আবার চেষ্টা করুন।"
            )
        except httpx.TimeoutException:
            logger.error("Ollama request timed out")
            raise RuntimeError(
                "Ollama response timeout। Model load হচ্ছে — একটু পরে আবার চেষ্টা করুন।"
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

        Args:
            message: The user's current message.
            history: Previous conversation messages.

        Yields:
            str: Individual response tokens.
        """
        messages = []

        if SYSTEM_PROMPT:
            messages.append({"role": "system", "content": SYSTEM_PROMPT})

        if history:
            recent = history[-self.max_history:]
            messages.extend(recent)

        messages.append({"role": "user", "content": f"{message} /no_think"})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "think": False,
            "options": {
                "temperature": 0.7,
                "num_ctx": 8192,
                "num_predict": 2048,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
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
            raise ConnectionError("Ollama চালু নেই।")
        except Exception as e:
            logger.error("Ollama stream error: %s", e)
            raise RuntimeError(f"Stream error: {str(e)}")


# ── Singleton instance ────────────────────────────────────────────────────────
ollama_service = OllamaService()