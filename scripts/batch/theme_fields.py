"""Theme angle helpers: productFlow generation + themeAngle formatting."""

from __future__ import annotations

from typing import Any


def _attr(row: Any, name: str) -> str:
    """Read attribute from dataclass or dict, return stripped string."""
    if hasattr(row, name):
        return (getattr(row, name) or "").strip()
    if isinstance(row, dict):
        return (row.get(name) or "").strip()
    return ""


def generate_product_flow(row: Any) -> str:
    """Template-based English productFlow from theme fields.

    Mirrors the fallback logic of ``_product_flow_from_theme`` in the legacy
    cursor-ios-batch pipeline: builds a Browse/save/log/export tool-flow string
    from ``audience``, ``core_scene`` and ``local_feature``.
    """
    audience = _attr(row, "audience") or "users"
    scene = _attr(row, "core_scene") or "daily tasks"
    feature = _attr(row, "local_feature") or "journal"
    return (
        f"Pick a category chip to browse {scene}, save entries in a {feature}, "
        f"log notes for {audience}, attach reference photos per item, "
        f"export a weekly summary card, and review saved items by tag or date"
    )


def format_theme_angle(row: Any) -> str:
    """Build English themeAngle for prompts, registry, and queue desc.

    Assembles ``Theme: …; Track: …; Audience: …; Core scene: …;
    Local feature: …; Product flow: …`` from flat theme-library columns.
    Falls back to ``name — full_name`` when no theme fields are present.
    """
    segments: list[str] = []
    theme_cn = _attr(row, "theme_cn")
    if theme_cn:
        segments.append(f"Theme: {theme_cn}")
    track = _attr(row, "track")
    if track:
        segments.append(f"Track: {track}")
    audience = _attr(row, "audience")
    if audience:
        segments.append(f"Audience: {audience}")
    core_scene = _attr(row, "core_scene")
    if core_scene:
        segments.append(f"Core scene: {core_scene}")
    local_feature = _attr(row, "local_feature")
    if local_feature:
        segments.append(f"Local feature: {local_feature}")
    product_flow = _attr(row, "product_flow")
    if product_flow:
        segments.append(f"Product flow: {product_flow}")
    if segments:
        return "; ".join(segments)
    name = _attr(row, "name")
    full_name = _attr(row, "full_name")
    return f"{name} — {full_name}".strip(" —")


def parse_legacy_theme_angle(value: str) -> dict[str, str]:
    """Parse old ``Theme: …; Track: …`` blob into flat keys."""
    import re

    raw = (value or "").strip()
    if not raw:
        return {}
    if not raw.lower().startswith("theme:"):
        return {"theme_en": raw}

    parts = re.split(r"\s*;\s*(?=Theme:|Track:|Audience:|Core scene:|Local feature:|Product flow:)", raw)
    key_map = {
        "theme": "theme_en",
        "track": "track",
        "audience": "audience",
        "core scene": "core_scene",
        "local feature": "local_feature",
        "product flow": "product_flow",
    }
    out: dict[str, str] = {}
    for part in parts:
        part = part.strip()
        if not part or ":" not in part:
            continue
        label, _, val = part.partition(":")
        key = key_map.get(label.strip().lower())
        if key:
            out[key] = val.strip()
    return out


def theme_task_description(row: Any, *, fallback: str = "") -> str:
    """Description passed to ``QueueTask`` / pipeline ``ctx.desc``."""
    angle = format_theme_angle(row)
    return angle or fallback
