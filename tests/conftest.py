"""Pytest test fixtures and isolated environment setup."""
import os
import tempfile
from pathlib import Path
import pytest


@pytest.fixture(scope="session", autouse=True)
def test_env(tmp_path_factory):
    """Set up an isolated data directory, vault, and database for the test run."""
    temp_dir = tmp_path_factory.mktemp("hlib_test_data")

    import app.config as cfg
    cfg.DATA_DIR = temp_dir
    cfg.VAULT_DIR = temp_dir / "vault"
    cfg.LINKS_VAULT_DIR = cfg.VAULT_DIR / "links"
    cfg.BRIEFINGS_VAULT_DIR = cfg.VAULT_DIR / "briefings"
    cfg.ASSETS_VAULT_DIR = cfg.VAULT_DIR / "assets"
    cfg.SNAPSHOTS_DIR = cfg.ASSETS_VAULT_DIR / "snapshots"
    cfg.DB_PATH = temp_dir / "links.db"

    import app.database as db
    import app.vault as vault
    import app.extractor as extractor
    import app.routes.api as api_routes

    db.DB_PATH = cfg.DB_PATH
    vault.VAULT_DIR = cfg.VAULT_DIR
    vault.LINKS_VAULT_DIR = cfg.LINKS_VAULT_DIR
    vault.BRIEFINGS_VAULT_DIR = cfg.BRIEFINGS_VAULT_DIR
    extractor.SNAPSHOTS_DIR = cfg.SNAPSHOTS_DIR
    api_routes.VAULT_DIR = cfg.VAULT_DIR
    api_routes.LINKS_VAULT_DIR = cfg.LINKS_VAULT_DIR
    api_routes.BRIEFINGS_VAULT_DIR = cfg.BRIEFINGS_VAULT_DIR

    cfg.ensure_directories()
    db.init_db()

    yield temp_dir
