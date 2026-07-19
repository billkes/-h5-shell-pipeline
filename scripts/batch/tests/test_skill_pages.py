"""Tests for skill_pages H5 canonical page overrides."""

from __future__ import annotations

from pathlib import Path

from batch.csv_tasks import CsvTaskRow
from batch.skill_pages import (
    CANONICAL_H5_PAGES,
    H5_PAGE_QUERY_HINTS,
    H5_PAGE_SPECS,
    _format_h5_page_override_md,
    _page_query,
    _slugify_page,
    _write_h5_page_file,
)


def _sample_row(**overrides: str) -> CsvTaskRow:
    base = dict(
        name="Buildioo",
        full_name="Buildioo - Calm & List",
        state_management="",
        architecture_pattern="",
        naming_obfuscation_rule="",
        privacy_style="",
        privacy_file="",
        git_url="",
        first_product_code="",
        programming_style="",
        pack_type="h5_swift_shell",
        audience="陪读家长",
        core_scene="开学物品准备清单与采购预算控制",
        local_feature="到期提醒记录本",
        product_flow="Pick a category chip, save entries, export weekly summary",
    )
    base.update(overrides)
    return CsvTaskRow(**base)


def _sample_ctx(**overrides: object) -> dict:
    base: dict = {
        "product": {
            "audience": "陪读家长",
            "coreScene": "开学物品准备清单与采购预算控制",
            "localFeature": "到期提醒记录本",
        },
        "constraints": {
            "interactionTopology": "T5_workspace",
            "interactionTopologyLabel": "Single workspace",
        },
        "designerSeeds": {
            "heroVisualMotif": "开学物品准备清单 · Single workspace",
            "colorTemperature": "Warm amber",
        },
    }
    base.update(overrides)
    return base


def _sample_candidate(project: str = "Buildioo") -> dict:
    return {
        "project_name": project,
        "pattern": {
            "name": "Hero + Features + CTA",
            "sections": "1. Hero, 2. Features, 3. CTA",
        },
        "style": {
            "name": "Predictive Analytics",
            "effects": "Forecast line animation on draw",
        },
    }


def test_page_query_includes_domain_hints() -> None:
    q = _page_query("Buildioo parenting checklist", "hub")
    assert "primary zone" in q
    assert H5_PAGE_QUERY_HINTS["hub"] in q


def test_canonical_h5_pages_is_template_catalog() -> None:
    assert "splash" in CANONICAL_H5_PAGES
    assert "wizard" in CANONICAL_H5_PAGES


def test_h5_page_specs_cover_known_templates() -> None:
    from batch.skill_pages import H5_PAGE_SPECS

    for slug in ("splash", "welcome", "hub", "list", "legal", "wizard", "live"):
        assert slug in H5_PAGE_SPECS


def test_slugify_page() -> None:
    assert _slugify_page("My Detail Screen") == "my-detail-screen"
    assert _slugify_page("") == "screen"


def test_splash_vs_hub_content_differs() -> None:
    row = _sample_row()
    ctx = _sample_ctx()
    cand = _sample_candidate()
    splash = _format_h5_page_override_md("splash", cand, ctx, row)
    hub = _format_h5_page_override_md("hub", cand, ctx, row)

    assert "> **Page Type:** Splash / Launch" in splash
    assert "> **Page Type:** Hub / Home Dashboard" in hub
    assert "shellReady" in splash
    assert "Scene Brief" in hub
    assert "T5_workspace" in hub or "Single workspace" in hub
    assert "开学物品准备清单与采购预算控制" in hub
    assert splash != hub


