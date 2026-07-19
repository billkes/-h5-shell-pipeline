"""Load prompt templates from ``prompts/flutter/``.

Pipeline V3 (default):

* ``phase_build_agent_*.txt`` + ``phase_pm_ui_plan.txt`` — Build Agent 子步
* ``phase_programmer.txt`` / ``phase_h5_*`` — 实现
* ``phase9_asset_generator.txt`` — 独立 ``batch generate-assets`` 命令

Pipeline V2 (``--legacy-pipeline``):

* ``phase1_pm.txt`` / ``phase1_pm_tool.txt`` — PM 功能蓝图
* ``phase2_designer.txt`` — 设计师视觉蓝图
* ``phase_programmer.txt`` — 程序员实现
* ``phase7_tester.txt`` — 测试员 (Main Tool Flow)
"""

from __future__ import annotations

from pathlib import Path

from batch.config import BatchConfig

_PM_BRAIN_FOCUS = """   - `01_tech_common/A-Crush项目总览.md`
   - `01_tech_common/Cursor-Agent上下文隔离.md`
   - `02_audit_risk/App-Store-Guideline-4.3-Spam.md`
   - `02_audit_risk/0630-4.3复盘结论.md`"""

_UI_BRAIN_FOCUS = """   - `01_tech_common/Flutter-ui-layout-pitfalls.md`
   - `01_tech_common/Flutter-asset-alignment-pitfalls.md`
   - `01_tech_common/Cursor-Agent上下文隔离.md`"""

_PROGRAMMER_BRAIN_FOCUS = """   - `01_tech_common/Flutter-iap-storekit-pitfalls.md`
   - `01_tech_common/Flutter-legal-webview-pitfalls.md`
   - `01_tech_common/Flutter-ui-layout-pitfalls.md`
   - `01_tech_common/Flutter-asset-alignment-pitfalls.md`
   - `01_tech_common/Flutter-dart-model-pitfalls.md`
   - `01_tech_common/Cursor-Agent上下文隔离.md`
   - `01_tech_common/cursor-ios-batch断点续跑.md`
   - `02_audit_risk/a面研发checklist/` (all applicable `.md`)"""

_TESTER_BRAIN_FOCUS = """   - `01_tech_common/Flutter-widget-test-pitfalls.md`
   - `01_tech_common/Cursor-Agent上下文隔离.md`
   - `02_audit_risk/a面研发checklist/` (items relevant to flow smoke tests)"""

_FIX_BRAIN_FOCUS = """   - `01_tech_common/Flutter-widget-test-pitfalls.md`
   - `01_tech_common/Flutter-dart-model-pitfalls.md`
   - `01_tech_common/Cursor-Agent上下文隔离.md`
   - `02_audit_risk/a面研发checklist/` (regressions tied to test failures)"""

_ANALYZE_FIX_BRAIN_FOCUS = """   - `01_tech_common/Flutter-ui-layout-pitfalls.md`
   - `01_tech_common/Flutter-dart-model-pitfalls.md`
   - `01_tech_common/Cursor-Agent上下文隔离.md`
   - `01_tech_common/cursor-ios-batch断点续跑.md`"""

_PM_UI_PLAN_BRAIN_FOCUS = """   - `01_tech_common/A-Crush项目总览.md`
   - `01_tech_common/Cursor-Agent上下文隔离.md`
   - `01_tech_common/Flutter-ui-layout-pitfalls.md`
   - `01_tech_common/Flutter-asset-alignment-pitfalls.md`
   - `02_audit_risk/App-Store-Guideline-4.3-Spam.md`
   - `02_audit_risk/0630-4.3复盘结论.md`"""


