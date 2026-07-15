"""Gemini Flash REST client with model fallback (ported from data-scraper-agent).

Free tier via GEMINI_API_KEY. Returns parsed JSON dict, or {} on any failure —
callers must treat {} as "AI unavailable" and degrade gracefully. Never logs the key.
"""
from __future__ import annotations

import json
import os
import time

import requests

# Quality-first chain (billed account). Try best → fall through on 404/429.
# gemini-pro-latest is an alias to the latest STABLE Pro, so the run keeps working
# even if the preview model above is ever retired.
MODEL_FALLBACK = [
    "gemini-3.1-pro-preview",
    "gemini-pro-latest",
    "gemini-flash-latest",
]

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_last_call = 0.0


def available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def generate(prompt: str, rate_limit: float = 7.0) -> dict:
    """Call Gemini with model fallback. Returns parsed JSON dict or {}."""
    global _last_call

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return {}

    elapsed = time.time() - _last_call
    if elapsed < rate_limit:
        time.sleep(rate_limit - elapsed)
    _last_call = time.time()

    for model in MODEL_FALLBACK:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.3,
                "maxOutputTokens": 8192,  # detailed multi-sentence summaries per batch
            },
        }
        try:
            resp = requests.post(
                _ENDPOINT.format(model=model),
                headers={"x-goog-api-key": api_key},  # header, not query param (avoids log leakage)
                json=payload,
                timeout=30,
            )
            if resp.status_code == 200:
                parsed = _parse(resp)
                if parsed:
                    return parsed
                # 200 but empty/truncated/blocked body — try the next model
                # instead of short-circuiting the fallback chain.
                print(f"[gemini] {model} returned unparseable body — trying next model")
                continue
            if resp.status_code in (429, 404):
                time.sleep(1)
                continue
            # Other errors: log status only, never the key or URL (which carries the key).
            print(f"[gemini] {model} HTTP {resp.status_code} — trying next model")
        except requests.RequestException as exc:
            print(f"[gemini] {model} request error: {type(exc).__name__}")
    return {}


def _parse(resp) -> dict:
    """Extract and JSON-parse the model's text response. {} on any problem."""
    try:
        text = (
            resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        )
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return {}
