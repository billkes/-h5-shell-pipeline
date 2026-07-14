"""Tests for native LAN dev network helpers."""

from __future__ import annotations

import plistlib
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from batch.native_dev_network import (  # noqa: E402
    collect_native_dev_network_violations,
    sync_native_ats_lan_ip,
)


class NativeDevNetworkTests(unittest.TestCase):
    def test_sync_native_ats_lan_ip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            plist = ws / "ios" / "Demo" / "Info.plist"
            plist.parent.mkdir(parents=True)
            plist.write_bytes(plistlib.dumps({"CFBundleName": "Demo"}))
            changed = sync_native_ats_lan_ip(ws, lan_ip="192.168.1.42")
            self.assertEqual(changed, ["ios/Demo/Info.plist"])
            data = plistlib.loads(plist.read_bytes())
            ats = data["NSAppTransportSecurity"]
            self.assertTrue(ats["NSAllowsLocalNetworking"])
            self.assertTrue(ats["NSExceptionDomains"]["192.168.1.42"]["NSExceptionAllowsInsecureHTTPLoads"])

    def test_collect_violations_missing_ats_and_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            plist = ws / "ios" / "Demo" / "Info.plist"
            plist.parent.mkdir(parents=True)
            plist.write_bytes(plistlib.dumps({"CFBundleName": "Demo"}))
            vm = ws / "ios" / "Demo" / "DemoWebShellViewModel.swift"
            vm.write_text(
                "final class DemoWebShellViewModel {\n"
                "  private let loadTimeout: TimeInterval = 12\n"
                "  func handleNavigationFinished() {}\n"
                "}\n",
                encoding="utf-8",
            )
            issues = collect_native_dev_network_violations(ws)
            self.assertTrue(any("NSAllowsLocalNetworking" in i for i in issues))
            self.assertTrue(any("shellReady fallback" in i for i in issues))


if __name__ == "__main__":
    unittest.main()
