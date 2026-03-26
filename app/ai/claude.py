"""Helpers around Claude API responses and chat shaping."""

from __future__ import annotations

import asyncio
from typing import Any

from app.infra import config

# enforces a sliding window on conversation history
def trim_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(messages) <= config.MAX_HISTORY_MESSAGES:
        return messages
    return messages[-config.MAX_HISTORY_MESSAGES :]


def assistant_text_from_response(response: object) -> str:
    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip() or "(No text in response.)"

# extracts the tool uses from the claude response
def tool_uses_from_response(response: object) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for block in getattr(response, "content", []):
        if getattr(block, "type", None) != "tool_use":
            continue
        out.append(
            {
                "id": getattr(block, "id", ""),
                "name": getattr(block, "name", ""),
                "input": getattr(block, "input", {}) or {},
            },
        )
    return out

# background async task that sends a "typing..." indicator to Telegram every 4 seconds 
async def keep_typing(chat: object) -> None:
    try:
        while True:
            await chat.send_action("typing")
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass
