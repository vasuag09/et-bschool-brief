# 📈 ET B-School Brief

A free, automated daily digest of **Economic Times** (plus other free business papers),
curated by AI for an MBA-Tech student and emailed to your Gmail every morning.

- **Collect** — pulls Economic Times RSS feeds (primary) + Livemint/BusinessLine (supplementary)
- **Curate** — an LLM (Claude Haiku 4.5) drops sports/lifestyle noise, keeps
  strategy / economy / corporate / policy / markets / leadership, and writes a short
  "why it matters" for each item
- **Deliver** — a clean HTML brief lands in your inbox at ~7 AM IST
- **Runs 100% free** on GitHub Actions — no server, nothing on your laptop

## Quick start (local test)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in the three secrets (see Setup below)
python -m etbrief.main    # fetch → curate → email, once
```

## Configuration

Everything user-facing lives in `config.yaml` — sources, item caps, digest size,
recipient. No code changes needed to tune it.

## Setup (one time, ~5 minutes)

You need two things: a **Gmail App Password** (free) and an **Amazon Bedrock API key**.

### 1. Gmail App Password (for sending)
1. Turn on **2-Step Verification**: https://myaccount.google.com/security
2. Create an App Password: https://myaccount.google.com/apppasswords
   → pick "Mail", name it "ET Brief" → copy the **16-character** password.
   (This is *not* your normal Gmail password.)

### 2. Amazon Bedrock API key (for curation)
1. In the **AWS Bedrock console** (region **ap-south-1 / Mumbai**): enable **model access**
   for *Claude Haiku 4.5*, then create a **Bedrock API key** (a bearer token) and copy it.
   This project uses **Claude Haiku 4.5** on Bedrock (cost-first — cheap and more than
   capable for news summarisation). Region and model id are set in `etbrief/llm.py` and
   overridable via `BEDROCK_REGION` / `BEDROCK_MODEL_ID`; the default uses the ap-south-1
   runtime with Haiku 4.5's `global.` inference profile.

### 3. Run it daily for free (GitHub Actions)
1. Push this repo to GitHub.
2. In the repo: **Settings → Secrets and variables → Actions → New repository secret**,
   add these four:

   | Secret | Value |
   |--------|-------|
   | `AWS_BEARER_TOKEN_BEDROCK` | your Bedrock API key (bearer token) |
   | `GMAIL_USER` | the Gmail address that sends the brief |
   | `GMAIL_APP_PASSWORD` | the 16-char App Password from step 1 |
   | `BRIEF_TO` | where to deliver (can be the same address) |

3. Go to the **Actions** tab → **Daily ET B-School Brief** → **Run workflow** to test now.
   After that it runs automatically every day at **07:00 IST**.

> The workflow exits non-zero on a day with no items (so an empty day is visible in the
> Actions log) — that is expected behavior, not a failure of your setup.

## Tests

```bash
pip install -r requirements.txt
pytest                      # 33 tests
pytest --cov=etbrief        # coverage
```
