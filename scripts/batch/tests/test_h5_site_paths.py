"""Tests for h5_shell remote site path helpers."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["H5_PROD_HOST"] = "test.darin.beauty"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from batch.h5_site_paths import (
    active_h5_entry_url,
    app_slug_from_name,
    h5_prod_entry_url,
    resolve_h5_remote_config,
    site_entry_rel,
    site_root_from_register,
)


class H5SitePathsTests(unittest.TestCase):
    def test_app_slug_lowercase(self) -> None:
        self.assertEqual(app_slug_from_name("Gark"), "gark")
        self.assertEqual(app_slug_from_name("Hathoo"), "hathoo")

    def test_prod_url(self) -> None:
        self.assertEqual(h5_prod_entry_url("gark"), "https://test.darin.beauty/gark/")

    def test_resolve_remote_config(self) -> None:
        cfg = resolve_h5_remote_config("Gark", prefix="gark")
        self.assertEqual(cfg["appSlug"], "gark")
        self.assertEqual(cfg["h5SiteUploadRoot"], "h5_site/")
        self.assertEqual(cfg["h5SiteRoot"], "h5_site/gark/")
        self.assertEqual(cfg["h5SiteEntry"], "index.html")
        self.assertTrue(cfg["h5EntryUrl"].startswith("http://"))
        self.assertEqual(cfg["h5EntryUrlProd"], "https://test.darin.beauty/gark/")
        self.assertEqual(cfg["bundleEntryPath"], "h5_site/gark/index.html")
        self.assertEqual(cfg["bundleVaultDir"], "h5_site/gark/")

    def test_site_entry_rel_from_register(self) -> None:
        reg = {
            "appSlug": "demo",
            "h5SiteRoot": "h5_site/demo/",
            "h5SiteEntry": "index.html",
        }
        self.assertEqual(site_entry_rel(reg, "demo"), "h5_site/demo/index.html")

    def test_site_entry_rel_coerces_legacy_entry_htm(self) -> None:
        reg = {
            "appSlug": "spinoo",
            "bundleEntryPath": "h5_site/spxx_entry.htm",
            "h5SiteEntry": "spxx_entry.htm",
        }
        self.assertEqual(site_entry_rel(reg, "spxx"), "h5_site/spinoo/index.html")

    def test_resolve_h5_vault_always_monolith(self) -> None:
        from batch.programming_layout import resolve_h5_vault_layout

        for persona in ("美国人", "法国人", "日本人", "中国人", "德国人"):
            layout = resolve_h5_vault_layout(persona, prefix="abcd", app_name="Pettoo")
            self.assertEqual(layout["h5VaultPattern"], "h5_monolith")
            self.assertEqual(layout["bundleEntryPath"], "h5_site/pettoo/index.html")
            self.assertEqual(layout["h5VaultFiles"], ["h5_site/pettoo/index.html"])

    def test_site_root_from_register_legacy_upload_root(self) -> None:
        reg = {"h5SiteRoot": "h5_site/", "appSlug": "temioo"}
        self.assertEqual(site_root_from_register(reg), "h5_site/temioo/")

    def test_active_h5_entry_url_prefers_h5_entry_url(self) -> None:
        reg = {
            "h5EntryUrl": "http://192.168.1.10:8080/",
            "h5EntryUrlProd": "https://test.darin.beauty/gark/",
        }
        self.assertEqual(active_h5_entry_url(reg), "http://192.168.1.10:8080/")


    def test_detect_lan_ip_prefers_darwin_wifi(self) -> None:
        from unittest.mock import patch

        from batch.h5_site_paths import detect_lan_ip

        with patch("batch.h5_site_paths._darwin_wifi_ip", return_value="192.168.11.74"):
            self.assertEqual(detect_lan_ip(), "192.168.11.74")

    def test_detect_lan_ip_skips_docker_bridge(self) -> None:
        from unittest.mock import patch

        from batch.h5_site_paths import detect_lan_ip

        with patch("batch.h5_site_paths._darwin_wifi_ip", return_value=None):
            with patch("socket.socket") as mock_sock_cls:
                mock_sock = mock_sock_cls.return_value.__enter__.return_value
                mock_sock.getsockname.return_value = ("172.19.0.1", 0)
                self.assertIsNone(detect_lan_ip())

    def test_h5_dev_entry_url_uses_lan_when_available(self) -> None:
        from unittest.mock import patch

        from batch.h5_site_paths import h5_dev_entry_url

        with patch("batch.h5_site_paths.detect_lan_ip", return_value="192.168.1.42"):
            self.assertEqual(h5_dev_entry_url(), "http://192.168.1.42:5174/")

    def test_sync_h5_dev_entry_urls(self) -> None:
        import json
        from unittest.mock import patch

        from batch.h5_site_paths import sync_h5_dev_entry_urls

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "本包登记信息.json").write_text(
                json.dumps({"h5EntryUrl": "http://127.0.0.1:5174/", "h5EntryUrlDev": "http://127.0.0.1:5174/"}),
                encoding="utf-8",
            )
            (ws / "Demo").mkdir()
            (ws / "Demo" / "DemoHostController.m").write_text(
                '- (void)DemoLoadRegister {\n    self.demoEntryUrl = @"http://127.0.0.1:5174/";\n}\n',
                encoding="utf-8",
            )
            with patch("batch.h5_site_paths.detect_lan_ip", return_value="10.0.0.5"):
                url = sync_h5_dev_entry_urls(ws, force=True)
            self.assertEqual(url, "http://10.0.0.5:5174/")
            reg = json.loads((ws / "本包登记信息.json").read_text(encoding="utf-8"))
            self.assertEqual(reg["h5EntryUrlDev"], "http://10.0.0.5:5174/")
            self.assertEqual(reg["h5EntryUrl"], "http://10.0.0.5:5174/")
            host = (ws / "Demo" / "DemoHostController.m").read_text(encoding="utf-8")
            self.assertIn('@"http://10.0.0.5:5174/"', host)


if __name__ == "__main__":
    unittest.main()
