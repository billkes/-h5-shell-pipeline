"""Verify h5_shell vault baseline deflavor rules (L0 reset + beautification guardrails)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from batch.h5_legal_ui import is_h5_shell_project, resolve_prefix
from batch.h5_site_paths import site_entry_path, vault_dir_path

REGISTER_FILE = "本包登记信息.json"

TAP_HIGHLIGHT_RE = re.compile(
    r"-webkit-tap-highlight-color\s*:\s*transparent",
    re.I,
)
SCROLLBAR_NONE_RE = re.compile(
    r"::-webkit-scrollbar\s*\{[^}]*display\s*:\s*none",
    re.I | re.S,
)
SCROLLBAR_BLOCK_RE = re.compile(
    r"::-webkit-scrollbar\s*\{[^}]*display\s*:\s*block",
    re.I | re.S,
)
SCROLLBAR_THUMB_RE = re.compile(r"::-webkit-scrollbar-thumb", re.I)
USER_SELECT_NONE_RE = re.compile(
    r"user-select\s*:\s*none|"
    r"-webkit-user-select\s*:\s*none",
    re.I,
)
VIEWPORT_COVER_RE = re.compile(r"viewport-fit\s*=\s*cover", re.I)
SAFE_AREA_RE = re.compile(
    r"safe-area-inset|env\s*\(\s*safe-area",
    re.I,
)


def _read_register(project: Path) -> dict:
    path = project / REGISTER_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _bundle_entry_path(reg: dict) -> str:
    from batch.h5_bundle_gate import bundle_entry_path

    return bundle_entry_path(reg)


def _collect_vault_css(vault_dir: Path, prefix: str) -> str:
    chunks: list[str] = []
    patterns = (
        f"{prefix}_baseline.css",
        f"{prefix}_primitives.css",
        f"{prefix}_composites.css",
        "polish.css",
    )
    names = {p.name for p in vault_dir.iterdir() if p.is_file()} if vault_dir.is_dir() else set()
    for name in patterns:
        if name in names:
            try:
                chunks.append((vault_dir / name).read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    for path in sorted(vault_dir.rglob("*.css")) if vault_dir.is_dir() else []:
        if path.name in patterns:
            continue
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(chunks)


def _collect_entry_css(project: Path, vault_dir: Path, entry_rel: str) -> str:
    entry = project / entry_rel
    if not entry.is_file():
        entry = vault_dir / Path(entry_rel).name
    if not entry.is_file():
        return ""
    try:
        text = entry.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    blocks = re.findall(r"<style[^>]*>(.*?)</style>", text, re.I | re.S)
    return "\n".join(blocks)


TEXT_SIZE_ADJUST_RE = re.compile(r"-webkit-text-size-adjust\s*:\s*100%", re.I)


def _native_app_dir(project: Path) -> Path | None:
    reg = _read_register(project)
    pack = str(reg.get("packType") or "").strip().lower()
    if pack in ("h5_oc_shell", "h5_swift_shell"):
        for child in sorted(project.iterdir()):
            if not child.is_dir():
                continue
            if not (any(child.rglob("*.m")) or any(child.rglob("*.swift"))):
                continue
            if (child / "Info.plist").is_file():
                return child
    flutter = project / "ios" / "Runner"
    if flutter.is_dir():
        return flutter
    return None


def _scan_h5_src_patterns(project: Path) -> list[str]:
    h5_src = project / "h5" / "src"
    if not h5_src.is_dir():
        return []
    issues: list[str] = []
    patterns: tuple[tuple[re.Pattern[str], str], ...] = (
        (re.compile(r"stopPropagation\s*\(", re.I), "H5: stopPropagation() 可能阻断点击委托"),
        (re.compile(r"touchstart.*blockFast|blockFastDoubleTap.*touchstart", re.I | re.S), "H5: blockFastDoubleTap 禁止绑 touchstart"),
        (re.compile(r"eruda|vconsole", re.I), "H5: 禁止 eruda/vconsole 调试脚本"),
        (re.compile(r"scrollbar-thumb", re.I), "H5: 禁止 scrollbar-thumb 网页滚动条样式"),
        (re.compile(r"::-webkit-scrollbar[^{]*\{[^}]*display\s*:\s*block", re.I | re.S), "H5: 禁止 display:block 滚动条"),
        (re.compile(r"<audio[^>]*\bcontrols\b", re.I), "H5: 禁止 <audio controls>，须用自定义 AudioPlayer"),
        (re.compile(r"isTextInteractionEnabled\s*=\s*false", re.I), "H5/壳: 禁止 isTextInteractionEnabled=false"),
    )
    for path in h5_src.rglob("*"):
        if not path.is_file() or path.suffix not in {".ts", ".vue", ".js", ".css"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(project)
        for rx, msg in patterns:
            if rx.search(text):
                issues.append(f"{msg} ({rel})")
    return issues


def _scan_native_deflavor(project: Path) -> list[str]:
    native = _native_app_dir(project)
    if native is None:
        return []
    issues: list[str] = []
    sources = [
        p
        for suffix in (".m", ".mm", ".swift")
        for p in native.rglob(f"*{suffix}")
        if p.is_file()
    ]
    joined = "\n".join(
        p.read_text(encoding="utf-8", errors="replace") for p in sources[:24]
    )
    if joined and "WebViewDeflavor" not in joined and "inputAccessoryView" not in joined:
        issues.append(f"Native: 缺少 WebViewDeflavor / inputAccessoryView 去键盘 accessory")
    if re.search(r"isTextInteractionEnabled\s*=\s*false", joined, re.I):
        issues.append("Native: 禁止 isTextInteractionEnabled=false（阻断 input 键盘）")
    if joined and "WKWebView" in joined:
        if not re.search(r"StripDoubleTap|doubleTap|DTTZ", joined, re.I):
            issues.append("Native: WKWebView 建议 strip 双击缩放手势")
    return issues


def verify_h5_source_deflavor(project: Path) -> list[str]:
    """Extra L0 rules on h5/src/styles before build:deploy."""
    css_path = project / "h5" / "src" / "styles" / "global.css"
    if not css_path.is_file():
        return []
    try:
        css = css_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    issues: list[str] = []
    if not re.search(r"overflow-x\s*:\s*hidden", css, re.I):
        issues.append("H5 source: html/body 缺少 overflow-x: hidden（《H5去风味规范》§1）")
    if not TEXT_SIZE_ADJUST_RE.search(css):
        issues.append("H5 source: 缺少 -webkit-text-size-adjust: 100%")
    return issues


def collect_h5_deflavor_violations(project: Path) -> list[str]:
    """Post-build checklist #18: H5 L0 + Legal scroll + native WK + interaction rg."""
    project = project.expanduser().resolve()
    issues: list[str] = []
    issues.extend(verify_h5_deflavor_baseline(project))
    try:
        from batch.h5_legal_ui import verify_h5_legal_ui, verify_h5_legal_view_mode

        issues.extend(verify_h5_legal_ui(project))
        issues.extend(verify_h5_legal_view_mode(project))
    except ImportError:
        pass
    issues.extend(verify_h5_source_deflavor(project))
    issues.extend(_scan_native_deflavor(project))
    issues.extend(_scan_h5_src_patterns(project))
    return issues


