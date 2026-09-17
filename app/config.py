"""Application configuration and environment settings."""
from __future__ import annotations

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent

# Storage configuration
DEFAULT_DATA_DIR = Path(os.environ.get("HLIB_DATA_DIR", BASE_DIR / "data"))
DATA_DIR = DEFAULT_DATA_DIR.resolve()
VAULT_DIR = Path(os.environ.get("HLIB_VAULT_DIR", DATA_DIR / "vault")).resolve()
LINKS_VAULT_DIR = VAULT_DIR / "links"
BRIEFINGS_VAULT_DIR = VAULT_DIR / "briefings"
ASSETS_VAULT_DIR = VAULT_DIR / "assets"
SNAPSHOTS_DIR = ASSETS_VAULT_DIR / "snapshots"
DB_PATH = Path(os.environ.get("HLIB_DB_PATH", DATA_DIR / "links.db")).resolve()

# Server configuration
APP_HOST = os.environ.get("HLIB_HOST", "127.0.0.1")
APP_PORT = int(os.environ.get("HLIB_PORT", "8090"))
HLIB_API_KEY = os.environ.get("HLIB_API_KEY", "").strip() or None
APP_TITLE = "Hermes Librarian"
APP_DESCRIPTION = "Personal link archiver, offline reader, and Obsidian research vault."

def ensure_directories():
    """Ensure all required directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    LINKS_VAULT_DIR.mkdir(parents=True, exist_ok=True)
    BRIEFINGS_VAULT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_VAULT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

ensure_directories()
