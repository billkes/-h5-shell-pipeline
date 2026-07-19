"""Tests for plan.gate soft-warning noise reduction (h5_shell)."""

from __future__ import annotations

from batch.component_kit_index import validate_selection_ids
from batch.pipeline_gates import (
    _count_export_compositions,
    _count_export_flows_in_spec,
    verify_pm_ui_plan_outputs,
)
from batch.selection_sync import _sync_welcome_layout_variant
from batch.spec_business_depth import _has_forbidden_optional_wording


def test_h5_shell_skips_non_shell_component_kit_validation() -> None:
    ids = [
        "shell/legal_modal",
        "feedback/snackbar",
        "patterns/welcome_gate",
        "shell/missing_stub",
    ]
    issues = validate_selection_ids(ids, pack_type="h5_shell")
    assert issues == ["component_kit 中未找到组件: shell/missing_stub"]


def test_flutter_still_validates_all_component_ids() -> None:
    issues = validate_selection_ids(
        ["feedback/snackbar", "patterns/welcome_gate"],
        pack_type="tool_flutter",
    )
    assert issues == ["component_kit 中未找到组件: feedback/snackbar"]


def test_export_composition_counts_table_rows() -> None:
    visual = """
## Export Card Composition

| Flow | Layer stack |
|------|-------------|
| Primary | ambient ring → header |
| Quick | ambient ring → KPI |
| Re-export | ambient ring → stamp |
"""
    assert _count_export_compositions(visual) == 3


def test_export_flow_spec_ignores_export_record_metadata() -> None:
    spec = """
## Export / Save Flow

1. **Primary card:** compose and save.
2. **Quick export:** one-tap from insights.
3. **Re-export:** reopen history row.
- **Export record:** Append ExportRecord after publish.
"""
    assert _count_export_flows_in_spec(spec) == 3


def test_spec_optional_wording_ignores_glossary_field_qualifier() -> None:
    spec = """
## Domain Glossary

| Term | Definition |
|------|------------|
| Slide Ref | Optional reference image attached to a script section |

## Primary Workflow

1. Import script.
"""
    assert not _has_forbidden_optional_wording(spec)


def test_spec_optional_wording_flags_skippable_features() -> None:
    spec = """
## Primary Workflow

1. Import script.
2. This step is optional and may be skipped.
"""
    assert _has_forbidden_optional_wording(spec)


def test_welcome_layout_variant_alias_sync() -> None:
    lock = {"welcomeSpec": {"layoutVariant": "centered-card"}}
    changes = _sync_welcome_layout_variant(lock)
    assert changes
    assert lock["welcomeSpec"]["layoutVariant"] == "hero-top-card-legal"


def test_plan_gate_dedupes_soft_warnings(tmp_path) -> None:
    workspace = tmp_path
    (workspace / "功能文档.md").write_text(
        """
# Spec
## Data Contract
## Domain Model
entity A
## Business Rules
BR-01 rule
## Primary Workflow
""" + "\n".join(f"{i}. step {i}" for i in range(1, 13)) + """
## Secondary Workflows
### Flow A
""" + "\n".join(f"{i}. s{i}" for i in range(1, 7)) + """
## State & Empty Matrix
| a | b |
## Professional Surface
### Domain Glossary
| Term | Definition |
| Slide Ref | Optional reference image |
### Metrics & Reports
| M | D | P |
| Avg | mean | run |
## 4.2 Native Offset
1. bridge pick
2. bridge save
3. bridge purchase
## Bridge Capability Matrix
| c | s | in | out | fail |
| pick | 1 | {} | {} | toast |
## Screen Inventory
| id | route |
| hub | #/hub |
| welcome | #/welcome |
| export | #/export |
## Export / Save Flow
1. Primary export
2. Quick export
3. Re-export
## IAP Catalog & Free Tier
Free tier 2
## §H5 Architecture
| Draw | Value | File |
| h5RouterPattern | hash | router |
""",
        encoding="utf-8",
    )
    (workspace / "本包登记信息.json").write_text(
        '{"packType":"h5_shell","bundleEntryPath":"h5_site/x/index.html","themeAngle":"x","codeAntiCorrelation":"y"}',
        encoding="utf-8",
    )
    (workspace / "视觉蓝图.md").write_text(
        "# Visual\n"
        + "\n".join(f"## {s}\ncontent layer stack table | a | b |\n| x | y |" for s in [
            "Ambient Canvas", "Overlay & Feedback", "Export Card Composition",
            "Confirmation Dialog Inventory", "List Row Anatomy", "Detail Page Pattern",
            "Modal Interior Spec", "Form & Input Canon", "Tag & Filter Chip Canon",
            "IAP Store Layout", "Welcome Gate Canon",
        ])
        + "\n## Component Selection\n| Kit path | Usage |\n| shell/legal_modal | legal |\n| primitives/snackbar | toast |\n"
        + "\n## Package Token Overrides\n| id | h | p | r | typo | color |\n| shell/legal_modal | k | k | k | bodyMedium | surface |\n| primitives/snackbar | k | k | k | bodyMedium | surface |\n",
        encoding="utf-8",
    )
    (workspace / "本包视觉锁.json").write_text(
        """{
  "designerDeckSelections": {"colorTemperature": "x"},
  "colorTokens": {"primary": "#000"},
  "baselineReference": "data/static/component_kit/baseline.md#h5",
  "componentSelection": ["shell/legal_modal", "primitives/snackbar"],
  "ambientCanvas": {"motifKey": "m", "scenes": {"hub": "hub"}},
  "overlayTokens": {"veil": "rgba(0,0,0,0.5)"},
  "exportCards": [{"id": "a", "width": 1, "height": 1, "layers": []}],
  "listRowSpec": {"minHeight": "56px"},
  "chipSpec": {"height": "32px"},
  "formFieldSpec": {"hintUsesSameToken": true},
  "welcomeSpec": {"layoutVariant": "centered-card", "trustBulletSource": ["a", "b"]}
}""",
        encoding="utf-8",
    )
    (workspace / "产包计划.md").write_text(
        "# Plan\n§1\n§2\n§2.x Component & Baseline Implementation Order\n| 1 | shell/legal_modal |\n§3 Final Gate flutter analyze 0 error max_analyze_fix_rounds\n§4\n§5\n" + "x" * 400,
        encoding="utf-8",
    )
    (workspace / "资源计划.md").write_text("assets " * 40, encoding="utf-8")

    result = verify_pm_ui_plan_outputs(workspace, tool_flutter=False, videostream=False, h5_shell=True)
    dupes = [m for m in result.soft if result.soft.count(m) > 1]
    assert dupes == []
    assert not any("feedback/snackbar" in m for m in result.soft)
    assert not any("layoutVariant 非法" in m for m in result.soft)
