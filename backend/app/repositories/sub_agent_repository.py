"""
AURA Backend — Sub-Agent Repository.

Module: app.repositories.sub_agent_repository
Purpose: All database operations for SubAgent and SubAgentKnowledge.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sub_agent import SubAgent, SubAgentKnowledge

logger = logging.getLogger(__name__)

# Cap how much taught content gets pulled into a single prompt — keeps
# generation time/RAM sane on this hardware. Most recent rows win.
MAX_KNOWLEDGE_CHARS = 6000


class SubAgentRepository:
    """Repository for SubAgent / SubAgentKnowledge database operations."""

    async def create(
        self,
        db: AsyncSession,
        name: str,
        task_description: str,
        system_prompt: str,
    ) -> SubAgent:
        agent = SubAgent(
            name=name,
            task_description=task_description,
            system_prompt=system_prompt,
            status="active",
        )
        db.add(agent)
        await db.flush()
        await db.refresh(agent)
        logger.info("Created sub-agent: %s", name)
        return agent

    async def get_by_name(self, db: AsyncSession, name: str) -> SubAgent | None:
        result = await db.execute(
            select(SubAgent)
            .options(selectinload(SubAgent.knowledge))
            .where(SubAgent.name == name, SubAgent.status == "active")
        )
        return result.scalar_one_or_none()

    async def list_all(self, db: AsyncSession) -> list[SubAgent]:
        result = await db.execute(
            select(SubAgent)
            .options(selectinload(SubAgent.knowledge))
            .where(SubAgent.status == "active")
            .order_by(SubAgent.created_at.desc())
        )
        return list(result.scalars().all())

    async def retire(self, db: AsyncSession, name: str) -> bool:
        agent = await self.get_by_name(db, name)
        if not agent:
            return False
        agent.status = "retired"
        await db.flush()
        return True

    async def add_knowledge(
        self, db: AsyncSession, sub_agent_id: str, content: str, title: str | None = None,
    ) -> SubAgentKnowledge:
        row = SubAgentKnowledge(sub_agent_id=sub_agent_id, content=content, title=title)
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row

    def build_context(self, agent: SubAgent) -> str:
        """
        Concatenate this sub-agent's taught knowledge into a prompt-ready
        block, most recent first, capped at MAX_KNOWLEDGE_CHARS.
        """
        if not agent.knowledge:
            return ""

        chunks = []
        total = 0
        for item in reversed(agent.knowledge):  # most recent first
            piece = f"[{item.title or 'note'}]\n{item.content}\n"
            if total + len(piece) > MAX_KNOWLEDGE_CHARS:
                break
            chunks.append(piece)
            total += len(piece)

        return "\n---\n".join(chunks)


sub_agent_repository = SubAgentRepository()
