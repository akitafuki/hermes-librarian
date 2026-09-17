"""HTML template web routes for the user interface."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import markdown

from app.config import BASE_DIR
from app.database import list_links, get_link, get_stats, get_calendar_data
from app.models import LinkStatus, LinkType

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")


def get_base_context(request: Request, current_page: str) -> dict:
    """Common context variables for header, navigation, and sidebar."""
    stats = get_stats()
    return {
        "request": request,
        "current_page": current_page,
        "stats": stats,
        "statuses": [s.value for s in LinkStatus],
        "types": [t.value for t in LinkType],
    }


@router.get("/", response_class=HTMLResponse)
def index_view(
    request: Request,
    q: Optional[str] = None,
    type: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    page: int = Query(1, ge=1),
):
    """Grid / Cards dashboard view."""
    limit = 24
    offset = (page - 1) * limit
    items, total = list_links(
        query=q,
        entry_type=type,
        tag=tag,
        status=status,
        domain=domain,
        limit=limit,
        offset=offset,
    )
    total_pages = max(1, (total + limit - 1) // limit)

    ctx = get_base_context(request, "grid")
    ctx.update({
        "items": items,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "q": q or "",
        "selected_type": type or "",
        "selected_tag": tag or "",
        "selected_status": status or "",
        "selected_domain": domain or "",
    })
    return templates.TemplateResponse(request=request, name="index.html", context=ctx)


@router.get("/list", response_class=HTMLResponse)
def list_view(
    request: Request,
    q: Optional[str] = None,
    type: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    domain: Optional[str] = None,
    page: int = Query(1, ge=1),
):
    """Compact Table / List view."""
    limit = 50
    offset = (page - 1) * limit
    items, total = list_links(
        query=q,
        entry_type=type,
        tag=tag,
        status=status,
        domain=domain,
        limit=limit,
        offset=offset,
    )
    total_pages = max(1, (total + limit - 1) // limit)

    ctx = get_base_context(request, "list")
    ctx.update({
        "items": items,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "q": q or "",
        "selected_type": type or "",
        "selected_tag": tag or "",
        "selected_status": status or "",
        "selected_domain": domain or "",
    })
    return templates.TemplateResponse(request=request, name="list.html", context=ctx)


@router.get("/kanban", response_class=HTMLResponse)
def kanban_view(request: Request):
    """Reading workflow Kanban board grouped by status."""
    inbox, _ = list_links(status="inbox", limit=50)
    reading, _ = list_links(status="reading", limit=50)
    archived, _ = list_links(status="archived", limit=50)
    favorite, _ = list_links(status="favorite", limit=50)

    ctx = get_base_context(request, "kanban")
    ctx.update({
        "inbox": inbox,
        "reading": reading,
        "archived": archived,
        "favorite": favorite,
    })
    return templates.TemplateResponse(request=request, name="kanban.html", context=ctx)


@router.get("/reader/{link_id}", response_class=HTMLResponse)
def reader_view(request: Request, link_id: str):
    """Distraction-free Reader Mode for reading archived article markdown."""
    link = get_link(link_id)
    if not link:
        return HTMLResponse("<h1>Link not found</h1>", status_code=404)

    # Convert markdown to clean HTML
    raw_md = link.content_markdown or (f"*(No archived body content. Showing summary)*\n\n{link.summary}")
    rendered_html = markdown.markdown(
        raw_md,
        extensions=["fenced_code", "tables", "nl2br", "sane_lists"]
    )

    ctx = get_base_context(request, "reader")
    ctx.update({
        "link": link,
        "rendered_html": rendered_html,
    })
    return templates.TemplateResponse(request=request, name="reader.html", context=ctx)


@router.get("/calendar", response_class=HTMLResponse)
def calendar_view(request: Request):
    """Timeline and calendar activity view."""
    cal_data = get_calendar_data()
    ctx = get_base_context(request, "calendar")
    ctx.update({
        "calendar_data": cal_data,
    })
    return templates.TemplateResponse(request=request, name="calendar.html", context=ctx)


@router.get("/graph", response_class=HTMLResponse)
def graph_view(request: Request):
    """D3.js force-directed knowledge graph view."""
    ctx = get_base_context(request, "graph")
    return templates.TemplateResponse(request=request, name="graph.html", context=ctx)


@router.get("/snapshot/{link_id}", response_class=HTMLResponse)
def view_snapshot(link_id: str):
    """Serve offline HTML snapshot of an archived page."""
    from app.config import VAULT_DIR
    link = get_link(link_id)
    if not link or not link.offline_snapshot_path:
        return HTMLResponse("<h3>No offline HTML snapshot available for this link.</h3>", status_code=404)
    file_path = VAULT_DIR / link.offline_snapshot_path
    if not file_path.exists():
        return HTMLResponse("<h3>Snapshot file not found on disk.</h3>", status_code=404)
    return HTMLResponse(file_path.read_text(encoding="utf-8", errors="replace"))


@router.get("/bookmarklet", response_class=HTMLResponse)
def bookmarklet_view(request: Request, url: str = "", title: str = "", quote: str = ""):
    """Popup helper for the 1-click browser bookmarklet."""
    ctx = {
        "request": request,
        "url": url,
        "title": title,
        "quote": quote,
    }
    return templates.TemplateResponse(request=request, name="bookmarklet.html", context=ctx)
