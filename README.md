# Hermes Librarian

Personal link archiver, offline reader, and Obsidian research vault for Nous Research's Hermes Agent.

Archive any link into an **Obsidian-compatible Markdown vault**, extract **clean reader-view content & offline HTML snapshots**, browse via **rich cards, compact tables, or a reading Kanban board**, read distraction-free with **in-text highlighting & audio TTS**, and give **Hermes Agent** a deep long-term memory for research and automated weekly briefings.

---

## ✨ Why Hermes Librarian?

| Feature | Standard Bookmarkers / Flat-File Curators | **Hermes Librarian** |
| :--- | :--- | :--- |
| **Storage Architecture** | Monolithic index files or closed proprietary DBs | **Individual Markdown notes + SQLite with FTS5** |
| **Data Integrity** | Vulnerable to parsing conflicts & lock contention | **Safe, non-destructive atomic writes** |
| **Content Archiving** | URL + brief description only (vulnerable to link rot) | **Full clean article body in Markdown + Offline HTML snapshot** |
| **Search** | Exact substring matches | **Instant SQLite FTS5 full-text search** (title, summary, tags, & full body) |
| **Views** | Simple list or bookmarks folder | **Cards Grid, Compact List, Kanban Board, Calendar, & D3 Graph** |
| **Reading Experience** | External browser tabs only | **Distraction-Free Reader Mode** (typography, progress bar, audio TTS) |
| **Annotations** | Separate notes or external extensions | **In-text highlighting & quotes** (auto-persisted to Markdown frontmatter) |
| **Media Specialization**| Generic URL previews | **YouTube transcripts & player, GitHub API stats, ArXiv BibTeX & PDF** |
| **Ingestion** | Manual copy-paste | **1-Click Bookmarklet, Netscape HTML / CSV Bulk Import, REST API, & CLI** |
| **Hermes Agent Intelligence** | Unassisted filing | **Full Research Partner (RAG recall, topic search, weekly digests)** |

---

## 🚀 Key Features

* 🗂 **Obsidian-Native Vault**: Every link is saved as an individual note in `data/vault/links/YYYY-MM-DD-slug.md` with standard Obsidian YAML frontmatter properties, master `INDEX.md`, and auto-generated weekly research briefings with `[[wikilinks]]` in `data/vault/briefings/`.
* 📖 **Distraction-Free Reader Mode**: Read saved articles directly inside the web app with customizable typography (Serif / Sans), adjustable font sizes, reading time badge, **Sepia & OLED Black themes**, a reading progress bar, and built-in **audio Text-to-Speech (TTS)**.
* 🖍️ **In-Reader Text Highlighting**: Select any text in Reader Mode to highlight and save quotes directly to your Obsidian note's frontmatter and `## Highlights & Quotes` section.
* 📋 **Reading Workflow Kanban**: Triage your links through `Inbox` $\to$ `Reading` $\to$ `Archived` $\to$ `Favorite` columns.
* ⚡ **Blazing Fast Full-Text Search**: Powered by SQLite FTS5. Search across titles, summaries, domains, tags, and full archived text in milliseconds.
* 🎥 **Media-Specific Deep Extraction & Fallbacks**:
  * **YouTube**: Auto-extracts transcripts with timestamps and embeds an in-reader player.
  * **GitHub**: Queries GitHub API for stars, forks, languages, license, and topics.
  * **ArXiv**: Auto-generates BibTeX citation blocks and PDF download links.
  * **Wayback Machine Fallback**: Automatically attempts recovery from the Internet Archive if a direct URL is broken or blocked.
* 🔖 **1-Click Browser Bookmarklet & API Key Auth**: Drag the bookmarklet to your browser bar. Support for optional `HLIB_API_KEY` for secure remote hosting on VPS or Tailscale.
* 📦 **Bulk Import & Export**: Upload Chrome/Safari/Firefox HTML bookmarks or CSVs; download JSON dumps, CSVs, or the complete Obsidian Vault as a `.zip`.
* 🤖 **Hermes Agent Skill**: Equips Hermes with tools to archive, search, read full content for RAG, and produce weekly briefings.
* 🧪 **Automated Test Suite**: 23 comprehensive tests verifying database CRUD, FTS5 search, vault serialization, API routes, and auth (`python cli.py test`).

