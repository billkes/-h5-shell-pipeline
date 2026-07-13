"""Bind uupm visual outputs to CSV product + interaction topology (canonical source)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from batch.interaction_topology import card_by_id, load_deck

_CONTEXT_FILE = "skill-input/context.json"


def load_product_bind(workspace: Path) -> dict[str, Any]:
    path = workspace / _CONTEXT_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _product_fields(bind: dict[str, Any]) -> dict[str, str]:
    product = bind.get("product") or {}
    constraints = bind.get("constraints") or {}
    return {
        "audience": str(product.get("audience") or ""),
        "coreScene": str(product.get("coreScene") or ""),
        "localFeature": str(product.get("localFeature") or ""),
        "themeCn": str(product.get("themeCn") or ""),
        "productFlow": str(product.get("searchQuery") or ""),
        "topologyId": str(constraints.get("interactionTopology") or ""),
        "topologyLabel": str(constraints.get("interactionTopologyLabel") or ""),
    }


def hero_visual_motif(bind: dict[str, Any]) -> str:
    """Product-grounded motif — never raw uupm style.best_for."""
    p = _product_fields(bind)
    parts = [p["coreScene"], p["localFeature"], p["topologyLabel"]]
    text = " · ".join(x.strip() for x in parts if x and str(x).strip())
    return text[:200] if text else "Offline mobile utility — domain-specific surfaces"


def navigation_pattern_canon(
    bind: dict[str, Any],
    *,
    project_dir: Path,
    fallback: str = "",
) -> str:
    p = _product_fields(bind)
    if p["topologyLabel"]:
        return p["topologyLabel"]
    tid = p["topologyId"]
    if tid:
        card = card_by_id(load_deck(project_dir), tid)
        if card:
            return card.label
    return fallback or "Tab + stack navigation"


def topology_modules_summary(bind: dict[str, Any], project_dir: Path) -> str:
    p = _product_fields(bind)
    tid = p["topologyId"]
    if not tid:
        return ""
    card = card_by_id(load_deck(project_dir), tid)
    if not card or not card.modules:
        return ""
    lines = [f"- **{role}:** {desc}" for role, desc in card.modules.items()]
    return "\n".join(lines)


def ambient_motif_key(bind: dict[str, Any], candidate: dict[str, Any]) -> str:
    """Topology wins over style-keyword inference for ambient canvas."""
    from batch.ambient_canvas import motif_key_from_candidate

    tid = _product_fields(bind).get("topologyId") or ""
    topology_map = {
        "T8_reminder_ring": "reminder_ring",
        "T4_wizard": "wizard_pipeline",
        "T6_checklist_session": "checklist_session",
        "T3_timeline": "horizontal_journey",
        "T2_capture_first": "capture_first",
        "T1_dashboard": "dashboard_kpi",
    }
    if tid in topology_map:
        return topology_map[tid]
    return motif_key_from_candidate(candidate)


def master_category_label(bind: dict[str, Any]) -> str:
    p = _product_fields(bind)
    for val in (p["coreScene"], p["localFeature"], p["themeCn"], p["audience"]):
        if val.strip():
            return val.strip()[:80]
    app = bind.get("app") or {}
    return str(app.get("name") or "Mobile App")


def product_navigation_brief(bind: dict[str, Any], project_dir: Path) -> str:
    p = _product_fields(bind)
    lines = [
        "## Product Navigation Canon (MANDATORY — overrides uupm page pattern name)",
        "",
        f"- **Interaction topology:** {p['topologyId'] or '—'} · {p['topologyLabel'] or '—'}",
        f"- **Core scene:** {p['coreScene'] or '—'}",
        f"- **Local feature:** {p['localFeature'] or '—'}",
        f"- **Audience:** {p['audience'] or '—'}",
        "",
        "Implement navigation, hub layout, and primary workflows from **productFlow** + topology above.",
        "Candidate `pattern.name` (e.g. Lead Magnet / Enterprise SaaS) is **visual tone only**, not IA.",
        "",
    ]
    modules = topology_modules_summary(bind, project_dir)
    if modules:
        lines.append("### Topology module roles")
        lines.append(modules)
        lines.append("")
    return "\n".join(lines)


def domain_theme_boost(candidate: dict[str, Any], product_text: str) -> float:
    """Score bonus (subtracted from pick score) when domain keywords align."""
    from batch.skill_adapt import _candidate_blob, _tokenize

    pt = _tokenize(product_text)
    ct = _tokenize(_candidate_blob(candidate) + " " + str(candidate.get("category") or ""))
    boost = 0.0
    budget_terms = {
        "budget",
        "financial",
        "checklist",
        "spending",
        "tracker",
        "inventory",
        "reminder",
        "ledger",
        "school",
        "parent",
    }
    finance_style = {
        "budget",
        "financial",
        "ledger",
        "tracker",
        "accounting",
        "monitoring",
        "dashboard",
        "cash",
    }
    if pt & budget_terms and ct & finance_style:
        boost = max(boost, 0.14)
    tele_terms = {
        "teleprompter",
        "presentation",
        "speech",
        "pace",
        "wpm",
        "scroll",
        "lecture",
        "rehearsal",
        "university",
    }
    edu_style = {"academic", "education", "university", "readable", "accessible", "scholarly", "lecture"}
    if pt & tele_terms and ct & edu_style:
        boost = max(boost, 0.12)
    style_name = str((candidate.get("style") or {}).get("name") or "").lower()
    if pt & budget_terms and any(x in style_name for x in ("financial", "budget", "ledger")):
        boost = max(boost, 0.08)
    return boost
