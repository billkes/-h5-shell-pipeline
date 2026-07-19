"""Tests for skill.enrich domain query shaping."""

from __future__ import annotations

from batch.skill_enrich import enrich_domain_query


def test_enrich_domain_query_appends_focus_hint() -> None:
    base = "Monthio mobile app habit tracker monthly review"
    ux = enrich_domain_query(base, "ux")
    icons = enrich_domain_query(base, "icons")
    assert ux.startswith(base)
    assert icons.startswith(base)
    assert "accessibility" in ux
    assert "phosphor" in icons
    assert len(ux) < len(base) + 80
