"""
Helix — Telegram + Claude + Pinecone long-term memory.

Run from project root:  python -m app.main.py

"""

from __future__ import annotations
from app.infra.logging import setup_logging

setup_logging()

# Config loads dotenv, clients, and memory flags — must follow logging setup.
from app.infra import config  # noqa: E402
from app.infra.logging import get_logger  # noqa: E402

log = get_logger("helix")

from telegram import Update  # noqa: E402
from telegram.ext import Application, CommandHandler, MessageHandler, filters  # noqa: E402

from app.bot import commands  # noqa: E402
from app.bot import handlers  # noqa: E402


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN in environment (.env)")
    if not config.ALLOWED_TELEGRAM_USER_IDS:
        raise SystemExit("Missing ALLOWED_TELEGRAM_USER_IDS in .env")
    if not config.ANTHROPIC_API_KEY:
        raise SystemExit("Missing ANTHROPIC_API_KEY in environment (.env)")

    # Warn if whitelisted IDs lack profile bindings (still runs with generic fallback)
    unbound = config.ALLOWED_TELEGRAM_USER_IDS - set(config.USER_PROFILES.keys())
    if unbound:
        log.warning(
            "Whitelisted user id(s) have no profile env mapping: %s",
            sorted(unbound),
        )
     # 🎮 Build the Telegram application — control center for all updates
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    log.info("Helix bot starting model=%s memory=%s", config.CLAUDE_MODEL, config.MEMORY_ENABLED)       ##IMPORTANT LOG check at startup if startup dependency is True/false

    application.add_handler(CommandHandler("start", commands.start_command))    # 👋 /start + clear history
    application.add_handler(CommandHandler("help", commands.help_command)) # ❓ command list
    application.add_handler(CommandHandler("clear", commands.clear_command))  # 🧹 wipe history silently
    application.add_handler(CommandHandler("status", commands.status_command)) # 📊 uptime / model / profile
    application.add_handler(CommandHandler("usage", commands.usage_command))
    application.add_handler(CommandHandler("memory_reset", commands.memory_reset_command))  # 🧹 delete YOUR long-term vectors in Pinecone
    application.add_handler(CommandHandler("memory_list", commands.memory_list_command))  # 📊 ids + kind + created_at (metadata)
    application.add_handler(CommandHandler("memory_debug", commands.memory_debug_command))  # 🔍 same + summary text (private)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.claude_reply),
    )
    application.add_error_handler(handlers.on_error) # 🚨 last-resort errors (no message body in logs)

    print("Starting Helix bot (Claude + Pinecone memory + Telegram)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES) #chose between pollng and webhooks - polling is more reliable and easier to setup


if __name__ == "__main__":
    main()
