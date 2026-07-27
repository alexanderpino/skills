#!/usr/bin/env bash
# Run Terrain Studio locally.
#
# A service worker only registers on a SECURE ORIGIN - https, or http on localhost. It never runs
# from file://. So installability, offline mode and the update prompt can only be exercised through
# a served origin, which is what this script provides.
#
#   ./run-studio.sh              dev server with HMR (service worker NOT active)
#   ./run-studio.sh pwa          production build + preview - use this for install/offline/Lighthouse
#   ./run-studio.sh build        build only, no server
#   PORT=8080 ./run-studio.sh    override the port
#   NO_OPEN=1 ./run-studio.sh    do not launch a browser
set -euo pipefail

MODE="${1:-dev}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$REPO/apps/terrain-studio"

[ -d "$APP" ] || { echo "Cannot find $APP. Run this from the repository root." >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js not found on PATH. Install Node 20 or newer." >&2; exit 1; }

MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
[ "$MAJOR" -ge 20 ] || { echo "Node $MAJOR found; this project needs Node 20 or newer." >&2; exit 1; }

if [ ! -d "$REPO/node_modules" ]; then
  echo "Installing dependencies (first run)..."
  (cd "$REPO" && npm install --no-audit --no-fund)
fi

open_url() {
  [ -n "${NO_OPEN:-}" ] && return 0
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "$1" >/dev/null 2>&1 || true
  elif command -v open     >/dev/null 2>&1; then open "$1"     >/dev/null 2>&1 || true
  elif command -v start    >/dev/null 2>&1; then start "$1"    >/dev/null 2>&1 || true
  fi
}

cd "$APP"
case "$MODE" in
  build)
    npx vite build
    echo; echo "Built to $APP/dist"
    ;;
  dev)
    PORT="${PORT:-5173}"
    URL="http://127.0.0.1:$PORT/index.html"
    echo; echo "Terrain Studio (dev)  $URL"
    echo "Service worker is NOT active in dev - use './run-studio.sh pwa' to test install/offline."
    open_url "$URL"
    exec npx vite --port "$PORT" --strictPort
    ;;
  pwa)
    PORT="${PORT:-4173}"
    echo "Building production bundle..."
    npx vite build
    URL="http://127.0.0.1:$PORT/index.html"
    echo; echo "Terrain Studio (PWA)  $URL"
    echo "localhost counts as a secure origin, so the service worker registers here."
    echo "Install: address-bar install icon. Offline: DevTools > Network > Offline, then reload."
    open_url "$URL"
    exec npx vite preview --port "$PORT" --strictPort
    ;;
  *)
    echo "Unknown mode '$MODE'. Use: dev | pwa | build" >&2; exit 2
    ;;
esac
