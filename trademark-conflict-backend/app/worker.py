from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import Session
from rq import get_current_job

from app.core.config import UPLOAD_DIR
from app.db.database import SessionLocal
from app.models.job import AnalysisJob
from app.services.analysis_service import AnalysisService
from app.services.jurisdiction import (
    CitationMetadata,
    GoodsServices,
    TrademarkRecord,
    compare_records,
)


def _json_safe(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            field.name: _json_safe(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def _goods_services_assessment(job: AnalysisJob) -> dict[str, object]:
    left_classes = json.loads(job.left_nice_classes or "[]")
    right_classes = json.loads(job.right_nice_classes or "[]")
    if not (
        job.left_jurisdiction
        and job.right_jurisdiction
        and left_classes
        and right_classes
        and job.left_goods_services.strip()
        and job.right_goods_services.strip()
    ):
        return {
            "disposition": "NEEDS_REVIEW",
            "score": 0.0,
            "review_reasons": [
                "Provide both jurisdictions, Nice classes, and goods/services "
                "descriptions to assess scope overlap."
            ],
        }

    citation = CitationMetadata(
        source_name=job.source_name,
        source_url=job.source_url,
        retrieved_at=job.source_retrieved_at,
        source_record_id=job.source_record_id,
    )
    left = TrademarkRecord(
        jurisdiction=job.left_jurisdiction,
        goods_services=tuple(
            GoodsServices(nice_class=nice_class, description=job.left_goods_services)
            for nice_class in left_classes
        ),
        citation=citation,
    )
    right = TrademarkRecord(
        jurisdiction=job.right_jurisdiction,
        goods_services=tuple(
            GoodsServices(nice_class=nice_class, description=job.right_goods_services)
            for nice_class in right_classes
        ),
        citation=citation,
    )
    result = _json_safe(compare_records(left, right))
    if not isinstance(result, dict):
        raise TypeError("Goods/services comparison did not produce an object.")
    return result


def _update_job(
    db: Session,
    job: AnalysisJob,
    *,
    status: str,
    progress: int,
    message: str,
    error: str | None = None,
) -> None:
    job.status = status
    job.progress = progress
    job.message = message
    job.error = error
    job.updated_at = datetime.now(timezone.utc)
    db.commit()


def process_analysis_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.execute(
            select(AnalysisJob).where(AnalysisJob.job_id == job_id)
        ).scalar_one_or_none()
        if job is None:
            raise LookupError(f"Analysis job {job_id} was not found.")

        job.attempts += 1
        _update_job(
            db, job, status="PROCESSING", progress=1,
            message="Analysis worker started.",
        )
        job_dir = UPLOAD_DIR / job_id
        pdf_path = job_dir / "government_journal.pdf"
        xlsx_path = job_dir / "client_trademarks.xlsx"
        client_pdf_path = job_dir / "client_trademarks.pdf"
        left_xlsx_path = job_dir / "left_trademarks.xlsx"
        right_xlsx_path = job_dir / "right_trademarks.xlsx"
        service = AnalysisService(
            pdf_path=str(pdf_path),
            xlsx_path=str(xlsx_path) if xlsx_path.exists() else None,
            client_pdf_path=(
                str(client_pdf_path) if client_pdf_path.exists() else None
            ),
            left_xlsx_path=(
                str(left_xlsx_path) if left_xlsx_path.exists() else None
            ),
            right_xlsx_path=(
                str(right_xlsx_path) if right_xlsx_path.exists() else None
            ),
            job_id=job_id,
            progress_callback=lambda progress, message: _update_job(
                db, job, status="PROCESSING", progress=progress,
                message=message,
            ),
            analysis_metadata={
                "jurisdiction": job.jurisdiction,
                "nice_classes": json.loads(job.nice_classes),
                "jurisdiction_scope": {
                    "left": job.left_jurisdiction,
                    "right": job.right_jurisdiction,
                },
                "nice_class_scope": {
                    "left": json.loads(job.left_nice_classes or "[]"),
                    "right": json.loads(job.right_nice_classes or "[]"),
                },
                "goods_services_assessment": _goods_services_assessment(job),
                "source_citations": (
                    [
                        {
                            "source_name": job.source_name,
                            "source_url": job.source_url,
                            "retrieved_at": job.source_retrieved_at.isoformat()
                            if job.source_retrieved_at
                            else None,
                            "source_record_id": job.source_record_id,
                        }
                    ]
                    if job.source_name
                    else []
                ),
            },
        )
        service.run()
        _update_job(
            db, job, status="COMPLETED", progress=100,
            message="Analysis completed successfully.",
        )
    except Exception as error:
        db.rollback()
        job = db.execute(
            select(AnalysisJob).where(AnalysisJob.job_id == job_id)
        ).scalar_one_or_none()
        if job is not None:
            rq_job = get_current_job()
            will_retry = bool(
                rq_job is not None
                and getattr(rq_job, "retries_left", 0) > 0
            )
            _update_job(
                db,
                job,
                status="QUEUED" if will_retry else "FAILED",
                progress=job.progress,
                message=(
                    "Analysis failed; retry scheduled."
                    if will_retry
                    else "Analysis failed."
                ),
                error=f"{type(error).__name__}: {error}",
            )
        raise
    finally:
        db.close()
