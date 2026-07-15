"""ENRICH stage — turn raw Articles into a curated, management-relevant Digest.

The LLM does the topic filtering (drop sport/lifestyle, keep business — AC-2) and
writes a takeaway + "why it matters" per kept item (AC-3). If the LLM is unavailable
(no key, or every call fails), we degrade to a headline-only digest rather than send
nothing — the Digest is flagged `degraded` so the email says so.
"""
from __future__ import annotations

from collections.abc import Callable

from etbrief.gemini import generate as _default_generate
from etbrief.models import Article, CuratedItem, Digest

GenerateFn = Callable[..., dict]


def _chunks(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _build_prompt(batch: list[Article], reader_context: str) -> str:
    listing = "\n".join(
        f'{i}. [{"ET" if a.is_et else a.source}] {a.title} — {a.summary[:500]}'
        for i, a in enumerate(batch)
    )
    return f"""You are writing a detailed daily business-news digest.

# Reader
{reader_context}

# Candidate items (index. [source] headline — summary)
{listing}

# Task
Select ONLY the items relevant to the reader (business strategy, economy, corporate
moves, policy, markets, leadership). DROP sports, lifestyle, entertainment, celebrity.
For each SELECTED item, write a DETAILED, self-contained summary — the reader should
understand the full story WITHOUT opening the article. Cover the key facts, the
numbers/figures involved, who the players are, the context or background, and what
happened. Aim for a thorough 5-8 sentence summary, in clear plain language (expand
jargon). Do not be terse — depth is the goal.

# Output (JSON only)
{{"items": [{{"index": <int>, "headline": "<clear, informative headline>",
"takeaway": "<detailed 5-8 sentence summary of the full story>",
"why_it_matters": "<2-3 sentences: why an MBA student should care, tied to a management concept where relevant>",
"theme": "<one of: Economy, Markets, Corporate, Policy, Strategy, Leadership>"}}]}}
Return only items worth the reader's time. Omit weak/irrelevant ones entirely."""


def _to_item(analysis: dict, art: Article) -> CuratedItem:
    return CuratedItem(
        headline=(analysis.get("headline") or art.title).strip(),
        takeaway=(analysis.get("takeaway") or "").strip(),
        why_it_matters=(analysis.get("why_it_matters") or "").strip(),
        theme=(analysis.get("theme") or "General").strip(),
        source=art.source,
        url=art.url,
        is_et=art.is_et,
    )


def _degraded(articles: list[Article], max_items: int) -> Digest:
    """Headline-only fallback when the AI is unavailable."""
    items = tuple(
        CuratedItem(
            headline=a.title,
            takeaway=a.summary[:300],
            why_it_matters="",
            theme="ET" if a.is_et else a.source,
            source=a.source,
            url=a.url,
            is_et=a.is_et,
        )
        for a in articles[:max_items]
    )
    return Digest(
        items=items,
        degraded=True,
        note="AI curation was unavailable today — showing raw headlines.",
    )


def curate(
    articles: list[Article],
    config: dict,
    generate_fn: GenerateFn | None = None,
) -> Digest:
    """Curate articles into a Digest. Falls back to headline-only if the AI fails."""
    if not articles:
        return Digest()

    generate_fn = generate_fn or _default_generate
    digest_cfg = config.get("digest", {})
    max_items = int(digest_cfg.get("max_items", 12))
    ai_cfg = config.get("ai", {})
    batch_size = int(ai_cfg.get("batch_size", 5))
    rate_limit = float(ai_cfg.get("rate_limit_seconds", 7))
    reader_context = config.get("curation", {}).get("reader_context", "")

    curated: list[CuratedItem] = []
    batches = _chunks(articles, batch_size)
    any_call_succeeded = False

    for n, batch in enumerate(batches, 1):
        result = generate_fn(_build_prompt(batch, reader_context), rate_limit=rate_limit)
        # A successful call returns a dict containing "items" (possibly empty);
        # a failed call returns {} (no "items" key). These must not be conflated:
        # an empty selection is a valid AI decision, not a reason to dump raw items.
        call_ok = isinstance(result, dict) and "items" in result
        analyses = result.get("items", []) if call_ok else []
        any_call_succeeded = any_call_succeeded or call_ok
        kept = 0
        for entry in analyses:
            idx = entry.get("index")
            if isinstance(idx, int) and 0 <= idx < len(batch):
                curated.append(_to_item(entry, batch[idx]))
                kept += 1
        status = "ok" if call_ok else "FAILED"
        print(f"[curate] batch {n}/{len(batches)}: {status}, kept {kept}")

    # Only degrade to a raw headline dump if the AI never responded at all.
    # If it responded but selected nothing, return empty → main sends the
    # "no items" notice rather than an unfiltered list (AC-2).
    if not any_call_succeeded:
        print("[curate] AI unavailable for every batch — degrading to headlines")
        return _degraded(articles, max_items)

    # ET items first, then cap (AC-3 prioritization).
    curated.sort(key=lambda i: not i.is_et)
    return Digest(items=tuple(curated[:max_items]), degraded=False)
