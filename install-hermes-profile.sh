#!/usr/bin/env bash
# install-hermes-profile.sh — Automated Hermes Agent Profile Installer for Hermes Librarian
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PROFILE_NAME="${1:-librarian}"

echo "========================================================"
echo "  🤖 Hermes Librarian — Hermes Agent Profile Setup"
echo "========================================================"

# 1. Locate hermes CLI
HERMES_BIN=""
if command -v hermes >/dev/null 2>&1; then
    HERMES_BIN="hermes"
elif [ -x "$HOME/.local/bin/hermes" ]; then
    HERMES_BIN="$HOME/.local/bin/hermes"
elif [ -x "$HOME/.hermes/hermes-agent/venv/bin/hermes" ]; then
    HERMES_BIN="$HOME/.hermes/hermes-agent/venv/bin/hermes"
fi

if [ -z "$HERMES_BIN" ]; then
    echo "❌ Error: Hermes Agent CLI ('hermes') was not found." >&2
    echo "   Install Hermes Agent first, or ensure ~/.local/bin is in your PATH." >&2
    exit 1
fi

echo "✓ Found Hermes Agent CLI: $HERMES_BIN"

# 2. Check or create profile
PROFILES_DIR="$HOME/.hermes/profiles"
PROFILE_DIR="$PROFILES_DIR/$PROFILE_NAME"

if "$HERMES_BIN" profile list 2>/dev/null | grep -qw "$PROFILE_NAME"; then
    echo "→ Profile '$PROFILE_NAME' already exists. Updating configuration..."
else
    echo "→ Creating new Hermes profile '$PROFILE_NAME' (cloning base settings)..."
    "$HERMES_BIN" profile create "$PROFILE_NAME" --clone \
        --description "Digital librarian, offline reader, and Obsidian research partner."
    echo "✓ Profile '$PROFILE_NAME' created."
fi

# 3. Install/symlink skill
SKILLS_DIR="$PROFILE_DIR/skills/note-taking"
mkdir -p "$SKILLS_DIR"
SKILL_TARGET="$SKILLS_DIR/hermes-librarian"

if [ -L "$SKILL_TARGET" ] || [ -d "$SKILL_TARGET" ]; then
    rm -rf "$SKILL_TARGET"
fi

ln -s "$DIR/skill" "$SKILL_TARGET"
echo "✓ Symlinked skill to $SKILL_TARGET"

# 4. Install SOUL.md persona
cp "$DIR/SOUL.md" "$PROFILE_DIR/SOUL.md"
echo "✓ Copied SOUL.md to $PROFILE_DIR/SOUL.md"

# 5. Configure HLIB_ROOT in profile .env
ENV_FILE="$PROFILE_DIR/.env"
touch "$ENV_FILE"

if grep -q "HLIB_ROOT=" "$ENV_FILE"; then
    sed -i "s|^HLIB_ROOT=.*|HLIB_ROOT=\"$DIR\"|" "$ENV_FILE"
else
    echo "HLIB_ROOT=\"$DIR\"" >> "$ENV_FILE"
fi
echo "✓ Configured HLIB_ROOT in $ENV_FILE"

# 6. Verify skill registration
if "$HERMES_BIN" -p "$PROFILE_NAME" skills list 2>/dev/null | grep -qi "hermes-librarian"; then
    echo "✓ Hermes Librarian skill verified and active."
fi

echo "========================================================"
echo "  ✅ Hermes Profile '$PROFILE_NAME' is ready!"
echo "========================================================"
echo "  Start chatting : $PROFILE_NAME chat"
echo "  Or via flag    : hermes -p $PROFILE_NAME chat"
echo "========================================================"
