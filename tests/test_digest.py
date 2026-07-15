"""T4 tests — HTML digest builder: item shape (AC-3), empty-day (AC-6), degraded note."""
from etbrief.models import CuratedItem, Digest
from etbrief import digest as dg


def _item(headline="RBI hikes rate", theme="Economy", is_et=True):
    return CuratedItem(
        headline=headline,
        takeaway="The RBI raised the repo rate by 25bps.",
        why_it_matters="Signals a tightening cycle relevant to corporate borrowing.",
        theme=theme,
        source="Economic Times" if is_et else "Livemint",
        url="https://x/1",
        is_et=is_et,
    )


def test_empty_digest_renders_no_items_message():
    html = dg.build(Digest(items=()), "15 Jul 2026")
    assert "no items" in html.lower()
    assert "<html" in html.lower()


def test_normal_digest_includes_all_fields_and_theme():
    d = Digest(items=(_item(),))
    html = dg.build(d, "15 Jul 2026")
    assert "RBI hikes rate" in html
    assert "why it matters" in html.lower()
    assert "Signals a tightening cycle" in html
    assert "Economy" in html            # theme grouping header
    assert "15 Jul 2026" in html        # dated


def test_et_item_is_attributed():
    html = dg.build(Digest(items=(_item(is_et=True),)), "15 Jul 2026")
    assert "Economic Times" in html


def test_degraded_digest_shows_notice():
    d = Digest(items=(_item(),), degraded=True, note="AI curation was unavailable today.")
    html = dg.build(d, "15 Jul 2026")
    assert "unavailable" in html.lower()


def test_subject_is_dated():
    subj = dg.subject("15 Jul 2026", {"delivery": {"subject_prefix": "ET Brief"}})
    assert "ET Brief" in subj and "15 Jul 2026" in subj


def test_all_untrusted_fields_escaped_no_xss():
    # Security invariant: no untrusted field can inject markup into the email.
    item = CuratedItem(
        headline="<script>alert(1)</script>",
        takeaway='"><img src=x onerror=alert(1)>',
        why_it_matters="</style><b>x</b>",
        theme="<i>evil</i>",
        source='"><svg onload=alert(1)>',
        url="javascript:alert(1)",
        is_et=False,
    )
    html = dg.build(Digest(items=(item,)), "15 Jul 2026")
    for payload in ("<script>", "<img src=x", "<svg onload", "<i>evil</i>"):
        assert payload not in html
    assert "&lt;script&gt;" in html    # the payload survived only in escaped form
    assert 'href="#"' in html          # unsafe scheme neutralized


def test_unsafe_url_scheme_rendered_inert():
    item = CuratedItem("H", "t", "w", "T", "S", "javascript:alert(1)", False)
    html = dg.build(Digest(items=(item,)), "15 Jul 2026")
    assert "javascript:" not in html
    assert 'href="#"' in html


def test_build_escapes_html_in_content():
    d = Digest(items=(_item(headline="Tata & Sons <script>"),))
    html = dg.build(d, "15 Jul 2026")
    assert "<script>" not in html          # escaped, not injected
    assert "Tata &amp; Sons" in html
