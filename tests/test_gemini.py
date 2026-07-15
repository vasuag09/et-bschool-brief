"""T7 — Gemini client: no-key degrade, JSON parsing incl. code-fence stripping, fallback."""
from unittest.mock import MagicMock, patch

from etbrief import gemini


def _resp(status, text=""):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
    return r


def test_available_reflects_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert gemini.available() is False
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    assert gemini.available() is True


def test_generate_returns_empty_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert gemini.generate("prompt", rate_limit=0) == {}


def test_generate_parses_plain_json(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    with patch.object(gemini.requests, "post", return_value=_resp(200, '{"items": [1]}')):
        assert gemini.generate("p", rate_limit=0) == {"items": [1]}


def test_generate_strips_code_fence(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    fenced = '```json\n{"ok": true}\n```'
    with patch.object(gemini.requests, "post", return_value=_resp(200, fenced)):
        assert gemini.generate("p", rate_limit=0) == {"ok": True}


def test_generate_falls_back_on_404_then_succeeds(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    responses = [_resp(404), _resp(200, '{"done": 1}')]
    with patch.object(gemini.requests, "post", side_effect=responses), \
         patch.object(gemini.time, "sleep"):
        assert gemini.generate("p", rate_limit=0) == {"done": 1}


def test_generate_returns_empty_on_bad_json(monkeypatch):
    # 200 with unparseable body: falls through all models, ends up {} (no valid model).
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    with patch.object(gemini.requests, "post", return_value=_resp(200, "not json")), \
         patch.object(gemini.time, "sleep"):
        assert gemini.generate("p", rate_limit=0) == {}


def test_generate_returns_empty_when_all_models_404(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    with patch.object(gemini.requests, "post", return_value=_resp(404)), \
         patch.object(gemini.time, "sleep"):
        assert gemini.generate("p", rate_limit=0) == {}


def test_generate_returns_empty_on_network_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    with patch.object(gemini.requests, "post",
                      side_effect=gemini.requests.RequestException("boom")):
        assert gemini.generate("p", rate_limit=0) == {}
