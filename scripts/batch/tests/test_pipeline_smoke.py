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
    assert "Monthio" in proc.stdout


def test_dry_run_single_app() -> None:
    proc = _run(["--dry-run", "--name", "Monthio"])
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "dry" in proc.stdout.lower() or "Monthio" in proc.stdout


def test_pipeline_steps_h5_swift() -> None:
    sys.path.insert(0, str(SCRIPTS))
    from batch.pipeline_steps import steps_for_run

    steps = steps_for_run(pack_type="h5_swift_shell")
    assert "agent.design" in steps
    assert "agent.plan.spec" in steps
    assert "agent.plan.docs" not in steps
    assert "agent.plan.pack" in steps
    assert "agent.shell" in steps
    assert "agent.h5" in steps
    assert "build.agent" not in steps
    assert "preview.tabs" not in steps
    assert steps.index("prepare.context") < steps.index("lock.dimensions")
    assert steps.index("lock.dimensions") < steps.index("sync.distilled")
    assert steps.index("sync.distilled") < steps.index("agent.design")
    assert steps.index("agent.design") < steps.index("agent.plan.spec")
    assert steps.index("agent.plan.spec") < steps.index("agent.plan.pack")
    assert steps.index("agent.plan.pack") < steps.index("agent.assets")
    assert steps.index("agent.assets") < steps.index("agent.shell")
    assert steps.index("agent.shell") < steps.index("agent.h5")
    assert "skill.design" not in steps
    assert "skill.pages" not in steps
    assert "skill.tokens" not in steps
    assert "dev.h5.build" in steps
    assert "dev.h5.gate" not in steps
    assert "native.check" not in steps
    assert "dev.pubget" not in steps


def test_pipeline_steps_oc_shell() -> None:
    sys.path.insert(0, str(SCRIPTS))
    from batch.pipeline_steps import steps_for_run

    steps = steps_for_run(pack_type="h5_oc_shell")
    assert "agent.plan.spec" in steps
    assert "agent.plan.docs" not in steps
    assert "agent.plan.pack" in steps
    assert "build.agent" not in steps
    assert "native.check" not in steps
    assert "dev.h5.gate" not in steps


def test_repo_container_name_native_shell() -> None:
    sys.path.insert(0, str(SCRIPTS))
    from batch.csv_tasks import repo_container_name

    assert (
        repo_container_name(
            "Buildioo",
            "https://github.com/example/Buildioo.git",
            pack_type="h5_swift_shell",
        )
        == "Buildioo-Swift"
    )
    assert (
        repo_container_name(
            "Hathoo",
            "",
            pack_type="h5_oc_shell",
        )
        == "Hathoo-OC"
    )
    assert (
        repo_container_name(
            "Pawioo",
            "",
            pack_type="h5_flutter_shell",
        )
        == "Pawioo-Flutter"
    )


def test_app_workspace_registry_entry() -> None:
    sys.path.insert(0, str(SCRIPTS))
    from batch.csv_tasks import app_workspace_registry_entry

    entry = app_workspace_registry_entry(
        ROOT / "output",
        name="Buildioo",
        pack_type="h5_swift_shell",
        git_url="https://github.com/example/Buildioo.git",
    )
    assert entry["container"] == "Buildioo-Swift"
    assert entry["workspace"].endswith("/output/Buildioo-Swift/Buildioo")
