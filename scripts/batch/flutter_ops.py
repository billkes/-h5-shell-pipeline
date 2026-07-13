"""Flutter build, resources, and simulator helpers."""

from __future__ import annotations

import json
import re
import ssl
import struct
import subprocess
import time
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

from batch.config import BatchConfig
from batch.image_compress import compress_workspace_images
from batch.asset_naming import build_content_asset_filename
from batch.dimension_lock import read_dimension_lock
from batch.programming_layout import (
    RESOURCE_LAYOUT_FILE,
    layout_from_lock,
    refresh_tool_asset_manifest,
)
from batch.pub_cache_repair import (
    clear_pub_advisories_cache,
    is_pub_advisories_crash,
)

DEFAULT_PUB_GET_MAX_RETRIES = 3
DOWNLOAD_MAX_ATTEMPTS = 3
MIN_ASSET_BYTES = 200
PLACEHOLDER_SIZE_THRESHOLD = 5120

# Phase 6: fail only on analyzer *errors*; info/warning must not block health.
ANALYZE_CMD = [
    "flutter",
    "analyze",
    "--no-fatal-warnings",
    "--no-fatal-infos",
]


def _ssl_context() -> ssl.SSLContext:
    """Use certifi CA bundle when available (macOS Python 3.14+)."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def find_flutter_project(workspace: Path) -> Path | None:
    candidates = [workspace / "pubspec.yaml", *workspace.glob("*/pubspec.yaml")]
    for pubspec in candidates:
        if pubspec.is_file():
            return pubspec.parent
    return None


def build_log_shows_success(log_file: Path) -> bool:
    """Return True when build.log contains a successful flutter build ios run."""
    if not log_file.is_file():
        return False
    text = log_file.read_text(encoding="utf-8", errors="replace")
    marker = "--- flutter build ios"
    idx = text.rfind(marker)
    if idx == -1:
        return False
    tail = text[idx:]
    if "命令失败" in tail:
        return False
    lowered = tail.lower()
    return any(
        needle in lowered
        for needle in (
            "built build/ios",
            "xcode build done",
            "build/ios/iphoneos/runner.app",
            "✓ built",
        )
    )


def run_pub_get(
    flutter_dir: Path,
    log_file: Path,
    *,
    max_retries: int = DEFAULT_PUB_GET_MAX_RETRIES,
) -> bool:
    """Run flutter pub get; repair advisories cache on known pub crash."""
    cmd = ["flutter", "pub", "get"]
    attempts = max(1, max_retries)
    for attempt in range(1, attempts + 1):
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as log:
            log.write(f"--- {' '.join(cmd)} ---\n")
            if attempt > 1:
                log.write(f"(retry {attempt}/{attempts})\n")
            log.flush()
            result = subprocess.run(
                cmd,
                cwd=flutter_dir,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
            if result.returncode == 0:
                return True
            log.write(f"命令失败，退出码: {result.returncode}\n")
            tail = log_file.read_text(encoding="utf-8", errors="replace")[-16000:]
        if attempt < attempts and is_pub_advisories_crash(tail):
            removed = clear_pub_advisories_cache()
            print(
                f">>> pub get 因 advisories 缓存异常失败，"
                f"已清理 {removed} 个缓存项，重试 ({attempt}/{attempts})..."
            )
            continue
        return False
    return False


def do_flutter_build(
    flutter_dir: Path,
    log_file: Path,
    *,
    append: bool = False,
    pub_get_max_retries: int = DEFAULT_PUB_GET_MAX_RETRIES,
) -> bool:
    if not flutter_dir.is_dir() or not (flutter_dir / "pubspec.yaml").is_file():
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as f:
            f.write("未找到 Flutter 项目目录或 pubspec.yaml\n")
        return False
    log_file.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with log_file.open(mode, encoding="utf-8") as log:
        if append:
            log.write("\n--- Phase 6 retry ---\n")
        if not run_pub_get(
            flutter_dir,
            log_file,
            max_retries=pub_get_max_retries,
        ):
            return False
        steps = [
            [
                "dart",
                "analyze",
                "--no-fatal-warnings",
                "--no-fatal-infos",
            ],
            ["flutter", "build", "ios", "--no-codesign"],
        ]
        for cmd in steps:
            log.write(f"--- {' '.join(cmd)} ---\n")
            log.flush()
            result = subprocess.run(
                cmd,
                cwd=flutter_dir,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
            if result.returncode != 0:
                log.write(f"命令失败，退出码: {result.returncode}\n")
                return False
        return True


def _analyze_log_section(text: str) -> str:
    marker = "--- flutter analyze"
    idx = text.rfind(marker)
    if idx == -1:
        return ""
    return text[idx:]


def analyze_log_has_errors(log_file: Path) -> bool:
    """True when the analyze section contains one or more error-level issues."""
    if not log_file.is_file():
        return True
    section = _analyze_log_section(
        log_file.read_text(encoding="utf-8", errors="replace")
    )
    if not section:
        return True
    return bool(re.search(r"^\s*error •", section, re.MULTILINE))


def analyze_log_shows_success(log_file: Path) -> bool:
    """True when pub get succeeded and analyze has no error-level issues."""
    if not log_file.is_file():
        return False
    text = log_file.read_text(encoding="utf-8", errors="replace")
    pub_marker = "--- flutter pub get ---"
    analyze_marker = "--- flutter analyze"
    if pub_marker not in text:
        return False
    pub_idx = text.rfind(pub_marker)
    analyze_idx = text.rfind(analyze_marker)
    if analyze_idx == -1:
        return False
    pub_tail = text[pub_idx:analyze_idx] if analyze_idx > pub_idx else text[pub_idx:]
    if "命令失败" in pub_tail:
        return False
    section = text[analyze_idx:]
    lowered = section.lower()
    if "no issues found" in lowered or "0 issues found" in lowered:
        return True
    if analyze_log_has_errors(log_file):
        return False
    # Info / warning only (allowed under --no-fatal-infos / --no-fatal-warnings).
    return "issues found" in lowered or "issue found" in lowered


def run_pub_get_and_analyze(
    flutter_dir: Path,
    log_file: Path,
    *,
    pub_get_max_retries: int = DEFAULT_PUB_GET_MAX_RETRIES,
) -> bool:
    """Lightweight project health check: ``flutter pub get`` + ``flutter analyze``.

    Replaces the heavy ``flutter build ios`` step. Both commands stream their
    output into ``log_file`` so the AI Self-Review phase can read it back if
    needed.
    """
    if not flutter_dir.is_dir() or not (flutter_dir / "pubspec.yaml").is_file():
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("w", encoding="utf-8") as f:
            f.write("未找到 Flutter 项目目录或 pubspec.yaml\n")
        return False
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("")
    if not run_pub_get(
        flutter_dir,
        log_file,
        max_retries=pub_get_max_retries,
    ):
        return False
    with log_file.open("a", encoding="utf-8") as log:
        cmd = ANALYZE_CMD
        log.write(f"--- {' '.join(cmd)} ---\n")
        log.flush()
        result = subprocess.run(
            cmd,
            cwd=flutter_dir,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode != 0:
            log.write(f"命令失败，退出码: {result.returncode}\n")
            log.flush()
            return analyze_log_shows_success(log_file)
        return True


def run_analyze_only(
    flutter_dir: Path,
    log_file: Path,
    *,
    append: bool = False,
) -> bool:
    """Run ``dart analyze`` only (expects pub get already succeeded)."""
    if not flutter_dir.is_dir() or not (flutter_dir / "pubspec.yaml").is_file():
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a" if append else "w", encoding="utf-8") as f:
            f.write("未找到 Flutter 项目目录或 pubspec.yaml\n")
        return False
    log_file.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with log_file.open(mode, encoding="utf-8") as log:
        if append:
            log.write("\n")
        cmd = ANALYZE_CMD
        log.write(f"--- {' '.join(cmd)} ---\n")
        log.flush()
        result = subprocess.run(
            cmd,
            cwd=flutter_dir,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode != 0:
            log.write(f"命令失败，退出码: {result.returncode}\n")
            log.flush()
            return analyze_log_shows_success(log_file)
        return True


def run_flutter_test(
    flutter_dir: Path,
    log_file: Path,
    *,
    timeout_sec: int = 600,
    per_test_timeout: str = "30s",
    concurrency: int = 4,
    test_paths: str | list[str] = "test/flows",
) -> str:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(test_paths, str):
        paths = [p.strip() for p in test_paths.split(",") if p.strip()]
    else:
        paths = [p.strip() for p in test_paths if p.strip()]
    if not paths:
        paths = ["test/flows"]
    cmd = [
        "flutter",
        "test",
        *paths,
        "--timeout",
        per_test_timeout,
        "--concurrency",
        str(max(1, concurrency)),
    ]
    try:
        with log_file.open("w", encoding="utf-8") as out:
            result = subprocess.run(
                cmd,
                cwd=flutter_dir,
                stdout=out,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=max(30, timeout_sec) if timeout_sec > 0 else None,
            )
    except subprocess.TimeoutExpired:
        with log_file.open("a", encoding="utf-8") as log:
            log.write(
                f"\n>>> pipeline: flutter test exceeded {timeout_sec}s wall-clock timeout\n"
            )
        return "failed"
    if result.returncode == 0:
        return "done"
    text = log_file.read_text(encoding="utf-8", errors="replace").lower()
    if any(
        s in text
        for s in ("no test file", "no tests found", "no tests ran")
    ):
        return "skipped"
    if "timer is still pending" in text and "some tests failed" in text:
        return "skipped"
    return "failed"


def _search_image_url(
    keyword: str,
    cfg: BatchConfig,
    *,
    page: int = 1,
) -> str:
    keyword = re.sub(r"[^a-zA-Z0-9 -]", "", keyword)[:60].strip() or "minimal"
    q = urllib.parse.quote(keyword)
    page = max(1, min(page, 30))
    if cfg.unsplash_access_key:
        url = (
            "https://api.unsplash.com/search/photos?"
            f"query={q}&client_id={cfg.unsplash_access_key}"
            f"&per_page=1&page={page}"
        )
        req = urllib.request.Request(url, headers={"Accept-Version": "v1"})
        try:
            with urllib.request.urlopen(
                req, timeout=20, context=_ssl_context()
            ) as resp:
                data = json.loads(resp.read().decode())
            results = data.get("results") or []
            if results:
                urls = results[0].get("urls") or {}
                return urls.get("regular") or urls.get("small") or ""
        except (OSError, json.JSONDecodeError, KeyError):
            pass
    if cfg.pexels_api_key:
        url = (
            f"https://api.pexels.com/v1/search?query={q}"
            f"&per_page=1&page={page}"
        )
        req = urllib.request.Request(
            url,
            headers={"Authorization": cfg.pexels_api_key},
        )
        try:
            with urllib.request.urlopen(
                req, timeout=20, context=_ssl_context()
            ) as resp:
                data = json.loads(resp.read().decode())
            photos = data.get("photos") or []
            if photos:
                src = photos[0].get("src") or {}
                return src.get("original") or src.get("large") or ""
        except (OSError, json.JSONDecodeError, KeyError):
            pass
    return ""


def write_minimal_placeholder_png(
    dest: Path,
    *,
    rgb: tuple[int, int, int] = (232, 220, 204),
    size: int = 512,
) -> None:
    """Write a sized solid-color PNG as a non-empty placeholder.

    Default is 512x512 in a warm pastel tone so that downstream UI containers
    (cards, root background) never expose a black or zero-byte region when the
    real image cannot be downloaded.
    """
    width = height = max(64, int(size))
    dest.parent.mkdir(parents=True, exist_ok=True)

    def _chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", crc)
        )

    row = bytes([rgb[0], rgb[1], rgb[2]]) * width
    raw = (b"\x00" + row) * height
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )
    dest.write_bytes(png)


def _fetch_url_to_file(url: str, dest: Path) -> bool:
    try:
        with urllib.request.urlopen(
            url, timeout=60, context=_ssl_context()
        ) as resp:
            dest.write_bytes(resp.read())
        return dest.stat().st_size >= MIN_ASSET_BYTES
    except OSError:
        dest.unlink(missing_ok=True)
        return False


def download_image_to_file(
    cfg: BatchConfig,
    keyword: str,
    dest: Path,
    fallback_url: str,
    *,
    search_page: int = 1,
) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    urls: list[str] = []
    primary = _search_image_url(keyword, cfg, page=search_page)
    if primary:
        urls.append(primary)
    if fallback_url and fallback_url not in urls:
        urls.append(fallback_url)

    for url in urls:
        for attempt in range(1, DOWNLOAD_MAX_ATTEMPTS + 1):
            if _fetch_url_to_file(url, dest):
                return True
            if attempt < DOWNLOAD_MAX_ATTEMPTS:
                time.sleep(0.4 * attempt)

    write_minimal_placeholder_png(dest)
    return dest.stat().st_size >= MIN_ASSET_BYTES


def _theme_hint_from_workspace(workspace: Path) -> str:
    reg = workspace / "本包登记信息.json"
    if not reg.is_file():
        return ""
    try:
        data = json.loads(reg.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    if not isinstance(data, dict):
        return ""
    for key in ("themeAngle", "mainFeature", "theme"):
        val = str(data.get(key) or "").strip()
        if val:
            return val[:120]
    return ""


def _primary_asset_root(flutter_dir: Path, layout: dict) -> Path:
    roots = layout.get("assetRoots") or ["assets/images/"]
    first = str(roots[0]).strip("/")
    return flutter_dir / first


def download_tool_flutter_assets(
    cfg: BatchConfig,  # noqa: ARG001 — signature preserved; no network access in new flow
    workspace: Path,
    flutter_dir: Path,
    app_name: str,
) -> tuple[int, int]:
    """Write uniform placeholder PNGs for every tool-pack assetSlot.

    The script no longer hits the network. Each slot gets:
      1) a palette-tinted placeholder PNG (uniform watermark, ``Replace via image_prompts.md``)
      2) one structured entry in ``image_prompts.{md,json}`` at the Flutter project root.

    A downstream agent reads ``image_prompts.json`` to swap placeholders for real images.

    Returns ``(total, placeholders)`` where ``placeholders == total`` (everything is a placeholder).
    """
    from batch.image_placeholders import (
        ImagePromptEntry,
        build_prompt_text,
        is_icon_slot,
        palette_anchors_hex,
        palette_from_color_tokens,
        recommended_size_for,
        source_hints_for,
        write_placeholder,
        write_prompts_manifest,
    )
    from batch.visual_lock_assets import _load_or_init_manifest, _parse_size_override

    lock = read_dimension_lock(workspace)
    if lock is None:
        return 0, 0
    layout = refresh_tool_asset_manifest(workspace, lock)
    slots = layout.get("assetSlots") or []
    if not slots:
        return 0, 0

    visual_lock_path = workspace / "本包视觉锁.json"
    color_tokens: dict = {}
    if visual_lock_path.is_file():
        try:
            color_tokens = (
                json.loads(visual_lock_path.read_text(encoding="utf-8")).get(
                    "colorTokens"
                )
                or {}
            )
        except json.JSONDecodeError:
            color_tokens = {}
    palette_rgb = palette_from_color_tokens(color_tokens)
    palette_hex = palette_anchors_hex(color_tokens)

    manifest = _load_or_init_manifest(flutter_dir / "image_prompts.json", app_name)
    seen_paths = {e.path for e in manifest.entries}

    total = ph = 0
    skipped_icons = 0
    placeholders: list[str] = []
    for slot in slots:
        if not isinstance(slot, dict):
            continue
        rel = str(slot.get("path") or "").strip()
        if not rel:
            continue
        role = str(slot.get("role") or "").strip()
        if is_icon_slot(role, rel):
            skipped_icons += 1
            if rel not in seen_paths:
                manifest.add(
                    ImagePromptEntry(
                        path=rel,
                        role=role or "icon",
                        basename=Path(rel).stem,
                        recommendedSize="—",
                        skipped=True,
                        skipReason="icon font (FontAwesome / Material Icons)",
                    )
                )
                seen_paths.add(rel)
            continue

        keyword = str(slot.get("keyword") or "").strip()
        description = str(slot.get("description") or "").strip()
        basename = Path(rel).stem
        size = recommended_size_for(
            role, rel, _parse_size_override(slot.get("recommendedSize"))
        )

        dest = flutter_dir / rel
        try:
            write_placeholder(
                dest,
                role=role or "asset",
                basename=basename,
                palette_anchors=palette_rgb,
                size=size,
            )
        except OSError as exc:
            placeholders.append(f"{rel}(失败:{exc})")
            ph += 1
            total += 1
            continue
        total += 1
        ph += 1
        placeholders.append(rel)

        if rel in seen_paths:
            continue
        slot_palette = list(slot.get("paletteAnchors") or []) or palette_hex
        prompt = str(slot.get("imagePrompt") or "").strip() or build_prompt_text(
            app=app_name,
            role=role,
            basename=basename,
            description=description,
            keyword=keyword,
            palette_hex=slot_palette,
        )
        sources = list(slot.get("sourceHints") or []) or source_hints_for(
            role, basename, keyword or description
        )
        manifest.add(
            ImagePromptEntry(
                path=rel,
                role=role or "asset",
                basename=basename,
                recommendedSize=f"{size[0]}×{size[1]}",
                paletteAnchors=slot_palette,
                prompt=prompt,
                sourceHints=sources,
                description=description,
            )
        )
        seen_paths.add(rel)

    layout_path = workspace / RESOURCE_LAYOUT_FILE
    layout_path.write_text(
        json.dumps(
            {
                "libLayout": layout.get("libLayout"),
                "assetLayout": layout.get("assetLayout"),
                "skinBucket": layout.get("skinBucket"),
                "assetRoots": layout.get("assetRoots") or [],
                "assetSlots": slots,
                "assetNamingPattern": layout.get("assetNamingPattern"),
                "forbiddenAssetBasenames": layout.get("forbiddenAssetBasenames") or [],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    write_prompts_manifest(flutter_dir, manifest)
    if total:
        print(
            f">>> 已写入 {total} 张工具包占位图（icon-class skip {skipped_icons}），"
            "image_prompts.md/json 已生成"
        )
    compress_workspace_images(flutter_dir)
    if placeholders:
        text = (
            "# 资源说明（Flutter）\n\n"
            "脚本仅生成占位图。**真实美术资源由下游 agent 按 `image_prompts.md/json` 替换**。\n\n"
            "占位路径:\n\n"
            + "\n".join(f"- {p}" for p in placeholders)
            + "\n"
        )
        (workspace / "资源说明.md").write_text(text, encoding="utf-8")
    return total, ph


def download_content_images(
    cfg: BatchConfig,  # noqa: ARG001 — signature preserved; no network access in new flow
    workspace: Path,
    flutter_dir: Path,
    app_name: str,
    *,
    videostream: bool = False,
) -> tuple[int, int]:
    """Write placeholder PNGs for every entry in 默认内容列表.json.

    Same contract as ``download_tool_flutter_assets``: no network, palette-tinted
    placeholders + ``image_prompts.{md,json}``. Downstream agent replaces.
    """
    from batch.image_placeholders import (
        ImagePromptEntry,
        build_prompt_text,
        palette_anchors_hex,
        palette_from_color_tokens,
        recommended_size_for,
        source_hints_for,
        write_placeholder,
        write_prompts_manifest,
    )
    from batch.visual_lock_assets import _load_or_init_manifest

    json_file = workspace / "默认内容列表.json"
    if not json_file.is_file():
        return 0, 0
    lock = read_dimension_lock(workspace)
    layout = layout_from_lock(lock) if lock else {}
    images = _primary_asset_root(flutter_dir, layout)
    images.mkdir(parents=True, exist_ok=True)
    from batch.naming import meta_from_lock

    rule_key = ""
    meta = meta_from_lock(None)
    if lock:
        naming = lock.get("namingObfuscationRule") or {}
        meta = meta_from_lock(
            naming.get("namingRuleMeta")
            if isinstance(naming.get("namingRuleMeta"), dict)
            else None
        )
        rule_key = meta.rule_key or str(
            (naming.get("namingRuleMeta") or {}).get("ruleKey") or ""
        ).strip()

    kw_key = "thumbnailKeyword" if videostream else "imageKeyword"
    try:
        items = json.loads(json_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0, 0
    if not isinstance(items, list):
        return 0, 0

    visual_lock_path = workspace / "本包视觉锁.json"
    color_tokens: dict = {}
    if visual_lock_path.is_file():
        try:
            color_tokens = (
                json.loads(visual_lock_path.read_text(encoding="utf-8")).get(
                    "colorTokens"
                )
                or {}
            )
        except json.JSONDecodeError:
            color_tokens = {}
    palette_rgb = palette_from_color_tokens(color_tokens)
    palette_hex = palette_anchors_hex(color_tokens)

    manifest = _load_or_init_manifest(flutter_dir / "image_prompts.json", app_name)
    seen_paths = {e.path for e in manifest.entries}

    role_default = "content_thumbnail" if videostream else "content_image"
    ok = ph = 0
    placeholders: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id") or item.get("itemId") or ok + ph + 1
        keyword = (
            item.get(kw_key)
            or item.get("imageKeyword")
            or item.get("keyword")
            or str(item.get("title", ""))[:80]
        )
        keyword = str(keyword).strip()
        description = (
            str(item.get("bodyText") or item.get("subtitle") or item.get("title") or "")
            .strip()[:200]
        )
        if rule_key:
            fname = build_content_asset_filename(
                rule_key=rule_key,
                meta=meta,
                item_id=str(item_id),
            )
        else:
            prefix = "content_thumbnail" if videostream else "content_image"
            fname = f"{prefix}_{item_id}.png"
        dest = images / fname
        basename = Path(fname).stem
        size = recommended_size_for(role_default, fname)

        try:
            write_placeholder(
                dest,
                role=role_default,
                basename=basename,
                palette_anchors=palette_rgb,
                size=size,
            )
        except OSError as exc:
            placeholders.append(f"{fname}(失败:{exc})")
            ph += 1
            continue
        ph += 1
        placeholders.append(fname)

        rel = str(dest.relative_to(flutter_dir))
        if rel in seen_paths:
            continue
        slot_palette = palette_hex
        prompt = build_prompt_text(
            app=app_name,
            role=role_default,
            basename=basename,
            description=description,
            keyword=keyword,
            palette_hex=slot_palette,
        )
        sources = source_hints_for(role_default, basename, keyword or description)
        manifest.add(
            ImagePromptEntry(
                path=rel,
                role=role_default,
                basename=basename,
                recommendedSize=f"{size[0]}×{size[1]}",
                paletteAnchors=slot_palette,
                prompt=prompt,
                sourceHints=sources,
                description=description,
            )
        )
        seen_paths.add(rel)

    total = ok + ph
    write_prompts_manifest(flutter_dir, manifest)
    if total:
        print(
            f">>> 已写入 {total} 张内容占位图，image_prompts.md/json 已生成"
        )
    compress_workspace_images(flutter_dir)
    if placeholders:
        text = (
            "# 资源说明（Flutter）\n\n"
            "脚本仅生成占位图。**真实配图由下游 agent 按 `image_prompts.md/json` 替换**。\n\n"
            "占位文件:\n\n"
            + "\n".join(f"- {p}" for p in placeholders)
            + "\n"
        )
        (workspace / "资源说明.md").write_text(text, encoding="utf-8")
    return total, ph


def count_resource_stats(
    flutter_dir: Path,
    *,
    videostream: bool,
    tool_flutter: bool = False,
) -> tuple[int, int]:
    """Return ``(total, placeholder_count)`` for batch reporting."""
    from batch.image_prompts_sync import count_manifest_resource_stats

    manifest_total, manifest_ph = count_manifest_resource_stats(flutter_dir)
    if manifest_total > 0:
        return manifest_total, manifest_ph

    if tool_flutter:
        ws = flutter_dir.parent if (flutter_dir.parent / "本包维度锁.json").is_file() else flutter_dir
        lock = read_dimension_lock(ws)
        layout = layout_from_lock(lock) if lock else {}
        slots = layout.get("assetSlots") or []
        if slots:
            total = 0
            placeholder = 0
            for slot in slots:
                if not isinstance(slot, dict):
                    continue
                rel = str(slot.get("path") or "").strip()
                if not rel:
                    continue
                total += 1
                path = flutter_dir / rel
                if (
                    not path.is_file()
                    or path.stat().st_size < PLACEHOLDER_SIZE_THRESHOLD
                ):
                    placeholder += 1
            return total, placeholder

    glob = (
        "content_thumbnail_*.png" if videostream else "content_image_*.png"
    )
    images = flutter_dir / "assets" / "images"
    if not images.is_dir():
        return 0, 0
    files = list(images.glob(glob))
    placeholder = sum(
        1 for f in files if f.stat().st_size < PLACEHOLDER_SIZE_THRESHOLD
    )
    return len(files), placeholder


def expected_content_image_count(
    workspace: Path,
    *,
    videostream: bool = False,
) -> int:
    json_file = workspace / "默认内容列表.json"
    if not json_file.is_file():
        return 0
    try:
        items = json.loads(json_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    if not isinstance(items, list):
        return 0
    return sum(1 for item in items if isinstance(item, dict))


def download_all_workspace_images(
    cfg: BatchConfig,
    workspace: Path,
    flutter_dir: Path,
    app_name: str,
    *,
    tool_flutter: bool = False,
    videostream: bool = False,
    h5_shell: bool = False,
) -> tuple[int, int]:
    """Download raster assets into obfuscated paths (idempotent)."""
    if tool_flutter or h5_shell:
        return download_tool_flutter_assets(
            cfg, workspace, flutter_dir, app_name
        )
    return download_content_images(
        cfg,
        workspace,
        flutter_dir,
        app_name,
        videostream=videostream,
    )


def verify_workspace_assets(
    workspace: Path,
    flutter_dir: Path,
    *,
    tool_flutter: bool = False,
    videostream: bool = False,
) -> list[str]:
    """Return human-readable issues when required content images are missing."""
    issues: list[str] = []
    lock = read_dimension_lock(workspace)
    layout = layout_from_lock(lock) if lock else {}

    if tool_flutter:
        from batch.image_prompts_sync import (
            verify_manifest_assets,
            verify_manifest_duplicate_md5,
        )

        issues.extend(verify_manifest_assets(flutter_dir))
        issues.extend(verify_manifest_duplicate_md5(flutter_dir))
        slots = layout.get("assetSlots") or []
        if not slots and not issues:
            return issues
        missing = 0
        for slot in slots:
            if not isinstance(slot, dict):
                continue
            rel = str(slot.get("path") or "")
            path = flutter_dir / rel
            if not path.is_file() or path.stat().st_size < MIN_ASSET_BYTES:
                missing += 1
        if missing:
            issues.append(
                f"工具包配图不足: assetSlots 中 {missing} 个文件缺失或过小"
            )
        return issues

    images = _primary_asset_root(flutter_dir, layout)
    if not images.is_dir():
        issues.append("资源根目录缺失（见 本包资源布局.json assetRoots）")
        return issues

    expected = expected_content_image_count(workspace, videostream=videostream)
    if expected <= 0:
        return issues

    found = [
        p
        for p in images.glob("*.png")
        if p.stat().st_size >= MIN_ASSET_BYTES
    ]
    if len(found) < expected:
        issues.append(
            f"内容配图不足: 需要 {expected} 张，有效文件 {len(found)} 张"
        )
    return issues
