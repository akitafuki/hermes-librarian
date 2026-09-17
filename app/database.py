"""SQLite database with FTS5 full-text search, media metadata, and highlights."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple
from app.config import DB_PATH
from app.models import Link, LinkUpdate, LinkStatus, LinkType, StatsResponse, Highlight


def get_connection() -> sqlite3.Connection:
    """Get SQLite database connection with row factory and WAL mode."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Initialize database tables, apply column migrations, and full-text search triggers."""
    with get_connection() as conn:
        # 1. Main links table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id TEXT PRIMARY KEY,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                author TEXT,
                site_name TEXT,
                domain TEXT,
                entry_type TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'inbox',
                summary TEXT,
                user_notes TEXT,
                content_markdown TEXT,
                cover_image TEXT,
                favicon TEXT,
                reading_time_minutes INTEGER DEFAULT 1,
                word_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                vault_file TEXT,
                media_meta TEXT NOT NULL DEFAULT '{}',
                highlights TEXT NOT NULL DEFAULT '[]',
                offline_snapshot_path TEXT
            );
        """)

        # 2. Check for missing columns if table already existed (schema migration)
        existing_cols = {r["name"] for r in conn.execute("PRAGMA table_info(links)").fetchall()}
        if "media_meta" not in existing_cols:
            conn.execute("ALTER TABLE links ADD COLUMN media_meta TEXT NOT NULL DEFAULT '{}';")
        if "highlights" not in existing_cols:
            conn.execute("ALTER TABLE links ADD COLUMN highlights TEXT NOT NULL DEFAULT '[]';")
        if "offline_snapshot_path" not in existing_cols:
            conn.execute("ALTER TABLE links ADD COLUMN offline_snapshot_path TEXT;")

        # 3. Indexes on frequently queried columns
        conn.execute("CREATE INDEX IF NOT EXISTS idx_links_status ON links(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_links_type ON links(entry_type);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_links_created_at ON links(created_at DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_links_domain ON links(domain);")

        # 4. FTS5 Virtual Table for full-text search
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS links_fts USING fts5(
                id UNINDEXED,
                title,
                summary,
                content_markdown,
                tags,
                domain,
                tokenize = 'porter unicode61'
            );
        """)

        # 5. Triggers to maintain FTS5 table
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_links_after_insert AFTER INSERT ON links BEGIN
                INSERT INTO links_fts(id, title, summary, content_markdown, tags, domain)
                VALUES (new.id, new.title, new.summary, new.content_markdown, new.tags, new.domain);
            END;
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_links_after_delete AFTER DELETE ON links BEGIN
                DELETE FROM links_fts WHERE id = old.id;
            END;
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_links_after_update AFTER UPDATE ON links BEGIN
                DELETE FROM links_fts WHERE id = old.id;
                INSERT INTO links_fts(id, title, summary, content_markdown, tags, domain)
                VALUES (new.id, new.title, new.summary, new.content_markdown, new.tags, new.domain);
            END;
        """)
        conn.commit()


def row_to_link(row: sqlite3.Row) -> Link:
    """Convert database row to Pydantic Link model."""
    d = dict(row)
    d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
    d["entry_type"] = LinkType(d["entry_type"])
    d["status"] = LinkStatus(d["status"])
    d["media_meta"] = json.loads(d.get("media_meta") or "{}")

    # Parse highlights
    raw_highlights = json.loads(d.get("highlights") or "[]")
    d["highlights"] = [Highlight(**h) if isinstance(h, dict) else h for h in raw_highlights]

    return Link(**d)


def save_link(link: Link) -> Link:
    """Insert or replace a link into the database."""
    with get_connection() as conn:
        highlights_json = json.dumps([h.model_dump() for h in link.highlights])
        media_meta_json = json.dumps(link.media_meta)

        conn.execute("""
            INSERT INTO links (
                id, url, title, author, site_name, domain, entry_type,
                tags, status, summary, user_notes, content_markdown,
                cover_image, favicon, reading_time_minutes, word_count,
                created_at, updated_at, vault_file, media_meta, highlights, offline_snapshot_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                author = coalesce(excluded.author, links.author),
                site_name = coalesce(excluded.site_name, links.site_name),
                domain = excluded.domain,
                entry_type = excluded.entry_type,
                tags = excluded.tags,
                status = excluded.status,
                summary = excluded.summary,
                user_notes = coalesce(excluded.user_notes, links.user_notes),
                content_markdown = coalesce(excluded.content_markdown, links.content_markdown),
                cover_image = coalesce(excluded.cover_image, links.cover_image),
                favicon = coalesce(excluded.favicon, links.favicon),
                reading_time_minutes = excluded.reading_time_minutes,
                word_count = excluded.word_count,
                updated_at = excluded.updated_at,
                vault_file = coalesce(excluded.vault_file, links.vault_file),
                media_meta = excluded.media_meta,
                highlights = excluded.highlights,
                offline_snapshot_path = coalesce(excluded.offline_snapshot_path, links.offline_snapshot_path)
        """, (
            link.id, link.url, link.title, link.author, link.site_name, link.domain,
            link.entry_type.value, json.dumps(link.tags), link.status.value,
            link.summary, link.user_notes, link.content_markdown,
            link.cover_image, link.favicon, link.reading_time_minutes, link.word_count,
            link.created_at, link.updated_at, link.vault_file,
            media_meta_json, highlights_json, link.offline_snapshot_path
        ))
        conn.commit()
    return get_link_by_url(link.url) or link


def get_link(link_id: str) -> Optional[Link]:
    """Retrieve a link by its ID."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM links WHERE id = ?", (link_id,)).fetchone()
        return row_to_link(row) if row else None


