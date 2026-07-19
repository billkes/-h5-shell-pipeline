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
from batch.pipeline_gates import verify_pm_ui_plan_outputs, write_plan_gate_report
from batch.pipeline_steps import (
    ANALYZE,
    AGENT_H5,
    AGENT_PLAN,
    AGENT_SHELL,
    DEV_H5_BUILD,
    LOCK_DIMENSIONS,
    PREPARE_CONTEXT,
    SKILL_ADAPT,
    SKILL_DESIGN,
    SKILL_ENRICH,
    SKILL_PAGES,
    SKILL_TOKENS,
    GIT_DEV,
    GIT_PLAN,
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

        resume_agent = step_id in (AGENT_PLAN, AGENT_SHELL, AGENT_H5) and not self.p.cfg.force_rerun

        try:
            if step_id in (AGENT_PLAN, AGENT_SHELL, AGENT_H5):
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
        """Minimal kwargs for V3 prompts (norms live in skill-input/agent-spec-index.md)."""
        from batch.workspace import dart_prefix

        h5 = is_h5_shell(ctx.pack_type)
        if h5:
            product_doc = "H5壳Flutter产品要求.md"
        elif ctx.pack_type == "tool_flutter":
            product_doc = "工具包Flutter产品要求.md"
        elif ctx.pack_type == "videostream":
            product_doc = "视频流包产品要求.md"
        else:
            product_doc = "图文包产品要求.md"

        return {
            "name": ctx.name,
            "desc": ctx.desc,
            "dart_name": ctx.dart_name,
            "prefix": dart_prefix(ctx.workspace),
            "product_req_doc": product_doc,
            "p2_product_doc": product_doc,
            "shell_runtime": h5_shell_runtime(ctx.pack_type) if h5 else "flutter",
        }

    def _step_prepare_context(self, ctx: AppContext) -> bool:
        return self.p._run_prepare_context(ctx)

    def _step_skill_design(self, ctx: AppContext) -> bool:
        return self.p._run_skill_design(ctx)

    def _step_skill_enrich(self, ctx: AppContext) -> bool:
        return self.p._run_skill_enrich(ctx)

    def _step_skill_adapt(self, ctx: AppContext) -> bool:
        return self.p._run_skill_adapt(ctx)

    def _step_skill_pages(self, ctx: AppContext) -> bool:
        return self.p._run_skill_pages(ctx)

    def _step_skill_tokens(self, ctx: AppContext) -> bool:
        return self.p._run_skill_tokens(ctx)

    def _step_lock_dimensions(self, ctx: AppContext) -> bool:
        return self.p._run_lock_dimensions(ctx)

    def _step_design_system(self, ctx: AppContext) -> bool:
        return self.p._run_skill_design(ctx)

    def _prepare_agent_prompt_files(
        self,
        ctx: AppContext,
        *,
        phase: str,
        role_slug: str,
        role_focus: str,
    ) -> None:
        from batch.agent_spec_index import prepare_agent_prompt_files

        prepare_agent_prompt_files(
            ctx.workspace,
            phase=phase,  # type: ignore[arg-type]
            app_name=ctx.name,
            pack_type=ctx.pack_type,
            role_slug=role_slug,
            role_focus=role_focus,
        )

    def _step_agent_plan(self, ctx: AppContext, *, resume: bool = False) -> bool:
        """Granular agent.plan step — Part 1 only (PM + UI + Plan + legal MDs)."""
        from batch.cursor_runner import run_agent
        from batch.prompts import _PM_UI_PLAN_BRAIN_FOCUS

        self._prepare_agent_prompt_files(
            ctx,
            phase="plan",
            role_slug="build-agent-plan",
            role_focus=_PM_UI_PLAN_BRAIN_FOCUS,
        )
        kw = self._agent_pack_context(ctx)
        prompt = self.p.prompts.build_agent_plan_only_phase(resume=resume, **kw)
        return run_agent(
            self.p.cfg,
            ctx.workspace,
            prompt,
            log_section_title=f"{ctx.name} · Agent · Plan",
        )

    def _step_agent_shell(self, ctx: AppContext, *, resume: bool = False) -> bool:
        """Granular agent.shell step — Part 2 (native/Flutter shell) + native hooks."""
        from batch.cursor_runner import run_agent
        from batch.prompts import _PROGRAMMER_BRAIN_FOCUS

        self._prepare_agent_prompt_files(
            ctx,
            phase="shell",
            role_slug="build-agent-shell",
            role_focus=_PROGRAMMER_BRAIN_FOCUS,
        )
        kw = self._agent_pack_context(ctx)
        prompt = self.p.prompts.build_agent_shell_phase(resume=resume, **kw)
        ok = run_agent(
            self.p.cfg,
            ctx.workspace,
            prompt,
            log_section_title=f"{ctx.name} · Agent · Shell",
        )
        if ok and is_native_ios_runtime(ctx.pack_type):
            try:
                from batch.csv_naming import repair_naming_rule_meta_ledgers

                for msg in repair_naming_rule_meta_ledgers(
                    ctx.workspace, batch_id=self.p._batch_id()
                ):
                    print(f">>> agent.shell: {msg}")
            except OSError as exc:
                print(f">>> agent.shell: naming meta repair skipped: {exc}")
            try:
                from batch.h5_shell_placeholders import prefix_from_workspace
                from batch.native_shell_naming import apply_native_architecture_folder_rename

                prefix = prefix_from_workspace(ctx.workspace)
                for rel in apply_native_architecture_folder_rename(
                    ctx.workspace, prefix=prefix, app_name=ctx.name
                ):
                    print(f">>> agent.shell: architecture rename → {rel}")
            except (FileExistsError, OSError) as exc:
                print(f">>> agent.shell: architecture rename skipped: {exc}")
            try:
                from batch.native_shell_obfuscation import apply_native_shell_obfuscation

                for rel in apply_native_shell_obfuscation(ctx.workspace, app_name=ctx.name):
                    print(f">>> agent.shell: native obfuscation → {rel}")
            except (FileNotFoundError, ValueError, OSError) as exc:
                print(f">>> agent.shell: native obfuscation skipped: {exc}")
            try:
                from batch.native_ios_signing import sync_workspace_ios_signing_from_registration

                for msg in sync_workspace_ios_signing_from_registration(
                    ctx.workspace, app_name=ctx.name
                ):
                    print(f">>> agent.shell: {msg}")
            except OSError as exc:
                print(f">>> agent.shell: signing sync skipped: {exc}")
        if ok:
            update_state_fields(ctx.workspace, phase_programmer_agent="done")
        return ok

    def _step_agent_h5(self, ctx: AppContext, *, resume: bool = False) -> bool:
        """Granular agent.h5 step — Part 3 (H5 Vite source / legal / overlay) + h5 hooks."""
        from batch.cursor_runner import run_agent
        from batch.prompts import _PROGRAMMER_BRAIN_FOCUS

        self._prepare_agent_prompt_files(
            ctx,
            phase="h5",
            role_slug="build-agent-h5",
            role_focus=_PROGRAMMER_BRAIN_FOCUS,
        )
        kw = self._agent_pack_context(ctx)
        prompt = self.p.prompts.build_agent_h5_phase(resume=resume, **kw)
        ok = run_agent(
            self.p.cfg,
            ctx.workspace,
            prompt,
            log_section_title=f"{ctx.name} · Agent · H5",
        )
        if ok:
            from batch.preview_fidelity_gate import verify_preview_approved_colors

            color_issues = verify_preview_approved_colors(ctx.workspace, ctx.name)
            if color_issues:
                get_run_log().fail_banner(
                    "agent.h5 后 preview-approved-colors 未通过",
                    color_issues,
                )
                return False
            from batch.h5_theme_tokens import sync_h5_global_theme

            sync_h5_global_theme(ctx.workspace, write=True)
            update_state_fields(ctx.workspace, phase_h5_agent="done")
        return ok

    def _step_prepare(self, ctx: AppContext) -> bool:
        """Legacy alias — full plan-phase prep chain."""
        return (
            self._step_prepare_context(ctx)
            and self._step_skill_design(ctx)
            and self._step_skill_adapt(ctx)
            and self._step_lock_dimensions(ctx)
        )

    def _run_plan_gate_with_repair(self, ctx: AppContext) -> tuple[bool, object]:
        """Verify PM+UI+Plan outputs; optional targeted repair rounds."""
        ws = ctx.workspace
        tool = ctx.pack_type == "tool_flutter"
        video = ctx.pack_type == "videostream"
        h5 = is_h5_shell(ctx.pack_type)

        from batch.selection_sync import sync_selection_artifacts
        from batch.interaction_topology import plan_gate_strict

        sibling_ws: list[Path] = []
        output_root = self.p.cfg.output_dir
        if output_root.is_dir():
            for pack_dir in output_root.iterdir():
                if not pack_dir.is_dir():
                    continue
                for app_dir in pack_dir.iterdir():
                    if not app_dir.is_dir() or app_dir.resolve() == ws.resolve():
                        continue
                    if (app_dir / "功能文档.md").is_file() or (app_dir / "skill-input").is_dir():
                        sibling_ws.append(app_dir)

        def _verify():
            sync_changes = sync_selection_artifacts(ws, pack_type=ctx.pack_type)
            if sync_changes:
                print(">>> Selection 产物同步（plan.gate 前）:")
                for line in sync_changes:
                    print(f"       {line}")
            row = self.p._csv_row_for(ctx)
            if row is not None and h5 and (ws / "功能文档.md").is_file():
                from batch.skill_pages import reconcile_pages_from_spec

                page_sync = reconcile_pages_from_spec(
                    cfg=self.p.cfg,
                    workspace=ws,
                    row=row,
                    pack_type=ctx.pack_type,
                )
                if page_sync:
                    print(">>> skill.pages reconcile（plan.gate 前）:")
                    for line in page_sync:
                        print(f"       {line}")
            return verify_pm_ui_plan_outputs(
                ws,
                tool_flutter=tool,
                videostream=video,
                h5_shell=h5,
                csv_full_name=self.p._csv_full_name_for(ctx),
                app_name=ctx.name,
                project_dir=self.p.cfg.project_dir,
                sibling_workspaces=sibling_ws,
            )

        strict = plan_gate_strict()
        gate_result = _verify()
        write_plan_gate_report(ws, gate_result, strict=strict)

        from batch.plan_gate_repair import (
            append_repair_history,
            build_repair_prompt,
            plan_gate_repair_enabled,
            plan_gate_repair_max_rounds,
            pick_repair_target,
        )

        max_rounds = plan_gate_repair_max_rounds()
        if plan_gate_repair_enabled() and max_rounds > 0:
            for round_no in range(1, max_rounds + 1):
                if gate_result.ok(strict=strict):
                    break
                target = pick_repair_target(hard=gate_result.hard, soft=gate_result.soft)
                if target is None:
                    break
                print(
                    f">>> plan.gate repair 轮次 {round_no}/{max_rounds} "
                    f"({target.category}): {target.issue}"
                )
                prompt = build_repair_prompt(
                    ws,
                    target,
                    app_name=ctx.name,
                    desc=ctx.desc,
                    project_dir=self.p.cfg.project_dir,
                )
                from batch.cursor_runner import run_agent

                agent_ok = run_agent(
                    self.p.cfg,
                    ws,
                    prompt,
                    log_section_title=f"{ctx.name} · Plan Gate Repair · 轮次 {round_no}",
                )
                append_repair_history(ws, round_no=round_no, target=target, ok=agent_ok)
                gate_result = _verify()
                write_plan_gate_report(ws, gate_result, strict=strict)

        return gate_result.ok(strict=strict), gate_result

    def _step_plan_gate(self, ctx: AppContext) -> bool:
        ws = ctx.workspace
        h5 = is_h5_shell(ctx.pack_type)
        from batch.interaction_topology import plan_gate_strict

        ok, gate_result = self._run_plan_gate_with_repair(ctx)
        strict = plan_gate_strict()

        if gate_result.soft:
            print(">>> PM+UI+Plan 产出物软警告（默认续跑，见 plan-gate-report.json）:")
            for issue in gate_result.soft:
                print(f"       [WARN] {issue}")

        if not ok:
            print(">>> PM+UI+Plan 产出物校验未通过（硬错误）:")
            for issue in gate_result.hard:
                print(f"       {issue}")
            if strict and gate_result.soft:
                print(">>> STRICT_PLAN_GATE=1 时软警告亦阻断:")
                for issue in gate_result.soft:
                    print(f"       {issue}")
            return False

        from batch.skill_brand import brand_check_warnings

        for warn in brand_check_warnings(ws):
            print(f"       [WARN] {warn}")

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

        row = self.p._csv_row_for(ctx)
        if row is not None and h5:
            from batch.skill_pages import sync_pages_from_spec

            synced = sync_pages_from_spec(
                cfg=self.p.cfg,
                workspace=ws,
                row=row,
                pack_type=ctx.pack_type,
            )
            if synced:
                print(">>> skill.pages sync_from_spec:")
                for line in synced:
                    print(f"       {line}")
        return True

    def _step_dev_h5_build(self, ctx: AppContext) -> bool:
        if not is_h5_shell(ctx.pack_type):
            return True
        from batch.h5_vite_build import (
            cleanup_stale_h5_site_sources,
            run_h5_vite_build,
        )
        from batch.sync_h5_legal_bundled import sync_h5_legal_bundled
        from batch.h5_theme_tokens import sync_h5_global_theme
        from batch.h5_page_scaffold import sync_h5_page_scaffold

        ws = ctx.workspace
        try:
            sync_h5_legal_bundled(ws, write=True)
        except (OSError, ValueError) as exc:
            print(f">>> dev.h5.build: legal sync failed: {exc}")
            return False

        try:
            theme_path = sync_h5_global_theme(ws, write=True)
            if theme_path is not None:
                print(f">>> dev.h5.build: synced system theme → {theme_path.relative_to(ws)}")
        except OSError as exc:
            print(f">>> dev.h5.build: theme sync failed: {exc}")

        try:
            for sp in sync_h5_page_scaffold(ws, app_name=ctx.name, write=True):
                print(f">>> dev.h5.build: page bootstrap → {sp.relative_to(ws)}")
        except OSError as exc:
            print(f">>> dev.h5.build: page scaffold sync failed: {exc}")
            return False

        for rel in cleanup_stale_h5_site_sources(ws):
            print(f">>> dev.h5.build: removed stale {rel}")

        ok, issues = run_h5_vite_build(ws)
        if not ok:
            print(">>> dev.h5.build 未通过:")
            for item in issues:
                print(f"       {item}")
        return ok


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
    SKILL_ENRICH: V3StepRunner._step_skill_enrich,
    SKILL_ADAPT: V3StepRunner._step_skill_adapt,
    SKILL_PAGES: V3StepRunner._step_skill_pages,
    SKILL_TOKENS: V3StepRunner._step_skill_tokens,
    LOCK_DIMENSIONS: V3StepRunner._step_lock_dimensions,
    AGENT_PLAN: V3StepRunner._step_agent_plan,
    AGENT_SHELL: V3StepRunner._step_agent_shell,
    AGENT_H5: V3StepRunner._step_agent_h5,
    PLAN_GATE: V3StepRunner._step_plan_gate,
    DEV_H5_BUILD: V3StepRunner._step_dev_h5_build,
    GIT_PLAN: V3StepRunner._step_git_plan,
    PUBGET: V3StepRunner._step_pubget,
    ANALYZE: V3StepRunner._step_analyze,
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