def verify_h5_deflavor_baseline(project: Path) -> list[str]:
    """Return issues when L0 deflavor baseline is missing or regressed."""
    if not is_h5_shell_project(project):
        return []

    reg = _read_register(project)
    entry_rel = _bundle_entry_path(reg)
    if not entry_rel:
        return ["missing h5SiteEntry / bundleEntryPath — cannot verify deflavor baseline"]

    vault_dir = (project / entry_rel).parent
    if not vault_dir.is_dir():
        return [f"vault dir not found: {vault_dir}"]

    prefix = resolve_prefix(project)
    css = _collect_vault_css(vault_dir, prefix) + "\n" + _collect_entry_css(
        project, vault_dir, entry_rel
    )
    if not css.strip():
        return ["no vault CSS found for deflavor baseline check"]

    issues: list[str] = []
    if not TAP_HIGHLIGHT_RE.search(css):
        issues.append("missing -webkit-tap-highlight-color: transparent in vault CSS")
    if not SCROLLBAR_NONE_RE.search(css):
        issues.append("missing global ::-webkit-scrollbar { display: none } in vault CSS")
    if SCROLLBAR_BLOCK_RE.search(css):
        issues.append(
            "FORBIDDEN: ::-webkit-scrollbar { display: block } detected (beautification regression)"
        )
    if SCROLLBAR_THUMB_RE.search(css):
        issues.append("FORBIDDEN: ::-webkit-scrollbar-thumb detected (web scrollbar styling)")
    if not USER_SELECT_NONE_RE.search(css):
        issues.append("missing user-select: none baseline for non-input elements")
    entry_text = ""
    entry_path = project / entry_rel
    if entry_path.is_file():
        try:
            entry_text = entry_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    if entry_text and not VIEWPORT_COVER_RE.search(entry_text):
        issues.append("entry.htm missing viewport-fit=cover")
    if not SAFE_AREA_RE.search(css) and entry_text and not SAFE_AREA_RE.search(entry_text):
        issues.append("missing safe-area-inset / env(safe-area-*) variables")

    return issues
