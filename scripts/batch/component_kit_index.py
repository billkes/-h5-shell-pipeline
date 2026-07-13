"""Scan and validate data/static/component_kit/ for pipeline gates and prompt injection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_BATCH_DIR = Path(__file__).resolve().parents[2]
KIT_ROOT = _BATCH_DIR / "data" / "static" / "component_kit"

_ID_LINE_RE = re.compile(r"^##\s+组件\s+ID\s*$", re.M)
_ID_VALUE_RE = re.compile(r"^`([^`]+)`\s*$", re.M)


@dataclass(frozen=True)
class ComponentKitEntry:
    component_id: str
    category: str
    name: str
    path: Path


def _parse_component_id(md_text: str, rel_path: Path) -> str | None:
    match = _ID_LINE_RE.search(md_text)
    if not match:
        parts = rel_path.parts
        if len(parts) >= 2:
            return f"{parts[-2]}/{rel_path.stem}"
        return None
    tail = md_text[match.end() :]
    value = _ID_VALUE_RE.search(tail)
    if value:
        return value.group(1).strip()
    return None


def scan_component_kit(root: Path | None = None) -> list[ComponentKitEntry]:
    """Return all indexed components under component_kit/."""
    base = root or KIT_ROOT
    if not base.is_dir():
        return []
    entries: list[ComponentKitEntry] = []
    skip = {"README.md", "baseline.md", "tokens.md"}
    for path in sorted(base.rglob("*.md")):
        if path.name in skip:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(base)
        cid = _parse_component_id(text, rel)
        if not cid or "/" not in cid:
            continue
        category, name = cid.split("/", 1)
        entries.append(
            ComponentKitEntry(
                component_id=cid,
                category=category,
                name=name,
                path=path,
            )
        )
    return entries


def component_id_set(root: Path | None = None) -> set[str]:
    return {e.component_id for e in scan_component_kit(root)}


def validate_selection_ids(
    ids: list[str],
    *,
    root: Path | None = None,
) -> list[str]:
    """Return unknown component ids (not in kit, not marked temporary)."""
    known = component_id_set(root)
    issues: list[str] = []
    for raw in ids:
        cid = raw.strip()
        if not cid or cid.lower().startswith("temp"):
            continue
        if cid not in known:
            issues.append(f"component_kit 中未找到组件: {cid}")
    return issues


_KIT_CATEGORY_RE = re.compile(
    r"^(primitives|navigation|feedback|data_display|patterns|shell)/[a-z0-9_]+$",
    re.I,
)


def normalize_component_id(raw: str) -> str:
    """Canonical form category/id."""
    cid = raw.strip().strip("`")
    if not cid:
        return ""
    if "/" in cid:
        category, name = cid.split("/", 1)
        return f"{category.strip()}/{name.strip()}"
    return cid


def is_kit_component_id(cid: str) -> bool:
    """True when id matches canonical component_kit category/id."""
    norm = normalize_component_id(cid)
    return bool(norm and _KIT_CATEGORY_RE.match(norm))


def parse_lock_component_entry(item: object) -> str | None:
    """Normalize one componentSelection entry (object or category/id string)."""
    if isinstance(item, str):
        cid = normalize_component_id(item)
        return cid if is_kit_component_id(cid) else None
    if isinstance(item, dict):
        cid = str(item.get("id") or "").strip()
        cat = str(item.get("category") or "").strip()
        if cid and cat:
            combined = normalize_component_id(f"{cat}/{cid}")
            return combined if is_kit_component_id(combined) else None
        if cid and "/" in cid:
            combined = normalize_component_id(cid)
            return combined if is_kit_component_id(combined) else None
    return None


def resolve_baseline_reference(ref: object) -> dict[str, str]:
    """Parse baselineReference whether object or legacy single-path string."""
    empty = {"h5": "", "flutter": ""}
    if ref is None:
        return empty
    if isinstance(ref, dict):
        return {
            "h5": str(ref.get("h5") or "").strip(),
            "flutter": str(ref.get("flutter") or "").strip(),
        }
    if isinstance(ref, str):
        text = ref.strip()
        if not text:
            return empty
        lower = text.lower()
        out = {"h5": "", "flutter": ""}
        if "#h5" in lower or lower.endswith("#h5"):
            out["h5"] = text
        if "#flutter" in lower or lower.endswith("#flutter"):
            out["flutter"] = text
        if not out["h5"] and not out["flutter"]:
            # Legacy: single baseline path for h5_shell vault-only packs.
            if "baseline" in lower:
                out["h5"] = text
            else:
                out["flutter"] = text
        return out
    return empty


def extract_selection_ids_from_blueprint(visual_text: str) -> list[str]:
    """Parse §Component Selection table rows for component id (category/id)."""
    section = _extract_md_section(visual_text, "Component Selection")
    if not section:
        return []
    ids: list[str] = []
    header_cells: list[str] = []
    category_idx = -1
    id_idx = 0
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells:
            continue
        first = cells[0].lower()
        if re.match(r"^:?-+:?$", first):
            continue
        if first in ("组件 id", "component id") or "分类" in first or "category" in first:
            header_cells = [c.lower() for c in cells]
            for i, h in enumerate(header_cells):
                if h in ("组件 id", "component id", "id"):
                    id_idx = i
                if h in ("分类", "category"):
                    category_idx = i
            continue
        if first in ("id",) and len(cells) > 1 and "分类" in " ".join(cells).lower():
            header_cells = [c.lower() for c in cells]
            continue
        if header_cells and (first == header_cells[0] or "----" in first):
            continue
        comp_id = cells[id_idx] if id_idx < len(cells) else cells[0]
        if comp_id.lower() in ("组件 id", "component id", "id"):
            continue
        if "/" in comp_id:
            ids.append(comp_id)
        elif category_idx >= 0 and category_idx < len(cells) and cells[category_idx]:
            ids.append(f"{cells[category_idx]}/{comp_id}")
        else:
            ids.append(comp_id)
    return _filter_kit_component_ids(ids)


def _filter_kit_component_ids(ids: list[str]) -> list[str]:
    """Drop pseudo baseline rows and non-kit paths."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in ids:
        cid = normalize_component_id(raw)
        if not cid or not is_kit_component_id(cid) or cid in seen:
            continue
        seen.add(cid)
        out.append(cid)
    return out


