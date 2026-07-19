"""Load V3 Agent prompt templates from ``prompts/h5_shell/``.

V3 steps:

* ``phase_pm_ui_plan.txt`` — agent.plan
* ``phase_h5_shell_programmer.txt`` — agent.shell (all runtimes)
* ``phase_h5_implementer.txt`` — agent.h5
* ``phase_plan_gate_repair.txt`` — plan.gate repair
* ``phase9_asset_generator.txt`` — optional ``batch generate-assets``
"""

from __future__ import annotations

from pathlib import Path

from batch.config import BatchConfig

# Written to skill-input/agent-brain-focus.md (not injected into prompt body).
_PROGRAMMER_BRAIN_FOCUS = """   - `01_tech_common/Flutter-iap-storekit-pitfalls.md`
   - `01_tech_common/Flutter-legal-webview-pitfalls.md`
   - `01_tech_common/Flutter-ui-layout-pitfalls.md`
   - `01_tech_common/Flutter-asset-alignment-pitfalls.md`
   - `01_tech_common/Flutter-dart-model-pitfalls.md`
   - `01_tech_common/Cursor-Agent上下文隔离.md`
   - `01_tech_common/cursor-ios-batch断点续跑.md`
   - `02_audit_risk/a面研发checklist/` (all applicable `.md`)"""

_PM_UI_PLAN_BRAIN_FOCUS = """   - `01_tech_common/A-Crush项目总览.md`
   - `01_tech_common/Cursor-Agent上下文隔离.md`
   - `01_tech_common/Flutter-ui-layout-pitfalls.md`
   - `01_tech_common/Flutter-asset-alignment-pitfalls.md`
   - `02_audit_risk/App-Store-Guideline-4.3-Spam.md`
   - `02_audit_risk/0630-4.3复盘结论.md`"""


class PromptBuilder:
    """Load and fill V3 prompt templates (path-index style; no prose injection)."""

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
        return self._fmt(
            self._load("phase_h5_shell_programmer.txt"),
            {
                "name": name,
                "desc": desc,
                "dart_name": dart_name or "(n/a)",
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
        return self._build_agent_plan_body(resume=resume, **kwargs)  # type: ignore[arg-type]

    def build_agent_shell_phase(self, *, resume: bool = False, **kwargs: object) -> str:
        return self._build_agent_shell_body(resume=resume, **kwargs)  # type: ignore[arg-type]

    def build_agent_h5_phase(self, *, resume: bool = False, **kwargs: object) -> str:
        return self._build_agent_h5_body(resume=resume, **kwargs)  # type: ignore[arg-type]

    def asset_generator_phase(self, *, name: str, desc: str) -> str:
        text = self._load("phase9_asset_generator.txt")
        return self._fmt(text, {"name": name, "desc": desc})
