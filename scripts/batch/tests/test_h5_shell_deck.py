"""Tests for h5_shell Bridge deck compat filtering."""

from __future__ import annotations

import unittest
from pathlib import Path

from batch.h5_shell_deck import (
    filter_bridge_cards,
    load_compat_matrix,
    load_h5_bridge_pools,
)
from batch.task_schema import COL_BRIDGE_CALL_STYLE, COL_WEBVIEW_ENGINE

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class H5ShellCompatTests(unittest.TestCase):
    def test_webview_flutter_excludes_call_handler(self) -> None:
        compat = load_compat_matrix(PROJECT_ROOT)
        pools = load_h5_bridge_pools(PROJECT_ROOT)
        cards = pools[COL_BRIDGE_CALL_STYLE]
        filtered = filter_bridge_cards(
            COL_BRIDGE_CALL_STYLE,
            cards,
            {COL_WEBVIEW_ENGINE: "webview_flutter"},
            compat,
        )
        self.assertIn("JavascriptChannel.postMessage(JSON)", filtered)
        self.assertNotIn("flutter_inappwebview.callHandler(Promise)", filtered)

    def test_inappwebview_excludes_javascript_channel(self) -> None:
        compat = load_compat_matrix(PROJECT_ROOT)
        pools = load_h5_bridge_pools(PROJECT_ROOT)
        cards = pools[COL_BRIDGE_CALL_STYLE]
        filtered = filter_bridge_cards(
            COL_BRIDGE_CALL_STYLE,
            cards,
            {COL_WEBVIEW_ENGINE: "flutter_inappwebview"},
            compat,
        )
        self.assertIn("flutter_inappwebview.callHandler(Promise)", filtered)
        self.assertNotIn("JavascriptChannel.postMessage(JSON)", filtered)


if __name__ == "__main__":
    unittest.main()
