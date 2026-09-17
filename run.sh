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
HOST="${HLIB_HOST:-127.0.0.1}"

echo "════════════════════════════════════════════════════════"
echo "  🚀 Launching Hermes Librarian"
echo "════════════════════════════════════════════════════════"
echo "  Dashboard URL: http://$HOST:$PORT"
echo "  Data Dir:      $DIR/data"
echo "  Vault Dir:     $DIR/data/vault"
echo "  Database:      $DIR/data/links.db"
echo "════════════════════════════════════════════════════════"

exec "$PYTHON" cli.py serve --host "$HOST" --port "$PORT"
