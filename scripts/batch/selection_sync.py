"""Sync componentSelection across visual lock, blueprint, and plan before plan.gate."""

from __future__ import annotations

import json
import re
from pathlib import Path

from batch.component_kit_index import (
    _extract_md_section,
    extract_override_ids_from_blueprint,
    extract_selection_ids_from_blueprint,
    extract_selection_ids_from_visual_lock,
    extract_tokens_from_overrides,
    normalize_component_id,
)
from batch.selection_requirements import collect_required_selection_ids

from batch.welcome_canon import WELCOME_LAYOUT_VARIANTS

VISUAL_BLUEPRINT_FILE = "视觉蓝图.md"
VISUAL_LOCK_FILE = "本包视觉锁.json"
SPEC_FILE = "功能文档.md"

# Paired color tokens used in Overrides but often omitted from Agent-generated locks.
_PAIRED_COLOR_DEFAULTS: dict[str, tuple[str, ...]] = {
    "onMuted": ("onSurfaceVariant", "onSurfaceVariantDark", "onSurface"),
}

_WELCOME_VARIANT_ALIASES: dict[str, str] = {
    "centered-card": "hero-top-card-legal",
    "centered_card": "hero-top-card-legal",
    "card": "hero-top-card-legal",
    "top-card-legal": "hero-top-card-legal",
}


def _sync_welcome_layout_variant(lock_data: dict) -> list[str]:
    """Normalize Agent-invented welcome layout names to canonical variants."""
    spec = lock_data.get("welcomeSpec")
    if not isinstance(spec, dict):
        return []
    variant = str(spec.get("layoutVariant") or "").strip()
    if not variant or variant in WELCOME_LAYOUT_VARIANTS:
        return []
    normalized = _WELCOME_VARIANT_ALIASES.get(variant) or "hero-top-card-legal"
    spec["layoutVariant"] = normalized
    lock_data["welcomeSpec"] = spec
    return [f"本包视觉锁.json welcomeSpec.layoutVariant {variant!r} → {normalized}"]


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _load_lock(workspace: Path) -> dict:
    path = workspace / VISUAL_LOCK_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _write_lock(workspace: Path, data: dict) -> None:
    path = workspace / VISUAL_LOCK_FILE
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _canonical_selection_ids(
    workspace: Path,
    *,
    pack_type: str,
    lock_data: dict,
) -> set[str]:
    lock_ids = {
        normalize_component_id(i)
        for i in extract_selection_ids_from_visual_lock(lock_data)
    }
    return collect_required_selection_ids(
        workspace, pack_type=pack_type, existing=lock_ids
    )


def _sync_lock_selection(
    lock_data: dict,
    canonical: set[str],
) -> list[str]:
    changes: list[str] = []
    current = {
        normalize_component_id(i)
        for i in extract_selection_ids_from_visual_lock(lock_data)
    }
    missing = sorted(canonical - current)
    if not missing:
        return changes
    selection = lock_data.get("componentSelection")
    if not isinstance(selection, list):
        selection = []
    for cid in missing:
        selection.append(cid)
        changes.append(f"本包视觉锁.json +componentSelection {cid}")
    lock_data["componentSelection"] = selection
    return changes


def _sync_color_tokens_for_overrides(
    lock_data: dict,
    blueprint_text: str,
) -> list[str]:
    changes: list[str] = []
    color_tokens = lock_data.get("colorTokens")
    if not isinstance(color_tokens, dict):
        color_tokens = {}
        lock_data["colorTokens"] = color_tokens
    override_tokens = extract_tokens_from_overrides(blueprint_text)
    known = {str(k) for k in color_tokens}
    known.update(str(k) for k in lock_data.get("typographyTokens") or {})
    for token in sorted(override_tokens):
        if not re.match(r"^[a-z][a-zA-Z0-9]*$", token):
            continue
        if token in known or token.lower() in ("n/a", "—", "-", "kit-default"):
            continue
        if token in color_tokens:
            continue
        defaults = _PAIRED_COLOR_DEFAULTS.get(token)
        if defaults:
            for src in defaults:
                if src in color_tokens:
                    color_tokens[token] = color_tokens[src]
                    changes.append(f"本包视觉锁.json colorTokens +{token} (from {src})")
                    known.add(token)
                    break
            continue
        if token.startswith("on") and len(token) > 2:
            base = token[2:]
            if base.lower() in color_tokens:
                color_tokens[token] = color_tokens[base.lower()]
                changes.append(f"本包视觉锁.json colorTokens +{token} (from {base.lower()})")
                known.add(token)
    return changes


