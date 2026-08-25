"""
Tier 7 — Adaptive Multi-Model Brain.

Module: app.services.brain_orchestrator
Purpose: Manages which Ollama model handles a given task. Three roles:
    - DEFAULT (aura-brain / qwen2.5:3b-instruct): always assumed
      resident, used for routine chat and all existing intents.
    - CODING (phi4-mini): loaded only for coding tasks, unloaded
      immediately after (keep_alive=0).
    - BUSINESS (gemma4:e2b): loaded only for business/decision tasks,
      unloaded immediately after (keep_alive=0).

Precedence: image generation always wins. If the image pipeline
currently has a model loaded (image_service.is_loaded()), a CODING/
BUSINESS role call waits briefly rather than loading a second heavy
process alongside it — this hardware has 8GB RAM total, running an
LLM role and the image pipeline at once risks OOM.
"""

import asyncio
import logging
from enum import Enum

logger = logging.getLogger(__name__)

# How long to wait (and how many times) for the image pipeline to
# free up before giving up and returning an error, rather than risking
# an OOM by loading a second heavy process anyway.
_WAIT_INTERVAL_SECONDS = 5
_MAX_WAIT_ATTEMPTS = 24  # 24 * 5s = 2 minutes max wait


class BrainRole(str, Enum):
    DEFAULT = "aura-brain"       # matches settings.ollama_model — unchanged behavior
    CODING = "phi4-mini"
    BUSINESS = "gemma4:e2b"


async def _image_pipeline_busy() -> bool:
    """True if the image generation pipeline currently holds RAM."""
    try:
        from app.services.image_service import image_service
        return image_service.is_loaded()
    except Exception as e:
        logger.warning("Could not check image pipeline state (assuming free): %s", e)
        return False


async def run_with_role(
    role: BrainRole,
    message: str,
    history: list[dict] | None = None,
    system_prompt: str | None = None,
) -> str:
    """
    Run a chat completion using the given role's model.

    DEFAULT role behaves exactly like a normal ollama_service.chat()
    call (no special handling — this IS the existing behavior).

    CODING/BUSINESS roles: wait for the image pipeline to be free (if
    busy), then call with keep_alive=0 so the model unloads the
    instant this call finishes.
    """
    from app.services.ollama_service import ollama_service

    if role == BrainRole.DEFAULT:
        return await ollama_service.chat(
            message=message, history=history, system_prompt=system_prompt,
        )

    # CODING / BUSINESS — wait for image pipeline if it's currently loaded.
    for attempt in range(_MAX_WAIT_ATTEMPTS):
        if not await _image_pipeline_busy():
            break
        logger.info(
            "Brain role '%s' waiting for image pipeline to free RAM "
            "(attempt %d/%d) ...", role.value, attempt + 1, _MAX_WAIT_ATTEMPTS,
        )
        await asyncio.sleep(_WAIT_INTERVAL_SECONDS)
    else:
        raise RuntimeError(
            "Image generation is still using RAM after waiting 2 minutes — "
            "try again once it finishes."
        )

    logger.info("Loading brain role '%s' (%s) with keep_alive=0 ...", role.value, role.name)
    result = await ollama_service.chat(
        message=message, history=history, system_prompt=system_prompt,
        model=role.value, keep_alive=0,
    )
    logger.info("Brain role '%s' call complete — model unloads immediately.", role.value)
    return result