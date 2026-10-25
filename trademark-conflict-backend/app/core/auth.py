from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str
    roles: frozenset[str]


@lru_cache
def _jwks_client() -> PyJWKClient:
    jwks_url = os.getenv("OIDC_JWKS_URL", "").strip()
    if not jwks_url:
        raise RuntimeError("OIDC_JWKS_URL must be configured.")
    return PyJWKClient(jwks_url)


def oidc_is_configured() -> bool:
    return all(
        os.getenv(name, "").strip()
        for name in ("OIDC_ISSUER", "OIDC_AUDIENCE", "OIDC_JWKS_URL")
    )


def require_oidc_configuration() -> None:
    if os.getenv("APP_ENV", "development").lower() == "production":
        if not oidc_is_configured():
            raise RuntimeError(
                "Production requires OIDC_ISSUER, OIDC_AUDIENCE, "
                "and OIDC_JWKS_URL."
            )
        if not os.getenv("EVIDENCE_URL_SIGNING_KEY", "").strip():
            raise RuntimeError(
                "Production requires EVIDENCE_URL_SIGNING_KEY."
            )


def _claims_to_principal(claims: dict[str, Any]) -> Principal:
    subject = claims.get("sub")
    tenant_claim = os.getenv("OIDC_TENANT_CLAIM", "tenant_id")
    tenant_id = claims.get(tenant_claim)
    roles_claim = claims.get(os.getenv("OIDC_ROLES_CLAIM", "roles"), [])

    if not isinstance(subject, str) or not subject:
        raise HTTPException(status_code=401, detail="Token subject is missing.")
    if not isinstance(tenant_id, str) or not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant claim is missing.")
    if tenant_id == "legacy-unassigned":
        raise HTTPException(status_code=403, detail="Tenant is not provisioned.")

    if isinstance(roles_claim, str):
        roles = {roles_claim}
    elif isinstance(roles_claim, list) and all(
        isinstance(role, str) for role in roles_claim
    ):
        roles = set(roles_claim)
    else:
        roles = set()

    return Principal(
        subject=subject,
        tenant_id=tenant_id,
        roles=frozenset(role.lower() for role in roles),
    )


def decode_access_token(token: str) -> dict[str, Any]:
    if not oidc_is_configured():
        raise RuntimeError("OIDC is not configured.")
    issuer = os.environ["OIDC_ISSUER"].rstrip("/")
    audience = os.environ["OIDC_AUDIENCE"]
    signing_key = _jwks_client().get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256", "ES256"],
        issuer=issuer,
        audience=audience,
        options={"require": ["exp", "iat", "sub"]},
    )
    _claims_to_principal(claims)
    return claims


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    if not oidc_is_configured():
        if os.getenv("APP_ENV", "development").lower() == "production":
            raise HTTPException(
                status_code=503,
                detail="OIDC authentication is not configured.",
            )
        return Principal(
            subject="local-development",
            tenant_id="local-development",
            roles=frozenset({"admin", "analyst", "reviewer"}),
        )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as error:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    return _claims_to_principal(claims)


def require_roles(*allowed_roles: str):
    async def dependency(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if not principal.roles.intersection(
            role.lower() for role in allowed_roles
        ):
            raise HTTPException(status_code=403, detail="Insufficient role.")
        return principal

    return dependency
