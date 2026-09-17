"""Unit tests for SQLite database operations, FTS5 search, and highlights."""
from datetime import datetime
import pytest

from app.database import (
    save_link, get_link, get_link_by_url, update_link, delete_link,
    list_links, get_stats, get_graph_data, add_highlight, delete_highlight,
    get_links_since
)
from app.models import Link, LinkStatus, LinkType, LinkUpdate, Highlight


def create_sample_link(link_id: str = "test001", title: str = "Test Title", url: str = "https://example.com/test"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return Link(
        id=link_id,
        url=url,
        title=title,
        author="Test Author",
        site_name="Example Site",
        domain="example.com",
        entry_type=LinkType.ARTICLE,
        tags=["python", "testing", "ai"],
        status=LinkStatus.INBOX,
        summary="This is a test summary about artificial intelligence and python testing.",
        content_markdown="Full content body for testing SQLite FTS5 search queries.",
        word_count=50,
        reading_time_minutes=1,
        created_at=now,
        updated_at=now,
    )


def test_save_and_get_link():
    link = create_sample_link(link_id="db001", url="https://example.com/db001")
    save_link(link)

    fetched = get_link("db001")
    assert fetched is not None
    assert fetched.id == "db001"
    assert fetched.title == "Test Title"
    assert "python" in fetched.tags
    assert fetched.status == LinkStatus.INBOX

    by_url = get_link_by_url("https://example.com/db001")
    assert by_url is not None
    assert by_url.id == "db001"


def test_update_link():
    link = create_sample_link(link_id="db002", url="https://example.com/db002")
    save_link(link)

    updates = LinkUpdate(
        status=LinkStatus.READING,
        tags=["updated-tag"],
        user_notes="Important note",
    )
    updated = update_link("db002", updates)
    assert updated is not None
    assert updated.status == LinkStatus.READING
    assert updated.tags == ["updated-tag"]
    assert updated.user_notes == "Important note"


def test_delete_link():
    link = create_sample_link(link_id="db003", url="https://example.com/db003")
    save_link(link)

    assert get_link("db003") is not None
    deleted = delete_link("db003")
    assert deleted is True
    assert get_link("db003") is None


def test_fts5_full_text_search():
    link1 = create_sample_link(
        link_id="fts001",
        title="Deep Learning with PyTorch",
        url="https://example.com/pytorch",
    )
    link1.summary = "A comprehensive tutorial on neural networks and backpropagation."
    save_link(link1)

    link2 = create_sample_link(
        link_id="fts002",
        title="Database Optimization in SQLite",
        url="https://example.com/sqlite-perf",
    )
    link2.summary = "Techniques for index tuning and WAL mode concurrency."
    save_link(link2)

    # Search for PyTorch / neural
    results, total = list_links(query="neural")
    assert total >= 1
    ids = [r.id for r in results]
    assert "fts001" in ids

    # Search for WAL mode / SQLite
    results_sqlite, total_sqlite = list_links(query="concurrency")
    assert total_sqlite >= 1
    assert any(r.id == "fts002" for r in results_sqlite)


def test_filter_links_by_status_and_tag():
    link = create_sample_link(link_id="filter001", url="https://example.com/filter001")
    link.status = LinkStatus.FAVORITE
    link.tags = ["unique-tag-xyz"]
    save_link(link)

    # Filter by tag
    results, count = list_links(tag="unique-tag-xyz")
    assert count >= 1
    assert any(r.id == "filter001" for r in results)

    # Filter by status
    results_fav, count_fav = list_links(status="favorite")
    assert any(r.id == "filter001" for r in results_fav)


def test_highlights_crud():
    link = create_sample_link(link_id="hl001", url="https://example.com/hl001")
    save_link(link)

    hl = Highlight(id="quote1", text="This is a highlighted quotation.", note="Remarkable statement")
    updated = add_highlight("hl001", hl)
    assert len(updated.highlights) == 1
    assert updated.highlights[0].text == "This is a highlighted quotation."

    # Delete highlight
    after_del = delete_highlight("hl001", "quote1")
    assert len(after_del.highlights) == 0


def test_get_stats():
    stats = get_stats()
    assert stats.total_links >= 1
    assert "inbox" in stats.by_status or "reading" in stats.by_status or "favorite" in stats.by_status


def test_get_links_since():
    link = create_sample_link(link_id="since001", url="https://example.com/since001")
    save_link(link)

    items = get_links_since("2020-01-01 00:00:00")
    assert any(i.id == "since001" for i in items)
