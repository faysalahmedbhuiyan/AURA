"""
AURA Backend — Content Fetch Service.

Module: app.services.content_fetch_service
Purpose: Fetches and extracts readable text from a URL. This is the
         "Collect" step of the Knowledge System pipeline.
"""

import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

MAX_CHARS = 4000  # Cap per-source content to keep LLM prompts small (RAM-aware)
REQUEST_TIMEOUT = 8.0
USER_AGENT = "Mozilla/5.0 (compatible; AURA-Research-Bot/1.0)"


class ContentFetchService:
    """
    Fetches a URL and extracts readable body text.

    Methods:
        fetch: Download and extract text content from a single URL.
    """

    async def fetch(self, url: str) -> str | None:
        """
        Fetch a URL and return extracted plain text.

        Args:
            url: The URL to fetch.

        Returns:
            str | None: Extracted text (truncated to MAX_CHARS),
                         or None if the fetch/parse failed.
        """
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Strip non-content elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            text = " ".join(soup.get_text(separator=" ").split())

            if not text:
                return None

            return text[:MAX_CHARS]

        except Exception as e:
            logger.warning("Failed to fetch content from %s: %s", url, e)
            return None


# ── Singleton instance ────────────────────────────────────────────────────────
content_fetch_service = ContentFetchService()