from pathlib import Path

from datetime import datetime

import shutil

import re

ROOT = Path(__file__).resolve().parent

RESULTS = ROOT / "app" / "api" / "results.py"

ANALYSIS = ROOT / "app" / "services" / "analysis_service.py"

def backup(path: Path):

    backup_dir = ROOT / "patch_backups"

    backup_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    target = backup_dir / f"{path.stem}.before_production_patch_{stamp}{path.suffix}"

    shutil.copy2(path, target)

    print(f"[BACKUP] {target}")

    return target

def patch_analysis_service():

    print("\n[1] Patching analysis_service.py")

    text = ANALYSIS.read_text(encoding="utf-8-sig")

    original = text

    # Fix Python exception-name bug.

    text = text.replace(

        "type(error).name",

        "type(error).__name__",

    )

    if text != original:

        print("[YES] Fixed type(error).name")

    else:

        print("[OK ] Exception-name bug already fixed")

    ANALYSIS.write_text(text, encoding="utf-8")

    compile(text, str(ANALYSIS), "exec")

    print("[PASS] analysis_service.py syntax")

def patch_results_api():

    print("\n[2] Replacing results.py")

    backup(RESULTS)

    code = '''from pathlib import Path

import json

from fastapi import APIRouter

from app.core.config import (

    EVIDENCE_DIR,

)

router = APIRouter(

    prefix="/api/results",

    tags=["Results"],

)

def _load_saved_result(job_id: str):

    """

    Try to load the persisted analysis result if one exists.

    Supported locations:

      evidence/<job_id>/result.json

      evidence/<job_id>/analysis_result.json

    """

    evidence_dir = EVIDENCE_DIR / job_id

    candidates = [

        evidence_dir / "result.json",

        evidence_dir / "analysis_result.json",

    ]

    for path in candidates:

        if not path.exists() or not path.is_file():

            continue

        try:

            return json.loads(

                path.read_text(

                    encoding="utf-8"

                )

            )

        except Exception:

            continue

    return None

@router.get("/{job_id}")

async def get_results(

    job_id: str,

):

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

    for path in sorted(evidence_dir.iterdir()):

        if path.is_file():

            files.append({

                "filename": path.name,

                "path": str(path),

                "url": (

                    f"/evidence/"

                    f"{job_id}/"

                    f"{path.name}"

                ),

            })

    saved = _load_saved_result(job_id)

    if isinstance(saved, dict):

        response = dict(saved)

        response["job_id"] = job_id

        response["files"] = files

        return response

    # No persisted result exists yet.

    #

    # The analysis endpoint itself returns the complete result.

    # This fallback still exposes the evidence files so the

    # frontend can display available evidence immediately.

    return {

        "job_id": job_id,

        "files": files,

        "matches": [],

        "application_match_details": [],

        "logo_match_details": [],

        "company_match_details": [],

        "phone_match_details": [],

        "message": (

            "Evidence files found, but the "

            "analysis result was not persisted."

        ),

    }

@router.get("/{job_id}/file/{filename}")

async def get_result_file(

    job_id: str,

    filename: str,

):

    """

    Return metadata for one evidence file.

    The actual image is served by the /evidence static mount.

    """

    evidence_dir = EVIDENCE_DIR / job_id

    file_path = evidence_dir / filename

    if not file_path.exists() or not file_path.is_file():

        return {

            "job_id": job_id,

            "filename": filename,

            "exists": False,

        }

    return {

        "job_id": job_id,

        "filename": filename,

        "exists": True,

        "path": str(file_path),

        "url": (

            f"/evidence/"

            f"{job_id}/"

            f"{filename}"

        ),

    }

'''

    RESULTS.write_text(code, encoding="utf-8")

    compile(code, str(RESULTS), "exec")

    print("[PASS] results.py syntax")

def main():

    print("=" * 70)

    print("TRADEMARK CONFLICT DETECTOR")

    print("PRODUCTION RESULTS API PATCH")

    print("=" * 70)

    patch_analysis_service()

    patch_results_api()

    print("\n" + "=" * 70)

    print("PATCH COMPLETE")

    print("=" * 70)

if __name__ == "__main__":

    main()