"""Tests for design-system diversity (anti-SaaS convergence)."""

from __future__ import annotations

import json
from pathlib import Path

from batch.design_diversity import (
    diversify_candidates,
    fingerprint_batch_collision,
    fingerprint_overlap,
    theme_search_query_from_row,
    visual_fingerprint,
)
from batch.skill_adapt import collision_score, pick_candidate


class _Row:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_theme_search_query_includes_english_scene_hints() -> None:
    build = _Row(
        name="Buildioo",
        track="亲子家庭",
        audience="陪读家长",
        core_scene="开学物品准备清单与采购预算控制",
        local_feature="到期提醒记录本",
    )
    promp = _Row(
        name="Prompio",
        track="教育培训",
        audience="欧洲大学生",
        core_scene="课堂演讲准备与现场展示",
        local_feature="滚动提词语速预警记录本",
    )
    q1 = theme_search_query_from_row(build)
    q2 = theme_search_query_from_row(promp)
    assert "back-to-school" in q1 or "checklist" in q1
    assert "teleprompter" in q2 or "presentation" in q2
    assert q1 != q2


def test_visual_fingerprint_overlap_detects_saas_clone() -> None:
    a = visual_fingerprint(
        {
            "colors": {"primary": "#475569", "accent": "#059669", "background": "#F8FAFC"},
            "typography": {"heading": "Rubik", "body": "Nunito Sans"},
            "pattern": {"name": "Feature-Rich Showcase"},
            "style": {"name": "Enterprise SaaS (Mobile)"},
        }
    )
    b = visual_fingerprint(
        {
            "colors": {"primary": "#475569", "accent": "#059669", "background": "#F8FAFC"},
            "typography": {"heading": "Rubik", "body": "Nunito Sans"},
            "pattern": {"name": "Feature-Rich Showcase"},
            "style": {"name": "Interactive Product Demo"},
        }
    )
    c = visual_fingerprint(
        {
            "colors": {"primary": "#EA580C", "accent": "#2563EB", "background": "#0F172A"},
            "typography": {"heading": "EB Garamond", "body": "Crimson Text"},
            "pattern": {"name": "Webinar Registration"},
            "style": {"name": "Parallax Storytelling"},
        }
    )
    assert fingerprint_overlap(a, b) >= 0.55
    assert fingerprint_overlap(a, c) < 0.3


def test_pick_candidate_rejects_sibling_visual_clone() -> None:
    sibling = visual_fingerprint(
        {
            "colors": {"primary": "#475569", "accent": "#059669", "background": "#F8FAFC"},
            "typography": {"heading": "Rubik", "body": "Nunito Sans"},
            "pattern": {"name": "Feature-Rich Showcase"},
            "style": {"name": "Enterprise SaaS (Mobile)"},
        }
    )
    anti = {
        "sameBatchUsed": [{"name": "Buildioo", "themeAngle": "school list"}],
        "sameBatchVisualFingerprints": [sibling],
        "historicalAvoid": [],
    }
    candidates = [
        {
            "id": "c1",
            "colors": {"primary": "#475569", "accent": "#059669", "background": "#F8FAFC"},
            "typography": {"heading": "Rubik", "body": "Nunito Sans"},
            "pattern": {"name": "Feature-Rich Showcase"},
            "style": {"name": "Interactive Product Demo", "keywords": "demo"},
        },
        {
            "id": "c2",
            "colors": {"primary": "#EA580C", "accent": "#2563EB", "background": "#0F172A"},
            "typography": {"heading": "EB Garamond", "body": "Crimson Text"},
            "pattern": {"name": "Webinar Registration"},
            "style": {"name": "Parallax Storytelling", "keywords": "story"},
        },
    ]
    picked, rationale = pick_candidate(candidates, anti)
    assert picked["id"] == "c2"
    assert "garamond" in rationale.lower() or "c2" in rationale


def test_diversify_candidates_spreads_tokens(tmp_path: Path) -> None:
    try:
        from batch.config import BatchConfig
        from batch.uupm_design_system import resolve_uupm_scripts_dir, _inject_scripts

        cfg = BatchConfig.from_env()
        scripts_dir = resolve_uupm_scripts_dir(cfg)
        _inject_scripts(scripts_dir)
    except RuntimeError:
        return  # uupm skill not installed in CI — skip integration check

    base = {
        "id": "c1",
        "colors": {"primary": "#111111", "accent": "#222222", "background": "#333333"},
        "typography": {"heading": "Inter", "body": "Inter"},
        "pattern": {"name": "Hero + Features + CTA"},
        "style": {"name": "Minimalism", "effects": "fade"},
        "key_effects": "fade",
    }
    candidates = [json.loads(json.dumps({**base, "id": f"c{i}"})) for i in range(1, 4)]
    query = theme_search_query_from_row(
        _Row(
            name="Prompio",
            track="教育培训",
            audience="欧洲大学生",
            core_scene="课堂演讲准备与现场展示",
            local_feature="滚动提词语速预警记录本",
        )
    )
    out = diversify_candidates(candidates, query=query)
    primaries = {c["colors"]["primary"] for c in out}
    headings = {c["typography"]["heading"] for c in out}
    assert len(primaries) >= 2 or len(headings) >= 2
