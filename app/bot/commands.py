"""Slash commands for Helix."""

from __future__ import annotations

import asyncio
import time

from telegram import Update
from telegram.ext import ContextTypes

from app.ai import claude
from app.ai import embeddings
from app.ai import memory
from app.bot import access
from app.infra import config
from app.infra.logging import get_logger
from app.social.discovery import run_social_discovery
from app.social.intent import SocialIntent

log = get_logger("helix")

# required for the /status for time formatting
def _format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    mins, sec = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs}h {mins}m {sec}s"

# /start command: clears history and provides a welcome message
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not access.is_allowed(update):
        return
    context.chat_data.pop("claude_messages", None)
    await update.message.reply_text(
        "Helix: Claude + per-user profiles + Pinecone long-term memory.\n"
        "Discovery: /comedy /music /today /events /food\n"
        "Commands: /help, /memory_list, /memory_debug, /memory_reset, /status, …"
    )

# /help command: provides a list of commands
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not access.is_allowed(update):
        return
    await update.message.reply_text(
        "Commands:\n"
        "/start — intro + keep history\n"
        "/clear — wipe in-chat history only\n"
        "/memory_reset — delete YOUR long-term vectors in Pinecone\n"
        "/memory_list — ids + kind + created_at (metadata)\n"
        "/memory_debug — same + summary text (private)\n"
        "/comedy /music /today /events /food — Berlin discovery (Tavily, trusted list)\n"
        "/help /status /usage\n"
        "Short event-style questions may also trigger discovery.\n"
        "Any other text — Claude"
    )


async def _run_social_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    intent: SocialIntent,
) -> None:
    if not access.is_allowed(update):
        return
    if not update.message:
        return
    extra = " ".join(context.args or [])
    user = update.effective_user
    sender_id = user.id if user else 0
    cmd_line = (update.message.text or "").strip()

    typing_task = asyncio.create_task(claude.keep_typing(update.message.chat))
    try:
        reply_text = await run_social_discovery(intent, extra)
    finally:
        typing_task.cancel()

    history: list[dict[str, str]] = list(context.chat_data.get("claude_messages") or [])
    history.append({"role": "user", "content": cmd_line})
    history.append({"role": "assistant", "content": reply_text})
    context.chat_data["claude_messages"] = claude.trim_messages(history)

    await update.message.reply_text(reply_text)
    await memory.maybe_write_memory(sender_id, cmd_line, reply_text)


async def social_comedy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_social_command(update, context, SocialIntent.COMEDY)


async def social_music_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_social_command(update, context, SocialIntent.MUSIC)


async def social_today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_social_command(update, context, SocialIntent.TODAY)


async def social_events_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_social_command(update, context, SocialIntent.EVENTS)


async def social_food_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_social_command(update, context, SocialIntent.FOOD)

# /clear command: wipes the in-memory Claude conversation history for this chat
async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not access.is_allowed(update):
        return
    context.chat_data.pop("claude_messages", None)
    await update.message.reply_text("In-chat history cleared (Pinecone untouched).")

# /status command: provides a lightweight status for operators (whitelisted only)
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not access.is_allowed(update):
        return
    uptime = _format_uptime(time.time() - config.START_TIME)
    n_hist = len(context.chat_data.get("claude_messages") or [])
    uid = update.effective_user.id if update.effective_user else 0
    has_profile = uid in config.USER_PROFILES
    await update.message.reply_text(
        f"Helix running\n"
        f"Uptime: {uptime}\n"
        f"Claude calls: {config.CLAUDE_CALL_COUNT}\n"
        f"Tavily calls: {config.TAVILY_CALL_COUNT}/{config.TAVILY_DAILY_FREE_LIMIT}\n"
        f"History buffer: {n_hist}\n"
        f"Model: {config.CLAUDE_MODEL}\n"
        f"Profile: {'yes' if has_profile else 'fallback'}\n"
        f"Memory: {'on' if config.MEMORY_ENABLED else 'off'} ({config.PINECONE_INDEX_NAME})"
    )

