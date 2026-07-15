"""Orchestrator — fetch → dedup → curate → build → send. Runs once per invocation.

Exit code 0 on a normal run; non-zero when there were no items (AC-6) so a scheduler
surfaces the empty day. Designed so `run()` is unit-testable with injected deps.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv

from etbrief import curate as _curate
from etbrief import digest as _digest
from etbrief import mailer as _mailer
from etbrief import sources as _sources

_IST = ZoneInfo("Asia/Kolkata")
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path: Path = _CONFIG_PATH) -> dict:
    return yaml.safe_load(path.read_text())


def _today_ist() -> str:
    return datetime.now(timezone.utc).astimezone(_IST).strftime("%d %b %Y")


def run(
    config: dict,
    *,
    collect_fn=_sources.collect,
    curate_fn=_curate.curate,
    build_fn=_digest.build,
    send_fn=_mailer.send,
    recipient: str | None = None,
) -> int:
    """Execute one full pipeline pass. Returns a process exit code."""
    date_str = _today_ist()
    to = (recipient or config.get("delivery", {}).get("to", "")).strip()
    if not to:
        raise RuntimeError(
            "No recipient set — provide BRIEF_TO or delivery.to in config.yaml."
        )

    articles = collect_fn(config["sources"], config.get("max_items_per_feed", 15))

    if not articles:
        print("[main] no items fetched — sending empty-day notice")
        html = build_fn(_digest.Digest(items=()), date_str)
        send_fn(html, _digest.subject(date_str, config), to)
        return 1  # non-zero for observability (AC-6)

    digest = curate_fn(articles, config)
    if not digest.items:
        print("[main] nothing survived curation — sending empty-day notice")
        send_fn(build_fn(_digest.Digest(items=()), date_str), _digest.subject(date_str, config), to)
        return 1

    html = build_fn(digest, date_str)
    send_fn(html, _digest.subject(date_str, config), to)
    print(f"[main] sent {len(digest.items)} items (degraded={digest.degraded})")
    return 0


def main() -> int:
    load_dotenv()
    # BRIEF_TO (env / GH secret) overrides config.yaml's recipient when set.
    return run(load_config(), recipient=os.environ.get("BRIEF_TO") or None)


if __name__ == "__main__":
    sys.exit(main())
