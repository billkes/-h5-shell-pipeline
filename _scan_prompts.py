"""Scan which Python files reference each agent prompt template."""
import pathlib

root = pathlib.Path("scripts/batch")
files = [
    "phase_build_agent.txt",
    "phase_build_agent_h5.txt",
    "phase_build_agent_shell.txt",
    "phase_pm_ui_plan.txt",
    "phase_h5_implementer.txt",
    "phase_h5_shell_programmer.txt",
]
for f in files:
    print(f"\n=== {f} ===")
    for p in root.rglob("*.py"):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if f in line and not line.strip().startswith("#"):
                rel = p.relative_to(root)
                print(f"  {rel}:{i}: {line.strip()[:120]}")