---

## 🛠 Tech Stack

- **Backend**: FastAPI, Uvicorn, SQLite3 (WAL mode + FTS5), Pydantic v2
- **Extraction**: Trafilatura, BeautifulSoup4, HTTPX, YouTube Transcript API
- **Frontend**: Tailwind CSS, Jinja2, Lucide Icons, D3.js v7, Web Speech API
- **Vault**: YAML Frontmatter, Python-Markdown

---

## 📦 Quickstart

### Automated 1-Step Setup
```bash
./setup.sh
```

*(Or manually: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`)*

> 🤖 **For AI Agents**: See the comprehensive [AGENT_GUIDE.md](AGENT_GUIDE.md) for full setup instructions, Hermes skill integration, and API/CLI documentation.

### Run the Web Dashboard & API

**Option A: 24/7 Background Service (Recommended for Linux/Servers)**
```bash
./install-service.sh
```
Installs a systemd user service that starts automatically on boot and runs in the background.
- Check status: `./install-service.sh status`
- View live logs: `./install-service.sh logs`
- Restart: `./install-service.sh restart`
- Stop: `./install-service.sh stop`

**Option B: Run in Foreground Terminal**
```bash
./run.sh
```

By default, Hermes Librarian binds to `0.0.0.0:8090` so it is accessible locally and across your LAN:
- Local URL: **`http://localhost:8090`**
- LAN Access: **`http://<server-ip>:8090`** (from laptops, phones, or remote Hermes instances)

---

## 🤖 Hermes Agent Integration (Skills & Tools)

Instead of a redundant chatbot inside the dashboard, **Hermes Agent** itself is the intelligent librarian and research partner.

### 1. Automated Profile & Skill Setup
Run the installer script to create a dedicated Hermes profile and link the skill automatically:
```bash
./install-hermes-profile.sh
```
This automatically clones your Hermes settings into a new `librarian` profile, links the skill tools, and activates [`SOUL.md`](SOUL.md). You can immediately begin using it via:
```bash
librarian chat
# or: hermes -p librarian chat
```

*(Manual setup: copy `skill/` to `~/.hermes/profiles/<name>/skills/note-taking/hermes-librarian` and copy `SOUL.md` to `~/.hermes/profiles/<name>/SOUL.md`)*

### 2. Skill Tools Available to Hermes

| Tool Script | What Hermes Does | Example User Prompt |
| :--- | :--- | :--- |
| `vault_archive.py` | Ingests URL, extracts markdown, tags, offline snapshot | *"Archive this link: https://..."* |
| `vault_search.py` | High-speed FTS5 search across all saved content | *"What did I save about transformer attention?"* |
| `vault_read.py` | Pulls full archived body markdown into context for RAG | *"Summarize the methodology of that ArXiv paper"* |
| `vault_digest.py` | Retrieves links saved over past N days (`--save` creates Obsidian note) | *"Give me a weekly reading briefing"* |
| `vault_triage.py` | Updates reading status (`inbox`, `reading`, `favorite`) | *"Mark that article as reading"* |

---

## 💻 CLI Usage

The system includes a full-featured CLI tool (`cli.py`):

```bash
# Archive a URL
python cli.py add "https://arxiv.org/abs/1706.03762" --status inbox

# Add with custom tags and reading status
python cli.py add "https://github.com/NousResearch/hermes-agent" --tags "ai, agents, open-source" --status favorite

# Full-text search across titles, summaries, and full body content
python cli.py list -q "transformer"

# Read full content & highlights of an archived link (for RAG)
python cli.py view bfc1d723

# Output past 7 days digest to terminal or JSON
python cli.py digest --days 7

# Generate and persist an Obsidian weekly briefing note with [[wikilinks]]
python cli.py digest --days 7 --save --title "Weekly Research Review" --notes "Focus on transformer architectures"

# Update status or tags
python cli.py update bfc1d723 --status reading

# View archive metrics
python cli.py stats

# Rebuild SQLite database from Markdown vault files (100% portable)
python cli.py reindex

# Run automated test suite (23 unit & integration tests)
python cli.py test -v

# Start server on custom port
python cli.py serve --port 8090
```

---

## 🔌 REST API Endpoints

The service exposes a complete REST API on port `8090`:

> 🔒 **Authentication**: When `HLIB_API_KEY` is configured, mutating endpoints (`POST`, `PATCH`, `DELETE`) require `Authorization: Bearer <key>` or `X-API-Key: <key>`. Read-only endpoints and `/api/health` remain accessible without a key.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/links` | Ingest and archive a new URL (`{"url": "...", "tags": [...], "status": "..."}`) |
| `GET` | `/api/links` | Search and filter links (`?q=...&type=...&status=...&tag=...`) |
| `GET` | `/api/links/{id}` | Retrieve link details with full archived markdown content |
| `PATCH`| `/api/links/{id}` | Update status, tags, or personal notes |
| `DELETE`|`/api/links/{id}` | Delete link from database and Obsidian vault |
| `POST` | `/api/links/{id}/highlights` | Save an in-text highlight / quote |
| `DELETE`|`/api/links/{id}/highlights/{hl_id}` | Delete a highlight |
| `POST` | `/api/briefings` | Generate and save an Obsidian weekly briefing note with wikilinks |
| `POST` | `/api/import/bookmarks` | Upload Netscape HTML bookmarks or CSV |
| `GET` | `/api/export/json` | Download complete archive as JSON |
| `GET` | `/api/export/csv` | Download links table as CSV |
| `GET` | `/api/export/zip` | Download complete Obsidian Vault as ZIP |
| `GET` | `/snapshot/{id}` | View preserved offline HTML snapshot |
| `GET` | `/bookmarklet` | 1-click browser bookmarklet helper popup |
| `GET` | `/api/stats` | Aggregate analytics (totals, counts by status/type, top tags) |
| `GET` | `/api/graph` | Graph nodes and edge links for D3 visualization |
| `POST` | `/api/sync` | Reconcile and reindex database from the Obsidian vault |
| `GET` | `/api/health` | Service health status |

---

## ⚙️ Configuration & Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `HLIB_PORT` | `8090` | Web dashboard & API bind port |
| `HLIB_HOST` | `0.0.0.0` | Bind host address (accessible locally and on LAN) |
| `HLIB_API_KEY` | `None` (disabled) | Optional secret token for API authentication |
| `HLIB_ROOT` | Repository Root | Path used by skill scripts to locate CLI and virtualenv |
| `HLIB_DATA_DIR` | `<HLIB_ROOT>/data` | Directory where database and vault are stored |
| `HLIB_VAULT_DIR` | `<HLIB_DATA_DIR>/vault` | Obsidian vault root directory |
| `HLIB_DB_PATH` | `<HLIB_DATA_DIR>/links.db`| SQLite database file path |

---

## 📂 Vault Structure

```text
data/
├── links.db                    # SQLite FTS5 database (instant read cache)
└── vault/                      # Standard Obsidian Vault
    ├── INDEX.md                # Master markdown table index
    ├── assets/
    │   └── snapshots/          # Preserved offline HTML snapshots
    ├── briefings/              # Auto-generated weekly synthesis notes (with [[wikilinks]])
    │   └── 2026-09-16-briefing-2026-W37.md
    └── links/                  # Individual note per link with YAML frontmatter
        ├── 2026-09-16-attention-is-all-you-need.md
        └── 2026-09-16-hermes-agent.md
```

---

## 📜 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
