"""Query sanitization for external web search tools."""

from __future__ import annotations

import re

# ----
#  removes high-risk PII-like terms before external web lookup
# -------
_RE_EMAIL = re.compile(r"\b[\w.\-+%]+@[\w.\-]+\.[A-Za-z]{2,}\b")
_RE_PHONEISH = re.compile(r"\b\+?\d[\d\s\-()]{7,}\d\b")
_RE_POSTCODE = re.compile(r"\b\d{5}\b")
_RE_STREET = re.compile(
    r"\b[\wäöüÄÖÜß.\-]+(?:straße|strasse|str\.|allee|weg|platz|ring|damm|ufer)\s+\d{1,4}[a-z]?\b",
    re.IGNORECASE,
)
_RE_APT_UNIT = re.compile(r"\b(?:no\.?|#|apt\.?|flat|unit)\s*\d+\w*\b", re.IGNORECASE)
_RE_MULTISPACE = re.compile(r"\s+")


def sanitize_query_for_web(raw_query: str) -> str:
    """Redact likely personal identifiers while preserving search intent."""
    text = (raw_query or "").strip()
    if not text:
        return ""

    # remove direct contact/address-like fragments
    text = _RE_EMAIL.sub("[redacted_email]", text)
    text = _RE_PHONEISH.sub("[redacted_phone]", text)
    text = _RE_STREET.sub("[redacted_address]", text)
    text = _RE_APT_UNIT.sub("[redacted_unit]", text)
    text = _RE_POSTCODE.sub("[redacted_postcode]", text)

    # keep coarse location intent (street names/intersections/venues) intact
    text = _RE_MULTISPACE.sub(" ", text).strip()
    return text
