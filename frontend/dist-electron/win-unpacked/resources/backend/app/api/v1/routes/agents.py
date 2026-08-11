"""
AURA Backend — Agent Routes.

Module: app.api.v1.routes.agents
Purpose: HTTP endpoints for AURA's agent system.
         Allows frontend and chat to trigger agent actions.

Endpoints:
    POST /api/v1/agents/execute     — Execute any agent action
    GET  /api/v1/agents/health      — System health check
    GET  /api/v1/agents/list        — List available agents
"""

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.file_agent import file_agent
from app.agents.system_agent import system_agent

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Agent Registry ────────────────────────────────────────────────────────────
AGENT_REGISTRY = {
    "file": file_agent,
    "system": system_agent,
}


# ── Schemas ───────────────────────────────────────────────────────────────────
class AgentExecuteRequest(BaseModel):
    """Request schema for agent execution."""

    agent: str = Field(
        ...,
        description="Agent name: 'file' or 'system'",
    )
    action: str = Field(
        ...,
        description="Action to perform (e.g., 'list', 'read', 'ram')",
    )
    params: dict = Field(
        default_factory=dict,
        description="Action-specific parameters",
    )


class AgentResponse(BaseModel):
    """Response schema for agent execution."""

    success: bool
    agent: str
    action: str
    data: dict | list | str | None
    error: str | None
    timestamp: str


class AgentInfo(BaseModel):
    """Info about an available agent."""

    id: str
    name: str
    description: str
    actions: list[str]


# ── Routes ────────────────────────────────────────────────────────────────────
@router.get(
    "/agents/list",
    response_model=list[AgentInfo],
    summary="List Available Agents",
    description="Returns all available AURA agents and their supported actions.",
    tags=["Agents"],
)
async def list_agents() -> list[AgentInfo]:
    """
    List all registered agents and their capabilities.

    Returns:
        list[AgentInfo]: Available agents with actions.
    """
    return [
        AgentInfo(
            id="file",
            name="File Agent",
            description="Read, write, list, and search files on the local system.",
            actions=["list", "read", "write", "search", "info", "exists"],
        ),
        AgentInfo(
            id="system",
            name="System Agent",
            description="Monitor system health: RAM, CPU, disk, and processes.",
            actions=["ram", "cpu", "disk", "health", "info", "processes"],
        ),
    ]


@router.post(
    "/agents/execute",
    response_model=AgentResponse,
    summary="Execute Agent Action",
    description="Execute an action on a specific AURA agent.",
    tags=["Agents"],
)
async def execute_agent(request: AgentExecuteRequest) -> AgentResponse:
    """
    Execute an agent action.

    Args:
        request: Agent name, action, and parameters.

    Returns:
        AgentResponse: Result with success/data/error.

    Raises:
        404: If agent not found.
        500: If agent execution fails.
    """
    agent = AGENT_REGISTRY.get(request.agent)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{request.agent}' not found. "
                   f"Available: {', '.join(AGENT_REGISTRY.keys())}",
        )

    result = await agent.execute(request.action, request.params)

    return AgentResponse(
        success=result.success,
        agent=request.agent,
        action=result.action,
        data=result.data,
        error=result.error,
        timestamp=result.timestamp,
    )


@router.get(
    "/agents/health",
    response_model=AgentResponse,
    summary="System Health Check",
    description="Quick system health check via System Agent.",
    tags=["Agents"],
)
async def agent_health() -> AgentResponse:
    """
    Get system health via SystemAgent.

    Returns:
        AgentResponse: CPU, RAM, disk status.
    """
    result = await system_agent.execute("health", {})

    return AgentResponse(
        success=result.success,
        agent="system",
        action=result.action,
        data=result.data,
        error=result.error,
        timestamp=result.timestamp,
    )