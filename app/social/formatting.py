"""Format top discovery hits for Telegram (plain text, concise)."""

from __future__ import annotations

import re

from app.social.intent import SocialIntent


def _snippet(text: str, max_len: int = 180) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _find_instagram_urls(blob: str) -> list[str]:
    return re.findall(r"https?://(?:www\.)?instagram\.com/[^\s)]+", blob, flags=re.I)


def format_discovery_reply(
    intent: SocialIntent,
    items: list[dict[str, str]],
    *,
    days_window: int,
) -> str:
    title_map = {
        SocialIntent.COMEDY: "Comedy (trusted + web)",
        SocialIntent.MUSIC: "Live music & clubs (trusted + web)",
        SocialIntent.TODAY: "Tonight / today",
        SocialIntent.EVENTS: "Events (next days)",
        SocialIntent.FOOD: "Food festivals & markets",
    }
    head = title_map.get(intent, "Discovery")
    lines: list[str] = [
        f"Helix — {head}",
        f"Area: Kreuzberg / Neukölln · window: ~{days_window} days (see each link for dates)",
        "",
    ]

    if not items:
        lines.append("No strong matches from the last search pass. Try /events or rephrase (genre, day).")
        return "\n".join(lines)

    for i, it in enumerate(items, start=1):
        t = str(it.get("title", "")).strip() or "Untitled"
        url = str(it.get("url", "")).strip()
        body = str(it.get("content", "")).strip()
        ig_links = _find_instagram_urls(body + " " + url)
        ig_note = f"\n   IG: {ig_links[0]}" if ig_links else ""

        lines.append(f"{i}) {t}")
        lines.append(f"   {_snippet(body)}")
        if url:
            lines.append(f"   Link: {url}{ig_note}")
        lines.append("")

    lines.append("Tip: add keywords after a slash command, e.g. /music jazz or /comedy open mic")
    return "\n".join(lines).strip()