def get_link_by_url(url: str) -> Optional[Link]:
    """Retrieve a link by its URL."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM links WHERE url = ?", (url,)).fetchone()
        return row_to_link(row) if row else None


def update_link(link_id: str, updates: LinkUpdate) -> Optional[Link]:
    """Update fields on an existing link."""
    existing = get_link(link_id)
    if not existing:
        return None

    update_dict = updates.model_dump(exclude_unset=True)
    if not update_dict:
        return existing

    set_clauses = []
    values = []
    for k, v in update_dict.items():
        if k == "tags":
            set_clauses.append("tags = ?")
            values.append(json.dumps(v))
        elif k == "status" and v is not None:
            set_clauses.append("status = ?")
            values.append(v.value if isinstance(v, LinkStatus) else str(v))
        elif k == "entry_type" and v is not None:
            set_clauses.append("entry_type = ?")
            values.append(v.value if isinstance(v, LinkType) else str(v))
        elif k == "media_meta" and v is not None:
            set_clauses.append("media_meta = ?")
            values.append(json.dumps(v))
        elif k == "highlights" and v is not None:
            set_clauses.append("highlights = ?")
            values.append(json.dumps([h if isinstance(h, dict) else h.model_dump() for h in v]))
        else:
            set_clauses.append(f"{k} = ?")
            values.append(v)

    set_clauses.append("updated_at = ?")
    values.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    values.append(link_id)

    with get_connection() as conn:
        conn.execute(f"UPDATE links SET {', '.join(set_clauses)} WHERE id = ?", values)
        conn.commit()

    return get_link(link_id)


def add_highlight(link_id: str, highlight: Highlight) -> Optional[Link]:
    """Append a highlight to a link."""
    link = get_link(link_id)
    if not link:
        return None

    highlights = [h.model_dump() for h in link.highlights]
    highlights.append(highlight.model_dump())

    with get_connection() as conn:
        conn.execute(
            "UPDATE links SET highlights = ?, updated_at = ? WHERE id = ?",
            (json.dumps(highlights), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), link_id)
        )
        conn.commit()

    return get_link(link_id)


def delete_highlight(link_id: str, highlight_id: str) -> Optional[Link]:
    """Remove a highlight from a link."""
    link = get_link(link_id)
    if not link:
        return None

    highlights = [h.model_dump() for h in link.highlights if h.id != highlight_id]

    with get_connection() as conn:
        conn.execute(
            "UPDATE links SET highlights = ?, updated_at = ? WHERE id = ?",
            (json.dumps(highlights), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), link_id)
        )
        conn.commit()

    return get_link(link_id)


def delete_link(link_id: str) -> bool:
    """Delete a link by ID."""
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM links WHERE id = ?", (link_id,))
        conn.commit()
        return cur.rowcount > 0


def list_links(
    query: Optional[str] = None,
    entry_type: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[List[Link], int]:
    """Query and filter links with full-text search support."""
    with get_connection() as conn:
        conditions = []
        params = []

        if query and query.strip():
            clean_q = "".join(c if c.isalnum() or c in " *_-#" else " " for c in query.strip())
            terms = [f'"{t}"*' for t in clean_q.split() if t]
            if terms:
                match_str = " ".join(terms)
                conditions.append("id IN (SELECT id FROM links_fts WHERE links_fts MATCH ?)")
                params.append(match_str)

        if entry_type:
            conditions.append("entry_type = ?")
            params.append(entry_type)

        if status:
            conditions.append("status = ?")
            params.append(status)

        if domain:
            conditions.append("domain = ?")
            params.append(domain)

        if tag:
            clean_tag = tag.lower().lstrip("#")
            conditions.append("tags LIKE ?")
            params.append(f'%"{clean_tag}"%')

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Total matching count
        count_cur = conn.execute(f"SELECT COUNT(*) FROM links {where_clause}", params)
        total_count = count_cur.fetchone()[0]

        # Results page
        query_sql = f"""
            SELECT * FROM links
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(query_sql, params + [limit, offset]).fetchall()
        links = [row_to_link(r) for r in rows]

        return links, total_count


