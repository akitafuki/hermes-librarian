"""Pydantic data models and schemas."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LinkStatus(str, Enum):
    INBOX = "inbox"
    READING = "reading"
    ARCHIVED = "archived"
    FAVORITE = "favorite"


class LinkType(str, Enum):
    ARTICLE = "article"
    GITHUB = "github"
    VIDEO = "video"
    PAPER = "paper"
    TOOL = "tool"
    X_POST = "x-post"
    OTHER = "other"


class Highlight(BaseModel):
    id: str
    text: str
    note: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class HighlightCreate(BaseModel):
    text: str
    note: Optional[str] = None


class LinkBase(BaseModel):
    url: str
    title: Optional[str] = None
    author: Optional[str] = None
    site_name: Optional[str] = None
    domain: Optional[str] = None
    entry_type: LinkType = LinkType.ARTICLE
    tags: List[str] = Field(default_factory=list)
    status: LinkStatus = LinkStatus.INBOX
    summary: Optional[str] = None
    user_notes: Optional[str] = None
    cover_image: Optional[str] = None
    favicon: Optional[str] = None
    media_meta: Dict[str, Any] = Field(default_factory=dict)
    highlights: List[Highlight] = Field(default_factory=list)
    offline_snapshot_path: Optional[str] = None


class LinkCreate(BaseModel):
    url: str
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[LinkStatus] = LinkStatus.INBOX
    summary: Optional[str] = None
    user_notes: Optional[str] = None
    entry_type: Optional[LinkType] = None
    media_meta: Optional[Dict[str, Any]] = None


class LinkUpdate(BaseModel):
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[LinkStatus] = None
    summary: Optional[str] = None
    user_notes: Optional[str] = None
    entry_type: Optional[LinkType] = None
    media_meta: Optional[Dict[str, Any]] = None
    highlights: Optional[List[Highlight]] = None


class Link(LinkBase):
    id: str
    content_markdown: Optional[str] = ""
    reading_time_minutes: int = 1
    word_count: int = 0
    created_at: str
    updated_at: str
    vault_file: Optional[str] = None


class LinkSummary(BaseModel):
    id: str
    url: str
    title: str
    author: Optional[str] = None
    site_name: Optional[str] = None
    domain: Optional[str] = None
    entry_type: LinkType
    tags: List[str]
    status: LinkStatus
    summary: Optional[str] = None
    cover_image: Optional[str] = None
    favicon: Optional[str] = None
    media_meta: Dict[str, Any] = Field(default_factory=dict)
    reading_time_minutes: int
    word_count: int
    created_at: str
    updated_at: str


class StatsResponse(BaseModel):
    total_links: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    top_tags: list[tuple[str, int]]
    top_domains: list[tuple[str, int]]
    total_words_archived: int
    total_highlights: int = 0
