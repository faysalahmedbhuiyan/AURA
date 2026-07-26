"""
AURA Backend — Computer Control Service.

Module: app.computer_control.computer_service
Purpose: Main orchestrator for Computer Control (Tier 4-A3).
         Routes natural language commands to appropriate controllers.

Safety levels:
    LOW  — screenshot, clipboard read, window list, open URL
    HIGH — shell commands, clipboard write, window focus/close

HIGH risk operations ALWAYS require confirmed=True.
Every operation is logged.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Natural language → action mapping
COMPUTER_INTENTS = {
    "screenshot": [
        r'\btake.*(screenshot|screen shot|snap)\b',
        r'\bscreenshot\b', r'\bcapture.*screen\b',
        r'স্ক্রিনশট', r'স্ক্রিন ক্যাপচার',
    ],
    "screenshot_ocr": [
        r'\b(read|extract|ocr).*(screen|screenshot)\b',
        r'\bwhat.*screen\b', r'\bscreen.*text\b',
    ],
    "clipboard_read": [
        r'\b(read|get|show).*(clipboard|copied)\b',
        r'\bwhat.*clipboard\b', r'ক্লিপবোর্ড',
    ],
    "clipboard_write": [
        r'\b(copy|write|put).*(clipboard)\b',
    ],
    "window_list": [
        r'\b(list|show|what).*(windows?|apps?|applications?)\b',
        r'\bopen.*(windows?|apps?)\b',
        r'কোন (উইন্ডো|অ্যাপ)',
    ],
    "open_url": [
        r'\b(open|go to|visit|browse)\s+https?://',
        r'\bopen\s+\w+\.(com|net|org|io|bd)\b',
    ],
    "run_powershell": [
        r'\brun\b.*\bpowershell\b', r'\bpowershell\b.*\brun\b',
        r'\bexecute\b.*\bcommand\b',
    ],
}


class ComputerService:
    """
    Computer Control orchestrator.

    Routes natural language requests to appropriate controllers.
    Enforces safety rules — HIGH risk always needs confirmation.

    Methods:
        execute: Main entry point for computer control actions.
        detect_action: Detect what action is needed from message.
        get_capabilities: List all available actions.
    """

    def detect_action(self, message: str) -> str | None:
        """
        Detect computer control action from message.

        Args:
            message: User message.

        Returns:
            str | None: Action name or None if not a computer command.
        """
        msg_lower = message.lower()
        for action, patterns in COMPUTER_INTENTS.items():
            if any(re.search(p, msg_lower, re.IGNORECASE) for p in patterns):
                return action
        return None

    async def execute(
        self,
        action: str,
        params: dict,
        confirmed: bool = False,
    ) -> dict:
        """
        Execute a computer control action.

        Args:
            action: Action to execute.
            params: Action parameters.
            confirmed: Required for HIGH risk actions.

        Returns:
            dict: Result with success/data/error.
        """
        from app.computer_control.browser_controller import browser_controller
        from app.computer_control.clipboard_controller import clipboard_controller
        from app.computer_control.screenshot_controller import screenshot_controller
        from app.computer_control.shell_controller import shell_controller
        from app.computer_control.window_controller import window_controller

        logger.info("Computer control: action=%s confirmed=%s", action, confirmed)

        if action == "screenshot":
            result = screenshot_controller.capture()
            return result.to_dict()

        elif action == "screenshot_ocr":
            result = screenshot_controller.capture_with_ocr()
            return result.to_dict()

        elif action == "clipboard_read":
            result = clipboard_controller.read()
            return result.to_dict()

        elif action == "clipboard_write":
            content = params.get("content", "")
            result = clipboard_controller.write(content, confirmed=confirmed)
            return result.to_dict()

        elif action == "window_list":
            result = window_controller.list_windows()
            return result.to_dict()

        elif action == "window_focus":
            title = params.get("title", "")
            result = window_controller.focus_window(title, confirmed=confirmed)
            return result.to_dict()

        elif action == "open_url":
            url = params.get("url", "")
            if not url:
                url = self._extract_url(params.get("message", ""))
            result = browser_controller.open_url(url)
            return result.to_dict()

        elif action == "run_powershell":
            command = params.get("command", "")
            result = shell_controller.run_powershell(
                command, confirmed=confirmed
            )
            return result.to_dict()

        elif action == "run_cmd":
            command = params.get("command", "")
            result = shell_controller.run_cmd(command, confirmed=confirmed)
            return result.to_dict()

        else:
            return {
                "success": False,
                "error": f"Unknown action: '{action}'",
                "available": list(COMPUTER_INTENTS.keys()),
            }

    def _extract_url(self, message: str) -> str:
        """Extract URL from message text."""
        url_match = re.search(r'https?://\S+', message)
        return url_match.group(0) if url_match else ""

    def get_capabilities(self) -> list[dict]:
        """List all computer control capabilities."""
        return [
            {
                "action": "screenshot",
                "description": "Take a screenshot",
                "risk": "low",
                "confirmation_required": False,
            },
            {
                "action": "screenshot_ocr",
                "description": "Screenshot + extract text",
                "risk": "low",
                "confirmation_required": False,
            },
            {
                "action": "clipboard_read",
                "description": "Read clipboard content",
                "risk": "low",
                "confirmation_required": False,
            },
            {
                "action": "clipboard_write",
                "description": "Write to clipboard",
                "risk": "medium",
                "confirmation_required": True,
            },
            {
                "action": "window_list",
                "description": "List open windows",
                "risk": "low",
                "confirmation_required": False,
            },
            {
                "action": "window_focus",
                "description": "Focus a window",
                "risk": "medium",
                "confirmation_required": True,
            },
            {
                "action": "open_url",
                "description": "Open URL in browser",
                "risk": "low",
                "confirmation_required": False,
            },
            {
                "action": "run_powershell",
                "description": "Run PowerShell command",
                "risk": "high",
                "confirmation_required": True,
            },
        ]


computer_service = ComputerService()