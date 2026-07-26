"""
AURA Backend — Document Parser.

Module: app.ingestion.document_parser
Purpose: Extracts plain text AND renders page images from PDF, DOCX,
         and image files. Uses PyMuPDF (fitz) for PDFs — one library
         handles both text extraction and page-to-image rendering,
         needed for the File Vault's "show me page N" feature.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_CHARS = 100_000
MAX_PDF_PAGES_TO_RENDER = 30  # safety cap — RAM/disk aware on 8GB machine
RENDER_DPI = 150


class DocumentParser:
    """
    Extracts text and renders page images from PDF/DOCX/image files.

    Methods:
        parse_pdf: Extract text from a PDF.
        render_pdf_pages: Render each PDF page to a PNG.
        parse_docx: Extract text from a Word document.
        parse_image: OCR text from an image.
    """

    def parse_pdf(self, path: Path) -> dict:
        """Extract text from a PDF via PyMuPDF."""
        import fitz  # PyMuPDF

        doc = fitz.open(str(path))
        parts = []
        for page in doc:
            try:
                parts.append(page.get_text() or "")
            except Exception as e:
                logger.warning("Failed to extract a PDF page: %s", e)
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
            path: Path to the source PDF.
            output_dir: Directory to write page_N.png files into.

        Returns:
            list[str]: Paths to the rendered PNGs, in page order.
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
        """Extract text from a Word (.docx) document, including tables."""
        from docx import Document

        doc = Document(str(path))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                if row_text:
                    parts.append(row_text)

        text = "\n".join(parts).strip()
        return {
            "text": text[:MAX_CHARS],
            "paragraphs": len(parts),
            "truncated": len(text) > MAX_CHARS,
        }

    def parse_image(self, path: Path) -> dict:
        """OCR text from an image."""
        try:
            import pytesseract
            from PIL import Image
        except ImportError as e:
            raise RuntimeError(
                "OCR dependencies missing. Run: pip install pytesseract pillow, "
                "and install Tesseract OCR."
            ) from e

        try:
            image = Image.open(path)
            text = pytesseract.image_to_string(image)
        except Exception as e:
            raise RuntimeError(f"OCR failed: {e}") from e

        text = text.strip()
        return {"text": text[:MAX_CHARS], "truncated": len(text) > MAX_CHARS}


# ── Singleton instance ────────────────────────────────────────────────────────
document_parser = DocumentParser()