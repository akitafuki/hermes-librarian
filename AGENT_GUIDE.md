# Hermes Librarian — Autonomous Agent Guide

This document is the authoritative setup, integration, and operational manual for AI agents (e.g., Hermes Agent, autonomous coding assistants, or headless runners) interacting with the **Hermes Librarian** repository.

---

## ⚡ 1. Agent Quickstart (TL;DR)

### One-Command Setup
To configure the environment, create the virtualenv, install dependencies, and verify the database:
```bash
./setup.sh
```

### Manual Fast Setup
```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize storage and verify database
python3 -c "from app.config import ensure_directories; from app.database import init_db; ensure_directories(); init_db()"

# 4. Smoke test
python3 cli.py stats
```

### Launch the Service & Web Dashboard
```bash
# Option A: Run 24/7 in background as a systemd user service
./install-service.sh

# Option B: Run interactively in the active terminal
./run.sh
```
Server binds by default to `0.0.0.0:8090` (accessible via `http://localhost:8090` or `http://<lan-ip>:8090`).

### Verify Service Health
```bash
curl -f http://127.0.0.1:8090/api/health
# Expected output: {"status":"healthy","database":"connected","vault":"ready","links_count":8}
```

---

## 📁 2. Architecture & File Layout

```
hermes-librarian/
├── app/                      # Core FastAPI backend & business logic
│   ├── config.py             # Paths, port (default: 8090), env var overrides
│   ├── database.py           # SQLite connection (WAL mode), schema, FTS5 triggers, CRUD
│   ├── extractor.py          # Trafilatura reader extractor, YouTube/GitHub/ArXiv, HTML snapshots
│   ├── models.py             # Pydantic v2 schemas (Link, LinkStatus, LinkType, Highlight, etc.)
│   ├── vault.py              # Obsidian note serializer (atomic writes), INDEX.md generator, reindexing
│   ├── routes/
│   │   ├── api.py            # REST API (/api/links, /api/import, /api/export, /api/stats, etc.)
│   │   └── web.py            # HTML views (Grid, List, Kanban, Reader, Calendar, D3 Graph)
│   ├── static/               # CSS, JS (theme toggle, reader progress, highlighting, D3 graph)
│   └── templates/            # Jinja2 templates for all views
├── cli.py                    # Unified command-line interface (add, list, view, digest, test, stats, etc.)
├── data/                     # Persistent application data (auto-created)
│   ├── links.db              # SQLite database with FTS5 search table
│   └── vault/                # Obsidian knowledge vault
│       ├── INDEX.md          # Auto-generated master index
│       ├── links/            # YYYY-MM-DD-<slug>.md individual Markdown notes
│       ├── briefings/        # Auto-generated weekly synthesis notes (with Obsidian wikilinks)
│       └── assets/snapshots/ # Full offline HTML snapshots (<id>.html)
├── skill/                    # Drop-in skill for Hermes Agent (Nous Research)
│   ├── SKILL.md              # Skill instructions and tool triggers
│   └── scripts/              # Executable agent tools (archive, search, read, digest, triage)
├── tests/                    # 23 automated tests (database, vault, extractor, api, auth)
├── SOUL.md                   # Persona definition for Hermes (Librarian & Research Partner)
├── requirements.txt          # Python dependencies
├── setup.sh                  # Automated setup script
├── run.sh                    # Automated service launcher
├── install-service.sh        # Persistent systemd background service manager
└── install-hermes-profile.sh # Automated Hermes profile installer
```

---

## ⚙️ 3. Environment Variables

All settings can be customized via environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `HLIB_ROOT` | Repository Root Path | Used by skill scripts to locate `cli.py` and `.venv` |
| `HLIB_HOST` | `0.0.0.0` | Bind host for the web server (accessible locally and on LAN) |
| `HLIB_PORT` | `8090` | Bind port for the web server |
| `HLIB_API_KEY` | `None` (disabled) | Optional API key. When set, mutations require `Authorization: Bearer <key>` |
| `HLIB_DATA_DIR` | `<HLIB_ROOT>/data` | Directory where database and vault are stored |
| `HLIB_VAULT_DIR` | `<HLIB_DATA_DIR>/vault` | Obsidian vault root directory |
| `HLIB_DB_PATH` | `<HLIB_DATA_DIR>/links.db`| SQLite database file path |

