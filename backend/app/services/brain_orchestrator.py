"""
Tier 7 — Adaptive Multi-Model Brain.
Manages which Ollama model is loaded, ensures only one heavy role is
resident at a time, and coordinates with image_service.py's existing
"unload Ollama before generation" logic so the two systems never fight
over RAM.
"""

from enum import Enum

class BrainRole(str, Enum):
    DEFAULT = "qwen2.5:3b-instruct"   # aura-brain — always assumed available
    CODING = "phi4-mini"
    BUSINESS = "gemma4:e2b"


async def run_with_role(role: BrainRole, messages: list[dict], **ollama_kwargs) -> dict:
    """
    Calls Ollama with the given role's model.
    - DEFAULT role: normal call, no special keep_alive (stays resident as usual).
    - CODING / BUSINESS role: always passed with keep_alive=0, so the model
      unloads the instant this call finishes — never lingers, never competes
      with the next image-generation request or the next chat turn.

    Precedence rule (must match image_service.py's existing behavior):
    before loading CODING or BUSINESS role, check whether the image
    pipeline currently holds GPU/RAM (image_service already exposes an
    "is generating" state for its own Ollama-unload logic — reuse that
    same check here rather than duplicating it). If image generation is
    active, queue/wait rather than loading a second heavy process
    simultaneously.
    """
    ...