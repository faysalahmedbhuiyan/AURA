"""
AURA Backend — Sub-Agent Factory.

Module: app.agents_v2.sub_agent_factory
Purpose: Lets AURA create specialized "sub-agents" on request — e.g.
         "create a sub agent for writing code". A sub-agent is:
           1. A specialized system prompt (AURA writes this itself,
              via one LLM call, based on the task description).
           2. A dedicated knowledge table (SubAgentKnowledge) — content
              the user teaches it gets stored here and pulled into the
              prompt context on every question asked to that sub-agent.

         This is NOT real fine-tuning (not feasible on 8GB RAM / no GPU).
         It's prompt specialization + a private knowledge scratchpad —
         a realistic, honest version of "make this agent an expert at X".
"""

import logging
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.sub_agent_repository import sub_agent_repository

logger = logging.getLogger(__name__)

META_PROMPT_TEMPLATE = (
    "You are helping design a specialized AI assistant persona. "
    "The user wants a sub-agent for this task:\n\n"
    "\"{task_description}\"\n\n"
    "Write a system prompt (2-5 sentences) that turns a general-purpose "
    "assistant into a specialist for exactly this task. Be concrete about "
    "what it should focus on, what tone/format to use, and what to avoid. "
    "Output ONLY the system prompt text — no preamble, no quotes, no "
    "explanation."
)


def _slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].strip("-") or "agent"


class SubAgentFactory:
    """Creates, teaches, and queries specialized sub-agents."""

    async def create_sub_agent(self, db: AsyncSession, task_description: str, brain_role: str = "default") -> dict:
        """Create a new sub-agent specialized for the given task."""
        from app.services.ollama_service import ollama_service

        base_slug = _slugify(task_description)
        name = f"{base_slug}-{uuid.uuid4().hex[:6]}"  # guaranteed-unique, no retry needed

        meta_prompt = META_PROMPT_TEMPLATE.format(task_description=task_description)
        system_prompt = await ollama_service.chat(
            message=meta_prompt,
            history=[],
            system_prompt="You are a precise prompt engineer. Follow instructions exactly.",
        )
        system_prompt = system_prompt.strip()

        agent = await sub_agent_repository.create(
            db=db,
            name=name,
            task_description=task_description,
            system_prompt=system_prompt,
            brain_role=brain_role,
        )
        await db.commit()

        logger.info("Sub-agent '%s' created for task: %s", name, task_description[:80])

        return {
            "id": agent.id,
            "name": agent.name,
            "task_description": agent.task_description,
            "status": agent.status,
            "brain_role": agent.brain_role,
            "knowledge_count": 0,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "system_prompt": system_prompt,
        }

    async def teach(
        self, db: AsyncSession, name: str, content: str, title: str | None = None,
    ) -> dict:
        """Add a piece of knowledge to a sub-agent's private scratchpad."""
        agent = await sub_agent_repository.get_by_name(db, name)
        if not agent:
            return {"success": False, "error": f"No sub-agent named '{name}' found."}

        await sub_agent_repository.add_knowledge(db, agent.id, content, title)
        await db.commit()

        logger.info("Taught sub-agent '%s': %s", name, (title or content[:40]))
        return {"success": True, "sub_agent": name}

    async def ask(self, db: AsyncSession, name: str, question: str) -> dict:
        """Ask a specific sub-agent a question, using its specialized prompt + knowledge."""
        from app.services.ollama_service import ollama_service

        agent = await sub_agent_repository.get_by_name(db, name)
        if not agent:
            return {"success": False, "error": f"No sub-agent named '{name}' found."}

        context = sub_agent_repository.build_context(agent)
        prompt = question
        if context:
            prompt = (
                f"Relevant knowledge you've been taught:\n\n{context}\n\n"
                f"---\n\nUsing the above where relevant, answer:\n{question}"
            )

        from app.services.brain_orchestrator import BrainRole, run_with_role

        role = BrainRole.BUSINESS if agent.brain_role == "business" else (
            BrainRole.CODING if agent.brain_role == "coding" else BrainRole.DEFAULT
        )
        answer = await run_with_role(role, prompt, system_prompt=agent.system_prompt)

        return {"success": True, "sub_agent": name, "answer": answer.strip()}

    async def list_sub_agents(self, db: AsyncSession) -> list[dict]:
        agents = await sub_agent_repository.list_all(db)
        return [a.to_dict() for a in agents]


sub_agent_factory = SubAgentFactory()
