"""
AURA Backend — Screenshot Controller.

Module: app.computer_control.screenshot_controller
Purpose: Capture screenshots and extract text via OCR.
         Low-risk operation — no confirmation needed.

Dependencies:
    pip install pillow pytesseract pyautogui
    External: Tesseract OCR binary (already installed for Tier 3)
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path("D:/AURA/screenshots")


@dataclass
class ScreenshotResult:
    success: bool
    file_path: str = ""
    ocr_text: str = ""
    width: int = 0
    height: int = 0
    error: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "file_path": self.file_path,
            "ocr_text": self.ocr_text[:2000] if self.ocr_text else "",
            "width": self.width,
            "height": self.height,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class ScreenshotController:
    """
    Screenshot capture and OCR controller.

    Methods:
        capture: Take a screenshot and save to disk.
        capture_with_ocr: Screenshot + extract text via Tesseract.
        capture_region: Screenshot of a specific screen region.
    """

    def __init__(self) -> None:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    def capture(self) -> ScreenshotResult:
        """
        Take a full-screen screenshot.

        Returns:
            ScreenshotResult: Path to saved PNG file.
        """
        try:
            import pyautogui
            from PIL import Image

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = SCREENSHOT_DIR / f"screenshot_{timestamp}.png"

            screenshot = pyautogui.screenshot()
            screenshot.save(str(filename))

            return ScreenshotResult(
                success=True,
                file_path=str(filename),
                width=screenshot.width,
                height=screenshot.height,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            logger.exception("Screenshot failed: %s", e)
            return ScreenshotResult(success=False, error=str(e))

    def capture_with_ocr(self) -> ScreenshotResult:
        """
        Take screenshot and extract text via Tesseract OCR.

        Returns:
            ScreenshotResult: Path + extracted text.
        """
        result = self.capture()
        if not result.success:
            return result

        try:
            import pytesseract
            from PIL import Image

            img = Image.open(result.file_path)
            text = pytesseract.image_to_string(img, lang="eng+ben")
            result.ocr_text = text.strip()
            return result

        except Exception as e:
            logger.warning("OCR failed: %s", e)
            result.ocr_text = ""
            return result

    def capture_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> ScreenshotResult:
        """
        Take screenshot of a specific screen region.

        Args:
            x, y: Top-left corner coordinates.
            width, height: Region dimensions.

        Returns:
            ScreenshotResult: Cropped screenshot.
        """
        try:
            import pyautogui

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = SCREENSHOT_DIR / f"region_{timestamp}.png"

            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            screenshot.save(str(filename))

            return ScreenshotResult(
                success=True,
                file_path=str(filename),
                width=width,
                height=height,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            return ScreenshotResult(success=False, error=str(e))


screenshot_controller = ScreenshotController()