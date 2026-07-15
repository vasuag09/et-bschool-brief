"""T6 tests — orchestrator wiring: empty-day non-zero exit (AC-6), happy path (AC-1..4)."""
from etbrief.models import Article, CuratedItem, Digest
from etbrief import main


CFG = {
    "sources": [{"name": "F", "url": "u", "is_et": True}],
    "max_items_per_feed": 15,
    "delivery": {"to": "to@example.com", "subject_prefix": "Brief"},
    "digest": {"max_items": 12},
}


def test_empty_day_sends_notice_and_exits_nonzero():
    sent = {}

    def fake_send(html, subject, to):
        sent["html"], sent["to"] = html, to

    code = main.run(
        CFG,
        collect_fn=lambda *a, **k: [],           # no articles
        send_fn=fake_send,
    )
    assert code == 1                              # AC-6 observability
    assert "no items" in sent["html"].lower()
    assert sent["to"] == "to@example.com"


def test_happy_path_curates_and_sends_zero():
    sent = {}

    def fake_send(html, subject, to):
        sent["subject"] = subject

    item = CuratedItem("H", "t", "w", "Economy", "Economic Times", "https://x/1", True)

    code = main.run(
        CFG,
        collect_fn=lambda *a, **k: [Article("H", "https://x/1", "", "ET", True)],
        curate_fn=lambda arts, cfg: Digest(items=(item,)),
        send_fn=fake_send,
    )
    assert code == 0
    assert "Brief" in sent["subject"]


def test_degraded_digest_still_sends_and_exits_zero():
    # AI unavailable → degraded headline digest; run still succeeds (exit 0) and
    # the email carries the degraded notice.
    sent = {}
    item = CuratedItem("H", "raw", "", "ET", "Economic Times", "https://x/1", True)
    code = main.run(
        CFG,
        collect_fn=lambda *a, **k: [Article("H", "https://x/1", "", "ET", True)],
        curate_fn=lambda arts, cfg: Digest(items=(item,), degraded=True, note="AI unavailable"),
        send_fn=lambda html, subject, to: sent.update(html=html),
    )
    assert code == 0
    assert "unavailable" in sent["html"].lower()


def test_run_raises_without_recipient():
    import pytest
    cfg = {**CFG, "delivery": {"to": ""}}
    with pytest.raises(RuntimeError, match="recipient"):
        main.run(cfg, collect_fn=lambda *a, **k: [], send_fn=lambda *a, **k: None)


def test_curation_empty_falls_back_to_notice():
    sent = {}
    code = main.run(
        CFG,
        collect_fn=lambda *a, **k: [Article("H", "https://x/1", "", "ET", True)],
        curate_fn=lambda arts, cfg: Digest(items=()),   # AI kept nothing
        send_fn=lambda html, subject, to: sent.update(html=html),
    )
    assert code == 1
    assert "no items" in sent["html"].lower()
