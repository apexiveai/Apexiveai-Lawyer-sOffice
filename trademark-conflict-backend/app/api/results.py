from __future__ import annotations

import json

from pathlib import Path
from urllib.parse import quote
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.auth import Principal, require_roles
from app.core.authorization import get_accessible_job
from app.core.config import EVIDENCE_DIR
from app.core.evidence_links import sign_evidence_url
from app.db.database import get_db

router = APIRouter(

    prefix="/api/results",

    tags=["Results"],

)

def _evidence_url(
    job_id: str,
    value: object,
    tenant_id: str,
) -> str | None:
    if not value:
        return None

    if isinstance(value, dict):
        value = (
            value.get("url")
            or value.get("image_path")
            or value.get("path")
            or value.get("file_path")
            or value.get("filename")
        )

    if not isinstance(value, str):
        return None

    normalized = value.replace("\\", "/")
    filename = normalized.rsplit("/", 1)[-1]
    if not filename:
        return None

    requested_file = (EVIDENCE_DIR / job_id / filename).resolve()
    evidence_dir = (EVIDENCE_DIR / job_id).resolve()
    try:
        requested_file.relative_to(evidence_dir)
    except ValueError:
        return None

    if not requested_file.is_file():
        return None

    expires = int(time.time()) + 300
    signature = sign_evidence_url(tenant_id, job_id, filename, expires)
    return (
        f"/evidence/{quote(job_id)}/{quote(filename)}"
        f"?tenant={quote(tenant_id)}&expires={expires}&signature={signature}"
    )


def _normalize_result_evidence(
    result: dict,
    job_id: str,
    tenant_id: str,
) -> dict:
    normalized = dict(result)
    files = normalized.get("files")
    if isinstance(files, list):
        normalized_files = []
        for item in files:
            if not isinstance(item, dict):
                normalized_files.append(item)
                continue
            item_copy = dict(item)
            item_copy["url"] = _evidence_url(
                job_id,
                item_copy.get("filename"),
                tenant_id,
            )
            item_copy.pop("path", None)
            normalized_files.append(item_copy)
        normalized["files"] = normalized_files
    for collection_name in (
        "matches",
        "application_match_details",
        "company_match_details",
        "phone_match_details",
        "logo_match_details",
    ):
        collection = normalized.get(collection_name)
        if not isinstance(collection, list):
            continue

        normalized_items = []
        for item in collection:
            if not isinstance(item, dict):
                normalized_items.append(item)
                continue

            item_copy = dict(item)
            for field in ("pdf_evidence", "client_evidence"):
                if field in item_copy:
                    item_copy[field] = _evidence_url(
                        job_id,
                        item_copy[field],
                        tenant_id,
                    )
            normalized_items.append(item_copy)
        normalized[collection_name] = normalized_items
    return normalized

def _load_saved_result(job_id: str):

    evidence_dir = EVIDENCE_DIR / job_id

    candidates = [

        evidence_dir / "analysis_result.json",

        evidence_dir / "result.json",

    ]

    for path in candidates:

        if path.exists() and path.is_file():

            try:

                with path.open("r", encoding="utf-8") as file:

                    data = json.load(file)

                if isinstance(data, dict):

                    return data

            except Exception:

                return None

    return None

@router.get("/{job_id}")

async def get_results(
    job_id: str,
    principal: Principal = Depends(
        require_roles("analyst", "admin", "reviewer")
    ),
    db: Session = Depends(get_db),
):

    get_accessible_job(job_id, principal, db)

    evidence_dir = EVIDENCE_DIR / job_id

    if not evidence_dir.exists():

        return {

            "job_id": job_id,

            "files": [],

            "matches": [],

            "application_match_details": [],

            "logo_match_details": [],

            "company_match_details": [],

            "phone_match_details": [],

        }

    files = []

    for path in evidence_dir.iterdir():

        if not path.is_file():

            continue

        if path.name.lower().endswith(

            (

                ".png",

                ".jpg",

                ".jpeg",

                ".webp",

            )

        ):

            files.append(

                {
                    "filename": path.name,
                    "url": _evidence_url(
                        job_id,
                        path.name,
                        principal.tenant_id,
                    ),
                }

            )

    result = _load_saved_result(job_id)
    if result is not None:
        result = _normalize_result_evidence(
            result, job_id, principal.tenant_id
        )
        result["job_id"] = job_id

        result["files"] = files

        return result

    return {

        "job_id": job_id,

        "files": files,

        "matches": [],

        "application_match_details": [],

        "logo_match_details": [],

        "company_match_details": [],

        "phone_match_details": [],

        "message": "Evidence files found, but analysis result was not saved.",

    }

@router.get("/{job_id}/file/{filename}")

async def get_evidence_file(

    job_id: str,

    filename: str,
    principal: Principal = Depends(
        require_roles("analyst", "admin", "reviewer")
    ),
    db: Session = Depends(get_db),

):

    get_accessible_job(job_id, principal, db)
    evidence_dir = (

        EVIDENCE_DIR / job_id

    ).resolve()

    requested_file = (

        evidence_dir / filename

    ).resolve()

    # Prevent path traversal.

    try:

        requested_file.relative_to(evidence_dir)

    except ValueError:

        raise HTTPException(

            status_code=400,

            detail="Invalid evidence filename.",

        )

    if not requested_file.exists():

        raise HTTPException(

            status_code=404,

            detail="Evidence file not found.",

        )

    if not requested_file.is_file():

        raise HTTPException(

            status_code=404,

            detail="Evidence file not found.",

        )

    return FileResponse(

        path=str(requested_file),

    )

# Frontend currently uses:

# /evidence/{job_id}/{filename}

#

# This route intentionally serves the actual image bytes.

@router.get("/evidence/{job_id}/{filename}")

async def serve_evidence_image(

    job_id: str,

    filename: str,
    principal: Principal = Depends(
        require_roles("analyst", "admin", "reviewer")
    ),
    db: Session = Depends(get_db),

):

    get_accessible_job(job_id, principal, db)
    evidence_dir = (

        EVIDENCE_DIR / job_id

    ).resolve()

    requested_file = (

        evidence_dir / filename

    ).resolve()

    # Prevent path traversal.

    try:

        requested_file.relative_to(evidence_dir)

    except ValueError:

        raise HTTPException(

            status_code=400,

            detail="Invalid evidence filename.",

        )

    if not requested_file.exists():

        raise HTTPException(

            status_code=404,
            
            detail="Evidence image not found.",

        )

    if not requested_file.is_file():

        raise HTTPException(

            status_code=404,

            detail="Evidence image not found.",

        )

    allowed_extensions = {

        ".png",

        ".jpg",

        ".jpeg",

        ".webp",

    }

    if requested_file.suffix.lower() not in allowed_extensions:

        raise HTTPException(

            status_code=400,

            detail="Unsupported evidence image type.",

        )

    return FileResponse(

        path=str(requested_file),

    )
