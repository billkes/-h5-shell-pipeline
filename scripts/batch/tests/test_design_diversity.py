"""Tests for design-system diversity (anti-SaaS convergence)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from batch.design_diversity import (
    diversify_candidates,
    fingerprint_batch_collision,
    fingerprint_overlap,
    is_banned_saas_design,
    theme_search_query_from_row,
    visual_fingerprint,
)
from batch.skill_adapt import collision_score, pick_candidate
from batch.uupm_design_system import design_query_from_context

_CJK = re.compile(r"[\u4e00-\u9fff]")


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


def test_beauty_health_tracks_avoid_productivity_saas_query() -> None:
    beauty = theme_search_query_from_row(
        _Row(
            name="Tintoo",
            track="美妆个护",
            audience="染发人群",
            core_scene="护色周期追踪",
            local_feature="水质匹配护色方案",
        )
    )
    health = theme_search_query_from_row(
        _Row(
            name="Lensoo",
            track="健康个护",
            audience="隐形眼镜用户",
            core_scene="镜片佩戴适配",
            local_feature="场景化镜片适配",
        )
    )
    for q in (beauty, health):
        low = q.lower()
        assert "saas" not in low
        assert "productivity" not in low
        assert "b2b" not in low
    assert "beauty" in beauty.lower() or "wellness" in beauty.lower() or "spa" in beauty.lower()
    assert "wellness" in health.lower() or "healthcare" in health.lower() or "organic" in health.lower()


def test_is_banned_saas_design_detects_style_and_category() -> None:
    assert is_banned_saas_design(
        {"style": {"name": "SaaS Mobile (High-Tech Boutique)"}, "category": "Productivity Tool"}
    )
    assert is_banned_saas_design(style_name="Enterprise SaaS (Mobile)")
    assert is_banned_saas_design(category="Micro SaaS")
    assert not is_banned_saas_design(
        {"style": {"name": "Organic Biophilic"}, "category": "Biohacking / Longevity App"}
    )


def test_theme_search_query_is_english_only() -> None:
    row = _Row(
        name="Monthio",
        track="个人成长",
        audience="需要追踪长期习惯并进行月度复盘的自我提升者",
        core_scene="月末生成习惯复盘报告",
        local_feature="习惯打卡与月度数据可视化分析",
    )
    query = theme_search_query_from_row(row)
    assert not _CJK.search(query), query
    assert "habit" in query or "review" in query or "monthly" in query
    assert len(query) < 220


def test_design_query_from_context_ignores_anti_collision_suffix() -> None:
    row = _Row(
        name="Monthio",
        track="个人成长",
        audience="自我提升者",
        core_scene="月末生成习惯复盘报告",
        local_feature="习惯打卡与月度数据可视化分析",
    )
    anti = {
        "sameBatchUsed": [{"themeAngle": "Theme: huge historical blob " * 40}],
        "historicalAvoid": ["Theme: another huge blob " * 40],
    }
    ctx = {"product": {"searchQuery": theme_search_query_from_row(row)}}
    assert design_query_from_context(ctx, anti, row=row) == theme_search_query_from_row(row)
    assert len(design_query_from_context(ctx, anti, row=row)) < 220


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


def test_pick_candidate_rejects_saas_when_alternative_exists() -> None:
    # Theme text biased toward SaaS so score prefers c1; hard reject must switch.
    saas = {
        "id": "c1",
        "style": {"name": "SaaS Mobile (High-Tech Boutique)", "keywords": "saas productivity b2b"},
        "colors": {"primary": "#0d9488", "accent": "#ea580c", "notes": "saas"},
        "typography": {"heading": "Inter", "body": "Inter", "mood": "saas productivity"},
        "pattern": {"name": "App Store Style Landing"},
        "category": "Productivity Tool",
    }
    organic = {
        "id": "c2",
        "style": {"name": "Organic Biophilic", "keywords": "nature"},
        "colors": {"primary": "#d97706", "accent": "#059669", "notes": ""},
        "typography": {"heading": "Lora", "body": "Raleway", "mood": "calm"},
        "pattern": {"name": "Minimal Single Column"},
        "category": "General",
    }
    picked, rationale = pick_candidate(
        [saas, organic],
        {},
        product_text="saas productivity b2b dashboard tool",
        audience="",
    )
    assert picked["id"] == "c2"
    assert "saas" in rationale.lower() or "SaaS" in rationale


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


def test_pick_candidate_prefers_theme_fit_over_collision() -> None:
    anti = {
        "sameBatchUsed": [],
        "sameBatchVisualFingerprints": [],
        "historicalAvoid": [],
    }
    product = (
        "back-to-school checklist budget spending tracker parent school preparation "
        "inventory finance control"
    )
    candidates = [
        {
            "id": "c1",
            "category": "Finance",
            "style": {
                "name": "Financial Dashboard",
                "keywords": "budget tracking financial ratios portfolio",
            },
            "colors": {"primary": "#059669", "notes": "green finance"},
            "typography": {"heading": "Inter", "mood": "professional clear"},
            "pattern": {"name": "Dashboard"},
        },
        {
            "id": "c3",
            "style": {
                "name": "Predictive Analytics",
                "keywords": "forecast AI anomaly detection visualization",
            },
            "colors": {"primary": "#EC4899"},
            "typography": {"heading": "Fredoka", "mood": "playful friendly"},
            "pattern": {"name": "Hero + Features + CTA"},
        },
    ]
    picked, rationale = pick_candidate(
        candidates,
        anti,
        product_text=product,
        audience="陪读家长",
    )
    assert picked["id"] == "c1"
    assert "theme-fit" in rationale or "combined" in rationale


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