def get_stats() -> StatsResponse:
    """Aggregate statistics across all links."""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
        words = conn.execute("SELECT coalesce(SUM(word_count), 0) FROM links").fetchone()[0]

        # By status
        status_rows = conn.execute("SELECT status, COUNT(*) FROM links GROUP BY status").fetchall()
        by_status = {r[0]: r[1] for r in status_rows}

        # By type
        type_rows = conn.execute("SELECT entry_type, COUNT(*) FROM links GROUP BY entry_type").fetchall()
        by_type = {r[0]: r[1] for r in type_rows}

        # Top domains
        domain_rows = conn.execute(
            "SELECT domain, COUNT(*) as c FROM links WHERE domain IS NOT NULL GROUP BY domain ORDER BY c DESC LIMIT 15"
        ).fetchall()
        top_domains = [(r[0], r[1]) for r in domain_rows]

        # Top tags (parse JSON tags)
        tag_rows = conn.execute("SELECT tags FROM links").fetchall()
        tag_counts: dict[str, int] = {}
        for r in tag_rows:
            if r[0]:
                for t in json.loads(r[0]):
                    tag_counts[t] = tag_counts.get(t, 0) + 1
        top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:20]

        # Total highlights
        highlight_rows = conn.execute("SELECT highlights FROM links").fetchall()
        total_hl = 0
        for hr in highlight_rows:
            if hr[0]:
                try:
                    total_hl += len(json.loads(hr[0]))
                except Exception:
                    pass

        return StatsResponse(
            total_links=total,
            by_status=by_status,
            by_type=by_type,
            top_tags=top_tags,
            top_domains=top_domains,
            total_words_archived=words,
            total_highlights=total_hl,
        )


def get_calendar_data() -> list[dict]:
    """Group link counts and previews by date."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT substr(created_at, 1, 10) as day, COUNT(*) as count
            FROM links
            GROUP BY day
            ORDER BY day DESC
        """).fetchall()
        return [{"date": r["day"], "count": r["count"]} for r in rows]


def get_links_since(since_timestamp: str) -> list[Link]:
    """Retrieve all links created since a given timestamp string."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM links WHERE created_at >= ? ORDER BY created_at DESC",
            (since_timestamp,)
        ).fetchall()
        return [row_to_link(r) for r in rows]


def get_graph_data() -> dict:
    """Build knowledge graph data connecting links, tags, and domains."""
    with get_connection() as conn:
        links = conn.execute("SELECT id, title, entry_type, domain, tags, url FROM links").fetchall()

    nodes = []
    links_list = []
    seen_nodes = set()
    tag_counts = {}
    domain_counts = {}

    for l in links:
        tags = json.loads(l["tags"]) if l["tags"] else []
        domain = l["domain"]
        if domain:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        for t in tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1

    # Add Tag nodes
    for t, count in tag_counts.items():
        node_id = f"tag:{t}"
        nodes.append({"id": node_id, "label": f"#{t}", "kind": "tag", "count": count})
        seen_nodes.add(node_id)

    # Add Domain nodes
    for d, count in domain_counts.items():
        node_id = f"domain:{d}"
        nodes.append({"id": node_id, "label": d, "kind": "domain", "count": count})
        seen_nodes.add(node_id)

    # Add Link nodes & Edges
    for l in links:
        link_id = f"link:{l['id']}"
        nodes.append({
            "id": link_id,
            "label": l["title"][:50],
            "kind": "link",
            "type": l["entry_type"],
            "url": l["url"],
            "count": 1,
        })

        # Connect to domain
        if l["domain"] and f"domain:{l['domain']}" in seen_nodes:
            links_list.append({"source": link_id, "target": f"domain:{l['domain']}"})

        # Connect to tags
        tags = json.loads(l["tags"]) if l["tags"] else []
        for t in tags:
            if f"tag:{t}" in seen_nodes:
                links_list.append({"source": link_id, "target": f"tag:{t}"})

    return {"nodes": nodes, "links": links_list}
