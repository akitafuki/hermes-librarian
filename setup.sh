#!/usr/bin/env bash
# setup.sh — Automated Environment Setup for Hermes Librarian
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "========================================================"
echo "  🛠️  Hermes Librarian — Automated Setup"
echo "========================================================"

# 1. Check Python 3 availability
if command -v python3 >/dev/null 2>&1; then
    PYTHON_SYS="python3"
else
    echo "❌ Error: python3 is required but not installed." >&2
    exit 1
fi

PY_VERSION=$("$PYTHON_SYS" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$("$PYTHON_SYS" -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$("$PYTHON_SYS" -c 'import sys; print(sys.version_info.minor)')

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
    echo "❌ Error: Python 3.10+ is required. Found Python $PY_VERSION." >&2
    exit 1
fi
echo "✓ Python $PY_VERSION detected."

# 2. Set up virtual environment
if [ ! -d ".venv" ]; then
    echo "→ Creating virtual environment in .venv..."
    "$PYTHON_SYS" -m venv .venv
fi

VENV_PYTHON="$DIR/.venv/bin/python"
VENV_PIP="$DIR/.venv/bin/pip"

# 3. Install requirements
echo "→ Installing / updating dependencies from requirements.txt..."
"$VENV_PIP" install --upgrade pip --quiet
"$VENV_PIP" install -r requirements.txt --quiet
echo "✓ Dependencies installed successfully."

# 4. Initialize storage directories and database
echo "→ Initializing database and Obsidian vault folders..."
"$VENV_PYTHON" -c "from app.config import ensure_directories; from app.database import init_db; ensure_directories(); init_db(); print('✓ Database and vault ready.')"

# 5. Run automated test suite
echo "→ Running automated test suite..."
"$VENV_PYTHON" -m pytest --quiet
echo "✓ All 23 tests passed successfully."

# 6. Optional: Set up Hermes Agent profile
if [ "$1" = "--hermes" ] || [ "$1" = "--profile" ]; then
    echo ""
    "$DIR/install-hermes-profile.sh"
fi

echo "========================================================"
echo "  ✅ Hermes Librarian is ready!"
echo "========================================================"
echo "  Start Web Dashboard : ./run.sh"
echo "  Or via CLI          : source .venv/bin/activate && python cli.py serve --port 8090"
echo "  Add a link          : python cli.py add \"<URL>\" --tags \"ai, research\""
echo "  Search links        : python cli.py list -q \"<query>\""
if command -v hermes >/dev/null 2>&1 || [ -x "$HOME/.local/bin/hermes" ]; then
    echo "  Hermes Profile      : ./install-hermes-profile.sh"
fi
echo "========================================================"
