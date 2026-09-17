"""Web scraper and content extractor for rich link archiving, media specialization, and offline snapshots."""
from __future__ import annotations

import math
import re
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from typing import Optional
import httpx
from bs4 import BeautifulSoup
import trafilatura

from app.config import SNAPSHOTS_DIR
from app.models import LinkType

COMMON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def detect_link_type(url: str) -> LinkType:
    """Detect resource type based on URL pattern."""
    domain = urlparse(url).netloc.lower()

    if "github.com" in domain or "gitlab.com" in domain:
        return LinkType.GITHUB
    if "twitter.com" in domain or "x.com" in domain:
        return LinkType.X_POST
    if any(v in domain for v in ["youtube.com", "youtu.be", "vimeo.com", "twitch.tv"]):
        return LinkType.VIDEO
    if any(p in domain for p in ["arxiv.org", "biorxiv.org", "doi.org", "sciencedirect.com"]):
        return LinkType.PAPER
    if any(t in domain for t in ["producthunt.com", "toolify.ai", "alternativeto.net"]):
        return LinkType.TOOL

    return LinkType.ARTICLE


def extract_domain(url: str) -> str:
    """Extract clean domain name without www."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain or "unknown"


def extract_youtube_id(url: str) -> Optional[str]:
    """Extract YouTube video ID if URL points to YouTube."""
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            return qs.get("v", [None])[0]
        elif parsed.path.startswith(("/embed/", "/v/")):
            parts = parsed.path.split("/")
            return parts[2] if len(parts) > 2 else None
    elif "youtu.be" in parsed.netloc:
        return parsed.path.strip("/")
    return None


async def fetch_github_metadata(owner: str, repo: str) -> dict:
    """Query GitHub API for stars, forks, language, license, and description."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        async with httpx.AsyncClient(headers={"User-Agent": "Hermes-Librarian"}, timeout=6.0) as client:
            resp = await client.get(api_url)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "stars": data.get("stargazers_count", 0),
                    "forks": data.get("forks_count", 0),
                    "language": data.get("language"),
                    "license": data.get("license", {}).get("spdx_id") if data.get("license") else None,
                    "open_issues": data.get("open_issues_count", 0),
                    "topics": data.get("topics", []),
                    "repo_name": f"{owner}/{repo}",
                }
    except Exception:
        pass
    return {}


def infer_tags(url: str, title: str, summary: str, entry_type: LinkType) -> list[str]:
    """Auto-infer a clean set of relevant tags."""
    text = f"{url} {title} {summary}".lower()
    tags = set()

    if entry_type == LinkType.GITHUB:
        tags.add("open-source")
        tags.add("dev-tools")
    elif entry_type == LinkType.PAPER:
        tags.add("research")
        tags.add("paper")
    elif entry_type == LinkType.VIDEO:
        tags.add("video")

    keyword_map = {
        "ai": ["ai", "artificial intelligence", "deep learning", "neural"],
        "llm": ["llm", "large language model", "gpt", "claude", "gemini", "llama"],
        "agent": ["agent", "agentic", "autonomous"],
        "python": ["python", "pip", "fastapi", "django"],
        "rust": ["rust", "cargo"],
        "typescript": ["typescript", "javascript", "react", "vue", "svelte", "node"],
        "design": ["design", "ui", "ux", "typography", "css", "tailwind"],
        "productivity": ["productivity", "workflow", "note-taking", "obsidian"],
        "security": ["security", "vulnerability", "cve", "auth", "cryptography"],
        "database": ["database", "sqlite", "postgres", "sql", "vector"],
        "dev-tools": ["dev-tools", "cli", "compiler", "terminal", "debugger", "git"],
    }

    for tag, keywords in keyword_map.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', text):
                tags.add(tag)
                break

    return sorted(list(tags))


