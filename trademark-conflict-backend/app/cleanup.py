from __future__ import annotations

import os
import re
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import and_, or_, select

from app.core.config import EVIDENCE_DIR, EXTRACTED_DIR, RESULTS_DIR, UPLOAD_DIR
from app.db.database import SessionLocal
from app.models.audit_event import AuditEvent
from app.models.job import AnalysisJob
from app.models.report import Report
from app.models.review import Review

_JOB_ID = re.compile(r"^[a-f0-9]{32}$")


def _remove_job_directory(root: Path, job_id: str) -> None:
    if not _JOB_ID.fullmatch(job_id):
        raise ValueError(f"Refusing to clean invalid job id: {job_id}")
    directory = (root / job_id).resolve()
    if not directory.is_relative_to(root.resolve()):
        raise ValueError(f"Refusing to clean path outside {root}")
    if directory.exists():
        shutil.rmtree(directory)


def cleanup_expired_jobs(now: datetime | None = None) -> int:
    cutoff = now or datetime.now(timezone.utc)
    retention_days = int(os.getenv("JOB_RETENTION_DAYS", "90"))
    if retention_days <= 0:
        raise ValueError("JOB_RETENTION_DAYS must be a positive integer.")
    legacy_cutoff = cutoff - timedelta(days=retention_days)
    with SessionLocal() as db:
        expired_jobs = db.execute(
            select(AnalysisJob).where(
                or_(
                    AnalysisJob.retention_until <= cutoff,
                    and_(
                        AnalysisJob.retention_until.is_(None),
                        AnalysisJob.created_at <= legacy_cutoff,
                    ),
                )
            )
        ).scalars().all()
        for job in expired_jobs:
            for root in (UPLOAD_DIR, EXTRACTED_DIR, EVIDENCE_DIR, RESULTS_DIR):
                _remove_job_directory(root, job.job_id)

            db.query(Review).filter(Review.job_id == job.job_id).delete()
            db.query(Report).filter(Report.job_id == job.job_id).delete()
            db.add(
                AuditEvent(
                    tenant_id=job.tenant_id,
                    actor_id="system-retention",
                    action="job.retention_deleted",
                    resource_id=job.job_id,
                    details="{}",
                    created_at=cutoff,
                )
            )
            db.delete(job)
        db.commit()
        return len(expired_jobs)


def main() -> None:
    interval = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "86400"))
    while True:
        deleted = cleanup_expired_jobs()
        print(f"Expired analysis jobs deleted: {deleted}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
