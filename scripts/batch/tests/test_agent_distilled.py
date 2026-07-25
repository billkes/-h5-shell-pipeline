"""Phase 1: resolve agent-distilled absolute paths (win / mac)."""

from __future__ import annotations

from pathlib import Path

import json

from batch.agent_distilled import (
    DEFAULT_SOURCE_MAC,
    DEFAULT_SOURCE_WIN,
    DISTILLED_MANIFEST_REL,
    DISTILLED_REL,
    copy_agent_distilled,
    platform_source_dir,
    resolve_agent_distilled_source,
)
from batch.config import BatchConfig


def _cfg(**kwargs: object) -> BatchConfig:
    base = BatchConfig(
        agent_distilled_enabled=True,
        agent_distilled_source_dir="",
        agent_distilled_source_dir_win=DEFAULT_SOURCE_WIN,
        agent_distilled_source_dir_mac=DEFAULT_SOURCE_MAC,
    )
    for key, val in kwargs.items():
        setattr(base, key, val)
    return base


def test_platform_source_dir_win_and_mac() -> None:
    cfg = _cfg()
    assert platform_source_dir(cfg, platform="win32") == DEFAULT_SOURCE_WIN
    assert platform_source_dir(cfg, platform="darwin") == DEFAULT_SOURCE_MAC


def test_platform_source_dir_override_beats_os() -> None:
    cfg = _cfg(agent_distilled_source_dir=r"D:\custom\agent-distilled")
    assert platform_source_dir(cfg, platform="darwin") == r"D:\custom\agent-distilled"
    assert platform_source_dir(cfg, platform="win32") == r"D:\custom\agent-distilled"


def test_resolve_disabled_returns_none(tmp_path: Path) -> None:
    src = tmp_path / "agent-distilled"
    src.mkdir()
    cfg = _cfg(
        agent_distilled_enabled=False,
        agent_distilled_source_dir=str(src),
    )
    assert resolve_agent_distilled_source(cfg, warn=False) is None


def test_resolve_missing_returns_none_no_raise() -> None:
    cfg = _cfg(
        agent_distilled_source_dir=r"E:\__no_such_agent_distilled__",
    )
    assert resolve_agent_distilled_source(cfg, warn=False) is None


def test_resolve_existing_dir(tmp_path: Path) -> None:
    src = tmp_path / "agent-distilled"
    (src / "shared").mkdir(parents=True)
    (src / "shared" / "x.md").write_text("# x\n", encoding="utf-8")
    cfg = _cfg(agent_distilled_source_dir=str(src))
    got = resolve_agent_distilled_source(cfg, warn=False)
    assert got is not None
    assert got == src.resolve()
    assert (got / "shared" / "x.md").is_file()


def test_defaults_are_absolute() -> None:
    # Path.is_absolute() is OS-specific: POSIX /Users/... is not absolute on Windows.
    assert Path(DEFAULT_SOURCE_WIN).is_absolute()
    assert DEFAULT_SOURCE_MAC.startswith("/")
    assert "global-brain" in DEFAULT_SOURCE_WIN
    assert "agent-distilled" in DEFAULT_SOURCE_MAC
    assert "1_项目" in DEFAULT_SOURCE_WIN
    assert "1_项目" in DEFAULT_SOURCE_MAC


def test_copy_projects_role_trees_only(tmp_path: Path) -> None:
    src = tmp_path / "agent-distilled"
    (src / "shared").mkdir(parents=True)
    (src / "plan").mkdir()
    (src / "shared" / "a.md").write_text("# a\n", encoding="utf-8")
    (src / "plan" / "b.md").write_text("# b\n", encoding="utf-8")
    (src / "README.md").write_text("# human\n", encoding="utf-8")
    (src / "MANIFEST.md").write_text("# manifest\n", encoding="utf-8")

    workspace = tmp_path / "pkg"
    workspace.mkdir()
    stale = workspace / DISTILLED_REL / "old.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale\n", encoding="utf-8")

    cfg = _cfg(agent_distilled_source_dir=str(src))
    result = copy_agent_distilled(cfg, workspace, warn=False)
    assert result["ok"] is True
    assert result["skipped"] is False
    dest = workspace / DISTILLED_REL
    assert (dest / "shared" / "a.md").is_file()
    assert (dest / "plan" / "b.md").is_file()
    assert not (dest / "README.md").exists()
    assert not (dest / "MANIFEST.md").exists()
    assert not (dest / "old.md").exists()
    man = json.loads(
        (workspace / DISTILLED_MANIFEST_REL).read_text(encoding="utf-8")
    )
    assert man["file_count"] == 2
    assert "shared/a.md" in man["copied_files"]


def test_copy_missing_source_writes_skipped_manifest(tmp_path: Path) -> None:
    workspace = tmp_path / "pkg"
    workspace.mkdir()
    cfg = _cfg(
        agent_distilled_source_dir=str(tmp_path / "nope"),
    )
    result = copy_agent_distilled(cfg, workspace, warn=False)
    assert result["skipped"] is True
    assert (workspace / DISTILLED_MANIFEST_REL).is_file()
    assert not (workspace / DISTILLED_REL).exists()
