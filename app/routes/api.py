"""REST API endpoints for links, search, stats, graph, highlights, import, and export."""
from __future__ import annotations

import csv
import io
import json
import uuid
import zipfile
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Header, Request, Depends, status
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from bs4 import BeautifulSoup

from app.database import (
    save_link, get_link, get_link_by_url, update_link, delete_link,
    list_links, get_stats, get_graph_data, add_highlight, delete_highlight
)
from app.extractor import fetch_and_extract
from app.models import Link, LinkCreate, LinkUpdate, StatsResponse, LinkStatus, LinkType, Highlight, HighlightCreate
from app.vault import save_link_to_vault, import_vault_to_database, create_vault_briefing
from app.config import LINKS_VAULT_DIR, VAULT_DIR, BRIEFINGS_VAULT_DIR, HLIB_API_KEY

router = APIRouter(prefix="/api", tags=["api"])


def verify_api_key(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Validate API key if HLIB_API_KEY is configured.
    Supports:
    1. 'Authorization: Bearer <key>'
    2. 'X-API-Key: <key>'
    3. Query parameter '?api_key=<key>'
    4. Cookie 'hlib_token'
    Permits all requests if HLIB_API_KEY is not set.
    """
    if not HLIB_API_KEY:
        return True

    token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        elif len(parts) == 1:
            token = parts[0]
    elif x_api_key:
        token = x_api_key
    elif "api_key" in request.query_params:
        token = request.query_params["api_key"]
    elif "hlib_token" in request.cookies:
        token = request.cookies["hlib_token"]

    if token != HLIB_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True


class BriefingRequest(BaseModel):
    days: int = 7
    title: Optional[str] = None
    notes: Optional[str] = None


@router.post("/links", response_model=Link, dependencies=[Depends(verify_api_key)])
async def create_link(payload: LinkCreate):
    """Ingest, extract, archive, and index a new link."""
    existing = get_link_by_url(payload.url)
    if existing and not (payload.summary or payload.user_notes or payload.tags):
        return existing

    link_id = existing.id if existing else str(uuid.uuid4())[:8]

    # Extract metadata, clean reader markdown, media metadata, and save offline snapshot
    extracted = await fetch_and_extract(payload.url, link_id=link_id)

    # Use payload overrides if provided
    title = payload.title or extracted["title"]
    entry_type = payload.entry_type or extracted["entry_type"]
    tags = payload.tags if payload.tags is not None else extracted["tags"]
    summary = payload.summary if payload.summary else extracted["summary"]
    status = payload.status or LinkStatus.INBOX
    media_meta = payload.media_meta if payload.media_meta is not None else extracted.get("media_meta", {})

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        summary=summary,
        user_notes=payload.user_notes or (existing.user_notes if existing else None),
        content_markdown=extracted.get("content_markdown", ""),
        cover_image=extracted.get("cover_image"),
        favicon=extracted.get("favicon"),
        reading_time_minutes=extracted.get("reading_time_minutes", 1),
        word_count=extracted.get("word_count", 0),
        created_at=existing.created_at if existing else now_str,
        updated_at=now_str,
        media_meta=media_meta,
        highlights=existing.highlights if existing else [],
        offline_snapshot_path=extracted.get("offline_snapshot_path"),
    )

    # 1. Save to Markdown Vault
    vault_file = save_link_to_vault(link)
    link.vault_file = f"links/{vault_file.name}"

    # 2. Save to SQLite with FTS5
    saved = save_link(link)
    return saved


@router.get("/links")
def get_links(
    q: Optional[str] = Query(None, description="Search query"),
    type: Optional[str] = Query(None, description="Filter by type"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    status: Optional[str] = Query(None, description="Filter by status (inbox, reading, archived, favorite)"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Search and filter links with pagination."""
    items, total = list_links(
        query=q,
        entry_type=type,
        tag=tag,
        status=status,
        domain=domain,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/links/{link_id}", response_model=Link)
def get_single_link(link_id: str):
    """Retrieve full link details including archived content and highlights."""
    link = get_link(link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return link


@router.patch("/links/{link_id}", response_model=Link, dependencies=[Depends(verify_api_key)])
def update_single_link(link_id: str, updates: LinkUpdate):
    """Update metadata, tags, notes, or reading status."""
    updated = update_link(link_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Link not found")

    # Sync back to Markdown Vault
    save_link_to_vault(updated)
    return updated


@router.delete("/links/{link_id}", dependencies=[Depends(verify_api_key)])
def delete_single_link(link_id: str):
    """Delete link from database and vault."""
    link = get_link(link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    # Delete vault file if exists
    if link.vault_file:
        vf = LINKS_VAULT_DIR.parent / link.vault_file
        if vf.exists():
            vf.unlink()

    success = delete_link(link_id)
    return {"success": success, "deleted_id": link_id}


# ─── Highlighting Endpoints ──────────────────────────────────────────────────

@router.post("/links/{link_id}/highlights", response_model=Link, dependencies=[Depends(verify_api_key)])
def create_highlight(link_id: str, payload: HighlightCreate):
    """Save an in-text highlight / quote from reader mode."""
    hl = Highlight(
        id=str(uuid.uuid4())[:8],
        text=payload.text.strip(),
        note=payload.note.strip() if payload.note else None,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    updated = add_highlight(link_id, hl)
    if not updated:
        raise HTTPException(status_code=404, detail="Link not found")

    save_link_to_vault(updated)
    return updated


@router.delete("/links/{link_id}/highlights/{highlight_id}", response_model=Link, dependencies=[Depends(verify_api_key)])
def remove_highlight(link_id: str, highlight_id: str):
    """Delete a highlight from a link."""
    updated = delete_highlight(link_id, highlight_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Link or highlight not found")

    save_link_to_vault(updated)
    return updated


# ─── Bulk Import & Export ────────────────────────────────────────────────────

@router.post("/import/bookmarks", dependencies=[Depends(verify_api_key)])
async def import_bookmarks(file: UploadFile = File(...)):
    """Import bookmarks from Chrome / Safari / Firefox Netscape HTML export or CSV."""
    content_bytes = await file.read()
    filename = file.filename.lower()

    imported = 0
    errors = 0

    if filename.endswith(".html") or filename.endswith(".htm"):
        # Netscape bookmarks format
        soup = BeautifulSoup(content_bytes.decode("utf-8", errors="ignore"), "html.parser")
        links_found = soup.find_all("a")
        for tag in links_found:
            href = tag.get("href")
            title = tag.get_text().strip() or href
            if href and href.startswith(("http://", "https://")):
                try:
                    # Quick save without heavy blocking fetch
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    link_id = str(uuid.uuid4())[:8]
                    link = Link(
                        id=link_id,
                        url=href,
                        title=title,
                        domain=href.split("/")[2].replace("www.", ""),
                        entry_type=LinkType.ARTICLE,
                        status=LinkStatus.INBOX,
                        created_at=now_str,
                        updated_at=now_str,
                    )
                    save_link(link)
                    save_link_to_vault(link)
                    imported += 1
                except Exception:
                    errors += 1

    elif filename.endswith(".csv"):
        # CSV format (url, title, tags)
        text = content_bytes.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            url = row.get("url") or row.get("URL") or row.get("link")
            if url and url.startswith(("http://", "https://")):
                title = row.get("title") or row.get("Title") or url
                tags_raw = row.get("tags") or row.get("Tags") or ""
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                link_id = str(uuid.uuid4())[:8]
                link = Link(
                    id=link_id,
                    url=url,
                    title=title,
                    domain=url.split("/")[2].replace("www.", ""),
                    tags=tags,
                    created_at=now_str,
                    updated_at=now_str,
                )
                save_link(link)
                save_link_to_vault(link)
                imported += 1

    return {"imported": imported, "errors": errors}


@router.get("/export/json")
def export_json():
    """Export all links as a JSON dump."""
    items, _ = list_links(limit=10000)
    data = [item.model_dump() for item in items]
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=hermes_links_export.json"}
    )


@router.get("/export/csv")
def export_csv():
    """Export link metadata as CSV."""
    items, _ = list_links(limit=10000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "URL", "Title", "Domain", "Type", "Status", "Tags", "ReadingTime", "Words", "Added"])

    for item in items:
        writer.writerow([
            item.id, item.url, item.title, item.domain, item.entry_type.value,
            item.status.value, " ".join(item.tags), item.reading_time_minutes,
            item.word_count, item.created_at[:10]
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=hermes_links_export.csv"}
    )


@router.get("/export/zip")
def export_vault_zip():
    """Export the entire Obsidian Markdown vault as a ZIP file."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in VAULT_DIR.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(VAULT_DIR)
                zf.write(file_path, arcname=str(rel_path))

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=hermes_obsidian_vault.zip"}
    )


# ─── System & Analytics Endpoints ────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse)
def get_stats_endpoint():
    """Retrieve archive analytics and taxonomy."""
    return get_stats()


@router.get("/graph")
def get_graph_endpoint():
    """Retrieve D3 force-directed knowledge graph data."""
    return get_graph_data()


@router.post("/sync", dependencies=[Depends(verify_api_key)])
def sync_vault():
    """Sync and rebuild SQLite database from the Obsidian vault."""
    count = import_vault_to_database()
    return {"status": "ok", "synced_files": count}


@router.post("/briefings", dependencies=[Depends(verify_api_key)])
def create_briefing_endpoint(payload: BriefingRequest):
    """Generate and persist an Obsidian weekly research briefing note in vault/briefings/."""
    file_path = create_vault_briefing(days=payload.days, title=payload.title, custom_notes=payload.notes)
    return {
        "status": "success",
        "file": str(file_path),
        "filename": file_path.name,
        "vault_path": f"briefings/{file_path.name}",
    }


@router.get("/health")
def health_check():
    """Service health check."""
    stats = get_stats()
    return {
        "status": "healthy",
        "total_links": stats.total_links,
        "version": "1.2.0",
    }
