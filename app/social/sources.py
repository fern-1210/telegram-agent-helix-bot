"""Parse trusted_list/list.txt — template rows, legacy bullets, and URL extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from app.infra import config
from app.infra.logging import get_logger

log = get_logger("helix")


def trusted_list_path() -> Path:
    """Resolved path to trusted_list/list.txt (see TRUSTED_LIST_PATH in config)."""
    return config.TRUSTED_LIST_FILE_PATH

_URL_RE = re.compile(r"https?://[^\s)\]>]+", re.I)


@dataclass
class TrustedEntry:
    """A venue, site, or listing source from the trusted list."""

    name: str
    category: str = ""
    area: str = ""
    url: str = ""
    instagram: str = ""
    raw_line: str = ""

    def domains(self) -> set[str]:
        out: set[str] = set()
        for link in (self.url, self.instagram):
            if not link or not link.startswith("http"):
                continue
            host = _hostname(link)
            if host:
                out.add(host.lower())
        return out


def _hostname(url: str) -> str:
    try:
        p = urlparse(url)
        return (p.hostname or "").lstrip("/")
    except Exception:
        return ""


def _normalize_instagram(s: str) -> str:
    s = s.strip()
    if not s:
        return ""
    if s.startswith("http"):
        return s
    handle = s.lstrip("@").strip()
    if handle:
        return f"https://instagram.com/{handle}"
    return ""


def _parse_pipe_line(body: str) -> TrustedEntry | None:
    """`- Name | cat | area | url | ig`"""
    parts = [p.strip() for p in body.split("|")]
    if len(parts) < 2:
        return None
    name = parts[0].strip()
    if not name:
        return None
    cat = parts[1] if len(parts) > 1 else ""
    area = parts[2] if len(parts) > 2 else ""
    url = parts[3] if len(parts) > 3 else ""
    ig = parts[4] if len(parts) > 4 else ""
    if url and not url.startswith("http"):
        # allow bare domain like deutschestheater.de
        if "." in url and " " not in url:
            url = f"https://{url.lstrip('/')}"
        else:
            url = ""
    ig_norm = _normalize_instagram(ig)
    return TrustedEntry(
        name=name,
        category=cat.lower(),
        area=area,
        url=url,
        instagram=ig_norm,
        raw_line=body,
    )


def _legacy_line_to_entry(line: str) -> TrustedEntry | None:
    stripped = line.strip()
    if not stripped.startswith("-"):
        return None
    body = stripped[1:].strip()
    if "|" in body:
        return _parse_pipe_line(body)

    urls = _URL_RE.findall(body)
    primary_url = urls[0] if urls else ""
    # Name: text before first URL or first " - " chunk
    name = body
    if primary_url:
        name = body.split(primary_url, 1)[0].strip()
        name = re.sub(r"\s*-\s*$", "", name).strip()
    else:
        # "Name - address" pattern
        bits = [b.strip() for b in body.split(" - ")]
        if bits:
            name = bits[0]

    name = re.sub(r"\s+", " ", name).strip()
    if not name and primary_url:
        host = _hostname(primary_url)
        name = host or "source"

    if not name:
        return None

    return TrustedEntry(
        name=name[:200],
        category="",
        area="",
        url=primary_url,
        instagram="",
        raw_line=body[:500],
    )


def load_trusted_list(path: Path) -> list[TrustedEntry]:
    if not path.is_file():
        log.warning("Trusted list not found at %s", path)
        return []

    entries: list[TrustedEntry] = []
    seen_urls: set[str] = set()

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Section headers (no leading dash)
        if not line.startswith("-"):
            continue

        ent: TrustedEntry | None = None
        if "|" in line:
            ent = _parse_pipe_line(line[1:].strip())
        else:
            ent = _legacy_line_to_entry(line)

        if ent:
            if ent.url:
                seen_urls.add(ent.url)
            entries.append(ent)

    # Bare URL lines (no leading bullet) — e.g. standalone https://...
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("http"):
            continue
        for u in _URL_RE.findall(line):
            if u in seen_urls:
                continue
            seen_urls.add(u)
            host = _hostname(u)
            entries.append(
                TrustedEntry(
                    name=host or "link",
                    url=u,
                    raw_line=line[:300],
                )
            )

    # Dedupe by (name, url) for stability
    deduped: list[TrustedEntry] = []
    keys: set[tuple[str, str]] = set()
    for e in entries:
        key = (e.name.lower(), e.url)
        if key in keys:
            continue
        keys.add(key)
        deduped.append(e)

    return deduped


def trusted_domains(entries: list[TrustedEntry]) -> set[str]:
    out: set[str] = set()
    for e in entries:
        out |= e.domains()
    return out
