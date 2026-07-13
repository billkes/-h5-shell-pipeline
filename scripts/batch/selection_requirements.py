"""Feature signals → required §Component Selection ids for Plan gate."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet

from batch.pack_type import is_h5_shell
from batch.screen_inventory import parse_h5_routes

_LIST_CONTAINER_IDS: tuple[str, ...] = (
    "data_display/list_view",
    "data_display/masonry_grid",
    "data_display/grid_view",
)

_FEEDBACK_IDS: tuple[str, ...] = (
    "primitives/snackbar",
    "feedback/empty_state",
    "feedback/error_state",
    "feedback/loading_spinner",
)


@dataclass(frozen=True)
class RequiredComponentRule:
    signal: str
    required_ids: tuple[str, ...]
    pack_types: FrozenSet[str] | None  # None = all pack types
    message: str


REQUIRED_COMPONENT_RULES: tuple[RequiredComponentRule, ...] = (
    RequiredComponentRule(
        signal="export_flow",
        required_ids=("patterns/export_card_builder",),
        pack_types=None,
        message="功能文档含 Export/Save Flow，须选 patterns/export_card_builder",
    ),
    RequiredComponentRule(
        signal="iap_store",
        required_ids=("patterns/gem_store_layout",),
        pack_types=None,
        message="功能文档含 IAP/Coin Store，须选 patterns/gem_store_layout",
    ),
    RequiredComponentRule(
        signal="welcome_gate",
        required_ids=("patterns/welcome_gate", "primitives/checkbox"),
        pack_types=None,
        message="Screen Inventory 含 #/welcome，须选 patterns/welcome_gate + primitives/checkbox",
    ),
    RequiredComponentRule(
        signal="list_screens",
        required_ids=("data_display/list_row",),
        pack_types=None,
        message="Screen Inventory 含列表/Feed/History，须选 data_display/list_row",
    ),
    RequiredComponentRule(
        signal="filter_chip",
        required_ids=("primitives/chip", "patterns/filter_panel"),
        pack_types=None,
        message="含 Filter/Tag/Chip，须选 primitives/chip 或 patterns/filter_panel（至少其一）",
    ),
    RequiredComponentRule(
        signal="form_input",
        required_ids=("primitives/input",),
        pack_types=frozenset({"tool_flutter", "h5_shell"}),
        message="含表单/录入，须选 primitives/input",
    ),
    RequiredComponentRule(
        signal="overlay_feedback",
        required_ids=_FEEDBACK_IDS,
        pack_types=None,
        message="Overlay & Feedback 须对应 primitives/snackbar 或 feedback/* 组件（至少其一）",
    ),
    RequiredComponentRule(
        signal="h5_shell_infra",
        required_ids=(
            "shell/webview_host",
            "shell/launch_veil",
            "shell/bridge_toast",
        ),
        pack_types=frozenset({"h5_shell"}),
        message=(
            "h5_shell 须选 shell/webview_host、shell/launch_veil、shell/bridge_toast"
        ),
    ),
    RequiredComponentRule(
        signal="h5_legal_modal",
        required_ids=("shell/legal_modal",),
        pack_types=frozenset({"h5_shell"}),
        message="Screen Inventory 含 #/legal，须选 shell/legal_modal",
    ),
    RequiredComponentRule(
        signal="h5_plaza",
        required_ids=("shell/bridge_plaza",),
        pack_types=frozenset({"h5_shell"}),
        message="Screen Inventory 含 #/plaza，须选 shell/bridge_plaza",
    ),
    RequiredComponentRule(
        signal="h5_pick_image",
        required_ids=("data_display/media_picker",),
        pack_types=frozenset({"h5_shell"}),
        message="bridgeCapabilities 含 pickImage，须选 data_display/media_picker",
    ),
)

_EXCLUDED_SCREEN_IDS: frozenset[str] = frozenset(
    {
        "launchscreen",
        "launch_screen",
        "ios_launch",
        "native_launch",
    }
)


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


def detect_feature_signals(
    spec_text: str,
    register: dict,
    *,
    pack_type: str,
    visual_text: str = "",
) -> set[str]:
    """Return active feature signal keys for required-component rules."""
    text = spec_text.lower()
    signals: set[str] = set()

    if re.search(r"export\s*/\s*save\s+flow|save\s+flow|export\s+flow", spec_text, re.I):
        signals.add("export_flow")
    if re.search(
        r"iap\s+catalog|coin\s+store|in-app\s+purchase|gem\s+store|purchase\s+bridge",
        spec_text,
        re.I,
    ):
        signals.add("iap_store")

    routes = parse_h5_routes(spec_text)
    if "/welcome" in routes:
        signals.add("welcome_gate")
    if "/legal" in routes:
        signals.add("h5_legal_modal")
    if "/plaza" in routes:
        signals.add("h5_plaza")

    if re.search(
        r"screen inventory|^\s*\|.*\|\s*list|history|feed|archive|saved\s+items",
        spec_text,
        re.I | re.M,
    ):
        signals.add("list_screens")

    if re.search(r"filter|chip|tag\s+canon|style\s+chip", spec_text, re.I):
        signals.add("filter_chip")

    if re.search(
        r"textfield|form\s+field|录入|textarea|quick\s+entry",
        spec_text,
        re.I,
    ):
        signals.add("form_input")

    feedback = visual_text
    if feedback and re.search(r"overlay\s*&\s*feedback", feedback, re.I):
        rows = re.findall(r"^\s*\|[^|]+\|", feedback, re.M)
        if len(rows) >= 3:
            signals.add("overlay_feedback")

    if is_h5_shell(pack_type):
        signals.add("h5_shell_infra")
        caps = register.get("bridgeCapabilities") or []
        if isinstance(caps, list):
            cap_text = " ".join(str(c).lower() for c in caps)
            if "pickimage" in cap_text or "pick_image" in cap_text:
                signals.add("h5_pick_image")

    return signals


def verify_required_components(
    selection_ids: set[str],
    signals: set[str],
    *,
    pack_type: str,
) -> list[str]:
    """Return issues for missing required components given active signals."""
    issues: list[str] = []
    for rule in REQUIRED_COMPONENT_RULES:
        if rule.signal not in signals:
            continue
        if rule.pack_types is not None and not _rule_applies_to_pack(rule, pack_type):
            continue
        if rule.signal == "filter_chip":
            if not any(rid in selection_ids for rid in rule.required_ids):
                issues.append(f"[SEL-REQ] {rule.message}")
            continue
        if rule.signal == "overlay_feedback":
            if not any(rid in selection_ids for rid in rule.required_ids):
                issues.append(f"[SEL-REQ] {rule.message}")
            continue
        if rule.signal == "list_screens":
            missing = [rid for rid in rule.required_ids if rid not in selection_ids]
            if missing:
                issues.append(f"[SEL-REQ] {rule.message}")
            if not any(rid in selection_ids for rid in _LIST_CONTAINER_IDS):
                issues.append(
                    "[SEL-REQ] Screen Inventory 含列表屏，须另选 list_view、masonry_grid 或 grid_view 之一"
                )
            continue
        missing = [rid for rid in rule.required_ids if rid not in selection_ids]
        if missing:
            issues.append(f"[SEL-REQ] {rule.message}（缺: {', '.join(missing)}）")
    return issues


def _rule_applies_to_pack(rule: RequiredComponentRule, pack_type: str) -> bool:
    if rule.pack_types is None:
        return True
    if pack_type in rule.pack_types:
        return True
    return is_h5_shell(pack_type) and "h5_shell" in rule.pack_types


_DEFAULT_LIST_CONTAINER = "data_display/list_view"


def compute_required_selection_ids(
    signals: set[str],
    *,
    pack_type: str,
    existing: set[str] | None = None,
) -> set[str]:
    """Kit ids mandated by active feature signals (for prompt + sync)."""
    out: set[str] = set(existing or ())
    for rule in REQUIRED_COMPONENT_RULES:
        if rule.signal not in signals:
            continue
        if rule.pack_types is not None and not _rule_applies_to_pack(rule, pack_type):
            continue
        if rule.signal == "filter_chip":
            out.update(rule.required_ids)
            continue
        if rule.signal == "overlay_feedback":
            continue
        if rule.signal == "list_screens":
            out.update(rule.required_ids)
            if not any(rid in out for rid in _LIST_CONTAINER_IDS):
                out.add(_DEFAULT_LIST_CONTAINER)
            continue
        out.update(rule.required_ids)
    return out


def collect_required_selection_ids(
    workspace: Path,
    *,
    pack_type: str,
    existing: set[str] | None = None,
) -> set[str]:
    """Read workspace artifacts and return required + existing selection ids."""
    spec_path = workspace / "功能文档.md"
    spec_text = (
        spec_path.read_text(encoding="utf-8", errors="replace")
        if spec_path.is_file()
        else ""
    )
    blueprint_path = workspace / "视觉蓝图.md"
    visual_text = (
        blueprint_path.read_text(encoding="utf-8", errors="replace")
        if blueprint_path.is_file()
        else ""
    )
    register = _read_register(workspace)
    signals = detect_feature_signals(
        spec_text, register, pack_type=pack_type, visual_text=visual_text
    )
    return compute_required_selection_ids(
        signals, pack_type=pack_type, existing=existing
    )


def format_required_selection_block(
    workspace: Path,
    *,
    pack_type: str,
) -> str:
    """Prompt block listing kit ids Plan gate will require."""
    from batch.component_kit_index import (
        extract_selection_ids_from_visual_lock,
        normalize_component_id,
    )

    lock_path = workspace / "本包视觉锁.json"
    lock_ids: set[str] = set()
    if lock_path.is_file():
        try:
            data = json.loads(lock_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                lock_ids = {
                    normalize_component_id(i)
                    for i in extract_selection_ids_from_visual_lock(data)
                }
        except json.JSONDecodeError:
            pass
    required = collect_required_selection_ids(
        workspace, pack_type=pack_type, existing=lock_ids
    )
    missing = sorted(required - lock_ids)
    if not missing and not required:
        return ""
    lines = [
        "[Required §Component Selection — batch-enforced at plan.gate]",
        "MUST appear in 视觉蓝图 §Component Selection, 本包视觉锁.json "
        "componentSelection, §Package Token Overrides, and 产包计划 §2.x:",
    ]
    for cid in sorted(required):
        lines.append(f"- `{cid}`")
    if missing:
        lines.append(f"Currently missing from visual lock (add now): {', '.join(missing)}")
    return "\n".join(lines)


def parse_screen_inventory(spec_text: str) -> list[str]:
    """Extract screen ids/names from Screen Inventory table."""
    match = re.search(
        r"(?is)(?:^|\n)#+\s*.*screen\s+inventory.*?\n(.*?)(?:\n#+\s|\Z)",
        spec_text,
    )
    if not match:
        return []
    block = match.group(1)
    screen_ids: list[str] = []
    for line in block.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or re.match(r"^:?-+:?$", cells[0]):
            continue
        first = cells[0].lower()
        if first in ("screen", "name", "screen name", "屏", "屏幕"):
            continue
        raw = cells[0]
        sid = re.sub(r"[^a-zA-Z0-9_-]", "_", raw.strip()).lower().strip("_")
        if sid and sid not in _EXCLUDED_SCREEN_IDS:
            screen_ids.append(sid)
    return screen_ids
