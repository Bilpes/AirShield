#!/usr/bin/env bash
#
# AirShield — local development voice edge.
#
# Boots the self-hosted English voice edge on http://localhost:8001 so the
# Next.js web app (npm run dev on http://localhost:4174) can do live
# microphone transcription through ws://localhost:8001/ws/voice.
#
# Development mode only: uses the in-memory local PII/masking engine and
# does NOT require the control plane, Postgres, or the authenticated gateway.
# It does NOT send audio anywhere — Whisper runs locally, nothing is uploaded.
#
# Requirements on this machine:
#   - Python 3.12+ and pip
#   - ffmpeg and libsndfile (whisper decodes via ffmpeg; try:
#       sudo apt-get install -y ffmpeg libsndfile1   # Debian/Ubuntu
#       brew install ffmpeg libsndfile               # macOS
#     )
#   - ~1.5 GB free disk for the faster-whisper "small.en" model on first run.

set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"

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

# 3) Pinned spaCy English model (used by Presidio contextual detection)
if ! python -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null; then
  echo "==> Installing pinned en_core_web_sm spaCy model"
  pip install --quiet \
    https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
fi

# 4) Boot the edge in development mode
echo "==> Starting voice edge on http://localhost:8001"
echo "    Health:  curl http://localhost:8001/v1/health"
echo "    WS:      ws://localhost:8001/ws/voice  (used by the web app)"
echo "    Web app should already be running with NEXT_PUBLIC_EDGE_WS_URL=ws://localhost:8001/ws/voice"
echo "    Press Ctrl-C to stop."
ENVIRONMENT=development \
AIRSHIELD_ALLOW_INSECURE_LOCAL_EDGE=true \
ALLOW_ORIGINS="http://localhost:4174" \
exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --no-proxy-headers
