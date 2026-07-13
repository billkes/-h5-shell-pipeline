"""Tests for sync_h5_legal_bundled Vite paths."""

from __future__ import annotations

import json
from pathlib import Path

from batch.sync_h5_legal_bundled import (
    bundled_script_rel,
    ensure_legal_md_canon,
    sync_h5_legal_bundled,
    verify_h5_legal_bundled,
)


def _write_legal_md(project: Path) -> None:
    (project / "Demo Privacy Agreement.md").write_text(
        "# Demo Privacy Agreement\n\n## Children's Privacy\n\nNo collection.\n",
        encoding="utf-8",
    )
    (project / "Demo User Agreement.md").write_text(
        "# Demo User Agreement\n\n## Limitation of Liability\n\nAs-is.\n",
        encoding="utf-8",
    )


def test_legal_sync_to_h5_src(tmp_path: Path) -> None:
    (tmp_path / "h5" / "src" / "legal").mkdir(parents=True)
    reg = {
        "packType": "h5_oc_shell",
        "codeAntiCorrelation": {"dartCodePrefix": "usfye"},
    }
    (tmp_path / "本包登记信息.json").write_text(json.dumps(reg), encoding="utf-8")
    _write_legal_md(tmp_path)

    out = sync_h5_legal_bundled(tmp_path, write=True)
    assert out == tmp_path / "h5" / "src" / "legal" / "usfye_legal_bundled.ts"
    text = out.read_text(encoding="utf-8")
    assert "export const LEGAL" in text
    assert "Children's Privacy" in text
    assert bundled_script_rel(tmp_path).as_posix().endswith(
        "h5/src/legal/usfye_legal_bundled.ts"
    )


def test_ensure_legal_md_canon_appends_required_headings(tmp_path: Path) -> None:
    reg = {
        "packType": "h5_oc_shell",
        "appSlug": "demo",
        "codeAntiCorrelation": {"dartCodePrefix": "demo"},
    }
    (tmp_path / "本包登记信息.json").write_text(json.dumps(reg), encoding="utf-8")
    (tmp_path / "Demo Privacy Agreement.md").write_text(
        "# Demo Privacy Agreement\n\n## Data Collection\n\nLocal only.\n",
        encoding="utf-8",
    )
    (tmp_path / "Demo User Agreement.md").write_text(
        "# Demo User Agreement\n\n## Contact\n\nsupport@demo.app\n",
        encoding="utf-8",
    )

    actions = ensure_legal_md_canon(tmp_path, write=True)
    assert "privacy +Children's Privacy" in actions
    assert "terms +Limitation of Liability" in actions
    assert "Children's Privacy" in (tmp_path / "Demo Privacy Agreement.md").read_text(encoding="utf-8")
    assert "Limitation of Liability" in (tmp_path / "Demo User Agreement.md").read_text(encoding="utf-8")

    (tmp_path / "h5" / "src" / "legal").mkdir(parents=True)
    (tmp_path / "h5" / "src" / "router").mkdir(parents=True)
    (tmp_path / "h5" / "src" / "router" / "index.ts").write_text(
        "export const routes = [{ path: '/legal', component: {} }];\n",
        encoding="utf-8",
    )
    sync_h5_legal_bundled(tmp_path, write=True)
    assert verify_h5_legal_bundled(tmp_path) == []
