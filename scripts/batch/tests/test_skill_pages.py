"""Tests for skill_pages slug helpers."""

from __future__ import annotations

from batch.skill_pages import CANONICAL_H5_PAGES, _slugify_page


def test_canonical_h5_pages_count() -> None:
    assert len(CANONICAL_H5_PAGES) >= 9


def test_slugify_page() -> None:
    assert _slugify_page("My Detail Screen") == "my-detail-screen"
    assert _slugify_page("") == "screen"
