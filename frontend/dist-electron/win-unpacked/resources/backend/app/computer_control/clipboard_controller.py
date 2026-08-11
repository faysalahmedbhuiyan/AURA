"""
AURA Backend — Clipboard Controller.

Module: app.computer_control.clipboard_controller
Purpose: Read from and write to Windows clipboard.
         Low-risk — reading needs no confirmation.
         Writing asks user to confirm.

Dependencies:
    pip install pyperclip
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClipboardResult:
    success: bool
    operation: str
    content: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "operation": self.operation,
            "content": self.content[:1000],
            "error": self.error,
        }


class ClipboardController:
    """
    Windows clipboard controller.

    Methods:
        read: Get current clipboard content.
        write: Set clipboard content (confirmed=True required).
    """

    def read(self) -> ClipboardResult:
        """Read current clipboard text content."""
        try:
            import pyperclip
            content = pyperclip.paste()
            logger.info("Clipboard read: %d chars", len(content))
            return ClipboardResult(
                success=True,
                operation="read",
                content=content or "",
            )
        except Exception as e:
            logger.error("Clipboard read failed: %s", e)
            return ClipboardResult(
                success=False,
                operation="read",
                error=str(e),
            )

    def write(
        self,
        content: str,
        confirmed: bool = False,
    ) -> ClipboardResult:
        """
        Write text to clipboard.

        Args:
            content: Text to copy.
            confirmed: Must be True to proceed.

        Returns:
            ClipboardResult: Success/failure.
        """
        if not confirmed:
            return ClipboardResult(
                success=False,
                operation="write",
                error="Clipboard write requires confirmed=True.",
            )

        try:
            import pyperclip
            pyperclip.copy(content)
            logger.info("Clipboard write: %d chars", len(content))
            return ClipboardResult(
                success=True,
                operation="write",
                content=content[:100] + "..." if len(content) > 100 else content,
            )
        except Exception as e:
            logger.error("Clipboard write failed: %s", e)
            return ClipboardResult(
                success=False,
                operation="write",
                error=str(e),
            )


clipboard_controller = ClipboardController()