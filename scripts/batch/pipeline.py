"""Single-app H5 shell / Flutter batch pipeline (V3 StepRunner)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from batch.batch_run_log import get_run_log
from batch.config import BatchConfig, dart_package_name
from batch.csv_architecture import apply_csv_to_code_combo
from batch.csv_tasks import CsvTaskRow
from batch.cursor_rules import write_flutter_cursor_rules
from batch.flutter_ops import (
    download_all_workspace_images,
    find_flutter_project,
)
from batch.git_ops import push_if_remote, repo_root_from_workspace, sync_phase_git
from batch.pack_type import is_flutter_runtime, is_h5_shell, is_native_ios_runtime
from batch.prompts import PromptBuilder
from batch.state import (
    PM_UI_PLAN_PHASE,
    PROGRAMMER_PHASE,
    phase_done,
    show_state,
)
from batch.visual_lock_assets import fill_visual_lock_assets
from batch.workspace import (
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

    def _run_prepare_context(self, ctx: AppContext) -> bool:
        from batch.dimension_lock import ensure_code_dimensions_locked
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
        ensure_code_dimensions_locked(
            self.cfg,
            ctx.workspace,
            row,
            dart_package_name=ctx.dart_name,
            batch_id=self._batch_id(),
        )
        write_flutter_cursor_rules(ctx.workspace, row)
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

    def _run_lock_dimensions(self, ctx: AppContext) -> bool:
        from batch.workspace import write_layout_manifest

        try:
            self._prepare_dimensions(ctx)
        except Exception as exc:
            get_run_log().detail(f"prepare_dimensions 失败: {exc}")
            return False
        if not self._prepare_programmer_workspace(ctx):
            return False
        if is_h5_shell(ctx.pack_type):
            from batch.h5_vite_scaffold import ensure_h5_vite_scaffold
            from batch.workspace import dart_prefix

            prefix = dart_prefix(ctx.workspace)
            path = ensure_h5_vite_scaffold(
                ctx.workspace,
                app_name=ctx.name,
                prefix=prefix,
                pack_type=ctx.pack_type,
            )
            if path is None:
                get_run_log().detail(
                    "h5/ Agent-owned — no template; create per docs/H5壳Vite工程规范.md"
                )
            else:
                get_run_log().detail(
                    f"h5/ present → sync helpers only ({path.relative_to(ctx.workspace)})"
                )
            from batch.h5_site_paths import sync_h5_dev_entry_urls
            from batch.h5_theme_tokens import sync_h5_global_theme

            dev_url = sync_h5_dev_entry_urls(ctx.workspace)
            if dev_url:
                get_run_log().detail(
                    f"h5 dev LAN → {dev_url} (`cd h5 && npm run dev` — use Network URL on other devices)"
                )
            theme_path = sync_h5_global_theme(ctx.workspace, write=True)
            if theme_path is not None:
                get_run_log().detail(
                    f"h5 theme → system light/dark synced ({theme_path.relative_to(ctx.workspace)})"
                )
            from batch.h5_page_scaffold import sync_h5_page_scaffold

            scaffold_paths = sync_h5_page_scaffold(
                ctx.workspace, app_name=ctx.name, write=True
            )
            for sp in scaffold_paths:
                get_run_log().detail(
                    f"h5 page bootstrap → {sp.relative_to(ctx.workspace)}"
                )
        if is_native_ios_runtime(ctx.pack_type):
            row = self._csv_row_for(ctx)
            if row is None:
                get_run_log().detail("native shell scaffold 跳过：CSV 未找到任务行")
                return False
            from batch.h5_shell_placeholders import apply_shell_placeholders
            from batch.native_shell_apply import ensure_native_shell_scaffold

            try:
                native_paths = ensure_native_shell_scaffold(
                    project_dir=self.cfg.project_dir,
                    workspace=ctx.workspace,
                    row=row,
                    bundle_id=self.cfg.xcode_bundle_id,
                    force=self.cfg.force_rerun,
                )
            except (OSError, RuntimeError) as exc:
                get_run_log().detail(f"native shell scaffold 失败: {exc}")
                return False
            for rel in native_paths:
                get_run_log().detail(f"native shell scaffold → {rel}")
            prefix = dart_prefix(ctx.workspace)
            for rel in apply_shell_placeholders(ctx.workspace, prefix=prefix, force=True):
                get_run_log().detail(f"shell placeholder → {rel}")
            from batch.native_launch_style import sync_oc_host_launch_ui

            synced = sync_oc_host_launch_ui(ctx.workspace, write=True)
            if synced is not None:
                get_run_log().detail(f"native launch UI → {synced.relative_to(ctx.workspace)}")
        write_layout_manifest(ctx.workspace, ctx.dart_name)
        row = self._csv_row_for(ctx)
        if row is not None:
            from batch.skill_logo import maybe_write_logo_brief

            maybe_write_logo_brief(cfg=self.cfg, workspace=ctx.workspace, row=row)
        return True

    def _run_design_system_step(self, ctx: AppContext) -> bool:
        """Legacy alias → skill.design."""
        return self._run_skill_design(ctx)

    def _prepare_dimensions(self, ctx: AppContext) -> None:
        """Lock CSV dimensions before any Agent phase."""
        from batch.dimension_lock import ensure_code_dimensions_locked

        row = self._csv_row_for(ctx)
        if row is None:
            raise RuntimeError(f"CSV 未找到任务行: {ctx.name}")
        ws = ctx.workspace
        ensure_code_dimensions_locked(
            self.cfg,
            ws,
            row,
            dart_package_name=ctx.dart_name,
            batch_id=self._batch_id(),
        )
        self._apply_csv_code_combo(ctx)
        write_layout_manifest(ws, ctx.dart_name)
        write_flutter_cursor_rules(ws, row)

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

    def _apply_xcode_delivery(self, ctx: AppContext) -> None:
        from batch.pack_type import h5_shell_runtime, is_native_ios_runtime

        if is_native_ios_runtime(ctx.pack_type) and h5_shell_runtime(ctx.pack_type) == "swift":
            from batch.xcode_delivery import (
                apply_workspace_ios_signing,
                regenerate_xcodegen_project,
            )

            regenerate_xcodegen_project(ctx.workspace, ctx.name)
            apply_workspace_ios_signing(self.cfg, ctx.workspace)
            return
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

    def _is_legacy_pipeline(self) -> bool:
        return self.cfg.legacy_pipeline

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

