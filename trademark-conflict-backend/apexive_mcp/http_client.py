from __future__ import annotations

from contextvars import ContextVar
from typing import Any

import httpx

from .config import BACKEND_BASE_URL, BACKEND_TIMEOUT

backend_bearer_token: ContextVar[str | None] = ContextVar(
    "backend_bearer_token",
    default=None,
)

async def backend_request(

    method: str,

    path: str,

    *,

    json: dict[str, Any] | None = None,

    params: dict[str, Any] | None = None,

) -> Any:

    url = f"{BACKEND_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    headers: dict[str, str] = {}
    token = backend_bearer_token.get()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=BACKEND_TIMEOUT) as client:
        response = await client.request(

            method=method.upper(),

            url=url,

            json=json,
            params=params,
            headers=headers,
        )

        response.raise_for_status()

        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:

            return response.json()

        return {

            "status_code": response.status_code,

            "text": response.text,

        }

async def backend_get(

    path: str,

    *,

    params: dict[str, Any] | None = None,

) -> Any:

    return await backend_request(

        "GET",

        path,

        params=params,

    )

async def backend_post(

    path: str,

    *,

    json: dict[str, Any] | None = None,

) -> Any:

    return await backend_request(

        "POST",

        path,

        json=json,

    )