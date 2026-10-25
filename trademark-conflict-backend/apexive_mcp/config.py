from __future__ import annotations

import os

from pathlib import Path

# ============================================================

# Environment

# ============================================================

APP_ENV = os.getenv(

    "APP_ENV",

    "development",

).strip().lower()

IS_PRODUCTION = APP_ENV == "production"

# ============================================================

# Application

# ============================================================

APP_NAME = os.getenv(

    "APP_NAME",

    "Apexive Trademark Conflict Intelligence",

).strip()

APP_VERSION = os.getenv(

    "APP_VERSION",

    "4.0.0",

).strip()

LOG_LEVEL = os.getenv(

    "LOG_LEVEL",

    "INFO",

).strip().upper()

# ============================================================

# Backend API

# ============================================================

BACKEND_BASE_URL = os.getenv(

    "BACKEND_BASE_URL",

    "http://127.0.0.1:8000",

).rstrip("/")

BACKEND_TIMEOUT = float(

    os.getenv(

        "BACKEND_TIMEOUT",

        "120",

    )

)

# ============================================================

# MCP Server

# ============================================================

MCP_HOST = os.getenv(

    "MCP_HOST",

    "127.0.0.1",

).strip()

MCP_PORT = int(

    os.getenv(

        "MCP_PORT",

        "8100",

    )

)

# ============================================================

# MCP Security

# ============================================================

MCP_API_KEY = os.getenv(

    "MCP_API_KEY",

    "",

).strip()

MCP_API_KEY_HEADER = os.getenv(

    "MCP_API_KEY_HEADER",

    "Authorization",

).strip()

MCP_BEARER_PREFIX = os.getenv(

    "MCP_BEARER_PREFIX",

    "Bearer",

).strip()

# ============================================================

# Rate Limiting

# ============================================================

MCP_RATE_LIMIT = int(

    os.getenv(

        "MCP_RATE_LIMIT",

        "60",

    )

)

MCP_RATE_WINDOW_SECONDS = int(

    os.getenv(

        "MCP_RATE_WINDOW_SECONDS",

        "60",

    )

)

# ============================================================

# Local File Access

# ============================================================

MCP_ALLOW_LOCAL_PATHS = (

    os.getenv(

        "MCP_ALLOW_LOCAL_PATHS",

        "false" if IS_PRODUCTION else "true",

    ).strip().lower()

    in {

        "1",

        "true",

        "yes",

        "on",

    }

)

# ============================================================

# Evidence

# ============================================================

EVIDENCE_PUBLIC_BASE_URL = os.getenv(

    "EVIDENCE_PUBLIC_BASE_URL",

    "http://127.0.0.1:8000/evidence",

).rstrip("/")

# ============================================================

# PostgreSQL

# ============================================================

DATABASE_URL = os.getenv(

    "DATABASE_URL",

    "",

).strip()

DATABASE_POOL_SIZE = int(

    os.getenv(

        "DATABASE_POOL_SIZE",

        "10",

    )

)

DATABASE_MAX_OVERFLOW = int(

    os.getenv(

        "DATABASE_MAX_OVERFLOW",

        "20",

    )

)

DATABASE_POOL_TIMEOUT = int(

    os.getenv(

        "DATABASE_POOL_TIMEOUT",

        "30",

    )

)

DATABASE_POOL_RECYCLE = int(

    os.getenv(

        "DATABASE_POOL_RECYCLE",

        "1800",

    )

)

# ============================================================

# Redis

# ============================================================

REDIS_URL = os.getenv(

    "REDIS_URL",

    "",

).strip()

REDIS_TIMEOUT = float(

    os.getenv(

        "REDIS_TIMEOUT",

        "5",

    )

)

# ============================================================

# Storage

# ============================================================

BASE_DIR = Path(

    os.getenv(

        "APP_BASE_DIR",

        Path(__file__).resolve().parents[1],

    )

).resolve()

UPLOAD_DIR = Path(

    os.getenv(

        "UPLOAD_DIR",

        BASE_DIR / "uploads",

    )

).resolve()

EXTRACTED_DIR = Path(

    os.getenv(

        "EXTRACTED_DIR",
BASE_DIR / "extracted",

    )

).resolve()

EVIDENCE_DIR = Path(

    os.getenv(

        "EVIDENCE_DIR",

        BASE_DIR / "evidence",

    )

).resolve()

# ============================================================

