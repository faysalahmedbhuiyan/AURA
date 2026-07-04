"""
AURA Backend — Database Base Model.

Module: app.database.base
Purpose: Provides DeclarativeBase and TimestampMixin for all ORM models.
         Every table inherits from Base and TimestampMixin to get
         automatic id, created_at, and updated_at fields.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    SQLAlchemy DeclarativeBase for all AURA models.

    All ORM models must inherit from this class.
    """
    pass


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at columns to any model.

    Both fields are timezone-aware UTC timestamps.
    updated_at is automatically refreshed on every update.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UUIDMixin:
    """
    Mixin that adds a UUID primary key to any model.

    Uses string representation of UUID4 for SQLite compatibility.
    """

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )