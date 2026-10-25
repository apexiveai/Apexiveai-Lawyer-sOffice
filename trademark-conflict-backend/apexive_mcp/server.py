from contextlib import asynccontextmanager
import os
import uvicorn
from fastapi import FastAPI, Request

from starlette.middleware.base import BaseHTTPMiddleware

from starlette.responses import JSONResponse

from mcp.server.fastmcp import FastMCP
from jwt import PyJWTError

from app.core.auth import decode_access_token, oidc_is_configured
from apexive_mcp.config import (

    MCP_HOST,

    MCP_PORT,

)

from apexive_mcp.security import (

    audit_log,


    generate_request_id,

    rate_limiter,

)

from apexive_mcp.tools.analysis import register_analysis_tools

from apexive_mcp.tools.conflicts import register_conflict_tools

from apexive_mcp.tools.evidence import register_evidence_tools
from apexive_mcp.http_client import backend_bearer_token

mcp = FastMCP(

    "Apexive Trademark Conflict Intelligence",

    stateless_http=True,

    json_response=True,

)

mcp_app = mcp.streamable_http_app()

register_analysis_tools(mcp)

register_conflict_tools(mcp)

register_evidence_tools(mcp)

class EnterpriseSecurityMiddleware(

    BaseHTTPMiddleware

):

    async def dispatch(

        self,

        request: Request,

        call_next,

    ):

        request_id = generate_request_id()

        request.state.request_id = request_id

        # -----------------------------

        # Public endpoints

        # -----------------------------

        public_paths = {

            "/",

            "/health",

        }

        bearer_token: str | None = None
        if request.url.path not in public_paths:
            # Authentication
            authorization = request.headers.get("authorization", "")
            authenticated = (
                not oidc_is_configured()
                and os.getenv("APP_ENV", "development").lower()
                != "production"
            )
            if authorization.lower().startswith("bearer ") and oidc_is_configured():
                bearer_token = authorization[7:].strip()
                try:
                    decode_access_token(bearer_token)
                    authenticated = True
                except PyJWTError:
                    authenticated = False
            if not authenticated:

                response = JSONResponse(

                    status_code=401,

                    content={

                        "error": "Unauthorized",

                        "request_id": request_id,

                    },

                )

                response.headers[

                    "X-Request-ID"

                ] = request_id

                return response

            # Rate limiting

            client_key = (

                request.client.host

                if request.client

                else "unknown"

            )

            if not rate_limiter.allowed(

                client_key

            ):

                response = JSONResponse(

                    status_code=429,

                    content={

                        "error": "Rate limit exceeded",

                        "request_id": request_id,

                    },

                )

                response.headers[

                    "Retry-After"

                ] = "60"

                response.headers[

                    "X-Request-ID"

                ] = request_id

                return response

        token = backend_bearer_token.set(bearer_token)
        try:
            response = await call_next(request)

        except Exception:

            audit_log(

                request_id=request_id,

                method=request.method,

                path=request.url.path,

                status_code=500,

                client=(

                    request.client.host

                    if request.client

                    else "unknown"

                ),

            )
            raise
        finally:
            backend_bearer_token.reset(token)

        response.headers[

            "X-Request-ID"

        ] = request_id

        # Security headers

        response.headers[

            "X-Content-Type-Options"

        ] = "nosniff"

        response.headers[

            "X-Frame-Options"

        ] = "DENY"

        response.headers[

            "Referrer-Policy"

        ] = "no-referrer"

        response.headers[

            "Cache-Control"

        ] = "no-store"

        audit_log(

            request_id=request_id,

            method=request.method,

            path=request.url.path,

            status_code=response.status_code,

            client=(

                request.client.host

                if request.client

                else "unknown"

            ),

        )

        return response

@asynccontextmanager

async def lifespan(app: FastAPI):

    async with mcp.session_manager.run():

        yield

app = FastAPI(

    title="Apexive Trademark Conflict MCP",

    version="3.0.0",

    lifespan=lifespan,

)

app.add_middleware(

    EnterpriseSecurityMiddleware

)

mcp_app.add_middleware(EnterpriseSecurityMiddleware)

@app.get("/")

async def root():

    return {

        "service":

            "Apexive Trademark Conflict Intelligence",

        "version": "3.0.0",

        "transport": "streamable-http",

        "mcp_endpoint": "/mcp",

        "security": {

            "authentication": oidc_is_configured(),

            "rate_limit": "60 requests/minute",

            "audit_logging": True,

        },

    }

@app.get("/health")

async def health():

    return {

        "service":

            "Apexive Trademark Conflict Intelligence",

        "status": "ok",

        "transport": "streamable-http",

        "authentication": oidc_is_configured(),

        "rate_limit": "60/minute",

        "audit_logging": True,

    }

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "apexive_mcp.server:mcp_app",

        host=MCP_HOST,

        port=MCP_PORT,

        proxy_headers=True,

        forwarded_allow_ips="*",

    )