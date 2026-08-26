from __future__ import annotations

import asyncio
import json
import re
import ssl
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import Any

import jwt
import websockets
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from jwt import PyJWKClient

from .config import settings

POLICIES = {
    "Healthcare · HIPAA",
    "Financial services · PCI",
    "Insurance claims",
    "Contact center privacy",
    "Internal copilot DLP",
    "healthcare-us-eu-v1",
    "finance-eu-us-v1",
    "insurance-eu-us-v1",
    "contact-center-eu-us-v1",
    "saas-copilot-eu-us-v1",
}
_jwks = PyJWKClient(settings.oidc_jwks_url, cache_keys=True, lifespan=300) if settings.oidc_jwks_url else None
_connection_lock = asyncio.Lock()
_dependency_lock = asyncio.Lock()
_dependency_checked_at = 0.0
_dependency_status = False
_connections = 0


def edge_ssl_context() -> ssl.SSLContext | None:
    if not settings.edge_websocket_url.startswith("wss://"):
        return None
    return ssl.create_default_context(cafile=str(settings.edge_ca_file) if settings.edge_ca_file else None)


class AuthenticationError(Exception):
    pass


async def authenticate(token: str | None) -> dict[str, Any]:
    if not token:
        raise AuthenticationError("missing session")
    if settings.environment != "production" and not _jwks:
        if settings.dev_session_token and token == settings.dev_session_token:
            return {"sub": "development-user", settings.tenant_claim: "development-tenant"}
        raise AuthenticationError("invalid development session")
    if not _jwks or not settings.oidc_issuer or not settings.oidc_audience:
        raise AuthenticationError("identity provider unavailable")
    try:
        signing_key = await asyncio.to_thread(_jwks.get_signing_key_from_jwt, token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            leeway=30,
        )
    except Exception as exc:
        raise AuthenticationError("invalid session") from exc
    if claims.get(settings.tenant_claim) != settings.expected_tenant_id:
        raise AuthenticationError("tenant mismatch")
    return claims


def bearer_or_cookie(ws: WebSocket) -> str | None:
    authorization = ws.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ws.cookies.get(settings.session_cookie_name)


def allowed_origin(ws: WebSocket) -> bool:
    origin = ws.headers.get("origin", "").rstrip("/")
    return bool(origin and origin in settings.origin_list)


def normalize_edge_event(event: object) -> dict[str, Any]:
    if not isinstance(event, dict) or event.get("type") not in {
        "session.ready",
        "transcript.pair",
        "transcript.final",
        "policy.decision",
    }:
        raise ValueError("Invalid edge event")
    normalized = dict(event)
    if normalized["type"] == "transcript.pair":
        normalized["safe_for_egress"] = False
        normalized["provisional"] = True
    elif normalized["type"] == "transcript.final":
        receipt = normalized.get("receipt")
        signature = receipt.get("signature") if isinstance(receipt, dict) else None
        receipt_id = receipt.get("receipt_id") if isinstance(receipt, dict) else None
        signed_allow = (
            normalized.get("decision") == "allow"
            and isinstance(receipt_id, str)
            and bool(receipt_id)
            and isinstance(signature, str)
            and len(signature) >= 40
            and signature != "demo_unsigned"
        )
        normalized["safe_for_egress"] = signed_allow
        if not signed_allow and normalized.get("decision") == "allow":
            normalized["decision"] = "block"
            normalized["protected"] = ""
            normalized["reason"] = "signed_final_receipt_required"
    return normalized


class MessageRate:
    def __init__(self) -> None:
        self.timestamps: deque[float] = deque()

    def accept(self) -> bool:
        now = time.monotonic()
        while self.timestamps and self.timestamps[0] <= now - 1:
            self.timestamps.popleft()
        if len(self.timestamps) >= settings.max_messages_per_second:
            return False
        self.timestamps.append(now)
        return True


async def reserve_connection() -> bool:
    global _connections
    async with _connection_lock:
        if _connections >= settings.max_connections:
            return False
        _connections += 1
        return True


async def release_connection() -> None:
    global _connections
    async with _connection_lock:
        _connections = max(0, _connections - 1)


async def dependencies_ready() -> bool:
    global _dependency_checked_at, _dependency_status
    if settings.environment != "production":
        return True
    now = time.monotonic()
    if now - _dependency_checked_at < 30:
        return _dependency_status
    async with _dependency_lock:
        now = time.monotonic()
        if now - _dependency_checked_at < 30:
            return _dependency_status
        try:
            if _jwks is None:
                return False
            await asyncio.to_thread(_jwks.fetch_data)
            async with websockets.connect(
                settings.edge_websocket_url,
                additional_headers={"x-airshield-edge-auth": settings.edge_gateway_secret or ""},
                ssl=edge_ssl_context(),
                open_timeout=3,
                close_timeout=3,
            ):
                pass
            _dependency_status = True
        except Exception:
            _dependency_status = False
        _dependency_checked_at = now
        return _dependency_status


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.environment == "production" and _jwks is None:
        raise RuntimeError("Production OIDC validation is unavailable")
    yield


app = FastAPI(title="AirShield Trusted WebSocket Gateway", version="1.0.0", lifespan=lifespan)


@app.get("/healthz")
async def health():
    return {"status": "alive"}


@app.get("/readyz")
async def ready(response: Response):
    healthy = await dependencies_ready()
    if not healthy:
        response.status_code = 503
    return {
        "status": "ready" if healthy else "not_ready",
        "active_connections": _connections,
    }