def extract_override_ids_from_blueprint(visual_text: str) -> list[str]:
    """Parse §Package Token Overrides table first-column component ids."""
    section = _extract_md_section(visual_text, "Package Token Overrides")
    if not section:
        legacy = _extract_md_section(visual_text, "Shared Component Whitelist")
        section = legacy
    if not section:
        return []
    raw = _parse_table_component_ids(section)
    selection_ids = extract_selection_ids_from_blueprint(visual_text)
    by_short: dict[str, str] = {}
    for sid in selection_ids:
        if "/" in sid:
            by_short[sid.split("/", 1)[1]] = normalize_component_id(sid)
    resolved: list[str] = []
    for rid in raw:
        norm = normalize_component_id(rid)
        if "/" in norm:
            resolved.append(norm)
        elif norm in by_short:
            resolved.append(by_short[norm])
        else:
            resolved.append(norm)
    return _filter_kit_component_ids(resolved)


def extract_selection_ids_from_visual_lock(lock_data: dict) -> list[str]:
    """Parse componentSelection array from 本包视觉锁.json."""
    selection = lock_data.get("componentSelection") or []
    if not isinstance(selection, list):
        return []
    ids: list[str] = []
    seen: set[str] = set()
    for item in selection:
        parsed = parse_lock_component_entry(item)
        if parsed and parsed not in seen:
            seen.add(parsed)
            ids.append(parsed)
    return ids


