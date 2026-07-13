"""Optional logo brief via design skill (requires gemini_api_key)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from batch.skill_resolve import resolve_subskill_dir

if TYPE_CHECKING:
    from batch.config import BatchConfig
    from batch.csv_tasks import CsvTaskRow


def maybe_write_logo_brief(
    *,
    cfg: BatchConfig,
    workspace: Path,
    row: CsvTaskRow,
) -> Path | None:
    key = (cfg.design_gemini_api_key or "").strip()
    if not key:
        return None

    design_dir = resolve_subskill_dir(cfg, "design")
    if design_dir is None:
        return None
    script = design_dir / "scripts" / "logo" / "search.py"
    if not script.is_file():
        return None

    out_dir = workspace / "resources"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "logo-brief.md"
    query = f"{row.name} {row.theme_angle or ''} {row.track or ''}".strip()
    try:
        proc = subprocess.run(
            [
                "python3",
                str(script),
                query,
                "--design-brief",
                "-p",
                row.name,
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(design_dir),
        )
        if proc.returncode == 0 and proc.stdout.strip():
            out_path.write_text(proc.stdout, encoding="utf-8")
            return out_path
    except (OSError, subprocess.SubprocessError):
        return None
    return None
