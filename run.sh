#!/usr/bin/env bash
# run.sh — Launch Hermes Librarian
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Check for virtualenv
if [ -d ".venv" ]; then
    PYTHON="$DIR/.venv/bin/python"
elif [ -x "$HOME/.hermes/hermes-agent/venv/bin/python" ]; then
    PYTHON="$HOME/.hermes/hermes-agent/venv/bin/python"
else
    PYTHON="python3"
fi

PORT="${HLIB_PORT:-8090}"
HOST="${HLIB_HOST:-0.0.0.0}"

LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')

echo "════════════════════════════════════════════════════════"
echo "  🚀 Launching Hermes Librarian"
echo "════════════════════════════════════════════════════════"
echo "  Local URL:     http://localhost:$PORT"
if [ -n "$LAN_IP" ]; then
echo "  LAN Access:    http://$LAN_IP:$PORT"
fi
echo "  Data Dir:      $DIR/data"
echo "  Vault Dir:     $DIR/data/vault"
echo "  Database:      $DIR/data/links.db"
echo "════════════════════════════════════════════════════════"

exec "$PYTHON" cli.py serve --host "$HOST" --port "$PORT"