---

## 🤖 4. Hermes Agent Integration

Hermes Agent connects directly to Hermes Librarian as its **storage engine, full-text index, and research memory**.

### Option A: Automated 1-Command Profile Setup (Recommended)
Run the included profile installer script:
```bash
./install-hermes-profile.sh
```
This automatically:
1. Clones your Hermes model and credentials into a dedicated `librarian` profile.
2. Symlinks the `skill/` directory into `~/.hermes/profiles/librarian/skills/note-taking/hermes-librarian`.
3. Sets up [`SOUL.md`](SOUL.md) as the active persona.
4. Injects `HLIB_ROOT` into the profile's `.env`.

You can then run the agent immediately:
```bash
librarian chat
# or: hermes -p librarian chat
```

### Option B: Manual Installation
1. Symlink or copy the `skill/` directory into your Hermes Agent's skills directory:
   ```bash
   ln -s "$(pwd)/skill" "$HOME/.hermes/skills/hermes-librarian"
   ```
   If copying rather than symlinking, export `HLIB_ROOT` in the environment:
   ```bash
   export HLIB_ROOT="/absolute/path/to/hermes-librarian"
   ```
2. Copy [`SOUL.md`](SOUL.md) into Hermes Agent's active prompt profile (e.g. `~/.hermes/profiles/<profile>/SOUL.md`). This instructs Hermes to:
   - Instantly archive URLs when mentioned (`vault_archive.py`).
   - Use SQLite FTS5 search when asked about saved topics (`vault_search.py`).
   - Retrieve the full Markdown text into context for RAG and synthesis (`vault_read.py`).
   - Generate weekly briefings on reading trends (`vault_digest.py`).

### Step 3: Skill Scripts Reference

| Script | Purpose | Example Usage |
| :--- | :--- | :--- |
| `skill/scripts/vault_archive.py` | Archive a link | `python vault_archive.py "<URL>" --tags "ai, ml" --notes "Focus on section 3"` |
| `skill/scripts/vault_search.py` | Search with FTS5 | `python vault_search.py "transformers" --tag ai --limit 5` |
| `skill/scripts/vault_read.py` | Pull full body for RAG | `python vault_read.py "<id_or_url>"` (returns full Markdown article body) |
| `skill/scripts/vault_digest.py` | Weekly summary data | `python vault_digest.py --days 7 --json` |
| `skill/scripts/vault_triage.py` | Update status/tags | `python vault_triage.py "<id_or_url>" --status reading` |

---

## 💻 5. CLI Reference for Agents

The CLI ([`cli.py`](cli.py)) is the primary interface for autonomous execution. All commands support execution from the virtual environment:

```bash
source .venv/bin/activate
```

### 1. Archive a URL (`add`)
```bash
python cli.py add "<URL>" \
  --tags "python, fastapi" \
  --status inbox \
  --notes "Recommended by coworker"
```
* **Output**: Extracts title, author, summary, full body in Markdown, downloads an offline HTML snapshot, writes an Obsidian note to `data/vault/links/`, updates `INDEX.md`, and inserts into SQLite FTS5.

### 2. Search Links (`list`)
```bash
# Full-text search across titles, summaries, tags, and full body text:
python cli.py list -q "neural network"

# Filter by status and type:
python cli.py list --status reading --type paper

# Output as JSON:
python cli.py list -q "search query" --json
```

### 3. Read Full Content (`view`)
```bash
# Output full Markdown note and quotes for RAG context:
python cli.py view <id_or_url>

# Output raw JSON:
python cli.py view <id_or_url> --json
```

### 4. Update Status / Tags (`update`)
```bash
python cli.py update <id_or_url> --status reading --tags "ai, updated-tag"
```

### 5. Generate Weekly Digest & Vault Briefing (`digest`)
```bash
# Print summary to terminal:
python cli.py digest --days 7

# Generate and save an Obsidian briefing note with wikilinks into data/vault/briefings/:
python cli.py digest --days 7 --save --title "Weekly Research Digest" --notes "Executive summary"
```

