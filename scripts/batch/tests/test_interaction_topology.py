"""Tests for interaction topology deck + productFlow."""

from __future__ import annotations

from pathlib import Path

from batch.interaction_topology import (
    assign_topology_for_row,
    audit_batch_topology_duplicates,
    draw_topology_for_batch,
    ensure_topology_for_app,
    generate_product_flow_for_topology,
    load_deck,
    topology_for_app,
)


def test_product_flow_not_crud_template() -> None:
    flow = generate_product_flow_for_topology(
        audience="parents",
        scene="school prep",
        feature="reminder log",
        topology_id="T8_reminder_ring",
    )
    assert "category chip" not in flow.lower()
    assert "reminder ring" in flow.lower()


def test_batch_topology_unique(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    deck_src = Path(__file__).resolve().parents[3] / "data" / "decks" / "interaction-topology-deck.json"
    (project / "data" / "decks").mkdir(parents=True)
    (project / "data" / "registry").mkdir(parents=True)
    (project / "data" / "decks" / "interaction-topology-deck.json").write_text(
        deck_src.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    cards = load_deck(project)
    used: set[str] = set()
    a = assign_topology_for_row(
        app_name="AppA",
        batch_id="B1",
        theme_code="T1",
        cards=cards,
        used_in_batch=used,
        core_scene="课堂演讲提词",
        local_feature="语速预警",
        theme_cn="课堂演讲提词器",
    )
    assert a.topology_id in ("T4_wizard", "T5_workspace")
    used.add(a.topology_id)
    b = assign_topology_for_row(
        app_name="AppB",
        batch_id="B1",
        theme_code="T2",
        cards=cards,
        used_in_batch=used,
    )
    assert a.topology_id != b.topology_id


def test_audit_duplicate_topology(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    reg = project / "data" / "registry"
    reg.mkdir(parents=True)
    (reg / "interaction-topology-ledger.json").write_text(
        """{
  "apps": {
    "A": {"topologyId": "T1_dashboard", "batchId": "B1"},
    "B": {"topologyId": "T1_dashboard", "batchId": "B1"}
  },
  "batchUsage": {"B1": ["T1_dashboard"]}
}""",
        encoding="utf-8",
    )
    issues = audit_batch_topology_duplicates(project, ["A", "B"], batch_id="B1")
    assert any("重复" in i for i in issues)


def test_ensure_topology_for_app_assigns_from_brief(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    deck_src = Path(__file__).resolve().parents[3] / "data" / "decks" / "interaction-topology-deck.json"
    (project / "data" / "decks").mkdir(parents=True)
    (project / "data" / "registry").mkdir(parents=True)
    (project / "data" / "decks" / "interaction-topology-deck.json").write_text(
        deck_src.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    card = ensure_topology_for_app(
        project,
        app_name="Buildioo",
        batch_id="TEST-0714",
        core_scene="开学物品准备清单与采购预算控制",
        local_feature="到期提醒记录本",
        theme_cn="陪读家长开学清单",
    )
    assert card is not None
    assert topology_for_app(project, "Buildioo", batch_id="TEST-0714") == card.topology_id