def extract_selection_ids_from_plan(plan_text: str) -> list[str]:
    """Extract category/id mentions from §2.x Component & Baseline Implementation Order."""
    match = re.search(
        r"(?is)(?:component\s*&\s*baseline\s*implementation\s*order|组件.*baseline.*实现顺序)(.*?)(?:\n#{1,3}\s*§?[34]\b|\n###\s*§?[34]\b|\Z)",
        plan_text,
    )
    block = match.group(1) if match else plan_text
    ids: set[str] = set()
    for m in re.finditer(
        r"\b(primitives|navigation|feedback|data_display|patterns|shell)/[a-z0-9_]+",
        block,
        re.I,
    ):
        ids.add(normalize_component_id(m.group(0).lower()))
    for m in re.finditer(
        r"component_kit/(primitives|navigation|feedback|data_display|patterns|shell)/([a-z0-9_]+)\.md",
        block,
        re.I,
    ):
        ids.add(normalize_component_id(f"{m.group(1).lower()}/{m.group(2).lower()}"))
    for raw in _parse_table_component_ids(block):
        norm = normalize_component_id(raw)
        if norm:
            ids.add(norm)
    return sorted(ids)


def extract_selection_screen_refs(visual_text: str) -> set[str]:
    """Parse screens column values from §Component Selection table."""
    section = _extract_md_section(visual_text, "Component Selection")
    if not section:
        return set()
    refs: set[str] = set()
    screens_idx = -1
    header_cells: list[str] = []
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or re.match(r"^:?-+:?$", cells[0]):
            continue
        first = cells[0].lower()
        if "screen" in first or first in ("屏", "引用屏"):
            header_cells = [c.lower() for c in cells]
            for i, h in enumerate(header_cells):
                if "screen" in h or h in ("屏", "引用屏"):
                    screens_idx = i
            continue
        if header_cells and screens_idx >= 0 and screens_idx < len(cells):
            cell = cells[screens_idx]
            if cell and cell.lower() not in ("screens", "screen", "屏"):
                for part in re.split(r"[,，、/]", cell):
                    sid = re.sub(r"[^a-zA-Z0-9_-]", "_", part.strip()).lower().strip("_")
                    if sid:
                        refs.add(sid)
    return refs


def extract_tokens_from_overrides(visual_text: str) -> set[str]:
    """Collect typography/color token names from Overrides table."""
    section = _extract_md_section(visual_text, "Package Token Overrides")
    if not section:
        section = _extract_md_section(visual_text, "Shared Component Whitelist")
    if not section:
        return set()
    tokens: set[str] = set()
    typo_idx = color_idx = -1
    header_cells: list[str] = []
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or re.match(r"^:?-+:?$", cells[0]):
            continue
        first = cells[0].lower()
        joined = " ".join(c.lower() for c in cells)
        if first in ("component id", "组件 id") or (
            "minheight" in joined.replace(" ", "")
            and "padding" in joined
            and ("typography" in joined or "color" in joined)
        ):
            header_cells = [c.lower() for c in cells]
            typo_idx = color_idx = -1
            for i, h in enumerate(header_cells):
                if "typography" in h:
                    typo_idx = i
                if h == "color" or h.endswith(" color") or h.startswith("color "):
                    color_idx = i
            continue
        if typo_idx < 0 and color_idx < 0:
            continue
        for idx in (typo_idx, color_idx):
            if 0 <= idx < len(cells):
                val = cells[idx]
                if val and val.lower() not in ("n/a", "—", "-", "kit-default"):
                    for part in re.split(r"[,/]", val):
                        t = part.strip()
                        if t and not t.endswith("pt"):
                            tokens.add(t)
    return tokens


def _parse_table_component_ids(section: str) -> list[str]:
    ids: list[str] = []
    header_cells: list[str] = []
    category_idx = -1
    id_idx = 0
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells:
            continue
        first = cells[0].lower()
        if re.match(r"^:?-+:?$", first):
            continue
        if first in ("组件 id", "component id") or "分类" in first or "category" in first:
            header_cells = [c.lower() for c in cells]
            for i, h in enumerate(header_cells):
                if h in ("组件 id", "component id", "id"):
                    id_idx = i
                if h in ("分类", "category"):
                    category_idx = i
            continue
        comp_id = cells[id_idx] if id_idx < len(cells) else cells[0]
        if comp_id.lower() in ("组件 id", "component id", "id", "kit-default"):
            continue
        if comp_id.lower() == "kit-default":
            continue
        if "/" in comp_id:
            ids.append(normalize_component_id(comp_id))
        elif category_idx >= 0 and category_idx < len(cells) and cells[category_idx]:
            ids.append(normalize_component_id(f"{cells[category_idx]}/{comp_id}"))
        elif comp_id and not re.match(r"^:?-+:?$", comp_id):
            ids.append(normalize_component_id(comp_id))
    return ids


