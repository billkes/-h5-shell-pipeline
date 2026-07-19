"""dev.h5.build compile failure → targeted H5 source repair (default max 3 rounds)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

H5_BUILD_REPORT = "h5-build-report.json"

_NON_REPAIRABLE_MARKERS: tuple[str, ...] = (
    "MISSING: npm (Node.js)",
    "MISSING: npm",
    "run lock.dimensions scaffold",
)


@dataclass
class H5BuildGateResult:
    ok: bool
    issues: list[str] = field(default_factory=list)
    build_round: int = 1


def h5_build_repair_max_rounds() -> int:
    raw = os.environ.get("H5_BUILD_REPAIR_MAX_ROUNDS", "3").strip()
    try:
        return max(0, min(5, int(raw)))
    except ValueError:
        return 3


def h5_build_repair_enabled() -> bool:
    return os.environ.get("ENABLE_H5_BUILD_REPAIR", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def is_repairable_build_failure(issues: list[str]) -> bool:
    if not issues:
        return False
    combined = "\n".join(issues)
    for marker in _NON_REPAIRABLE_MARKERS:
        if marker in combined:
            return False
    if "MISSING:" in combined and "package.json" in combined:
        return False
    return True


def build_focus_for_issues(issues: list[str]) -> str:
    combined = "\n".join(issues)
    if "build:deploy failed" in combined or "npm run build" in combined:
        return (
            "Fix TypeScript/Vue/import/rollup errors under h5/ "
            "so `npm run build:deploy` succeeds"
        )
    if "npm install failed" in combined:
        return "Fix h5/package.json or lockfile issues under h5/ only"
    if "MISSING: build output" in combined:
        return (
            "Ensure Vite build:deploy writes h5_site entry; "
            "fix h5/vite.config.ts and build scripts under h5/"
        )
    return "Fix H5 source under h5/ until Vite build:deploy passes"


def write_h5_build_report(
    workspace: Path,
    result: H5BuildGateResult,
    *,
    max_repair_rounds: int,
) -> Path:
    workspace = workspace.expanduser().resolve()
    path = workspace / H5_BUILD_REPORT
    repair_history: list = []
    if path.is_file():
        try:
            prev = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(prev, dict) and isinstance(prev.get("repairHistory"), list):
                repair_history = prev["repairHistory"]
        except json.JSONDecodeError:
            pass

    payload = {
        "maxRepairRounds": max_repair_rounds,
        "buildRound": result.build_round,
        "passed": result.ok,
        "issues": result.issues,
        "repairHistory": repair_history,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build_h5_build_repair_prompt(
    workspace: Path,
    issues: list[str],
    *,
    app_name: str,
    desc: str,
    round_no: int,
    max_rounds: int,
    project_dir: Path | None = None,
) -> str:
    from batch.agent_spec_index import (
        write_agent_spec_index,
        write_h5_build_repair_brief,
    )
    from batch.config import BatchConfig
    from batch.prompts import PromptBuilder

    cfg = BatchConfig.from_env()
    if project_dir is not None:
        cfg.project_dir = project_dir
    store = PromptBuilder(cfg)

    write_h5_build_repair_brief(
        workspace,
        issues=issues,
        focus=build_focus_for_issues(issues),
        round_no=round_no,
        max_rounds=max_rounds,
    )
    write_agent_spec_index(
        workspace,
        phase="h5_build_repair",
        app_name=app_name,
        pack_type="h5_shell",
    )

    return store._fmt(
        store._load("phase_h5_build_repair.txt"),
        {"name": app_name, "desc": desc},
    )


def append_h5_build_repair_history(
    workspace: Path,
    *,
    round_no: int,
    issues: list[str],
    agent_ok: bool,
) -> None:
    report_path = workspace / H5_BUILD_REPORT
    payload: dict = {}
    if report_path.is_file():
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
    history = list(payload.get("repairHistory") or [])
    history.append(
        {
            "round": round_no,
            "issues": issues,
            "focus": build_focus_for_issues(issues),
            "agentOk": agent_ok,
        }
    )
    payload["repairHistory"] = history
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
