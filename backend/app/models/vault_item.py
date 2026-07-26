"""
AURA Backend — File Vault Item Model.

Module: app.models.vault_item
Purpose: Permanent storage record for an original file the user
         explicitly named and saved — distinct from Tier 2's
         KnowledgeItem (which stores CLASSIFIED/SUMMARIZED knowledge).
         FileVaultItem preserves the exact original file, full
         unsummarized text, and rendered page images so the user can
         later ask for exact details or view specific pages, from any
         conversation.
"""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDMixin


class FileVaultItem(Base, UUIDMixin, TimestampMixin):
    """A permanently saved, named file with full text and page images."""

    __tablename__ = "file_vault_items"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf | docx | image
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    page_image_paths: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="en")

    def __repr__(self) -> str:
        return f"<FileVaultItem name={self.name!r} kind={self.kind}>"