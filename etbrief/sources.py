"""COLLECT stage — fetch and normalize RSS items from the configured feeds.

Uses feedparser (handles ET's CDATA-wrapped titles and RSS/Atom variance). Every
feed is fetched independently so one broken feed never aborts the run (AC-1).
"""
from __future__ import annotations

import html
import re
import socket

import feedparser

from etbrief.models import Article

_TAG_RE = re.compile(r"<[^>]+>")
_FEED_TIMEOUT = 20  # seconds — feedparser uses urllib, which honors the socket default


def _clean(text: str) -> str:
    """Strip HTML tags/entities that RSS summaries often carry."""
    if not text:
        return ""
    return html.unescape(_TAG_RE.sub("", text)).strip()


def _normalize(entry, source_name: str, is_et: bool) -> Article | None:
    """Convert a feedparser entry to an Article, or None if it has no link."""
    url = (entry.get("link") or "").strip()
    if not url:
        return None
    return Article(
        title=_clean(entry.get("title", "")),
        url=url,
        summary=_clean(entry.get("summary", "") or entry.get("description", "")),
        source=source_name,
        is_et=is_et,
        published=entry.get("published", "") or entry.get("updated", ""),
    )


def dedupe(articles: list[Article]) -> list[Article]:
    """Collapse duplicate URLs (AC-8). On collision the ET copy wins (AC-3).

    Drops articles without a URL. Preserves first-seen order otherwise.
    """
    by_url: dict[str, Article] = {}
    for art in articles:
        if not art.url:
            continue
        existing = by_url.get(art.url)
        if existing is None:
            by_url[art.url] = art
        elif art.is_et and not existing.is_et:
            by_url[art.url] = art  # prefer ET attribution
    return list(by_url.values())


def collect(sources_cfg: list[dict], max_items: int) -> list[Article]:
    """Fetch all configured feeds, normalize, cap per feed, and dedupe.

    A failing/malformed single feed is logged and skipped (AC-1).
    """
    collected: list[Article] = []
    socket.setdefaulttimeout(_FEED_TIMEOUT)  # stop a hung feed from eating the job budget
    for src in sources_cfg:
        name = src.get("name", "?")
        try:
            # Extract config keys inside the try so a malformed entry skips only
            # this feed, not the whole run (AC-1).
            url, is_et = src["url"], bool(src.get("is_et"))
            # Only fetch https feeds — blocks file://, http, and other schemes
            # (defense-in-depth against SSRF/LFI if config is ever untrusted).
            if not url.lower().startswith("https://"):
                print(f"[collect] {name}: skipped — non-https feed URL")
                continue
            parsed = feedparser.parse(url)
            if getattr(parsed, "bozo", 0) and getattr(parsed, "bozo_exception", None):
                print(f"[collect] {name}: malformed feed ({parsed.bozo_exception}) — parsing what we can")
            entries = getattr(parsed, "entries", []) or []
            kept = 0
            for entry in entries:
                if kept >= max_items:
                    break
                art = _normalize(entry, name, is_et)
                if art is not None:
                    collected.append(art)
                    kept += 1
            print(f"[collect] {name}: {kept} items")
        except Exception as exc:  # noqa: BLE001 — one bad feed must not kill the run
            print(f"[collect] {name}: FAILED ({exc}) — skipping")
    deduped = dedupe(collected)
    print(f"[collect] {len(deduped)} unique items from {len(sources_cfg)} feeds")
    return deduped
