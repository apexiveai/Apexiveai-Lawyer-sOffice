from __future__ import annotations

from pathlib import Path

def build_logo_evidence(

    job_id: str,

    pdf_filename: str | None,

    client_filename: str | None,

    page: int | None = None,

    client_row: int | None = None,

    similarity: float | None = None,

    text_match: str = "NO_TEXT",

    visual_match: bool = False,

) -> dict:

    result = {

        "job_id": job_id,

        "logo_match": False,

        "similarity": (

            round(float(similarity), 2)

            if similarity is not None

            else 0.0

        ),

        "text_match": text_match,

        "visual_match": (

            "CONFIRMED"

            if visual_match

            else "NOT_CONFIRMED"

        ),

        "page": page,

        "client_row": client_row,

        "pdf_evidence": None,

        "client_evidence": None,

    }

    if pdf_filename:

        result["pdf_evidence"] = (

            f"/evidence/{job_id}/{Path(pdf_filename).name}"

        )

    if client_filename:

        result["client_evidence"] = (

            f"/evidence/{job_id}/{Path(client_filename).name}"

        )

    result["logo_match"] = bool(

        text_match in {"EXACT", "NO_TEXT"}

        and visual_match

    )

    return result