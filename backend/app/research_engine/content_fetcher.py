"""
AURA Backend — Content Fetcher.

Module: app.research_engine.content_fetcher
Purpose: Fetches and extracts clean text from URLs.
         Uses httpx (async) + BeautifulSoup for parsing.
         RAM-aware: Truncates content to 5000 chars per page.

Features:
    - Async fetching (fast)
    - Smart text extraction (removes nav/footer/scripts)
    - Timeout protection (no hanging)
    - Error recovery (returns None on failure)
"""

import asyncio
import logging
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 5000   # Chars per page — RAM protection
FETCH_TIMEOUT = 10.0        # Seconds timeout per URL
MAX_CONCURRENT_FETCHES = 3  # Parallel fetch limit

# Tags to remove before text extraction
REMOVE_TAGS = [
    "script", "style", "nav", "footer", "header",
    "aside", "advertisement", "ads", "cookie",
    "popup", "modal", "sidebar",
]


@dataclass
class FetchedContent:
    """Content fetched from a URL."""
    url: str
    title: str
    content: str
    word_count: int
    success: bool
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "word_count": self.word_count,
            "success": self.success,
        }


class ContentFetcher:
    """
    Async content fetcher and text extractor.

    Fetches URLs concurrently with rate limiting.
    Extracts clean readable text using BeautifulSoup.

    Methods:
        fetch: Fetch single URL.
        fetch_batch: Fetch multiple URLs concurrently.
    """

    def _extract_text(self, html: str, url: str) -> tuple[str, str]:
        """
        Extract clean text and title from HTML.

        Args:
            html: Raw HTML content.
            url: Source URL (for logging).

        Returns:
            tuple: (title, clean_text)
        """
        try:
            soup = BeautifulSoup(html, "lxml")

            # Remove noise tags
            for tag in REMOVE_TAGS:
                for element in soup.find_all(tag):
                    element.decompose()

            # Extract title
            title = ""
            if soup.title:
                title = soup.title.get_text(strip=True)[:200]

            # Try main content areas first
            content = ""
            for selector in ["main", "article", ".content", "#content", "body"]:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(separator=" ", strip=True)
                    if len(content) > 100:
                        break

            if not content:
                content = soup.get_text(separator=" ", strip=True)

            # Clean whitespace
            import re
            content = re.sub(r'\s+', ' ', content).strip()

            # Truncate to RAM-safe size
            if len(content) > MAX_CONTENT_LENGTH:
                content = content[:MAX_CONTENT_LENGTH] + "..."

            return title, content

        except Exception as e:
            logger.warning("Text extraction failed for %s: %s", url, e)
            return "", ""

    async def fetch(self, url: str) -> FetchedContent:
        """
        Fetch and extract content from a single URL.

        Args:
            url: URL to fetch.

        Returns:
            FetchedContent: Extracted content or error.
        """
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
            }

            async with httpx.AsyncClient(
                timeout=FETCH_TIMEOUT,
                follow_redirects=True,
                verify=False,  # Skip SSL errors for speed
            ) as client:
                response = await client.get(url, headers=headers)

                if response.status_code != 200:
                    return FetchedContent(
                        url=url, title="", content="",
                        word_count=0, success=False,
                        error=f"HTTP {response.status_code}",
                    )

                html = response.text
                title, content = self._extract_text(html, url)

                if not content or len(content) < 50:
                    return FetchedContent(
                        url=url, title=title, content="",
                        word_count=0, success=False,
                        error="No extractable content",
                    )

                word_count = len(content.split())
                logger.debug("Fetched %s: %d words", url[:60], word_count)

                return FetchedContent(
                    url=url,
                    title=title,
                    content=content,
                    word_count=word_count,
                    success=True,
                )

        except httpx.TimeoutException:
            return FetchedContent(
                url=url, title="", content="",
                word_count=0, success=False,
                error="Timeout",
            )
        except Exception as e:
            logger.warning("Fetch failed for %s: %s", url[:60], e)
            return FetchedContent(
                url=url, title="", content="",
                word_count=0, success=False,
                error=str(e)[:100],
            )

    async def fetch_batch(
        self,
        urls: list[str],
        max_concurrent: int = MAX_CONCURRENT_FETCHES,
    ) -> list[FetchedContent]:
        """
        Fetch multiple URLs concurrently with rate limiting.

        Args:
            urls: List of URLs to fetch.
            max_concurrent: Max parallel fetches.

        Returns:
            list[FetchedContent]: Results for each URL.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_limit(url: str) -> FetchedContent:
            async with semaphore:
                return await self.fetch(url)

        tasks = [fetch_with_limit(url) for url in urls[:10]]  # Max 10 URLs
        results = await asyncio.gather(*tasks, return_exceptions=True)

        fetched = []
        for result in results:
            if isinstance(result, FetchedContent):
                fetched.append(result)

        successful = sum(1 for f in fetched if f.success)
        logger.info(
            "Batch fetch: %d/%d successful", successful, len(urls)
        )
        return fetched


# ── Singleton ─────────────────────────────────────────────────────────────────
content_fetcher = ContentFetcher()