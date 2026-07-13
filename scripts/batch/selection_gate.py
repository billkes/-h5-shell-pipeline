"""Plan-phase gate: §Component Selection consistency across blueprint, lock, plan."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from batch.component_kit_index import (
    extract_override_ids_from_blueprint,
    extract_selection_ids_from_blueprint,
    extract_selection_ids_from_plan,
    extract_selection_ids_from_visual_lock,
    extract_selection_screen_refs,
    extract_tokens_from_overrides,
    normalize_component_id,
    validate_selection_ids,
)
from batch.pack_type import is_h5_shell
from batch.selection_requirements import (
    detect_feature_signals,
    parse_screen_inventory,
    verify_required_components,
)

VISUAL_BLUEPRINT_FILE = "视觉蓝图.md"
VISUAL_LOCK_FILE = "本包视觉锁.json"
PLAN_FILE = "产包计划.md"
SPEC_FILE = "功能文档.md"

# 1=core HARD, 2=screen coverage HARD, 3=screens column HARD
SELECTION_GATE_STRICT_LEVEL = max(
    1, min(3, int(os.environ.get("SELECTION_GATE_STRICT_LEVEL", "1")))
)


def selection_gate_enabled() -> bool:
    return os.environ.get("ENABLE_SELECTION_GATE", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _read_register(workspace: Path) -> dict:
    for name in ("本包登记信息.json", "package-register.json"):
        path = workspace / name
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass
    return {}


def _resolve_pack_type(workspace: Path, register: dict) -> str:
    pt = str(register.get("packType") or "").strip()
    if pt:
        return pt
    if register.get("bundleEntryPath") or register.get("h5SiteRoot") or register.get("h5VaultPattern"):
        return "h5_shell"
    state = workspace / ".build-state.json"
    if state.is_file():
        try:
            data = json.loads(state.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return str(data.get("packType") or "").strip()
        except json.JSONDecodeError:
            pass
    return ""


def _collect_visual_lock_tokens(lock_data: dict) -> set[str]:
    tokens: set[str] = set()
    for key in ("colorTokens", "typographyTokens"):
        val = lock_data.get(key)
        if isinstance(val, dict):
            tokens.update(str(k).strip() for k in val if str(k).strip())
    chip = lock_data.get("chipSpec")
    if isinstance(chip, dict):
        tokens.update(str(k).strip() for k in chip if str(k).strip())
    return tokens


def _verify_selection_id_consistency(
    blueprint_ids: set[str],
    lock_ids: set[str],
    override_ids: set[str],
    plan_ids: set[str],
) -> list[str]:
    issues: list[str] = []

    if not blueprint_ids:
        issues.append("[SEL-001] 视觉蓝图.md §Component Selection 须列出至少一个组件 ID")
        return issues

    only_blueprint = blueprint_ids - lock_ids
    only_lock = lock_ids - blueprint_ids
    if only_blueprint or only_lock:
        parts: list[str] = []
        if only_blueprint:
            parts.append(f"视觉锁缺失: {sorted(only_blueprint)}")
        if only_lock:
            parts.append(f"蓝图缺失: {sorted(only_lock)}")
        issues.append(f"[SEL-002] 蓝图 Selection IDs 与 本包视觉锁 componentSelection 不一致（{'; '.join(parts)}）")

    missing_overrides = blueprint_ids - override_ids
    if missing_overrides:
        issues.append(
            f"[SEL-003] 每个 Selection id 须在 §Package Token Overrides 有行（缺: {sorted(missing_overrides)}）"
        )

    orphan_overrides = override_ids - blueprint_ids
    if orphan_overrides:
        issues.append(
            f"[SEL-005] Overrides 含 Selection 外 id（{sorted(orphan_overrides)}）"
        )

    missing_plan = blueprint_ids - plan_ids
    if missing_plan:
        issues.append(
            f"[SEL-004] 产包计划 §2.x 未覆盖 Selection id（缺: {sorted(missing_plan)}）"
        )

    issues.extend(
        f"[SEL-006] {msg}"
        for msg in validate_selection_ids(sorted(blueprint_ids))
    )
    return issues


def _verify_override_tokens_resolved(
    override_tokens: set[str],
    lock_tokens: set[str],
) -> list[str]:
    issues: list[str] = []
    css_var = re.compile(r"^var\(--[a-z0-9-]+\)$", re.I)
    allowed = lock_tokens | frozenset(
        {
            "chipSpec",
            "listRowSpec",
            "overlayTokens",
            "primary",
            "onPrimary",
            "surfaceVariant",
            "surface",
            "onSurface",
        }
    )
    for token in sorted(override_tokens):
        if not token or token.lower() in ("n/a", "—", "-", "kit-default"):
            continue
        if css_var.match(token):
            continue
        if re.search(r"\d+\s*pt", token, re.I):
            continue
        for part in re.split(r"[,/]", token):
            part = part.strip()
            if not part or part.startswith("radius-"):
                continue
            if part in allowed:
                continue
            if re.match(r"^[a-z][a-zA-Z0-9]*$", part):
                issues.append(
                    f"[SEL-020] Overrides token `{part}` 未在 本包视觉锁 colorTokens/typographyTokens 中定义"
                )
    return issues


def _verify_screen_coverage(
    spec_text: str,
    blueprint_text: str,
    *,
    strict: bool,
) -> list[str]:
    if not strict:
        return []
    screens = parse_screen_inventory(spec_text)
    if not screens:
        return []
    refs = extract_selection_screen_refs(blueprint_text)
    covered: set[str] = set()
    for ref in refs:
        for sid in screens:
            if ref == sid or ref in sid or sid in ref:
                covered.add(sid)
    missing = [s for s in screens if s not in covered]
    if missing:
        return [
            f"[SEL-010] Screen Inventory 屏未被 Selection screens 列引用（{missing[:8]}{'…' if len(missing) > 8 else ''}）"
        ]
    return []


def _verify_screens_column(blueprint_text: str, *, strict: bool) -> list[str]:
    if not strict:
        return []
    refs = extract_selection_screen_refs(blueprint_text)
    ids = extract_selection_ids_from_blueprint(blueprint_text)
    if ids and not refs:
        return ["[SEL-011] §Component Selection 每行须填 screens 列（Screen Inventory 屏 id）"]
    return []


def verify_selection_plan(
    workspace: Path,
    *,
    pack_type: str = "",
    h5_shell: bool | None = None,
    strict_level: int | None = None,
) -> list[str]:
    """Run Selection rigor checks; return human-readable issue strings."""
    if not selection_gate_enabled():
        return []

    level = strict_level if strict_level is not None else SELECTION_GATE_STRICT_LEVEL
    register = _read_register(workspace)
    pt = pack_type or _resolve_pack_type(workspace, register)
    h5 = h5_shell if h5_shell is not None else is_h5_shell(pt)

    blueprint_text = _read_text(workspace / VISUAL_BLUEPRINT_FILE)
    plan_text = _read_text(workspace / PLAN_FILE)
    spec_text = _read_text(workspace / SPEC_FILE)

    lock_data: dict = {}
    lock_path = workspace / VISUAL_LOCK_FILE
    if lock_path.is_file():
        try:
            parsed = json.loads(lock_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                lock_data = parsed
        except json.JSONDecodeError:
            pass

    blueprint_ids = {
        normalize_component_id(i) for i in extract_selection_ids_from_blueprint(blueprint_text)
    }
    lock_ids = {
        normalize_component_id(i) for i in extract_selection_ids_from_visual_lock(lock_data)
    }
    override_ids = {
        normalize_component_id(i)
        for i in extract_override_ids_from_blueprint(blueprint_text)
    }
    plan_ids = {
        normalize_component_id(i) for i in extract_selection_ids_from_plan(plan_text)
    }

    issues: list[str] = []
    issues.extend(
        _verify_selection_id_consistency(blueprint_ids, lock_ids, override_ids, plan_ids)
    )

    signals = detect_feature_signals(
        spec_text, register, pack_type=pt, visual_text=blueprint_text
    )
    issues.extend(verify_required_components(blueprint_ids, signals, pack_type=pt))

    issues.extend(_verify_screen_coverage(spec_text, blueprint_text, strict=level >= 2))
    issues.extend(_verify_screens_column(blueprint_text, strict=level >= 3))

    override_tokens = extract_tokens_from_overrides(blueprint_text)
    lock_tokens = _collect_visual_lock_tokens(lock_data)
    issues.extend(_verify_override_tokens_resolved(override_tokens, lock_tokens))

    if h5 and lock_data:
        from batch.component_kit_index import resolve_baseline_reference

        paths = resolve_baseline_reference(lock_data.get("baselineReference"))
        if not paths["h5"]:
            issues.append("[SEL-H5] 本包视觉锁.json baselineReference 须含 h5 路径（h5_shell）")

    return issues
