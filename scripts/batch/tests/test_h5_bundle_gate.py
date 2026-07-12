"""Tests for h5_shell soft bundle gate."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from batch.h5_bundle_gate import bundle_entry_path, verify_h5_bundle_soft


class H5BundleGateTests(unittest.TestCase):
    def test_bundle_entry_path_prefers_bundle_entry(self) -> None:
        data = {"h5EntryPath": "bad", "bundleEntryPath": "assets/swai_vault/swai_entry.htm"}
        self.assertEqual(bundle_entry_path(data), "assets/swai_vault/swai_entry.htm")

    def test_soft_warn_missing_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            warns = verify_h5_bundle_soft(ws)
            self.assertTrue(any("h5EntryUrl" in w for w in warns))
            self.assertTrue(any("h5SiteEntry" in w or "bundleEntryPath" in w for w in warns))

    def test_soft_warn_forbidden_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "本包登记信息.json").write_text(
                json.dumps({"bundleEntryPath": "assets/h5/index.html"}),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            self.assertTrue(any("敏感片段" in w for w in warns))

    def test_never_raises_on_bad_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "本包登记信息.json").write_text("{bad", encoding="utf-8")
            warns = verify_h5_bundle_soft(ws)
            self.assertIsInstance(warns, list)

    def test_inline_style_satisfies_polish_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault = ws / "assets" / "swai_vault"
            vault.mkdir(parents=True)
            css = "html,body{margin:0;padding:0;}" + ("x" * 250)
            entry = vault / "swai_entry.htm"
            entry.write_text(f"<html><head><style>{css}</style></head></html>", encoding="utf-8")
            (ws / "本包登记信息.json").write_text(
                json.dumps({"bundleEntryPath": "assets/swai_vault/swai_entry.htm"}),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            polish_warns = [w for w in warns if "polish/baseline CSS" in w]
            self.assertEqual(polish_warns, [])

    def test_warns_on_forbidden_icon_font_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault = ws / "assets" / "swai_vault"
            vault.mkdir(parents=True)
            entry = vault / "swai_entry.htm"
            entry.write_text(
                "<html><head><link href='iconfont.css'></head></html>",
                encoding="utf-8",
            )
            (ws / "本包登记信息.json").write_text(
                json.dumps({"bundleEntryPath": "assets/swai_vault/swai_entry.htm"}),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            self.assertTrue(any("iconfont" in w for w in warns))

    def test_warns_modular_full_missing_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault = ws / "assets" / "paaew_vault"
            vault.mkdir(parents=True)
            (vault / "paaew_entry.htm").write_text(
                "<html><head><style>" + ("x" * 250) + "</style></head></html>",
                encoding="utf-8",
            )
            (ws / "本包登记信息.json").write_text(
                json.dumps(
                    {
                        "bundleEntryPath": "assets/paaew_vault/paaew_entry.htm",
                        "h5VaultPattern": "h5_modular_full",
                    }
                ),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            self.assertTrue(any("baseline.css" in w for w in warns))

    def test_inline_sprite_satisfies_marks_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault = ws / "assets" / "paaew_vault"
            vault.mkdir(parents=True)
            symbols = "".join(
                f'<symbol id="m{i}"></symbol>' for i in range(10)
            )
            entry = vault / "paaew_entry.htm"
            entry.write_text(
                f"<html><head><style>{'x' * 250}</style></head>"
                f"<body><svg>{symbols}</svg></body></html>",
                encoding="utf-8",
            )
            (vault / "paaew_baseline.css").write_text(".u-paaew-btn {}", encoding="utf-8")
            (ws / "本包登记信息.json").write_text(
                json.dumps(
                    {
                        "bundleEntryPath": "assets/paaew_vault/paaew_entry.htm",
                        "h5VaultPattern": "h5_modular_full",
                    }
                ),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            marks_warns = [w for w in warns if "marks.svg" in w]
            self.assertEqual(marks_warns, [])

    def test_warns_onerror_html_in_attribute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault = ws / "assets" / "paaew_vault"
            panels = vault / "paaew_panels"
            panels.mkdir(parents=True)
            (vault / "paaew_baseline.css").write_text(".u-paaew-btn {}", encoding="utf-8")
            (vault / "paaew_entry.htm").write_text(
                "<html><head><style>" + ("x" * 250) + "</style></head></html>",
                encoding="utf-8",
            )
            (panels / "paaew_render.js").write_text(
                "function renderHome(){return '<img onerror=\"this.outerHTML=\\'<span></span>\\'\">';}",
                encoding="utf-8",
            )
            (ws / "本包登记信息.json").write_text(
                json.dumps({"bundleEntryPath": "assets/paaew_vault/paaew_entry.htm"}),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            self.assertTrue(any("onerror" in w and "乱码" in w for w in warns))

    def test_warns_hub_home_should_not_have_tab_bar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault = ws / "assets" / "paaew_vault"
            panels = vault / "paaew_panels"
            panels.mkdir(parents=True)
            (vault / "paaew_baseline.css").write_text(".u-paaew-btn {}", encoding="utf-8")
            (vault / "paaew_entry.htm").write_text(
                "<html><head><style>" + ("x" * 250) + "</style></head></html>",
                encoding="utf-8",
            )
            (panels / "paaew_render.js").write_text(
                "function renderHome() {\n"
                "  return '<div class=\"c-paaow-page\">hub</div>' + U.tabBar('');\n"
                "}\n",
                encoding="utf-8",
            )
            (ws / "本包登记信息.json").write_text(
                json.dumps(
                    {
                        "bundleEntryPath": "assets/paaew_vault/paaew_entry.htm",
                        "designerDeckSelections": {
                            "navigationPattern": "Index grid home → drill-down list",
                        },
                    }
                ),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            self.assertTrue(any("不应拼接 tabBar" in w for w in warns))

    def test_warns_missing_fallback_mark_error_delegate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault = ws / "assets" / "paaew_vault"
            panels = vault / "paaew_panels"
            panels.mkdir(parents=True)
            (vault / "paaew_baseline.css").write_text(".u-paaew-btn {}", encoding="utf-8")
            (vault / "paaew_entry.htm").write_text(
                "<html><head><style>" + ("x" * 250) + "</style></head><body></body></html>",
                encoding="utf-8",
            )
            (panels / "paaew_render.js").write_text(
                '<img data-fallback-mark="paaew-mark-ref" src="missing.png">',
                encoding="utf-8",
            )
            (ws / "本包登记信息.json").write_text(
                json.dumps({"bundleEntryPath": "assets/paaew_vault/paaew_entry.htm"}),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            self.assertTrue(any("error 委托" in w for w in warns))

    def test_hub_tile_route_dedup_warns_when_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault = ws / "assets" / "paaew_vault"
            panels = vault / "paaew_panels"
            panels.mkdir(parents=True)
            (vault / "paaew_baseline.css").write_text(".u-paaew-btn {}", encoding="utf-8")
            (vault / "paaew_entry.htm").write_text(
                "<html><head><style>" + ("x" * 250) + "</style></head></html>",
                encoding="utf-8",
            )
            (panels / "paaew_render.js").write_text(
                "var tabs = [{ route: '#/reference' }, { route: '#/journal' }, { route: '#/household' }];\n"
                "function renderHome() {\n"
                "  return '<button data-route=\"#/reference\">R</button>'\n"
                "    + '<button data-route=\"#/journal\">J</button>'\n"
                "    + '<button data-route=\"#/household\">H</button>'\n"
                "    + U.tabBar('');\n"
                "}\n",
                encoding="utf-8",
            )
            (ws / "本包登记信息.json").write_text(
                json.dumps(
                    {
                        "bundleEntryPath": "assets/paaew_vault/paaew_entry.htm",
                        "designerDeckSelections": {
                            "navigationPattern": "Index grid home → drill-down list",
                        },
                    }
                ),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            self.assertTrue(any("hub 同时存在 tab 入口 tile 与 tabBar" in w for w in warns))

    def test_empty_state_cta_guard_warns_when_missing_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault = ws / "assets" / "paaew_vault"
            panels = vault / "paaew_panels"
            panels.mkdir(parents=True)
            (vault / "paaew_baseline.css").write_text(".u-paaew-btn {}", encoding="utf-8")
            (vault / "paaew_entry.htm").write_text(
                "<html><head><style>" + ("x" * 250) + "</style></head></html>",
                encoding="utf-8",
            )
            (panels / "paaew_render.js").write_text(
                "function renderHome() {\n"
                "  return '<button data-route=\"#/journal/compare-pick\">Compare</button>'\n"
                "    + U.tabBar('');\n"
                "}\n",
                encoding="utf-8",
            )
            (ws / "本包登记信息.json").write_text(
                json.dumps(
                    {
                        "bundleEntryPath": "assets/paaew_vault/paaew_entry.htm",
                        "designerDeckSelections": {
                            "navigationPattern": "Index grid home → drill-down list",
                        },
                    }
                ),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            self.assertTrue(any("未做 disabled/empty 兜底" in w for w in warns))

    def test_hub_kpi_only_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault = ws / "assets" / "paaew_vault"
            panels = vault / "paaew_panels"
            panels.mkdir(parents=True)
            (vault / "paaew_baseline.css").write_text(".u-paaew-btn {}", encoding="utf-8")
            (vault / "paaew_entry.htm").write_text(
                "<html><head><style>" + ("x" * 250) + "</style></head></html>",
                encoding="utf-8",
            )
            (panels / "paaew_render.js").write_text(
                "var tabs = [{ route: '#/reference' }, { route: '#/journal' }, { route: '#/household' }];\n"
                "function renderHome() {\n"
                "  var canCompare = U.data.journalCount() >= 2;\n"
                "  return '<div class=\"c-paaow-page--hub\">'\n"
                "    + '<button data-route=\"#/reference\">R</button>'\n"
                "    + '<button data-route=\"#/journal\">J</button>'\n"
                "    + '<button data-route=\"#/household\">H</button>'\n"
                "    + '<button class=\"c-paaow-home-quick--off\" data-empty=\"1\" aria-disabled=\"true\">Compare</button>'\n"
                "    + '</div>';\n"
                "}\n",
                encoding="utf-8",
            )
            (ws / "本包登记信息.json").write_text(
                json.dumps(
                    {
                        "bundleEntryPath": "assets/paaew_vault/paaew_entry.htm",
                        "designerDeckSelections": {
                            "navigationPattern": "Index grid home → drill-down list",
                        },
                    }
                ),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            self.assertFalse(any("hub 同时存在 tab 入口 tile 与 tabBar" in w for w in warns))
            self.assertFalse(any("未做 disabled/empty 兜底" in w for w in warns))

    def test_tab_nav_replace_warns_when_tabbar_uses_data_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault = ws / "assets" / "paaew_vault"
            panels = vault / "paaew_panels"
            panels.mkdir(parents=True)
            (vault / "paaew_baseline.css").write_text(".u-paaew-btn {}", encoding="utf-8")
            (vault / "paaew_entry.htm").write_text(
                "<html><head><style>" + ("x" * 250) + "</style></head></html>",
                encoding="utf-8",
            )
            (panels / "paaew_core.js").write_text(
                "NS.ui.tabBar = function (active) {\n"
                "  return '<button data-route=\"#/reference\">R</button>';\n"
                "};\n"
                "NS.ui.router = { navigate: function (h) { location.hash = h; } };\n",
                encoding="utf-8",
            )
            (panels / "paaew_render.js").write_text(
                "function renderReference() {\n"
                "  return U.appBar('Reference', { back: true }) + U.tabBar('#/reference');\n"
                "}\n",
                encoding="utf-8",
            )
            (ws / "本包登记信息.json").write_text(
                json.dumps({"bundleEntryPath": "assets/paaew_vault/paaew_entry.htm"}),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            self.assertTrue(any("data-route 切换 Tab" in w for w in warns))
            self.assertTrue(any("back: true" in w for w in warns))

    def test_tab_nav_replace_passes_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault = ws / "assets" / "paaew_vault"
            panels = vault / "paaew_panels"
            panels.mkdir(parents=True)
            (vault / "paaew_baseline.css").write_text(".u-paaew-btn {}", encoding="utf-8")
            (vault / "paaew_entry.htm").write_text(
                "<html><head><style>" + ("x" * 250) + "</style></head></html>",
                encoding="utf-8",
            )
            (panels / "paaew_core.js").write_text(
                "NS.ui.TAB_ROOTS = ['#/reference', '#/journal', '#/household'];\n"
                "NS.ui.isTabRoot = function (hash) { return true; };\n"
                "NS.ui.tabBar = function (active) {\n"
                "  return '<button data-action=\"tab\" data-tab-route=\"#/reference\">R</button>';\n"
                "};\n"
                "NS.ui.router = {\n"
                "  navigate: function (hash, replace) {\n"
                "    if (replace == null && NS.ui.isTabRoot(hash)) replace = true;\n"
                "    if (replace) history.replaceState(null, '', hash);\n"
                "    else location.hash = hash;\n"
                "  }\n"
                "};\n",
                encoding="utf-8",
            )
            (panels / "paaew_render.js").write_text(
                "function renderReference() {\n"
                "  return U.appBar('Reference') + U.tabBar('#/reference');\n"
                "}\n",
                encoding="utf-8",
            )
            (ws / "本包登记信息.json").write_text(
                json.dumps({"bundleEntryPath": "assets/paaew_vault/paaew_entry.htm"}),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            tab_warns = [w for w in warns if "Tab" in w or "tabBar" in w.lower()]
            self.assertFalse(any("data-route 切换 Tab" in w for w in warns))
            self.assertFalse(any("back: true" in w for w in warns))
            self.assertFalse(any("replaceState" in w for w in tab_warns))

    def test_warns_settimeout_boot_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault = ws / "assets" / "paaew_vault"
            vault.mkdir(parents=True)
            (vault / "paaew_entry.htm").write_text(
                "<script>setTimeout(boot, 500);</script>",
                encoding="utf-8",
            )
            (ws / "本包登记信息.json").write_text(
                json.dumps({"bundleEntryPath": "assets/paaew_vault/paaew_entry.htm"}),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            self.assertTrue(any("setTimeout(boot" in w for w in warns))

    def test_warns_missing_shell_ready_on_splash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            vault = ws / "assets" / "paaew_vault"
            panels = vault / "paaew_panels"
            panels.mkdir(parents=True)
            (vault / "paaew_baseline.css").write_text(".x{}", encoding="utf-8")
            (vault / "paaew_entry.htm").write_text(
                "<html><head><style>" + ("x" * 250) + "</style></head></html>",
                encoding="utf-8",
            )
            (panels / "paaew_render.js").write_text(
                "function renderSplash(){return '<div/>';}",
                encoding="utf-8",
            )
            (ws / "本包登记信息.json").write_text(
                json.dumps({"bundleEntryPath": "assets/paaew_vault/paaew_entry.htm"}),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            self.assertTrue(any("shellReady" in w for w in warns))

    def test_warns_flutter_shell_missing_launch_veil(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            lib = ws / "lib"
            lib.mkdir(parents=True)
            (lib / "main.dart").write_text(
                "import 'webview.dart';\n"
                "void main() { runApp(WebViewWidget()); }\n",
                encoding="utf-8",
            )
            (ws / "本包登记信息.json").write_text(
                json.dumps({"bundleEntryPath": "assets/x_vault/x_entry.htm"}),
                encoding="utf-8",
            )
            warns = verify_h5_bundle_soft(ws, ws)
            self.assertTrue(any("LaunchVeil" in w for w in warns))


if __name__ == "__main__":
    unittest.main()
