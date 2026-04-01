"""Orchestrate Tavily searches, ranking, and formatting for Stage 6."""

from __future__ import annotations

from app.ai.tavily_search import tavily_search
from app.infra import config
from app.infra.logging import get_logger
from app.social.formatting import format_discovery_reply
from app.social.planner import extended_followup_query, plan_queries
from app.social.ranker import rank_hits
from app.social.sources import load_trusted_list, trusted_list_path

log = get_logger("helix")


async def run_social_discovery(intent: SocialIntent, filter_text: str = "") -> str:
    """
    Run bounded Tavily queries, rank, return a Telegram-sized reply.
    """
    if not config.SOCIAL_DISCOVERY_ENABLED:
        return "Social discovery is disabled."

    if not config.TAVILY_API_KEY:
        return "Web search is not configured (missing TAVILY_API_KEY)."

    path = trusted_list_path()
    trusted = load_trusted_list(path)

    days = config.SOCIAL_DEFAULT_DAYS
    queries = plan_queries(intent, filter_text, days=days)

    raw: list[dict[str, str]] = []
    res: dict[str, object] = {"ok": False}
    for q in queries:
        res = await tavily_search(q)
        if res.get("ok"):
            raw.extend(res.get("results") or [])
        log.info(
            "social_discovery intent=%s query_ok=%s merged=%s",
            intent.value,
            bool(res.get("ok")),
            len(raw),
        )

    if len(raw) < config.SOCIAL_MERGE_THRESHOLD:
        ext_q = extended_followup_query(intent, filter_text, config.SOCIAL_EXTEND_DAYS)
        if ext_q:
            res2 = await tavily_search(ext_q)
            if res2.get("ok"):
                raw.extend(res2.get("results") or [])
            days = max(days, config.SOCIAL_EXTEND_DAYS)

    top = rank_hits(
        intent,
        raw,
        trusted_entries=trusted,
        filter_text=filter_text,
        top_n=config.SOCIAL_TOP_N,
    )

    return format_discovery_reply(intent, top, days_window=days)
