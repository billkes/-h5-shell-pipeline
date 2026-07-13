"""V3 granular step runner — breakpoint resume for Plan / Dev."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

from batch.batch_run_log import get_run_log
from batch.failure_notes import analyze_log_error_snippets
from batch.flutter_ops import (
    analyze_log_shows_success,
    count_resource_stats,
    find_flutter_project,
    run_analyze_only,
    run_pub_get,
)
from batch.pack_type import h5_shell_runtime, is_flutter_runtime, is_h5_shell, is_native_ios_runtime
from batch.pipeline_gates import verify_pm_ui_plan_outputs
from batch.pipeline_steps import (
    ANALYZE,
    BUILD_AGENT,
    LOCK_DIMENSIONS,
    PREPARE_CONTEXT,
    SKILL_ADAPT,
    SKILL_DESIGN,
    GIT_DEV,
    GIT_PLAN,
    NATIVE_CHECK,
    PLAN_GATE,
    PUBGET,
    step_display,
    step_index,
    steps_for_run,
)
from batch.registry import append_to_registry
from batch.state import (
    PM_UI_PLAN_PHASE,
    PROGRAMMER_PHASE,
    first_failed_step,
    first_incomplete_step,
    get_step,
    init_state,
    read_state,
    reset_steps,
    set_step,
    step_done,
    update_state_fields,
)

if TYPE_CHECKING:
    from batch.pipeline import AppContext, FlutterPipeline


_STEP_ICONS = {
    "done": "✅",
    "failed": "❌",
    "running": "⚡",
    "skipped": "⏭️",
    "pending": "○",
}


class V3StepRunner:
    """Execute V3 pipeline steps with granular breakpoint state."""

    def __init__(self, pipeline: FlutterPipeline) -> None:
        self.p = pipeline

    def ordered_steps(self, ctx: AppContext) -> tuple[str, ...]:
        return steps_for_run(
            pack_type=ctx.pack_type,
        )

    def ensure_state(self, ctx: AppContext) -> None:
        from batch.state import STEPS_KEY, steps_map_from_data, sync_phases_from_steps

        ws = ctx.workspace
        sf = ws / ".build-state.json"
        if sf.is_file() and not self.p.cfg.force_rerun:
            data = read_state(ws)
            updates: dict[str, object] = {
                "pack_type": ctx.pack_type,
            }
            if not data.get(STEPS_KEY):
                updates[STEPS_KEY] = steps_map_from_data(data)
            update_state_fields(ws, **updates)
            data = read_state(ws)
            sync_phases_from_steps(data)
            sf.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return
        init_state(
            ws,
            ctx.name,
            ctx.desc,
            ctx.dart_name,
            force=self.p.cfg.force_rerun,
            pipeline_version="v3",
            pack_type=ctx.pack_type,
        )

    def run_all(
        self,
        ctx: AppContext,
        *,
        step_ids: list[str] | None = None,
        continue_from: bool = False,
        rerun: bool = False,
    ) -> bool:
        ordered = self.ordered_steps(ctx)
        if continue_from:
            start = first_failed_step(ctx.workspace, ordered)
            if start is None:
                start = first_incomplete_step(ctx.workspace, ordered)
            if start is None:
                get_run_log().detail("所有步骤已完成")
                return True
            idx = ordered.index(start)
            to_run = list(ordered[idx:])
        elif step_ids:
            to_run = [s for s in ordered if s in step_ids]
        else:
            to_run = list(ordered)

        if rerun and step_ids:
            reset_steps(ctx.workspace, step_ids)

        i = 0
        while i < len(to_run):
            step = to_run[i]
            if (
                not rerun
                and not continue_from
                and step_done(ctx.workspace, step)
                and step not in (step_ids or [])
            ):
                if step_ids is None:
                    i += 1
                    continue

            if not self.execute_step(ctx, step, force=rerun):
                return False
            i += 1
        return True

    def execute_step(self, ctx: AppContext, step_id: str, *, force: bool = False) -> bool:
        ws = ctx.workspace
        ordered = self.ordered_steps(ctx)
        if step_id not in ordered:
            get_run_log().detail(f"跳过不适用的步骤: {step_id}")
            return True

        if step_done(ws, step_id) and not force:
            get_run_log().detail(f"跳过 {step_display(step_id)}（已完成）")
            return True

        if not self._prerequisites_ok(ctx, step_id):
            get_run_log().detail(f"前置步骤未完成，跳过 {step_id}")
            set_step(ws, step_id, "skipped")
            return True

        title = step_display(step_id)
        num = step_index(step_id, ordered)
        total = len(ordered)
        set_step(ws, step_id, "running")
        start = time.time()
        print(f"  [{num}/{total}] {title} ...")
        get_run_log().queue(f"[{num}/{total}] {title} ⟳")

        handler = _STEP_HANDLERS.get(step_id)
        if handler is None:
            set_step(ws, step_id, "failed")
            print(f"  [{num}/{total}] 未知步骤 {step_id}")
            return False

        resume_agent = step_id == BUILD_AGENT and not self.p.cfg.force_rerun

        try:
            if step_id == BUILD_AGENT:
                ok = handler(self, ctx, resume=resume_agent)
            else:
                ok = handler(self, ctx)
        except Exception as exc:  # noqa: BLE001 — surface step failure
            get_run_log().detail(f"步骤异常 {step_id}: {exc}")
            ok = False

        status = "done" if ok else "failed"
        set_step(ws, step_id, status)
        elapsed = int(time.time() - start)
        icon = "✅" if ok else "❌"
        print(f"  [{num}/{total}] {icon} {title} ({elapsed}s)")
        get_run_log().queue(f"[{num}/{total}] {title} {icon} ({elapsed}s)")
        return ok

    def _prerequisites_ok(self, ctx: AppContext, step_id: str) -> bool:
        ws = ctx.workspace
        ordered = self.ordered_steps(ctx)
        idx = ordered.index(step_id)
        for prior in ordered[:idx]:
            st = get_step(ws, prior)
            if st in ("done", "skipped"):
                continue
            if st == "failed":
                return False
            return False
        return True

    def _run_analyze_fix_chain(self, ctx: AppContext) -> bool:
        """Deprecated — lite pipeline uses single Agent; analyze fix is manual."""
        fp = find_flutter_project(ctx.workspace) or ctx.workspace
        return self._do_dev_analyze(ctx, fp)

    # ── Prepare + Agent sub-steps ─────────────────────────────────────

    def _agent_pack_context(self, ctx: AppContext) -> dict[str, object]:
        """Shared kwargs for build_agent_*_phase prompts."""
        from batch.csv_prompt_blocks import dimension_boundary_block
        from batch.workspace import code_combo_block, dart_prefix

        ws = ctx.workspace
        tool = ctx.pack_type == "tool_flutter"
        video = ctx.pack_type == "videostream"
        h5 = is_h5_shell(ctx.pack_type)
        prefix = dart_prefix(ws)
        combo = code_combo_block(ws)
        content_preview = ""
        cl = ws / "默认内容列表.json"
        if cl.is_file():
            content_preview = cl.read_text(encoding="utf-8")[:5000]

        if h5:
            product_doc = "H5壳Flutter产品要求.md"
            p2_doc = "H5壳Flutter产品要求.md"
            video_hint = ""
            p2_video = ""
        elif tool:
            product_doc = "工具包Flutter产品要求.md"
            p2_doc = product_doc
            video_hint = ""
            p2_video = ""
        elif video:
            product_doc = "视频流包产品要求.md"
            p2_doc = product_doc
            video_hint = "\n[VIDEO STREAM — video-specific feed/detail innovations required]"
            p2_video = "\n[VIDEO STREAM PACK — videostream type]"
        else:
            product_doc = "图文包产品要求.md"
            p2_doc = product_doc
            video_hint = ""
            p2_video = ""

        h5_block = self.p._h5_shell_block_for(ctx)
        from batch.selection_requirements import format_required_selection_block

        return {
            "tool_flutter": tool,
            "name": ctx.name,
            "desc": ctx.desc,
            "dart_name": ctx.dart_name,
            "prefix": prefix,
            "content_list": content_preview,
            "product_req_doc": product_doc,
            "code_combo": combo,
            "legal_agreement_block": self.p._legal_agreement_block_for(ctx, tool),
            "video_hint": video_hint,
            "csv_architecture_block": self.p._csv_architecture_block_for(ctx),
            "csv_programming_style_block": self.p._csv_programming_style_block_for(ctx),
            "csv_naming_rule_block": self.p._csv_naming_rule_block_for(ctx),
            "csv_full_name_block": self.p._csv_full_name_block_for(ctx),
            "csv_iap_block": self.p._csv_iap_block_for(ctx),
            "design_system_block": self.p._design_system_block(ctx),
            "designer_lock_block": self.p._designer_lock_block(ctx),
            "ambient_canvas_block": self.p._ambient_canvas_block(ctx),
            "naming_transform_block": self.p._naming_transform_block(ctx),
            "dimension_boundary_block": dimension_boundary_block(),
            "p2_product_doc": p2_doc,
            "p2_video_hint": p2_video,
            "h5_shell": h5,
            "shell_runtime": h5_shell_runtime(ctx.pack_type) if h5 else "flutter",
            "h5_shell_block": h5_block,
            "h5_shell_block_programmer": self.p._h5_shell_block_for(ctx, programmer=True),
            "required_selection_block": format_required_selection_block(
                ws, pack_type=ctx.pack_type
            ),
        }

    def _step_prepare_context(self, ctx: AppContext) -> bool:
        return self.p._run_prepare_context(ctx)

    def _step_skill_design(self, ctx: AppContext) -> bool:
        return self.p._run_skill_design(ctx)

    def _step_skill_adapt(self, ctx: AppContext) -> bool:
        return self.p._run_skill_adapt(ctx)

    def _step_lock_dimensions(self, ctx: AppContext) -> bool:
        return self.p._run_lock_dimensions(ctx)

    def _step_design_system(self, ctx: AppContext) -> bool:
        return self.p._run_skill_design(ctx)

    def _step_build_agent(self, ctx: AppContext, *, resume: bool = False) -> bool:
        from batch.cursor_runner import run_agent

        kw = self._agent_pack_context(ctx)
        prompt = self.p.prompts.build_agent_phase(resume=resume, **kw)
        ok = run_agent(
            self.p.cfg,
            ctx.workspace,
            prompt,
            log_section_title=f"{ctx.name} · Build Agent · 蓝图 + 实现",
        )
        if ok:
            extra: dict[str, str] = {"phase_programmer_agent": "done"}
            if is_h5_shell(ctx.pack_type):
                extra["phase_h5_agent"] = "done"
            update_state_fields(ctx.workspace, **extra)
        return ok

    def _step_agent_plan(self, ctx: AppContext, *, resume: bool = False) -> bool:
        """Legacy alias → single build.agent call."""
        return self._step_build_agent(ctx, resume=resume)

    def _step_agent_impl(self, ctx: AppContext, *, resume: bool = False) -> bool:
        return self._step_build_agent(ctx, resume=resume)

    def _step_agent_shell(self, ctx: AppContext, *, resume: bool = False) -> bool:
        return self._step_build_agent(ctx, resume=resume)

    def _step_agent_h5(self, ctx: AppContext, *, resume: bool = False) -> bool:
        return self._step_build_agent(ctx, resume=resume)

    def _step_prepare(self, ctx: AppContext) -> bool:
        """Legacy alias — full plan-phase prep chain."""
        return (
            self._step_prepare_context(ctx)
            and self._step_skill_design(ctx)
            and self._step_skill_adapt(ctx)
            and self._step_lock_dimensions(ctx)
        )

    def _step_plan_gate(self, ctx: AppContext) -> bool:
        ws = ctx.workspace
        tool = ctx.pack_type == "tool_flutter"
        video = ctx.pack_type == "videostream"
        h5 = is_h5_shell(ctx.pack_type)

        from batch.selection_sync import sync_selection_artifacts

        sync_changes = sync_selection_artifacts(ws, pack_type=ctx.pack_type)
        if sync_changes:
            print(">>> Selection 产物同步（plan.gate 前）:")
            for line in sync_changes:
                print(f"       {line}")

        gate_ok, gate_issues = verify_pm_ui_plan_outputs(
            ws,
            tool_flutter=tool,
            videostream=video,
            h5_shell=h5,
            csv_full_name=self.p._csv_full_name_for(ctx),
            app_name=ctx.name,
        )
        if not gate_ok:
            print(">>> PM+UI+Plan 产出物校验未通过:")
            for issue in gate_issues:
                print(f"       {issue}")
            return False

        reg_file = ws / "本包登记信息.json"
        if not reg_file.is_file():
            alt = ws / "package-register.json"
            reg_file = alt if alt.is_file() else reg_file
        if reg_file.is_file():
            append_to_registry(
                self.p.cfg.contentpack_registry,
                reg_file,
                ws,
                ctx.name,
                ctx.desc,
                batch_id=self.p._batch_id(),
                upsert=self.p.cfg.force_rerun,
            )
        return True

    def _step_git_plan(self, ctx: AppContext) -> bool:
        self.p._git_sync(ctx, PM_UI_PLAN_PHASE, init=True)
        return True

    def _step_pubget(self, ctx: AppContext) -> bool:
        if not is_flutter_runtime(ctx.pack_type):
            return True
        fp = find_flutter_project(ctx.workspace) or ctx.workspace
        if not (fp / "pubspec.yaml").is_file():
            return False
        self.p._apply_xcode_delivery(ctx)
        log = ctx.workspace / "analyze.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        if not log.is_file():
            log.write_text("", encoding="utf-8")
        return run_pub_get(
            fp,
            log,
            max_retries=self.p.cfg.pub_get_max_retries,
        )

    def _step_analyze(self, ctx: AppContext) -> bool:
        if not is_flutter_runtime(ctx.pack_type):
            return True
        fp = find_flutter_project(ctx.workspace) or ctx.workspace
        return self._do_dev_analyze(ctx, fp)

    def _step_native_check(self, ctx: AppContext) -> bool:
        if not is_native_ios_runtime(ctx.pack_type):
            return True
        ok, issues = self._check_native_shell(ctx)
        if not ok:
            update_state_fields(
                ctx.workspace,
                phase_programmer_failure_reason="native shell check 未通过",
                phase_programmer_failure_details=issues,
            )
            get_run_log().fail_banner("native shell check 未通过", issues)
        return ok

    def _check_native_shell(self, ctx: AppContext) -> tuple[bool, list[str]]:
        ws = ctx.workspace
        runtime = h5_shell_runtime(ctx.pack_type)
        issues: list[str] = []
        if not any(ws.glob("*.xcodeproj")) and not any(ws.glob("*.xcworkspace")):
            issues.append("缺少 .xcodeproj/.xcworkspace")
        if not list(ws.rglob("Info.plist")):
            issues.append("缺少 Info.plist")
        if not list(ws.rglob("*LaunchScreen*.storyboard")):
            issues.append("缺少 LaunchScreen.storyboard")

        suffixes = (".swift",) if runtime == "swift" else (".m", ".mm")
        source_files = [
            p
            for suffix in suffixes
            for p in ws.rglob(f"*{suffix}")
            if "/build/" not in str(p)
        ]
        if not source_files:
            issues.append(f"缺少 {runtime} native source 文件")
            return False, issues

        joined_parts: list[str] = []
        for path in source_files[:40]:
            try:
                joined_parts.append(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
        joined = "\n".join(joined_parts)
        required_tokens = (
            "WKWebView",
            "WKScriptMessageHandler",
            "shellReady",
            "readFile",
            "writeFile",
            "pickImage",
            "saveImage",
            "purchase",
            "restorePurchases",
            "mediaServe",
        )
        if runtime == "oc":
            required_tokens = required_tokens + (
                "WKURLSchemeHandler",
                "app-callback",
            )
        for token in required_tokens:
            if token not in joined:
                issues.append(f"native shell 缺少 Bridge/host token: {token}")
        if "SFSafariViewController" in joined:
            issues.append("禁止主流程使用 SFSafariViewController/browser chrome")

        issues.extend(self._optional_xcodebuild(ws, ctx.name, runtime))
        return len(issues) == 0, issues

    def _optional_xcodebuild(self, ws: Path, app_name: str, runtime: str) -> list[str]:
        """Run xcodebuild on macOS when project exists; skip elsewhere."""
        import platform
        import subprocess

        if platform.system() != "Darwin":
            return []
        projects = list(ws.glob("*.xcodeproj"))
        if not projects:
            return []
        project = projects[0]
        cmd = [
            "xcodebuild",
            "-project",
            str(project),
            "-scheme",
            app_name,
            "-sdk",
            "iphonesimulator",
            "-destination",
            "generic/platform=iOS Simulator",
            "build",
            "CODE_SIGNING_ALLOWED=NO",
        ]
        try:
            result = subprocess.run(
                cmd,
                cwd=str(ws),
                capture_output=True,
                text=True,
                timeout=300,
            )
        except FileNotFoundError:
            return []
        except subprocess.TimeoutExpired:
            return [f"xcodebuild 超时（{runtime}）"]
        if result.returncode != 0:
            tail = (result.stderr or result.stdout or "").strip().splitlines()[-5:]
            return [f"xcodebuild 失败: {' | '.join(tail)}"]
        return []

    def _do_dev_analyze(self, ctx: AppContext, fp) -> bool:  # noqa: ANN001
        ws = ctx.workspace
        log = ws / "analyze.log"
        self.p._apply_xcode_delivery(ctx)
        from batch.debug_banner import ensure_debug_banner_false
        from batch.workspace import patch_pubspec_overrides

        patch_pubspec_overrides(fp)
        banner_fixed = ensure_debug_banner_false(fp)
        if banner_fixed:
            get_run_log().detail(f"已自动关闭 DEBUG 角标: {', '.join(banner_fixed)}")

        pub_ok = True
        if not analyze_log_shows_success(log):
            pub_ok = run_pub_get(fp, log, max_retries=self.p.cfg.pub_get_max_retries)
        ok = run_analyze_only(fp, log, append=True) if pub_ok else False
        if ok and not analyze_log_shows_success(log):
            ok = False

        total, placeholder = count_resource_stats(
            fp,
            videostream=ctx.pack_type == "videostream",
            tool_flutter=ctx.pack_type == "tool_flutter",
        )
        if not ok:
            errors = analyze_log_error_snippets(log)
            update_state_fields(
                ws,
                phase_programmer_failure_reason="flutter pub get / analyze 未通过",
                phase_programmer_failure_details=errors,
                phase_programmer_analyze_log=str(log.resolve()),
                phase_programmer_image_total=total,
                phase_programmer_image_placeholder=placeholder,
            )
            get_run_log().fail_banner(
                "flutter pub get / analyze 未通过",
                errors or [f"详见 {log}"],
            )
        return ok

    def _step_git_dev(self, ctx: AppContext) -> bool:
        self.p._git_sync(ctx, PROGRAMMER_PHASE)
        return True


_STEP_HANDLERS = {
    PREPARE_CONTEXT: V3StepRunner._step_prepare_context,
    SKILL_DESIGN: V3StepRunner._step_skill_design,
    SKILL_ADAPT: V3StepRunner._step_skill_adapt,
    LOCK_DIMENSIONS: V3StepRunner._step_lock_dimensions,
    BUILD_AGENT: V3StepRunner._step_build_agent,
    PLAN_GATE: V3StepRunner._step_plan_gate,
    GIT_PLAN: V3StepRunner._step_git_plan,
    PUBGET: V3StepRunner._step_pubget,
    ANALYZE: V3StepRunner._step_analyze,
    NATIVE_CHECK: V3StepRunner._step_native_check,
    GIT_DEV: V3StepRunner._step_git_dev,
}


def format_step_status_lines(
    workspace,
    ordered_steps: tuple[str, ...],
) -> list[str]:
    from pathlib import Path

    from batch.pipeline_steps import step_display

    ws = Path(workspace)
    steps = read_state(ws).get("steps") or {}
    lines: list[str] = []
    for idx, step_id in enumerate(ordered_steps, start=1):
        status = str(steps.get(step_id) or "pending")
        icon = _STEP_ICONS.get(status, "?")
        lines.append(f"  [{idx:2}] {icon} {step_display(step_id)}")
    return lines
