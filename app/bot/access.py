"""Whitelist check — only configured Telegram user ids may use the bot."""

from __future__ import annotations

import re

from telegram import Update

from app.infra import config

# connected to each handler to ensure only whitelisted users can use the bot
def is_allowed(update: Update) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if user is None:
        return False
    if user.id not in config.ALLOWED_TELEGRAM_USER_IDS:
        return False
    if chat is None:
        return False
    if chat.type == "private":
        return True
    return chat.id in config.ALLOWED_TELEGRAM_GROUP_IDS

# connected to goupchat
def should_reply_to_group_message(update: Update, bot_username: str, bot_user_id: int) -> bool:
    """In groups, respond only when directly addressed (mention or reply)."""
    message = update.message
    if not message or not message.text:
        return False
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id == bot_user_id:
            return True

    # Mention-based triggering (e.g. @helix_bot ...)
    entities = message.entities or []
    for entity in entities:
        if entity.type == "mention":
            token = message.text[entity.offset : entity.offset + entity.length].lstrip("@")
            if bot_username and token.lower() == bot_username.lower():
                return True
        if entity.type == "text_mention" and entity.user and entity.user.id == bot_user_id:
            return True

    # fallback for clients that do not set mention entities reliably.
    # use a boundary-aware regex so punctuation or spacing still matches.
    if bot_username and re.search(rf"(?<!\w)@{re.escape(bot_username)}(?!\w)", message.text, re.IGNORECASE):
        return True
    return False