async def fetch_wayback_snapshot(url: str) -> Optional[dict]:
    """
    Query the Wayback Machine Availability API to locate the closest snapshot.
    Returns dict with {"archived_url": ..., "timestamp": ..., "html": ...} or None.
    """
    api_url = f"https://archive.org/wayback/available?url={url}"
    try:
        async with httpx.AsyncClient(headers={"User-Agent": "Hermes-Librarian"}, timeout=10.0) as client:
            resp = await client.get(api_url)
            if resp.status_code == 200:
                data = resp.json()
                snapshots = data.get("archived_snapshots", {})
                closest = snapshots.get("closest")
                if closest and closest.get("available") and closest.get("url"):
                    archived_url = closest["url"]
                    page_resp = await client.get(archived_url, headers=COMMON_HEADERS, follow_redirects=True, timeout=15.0)
                    if page_resp.status_code == 200 and page_resp.text:
                        return {
                            "archived_url": archived_url,
                            "timestamp": closest.get("timestamp"),
                            "html": page_resp.text,
                        }
    except Exception:
        pass
    return None


async def fetch_and_extract(url: str, link_id: Optional[str] = None) -> dict:
    """
    Fetch a webpage, extract rich metadata, clean reader markdown,
    media-specific enrichments (YouTube, GitHub, ArXiv), and save an offline snapshot.
    Falls back to the Wayback Machine (Archive.org) if the direct URL is down or unreachable.
    """
    domain = extract_domain(url)
    inferred_type = detect_link_type(url)
    fallback_favicon = f"https://www.google.com/s2/favicons?domain={domain}&sz=64"

    result = {
        "url": url,
        "title": url,
        "author": None,
        "site_name": domain,
        "domain": domain,
        "entry_type": inferred_type,
        "tags": [],
        "summary": "",
        "content_markdown": "",
        "cover_image": None,
        "favicon": fallback_favicon,
        "word_count": 0,
        "reading_time_minutes": 1,
        "media_meta": {},
        "offline_snapshot_path": None,
    }

    html = ""
    final_url = url
    recovered_from_wayback = False

    # Try direct fetch first
    try:
        async with httpx.AsyncClient(headers=COMMON_HEADERS, follow_redirects=True, timeout=12.0) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                raise httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=resp.request, response=resp)
            html = resp.text
            final_url = str(resp.url)
            result["url"] = final_url
    except Exception as direct_err:
        # Fallback to Internet Archive Wayback Machine
        wb_data = await fetch_wayback_snapshot(url)
        if wb_data:
            html = wb_data["html"]
            recovered_from_wayback = True
            result["media_meta"]["wayback_fallback"] = True
            result["media_meta"]["wayback_url"] = wb_data["archived_url"]
            result["media_meta"]["wayback_timestamp"] = wb_data.get("timestamp")
            result["tags"].append("wayback-archive")
            ts_str = wb_data.get("timestamp", "")
            date_hint = f"{ts_str[:4]}-{ts_str[4:6]}-{ts_str[6:8]}" if len(ts_str) >= 8 else "historical"
            result["summary"] = f"Recovered from Wayback Machine snapshot ({date_hint}). Direct fetch failed: {type(direct_err).__name__}."
        else:
            result["summary"] = f"Archived link (direct fetch encountered: {type(direct_err).__name__})"
            result["tags"] = infer_tags(url, result["title"], result["summary"], inferred_type)
            return result

    # Save offline HTML snapshot
    if link_id and html:
        try:
            snapshot_file = SNAPSHOTS_DIR / f"{link_id}.html"
            snapshot_file.write_text(html, encoding="utf-8", errors="replace")
            result["offline_snapshot_path"] = f"assets/snapshots/{link_id}.html"
        except Exception:
            pass

    # 1. Parse metadata via BeautifulSoup
    try:
        soup = BeautifulSoup(html, "html.parser")

        og_title = soup.find("meta", property="og:title")
        twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
        tag_title = soup.title.string.strip() if (soup.title and soup.title.string) else None

        title = None
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        elif twitter_title and twitter_title.get("content"):
            title = twitter_title["content"].strip()
        elif tag_title:
            title = tag_title
        else:
            title = url
        result["title"] = title

        # Description / Summary
        og_desc = soup.find("meta", property="og:description")
        meta_desc = soup.find("meta", attrs={"name": "description"})
        twitter_desc = soup.find("meta", attrs={"name": "twitter:description"})

        desc = ""
        if og_desc and og_desc.get("content"):
            desc = og_desc["content"].strip()
        elif meta_desc and meta_desc.get("content"):
            desc = meta_desc["content"].strip()
        elif twitter_desc and twitter_desc.get("content"):
            desc = twitter_desc["content"].strip()
        result["summary"] = desc

        # Author
        meta_author = (
            soup.find("meta", attrs={"name": "author"})
            or soup.find("meta", property="article:author")
            or soup.find("meta", attrs={"name": "twitter:creator"})
        )
        if meta_author and meta_author.get("content"):
            result["author"] = meta_author["content"].strip()

        # Site Name
        og_site = soup.find("meta", property="og:site_name")
        if og_site and og_site.get("content"):
            result["site_name"] = og_site["content"].strip()

        # Cover Image
        og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if og_img and og_img.get("content"):
            img_url = og_img["content"].strip()
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            elif img_url.startswith("/"):
                parsed = urlparse(final_url)
                img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
            result["cover_image"] = img_url

        # Favicon
        icon_link = (
            soup.find("link", rel=lambda x: x and "icon" in x.lower())
            or soup.find("link", rel=lambda x: x and "apple-touch-icon" in x.lower())
        )
        if icon_link and icon_link.get("href"):
            fav = icon_link["href"].strip()
            if fav.startswith("//"):
                fav = "https:" + fav
            elif fav.startswith("/"):
                parsed = urlparse(final_url)
                fav = f"{parsed.scheme}://{parsed.netloc}{fav}"
            result["favicon"] = fav
    except Exception:
        pass

    # 2. Extract full reader markdown body using Trafilatura
    try:
        extracted = trafilatura.extract(
            html,
            output_format="markdown",
            include_links=True,
            include_images=True,
            include_tables=True,
            favor_precision=False,
        )
        if extracted:
            result["content_markdown"] = extracted.strip()
            words = len(extracted.split())
            result["word_count"] = words
            result["reading_time_minutes"] = max(1, math.ceil(words / 200))
            if not result["summary"]:
                first_para = extracted.split("\n\n")[0]
                result["summary"] = (first_para[:280] + "...") if len(first_para) > 280 else first_para
    except Exception:
        result["content_markdown"] = ""

    # 3. Media Specialization
    # ── A. YouTube & Video ──
    yt_id = extract_youtube_id(url)
    if yt_id:
        result["entry_type"] = LinkType.VIDEO
        result["media_meta"]["youtube_id"] = yt_id
        if not result["cover_image"]:
            result["cover_image"] = f"https://img.youtube.com/vi/{yt_id}/maxresdefault.jpg"

        # Attempt transcript extraction
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            transcript_list = YouTubeTranscriptApi().get_transcript(yt_id)
            if transcript_list:
                transcript_md = "\n\n".join(
                    f"**[{int(item['start'] // 60):02d}:{int(item['start'] % 60):02d}]** {item['text']}"
                    for item in transcript_list
                )
                result["content_markdown"] = f"### Video Transcript\n\n{transcript_md}"
                result["media_meta"]["has_transcript"] = True
                words = len(result["content_markdown"].split())
                result["word_count"] = words
                result["reading_time_minutes"] = max(1, math.ceil(words / 200))
        except Exception:
            result["media_meta"]["has_transcript"] = False

    # ── B. GitHub Repositories ──
    gh_match = re.search(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", url)
    if gh_match:
        owner, repo = gh_match.group(1), gh_match.group(2)
        if owner not in ["topics", "features", "explore", "settings"]:
            gh_meta = await fetch_github_metadata(owner, repo)
            if gh_meta:
                result["media_meta"]["github"] = gh_meta
                if gh_meta.get("topics"):
                    for top in gh_meta["topics"][:3]:
                        result["tags"].append(top)

    # ── C. ArXiv Papers ──
    arxiv_match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d+\.\d+)", url)
    if arxiv_match:
        arxiv_id = arxiv_match.group(1)
        result["entry_type"] = LinkType.PAPER
        result["media_meta"]["arxiv_id"] = arxiv_id
        result["media_meta"]["pdf_url"] = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        result["media_meta"]["bibtex"] = (
            f"@article{{{arxiv_id},\n"
            f"  title = {{{result['title']}}},\n"
            f"  url = {{https://arxiv.org/abs/{arxiv_id}}}\n"
            f"}}"
        )

    # 4. Infer tags
    inferred = infer_tags(result["url"], result["title"], result["summary"], result["entry_type"])
    for t in inferred:
        if t not in result["tags"]:
            result["tags"].append(t)

    return result
