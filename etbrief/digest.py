"""DELIVER (format) stage — render a Digest into a skimmable HTML email body.

Pure functions: no I/O. All dynamic content is HTML-escaped (AC — no injection).
Items are grouped by theme; ET items are visually attributed.
"""
from __future__ import annotations

from collections import OrderedDict
from html import escape

from etbrief.models import CuratedItem, Digest

_STYLE = """
  body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
       color:#1a1a1a;line-height:1.5;margin:0;padding:0;background:#f6f7f9}
  .wrap{max-width:640px;margin:0 auto;padding:24px}
  h1{font-size:22px;margin:0 0 4px}
  .date{color:#666;font-size:13px;margin:0 0 20px}
  .theme{font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;
         color:#b8860b;border-bottom:1px solid #e5e5e5;padding-bottom:4px;margin:24px 0 12px}
  .item{margin:0 0 18px}
  .headline{font-size:16px;font-weight:600;margin:0 0 4px}
  .headline a{color:#111;text-decoration:none}
  .src{font-size:11px;font-weight:600;color:#fff;background:#c0392b;border-radius:3px;
       padding:1px 6px;margin-left:6px;vertical-align:middle}
  .src.other{background:#7f8c8d}
  .takeaway{margin:2px 0;font-size:14px}
  .why{margin:2px 0;font-size:13px;color:#555}
  .why b{color:#333}
  .notice{background:#fff3cd;border:1px solid #ffe69c;border-radius:6px;
          padding:10px 12px;font-size:13px;margin:0 0 16px}
  .foot{color:#999;font-size:11px;margin-top:28px;border-top:1px solid #e5e5e5;padding-top:12px}
"""


def subject(date_str: str, config: dict) -> str:
    prefix = config.get("delivery", {}).get("subject_prefix", "ET B-School Brief")
    return f"{prefix} — {date_str}"


def _safe_href(url: str) -> str:
    """Only allow http(s) links; anything else (javascript:, data:) renders inert."""
    return url if url.lower().startswith(("http://", "https://")) else "#"


def _render_item(item: CuratedItem) -> str:
    badge = (
        '<span class="src">ET</span>'
        if item.is_et
        else f'<span class="src other">{escape(item.source)}</span>'
    )
    link = escape(_safe_href(item.url), quote=True)
    parts = [
        '<div class="item">',
        f'<p class="headline"><a href="{link}">{escape(item.headline)}</a>{badge}</p>',
    ]
    if item.takeaway:
        parts.append(f'<p class="takeaway">{escape(item.takeaway)}</p>')
    if item.why_it_matters:
        parts.append(f'<p class="why"><b>Why it matters:</b> {escape(item.why_it_matters)}</p>')
    parts.append("</div>")
    return "".join(parts)


def _group_by_theme(items: tuple[CuratedItem, ...]) -> "OrderedDict[str, list[CuratedItem]]":
    groups: OrderedDict[str, list[CuratedItem]] = OrderedDict()
    for item in items:
        groups.setdefault(item.theme or "General", []).append(item)
    return groups


def build(digest: Digest, date_str: str) -> str:
    """Render the full HTML email body for a Digest."""
    body: list[str] = []

    if digest.degraded and digest.note:
        body.append(f'<div class="notice">⚠️ {escape(digest.note)}</div>')

    if not digest.items:
        body.append(
            '<div class="notice">No items today — all feeds were empty or unavailable. '
            "Nothing to summarize.</div>"
        )
    else:
        for theme, group in _group_by_theme(digest.items).items():
            body.append(f'<p class="theme">{escape(theme)}</p>')
            body.extend(_render_item(i) for i in group)

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>{_STYLE}</style></head>
<body><div class="wrap">
  <h1>📈 ET B-School Brief</h1>
  <p class="date">{escape(date_str)}</p>
  {''.join(body)}
  <p class="foot">Curated from Economic Times &amp; free business feeds. Read the full
  articles via the links above.</p>
</div></body></html>"""
