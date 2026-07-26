"""
AURA Backend — Computer Control Routes.

Module: app.api.v1.routes.computer_control
Purpose: HTTP endpoints for Tier 4-A3 — Computer Control.

Endpoints:
    GET  /api/v1/computer/capabilities  — List all actions
    POST /api/v1/computer/execute       — Execute an action
    POST /api/v1/computer/screenshot    — Quick screenshot
    GET  /api/v1/computer/clipboard     — Read clipboard
    GET  /api/v1/computer/windows       — List windows
"""

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.computer_control.computer_service import computer_service

logger = logging.getLogger(__name__)
router = APIRouter()


class ComputerExecuteRequest(BaseModel):
    action: str = Field(
        ...,
        description=(
            "screenshot | screenshot_ocr | clipboard_read | "
            "clipboard_write | window_list | window_focus | "
            "open_url | run_powershell | run_cmd"
        ),
    )
    params: dict = Field(default_factory=dict)
    confirmed: bool = Field(
        default=False,
        description="Required for HIGH risk actions (shell, clipboard write, window focus)",
    )


@router.get(
    "/computer/capabilities",
    summary="List Computer Control Capabilities",
    tags=["Computer Control"],
)
async def get_capabilities() -> dict:
    """List all available computer control actions."""
    return {
        "capabilities": computer_service.get_capabilities(),
        "note": "HIGH risk actions require confirmed=True in the execute request.",
    }


@router.post(
    "/computer/execute",
    summary="Execute Computer Action",
    description=(
        "Execute a computer control action. "
        "HIGH risk actions (shell, clipboard write) require confirmed=True."
    ),
    tags=["Computer Control"],
)
async def execute_computer_action(request: ComputerExecuteRequest) -> dict:
    """Execute a computer control action."""
    result = await computer_service.execute(
        action=request.action,
        params=request.params,
        confirmed=request.confirmed,
    )

    if not result.get("success") and result.get("was_blocked"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result.get("error", "Command blocked for safety"),
        )

    return result


@router.post(
    "/computer/screenshot",
    summary="Take Screenshot",
    description="Capture full screen screenshot. Low risk — no confirmation needed.",
    tags=["Computer Control"],
)
async def take_screenshot(ocr: bool = False) -> dict:
    """Take a screenshot, optionally with OCR text extraction."""
    from app.computer_control.screenshot_controller import screenshot_controller

    if ocr:
        result = screenshot_controller.capture_with_ocr()
    else:
        result = screenshot_controller.capture()

    return result.to_dict()


@router.get(
    "/computer/clipboard",
    summary="Read Clipboard",
    description="Read current clipboard content. Low risk.",
    tags=["Computer Control"],
)
async def read_clipboard() -> dict:
    """Read clipboard content."""
    from app.computer_control.clipboard_controller import clipboard_controller
    result = clipboard_controller.read()
    return result.to_dict()


@router.get(
    "/computer/windows",
    summary="List Open Windows",
    description="List all open application windows.",
    tags=["Computer Control"],
)
async def list_windows() -> dict:
    """List all open windows."""
    from app.computer_control.window_controller import window_controller
    result = window_controller.list_windows()
    return result.to_dict()