### 6. View Statistics (`stats`)
```bash
python cli.py stats
```

### 7. Reindex from Obsidian Vault (`reindex`)
If Markdown files in `data/vault/links/` were created or modified externally (e.g. by Obsidian directly):
```bash
python cli.py reindex
```
This re-parses all `.md` frontmatter and rebuilds the SQLite FTS5 index.

### 8. Run Automated Test Suite (`test`)
```bash
python cli.py test
# Or with verbose output:
python cli.py test -v
```

---

## 🌐 6. REST API Reference

The service exposes a complete REST API on port `8090`:

> 🔒 **Authentication**: When `HLIB_API_KEY` is configured in the environment, all mutating endpoints (`POST`, `PATCH`, `DELETE`) require `Authorization: Bearer <key>` or `X-API-Key: <key>`. Read-only endpoints and `/api/health` remain accessible without a key.

### Ingestion & Search
- `POST /api/links`: Archive a new URL.
  ```json
  {
    "url": "https://example.com/article",
    "tags": ["tech", "guide"],
    "status": "inbox",
    "personal_notes": "Interesting overview"
  }
  ```
- `GET /api/links`: Query links.
  - Query parameters: `query` (FTS5 search), `status`, `type`, `tag`, `limit`, `offset`.
- `GET /api/links/{id}`: Retrieve a single link record.
- `PATCH /api/links/{id}`: Update status, tags, title, or personal notes.
- `DELETE /api/links/{id}`: Remove link from database and archive note.

### Annotations & Highlights
- `POST /api/links/{id}/highlights`: Save a text highlight.
  ```json
  {
    "text": "Selected sentence or quote",
    "note": "Optional personal remark",
    "color": "yellow"
  }
  ```
- `DELETE /api/links/{id}/highlights/{highlight_id}`: Delete a highlight.

### Research Briefings & Bulk Sync
- `POST /api/briefings`: Generate and persist an Obsidian weekly briefing note in `data/vault/briefings/`.
  ```json
  {
    "days": 7,
    "title": "Weekly Research Review",
    "notes": "Executive synthesis of recent papers"
  }
  ```
- `POST /api/import/bookmarks`: Upload browser HTML bookmarks (Netscape format) or CSV.
- `GET /api/export/json`: Download full JSON export.
- `GET /api/export/csv`: Download CSV export.
- `GET /api/export/zip`: Download entire Obsidian vault as a `.zip` archive.
- `POST /api/sync`: Trigger vault $\leftrightarrow$ database reindex.
- `GET /api/stats`: Retrieve statistics (counts by status, type, word count, top tags).
- `GET /api/graph`: Graph data (`nodes` and `links`) for visualization.
- `GET /api/health`: System health check.

---

## 🛡️ 7. Operational Principles & Guardrails for Agents

1. **Dual-Write Architecture**:
   - Every archived link writes both to SQLite (`data/links.db`) and to an individual Obsidian note (`data/vault/links/YYYY-MM-DD-<slug>.md`).
   - SQLite handles millisecond FTS5 queries and UI state.
   - Markdown handles human readability, Obsidian graph linking, and LLM context ingestion.
2. **Safe Atomic Writes**:
   - Vault files are written atomically to prevent file corruption.
   - SQLite uses `WAL` (Write-Ahead Logging) and `busy_timeout = 30.0s`, allowing concurrent reads during writes.
3. **Link Rot Protection & Wayback Fallback**:
   - When archiving web articles, an offline snapshot is saved to `data/vault/assets/snapshots/<id>.html`.
   - If a direct URL is unreachable, returns 404/403, or times out, the extractor automatically attempts recovery via the **Wayback Machine (Archive.org)** availability API.
4. **Distraction-Free Reader Themes**:
   - Reader mode supports Auto (Light/Dark), warm **Sepia** (parchment eye-comfort), and pure **OLED Black** color schemes, with customizable typography and audio TTS.
5. **Git Hygiene**:
   - **Do not commit or add files to Git** unless explicitly commanded by the user.
6. **No Cloud Lock-in**:
   - All data is 100% self-hosted and local-first. No third-party API keys or external SaaS subscriptions are required.
