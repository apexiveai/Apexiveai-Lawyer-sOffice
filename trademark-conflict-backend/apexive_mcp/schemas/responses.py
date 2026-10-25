from typing import Any

from pydantic import BaseModel, Field

class JobStatusResponse(BaseModel):

    job_id: str

    status: str

    progress: int = Field(default=0, ge=0, le=100)

    message: str = ""

class ConflictSearchResponse(BaseModel):

    job_id: str

    total: int

    conflicts: list[dict[str, Any]]

class EvidenceResponse(BaseModel):

    job_id: str

    match_index: int

    pdf_evidence: dict[str, Any] | None = None

    client_evidence: dict[str, Any] | None = None

    similarity_percent: float | None = None

    match_type: str | None = None

class AnalysisResponse(BaseModel):

    job_id: str

    status: str

    pdf_pages: int = 0

    client_records: int = 0

    pdf_logos: int = 0

    xlsx_logos: int = 0

    application_matches: int = 0

    logo_matches: int = 0

    company_matches: int = 0

    phone_matches: int = 0