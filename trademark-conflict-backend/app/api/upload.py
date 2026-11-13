
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
from app.core.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, UPLOAD_DIR
from app.db.database import get_db
from app.models.job import AnalysisJob


router = APIRouter(
    prefix="/api/upload",
    tags=["Upload"],
)

CHUNK_SIZE = 1024 * 1024
MAX_FILENAME_LENGTH = 255
MAX_SOURCE_NAME_LENGTH = 255
MAX_SOURCE_RECORD_ID_LENGTH = 255


# ============================================================
# VALIDATION
# ============================================================

def validate_extension(filename: str, expected: str) -> None:
    extension = Path(filename).suffix.lower()

    if extension != expected:
        raise HTTPException(
            status_code=400,
            detail=f"Expected {expected} file but received {extension or '(none)'}",
        )


def validate_supported_upload(filename: str) -> str:
    if not filename or len(filename) > MAX_FILENAME_LENGTH:
        raise HTTPException(
            status_code=400,
            detail="Invalid upload filename.",
        )

    extension = Path(filename).suffix.lower()

    allowed_extensions = {
        str(item).lower()
        for item in ALLOWED_EXTENSIONS
    }

    if extension not in allowed_extensions:
        supported = ", ".join(sorted(allowed_extensions))

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type {extension or '(none)'}. "
                f"Supported types: {supported}"
            ),
        )

    return extension


def _validate_upload_pair(
    *,
    pdf: UploadFile | None,
    xlsx: UploadFile | None,
    client_pdf: UploadFile | None,
    left_xlsx: UploadFile | None,
    right_xlsx: UploadFile | None,
) -> None:

    has_xlsx_pair = (
        left_xlsx is not None
        or right_xlsx is not None
    )

    # XLSX + XLSX comparison
    if has_xlsx_pair:

        if (
            left_xlsx is None
            or right_xlsx is None
            or pdf is not None
            or xlsx is not None
            or client_pdf is not None
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Upload exactly two XLSX files "
                    "for XLSX comparison."
                ),
            )

        validate_extension(
            left_xlsx.filename or "",
            ".xlsx",
        )

        validate_extension(
            right_xlsx.filename or "",
            ".xlsx",
        )

        return

    # Government PDF + Client XLSX/PDF
    if pdf is None or ((xlsx is None) == (client_pdf is None)):
        raise HTTPException(
            status_code=400,
            detail=(
                "Upload one PDF and one XLSX "
                "or one PDF and another PDF."
            ),
        )

    validate_extension(
        pdf.filename or "",
        ".pdf",
    )

    if xlsx is not None:
        validate_extension(
            xlsx.filename or "",
            ".xlsx",
        )

    if client_pdf is not None:
        validate_extension(
            client_pdf.filename or "",
            ".pdf",
        )


# ============================================================
# FILE STORAGE
# ============================================================

async def save_upload(
    upload: UploadFile,
    destination: Path,
) -> Path:

    maximum = MAX_FILE_SIZE_MB * 1024 * 1024
    total = 0

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        with destination.open("wb") as output_file:

            while True:

                chunk = await upload.read(CHUNK_SIZE)

                if not chunk:
                    break

                total += len(chunk)

                if total > maximum:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"File exceeds "
                            f"{MAX_FILE_SIZE_MB} MB"
                        ),
                    )

                output_file.write(chunk)

        if total == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        return destination

    except Exception:
        destination.unlink(missing_ok=True)
        raise

    finally:
        await upload.close()


# ============================================================
# METADATA VALIDATION
# ============================================================

def _parse_nice_classes(value: str) -> list[int]:

    try:
        classes = sorted(
            {
                int(item.strip())
                for item in value.split(",")
                if item.strip()
            }
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=(
                "Nice classes must be "
                "comma-separated integers."
            ),
        ) from error

    if any(item < 1 or item > 45 for item in classes):
        raise HTTPException(
            status_code=400,
            detail=(
                "Nice classes must be "
                "integers from 1 to 45."
            ),
        )

    return classes


def _validate_jurisdiction(value: str | None) -> str | None:

    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    if not re.fullmatch(
        r"[A-Za-z0-9-]{2,16}",
        value,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Jurisdiction must be "
                "a 2-16 character code."
            ),
        )

    return value.upper()


def _parse_source_retrieved_at(
    value: str | None,
) -> datetime | None:

    if not value:
        return None

    try:
        normalized = value.strip()

        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"

        retrieved_at = datetime.fromisoformat(normalized)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=(
                "Source retrieval time must be ISO 8601."
            ),
        ) from error

    if retrieved_at.tzinfo is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Source retrieval time must include a timezone."
            ),
        )

    return retrieved_at


