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
from batch.tests.test_h5_legal_md_gate import sample_privacy_md, sample_terms_md


def _write_legal_md(project: Path) -> None:
    (project / "Demo Privacy Agreement.md").write_text(
        sample_privacy_md("Demo"), encoding="utf-8"
    )
    (project / "Demo User Agreement.md").write_text(
        sample_terms_md("Demo"), encoding="utf-8"
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
    project = tmp_path / "Demo"
    project.mkdir()
    reg = {
        "packType": "h5_oc_shell",
        "appSlug": "demo",
        "codeAntiCorrelation": {"dartCodePrefix": "demo"},
    }
    (project / "本包登记信息.json").write_text(json.dumps(reg), encoding="utf-8")
    privacy = sample_privacy_md("Demo").replace("## Children's Privacy\n\n", "")
    terms = sample_terms_md("Demo").replace("## Limitation of Liability\n\n", "")
    (project / "Demo Privacy Agreement.md").write_text(privacy, encoding="utf-8")
    (project / "Demo User Agreement.md").write_text(terms, encoding="utf-8")

    actions = ensure_legal_md_canon(project, write=True)
    assert "privacy +Children's Privacy" in actions
    assert "terms +Limitation of Liability" in actions
    assert "Children's Privacy" in (project / "Demo Privacy Agreement.md").read_text(encoding="utf-8")
    assert "Limitation of Liability" in (project / "Demo User Agreement.md").read_text(encoding="utf-8")

    (project / "h5" / "src" / "legal").mkdir(parents=True)
    (project / "h5" / "package.json").write_text("{}", encoding="utf-8")
    (project / "h5" / "src" / "App.vue").write_text(
        "import './legal/demo_legal_bundled.ts'\n",
        encoding="utf-8",
    )
    (project / "h5" / "src" / "router").mkdir(parents=True)
    (project / "h5" / "src" / "router" / "index.ts").write_text(
        "export const routes = [{ path: '/legal', component: {} }];\n",
        encoding="utf-8",
    )
    sync_h5_legal_bundled(project, write=True)
    assert verify_h5_legal_bundled(project) == []
