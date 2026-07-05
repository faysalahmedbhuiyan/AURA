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
SYSTEM_PROMPT = """You are AURA, a personal AI Operating System assistant.
You are helpful, precise, and honest.
You support Bangla, English, Hindi, and Korean languages.
Always respond in the same language the user writes in.
Never make up facts. If you don't know something, say so clearly.
Keep responses concise and useful."""


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
    ) -> str:
        """
        Send a message to Ollama and get a complete response.

        Includes conversation history for context.
        Limits history to max_history messages for RAM efficiency.

        Args:
            message: The user's current message.
            history: List of previous messages as
                     [{"role": "user"|"assistant", "content": "..."}]

        Returns:
            str: The assistant's response text.

        Raises:
            ConnectionError: If Ollama server is unreachable.
            RuntimeError: If Ollama returns an error response.
        """
        # Build messages list
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add history — limit to max_history for RAM efficiency
        if history:
            recent = history[-self.max_history:]
            messages.extend(recent)

        # Add current user message
        messages.append({"role": "user", "content": message})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_ctx": 2048,      # Context window — kept small for 8GB RAM
                "num_predict": 512,   # Max response tokens
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(OLLAMA_CHAT_URL, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"]

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

        messages.append({"role": "user", "content": message})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
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
                                    yield token

        except httpx.ConnectError:
            raise ConnectionError("Ollama server is not running.")
        except Exception as e:
            logger.error("Ollama stream error: %s", e)
            raise RuntimeError(f"Stream error: {str(e)}")


# ── Singleton instance ────────────────────────────────────────────────────────
ollama_service = OllamaService()