def _validate_source_metadata(
    *,
    source_name: str | None,
    source_url: str | None,
    source_record_id: str | None,
    source_retrieved_at: str | None,
) -> datetime | None:

    if source_name is not None:
        source_name = source_name.strip()

        if len(source_name) > MAX_SOURCE_NAME_LENGTH:
            raise HTTPException(
                status_code=400,
                detail="Source name is too long.",
            )

    if source_record_id is not None:
        source_record_id = source_record_id.strip()

        if len(source_record_id) > MAX_SOURCE_RECORD_ID_LENGTH:
            raise HTTPException(
                status_code=400,
                detail="Source record ID is too long.",
            )

    if source_url:

        parsed = urlparse(source_url.strip())

        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Source URL must be an absolute "
                    "HTTP or HTTPS URL."
                ),
            )

    if any(
        (
            source_url,
            source_record_id,
            source_retrieved_at,
        )
    ) and not source_name:

        raise HTTPException(
            status_code=400,
            detail=(
                "Source name is required when "
                "source citation details are provided."
            ),
        )

    return _parse_source_retrieved_at(
        source_retrieved_at,
    )


def _get_retention_days() -> int:

    try:
        retention_days = int(
            os.getenv("JOB_RETENTION_DAYS", "90")
        )

    except ValueError as error:
        raise HTTPException(
            status_code=500,
            detail="Invalid JOB_RETENTION_DAYS configuration.",
        ) from error

    if retention_days < 1:
        raise HTTPException(
            status_code=500,
            detail="JOB_RETENTION_DAYS must be at least 1.",
        )

    return retention_days


# ============================================================
# UPLOAD ENDPOINT
# ============================================================

