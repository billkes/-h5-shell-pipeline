"""Soft H5 bundle checks for h5_shell — warnings only, never blocks pipeline."""

from __future__ import annotations

import json
import re
from pathlib import Path

from batch.h5_site_paths import active_h5_entry_url, site_entry_rel

REGISTER_FILE = "本包登记信息.json"

FORBIDDEN_PATH_FRAGMENTS: tuple[str, ...] = (
    "/h5/",
    "\\h5\\",
    "/h5\\",
    "index.html",
    "index.htm",
    "/web/",
    "/bridge/",
    "/webview/",
)

FORBIDDEN_ICON_FONT_FRAGMENTS: tuple[str, ...] = (
    "iconfont",
    "fontawesome",
    "font-awesome",
    "material-icons",
    "material-symbols",
    "fa-solid",
    "fa-regular",
    "fa-brands",
)

INLINE_STYLE_MIN_CHARS = 200

_CSS_CLASS_RE = re.compile(r"\.([a-zA-Z_][\w-]*)")
_BARE_INTERACTIVE_RE = re.compile(
    r"<(button|input|a)\b[^>]*(?:style\s*=|class\s*=\s*['\"][^'\"]*\b(primary|btn|button|link)\b)",
    re.I,
)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _prefix_from_entry(entry_file: Path) -> str:
    stem = entry_file.stem
    if "_" in stem:
        return stem.rsplit("_", 1)[0]
    return stem


def _cap_prefix(prefix: str) -> str:
    if not prefix:
        return ""
    return prefix[0].upper() + prefix[1:]


def _collect_vault_css_text(vault_dir: Path, prefix: str) -> str:
    chunks: list[str] = []
    if not vault_dir.is_dir():
        return ""
    for path in sorted(vault_dir.iterdir()):
        if path.is_file() and path.suffix.lower() == ".css":
            try:
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    if not chunks:
        for path in vault_dir.glob("*.css"):
            try:
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    _ = prefix
    return "\n".join(chunks)


def _extract_css_classes(css_text: str) -> set[str]:
    return {m.group(1) for m in _CSS_CLASS_RE.finditer(css_text or "")}


H5_MODULAR_FULL_MIN_RENDER_MODULES = 5


def _inline_sprite_symbol_count(entry_file: Path | None) -> int:
    if entry_file is None or not entry_file.is_file():
        return 0
    try:
        text = entry_file.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0
    return len(re.findall(r"<symbol\b", text, re.I))


def _count_render_modules(panels_dir: Path, prefix: str) -> int:
    if not panels_dir.is_dir():
        return 0
    named = list(panels_dir.glob(f"{prefix}_render_*.js"))
    if len(named) >= H5_MODULAR_FULL_MIN_RENDER_MODULES:
        return len(named)
    generic = [p for p in panels_dir.glob("*_render_*.js") if p.is_file()]
    monolith = panels_dir / f"{prefix}_render.js"
    if monolith.is_file() and monolith not in generic:
        generic.append(monolith)
    return len(generic)


def _verify_h5_modular_render_split(
    *,
    vault_dir: Path,
    prefix: str,
    pattern: str,
    screen_pattern: str,
) -> list[str]:
    warns: list[str] = []
    if pattern != "h5_modular_full" or screen_pattern != "functional-render":
        return warns
    panels_dir = vault_dir / f"{prefix}_panels"
    count = _count_render_modules(panels_dir, prefix)
    if count < H5_MODULAR_FULL_MIN_RENDER_MODULES:
        warns.append(
            "H5 Gate：h5_modular_full + functional-render 但 render 模块只有 "
            f"{count} 个（应按屏拆分 ≥{H5_MODULAR_FULL_MIN_RENDER_MODULES}）"
        )
    return warns


_ONERROR_HTML_IN_ATTR = re.compile(
    r"onerror\s*=\s*[\"'][^\"']*(?:outerHTML|<(?:span|svg|div|use))",
    re.I,
)


def _verify_forbidden_onerror_html(vault_dir: Path, root: Path) -> list[str]:
    """Warn when inline handlers embed HTML (breaks attribute quoting → visible garble)."""
    warns: list[str] = []
    for child in vault_dir.rglob("*"):
        if not child.is_file() or child.suffix.lower() not in {".js", ".htm", ".html"}:
            continue
        try:
            text = child.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if _ONERROR_HTML_IN_ATTR.search(text):
            warns.append(
                "H5 Gate：onerror 属性内嵌 HTML（引号冲突会导致页面乱码）→ "
                f"{child.relative_to(root)}"
            )
    return warns


