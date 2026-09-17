"""Unit tests for Obsidian vault serialization, frontmatter parsing, and briefings."""
from datetime import datetime
from pathlib import Path
import frontmatter
import pytest

from app.vault import (
    slugify, save_link_to_vault, update_master_index,
    import_vault_to_database, create_vault_briefing
)
from app.models import Link, LinkStatus, LinkType, Highlight
from app.config import LINKS_VAULT_DIR, VAULT_DIR, BRIEFINGS_VAULT_DIR


def test_slugify():
    assert slugify("Attention Is All You Need") == "attention-is-all-you-need"
    assert slugify("Hello, World! 123?") == "hello-world-123"
    assert slugify("---Leading and trailing---") == "leading-and-trailing"


def test_save_link_to_vault_and_frontmatter():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    link = Link(
        id="vlt001",
        url="https://arxiv.org/abs/1706.03762",
        title="Attention Is All You Need",
        author="Vaswani et al.",
        domain="arxiv.org",
        entry_type=LinkType.PAPER,
        tags=["ai", "transformers"],
        status=LinkStatus.READING,
        summary="Introduces the Transformer architecture based on self-attention.",
        content_markdown="Full paper content body here.",
        user_notes="Groundbreaking paper",
        highlights=[Highlight(id="h1", text="Dispensing with recurrence and convolutions entirely.")],
        media_meta={"arxiv_id": "1706.03762", "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf"},
        created_at=now,
        updated_at=now,
    )

    file_path = save_link_to_vault(link)
    assert file_path.exists()

    # Load and verify frontmatter
    post = frontmatter.load(file_path)
    assert post.metadata["id"] == "vlt001"
    assert post.metadata["title"] == "Attention Is All You Need"
    assert post.metadata["status"] == "reading"
    assert "ai" in post.metadata["tags"]
    assert len(post.metadata["highlights"]) == 1

    # Verify body sections
    content = post.content
    assert "## Summary" in content
    assert "Introduces the Transformer architecture" in content
    assert "## Highlights & Quotes" in content
    assert "Dispensing with recurrence" in content
    assert "## Personal Notes" in content
    assert "Groundbreaking paper" in content


def test_master_index_generation():
    update_master_index()
    index_file = VAULT_DIR / "INDEX.md"
    assert index_file.exists()
    content = index_file.read_text(encoding="utf-8")
    assert "# Link Vault Index" in content
    assert "| Date | Title | Type | Tags | Status | Highlights |" in content


def test_create_vault_briefing():
    import app.config as cfg
    briefing_file = create_vault_briefing(days=30, title="Monthly Research Review", custom_notes="Testing briefing synthesis.")
    assert briefing_file.exists()
    assert briefing_file.parent == cfg.BRIEFINGS_VAULT_DIR

    post = frontmatter.load(briefing_file)
    assert post.metadata["title"] == "Monthly Research Review"
    assert post.metadata["type"] == "briefing"

    content = post.content
    assert "## Executive Summary" in content
    assert "Testing briefing synthesis." in content
    assert "## Reading Pipeline" in content
    assert "## Captured Resources" in content
    assert "[[" in content  # Wikilinks generated
