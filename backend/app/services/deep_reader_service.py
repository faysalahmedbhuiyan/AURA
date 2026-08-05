"""
AURA Backend — Deep Reader Service (Tier 6, A1).

Module: app.services.deep_reader_service
Purpose: Read URLs and YouTube videos, extract their real content, and
         feed it through the EXISTING Tier 2 Intelligence pipeline
         (classify -> deduplicate -> create/evolve -> relate) — the
         same pipeline that already handles PDF/DOCX documents. This
         reuses proven, working infrastructure instead of building a
         separate "understanding" system from scratch.

"Critical thinking" honesty note: this does NOT give AURA human-level
reasoning (qwen2.5:3b can't do that). What it DOES do: connect new
content to existing knowledge via the same relationship_builder logic
already in Tier 2, so future chats can draw on it.
"""

import logging

logger = logging.getLogger(__name__)


class DeepReaderService:
    """Extracts real content from URLs/YouTube for the knowledge pipeline."""

    async def read_url(self, url: str) -> dict:
        """Fetch a webpage and extract its main readable text (no ads/nav/boilerplate)."""
        try:
            import trafilatura
        except ImportError:
            return {
                "success": False,
                "error": "trafilatura not installed. Run: pip install trafilatura",
            }

        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return {"success": False, "error": f"Could not fetch URL: {url}"}

            text = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
            title = trafilatura.extract_metadata(downloaded)
            title_str = title.title if title and title.title else url

            if not text or len(text.strip()) < 50:
                return {"success": False, "error": "Page had no meaningful readable content."}

            return {"success": True, "title": title_str, "content": text, "source": url}

        except Exception as e:
            logger.exception("URL read failed")
            return {"success": False, "error": f"Failed to read URL: {e}"}

    async def read_youtube(self, url: str) -> dict:
        """Fetch a YouTube video's transcript (captions), not the video itself."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            return {
                "success": False,
                "error": "youtube-transcript-api not installed. Run: pip install youtube-transcript-api",
            }

        video_id = self._extract_youtube_id(url)
        if not video_id:
            return {"success": False, "error": f"Could not extract a video ID from: {url}"}

        try:
            ytt_api = YouTubeTranscriptApi()
            fetched_transcript = ytt_api.fetch(video_id)
            text = " ".join(snippet.text for snippet in fetched_transcript)
            
            if not text.strip():
                return {"success": False, "error": "This video has no available transcript/captions."}

            return {
                "success": True,
                "title": f"YouTube video {video_id}",
                "content": text,
                "source": url,
            }

        except Exception as e:
            logger.exception("YouTube transcript fetch failed")
            return {
                "success": False,
                "error": (
                    f"Could not get transcript (video may have no captions, or be "
                    f"private/restricted): {e}"
                ),
            }

    def _extract_youtube_id(self, url: str) -> str | None:
        import re

        patterns = [
            r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        ]
        for p in patterns:
            m = re.search(p, url)
            if m:
                return m.group(1)
        return None


deep_reader_service = DeepReaderService()
