"""Write per-package .cursor/rules/*.mdc into each generated project root.

The generated project root is the Cursor working directory used for later
manual maintenance (Flutter: the app workspace; native: the {AppName}
sub-directory). These rules pin the package's assigned dartCodePrefix,
state management, architecture pattern, programming persona and naming
obfuscation rule so that human edits via Cursor Agent stay consistent with
the anti-correlation scheme produced by the batch pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from batch.architecture_folders import (
    architecture_folders_from_lock,
    build_architecture_folder_prompt_block,
)
from batch.csv_architecture import (
    build_architecture_prompt_block,
    build_native_architecture_prompt_block,
    build_programming_style_prompt_block,
)
from batch.csv_prompt_blocks import dimension_boundary_block
from batch.dimension_lock import resolve_dimension_lock
from batch.csv_naming import build_naming_rule_prompt_block
from batch.csv_tasks import CsvTaskRow
from batch.pack_type import is_h5_shell

COMBO_FILE = "本包代码组合.json"
REGISTER_FILE = "本包登记信息.json"
VISUAL_LOCK_FILE = "本包视觉锁.json"
VISUAL_BLUEPRINT_FILE = "视觉蓝图.md"
RULES_SUBDIR = ".cursor/rules"


def _write_mdc(
    rules_dir: Path,
    filename: str,
    description: str,
    body: str,
    *,
    always_apply: bool = True,
    globs: str | None = None,
) -> None:
    rules_dir.mkdir(parents=True, exist_ok=True)
    front = f"---\ndescription: {description}\n"
    if globs:
        front += f"globs: {globs}\n"
    if always_apply:
        front += "alwaysApply: true\n"
    front += "---\n\n"
    text = front + body.strip() + "\n"
    (rules_dir / filename).write_text(text, encoding="utf-8")


def _read_combo(workspace: Path) -> dict[str, Any]:
    combo = workspace / COMBO_FILE
    if not combo.is_file():
        return {}
    try:
        data = json.loads(combo.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_register(workspace: Path) -> dict[str, Any]:
    path = workspace / REGISTER_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _is_h5_shell_workspace(workspace: Path, row: CsvTaskRow | None) -> bool:
    reg = _read_register(workspace)
    if is_h5_shell(str(reg.get("packType") or "")):
        return True
    if row is not None and is_h5_shell(row.pack_type):
        return True
    return False


def _read_visual_lock(workspace: Path) -> dict[str, Any]:
    path = workspace / VISUAL_LOCK_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_prefix(workspace: Path, combo: dict[str, Any]) -> str:
    prefix = (combo.get("dartCodePrefix") or "").strip()
    if prefix:
        return prefix
    reg = _read_register(workspace)
    anti = reg.get("codeAntiCorrelation") or {}
    if isinstance(anti, dict):
        return str(anti.get("dartCodePrefix") or "").strip()
    return ""


def _resolve_vault_dir(workspace: Path, combo: dict[str, Any]) -> str:
    reg = _read_register(workspace)
    vault_dir = str(reg.get("bundleVaultDir") or "").strip()
    if vault_dir:
        return vault_dir
    prefix = _resolve_prefix(workspace, combo)
    if prefix:
        return f"assets/{prefix}_vault/"
    return "assets/**/*_vault/"


def _component_selection_lines(workspace: Path, lock: dict[str, Any]) -> list[str]:
    from batch.component_kit_index import (
        extract_selection_ids_from_blueprint,
        parse_lock_component_entry,
    )

    selection = lock.get("componentSelection") or []
    lines: list[str] = []
    if isinstance(selection, list):
        for item in selection:
            if isinstance(item, dict):
                cid = str(item.get("id") or "").strip()
                cat = str(item.get("category") or "").strip()
                variants = item.get("variants") or []
                if not cid or not cat:
                    parsed = parse_lock_component_entry(item)
                    if parsed:
                        lines.append(f"- {parsed}")
                    continue
                variant_text = ""
                if isinstance(variants, list) and variants:
                    variant_text = f" ({', '.join(str(v) for v in variants)})"
                lines.append(f"- {cat}/{cid}{variant_text}")
            else:
                parsed = parse_lock_component_entry(item)
                if parsed:
                    lines.append(f"- {parsed}")
    if lines:
        return lines

    blueprint = workspace / VISUAL_BLUEPRINT_FILE
    if blueprint.is_file():
        for cid in extract_selection_ids_from_blueprint(
            blueprint.read_text(encoding="utf-8", errors="replace")
        ):
            lines.append(f"- {cid}")
    if not lines:
        lines.append("- （产包后从 视觉蓝图.md §Component Selection 补全）")
    return lines


def _component_kit_body(workspace: Path, combo: dict[str, Any], *, h5_shell: bool) -> str:
    from batch.component_kit_index import resolve_baseline_reference

    lock = _read_visual_lock(workspace)
    paths = resolve_baseline_reference(lock.get("baselineReference"))
    if h5_shell:
        baseline_path = (
            paths["h5"] or "data/static/component_kit/baseline.md#h5"
        )
        platform = "§H5"
    else:
        baseline_path = (
            paths["flutter"] or "data/static/component_kit/baseline.md#flutter"
        )
        platform = "§Flutter"

    selection_lines = _component_selection_lines(workspace, lock)
    return "\n".join(
        [
            "# 本包 Component Kit 铁律（iron-5）",
            "",
            "## 权威来源",
            f"- `data/static/component_kit/`（已复制到本 workspace）",
            f"- `{VISUAL_BLUEPRINT_FILE}` §Component Selection + §Package Token Overrides",
            f"- `{VISUAL_LOCK_FILE}` → componentSelection, baselineReference",
            "",
            "## 实现顺序（MUST）",
            f"0. `component_kit/baseline.md` {platform}（{baseline_path}）",
            "1. §Component Selection 所列 id — 逐个读 `{category}/{id}.md`",
            "2. 屏幕级布局（视觉蓝图 §Per-screen Layout 之后）",
            "",
            "## 禁止",
            "- Selection 外自造共享 UI 组件",
            "",
            "## Plan Gate（SEL 规则摘要）",
            "- 蓝图 Selection = 视觉锁 componentSelection = Overrides",
            "- 功能场景必选组件见 selection_requirements.py（Export/IAP/Welcome/列表/h5 shell）",
            "- Overrides typography/color token 须在 本包视觉锁 中定义",
            "- 未读 kit md 即手写 Material 默认 Button / TextField / Chip / SnackBar",
            "- 用 Selection 替代 Export Card / IAP Store / Welcome Gate 场景规格（仍看视觉蓝图 V2 章节）",
            "",
            "## 本包入选组件",
            *selection_lines,
        ]
    )


def _visual_canon_body(lock: dict[str, Any]) -> str:
    overlay = lock.get("overlayTokens") or {}
    form = lock.get("formFieldSpec") or {}
    export_cards = lock.get("exportCards") or []
    welcome = lock.get("welcomeSpec") or {}
    list_row = lock.get("listRowSpec") or {}
    chip = lock.get("chipSpec") or {}

    lines = [
        "# 本包视觉 Canon 铁律（iron-6）",
        "",
        "视觉蓝图 V2 深度章节在代码中的落地约束。详规见 `视觉蓝图.md` + `本包视觉锁.json`。",
        "",
        "## Overlay & Feedback",
        "- **禁止**裸 `SnackBar(content: Text(...))` — 用 kit snackbar + overlayTokens",
    ]
    if isinstance(overlay, dict) and overlay:
        lines.append(f"- overlayTokens keys: {', '.join(sorted(overlay.keys()))}")

    lines += [
        "",
        "## Form & Input Canon",
    ]
    if isinstance(form, dict) and form.get("hintUsesSameToken"):
        token = form.get("textStyleToken") or "bodyMedium"
        lines.append(
            f"- TextField `hintStyle` 与 `style` **必须**共用 typography token `{token}`"
        )
    else:
        lines.append("- formFieldSpec.hintUsesSameToken 须为 true（见视觉锁）")

    lines += [
        "",
        "## Export Card",
        "- 单 WYSIWYG builder：预览 FittedBox 仅缩放，禁止 preview/export 双套布局",
    ]
    if isinstance(export_cards, list) and export_cards:
        ids = [
            str(c.get("id") or f"card{i}")
            for i, c in enumerate(export_cards)
            if isinstance(c, dict)
        ]
        lines.append(f"- exportCards: {', '.join(ids)}")

    lines += [
        "",
        "## IAP Store Layout",
        "- 禁纯 ListTile 商店；须有 balance hero + grid/promo（见视觉蓝图 IAP Store Layout Canon）",
        "",
        "## Welcome Gate",
    ]
    if isinstance(welcome, dict) and welcome.get("layoutVariant"):
        lines.append(f"- welcomeSpec.layoutVariant = `{welcome.get('layoutVariant')}`")
    else:
        lines.append("- 按视觉蓝图 Welcome Gate Canon + welcomeSpec 实现")

    lines += ["", "## List / Chip"]
    if isinstance(list_row, dict) and list_row.get("minHeight"):
        lines.append(f"- listRowSpec.minHeight = {list_row.get('minHeight')}pt")
    if isinstance(chip, dict) and chip:
        lines.append("- chipSpec 对比度与选中态须匹配视觉蓝图 Tag & Filter Chip Canon")

    return "\n".join(lines)


def _h5_deflavor_body(prefix: str, vault_dir: str) -> str:
    p = prefix or "{prefix}"
    vault = vault_dir or f"assets/{p}_vault/"
    return f"""# h5_shell 去风味铁律（iron-7）

