from typing import List, Optional

from pydantic import BaseModel, Field

class BoundingBox(BaseModel):

    x: float

    y: float

    width: float

    height: float

class LogoCandidate(BaseModel):

    id: str

    source_type: str

    source_file: str

    page: Optional[int] = None

    sheet: Optional[str] = None

    cell: Optional[str] = None

    image_path: str

    bbox: Optional[BoundingBox] = None

    width: int

    height: int

    confidence: float = 0.0

class SimilarityMatch(BaseModel):

    match_id: str

    original_logo_id: str

    compare_logo_id: str

    similarity: float

    similarity_percent: float

    status: str

    original_evidence: Optional[str] = None

    compare_evidence: Optional[str] = None

class AnalysisResponse(BaseModel):

    job_id: str

    pdf_pages: int

    client_records: int

    pdf_logos: int

    xlsx_logos: int

    application_matches: int

    logo_matches: int

    matches: List[SimilarityMatch] = Field(default_factory=list)