from __future__ import annotations

import hashlib
import hmac
import json
from functools import lru_cache
from pathlib import Path

from .config import settings


def verify_model_manifest() -> None:
    manifest_path = settings.model_manifest_path
    content = manifest_path.read_bytes()
    actual_manifest_hash = hashlib.sha256(content).hexdigest()
    if not settings.model_manifest_sha256 or not hmac.compare_digest(
        actual_manifest_hash, settings.model_manifest_sha256
    ):
        raise RuntimeError("Model manifest digest mismatch")
    try:
        manifest = json.loads(content)
        files = manifest["files"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RuntimeError("Model manifest is invalid") from exc
    if manifest.get("format") != 1 or not isinstance(files, dict) or not 1 <= len(files) <= 10_000:
        raise RuntimeError("Model manifest has an unsupported format or file count")

    root = manifest_path.parent.resolve()
    required_roots = [Path(settings.asr_model).resolve()]
    if settings.enable_diarization:
        required_roots.append(Path(settings.pyannote_model).resolve())
    covered_roots: set[Path] = set()
    for relative, expected in files.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise RuntimeError("Model manifest entries must be path/digest strings")
        if not hmac.compare_digest(expected, expected.lower()) or len(expected) != 64:
            raise RuntimeError("Model manifest contains an invalid digest")
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise RuntimeError("Model manifest path escapes its root")
        unresolved = root / relative_path
        current = root
        for part in relative_path.parts:
            current /= part
            if current.is_symlink():
                raise RuntimeError("Model artifact paths cannot contain symlinks")
        candidate = unresolved.resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise RuntimeError("Model manifest path escapes its root") from exc
        if candidate.is_symlink() or not candidate.is_file():
            raise RuntimeError("Model artifact is missing or is a symlink")
        digest = hashlib.sha256()
        with candidate.open("rb") as artifact:
            while chunk := artifact.read(1024 * 1024):
                digest.update(chunk)
        if not hmac.compare_digest(digest.hexdigest(), expected):
            raise RuntimeError("Model artifact digest mismatch")
        for required_root in required_roots:
            if candidate == required_root or required_root in candidate.parents:
                covered_roots.add(required_root)
    if covered_roots != set(required_roots):
        raise RuntimeError("Model manifest does not cover every configured model")


@lru_cache(maxsize=1)
def asr_model():
    from faster_whisper import WhisperModel

    print(
        f"Loading local ASR model {settings.asr_model} on {settings.asr_device}/{settings.asr_compute_type}"
    )
    return WhisperModel(
        settings.asr_model, device=settings.asr_device, compute_type=settings.asr_compute_type
    )


def transcribe(audio_path: Path) -> tuple[str, list[dict]]:
    segments, info = asr_model().transcribe(
        str(audio_path), language="en", vad_filter=True, beam_size=3, condition_on_previous_text=False
    )
    rows = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            rows.append({"start": segment.start, "end": segment.end, "text": text})
    return " ".join(row["text"] for row in rows).strip(), rows


@lru_cache(maxsize=1)
def diarization_pipeline():
    if not settings.enable_diarization:
        return None
    try:
        from pyannote.audio import Pipeline

        return Pipeline.from_pretrained(settings.pyannote_model, use_auth_token=settings.hf_token)
    except Exception as exc:
        print(f"Diarization unavailable; single-track mode: {exc}")
        return None


def diarize(audio_path: Path) -> list[dict]:
    pipeline = diarization_pipeline()
    if not pipeline:
        return []
    result = pipeline(str(audio_path))
    rows = []
    for turn, _, speaker in result.itertracks(yield_label=True):
        rows.append({"start": turn.start, "end": turn.end, "speaker": speaker})
    return rows


def speaker_for_segment(segment: dict, turns: list[dict]) -> str:
    if not turns:
        return "SPEAKER_A"
    midpoint = (segment["start"] + segment["end"]) / 2
    matching = [t for t in turns if t["start"] <= midpoint <= t["end"]]
    return matching[0]["speaker"] if matching else "UNKNOWN"