def test_welcome_and_hub_are_product_bound_not_clones() -> None:
    peopio = _sample_row(
        name="Peopio",
        audience="Busy professionals before meetings",
        core_scene="10-second people glance before elevator opens",
        local_feature="Offline rehearsal teleprompter",
        product_flow="Glance dossier; rehearse pace; export brief",
    )
    yeario = _sample_row(
        name="Yeario",
        audience="Nightly journalers",
        core_scene="One soul question before sleep",
        local_feature="Reminder ring streak",
        product_flow="Answer tonight; light the ring; export yearbook",
    )
    ctx_p = _sample_ctx(
        product={
            "audience": peopio.audience,
            "coreScene": peopio.core_scene,
            "localFeature": peopio.local_feature,
        },
        constraints={
            "interactionTopology": "T4_wizard",
            "interactionTopologyLabel": "Wizard pipeline",
        },
    )
    ctx_y = _sample_ctx(
        product={
            "audience": yeario.audience,
            "coreScene": yeario.core_scene,
            "localFeature": yeario.local_feature,
        },
        constraints={
            "interactionTopology": "T8_reminder_ring",
            "interactionTopologyLabel": "Reminder ring",
        },
    )
    welcome_p = _format_h5_page_override_md("welcome", _sample_candidate("Peopio"), ctx_p, peopio)
    welcome_y = _format_h5_page_override_md("welcome", _sample_candidate("Yeario"), ctx_y, yeario)
    hub_p = _format_h5_page_override_md("hub", _sample_candidate("Peopio"), ctx_p, peopio)
    hub_y = _format_h5_page_override_md("hub", _sample_candidate("Yeario"), ctx_y, yeario)

    assert "10-second people glance" in welcome_p
    assert "One soul question before sleep" in welcome_y
    assert welcome_p != welcome_y
    assert "T4_wizard" in hub_p
    assert "T8_reminder_ring" in hub_y
    assert "Calendar ring" in hub_y or "ring" in hub_y.lower()
    assert hub_p != hub_y
    assert "Onboarding Pattern Guidance" in welcome_p
    assert "Hub Identity Guidance" in hub_p


def test_store_and_plaza_have_distinct_semantics() -> None:
    row = _sample_row()
    ctx = _sample_ctx()
    cand = _sample_candidate()
    store = _format_h5_page_override_md("store", cand, ctx, row)
    plaza = _format_h5_page_override_md("plaza", cand, ctx, row)

    assert "consumable IAP" in store
    assert "#/plaza" in plaza
    assert "long-press version" in plaza.lower()
    assert store != plaza


def test_product_context_injected() -> None:
    row = _sample_row()
    ctx = _sample_ctx()
    text = _format_h5_page_override_md("list", _sample_candidate(), ctx, row)

    assert "## Product Context (skill.pages)" in text
    assert "陪读家长" in text
    assert "开学物品准备清单与采购预算控制" in text
    assert "Interaction topology" in text


def test_hub_navigation_uses_topology_not_uupm_pattern() -> None:
    row = _sample_row()
    ctx = _sample_ctx()
    text = _format_h5_page_override_md("hub", _sample_candidate(), ctx, row)

    assert "**Navigation pattern:** Single workspace" in text
    assert "Hero + Features + CTA" not in text.split("Navigation pattern:")[1].split("\n")[0]
    assert "**Visual tone (uupm):** Hero + Features + CTA" in text
    assert "IA source" in text


def test_cross_project_differs_by_candidate_pattern(tmp_path: Path) -> None:
    row_a = _sample_row(name="Buildioo")
    row_b = _sample_row(name="Prompio")
    ctx = _sample_ctx()
    cand_a = _sample_candidate("Buildioo")
    cand_b = {
        "project_name": "Prompio",
        "pattern": {
            "name": "Horizontal Scroll Journey",
            "sections": "1. Intro, 2. Horizontal track, 3. Footer",
        },
        "style": {
            "name": "Inclusive Design",
            "effects": "Haptic feedback, focus indicators",
        },
    }
    out_a = _format_h5_page_override_md("hub", cand_a, ctx, row_a)
    out_b = _format_h5_page_override_md("hub", cand_b, ctx, row_b)

    assert "> **PROJECT:** Buildioo" in out_a
    assert "> **PROJECT:** Prompio" in out_b
    assert "**Visual tone (uupm):** Hero + Features + CTA" in out_a
    assert "**Visual tone (uupm):** Horizontal Scroll Journey" in out_b
    assert out_a != out_b


def test_write_h5_page_file_creates_distinct_siblings(tmp_path: Path) -> None:
    pages_dir = tmp_path / "pages"
    row = _sample_row()
    ctx = _sample_ctx()
    cand = _sample_candidate()

    for page in ("splash", "welcome", "hub", "list"):
        _write_h5_page_file(pages_dir, page=page, candidate=cand, ctx=ctx, row=row)

    files = {p.name: p.read_text(encoding="utf-8") for p in pages_dir.glob("*.md")}
    assert set(files) == {"splash.md", "welcome.md", "hub.md", "list.md"}
    assert files["splash.md"] != files["hub.md"]
    assert files["welcome.md"] != files["list.md"]
