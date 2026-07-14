"""Tests for h5_vite scaffold."""

from __future__ import annotations

from pathlib import Path

from batch.h5_vite_scaffold import apply_h5_vite_scaffold, scaffold_exists


def test_apply_h5_vite_scaffold(tmp_path: Path) -> None:
    dst = apply_h5_vite_scaffold(tmp_path, app_name="Temioo", prefix="usfye")
    assert scaffold_exists(tmp_path)
    assert (dst / "package.json").is_file()
    assert (dst / "vite.config.ts").is_file()
    assert (dst / "src" / "main.ts").is_file()
    legal = dst / "src" / "legal" / "usfye_legal_bundled.ts"
    assert legal.is_file()
    text = legal.read_text(encoding="utf-8")
    assert "export const LEGAL" in text
    pkg = (dst / "package.json").read_text(encoding="utf-8")
    assert "vite-plugin-singlefile" in pkg
    vite_cfg = (dst / "vite.config.ts").read_text(encoding="utf-8")
    assert "host: true" in vite_cfg
    assert "legalMdSyncPlugin" in vite_cfg
    assert (dst / "legal-md-sync.plugin.mjs").is_file()
    assert '"dev": "vite --host"' in pkg or "'dev': 'vite --host'" in pkg
    copy_script = (dst / "scripts" / "copy-to-h5-site.mjs").read_text(encoding="utf-8")
    assert "h5_site" in copy_script
    assert "H5_APP_SLUG" in copy_script
    assert "uhfnf_vault" in copy_script or "_vault" in copy_script
    bridge = (dst / "src" / "bridge" / "index.ts").read_text(encoding="utf-8")
    assert "export { showSnack }" in bridge
    assert (dst / "src" / "lib" / "snack.ts").is_file()


def test_scaffold_idempotent(tmp_path: Path) -> None:
    apply_h5_vite_scaffold(tmp_path, app_name="Demo", prefix="demo")
    marker = tmp_path / "h5" / "README.md"
    marker.write_text("keep", encoding="utf-8")
    apply_h5_vite_scaffold(tmp_path, app_name="Demo", prefix="demo")
    assert marker.read_text(encoding="utf-8") == "keep"


def test_merge_toolchain_preserves_src(tmp_path: Path) -> None:
    src = tmp_path / "h5" / "src" / "views"
    src.mkdir(parents=True)
    (src / "HubView.vue").write_text("<template>hub</template>", encoding="utf-8")
    apply_h5_vite_scaffold(tmp_path, app_name="Temioo", prefix="usfye")
    assert (tmp_path / "h5" / "package.json").is_file()
    assert (src / "HubView.vue").is_file()
    assert (tmp_path / "h5" / "vite.config.ts").is_file()
