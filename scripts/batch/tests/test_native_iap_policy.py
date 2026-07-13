"""Tests for native IAP no-storekit policy."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from batch.native_iap_policy import (  # noqa: E402
    collect_storekit_violations,
    enforce_no_storekit,
    strip_storekit_from_pbxproj,
    strip_storekit_from_xcscheme,
)


def test_strip_storekit_from_pbxproj() -> None:
    raw = (
        "\t\tAAAA /* FooIAP.storekit */ = "
        "{isa = PBXFileReference; lastKnownFileType = text.storekit; "
        "path = FooIAP.storekit; sourceTree = \"<group>\"; };\n"
        "\t\t\t\tBBBB /* FooIAP.storekit */,\n"
        "\t\tCCCC /* Info.plist */ = {isa = PBXFileReference;};\n"
    )
    cleaned = strip_storekit_from_pbxproj(raw)
    assert ".storekit" not in cleaned
    assert "Info.plist" in cleaned


def test_strip_storekit_from_xcscheme() -> None:
    raw = (
        "      </BuildableProductRunnable>\n"
        "      <StoreKitConfigurationFileReference\n"
        '         identifier = "Foo/FooIAP.storekit">\n'
        "      </StoreKitConfigurationFileReference>\n"
        "   </LaunchAction>\n"
    )
    cleaned = strip_storekit_from_xcscheme(raw)
    assert "StoreKitConfigurationFileReference" not in cleaned
    assert "</LaunchAction>" in cleaned


def test_enforce_no_storekit_cleans_workspace() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        storekit = ws / "Demo" / "DemoIAP.storekit"
        storekit.parent.mkdir(parents=True)
        storekit.write_text("{}", encoding="utf-8")
        pbx = ws / "Demo.xcodeproj" / "project.pbxproj"
        pbx.parent.mkdir(parents=True)
        pbx.write_text(
            "\t\tAAAA /* DemoIAP.storekit */ = "
            "{isa = PBXFileReference; path = DemoIAP.storekit; };\n",
            encoding="utf-8",
        )
        scheme = ws / "Demo.xcodeproj" / "xcshareddata" / "xcschemes" / "Demo.xcscheme"
        scheme.parent.mkdir(parents=True)
        scheme.write_text(
            "<StoreKitConfigurationFileReference "
            'identifier="Demo/DemoIAP.storekit"/>',
            encoding="utf-8",
        )

        changed = enforce_no_storekit(ws)
        assert changed
        assert not storekit.exists()
        assert collect_storekit_violations(ws) == []
