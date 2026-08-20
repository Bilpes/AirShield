from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import secrets
import tempfile
import time
from collections import Counter
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .control_plane import ControlPlaneClient
from .models import (
    asr_model,
    diarization_pipeline,
    diarize,
    speaker_for_segment,
    transcribe,
    verify_model_manifest,
)
from .privacy import PrivacyEngine

control = ControlPlaneClient(settings) if settings.control_plane_url else None
privacy = PrivacyEngine() if control is None and settings.environment != "production" else None
inference_slots = asyncio.Semaphore(settings.max_concurrent_inference)


async def finish_inference_call(function: Callable[[Path], Any], path: Path) -> Any:
    task = asyncio.create_task(asyncio.to_thread(function, path))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        # A worker thread cannot be cancelled safely. Hold the slot and temp file
        # until it exits so disconnect storms cannot exceed the inference bound.
        await task
        raise


async def infer(path: Path) -> tuple[str, list[dict], list[dict]]:
    async with inference_slots:
        text, segments = await finish_inference_call(transcribe, path)
        turns = await finish_inference_call(diarize, path)
        return text, segments, turns


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.environment == "production":
        if control is None or not await control.ready():
            raise RuntimeError("Production privacy control plane is unavailable")
        await asyncio.to_thread(verify_model_manifest)
        await asyncio.to_thread(asr_model)
        if settings.enable_diarization and await asyncio.to_thread(diarization_pipeline) is None:
            raise RuntimeError("Configured production diarization model is unavailable")
    yield
    if control:
        await control.close()


app = FastAPI(title="AirShield Self-Hosted Voice Edge", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type", "x-airshield-edge-auth"],
)


class ProtectRequest(BaseModel):
    text: str
    policy: str = "finance-eu-us-v1"


def gateway_authorized(value: str | None) -> bool:
    if settings.environment != "production":
        return True
    expected = [
        secret for secret in (settings.gateway_shared_secret, settings.gateway_previous_secret) if secret
    ]
    comparisons = [hmac.compare_digest(value or "", secret) for secret in expected]
    return bool(value and any(comparisons))


def require_gateway(request: Request) -> None:
    if not gateway_authorized(request.headers.get("x-airshield-edge-auth")):
        raise HTTPException(401, "Authenticated private gateway required")


async def read_bounded(upload: UploadFile) -> bytes:
    output = bytearray()
    while chunk := await upload.read(1024 * 1024):
        output.extend(chunk)
        if len(output) > settings.max_audio_bytes:
            raise HTTPException(413, "Audio exceeds configured limit")
    return bytes(output)