def _append_before_marker(
    text: str,
    section_fragment: str,
    new_lines: list[str],
    *,
    markers: tuple[str, ...],
) -> tuple[str, bool]:
    if not new_lines:
        return text, False
    section = _extract_md_section(text, section_fragment)
    if not section:
        return text, False
    section_start = text.lower().find(section_fragment.lower())
    if section_start < 0:
        return text, False
    heading_line_end = text.find("\n", section_start)
    if heading_line_end < 0:
        return text, False
    body_start = heading_line_end + 1
    body = _extract_md_section(text, section_fragment)
    body_end = body_start + len(body)
    insert_at = body_end
    for marker in markers:
        idx = text.find(marker, body_start, body_end)
        if idx >= 0:
            insert_at = min(insert_at, idx)
    block = "\n".join(new_lines) + "\n"
    if insert_at < body_end:
        updated = text[:insert_at] + block + text[insert_at:]
    else:
        updated = text[:body_end] + "\n" + block + text[body_end:]
    return updated, True


def _selection_row(cid: str) -> str:
    category = cid.split("/", 1)[0] if "/" in cid else "primitives"
    return (
        f"| `{cid}` | {category} | synced | batch gate | all | "
        f"data/static/component_kit/{cid}.md | auto-sync |"
    )


def _override_row(cid: str) -> str:
    return (
        f"| `{cid}` | kit-default | kit-default | kit-default | "
        f"bodyMedium | surfaceVariant | batch-synced |"
    )


def _sync_blueprint_selection(
    blueprint_text: str,
    canonical: set[str],
) -> tuple[str, list[str]]:
    changes: list[str] = []
    current = {
        normalize_component_id(i)
        for i in extract_selection_ids_from_blueprint(blueprint_text)
    }
    missing = sorted(canonical - current)
    if not missing:
        return blueprint_text, changes
    rows = [_selection_row(cid) for cid in missing]
    updated, ok = _append_before_marker(
        blueprint_text,
        "Component Selection",
        rows,
        markers=("**Total selected", "**Baseline reference", "\n---"),
    )
    if ok:
        for cid in missing:
            changes.append(f"视觉蓝图.md §Component Selection +{cid}")
        return updated, changes
    return blueprint_text, changes


def _sync_blueprint_overrides(
    blueprint_text: str,
    canonical: set[str],
) -> tuple[str, list[str]]:
    changes: list[str] = []
    current = {
        normalize_component_id(i)
        for i in extract_override_ids_from_blueprint(blueprint_text)
    }
    missing = sorted(canonical - current)
    if not missing:
        return blueprint_text, changes
    rows = [_override_row(cid) for cid in missing]
    updated, ok = _append_before_marker(
        blueprint_text,
        "Package Token Overrides",
        rows,
        markers=("\n---", "## "),
    )
    if ok:
        for cid in missing:
            changes.append(f"视觉蓝图.md §Package Token Overrides +{cid}")
        return updated, changes
    return blueprint_text, changes


def sync_selection_artifacts(
    workspace: Path,
    *,
    pack_type: str,
) -> list[str]:
    """Align lock / blueprint / plan selection artifacts before plan.gate."""
    lock_data = _load_lock(workspace)
    if not lock_data:
        return []

    canonical = _canonical_selection_ids(workspace, pack_type=pack_type, lock_data=lock_data)
    if not canonical:
        return []

    changes: list[str] = []
    changes.extend(_sync_welcome_layout_variant(lock_data))
    changes.extend(_sync_lock_selection(lock_data, canonical))

    blueprint_path = workspace / VISUAL_BLUEPRINT_FILE
    blueprint_text = _read_text(blueprint_path)
    if blueprint_text:
        blueprint_text, c1 = _sync_blueprint_selection(blueprint_text, canonical)
        changes.extend(c1)
        blueprint_text, c2 = _sync_blueprint_overrides(blueprint_text, canonical)
        changes.extend(c2)
        changes.extend(_sync_color_tokens_for_overrides(lock_data, blueprint_text))

    if changes:
        _write_lock(workspace, lock_data)
        if blueprint_path.is_file() and blueprint_text:
            blueprint_path.write_text(blueprint_text, encoding="utf-8")

    return changes
