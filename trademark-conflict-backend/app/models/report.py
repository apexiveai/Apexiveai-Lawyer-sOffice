from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String

from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

class Report(Base):

    __tablename__ = "reports"

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

    filename: Mapped[str] = mapped_column(

        String(255),

        nullable=False,

    )

    report_type: Mapped[str] = mapped_column(

        String(50),

        nullable=False,

        default="CONFLICT_INVESTIGATION",

    )

    created_at: Mapped[datetime] = mapped_column(

        DateTime(timezone=True),

        nullable=False,

        default=lambda: datetime.now(timezone.utc),

    )