本包 H5 vault：`{vault}`。全局 L0 reset 与美化禁区 — **产包后改 CSS/JS 仍须遵守**。
详规：《H5去风味规范.md》· `component_kit/baseline.md` §H5 · brain `h5-deflavor-interaction-pitfalls`。

## L0 Baseline 不可删（美化只能改色值，不能删选择器）

| 项 | 规则 |
|----|------|
| tap-highlight | `-webkit-tap-highlight-color: transparent` |
| scrollbar | 全局 `::-webkit-scrollbar {{ display: none }}` |
| user-select | 非 input/textarea 禁用选区与放大镜 |
| checkbox/radio | **排除** `appearance: none`（Welcome 门闸可见） |
| safe-area | `:root` 声明 `--safe-*: env(safe-area-inset-*)` |
| viewport | `viewport-fit=cover` |

## 组件与标签

- 禁裸 styled `button` / `input` / `a`（须 `c-{p}-*` kit 类）
- 禁 `<select>`、`<input type="file/color/date">`
- 禁 `alert` / `confirm` / `prompt`
- AppBar `position: fixed`，不随内容滚动
- 顶栏/底栏/`.page-shell` / `.page-stack` 使用 **LAYOUT:pipeline**（仅 inset + fixed 几何；**不含** stack 内页视觉样式）

