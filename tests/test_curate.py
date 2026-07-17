"""T3 tests — curation: topic filtering (AC-2), item shape (AC-3), degrade path."""
from etbrief.models import Article
from etbrief import curate


def _art(title, url, is_et=False):
    return Article(title=title, url=url, summary="", source="S", is_et=is_et)


CFG = {
    "digest": {"max_items": 12, "max_themes": 5},
    "curation": {"reader_context": "MBA student"},
    "ai": {"batch_size": 5, "rate_limit_seconds": 0},
}


def test_curate_keeps_business_drops_sport_via_ai_selection():
    # AC-2: the AI returns only business items (by index); sport item is omitted → dropped.
    arts = [
        _art("RBI hikes repo rate", "https://x/1", is_et=True),
        _art("India wins cricket match", "https://x/2"),
        _art("Tata acquires startup", "https://x/3", is_et=True),
    ]

    def fake_generate(prompt, rate_limit=0):
        return {"items": [
            {"index": 0, "headline": "RBI hikes rate", "takeaway": "t", "why_it_matters": "w", "theme": "Economy"},
            {"index": 2, "headline": "Tata buys", "takeaway": "t", "why_it_matters": "w", "theme": "Corporate"},
        ]}

    digest = curate.curate(arts, CFG, generate_fn=fake_generate)
    urls = {i.url for i in digest.items}
    assert urls == {"https://x/1", "https://x/3"}  # cricket dropped
    assert digest.degraded is False


def test_curate_items_have_full_shape_and_et_flag():
    # AC-3: each item has headline + takeaway + why_it_matters; ET flag preserved.
    arts = [_art("RBI policy", "https://x/1", is_et=True)]

    def fake_generate(prompt, rate_limit=0):
        return {"items": [
            {"index": 0, "headline": "RBI", "takeaway": "two lines", "why_it_matters": "matters", "theme": "Economy"},
        ]}

    item = curate.curate(arts, CFG, generate_fn=fake_generate).items[0]
    assert item.headline and item.takeaway and item.why_it_matters
    assert item.is_et is True


def test_curate_degrades_when_ai_unavailable():
    # AI down (returns {}) → degraded digest, headline-only, not empty.
    arts = [_art("Some biz news", "https://x/1", is_et=True), _art("More news", "https://x/2")]

    digest = curate.curate(arts, CFG, generate_fn=lambda *a, **k: {})
    assert digest.degraded is True
    assert len(digest.items) == 2
    assert digest.items[0].headline == "Some biz news"


def test_curate_valid_empty_selection_is_not_degraded_dump():
    # AC-2 regression: AI runs fine but selects nothing → empty Digest, NOT a raw
    # unfiltered dump of the (possibly sport/lifestyle) articles.
    arts = [_art("India wins cricket", "https://x/1"), _art("Bollywood gossip", "https://x/2")]
    digest = curate.curate(arts, CFG, generate_fn=lambda *a, **k: {"items": []})
    assert digest.degraded is False
    assert digest.items == ()          # nothing selected → nothing emitted


def test_curate_partial_batch_failure_keeps_successful_items():
    # One batch call fails ({}), the other succeeds — succeeded items still ship,
    # and the failure does not trigger a full degrade.
    arts = [_art(f"n{i}", f"https://x/{i}", is_et=True) for i in range(10)]  # 2 batches of 5
    calls = {"n": 0}

    def flaky(prompt, rate_limit=0):
        calls["n"] += 1
        if calls["n"] == 1:
            return {}  # first batch call fails
        return {"items": [{"index": 0, "headline": "H", "takeaway": "t",
                           "why_it_matters": "w", "theme": "T"}]}

    digest = curate.curate(arts, CFG, generate_fn=flaky)
    assert digest.degraded is False
    assert len(digest.items) == 1


def test_curate_caps_at_max_items():
    arts = [_art(f"News {i}", f"https://x/{i}", is_et=True) for i in range(20)]

    def fake_generate(prompt, rate_limit=0):
        # AI returns all indices in this batch
        # crude: return every item mentioned by echoing indices 0..n
        return {"items": [
            {"index": i, "headline": f"H{i}", "takeaway": "t", "why_it_matters": "w", "theme": "T"}
            for i in range(20)
        ]}

    digest = curate.curate(arts, {**CFG, "digest": {"max_items": 12, "max_themes": 5}}, generate_fn=fake_generate)
    assert len(digest.items) <= 12
