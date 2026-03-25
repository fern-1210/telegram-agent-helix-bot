"""
Stage 1 — Telegram echo bot with user whitelist.
Run from project root:  python stage1_bot.py
"""
from __future__ import annotations

import os
import logging

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

#Importing time module to track the start time and message count
import time

START_TIME = time.time()
MESSAGE_COUNT = 0




# -----------------------------------------------------------------------------
# Config: token + whitelist from environment (never hardcode secrets)
# -----------------------------------------------------------------------------
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
_raw_ids = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "").strip()
# Comma-separated Telegram user ids, e.g. "123456789" or "111,222"
ALLOWED_TELEGRAM_USER_IDS: set[int] = set()
if _raw_ids:
    ALLOWED_TELEGRAM_USER_IDS = {int(part.strip()) for part in _raw_ids.split(",") if part.strip()}

# -----------------------------------------------------------------------------
# Security measures:no logging of message body
# -----------------------------------------------------------------------------
# Metadata-only logging (do not log message body — PLAN.md Rule 3)
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("helix.stage1")


def _is_allowed(update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False
    return user.id in ALLOWED_TELEGRAM_USER_IDS


# calculating uptime 
def _format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    mins, sec = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs}h {mins}m {sec}s"







async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        # Silent ignore for non-whitelisted users (PLAN.md Rule 1)
        return
    await update.message.reply_text(
        "Helix Stage 1: send any text and I will echo it back. "
        "(Claude / memory / search are not wired yet.)"
    )

#added help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return

    await update.message.reply_text(
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/status - Check if the bot is running"
    )

# adding status command - version 1: basic is running + Version 2: below with uptime, message count, and user id
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return

    uptime = _format_uptime(time.time() - START_TIME)
    user = update.effective_user                        #this can be a problem for security as it shows the user id to all users


    await update.message.reply_text(
        f"📊 Bot Status\n\n"
        f"🟢 Status: Running\n"
        f"⏱️ Uptime: {uptime}\n"
        f"💬 Messages handled: {MESSAGE_COUNT}\n"
        f"👤 Your user ID: {user.id if user else 'unknown'}"
    )




async def echo_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global MESSAGE_COUNT

    if not update.message or not update.message.text:
        return
    if not _is_allowed(update):
        return

    MESSAGE_COUNT += 1  #  track usage

    await update.message.reply_text(update.message.text)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors without leaking chat content."""
    log.exception("Handler error", exc_info=context.error)


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN in environment (.env)")
    if not ALLOWED_TELEGRAM_USER_IDS:
        raise SystemExit(
            "Missing ALLOWED_TELEGRAM_USER_IDS in .env "
            "(comma-separated numeric ids, e.g. ALLOWED_TELEGRAM_USER_IDS=123456789)"
        )
    # Create the bot application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()   #main function, entry point

    log.info("Stage 1 bot starting (polling)")

    application.add_handler(CommandHandler("start", start_command)) #the command handler when start is message d
    application.add_handler(CommandHandler("help", help_command)) #added help command
    application.add_handler(CommandHandler("status", status_command)) #added status command
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_text)) #the message handler when any text is message

    application.add_error_handler(on_error)

    # Start the bot
    print('🚀 Starting bot...')
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

