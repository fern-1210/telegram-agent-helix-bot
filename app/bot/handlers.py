"""Primary message handler, errors, and Claude reply loop."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from app.ai import claude
from app.ai import memory
from app.ai.tavily_search import tavily_search
from app.bot import access
from app.infra import config
from app.infra.logging import get_logger
from app.social.discovery import run_social_discovery
from app.social.intent import detect_intent, should_route_natural_language_discovery

log = get_logger("helix")

_TAVILY_TOOL_DEF: dict[str, Any] = {
    "name": "tavily_search",
    "description": (
        "Search current web information when the user asks for up-to-date events, "
        "news, listings, or time-sensitive recommendations."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
        },
        "required": ["query"],
    },
}



# ----
# # claude_reply is the main handler for the bot. it is called when a message is received.
# -------


async def claude_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    user_text = (update.message.text or update.message.caption or "").strip()
    if not user_text:
        return
    if not access.is_allowed(update):
        return
    # check if the message is in a group chat and if the bot is mentioned
    chat = update.effective_chat
    if chat is not None and chat.type != "private":
        bot_user = await context.bot.get_me()
        bot_username = bot_user.username or ""
        should_reply = access.should_reply_to_group_message(update, bot_username, bot_user.id)
        if not should_reply:
            entities = [(e.type, e.offset, e.length) for e in (update.message.entities or [])]
            log.info(
                "Group message ignored chat_id=%s user_id=%s text_len=%s entities=%s bot_username=%s bot_id=%s",
                chat.id,
                update.effective_user.id if update.effective_user else 0,
                len(user_text),
                entities,
                bot_username,
                bot_user.id,
            )
            return
    user = update.effective_user
    sender_id = user.id if user else 0

    # Stage 6: conservative natural-language routing to local discovery (no Claude)
    if config.SOCIAL_DISCOVERY_ENABLED and should_route_natural_language_discovery(
        user_text,
        config.SOCIAL_NL_MAX_CHARS,
    ):
        nl_intent, remainder = detect_intent(user_text)
        if nl_intent is not None:
            log.info("social_nl_route intent=%s text_len=%s", nl_intent.value, len(user_text))
            typing_task = asyncio.create_task(claude.keep_typing(update.message.chat))
            try:
                reply_text = await run_social_discovery(nl_intent, remainder)
            except Exception:
                log.exception("Social discovery error")
                await update.message.reply_text("Discovery failed. Try again or use a slash command.")
                return
            finally:
                typing_task.cancel()

            history_nl: list[dict[str, str]] = list(context.chat_data.get("claude_messages") or [])
            history_nl.append({"role": "user", "content": user_text})
            history_nl.append({"role": "assistant", "content": reply_text})
            context.chat_data["claude_messages"] = claude.trim_messages(history_nl)
            await update.message.reply_text(reply_text)
            await memory.maybe_write_memory(sender_id, user_text, reply_text)
            return

    if config.anthropic_client is None:
        await update.message.reply_text("Claude is not configured (missing ANTHROPIC_API_KEY).")
        return

    # ----
    # First, retrieve relevant memories and build the profile system prompt — both happen before touching Claude.
    # memories (pinecone) + system prompt (profile)
    # -------

    typing_task = asyncio.create_task(claude.keep_typing(update.message.chat))
    try:
        memory_block = await memory.build_memory_context_block(sender_id, user_text)
        system_prompt = memory.build_system_prompt(sender_id)

        # ----
        # Second, load the conversation history, append the new message, trim to the window limit.
        # -------

        history: list[dict[str, str]] = list(context.chat_data.get("claude_messages") or [])
        core_messages = claude.trim_messages(history + [{"role": "user", "content": user_text}])
        
        
        api_messages: list[dict[str, str]] = []
        if memory_block.strip():
            api_messages.append(
                {"role": "user", "content": config.MEMORY_CONTEXT_USER_PREFIX + memory_block.strip()},
            )
        api_messages.extend(core_messages)

        # ----
        # Third: Claude + optional Tavily (typing stopped in finally below).
        # -------

        response = await config.anthropic_client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=config.MAX_TOKENS,
            system=system_prompt,
            messages=api_messages,
            tools=[_TAVILY_TOOL_DEF],
        )

        # bounded one-pass tool loop: if Claude requests Tavily, execute once and ask Claude to finalize
        tool_uses = claude.tool_uses_from_response(response)
        if tool_uses:
            log.info("Claude selected tool=%s count=%s", tool_uses[0]["name"], len(tool_uses))
            followup_messages: list[dict[str, Any]] = list(api_messages)
            followup_messages.append({"role": "assistant", "content": response.content})
            for tool_use in tool_uses:
                tool_name = str(tool_use.get("name", ""))
                tool_id = str(tool_use.get("id", ""))
                tool_input = tool_use.get("input", {}) if isinstance(tool_use.get("input", {}), dict) else {}

                tool_result: dict[str, Any]
                if tool_name == "tavily_search":
                    query = str(tool_input.get("query", "")).strip()
                    tool_result = await tavily_search(query)
                else:
                    tool_result = {"ok": False, "error": "unsupported_tool", "results": []}

                followup_messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": json.dumps(tool_result),
                            },
                        ],
                    },
                )

            response = await config.anthropic_client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=config.MAX_TOKENS,
                system=system_prompt,
                messages=followup_messages,
                tools=[_TAVILY_TOOL_DEF],
            )
    except Exception:
        log.exception("Claude API error")
        await update.message.reply_text("Something went wrong talking to Claude. Try again shortly.")
        return
    finally:
        typing_task.cancel()

    # ----
    # Fourth, update the session usage counters and log usage.
    # -------

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

    await memory.maybe_write_memory(sender_id, user_text, assistant_text)       # bot asynchronously decides to write the memory




# is a catch-all registered with the application that logs any unhandled exception from any handler.
async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Handler error", exc_info=context.error)
