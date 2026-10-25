from pathlib import Path

import os

BASE_DIR = Path(__file__).resolve().parents[2]

UPLOAD_DIR = BASE_DIR / "uploads"

EXTRACTED_DIR = BASE_DIR / "extracted"

EVIDENCE_DIR = BASE_DIR / "evidence"

RESULTS_DIR = BASE_DIR / "results"

for directory in [

    UPLOAD_DIR,

    EXTRACTED_DIR,

    EVIDENCE_DIR,

    RESULTS_DIR,

]:

    directory.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "100"))

ALLOWED_EXTENSIONS = {

    ".pdf",

    ".xlsx",

}

SIMILARITY_THRESHOLD = float(

    os.getenv("SIMILARITY_THRESHOLD", "0.82")

)

HIGH_SIMILARITY_THRESHOLD = float(

    os.getenv("HIGH_SIMILARITY_THRESHOLD", "0.90")

)