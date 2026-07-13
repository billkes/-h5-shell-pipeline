"""Tests for self-composed theme brief parsing and audit."""

from __future__ import annotations

from types import SimpleNamespace

from batch.theme_audit import audit_theme_brief, parse_one_liner


USER_SAMPLES = [
    "亲密边界自测清单",
    "轻社交礼物匹配库：按关系、预算、场景精准匹配欧洲小众平价礼物，解决派对/生日选礼纠结",
    "社交电量规划本：记录社交耗能与回血节奏，智能建议每日社交强度，缓解年轻人群社交内耗",
    "染发护色追踪档案：记录染发产品、补色周期与掉色速度，匹配本地水质沉淀个人护色方案",
    "隐形眼镜适配日记：记录不同品牌镜片的佩戴时长、干涩红血丝反应，对应空调/户外场景筛选个人适配款",
    "咖啡馆点单记忆库：记录本地各店的点单搭配与口味评分，沉淀个人点单白名单",
    "课堂演讲提词器：自带滚动提词+实时计时+语速预警，自动标记超时段落",
]


def test_parse_user_samples_have_core_columns() -> None:
    for text in USER_SAMPLES[1:]:
        parsed = parse_one_liner(text)
        assert parsed["中文主题"]
        assert parsed["核心场景"]
        assert parsed["本地功能"]
        assert parsed["赛道分类"]


def test_user_samples_pass_individual_audit() -> None:
    for text in USER_SAMPLES:
        parsed = parse_one_liner(text)
        result = audit_theme_brief(
            theme_cn=parsed.get("中文主题", text),
            track=parsed.get("赛道分类", ""),
            audience=parsed.get("目标人群", ""),
            core_scene=parsed.get("核心场景", ""),
            local_feature=parsed.get("本地功能", ""),
        )
        assert result.ok, f"{text!r} -> {result.codes} {result.hints}"


def test_generic_brief_rejected() -> None:
    result = audit_theme_brief(
        theme_cn="清单管理工具",
        track="工具",
        audience="用户",
        core_scene="日常使用",
        local_feature="记录本",
    )
    assert not result.ok
    assert "THEME-004" in result.codes


def test_crud_product_flow_rejected() -> None:
    flow = (
        "Pick a category chip to browse items, save entries in a log, "
        "export a weekly summary card"
    )
    result = audit_theme_brief(
        theme_cn="采购记录",
        track="工具",
        audience="用户",
        core_scene="产品记录",
        local_feature="列表管理",
        product_flow=flow,
    )
    assert not result.ok
    assert "THEME-003" in result.codes
    assert result.suggest_topology


def test_recommend_topology_for_presentation() -> None:
    from batch.interaction_topology import recommend_topology_ids

    ids = recommend_topology_ids(
        core_scene="课堂演讲提词",
        local_feature="语速预警提词",
        theme_cn="课堂演讲提词器",
    )
    assert "T4_wizard" in ids or "T5_workspace" in ids


def test_batch_duplicate_pair_detected() -> None:
    row_a = SimpleNamespace(
        name="A",
        theme_cn="主题A",
        track="工具",
        audience="用户",
        core_scene="场景X",
        local_feature="机制Y",
        product_flow="",
    )
    row_b = SimpleNamespace(
        name="B",
        theme_cn="主题B",
        track="工具",
        audience="用户2",
        core_scene="场景X",
        local_feature="机制Y",
        product_flow="",
    )
    from batch.theme_audit import audit_theme_rows

    results = {name: res for _, name, res in audit_theme_rows([row_a, row_b])}
    assert results["B"].ok is False
    assert "THEME-002" in results["B"].codes
