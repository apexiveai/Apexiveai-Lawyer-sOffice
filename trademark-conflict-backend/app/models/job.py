from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UPLOADED", index=True
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(32), nullable=True)
    nice_classes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    left_jurisdiction: Mapped[str | None] = mapped_column(String(32), nullable=True)
    right_jurisdiction: Mapped[str | None] = mapped_column(String(32), nullable=True)
    left_nice_classes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    right_nice_classes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    left_goods_services: Mapped[str] = mapped_column(Text, nullable=False, default="")
    right_goods_services: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_record_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_retrieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retention_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
