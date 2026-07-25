"""Packaging Agent path isolation (.cursorignore + forced sandbox)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from batch.config import BatchConfig
from batch.cursor_runner import _build_agent_cmd
from batch.git_ops import (
    CURSORIGNORE_HEADER,
    WORKSPACE_CURSORIGNORE_HEADER,
    ensure_agent_path_isolation,
)


def test_ensure_agent_path_isolation_writes_cursorignores(tmp_path: Path) -> None:
    repo = tmp_path / "Lensoo-Swift"
    ws = repo / "Lensoo"
    ws.mkdir(parents=True)
    ensure_agent_path_isolation(ws)
    repo_ci = (repo / ".cursorignore").read_text(encoding="utf-8")
    ws_ci = (ws / ".cursorignore").read_text(encoding="utf-8")
    assert repo_ci.startswith(CURSORIGNORE_HEADER)
    assert ws_ci.startswith(WORKSPACE_CURSORIGNORE_HEADER)
    assert "../*" in repo_ci
    assert "../../*" in repo_ci
    assert "../*" in ws_ci
    assert "../../*" in ws_ci
    # Neutral wording only — no sibling-app / copy framing.
    assert "其他" not in repo_ci
    assert "抄" not in repo_ci
    assert "sibling" not in repo_ci.lower()


def test_build_agent_cmd_always_enables_sandbox(tmp_path: Path) -> None:
    cfg = MagicMock(spec=BatchConfig)
    cfg.cursor_cli = "agent"
    cfg.cursor_agent_sandbox = False
    cfg.cursor_agent_output_format = "text"
    cfg.cursor_agent_stream_partial = False
    cmd = _build_agent_cmd(cfg, tmp_path, "hello")
    assert "--sandbox" in cmd
    assert "enabled" in cmd
    assert "--workspace" in cmd
    assert str(tmp_path.resolve()) in cmd
