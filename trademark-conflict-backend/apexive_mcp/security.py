import hashlib

import time

import uuid

from collections import defaultdict, deque

from datetime import datetime, timezone

from fastapi import Request

from starlette.responses import JSONResponse

class RateLimiter:

    def __init__(self, limit: int = 60, window_seconds: int = 60):

        self.limit = limit

        self.window_seconds = window_seconds

        self.requests = defaultdict(deque)

    def allowed(self, key: str) -> bool:

        now = time.time()

        queue = self.requests[key]

        while queue and now - queue[0] > self.window_seconds:

            queue.popleft()

        if len(queue) >= self.limit:

            return False

        queue.append(now)

        return True

rate_limiter = RateLimiter(

    limit=60,

    window_seconds=60,

)

def generate_request_id() -> str:

    return str(uuid.uuid4())

def hash_api_key(api_key: str) -> str:

    return hashlib.sha256(

        api_key.encode("utf-8")

    ).hexdigest()

def audit_log(

    request_id: str,

    method: str,

    path: str,

    status_code: int,

    client: str,

):

    timestamp = datetime.now(

        timezone.utc

    ).isoformat()

    print(

        "[AUDIT]"

        f" timestamp={timestamp}"

        f" request_id={request_id}"

        f" method={method}"

        f" path={path}"

        f" status={status_code}"

        f" client={client}"

    )

async def authenticate_request(

    request: Request,

    api_key: str,

):

    if not api_key:

        return True

    authorization = request.headers.get(

        "authorization",

        "",

    )

    expected = f"Bearer {api_key}"

    if authorization != expected:

        return False

    return True