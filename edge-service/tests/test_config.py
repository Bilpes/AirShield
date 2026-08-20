import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings


def manifest_fixture(tmp_path: Path) -> tuple[Path, str]:
    manifest = tmp_path / "manifest.json"
    content = b'{"format":1,"files":{}}'
    manifest.write_bytes(content)
    return manifest, hashlib.sha256(content).hexdigest()


def test_production_rejects_local_only_privacy_path(tmp_path: Path):
    model = tmp_path / "whisper"
    model.mkdir()
    manifest, digest = manifest_fixture(tmp_path)
    with pytest.raises(ValidationError, match="CONTROL_PLANE_URL"):
        Settings(
            environment="production",
            asr_model=str(model),
            model_manifest_path=manifest,
            model_manifest_sha256=digest,
            gateway_shared_secret="x" * 32,
        )


def test_production_accepts_projected_workload_identity(tmp_path: Path):
    token = tmp_path / "token"
    token.write_text("signed-workload-token")
    model = tmp_path / "whisper"
    model.mkdir()
    ca = tmp_path / "control-plane-ca.crt"
    ca.write_text("test-ca-placeholder")
    manifest, digest = manifest_fixture(tmp_path)
    settings = Settings(
        environment="production",
        asr_model=str(model),
        model_manifest_path=manifest,
        model_manifest_sha256=digest,
        control_plane_url="https://control.internal",
        control_plane_ca_file=ca,
        control_plane_token_file=token,
        gateway_shared_secret="x" * 32,
    )
    assert settings.control_plane_token_file == token


def test_previous_gateway_secret_must_be_distinct(tmp_path: Path):
    token = tmp_path / "token"
    token.write_text("signed-workload-token")
    model = tmp_path / "whisper"
    model.mkdir()
    ca = tmp_path / "control-plane-ca.crt"
    ca.write_text("test-ca-placeholder")
    manifest, digest = manifest_fixture(tmp_path)
    with pytest.raises(ValidationError, match="strong and distinct"):
        Settings(
            environment="production",
            asr_model=str(model),
            model_manifest_path=manifest,
            model_manifest_sha256=digest,
            control_plane_url="https://control.internal",
            control_plane_ca_file=ca,
            control_plane_token_file=token,
            gateway_shared_secret="x" * 32,  # noqa: S106 - test secret
            gateway_previous_secret="x" * 32,  # noqa: S106 - equality under test
        )
