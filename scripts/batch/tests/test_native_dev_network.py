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
                "  private let shellReadyFallback: TimeInterval = 4\n"
                "  func handleNavigationFinished() {}\n"
                "}\n",
                encoding="utf-8",
            )
            vc = ws / "ios" / "Demo" / "DemoWebViewController.swift"
            vc.write_text(
                "final class DemoWebViewController {\n"
                "  func requestLoad() {\n"
                "    webView.load(URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData))\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            issues = collect_native_dev_network_violations(ws)
            self.assertTrue(any("NSAllowsLocalNetworking" in i for i in issues))
            self.assertTrue(any("shellReady fallback" in i for i in issues))
            self.assertTrue(any("mainFrameDidFinish" in i for i in issues))
            self.assertTrue(any("loadTimeout=12s" in i for i in issues))
            self.assertTrue(any("reloadIgnoringLocalCacheData" in i for i in issues))
            self.assertTrue(any("NSURLErrorCancelled" in i for i in issues))

    def test_collect_passes_with_cdn_safe_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            plist = ws / "ios" / "Demo" / "Info.plist"
            plist.parent.mkdir(parents=True)
            data = {"CFBundleName": "Demo", "NSAppTransportSecurity": {"NSAllowsLocalNetworking": True}}
            plist.write_bytes(plistlib.dumps(data))
            vm = ws / "ios" / "Demo" / "DemoWebShellViewModel.swift"
            vm.write_text(
                "final class DemoWebShellViewModel {\n"
                "  private let loadTimeout: TimeInterval = 30\n"
                "  private let shellReadyFallback: TimeInterval = 8\n"
                "  private var mainFrameDidFinish = false\n"
                "  func handleNavigationFinished() { mainFrameDidFinish = true }\n"
                "  func scheduleShellReadyFallback() {}\n"
                "}\n",
                encoding="utf-8",
            )
            vc = ws / "ios" / "Demo" / "DemoWebViewController.swift"
            vc.write_text(
                "final class DemoWebViewController {\n"
                "  private static func isBenignNavigationCancel(_ error: Error) -> Bool { true }\n"
                "  func requestLoad() {\n"
                "    webView.load(URLRequest(url: url, cachePolicy: .useProtocolCachePolicy))\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            issues = collect_native_dev_network_violations(ws)
            self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
