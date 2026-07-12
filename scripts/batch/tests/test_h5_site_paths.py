"""Tests for h5_shell remote site path helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from batch.h5_site_paths import (
    active_h5_entry_url,
    app_slug_from_name,
    h5_prod_entry_url,
    resolve_h5_remote_config,
    site_entry_rel,
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
        self.assertEqual(cfg["h5SiteRoot"], "h5_site/")
        self.assertTrue(cfg["h5EntryUrl"].startswith("http://"))
        self.assertEqual(cfg["h5EntryUrlProd"], "https://test.darin.beauty/gark/")
        self.assertEqual(cfg["bundleEntryPath"], "h5_site/gark_entry.htm")

    def test_site_entry_rel_from_register(self) -> None:
        reg = {"h5SiteRoot": "h5_site/", "h5SiteEntry": "demo_entry.htm"}
        self.assertEqual(site_entry_rel(reg, "demo"), "h5_site/demo_entry.htm")

    def test_active_h5_entry_url_prefers_h5_entry_url(self) -> None:
        reg = {
            "h5EntryUrl": "http://192.168.1.10:8080/",
            "h5EntryUrlProd": "https://test.darin.beauty/gark/",
        }
        self.assertEqual(active_h5_entry_url(reg), "http://192.168.1.10:8080/")


if __name__ == "__main__":
    unittest.main()
