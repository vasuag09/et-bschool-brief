"""T2 tests — RSS ingestion: dedup (AC-8) and graceful feed failure (AC-1)."""
from unittest.mock import patch

from etbrief.models import Article
from etbrief import sources


def _art(url, title="t", source="S", is_et=False):
    return Article(title=title, url=url, summary="", source=source, is_et=is_et)


def test_dedupe_collapses_same_url_keeping_et():
    # Same story from a non-ET and an ET feed → one item, ET version wins (AC-8, AC-3).
    items = [
        _art("https://x.com/a", source="Livemint", is_et=False),
        _art("https://x.com/a", source="ET", is_et=True),
        _art("https://x.com/b", source="ET", is_et=True),
    ]
    out = sources.dedupe(items)
    assert len(out) == 2
    a = next(i for i in out if i.url == "https://x.com/a")
    assert a.is_et is True  # ET copy preferred on collision


def test_dedupe_drops_items_without_url():
    items = [_art(""), _art("https://x.com/a")]
    assert len(sources.dedupe(items)) == 1


def test_collect_survives_one_broken_feed():
    # AC-1: a single failing feed must not abort the run.
    good = [{"title": "Good", "link": "https://x.com/good", "summary": "s"}]

    def fake_parse(url):
        if "bad" in url:
            raise ValueError("boom")
        return type("F", (), {"entries": good, "bozo": 0})()

    cfg = [
        {"name": "Bad", "url": "https://bad.example/feed", "is_et": True},
        {"name": "Good", "url": "https://good.example/feed", "is_et": False},
    ]
    with patch.object(sources.feedparser, "parse", side_effect=fake_parse):
        out = sources.collect(cfg, max_items=15)
    assert len(out) == 1
    assert out[0].url == "https://x.com/good"


def test_collect_respects_max_items_per_feed():
    many = [{"title": f"T{i}", "link": f"https://x.com/{i}", "summary": ""} for i in range(50)]

    def fake_parse(url):
        return type("F", (), {"entries": many, "bozo": 0})()

    cfg = [{"name": "F", "url": "https://f.example", "is_et": True}]
    with patch.object(sources.feedparser, "parse", side_effect=fake_parse):
        out = sources.collect(cfg, max_items=15)
    assert len(out) == 15
