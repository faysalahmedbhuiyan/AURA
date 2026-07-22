"""
AURA Backend — Goal Manager Models.

Module: app.models.goal
Purpose: Breaks large goals into trackable milestones and tasks (Phase 16).
"""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDMixin


class Goal(Base, UUIDMixin, TimestampMixin):
    """A high-level goal, broken into milestones."""

    __tablename__ = "goals"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started")

    def __repr__(self) -> str:
        return f"<Goal title={self.title!r} status={self.status}>"


class Milestone(Base, UUIDMixin, TimestampMixin):
    """A milestone within a goal, containing tasks."""

    __tablename__ = "milestones"

    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started")

    def __repr__(self) -> str:
        return f"<Milestone title={self.title!r} goal_id={self.goal_id}>"


class Task(Base, UUIDMixin, TimestampMixin):
    """A single task within a milestone. May depend on another task."""

    __tablename__ = "tasks"

    milestone_id: Mapped[str] = mapped_column(ForeignKey("milestones.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started")
    depends_on_task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Task title={self.title!r} status={self.status}>"