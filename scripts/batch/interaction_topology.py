"""Interaction topology deck — break default CRUD+export chain across batch."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DECK_NAME = "interaction-topology-deck.json"
LEDGER_NAME = "interaction-topology-ledger.json"

# Legacy unified template (batch anti-pattern).
_CRUD_TEMPLATE_RE = re.compile(
    r"pick\s+a\s+category\s+chip\s+to\s+browse.*export\s+a\s+weekly\s+summary",
    re.I | re.S,
)

_WORKFLOW_STEP_RE = re.compile(r"^\s*\d+[.)]\s+(\S.*?)$", re.M)


@dataclass(frozen=True)
class TopologyCard:
    topology_id: str
    label: str
    forbidden_landing: tuple[str, ...]
    modules: dict[str, str]


def deck_path(project_dir: Path) -> Path:
    return project_dir / "data" / "decks" / DECK_NAME


def ledger_path(project_dir: Path) -> Path:
    return project_dir / "data" / "registry" / LEDGER_NAME


def load_deck(project_dir: Path) -> list[TopologyCard]:
    path = deck_path(project_dir)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    cards: list[TopologyCard] = []
    for raw in data.get("cards") or []:
        if not isinstance(raw, dict):
            continue
        tid = str(raw.get("id") or "").strip()
        if not tid:
            continue
        cards.append(
            TopologyCard(
                topology_id=tid,
                label=str(raw.get("label") or tid),
                forbidden_landing=tuple(
                    str(x).strip().lower()
                    for x in (raw.get("forbiddenLanding") or [])
                    if str(x).strip()
                ),
                modules={
                    str(k): str(v)
                    for k, v in (raw.get("modules") or {}).items()
                    if isinstance(k, str)
                },
            )
        )
    return cards


def _load_ledger(project_dir: Path) -> dict[str, Any]:
    path = ledger_path(project_dir)
    if not path.is_file():
        return {"apps": {}, "batchUsage": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"apps": {}, "batchUsage": {}}
    if not isinstance(data, dict):
        return {"apps": {}, "batchUsage": {}}
    data.setdefault("apps", {})
    data.setdefault("batchUsage", {})
    return data


def _save_ledger(project_dir: Path, data: dict[str, Any]) -> None:
    path = ledger_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def topology_for_app(project_dir: Path, app_name: str, *, batch_id: str = "") -> str:
    """Return assigned topology id for app (empty if unknown)."""
    data = _load_ledger(project_dir)
    apps = data.get("apps") or {}
    entry = apps.get(app_name)
    if not isinstance(entry, dict):
        return ""
    tid = str(entry.get("topologyId") or "").strip()
    if batch_id and str(entry.get("batchId") or "") != batch_id:
        return tid
    return tid


def card_by_id(cards: list[TopologyCard], topology_id: str) -> TopologyCard | None:
    for card in cards:
        if card.topology_id == topology_id:
            return card
    return None


def _pick_index(seed: str, n: int, *, exclude: set[int]) -> int:
    if n <= 0:
        return 0
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    base = int(digest[:8], 16) % n
    if base not in exclude:
        return base
    for offset in range(1, n):
        candidate = (base + offset) % n
        if candidate not in exclude:
            return candidate
    return base


def assign_topology_for_row(
    *,
    app_name: str,
    batch_id: str,
    theme_code: str,
    cards: list[TopologyCard],
    used_in_batch: set[str],
) -> TopologyCard:
    """Pick topology card — batch-unique when possible."""
    if not cards:
        raise ValueError("interaction-topology-deck 为空")
    exclude: set[int] = set()
    for i, card in enumerate(cards):
        if card.topology_id in used_in_batch:
            exclude.add(i)
    seed = f"{batch_id}:{app_name}:{theme_code}"
    idx = _pick_index(seed, len(cards), exclude=exclude)
    return cards[idx]


def draw_topology_for_batch(
    csv_path: Path,
    project_dir: Path,
    *,
    batch_id: str = "",
    force: bool = False,
) -> list[str]:
    """Assign interactionTopology per task.csv row; return filled app names."""
    from batch.csv_tasks import load_task_csv_meta, load_task_csv_raw, write_task_csv_rows
    from batch.task_schema import COL_NAME, COL_THEME_CODE

    cards = load_deck(project_dir)
    if not cards:
        return []

    meta = load_task_csv_meta(csv_path)
    bid = batch_id or meta.batch_id
    _, rows_raw, fieldnames = load_task_csv_raw(csv_path)
    ledger = _load_ledger(project_dir)
    apps: dict[str, Any] = ledger.setdefault("apps", {})
    batch_usage: dict[str, list[str]] = ledger.setdefault("batchUsage", {})
    used: set[str] = set(batch_usage.get(bid) or [])

    filled: list[str] = []
    for raw in rows_raw:
        name = (raw.get(COL_NAME) or "").strip()
        if not name:
            continue
        existing = apps.get(name)
        if (
            isinstance(existing, dict)
            and existing.get("topologyId")
            and not force
            and str(existing.get("batchId") or "") == bid
        ):
            used.add(str(existing["topologyId"]))
            continue

        theme_code = (raw.get(COL_THEME_CODE) or name).strip()
        card = assign_topology_for_row(
            app_name=name,
            batch_id=bid,
            theme_code=theme_code,
            cards=cards,
            used_in_batch=used,
        )
        used.add(card.topology_id)
        apps[name] = {
            "topologyId": card.topology_id,
            "label": card.label,
            "batchId": bid,
        }
        filled.append(name)

    batch_usage[bid] = sorted(used)
    _save_ledger(project_dir, ledger)
    if filled:
        write_task_csv_rows(csv_path, meta, rows_raw, fieldnames=fieldnames)
    return filled


def generate_product_flow_for_topology(
    *,
    audience: str,
    scene: str,
    feature: str,
    topology_id: str,
    cards: list[TopologyCard] | None = None,
    project_dir: Path | None = None,
) -> str:
    """Topology-specific English productFlow (not the legacy CRUD template)."""
    card = None
    if cards:
        card = card_by_id(cards, topology_id)
    elif project_dir is not None:
        card = card_by_id(load_deck(project_dir), topology_id)

    aud = audience or "users"
    sc = scene or "daily tasks"
    feat = feature or "journal"
    tid = topology_id or "T6_checklist_session"

    templates: dict[str, str] = {
        "T1_dashboard": (
            f"Land on a {sc} dashboard with KPI tiles for {aud}; tap a metric to drill into "
            f"one {feat} record; adjust values inline; snapshot the dashboard as a share card "
            f"when review is complete."
        ),
        "T2_capture_first": (
            f"Start with Bridge photo capture to create a {feat} card for {sc}; cards stack in "
            f"an archive lane; open a card to annotate for {aud}; export a collage summary."
        ),
        "T3_timeline": (
            f"Scroll a horizontal timeline of {sc} chapters; add notes per chapter in {feat}; "
            f"jump to a chapter detail; export a date-range story card for {aud}."
        ),
        "T4_wizard": (
            f"Launch a guided wizard for {sc}: step through inputs, validate, commit to {feat}; "
            f"review the final artifact; export the completed {feat} bundle."
        ),
        "T5_workspace": (
            f"Use a single workspace canvas for {sc}: edit {feat} fields in place for {aud}; "
            f"preview changes live; export the canvas composition card."
        ),
        "T6_checklist_session": (
            f"Open a session checklist for {sc}; tick lines with budget caps in {feat}; attach "
            f"a photo per line; finish with a session report; optional weekly rollup for {aud}."
        ),
        "T7_compare_board": (
            f"Pick two {feat} items to compare {sc} side by side for {aud}; highlight deltas; "
            f"save comparison pairs; export a dual-column summary card."
        ),
        "T8_reminder_ring": (
            f"Scan a reminder ring calendar for {sc}; quick-capture into {feat}; open day agenda "
            f"for {aud}; export a period reminder card with due counts."
        ),
    }
    if card and card.topology_id in templates:
        return templates[card.topology_id]
    return templates.get(tid, templates["T6_checklist_session"])


def audit_batch_topology_duplicates(
    project_dir: Path,
    app_names: list[str],
    *,
    batch_id: str = "",
) -> list[str]:
    """task-ready hard issues when batch reuses same topology."""
    ledger = _load_ledger(project_dir)
    apps = ledger.get("apps") or {}
    seen: dict[str, str] = {}
    issues: list[str] = []
    for name in app_names:
        entry = apps.get(name)
        if not isinstance(entry, dict):
            continue
        if batch_id and str(entry.get("batchId") or "") != batch_id:
            continue
        tid = str(entry.get("topologyId") or "").strip()
        if not tid:
            continue
        owner = seen.get(tid)
        if owner and owner != name:
            issues.append(
                f"批内 interactionTopology 重复: {tid!r}（{owner} vs {name}）"
            )
        else:
            seen.setdefault(tid, name)
    return issues


def _workflow_signature(spec_text: str) -> list[str]:
    primary = ""
    match = re.search(
        r"(?is)#+\s*.*primary\s+workflow.*?\n(.*?)(?:\n#+\s|\Z)",
        spec_text,
    )
    if match:
        primary = match.group(1)
    else:
        primary = spec_text
    steps: list[str] = []
    for m in _WORKFLOW_STEP_RE.finditer(primary):
        step = re.sub(r"[^a-z0-9]+", " ", m.group(1).lower()).strip()
        if step:
            steps.append(step)
    return steps


def _jaccard(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    union = sa | sb
    if not union:
        return 0.0
    return len(sa & sb) / len(union)


def verify_flow_topology_soft_for_workspace(
    workspace: Path,
    *,
    project_dir: Path,
    sibling_workspaces: list[Path] | None = None,
) -> list[str]:
    """Soft flow checks for plan.gate."""
    issues: list[str] = []
    spec_path = workspace / "功能文档.md"
    if not spec_path.is_file():
        return issues
    spec_text = spec_path.read_text(encoding="utf-8", errors="replace")

    ctx_path = workspace / "skill-input" / "context.json"
    topology_id = ""
    product_flow = ""
    app_name = workspace.name
    if ctx_path.is_file():
        try:
            ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
            if isinstance(ctx, dict):
                app_name = str((ctx.get("app") or {}).get("name") or app_name)
                constraints = ctx.get("constraints") or {}
                topology_id = str(constraints.get("interactionTopology") or "")
                product = ctx.get("product") or {}
                product_flow = str(product.get("productFlow") or "")
        except json.JSONDecodeError:
            pass
    if not topology_id:
        topology_id = topology_for_app(project_dir, app_name)

    flow_blob = f"{product_flow}\n{spec_text}"
    if _CRUD_TEMPLATE_RE.search(flow_blob):
        issues.append(
            "[FLOW-001] 仍命中 legacy CRUD 模板（chip browse → weekly export）；"
            f"应使用 topology {topology_id or '?'} 句式"
        )

    if topology_id:
        card = card_by_id(load_deck(project_dir), topology_id)
        if card:
            lower = spec_text.lower()
            for forbidden in card.forbidden_landing:
                if forbidden and forbidden in lower:
                    issues.append(
                        f"[FLOW-002] 功能文档 landing 含禁用短语 {forbidden!r} "
                        f"（topology {topology_id}）"
                    )

    sig = _workflow_signature(spec_text)
    if sibling_workspaces:
        for sib in sibling_workspaces:
            sib_spec = sib / "功能文档.md"
            if not sib_spec.is_file() or sib.resolve() == workspace.resolve():
                continue
            other = _workflow_signature(sib_spec.read_text(encoding="utf-8", errors="replace"))
            jac = _jaccard(sig, other)
            if jac >= 0.45 and len(sig) >= 6:
                issues.append(
                    f"[FLOW-003] Primary Workflow 与 {sib.name} 步骤相似度过高 "
                    f"(Jaccard={jac:.2f})"
                )
    return issues


def plan_gate_strict() -> bool:
    return os.environ.get("STRICT_PLAN_GATE", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def format_topology_block(workspace: Path, project_dir: Path) -> str:
    """Prompt block for build.agent Part 1."""
    ctx_path = workspace / "skill-input" / "context.json"
    topology_id = ""
    label = ""
    app_name = ""
    if ctx_path.is_file():
        try:
            ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
            if isinstance(ctx, dict):
                app_name = str((ctx.get("app") or {}).get("name") or "")
                c = ctx.get("constraints") or {}
                topology_id = str(c.get("interactionTopology") or "")
                label = str(c.get("interactionTopologyLabel") or "")
        except json.JSONDecodeError:
            pass
    if not topology_id and app_name:
        topology_id = topology_for_app(project_dir, app_name)
    card = card_by_id(load_deck(project_dir), topology_id) if topology_id else None
    if not card:
        return ""
    modules = ", ".join(f"{k}={v}" for k, v in card.modules.items())
    forbidden = "; ".join(card.forbidden_landing) or "generic list-landing"
    return "\n".join(
        [
            "[Interaction Topology — MANDATORY]",
            f"- Assigned: **{card.topology_id}** ({card.label or label})",
            f"- Module roles: {modules}",
            f"- FORBIDDEN as home/landing: {forbidden}",
            "- Do NOT default to: chip filter → browse list → detail page → export weekly card.",
            "- 功能文档.md MUST include **Interaction Topology** section citing this id.",
            "- Primary Workflow must match topology (not generic CRUD).",
        ]
    )