class PromptBuilder:
    """Load prompt templates from ``prompts/flutter/``."""

    def __init__(self, cfg: BatchConfig) -> None:
        self.cfg = cfg
        self.dir = cfg.prompts_dir

    def _load(self, name: str) -> str:
        path = self.dir / name
        if not path.is_file():
            raise FileNotFoundError(f"Prompt template missing: {path}")
        return path.read_text(encoding="utf-8")

    def _fmt(self, template: str, mapping: dict[str, str]) -> str:
        text = template
        for key, val in mapping.items():
            text = text.replace("${" + key + "}", val)
            text = text.replace("{" + key + "}", val)
            text = text.replace("$" + key, val)
        return text

    def global_brain_block(
        self,
        *,
        name: str,
        role_slug: str,
        role_focus: str,
    ) -> str:
        text = self._load("_global_brain_block.txt")
        return self._fmt(
            text,
            {
                "name": name,
                "GLOBAL_BRAIN_ROLE_SLUG": role_slug,
                "GLOBAL_BRAIN_ROLE_FOCUS": role_focus,
            },
        )

    def _prepend_brain(self, brain: str, body: str) -> str:
        return brain.rstrip() + "\n\n" + body.lstrip()

    def component_kit_pointer_block(self) -> str:
        return (
            "[Component Kit — Plan gate only; read kit `.md` files during §Component Selection]\n"
            "- Index: `data/static/component_kit/README.md` · `baseline.md` · `tokens.md`\n"
            "- Do NOT invent off-list shared widgets; cite kit paths in §Component Selection."
        )

    def component_kit_block(self) -> str:
        from batch.component_kit_index import format_kit_index_for_prompt

        block = format_kit_index_for_prompt()
        return f"{block}\n" if block else ""

    def free_tier_block(self, *, tool_flutter: bool) -> str:
        """Inject mandatory free-tier defaults from ``BatchConfig``."""
        if tool_flutter:
            count = self.cfg.free_tier_default
            return (
                "[Free Tier — MANDATORY for tool apps]\n"
                "- Section title in 功能文档.md: **\"Free Tier\"**.\n"
                f"- freeTierCount: {count} (2-5).\n"
                "- gatedActions: every coin-gated action; primary export/save MUST use free tier.\n"
                "- uiPlacement: main action area + success feedback.\n"
                "- logic: freeRemaining > 0 → consume 1 free use; else coin deduction with AlertDialog;\n"
                "  coins insufficient → guide to store.\n"
                "- Persist key: free_remaining_v1 (int). Coin balance default 0."
            )
        count = self.cfg.free_publish_default
        return (
            "[Free Tier — MANDATORY for content/video apps]\n"
            "- Section title in 功能文档.md: **\"Free Tier\"**.\n"
            f"- freeTierCount: {count} for Publish (and any other IAP-gated actions).\n"
            "- gatedActions: Publish MUST use free tier first; Detail Innovation save/export may also gate.\n"
            "- uiPlacement: Compose/Publish screen and Profile show \"Free posts remaining: N\".\n"
            "- logic: freeRemaining > 0 on publish → allow without coins; else coin deduction + confirm;\n"
            "  insufficient → store.\n"
            "- Persist key: free_remaining_v1 (int). Coin balance default 0."
        )

    def pm_phase(
        self,
        *,
        tool_flutter: bool,
        name: str,
        desc: str,
        product_req_doc: str,
        code_combo: str,
        legal_agreement_block: str = "",
        video_hint: str = "",
        csv_architecture_block: str = "",
        csv_programming_style_block: str = "",
        csv_naming_rule_block: str = "",
        csv_full_name_block: str = "",
        csv_iap_block: str = "",
        free_tier_block: str = "",
        h5_shell_block: str = "",
    ) -> str:
        fname = "phase1_pm_tool.txt" if tool_flutter else "phase1_pm.txt"
        text = self._load(fname)
        tier = free_tier_block or self.free_tier_block(tool_flutter=tool_flutter)
        body = self._fmt(
            text,
            {
                "name": name,
                "desc": desc,
                "PRODUCT_REQ_DOC": product_req_doc,
                "CODE_COMBO_BLOCK": code_combo,
                "LEGAL_AGREEMENT_BLOCK": legal_agreement_block,
                "VIDEO_FEED_DETAIL_HINT": video_hint,
                "CSV_ARCHITECTURE_BLOCK": csv_architecture_block,
                "CSV_PROGRAMMING_STYLE_BLOCK": csv_programming_style_block,
                "CSV_NAMING_RULE_BLOCK": csv_naming_rule_block,
                "CSV_FULL_NAME_BLOCK": csv_full_name_block,
                "CSV_IAP_BLOCK": csv_iap_block,
                "FREE_TIER_BLOCK": tier,
                "H5_SHELL_BLOCK": h5_shell_block,
            },
        )
        brain = self.global_brain_block(
            name=name, role_slug="pm", role_focus=_PM_BRAIN_FOCUS
        )
        return self._prepend_brain(brain, body)

    def h5_shell_block(self, *, bridge_deck_block: str = "") -> str:
        """Deprecated — norm prose lives in H5壳Pack约束.md + agent-spec-index."""
        return ""

    def h5_shell_programmer_block(self, *, bridge_deck_block: str = "") -> str:
        """Deprecated — norm prose lives in H5壳Pack约束.md + agent-spec-index."""
        return ""

    def h5_kit_block(self, *, kit_deck_block: str = "") -> str:
        """Deprecated — norm prose lives in H5壳Micro-UI Kit约束.md + 本包登记信息.json."""
        return ""

    def h5_shell_programmer_phase(
        self,
        *,
        name: str,
        dart_name: str,
        prefix: str,
        p2_product_doc: str,
        csv_iap_block: str = "",
        csv_architecture_block: str = "",
        csv_programming_style_block: str = "",
        csv_naming_rule_block: str = "",
        native_shell_naming_block: str = "",
        naming_transform_block: str = "",
        dimension_boundary_block: str = "",
        h5_shell_block: str = "",
    ) -> str:
        text = self._load("phase_h5_shell_programmer.txt")
        body = self._fmt(
            text,
            {
                "name": name,
                "dart_name": dart_name,
                "FLUTTER_DART_PREFIX": prefix,
                "P2_PRODUCT_DOC": p2_product_doc,
                "CSV_IAP_BLOCK": csv_iap_block,
                "CSV_ARCHITECTURE_BLOCK": csv_architecture_block,
                "CSV_PROGRAMMING_STYLE_BLOCK": csv_programming_style_block,
                "CSV_NAMING_RULE_BLOCK": csv_naming_rule_block,
                "NAMING_TRANSFORM_BLOCK": naming_transform_block,
                "DIMENSION_BOUNDARY_BLOCK": dimension_boundary_block,
                "H5_SHELL_BLOCK": h5_shell_block,
            },
        )
        brain = self.global_brain_block(
            name=name, role_slug="programmer", role_focus=_PROGRAMMER_BRAIN_FOCUS
        )
        return self._prepend_brain(brain, body)

    def h5_implementer_phase(
        self,
        *,
        name: str,
        prefix: str,
        p2_product_doc: str,
        h5_shell_block: str = "",
    ) -> str:
        text = self._load("phase_h5_implementer.txt")
        body = self._fmt(
            text,
            {
                "name": name,
                "FLUTTER_DART_PREFIX": prefix,
                "P2_PRODUCT_DOC": p2_product_doc,
                "H5_SHELL_BLOCK": h5_shell_block,
            },
        )
        brain = self.global_brain_block(
            name=name, role_slug="programmer", role_focus=_PROGRAMMER_BRAIN_FOCUS
        )
        return self._prepend_brain(brain, body)

    def _build_agent_plan_body(
        self,
        *,
        name: str,
        desc: str,
        product_req_doc: str,
        resume: bool = False,
        **_: object,
    ) -> str:
        resume_block = (
            "**RESUME:** 上次 Agent 超时/失败。计划文档可能已部分存在 — "
            "仅补全缺失或过短文件，勿重写已完整的产物。"
            if resume
            else ""
        )
        return self._fmt(
            self._load("phase_pm_ui_plan.txt"),
            {
                "name": name,
                "desc": desc,
                "RESUME_BLOCK": resume_block,
                "PRODUCT_REQ_DOC": product_req_doc,
            },
        )

    def preview_tabs_phase(self, *, resume: bool = False, **kwargs: object) -> str:
        """Lightweight Agent — static Tab preview HTML + preview-canonical.md."""
        from batch.h5_site_paths import app_slug_from_name

        name = str(kwargs.get("name", ""))
        resume_block = (
            "**RESUME:** Overwrite `_preview/` files only; do not touch `h5/src` or plan docs."
            if resume
            else ""
        )
        return self._fmt(
            self._load("phase_preview_tabs.txt"),
            {
                "name": name,
                "desc": str(kwargs.get("desc", "")),
                "APP_SLUG": app_slug_from_name(name),
                "RESUME_BLOCK": resume_block,
            },
        )

    def _build_agent_shell_body(
        self,
        *,
        name: str,
        desc: str,
        dart_name: str,
        prefix: str,
        p2_product_doc: str,
        shell_runtime: str,
        resume: bool = False,
        **_: object,
    ) -> str:
        runtime = (shell_runtime or "flutter").strip().lower()
        resume_block = (
            "**RESUME:** 上次壳实现子步超时/失败。壳代码可能不完整 — "
            "在现有 native shell / Flutter shell 基础上继续，勿重做 H5 vault。"
            if resume
            else ""
        )
        template = {
            "flutter": "phase_h5_shell_programmer.txt",
            "swift": "phase_h5_shell_swift_programmer.txt",
            "oc": "phase_h5_shell_oc_programmer.txt",
        }.get(runtime, "phase_h5_shell_programmer.txt")
        return self._fmt(
            self._load(template),
            {
                "name": name,
                "desc": desc,
                "dart_name": dart_name,
                "FLUTTER_DART_PREFIX": prefix,
                "P2_PRODUCT_DOC": p2_product_doc,
                "SHELL_RUNTIME": runtime,
                "RESUME_BLOCK": resume_block,
            },
        )

    def _build_agent_h5_body(
        self,
        *,
        name: str,
        desc: str,
        prefix: str,
        p2_product_doc: str,
        resume: bool = False,
        **_: object,
    ) -> str:
        resume_block = (
            "**RESUME:** H5 子步未完成 — 在现有 vault 文件上继续，勿重做 native shell。"
            if resume
            else ""
        )
        return self._fmt(
            self._load("phase_h5_implementer.txt"),
            {
                "name": name,
                "desc": desc,
                "FLUTTER_DART_PREFIX": prefix,
                "P2_PRODUCT_DOC": p2_product_doc,
                "RESUME_BLOCK": resume_block,
            },
        )

    def build_agent_plan_only_phase(self, *, resume: bool = False, **kwargs: object) -> str:
        """Plan-only Agent prompt — Part 1 (PM + UI + Plan + legal)."""
        return self._build_agent_plan_body(resume=resume, **kwargs)  # type: ignore[arg-type]

    def build_agent_shell_phase(self, *, resume: bool = False, **kwargs: object) -> str:
        return self._build_agent_shell_body(resume=resume, **kwargs)  # type: ignore[arg-type]

    def build_agent_h5_phase(self, *, resume: bool = False, **kwargs: object) -> str:
        return self._build_agent_h5_body(resume=resume, **kwargs)  # type: ignore[arg-type]

    def designer_phase(
        self,
        *,
        name: str,
        desc: str,
        csv_architecture_block: str = "",
        csv_programming_style_block: str = "",
        csv_naming_rule_block: str = "",
    ) -> str:
        text = self._load("phase2_designer.txt")
        body = self._fmt(
            text,
            {
                "name": name,
                "desc": desc,
                "CSV_ARCHITECTURE_BLOCK": csv_architecture_block,
                "CSV_PROGRAMMING_STYLE_BLOCK": csv_programming_style_block,
                "CSV_NAMING_RULE_BLOCK": csv_naming_rule_block,
                "COMPONENT_KIT_BLOCK": self.component_kit_block(),
            },
        )
        brain = self.global_brain_block(
            name=name, role_slug="ui", role_focus=_UI_BRAIN_FOCUS
        )
        return self._prepend_brain(brain, body)

    def implementer_phase(
        self,
        *,
        name: str,
        tool_flutter: bool,
        dart_name: str,
        prefix: str,
        content_list: str,
        p2_product_doc: str,
        csv_iap_block: str = "",
        csv_architecture_block: str = "",
        csv_programming_style_block: str = "",
        csv_naming_rule_block: str = "",
        native_shell_naming_block: str = "",
        naming_transform_block: str = "",
        dimension_boundary_block: str = "",
        p2_video_hint: str = "",
        free_tier_block: str = "",
        h5_shell_block: str = "",
    ) -> str:
        text = self._load("phase_programmer.txt")
        tier = free_tier_block or self.free_tier_block(tool_flutter=tool_flutter)
        body = self._fmt(
            text,
            {
                "dart_name": dart_name,
                "name": name,
                "FLUTTER_DART_PREFIX": prefix,
                "content_list_escaped": content_list,
                "P2_PRODUCT_DOC": p2_product_doc,
                "CSV_IAP_BLOCK": csv_iap_block,
                "CSV_ARCHITECTURE_BLOCK": csv_architecture_block,
                "CSV_PROGRAMMING_STYLE_BLOCK": csv_programming_style_block,
                "CSV_NAMING_RULE_BLOCK": csv_naming_rule_block,
                "NAMING_TRANSFORM_BLOCK": naming_transform_block,
                "DIMENSION_BOUNDARY_BLOCK": dimension_boundary_block,
                "P2_VIDEO_HINT": p2_video_hint,
                "FREE_TIER_BLOCK": tier,
                "H5_SHELL_BLOCK": h5_shell_block,
                "COMPONENT_KIT_BLOCK": self.component_kit_block(),
            },
        )
        brain = self.global_brain_block(
            name=name, role_slug="programmer", role_focus=_PROGRAMMER_BRAIN_FOCUS
        )
        return self._prepend_brain(brain, body)

    def _phase7_resume_block(self, flutter_project: Path) -> str:
        flow_file = flutter_project / "test" / "flows" / "main_tool_flow_test.dart"
        if not flow_file.is_file():
            return ""
        return (
            "[RESUME — existing flow test detected]\n"
            f"Found `{flow_file.name}`. Do NOT rewrite from scratch. Only fix failures "
            "referenced in previous_failures. Keep harness files unless they cause the failure.\n"
        )

    def tester_phase(
        self,
        *,
        name: str,
        desc: str,
        iteration: int,
        previous_failures: str,
        flutter_project: Path | None = None,
    ) -> str:
        text = self._load("phase7_tester.txt")
        resume_block = ""
        if flutter_project is not None:
            resume_block = self._phase7_resume_block(flutter_project)
        failures_block = previous_failures.strip()
        if failures_block:
            failures_block = f"[Previous failures]\n{failures_block}\n"
        body = self._fmt(
            text,
            {
                "name": name,
                "desc": desc,
                "iteration": str(iteration),
                "previous_failures": failures_block,
                "resume_block": resume_block,
            },
        )
        brain = self.global_brain_block(
            name=name, role_slug="tester", role_focus=_TESTER_BRAIN_FOCUS
        )
        return self._prepend_brain(brain, body)

    def programmer_fix_phase(
        self,
        *,
        name: str,
        desc: str,
        test_report: str,
    ) -> str:
        text = self._load("phase4_programmer_fix.txt")
        body = self._fmt(
            text,
            {
                "name": name,
                "desc": desc,
                "test_report": test_report,
            },
        )
        brain = self.global_brain_block(
            name=name, role_slug="programmer-fix", role_focus=_FIX_BRAIN_FOCUS
        )
        return self._prepend_brain(brain, body)

    def programmer_analyze_fix_phase(
        self,
        *,
        name: str,
        desc: str,
        analyze_errors: str,
    ) -> str:
        text = self._load("phase_programmer_analyze_fix.txt")
        body = self._fmt(
            text,
            {
                "name": name,
                "desc": desc,
                "analyze_errors": analyze_errors,
            },
        )
        brain = self.global_brain_block(
            name=name,
            role_slug="programmer-analyze-fix",
            role_focus=_ANALYZE_FIX_BRAIN_FOCUS,
        )
        return self._prepend_brain(brain, body)

    def asset_generator_phase(self, *, name: str, desc: str) -> str:
        text = self._load("phase9_asset_generator.txt")
        return self._fmt(text, {"name": name, "desc": desc})
