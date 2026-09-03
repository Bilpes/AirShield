#!/usr/bin/env bash
#
# AirShield — local development voice edge (NO Docker required).
#
# Boots the self-hosted English voice edge on http://localhost:8001 so the
# Next.js web app (npm run dev on http://localhost:4174) can do live
# microphone transcription through ws://localhost:8001/ws/voice.
#
# Development mode only: uses the in-memory local PII/masking engine and a
# pinned development-only receipt signing key. It does NOT require the control
# plane, Postgres, the authenticated gateway, or Docker. It does NOT send audio
# anywhere — Whisper runs locally on this machine, nothing is uploaded.
#
# Requirements on this machine:
#   - Python 3.11+ and pip (3.12 is used by the production Docker image)
#   - ~200 MB free disk for the faster-whisper "base.en" model on first run
#     (set ASR_MODEL=small.en for higher accuracy, ~460 MB)
#   - ffmpeg/libsndfile are NOT required to install: audio decoding uses the
#     PyAV-bundled ffmpeg libraries. (The Dockerfile installs system ffmpeg for
#     parity; the local venv path works without it.)

set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"

# Model size is overridable: ASR_MODEL=small.en ./run_dev_edge.sh
export ASR_MODEL="${ASR_MODEL:-base.en}"
export ASR_DEVICE="${ASR_DEVICE:-cpu}"
export ASR_COMPUTE_TYPE="${ASR_COMPUTE_TYPE:-int8}"
export LANGUAGE="${LANGUAGE:-en}"
export ENVIRONMENT="${ENVIRONMENT:-development}"
export AIRSHIELD_ALLOW_INSECURE_LOCAL_EDGE="${AIRSHIELD_ALLOW_INSECURE_LOCAL_EDGE:-true}"
# Accept both localhost and 127.0.0.1 web origins, plus common preview ports.
export ALLOW_ORIGINS="${ALLOW_ORIGINS:-http://localhost:4174,http://127.0.0.1:4174}"

# 1) Python virtualenv
if [ ! -d ".venv" ]; then
  echo "==> Creating virtualenv (.venv)"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate

# 2) Requirements (idempotent)
echo "==> Installing edge requirements (first run may take a few minutes)"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 3) Optional spaCy English model (used by Presidio contextual detection).
#    This is an enhancement, not a requirement: deterministic PII/PHI rules run
#    without it, so do not fail startup if the wheel host is unreachable.
if ! python -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null; then
  echo "==> Installing optional en_core_web_sm spaCy model (Presidio contextual detection)"
  if ! pip install --quiet \
      https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl; then
    echo "    (skipped: model download unavailable; deterministic privacy rules still run)"
  fi
fi

# 4) Boot the edge in development mode
echo "==> Starting voice edge on http://localhost:8001"
echo "    Health:  curl http://localhost:8001/v1/health"
echo "    WS:      ws://localhost:8001/ws/voice  (used by the web app)"
echo "    Web app should run with NEXT_PUBLIC_EDGE_WS_URL=ws://localhost:8001/ws/voice"
echo "    (already the committed .env.local default). Press Ctrl-C to stop."
exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --no-proxy-headers
