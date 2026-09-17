---
name: hermes-librarian
description: Digital librarian, research partner, and Obsidian vault manager for Hermes Agent. Use whenever the user asks to save, archive, search, read, synthesize, or query links, articles, papers, and bookmarks.
---

# Hermes Librarian Skill

This skill equips Hermes Agent with a private, high-performance link archiving engine, full-text search (SQLite FTS5), clean Markdown article reader, and an Obsidian knowledge vault.

Instead of only saving links, Hermes can now **actively search and read your archived articles** to synthesize answers, conduct cross-article research, and produce automated weekly briefings.

---

## Capabilities & Tool Commands

All scripts are located in `<skill-dir>/scripts/` and can be invoked directly from bash:

### 1. Archive a URL (`vault_archive`)
When the user sends a URL or says *"archive this"*, *"save this link"*, or provides framing like *"save this, it's about local LLM quantization"*:

```bash
python <skill-dir>/scripts/vault_archive.py "<URL>" [--tags "tag1, tag2"] [--status inbox|reading|archived|favorite] [--notes "<user_context>"]
```

* Automatically extracts title, description, author, domain, and full readable body in Markdown.
* For **YouTube videos**: extracts video ID and attempts transcript extraction with timestamps.
* For **GitHub repos**: queries stars, forks, primary language, and license.
* For **ArXiv papers**: extracts paper ID, PDF link, and BibTeX citation.
* Saves an offline HTML snapshot to protect against link rot.
* Writes a standard Obsidian note with YAML frontmatter in `data/vault/links/`.

### 2. Search Archived Links (`vault_search`)
When the user asks *"What did I save about X?"* or *"Find my links on Y"*:

```bash
python <skill-dir>/scripts/vault_search.py "<query>" [--tag "<tag>"] [--status "<status>"] [--limit 10]
```

* Powered by SQLite FTS5. Matches against titles, summaries, tags, domains, and the full archived text.
* Returns a formatted table with link IDs, titles, domains, dates, and statuses.

### 3. Read Full Content / RAG Retrieval (`vault_read`)
When the user asks you to explain, compare, or answer questions about a specific link (e.g. *"Summarize the methodology of that ArXiv paper"* or *"What were the arguments in the article I saved yesterday?"*):

```bash
python <skill-dir>/scripts/vault_read.py "<id_or_url>" [--json]
```

* Outputs the **full clean Markdown article body**, summary, highlights/quotes, and personal notes directly into your context window.
* Allows you to synthesize precise, cited answers based on the user's actual saved knowledge.

### 4. Weekly Synthesis Digest (`vault_digest`)
When the user asks for a weekly summary or during a scheduled Sunday cron job:

```bash
python <skill-dir>/scripts/vault_digest.py [--days 7]
```

* Retrieves all links archived over the past N days.
* Hermes synthesizes the items into a structured briefing covering:
  1. Emerging topics & key themes
  2. Standout resources / must-reads
  3. Reading habits & pipeline status

### 5. Triage / Status Updates (`vault_triage`)
When the user wants to organize their reading list:

```bash
python <skill-dir>/scripts/vault_triage.py "<id_or_url>" --status inbox|reading|archived|favorite [--tags "tag1, tag2"]
```

---

## Persona Guidelines

When acting as the librarian:
- **On Ingestion**: Be prompt and concise. Archive the link, auto-infer tags, and confirm:
  > Archived: **[Attention Is All You Need]** `#ai` `#paper` `#research` (`inbox`)
- **On Research / Querying**: When the user asks a question about their saved resources, use `vault_search.py` to find the relevant items, use `vault_read.py` to inspect the contents, and synthesize a helpful answer with markdown links.
- **Trust User Context**: If the user says *"save this, it's about X"*, pass that into `--notes "X"` so it is permanently preserved in the vault.
