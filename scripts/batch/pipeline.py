"""Single-app Flutter batch pipeline.

Pipeline V3 (default) — single Build Agent call + script gates (10+20 lite):

* prepare.context / skill.design / skill.adapt / lock.dimensions — scripts
* build.agent — one cursor-agent call (plan + impl + h5); resume on timeout
* plan.gate / pubget / analyze / git — scripts only

Pipeline V2 (``--legacy-pipeline``) — four roles:

* PM / UI / Programmer / Tester
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from batch.batch_run_log import get_run_log


def _log_skip_done(role: str, num: int) -> None:
    get_run_log().detail(f"跳过 {role}（断点已完成）")


def _log_skip(reason: str) -> None:
    get_run_log().detail(reason)


def _phase_running(num: int, title: str) -> float:
    get_run_log().queue(f"[{num}/{PHASE_COUNT}] {title} ⟳")
    return time.time()


def _phase_finished(
    num: int, title: str, status: str, start: float, *, note: str = ""
) -> None:
    get_run_log().phase_line(num, title, status, time.time() - start, note=note)


from batch.config import BatchConfig, dart_package_name
from batch.phase7_report_gate import phase7_test_gate_passes
from batch.phase7_test_report import build_tester_report_from_log
from batch.csv_architecture import apply_csv_to_code_combo
from batch.csv_prompt_blocks import (
    csv_architecture_block,
    csv_full_name_block,
    csv_iap_block,
    csv_naming_rule_block,
    csv_programming_style_block,
    dimension_boundary_block,
)
from batch.csv_tasks import CsvTaskRow, parse_privacy_style_number
from batch.h5_bundle_gate import print_h5_bundle_warnings, verify_h5_bundle_soft
from batch.pack_type import is_flutter_runtime, is_h5_shell
from batch.cursor_rules import write_flutter_cursor_rules
from batch.failure_notes import analyze_log_error_snippets
from batch.cursor_runner import run_agent
from batch.debug_banner import ensure_debug_banner_false

from batch.dimension_lock import (
    resolve_dimension_lock,
    write_dimension_lock,
)
from batch.visual_lock_assets import fill_visual_lock_assets
from batch.flutter_ops import (
    analyze_log_shows_success,
    count_resource_stats,
    download_all_workspace_images,
    find_flutter_project,
    run_flutter_test,
    run_pub_get_and_analyze,
)
from batch.git_ops import push_if_remote, repo_root_from_workspace, sync_phase_git
from batch.naming import meta_from_lock, transform_block_for_prompt
from batch.prompts import PromptBuilder
from batch.state import (
    PHASE_COUNT,
    PIPELINE_V3,
    PM_UI_PLAN_PHASE,
    PROGRAMMER_PHASE,
    TEST_PHASE,
    get_phase,
    init_state,
    phase_done,
    read_state,
    set_phase,
    show_state,
)
from batch.workspace import (
    alloc_code_combo,
    code_combo_block,
    copy_workspace_docs,
    dart_prefix,
    ensure_flutter_create,
    ensure_pubspec_assets,
    patch_pubspec_overrides,
    write_layout_manifest,
)
from batch.xcode_delivery import apply_xcode_delivery_settings


@dataclass
class AppContext:
    """Per-app immutable context for the pipeline."""

    name: str
    desc: str
    pack_type: str
    workspace: Path
    dart_name: str


class FlutterPipeline:
    """Run all production phases for one Flutter app workspace."""

    def __init__(self, cfg: BatchConfig) -> None:
        self.cfg = cfg
        self.prompts = PromptBuilder(cfg)

    def build_context(
        self,
        name: str,
        desc: str,
        pack_type: str,
        workspace: Path,
    ) -> AppContext:
        ws = workspace
        ws.mkdir(parents=True, exist_ok=True)
        return AppContext(
            name=name,
            desc=desc,
            pack_type=pack_type,
            workspace=ws,
            dart_name=dart_package_name(name),
        )

    def _csv_row_for(self, ctx: AppContext) -> CsvTaskRow | None:
        row = self.cfg.task_csv_by_name.get(ctx.name)
        return row if isinstance(row, CsvTaskRow) else None

    def _batch_id(self) -> str:
        if self.cfg.batch_id:
            return self.cfg.batch_id
        if self.cfg.task_csv_path is not None:
            from batch.csv_tasks import load_task_csv_meta

            try:
                meta = load_task_csv_meta(self.cfg.task_csv_path)
                if meta.batch_id:
                    return meta.batch_id
            except OSError:
                pass
        return "default"

    def _h5_shell_bridge_block_for(self, ctx: AppContext) -> str:
        row = self._csv_row_for(ctx)
        if row is None:
            return ""
        from batch.h5_shell_deck import format_h5_shell_bridge_block

        return format_h5_shell_bridge_block(row)

    def _h5_kit_block_for(self, ctx: AppContext) -> str:
        if not is_h5_shell(ctx.pack_type):
            return ""
        row = self._csv_row_for(ctx)
        if row is None:
            return ""
        from batch.h5_kit_deck import format_h5_kit_deck_block

        deck = format_h5_kit_deck_block(row)
        return self.prompts.h5_kit_block(kit_deck_block=deck)

    def _h5_shell_block_for(self, ctx: AppContext, *, programmer: bool = False) -> str:
        if not is_h5_shell(ctx.pack_type):
            return ""
        bridge = self._h5_shell_bridge_block_for(ctx)
        if programmer:
            base = self.prompts.h5_shell_programmer_block(bridge_deck_block=bridge)
        else:
            base = self.prompts.h5_shell_block(bridge_deck_block=bridge)
        row = self._csv_row_for(ctx)
        lock = resolve_dimension_lock(ctx.workspace) or {}
        naming = lock.get("namingObfuscationRule") or {}
        prefix = str(naming.get("dartCodePrefix") or "").strip()
        from batch.programming_layout import build_h5_vault_layout_prompt_block

        vault = build_h5_vault_layout_prompt_block(row, prefix=prefix, app_name=ctx.name)
        kit = self._h5_kit_block_for(ctx)
        parts = [base.strip(), vault.strip(), kit.strip()]
        return "\n\n".join(p for p in parts if p)

    def _apply_csv_code_combo(self, ctx: AppContext) -> None:
        row = self._csv_row_for(ctx)
        if row is None:
            return
        apply_csv_to_code_combo(
            ctx.workspace,
            row,
            registry_path=self.cfg.contentpack_registry,
            batch_id=self._batch_id(),
        )

    def _designer_lock_block(self, ctx: AppContext) -> str:
        from batch.skill_adapt import format_designer_lock_from_adapt

        return format_designer_lock_from_adapt(ctx.workspace)

    def _design_system_block(self, ctx: AppContext) -> str:
        from batch.skill_adapt import format_design_brief_block

        return format_design_brief_block(ctx.workspace)

    def _ambient_canvas_block(self, ctx: AppContext) -> str:
        from batch.skill_adapt import format_ambient_canvas_block

        return format_ambient_canvas_block(ctx.workspace)

    def _run_prepare_context(self, ctx: AppContext) -> bool:
        from batch.skill_context import write_skill_input

        row = self._csv_row_for(ctx)
        if row is None:
            raise RuntimeError(f"CSV 未找到任务行: {ctx.name}")
        write_skill_input(
            ctx.workspace,
            cfg=self.cfg,
            row=row,
            desc=ctx.desc,
            pack_type=ctx.pack_type,
            batch_id=self._batch_id(),
        )
        return True

    def _run_skill_design(self, ctx: AppContext) -> bool:
        row = self._csv_row_for(ctx)
        if row is None:
            raise RuntimeError(f"CSV 未找到任务行: {ctx.name}")
        from batch.uupm_design_system import run_skill_design

        try:
            master = run_skill_design(
                cfg=self.cfg,
                workspace=ctx.workspace,
                row=row,
                pack_type=ctx.pack_type,
            )
        except Exception as exc:
            from batch.batch_run_log import get_run_log

            get_run_log().detail(f"skill.design 失败: {exc}")
            print(f"skill.design 失败: {exc}")
            return False
        from batch.batch_run_log import get_run_log

        get_run_log().detail(f"skill.design → {master}")
        return True

    def _run_skill_adapt(self, ctx: AppContext) -> bool:
        row = self._csv_row_for(ctx)
        if row is None:
            raise RuntimeError(f"CSV 未找到任务行: {ctx.name}")
        from batch.uupm_design_system import run_skill_adapt_step

        try:
            brief = run_skill_adapt_step(workspace=ctx.workspace, row=row)
        except Exception as exc:
            from batch.batch_run_log import get_run_log

            get_run_log().detail(f"skill.adapt 失败: {exc}")
            print(f"skill.adapt 失败: {exc}")
            return False
        from batch.batch_run_log import get_run_log

        get_run_log().detail(f"skill.adapt → {brief}")
        return True

    def _run_skill_enrich(self, ctx: AppContext) -> bool:
        row = self._csv_row_for(ctx)
        if row is None:
            raise RuntimeError(f"CSV 未找到任务行: {ctx.name}")
        from batch.skill_enrich import run_skill_enrich

        try:
            out = run_skill_enrich(cfg=self.cfg, workspace=ctx.workspace, row=row)
        except Exception as exc:
            from batch.batch_run_log import get_run_log

            get_run_log().detail(f"skill.enrich 失败: {exc}")
            print(f"skill.enrich 失败: {exc}")
            return False
        from batch.batch_run_log import get_run_log

        get_run_log().detail(f"skill.enrich → {out}")
        return True

    def _run_skill_pages(self, ctx: AppContext) -> bool:
        row = self._csv_row_for(ctx)
        if row is None:
            raise RuntimeError(f"CSV 未找到任务行: {ctx.name}")
        from batch.skill_pages import run_skill_pages

        try:
            out = run_skill_pages(
                cfg=self.cfg,
                workspace=ctx.workspace,
                row=row,
                pack_type=ctx.pack_type,
            )
        except Exception as exc:
            from batch.batch_run_log import get_run_log

            get_run_log().detail(f"skill.pages 失败: {exc}")
            print(f"skill.pages 失败: {exc}")
            return False
        from batch.batch_run_log import get_run_log

        get_run_log().detail(f"skill.pages → {out}")
        return True

    def _run_skill_tokens(self, ctx: AppContext) -> bool:
        from batch.skill_tokens import run_skill_tokens

        try:
            out = run_skill_tokens(cfg=self.cfg, workspace=ctx.workspace)
        except Exception as exc:
            from batch.batch_run_log import get_run_log

            get_run_log().detail(f"skill.tokens 失败: {exc}")
            print(f"skill.tokens 失败: {exc}")
            return False
        from batch.batch_run_log import get_run_log

        get_run_log().detail(f"skill.tokens → {out}")
        return True

    def _ux_checklist_block(self, ctx: AppContext) -> str:
        from batch.skill_enrich import format_enrich_summary_block

        return format_enrich_summary_block(ctx.workspace, ctx.name)

    def _pages_block(self, ctx: AppContext) -> str:
        from batch.skill_pages import format_pages_block

        return format_pages_block(ctx.workspace, ctx.name)

    def _token_impl_block(self, ctx: AppContext) -> str:
        from batch.skill_tokens import format_token_impl_block

        return format_token_impl_block(ctx.workspace)

    def _css_motion_block(self, ctx: AppContext) -> str:
        from batch.skill_adapt import format_css_motion_block

        return format_css_motion_block(ctx.workspace)

    def _icon_manifest_block(self, ctx: AppContext) -> str:
        from batch.skill_adapt import format_icon_manifest_block

        return format_icon_manifest_block(ctx.workspace)

    def _run_lock_dimensions(self, ctx: AppContext) -> bool:
        from batch.workspace import write_layout_manifest

        self._prepare_dimensions(ctx)
        if not self._prepare_programmer_workspace(ctx):
            return False
        write_layout_manifest(ctx.workspace, ctx.dart_name)
        row = self._csv_row_for(ctx)
        if row is not None:
            from batch.skill_logo import maybe_write_logo_brief

            maybe_write_logo_brief(cfg=self.cfg, workspace=ctx.workspace, row=row)
            from batch.skill_adapt import refresh_icon_sprite_manifest_prefix

            if refresh_icon_sprite_manifest_prefix(ctx.workspace):
                print(">>> icon-sprite-manifest: 已同步 dartCodePrefix")
            from batch.skill_tokens import run_skill_tokens

            run_skill_tokens(cfg=self.cfg, workspace=ctx.workspace)
        return True

    def _run_design_system_step(self, ctx: AppContext) -> bool:
        """Legacy alias → skill.design."""
        return self._run_skill_design(ctx)

    def _prepare_dimensions(self, ctx: AppContext) -> None:
        """Lock CSV dimensions before any Agent phase."""
        row = self._csv_row_for(ctx)
        if row is None:
            raise RuntimeError(f"CSV 未找到任务行: {ctx.name}")
        ws = ctx.workspace
        alloc_code_combo(self.cfg, ws)
        self._apply_csv_code_combo(ctx)
        write_dimension_lock(
            ws,
            row,
            dart_package_name=ctx.dart_name,
            batch_id=self._batch_id(),
        )
        write_layout_manifest(ws, ctx.dart_name)
        write_flutter_cursor_rules(ws, row)

    def _csv_iap_block_for(self, ctx: AppContext) -> str:
        return csv_iap_block(self._csv_row_for(ctx), ctx.workspace)

    def _csv_architecture_block_for(self, ctx: AppContext) -> str:
        return csv_architecture_block(self._csv_row_for(ctx))

    def _csv_programming_style_block_for(self, ctx: AppContext) -> str:
        lock = resolve_dimension_lock(ctx.workspace) or {}
        naming = lock.get("namingObfuscationRule") or {}
        prefix = str(naming.get("dartCodePrefix") or "").strip()
        return csv_programming_style_block(
            self._csv_row_for(ctx),
            prefix=prefix,
        )

    def _csv_naming_rule_block_for(self, ctx: AppContext) -> str:
        return csv_naming_rule_block(self._csv_row_for(ctx))

    def _csv_full_name_block_for(self, ctx: AppContext) -> str:
        return csv_full_name_block(self._csv_row_for(ctx))

    def _git_remote_url(self, ctx: AppContext) -> str:
        row = self._csv_row_for(ctx)
        return (row.git_url if row else "") or ""

    def _git_sync(
        self,
        ctx: AppContext,
        phase: str,
        *,
        init: bool = False,
    ) -> None:
        if self.cfg.dry_run:
            return
        try:
            sync_phase_git(
                ctx.workspace,
                phase,
                self.cfg.static_dir,
                remote_url=self._git_remote_url(ctx),
                init=init,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            err = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
            print(f"  >>> Git 同步警告 ({phase}): {err}")

    def _git_push(self, ctx: AppContext) -> None:
        if self.cfg.dry_run:
            return
        remote = self._git_remote_url(ctx)
        if not remote:
            return
        repo_root = repo_root_from_workspace(ctx.workspace)
        try:
            push_if_remote(repo_root, remote)
        except (OSError, subprocess.CalledProcessError) as exc:
            err = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
            print(f"  >>> Git 推送警告: {err}")

    def _csv_full_name_for(self, ctx: AppContext) -> str:
        row = self._csv_row_for(ctx)
        if row is None:
            return ""
        return (row.full_name or "").strip()

    def _legal_agreement_block_for(self, ctx: AppContext, tool: bool) -> str:
        row = self._csv_row_for(ctx)
        privacy_style = "1"
        if row is not None:
            num = parse_privacy_style_number(row.privacy_style)
            if num is not None:
                privacy_style = str(num)
        main_name = ctx.name.split("-")[0].strip() if "-" in ctx.name else ctx.name
        return (
            f"\n[Legal Agreements — REQUIRED]\n"
            f"Generate TWO legal documents following 法律协议规范.md:\n"
            f"1) '{main_name} Privacy Agreement.md' — Privacy policy "
            f"(style: {privacy_style})\n"
            f"2) '{main_name} User Agreement.md' — Terms of service "
            f"(style: {privacy_style})\n"
            f"- All content in ENGLISH; no country-specific clauses;\n"
            f"  Latest Updated: May 18, 2026; Age rating 18+;\n"
            f"  Contact: {main_name}@gmail.com.\n"
            f"- Body: H1/H2/H3 + prose; NO markdown tables, lists, or block "
            f"quotes.\n"
        )

    def _naming_transform_block(self, ctx: AppContext) -> str:
        lock = resolve_dimension_lock(ctx.workspace) or {}
        naming = lock.get("namingObfuscationRule") or {}
        meta = meta_from_lock(naming.get("namingRuleMeta") if isinstance(naming, dict) else None)
        return transform_block_for_prompt(meta)

    def _apply_xcode_delivery(self, ctx: AppContext) -> None:
        fp = find_flutter_project(ctx.workspace) or ctx.workspace
        ios = fp / "ios"
        if not ios.is_dir():
            return
        apply_xcode_delivery_settings(
            self.cfg,
            ios,
            privacy_file_label=(
                self._csv_row_for(ctx).privacy_file
                if self._csv_row_for(ctx)
                else ""
            ),
        )

    def _programmer_agent_done(self, ws: Path) -> bool:
        state = read_state(ws)
        return state.get("phase4") == "done" or state.get("phase_programmer_agent") == "done"

    def _h5_agent_done(self, ws: Path) -> bool:
        return read_state(ws).get("phase_h5_agent") == "done"

    def _run_h5_implementer(self, ctx: "AppContext", fp: Path) -> bool:
        ws = ctx.workspace
        prefix = dart_prefix(ws)
        prompt = self.prompts.h5_implementer_phase(
            name=ctx.name,
            prefix=prefix,
            p2_product_doc="H5壳Flutter产品要求.md",
            h5_shell_block=self._h5_shell_block_for(ctx),
        )
        get_run_log().detail("h5_shell：运行 H5 Implementer Agent …")
        ok = run_agent(
            self.cfg,
            fp,
            prompt,
            log_section_title=f"{ctx.name} · Programmer · H5 Implementer",
        )
        if not ok:
            return False
        from batch.sync_h5_legal_bundled import sync_h5_legal_bundled, verify_h5_legal_bundled

        try:
            sync_h5_legal_bundled(fp, write=True)
            legal_issues = verify_h5_legal_bundled(fp)
            from batch.h5_legal_ui import verify_h5_legal_ui

            ui_issues = verify_h5_legal_ui(fp)
            from batch.h5_overlay_stack import verify_h5_overlay_stack

            overlay_issues = verify_h5_overlay_stack(fp)
            if legal_issues or ui_issues or overlay_issues:
                get_run_log().detail(
                    "h5_shell legal verify failed: "
                    + "; ".join((legal_issues + ui_issues + overlay_issues)[:8])
                )
                print("H5 vault verify failed:")
                for item in legal_issues + ui_issues + overlay_issues:
                    print(f"  {item}")
                return False
        except (FileNotFoundError, ValueError) as exc:
            get_run_log().detail(f"h5_shell legal sync failed: {exc}")
            print(f"H5 legal sync failed: {exc}")
            return False
        set_phase(ws, "phase_h5_agent", "done")
        warnings = verify_h5_bundle_soft(ws, fp)
        print_h5_bundle_warnings(warnings)
        return True

    def _programmer_analyze_errors_text(self, ws: Path, fp: Path) -> str:
        state = read_state(ws)
        details = state.get("phase_programmer_failure_details") or state.get(
            "phase6_failure_details"
        )
        if isinstance(details, list) and details:
            return "\n".join(str(line) for line in details)
        log = ws / "analyze.log"
        if not log.is_file():
            log_path = state.get("phase_programmer_analyze_log") or state.get(
                "phase6_analyze_log"
            )
            if log_path:
                log = Path(str(log_path))
        snippets = analyze_log_error_snippets(log)
        return "\n".join(snippets)

    def _is_legacy_pipeline(self) -> bool:
        return self.cfg.legacy_pipeline

    def _programmer_prereq_done(self, ws: Path) -> bool:
        return phase_done(ws, PM_UI_PLAN_PHASE)

    def _max_analyze_rounds(self) -> int:
        return max(1, self.cfg.max_analyze_fix_rounds)

    def dry_run_steps(self, ctx: AppContext) -> None:
        from batch.pipeline_steps import step_display, steps_for_run

        ordered = steps_for_run(
            pack_type=ctx.pack_type,
        )
        print("[dry-run] " + " → ".join(step_display(s) for s in ordered))

    def run(self, ctx: AppContext) -> str:
        if self.cfg.dry_run:
            self.dry_run_steps(ctx)
            return "dry-run"

        row = self._csv_row_for(ctx)
        first_code = (row.first_product_code if row else "") or ""
        copy_workspace_docs(
            self.cfg,
            ctx.workspace,
            ctx.name,
            ctx.pack_type,
            first_product_code=first_code,
        )

        if self._is_legacy_pipeline():
            raise RuntimeError(
                "--legacy-pipeline 已退役；V3 流水线默认使用 skill.design + build.agent"
            )
        else:
            from batch.pipeline_v3_runner import V3StepRunner

            runner = V3StepRunner(self)
            runner.ensure_state(ctx)
            show_state(ctx.workspace)
            runner.run_all(
                ctx,
                step_ids=self.cfg.pipeline_step_ids,
                continue_from=self.cfg.pipeline_step_continue,
                rerun=self.cfg.pipeline_step_rerun,
            )

        self._git_push(ctx)
        return self._run_result_icon(ctx)

    def _run_result_icon(self, ctx: AppContext) -> str:
        ws = ctx.workspace
        if phase_done(ws, PROGRAMMER_PHASE):
            return "✅"
        if phase_done(ws, PM_UI_PLAN_PHASE):
            return "🟡"
        return "❌"

    def _prepare_programmer_workspace(self, ctx: AppContext) -> bool:
        """Script prep before Programmer Agent: Flutter scaffold when needed + assets."""
        ws = ctx.workspace
        if is_flutter_runtime(ctx.pack_type):
            ok = ensure_flutter_create(ws, ctx.dart_name)
            ensure_pubspec_assets(ws)
            patch_pubspec_overrides(ws)
            if not ok:
                return False
            fp = find_flutter_project(ws) or ws
        else:
            fp = ws
        tool = ctx.pack_type == "tool_flutter"
        video = ctx.pack_type == "videostream"
        h5 = is_h5_shell(ctx.pack_type)
        if self.cfg.skip_images:
            get_run_log().detail("跳过占位图生成 (--skip-images)")
        else:
            get_run_log().detail("预下载内容配图 ...")
            download_all_workspace_images(
                self.cfg,
                ws,
                fp,
                ctx.name,
                tool_flutter=tool,
                videostream=video,
                h5_shell=h5,
            )
        if (ws / "本包视觉锁.json").is_file() and not h5:
            fill_visual_lock_assets(ws, fp, ctx.name)
        return True

    def _execute_analyze_gate(
        self, ctx: AppContext, fp: Path, *, log: Path | None = None
    ) -> tuple[bool, list[str], int, int]:
        """Run pub get + analyze; return (ok, error_snippets, total_images, placeholders)."""
        ws = ctx.workspace
        self._apply_xcode_delivery(ctx)
        patch_pubspec_overrides(fp)
        banner_fixed = ensure_debug_banner_false(fp)
        if banner_fixed:
            get_run_log().detail(f"已自动关闭 DEBUG 角标: {', '.join(banner_fixed)}")

        analyze_log = log or (ws / "analyze.log")
        ok = run_pub_get_and_analyze(
            fp,
            analyze_log,
            pub_get_max_retries=self.cfg.pub_get_max_retries,
        )
        if not ok and analyze_log_shows_success(analyze_log):
            ok = True
        if ok and not analyze_log_shows_success(analyze_log):
            ok = False
        total, placeholder = count_resource_stats(
            fp,
            videostream=ctx.pack_type == "videostream",
            tool_flutter=ctx.pack_type == "tool_flutter",
        )
        errors: list[str] = []
        if not ok:
            errors = analyze_log_error_snippets(analyze_log)
            get_run_log().fail_banner(
                "flutter pub get / analyze 未通过",
                errors or [f"详见 {analyze_log}"],
            )
        return ok, errors, total, placeholder

    def _run_programmer_analyze_gate(self, ctx: AppContext, fp: Path) -> bool:
        ws = ctx.workspace
        log = ws / "analyze.log"
        ok, analyze_errors, total, placeholder = self._execute_analyze_gate(ctx, fp, log=log)
        if not ok:
            set_phase(
                ws,
                PROGRAMMER_PHASE,
                "failed",
                phase_programmer_image_total=total,
                phase_programmer_image_placeholder=placeholder,
                phase_programmer_failure_reason="flutter pub get / analyze 未通过",
                phase_programmer_failure_details=analyze_errors,
                phase_programmer_analyze_log=str(log.resolve()),
                phase6_failure_reason="flutter pub get / analyze 未通过",
                phase6_failure_details=analyze_errors,
                phase6_analyze_log=str(log.resolve()),
            )
            return False
        set_phase(
            ws,
            PROGRAMMER_PHASE,
            "done",
            phase_programmer_image_total=total,
            phase_programmer_image_placeholder=placeholder,
            phase6_image_total=total,
            phase6_image_placeholder=placeholder,
        )
        return True

    def _phase_programmer(self, ctx: AppContext) -> None:
        ws = ctx.workspace
        if phase_done(ws, PROGRAMMER_PHASE):
            _log_skip_done("Programmer", 3)
            return
        if not self._programmer_prereq_done(ws):
            label = "UI" if self._is_legacy_pipeline() else "PM+UI+Plan"
            _log_skip(f"{label} 未完成，跳过 Programmer")
            set_phase(ws, PROGRAMMER_PHASE, "skipped")
            return

        set_phase(ws, PROGRAMMER_PHASE, "running")
        start = _phase_running(3, "Programmer")
        fp = find_flutter_project(ws) or ws
        agent_done = self._programmer_agent_done(ws)
        max_rounds = self._max_analyze_rounds()

        if not agent_done:
            if not self._prepare_programmer_workspace(ctx):
                set_phase(
                    ws,
                    PROGRAMMER_PHASE,
                    "failed",
                    phase_programmer_failure_reason="工程准备失败",
                )
                _phase_finished(3, "Programmer", "failed", start, note="prep")
                return

            write_layout_manifest(ws, ctx.dart_name)
            prefix = dart_prefix(ws)
            tool = ctx.pack_type == "tool_flutter"
            h5 = is_h5_shell(ctx.pack_type)
            content_preview = ""
            cl = ws / "默认内容列表.json"
            if cl.is_file():
                content_preview = cl.read_text(encoding="utf-8")[:5000]

            if h5:
                p2_doc = "H5壳Flutter产品要求.md"
                p2_video = ""
            elif ctx.pack_type == "videostream":
                p2_doc = "视频流包产品要求.md"
                p2_video = "\n[VIDEO STREAM PACK — videostream type]"
            elif tool:
                p2_doc = "工具包Flutter产品要求.md"
                p2_video = ""
            else:
                p2_doc = "图文包产品要求.md"
                p2_video = ""

            if h5:
                prompt = self.prompts.h5_shell_programmer_phase(
                    name=ctx.name,
                    dart_name=ctx.dart_name,
                    prefix=prefix,
                    p2_product_doc=p2_doc,
                    csv_iap_block=self._csv_iap_block_for(ctx),
                    csv_architecture_block=self._csv_architecture_block_for(ctx),
                    csv_programming_style_block=self._csv_programming_style_block_for(ctx),
                    csv_naming_rule_block=self._csv_naming_rule_block_for(ctx),
                    naming_transform_block=self._naming_transform_block(ctx),
                    dimension_boundary_block=dimension_boundary_block(),
                    h5_shell_block=self._h5_shell_block_for(ctx, programmer=True),
                )
            else:
                prompt = self.prompts.implementer_phase(
                    name=ctx.name,
                    tool_flutter=tool,
                    dart_name=ctx.dart_name,
                    prefix=prefix,
                    content_list=content_preview,
                    p2_product_doc=p2_doc,
                    csv_iap_block=self._csv_iap_block_for(ctx),
                    csv_architecture_block=self._csv_architecture_block_for(ctx),
                    csv_programming_style_block=self._csv_programming_style_block_for(ctx),
                    csv_naming_rule_block=self._csv_naming_rule_block_for(ctx),
                    naming_transform_block=self._naming_transform_block(ctx),
                    dimension_boundary_block=dimension_boundary_block(),
                    p2_video_hint=p2_video,
                    h5_shell_block="",
                )
            agent_ok = run_agent(
                self.cfg,
                ws,
                prompt,
                log_section_title=f"{ctx.name} · Programmer · 实现",
            )
            if not agent_ok:
                set_phase(
                    ws,
                    PROGRAMMER_PHASE,
                    "failed",
                    phase_programmer_failure_reason="Agent 未成功",
                )
                _phase_finished(3, "Programmer", "failed", start, note="agent")
                return
            set_phase(ws, "phase_programmer_agent", "done")
            self._git_sync(ctx, PROGRAMMER_PHASE, init=True)
        elif agent_done and not phase_done(ws, PROGRAMMER_PHASE):
            get_run_log().detail(
                "断点：实现 Agent 已完成，进入 analyze gate / 修复循环"
            )

        if not (fp / "pubspec.yaml").is_file():
            set_phase(
                ws,
                PROGRAMMER_PHASE,
                "failed",
                phase_programmer_failure_reason="缺少 pubspec.yaml",
            )
            _phase_finished(3, "Programmer", "failed", start)
            return

        h5 = is_h5_shell(ctx.pack_type)
        for iteration in range(1, max_rounds + 1):
            if self._run_programmer_analyze_gate(ctx, fp):
                if h5 and not self._h5_agent_done(ws):
                    if not self._run_h5_implementer(ctx, fp):
                        set_phase(
                            ws,
                            PROGRAMMER_PHASE,
                            "failed",
                            phase_programmer_failure_reason="H5 Implementer Agent 未成功",
                        )
                        _phase_finished(3, "Programmer", "failed", start, note="h5-agent")
                        return
                    self._git_sync(ctx, PROGRAMMER_PHASE)
                elif h5:
                    print_h5_bundle_warnings(verify_h5_bundle_soft(ws, fp))
                self._git_sync(ctx, PROGRAMMER_PHASE)
                _phase_finished(3, "Programmer", "done", start)
                return

            if iteration >= max_rounds:
                _phase_finished(3, "Programmer", "failed", start, note="analyze")
                return

            errors_text = self._programmer_analyze_errors_text(ws, fp)[:4000]
            get_run_log().detail(
                f"analyze 未通过，打回 Programmer 修复 (第 {iteration}/{max_rounds} 轮)"
            )
            fix_prompt = self.prompts.programmer_analyze_fix_phase(
                name=ctx.name,
                desc=ctx.desc,
                analyze_errors=errors_text,
            )
            fix_ok = run_agent(
                self.cfg,
                fp,
                fix_prompt,
                log_section_title=(
                    f"{ctx.name} · Programmer · analyze 修复 "
                    f"({iteration}/{max_rounds})"
                ),
            )
            if not fix_ok:
                set_phase(
                    ws,
                    PROGRAMMER_PHASE,
                    "failed",
                    phase_programmer_failure_reason="analyze 修复 Agent 调用失败",
                    phase_programmer_failure_details=[
                        f"iteration {iteration}/{max_rounds}"
                    ],
                )
                _phase_finished(3, "Programmer", "failed", start, note="fix-agent")
                return
            self._git_sync(ctx, PROGRAMMER_PHASE)

    def _run_flutter_test(self, flutter_dir: Path) -> bool:
        log = flutter_dir.parent / "build" / "phase7_flutter_test.log"
        result = run_flutter_test(
            flutter_dir,
            log,
            timeout_sec=self.cfg.flutter_test_timeout_sec,
            per_test_timeout=self.cfg.flutter_test_per_test_timeout,
            concurrency=self.cfg.flutter_test_concurrency,
            test_paths=self.cfg.flutter_test_paths,
        )
        if result == "done":
            return True
        if result == "skipped":
            get_run_log().detail("未检测到测试文件，跳过程序员修复循环")
            return True
        get_run_log().detail(f"flutter test 失败，日志: {log}")
        return False

    def _write_tester_report_from_log(
        self,
        fp: Path,
        *,
        app_name: str,
        iteration: int,
    ) -> str:
        test_log = fp.parent / "build" / "phase7_flutter_test.log"
        log_text = (
            test_log.read_text(encoding="utf-8", errors="replace")
            if test_log.is_file()
            else ""
        )
        report_text = build_tester_report_from_log(
            log_text,
            app_name=app_name,
            iteration=iteration,
        )
        test_report = fp / "test" / "tester-report.md"
        test_report.parent.mkdir(parents=True, exist_ok=True)
        test_report.write_text(report_text, encoding="utf-8")
        return report_text

    def _re_analyze_after_fix(self, ctx: AppContext) -> bool:
        ws = ctx.workspace
        fp = find_flutter_project(ws) or ws
        if not (fp / "pubspec.yaml").is_file():
            set_phase(ws, PROGRAMMER_PHASE, "failed")
            return False
        log = ws / "build" / "phase7_reanalyze.log"
        ok = run_pub_get_and_analyze(
            fp,
            log,
            pub_get_max_retries=self.cfg.pub_get_max_retries,
        )
        if not ok and analyze_log_shows_success(log):
            ok = True
        if ok and not analyze_log_shows_success(log):
            ok = False
        if not ok:
            set_phase(ws, PROGRAMMER_PHASE, "failed")
        return ok

    def _phase_tester(self, ctx: AppContext) -> None:
        ws = ctx.workspace
        if not phase_done(ws, PROGRAMMER_PHASE):
            if not phase_done(ws, TEST_PHASE):
                set_phase(ws, TEST_PHASE, "skipped")
            return
        if phase_done(ws, TEST_PHASE):
            _log_skip_done("Tester", 4)
            return

        fp = find_flutter_project(ws) or ws
        max_rounds = max(1, self.cfg.max_test_fix_rounds)
        previous_failures = ""

        for iteration in range(1, max_rounds + 1):
            set_phase(ws, TEST_PHASE, "running")
            start = time.time()
            print(f"  [4/{PHASE_COUNT}] 测试员 (第 {iteration}/{max_rounds} 轮) ...")

            prompt = self.prompts.tester_phase(
                name=ctx.name,
                desc=ctx.desc,
                iteration=iteration,
                previous_failures=previous_failures,
                flutter_project=fp,
            )
            ok = run_agent(
                self.cfg,
                fp,
                prompt,
                log_section_title=(
                    f"{ctx.name} · Tester · 第 {iteration}/{max_rounds} 轮"
                ),
            )

            if not ok:
                get_run_log().detail("警告: 测试员 Agent 调用失败")
                set_phase(
                    ws,
                    TEST_PHASE,
                    "failed",
                    phase_tester_failure_reason="测试员 Agent 调用失败",
                    phase7_failure_reason="测试员 Agent 调用失败",
                )
                return

            flutter_ok = self._run_flutter_test(fp)
            report_text = self._write_tester_report_from_log(
                fp,
                app_name=ctx.name,
                iteration=iteration,
            )
            test_report = fp / "test" / "tester-report.md"
            if phase7_test_gate_passes(flutter_ok=flutter_ok, report_text=report_text):
                set_phase(ws, TEST_PHASE, "done")
                self._git_sync(ctx, TEST_PHASE)
                print(f"  [4/{PHASE_COUNT}] 完成 (耗时 {int(time.time() - start)}s)")
                return

            get_run_log().detail(f"测试未通过，进入程序员修复 (第 {iteration} 轮)")
            previous_failures = report_text[:4000]

            fix_prompt = self.prompts.programmer_fix_phase(
                name=ctx.name,
                desc=ctx.desc,
                test_report=previous_failures,
            )
            fix_ok = run_agent(
                self.cfg,
                fp,
                fix_prompt,
                log_section_title=(
                    f"{ctx.name} · Tester · 程序员修复 "
                    f"({iteration}/{max_rounds})"
                ),
            )
            if not fix_ok:
                get_run_log().detail("警告: 程序员修复 Agent 调用失败")
                set_phase(
                    ws,
                    TEST_PHASE,
                    "failed",
                    phase_tester_failure_reason="程序员修复 Agent 调用失败",
                    phase_tester_failure_details=[f"iteration {iteration}/{max_rounds}"],
                    phase_tester_report=str(test_report.resolve()),
                    phase7_failure_reason="程序员修复 Agent 调用失败",
                    phase7_failure_details=[f"iteration {iteration}/{max_rounds}"],
                    phase7_tester_report=str(test_report.resolve()),
                )
                return

            if not self._re_analyze_after_fix(ctx):
                get_run_log().detail("警告: 修复后 analyze 未通过")
                set_phase(
                    ws,
                    TEST_PHASE,
                    "failed",
                    phase_tester_failure_reason="修复后 analyze 未通过",
                    phase_tester_failure_details=[f"iteration {iteration}/{max_rounds}"],
                    phase_tester_report=str(test_report.resolve()),
                    phase7_failure_reason="修复后 analyze 未通过",
                    phase7_failure_details=[f"iteration {iteration}/{max_rounds}"],
                    phase7_tester_report=str(test_report.resolve()),
                )
                return

        get_run_log().detail(f"测试员在 {max_rounds} 轮内未能全部通过")
        test_log = fp.parent / "build" / "phase7_flutter_test.log"
        tester_report = fp / "test" / "tester-report.md"
        failure_details = [f"共 {max_rounds} 轮仍未全部通过"]
        if previous_failures:
            failure_details.append(previous_failures.splitlines()[0][:200])
        set_phase(
            ws,
            TEST_PHASE,
            "failed",
            phase_tester_failure_reason=f"测试员在 {max_rounds} 轮内未能全部通过",
            phase_tester_failure_details=failure_details,
            phase_tester_test_log=str(test_log.resolve()) if test_log.is_file() else "",
            phase_tester_report=str(tester_report.resolve()) if tester_report.is_file() else "",
            phase7_failure_reason=f"测试员在 {max_rounds} 轮内未能全部通过",
            phase7_failure_details=failure_details,
            phase7_test_log=str(test_log.resolve()) if test_log.is_file() else "",
            phase7_tester_report=str(tester_report.resolve()) if tester_report.is_file() else "",
        )
        print(f"  [4/{PHASE_COUNT}] 完成 (耗时 {int(time.time() - start)}s)")
