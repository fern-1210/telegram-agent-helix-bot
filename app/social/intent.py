"""Intent detection for Stage 6 social discovery (slash commands + conservative NL)."""

from __future__ import annotations

import re
from enum import Enum


class SocialIntent(str, Enum):
    COMEDY = "comedy"
    MUSIC = "music"
    TODAY = "today"
    EVENTS = "events"
    FOOD = "food"


# Strong single-keyword triggers (word boundaries)
# Order matters: music before generic "tonight" so "jazz gigs tonight" maps to music.
_STRONG_PATTERNS: list[tuple[SocialIntent, re.Pattern[str]]] = [
    (SocialIntent.COMEDY, re.compile(r"\b(stand[- ]?up|open\s*mic|comedy\s+(night|show)|standup)\b", re.I)),
    (SocialIntent.FOOD, re.compile(r"\b(food\s+festival|street\s+food|ramen\s+festival|taco\s+festival|food\s+event)\b", re.I)),
    (
        SocialIntent.MUSIC,
        re.compile(
            r"\b(live\s+music|gigs?\s+tonight|gig\s+tonight|jazz\s+night|jazz|hip\s*hop|open\s+air\s+concert)\b",
            re.I,
        ),
    ),
    (SocialIntent.TODAY, re.compile(r"\b(what'?s\s+on\s+tonight|tonight|today\s+evening|this\s+evening)\b", re.I)),
]

# Scored keyword groups (first match wins by priority order in detect)
_INTENT_KEYWORDS: list[tuple[SocialIntent, frozenset[str]]] = [
    (SocialIntent.FOOD, frozenset({"food", "festival", "ramen", "taco", "streetfood", "foodtruck"})),
    (SocialIntent.COMEDY, frozenset({"comedy", "comedian", "kabarett", "kabaret"})),
    (SocialIntent.TODAY, frozenset({"tonight", "today", "heute", "abend", "evening"})),
    (SocialIntent.MUSIC, frozenset({"jazz", "hip", "hop", "hiphop", "r&b", "rnb", "gig", "concert", "live", "techno", "club", "dj"})),
    (SocialIntent.EVENTS, frozenset({"events", "happening", "weekend", "program", "programme"})),
]


def _tokenize_for_keywords(text: str) -> set[str]:
    raw = re.sub(r"[^\w\s&]", " ", text.lower())
    parts = raw.split()
    out: set[str] = set()
    for p in parts:
        if len(p) >= 2:
            out.add(p)
        if "&" in p:
            out.update(x for x in p.split("&") if len(x) >= 2)
    return out


def detect_intent(text: str) -> tuple[SocialIntent | None, str]:
    """
    Return (intent, remainder) where remainder is text after stripping command/boilerplate.
    If no social intent, returns (None, original stripped text).
    """
    raw = (text or "").strip()
    if not raw:
        return None, ""

    # Strip leading /command if present (natural copy-paste)
    cmd_stripped = re.sub(r"^/\w+\s*", "", raw).strip()

    # Strong patterns first
    for intent, pat in _STRONG_PATTERNS:
        if pat.search(cmd_stripped):
            return intent, _clean_remainder(cmd_stripped)

    tokens = _tokenize_for_keywords(cmd_stripped)
    best: tuple[SocialIntent, int] | None = None
    for intent, keys in _INTENT_KEYWORDS:
        score = len(tokens & keys)
        if score <= 0:
            continue
        if best is None or score > best[1]:
            best = (intent, score)

    if best is not None:
        return best[0], _clean_remainder(cmd_stripped)

    return None, cmd_stripped


def _clean_remainder(text: str) -> str:
    """Light cleanup for extra search terms (genre, day, etc.)."""
    t = re.sub(r"\s+", " ", text).strip()
    return t[:500] if len(t) > 500 else t


def should_route_natural_language_discovery(text: str, max_chars: int) -> bool:
    """
    Conservative gate: avoid hijacking long general chat.
    """
    t = (text or "").strip()
    if not t or len(t) > max_chars:
        return False
    intent, _ = detect_intent(t)
    if intent is None:
        return False
    # Require at least two signals for generic single-word messages
    tokens = _tokenize_for_keywords(t)
    if len(tokens) == 1 and tokens.pop() in {"events", "music", "comedy", "food", "tonight", "today"}:
        return False
    return True
