"""Primary message handler, errors, and Claude reply loop."""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from app.ai import claude
from app.ai import memory
from app.bot import access
from app.infra import config
from app.infra.logging import get_logger

log = get_logger("helix")


async def claude_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    if not access.is_allowed(update):
        return
    if config.anthropic_client is None:
        await update.message.reply_text("Claude is not configured (missing ANTHROPIC_API_KEY).")
        return

    user = update.effective_user
    sender_id = user.id if user else 0
    user_text = update.message.text

    memory_block = await memory.build_memory_context_block(sender_id, user_text)
    system_prompt = memory.build_system_prompt(sender_id)

    history: list[dict[str, str]] = list(context.chat_data.get("claude_messages") or [])
    core_messages = claude.trim_messages(history + [{"role": "user", "content": user_text}])
    api_messages: list[dict[str, str]] = []
    if memory_block.strip():
        api_messages.append(
            {"role": "user", "content": config.MEMORY_CONTEXT_USER_PREFIX + memory_block.strip()},
        )
    api_messages.extend(core_messages)

    typing_task = asyncio.create_task(claude.keep_typing(update.message.chat))
    try:
        response = await config.anthropic_client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=config.MAX_TOKENS,
            system=system_prompt,
            messages=api_messages,
        )
    except Exception:
        log.exception("Claude API error")
        await update.message.reply_text("Something went wrong talking to Claude. Try again shortly.")
        return
    finally:
        typing_task.cancel()

    config.CLAUDE_CALL_COUNT += 1
    usage = getattr(response, "usage", None)
    if usage is not None:
        inp = getattr(usage, "input_tokens", 0) or 0
        out = getattr(usage, "output_tokens", 0) or 0
        config.TOTAL_INPUT_TOKENS += inp
        config.TOTAL_OUTPUT_TOKENS += out
        print(
            f"[claude] call={config.CLAUDE_CALL_COUNT} in={inp} out={out} "
            f"session_est=${(config.TOTAL_INPUT_TOKENS * config.HAIKU_INPUT_COST_PER_TOKEN + config.TOTAL_OUTPUT_TOKENS * config.HAIKU_OUTPUT_COST_PER_TOKEN):.5f}"
        )

    assistant_text = claude.assistant_text_from_response(response)
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": assistant_text})
    context.chat_data["claude_messages"] = claude.trim_messages(history)

    await update.message.reply_text(assistant_text)

    await memory.maybe_write_memory(sender_id, user_text, assistant_text)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Handler error", exc_info=context.error)