def _extract_md_section(text: str, heading_fragment: str) -> str:
    lines = text.splitlines()
    frag = heading_fragment.lower()
    start: int | None = None
    start_level = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        title = stripped[level:].strip().lower()
        if frag in title:
            start = i + 1
            start_level = level
            break
    if start is None:
        return ""
    out: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if level <= start_level:
                break
        out.append(line)
    return "\n".join(out)


def verify_component_kit_blueprint(visual_text: str) -> list[str]:
    """Gate checks for Component Selection + Package Token Overrides."""
    issues: list[str] = []
    has_selection = "component selection" in visual_text.lower()
    has_overrides = "package token overrides" in visual_text.lower()
    has_legacy_whitelist = "shared component whitelist" in visual_text.lower()

    if not has_selection:
        if has_legacy_whitelist:
            issues.append(
                "[SOFT] 视觉蓝图仍使用 Shared Component Whitelist，建议迁移为 "
                "§Component Selection + §Package Token Overrides"
            )
        else:
            issues.append("视觉蓝图.md 缺少 §Component Selection")

    if not has_overrides:
        if has_legacy_whitelist:
            pass  # legacy whitelist carries token columns
        else:
            issues.append("视觉蓝图.md 缺少 §Package Token Overrides")

    if has_selection:
        section = _extract_md_section(visual_text, "Component Selection")
        if section and not re.search(r"^\s*\|", section, re.M):
            issues.append("视觉蓝图.md §Component Selection 须含表格")
        ids = extract_selection_ids_from_blueprint(visual_text)
        if not ids:
            issues.append("视觉蓝图.md §Component Selection 须列出至少一个组件 ID")
        issues.extend(validate_selection_ids(ids))

    overrides = _extract_md_section(visual_text, "Package Token Overrides")
    if overrides and not re.search(
        r"height|minHeight|typography|padding|radius|token",
        overrides,
        re.I,
    ):
        issues.append(
            "视觉蓝图.md §Package Token Overrides 须含 height/padding/radius/typography token 列"
        )

    legacy = _extract_md_section(visual_text, "Shared Component Whitelist")
    if legacy and not has_overrides and not re.search(
        r"height|minHeight|typography|padding|radius|token",
        legacy,
        re.I,
    ):
        issues.append(
            "视觉蓝图.md Shared Component Whitelist 须含 height/padding/radius/typography token 列"
        )

    return issues


def verify_plan_component_order(plan_text: str) -> list[str]:
    """Plan gate: §2 must describe component implementation order."""
    if not re.search(
        r"component\s*&\s*baseline\s*implementation\s*order|组件.*baseline.*实现顺序",
        plan_text,
        re.I,
    ):
        return ["产包计划.md §2 须含 Component & Baseline Implementation Order"]
    return []


def format_kit_index_for_prompt(root: Path | None = None) -> str:
    """Compact component_kit index for prompt injection."""
    entries = scan_component_kit(root)
    if not entries:
        return ""
    by_cat: dict[str, list[str]] = {}
    for entry in entries:
        by_cat.setdefault(entry.category, []).append(entry.component_id)
    lines = [
        "[Component Kit Index — data/static/component_kit/]",
        f"- {len(entries)} indexed components (read per-id .md before selecting):",
    ]
    for category in sorted(by_cat):
        ids = ", ".join(sorted(by_cat[category]))
        lines.append(f"  · {category}: {ids}")
    return "\n".join(lines)
