"""Repair pub.dev advisories cache entries that crash `pub get`."""

from __future__ import annotations

from pathlib import Path

_PUB_ADVISORIES_CRASH = "readAdvisoriesFromCache"


def is_pub_advisories_crash(output: str) -> bool:
    return _PUB_ADVISORIES_CRASH in output


def hosted_pub_cache_dir() -> Path | None:
    base = Path.home() / ".pub-cache" / "hosted"
    if not base.is_dir():
        return None
    for child in base.iterdir():
        if child.is_dir() and (child / ".cache").is_dir():
            return child
    return None


def clear_pub_advisories_cache() -> int:
    """Remove *-advisories.json under hosted pub cache; return files removed."""
    root = hosted_pub_cache_dir()
    if root is None:
        return 0
    cache_dir = root / ".cache"
    removed = 0
    for path in cache_dir.glob("*-advisories.json"):
        try:
            path.unlink()
            removed += 1
        except OSError:
            continue
    return removed
