from __future__ import annotations

import hashlib
import hmac
import os


def _signing_key() -> bytes:
    key = os.getenv(
        "EVIDENCE_URL_SIGNING_KEY",
        "development-evidence-signing-key-change-before-production",
    )
    return key.encode("utf-8")


def sign_evidence_url(
    tenant_id: str,
    job_id: str,
    filename: str,
    expires: int,
) -> str:
    payload = f"{tenant_id}\n{job_id}\n{filename}\n{expires}".encode("utf-8")
    return hmac.new(_signing_key(), payload, hashlib.sha256).hexdigest()


def verify_evidence_url(
    tenant_id: str,
    job_id: str,
    filename: str,
    expires: int,
    signature: str,
) -> bool:
    import time

    if expires < int(time.time()):
        return False
    expected = sign_evidence_url(tenant_id, job_id, filename, expires)
    return hmac.compare_digest(expected, signature)
