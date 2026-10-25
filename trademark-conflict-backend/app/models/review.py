from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint

from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

class Review(Base):

    __tablename__ = "reviews"

    __table_args__ = (

        UniqueConstraint(

            "job_id",

            "conflict_id",

            name="uq_review_job_conflict",

        ),

    )

    id: Mapped[int] = mapped_column(

        Integer,

        primary_key=True,

        autoincrement=True,

    )

    job_id: Mapped[str] = mapped_column(

        String(64),

        nullable=False,

        index=True,

    )

    conflict_id: Mapped[str] = mapped_column(

        String(255),

        nullable=False,

    )

    status: Mapped[str] = mapped_column(

        String(20),

        nullable=False,

        default="PENDING",

    )

    comment: Mapped[str] = mapped_column(

        Text,

        nullable=False,

        default="",

    )

    reviewer: Mapped[str] = mapped_column(

        String(255),

        nullable=False,

        default="Admin",

    )

    reviewed_at: Mapped[datetime] = mapped_column(

        DateTime(timezone=True),

        nullable=False,

        default=lambda: datetime.now(timezone.utc),

        onupdate=lambda: datetime.now(timezone.utc),

    )

    created_at: Mapped[datetime] = mapped_column(

        DateTime(timezone=True),

        nullable=False,

        default=lambda: datetime.now(timezone.utc),

    )