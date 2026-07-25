"""Vendor ui-ux-pro-max into app workspace as real files (not host symlinks)."""

from __future__ import annotations

from pathlib import Path

from batch.config import BatchConfig
from batch.workspace import (
    CURSOR_UUPM_SKILL_REL,
    _materialize_uupm_from_bundle,
    _skill_search_ready,
    ensure_cursor_uupm_skill,
)


def test_materialize_copies_real_tree(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    (bundle / "scripts").mkdir(parents=True)
    (bundle / "data").mkdir()
    (bundle / "scripts" / "search.py").write_text("# search\n", encoding="utf-8")
    (bundle / "SKILL.md").write_text("# skill\n", encoding="utf-8")
    (bundle / "data" / "styles.csv").write_text("a\n", encoding="utf-8")

    ws = tmp_path / "App"
    ws.mkdir()
    assert _materialize_uupm_from_bundle(ws, bundle, None)
    skill = ws / CURSOR_UUPM_SKILL_REL
    assert _skill_search_ready(skill)
    assert not skill.is_symlink()
    assert not (skill / "scripts").is_symlink()
    assert (skill / "scripts" / "search.py").is_file()
    assert "ui-ux-pro-max" in (skill / "SKILL.md").read_text(encoding="utf-8") or (
        skill / "SKILL.md"
    ).is_file()


def test_ensure_cursor_uupm_skill_offline_copy(tmp_path: Path, monkeypatch) -> None:
    """When git is skipped/fails, local skill_dir still vendors real files."""
    local = tmp_path / "ui-ux-pro-max-skill"
    claude = local / ".claude" / "skills" / "ui-ux-pro-max"
    (claude / "scripts").mkdir(parents=True)
    (claude / "data").mkdir()
    (claude / "scripts" / "search.py").write_text("print(1)\n", encoding="utf-8")
    (claude / "SKILL.md").write_text(
        "---\nname: ui-ux-pro-max\n---\n\n"
        "python3 skills/ui-ux-pro-max/scripts/search.py\n",
        encoding="utf-8",
    )

    cfg = BatchConfig.from_env()
    cfg.uupm_skill_dir = str(local)
    cfg.uupm_skill_git_url = "file:///nonexistent-uupm-repo-for-test"

    monkeypatch.setattr(
        "batch.workspace._git_clone_skill_repo",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "batch.skill_resolve.resolve_skill_repo_root",
        lambda _cfg: local,
    )
    monkeypatch.setattr(
        "batch.skill_resolve.resolve_uupm_package_dir",
        lambda _cfg: claude,
    )

    ws = tmp_path / "Pack"
    ws.mkdir()
    assert ensure_cursor_uupm_skill(cfg, ws)
    skill = ws / CURSOR_UUPM_SKILL_REL
    assert _skill_search_ready(skill)
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    assert ".cursor/skills/ui-ux-pro-max/scripts/" in text
