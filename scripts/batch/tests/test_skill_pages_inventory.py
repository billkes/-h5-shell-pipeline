"""Tests for PM-driven skill.pages reconcile."""

from __future__ import annotations

import json
from pathlib import Path

from batch.csv_tasks import CsvTaskRow
from batch.screen_inventory import page_slugs_from_spec, route_to_page_slug
from batch.skill_pages import reconcile_pages_from_spec, run_skill_pages


TEMIOO_SPEC = """
## Screen Inventory

| Route | Layer | Purpose |
|-------|-------|---------|
| `#/splash` | H5 | Brand veil |
| `#/welcome` | H5 | Consent gate |
| `#/hub` | H5 | Tab root |
| `#/runs` | H5 | History |
| `#/settings` | H5 | Settings |
| `#/wizard/script` | H5 | Wizard 1 |
| `#/wizard/map` | H5 | Wizard 2 |
| `#/live` | H5 | Teleprompter |
| `#/run/:id` | H5 | Detail |
| `#/export` | H5 | Export |
| `#/store` | H5 | IAP |
| `#/legal` | H5 overlay | Legal |
| `#/plaza` | H5 hidden | Plaza |
| Native WebView host | Shell | Host |
"""


def _row() -> CsvTaskRow:
    return CsvTaskRow(
        name="Temioo",
        full_name="Temioo - Quiet & Gauge",
        state_management="",
        architecture_pattern="",
        naming_obfuscation_rule="",
        privacy_style="",
        privacy_file="",
        git_url="",
        first_product_code="",
        programming_style="",
        pack_type="h5_oc_shell",
        audience="大学生",
        core_scene="演讲",
        local_feature="语速",
        product_flow="wizard then live",
    )


def test_temioo_page_slugs_from_inventory() -> None:
    slugs = page_slugs_from_spec(TEMIOO_SPEC)
    assert slugs == [
        "splash",
        "welcome",
        "hub",
        "list",
        "settings",
        "wizard",
        "live",
        "detail",
        "export",
        "store",
        "legal",
        "plaza",
    ]


def test_route_to_page_slug_wizard_and_runs() -> None:
    assert route_to_page_slug("#/runs") == "list"
    assert route_to_page_slug("/wizard/map") == "wizard"
    assert route_to_page_slug("/run/:id") == "detail"


def test_run_skill_pages_h5_writes_no_default_pages(tmp_path: Path) -> None:
    ws = tmp_path / "App"
    ds = ws / "design-system" / "temioo"
    ds.mkdir(parents=True)
    (ds / "MASTER.md").write_text("# Master\n", encoding="utf-8")
    (ws / "skill-adapt").mkdir()
    (ws / "skill-adapt" / "selected-candidate.json").write_text(
        json.dumps({"candidateId": "c1", "designSystem": {"style": {"name": "X"}}}),
        encoding="utf-8",
    )
    (ws / "skill-input").mkdir()
    (ws / "skill-input" / "context.json").write_text("{}", encoding="utf-8")

    from batch.config import BatchConfig

    cfg = BatchConfig()
    run_skill_pages(cfg=cfg, workspace=ws, row=_row(), pack_type="h5_oc_shell")
    pages = list((ds / "pages").glob("*.md")) if (ds / "pages").is_dir() else []
    assert pages == []


def test_reconcile_prunes_orphans_and_adds_inventory_pages(tmp_path: Path) -> None:
    ws = tmp_path / "App"
    ds = ws / "design-system" / "temioo"
    pages_dir = ds / "pages"
    pages_dir.mkdir(parents=True)
    (ds / "MASTER.md").write_text("# Master\n", encoding="utf-8")
    (pages_dir / "orphan.md").write_text("# orphan\n", encoding="utf-8")
    (pages_dir / "hub.md").write_text("# old hub\n", encoding="utf-8")
    (ws / "功能文档.md").write_text(TEMIOO_SPEC, encoding="utf-8")
    (ws / "skill-adapt").mkdir()
    (ws / "skill-adapt" / "selected-candidate.json").write_text(
        json.dumps({"candidateId": "c1", "designSystem": {"style": {"name": "X"}}}),
        encoding="utf-8",
    )
    (ws / "skill-input").mkdir()
    (ws / "skill-input" / "context.json").write_text(
        json.dumps({"constraints": {"interactionTopologyLabel": "T4_wizard"}}),
        encoding="utf-8",
    )

    from batch.config import BatchConfig

    cfg = BatchConfig()
    messages = reconcile_pages_from_spec(
        cfg=cfg, workspace=ws, row=_row(), pack_type="h5_oc_shell"
    )
    assert any("removed orphan" in m for m in messages)
    names = sorted(p.stem for p in pages_dir.glob("*.md"))
    assert "orphan" not in names
    assert names == sorted(page_slugs_from_spec(TEMIOO_SPEC))
    assert (pages_dir / "wizard.md").is_file()
    assert (pages_dir / "live.md").is_file()
