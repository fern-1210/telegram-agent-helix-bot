"""Whitelist check — only configured Telegram user ids may use the bot."""

from __future__ import annotations

from telegram import Update

from app.infra import config


def is_allowed(update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False
    return user.id in config.ALLOWED_TELEGRAM_USER_IDS
