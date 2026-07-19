"""Tests for skill_resolve integrations defaults."""

from __future__ import annotations

from batch.skill_resolve import DEFAULT_UUPM_INTEGRATIONS, load_uupm_integrations
from batch.config import BatchConfig


def test_default_integrations_all_on() -> None:
    assert DEFAULT_UUPM_INTEGRATIONS["enrich_domains"] is True
    assert "h5_gate" not in DEFAULT_UUPM_INTEGRATIONS


def test_load_uupm_integrations_from_cfg() -> None:
    cfg = BatchConfig(uupm_integrations={"token_sync": False})
    merged = load_uupm_integrations(cfg)
    assert merged["token_sync"] is False
    assert merged["enrich_domains"] is True
