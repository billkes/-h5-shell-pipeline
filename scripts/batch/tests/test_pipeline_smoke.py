"""Quick smoke tests for h5-shell-pipeline production entrypoints."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = {"PYTHONPATH": str(SCRIPTS), **__import__("os").environ}
    return subprocess.run(
        [sys.executable, "-m", "batch", *args],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def test_batch_imports() -> None:
    sys.path.insert(0, str(SCRIPTS))
    import batch.cli  # noqa: F401
    import batch.orchestrator  # noqa: F401
    import batch.pipeline  # noqa: F401
    import batch.task_cli  # noqa: F401


def test_task_list() -> None:
    proc = _run(["task", "list"])
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "Buildioo" in proc.stdout


def test_dry_run_single_app() -> None:
    proc = _run(["--dry-run", "--name", "Buildioo"])
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "dry" in proc.stdout.lower() or "Buildioo" in proc.stdout


def test_pipeline_steps_h5_swift() -> None:
    sys.path.insert(0, str(SCRIPTS))
    from batch.pipeline_steps import steps_for_run

    steps = steps_for_run(pack_type="h5_swift_shell")
    assert "build.agent" in steps
    assert "native.check" in steps
    assert "dev.pubget" not in steps
