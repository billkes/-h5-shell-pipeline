"""Pack type helpers for batch routing."""

from __future__ import annotations

H5_SHELL = "h5_shell"
H5_FLUTTER_SHELL = "h5_flutter_shell"
H5_SWIFT_SHELL = "h5_swift_shell"
H5_OC_SHELL = "h5_oc_shell"

H5_SHELL_TYPES = frozenset(
    {
        H5_SHELL,  # legacy alias: Flutter runtime
        H5_FLUTTER_SHELL,
        H5_SWIFT_SHELL,
        H5_OC_SHELL,
    }
)
FLUTTER_RUNTIME_TYPES = frozenset(
    {"contentpack", "videostream", "tool_flutter", H5_SHELL, H5_FLUTTER_SHELL}
)
NATIVE_IOS_RUNTIME_TYPES = frozenset({H5_SWIFT_SHELL, H5_OC_SHELL})


def is_h5_shell(pack_type: str) -> bool:
    return (pack_type or "").strip() in H5_SHELL_TYPES


def h5_shell_runtime(pack_type: str) -> str:
    """Return the native shell runtime for H5 packages: flutter / swift / oc."""
    text = (pack_type or "").strip()
    if text == H5_SWIFT_SHELL:
        return "swift"
    if text == H5_OC_SHELL:
        return "oc"
    return "flutter"


def is_flutter_runtime(pack_type: str) -> bool:
    return (pack_type or "").strip() in FLUTTER_RUNTIME_TYPES


def is_native_ios_runtime(pack_type: str) -> bool:
    return (pack_type or "").strip() in NATIVE_IOS_RUNTIME_TYPES


def expected_webview_engine(pack_type: str) -> str:
    """Locked webviewEngine card for native shells; empty for Flutter (deck pick)."""
    runtime = h5_shell_runtime(pack_type)
    if runtime == "swift":
        return "wkwebview_swift"
    if runtime == "oc":
        return "wkwebview_oc"
    return ""
