# 🤖 Helix — Private Berlin AI Agent for Two

Production‑ready Telegram AI agent for Mr X and Miss X. Tuned for Berlin life: urban sports, comedy nights, cultural events, and neighbourhood discoveries. It remembers conversations, searches the web, and runs with strict security and cost controls.



## ✨ Features

**Two‑user private access**
Whitelisted to exactly two Telegram user IDs; everyone else ignored.

**Claude‑powered**
Anthropic Claude (Haiku for efficiency, Sonnet for prod polish).

**Pinecone semantic memory**
Per‑user summaries and embeddings for long‑term recall across sessions.

**Tavily web search**
Claude decides when to search; queries are sanitized for anonymity.

**local persona**
Recommendations for local neighbourhood events, comedy clubs, urban sports, culture.

**Privacy‑first security**
No message logs, no hardcoded secrets, anonymous searches, prompt injection defense.

**Cost controls**
Token caps, conversation windowing, daily limits, Anthropic spend cap.




## 🛠 Tech Stack

- Telegram Bot API:[Messaging] --->	   ✅ Production
- Anthropic Claude: [AI Brain]	--->      ✅ Haiku/Sonnet
- Pinecone	Vector: [Memory]	--->      ✅ Per-user namespaces
- Tavily: [Web Search]	--->   ✅ Sanitized queries
- Railway: [Hosting]	 --->  ✅ One-click deploy


## Quick Start

**Local Development**

```bash
git clone https://github.com/fern-1210/telegram-agent-helix-bot.git
cd telegram-agent-helix-bot
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
python src/main.py
```

**Production Deploy (Railway)**

1. Fork or use this repo directly
2. Click "Deploy on Railway" above or:

```bash
railway login
railway new
```
3. Railway will detect Python + requirements.txt
4. Add environment variables in Railway dashboard:

```bash
TELEGRAM_BOT_TOKEN=your_token
ALLOWED_TELEGRAM_USER_IDS=123456789,987654321
ANTHROPIC_API_KEY=your_key
PINECONE_API_KEY=your_key
TAVILY_API_KEY=your_key
```
5. Deploy complete 🚀 Railway handles scaling, restarts, and secrets.
[→ Full Railway Deployment Guide](docs/deployment/railway.md)


## 💰 Cost Breakdown
| Service           | Free Tier        | Production Cost    |
| ----------------- | --------------- | ------------------ |
| Telegram          | Free             | Free               |
| Anthropic (Haiku) | Pay‑per‑token    | ~$0.01/conv        |
| Pinecone          | 2GB free         | Free (starter)     |
| Tavily            | 1k searches/mo   | Free               |
| Railway           | $5/mo credit     | ~$5/mo hobby       |

Pro tip: Set Anthropic spend limit in console before deploying.


🧪 Operator Commands
Send these to the bot (whitelisted users only):
```bash
/status     # Bot uptime, memory usage, token spend
/usage      # Daily message count, search usage
/reset      # Clear conversation window (debug)
/memory     # Show recent memories (debug)
```


## Security & Privacy Model

Helix is built with a privacy‑first mindset:

- **Whitelist‑only access**: The bot only responds to the two configured Telegram user IDs; all others are silently ignored.

- **No message content in logs**: Logs contain only metadata (timestamp, user ID, token counts, response time, model)—never raw message content.

- **Secrets never in code**: All API keys and access tokens are loaded from environment variables; no hardcoded secrets.

- **Pinecone stores summaries only**: Rather than storing full raw transcripts, Helix only saves short semantic summaries and embeddings per user.

- **Anonymous Tavily queries**: Before calling the Tavily search API, queries are sanitized to remove personal identifiers and only focus on general or location‑level intent (e.g., “comedy clubs in Prenzlauer Berg this weekend”).

- **Prompt‑injection aware**: The system prompt is explicitly written to instruct Claude to keep its identity and rules intact, refuse to reveal system prompts, and ignore attempts to override system instructions.


