from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from redis.exceptions import RedisError
from rq.exceptions import NoSuchJobError
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.auth import Principal, require_roles
from app.core.authorization import get_accessible_job
from app.core.config import UPLOAD_DIR
from app.core.jobs import enqueue_analysis, get_analysis_queue
from app.db.database import get_db
from app.models.job import AnalysisJob
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


def _job_status(job: AnalysisJob) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "attempts": job.attempts,
        "error": job.error,
    }


def _uploaded_paths(job_id: str) -> dict[str, str | None]:
    job_dir = UPLOAD_DIR / job_id
    paths = {
        "pdf_path": job_dir / "government_journal.pdf",
        "xlsx_path": job_dir / "client_trademarks.xlsx",
        "client_pdf_path": job_dir / "client_trademarks.pdf",
        "left_xlsx_path": job_dir / "left_trademarks.xlsx",
        "right_xlsx_path": job_dir / "right_trademarks.xlsx",
    }
    return {
        name: str(path) if path.exists() else None
        for name, path in paths.items()
    }


@router.post("/{job_id}")
async def analyze_job(
    job_id: str,
    principal: Principal = Depends(require_roles("analyst", "admin")),
    db: Session = Depends(get_db),
):
    job = get_accessible_job(job_id, principal, db)
    paths = _uploaded_paths(job_id)
    if not (
        paths["pdf_path"] or paths["left_xlsx_path"]
    ) or not (
        paths["xlsx_path"] or paths["client_pdf_path"] or paths["right_xlsx_path"]
    ):
        raise HTTPException(status_code=404, detail="Uploaded files not found.")
    if job.status in {"QUEUED", "PROCESSING"}:
        return _job_status(job)

    previous_status = job.status
    job.status = "QUEUED"
    job.progress = 0
    job.message = "Analysis queued."
    job.error = None
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    try:
        task_id = enqueue_analysis(job_id)
    except RedisError as error:
        job.status = previous_status
        job.message = "Analysis queue is unavailable."
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Analysis queue is unavailable.",
        ) from error

    record_audit_event(
        db, principal, "analysis.queued", job_id, {"task_id": task_id}
    )
    db.commit()
    return _job_status(job)


@router.get("/{job_id}/status")
async def get_analysis_status(
    job_id: str,
    principal: Principal = Depends(require_roles("analyst", "admin", "reviewer")),
    db: Session = Depends(get_db),
):
    job = get_accessible_job(job_id, principal, db)
    return _job_status(job)


@router.post("/{job_id}/retry")
async def retry_analysis(
    job_id: str,
    principal: Principal = Depends(require_roles("analyst", "admin")),
    db: Session = Depends(get_db),
):
    job = get_accessible_job(job_id, principal, db)
    if job.status != "FAILED":
        raise HTTPException(
            status_code=409,
            detail="Only failed analyses can be retried.",
        )
    previous_status = job.status
    job.status = "QUEUED"
    job.progress = 0
    job.message = "Analysis retry queued."
    job.error = None
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    try:
        task_id = enqueue_analysis(job_id)
    except RedisError as error:
        job.status = previous_status
        job.message = "Analysis queue is unavailable."
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Analysis queue is unavailable.",
        ) from error
    record_audit_event(
        db, principal, "analysis.retry_queued", job_id, {"task_id": task_id}
    )
    db.commit()
    return _job_status(job)
