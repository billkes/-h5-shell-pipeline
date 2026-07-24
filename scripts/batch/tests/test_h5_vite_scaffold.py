"""Tests for h5_vite helpers — no code template tree."""

from __future__ import annotations

from pathlib import Path

from batch.h5_vite_scaffold import (
    apply_h5_vite_scaffold,
    ensure_browser_bridge_mock,
    ensure_h5_vite_scaffold,
    scaffold_exists,
)


def test_apply_does_not_create_h5_tree(tmp_path: Path) -> None:
    dst = apply_h5_vite_scaffold(tmp_path, app_name="Temioo", prefix="usfye")
    assert dst == tmp_path / "h5"
    assert not scaffold_exists(tmp_path)
    assert not (tmp_path / "h5" / "package.json").is_file()


def test_ensure_returns_none_without_agent_tree(tmp_path: Path) -> None:
    out = ensure_h5_vite_scaffold(
        tmp_path,
        app_name="Demo",
        prefix="demo",
        pack_type="h5_swift_shell",
    )
    assert out is None
    assert not (tmp_path / "h5").exists() or not scaffold_exists(tmp_path)


def test_ensure_syncs_when_h5_exists(tmp_path: Path) -> None:
    h5 = tmp_path / "h5"
    h5.mkdir()
    (h5 / "package.json").write_text("{}", encoding="utf-8")
    (h5 / "vite.config.ts").write_text(
        "export default { server: { port: 5174 } }\n",
        encoding="utf-8",
    )
    (tmp_path / "本包登记信息.json").write_text(
        '{"packType":"h5_swift_shell","codeAntiCorrelation":{"dartCodePrefix":"demo"}}',
        encoding="utf-8",
    )
    out = ensure_h5_vite_scaffold(
        tmp_path,
        app_name="Demo",
        prefix="demo",
        pack_type="h5_swift_shell",
    )
    assert out == h5
    assert "host: true" in (h5 / "vite.config.ts").read_text(encoding="utf-8")


def test_ensure_browser_bridge_mock_writes_and_patches(tmp_path: Path) -> None:
    h5 = tmp_path / "h5"
    bridge = h5 / "src" / "bridge"
    bridge.mkdir(parents=True)
    (bridge / "index.ts").write_text(
        "export function bridgeCall(action: string, payload = {}) {\n"
        "  return new Promise((resolve, reject) => {\n"
        "    const body = { ...payload, action };\n"
        "    if (action === 'shellReady') resolve({});\n"
        "    else reject(new Error('Bridge unavailable'));\n"
        "  });\n"
        "}\n",
        encoding="utf-8",
    )
    changed = ensure_browser_bridge_mock(h5, app_name_lower="demo")
    assert "src/bridge/browserMock.ts" in changed
    assert "src/bridge/index.ts" in changed
    mock = (bridge / "browserMock.ts").read_text(encoding="utf-8")
    assert "demoBridge" in mock
    assert "{{APP_NAME_LOWER}}" not in mock
    index = (bridge / "index.ts").read_text(encoding="utf-8")
    assert "tryBrowserBridgeMock" in index
    assert "Bridge unavailable" not in index


def test_ensure_browser_bridge_mock_idempotent(tmp_path: Path) -> None:
    h5 = tmp_path / "h5"
    bridge = h5 / "src" / "bridge"
    bridge.mkdir(parents=True)
    (bridge / "index.ts").write_text(
        "import { tryBrowserBridgeMock } from './browserMock';\n"
        "void tryBrowserBridgeMock;\n",
        encoding="utf-8",
    )
    ensure_browser_bridge_mock(h5, app_name_lower="acme")
    second = ensure_browser_bridge_mock(h5, app_name_lower="acme")
    assert "src/bridge/index.ts" not in second
