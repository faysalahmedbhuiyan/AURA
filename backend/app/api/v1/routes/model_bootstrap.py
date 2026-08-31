"""
AURA Backend — Model Bootstrap Status Route.

Module: app.api.v1.routes.model_bootstrap
Purpose: Reports progress of the background first-run model check/download
         kicked off from main.py's lifespan (see model_bootstrap_service.
         run_bootstrap_in_background). The backend itself is reachable the
         moment the server boots — this endpoint is what the desktop UI
         should poll to show "downloading AI models..." instead of the app
         looking frozen while a multi-GB export happens in the background.
"""

from fastapi import APIRouter

from app.services.model_bootstrap_service import bootstrap_state
from app.services.ollama_bootstrap_service import ollama_bootstrap_state

router = APIRouter()


@router.get(
    "/model-bootstrap-status",
    summary="Model Bootstrap Status",
    description=(
        "Status of the background first-run model check/download. "
        "'status' is one of: pending, running, done, error. "
        "'report' (once done) groups model names by outcome: ok, "
        "downloaded, skipped_ram, skipped_disk, download_failed, "
        "missing_no_script."
    ),
    tags=["System"],
)
async def model_bootstrap_status() -> dict:
    return bootstrap_state


@router.get(
    "/ollama-bootstrap-status",
    summary="Ollama Bootstrap Status",
    description=(
        "Status of the background first-run Ollama install/start/model-pull. "
        "'status' progresses: pending -> checking -> installing -> starting -> "
        "pulling_model -> building_brain -> ready (or error / unsupported_platform)."
    ),
    tags=["System"],
)
async def ollama_bootstrap_status() -> dict:
    return ollama_bootstrap_state