@router.post("/two-files")
async def upload_two_files(

    # Generic upload
    left_file: UploadFile | None = File(None),
    right_file: UploadFile | None = File(None),

    # Legacy upload
    pdf: UploadFile | None = File(None),
    xlsx: UploadFile | None = File(None),
    client_pdf: UploadFile | None = File(None),
    left_xlsx: UploadFile | None = File(None),
    right_xlsx: UploadFile | None = File(None),

    # General metadata
    jurisdiction: str | None = Form(None),
    nice_classes: str = Form(""),

    # Side-specific metadata
    left_jurisdiction: str | None = Form(None),
    right_jurisdiction: str | None = Form(None),

    left_nice_classes: str = Form(""),
    right_nice_classes: str = Form(""),

    left_goods_services: str = Form(""),
    right_goods_services: str = Form(""),

    # Source citation
    source_name: str | None = Form(None),
    source_url: str | None = Form(None),
    source_record_id: str | None = Form(None),
    source_retrieved_at: str | None = Form(None),

    # Authentication and database
    principal: Principal = Depends(
        require_roles("analyst", "admin")
    ),

    db: Session = Depends(get_db),
):

    # --------------------------------------------------------
    # 1. Determine upload mode
    # --------------------------------------------------------

    generic_upload = (
        left_file is not None
        or right_file is not None
    )

    legacy_uploads = (
        pdf,
        xlsx,
        client_pdf,
        left_xlsx,
        right_xlsx,
    )

    left_extension = ""
    right_extension = ""

    if generic_upload:

        if left_file is None or right_file is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Both left and right files are required."
                ),
            )

        if any(legacy_uploads):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Use either left/right files "
                    "or legacy upload fields, not both."
                ),
            )

        if not left_file.filename or not right_file.filename:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Both uploaded files must have a filename."
                ),
            )

        left_extension = validate_supported_upload(
            left_file.filename,
        )

        right_extension = validate_supported_upload(
            right_file.filename,
        )

    else:

        _validate_upload_pair(
            pdf=pdf,
            xlsx=xlsx,
            client_pdf=client_pdf,
            left_xlsx=left_xlsx,
            right_xlsx=right_xlsx,
        )

    # --------------------------------------------------------
    # 2. Validate metadata
    # --------------------------------------------------------

    jurisdiction = (
        jurisdiction.strip()
        if jurisdiction
        else None
    )

    left_jurisdiction = (
        left_jurisdiction
        or jurisdiction
    )

    right_jurisdiction = (
        right_jurisdiction
        or jurisdiction
    )

    left_jurisdiction = _validate_jurisdiction(
        left_jurisdiction,
    )

    right_jurisdiction = _validate_jurisdiction(
        right_jurisdiction,
    )

    jurisdiction = _validate_jurisdiction(
        jurisdiction,
    )

    class_values = _parse_nice_classes(
        nice_classes,
    )

    left_class_values = (
        _parse_nice_classes(left_nice_classes)
        or class_values
    )

    right_class_values = (
        _parse_nice_classes(right_nice_classes)
        or class_values
    )

    source_name = (
        source_name.strip()
        if source_name
        else None
    )

    source_url = (
        source_url.strip()
        if source_url
        else None
    )

    source_record_id = (
        source_record_id.strip()
        if source_record_id
        else None
    )

    retrieved_at = _validate_source_metadata(
        source_name=source_name,
        source_url=source_url,
        source_record_id=source_record_id,
        source_retrieved_at=source_retrieved_at,
    )

    retention_days = _get_retention_days()

    # --------------------------------------------------------
    # 3. Create isolated job directory
    # --------------------------------------------------------

    job_id = uuid.uuid4().hex

    job_dir = UPLOAD_DIR / job_id

    try:
        job_dir.mkdir(
            parents=True,
            exist_ok=False,
        )

    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to create upload directory.",
        ) from error

    # --------------------------------------------------------
    # 4. Define storage paths
    # --------------------------------------------------------

    pdf_path = job_dir / "government_journal.pdf"

    xlsx_path = job_dir / "client_trademarks.xlsx"

    client_pdf_path = job_dir / "client_trademarks.pdf"

    left_xlsx_path = job_dir / "left_trademarks.xlsx"

    right_xlsx_path = job_dir / "right_trademarks.xlsx"

    left_document_path = (
        job_dir / f"left_document{left_extension}"
        if generic_upload
        else None
    )

    right_document_path = (
        job_dir / f"right_document{right_extension}"
        if generic_upload
        else None
    )

    # --------------------------------------------------------
    # 5. Save files and create database job
    # --------------------------------------------------------

    try:

        if generic_upload:

            assert left_file is not None
            assert right_file is not None
            assert left_document_path is not None
            assert right_document_path is not None

            await save_upload(
                left_file,
                left_document_path,
            )

            await save_upload(
                right_file,
                right_document_path,
            )

        else:

            if pdf is not None:
                await save_upload(
                    pdf,
                    pdf_path,
                )

            if left_xlsx is not None and right_xlsx is not None:

                await save_upload(
                    left_xlsx,
                    left_xlsx_path,
                )

                await save_upload(
                    right_xlsx,
                    right_xlsx_path,
                )

            if xlsx is not None:
                await save_upload(
                    xlsx,
                    xlsx_path,
                )

            if client_pdf is not None:
                await save_upload(
                    client_pdf,
                    client_pdf_path,
                )

        # ----------------------------------------------------
        # 6. Create AnalysisJob
        # ----------------------------------------------------

        job = AnalysisJob(
            job_id=job_id,

            tenant_id=principal.tenant_id,

            owner_id=principal.subject,

            status="UPLOADED",

            progress=0,

            message="Files uploaded.",

            jurisdiction=jurisdiction,

            nice_classes=json.dumps(
                class_values,
            ),

            left_jurisdiction=left_jurisdiction,

            right_jurisdiction=right_jurisdiction,

            left_nice_classes=json.dumps(
                left_class_values,
            ),

            right_nice_classes=json.dumps(
                right_class_values,
            ),

            left_goods_services=(
                left_goods_services.strip()
            ),

            right_goods_services=(
                right_goods_services.strip()
            ),

            source_name=source_name,

            source_url=source_url,

            source_record_id=source_record_id,

            source_retrieved_at=retrieved_at,

            retention_until=(
                datetime.now(timezone.utc)
                + timedelta(days=retention_days)
            ),
        )

        db.add(job)

        # ----------------------------------------------------
        # 7. Audit event
        # ----------------------------------------------------

        record_audit_event(
            db,
            principal,
            "job.uploaded",
            job_id,
            {
                "jurisdiction": jurisdiction,
                "nice_classes": class_values,
                "upload_mode": (
                    "generic"
                    if generic_upload
                    else "legacy"
                ),
            },
        )

        # ----------------------------------------------------
        # 8. Commit transaction
        # ----------------------------------------------------

        db.commit()

    except Exception:

        db.rollback()

        shutil.rmtree(
            job_dir,
            ignore_errors=True,
        )

        raise

    # --------------------------------------------------------
    # 9. API response
    # --------------------------------------------------------

    return {
        "job_id": job_id,

        "pdf": (
            str(pdf_path)
            if pdf_path.exists()
            else None
        ),

        "xlsx": (
            str(xlsx_path)
            if xlsx_path.exists()
            else None
        ),

        "client_pdf": (
            str(client_pdf_path)
            if client_pdf_path.exists()
            else None
        ),

        "left_xlsx": (
            str(left_xlsx_path)
            if left_xlsx_path.exists()
            else None
        ),

        "right_xlsx": (
            str(right_xlsx_path)
            if right_xlsx_path.exists()
            else None
        ),

        "left_file": (
            str(left_document_path)
            if left_document_path is not None
            and left_document_path.exists()
            else None
        ),

        "right_file": (
            str(right_document_path)
            if right_document_path is not None
            and right_document_path.exists()
            else None
        ),

        "status": "UPLOADED",

        "jurisdiction": jurisdiction,

        "nice_classes": class_values,
    }
