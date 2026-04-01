"""Build anonymous Tavily query strings for local Berlin discovery."""

from __future__ import annotations

from app.social.intent import SocialIntent
from app.infra import config


def plan_queries(
    intent: SocialIntent,
    filter_text: str,
    *,
    days: int,
) -> list[str]:
    """
    Return 2–3 sanitized search strings (no personal addresses — area labels only).
    """
    area = config.SOCIAL_AREA_LABEL
    extra = (filter_text or "").strip()
    base_bits = [area, "Berlin"]

    queries: list[str] = []

    if intent == SocialIntent.COMEDY:
        queries.append(
            " ".join(
                [
                    "comedy",
                    "standup",
                    "open mic",
                    *base_bits,
                    f"next {days} days",
                    extra,
                ]
            ).strip()
        )
        queries.append(
            " ".join(
                [
                    "site:eventbrite.de",
                    "comedy",
                    *base_bits,
                    extra,
                ]
            ).strip()
        )

    elif intent == SocialIntent.MUSIC:
        queries.append(
            " ".join(
                [
                    "live music",
                    "jazz",
                    "hip hop",
                    "R&B",
                    "gig",
                    *base_bits,
                    f"next {days} days",
                    extra,
                ]
            ).strip()
        )
        queries.append(
            " ".join(
                [
                    "site:ra.co",
                    "Berlin",
                    "Neukölln",
                    "Kreuzberg",
                    extra,
                ]
            ).strip()
        )
        queries.append(
            " ".join(
                [
                    "site:eventbrite.de",
                    "live music",
                    "Berlin",
                    extra,
                ]
            ).strip()
        )

    elif intent == SocialIntent.TODAY:
        queries.append(
            " ".join(
                [
                    "events",
                    "tonight",
                    *base_bits,
                    extra,
                ]
            ).strip()
        )
        queries.append(
            " ".join(
                [
                    "site:berlin.de",
                    "events",
                    "Berlin",
                    "today",
                    extra,
                ]
            ).strip()
        )

    elif intent == SocialIntent.FOOD:
        queries.append(
            " ".join(
                [
                    "food festival",
                    "street food",
                    "Berlin",
                    f"next {days} days",
                    extra,
                ]
            ).strip()
        )
        queries.append(
            " ".join(
                [
                    "site:eventbrite.de",
                    "food",
                    "festival",
                    "Berlin",
                    extra,
                ]
            ).strip()
        )

    else:  # EVENTS general
        queries.append(
            " ".join(
                [
                    "events",
                    "culture",
                    *base_bits,
                    f"next {days} days",
                    extra,
                ]
            ).strip()
        )
        queries.append(
            " ".join(
                [
                    "site:meetup.com",
                    "Berlin",
                    "Neukölln",
                    "Kreuzberg",
                    extra,
                ]
            ).strip()
        )
        queries.append(
            " ".join(
                [
                    "site:eventbrite.de",
                    "Berlin",
                    "events",
                    extra,
                ]
            ).strip()
        )

    # De-dupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q_clean = " ".join(q.split())
        if q_clean and q_clean not in seen:
            seen.add(q_clean)
            out.append(q_clean)

    return out[: config.SOCIAL_MAX_QUERIES]


def extended_followup_query(intent: SocialIntent, filter_text: str, extended_days: int) -> str | None:
    """Optional wider window when the first pass returns few hits."""
    if intent == SocialIntent.TODAY:
        return None
    area = config.SOCIAL_AREA_LABEL
    extra = (filter_text or "").strip()
    return " ".join(
        [
            "events",
            "culture",
            area,
            "Berlin",
            f"next {extended_days} days",
            extra,
        ]
    ).strip()