## 交互 pitfalls

- `blockFastDoubleTap` **仅 touchend**，禁 touchstart
- panel / 列表行禁 `stopPropagation` 挡点击
- 输入 `spellcheck="false"`；键盘后滚入可见区
- IAP 列表须 scroll-aware tap guard

## 美化禁区（防回归）

- **禁止** `::-webkit-scrollbar {{ display: block }}` 或 `scrollbar-thumb`（任意选择器）
- **禁止** 在组件 CSS 覆盖 baseline reset 核心项
- Legal 滚动暗示：仅 mask 渐变（见 `h5-vault-compliance.mdc`）

## 自检

- `verify_h5_deflavor_baseline()` PASS
- `verify_h5_legal_ui()` PASS（Legal 滚动专项）
"""


def _h5_vault_compliance_body(prefix: str, vault_dir: str) -> str:
    p = prefix or "{prefix}"
    vault = vault_dir or f"assets/{p}_vault/"
    return f"""# h5_shell Vault 合规铁律（Legal · 协议 sync · Overlay stack）

本包为 **h5_shell**（flutter / swift / oc runtime）：可见 UI 在 `{vault}`，壳层仅 WebView + Bridge。
**全局去风味 L0** 见 `h5-deflavor.mdc`（iron-7），本条只管 Legal 与 overlay 专项。

## Legal 内容（audit-5b）

- 协议唯一源：`{{App}} Privacy Agreement.md` / `{{App}} User Agreement.md`
- 流水线 / 改 MD 后运行 `sync_h5_legal_bundled.py` → `{p}_panels/{p}_legal_bundled.js`
- `{p}_entry.htm` 须在 `{p}_core.js` **之前** load bundled script
- **禁止**在 `{p}_core.js` 手写 `NS.ui.LEGAL` 或摘要字符串

## Legal UI（audit-5c · Agent-owned visual）

- 必读：`docs/H5壳Legal弹层规范.md`（**无代码 kit**；视觉跟本包设计系统）
- **必须** `formatLegalBody`（或等价）+ 可识别的 header / title / scroll 区域
- **禁止** `LEGAL[doc].replace(/\\n/g, '<br>')` 单 div 文字墙
- Close ≥ 44×44；滚动区隐藏系统滚动条 + 有滚动暗示

## Overlay 路由（audit-5d · hash overlay stack）

