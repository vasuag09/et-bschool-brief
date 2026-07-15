# Harness State

slug: et-bschool-brief
phase: ship
status: ready-to-commit
next_skill: (awaiting user go for git init + push)

## verify results
- Live end-to-end run succeeded: 89 unique items → Gemini curated 18/18 batches →
  12 items emailed to vasuagrawal1040@gmail.com, exit 0. User confirmed email arrived.
- Post-verify change (user request): detailed summaries, not a terse brief.
  curate.py prompt now asks for 5-8 sentence self-contained summaries + expanded
  "why it matters"; source text fed 200→500 chars; gemini maxOutputTokens 4096→8192.
  AC-3 revised (ID stable). 33 tests still pass. Not re-verified live (user's call).
- Model upgrade (user request, billed account, best quality): queried the API for
  available models; chain now gemini-3.1-pro-preview → gemini-pro-latest →
  gemini-flash-latest (gemini-3-pro-preview / 2.5-pro 404 on v1beta, excluded).
  rate_limit 7→2s, workflow timeout 10→20min, maxOutputTokens 8192. Live 1-batch
  curate check confirmed detailed 150-word summaries + management-tied "why it matters".

## security-review results — PASS (no Critical/High)
- Core guarantees verified clean: HTML escaping of untrusted content, secret handling
  (no key/password logged, .env gitignored, no hardcoded secrets), SMTP SSL, HTTPS,
  yaml.safe_load, no eval/exec/pickle.
- Fixed: workflow `permissions: contents: read` (Medium); Gemini key moved to
  x-goog-api-key header not query param (Low); configured feeds constrained to https
  (Low, anti-SSRF/LFI). Added XSS regression test locking the escaping invariant.
- Accepted residual risks (noted, not fixed): phishing-link via feed content (Medium —
  reputable feeds, not XSS, domain allowlist would be scope creep); actions pinned to
  @v4/@v5 not SHAs (Low — standard for this project); global socket timeout (Low —
  benign, also gives SMTP a timeout).
- 33 tests, 95.9% coverage.

## review results
- code-reviewer found 1 High + 4 Medium + several Low. All High/Medium fixed, plus
  the cheap Lows. 32 tests pass, 96.6% coverage.
- High: curate.py conflated "AI call failed" vs "AI selected nothing" → could dump raw
  unfiltered items (AC-2 violation). Fixed: distinguish {} (failed) from {"items":[]}
  (valid empty); only degrade on real failure. Two regression tests added.
- Medium fixed: feed socket timeout (20s); gemini 200-bad-body now retries next model;
  dead config keys removed (ai.enabled, digest.max_themes); href scheme validation.
- Low fixed: key-extraction moved inside try; per-batch curate logging; removed dead
  Article.with_url; empty-recipient guard; bozo-flag logging.
- Deferred (Low, non-blocking): print() vs logging — justified for a CI cron script.

## implement results
- All 8 tasks (T1–T8) complete, test-first. 25 tests pass, 95.2% coverage.
- Live smoke: collect() pulls 30 unique real articles (20 ET) from 6 feeds.
- Both plan-check carry-forwards honored: README appended (not rewritten);
  `Digest.degraded` flag added and threaded curate→digest→email.
- Package: etbrief/{sources,gemini,curate,digest,mailer,main,models}.py
- Not a git repo → no branch created.

## plan-check carry-forward (Low, honor at implement)
- README.md: T8 appends a setup section, does not rewrite T1's skeleton.
- Add explicit `degraded` flag to the item/digest model so curate→digest can signal
  "Gemini unavailable, headline-only" cleanly.

## Notes
- Direction chosen via /discover: free RSS-first ET digest → Gemini Flash curation →
  Gmail delivery → GitHub Actions daily cron. Zero cost.
- Strong reuse anchor for /research: the `data-scraper-agent` skill (~80% match).
