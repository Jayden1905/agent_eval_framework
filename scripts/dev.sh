#!/usr/bin/env bash
# Spawn cloudflared quick tunnel, then start uvicorn with TUNNEL_URL set so
# the backend can rewrite localhost agent URLs before handing them to the
# sandbox (which can't reach the mac's localhost).
#
# Kills the tunnel on exit / Ctrl-C via trap. Run: `make dev`.
set -euo pipefail

PORT=${PORT:-8000}
CF_LOG=$(mktemp -t agenteval-cf.XXXXXX)
trap 'kill $(jobs -p) 2>/dev/null || true; rm -f "$CF_LOG"' EXIT INT TERM

echo "==> spawning cloudflared quick tunnel on :$PORT"
cloudflared tunnel --url "http://localhost:$PORT" >"$CF_LOG" 2>&1 &

URL=""
for _ in $(seq 1 60); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$CF_LOG" | head -n1 || true)
  [ -n "$URL" ] && break
  sleep 0.5
done
if [ -z "$URL" ]; then
  echo "!! cloudflared did not report a trycloudflare URL within 30s"
  cat "$CF_LOG"
  exit 1
fi
echo "    tunnel: $URL"
sleep 3

SSL_CERT_FILE=$(.venv/bin/python -m certifi) \
TUNNEL_URL="$URL" \
  uvicorn backend.server:app --reload --port "$PORT"
