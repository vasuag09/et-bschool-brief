"""Data models. Immutable dataclasses passed between the collect → curate → deliver stages."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Article:
    """One normalized news item as fetched from an RSS feed."""

    title: str
    url: str
    summary: str
    source: str
    is_et: bool
    published: str = ""


@dataclass(frozen=True)
class CuratedItem:
    """One curated item ready for the digest."""

    headline: str
    takeaway: str        # 2–3 line summary
    why_it_matters: str
    theme: str
    source: str
    url: str
    is_et: bool


@dataclass(frozen=True)
class Digest:
    """The final curated brief.

    `degraded` is True when AI curation was unavailable and items are a raw,
    filtered-but-unsummarized fallback (headline-only). The digest builder and
    the email both surface this so the reader knows.
    """

    items: tuple[CuratedItem, ...] = field(default_factory=tuple)
    degraded: bool = False
    note: str = ""
