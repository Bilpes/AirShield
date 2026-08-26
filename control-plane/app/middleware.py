from __future__ import annotations

import time
import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from .config import get_settings

log = structlog.get_logger()


def safe_correlation_id(value: str | None) -> str:
    if value:
        try:
            return str(uuid.UUID(value))
        except ValueError:
            pass
    return str(uuid.uuid4())


class BodyLimitMiddleware:
    """Buffer at most the configured bounded API body before framework parsing."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        supplied_correlation = headers.get(b"x-correlation-id")
        correlation_id = safe_correlation_id(
            supplied_correlation.decode(errors="replace") if supplied_correlation else None
        )
        declared = headers.get(b"content-length")
        if declared:
            try:
                if int(declared) > self.max_bytes or int(declared) < 0:
                    await harden(
                        JSONResponse({"detail": "Request too large"}, status_code=413), correlation_id
                    )(scope, receive, send)
                    return
            except ValueError:
                await harden(
                    JSONResponse({"detail": "Invalid Content-Length"}, status_code=400), correlation_id
                )(scope, receive, send)
                return

        messages = []
        total = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                messages.append(message)
                break
            total += len(message.get("body", b""))
            if total > self.max_bytes:
                await harden(JSONResponse({"detail": "Request too large"}, status_code=413), correlation_id)(
                    scope, receive, send
                )
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        index = 0

        async def replay_receive():
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return {"type": "http.disconnect"}

        await self.app(scope, replay_receive, send)


def route_template(request: Request) -> str:
    route = request.scope.get("route")
    value = getattr(route, "path", None)
    return str(value) if value else "unmatched"


def harden(response: Response, correlation_id: str) -> Response:
    response.headers["x-correlation-id"] = correlation_id
    response.headers["x-content-type-options"] = "nosniff"
    response.headers["cache-control"] = "no-store"
    response.headers["referrer-policy"] = "no-referrer"
    response.headers["content-security-policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = safe_correlation_id(request.headers.get("x-correlation-id"))
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        try:
            try:
                content_length = int(request.headers.get("content-length", "0") or 0)
            except ValueError:
                return harden(
                    JSONResponse({"detail": "Invalid Content-Length"}, status_code=400), correlation_id
                )
            if content_length > get_settings().max_text_bytes + 16_384:
                return harden(JSONResponse({"detail": "Request too large"}, status_code=413), correlation_id)
            started = time.perf_counter()
            try:
                response = await call_next(request)
            except Exception as exc:
                log.error(
                    "request_failed",
                    method=request.method,
                    route=route_template(request),
                    error_type=type(exc).__name__,
                )
                raise
            harden(response, correlation_id)
            log.info(
                "request_complete",
                method=request.method,
                route=route_template(request),
                status=response.status_code,
                duration_ms=round((time.perf_counter() - started) * 1000),
            )
            return response
        finally:
            structlog.contextvars.clear_contextvars()