# CORS

# ============================================================

CORS_ORIGINS_RAW = os.getenv(

    "CORS_ORIGINS",

    "",

).strip()

if CORS_ORIGINS_RAW:

    CORS_ORIGINS = [

        origin.strip()

        for origin in CORS_ORIGINS_RAW.split(",")

        if origin.strip()

    ]

else:

    CORS_ORIGINS = [

        "http://localhost:5173",

        "http://127.0.0.1:5173",

    ]

# ============================================================

# HTTPS / Proxy

# ============================================================

TRUST_PROXY_HEADERS = (

    os.getenv(

        "TRUST_PROXY_HEADERS",

        "false" if IS_PRODUCTION else "true",

    ).strip().lower()

    in {

        "1",

        "true",

        "yes",

        "on",

    }

)

FORCE_HTTPS = (

    os.getenv(

        "FORCE_HTTPS",

        "true" if IS_PRODUCTION else "false",

    ).strip().lower()

    in {

        "1",

        "true",

        "yes",

        "on",

    }

)

# ============================================================

# Validation

# ============================================================

def validate_production_config() -> None:

    """

    Validate security-sensitive configuration

    before starting the production MCP server.

    """

    if not IS_PRODUCTION:

        return

    errors: list[str] = []

    if not MCP_API_KEY:

        errors.append(

            "MCP_API_KEY is required in production."

        )

    if len(MCP_API_KEY) < 32:

        errors.append(

            "MCP_API_KEY must be at least 32 characters."

        )

    if not DATABASE_URL:

        errors.append(

            "DATABASE_URL is required in production."

        )

    if not REDIS_URL:

        errors.append(

            "REDIS_URL is required in production."

        )

    if (

        "127.0.0.1" in BACKEND_BASE_URL

        or "localhost" in BACKEND_BASE_URL

    ):

        errors.append(

            "BACKEND_BASE_URL must not point to localhost "

            "inside production containers."

        )

    if (

        "127.0.0.1" in EVIDENCE_PUBLIC_BASE_URL

        or "localhost" in EVIDENCE_PUBLIC_BASE_URL

    ):

        errors.append(

            "EVIDENCE_PUBLIC_BASE_URL must use the "

            "production public URL."

        )

    if MCP_ALLOW_LOCAL_PATHS:

        errors.append(

            "MCP_ALLOW_LOCAL_PATHS must be false in production."

        )

    if errors:

        message = (

            "Production configuration validation failed:\n"

            + "\n".join(

                f"- {error}"

                for error in errors

            )

        )

        raise RuntimeError(message)

# ============================================================

# Runtime Summary

# ============================================================

def get_config_summary() -> dict[str, object]:

    """

    Safe configuration summary.

    Secrets are never returned.

    """

    return {

        "app_name": APP_NAME,

        "app_version": APP_VERSION,

        "environment": APP_ENV,

        "production": IS_PRODUCTION,

        "backend": BACKEND_BASE_URL,

        "mcp": {

            "host": MCP_HOST,

            "port": MCP_PORT,

            "authentication": bool(

                MCP_API_KEY

            ),

            "rate_limit": MCP_RATE_LIMIT,

            "rate_window_seconds":

                MCP_RATE_WINDOW_SECONDS,

        },

        "storage": {

            "uploads": str(UPLOAD_DIR),

            "extracted": str(EXTRACTED_DIR),

            "evidence": str(EVIDENCE_DIR),

            "local_paths_allowed":

                MCP_ALLOW_LOCAL_PATHS,

        },

        "database": {

            "configured": bool(

                DATABASE_URL

            ),

        },

        "redis": {

            "configured": bool(
REDIS_URL

            ),

        },

        "https": {

            "force_https": FORCE_HTTPS,

            "trust_proxy_headers":

                TRUST_PROXY_HEADERS,

        },

    }

# ============================================================

# Create Storage Directories

# ============================================================

def ensure_storage_directories() -> None:

    """

    Create required application directories.

    """

    UPLOAD_DIR.mkdir(

        parents=True,

        exist_ok=True,

    )

    EXTRACTED_DIR.mkdir(

        parents=True,

        exist_ok=True,

    )

    EVIDENCE_DIR.mkdir(

        parents=True,

        exist_ok=True,

    )

# ============================================================

# Development Initialization

# ============================================================

ensure_storage_directories()

if IS_PRODUCTION:

    validate_production_config()