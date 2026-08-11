"""
AURA Backend — Research Routes.

Module: app.api.v1.routes.research
Purpose: API endpoint for the Knowledge System "Search → Collect →
         Verify → Summarize" pipeline. Produces a candidate for
         review only — never saves or confirms automatically.

Endpoint:
    POST /api/v1/knowledge/research — Run the research pipeline.
"""

import logging

from fastapi import APIRouter

from app.schemas.research import ResearchCandidateResponse, ResearchRequest
from app.services.research_service import research_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/knowledge/research",
    response_model=ResearchCandidateResponse,
    summary="Research a Topic from the Web",
    description=(
        "Runs Search → Collect → Verify → Summarize on a topic and "
        "returns a candidate knowledge entry. Does NOT save anything — "
        "the user must review and POST to /memory/knowledge, then "
        "confirm it, per AURA's confirm-before-save rule."
    ),
    tags=["Knowledge Research"],
)
async def research_topic(request: ResearchRequest) -> ResearchCandidateResponse:
    """
    Run the research pipeline for a given query.

    Args:
        request: ResearchRequest with query, language, max_sources.

    Returns:
        ResearchCandidateResponse: Candidate entry for user review.
    """
    result = await research_service.research(
        query=request.query,
        language=request.language,
        max_sources=request.max_sources,
    )
    return ResearchCandidateResponse(**result)