"""
AURA Backend — Multi-Agent Framework Routes.

Module: app.api.v1.routes.agents_v2
Purpose: HTTP endpoints for Tier 4-A1 — Multi-Agent Framework.

Endpoints:
    GET  /api/v1/agents/list      — List all agents
    POST /api/v1/agents/run       — Run a task
    POST /api/v1/agents/code      — Code-specific shortcut
    POST /api/v1/agents/research  — Research-specific shortcut
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents_v2.agent_service import agent_service

logger = logging.getLogger(__name__)
router = APIRouter()


class AgentRunRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=2000)
    agent_id: str | None = Field(
        default=None,
        description="Force a specific agent: 'coding' or 'research'",
    )
    context: dict = Field(default_factory=dict)


class CodeTaskRequest(BaseModel):
    task: str = Field(..., min_length=1)
    task_type: str = Field(
        default="write",
        description="write|fix|explain|review|test",
    )
    code: str = Field(default="")
    language: str = Field(default="python")
    error: str = Field(default="")


class ResearchTaskRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    task_type: str = Field(
        default="web_search",
        description="web_search|news_search|deep_research",
    )
    language: str = Field(default="en")


@router.get(
    "/agents/list",
    summary="List Available Agents",
    tags=["Agents v2"],
    operation_id="list_agents_v2",  # এই line যোগ করুন
)
async def list_agents_v2() -> dict:  # function name ও বদলান
    """List all registered agents and their capabilities."""
    return {
        "agents": agent_service.list_agents(),
        "total": len(agent_service.list_agents()),
    }


@router.post(
    "/agents/run",
    summary="Run Agent Task",
    description="Execute any task through the agent coordinator.",
    tags=["Agents v2"],
)
async def run_agent(request: AgentRunRequest) -> dict:
    """Run a task through the multi-agent framework."""
    return await agent_service.run(
        task=request.task,
        context=request.context,
        agent_id=request.agent_id,
    )


@router.post(
    "/agents/code",
    summary="Code Task",
    description="Run a code-related task through the Coding Agent.",
    tags=["Agents v2"],
)
async def run_code_task(request: CodeTaskRequest) -> dict:
    """Execute a coding task."""
    context = {
        "task_type": request.task_type,
        "code": request.code,
        "language": request.language,
        "error": request.error,
    }
    return await agent_service.run(
        task=request.task,
        context=context,
        agent_id="coding",
    )


@router.post(
    "/agents/research",
    summary="Research Task",
    description="Run a research task through the Research Agent.",
    tags=["Agents v2"],
)
async def run_research_task(request: ResearchTaskRequest) -> dict:
    """Execute a research task."""
    context = {
        "task_type": request.task_type,
        "language": request.language,
    }
    return await agent_service.run(
        task=request.topic,
        context=context,
        agent_id="research",
    )