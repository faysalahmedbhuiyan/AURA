"""
AURA Backend — Browser Controller.

Module: app.computer_control.browser_controller
Purpose: Open URLs in the default browser.
         Low-risk — opens publicly accessible URLs only.

Safety:
    - Only http/https URLs allowed
    - No file:// or other protocols
"""

import logging
import re
import webbrowser
from dataclasses import dataclass

logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(
    r'^https?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$',
    re.IGNORECASE,
)


@dataclass
class BrowserResult:
    success: bool
    url: str
    message: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "url": self.url,
            "message": self.message,
            "error": self.error,
        }


class BrowserController:
    """
    Default browser controller.

    Methods:
        open_url: Open a URL in the default browser.
    """

    def open_url(self, url: str) -> BrowserResult:
        """
        Open URL in default browser.

        Only http/https URLs are allowed.

        Args:
            url: URL to open.

        Returns:
            BrowserResult: Success/failure.
        """
        if not URL_PATTERN.match(url):
            return BrowserResult(
                success=False,
                url=url,
                error=f"Invalid or unsafe URL: {url}. Only http/https allowed.",
            )

        try:
            webbrowser.open(url)
            logger.info("Opened browser: %s", url)
            return BrowserResult(
                success=True,
                url=url,
                message=f"Opened in browser: {url}",
            )
        except Exception as e:
            logger.exception("Browser open failed: %s", e)
            return BrowserResult(success=False, url=url, error=str(e))


browser_controller = BrowserController()