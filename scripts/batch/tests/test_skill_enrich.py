"""Tests for skill_enrich formatting."""

from __future__ import annotations

from batch.skill_enrich import ENRICH_DOMAINS, _format_search_md


def test_enrich_domains_include_style_typography_color_gsap() -> None:
    names = {d[0] for d in ENRICH_DOMAINS}
    assert {"style", "typography", "color", "gsap"}.issubset(names)


def test_format_search_md_includes_pre_delivery() -> None:
    result = {
        "file": "ux-guidelines.csv",
        "count": 1,
        "results": [
            {
                "Category": "Touch",
                "Issue": "touch-target-size",
                "Description": "Min 44pt",
            }
        ],
    }
    text = _format_search_md("ux", "test app", result)
    assert "Pre-Delivery Checklist" in text
    assert "touch-target-size" in text


def test_format_search_md_icons_includes_h5_landing() -> None:
    result = {
        "file": "icons.csv",
        "count": 1,
        "results": [{"Category": "Navigation", "Icon Name": "house", "Library": "Phosphor"}],
    }
    text = _format_search_md("icons", "test app", result, h5_prefix="buildioo")
    assert "H5 Delivery Canon" in text
    assert "buildioo-mark-home" in text
    assert "Import Code" in text
