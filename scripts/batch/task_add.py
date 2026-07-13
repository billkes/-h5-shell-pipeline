"""Simplified task fill for h5-shell-pipeline (Bridge deck + productFlow)."""

from __future__ import annotations

from pathlib import Path

from batch.config import BatchConfig
from batch.csv_tasks import fill_product_flow_to_csv
from batch.h5_shell_deck import draw_h5_shell_to_csv
from batch.task_schema import task_csv_path


def run_task_fill_simple(
    csv_path: Path,
    cfg: BatchConfig,
    *,
    batch_id: str = "",
    force: bool = False,
) -> None:
    """Draw Bridge 七维 + Kit 八维 + productFlow for h5 shells."""
    _ = force
    path = csv_path.resolve()
    bid = batch_id or cfg.batch_id
    draw_h5_shell_to_csv(path, cfg.project_dir, batch_id=bid)
    try:
        from batch.h5_kit_deck import draw_h5_kit_to_csv

        draw_h5_kit_to_csv(path, cfg.project_dir, batch_id=bid, force=force)
    except (OSError, ValueError, FileNotFoundError):
        pass
    fill_product_flow_to_csv(path)
