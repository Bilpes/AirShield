#!/usr/bin/env bash
#
# AirShield — one-command local run (web app + self-hosted voice edge).
#
# Starts BOTH:
#   1. The Next.js web UI  -> http://localhost:4174
#   2. The voice edge      -> ws://localhost:8001/ws/voice  (live microphone)
#
# so that Live Shield and CareShield Assistant can transcribe real voice.
# If you only run the web app (npm run dev) WITHOUT this, live voice fails
# with "Could not connect to the self-hosted voice edge on port 8001" —
# that is exactly what the edge being absent causes.

# --- option flags ---------------------------------------------------------
#   run_local.sh          start web + edge (foreground, Ctrl-C stops both)
#   run_local.sh --edge   start ONLY the edge (useful if web is run separately)
#   run_local.sh --web    start ONLY the web app
# ---------------------------------------------------------------------------

set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"

MODE="${1:-both}"
WEB_PORT=4174
EDGE_PORT=8001
EDGE_SCRIPT="$ROOT/edge-service/run_dev_edge.sh"

edge_pid=""
web_cmd() { echo "HOSTNAME=0.0.0.0 PORT=$WEB_PORT npx next dev --hostname 0.0.0.0 --port $WEB_PORT"; }

start_edge() {
  echo "==> Starting self-hosted voice edge on :$EDGE_PORT  (ws://localhost:$EDGE_PORT/ws/voice)"
  bash "$EDGE_SCRIPT" &
  edge_pid=$!
  # wait until it is reachable (up to 60s)
  for _ in $(seq 1 30); do
    if curl -sf "http://localhost:$EDGE_PORT/v1/health" >/dev/null 2>&1; then
      echo "==> Voice edge is HEALTHY: $(curl -s http://localhost:$EDGE_PORT/v1/health)"
      return 0
    fi
    sleep 2
  done
  echo "!! Voice edge did not come up on :$EDGE_PORT in 60s. See output above." >&2
  return 1
}

start_web() {
  echo "==> Starting web app on http://localhost:$WEB_PORT"
  echo "    Live voice requires the edge (ws://localhost:$EDGE_PORT/ws/voice)."
  # npx next dev in foreground; we run it through `exec`-less so edge keeps running
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
