"""Map CSV architecture / programming style into workspace code combo JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from batch.architecture_folders import merge_architecture_folders_into_combo
from batch.programming_layout import build_programming_layout_prompt_block
from batch.csv_naming import apply_naming_rule_to_combo
from batch.csv_tasks import (
    CsvTaskRow,
    normalize_architecture_pattern,
    normalize_state_management,
    architecture_pattern_key,
    state_management_key,
)
from batch.pack_type import is_native_ios_runtime

COMBO_FILE = "本包代码组合.json"


@dataclass(frozen=True)
class ArchitectureSpec:
    """Two independent CSV dimensions: state management and architecture pattern."""

    state_management: str
    architecture_pattern: str
    state_label: str
    pattern_label: str


def parse_architecture_from_csv(
    state_raw: str,
    pattern_raw: str,
) -> ArchitectureSpec:
    """Parse 状态管理 and 架构模式 as separate dimensions."""
    state_label = normalize_state_management(state_raw)
    pattern_label = normalize_architecture_pattern(pattern_raw)
    if not state_label or not pattern_label:
        raise ValueError(
            f"无法解析: 状态管理={state_raw!r}, 架构模式={pattern_raw!r}"
        )

    state_key = state_management_key(state_label)
    pattern_key = architecture_pattern_key(pattern_label)
    if not state_key or not pattern_key:
        raise ValueError(
            f"无法解析: 状态管理={state_raw!r}, 架构模式={pattern_raw!r}"
        )

    return ArchitectureSpec(
        state_management=state_key,
        architecture_pattern=pattern_key,
        state_label=state_label,
        pattern_label=pattern_label,
    )


def apply_csv_to_code_combo(
    workspace: Path,
    row: CsvTaskRow,
    *,
    registry_path: Path | None = None,
    batch_id: str = "",
) -> Path:
    """Merge CSV architecture/style/naming into 本包代码组合.json after alloc."""
    combo_path = workspace / COMBO_FILE
    if not combo_path.is_file():
        raise FileNotFoundError(
            f"缺少 {COMBO_FILE}，请先运行 alloc_code_combo: {combo_path}"
        )

    spec = parse_architecture_from_csv(row.state_management, row.architecture_pattern)
    try:
        data = json.loads(combo_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{COMBO_FILE} JSON 无效: {combo_path}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{COMBO_FILE} 必须是 JSON 对象: {combo_path}")

    data["programmingStyle"] = row.programming_style
    data["stateManagement"] = spec.state_management
    data["architecturePattern"] = spec.architecture_pattern
    data["csvStateManagement"] = spec.state_label
    data["csvArchitecturePattern"] = spec.pattern_label
    data.pop("architectureMode", None)

    apply_naming_rule_to_combo(
        workspace,
        row,
        data,
        registry_path=registry_path,
        batch_id=batch_id,
    )
    from batch.dimension_lock import locked_architecture_folders, locked_code_prefix

    lock_prefix = locked_code_prefix(workspace)
    combo_prefix = str(data.get("dartCodePrefix") or "").strip()
    lock_folders = locked_architecture_folders(workspace)
    if lock_prefix and lock_prefix == combo_prefix and lock_folders:
        data["architectureFolders"] = lock_folders
    else:
        merge_architecture_folders_into_combo(
            data,
            workspace=workspace,
            app_name=row.name,
            pattern_key=spec.architecture_pattern,
            naming_rule_label=row.naming_obfuscation_rule,
        )

    combo_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return combo_path


_STATE_PACKAGE_HINTS: dict[str, str] = {
    "getx": "get (GetX)",
    "setstate": "built-in StatefulWidget + setState only",
    "bloc": "flutter_bloc",
    "provider": "provider",
    "mobx": "flutter_mobx + mobx",
    "redux": "flutter_redux + redux",
}

_PATTERN_IMPLEMENTATION_HINTS: dict[str, str] = {
    "mvc": (
        "MVC — Model / View / Controller; role folders are opaque names in "
        "architectureFolders (NOT {prefix}_models/ etc.)"
    ),
    "mvp": (
        "MVP — Model / View / Presenter; use architectureFolders paths only"
    ),
    "mvvm": (
        "MVVM — Model / View / ViewModel; use architectureFolders paths only"
    ),
    "viper": (
        "VIPER — View / Interactor / Presenter / Entity / Router; "
        "use architectureFolders paths only"
    ),
    "simple_mv": (
        "简单 MV — View + Model only; use architectureFolders paths only; "
        "NO dedicated presenter/viewmodel/controller layer folders"
    ),
}


def build_architecture_prompt_block(row: CsvTaskRow) -> str:
    """Build Agent instruction block for two independent CSV architecture axes."""
    spec = parse_architecture_from_csv(row.state_management, row.architecture_pattern)
    pkg = _STATE_PACKAGE_HINTS.get(spec.state_management, spec.state_management)
    layout = _PATTERN_IMPLEMENTATION_HINTS.get(
        spec.architecture_pattern,
        spec.pattern_label,
    )
    return (
        "\n[CSV Architecture — REQUIRED]\n"
        "状态管理 and 架构模式 are TWO INDEPENDENT dimensions from CSV. "
        "Do NOT merge them into one nested label or treat one as a subtype of the other.\n"
        f"- stateManagement (CSV 状态管理): {spec.state_label} → "
        f"internal key `{spec.state_management}`, use {pkg}\n"
        f"- architecturePattern (CSV 架构模式): {spec.pattern_label} → "
        f"internal key `{spec.architecture_pattern}`; {layout}\n"
        "- Read 状态管理矩阵.md and 架构模式矩阵.md: "
        "state rules and folder layout apply separately per dimension.\n"
        "- architecturePattern and stateManagement (from CSV) are AUTHORITATIVE "
        "for code structure and state; the combo `architecture` / `folderStyle` "
        "keys are anti-correlation tags only — do NOT treat them as a second, "
        "conflicting structural directive.\n"
        f"- Do NOT default to setState unless CSV 状态管理 is SetState.\n"
        "- Add required pubspec dependencies for the chosen state package.\n"
        "- Document both dimensions in 功能文档.md Code layout section.\n"
    )


def build_programming_style_prompt_block(
    row: CsvTaskRow,
    *,
    prefix: str = "",
) -> str:
    """Build Agent instruction block for CSV programming persona."""
    layout_block = build_programming_layout_prompt_block(row, prefix=prefix)
    if is_native_ios_runtime(row.pack_type):
        return (
            "\n[CSV Programming Style — Native implementation (dims 2–5) — REQUIRED]\n"
            f"- programmingStyle (from CSV 编程风格): {row.programming_style}\n"
            "- Read 编程人设风格.md; locate the row for this persona.\n"
            "- Apply dims 2–5 to every Swift/OC shell source file:\n"
            "  2) Style / let-var / access  3) Syntax & iteration\n"
            "  4) Control flow & async  5) Method split & optional handling\n"
            "- dim-1 Widget split: N/A for native — ignore.\n"
            "- dims 6–7 (libLayout / assetLayout): H5 vault & Flutter layout only;\n"
            "  native directory names follow architectureFolders + naming rule.\n"
            "- Persona dims 2–5 MUST change control-flow/async/method shape — not only folders.\n"
            "- Persona MUST NOT override bridgeDeckSelections mechanisms (see 编程人设风格.md).\n"
            "- Flutter-only lock fields (dartPackageName, stateManagement, skinBucket) are non-binding.\n"
            f"{layout_block}"
        )
    return (
        "\n[CSV Programming Style — REQUIRED]\n"
        f"- programmingStyle (from CSV 编程风格): {row.programming_style}\n"
        "- Read 编程人设风格.md; locate the row for this persona.\n"
        "- Apply ALL 7 matrix cells for that row to every `.dart` file:\n"
        "  1) Widget split & nesting  2) Style / const / final\n"
        "  3) Syntax sugar & iteration  4) Control flow & async\n"
        "  5) Method split & null safety\n"
        "  6) Lib directory topology (libLayout)  7) Asset roots & naming\n"
        "- The 7 cells are MANDATORY and override your defaults.\n"
        "- Dims 6–7 are enforced via 本包维度锁.json + 本包资源布局.json.\n"
        "- Persona affects coding style and tree shape — NOT feature scope.\n"
        f"{layout_block}"
    )


_NATIVE_PATTERN_ROLES: dict[str, str] = {
    "mvc": (
        "MVC — Model (data) / View (UIView/UIViewController UI) / "
        "Controller (mediates view and model); keep controllers thin."
    ),
    "mvp": (
        "MVP — Model / View (passive, forwards user events) / "
        "Presenter (holds presentation logic, updates the view via a protocol)."
    ),
    "mvvm": (
        "MVVM — Model / View / ViewModel (exposes bindable state; "
        "the view observes the view model, no business logic in the view)."
    ),
    "viper": (
        "VIPER — View / Interactor (business logic) / Presenter / "
        "Entity (models) / Router (navigation); one module per feature."
    ),
    "simple_mv": (
        "简单 MV — View + Model only; no dedicated presenter/viewmodel/"
        "controller layer; keep logic minimal and inline."
    ),
}


def build_native_architecture_prompt_block(row: CsvTaskRow) -> str:
    """Build Agent instruction block for CSV 架构模式 in native Swift/OC apps."""
    label = normalize_architecture_pattern(row.architecture_pattern)
    key = architecture_pattern_key(label)
    if not label or not key:
        return ""
    roles = _NATIVE_PATTERN_ROLES.get(key, label)
    return (
        "\n[CSV Architecture Pattern — REQUIRED]\n"
        f"- architecturePattern (CSV 架构模式): {label} → internal key `{key}`.\n"
        f"- {roles}\n"
        "- Read 架构模式矩阵.md for role definitions; map the "
        "layer roles to native Swift/Objective-C constructs (the Dart folder "
        "layout there is illustrative only).\n"
        "- State management packages do NOT apply to native code.\n"
    )
