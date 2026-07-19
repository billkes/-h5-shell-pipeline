"""Design-system diversity: theme queries, visual fingerprints, candidate token spread."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from batch.task_schema import (
    COL_AUDIENCE,
    COL_CORE_SCENE,
    COL_LOCAL_FEATURE,
    COL_NAME,
    COL_TRACK,
)

H5_DESIGN_LEDGER_NAME = "h5-design-combo-ledger.json"

# English scene anchors — steer uupm product search away from generic SaaS/Mood Tracker.
# BM25 corpus is English; never echo raw Chinese CSV fields into search queries.
_TRACK_SCENE_HINTS: dict[str, str] = {
    "亲子家庭": "family parenting household organizer warm approachable",
    "教育培训": "university education classroom academic presentation learning",
    "教育": "education learning academic student",
    "教育娱乐": "edutainment word puzzle learning game playful",
    "工具": "utility productivity tool focused",
    "健康": "wellness health habit tracker calm",
    "金融": "finance budget money planning professional",
    "个人成长": "personal growth self improvement habit reflection",
    "效率工具": "productivity utility efficiency planner reminders",
    "校园效率": "campus student academic productivity lecture prep",
    "休闲益智": "casual puzzle brain game pixel art challenge",
    "轻社交": "party social game board dice multiplayer fun",
    "休闲生活": "lifestyle collection hobby album gallery cozy",
    "休闲游戏": "casual game pet companion playful offline",
}

_SCENE_KEYWORD_HINTS: tuple[tuple[str, str], ...] = (
    ("开学", "back-to-school supply checklist shopping budget reminder"),
    ("清单", "checklist list organizer inventory"),
    ("预算", "budget spending tracker finance control"),
    ("陪读", "parent guardian school preparation notes"),
    ("演讲", "presentation speech stage lecture"),
    ("提词", "teleprompter auto-scroll script reader"),
    ("语速", "pace speed timing wpm warning"),
    ("计时", "timer stopwatch elapsed duration"),
    ("课堂", "classroom lecture seminar university"),
    ("大学", "university campus student academic"),
    ("习惯", "habit tracker daily check-in streak routine"),
    ("复盘", "monthly review reflection report summary"),
    ("月末", "month-end monthly period review"),
    ("打卡", "daily check-in streak completion log"),
    ("可视化", "data visualization analytics chart heatmap"),
    ("收集", "collection gallery album vault showcase"),
    ("拼词", "word puzzle spelling letter game"),
    ("猫咪", "cat pet companion virtual nurture"),
    ("灵魂", "journal prompt reflection diary introspection"),
    ("备忘", "contact profile notes meeting prep reminder"),
    ("见面", "meeting prep quick profile card glance"),
    ("像素", "pixel art grid puzzle color match"),
    ("骰子", "dice board party game turn score"),
)


def design_ledger_path(project_dir: Path) -> Path:
    return project_dir / "data" / "registry" / H5_DESIGN_LEDGER_NAME


def _norm(value: object) -> str:
    return str(value or "").strip()


def _scene_english_hints(*texts: str) -> str:
    blob = " ".join(t for t in texts if t)
    hints: list[str] = []
    for track, phrase in _TRACK_SCENE_HINTS.items():
        if track in blob:
            hints.append(phrase)
    for zh, en in _SCENE_KEYWORD_HINTS:
        if zh in blob:
            hints.append(en)
    # De-dupe while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for h in hints:
        if h not in seen:
            seen.add(h)
            ordered.append(h)
    return " ".join(ordered)


def _dedupe_query_tokens(text: str) -> str:
    """Drop repeated words while preserving order (keeps BM25 queries concise)."""
    seen: set[str] = set()
    out: list[str] = []
    for token in text.split():
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(token)
    return " ".join(out)


def theme_search_query_from_row(row: Any) -> str:
    """Build short English uupm BM25 query from CSV theme columns.

    Chinese narrative stays in context.json / Agent prompts — not in search text.
    """
    name = _norm(getattr(row, "name", "") or (row.get(COL_NAME) if isinstance(row, dict) else ""))
    track = _norm(getattr(row, "track", "") or (row.get(COL_TRACK) if isinstance(row, dict) else ""))
    audience = _norm(getattr(row, "audience", "") or (row.get(COL_AUDIENCE) if isinstance(row, dict) else ""))
    scene = _norm(getattr(row, "core_scene", "") or (row.get(COL_CORE_SCENE) if isinstance(row, dict) else ""))
    feature = _norm(getattr(row, "local_feature", "") or (row.get(COL_LOCAL_FEATURE) if isinstance(row, dict) else ""))

    english = _scene_english_hints(track, audience, scene, feature)
    parts = [
        f"{name} mobile app" if name else "mobile app",
        english,
    ]
    return _dedupe_query_tokens(" ".join(p.strip() for p in parts if p and p.strip()))


def visual_fingerprint(candidate: dict[str, Any]) -> dict[str, str]:
    """Stable visual identity keys used for batch de-duplication."""
    colors = candidate.get("colors") or {}
    typo = candidate.get("typography") or {}
    pattern = candidate.get("pattern") or {}
    style = candidate.get("style") or {}
    return {
        "primary": _norm(colors.get("primary")).lower(),
        "accent": _norm(colors.get("accent")).lower(),
        "background": _norm(colors.get("background")).lower(),
        "heading": _norm(typo.get("heading")).lower(),
        "body": _norm(typo.get("body")).lower(),
        "pattern": _norm(pattern.get("name")).lower(),
        "style": _norm(style.get("name")).lower(),
        "category": _norm(candidate.get("category")).lower(),
    }


def fingerprint_key(fp: dict[str, str]) -> str:
    parts = [
        fp.get("primary", ""),
        fp.get("accent", ""),
        fp.get("background", ""),
        fp.get("heading", ""),
        fp.get("pattern", ""),
        fp.get("style", ""),
    ]
    raw = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def fingerprint_overlap(a: dict[str, str], b: dict[str, str]) -> float:
    """0 = fully distinct, 1 = identical on weighted visual keys."""
    weights = {
        "primary": 0.22,
        "accent": 0.12,
        "background": 0.12,
        "heading": 0.18,
        "body": 0.08,
        "pattern": 0.14,
        "style": 0.14,
    }
    score = 0.0
    for key, w in weights.items():
        av = a.get(key, "")
        bv = b.get(key, "")
        if av and bv and av == bv:
            score += w
    return min(1.0, score)


def fingerprint_batch_collision(candidate: dict[str, Any], sibling_fps: list[dict[str, str]]) -> float:
    """Max overlap vs any sibling fingerprint (higher = worse)."""
    if not sibling_fps:
        return 0.0
    fp = visual_fingerprint(candidate)
    return max(fingerprint_overlap(fp, sib) for sib in sibling_fps)


# ── uupm CSV row → candidate token patches ─────────────────────────────


def _color_from_csv_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        "primary": _norm(row.get("Primary")) or "#2563EB",
        "on_primary": _norm(row.get("On Primary")),
        "secondary": _norm(row.get("Secondary")) or "#3B82F6",
        "accent": _norm(row.get("Accent")) or "#F97316",
        "background": _norm(row.get("Background")) or "#F8FAFC",
        "foreground": _norm(row.get("Foreground")) or "#1E293B",
        "muted": _norm(row.get("Muted")),
        "border": _norm(row.get("Border")),
        "destructive": _norm(row.get("Destructive")),
        "ring": _norm(row.get("Ring")),
        "notes": _norm(row.get("Notes")),
        "cta": _norm(row.get("Accent")) or "#F97316",
        "text": _norm(row.get("Foreground")) or "#1E293B",
    }


def _typography_from_csv_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        "heading": _norm(row.get("Heading Font")) or "Inter",
        "body": _norm(row.get("Body Font")) or "Inter",
        "mood": _norm(row.get("Mood/Style Keywords")),
        "best_for": _norm(row.get("Best For")),
        "google_fonts_url": _norm(row.get("Google Fonts URL")),
        "css_import": _norm(row.get("CSS Import")),
    }


def _style_from_csv_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        "name": _norm(row.get("Style Category")) or "Minimalism",
        "type": _norm(row.get("Type")) or "General",
        "effects": _norm(row.get("Effects & Animation")),
        "keywords": _norm(row.get("Keywords")),
        "best_for": _norm(row.get("Best For")),
        "performance": _norm(row.get("Performance")),
        "accessibility": _norm(row.get("Accessibility")),
        "light_mode": _norm(row.get("Light Mode ✓")),
        "dark_mode": _norm(row.get("Dark Mode ✓")),
    }


def _pattern_from_csv_row(row: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    base = dict(fallback or {})
    if row.get("Pattern Name"):
        base["name"] = _norm(row.get("Pattern Name"))
    if row.get("Section Order"):
        base["sections"] = _norm(row.get("Section Order"))
    if row.get("Primary CTA Placement"):
        base["cta_placement"] = _norm(row.get("Primary CTA Placement"))
    if row.get("Color Strategy"):
        base["color_strategy"] = _norm(row.get("Color Strategy"))
    if row.get("Conversion Optimization"):
        base["conversion"] = _norm(row.get("Conversion Optimization"))
    return base


_PATTERN_FALLBACKS: tuple[str, ...] = (
    "Feature-Rich Showcase",
    "Wizard / Step Flow",
    "Dashboard + Drill-down",
    "Index Grid + Detail",
    "Hero + Features + CTA",
)


def _search_results(query: str, domain: str, count: int) -> list[dict[str, Any]]:
    from core import search  # type: ignore[import-not-found]

    payload = search(query, domain, count)
    results = payload.get("results") or []
    return [r for r in results if isinstance(r, dict)]


def diversify_candidates(
    candidates: list[dict[str, Any]],
    *,
    query: str,
) -> list[dict[str, Any]]:
    """Spread color / typography / style / pattern across c1–c3 (not only dials)."""
    if not candidates:
        return candidates

    color_rows = _search_results(query, "color", max(3, len(candidates)))
    typo_rows = _search_results(query, "typography", max(3, len(candidates)))
    style_rows = _search_results(query, "style", max(3, len(candidates)))
    landing_rows = _search_results(query, "landing", max(3, len(candidates)))

    for i, cand in enumerate(candidates):
        if i < len(color_rows):
            cand["colors"] = _color_from_csv_row(color_rows[i])
        if i < len(typo_rows):
            cand["typography"] = _typography_from_csv_row(typo_rows[i])
        if i < len(style_rows):
            style = _style_from_csv_row(style_rows[i])
            cand["style"] = style
            if style.get("effects"):
                cand["key_effects"] = style["effects"]
        if i < len(landing_rows):
            cand["pattern"] = _pattern_from_csv_row(landing_rows[i], cand.get("pattern") or {})
        elif i < len(_PATTERN_FALLBACKS):
            pattern = dict(cand.get("pattern") or {})
            pattern["name"] = _PATTERN_FALLBACKS[i % len(_PATTERN_FALLBACKS)]
            cand["pattern"] = pattern

    return candidates


# ── Design combo ledger (batch visual de-duplication) ────────────────────


def _load_ledger(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"apps": {}, "fingerprints": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"apps": {}, "fingerprints": {}}
    data.setdefault("apps", {})
    data.setdefault("fingerprints", {})
    return data


def _save_ledger(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def register_design_selection(
    ledger_path: Path,
    *,
    app: str,
    batch_id: str,
    candidate: dict[str, Any],
    workspace: Path | None = None,
) -> str:
    ledger = _load_ledger(ledger_path)
    fp = visual_fingerprint(candidate)
    key = fingerprint_key(fp)

    stale = [k for k, v in (ledger.get("fingerprints") or {}).items() if v == app and k != key]
    for k in stale:
        ledger["fingerprints"].pop(k, None)

    entry: dict[str, Any] = {
        "batchId": batch_id,
        "fingerprintKey": key,
        "visualFingerprint": fp,
        "candidateId": candidate.get("id") or "c1",
        "style": (candidate.get("style") or {}).get("name", ""),
        "category": candidate.get("category", ""),
    }
    if workspace is not None:
        for meta_path in workspace.glob("design-system/*/enrich-meta.json"):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                entry["uxDomainsUsed"] = meta.get("domains") or []
            except json.JSONDecodeError:
                pass
            break
        pages_dir = next(workspace.glob("design-system/*/pages"), None)
        entry["pageOverrideCount"] = len(list(pages_dir.glob("*.md"))) if pages_dir else 0
        manifest = workspace / "skill-adapt" / "icon-sprite-manifest.json"
        if manifest.is_file():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                libs = {i.get("source") for i in data.get("icons") or [] if i.get("source")}
                entry["iconLibrary"] = sorted(libs)
            except json.JSONDecodeError:
                pass
        tok = workspace / "skill-adapt" / "design-tokens.json"
        if tok.is_file():
            entry["tokenHash"] = hashlib.sha256(tok.read_bytes()).hexdigest()[:16]

    ledger.setdefault("apps", {})[app] = entry
    ledger.setdefault("fingerprints", {})[key] = app
    _save_ledger(ledger_path, ledger)
    return key


def sibling_visual_fingerprints(
    ledger_path: Path,
    *,
    app_name: str,
    batch_id: str = "",
) -> list[dict[str, str]]:
    ledger = _load_ledger(ledger_path)
    out: list[dict[str, str]] = []
    for name, entry in (ledger.get("apps") or {}).items():
        if name == app_name:
            continue
        if batch_id and entry.get("batchId") != batch_id:
            continue
        fp = entry.get("visualFingerprint")
        if isinstance(fp, dict) and fp:
            out.append(fp)
    return out


def discover_workspace_fingerprint(workspace: Path) -> dict[str, str] | None:
    """Read skill-adapt/selected-candidate.json from an existing output workspace."""
    matches = sorted(workspace.glob("skill-adapt/selected-candidate.json"))
    if not matches:
        matches = sorted(workspace.rglob("skill-adapt/selected-candidate.json"))
    for path in matches:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        ds = data.get("designSystem") or data
        if isinstance(ds, dict):
            return visual_fingerprint(ds)
    return None


def seed_ledger_from_outputs(
    ledger_path: Path,
    *,
    output_dir: Path,
    batch_id: str = "",
) -> int:
    """Backfill ledger from output/*/skill-adapt when ledger entry missing."""
    if not output_dir.is_dir():
        return 0
    ledger = _load_ledger(ledger_path)
    seeded = 0
    for child in sorted(output_dir.iterdir()):
        if not child.is_dir():
            continue
        app_dir = child
        app_name = child.name
        if "-" in child.name:
            nested = child / child.name.split("-", 1)[0]
            if nested.is_dir():
                app_dir = nested
                app_name = nested.name
        fp = discover_workspace_fingerprint(app_dir)
        if not fp or app_name in (ledger.get("apps") or {}):
            continue
        pseudo = {
            "id": "seed",
            "category": fp.get("category", ""),
            "colors": {
                "primary": fp.get("primary", ""),
                "accent": fp.get("accent", ""),
                "background": fp.get("background", ""),
            },
            "typography": {"heading": fp.get("heading", ""), "body": fp.get("body", "")},
            "pattern": {"name": fp.get("pattern", "")},
            "style": {"name": fp.get("style", "")},
        }
        register_design_selection(
            ledger_path,
            app=app_name,
            batch_id=batch_id,
            candidate=pseudo,
        )
        seeded += 1
    return seeded


def enrich_anti_collision_with_visuals(
    anti: dict[str, Any],
    *,
    ledger_path: Path,
    app_name: str,
    batch_id: str = "",
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Attach sibling visual fingerprints + expand mustDiffer for skill.adapt."""
    if output_dir is not None:
        seed_ledger_from_outputs(ledger_path, output_dir=output_dir, batch_id=batch_id)

    merged = dict(anti)
    sibling_fps = sibling_visual_fingerprints(ledger_path, app_name=app_name, batch_id=batch_id)

    same_batch = list(merged.get("sameBatchUsed") or [])
    for item in same_batch:
        if not isinstance(item, dict):
            continue
        sib_name = _norm(item.get("name"))
        if not sib_name:
            continue
        ledger = _load_ledger(ledger_path)
        entry = (ledger.get("apps") or {}).get(sib_name) or {}
        fp = entry.get("visualFingerprint")
        if isinstance(fp, dict) and fp:
            item["visualFingerprint"] = fp

    merged["sameBatchVisualFingerprints"] = sibling_fps
    must = list(merged.get("mustDiffer") or [])
    for field in ("visualFingerprint", "colorMood", "navigationPattern"):
        if field not in must:
            must.append(field)
    merged["mustDiffer"] = must
    return merged