- 必读：`H5壳Overlay路由规范.md` · kit：`data/static/h5_overlay_router_kit/`
- `#/legal`、filter/bottom-sheet 等 hash overlay：**必须** `render(base) + render(overlay)` 叠加来源页
- **禁止** `dispatch` 仅 `innerHTML = render(overlayPath)`（遮罩会呈不透明灰屏）
- 确认框 / IAP barrier 可走 `document.body` portal，不必 hash 路由

## Legal 滚动（专项）

- Legal 滚动暗示 **仅** 允许：`mask-image` 底部渐变 + `scrollbar-width: none` + `::-webkit-scrollbar {{ display: none }}`
- **禁止** Legal 区 `::-webkit-scrollbar {{ display: block }}` 或 `scrollbar-thumb`

## 自检

- `verify_h5_legal_bundled()` PASS
- `verify_h5_legal_ui()` PASS
- `verify_h5_overlay_stack()` PASS（有 `#/legal` / filter sheet 等 hash overlay 时）
"""


def _write_h5_vault_compliance_rule(
    rules_dir: Path,
    workspace: Path,
    combo: dict[str, Any],
) -> None:
    prefix = _resolve_prefix(workspace, combo)
    vault_dir = _resolve_vault_dir(workspace, combo)
    glob_vault = vault_dir.rstrip("/") + "/**" if not vault_dir.endswith("/**") else vault_dir
    _write_mdc(
        rules_dir,
        "h5-vault-compliance.mdc",
        "h5_shell vault 合规 — Legal kit、协议 sync、overlay stack",
        _h5_vault_compliance_body(prefix, vault_dir),
        always_apply=True,
        globs=f"{glob_vault},**/*_legal_bundled.js,**/*_render.js,**/*_baseline.css",
    )


def _write_h5_deflavor_rule(
    rules_dir: Path,
    workspace: Path,
    combo: dict[str, Any],
) -> None:
    prefix = _resolve_prefix(workspace, combo)
    vault_dir = _resolve_vault_dir(workspace, combo)
    glob_vault = vault_dir.rstrip("/") + "/**" if not vault_dir.endswith("/**") else vault_dir
    _write_mdc(
        rules_dir,
        "h5-deflavor.mdc",
        "h5_shell 去风味铁律 — L0 baseline + 美化禁区（iron-7）",
        _h5_deflavor_body(prefix, vault_dir),
        always_apply=True,
        globs=(
            f"{glob_vault},**/*_baseline.css,**/*_primitives.css,"
            "**/*_composites.css,**/*_render*.js,**/*_entry.htm,**/*_core.js"
        ),
    )


def _write_component_kit_rule(
    rules_dir: Path,
    workspace: Path,
    combo: dict[str, Any],
    *,
    h5_shell: bool,
) -> None:
    globs = (
        "lib/**,data/static/component_kit/**,"
        f"{VISUAL_BLUEPRINT_FILE},{VISUAL_LOCK_FILE}"
    )
    _write_mdc(
        rules_dir,
        "component-kit.mdc",
        "本包 Component Kit 铁律 — baseline → Selection → 逐 id md（iron-5）",
        _component_kit_body(workspace, combo, h5_shell=h5_shell),
        always_apply=True,
        globs=globs,
    )


def _write_visual_canon_rule(rules_dir: Path, workspace: Path) -> None:
    lock = _read_visual_lock(workspace)
    _write_mdc(
        rules_dir,
        "visual-canon.mdc",
        "本包视觉 Canon 铁律 — V2 深度章节代码落地（iron-6）",
        _visual_canon_body(lock),
        always_apply=True,
        globs=f"lib/**,{VISUAL_LOCK_FILE},{VISUAL_BLUEPRINT_FILE}",
    )


def _naming_structure_body(combo: dict[str, Any], row: CsvTaskRow | None) -> str:
    prefix = (combo.get("dartCodePrefix") or "").strip()
    lines = ["# 本包命名与目录结构约束（按包定制，请严格遵守）", ""]
    if prefix:
        lines.append(f"- `dartCodePrefix` = `{prefix}`（权威值，见 `{COMBO_FILE}`）。")
    else:
        lines.append(f"- `dartCodePrefix` 见 `{COMBO_FILE}`，禁止另造前缀。")
    lines += [
        "- 业务根目录为 `lib/{dartCodePrefix}_{pubspec_name}/`，"
        "精确取值见 `主题代码布局.txt`（`LIB_ROOT_FOLDER`）；`lib/` 下仅保留 `main.dart`。",
        "- 业务根下须有 **≥2 个 `{dartCodePrefix}_主题词` 子目录** 分类源码，禁止单层平铺。",
        "- 禁止通用目录名与文件名片段（`_screen` / `_models` / `_service` 等），"
        "完整清单见 `主题代码布局.txt`（`FORBIDDEN_*`）。",
        "- 完整差异化约定见 `Flutter差异化开发规则.md`。",
    ]
    naming_block = build_naming_rule_prompt_block(row) if row is not None else ""
    if naming_block.strip():
        lines += ["", naming_block.strip()]
    return "\n".join(lines)


def write_flutter_cursor_rules(workspace: Path, row: CsvTaskRow | None) -> None:
    """Write Flutter per-package rules into <workspace>/.cursor/rules/.

    tool_flutter / contentpack / videostream: 6 mdc (iron-1..6).
    h5_shell: 7 mdc (iron-1..5 + vault-compliance + iron-7 deflavor).
    """
    rules_dir = workspace / RULES_SUBDIR
    combo = _read_combo(workspace)
    h5_shell = _is_h5_shell_workspace(workspace, row)

    _write_mdc(
        rules_dir,
        "package-naming-and-structure.mdc",
        "本包命名与目录结构约束（dartCodePrefix / 命名混淆规则）",
        _naming_structure_body(combo, row),
    )

    _write_mdc(
        rules_dir,
        "dimension-boundary.mdc",
        "四维度边界与冲突 tie-break 顺序",
        "# 四维度边界（命名 > 架构 > 状态 > 编程风格）\n\n"
        + dimension_boundary_block().strip(),
    )

    if row is not None:
        try:
            arch_block = build_architecture_prompt_block(row)
        except ValueError:
            arch_block = ""
        lock = resolve_dimension_lock(workspace)
        if lock:
            folder_block = build_architecture_folder_prompt_block(
                architecture_folders_from_lock(lock)
            )
            if folder_block.strip():
                arch_block = arch_block + folder_block
        if arch_block.strip():
            _write_mdc(
                rules_dir,
                "architecture.mdc",
                "本包架构约束（状态管理 + 架构模式，两个正交维度）",
                "# 本包架构约束（按包定制，请严格遵守）\n\n" + arch_block.strip(),
            )

        style_block = build_programming_style_prompt_block(
            row,
            prefix=(combo.get("dartCodePrefix") or "").strip(),
        )
        if style_block.strip():
            _write_mdc(
                rules_dir,
                "programming-style.mdc",
                "本包编程风格 persona 约束",
                "# 本包编程风格约束（按包定制，请严格遵守）\n\n" + style_block.strip(),
            )

    _write_component_kit_rule(rules_dir, workspace, combo, h5_shell=h5_shell)

    if h5_shell:
        _write_h5_vault_compliance_rule(rules_dir, workspace, combo)
        _write_h5_deflavor_rule(rules_dir, workspace, combo)
    else:
        _write_visual_canon_rule(rules_dir, workspace)


def write_native_cursor_rules(
    workspace: Path,
    row: CsvTaskRow | None,
    language: str,
) -> None:
    """Write native (Swift/Objective-C) per-package rules into .cursor/rules/.

    Native apps only carry an architecture pattern and a programming
    persona; state management and dartCodePrefix do not apply.
    """
    if row is None:
        return
    rules_dir = workspace / RULES_SUBDIR

    arch_block = build_native_architecture_prompt_block(row)
    if arch_block.strip():
        _write_mdc(
            rules_dir,
            "architecture.mdc",
            f"本包架构约束（{language} 架构模式）",
            f"# 本包架构约束（{language}，按包定制，请严格遵守）\n\n"
            + arch_block.strip(),
        )

    style_block = build_programming_style_prompt_block(row, prefix="")
    if style_block.strip():
        _write_mdc(
            rules_dir,
            "programming-style.mdc",
            "本包编程风格 persona 约束",
            "# 本包编程风格约束（按包定制，请严格遵守）\n\n" + style_block.strip(),
        )

    from batch.native_shell_naming import build_native_shell_naming_prompt_block

    naming_block = build_native_shell_naming_prompt_block(row, prefix="")
    if naming_block.strip() and language.lower() == "swift":
        _write_mdc(
            rules_dir,
            "native-shell-naming.mdc",
            "本包 Native 壳目录命名约束",
            "# 本包 Native 壳目录命名（按包定制，请严格遵守）\n\n" + naming_block.strip(),
        )
