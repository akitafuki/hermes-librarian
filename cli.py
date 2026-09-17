#!/usr/bin/env python3
"""
Command-line interface for Hermes Librarian.

Usage:
    python cli.py add "https://github.com/..." --tags "ai, dev-tools" --status inbox
    python cli.py list -q "keyword"
    python cli.py view <id_or_url>
    python cli.py digest --days 7
    python cli.py update <id_or_url> --status reading
    python cli.py stats
    python cli.py reindex
    python cli.py serve --port 8090
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
import uuid

from app.config import APP_HOST, APP_PORT, ensure_directories
from app.database import (
    init_db, save_link, list_links, get_link, get_link_by_url,
    get_stats, delete_link, update_link
)
from app.extractor import fetch_and_extract
from app.models import Link, LinkStatus, LinkType, LinkUpdate
from app.vault import save_link_to_vault, import_vault_to_database, create_vault_briefing


def resolve_link(target: str) -> Link | None:
    """Find a link by either ID or URL."""
    link = get_link(target)
    if not link:
        link = get_link_by_url(target)
    return link


def cmd_add(args):
    """Add and archive a URL."""
    ensure_directories()
    init_db()

    url = args.url.strip()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    link_id = str(uuid.uuid4())[:8]

    print(f"→ Fetching and extracting: {url}...")
    extracted = asyncio.run(fetch_and_extract(url, link_id=link_id))

    tags = [t.strip().lstrip("#") for t in args.tags.split(",") if t.strip()] if args.tags else extracted["tags"]
    status = LinkStatus(args.status) if args.status else LinkStatus.INBOX
    entry_type = LinkType(args.type) if args.type else extracted["entry_type"]
    title = args.title or extracted["title"]

    link = Link(
        id=link_id,
        url=extracted["url"],
        title=title,
        author=extracted.get("author"),
        site_name=extracted.get("site_name"),
        domain=extracted.get("domain"),
        entry_type=entry_type,
        tags=tags,
        status=status,
        summary=extracted.get("summary", ""),
        user_notes=args.notes,
        content_markdown=extracted.get("content_markdown", ""),
        cover_image=extracted.get("cover_image"),
        favicon=extracted.get("favicon"),
        reading_time_minutes=extracted.get("reading_time_minutes", 1),
        word_count=extracted.get("word_count", 0),
        created_at=now_str,
        updated_at=now_str,
        media_meta=extracted.get("media_meta", {}),
        offline_snapshot_path=extracted.get("offline_snapshot_path"),
    )

    vault_file = save_link_to_vault(link)
    link.vault_file = f"links/{vault_file.name}"
    save_link(link)

    if args.json:
        print(json.dumps(link.model_dump(), indent=2))
        return

    print("\n✓ Successfully archived:")
    print(f"  ID:       {link.id}")
    print(f"  Title:    {link.title}")
    print(f"  Type:     {link.entry_type.value}")
    print(f"  Domain:   {link.domain}")
    print(f"  Tags:     {', '.join('#' + t for t in link.tags)}")
    print(f"  Status:   {link.status.value}")
    print(f"  Words:    {link.word_count} ({link.reading_time_minutes} min read)")
    print(f"  Vault:    {vault_file}")


def cmd_list(args):
    """List archived links with FTS5 search."""
    ensure_directories()
    init_db()

    items, total = list_links(
        query=args.query,
        entry_type=args.type,
        tag=args.tag,
        status=args.status,
        limit=args.limit,
    )

    if args.json:
        print(json.dumps([item.model_dump() for item in items], indent=2))
        return

    print(f"\nFound {total} link(s) (showing top {len(items)}):")
    print(f"{'ID':<10} {'DATE':<12} {'STATUS':<10} {'TYPE':<8} {'TITLE':<40} {'DOMAIN'}")
    print("─" * 95)

    for item in items:
        title = item.title[:37] + "..." if len(item.title) > 40 else item.title
        print(f"{item.id:<10} {item.created_at[:10]:<12} {item.status.value:<10} {item.entry_type.value:<8} {title:<40} {item.domain}")


def cmd_view(args):
    """View full details and archived body markdown of a link (RAG content)."""
    ensure_directories()
    init_db()

    link = resolve_link(args.target)
    if not link:
        print(f"ERROR: Link '{args.target}' not found.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(link.model_dump(), indent=2))
        return

    print(f"=== [{link.id}] {link.title} ===")
    print(f"URL:      {link.url}")
    print(f"Domain:   {link.domain} | Type: {link.entry_type.value} | Status: {link.status.value}")
    print(f"Added:    {link.created_at} | Read time: {link.reading_time_minutes}m ({link.word_count} words)")
    print(f"Tags:     {', '.join('#' + t for t in link.tags)}")
    if link.user_notes:
        print(f"Notes:    {link.user_notes}")
    if link.highlights:
        print(f"Highlights ({len(link.highlights)}):")
        for h in link.highlights:
            print(f"  • \"{h.text}\" {f'({h.note})' if h.note else ''}")
    print("\n--- Summary ---")
    print(link.summary or "(None)")
    print("\n--- Full Archived Body ---")
    print(link.content_markdown or "(No archived content)")


def cmd_digest(args):
    """Pull links saved over the last N days for weekly/topic briefing."""
    ensure_directories()
    init_db()

    cutoff_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    items, total = list_links(limit=200)
    recent = [item for item in items if item.created_at[:10] >= cutoff_date]

    if args.json:
        print(json.dumps([r.model_dump() for r in recent], indent=2))
        if getattr(args, "save", False):
            create_vault_briefing(days=args.days, title=getattr(args, "title", None), custom_notes=getattr(args, "notes", None))
        return

    print(f"\n=== Link Vault Digest (Past {args.days} Days — since {cutoff_date}) ===")
    print(f"Total entries: {len(recent)}\n")

    for i, item in enumerate(recent, 1):
        print(f"{i}. [{item.title}]({item.url})")
        print(f"   • Type: `{item.entry_type.value}` | Status: `{item.status.value}` | Tags: {' '.join('#' + t for t in item.tags)}")
        if item.summary:
            print(f"   • Summary: {item.summary[:200]}...")
        if item.highlights:
            print(f"   • Key Quote: \"{item.highlights[0].text[:120]}...\"")
        print()

    if getattr(args, "save", False):
        saved_path = create_vault_briefing(days=args.days, title=getattr(args, "title", None), custom_notes=getattr(args, "notes", None))
        print(f"✓ Obsidian briefing note saved: {saved_path}")


def cmd_update(args):
    """Update reading status, tags, or notes on a link."""
    ensure_directories()
    init_db()

    link = resolve_link(args.target)
    if not link:
        print(f"ERROR: Link '{args.target}' not found.", file=sys.stderr)
        sys.exit(1)

    tags = [t.strip().lstrip("#") for t in args.tags.split(",") if t.strip()] if args.tags else None
    status = LinkStatus(args.status) if args.status else None

    updates = LinkUpdate(
        status=status,
        tags=tags,
        user_notes=args.notes,
    )
    updated = update_link(link.id, updates)
    save_link_to_vault(updated)

    print(f"✓ Updated [{updated.id}] {updated.title}: status={updated.status.value}, tags={updated.tags}")


def cmd_stats(args):
    """Display archive stats."""
    ensure_directories()
    init_db()
    stats = get_stats()

    if args.json:
        print(json.dumps(stats.model_dump(), indent=2))
        return

    print("\n=== Hermes Librarian Statistics ===")
    print(f"Total Links:          {stats.total_links}")
    print(f"Total Highlights:     {stats.total_highlights}")
    print(f"Words Archived:       {stats.total_words_archived:,}")
    print("\nBy Status:")
    for k, v in stats.by_status.items():
        print(f"  {k:<12}: {v}")
    print("\nBy Type:")
    for k, v in stats.by_type.items():
        print(f"  {k:<12}: {v}")
    print("\nTop Tags:")
    for tag, count in stats.top_tags[:10]:
        print(f"  #{tag:<15}: {count}")


def cmd_reindex(args):
    """Rebuild SQLite database from Obsidian markdown files."""
    ensure_directories()
    init_db()
    print("→ Scanning Obsidian vault and syncing database...")
    count = import_vault_to_database()
    print(f"✓ Reindexed {count} files from vault into SQLite.")


def cmd_test(args):
    """Run automated test suite."""
    import subprocess
    cmd = [sys.executable, "-m", "pytest"]
    if getattr(args, "verbose", False):
        cmd.append("-v")
    res = subprocess.run(cmd)
    sys.exit(res.returncode)


def cmd_serve(args):
    """Start web dashboard server."""
    import uvicorn
    host = args.host or APP_HOST
    port = args.port or APP_PORT
    print(f"\n🚀 Starting Hermes Librarian on http://{host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)


def main():
    parser = argparse.ArgumentParser(description="Hermes Librarian CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = subparsers.add_parser("add", help="Archive a URL")
    p_add.add_argument("url", help="URL to archive")
    p_add.add_argument("--title", help="Custom title override")
    p_add.add_argument("--tags", help="Comma-separated tags")
    p_add.add_argument("--status", choices=["inbox", "reading", "archived", "favorite"], default="inbox")
    p_add.add_argument("--type", choices=["article", "github", "video", "paper", "tool", "x-post", "other"])
    p_add.add_argument("--notes", help="Personal notes")
    p_add.add_argument("--json", action="store_true", help="Output as JSON")
    p_add.set_defaults(func=cmd_add)

    # list
    p_list = subparsers.add_parser("list", help="List or search links")
    p_list.add_argument("-q", "--query", help="Full-text search query")
    p_list.add_argument("-t", "--tag", help="Filter by tag")
    p_list.add_argument("-s", "--status", help="Filter by status")
    p_list.add_argument("--type", help="Filter by type")
    p_list.add_argument("-n", "--limit", type=int, default=20)
    p_list.add_argument("--json", action="store_true", help="Output as JSON")
    p_list.set_defaults(func=cmd_list)

    # view / read
    p_view = subparsers.add_parser("view", aliases=["read"], help="View full archived content and highlights (for RAG)")
    p_view.add_argument("target", help="Link ID or URL")
    p_view.add_argument("--json", action="store_true", help="Output as JSON")
    p_view.set_defaults(func=cmd_view)

    # digest
    p_digest = subparsers.add_parser("digest", help="Get links from the past N days for weekly briefings")
    p_digest.add_argument("--days", type=int, default=7, help="Number of days to look back (default: 7)")
    p_digest.add_argument("--save", action="store_true", help="Save briefing note into data/vault/briefings/")
    p_digest.add_argument("--title", help="Custom title for the briefing note")
    p_digest.add_argument("--notes", help="Executive summary / synthesis for the briefing")
    p_digest.add_argument("--json", action="store_true", help="Output as JSON")
    p_digest.set_defaults(func=cmd_digest)

    # update
    p_update = subparsers.add_parser("update", help="Update link status, tags, or notes")
    p_update.add_argument("target", help="Link ID or URL")
    p_update.add_argument("--status", choices=["inbox", "reading", "archived", "favorite"], help="New status")
    p_update.add_argument("--tags", help="New comma-separated tags")
    p_update.add_argument("--notes", help="New notes")
    p_update.set_defaults(func=cmd_update)

    # stats
    p_stats = subparsers.add_parser("stats", help="Show archive statistics")
    p_stats.add_argument("--json", action="store_true", help="Output as JSON")
    p_stats.set_defaults(func=cmd_stats)

    # reindex
    p_reindex = subparsers.add_parser("reindex", help="Rebuild database from vault")
    p_reindex.set_defaults(func=cmd_reindex)

    # test
    p_test = subparsers.add_parser("test", help="Run automated test suite")
    p_test.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    p_test.set_defaults(func=cmd_test)

    # serve
    p_serve = subparsers.add_parser("serve", help="Run web dashboard")
    p_serve.add_argument("--host", default=None)
    p_serve.add_argument("-p", "--port", type=int, default=None)
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
