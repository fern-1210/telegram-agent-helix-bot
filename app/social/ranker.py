"""Score and dedupe Tavily hits; prefer trusted domains and listing sites."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.social.intent import SocialIntent
from app.social.sources import TrustedEntry
from app.infra import config


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _matches_intent(intent: SocialIntent, title: str, content: str) -> int:
    blob = f"{title} {content}".lower()
    if intent == SocialIntent.COMEDY:
        return 2 if re.search(r"\b(comedy|stand\s*up|kabarett|open\s*mic)\b", blob) else 0
    if intent == SocialIntent.MUSIC:
        return 2 if re.search(r"\b(jazz|live music|concert|gig|dj|techno|club)\b", blob) else 0
    if intent == SocialIntent.FOOD:
        return 2 if re.search(r"\b(food|festival|market|street food)\b", blob) else 0
    if intent == SocialIntent.TODAY:
        return 1 if re.search(r"\b(tonight|today|heute|abend|evening)\b", blob) else 0
    return 1


def _listing_bonus(host: str) -> int:
    for d in config.SOCIAL_LISTING_DOMAIN_HINTS:
        if d in host:
            return 2
    return 0


def _keyword_bonus(filter_text: str, title: str, content: str) -> int:
    if not filter_text.strip():
        return 0
    words = [w for w in re.split(r"\W+", filter_text.lower()) if len(w) >= 3]
    if not words:
        return 0
    blob = f"{title} {content}".lower()
    hits = sum(1 for w in words if w in blob)
    return min(3, hits)


def score_result(
    intent: SocialIntent,
    title: str,
    url: str,
    content: str,
    *,
    trusted_hosts: set[str],
    filter_text: str,
) -> float:
    host = _host(url)
    score = 0.0
    if host and host in trusted_hosts:
        score += 5.0
    score += float(_listing_bonus(host))
    if "instagram.com" in (url or "").lower():
        score += 1.5
    score += float(_matches_intent(intent, title, content))
    score += float(_keyword_bonus(filter_text, title, content))
    # Light title presence
    if title and len(title) > 10:
        score += 0.5
    return score


def dedupe_key(url: str) -> str:
    try:
        p = urlparse(url)
        path = (p.path or "").rstrip("/")
        return f"{(p.hostname or '').lower()}{path[:120]}"
    except Exception:
        return url[:200]


def rank_hits(
    intent: SocialIntent,
    items: list[dict[str, str]],
    *,
    trusted_entries: list[TrustedEntry],
    filter_text: str,
    top_n: int,
) -> list[dict[str, str]]:
    trusted_hosts: set[str] = set()
    for e in trusted_entries:
        trusted_hosts |= e.domains()
        for d in config.SOCIAL_TRUSTED_EXTRA_HOSTS:
            trusted_hosts.add(d.lower())

    best: dict[str, tuple[float, dict[str, str]]] = {}
    for it in items:
        title = str(it.get("title", "")).strip()
        url = str(it.get("url", "")).strip()
        content = str(it.get("content", "")).strip()
        if not url:
            continue
        s = score_result(
            intent,
            title,
            url,
            content,
            trusted_hosts=trusted_hosts,
            filter_text=filter_text,
        )
        key = dedupe_key(url)
        prev = best.get(key)
        if prev is None or s > prev[0]:
            best[key] = (s, {"title": title, "url": url, "content": content})

    ranked = sorted(best.values(), key=lambda x: x[0], reverse=True)
    return [x[1] for x in ranked[:top_n]]
