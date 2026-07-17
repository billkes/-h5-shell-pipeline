"""Dump the agent.plan prompt for a given app to a file for manual testing.

Usage:
    python -m batch.dump_agent_plan_prompt --name Monthio
    python -m batch.dump_agent_plan_prompt --name Monthio --out prompt.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from batch.config import _scripts_root

SCRIPTS_ROOT = _scripts_root()
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from batch.config import BatchConfig  # noqa: E402
from batch.csv_tasks import load_task_csv_meta, load_tasks_for_run  # noqa: E402
from batch.pipeline import AppContext, FlutterPipeline  # noqa: E402
from batch.pipeline_v3_runner import V3StepRunner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Dump agent.plan prompt")
    parser.add_argument("--name", required=True, help="App name in task.csv")
    parser.add_argument(
        "--out",
        default=None,
        help="Output file path (default: ./<name>-agent-plan-prompt.md)",
    )
    parser.add_argument("--csv", default=None, help="Task CSV path override")
    args = parser.parse_args()

    cfg = BatchConfig.from_env()
    if args.csv:
        cfg = cfg.model_copy(update={"task_csv": Path(args.csv).resolve()})

    meta = load_task_csv_meta(cfg.task_csv)
    tasks, csv_rows = load_tasks_for_run(
        cfg.task_csv, "h5_swift_shell", project_dir=cfg.project_dir
    )
    cfg.task_csv_path = cfg.task_csv
    cfg.task_csv_by_name = {r.name: r for r in csv_rows}
    cfg.batch_id = meta.batch_id

    task = next((t for t in tasks if t.name == args.name), None)
    if task is None:
        print(f"未找到应用: {args.name}")
        return 1

    row = cfg.task_csv_by_name.get(task.name)
    if row is None:
        print(f"CSV 未找到任务行: {task.name}")
        return 1

    from batch.csv_tasks import resolve_app_workspace

    ws = resolve_app_workspace(
        cfg.output_dir,
        name=task.name,
        pack_type=task.pack_type,
        git_url=row.git_url or "",
    )

    pipeline = FlutterPipeline(cfg)
    ctx = pipeline.build_context(
        task.name, task.desc, task.pack_type, ws
    )

    runner = V3StepRunner(pipeline)
    kw = runner._agent_pack_context(ctx)
    prompt = pipeline.prompts.build_agent_plan_only_phase(resume=False, **kw)

    out_path = Path(args.out) if args.out else Path(f"{args.name}-agent-plan-prompt.md")
    out_path.write_text(prompt, encoding="utf-8")

    print(f"应用: {task.name} ({task.pack_type})")
    print(f"workspace: {ctx.workspace}")
    print(f"prompt 大小: {len(prompt)} 字符")
    print(f"prompt 行数: {prompt.count(chr(10)) + 1}")
    print(f"输出文件: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())