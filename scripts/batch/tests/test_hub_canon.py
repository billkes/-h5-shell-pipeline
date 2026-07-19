"""Tests for Hub Home Canon plan + H5 audits."""

from __future__ import annotations

import json
from pathlib import Path

from batch.hub_canon import verify_h5_hub_canon, verify_hub_blueprint_section


def test_hub_blueprint_requires_product_bound_section() -> None:
    spec = """
## Screen Inventory
| Route | Screen | Purpose |
|-------|--------|---------|
| `#/today` | Today | Tab 1 |
"""
    empty = verify_hub_blueprint_section("# Visual\n\nNo hub section.\n", spec_text=spec)
    assert any("Hub Home Canon" in i for i in empty)

    good = """
## Hub Home Canon
| Slot | Spec |
|------|------|
| Primary zone | Workspace stamp board (T5) |
| Feed | Urgency habits for audience |
| Empty | Add first habit CTA |

Primary zone bound to coreScene month-end review for self-improvers.
Usage moment: evening check-in. Empty state keeps zone skeleton.
"""
    assert verify_hub_blueprint_section(good, spec_text=spec) == []


def test_hub_blueprint_skipped_without_tab_roots() -> None:
    spec = """
## Screen Inventory
| Route | Screen | Purpose |
|-------|--------|---------|
| `#/welcome` | Welcome | First launch |
"""
    assert verify_hub_blueprint_section("# Hub Home Canon\n\nx\n", spec_text=spec) == []


def test_h5_hub_canon_flags_generic_chip_kpi(tmp_path: Path) -> None:
    project = tmp_path / "App"
    h5 = project / "h5" / "src"
    (h5 / "views").mkdir(parents=True)
    (project / "skill-input").mkdir(parents=True)
    (project / "本包登记信息.json").write_text(
        json.dumps({"packType": "h5_swift_shell"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (project / "功能文档.md").write_text(
        "## Screen Inventory\n| Route | Screen | Purpose |\n"
        "|-------|--------|---------|\n"
        "| `#/today` | Today | Tab 1 |\n",
        encoding="utf-8",
    )
    (project / "skill-input" / "context.json").write_text(
        json.dumps(
            {
                "product": {"coreScene": "Month-end habit review"},
                "constraints": {"interactionTopology": "T5_workspace"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (project / "h5" / "package.json").write_text("{}", encoding="utf-8")
    (h5 / "views" / "TodayView.vue").write_text(
        "<template><div class='chip-rail'>chips</div>"
        "<div class='kpi-strip'>kpi</div></div></template>\n",
        encoding="utf-8",
    )

    issues = verify_h5_hub_canon(project)
    assert any("chip+KPI" in i or "primary zone" in i.lower() or "语义" in i for i in issues)