def _verify_hub_home_tab_bar(vault_dir: Path, workspace: Path, root: Path) -> list[str]:
    """Index-grid hub must NOT render bottom tab bar on #/home (entries on page)."""
    warns: list[str] = []
    nav = _navigation_pattern_from_lock(workspace).lower()
    if "index grid" not in nav and "grid home" not in nav:
        return warns
    for path in vault_dir.rglob("*render*.js"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "function renderHome" not in text:
            continue
        match = re.search(
            r"function renderHome\s*\([^)]*\)\s*\{([\s\S]*?)\n\s*\}",
            text,
        )
        if not match:
            continue
        body = match.group(1)
        if "tabBar" in body or "tab-bar" in body:
            warns.append(
                "H5 Gate：Index Grid Home 的 renderHome 不应拼接 tabBar（hub 用页内入口）→ "
                f"{path.relative_to(root)}"
            )
        if "c-paaow-page--full" in body and "c-paaow-page--hub" not in body:
            warns.append(
                "H5 Gate：renderHome 应使用 c-paaow-page--hub（无 tabBar 底栏占位）→ "
                f"{path.relative_to(root)}"
            )
    return warns


_TAB_ROOT_ROUTES = frozenset({"#/reference", "#/journal", "#/household"})

_DATA_DEPENDENT_ROUTES = (
    "#/journal/compare",
    "#/journal/compare-pick",
    "#/household/export-preview",
    "#/household/chart",
)

_EMPTY_CTA_GUARD_MARKERS = (
    "data-empty",
    "aria-disabled",
    "--off",
    "journalCount",
    "hasHouseholdData",
    "canCompare",
    "canExport",
)


def _extract_render_home_body(text: str) -> str:
    match = re.search(
        r"function renderHome\s*\([^)]*\)\s*\{([\s\S]*?)\n\s*\}",
        text,
    )
    return match.group(1) if match else ""


def _extract_data_routes(body: str) -> set[str]:
    return set(re.findall(r'data-route="(#[^"]+)"', body))


def _extract_tabbar_routes(text: str) -> set[str]:
    routes = set(re.findall(r"route:\s*['\"](#/[^'\"]+)['\"]", text))
    return {r for r in routes if r in _TAB_ROOT_ROUTES}


def _verify_hub_tile_route_dedup(
    vault_dir: Path, workspace: Path, root: Path
) -> list[str]:
    """Warn when hub renders tab-root routes AND bottom tabBar together (redundant)."""
    warns: list[str] = []
    nav = _navigation_pattern_from_lock(workspace).lower()
    if "index grid" not in nav and "grid home" not in nav:
        return warns
    for path in vault_dir.rglob("*render*.js"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "function renderHome" not in text:
            continue
        body = _extract_render_home_body(text)
        if not body:
            continue
        overlap = _extract_data_routes(body) & _extract_tabbar_routes(text)
        has_tabbar_in_home = "tabBar" in body or "tab-bar" in body
        if len(overlap) >= 2 and has_tabbar_in_home:
            warns.append(
                "H5 Gate：hub 同时存在 tab 入口 tile 与 tabBar（重复导航）"
                f" {sorted(overlap)} → {path.relative_to(root)}；"
                "home 保留页内入口、去掉 tabBar"
            )
    return warns


def _verify_empty_state_cta_guard(
    vault_dir: Path, workspace: Path, root: Path
) -> list[str]:
    """Data-dependent quick actions on #/home must expose disabled/empty guards."""
    warns: list[str] = []
    nav = _navigation_pattern_from_lock(workspace).lower()
    if "index grid" not in nav and "grid home" not in nav:
        return warns
    for path in vault_dir.rglob("*render*.js"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        body = _extract_render_home_body(text)
        if not body:
            continue
        for route in _DATA_DEPENDENT_ROUTES:
            if route not in body:
                continue
            if not any(marker in body for marker in _EMPTY_CTA_GUARD_MARKERS):
                warns.append(
                    f"H5 Gate：{route} 在 renderHome 暴露但未做 disabled/empty 兜底 → "
                    f"{path.relative_to(root)}"
                )
                break
            route_pos = body.find(route)
            window = body[max(0, route_pos - 400) : route_pos + 400]
            if not any(marker in window for marker in _EMPTY_CTA_GUARD_MARKERS):
                warns.append(
                    f"H5 Gate：{route} 在 renderHome 暴露但未做 disabled/empty 兜底 → "
                    f"{path.relative_to(root)}"
                )
    return warns


_TAB_ROOT_RENDER_FUNCS = (
    ("renderReference", "#/reference"),
    ("renderJournal", "#/journal"),
    ("renderHousehold", "#/household"),
)


def _extract_render_func_body(text: str, func_name: str) -> str:
    match = re.search(
        rf"function {func_name}\s*\([^)]*\)\s*\{{([\s\S]*?)\n\s*\}}",
        text,
    )
    return match.group(1) if match else ""


def _verify_tab_nav_replace(vault_dir: Path, root: Path) -> list[str]:
    """Bottom tab switches must replace history; tab roots must not expose back."""
    warns: list[str] = []
    core_text = ""
    render_text = ""
    core_path: Path | None = None
    render_path: Path | None = None
    for path in vault_dir.rglob("*.js"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "function tabBar" in text or ".tabBar = function" in text:
            core_text = text
            core_path = path
        if "function renderReference" in text or "function renderJournal" in text:
            render_text += "\n" + text
            render_path = path

    if not core_text:
        return warns

    tab_route_pat = "|".join(re.escape(r) for r in sorted(_TAB_ROOT_ROUTES))
    if re.search(rf'data-route="(?:{tab_route_pat})"', core_text):
        warns.append(
            "H5 Gate：tabBar 仍用 data-route 切换 Tab（会 push 历史栈）→ "
            f"{core_path.relative_to(root) if core_path else 'vault'}；"
            "应改为 data-action=\"tab\" + data-tab-route + navigate(..., true)"
        )
    elif 'data-action="tab"' not in core_text and "data-action='tab'" not in core_text:
        warns.append(
            "H5 Gate：tabBar 未见 data-action=\"tab\" 专用 Tab 切换 → "
            f"{core_path.relative_to(root) if core_path else 'vault'}"
        )

    has_tab_root_helper = "TAB_ROOTS" in core_text or "isTabRoot" in core_text
    has_replace_nav = "replacestate" in core_text.lower() and (
        "isTabRoot" in core_text or "TAB_ROOTS" in core_text
    )
    if not has_tab_root_helper or not has_replace_nav:
        warns.append(
            "H5 Gate：router.navigate 未对 Tab 根路由做 replaceState → "
            f"{core_path.relative_to(root) if core_path else 'vault'}"
        )

    if render_text:
        for func_name, tab_route in _TAB_ROOT_RENDER_FUNCS:
            body = _extract_render_func_body(render_text, func_name)
            if not body or "tabBar" not in body:
                continue
            if re.search(r"U\.appBar\([^)]*back:\s*true", body, re.I):
                warns.append(
                    f"H5 Gate：{func_name} 带 tabBar 仍启用 back: true（Tab 根页不应堆历史返回）→ "
                    f"{render_path.relative_to(root) if render_path else 'vault'}"
                )
            _ = tab_route
    return warns


def _verify_fallback_mark_error_delegate(
    vault_dir: Path,
    entry_file: Path | None,
    root: Path,
) -> list[str]:
    """When vault uses data-fallback-mark, entry must wire capture-phase error delegation."""
    warns: list[str] = []
    fallback_count = 0
    for child in vault_dir.rglob("*"):
        if not child.is_file() or child.suffix.lower() not in {".js", ".htm", ".html"}:
            continue
        try:
            fallback_count += child.read_text(encoding="utf-8", errors="ignore").count(
                "data-fallback-mark"
            )
        except OSError:
            continue
    if fallback_count == 0:
        return warns
    if entry_file is None or not entry_file.is_file():
        warns.append(
            "H5 Gate：vault 使用 data-fallback-mark 但缺少 bundle entry.htm"
        )
        return warns
    try:
        entry_text = entry_file.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return warns
    has_error_listener = (
        "addEventListener('error'" in entry_text
        or 'addEventListener("error"' in entry_text
    )
    has_fallback_read = (
        "data-fallback-mark" in entry_text
        and (
            "getAttribute('data-fallback-mark')" in entry_text
            or 'getAttribute("data-fallback-mark")' in entry_text
        )
    )
    uses_capture = ", true)" in entry_text or ",true)" in entry_text
    if not (has_error_listener and has_fallback_read):
        warns.append(
            "H5 Gate：entry.htm 缺少 data-fallback-mark 的 capture-phase error 委托 "
            f"→ {entry_file.relative_to(root)}"
        )
    elif not uses_capture:
        warns.append(
            "H5 Gate：error 委托应使用 capture phase（addEventListener(..., true)）→ "
            f"{entry_file.relative_to(root)}"
        )
    return warns


_BOOT_TIMEOUT_RE = re.compile(
    r"setTimeout\s*\(\s*boot\s*,",
    re.I,
)


def _verify_forbidden_boot_timeout(vault_dir: Path, root: Path) -> list[str]:
    """Warn when entry uses setTimeout(boot) fallback (causes visible flash)."""
    warns: list[str] = []
    for child in vault_dir.rglob("*"):
        if not child.is_file() or child.suffix.lower() not in {".js", ".htm", ".html"}:
            continue
        try:
            text = child.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if _BOOT_TIMEOUT_RE.search(text):
            warns.append(
                "H5 Gate：entry 使用 setTimeout(boot,…) 兜底会导致闪屏 → "
                f"{child.relative_to(root)}"
            )
            break
    return warns


def _verify_overlay_stack_soft(flutter_dir: Path) -> list[str]:
    """Hard-equivalent warnings when hash overlay routes omit base-page stack."""
    try:
        from batch.h5_legal_ui import is_h5_shell_project
        from batch.h5_overlay_stack import verify_h5_overlay_stack
    except ImportError:
        return []
    if not is_h5_shell_project(flutter_dir):
        return []
    return [f"H5 Gate：overlay stack → {item}" for item in verify_h5_overlay_stack(flutter_dir)]


def _verify_legal_ui_soft(flutter_dir: Path) -> list[str]:
    """Soft warnings when Legal overlay drifts from Modal Interior kit."""
    try:
        from batch.h5_legal_ui import is_h5_shell_project, verify_h5_legal_ui
    except ImportError:
        return []
    if not is_h5_shell_project(flutter_dir):
        return []
    return [f"H5 Gate：legal UI → {item}" for item in verify_h5_legal_ui(flutter_dir)]


def _verify_shell_ready_signal(vault_dir: Path, root: Path) -> list[str]:
    """Vault with splash route must call bridge shellReady after paint."""
    warns: list[str] = []
    vault_text = ""
    has_splash = False
    for child in vault_dir.rglob("*"):
        if not child.is_file() or child.suffix.lower() not in {".js", ".htm", ".html"}:
            continue
        try:
            text = child.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        vault_text += text
        if "renderSplash" in text or "#/splash" in text or "'/splash'" in text:
            has_splash = True
    if not has_splash:
        return warns
    if "shellReady" not in vault_text:
        warns.append(
            "H5 Gate：vault 含 splash 路由但未调用 bridge shellReady（Flutter 无法撤 LaunchVeil）"
        )
    return warns


def _verify_bridge_plaza(vault_dir: Path, root: Path) -> list[str]:
    """Soft-check hidden Bridge plaza route per H5壳广场页规范."""
    from batch.screen_inventory import project_includes_route

    if not project_includes_route(root, "/plaza"):
        return []

    warns: list[str] = []
    vault_text = ""
    for child in vault_dir.rglob("*"):
        if not child.is_file() or child.suffix.lower() not in {".js", ".htm", ".html"}:
            continue
        try:
            vault_text += child.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
    if not vault_text:
        return warns
    has_plaza = "#/plaza" in vault_text or "'/plaza'" in vault_text or '"/plaza"' in vault_text
    if not has_plaza:
        warns.append(
            "H5 Gate：未见 #/plaza 路由 — 须实现隐藏 Bridge 广场页（见 H5壳广场页规范.md）"
        )
        return warns
    for marker in ("shellReady", "pickImage", "purchase"):
        if marker not in vault_text and marker == "shellReady":
            continue
    bridge_markers = ("pickImage", "startRecord", "saveImageToAlbum", "purchase")
    if not any(m in vault_text for m in bridge_markers):
        warns.append(
            "H5 Gate：广场页须含 Bridge 验权按钮（pickImage / 录音 / 写图库 / purchase 等）"
        )
    return warns


def _verify_flutter_startup_shell(workspace: Path, root: Path) -> list[str]:
    """Soft-check Flutter/iOS startup splash architecture for h5_shell."""
    warns: list[str] = []
    lib_dir = workspace / "lib"
    ios_runner = workspace / "ios" / "Runner"
    dart_text = ""
    if lib_dir.is_dir():
        for dart_file in lib_dir.rglob("*.dart"):
            if not dart_file.is_file():
                continue
            try:
                dart_text += dart_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

    if "WebViewWidget" in dart_text or "WebViewController" in dart_text:
        has_veil = "LaunchVeil" in dart_text or "launch_veil" in dart_text.lower()
        if not has_veil:
            warns.append(
                "H5 Gate：Flutter shell 缺 LaunchVeil（LaunchScreen 续接遮罩）"
            )
        if "shellReady" not in dart_text:
            warns.append(
                "H5 Gate：Flutter Bridge 未处理 shellReady action"
            )
        if "loadFlutterAsset" in dart_text and "loadRequest" not in dart_text:
            warns.append(
                "H5 Gate：壳应 loadRequest(h5EntryUrl) 加载远程 H5，不应 loadFlutterAsset 本地 vault"
            )
        if "h5EntryUrl" not in dart_text and "h5_entry_url" not in dart_text.lower():
            warns.append(
                "H5 Gate：Flutter shell 未见 h5EntryUrl 配置（应从 本包登记信息.json 读取）"
            )
        if re.search(
            r"await\s+[^;]*\.warm\s*\([^)]*\)\s*;\s*\n\s*runApp",
            dart_text,
        ):
            warns.append(
                "H5 Gate：main() 在 runApp 前 await warm() 会导致 LaunchScreen 撤除后黑屏"
            )

    if ios_runner.is_dir():
        fc_custom = [
            p
            for p in ios_runner.glob("*.swift")
            if p.name != "AppDelegate.swift"
            and "FlutterViewController" in p.read_text(encoding="utf-8", errors="ignore")
        ]
        if dart_text and ("WebViewWidget" in dart_text) and not fc_custom:
            warns.append(
                "H5 Gate：iOS 缺自定义 FlutterViewController（splashScreenView 绑定）"
            )
        app_delegate = ios_runner / "AppDelegate.swift"
        if app_delegate.is_file():
            try:
                ad_text = app_delegate.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                ad_text = ""
            if "backgroundColor" not in ad_text:
                warns.append(
                    "H5 Gate：AppDelegate 未设置 window.backgroundColor（建议 .clear）"
                )

    return warns


def _read_register(workspace: Path) -> dict:
    path = workspace / REGISTER_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _navigation_pattern_from_lock(workspace: Path) -> str:
    """Read navigationPattern from visual lock (preferred) or register."""
    lock_path = workspace / "本包视觉锁.json"
    if lock_path.is_file():
        try:
            data = json.loads(lock_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                ds = data.get("designerDeckSelections") or {}
                nav = str(ds.get("navigationPattern") or "").strip()
                if nav:
                    return nav
                nav = str(data.get("navigation") or "").strip()
                if nav:
                    return nav
        except (OSError, json.JSONDecodeError):
            pass
    reg = _read_register(workspace)
    ds = reg.get("designerDeckSelections") or {}
    return str(ds.get("navigationPattern") or "").strip()


def bundle_entry_path(data: dict) -> str:
    for key in ("bundleEntryPath", "h5SiteEntryPath", "h5EntryPath", "bundle_entry_path"):
        val = str(data.get(key) or "").strip()
        if val:
            return val.replace("\\", "/")
    root = str(data.get("h5SiteRoot") or data.get("bundleVaultDir") or "").strip()
    entry = str(data.get("h5SiteEntry") or "").strip()
    if root and entry:
        return f"{root.rstrip('/')}/{entry}"
    anti = data.get("codeAntiCorrelation") or {}
    prefix = ""
    if isinstance(anti, dict):
        prefix = str(anti.get("dartCodePrefix") or "").strip()
    if prefix:
        return site_entry_rel(data, prefix)
    return ""


def verify_h5_bundle_soft(
    workspace: Path,
    flutter_dir: Path | None = None,
) -> list[str]:
    """Return soft warnings only; never raises."""
    warnings: list[str] = []
    data = _read_register(workspace)
    entry = bundle_entry_path(data)
    h5_url = active_h5_entry_url(data)
    if not h5_url:
        warnings.append(
            "H5 Gate：本包登记信息.json 缺少 h5EntryUrl / h5EntryUrlDev / appSlug（可继续流水线）"
        )
    elif not h5_url.startswith(("http://", "https://")):
        warnings.append(f"H5 Gate：h5EntryUrl 须以 http(s) 开头 → {h5_url}")
    if not entry:
        warnings.append(
            "H5 Gate：本包登记信息.json 缺少 h5SiteEntry / bundleEntryPath（可继续流水线）"
        )
        return warnings

    lowered = entry.lower().replace("\\", "/")
    for frag in FORBIDDEN_PATH_FRAGMENTS:
        if frag.lower() in lowered:
            warnings.append(
                f"H5 Gate：bundleEntryPath 含敏感片段 {frag!r} → {entry}"
            )

    root = flutter_dir or workspace
    entry_file = root / entry
    if not entry_file.is_file():
        warnings.append(f"H5 Gate：entry 文件未找到 → {entry}")

    vault_dir = entry_file.parent
    if vault_dir.is_dir():
        names = {p.name.lower() for p in vault_dir.iterdir() if p.is_file()}
        has_polish_file = any(
            "polish" in n or "baseline" in n or n.endswith(".css") for n in names
        )
        has_inline_polish = False
        if entry_file.is_file():
            try:
                entry_text = entry_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                entry_text = ""
            style_blocks = re.findall(
                r"<style[^>]*>(.*?)</style>",
                entry_text,
                re.I | re.S,
            )
            inline_css = "".join(style_blocks)
            has_inline_polish = len(inline_css.strip()) >= INLINE_STYLE_MIN_CHARS
            if not has_polish_file and not has_inline_polish:
                warnings.append(
                    f"H5 Gate：vault 内未见 polish/baseline CSS（{vault_dir.name}/）"
                )
        elif not has_polish_file:
            warnings.append(
                f"H5 Gate：vault 内未见 polish/baseline CSS（{vault_dir.name}/）"
            )
        pattern = str(data.get("h5VaultPattern") or "").strip()
        if pattern and entry_file.is_file():
            stem = entry_file.stem  # e.g. paaew_entry
            prefix = stem.rsplit("_", 1)[0] if "_" in stem else stem
            file_names = {p.name for p in vault_dir.iterdir() if p.is_file()}
            dir_names = {p.name for p in vault_dir.iterdir() if p.is_dir()}
            if pattern != "h5_monolith":
                if f"{prefix}_baseline.css" not in file_names:
                    warnings.append(
                        f"H5 Gate：h5VaultPattern={pattern} 但缺少 {prefix}_baseline.css"
                    )
            if pattern in {"h5_modular_svg", "h5_modular_full"}:
                has_marks_file = f"{prefix}_marks.svg" in file_names
                inline_symbols = _inline_sprite_symbol_count(entry_file)
                if not has_marks_file and inline_symbols < 8:
                    warnings.append(
                        f"H5 Gate：h5VaultPattern={pattern} 但缺少 {prefix}_marks.svg "
                        f"且 entry 内联 sprite 不足（{inline_symbols} symbols）"
                    )
            if pattern == "h5_modular_full":
                if f"{prefix}_panels" not in dir_names:
                    warnings.append(
                        f"H5 Gate：h5VaultPattern=h5_modular_full 但缺少 {prefix}_panels/"
                    )
                else:
                    screen_pattern = ""
                    warnings.extend(
                        _verify_h5_modular_render_split(
                            vault_dir=vault_dir,
                            prefix=prefix,
                            pattern=pattern,
                            screen_pattern=screen_pattern,
                        )
                    )
            if pattern == "h5_monolith" and len(file_names) > 1:
                from batch.h5_vite_scaffold import scaffold_exists

                if scaffold_exists(root):
                    extras = sorted(file_names - {entry_file.name})
                    warnings.append(
                        f"H5 Gate：Vite 包 deploy dir 应仅有 {entry_file.name}；"
                        f"发现多余文件 {extras} — 运行 dev.h5.build 清理并重新编译"
                    )
                else:
                    warnings.append(
                        f"H5 Gate：h5VaultPattern=h5_monolith 但 vault 含 {len(file_names)} 个文件"
                    )
            if pattern == "h5_monolith" and dir_names:
                from batch.h5_vite_scaffold import scaffold_exists

                if scaffold_exists(root):
                    warnings.append(
                        f"H5 Gate：Vite deploy dir 不应含子目录 {sorted(dir_names)} — 运行 dev.h5.build"
                    )
        for child in vault_dir.rglob("*"):
            if not child.is_file():
                continue
            try:
                if child.stat().st_size > 3_000_000:
                    warnings.append(
                        f"H5 Gate：单文件 >3MB → {child.relative_to(root)}"
                    )
            except OSError:
                continue
            if child.suffix.lower() in {".html", ".htm", ".js", ".css"}:
                try:
                    text = child.read_text(encoding="utf-8", errors="ignore")[:50000]
                except OSError:
                    continue
                lowered_text = text.lower()
                for frag in FORBIDDEN_ICON_FONT_FRAGMENTS:
                    if frag in lowered_text:
                        warnings.append(
                            f"H5 Gate：疑似通用 icon font 引用 {frag!r} → "
                            f"{child.relative_to(root)}"
                        )
                        break
                if re.search(r"data:image/[^;]+;base64,", text, re.I):
                    warnings.append(
                        f"H5 Gate：疑似 base64 内嵌图 → {child.relative_to(root)}"
                    )

    pubspec = root / "pubspec.yaml"
    if pubspec.is_file() and entry:
        try:
            pub_text = pubspec.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            pub_text = ""
        site_glob = str(Path(entry).parent).replace("\\", "/")
        if site_glob and site_glob in pub_text:
            warnings.append(
                f"H5 Gate：业务 H5 站点不应列入 pubspec assets → {site_glob}/"
            )

    if vault_dir and vault_dir.is_dir():
        warnings.extend(_verify_forbidden_onerror_html(vault_dir, root))
        warnings.extend(_verify_legal_ui_soft(root))
        warnings.extend(_verify_overlay_stack_soft(root))
        warnings.extend(_verify_hub_home_tab_bar(vault_dir, workspace, root))
        warnings.extend(_verify_hub_tile_route_dedup(vault_dir, workspace, root))
        warnings.extend(_verify_empty_state_cta_guard(vault_dir, workspace, root))
        warnings.extend(_verify_tab_nav_replace(vault_dir, root))
        warnings.extend(
            _verify_fallback_mark_error_delegate(vault_dir, entry_file, root)
        )
        warnings.extend(_verify_forbidden_boot_timeout(vault_dir, root))
        warnings.extend(_verify_shell_ready_signal(vault_dir, root))
        warnings.extend(_verify_bridge_plaza(vault_dir, root))
        try:
            from batch.h5_plaza_dev_gate import (
                find_plaza_obvious_entrance,
                verify_no_plaza_dev_entrance,
            )
            from batch.screen_inventory import project_includes_route

            if project_includes_route(root, "/plaza"):
                warnings.extend(verify_no_plaza_dev_entrance(vault_dir, root))
                warnings.extend(find_plaza_obvious_entrance(vault_dir, root))
        except ImportError:
            pass
        from batch.h5_deflavor_audit import verify_h5_deflavor_baseline

        for item in verify_h5_deflavor_baseline(root):
            warnings.append(f"H5 Gate Deflavor：{item}")
        try:
            from batch.welcome_canon import verify_h5_welcome_canon

            for item in verify_h5_welcome_canon(root):
                warnings.append(f"H5 Gate Welcome Canon：{item}")
        except ImportError:
            pass
    warnings.extend(_verify_flutter_startup_shell(workspace, root))

    return warnings


def print_h5_bundle_warnings(warnings: list[str]) -> None:
    if not warnings:
        return
    print("H5 Bundle Gate（软警告，不阻断流水线）:")
    for item in warnings:
        print(f"  ~ {item}")
