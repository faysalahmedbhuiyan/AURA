"""
AURA Backend — Semantic Relationship Builder.

Module: app.intelligence.relationship_builder
Purpose: Builds semantic connections between knowledge items.
         Creates a knowledge graph where everything is interconnected.

Relationship types:
    is_part_of   : A is a component of B
    requires     : A needs B to work
    leads_to     : A results in B
    contradicts  : A conflicts with B
    supports     : A reinforces B
    examples     : A is an example of B
    defines      : A explains what B means
    precedes     : A must happen before B
    alternatives : A and B solve the same problem differently

How it works:
    1. New knowledge item arrives
    2. Search existing items via ChromaDB (semantic similarity)
    3. For each similar item, detect relationship type
    4. Store relationship with strength score
    5. Build connected knowledge graph
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.models.knowledge_item import KnowledgeRelationship
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

RELATIONSHIP_TYPES = {
    "is_part_of", "requires", "leads_to", "contradicts",
    "supports", "examples", "defines", "precedes", "alternatives",
}


class RelationshipBuilder:
    """
    Builds semantic relationships between knowledge items.

    Uses ChromaDB for finding similar items and
    LLM for detecting relationship types.

    Methods:
        find_related: Find semantically related existing items.
        detect_relationship: Detect relationship type between two items.
        build_relationships: Create relationships for a new knowledge item.
        get_relationships: Get all relationships for an item.
    """

    async def find_related(
        self,
        content: str,
        category: str | None = None,
        n_results: int = 5,
        min_similarity: float = 0.6,
    ) -> list[dict]:
        """
        Find semantically related knowledge items.

        Args:
            content: Content to find relations for.
            category: Filter by category.
            n_results: Max results.
            min_similarity: Minimum similarity threshold.

        Returns:
            list[dict]: Related items with similarity scores.
        """
        try:
            from app.services.memory_service import memory_service
            results = await memory_service.search_knowledge(
                query=content,
                n_results=n_results,
            )
            return [r for r in results if r.get("relevance", 0) >= min_similarity]
        except Exception as e:
            logger.warning("Find related failed: %s", e)
            return []

    async def detect_relationship(
        self,
        source_title: str,
        source_content: str,
        target_title: str,
        target_content: str,
    ) -> tuple[str, float]:
        """
        Detect relationship type between two knowledge items.

        Args:
            source_title: Source item title.
            source_content: Source item content.
            target_title: Target item title.
            target_content: Target item content.

        Returns:
            tuple: (relationship_type, strength)
        """
        try:
            from app.services.ollama_service import ollama_service
            import json

            prompt = (
                f"Determine the relationship between these two knowledge items.\n\n"
                f"Item A: {source_title}\n{source_content[:300]}\n\n"
                f"Item B: {target_title}\n{target_content[:300]}\n\n"
                f"Respond with ONLY valid JSON:\n"
                f'{{"relationship": "is_part_of|requires|leads_to|contradicts|supports|examples|defines|precedes|alternatives", '
                f'"strength": 0.7, "reason": "brief explanation"}}'
            )

            response = await ollama_service.chat(
                message=prompt,
                history=[],
                system_prompt="You are a knowledge graph builder. Respond with valid JSON only.",
            )

            clean = response.strip()
            start = clean.find('{')
            end = clean.rfind('}')
            if start >= 0 and end > start:
                parsed = json.loads(clean[start:end+1])
                rel_type = parsed.get("relationship", "supports")
                strength = float(parsed.get("strength", 0.5))
                if rel_type in RELATIONSHIP_TYPES:
                    return rel_type, min(max(strength, 0.1), 1.0)

        except Exception as e:
            logger.warning("Relationship detection failed: %s", e)

        return "supports", 0.5

    async def build_relationships(
        self,
        db: AsyncSession,
        new_item_id: str,
        new_item_title: str,
        new_item_content: str,
        new_item_category: str | None = None,
    ) -> list[KnowledgeRelationship]:
        """
        Build relationships for a newly added knowledge item.

        Finds related existing items and creates connections.

        Args:
            db: Database session.
            new_item_id: New item's ID.
            new_item_title: New item's title.
            new_item_content: New item's content.
            new_item_category: New item's category.

        Returns:
            list[KnowledgeRelationship]: Created relationships.
        """
        related = await self.find_related(
            content=new_item_content,
            category=new_item_category,
            n_results=3,
            min_similarity=0.65,
        )

        created = []
        for item in related:
            target_id = item.get("id") or item.get("entry_id")
            if not target_id or target_id == new_item_id:
                continue

            target_content = item.get("content", "")
            target_title = item.get("title", "")

            rel_type, strength = await self.detect_relationship(
                new_item_title, new_item_content,
                target_title, target_content,
            )

            relationship = KnowledgeRelationship(
                source_id=new_item_id,
                target_id=target_id,
                relationship_type=rel_type,
                strength=strength,
                description=f"Auto-detected: {new_item_title} {rel_type} {target_title}",
            )
            db.add(relationship)
            created.append(relationship)

        if created:
            await db.flush()
            logger.info(
                "Built %d relationships for item %s",
                len(created), new_item_id[:8],
            )

        return created

    async def get_relationships(
        self,
        db: AsyncSession,
        item_id: str,
    ) -> list[dict]:
        """
        Get all relationships for a knowledge item.

        Args:
            db: Database session.
            item_id: Knowledge item ID.

        Returns:
            list[dict]: All relationships (incoming and outgoing).
        """
        # Outgoing
        out_result = await db.execute(
            select(KnowledgeRelationship).where(
                KnowledgeRelationship.source_id == item_id
            )
        )
        outgoing = out_result.scalars().all()

        # Incoming
        in_result = await db.execute(
            select(KnowledgeRelationship).where(
                KnowledgeRelationship.target_id == item_id
            )
        )
        incoming = in_result.scalars().all()

        return {
            "outgoing": [r.to_dict() for r in outgoing],
            "incoming": [r.to_dict() for r in incoming],
            "total": len(outgoing) + len(incoming),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
relationship_builder = RelationshipBuilder()