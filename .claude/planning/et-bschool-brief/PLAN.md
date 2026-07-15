# Plan: ET B-School Brief

Ported from `data-scraper-agent`: COLLECT (RSS) → ENRICH (Gemini curate) → DELIVER (Gmail).
Language: Python 3.11. All settings in `config.yaml`; all secrets via env / GH Actions.

## Tasks

### Task T1: Project scaffold + config + secrets hygiene
- files: `requirements.txt`, `config.yaml`, `.env.example`, `.gitignore`, `README.md`
- depends_on: []
- addresses: AC-7
- exit check: `pip install -r requirements.txt` succeeds in a fresh venv; `.env` is
  gitignored; `config.yaml` loads via `yaml.safe_load` with no error.

### Task T2: RSS ingestion (COLLECT)
- files: `etbrief/sources.py`, `etbrief/models.py`
- depends_on: [T1]
- addresses: AC-1, AC-8
- exit check: `python -m etbrief.sources` fetches ET top-stories + ≥1 supplementary feed,
  returns a normalized list of items (title, url, summary, source, published, is_et);
  a deliberately broken feed URL is caught (try/except) and the run continues; duplicate
  URLs collapsed to one. Uses `feedparser` (handles ET CDATA).

### Task T3: Gemini curation client + pipeline (ENRICH)
- files: `etbrief/gemini.py`, `etbrief/curate.py`
- depends_on: [T1]
- addresses: AC-2, AC-3
- exit check: `gemini.generate()` posts to the v1beta endpoint with model-fallback and
  returns parsed JSON (or {} on failure/no key); `curate.curate(items)` batches items,
  drops sports/lifestyle/entertainment, keeps business/management items, and returns
  theme-grouped items each with headline + 2–3 line takeaway + "why it matters", ET items
  flagged for priority. Unit-testable with a stubbed `generate`.

### Task T4: HTML digest builder (DELIVER format)
- files: `etbrief/digest.py`
- depends_on: [T3]
- addresses: AC-3, AC-6
- exit check: `digest.build(curated, date)` returns skimmable HTML (themes → items,
  ET prioritized, sources attributed); given empty input it returns a clearly-labeled
  "no items today" body. Snapshot-testable, pure function.

### Task T5: Gmail SMTP sender (DELIVER send)
- files: `etbrief/mailer.py`
- depends_on: [T1]
- addresses: AC-4, AC-6, AC-7
- exit check: `mailer.send(html, subject, to)` connects `smtp.gmail.com:465` SSL using
  `GMAIL_USER`/`GMAIL_APP_PASSWORD` from env, sends multipart HTML; raises clearly if
  creds missing. (Verified in T7 with a real send.)

### Task T6: Orchestrator (main)
- files: `etbrief/main.py`, `etbrief/__init__.py`
- depends_on: [T2, T3, T4, T5]
- addresses: AC-1, AC-2, AC-3, AC-4, AC-6
- exit check: `python -m etbrief.main` runs fetch → dedup → curate → build → send end to
  end; when all feeds yield nothing it sends the "no items" email and exits non-zero;
  a normal run exits zero and logs counts at each stage.

### Task T7: Tests
- files: `tests/test_sources.py`, `tests/test_curate.py`, `tests/test_digest.py`, `tests/test_mailer.py`
- depends_on: [T2, T3, T4, T5]
- addresses: AC-1, AC-2, AC-3, AC-6, AC-8
- exit check: `pytest` green ≥80% on `etbrief/` core logic; network + SMTP + Gemini
  mocked; dedup, sports-exclusion, and empty-day paths each covered.

### Task T8: GitHub Actions cron + docs
- files: `.github/workflows/daily-brief.yml`, `README.md` (setup section)
- depends_on: [T6]
- addresses: AC-5, AC-7
- exit check: workflow validates (cron `30 1 * * *` = 07:00 IST; `workflow_dispatch` for
  manual test); reads `GEMINI_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`,
  `BRIEF_TO` from `secrets`; README documents the App-Password + Gemini-key setup in <5 min.

## Risks & dependencies
- **Gemini free-tier drift** (T3): model 404 / 429 handled by fallback chain + graceful
  skip if key unset → run still emails an un-curated fallback? No — spec requires curation;
  if Gemini fully unavailable, degrade to headline-only digest with a notice (handle in T3/T4).
- **Gmail App Password** (T5/T8): requires user to enable 2FA and mint a password — a
  manual, out-of-band step. README must make this the first setup instruction.
- **ET feed schema/CDATA** (T2): mitigated by feedparser + per-feed try/except.
- **Red-team findings folded in:** (a) empty-day path is an explicit AC (AC-6) and exit
  check, not an afterthought; (b) partial-feed failure must not abort the run (T2 exit
  check); (c) Gemini returning malformed JSON handled by `gemini._parse` returning {} and
  curate falling back to uncurated-but-filtered items; (d) secrets never logged (T3 must
  not print the key on error).

## Parallelizable phases → /orchestrate candidate
After T1, tasks **T2, T3, T5** write disjoint files (`sources.py`+`models.py` /
`gemini.py`+`curate.py` / `mailer.py`), have no cross-dependency, and only converge at
T6. That is 3 independent write-sets → a genuine `/orchestrate` fan-out candidate.
(T4 depends on T3, so it is not part of the parallel set.)

## Where /architect is needed
None. Architecture is a direct port of a proven skill; no load-bearing design decision
remains open. Skip `/architect`.
