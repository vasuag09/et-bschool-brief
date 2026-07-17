# Harness State

slug: et-bschool-brief
phase: ship
status: MODEL-MIGRATION-PENDING-KEY
next_skill: (add AWS_BEARER_TOKEN_BEDROCK → live re-verify → commit/push)

## in progress: cost migration Gemini 3.1 Pro → Claude Haiku 4.5 on Bedrock (2026-07-17)
- Reason: pipeline works & content is fine; Gemini 3.1 Pro was burning money. User chose
  Claude Haiku 4.5 (cheap, plenty capable) via AMAZON BEDROCK (ap-south-1, access enabled).
- Code DONE + tested (34 pass, 96% cov, llm.py 96%). NOT yet live-verified, NOT committed.
- New module etbrief/llm.py: Bedrock InvokeModel REST via `requests` (no new dep). Bearer
  auth from AWS_BEARER_TOKEN_BEDROCK (no SigV4). URL model id = inference profile
  apac.anthropic.claude-haiku-4-5-20251001-v1:0 (env-overridable via BEDROCK_MODEL_ID /
  BEDROCK_REGION). Body: anthropic_version bedrock-2023-05-31, NO model field. JSON forced
  via assistant-prefill "{" (Claude has no JSON mode). curate.py provider-agnostic (injected
  generate_fn) — only its import changed.
- Deleted etbrief/gemini.py + tests/test_gemini.py; added tests/test_llm.py.
- Env: GEMINI_API_KEY removed; now AWS_BEARER_TOKEN_BEDROCK (secret) + BEDROCK_REGION /
  BEDROCK_MODEL_ID (plain env, defaults in code + set literally in workflow).
- config: rate_limit 2→1s; workflow timeout 20→10min.
- LIVE-VERIFIED (curation): key added to .env; full local run collected 89 items and
  Claude Haiku 4.5 curated ALL 18/18 batches OK. Bedrock path works end-to-end.
- MODEL-ID FIX: apac.anthropic.claude-haiku-4-5-... → 400 "model identifier is invalid"
  (apac profile is Claude 3 Haiku only). Correct id = GLOBAL profile
  global.anthropic.claude-haiku-4-5-20251001-v1:0 (found via Bedrock ListInferenceProfiles).
  Updated in llm.py default, .env, workflow, .env.example, README.
- EMAIL not locally verifiable: outbound SMTP port 465 is BLOCKED on this network
  (bare socket test to smtp.gmail.com:465 times out). mailer.py unchanged; GH Actions
  sends fine (prior runs). Verify email via a cloud workflow_dispatch run.
- REMAINING (needs user OK — git ops gated): 1) commit + push; 2) gh secret set
  AWS_BEARER_TOKEN_BEDROCK on vasuag09/et-bschool-brief; 3) after push, gh secret delete
  GEMINI_API_KEY (NOT before — old workflow still refs it until pushed); 4) trigger
  workflow_dispatch to confirm cloud curation+email.
- 34 tests pass, 96% cov.

## deployment
- Repo: https://github.com/vasuag09/et-bschool-brief (private, account vasuag09)
- 4 secrets set (GEMINI_API_KEY, GMAIL_USER, GMAIL_APP_PASSWORD, BRIEF_TO).
- Test workflow run 29414926203 succeeded in 1m14s — brief sent via cloud.
- Daily cron live: 07:00 IST (30 1 * * * UTC).
- Minor: Node20 deprecation warning on checkout@v4/setup-python@v5 (auto-forced to
  node24, non-blocking) — bump action majors someday.

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
