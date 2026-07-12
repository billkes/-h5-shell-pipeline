"""Tests for h5_plaza_dev_gate strip/verify utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from batch.h5_plaza_dev_gate import (
    DEV_ENTRANCE_END,
    DEV_ENTRANCE_START,
    find_plaza_obvious_entrance,
    strip_plaza_dev_entrance,
    verify_no_plaza_dev_entrance,
)


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    return tmp_path / "h5_site"


def test_strip_removes_html_markers(vault: Path) -> None:
    vault.mkdir()
    entry = vault / "paaow_entry.htm"
    entry.write_text(
        "<body>\n"
        f"<!-- {DEV_ENTRANCE_START} -->\n"
        '<button class="c-paaow-plaza-dev-entrance" data-action="go-plaza">Plaza</button>\n'
        f"<!-- {DEV_ENTRANCE_END} -->\n"
        "<script>boot()</script>\n"
        "</body>",
        encoding="utf-8",
    )
    modified = strip_plaza_dev_entrance(vault)
    assert modified == [entry]
    text = entry.read_text(encoding="utf-8")
    assert DEV_ENTRANCE_START not in text
    assert DEV_ENTRANCE_END not in text
    assert "Plaza" not in text
    assert "boot()" in text


def test_strip_removes_js_markers(vault: Path) -> None:
    vault.mkdir()
    js = vault / "paaow_render.js"
    js.write_text(
        "function renderSettings() {\n"
        "  initVersion();\n"
        f"  /* {DEV_ENTRANCE_START} */\n"
        "  bindPlazaDevEntrance();\n"
        f"  /* {DEV_ENTRANCE_END} */\n"
        "}\n",
        encoding="utf-8",
    )
    modified = strip_plaza_dev_entrance(vault)
    assert modified == [js]
    text = js.read_text(encoding="utf-8")
    assert DEV_ENTRANCE_START not in text
    assert "bindPlazaDevEntrance" not in text
    assert "initVersion()" in text


def test_strip_ignores_files_without_markers(vault: Path) -> None:
    vault.mkdir()
    entry = vault / "paaow_entry.htm"
    entry.write_text("<body><script>boot()</script></body>", encoding="utf-8")
    modified = strip_plaza_dev_entrance(vault)
    assert modified == []


def test_verify_detects_remaining_markers(vault: Path) -> None:
    vault.mkdir()
    entry = vault / "paaow_entry.htm"
    entry.write_text(
        f"<!-- {DEV_ENTRANCE_START} -->\n"
        '<button data-action="go-plaza">Plaza</button>\n'
        f"<!-- {DEV_ENTRANCE_END} -->\n",
        encoding="utf-8",
    )
    issues = verify_no_plaza_dev_entrance(vault, vault.parent)
    assert len(issues) == 1
    assert "H5_PLAZA_DEV_ENTRANCE_START" in issues[0]


def test_find_detects_unmarked_obvious_entrance(vault: Path) -> None:
    vault.mkdir()
    entry = vault / "paaow_entry.htm"
    entry.write_text(
        '<button class="c-paaow-plaza-dev-entrance" data-action="go-plaza">Plaza</button>\n',
        encoding="utf-8",
    )
    issues = find_plaza_obvious_entrance(vault, vault.parent)
    assert len(issues) == 1
    assert "未标记的广场页明显入口" in issues[0]


def test_find_ignores_marked_entrance(vault: Path) -> None:
    vault.mkdir()
    entry = vault / "paaow_entry.htm"
    entry.write_text(
        f"<!-- {DEV_ENTRANCE_START} -->\n"
        '<button class="c-paaow-plaza-dev-entrance" data-action="go-plaza">Plaza</button>\n'
        f"<!-- {DEV_ENTRANCE_END} -->\n",
        encoding="utf-8",
    )
    issues = find_plaza_obvious_entrance(vault, vault.parent)
    assert issues == []
