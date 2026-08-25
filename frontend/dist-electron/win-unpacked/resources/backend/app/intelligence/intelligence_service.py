"""
AURA Backend — Intelligence Service.

Module: app.intelligence.intelligence_service
Purpose: Main orchestrator for Tier 2 Intelligence Layer.
         Coordinates classification, relationship building, and evolution.

Pipeline for every new piece of knowledge:
    1. Classify      → Detect type, category, tags, importance
    2. Check Dup     → Find if similar knowledge already exists
    3. If duplicate  → Evolve existing item (merge + version)
    4. If new        → Create new KnowledgeItem
    5. Index         → Add to ChromaDB for semantic search
    6. Relate        → Build relationships with existing items
    7. Confirm       → Return candidate (user must confirm)

This service is called from:
    - Chat route (when user shares knowledge)
    - Research Engine (when web research is confirmed)
    - File ingestion (future: PDF/DOCX processing)
    - Direct API (developer use)
"""

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.classifier import knowledge_classifier
from app.intelligence.evolution_engine import evolution_engine
from app.intelligence.models.knowledge_item import KnowledgeItem, KnowledgeRelationship
from app.intelligence.relationship_builder import relationship_builder
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class IntelligenceService:
    """
    Intelligence Layer main orchestrator.

    Transforms raw content into structured, interconnected knowledge.
    Handles the full pipeline from input to indexed, related knowledge.

    Methods:
        process: Full intelligence pipeline for new content.
        confirm_item: Confirm a pending item for permanent storage.
        get_knowledge_graph: Get interconnected knowledge items.
        search: Semantic search across intelligence layer.
        get_stats: Intelligence layer statistics.
    """

    async def process(
        self,
        db: AsyncSession,
        title: str,
        content: str,
        source: str | None = None,
        source_type: str = "manual",
        language: str = "en",
        auto_confirm: bool = False,
    ) -> dict:
        """
        Full intelligence pipeline for new content.

        Args:
            db: Database session.
            title: Content title.
            content: Full content text.
            source: Source URL or description.
            source_type: manual/web/file/chat/research
            language: Content language.
            auto_confirm: If True, skip confirmation step.

        Returns:
            dict: Processing result with item details and action taken.
        """
        logger.info("Intelligence pipeline: '%s'", title[:60])

        # ── Step 1: Classify ──────────────────────────────────────────────────
        classification = await knowledge_classifier.classify(
            title=title,
            content=content,
            source=source or source_type,
            use_llm=len(content) > 150,
        )

        # ── Step 2: Check for duplicates ──────────────────────────────────────
        existing = await evolution_engine.find_duplicate(
            title=title,
            content=content,
            category=classification.get("category"),
            db=db,
        )

        # ── Step 3a: Evolve existing item ─────────────────────────────────────
        if existing:
            evolved = await evolution_engine.evolve(
                db=db,
                existing_item=existing,
                new_title=title,
                new_content=content,
                new_source=source,
                new_confidence=classification.get("confidence", 0.7),
                classification=classification,
            )
            await db.commit()

            logger.info(
                "Knowledge evolved: '%s' (v%d)",
                evolved.title[:50], evolved.version,
            )
            return {
                "action": "evolved",
                "item": evolved.to_dict(),
                "classification": classification,
                "message": f"Updated existing knowledge '{evolved.title}' to version {evolved.version}",
            }

        # ── Step 3b: Create new knowledge item ────────────────────────────────
        new_item = KnowledgeItem(
            knowledge_type=classification.get("knowledge_type", "Knowledge"),
            category=classification.get("category", "General"),
            subcategory=classification.get("subcategory"),
            title=title,
            summary=classification.get("summary", content[:300]),
            detailed_notes=content,
            rules_extracted=json.dumps(classification.get("rules_extracted", [])),
            concepts_extracted=json.dumps(classification.get("concepts_extracted", [])),
            common_mistakes=json.dumps(classification.get("common_mistakes", [])),
            best_practices=json.dumps(classification.get("best_practices", [])),
            tags=classification.get("tags", ""),
            source=source,
            source_type=source_type,
            language=language,
            confidence=classification.get("confidence", 0.7),
            importance=classification.get("importance", 0.5),
            is_confirmed=auto_confirm,
        )
        db.add(new_item)
        await db.flush()
        await db.refresh(new_item)

        # ── Step 4: Index in ChromaDB (if confirmed) ──────────────────────────
        if auto_confirm:
            await self._index_item(new_item)
            new_item.is_indexed = True
            await db.flush()

        # ── Step 5: Build relationships ───────────────────────────────────────
        try:
            await relationship_builder.build_relationships(
                db=db,
                new_item_id=new_item.id,
                new_item_title=title,
                new_item_content=content,
                new_item_category=classification.get("category"),
            )
        except Exception as e:
            logger.warning("Relationship building failed: %s", e)

        await db.commit()

        logger.info(
            "New knowledge created: '%s' (type=%s, confirmed=%s)",
            title[:50],
            classification.get("knowledge_type"),
            auto_confirm,
        )

        return {
            "action": "created",
            "item": new_item.to_dict(),
            "classification": classification,
            "confirmed": auto_confirm,
            "message": (
                f"New {classification.get('knowledge_type')} knowledge created."
                + (" Confirmed and indexed." if auto_confirm else
                   " Pending confirmation.")
            ),
        }

    async def confirm_item(
        self,
        db: AsyncSession,
        item_id: str,
    ) -> dict:
        """
        Confirm a pending knowledge item for permanent storage.

        Args:
            db: Database session.
            item_id: KnowledgeItem ID to confirm.

        Returns:
            dict: Confirmation result.
        """
        result = await db.execute(
            select(KnowledgeItem).where(KnowledgeItem.id == item_id)
        )
        item = result.scalar_one_or_none()

        if not item:
            return {"success": False, "error": f"Item {item_id} not found"}

        item.is_confirmed = True

        # Index in ChromaDB
        indexed = await self._index_item(item)
        item.is_indexed = indexed

        await db.commit()

        logger.info("Confirmed knowledge item: %s", item_id[:8])
        return {
            "success": True,
            "item": item.to_dict(),
            "indexed": indexed,
        }

    async def _index_item(self, item: KnowledgeItem) -> bool:
        """Index a knowledge item in ChromaDB."""
        try:
            text = f"{item.title}\n\n{item.summary}"
            if item.detailed_notes:
                text += f"\n\n{item.detailed_notes[:1000]}"

            embedding = await embedding_service.embed(text[:2000])
            if not embedding:
                return False

            from app.database.chroma_client import get_chroma_client
            client = get_chroma_client()

            collection = client.get_or_create_collection(
                name="aura_intelligence",
                metadata={
                    "description": "AURA Intelligence Layer",
                    "hnsw:space": "cosine",
                },
            )
            collection.upsert(
                ids=[item.id],
                embeddings=[embedding],
                documents=[item.summary[:500]],
                metadatas=[{
                    "knowledge_type": item.knowledge_type,
                    "category": item.category or "",
                    "title": item.title[:200],
                    "importance": item.importance,
                    "confidence": item.confidence,
                    "language": item.language,
                    "tags": item.tags or "",
                }],
            )
            return True

        except Exception as e:
            logger.exception("ChromaDB index failed for %s: %s", item.id[:8], e)
            return False

    async def search(self, query, knowledge_type=None, category=None, n_results=5):
        try:
            from app.database.chroma_client import get_chroma_client

            embedding = await embedding_service.embed(query)
            if not embedding:
                return []

            client = get_chroma_client()

            try:
                collection = client.get_collection("aura_intelligence")
            except Exception:
                return []

            if collection.count() == 0:
                return []

            where = {}
            if knowledge_type:
                where["knowledge_type"] = {"$eq": knowledge_type}
            if category:
                where["category"] = {"$eq": category}

            results = collection.query(
                query_embeddings=[embedding],
                n_results=min(n_results, collection.count()),
                where=where if where else None,
                include=["documents", "metadatas", "distances"],
            )

            items = []
            if results["documents"] and results["documents"][0]:
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    # L2 distance — lower is better, 0 = perfect match
                    # Convert to 0-1 score: use exponential decay
                    import math
                    relevance = round(math.exp(-float(dist) / 100), 3)
                    if relevance > 0.1:
                        items.append({
                            "content": doc,
                            "title": meta.get("title", ""),
                            "knowledge_type": meta.get("knowledge_type", ""),
                            "category": meta.get("category", ""),
                            "importance": meta.get("importance", 0.5),
                            "confidence": meta.get("confidence", 0.7),
                            "tags": meta.get("tags", ""),
                            "relevance": relevance,
                        })

            return sorted(items, key=lambda x: x["relevance"], reverse=True)

        except Exception as e:
            logger.warning("Intelligence search failed: %s", e)
            return []

    async def get_knowledge_graph(
        self,
        db: AsyncSession,
        item_id: str,
        depth: int = 2,
    ) -> dict:
        """
        Get interconnected knowledge items as a graph.

        Args:
            db: Database session.
            item_id: Starting item ID.
            depth: How many levels of relationships to traverse.

        Returns:
            dict: Graph with nodes and edges.
        """
        nodes = {}
        edges = []
        visited = set()

        async def traverse(current_id: str, current_depth: int):
            if current_id in visited or current_depth > depth:
                return
            visited.add(current_id)

            result = await db.execute(
                select(KnowledgeItem).where(KnowledgeItem.id == current_id)
            )
            item = result.scalar_one_or_none()
            if not item:
                return

            nodes[current_id] = {
                "id": item.id,
                "title": item.title,
                "knowledge_type": item.knowledge_type,
                "category": item.category,
                "importance": item.importance,
            }

            relationships = await relationship_builder.get_relationships(db, current_id)
            for rel in relationships.get("outgoing", []):
                edges.append(rel)
                if current_depth < depth:
                    await traverse(rel["target_id"], current_depth + 1)

        await traverse(item_id, 0)

        return {
            "root_id": item_id,
            "nodes": list(nodes.values()),
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }

    async def get_stats(self, db: AsyncSession) -> dict:
        """Get intelligence layer statistics."""
        from sqlalchemy import func

        # Count by type
        type_result = await db.execute(
            select(
                KnowledgeItem.knowledge_type,
                func.count(KnowledgeItem.id).label("count"),
            )
            .where(KnowledgeItem.is_confirmed == True)  # noqa: E712
            .group_by(KnowledgeItem.knowledge_type)
        )
        by_type = {row[0]: row[1] for row in type_result}

        # Count by category
        cat_result = await db.execute(
            select(
                KnowledgeItem.category,
                func.count(KnowledgeItem.id).label("count"),
            )
            .where(KnowledgeItem.is_confirmed == True)  # noqa: E712
            .group_by(KnowledgeItem.category)
        )
        by_category = {row[0]: row[1] for row in cat_result}

        # Total counts
        total_result = await db.execute(
            select(func.count(KnowledgeItem.id)).where(
                KnowledgeItem.is_confirmed == True  # noqa: E712
            )
        )
        total = total_result.scalar() or 0

        pending_result = await db.execute(
            select(func.count(KnowledgeItem.id)).where(
                KnowledgeItem.is_confirmed == False  # noqa: E712
            )
        )
        pending = pending_result.scalar() or 0

        rel_result = await db.execute(
            select(func.count(KnowledgeRelationship.id))
        )
        total_relationships = rel_result.scalar() or 0

        return {
            "total_confirmed": total,
            "total_pending": pending,
            "total_relationships": total_relationships,
            "by_type": by_type,
            "by_category": by_category,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
intelligence_service = IntelligenceService()