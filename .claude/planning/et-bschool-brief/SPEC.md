# Spec: ET B-School Brief — daily Economic Times digest to Gmail

> **Status: SHIPPED** — all acceptance criteria met; verified live (real brief delivered
> to the user's Gmail). Model upgraded to Gemini 3.1 Pro; summaries are detailed.

## Problem
An MBA-Tech student must read Economic Times daily for a management course but lacks
time to read the full paper. They want a curated, B-school-relevant daily digest —
strategy, economy, corporate moves, policy, markets, leadership — delivered to their
Gmail automatically every morning, at zero cost.

## In scope
- Ingest Economic Times via its **public RSS feeds** (primary source).
- Supplement with **other free business-news RSS feeds** (e.g. Livemint, Business
  Standard, BusinessLine) to fill gaps. ET remains primary.
- Optional per-article full-text fetch **only where the page is not paywalled**.
- Use an **LLM (Gemini 3.1 Pro — quality-first, billed)** to filter to management-relevant
  items and write detailed summaries. (Originally scoped to free Gemini Flash; user opted
  into billing for best quality.)
- Format a readable digest and **email it to the user's Gmail**.
- Run automatically on a **free daily GitHub Actions cron**.
- Store secrets (LLM key, Gmail credentials) as GitHub Actions secrets.

## Out of scope
- Paywall circumvention, ET Prime/epaper login scraping, or credentialed access.
- Co-equal treatment of non-ET sources (they are supplementary only).
- Web UI / dashboard, archive/search, or multi-recipient distribution.
- Paid *infrastructure* (Vercel, servers). Note: the LLM is now a billed Gemini Pro by
  user choice; hosting/scheduling stays free on GitHub Actions.

## Acceptance criteria
- [x] AC-1: Given a scheduled daily run, when the job executes, then it fetches items
      from Economic Times RSS feeds plus at least one supplementary free feed, and does
      not error out if a single feed is unavailable (degrades gracefully).
- [x] AC-2: Given the fetched items, when the LLM curates them, then sports, lifestyle,
      and entertainment items are excluded and business/management-relevant items
      (strategy, economy, corporate, policy, markets, leadership) are retained.
- [x] AC-3: Given curated items, when the digest is generated, then each item includes a
      headline, a DETAILED self-contained summary (≈5–8 sentences — the reader should
      grasp the full story without opening the article), and a "why it matters" note;
      ET-sourced items are clearly attributed and prioritized over supplementary sources.
      (Revised post-verify: user wants detailed summaries, not a terse brief.)
- [x] AC-4: Given a generated digest, when delivery runs, then an email is sent to the
      configured Gmail address with a dated subject line and the digest as readable HTML.
- [x] AC-5: Given the GitHub Actions cron trigger, when the scheduled time arrives, then
      the full pipeline (fetch → curate → format → email) runs unattended with no local
      machine required.
- [x] AC-6: Given no article content available on a given day (all feeds empty/failed),
      when the job runs, then it sends a clearly-labeled "no items today" email rather
      than a broken/empty one, and exits non-zero for observability.
- [x] AC-7: Given secrets are configured, when the workflow runs, then no API keys or
      Gmail credentials are hardcoded in the repo — all read from GitHub Actions secrets.
- [x] AC-8: Given deduplicated input, when the same story appears across multiple feeds,
      then it appears only once in the digest.

## Constraints
- **Cost:** hosting/scheduling free (GitHub Actions); LLM billed (Gemini 3.1 Pro, user's
  choice for quality). No servers.
- **Legality/robustness:** RSS-first; no paywall bypass; tolerate feed schema changes.
- **Delivery target:** vasuagrawal1040@gmail.com.
- **Security:** all credentials via GitHub Actions secrets; none committed.
- **Language:** implementation language open (Python likely, matches free-LLM tooling).

## Reuse decision (from /research)
- **Port** the `data-scraper-agent` skill's architecture (~80% fit): its COLLECT→ENRICH
  layers, the free **Gemini Flash REST client with model fallback** (directly reusable),
  **batch AI calls**, URL **dedup**, **config.yaml**-driven settings, and the **GitHub
  Actions cron** workflow all map straight onto this project.
- **Replace** the skill's STORE layer (Notion/Sheets/Supabase) with a new **DELIVER**
  module: build the curated items into an **HTML digest** and send via **Gmail SMTP +
  App Password** (Python stdlib `smtplib`/`email`). No database.
- **Drop** the skill's feedback/learning loop (`ai/memory.py`) and persistent DB dedup —
  out of scope; dedup happens within each day's run. (YAGNI.)
- **Build new** (genuinely novel): the RSS ingestion set + the *curation* prompt
  (theme-grouping + "why it matters" for a B-school reader, vs. the skill's 0–100 scoring).
- **Library choice:** use **`feedparser`** (not raw ElementTree) — ET titles arrive as
  CDATA and feeds vary between RSS/Atom; feedparser normalizes both. Runner-up (stdlib
  ElementTree) rejected: brittle on CDATA/malformed feeds.

## Verified facts the plan must respect
- **ET RSS is public** (HTTP 200): top-stories `rssfeedstopstories.cms` (~50 items);
  section feeds exist for Markets / Economy / Industry. Titles are CDATA-wrapped.
- **Supplementary feeds:** Livemint (`livemint.com/rss/markets`, ~35 items) and
  **The Hindu BusinessLine** (`.../economy|markets/feeder/default.rss`, ~60 items each).
  **Business Standard RSS returns 403 to bots — excluded.**
- **Gemini:** endpoint `POST generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=…`
  is stable; free tier via `GEMINI_API_KEY`. The model-fallback chain must tolerate a
  model 404'ing (free-tier model availability drifts).
- **Gmail send:** `smtplib` over SSL (`smtp.gmail.com:465`) with a 16-char App Password —
  no OAuth. Requires 2FA enabled on the account to mint an App Password.

## Risks of chosen dependencies
- **Gemini free-tier drift** — model names / RPD limits change; mitigated by the fallback
  chain + graceful skip if `GEMINI_API_KEY` unset.
- **feedparser** — mature (v6.x), permissive license, tiny footprint; low risk.
- **ET feed schema** — CDATA/section-id URLs can change; mitigated by per-feed try/except
  (AC-1 graceful degrade).

## Open questions (with recommended defaults)
- **Delivery time?** Default: **07:00 IST** daily (before class). Cron in UTC = `30 1 * * *`.
- **Digest length?** Default: top 3–5 themes + **8–12 curated items**, capped to keep the
  email skimmable in ~5 minutes.
- **Gmail send mechanism?** Default: **Gmail SMTP with an App Password** (simplest for a
  GitHub Actions cron; no OAuth refresh-token maintenance).
- **Supplementary sources?** Default: **Livemint + Business Standard + BusinessLine** RSS.
