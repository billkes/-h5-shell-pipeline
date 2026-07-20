"""Product-bound Welcome / Tab1 (hub) page specs — generate rules, not fixed templates.

Inputs: coreScene · audience · productFlow · interactionTopology · heroVisualMotif
Output: per-pack page override fragments for skill.pages.
"""

from __future__ import annotations

import re
from typing import Any

# Topology → Tab1 primary-zone guidance (labels only; Agent invents concrete UI).
TOPOLOGY_HUB_PATTERNS: dict[str, dict[str, str]] = {
    "T1_dashboard": {
        "primary_zone": "KPI / metric board as first scan target",
        "feed_style": "stat-first with drill-down to detail",
        "forbidden": "category-chip browse as sole home",
        "markers": "kpi|metric|dashboard|gauge|stat",
    },
    "T2_capture_first": {
        "primary_zone": "Dominant capture / compose entry above archive",
        "feed_style": "reverse-chronological captures",
        "forbidden": "browse-list landing without capture affordance",
        "markers": "capture|compose|quick.add|fab|input",
    },
    "T3_timeline": {
        "primary_zone": "Vertical timeline / chapter spine",
        "feed_style": "chronological journey markers",
        "forbidden": "flat data-table list as home",
        "markers": "timeline|chapter|journey|spine",
    },
    "T4_wizard": {
        "primary_zone": "Active draft / pipeline entry into wizard steps",
        "feed_style": "results or drafts only — not free browse",
        "forbidden": "open catalog list as first action",
        "markers": "wizard|draft|pipeline|step",
    },
    "T5_workspace": {
        "primary_zone": "Single canvas / workspace — no master-detail list",
        "feed_style": "inline sections inside the workspace",
        "forbidden": "list landing or master-detail stack as home",
        "markers": "workspace|canvas|stamp|board|panel",
    },
    "T6_checklist_session": {
        "primary_zone": "Active session checklist with progress",
        "feed_style": "session history below the active list",
        "forbidden": "catalog / chip taxonomy home",
        "markers": "checklist|session|progress|line.item",
    },
    "T7_compare_board": {
        "primary_zone": "Dual-pane / pair compare surface",
        "feed_style": "pair picks, not single-list browse",
        "forbidden": "single list browse as home",
        "markers": "compare|dual|pair|board",
    },
    "T8_reminder_ring": {
        "primary_zone": "Calendar ring / orbit / day nodes",
        "feed_style": "agenda sorted by urgency or date",
        "forbidden": "tag-filter list home",
        "markers": "ring|orbit|calendar|agenda|node",
    },
}

_ONBOARDING_PATTERN_HINTS: tuple[str, ...] = (
    "Carousel (2–3 swipe cards): distinct value pillars with a clear emotional arc",
    "Dialogue / typewriter: intimate or reflective products (journal, Q&A, nightly ritual)",
    "Narrative scroll: story / journey products (timeline, yearbook)",
    "Interactive preview: tool products — let the user feel the signature action once",
)


def _product_fields(
    ctx: dict[str, Any],
    *,
    audience: str = "",
    core_scene: str = "",
    local_feature: str = "",
    product_flow: str = "",
) -> dict[str, str]:
    product = ctx.get("product") if isinstance(ctx.get("product"), dict) else {}
    constraints = ctx.get("constraints") if isinstance(ctx.get("constraints"), dict) else {}
    seeds = ctx.get("designerSeeds") if isinstance(ctx.get("designerSeeds"), dict) else {}
    return {
        "audience": str(product.get("audience") or audience or "").strip(),
        "core_scene": str(product.get("coreScene") or core_scene or "").strip(),
        "local_feature": str(product.get("localFeature") or local_feature or "").strip(),
        "product_flow": str(product_flow or "").strip(),
        "topo_id": str(
            constraints.get("interactionTopology")
            or constraints.get("n")
            or ""
        ).strip(),
        "topo_label": str(
            constraints.get("interactionTopologyLabel")
            or constraints.get("nLabel")
            or ""
        ).strip(),
        "motif": str(seeds.get("heroVisualMotif") or "").strip(),
        "color_temp": str(seeds.get("colorTemperature") or "").strip(),
        "shape": str(seeds.get("shapeLanguage") or "").strip(),
    }


def _flow_beats(product_flow: str, *, limit: int = 3) -> list[str]:
    if not product_flow:
        return []
    parts = re.split(r"[;；\n]+", product_flow)
    beats = [p.strip() for p in parts if p.strip()]
    return beats[:limit]


def hub_pattern_for_topology(topo_id: str) -> dict[str, str]:
    if topo_id in TOPOLOGY_HUB_PATTERNS:
        return dict(TOPOLOGY_HUB_PATTERNS[topo_id])
    # Soft fallback — still product-bound via scene_brief, not chip dashboard.
    return {
        "primary_zone": "Derive a signature primary zone from coreScene + topology label",
        "feed_style": "Contextual feed tied to productFlow — not a generic recent carousel",
        "forbidden": "generic category-chip + KPI strip template when topology is known",
        "markers": "primary|zone|signature|empty.state",
    }


