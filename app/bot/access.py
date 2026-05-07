"""Whitelist check — only configured Telegram user ids may use the bot."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from telegram import Update

from app.infra import config

_DEBUG_LOG_PATH = Path("/Users/Julian/Desktop/GitHub-Repo/telegram-agent-helix-bot/.cursor/debug-d02e3e.log")
_DEBUG_SESSION_ID = "d02e3e"


def _agent_debug_log(hypothesis_id: str, location: str, message: str, data: dict[str, object]) -> None:
    payload = {
        "sessionId": _DEBUG_SESSION_ID,
        "runId": os.getenv("DEBUG_RUN_ID", "initial"),
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(__import__("time").time() * 1000),
    }
    try:
        _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except Exception:
        pass

# connected to each handler to ensure only whitelisted users can use the bot
def is_allowed(update: Update) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if user is None:
        # region agent log
        _agent_debug_log(
            "H3",
            "app/bot/access.py:is_allowed:user_none",
            "Access denied because effective_user is missing",
            {"chat_type": chat.type if chat else None},
        )
        # endregion
        return False
    if user.id not in config.ALLOWED_TELEGRAM_USER_IDS:
        # region agent log
        _agent_debug_log(
            "H1",
            "app/bot/access.py:is_allowed:not_whitelisted",
            "Access denied because user id is not in whitelist",
            {
                "user_id": user.id,
                "allowed_user_ids": sorted(config.ALLOWED_TELEGRAM_USER_IDS),
                "chat_type": chat.type if chat else None,
                "chat_id": chat.id if chat else None,
            },
        )
        # endregion
        return False
    if chat is None:
        # region agent log
        _agent_debug_log(
            "H3",
            "app/bot/access.py:is_allowed:chat_none",
            "Access denied because effective_chat is missing",
            {"user_id": user.id},
        )
        # endregion
        return False
    if chat.type == "private":
        # region agent log
        _agent_debug_log(
            "H2",
            "app/bot/access.py:is_allowed:allowed_private",
            "Access granted in private chat",
            {"user_id": user.id, "chat_id": chat.id},
        )
        # endregion
        return True
    is_group_allowed = chat.id in config.ALLOWED_TELEGRAM_GROUP_IDS
    # region agent log
    _agent_debug_log(
        "H2",
        "app/bot/access.py:is_allowed:group_check",
        "Group access evaluated",
        {
            "user_id": user.id,
            "chat_id": chat.id,
            "is_group_allowed": is_group_allowed,
            "allowed_group_ids": sorted(config.ALLOWED_TELEGRAM_GROUP_IDS),
        },
    )
    # endregion
    return is_group_allowed

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
