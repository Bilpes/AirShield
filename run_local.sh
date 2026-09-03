#!/usr/bin/env bash
#
# AirShield — one-command LOCAL run (NO Docker required).
#
# Starts BOTH:
#   1. The Next.js web UI  -> http://localhost:4174
#   2. The voice edge      -> ws://localhost:8001/ws/voice  (live microphone)
#
# so that Live Shield and CareShield Assistant can transcribe real voice with
# everything running on this machine. Docker is never required for this path —
# `docker compose up` remains available as the full-stack alternative.
#
# If you only run the web app (npm run dev) WITHOUT the edge, live voice shows
# "Voice edge not running" — that is exactly what the edge being absent causes.
#
# Option flags:
#   run_local.sh          start web + edge (foreground, Ctrl-C stops both)
#   run_local.sh --edge   start ONLY the edge (useful if web is run separately)
#   run_local.sh --web    start ONLY the web app
#
# Environment overrides:
#   ASR_MODEL=small.en    higher-accuracy Whisper model (default: base.en)
#   WEB_PORT=4174 EDGE_PORT=8001

set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"

MODE="${1:-both}"
WEB_PORT="${WEB_PORT:-4174}"
EDGE_PORT="${EDGE_PORT:-8001}"
EDGE_SCRIPT="$ROOT/edge-service/run_dev_edge.sh"

edge_pid=""
edge_log="$(mktemp -t airshield-edge.XXXXXX.log)"

start_edge() {
  echo "==> Starting self-hosted voice edge on :$EDGE_PORT  (ws://localhost:$EDGE_PORT/ws/voice)"
  echo "    First run creates a Python venv, installs requirements, and downloads"
  echo "    the Whisper model — this can take several minutes. Log: $edge_log"
  bash "$EDGE_SCRIPT" >"$edge_log" 2>&1 &
  edge_pid=$!
  # Wait until the edge is reachable. First run includes venv creation, pip
  # installs and model download, so allow up to 10 minutes instead of failing
  # after 60s while the process is still working.
  local waited=0
  while [ "$waited" -lt 600 ]; do
    if ! kill -0 "$edge_pid" 2>/dev/null; then
      echo "!! Voice edge process exited during startup. Last log lines:" >&2
      tail -n 20 "$edge_log" >&2 || true
      return 1
    fi
    if curl -sf "http://localhost:$EDGE_PORT/v1/health" >/dev/null 2>&1; then
      echo "==> Voice edge is HEALTHY: $(curl -s http://localhost:$EDGE_PORT/v1/health)"
      return 0
    fi
    sleep 3
    waited=$((waited + 3))
    if [ $((waited % 30)) -eq 0 ]; then
      echo "    …edge still starting (${waited}s). See $edge_log"
    fi
  done
  echo "!! Voice edge did not come up on :$EDGE_PORT within 10 minutes." >&2
  echo "   Log tail:" >&2
  tail -n 20 "$edge_log" >&2 || true
  return 1
}

start_web() {
  if [ ! -d "$ROOT/node_modules" ]; then
    echo "==> Installing web dependencies (npm install)"
    (cd "$ROOT" && npm install)
  fi
  echo "==> Starting web app on http://localhost:$WEB_PORT"
  echo "    Live voice uses the local edge (ws://localhost:$EDGE_PORT/ws/voice)."
  npm run dev
}

cleanup() {
  echo ""
  echo "==> Stopping voice edge (pid ${edge_pid:-n/a})"
  if [ -n "$edge_pid" ]; then
    kill "$edge_pid" 2>/dev/null || true
    wait "$edge_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

case "$MODE" in
  --edge)
    start_edge
    echo "==> Edge running (foreground). Press Ctrl-C to stop."
    wait "$edge_pid"
    ;;
  --web)
    start_web
    ;;
  both|*)
    start_edge
    start_web
    ;;
esac