def build_welcome_scene_spec(
    ctx: dict[str, Any],
    *,
    audience: str = "",
    core_scene: str = "",
    local_feature: str = "",
    product_flow: str = "",
) -> dict[str, Any]:
    """Dynamic Welcome page rules bound to this pack's product fields."""
    f = _product_fields(
        ctx,
        audience=audience,
        core_scene=core_scene,
        local_feature=local_feature,
        product_flow=product_flow,
    )
    beats = _flow_beats(f["product_flow"])
    beat_line = "; ".join(beats) if beats else f["core_scene"] or "productFlow beats"

    scene_brief = "\n".join(
        [
            f"- **Audience:** {f['audience'] or '—'}",
            f"- **Core scene:** {f['core_scene'] or '—'}",
            f"- **Local feature:** {f['local_feature'] or '—'}",
            f"- **Visual motif:** {f['motif'] or '—'}",
            f"- **Color temperature:** {f['color_temp'] or '—'}",
            f"- **Shape language:** {f['shape'] or '—'}",
            f"- **Flow beats to express:** {beat_line}",
            "",
            "Immerse the user in **this** product's moment of need. "
            "Do **not** ship a generic 'Welcome to {App}' + feature bullet card.",
            "Aim for **premium craft** (高级感): authored atmosphere, signature motif, "
            "2–3 purposeful motions — not a compliance skeleton.",
        ]
    )

    pattern_guidance = "\n".join(
        [
            "Choose **ONE** onboarding pattern that fits this pack's emotional tone "
            "(do not copy another app's pattern):",
            *[f"- {hint}" for hint in _ONBOARDING_PATTERN_HINTS],
            "",
            "Hard constraints:",
            "- Consent checkbox + Privacy/User links + disabled Continue until agreed "
            "(final beat only).",
            "- Headlines = situation / confidence / promise — not feature lists; "
            "never sole H1 `Welcome to {AppName}`.",
            "- Hero visual density: ≥2 of {CSS gradient, blur/glow, keyframes, "
            "SVG/illustration, domain motif}. A lone clip-path blob or text-only "
            "stepper is **not** enough.",
            "- Demo / hero visuals evoke the **core scene**; "
            "do not paste app UI screenshots as the hero.",
            "- Respect `prefers-reduced-motion` (keep hierarchy when motion is reduced).",
        ]
    )

    return {
        "layout": {
            "Max Width": "480px centered on full-bleed ambient wash",
            "Layout": (
                "Product-bound onboarding (carousel / dialogue / narrative / preview) "
                f"— pick from Scene Brief for: {f['core_scene'] or 'this coreScene'}"
            ),
            "Sections": (
                "1. Scene immersion tied to coreScene + audience, "
                "2. Signature value beat from productFlow, "
                "3. Trust + 18+ consent + Continue (final beat only)"
            ),
        },
        "spacing": {"Content Density": "Low — one emotional beat at a time"},
        "typography": {
            "Scale": "Display scene headline + body sub-copy; legal ≥ labelMedium / 14px"
        },
        "colors": {
            "Strategy": (
                "Derive a short emotional color arc from designerSeeds "
                f"({f['color_temp'] or 'package tokens'}); "
                "CTA on final beat uses primary accent"
            )
        },
        "components": [
            "Required: onboarding structure beyond a single static feature-bullet card",
            "Required: scene copy grounded in coreScene + audience (see Scene Brief)",
            "Required: hero visual density ≥2 of {gradient, blur, keyframes, SVG/illustration, domain motif}",
            "Required: persist first-run flag in local storage",
            "Required: legal checkbox + Privacy/User links on final beat only",
            "Required: Continue disabled until consent checked",
            "Avoid: Tab bar before Continue",
            "Avoid: Paywall / store entry on welcome",
            "Avoid: Generic 'Welcome to {AppName}' as the sole headline",
            "Avoid: Text-only steps or lone clip-path blob as the entire hero",
            "Avoid: Copying another pack's onboarding pattern (carousel vs typewriter etc.)",
        ],
        "unique_components": [
            "product-bound onboarding stage (pattern chosen from Scene Brief)",
            "scene-immersion hero (authored atmosphere — not stock icon row)",
            "legal consent row (checkbox + Privacy/User links)",
        ],
        "recommendations": [
            f"Open on the user's tension around: {f['core_scene'] or 'coreScene'}",
            f"Speak to: {f['audience'] or 'audience'}",
            f"Surface local capability: {f['local_feature'] or 'localFeature'}",
            "Premium craft: hierarchy + ambient wash + signature motif + purposeful motion",
            "Continue routes to Tab 1 (first tab-root from Screen Inventory)",
            "Show once per install unless data cleared",
        ],
        "scene_brief": scene_brief,
        "pattern_guidance": pattern_guidance,
        "guidance_heading": "Onboarding Pattern Guidance",
    }


