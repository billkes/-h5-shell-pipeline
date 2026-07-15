"""Tests for per-app gitignore _preview tracking rules."""

from __future__ import annotations

from pathlib import Path

from batch.git_ops import sync_gitignore_h5_rules


def test_sync_gitignore_drops_preview_ignore(tmp_path: Path) -> None:
    repo = tmp_path / "App-Swift"
    repo.mkdir()
    (repo / ".gitignore").write_text(
        "**/h5_site/\n**/.build-state.json\n**/_preview/\n",
        encoding="utf-8",
    )
    static = tmp_path / "static"
    static.mkdir()
    (static / "忽略文件模版.md").write_text(
        "```\n**/h5_site/\n**/_preview/wallpaper/node_modules/\n```\n",
        encoding="utf-8",
    )
    assert sync_gitignore_h5_rules(repo, static) is True
    text = (repo / ".gitignore").read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines()]
    assert "**/_preview/" not in lines
    assert "**/_preview/wallpaper/node_modules/" in lines
