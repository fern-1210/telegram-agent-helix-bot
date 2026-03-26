"""Tavily web search wrapper with safe logging and graceful fallback."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from typing import Any

from app.ai.query_sanitize import sanitize_query_for_web
from app.infra import config
from app.infra.logging import get_logger

log = get_logger("helix")

_TAVILY_SEARCH_URL = "https://api.tavily.com/search"


# ----
#  ==== TAVILY TRIMMIGN THE FAT  ====
#  only returns page title, ulr and snippet of content
# -------


def _compact_result(item: dict[str, Any]) -> dict[str, str]:
    return {
        "title": str(item.get("title", "")).strip(),
        "url": str(item.get("url", "")).strip(),
        "content": str(item.get("content", "")).strip(),
    }

# ----
#  ==== TAVILY API Call   ====
#  only returns page title, ulr and snippet of content
# -------


def _request_tavily(query: str) -> dict[str, Any]:
    payload = {
        "api_key": config.TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": config.TAVILY_MAX_RESULTS,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _TAVILY_SEARCH_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout = max(1.0, float(config.TAVILY_SEARCH_TIMEOUT_SECONDS))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw.strip() else {}


async def tavily_search(query: str) -> dict[str, Any]:
    """
    Run a single Tavily search request.

    Input query is expected to already be sanitized by caller policy.
    """
    normalized_query = query.strip()
    # sanitize the query to remove personal information
    sanitized_query = (
        sanitize_query_for_web(normalized_query)
        if config.TAVILY_ENABLE_QUERY_SANITIZER
        else normalized_query
    )

    # 2 checks before running query: empty query or missing api key
    if not normalized_query:
        return {"ok": False, "error": "empty_query", "results": []}
    if not sanitized_query:
        return {"ok": False, "error": "query_fully_redacted", "results": []}

    if not config.TAVILY_API_KEY:
        log.warning("Tavily search skipped: missing API key")
        config.TAVILY_FAILURE_COUNT += 1
        return {"ok": False, "error": "missing_api_key", "results": []}

    if config.TAVILY_CALL_COUNT >= config.TAVILY_DAILY_FREE_LIMIT:
        log.warning("Tavily search skipped: configured daily limit reached")
        config.TAVILY_FAILURE_COUNT += 1
        return {"ok": False, "error": "daily_limit_reached", "results": []}

    config.TAVILY_CALL_COUNT += 1

    # gracefull error handling for the api call
    try:
        raw = await asyncio.to_thread(_request_tavily, sanitized_query)
    except urllib.error.HTTPError as exc:
        log.warning("Tavily HTTP error status=%s", exc.code)
        config.TAVILY_FAILURE_COUNT += 1
        return {"ok": False, "error": f"http_{exc.code}", "results": []}
    except urllib.error.URLError:
        log.warning("Tavily network error")
        config.TAVILY_FAILURE_COUNT += 1
        return {"ok": False, "error": "network_error", "results": []}
    except TimeoutError:
        log.warning("Tavily request timed out")
        config.TAVILY_FAILURE_COUNT += 1
        return {"ok": False, "error": "timeout", "results": []}
    except Exception:
        log.exception("Tavily unexpected failure")
        config.TAVILY_FAILURE_COUNT += 1
        return {"ok": False, "error": "unexpected_error", "results": []}

    # extract the results from the api response
    items = raw.get("results") if isinstance(raw, dict) else []
    if not isinstance(items, list):
        items = []
    # trim the results to the page title, url and snippet of content
    results = [_compact_result(item) for item in items if isinstance(item, dict)]
    answer = str(raw.get("answer", "")).strip() if isinstance(raw, dict) else ""
    config.TAVILY_SUCCESS_COUNT += 1
    log.info("Tavily search success results=%s", len(results))
    return {"ok": True, "error": "", "results": results, "answer": answer}