def build_hub_scene_spec(
    ctx: dict[str, Any],
    *,
    audience: str = "",
    core_scene: str = "",
    local_feature: str = "",
    product_flow: str = "",
) -> dict[str, Any]:
    """Dynamic Tab1 / hub page rules bound to topology + product fields."""
    f = _product_fields(
        ctx,
        audience=audience,
        core_scene=core_scene,
        local_feature=local_feature,
        product_flow=product_flow,
    )
    pattern = hub_pattern_for_topology(f["topo_id"])
    topo_display = f["topo_label"] or f["topo_id"] or "unassigned"
    beats = _flow_beats(f["product_flow"])

    scene_brief = "\n".join(
        [
            f"- **Topology:** {f['topo_id'] or '—'} ({topo_display})",
            f"- **Audience:** {f['audience'] or '—'}",
            f"- **Core scene:** {f['core_scene'] or '—'}",
            f"- **Local feature:** {f['local_feature'] or '—'}",
            f"- **Visual motif:** {f['motif'] or '—'}",
            f"- **Primary zone intent:** {pattern['primary_zone']}",
            f"- **Feed style:** {pattern['feed_style']}",
            f"- **Forbidden landing:** {pattern['forbidden']}",
            f"- **Workflow entry hints:** {'; '.join(beats) if beats else '—'}",
            "",
            "Tab 1 is the app identity after Welcome. "
            "It must read as **this** product's home — not a generic chip+KPI dashboard.",
            "Empty state must still show a **primary-zone skeleton / preview motif** "
            "(not a lone white card + CTA).",
        ]
    )

    pattern_guidance = "\n".join(
        [
            f"Topology `{f['topo_id'] or 'unknown'}` → primary zone: {pattern['primary_zone']}.",
            f"Feed: {pattern['feed_style']}.",
            f"Do **not**: {pattern['forbidden']}.",
            "",
            "Also bind:",
            f"- Usage audience / moment: {f['audience'] or 'audience'}",
            f"- Core scene visible in first viewport: {f['core_scene'] or 'coreScene'}",
            "- Time-aware or context-aware greeting (forbid static-only labels like "
            "'Daily check-ins' with no scene voice)",
            "- FAB / quick actions map to Primary Workflow entry (≤2)",
            "- Empty state still shows the primary zone skeleton / motif + CTA",
            "- Signature H5 interaction from 功能文档 must be reachable on this screen",
            "- Aim for authored atmosphere (ambient + motif + hierarchy) — not flat utility UI",
        ]
    )

    return {
        "layout": {
            "Max Width": "100% with safe-area padding",
            "Layout": (
                f"Tab 1 root — topology={topo_display}. "
                f"Primary zone: {pattern['primary_zone']}."
            ),
            "Sections": (
                "1. Contextual header / greeting, "
                "2. Topology-bound primary interaction zone, "
                "3. Quick actions tied to Primary Workflow, "
                "4. Contextual feed (urgency / recency — not generic 'recent carousel')"
            ),
        },
        "spacing": {"Content Density": "Medium — clear hierarchy around the primary zone"},
        "typography": {
            "Scale": (
                "Contextual greeting + domain status; "
                "primary zone may use display numerals when metrics are core"
            )
        },
        "colors": {
            "Strategy": (
                "Primary zone uses brand accent; "
                "urgency / status use semantic tokens; feed on elevated surface"
            )
        },
        "components": [
            "Required: bottom TabBar visible (≥3 tabs)",
            f"Required: primary zone matches topology {f['topo_id'] or '(see Scene Brief)'}",
            "Required: empty state shows primary-zone skeleton/motif + CTA into Primary Workflow",
            "Required: contextual greeting grounded in audience / usage moment",
            "Required: quick actions map to Primary Workflow entry points",
            "Required: signature H5 interaction reachable on this screen",
            "Avoid: generic 'category chips + KPI strip + recent carousel' when topology forbids it",
            "Avoid: Bridge plaza entry on Tab 1",
            "Avoid: empty page that is only a white card + CTA with no motif/skeleton",
            f"Avoid: {pattern['forbidden']}",
        ],
        "unique_components": [
            f"topology primary zone ({f['topo_id'] or 'product-bound'})",
            "contextual greeting / status header",
            "workflow quick actions",
            "contextual feed (product-sorted)",
        ],
        "recommendations": [
            f"First viewport = identity for: {f['core_scene'] or 'coreScene'}",
            f"Speak to: {f['audience'] or 'audience'}",
            f"Local feature in primary zone: {f['local_feature'] or 'localFeature'}",
            "Hub layout must differ visually from list/detail — it is the home identity",
            "Signature interaction from Professional Surface must be on-screen here",
            "Premium craft on Tab 1: ambient + motif + hierarchy — not flat utility UI",
        ],
        "scene_brief": scene_brief,
        "pattern_guidance": pattern_guidance,
        "guidance_heading": "Hub Identity Guidance",
        "topology_markers": pattern["markers"],
    }
