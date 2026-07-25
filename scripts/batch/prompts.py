"""Load V3 Agent prompt templates from ``prompts/h5_shell/``.

V3 plan agent steps:

* ``phase_agent_design.txt`` — agent.design（包内 skill 设计主产）
* ``phase_agent_plan_spec.txt`` — agent.plan.spec（功能/产品文档 + Legal）
* ``phase_agent_plan_pack.txt`` — agent.plan.pack (JSON ledgers only; no 视觉蓝图)
* ``phase_h5_shell_programmer.txt`` — agent.shell
* ``phase_h5_implementer.txt`` — agent.h5
* ``phase_plan_gate_repair.txt`` — plan.gate repair
* ``phase9_asset_generator.txt`` — optional ``batch generate-assets``
"""

from __future__ import annotations

from pathlib import Path

from batch.config import BatchConfig

# Written to skill-input/agent-workspace-focus.md (in-package reading list).
# Distilled paths are under skill-input/distilled/ after sync.distilled.
_PROGRAMMER_BRAIN_FOCUS = """   - `H5壳Pack约束.md`
   - `H5-Bridge协议.md`
   - `H5壳启动闪屏规范.md`
   - `H5壳Swift实现规范.md` / `H5壳OC实现规范.md` (per shellRuntime)
   - `H5壳WKWebView性能与层叠规范.md`
   - `H5壳H5实现检查清单.md`
   - `H5壳Vite工程规范.md`
   - `H5壳ui-ux-pro-max使用规范.md`（§8：`_preview/pages` → `h5/` 两阶段）
   - `H5壳Legal弹层规范.md` · `H5壳广场页规范.md` · `H5去风味规范.md`
   - `命名混淆规则.md` · `编程人设风格.md`
   - `data/static/h5_snippets/bridge/` (browser mock)
   - `data/static/h5_snippets/legal/legalLinks.ts` (openLegal runtime branch)
   - `skill-input/distilled/shared/`
   - `skill-input/distilled/shell/` · `skill-input/distilled/h5/`"""

_DESIGN_AGENT_BRAIN_FOCUS = """   - `H5壳ui-ux-pro-max使用规范.md`
   - `.cursor/skills/ui-ux-pro-max/SKILL.md` · `scripts/search.py`（包内克隆）
   - `design-system/*/MASTER.md` · `candidates.json`
   - `skill-adapt/design-brief.md` · `design-tokens.css` · `design-audit.md`
   - `skill-input/context.json`
   - `skill-input/distilled/shared/`"""

_PM_UI_PLAN_BRAIN_FOCUS = """   - `H5壳Plan交付规范.md`
   - `H5壳功能文档深度标准.md`
   - `H5壳交互拓扑与PlanGate策略.md`
   - `H5壳产品文档格式.md`
   - `H5壳ui-ux-pro-max使用规范.md`（设计已由 agent.design 审核）
   - `法律协议规范.md`
   - `H5壳Flutter产品要求.md`
   - `H5壳Pack约束.md` · `H5壳Micro-UI Kit约束.md`
   - `skill-input/distilled/shared/`
   - `skill-input/distilled/plan/`"""

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

    def _resume_block_plan(self, *, resume: bool, focus: str) -> str:
        if not resume:
            return ""
        return (
            f"**RESUME:** 上次 {focus} 超时/失败 — "
            "仅补全缺失或过短文件，勿重写已完整的产物。"
        )

    def _build_agent_design_body(
        self,
        *,
        name: str,
        desc: str,
        resume: bool = False,
        **_: object,
    ) -> str:
        return self._fmt(
            self._load("phase_agent_design.txt"),
            {
                "name": name,
                "desc": desc,
                "RESUME_BLOCK": self._resume_block_plan(
                    resume=resume, focus="agent.design"
                ),
            },
        )

    def _build_agent_plan_spec_body(
        self,
        *,
        name: str,
        desc: str,
        product_req_doc: str,
        csv_full_name: str = "",
        resume: bool = False,
        **_: object,
    ) -> str:
        return self._fmt(
            self._load("phase_agent_plan_spec.txt"),
            {
                "name": name,
                "desc": desc,
                "CSV_FULL_NAME": csv_full_name or name,
                "RESUME_BLOCK": self._resume_block_plan(
                    resume=resume, focus="agent.plan.spec"
                ),
                "PRODUCT_REQ_DOC": product_req_doc,
            },
        )

    def _build_agent_plan_pack_body(
        self,
        *,
        name: str,
        desc: str,
        resume: bool = False,
        **_: object,
    ) -> str:
        return self._fmt(
            self._load("phase_agent_plan_pack.txt"),
            {
                "name": name,
                "desc": desc,
                "RESUME_BLOCK": self._resume_block_plan(
                    resume=resume, focus="agent.plan.pack"
                ),
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
        app_lower = name.strip().lower()
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
                "BRIDGE_CHANNEL": f"{app_lower}Bridge",
                "BRIDGE_CALLBACK": f"{app_lower}BridgeCallback",
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
        app_lower = name.strip().lower()
        return self._fmt(
            self._load("phase_h5_implementer.txt"),
            {
                "name": name,
                "desc": desc,
                "FLUTTER_DART_PREFIX": prefix,
                "P2_PRODUCT_DOC": p2_product_doc,
                "RESUME_BLOCK": resume_block,
                "BRIDGE_CHANNEL": f"{app_lower}Bridge",
                "BRIDGE_CALLBACK": f"{app_lower}BridgeCallback",
            },
        )

    def build_agent_design_phase(self, *, resume: bool = False, **kwargs: object) -> str:
        return self._build_agent_design_body(resume=resume, **kwargs)  # type: ignore[arg-type]

    def build_agent_plan_spec_phase(self, *, resume: bool = False, **kwargs: object) -> str:
        return self._build_agent_plan_spec_body(resume=resume, **kwargs)  # type: ignore[arg-type]

    def build_agent_plan_docs_phase(self, *, resume: bool = False, **kwargs: object) -> str:
        """Legacy alias → agent.plan.spec (merged docs step)."""
        return self.build_agent_plan_spec_phase(resume=resume, **kwargs)

    def build_agent_plan_pack_phase(self, *, resume: bool = False, **kwargs: object) -> str:
        return self._build_agent_plan_pack_body(resume=resume, **kwargs)  # type: ignore[arg-type]

    def build_agent_plan_only_phase(self, *, resume: bool = False, **kwargs: object) -> str:
        """Legacy alias → agent.plan.spec prompt."""
        return self.build_agent_plan_spec_phase(resume=resume, **kwargs)

    def build_agent_shell_phase(self, *, resume: bool = False, **kwargs: object) -> str:
        return self._build_agent_shell_body(resume=resume, **kwargs)  # type: ignore[arg-type]

    def build_agent_h5_phase(self, *, resume: bool = False, **kwargs: object) -> str:
        return self._build_agent_h5_body(resume=resume, **kwargs)  # type: ignore[arg-type]

    def asset_generator_phase(self, *, name: str, desc: str) -> str:
        text = self._load("phase9_asset_generator.txt")
        return self._fmt(text, {"name": name, "desc": desc})