# /usage command: provides a usage summary for the current session
async def usage_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not access.is_allowed(update):
        return
    est = (
        config.TOTAL_INPUT_TOKENS * config.HAIKU_INPUT_COST_PER_TOKEN
        + config.TOTAL_OUTPUT_TOKENS * config.HAIKU_OUTPUT_COST_PER_TOKEN
    )
    await update.message.reply_text(
        f"Session usage\n"
        f"Calls: {config.CLAUDE_CALL_COUNT}\n"
        f"Tavily ok/fail: {config.TAVILY_SUCCESS_COUNT}/{config.TAVILY_FAILURE_COUNT}\n"
        f"In: {config.TOTAL_INPUT_TOKENS:,}  Out: {config.TOTAL_OUTPUT_TOKENS:,}\n"
        f"Est USD: ${est:.5f}"
    )

# /memory_reset command: deletes all memories for the current user
async def memory_reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not access.is_allowed(update):
        return
    if not config.pinecone_index:
        await update.message.reply_text("Pinecone not configured.")
        return
    uid = update.effective_user.id
    ns = memory.namespace_for_user(uid)
    try:
        await embeddings.pinecone_delete_all_namespace(ns)
        log.info("memory_reset user_id=%s namespace=%s", uid, ns)
        await update.message.reply_text(f"Long-term memory cleared for your user id (namespace {ns}).")
    except Exception:
        log.exception("memory_reset failed user_id=%s", uid)
        await update.message.reply_text("Memory reset failed (see server logs).")

# /memory_list command: lists the IDs of the current user's memories
async def memory_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not access.is_allowed(update):
        return
    if not config.pinecone_index:
        await update.message.reply_text("Pinecone not configured.")
        return
    uid = update.effective_user.id
    ns = memory.namespace_for_user(uid)
    try:
        ids = await embeddings.pinecone_list_ids(ns, limit=50)
    except Exception:
        log.exception("memory_list list failed user_id=%s", uid)
        await update.message.reply_text("memory_list failed.")
        return
    if not ids:
        await update.message.reply_text("No stored memories in your namespace.")
        return
    lines: list[str] = [f"Memories ({len(ids)} ids, showing metadata only):", ""]
    chunk = ids[:40]
    try:
        fr = await embeddings.pinecone_fetch_ids(chunk, ns)
    except Exception:
        log.exception("memory_list fetch failed user_id=%s", uid)
        await update.message.reply_text("memory_list fetch failed.")
        return
    for vid in chunk:
        vec = fr.vectors.get(vid) if fr.vectors else None
        md = vec.metadata if vec else None
        if not md:
            lines.append(f"{vid} (no metadata)")
            continue
        lines.append(
            f"{vid} | kind={md.get('kind')} | at={md.get('created_at')}",
        )
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "\n…"
    await update.message.reply_text(text)


async def memory_debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not access.is_allowed(update):
        return
    if not config.pinecone_index:
        await update.message.reply_text("Pinecone not configured.")
        return
    uid = update.effective_user.id
    ns = memory.namespace_for_user(uid)
    try:
        ids = await embeddings.pinecone_list_ids(ns, limit=30)
    except Exception:
        log.exception("memory_debug list failed user_id=%s", uid)
        await update.message.reply_text("memory_debug failed.")
        return
    if not ids:
        await update.message.reply_text("No memories.")
        return
    lines: list[str] = ["memory_debug (includes summaries):", ""]
    try:
        fr = await embeddings.pinecone_fetch_ids(ids[:25], ns)
    except Exception:
        log.exception("memory_debug fetch failed user_id=%s", uid)
        await update.message.reply_text("memory_debug fetch failed.")
        return
    for vid in ids[:25]:
        vec = fr.vectors.get(vid) if fr.vectors else None
        md = vec.metadata if vec else {}
        summ = md.get("summary", "") if md else ""
        lines.append(f"— {vid}\n  kind={md.get('kind')} at={md.get('created_at')}\n  {summ}\n")
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "\n…"
    await update.message.reply_text(text)
