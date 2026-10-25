from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.auth import Principal, require_roles
from app.core.config import MAX_FILE_SIZE_MB, UPLOAD_DIR
from app.db.database import get_db
from app.models.job import AnalysisJob

router = APIRouter(prefix="/api/upload", tags=["Upload"])


def validate_extension(filename: str, expected: str) -> None:
    extension = Path(filename).suffix.lower()
    if extension != expected:
        raise HTTPException(
            status_code=400,
            detail=f"Expected {expected} file but received {extension}",
        )


async def save_upload(upload: UploadFile, destination: Path) -> Path:
    maximum = MAX_FILE_SIZE_MB * 1024 * 1024
    total = 0
    with destination.open("wb") as file:
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > maximum:
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds {MAX_FILE_SIZE_MB} MB",
                )
            file.write(chunk)
    return destination


def _parse_nice_classes(value: str) -> list[int]:
    try:
        classes = sorted(
            {int(item.strip()) for item in value.split(",") if item.strip()}
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="Nice classes must be comma-separated integers.",
        ) from error
    if any(item < 1 or item > 45 for item in classes):
        raise HTTPException(
            status_code=400,
            detail="Nice classes must be integers from 1 to 45.",
        )
    return classes


@router.post("/two-files")
async def upload_two_files(
    pdf: UploadFile | None = File(None),
    xlsx: UploadFile | None = File(None),
    client_pdf: UploadFile | None = File(None),
    left_xlsx: UploadFile | None = File(None),
    right_xlsx: UploadFile | None = File(None),
    jurisdiction: str | None = Form(None),
    nice_classes: str = Form(""),
    left_jurisdiction: str | None = Form(None),
    right_jurisdiction: str | None = Form(None),
    left_nice_classes: str = Form(""),
    right_nice_classes: str = Form(""),
    left_goods_services: str = Form(""),
    right_goods_services: str = Form(""),
    source_name: str | None = Form(None),
    source_url: str | None = Form(None),
    source_record_id: str | None = Form(None),
    source_retrieved_at: str | None = Form(None),
    principal: Principal = Depends(require_roles("analyst", "admin")),
    db: Session = Depends(get_db),
):
    if not pdf and not left_xlsx:
        raise HTTPException(status_code=400, detail="PDF filename missing")
    if not (xlsx or client_pdf or right_xlsx):
        raise HTTPException(
            status_code=400,
            detail="Client XLSX or PDF filename missing",
        )

    if pdf and pdf.filename:
        validate_extension(pdf.filename, ".pdf")
    if left_xlsx or right_xlsx:
        if not left_xlsx or not right_xlsx:
            raise HTTPException(
                status_code=400,
                detail="Both XLSX files are required for XLSX comparison",
            )
        validate_extension(left_xlsx.filename or "", ".xlsx")
        validate_extension(right_xlsx.filename or "", ".xlsx")
    if xlsx:
        validate_extension(xlsx.filename or "", ".xlsx")
    if client_pdf:
        validate_extension(client_pdf.filename or "", ".pdf")

    left_jurisdiction = left_jurisdiction or jurisdiction
    right_jurisdiction = right_jurisdiction or jurisdiction
    for jurisdiction_code in (left_jurisdiction, right_jurisdiction):
        if jurisdiction_code and not re.fullmatch(
            r"[A-Za-z0-9-]{2,16}", jurisdiction_code
        ):
            raise HTTPException(
                status_code=400,
                detail="Jurisdiction must be a 2-16 character code.",
            )
    class_values = _parse_nice_classes(nice_classes)
    left_class_values = _parse_nice_classes(left_nice_classes) or class_values
    right_class_values = _parse_nice_classes(right_nice_classes) or class_values
    if source_url:
        parsed_source_url = urlparse(source_url)
        if parsed_source_url.scheme not in {"http", "https"} or not parsed_source_url.netloc:
            raise HTTPException(
                status_code=400,
                detail="Source URL must be an absolute HTTP or HTTPS URL.",
            )
    if any((source_url, source_record_id, source_retrieved_at)) and not source_name:
        raise HTTPException(
            status_code=400,
            detail="Source name is required when source citation details are provided.",
        )
    try:
        retrieved_at = (
            datetime.fromisoformat(source_retrieved_at.replace("Z", "+00:00"))
            if source_retrieved_at
            else None
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="Source retrieval time must be ISO 8601.",
        ) from error
    if retrieved_at and retrieved_at.tzinfo is None:
        raise HTTPException(
            status_code=400,
            detail="Source retrieval time must include a timezone.",
        )
    job_id = uuid.uuid4().hex
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=False)

    pdf_path = job_dir / "government_journal.pdf"
    xlsx_path = job_dir / "client_trademarks.xlsx"
    client_pdf_path = job_dir / "client_trademarks.pdf"
    left_xlsx_path = job_dir / "left_trademarks.xlsx"
    right_xlsx_path = job_dir / "right_trademarks.xlsx"

    try:
        if pdf and pdf.filename:
            await save_upload(pdf, pdf_path)
        if left_xlsx and right_xlsx:
            await save_upload(left_xlsx, left_xlsx_path)
            await save_upload(right_xlsx, right_xlsx_path)
        if xlsx:
            await save_upload(xlsx, xlsx_path)
        if client_pdf:
            await save_upload(client_pdf, client_pdf_path)

        retention_days = int(os.getenv("JOB_RETENTION_DAYS", "90"))
        job = AnalysisJob(
            job_id=job_id,
            tenant_id=principal.tenant_id,
            owner_id=principal.subject,
            status="UPLOADED",
            progress=0,
            message="Files uploaded.",
            jurisdiction=jurisdiction.upper() if jurisdiction else None,
            nice_classes=json.dumps(class_values),
            left_jurisdiction=(
                left_jurisdiction.upper() if left_jurisdiction else None
            ),
            right_jurisdiction=(
                right_jurisdiction.upper() if right_jurisdiction else None
            ),
            left_nice_classes=json.dumps(left_class_values),
            right_nice_classes=json.dumps(right_class_values),
            left_goods_services=left_goods_services.strip(),
            right_goods_services=right_goods_services.strip(),
            source_name=source_name,
            source_url=source_url,
            source_record_id=source_record_id,
            source_retrieved_at=retrieved_at,
            retention_until=datetime.now(timezone.utc)
            + timedelta(days=retention_days),
        )
        db.add(job)
        record_audit_event(
            db,
            principal,
            "job.uploaded",
            job_id,
            {"jurisdiction": job.jurisdiction, "nice_classes": class_values},
        )
        db.commit()
    except Exception:
        db.rollback()
        shutil.rmtree(job_dir)
        raise

    return {
        "job_id": job_id,
        "pdf": str(pdf_path) if pdf_path.exists() else None,
        "xlsx": str(xlsx_path) if xlsx_path.exists() else None,
        "client_pdf": str(client_pdf_path) if client_pdf_path.exists() else None,
        "left_xlsx": str(left_xlsx_path) if left_xlsx_path.exists() else None,
        "right_xlsx": str(right_xlsx_path) if right_xlsx_path.exists() else None,
        "status": "UPLOADED",
        "jurisdiction": jurisdiction.upper() if jurisdiction else None,
        "nice_classes": class_values,
    }
