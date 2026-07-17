"""Scan callers of body/phase methods to determine which are still live."""
import pathlib

root = pathlib.Path("scripts/batch")
targets = [
    "build_agent_impl_phase",
    "build_agent_shell_phase",
    "build_agent_h5_phase",
    "h5_implementer_phase",
    "implementer_phase",
]
for tg in targets:
    print("===", tg, "===")
    for p in root.rglob("*.py"):
        t = p.read_text(encoding="utf-8")
        for i, line in enumerate(t.splitlines(), 1):
            s = line.strip()
            if tg not in s:
                continue
            if s.startswith("#") or s.startswith('"') or s.startswith("'"):
                continue
            if s.startswith("def ") and tg in s:
                continue