def enforce_signed_final(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("decision") != "allow":
        return result
    receipt = result.get("receipt")
    signature = receipt.get("signature") if isinstance(receipt, dict) else None
    receipt_id = receipt.get("receipt_id") if isinstance(receipt, dict) else None
    if (
        isinstance(signature, str)
        and len(signature) >= 40
        and signature != "demo_unsigned"
        and isinstance(receipt_id, str)
        and receipt_id
    ):
        return result
    return {
        "protected_text": "",
        "entities": [],
        "decision": "block",
        "receipt": receipt,
        "reason_codes": ["signed_final_receipt_required"],
    }


def local_protect(text: str, vault: dict[str, str]) -> dict[str, Any]:
    if privacy is None:
        raise RuntimeError("Development privacy engine is disabled")
    protected, entities = privacy.protect(text, vault)
    return {
        "protected_text": protected,
        "entities": entities,
        "decision": "review",
        "receipt": {
            "receipt_id": "dev_" + secrets.token_hex(5),
            "content_sha256": hashlib.sha256(protected.encode()).hexdigest(),
            "entity_counts": dict(Counter(entity["type"] for entity in entities)),
            "reason_codes": ["development_only_unsigned"],
            "signature": "demo_unsigned",
        },
    }


@app.get("/v1/health/live")
async def live():
    return {"status": "alive"}


@app.get("/v1/health")
async def health(response: Response):
    control_ready = await control.ready() if control else False
    healthy = control_ready or settings.environment != "production"
    if not healthy:
        response.status_code = 503
    return {
        "status": "healthy" if healthy else "not_ready",
        "language": "en",
        "asr_model": settings.asr_model,
        "asr_device": settings.asr_device,
        "diarization": settings.enable_diarization,
        "privacy_mode": "control-plane" if control else "development-only-local",
        "control_plane_ready": control_ready,
        "paid_speech_api": False,
    }


@app.post("/v1/protect")
async def protect_route(body: ProtectRequest, request: Request):
    require_gateway(request)
    if control:
        session_id, policy = await control.create_session(body.policy)
        result = await control.protect(
            session_id=session_id,
            policy=policy,
            text=body.text,
            final_egress=True,
        )
        return enforce_signed_final(result)
    if settings.environment == "production":
        raise HTTPException(503, "Privacy control unavailable; egress denied")
    return local_protect(body.text, {})


@app.post("/v1/transcribe")
async def transcribe_file(
    request: Request,
    audio: Annotated[UploadFile, File()],
    policy: str = "healthcare-us-eu-v1",
):
    require_gateway(request)
    content = await read_bounded(audio)
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        path = Path(handle.name)
        handle.write(content)
    try:
        text, segments, turns = await infer(path)
        vault: dict[str, str] = {}
        control_session: str | None = None
        policy_id = policy
        if control:
            control_session, policy_id = await control.create_session(policy)
        output = []
        for index, segment in enumerate(segments):
            if control and control_session:
                result = await control.protect(
                    session_id=control_session,
                    policy=policy_id,
                    text=segment["text"],
                    final_egress=False,
                )
            else:
                result = local_protect(segment["text"], vault)
            output.append(
                {
                    "sequence": index,
                    "speaker_track": speaker_for_segment(segment, turns),
                    "raw": segment["text"],
                    "protected": result["protected_text"],
                    "entities": result["entities"],
                    "decision": result["decision"],
                    "safe_for_egress": False,
                    "start": segment["start"],
                    "end": segment["end"],
                }
            )
        return {"language": "en", "policy": policy_id, "transcript": output, "final_text": text}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"Voice processing unavailable: {type(exc).__name__}") from exc
    finally:
        path.unlink(missing_ok=True)


