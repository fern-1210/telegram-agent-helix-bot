# Railway Deployment Guide (First-Time Friendly)

This guide deploys Helix to [Railway](https://railway.com/) with the least friction.

It assumes:
- your code is in GitHub,
- your API keys are ready,
- you want a simple, safe first production launch.

## 0) Pre-Flight Checklist

Before deploying, confirm:
- `.env` is not committed.
- `.env.example` has placeholders only.
- required keys are available:
  - `TELEGRAM_BOT_TOKEN`
  - `ALLOWED_TELEGRAM_USER_IDS`
  - `ANTHROPIC_API_KEY`
  - `OPENAI_API_KEY`
  - `PINECONE_API_KEY`
  - `PINECONE_INDEX_NAME`
  - `TAVILY_API_KEY`
- optional but recommended:
  - `JULIAN_TELEGRAM_USER_ID`
  - `MISS_X_TELEGRAM_USER_ID`
  - `ALLOWED_TELEGRAM_GROUP_IDS`
  - `CLAUDE_MODEL`

## 1) Create Railway Project

1. Go to [Railway](https://railway.com/).
2. Click **Start a New Project**.
3. Choose **Deploy from GitHub Repo**.
4. Select your `telegram-agent-helix-bot` repository.
5. Railway creates a service and starts the first build.

## 2) Configure Start Command

Helix runs as a worker process (long-running bot), not a web server.

Set the start command to:

```bash
python -m app.main
```

If Railway asks for a build command, use:

```bash
pip install -r requirements.txt
```

## 3) Add Environment Variables in Railway

In your Railway service:
1. Open **Variables**.
2. Add each environment variable one by one.
3. Save/apply changes.

Use these exact names (matching code):

```text
TELEGRAM_BOT_TOKEN=
ALLOWED_TELEGRAM_USER_IDS=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX_NAME=helix-memory
TAVILY_API_KEY=
```

Optional:

```text
JULIAN_TELEGRAM_USER_ID=
MISS_X_TELEGRAM_USER_ID=
ALLOWED_TELEGRAM_GROUP_IDS=
CLAUDE_MODEL=claude-3-5-haiku-20241022
```

Important:
- never paste these values into GitHub files,
- rotate keys immediately if accidentally exposed.

## 4) Deploy

After variables are set:
1. Trigger a new deploy (or redeploy latest commit).
2. Wait for build logs to finish.
3. Confirm service enters running state.

Expected startup behavior:
- app starts polling Telegram,
- `/status` responds from allowlisted account,
- logs show startup line with model + memory state.

## 5) Verify End-to-End

From an allowlisted Telegram account:
1. Send `/status` -> verify bot is up.
2. Send normal message -> verify Claude response.
3. Ask a timely/local query -> verify search-capable response.
4. Send `/usage` -> verify counters and cost estimate output.

From a non-allowlisted account:
- bot should silently ignore.

## 6) Safe Operations

For day-to-day operations:
- deploy by pushing to GitHub branch connected to Railway,
- review Railway logs after each deploy,
- use `/status` and `/usage` for quick health checks.

If you change env vars:
- redeploy to ensure runtime picks up new values.

## 7) Common Issues and Fixes

### Bot deploys but does not respond
- Check `TELEGRAM_BOT_TOKEN`.
- Check `ALLOWED_TELEGRAM_USER_IDS` format (comma-separated numbers only).
- Confirm you are messaging from an allowlisted account.

### Memory is off
- Confirm `OPENAI_API_KEY` and `PINECONE_API_KEY` are both set.
- Confirm `PINECONE_INDEX_NAME` exists and is accessible.

### Search does not work
- Confirm `TAVILY_API_KEY` is set.
- Check for Tavily errors in logs.

### Build fails
- Ensure Python dependencies install from `requirements.txt`.
- Redeploy after fixing dependency errors.

## 8) Security Checklist Before Public Release

- No secrets in git history.
- No `.env` in repository.
- README does not leak private operational details.
- Logs avoid raw message content.
- API keys rotated if any prior exposure is suspected.

## 9) Optional Next Improvements

- Add Railway environment separation (staging vs production).
- Add alerts/monitoring integration for failures.
- Add a health-check command runbook for faster incident response.

