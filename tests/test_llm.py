"""LLM client (Claude on Bedrock): no-token degrade, prefill-JSON parsing, error paths."""
from unittest.mock import MagicMock, patch

from etbrief import llm

_TOKEN = "AWS_BEARER_TOKEN_BEDROCK"


def _resp(status, text=""):
    """Build a fake Bedrock InvokeModel response (native Anthropic body). `text` is the
    reply AFTER the prefilled "{" — the client re-attaches the opening brace itself."""
    r = MagicMock()
    r.status_code = status
    r.json.return_value = {"content": [{"type": "text", "text": text}]}
    return r


def test_available_reflects_env(monkeypatch):
    monkeypatch.delenv(_TOKEN, raising=False)
    assert llm.available() is False
    monkeypatch.setenv(_TOKEN, "k")
    assert llm.available() is True


def test_generate_returns_empty_without_token(monkeypatch):
    monkeypatch.delenv(_TOKEN, raising=False)
    assert llm.generate("prompt", rate_limit=0) == {}


def test_generate_parses_prefilled_json(monkeypatch):
    # Reply omits the leading "{" (it was prefilled); client re-attaches it.
    monkeypatch.setenv(_TOKEN, "k")
    with patch.object(llm.requests, "post", return_value=_resp(200, '"items": [1]}')):
        assert llm.generate("p", rate_limit=0) == {"items": [1]}


def test_generate_trims_trailing_prose(monkeypatch):
    # Any stray text after the closing brace is trimmed before parsing.
    monkeypatch.setenv(_TOKEN, "k")
    with patch.object(llm.requests, "post", return_value=_resp(200, '"ok": true} done')):
        assert llm.generate("p", rate_limit=0) == {"ok": True}


def test_generate_returns_empty_on_bad_json(monkeypatch):
    monkeypatch.setenv(_TOKEN, "k")
    with patch.object(llm.requests, "post", return_value=_resp(200, "not json")):
        assert llm.generate("p", rate_limit=0) == {}


def test_generate_returns_empty_on_access_denied(monkeypatch):
    # 403: model not enabled / bad token — degrade, don't crash.
    monkeypatch.setenv(_TOKEN, "k")
    with patch.object(llm.requests, "post", return_value=_resp(403)):
        assert llm.generate("p", rate_limit=0) == {}


def test_generate_retries_once_when_throttled_then_succeeds(monkeypatch):
    # 429 (throttled) → one backoff retry → success.
    monkeypatch.setenv(_TOKEN, "k")
    responses = [_resp(429), _resp(200, '"done": 1}')]
    with patch.object(llm.requests, "post", side_effect=responses), \
         patch.object(llm.time, "sleep"):
        assert llm.generate("p", rate_limit=0) == {"done": 1}


def test_generate_returns_empty_when_throttled_twice(monkeypatch):
    # Persistent throttling: retry exhausted → {}.
    monkeypatch.setenv(_TOKEN, "k")
    with patch.object(llm.requests, "post", return_value=_resp(429)), \
         patch.object(llm.time, "sleep"):
        assert llm.generate("p", rate_limit=0) == {}


def test_generate_returns_empty_on_network_error(monkeypatch):
    monkeypatch.setenv(_TOKEN, "k")
    with patch.object(llm.requests, "post",
                      side_effect=llm.requests.RequestException("boom")):
        assert llm.generate("p", rate_limit=0) == {}
