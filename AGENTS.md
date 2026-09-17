# Agent Setup & Operational Guide

> **Notice**: For the full, comprehensive manual on architecture, Hermes Agent skills, REST API, and CLI usage, see [AGENT_GUIDE.md](AGENT_GUIDE.md).

## Quickstart for AI Agents

To set up and verify this repository in one command:
```bash
./setup.sh
```

To launch the web dashboard and REST API:
```bash
./run.sh
```
The server runs locally at `http://127.0.0.1:8090`. Health check: `curl http://127.0.0.1:8090/api/health`.

## Core Commands Cheatsheet

```bash
# Activate environment
source .venv/bin/activate

# Archive a link (extracts content, saves Obsidian note, and captures offline snapshot)
python cli.py add "<URL>" --tags "ai, ml" --status inbox --notes "Personal note"

# Search with SQLite FTS5 full-text search
python cli.py list -q "search keywords"

# Read full article body into context for RAG
python cli.py view <id_or_url>

# Triage or update status
python cli.py update <id_or_url> --status reading --tags "tag1, tag2"

# Pull past 7 days for weekly briefing
python cli.py digest --days 7

# Reindex database if Obsidian vault notes were edited externally
python cli.py reindex
```

## Hermes Agent Integration
- **1-Command Profile Installer**: [`./install-hermes-profile.sh`](install-hermes-profile.sh)
- **Skill Definition**: [`skill/SKILL.md`](skill/SKILL.md)
- **Executable Agent Tools**: [`skill/scripts/`](skill/scripts/)
  - `vault_archive.py`
  - `vault_search.py`
  - `vault_read.py`
  - `vault_digest.py`
  - `vault_triage.py`
- **Agent Persona**: [`SOUL.md`](SOUL.md)
