🤖 Helix — Private Telegram AI Agent for Two
Helix is a private, two‑user AI agent that lives in Telegram and is tuned to real life in Berlin — urban sports, comedy nights, cultural events, and neighbourhood discoveries.

It knows whether it’s talking to Julian or Miss X, remembers past conversations, can search the web, and runs with strict security and cost controls built in.

(line break)

✨ Features
Two‑user private assistant
Whitelisted to exactly two Telegram IDs; everyone else is silently ignored.

Claude‑powered brain
Uses Anthropic Claude (Haiku for dev, optional Sonnet for “prod” feel) with a carefully designed system prompt and identity.

Long‑term memory with Pinecone
Stores summaries, not raw chat logs, in a per‑user Pinecone index for semantic recall across sessions.

Tavily web search tools
Claude can call Tavily when it needs fresh information (e.g. “What’s on in Prenzlauer Berg this weekend?”), with anonymous, sanitized queries.

Berlin‑tuned persona
Optimised for Berlin social life: events, sports, comedy, culture, and neighbourhood exploration.

Strong security posture
No message content in logs, no API keys in code, anonymous search queries, and a memory model designed to minimize data exposure.

Cost‑aware by design
Token caps, conversation windowing, daily per‑user limits, and Anthropic account spend limits to avoid surprises.

(line break)

🧱 Architecture Overview

Julian / Miss X
      ↓ (Telegram message)
Telegram Bot API
      ↓
Python App (local or server)

1. User ID check (whitelist only)
2. Fetch user-specific memories from Pinecone
3. Build context:
   - System prompt (Helix identity + safety rules)
   - User profile (Julian or Miss X)
   - Retrieved memory hints
   - Recent conversation window
4. Call Anthropic Claude
   - Optional Tavily web search via tool use
5. Send reply back via Telegram

Key idea: Memory is injected as context before calling Claude, and web search is invoked as a tool only when the model decides it needs it.

(line break)

🛠 Tech Stack
Language: Python 3.11+

Messaging: Telegram Bot API (python‑telegram‑bot or equivalent)

LLM: Anthropic Claude (Haiku by default) via Anthropic API

Vector DB: Pinecone for long‑term semantic memory

Search: Tavily API for current information
​

Config: .env + environment variables

Deployment: Local Mac during early stages; later, a small cloud instance (Railway / Fly.io / DigitalOcean).


(line break)


🚀 Getting Started
1. Prerequisites
Python 3.11 or later installed

A Telegram bot token from @BotFather

Anthropic API key (Claude)

Pinecone account and index (e.g. helix-memory)

Tavily API key
​

2. Clone the Repository
bash
git clone https://github.com/<your-username>/telegram-agent-helix-bot.git
cd telegram-agent-helix-bot
3. Create and Activate Virtual Environment
bash
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
4. Install Dependencies
bash
pip install -r requirements.txt
5. Configure Environment
Create a .env file in the project root:

bash
cp .env.example .env
Fill in:

text
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ALLOWED_TELEGRAM_USER_IDS=123456789,987654321  # Julian, Miss X

ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-5-haiku-20241022

PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_env
PINECONE_INDEX_NAME=helix-memory

TAVILY_API_KEY=your_tavily_api_key
Security: API keys stay in .env only and .env is in .gitignore.

6. Run the Bot
bash
python src/main.py
Then open Telegram, find your bot, and send a message from a whitelisted account.

(line break)

🔒 Security & Privacy Model
Helix is built with a privacy‑first mindset:

Whitelist‑only access
The bot only responds to the two configured Telegram user IDs; all others are silently ignored.

No message content in logs
Logs contain only metadata (timestamp, user ID, token counts, response time, model).
​

Secrets never in code
All tokens/keys are loaded from environment variables; no hardcoded secrets.

Pinecone stores summaries only
Helix stores short semantic summaries and embeddings, not raw transcripts, per user namespace.

Anonymous Tavily queries
Queries are sanitized to avoid personal identifiers; they focus on general or location‑level intent (e.g. “comedy clubs in Prenzlauer Berg this weekend”).
​

Prompt‑injection aware
The system prompt explicitly instructs Claude to keep its identity and rules, refuse to reveal the prompt, and ignore attempts to override system instructions.

💸 Cost Controls
Built‑in limits to protect your Anthropic credit:

max_tokens cap on every Claude call (e.g. 500 tokens per reply).

Conversation windowing (e.g. last 12 messages only) to avoid runaway context growth.
​

Daily per‑user message cap (e.g. 50 messages/day before Helix asks you to come back tomorrow).
​

Anthropic account spend cap set in the console (e.g. hard limit at your current credit).
​

You can tune these in the config to match your budget and usage.