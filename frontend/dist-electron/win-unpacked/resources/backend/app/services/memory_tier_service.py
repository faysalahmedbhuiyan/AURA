"""
AURA Backend — Memory Tier Service.

Module: app.services.memory_tier_service
Purpose: Orchestrates the Learning Queue confirmation workflow — the
         ONLY path by which an item can become permanent memory.
         Enforces Phase 13's core safety rule: nothing moves from the
         queue to Personal Memory or Decision Records without explicit
         user confirmation.
"""

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.memory_tier_repository import memory_tier_repository

logger = logging.getLogger(__name__)


class MemoryTierService:
    """
    Handles queue-to-tier promotion after explicit confirmation.

    Methods:
        confirm_item: Move a pending queue item into its target tier.
        reject_item: Mark a queue item rejected — never stored permanently.
    """

    async def confirm_item(self, db: AsyncSession, item_id: str) -> dict:
        """
        Confirm a learning queue item, creating the permanent record.

        Args:
            db: Async database session.
            item_id: UUID of the queue item to confirm.

        Returns:
            dict: {"success": bool, "created": dict | None, "error": str | None}
        """
        item = await memory_tier_repository.get_queue_item(db, item_id)
        if not item:
            return {"success": False, "created": None, "error": "Queue item not found."}

        if item.status != "pending":
            return {
                "success": False, "created": None,
                "error": f"Item is already '{item.status}', cannot confirm again.",
            }

        try:
            payload = json.loads(item.payload)
        except json.JSONDecodeError as e:
            return {"success": False, "created": None, "error": f"Invalid payload: {e}"}

        try:
            if item.target_tier == "personal":
                created = await memory_tier_repository.create_personal(
                    db,
                    key=payload["key"],
                    value=payload["value"],
                    category=payload.get("category", "preference"),
                    is_sensitive=payload.get("is_sensitive", False),
                )
                created_data = {"id": created.id, "key": created.key, "value": created.value}

            elif item.target_tier == "decision":
                created = await memory_tier_repository.create_decision(
                    db,
                    title=payload["title"],
                    context=payload["context"],
                    decision=payload["decision"],
                    consequences=payload.get("consequences"),
                    status=payload.get("status", "accepted"),
                    tags=payload.get("tags"),
                )
                created_data = {"id": created.id, "title": created.title}

            else:
                return {
                    "success": False, "created": None,
                    "error": f"Unknown target_tier: '{item.target_tier}'.",
                }

        except KeyError as e:
            return {"success": False, "created": None, "error": f"Missing payload field: {e}"}

        await memory_tier_repository.update_queue_status(db, item_id, "confirmed")
        logger.info("Queue item confirmed and promoted: %s -> %s", item.title, item.target_tier)

        return {"success": True, "created": created_data, "error": None}

    async def reject_item(self, db: AsyncSession, item_id: str) -> dict:
        """
        Reject a learning queue item — it will never become permanent.

        Args:
            db: Async database session.
            item_id: UUID of the queue item to reject.

        Returns:
            dict: {"success": bool, "error": str | None}
        """
        item = await memory_tier_repository.update_queue_status(db, item_id, "rejected")
        if not item:
            return {"success": False, "error": "Queue item not found."}
        logger.info("Queue item rejected: %s", item.title)
        return {"success": True, "error": None}


# ── Singleton instance ────────────────────────────────────────────────────────
memory_tier_service = MemoryTierService()