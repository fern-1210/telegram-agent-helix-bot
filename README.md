# 🤖 Helix — Private Telegram AI Agent

Production‑ready Telegram AI agent for 2 whitelisted users. Tuned for Berlin life: urban sports, comedy nights, cultural events, and neighbourhood discoveries. It remembers conversations, searches the web, and runs with strict security and cost controls.

---

## Prerequisites

Before you start, you need accounts and API keys from:

- **Telegram** — create a bot via [@BotFather](https://t.me/botfather), get your `TELEGRAM_BOT_TOKEN`
- **Anthropic** — [console.anthropic.com](https://console.anthropic.com) — get your `ANTHROPIC_API_KEY`. Set a spend limit before deploying.
- **OpenAI** — [platform.openai.com](https://platform.openai.com) — get your `OPENAI_API_KEY` for embeddings. Set a spend limit.
- **Pinecone** — [app.pinecone.io](https://app.pinecone.io) — create a free index with **dimension 1536** and **cosine metric**. Note the index name.
- **Tavily** — [app.tavily.com](https://app.tavily.com) — get your `TAVILY_API_KEY` (free tier covers light use)
- **Python 3.11+** installed locally

---

## Quick Start — Local Development
```bash
git clone https://github.com/fern-1210/telegram-agent-helix-bot.git
cd telegram-agent-helix-bot
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
python -m app.main
```

To confirm everything is working, send these to your bot in order:

1. `/status` — should show uptime, model, and memory: on
2. `/memory_list` — should return "No stored memories" (not an error)
3. A plain message — Claude should reply
4. `/memory_debug` after 60 seconds — should show at least one stored memory


---

## Production Deploy — Railway

Railway connects directly to your GitHub repo and runs the bot in the cloud. No server management required.

See [`docs/deployment/railway.md`](docs/deployment/railway.md) for a detailed Railway deployment guide, including pre-flight API key checklist, Railway-specific setup instructions, and required/optional environment variables along with troubleshooting guide and extra tips.



---

## Environment Variables

Copy `.env.example` to `.env` and fill in all values:
```env
TELEGRAM_BOT_TOKEN=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX_NAME=
TAVILY_API_KEY=
ALLOWED_TELEGRAM_USER_IDS=123456789,987654321
```

`ALLOWED_TELEGRAM_USER_IDS` is a comma-separated list of Telegram user IDs. Only these users can interact with the bot. Everyone else is silently ignored. You can find your Telegram user ID by messaging [@userinfobot](https://t.me/userinfobot).

---

## Cost Estimates

Set spend limits in the Anthropic and OpenAI consoles before deploying.

| Tier | Messages/day | Est. monthly cost | Typical use |
|---|---|---|---|
| Hobby | ~10/day | $2–7 | Testing, occasional use |
| Light daily | ~50/day | $10–20 | Two users, daily planning |
| Medium personal | ~150/day | $30–55 | Heavy use, notes, recommendations |

Cost breakdown per tier is dominated by Claude API calls. Embeddings (OpenAI) and Pinecone are near-zero at personal scale. Tavily free tier covers most light usage. Railway free tier covers hobby and light daily use — check [railway.com/pricing](https://railway.com/pricing) for current limits.

*Estimates based on March 2026 pricing. Check individual service dashboards for current rates.*

---

## Bot Commands

Send these to the bot (whitelisted users only):
```
/start          Intro message + reset conversation window
/clear          Wipe in-session chat history (Pinecone untouched)
/status         Uptime, model, token spend, memory status
/usage          Session token counts and estimated cost
/memory_list    Your stored memory IDs with kind and timestamp
/memory_debug   Same as above plus full summary text
/memory_reset   Permanently delete all your long-term memories
/help           Full command list
```

---

## Tech Stack

| Component | Service | Purpose |
|---|---|---|
| Messaging | Telegram Bot API | User interface |
| AI brain | Anthropic Claude | Responses and tool decisions |
| Embeddings | OpenAI text-embedding | Text to vector conversion |
| Memory | Pinecone | Per-user long-term vector storage |
| Web search | Tavily | Sanitized real-time search |
| Hosting | Railway | Cloud deployment and uptime |

---

## Security and Privacy

- **Whitelist-only access** — the bot only responds to configured Telegram user IDs. All others are silently ignored.
- **No message content in logs** — logs contain only metadata (timestamp, user ID, token counts). Never raw message text.
- **Secrets never in code** — all API keys loaded from environment variables only. Nothing hardcoded.
- **Pinecone stores summaries only** — short semantic summaries and embeddings per user, not full transcripts.
- **Sanitized web searches** — personal identifiers (names, addresses, phone numbers) are stripped from queries before they reach Tavily.
- **Prompt injection defence** — the system prompt explicitly instructs Claude to maintain its rules regardless of user message content.

---

## Features

- **Two-user private access** - Whitelisted to exactly two Telegram user IDs. Everyone else is ignored.

- **Claude-powered responses** - Anthropic Claude handles all conversations, tool decisions, and memory extraction.

- **Long-term semantic memory** - Per-user Pinecone namespaces store conversation summaries as vector embeddings. The bot remembers context across sessions and days.

- **Web search when needed** - Claude decides autonomously when to search the web. Queries are sanitised before leaving your server.

- **Local persona** - Tuned for Berlin: neighbourhood recommendations, comedy clubs, urban sports, cultural events.

- **Cost controls** - Token caps, conversation windowing, and session cost tracking built in. Spend limits enforced at the API provider level.

---

## About the Builder

Julian Fernandes — Berlin-based data analyst and CRM specialist.
[LinkedIn](https://www.linkedin.com/in/julian-fernandes-a1a19ba/)

I didn't finish a 12-week data bootcamp and file the certificate away — I built Helix as a sandbox for testing, breaking, and iterating on everything I've learned. This project is my way of turning curiosity into shipping: a private, Berlin-tuned Telegram agent that I can poke, refine, and reshape until it genuinely fits into my daily life.

My background in CRM and customer data means I care less about shiny tech and more about actionable change: does this actually help me decide faster, plan better, and discover more? Helix is that philosophy in code — a living experiment where I use AI as a thinking partner, treat each iteration as a lesson, and keep pushing toward something small, focused, and genuinely useful.

---

## License

MIT — use it, adapt it, build on it.

If you use this as a base for your own bot, a mention or a star on the repo would be appreciated.

