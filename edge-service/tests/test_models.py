import hashlib
import json
from pathlib import Path

import pytest

from app import models


def write_manifest(root: Path, artifact: Path) -> tuple[Path, str]:
    content = json.dumps(
        {
            "format": 1,
            "files": {str(artifact.relative_to(root)): hashlib.sha256(artifact.read_bytes()).hexdigest()},
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    manifest = root / "manifest.json"
    manifest.write_bytes(content)
    return manifest, hashlib.sha256(content).hexdigest()


def test_model_manifest_covers_and_detects_tampered_asr_artifact(tmp_path: Path, monkeypatch):
    model = tmp_path / "whisper-small-en"
    model.mkdir()
    artifact = model / "model.bin"
    artifact.write_bytes(b"evaluated-model-artifact")
    manifest, manifest_hash = write_manifest(tmp_path, artifact)
    monkeypatch.setattr(models.settings, "asr_model", str(model))
    monkeypatch.setattr(models.settings, "enable_diarization", False)
    monkeypatch.setattr(models.settings, "model_manifest_path", manifest)
    monkeypatch.setattr(models.settings, "model_manifest_sha256", manifest_hash)

    models.verify_model_manifest()
    artifact.write_bytes(b"tampered-model-artifact")
    with pytest.raises(RuntimeError, match="artifact digest mismatch"):
        models.verify_model_manifest()
