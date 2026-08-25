"""
AURA Backend — Window Controller.

Module: app.computer_control.window_controller
Purpose: List, focus, minimize, maximize Windows application windows.
         Low-risk — listing needs no confirmation.
         Focusing/closing asks for confirmation.

Dependencies:
    pip install pygetwindow
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WindowInfo:
    title: str
    is_active: bool
    is_minimized: bool
    is_maximized: bool

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "is_active": self.is_active,
            "is_minimized": self.is_minimized,
            "is_maximized": self.is_maximized,
        }


@dataclass
class WindowResult:
    success: bool
    operation: str
    windows: list = None
    message: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "operation": self.operation,
            "windows": [w.to_dict() for w in (self.windows or [])],
            "message": self.message,
            "error": self.error,
        }


class WindowController:
    """
    Windows window management controller.

    Methods:
        list_windows: Get all visible windows.
        focus_window: Bring a window to front.
        minimize_window: Minimize a window.
        maximize_window: Maximize a window.
    """

    def list_windows(self) -> WindowResult:
        """List all visible application windows."""
        try:
            import pygetwindow as gw

            all_windows = gw.getAllWindows()
            visible = [
                WindowInfo(
                    title=w.title,
                    is_active=w.isActive,
                    is_minimized=w.isMinimized,
                    is_maximized=w.isMaximized,
                )
                for w in all_windows
                if w.title.strip()
            ]

            return WindowResult(
                success=True,
                operation="list",
                windows=visible,
                message=f"Found {len(visible)} windows",
            )
        except Exception as e:
            logger.exception("List windows failed: %s", e)
            return WindowResult(success=False, operation="list", error=str(e))

    def focus_window(
        self,
        title_keyword: str,
        confirmed: bool = False,
    ) -> WindowResult:
        """
        Focus a window matching the title keyword.

        Args:
            title_keyword: Partial window title to match.
            confirmed: Must be True to proceed.
        """
        if not confirmed:
            return WindowResult(
                success=False,
                operation="focus",
                error="Window focus requires confirmed=True.",
            )

        try:
            import pygetwindow as gw

            matches = gw.getWindowsWithTitle(title_keyword)
            if not matches:
                return WindowResult(
                    success=False,
                    operation="focus",
                    error=f"No window found with title containing '{title_keyword}'",
                )

            window = matches[0]
            window.activate()
            logger.info("Focused window: %s", window.title)
            return WindowResult(
                success=True,
                operation="focus",
                message=f"Focused: {window.title}",
            )
        except Exception as e:
            logger.exception("Focus window failed: %s", e)
            return WindowResult(success=False, operation="focus", error=str(e))


window_controller = WindowController()