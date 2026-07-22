"""
AURA Backend — Ollama Service.

Module: app.services.ollama_service
Purpose: LLM communication with aura-brain model.
         Handles chat, streaming, and system prompt injection.
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


class OllamaService:
    def __init__(self) -> None:
        self.model = settings.ollama_model
        self.base_url = settings.ollama_base_url
        self.max_history = 10

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(OLLAMA_HEALTH_URL)
                return r.status_code == 200
        except Exception:
            return False

    async def chat(
        self,
        message: str,
        history: list[dict] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if history:
            messages.extend(history[-self.max_history:])

        messages.append({"role": "user", "content": message})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.7,
                "num_ctx": 4096,
                "num_predict": 1024,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(OLLAMA_CHAT_URL, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["message"].get("content", "").strip()
                thinking = data["message"].get("thinking", "").strip()
                return content if content else thinking or "No response."
        except httpx.ConnectError:
            raise ConnectionError("Ollama is not running.")
        except httpx.TimeoutException:
            raise RuntimeError("Ollama timeout. Try again.")
        except Exception as e:
            raise RuntimeError(f"LLM error: {e}")

    async def chat_stream(
        self,
        message: str,
        history: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        messages = []
        if history:
            messages.extend(history[-self.max_history:])
        messages.append({"role": "user", "content": message})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "think": False,
            "options": {"temperature": 0.7, "num_ctx": 4096, "num_predict": 1024},
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", OLLAMA_CHAT_URL, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.strip():
                            import json
                            data = json.loads(line)
                            if not data.get("done", False):
                                token = data.get("message", {}).get("content", "")
                                if token:
                                    yield token
        except Exception as e:
            raise RuntimeError(f"Stream error: {e}")


ollama_service = OllamaService()