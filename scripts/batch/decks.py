"""Differentiation decks: deterministic per-app card assignment.

The PM deck enforces functional differentiation; the Designer deck enforces
visual differentiation. Each app draws exactly ONE card per dimension via a
deterministic hash of (appName, batchId, dimensionName), so the result is
reproducible and conflict-free across the batch.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_DECK_DIR = "data/decks"


def _stable_tie(seed: str) -> int:
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12], 16)


def ordered_cards_for_dim(
    cards: list[str],
    usage_col: dict[str, int],
    *,
    batch_id: str,
    app_name: str,
    csv_col: str,
) -> list[str]:
    """Least-used first; stable hash tie-break."""

    def sort_key(card: str) -> tuple[int, int]:
        count = usage_col.get(card, 0)
        tie = _stable_tie(f"{batch_id}\x1f{app_name}\x1f{csv_col}\x1f{card}")
        return (count, tie)

    return sorted(cards, key=sort_key)


def load_deck(deck_path: Path) -> dict[str, Any]:
    """Load and validate a deck JSON file."""
    if not deck_path.is_file():
        raise FileNotFoundError(f"差异化卡组缺失: {deck_path}")
    try:
        data = json.loads(deck_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"差异化卡组 JSON 不合法: {deck_path} ({exc})") from exc
    if not isinstance(data, dict) or "dimensions" not in data:
        raise ValueError(f"差异化卡组缺少 dimensions 字段: {deck_path}")
    return data