@app.websocket("/ws/voice")
async def voice_stream(ws: WebSocket):
    if not gateway_authorized(ws.headers.get("x-airshield-edge-auth")):
        await ws.close(code=4401, reason="Authenticated private gateway required")
        return
    await ws.accept()
    audio = bytearray()
    vault: dict[str, str] = {}
    last_text = ""
    sequence = 0
    last_process = 0.0
    policy = "healthcare-us-eu-v1"
    control_session: str | None = None
    speaker_bindings: dict[str, str] = {}
    audio_suffix = ".webm"

    async def process_current_audio(*, force: bool = False) -> bool:
        nonlocal last_text, last_process, sequence
        if not audio:
            return True
        now = time.monotonic()
        if not force and (
            len(audio) < settings.min_process_bytes or now - last_process < settings.process_interval_seconds
        ):
            return True
        last_process = now
        with tempfile.NamedTemporaryFile(suffix=audio_suffix, delete=False) as handle:
            handle.write(audio)
            path = Path(handle.name)
        try:
            text, segments, turns = await infer(path)
            if not text or text == last_text:
                return True
            delta = text[len(last_text) :].strip() if text.startswith(last_text) else text
            if not delta:
                return True
            last_text = text
            speaker = speaker_for_segment(segments[-1], turns) if segments else "SPEAKER_UNKNOWN"
            speaker_token = speaker_bindings.get(speaker)
            if control and control_session:
                result = await control.protect(
                    session_id=control_session,
                    policy=policy,
                    text=delta,
                    final_egress=False,
                    speaker_token=speaker_token,
                )
            elif settings.environment != "production":
                result = local_protect(delta, vault)
            else:
                raise RuntimeError("Control plane session unavailable")
            sequence += 1
            pair = {
                "type": "transcript.pair",
                "sequence": sequence,
                "speaker_track": speaker,
                "speaker": speaker.replace("_", " ").title(),
                "raw": delta,
                "protected": result["protected_text"],
                "entities": result["entities"],
                "decision": result["decision"],
                "time": round(segments[-1]["end"] if segments else 0, 1),
                "safe_for_egress": False,
                "provisional": True,
            }
            if speaker_token:
                pair["speaker_token"] = speaker_token
            await ws.send_json(pair)
            return True
        except Exception as exc:
            await ws.send_json(
                {
                    "type": "policy.decision",
                    "decision": "block",
                    "reason": type(exc).__name__,
                }
            )
            return False
        finally:
            path.unlink(missing_ok=True)

    try:
        while True:
            message = await ws.receive()
            if message.get("text"):
                event = json.loads(message["text"])
                event_type = event.get("type")
                if event_type == "session.start":
                    if event.get("language", "en") != "en":
                        await ws.send_json(
                            {"type": "policy.decision", "decision": "block", "reason": "english_only"}
                        )
                        continue
                    media_type = str(event.get("audio_format", "audio/webm")).lower().split(";", 1)[0]
                    suffixes = {"audio/webm": ".webm", "audio/mp4": ".mp4", "audio/ogg": ".ogg"}
                    if media_type not in suffixes:
                        await ws.send_json(
                            {
                                "type": "policy.decision",
                                "decision": "block",
                                "reason": "unsupported_audio_format",
                            }
                        )
                        break
                    audio_suffix = suffixes[media_type]
                    requested_policy = str(event.get("policy", policy))
                    if control:
                        control_session, policy = await control.create_session(requested_policy)
                        host_identity = event.get("host_identity")
                        if isinstance(host_identity, dict):
                            track = host_identity.get("speaker_track")
                            subject = host_identity.get("subject_token")
                            assurance = host_identity.get("assurance")
                            source = host_identity.get("source")
                            if (
                                not isinstance(track, str)
                                or not re.fullmatch(r"SPEAKER_[A-Z0-9]{1,8}", track)
                                or not isinstance(subject, str)
                                or not 3 <= len(subject) <= 256
                                or assurance != "sso_verified"
                                or source != "sso"
                            ):
                                await ws.send_json(
                                    {
                                        "type": "policy.decision",
                                        "decision": "block",
                                        "reason": "invalid_host_identity",
                                    }
                                )
                                break
                            try:
                                binding = await control.bind_identity(
                                    session_id=control_session,
                                    speaker_track=track,
                                    subject_token=subject,
                                    assurance=assurance,
                                    source=source,
                                )
                                speaker_bindings[track] = str(binding["llm_speaker_token"])
                            except Exception:
                                await ws.send_json(
                                    {
                                        "type": "policy.decision",
                                        "decision": "block",
                                        "reason": "identity_binding_unavailable",
                                    }
                                )
                                break
                    elif settings.environment == "production":
                        await ws.send_json(
                            {
                                "type": "policy.decision",
                                "decision": "block",
                                "reason": "control_plane_unavailable",
                            }
                        )
                        break
                    else:
                        policy = requested_policy
                    await ws.send_json(
                        {
                            "type": "session.ready",
                            "language": "en",
                            "policy": policy,
                            "model": settings.asr_model,
                            "interim_safe_for_egress": False,
                        }
                    )
                elif event_type == "session.end":
                    # Always process the last, possibly short, MediaRecorder chunk.
                    # Previously short utterances could end below the periodic byte
                    # threshold and therefore produced no transcript at all.
                    if not await process_current_audio(force=True):
                        break
                    if last_text and control and control_session:
                        final = enforce_signed_final(
                            await control.protect(
                                session_id=control_session,
                                policy=policy,
                                text=last_text,
                                final_egress=True,
                            )
                        )
                    elif last_text and settings.environment != "production":
                        final = local_protect(last_text, vault)
                    else:
                        final = {
                            "protected_text": "",
                            "entities": [],
                            "decision": "block" if settings.environment == "production" else "review",
                            "receipt": None,
                            "reason_codes": ["no_speech_detected"],
                        }
                    await ws.send_json(
                        {
                            "type": "transcript.final",
                            "protected": final["protected_text"],
                            "entities": final["entities"],
                            "decision": final["decision"],
                            "receipt": final["receipt"],
                            "reason_codes": final.get("reason_codes", []),
                            "safe_for_egress": final["decision"] == "allow",
                        }
                    )
                    break
            elif message.get("bytes"):
                audio.extend(message["bytes"])
                if len(audio) > settings.max_audio_bytes:
                    await ws.send_json(
                        {"type": "policy.decision", "decision": "block", "reason": "audio_limit"}
                    )
                    break
                if not await process_current_audio():
                    break
    except WebSocketDisconnect:
        pass
    finally:
        if ws.client_state.name == "CONNECTED":
            await ws.close()
