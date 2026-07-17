"""Amazon Bedrock (Claude Haiku 4.5) REST client.

Cheap, capable curation via Claude on Bedrock — far lower cost than a flagship model
for this summarisation task. Authenticates with a Bedrock API key (bearer token, no
SigV4) read from AWS_BEARER_TOKEN_BEDROCK. Returns a parsed JSON dict, or {} on any
failure — callers must treat {} as "AI unavailable" and degrade gracefully. Never logs
the token.

Region and model id are non-secret deployment config (env-overridable). The model id is
an inference-profile id (region-scoped): ap-south-1 → the 'apac.' profile.

Claude has no native JSON mode, so we prefill the assistant turn with "{" to force the
reply to start a JSON object, then re-attach that brace before parsing.
"""
from __future__ import annotations

import json
import os
import time

import requests

# Deployment config — override via env without touching code. Haiku 4.5 is offered as a
# GLOBAL inference profile (no regional apac./us. profile for this model); the request
# still goes to the ap-south-1 runtime endpoint.
REGION = os.environ.get("BEDROCK_REGION", "ap-south-1")
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0"
)

# Bedrock InvokeModel wraps the Anthropic Messages body; version is fixed by Bedrock.
_ANTHROPIC_VERSION = "bedrock-2023-05-31"
_ENDPOINT = "https://bedrock-runtime.{region}.amazonaws.com/model/{model}/invoke"
_last_call = 0.0


def available() -> bool:
    return bool(os.environ.get("AWS_BEARER_TOKEN_BEDROCK"))


def generate(prompt: str, rate_limit: float = 1.0) -> dict:
    """Call Claude on Bedrock with a JSON prefill. Returns parsed JSON dict or {}."""
    global _last_call

    token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "")
    if not token:
        return {}

    elapsed = time.time() - _last_call
    if elapsed < rate_limit:
        time.sleep(rate_limit - elapsed)
    _last_call = time.time()

    payload = {
        "anthropic_version": _ANTHROPIC_VERSION,  # Bedrock-fixed; model id is in the URL, not the body
        "max_tokens": 8192,  # detailed multi-sentence summaries per batch
        "temperature": 0.3,
        "messages": [
            {"role": "user", "content": prompt},
            # Prefill forces the reply to begin a JSON object — no code fences,
            # no preamble. We re-attach this "{" in _parse before json.loads.
            {"role": "assistant", "content": "{"},
        ],
    }
    url = _ENDPOINT.format(region=REGION, model=MODEL_ID)
    for attempt in range(2):  # one retry for transient throttling/overload
        try:
            resp = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",  # header only — never logged
                    "content-type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            if resp.status_code == 200:
                parsed = _parse(resp)
                if parsed:
                    return parsed
                print("[llm] Bedrock returned unparseable body")
                return {}
            if resp.status_code in (429, 503) and attempt == 0:  # throttled / overloaded
                time.sleep(1)
                continue
            # Other errors (403 access, 400 validation, ...): log status only, never the token.
            print(f"[llm] Bedrock HTTP {resp.status_code}")
            return {}
        except requests.RequestException as exc:
            print(f"[llm] Bedrock request error: {type(exc).__name__}")
            return {}
    return {}


def _parse(resp) -> dict:
    """Re-attach the prefill brace, then JSON-parse the reply. {} on any problem."""
    try:
        text = resp.json()["content"][0]["text"].strip()
        # The assistant turn was prefilled with "{", so the reply omits it.
        candidate = "{" + text
        # Defensive: if any trailing prose slipped in after the object, trim to the
        # last closing brace before parsing.
        end = candidate.rfind("}")
        if end != -1:
            candidate = candidate[: end + 1]
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return {}
