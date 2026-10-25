from contextlib import asynccontextmanager
import logging
import os
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request

from fastapi.responses import FileResponse

from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session

from app.api.assistant import router as assistant_router
from app.api.upload import router as upload_router
from app.api.reviews import router as reviews_router
from app.api.analysis import router as analysis_router
from app.api.reports import router as reports_router
from app.api.results import router as results_router
from app.api.audit import router as audit_router
from app.core.auth import require_oidc_configuration
from app.core.config import (

    EVIDENCE_DIR,

)
from app.core.evidence_links import verify_evidence_url
from app.core.logging import configure_logging
from app.db.init_db import init_db
from app.db.database import engine, get_db
from app.models.job import AnalysisJob
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from redis import Redis
from redis.exceptions import RedisError


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    require_oidc_configuration()
    init_db()
    yield

app = FastAPI(

    title="Apexive AI Trademark Conflict Detector",

    description=(

        "AI-powered trademark conflict "

        "detection using PDF and XLSX "

        "logo comparison."

    ),

    version="1.0.0",

    lifespan=lifespan,

)

app.add_middleware(

    CORSMiddleware,

    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ],

    allow_credentials=False,

    allow_methods=["*"],

    allow_headers=["*"],

)

logger = logging.getLogger("trademark.api")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )
        raise
    logger.info(
        "request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        },
    )
    response.headers["X-Request-ID"] = request_id
    return response

app.include_router(

    upload_router

)

app.include_router(

    analysis_router

)

app.include_router(results_router)
app.include_router(assistant_router)
app.include_router(reviews_router)
app.include_router(reports_router)
app.include_router(audit_router)

@app.get("/evidence/{job_id}/{filename}")

async def serve_evidence_image(
    job_id: str,
    filename: str,
    tenant: str,
    expires: int,
    signature: str,
    db: Session = Depends(get_db),
):

    job = db.get(AnalysisJob, job_id)
    if job is None or job.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Evidence image not found.")
    if not verify_evidence_url(
        tenant, job_id, filename, expires, signature
    ):
        raise HTTPException(status_code=403, detail="Evidence link is invalid or expired.")
    evidence_dir = (EVIDENCE_DIR / job_id).resolve()

    requested_file = (evidence_dir / filename).resolve()

    try:

        requested_file.relative_to(evidence_dir)

    except ValueError:

        raise HTTPException(

            status_code=400,

            detail="Invalid evidence filename."

        )

    if not requested_file.exists() or not requested_file.is_file():

        raise HTTPException(

            status_code=404,

            detail="Evidence image not found."

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

            detail="Unsupported evidence image type."

        )

    return FileResponse(

        path=str(requested_file)

    )

@app.get("/")

async def root():

    return {

        "application": (

            "Apexive AI "

            "Trademark Conflict Detector"

        ),

        "version": "1.0.0",

        "status": "ONLINE",

    }

@app.get("/health")
async def health():

    return {

        "status": "healthy"

    }


@app.get("/ready")
async def ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        redis_url = os.getenv(
            "REDIS_URL", "redis://localhost:6379/0"
        )
        client = Redis.from_url(redis_url)
        try:
            client.ping()
        finally:
            client.close()
    except (SQLAlchemyError, RedisError) as error:
        raise HTTPException(status_code=503, detail="Service dependencies unavailable.") from error
    return {"status": "ready"}
