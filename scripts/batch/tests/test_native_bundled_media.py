"""Tests for native bundled media gate (h5_oc_shell)."""

from __future__ import annotations

from pathlib import Path

from batch.h5_default_seed import collect_h5_default_seed_violations
from batch.native_bundled_media import collect_native_bundled_media_violations


def _write_temioo_like_ws(tmp: Path) -> Path:
    ws = tmp / "Temioo"
    ws.mkdir()
    (ws / "Temioo.xcodeproj").mkdir()
    app = ws / "Temioo"
    app.mkdir()
    (app / "assets" / "img").mkdir(parents=True)
    (app / "assets" / "img" / "seed_slide_cs101.jpg").write_bytes(b"jpeg")
    (ws / "本包登记信息.json").write_text(
        '{"packType":"h5_oc_shell","shellRuntime":"oc","codeAntiCorrelation":{"dartCodePrefix":"uhfnf"}}',
        encoding="utf-8",
    )
    h5 = ws / "h5"
    h5.mkdir()
    (h5 / "package.json").write_text("{}", encoding="utf-8")
    (h5 / "src" / "store").mkdir(parents=True)
    (h5 / "src" / "router").mkdir(parents=True)
    (h5 / "src" / "router" / "index.ts").write_text('"/welcome"\n"/hub"\nHubView', encoding="utf-8")
    (ws / "功能文档.md").write_text("演示数据\n静默预置", encoding="utf-8")
    return ws


def test_rejects_legacy_h5_vault_dir(tmp_path: Path) -> None:
    ws = _write_temioo_like_ws(tmp_path)
    legacy = ws / "h5" / "assets" / "uhfnf_vault"
    legacy.mkdir(parents=True)
    (legacy / "seed_slide_cs101.jpg").write_bytes(b"x")
    issues = collect_native_bundled_media_violations(ws)
    assert any("禁止 h5/assets/uhfnf_vault" in i for i in issues)


def test_accepts_native_assets_img_for_seed(tmp_path: Path) -> None:
    ws = _write_temioo_like_ws(tmp_path)
    seed = ws / "h5" / "src" / "store" / "defaultSeed.ts"
    seed.write_text(
        """
export const BOOTSTRAP_KEY = 'uhfnf_bootstrap_v1';
export function ensureBootstrapData() {}
export function buildDefaultPlans() { return [{ title: 'A' }]; }
export function buildDefaultRuns() { return [{ planId: 'p1' }]; }
import { vaultAssetPath } from '../lib/vaultAsset';
const x = vaultAssetPath('seed_slide_cs101.jpg');
""",
        encoding="utf-8",
    )
    (ws / "h5" / "src" / "views").mkdir(parents=True)
    (ws / "h5" / "src" / "views" / "WelcomeView.logic.ts").write_text(
        "export function continueFlow() { ensureBootstrapData(); }",
        encoding="utf-8",
    )
    issues = collect_h5_default_seed_violations(ws)
    assert not any("配图缺失" in i for i in issues)
    assert not any("禁止 h5/assets" in i for i in issues)