@app.websocket("/ws/voice")
async def voice_gateway(ws: WebSocket) -> None:
    if not allowed_origin(ws):
        await ws.close(code=4403, reason="Origin denied")
        return
    try:
        claims = await authenticate(bearer_or_cookie(ws))
    except AuthenticationError:
        await ws.close(code=4401, reason="Authenticated host session required")
        return
    host_identity: dict[str, str] | None = None
    claimed_track = claims.get(settings.speaker_track_claim)
    subject = claims.get("sub")
    if (
        isinstance(claimed_track, str)
        and re.fullmatch(r"SPEAKER_[A-Z0-9]{1,8}", claimed_track)
        and isinstance(subject, str)
        and 3 <= len(subject) <= 256
    ):
        host_identity = {
            "speaker_track": claimed_track,
            "subject_token": subject,
            "assurance": "sso_verified",
            "source": "sso",
        }

    if not await reserve_connection():
        await ws.close(code=4429, reason="Gateway capacity exceeded")
        return

    await ws.accept()
    final_seen = asyncio.Event()
    rate = MessageRate()
    total_audio = 0
    started = False

    try:
        async with websockets.connect(
            settings.edge_websocket_url,
            additional_headers={"x-airshield-edge-auth": settings.edge_gateway_secret or ""},
            ssl=edge_ssl_context(),
            max_size=settings.max_message_bytes,
            open_timeout=5,
            close_timeout=5,
            ping_interval=20,
            ping_timeout=20,
        ) as edge:

            async def browser_to_edge() -> None:
                nonlocal started, total_audio
                while True:
                    message = await ws.receive()
                    if message["type"] == "websocket.disconnect":
                        return
                    if not rate.accept():
                        await ws.close(code=4429, reason="Message rate exceeded")
                        return
                    data = message.get("bytes")
                    if data is not None:
                        if not started:
                            await ws.close(code=4400, reason="Session must start before audio")
                            return
                        if len(data) > settings.max_message_bytes:
                            await ws.close(code=4409, reason="Message too large")
                            return
                        total_audio += len(data)
                        if total_audio > settings.max_session_audio_bytes:
                            await ws.close(code=4409, reason="Session audio limit exceeded")
                            return
                        await edge.send(data)
                        continue

                    text = message.get("text")
                    if text is None or len(text.encode()) > min(settings.max_message_bytes, 16_384):
                        await ws.close(code=4400, reason="Invalid control message")
                        return
                    try:
                        event = json.loads(text)
                    except json.JSONDecodeError:
                        await ws.close(code=4400, reason="Invalid control message")
                        return
                    if not isinstance(event, dict):
                        await ws.close(code=4400, reason="Invalid control message")
                        return
                    event_type = event.get("type")
                    if event_type == "session.start" and not started:
                        policy = event.get("policy")
                        audio_format = event.get("audio_format", "audio/webm")
                        media_type = (
                            audio_format.lower().split(";", 1)[0] if isinstance(audio_format, str) else ""
                        )
                        if (
                            event.get("language", "en") != "en"
                            or policy not in POLICIES
                            or media_type not in {"audio/webm", "audio/mp4", "audio/ogg"}
                        ):
                            await ws.close(code=4400, reason="Unsupported session policy or audio format")
                            return
                        started = True
                        # Construct a new event: no client-supplied trust or gateway fields
                        # cross the private boundary. The validated media type is retained
                        # so the edge can select the correct local decoder container.
                        trusted_start: dict[str, Any] = {
                            "type": "session.start",
                            "language": "en",
                            "policy": policy,
                            "audio_format": audio_format,
                        }
                        if host_identity:
                            trusted_start["host_identity"] = host_identity
                        await edge.send(json.dumps(trusted_start))
                    elif event_type == "session.end" and started:
                        await edge.send(json.dumps({"type": "session.end"}))
                        try:
                            await asyncio.wait_for(final_seen.wait(), timeout=settings.final_wait_seconds)
                        except TimeoutError:
                            await ws.close(code=1011, reason="Final privacy decision unavailable")
                        return
                    else:
                        await ws.close(code=4400, reason="Invalid session transition")
                        return

            async def edge_to_browser() -> None:
                async for message in edge:
                    if isinstance(message, bytes):
                        await ws.close(code=1011, reason="Unexpected edge response")
                        return
                    try:
                        event = json.loads(message)
                    except json.JSONDecodeError:
                        await ws.close(code=1011, reason="Invalid edge response")
                        return
                    try:
                        event = normalize_edge_event(event)
                    except ValueError:
                        await ws.close(code=1011, reason="Invalid edge response")
                        return
                    await ws.send_text(json.dumps(event, separators=(",", ":")))
                    if event.get("type") in {"transcript.final", "policy.decision"}:
                        final_seen.set()
                        return

            async with asyncio.timeout(settings.max_session_seconds):
                browser_task = asyncio.create_task(browser_to_edge())
                edge_task = asyncio.create_task(edge_to_browser())
                done, pending = await asyncio.wait(
                    {browser_task, edge_task}, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                for task in done:
                    task.result()
    except TimeoutError:
        if ws.client_state.name == "CONNECTED":
            await ws.close(code=4408, reason="Session duration exceeded")
    except (OSError, websockets.WebSocketException):
        if ws.client_state.name == "CONNECTED":
            await ws.close(code=1011, reason="Private voice edge unavailable")
    except WebSocketDisconnect:
        pass
    finally:
        await release_connection()
