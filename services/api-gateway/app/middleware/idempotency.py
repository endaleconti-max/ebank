import hashlib
import json
from typing import Dict, Tuple

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Dev bootstrap middleware with in-memory response replay."""

    def __init__(self, app):
        super().__init__(app)
        self._cache: Dict[str, Tuple[int, dict]] = {}

    @staticmethod
    def _fingerprint(method: str, path: str, key: str, body: bytes) -> str:
        digest = hashlib.sha256(body).hexdigest()
        return f"{method}:{path}:{key}:{digest}"

    async def dispatch(self, request: Request, call_next):
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return await call_next(request)

        if request.url.path != "/v1/transfers":
            return await call_next(request)

        idem_key = request.headers.get("Idempotency-Key")
        if not idem_key:
            return JSONResponse(
                status_code=400,
                content={"detail": "Idempotency-Key header is required"},
            )

        body = await request.body()
        fingerprint = self._fingerprint(request.method, request.url.path, idem_key, body)

        cached = self._cache.get(fingerprint)
        if cached is not None:
            status_code, payload = cached
            return JSONResponse(status_code=status_code, content=payload)

        # Re-inject body for downstream handlers
        async def _receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request = Request(request.scope, _receive)
        response = await call_next(request)

        if 200 <= response.status_code < 300:
            raw = b""
            async for chunk in response.body_iterator:
                raw += chunk
            payload = json.loads(raw.decode("utf-8")) if raw else {}
            self._cache[fingerprint] = (response.status_code, payload)
            return JSONResponse(status_code=response.status_code, content=payload, headers=dict(response.headers))

        return response
