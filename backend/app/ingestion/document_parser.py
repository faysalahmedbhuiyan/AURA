"""
AURA Backend — Document Parser.

Module: app.ingestion.document_parser
Purpose: Extracts text AND handles all file types correctly:
         - PDF: text + page images (PyMuPDF)
         - DOCX: text + table content (python-docx)
         - Image (JPG/PNG/WEBP/BMP): save as-is + OCR for search
         - Text files: read directly
         - Code files: read directly

IMPORTANT — Image files:
    Images are saved as actual image files, NOT converted to text.
    OCR is done ONLY for search indexing purposes.
    The original image bytes are always preserved.
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_CHARS = 100_000
MAX_PDF_PAGES_TO_RENDER = 30
RENDER_DPI = 150

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff", ".tif"}
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".py", ".js", ".jsx", ".ts",
                   ".tsx", ".css", ".html", ".xml", ".yaml", ".yml", ".env",
                   ".sh", ".bat", ".c", ".cpp", ".java", ".go", ".rs"}


class DocumentParser:
    """
    Extracts text and handles all file types for the File Vault.

    Methods:
        parse: Auto-detect file type and parse accordingly.
        parse_pdf: Extract text + render page images from PDF.
        parse_docx: Extract text from Word documents.
        parse_image: Save image + OCR for search indexing.
        parse_text: Read plain text / code files.
        render_pdf_pages: Render PDF pages to PNG images.
    """

    def parse(self, path: Path, output_dir: Path | None = None) -> dict:
        """
        Auto-detect file type and parse accordingly.

        Args:
            path: File to parse.
            output_dir: Directory for page images (PDF only).

        Returns:
            dict: {
                text: str,           # Extracted/OCR text for search
                kind: str,           # pdf/docx/image/text/code
                pages: int,          # Page count (PDF) or 1
                page_image_paths: list[str],  # PNG paths for viewing
                truncated: bool,
                is_image: bool,      # True if file is an image
                image_path: str,     # Original image path (images only)
            }
        """
        ext = path.suffix.lower()

        if ext == ".pdf":
            result = self.parse_pdf(path)
            if output_dir:
                page_images = self.render_pdf_pages(path, output_dir)
            else:
                page_images = []
            result["page_image_paths"] = page_images
            result["kind"] = "pdf"
            result["is_image"] = False
            result["image_path"] = None
            return result

        elif ext in (".docx", ".doc"):
            result = self.parse_docx(path)
            result["page_image_paths"] = []
            result["kind"] = "docx"
            result["is_image"] = False
            result["image_path"] = None
            return result

        elif ext in IMAGE_EXTENSIONS:
            result = self.parse_image(path)
            result["page_image_paths"] = [str(path)]  # Image itself is the "page"
            result["kind"] = "image"
            result["is_image"] = True
            result["image_path"] = str(path)
            return result

        elif ext in TEXT_EXTENSIONS:
            result = self.parse_text(path)
            result["page_image_paths"] = []
            result["kind"] = "text"
            result["is_image"] = False
            result["image_path"] = None
            return result

        else:
            # Try as text, fallback to empty
            try:
                result = self.parse_text(path)
                result["page_image_paths"] = []
                result["kind"] = "text"
                result["is_image"] = False
                result["image_path"] = None
                return result
            except Exception:
                return {
                    "text": f"[Binary file: {path.name}]",
                    "kind": "binary",
                    "pages": 1,
                    "page_image_paths": [],
                    "truncated": False,
                    "is_image": False,
                    "image_path": None,
                }

    def parse_pdf(self, path: Path) -> dict:
        """Extract text from a PDF via PyMuPDF."""
        import fitz

        doc = fitz.open(str(path))
        parts = []
        for page in doc:
            try:
                parts.append(page.get_text() or "")
            except Exception as e:
                logger.warning("Failed to extract PDF page: %s", e)
        page_count = doc.page_count
        doc.close()

        text = "\n".join(parts).strip()
        return {
            "text": text[:MAX_CHARS],
            "pages": page_count,
            "truncated": len(text) > MAX_CHARS,
        }

    def render_pdf_pages(self, path: Path, output_dir: Path) -> list[str]:
        """
        Render each PDF page to a PNG image.

        Args:
            path: Source PDF path.
            output_dir: Directory to write page_N.png files.

        Returns:
            list[str]: Paths to rendered PNGs in page order.
        """
        import fitz

        output_dir.mkdir(parents=True, exist_ok=True)
        doc = fitz.open(str(path))
        paths = []
        zoom = RENDER_DPI / 72
        matrix = fitz.Matrix(zoom, zoom)

        page_count = min(doc.page_count, MAX_PDF_PAGES_TO_RENDER)
        for i in range(page_count):
            page = doc[i]
            pix = page.get_pixmap(matrix=matrix)
            out_path = output_dir / f"page_{i + 1}.png"
            pix.save(str(out_path))
            paths.append(str(out_path))

        if doc.page_count > MAX_PDF_PAGES_TO_RENDER:
            logger.warning(
                "PDF has %d pages, only rendered first %d.",
                doc.page_count, MAX_PDF_PAGES_TO_RENDER,
            )
        doc.close()
        return paths

    def parse_docx(self, path: Path) -> dict:
        """Extract text from a Word (.docx) document including tables."""
        from docx import Document

        doc = Document(str(path))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(
                    c.text.strip() for c in row.cells if c.text.strip()
                )
                if row_text:
                    parts.append(row_text)

        text = "\n".join(parts).strip()
        return {
            "text": text[:MAX_CHARS],
            "pages": 1,
            "paragraphs": len(parts),
            "truncated": len(text) > MAX_CHARS,
        }

    def parse_image(self, path: Path) -> dict:
        """
        Handle image files — preserve original, OCR for search.

        The original image is ALWAYS preserved as-is.
        OCR text is extracted only for search indexing.
        If OCR fails, empty text is used (image still saved).

        Args:
            path: Image file path.

        Returns:
            dict: text (OCR for search), pages=1, image preserved.
        """
        ocr_text = ""

        try:
            import pytesseract
            from PIL import Image

            image = Image.open(path)

            # Convert to RGB if needed (RGBA/palette images)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")

            ocr_text = pytesseract.image_to_string(image, lang="eng+ben").strip()

            # If OCR returns garbage (non-printable chars > 50%), clear it
            if ocr_text:
                printable_ratio = sum(
                    1 for c in ocr_text
                    if c.isprintable() or c in "\n\t"
                ) / len(ocr_text)
                if printable_ratio < 0.5:
                    logger.info("OCR result looks like garbage, clearing")
                    ocr_text = f"[Image file: {path.name}]"

        except ImportError:
            logger.warning("pytesseract not available, no OCR for image")
            ocr_text = f"[Image file: {path.name}]"
        except Exception as e:
            logger.warning("OCR failed for %s: %s", path.name, e)
            ocr_text = f"[Image file: {path.name}]"

        return {
            "text": ocr_text[:MAX_CHARS] if ocr_text else f"[Image: {path.name}]",
            "pages": 1,
            "truncated": False,
        }

    def parse_text(self, path: Path) -> dict:
        """Read plain text or code files directly."""
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise RuntimeError(f"Cannot read text file: {e}") from e

        return {
            "text": text[:MAX_CHARS],
            "pages": 1,
            "truncated": len(text) > MAX_CHARS,
        }


# ── Singleton instance ────────────────────────────────────────────────────────
document_parser = DocumentParser()