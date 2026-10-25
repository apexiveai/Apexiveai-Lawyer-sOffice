from pathlib import Path

import py_compile

target = Path("app/api/results.py")

content = r'''from __future__ import annotations

import json

from pathlib import Path

from fastapi import APIRouter, HTTPException

from fastapi.responses import FileResponse

from app.core.config import EVIDENCE_DIR

router = APIRouter(

    prefix="/api/results",

    tags=["Results"],

)

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

async def get_results(job_id: str):

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

                    "path": str(path),

                    "url": (

                        f"/evidence/{job_id}/"

                        f"{path.name}"

                    ),

                }

            )

    result = _load_saved_result(job_id)

    if result is not None:

        result = dict(result)

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

):

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

):

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

'''

target.write_text(

    content,

    encoding="utf-8",

)

py_compile.compile(

    str(target),

    doraise=True,

)

print()

print("=" * 60)

print("EVIDENCE API PATCH")

print("=" * 60)

print("[PASS] app/api/results.py")

print()

print("Evidence image endpoint:")

print("GET /evidence/{job_id}/{filename}")

print()

print("PATCH COMPLETE")

print("=" * 60)