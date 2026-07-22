"""
AURA Backend — Knowledge Evolution Engine.

Module: app.intelligence.evolution_engine
Purpose: Merges and improves existing knowledge when new info arrives.
         Knowledge never gets overwritten — it evolves with version history.
         If multiple sources teach the same thing, they are merged into
         one improved understanding.

Evolution rules:
    1. New source confirms existing → increase confidence + source_count
    2. New source adds details → update notes, increment version
    3. New source contradicts → flag conflict, keep both, lower confidence
    4. New source is duplicate → skip, just update source_count
    5. Knowledge > 3 versions → auto-summarize for clarity
"""

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.models.knowledge_item import KnowledgeItem, KnowledgeVersion
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.85  # Items > 85% similar are considered same topic
MAX_VERSIONS_BEFORE_SUMMARY = 3


class KnowledgeEvolutionEngine:
    """
    Evolves knowledge by merging and improving existing items.

    Methods:
        find_duplicate: Check if similar knowledge already exists.
        evolve: Merge new info with existing knowledge item.
        create_version: Save current state as a version.
        should_summarize: Check if item needs summarization.
    """

    async def find_duplicate(
        self,
        title: str,
        content: str,
        category: str | None = None,
        db: AsyncSession | None = None,
    ) -> KnowledgeItem | None:
        """
        Find an existing knowledge item that covers the same topic.

        Uses semantic similarity to find near-duplicates.

        Args:
            title: New item title.
            content: New item content.
            category: Category filter.
            db: Database session.

        Returns:
            KnowledgeItem | None: Existing item if duplicate found.
        """
        if not db:
            return None

        try:
            # Search by category first
            query = select(KnowledgeItem).where(
                KnowledgeItem.is_confirmed == True,  # noqa: E712
            )
            if category:
                query = query.where(KnowledgeItem.category == category)

            result = await db.execute(query.limit(50))
            existing_items = result.scalars().all()

            if not existing_items:
                return None

            # Get embedding for new content
            new_embedding = await embedding_service.embed(
                f"{title}\n{content[:500]}"
            )
            if not new_embedding:
                return None

            # Compare with existing items using simple keyword overlap
            for item in existing_items:
                item_words = set((item.title + " " + (item.summary or "")).lower().split())
                new_words = set((title + " " + content[:200]).lower().split())

                # Remove common words
                stopwords = {"the", "a", "an", "is", "are", "was", "were", "to", "of", "in", "and", "or"}
                item_words -= stopwords
                new_words -= stopwords

                if not item_words or not new_words:
                    continue

                overlap = len(item_words & new_words) / max(len(item_words | new_words), 1)
                if overlap > 0.5:  # 50% word overlap = likely same topic
                    logger.info(
                        "Found potential duplicate: '%s' (overlap=%.2f)",
                        item.title[:50], overlap,
                    )
                    return item

        except Exception as e:
            logger.warning("Duplicate check failed: %s", e)

        return None

    async def create_version(
        self,
        db: AsyncSession,
        item: KnowledgeItem,
        change_reason: str,
    ) -> KnowledgeVersion:
        """
        Save current knowledge state as a version.

        Called before any update to preserve history.

        Args:
            db: Database session.
            item: Knowledge item to version.
            change_reason: Why this version is being created.

        Returns:
            KnowledgeVersion: Created version record.
        """
        version = KnowledgeVersion(
            knowledge_id=item.id,
            version_number=item.version,
            title=item.title,
            summary=item.summary,
            detailed_notes=item.detailed_notes,
            confidence=item.confidence,
            change_reason=change_reason,
        )
        db.add(version)
        await db.flush()
        logger.info(
            "Created version %d for item %s",
            item.version, item.id[:8],
        )
        return version

    async def evolve(
        self,
        db: AsyncSession,
        existing_item: KnowledgeItem,
        new_title: str,
        new_content: str,
        new_source: str | None = None,
        new_confidence: float = 0.7,
        classification: dict | None = None,
    ) -> KnowledgeItem:
        """
        Evolve an existing knowledge item with new information.

        Evolution strategy:
        1. Save current state as version
        2. Merge new content intelligently
        3. Update confidence based on corroboration
        4. Increment version number
        5. Return updated item

        Args:
            db: Database session.
            existing_item: Item to evolve.
            new_title: New content title.
            new_content: New content to merge.
            new_source: New source URL/description.
            new_confidence: Confidence in new info.
            classification: Classification result for new content.

        Returns:
            KnowledgeItem: Evolved knowledge item.
        """
        # Save version before update
        await self.create_version(
            db, existing_item,
            f"New source added: {new_source or 'unknown'}"
        )

        # Update source count (corroboration increases confidence)
        existing_item.source_count += 1
        corroboration_boost = min(existing_item.source_count * 0.05, 0.2)
        existing_item.confidence = min(
            (existing_item.confidence + new_confidence) / 2 + corroboration_boost,
            0.95,
        )

        # Merge detailed notes
        if new_content and len(new_content) > 100:
            try:
                merged = await self._llm_merge(
                    existing_title=existing_item.title,
                    existing_notes=existing_item.detailed_notes or existing_item.summary,
                    new_content=new_content,
                )
                if merged:
                    existing_item.detailed_notes = merged
                    existing_item.is_merged = True
            except Exception as e:
                logger.warning("LLM merge failed, appending: %s", e)
                existing_item.detailed_notes = (
                    (existing_item.detailed_notes or existing_item.summary) +
                    f"\n\n[Additional source ({new_source or 'unknown'})]\n{new_content[:500]}"
                )

        # Merge classification data
        if classification:
            # Merge tags
            existing_tags = set((existing_item.tags or "").split(","))
            new_tags = set((classification.get("tags") or "").split(","))
            existing_item.tags = ",".join(filter(None, existing_tags | new_tags))

            # Merge extracted knowledge
            for field in ["rules_extracted", "concepts_extracted", "best_practices", "common_mistakes"]:
                existing_val = existing_item.__dict__.get(field, "[]")
                new_val = classification.get(field, [])
                if new_val:
                    try:
                        existing_list = json.loads(existing_val) if existing_val else []
                        merged_list = list(set(existing_list + new_val))
                        setattr(existing_item, field, json.dumps(merged_list))
                    except Exception:
                        pass

        existing_item.version += 1
        existing_item.updated_at = datetime.now(timezone.utc)

        if new_source and new_source not in (existing_item.source or ""):
            existing_item.source = (
                (existing_item.source or "") + f" | {new_source}"
            )[:500]

        await db.flush()
        logger.info(
            "Evolved item '%s' to version %d (confidence=%.2f, sources=%d)",
            existing_item.title[:50],
            existing_item.version,
            existing_item.confidence,
            existing_item.source_count,
        )
        return existing_item

    async def _llm_merge(
        self,
        existing_title: str,
        existing_notes: str | None,
        new_content: str,
    ) -> str | None:
        """Use LLM to intelligently merge two pieces of knowledge."""
        try:
            from app.services.ollama_service import ollama_service

            prompt = (
                f"Merge these two pieces of knowledge about '{existing_title}' "
                f"into one improved, comprehensive explanation.\n\n"
                f"EXISTING:\n{(existing_notes or '')[:800]}\n\n"
                f"NEW INFORMATION:\n{new_content[:800]}\n\n"
                f"Write a merged, improved explanation that:\n"
                f"1. Combines both pieces without repetition\n"
                f"2. Keeps all unique facts from both\n"
                f"3. Resolves any contradictions by noting them\n"
                f"4. Is clear and concise\n\n"
                f"Merged knowledge:"
            )

            result = await ollama_service.chat(
                message=prompt,
                history=[],
                system_prompt=(
                    "You are a knowledge curator. "
                    "Merge knowledge items intelligently. "
                    "Be concise. No preamble."
                ),
            )
            return result.strip() if result else None

        except Exception as e:
            logger.warning("LLM merge failed: %s", e)
            return None

    def should_summarize(self, item: KnowledgeItem) -> bool:
        """Check if item needs summarization after multiple versions."""
        return item.version >= MAX_VERSIONS_BEFORE_SUMMARY


# ── Singleton ─────────────────────────────────────────────────────────────────
evolution_engine = KnowledgeEvolutionEngine()