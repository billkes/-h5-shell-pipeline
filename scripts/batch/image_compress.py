"""Compress workspace image assets to stay under a size budget."""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

MAX_IMAGE_BYTES = 300 * 1024
MAX_IMAGE_KB = MAX_IMAGE_BYTES // 1024

IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})

# AppIcon / Launch 等编组 A 真图：禁止缩放像素，仅允许保尺寸压缩。
DIMENSION_LOCKED_NAMES = frozenset(
    {
        "AppIcon.png",
        "AppIcon-1024.png",
        "launch_placeholder.png",
    }
)

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".dart_tool",
        "build",
        "Pods",
        ".symlinks",
        "DerivedData",
        "node_modules",
    }
)


@dataclass
class CompressReport:
    """Summary of a workspace image compression pass."""

    scanned: int = 0
    compressed: int = 0
    skipped_ok: int = 0
    still_over_limit: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    max_kb: int = MAX_IMAGE_KB


def _should_skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIR_NAMES


def discover_workspace_images(workspace: Path) -> list[Path]:
    """Collect raster assets under common app resource directories."""
    root = workspace.resolve()
    if not root.is_dir():
        return []

    found: dict[Path, None] = {}

    def add_file(path: Path) -> None:
        if path.suffix.lower() in IMAGE_SUFFIXES and path.is_file():
            found[path.resolve()] = None

    asset_dirs: list[Path] = []
    for candidate in (
        root / "assets" / "images",
        root / "h5" / "assets",
    ):
        if candidate.is_dir():
            asset_dirs.append(candidate)
    from batch.native_bundled_media import native_bundled_img_dir

    native_img = native_bundled_img_dir(root)
    if native_img and native_img.is_dir():
        asset_dirs.append(native_img)
    asset_dirs.extend(
        p
        for p in root.glob("**/assets/images")
        if p.is_dir()
    )
    asset_dirs.extend(
        p
        for p in root.glob("**/h5/assets")
        if p.is_dir()
    )

    seen_dirs: set[Path] = set()
    for asset_dir in asset_dirs:
        resolved = asset_dir.resolve()
        if resolved in seen_dirs:
            continue
        seen_dirs.add(resolved)
        for path in asset_dir.rglob("*"):
            if any(_should_skip_dir(part) for part in path.parents):
                continue
            add_file(path)

    for imageset in root.rglob("*.imageset"):
        if not imageset.is_dir():
            continue
        if any(_should_skip_dir(part) for part in imageset.parents):
            continue
        for path in imageset.iterdir():
            add_file(path)

    for iconset in root.rglob("*.appiconset"):
        if not iconset.is_dir():
            continue
        if any(_should_skip_dir(part) for part in iconset.parents):
            continue
        for path in iconset.iterdir():
            add_file(path)

    return sorted(found.keys())


def is_dimension_locked_asset(path: Path) -> bool:
    """True for canonical AppIcon / Launch slots that must keep exact pixels."""
    name = path.name
    if name not in DIMENSION_LOCKED_NAMES:
        return False
    parent_chain = {p.name for p in path.parents}
    parent_lower = {p.lower() for p in parent_chain}
    if name in {"AppIcon.png", "AppIcon-1024.png"} and "AppIcon.appiconset" in parent_chain:
        return True
    if name == "launch_placeholder.png" and (
        "launch_placeholder.imageset" in parent_lower
        or "LaunchPlaceholder.imageset" in parent_chain
    ):
        return True
    return False


def _compress_with_pngquant(path: Path, max_bytes: int) -> tuple[bool, int, int]:
    """Lossy PNG quantize without changing dimensions."""
    if shutil.which("pngquant") is None or path.suffix.lower() != ".png":
        return False, path.stat().st_size, path.stat().st_size

    before = path.stat().st_size
    if before <= max_bytes:
        return False, before, before

    tmp = path.with_suffix(f"{path.suffix}.pngquant_tmp")
    best_data: bytes | None = None
    best_size = before

    for quality in ("60-85", "55-80", "50-75", "45-70", "40-65"):
        cmd = [
            "pngquant",
            f"--quality={quality}",
            "--skip-if-larger",
            "--force",
            "--output",
            str(tmp),
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, check=False)
        if result.returncode != 0 or not tmp.is_file():
            tmp.unlink(missing_ok=True)
            continue
        size = tmp.stat().st_size
        data = tmp.read_bytes()
        if size < best_size:
            best_size = size
            best_data = data
        if size <= max_bytes:
            path.write_bytes(data)
            tmp.unlink(missing_ok=True)
            return True, before, size

    tmp.unlink(missing_ok=True)
    if best_data is not None and best_size < before:
        path.write_bytes(best_data)
        return True, before, best_size
    return False, before, before


def _compress_with_pillow_no_scale(path: Path, max_bytes: int) -> tuple[bool, int, int]:
    """Palette / quality passes only — never resize locked brand assets."""
    from PIL import Image

    before = path.stat().st_size
    if before <= max_bytes:
        return False, before, before

    with Image.open(path) as source:
        source.load()
        orig_size = source.size
        best_data: bytes | None = None
        best_size = before

        for colors in (256, 192, 128, 96, 64):
            working = source
            if source.mode == "RGBA":
                buf_img = source
            else:
                buf_img = source.convert("P", palette=Image.Palette.ADAPTIVE, colors=colors)
            buf = io.BytesIO()
            if source.mode == "RGBA":
                buf_img.save(buf, format="PNG", optimize=True, compress_level=9)
            else:
                buf_img.save(buf, format="PNG", optimize=True, compress_level=9)
            size = buf.tell()
            if size < best_size:
                best_size = size
                best_data = buf.getvalue()
            if size <= max_bytes:
                path.write_bytes(buf.getvalue())
                with Image.open(path) as check:
                    if check.size != orig_size:
                        raise OSError(f"{path}: dimension-locked asset resized unexpectedly")
                return True, before, size

        if best_data is not None and best_size < before:
            path.write_bytes(best_data)
            with Image.open(path) as check:
                if check.size != orig_size:
                    raise OSError(f"{path}: dimension-locked asset resized unexpectedly")
            return True, before, best_size

    return False, before, before


def compress_dimension_locked_file(
    path: Path,
    *,
    max_bytes: int = MAX_IMAGE_BYTES,
) -> tuple[bool, int, int]:
    """Compress AppIcon / Launch without changing width×height."""
    if not path.is_file():
        return False, 0, 0

    before = path.stat().st_size
    if before <= max_bytes:
        return False, before, before

    changed, b, a = _compress_with_pngquant(path, max_bytes)
    if a <= max_bytes:
        return changed, b, a

    try:
        changed2, b2, a2 = _compress_with_pillow_no_scale(path, max_bytes)
        return changed or changed2, before, a2
    except ImportError:
        return changed, b, a


def _save_jpeg(img, buf: io.BytesIO, quality: int) -> None:
    from PIL import Image

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.save(buf, format="JPEG", quality=quality, optimize=True)


def _save_webp(img, buf: io.BytesIO, quality: int) -> None:
    img.save(buf, format="WEBP", quality=quality, method=6)


def _save_png(img, buf: io.BytesIO) -> None:
    from PIL import Image

    if img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
        img = img.convert("RGBA" if "A" in img.mode else "RGB")
    if img.mode == "RGBA":
        img.save(buf, format="PNG", optimize=True, compress_level=9)
        return
    if img.mode != "P":
        img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
    img.save(buf, format="PNG", optimize=True, compress_level=9)


def _compress_with_pillow(path: Path, max_bytes: int) -> tuple[bool, int, int]:
    from PIL import Image

    before = path.stat().st_size
    if before <= max_bytes:
        return False, before, before

    suffix = path.suffix.lower()
    with Image.open(path) as source:
        source.load()
        scale = 1.0
        quality = 85
        best_data: bytes | None = None
        best_size = before

        for _ in range(40):
            working = source
            if scale < 1.0:
                width, height = source.size
                new_size = (
                    max(1, int(width * scale)),
                    max(1, int(height * scale)),
                )
                working = source.resize(new_size, Image.Resampling.LANCZOS)

            buf = io.BytesIO()
            if suffix in (".jpg", ".jpeg"):
                _save_jpeg(working, buf, quality)
            elif suffix == ".webp":
                _save_webp(working, buf, quality)
            else:
                _save_png(working, buf)

            size = buf.tell()
            if size <= max_bytes:
                path.write_bytes(buf.getvalue())
                return True, before, size

            if size < best_size:
                best_size = size
                best_data = buf.getvalue()

            if suffix in (".jpg", ".jpeg", ".webp") and quality > 35:
                quality -= 5
            elif scale > 0.25:
                scale *= 0.85
                quality = 85
            else:
                break

        if best_data is not None and best_size < before:
            path.write_bytes(best_data)
            return True, before, best_size

    return False, before, before


def _compress_with_sips(path: Path, max_bytes: int) -> tuple[bool, int, int]:
    before = path.stat().st_size
    if before <= max_bytes or shutil.which("sips") is None:
        return False, before, before

    tmp = path.with_suffix(f"{path.suffix}.compress_tmp")
    current = path
    changed = False

    for max_side in (2048, 1600, 1200, 960, 720, 540, 400, 320, 240):
        cmd = [
            "sips",
            "-Z",
            str(max_side),
            str(current),
            "--out",
            str(tmp),
        ]
        result = subprocess.run(cmd, capture_output=True, check=False)
        if result.returncode != 0 or not tmp.is_file():
            tmp.unlink(missing_ok=True)
            continue
        size = tmp.stat().st_size
        if size <= max_bytes:
            tmp.replace(path)
            return True, before, size
        if size < current.stat().st_size:
            tmp.replace(path)
            current = path
            changed = True

    tmp.unlink(missing_ok=True)
    after = path.stat().st_size
    return changed and after < before, before, after


def compress_image_file(
    path: Path,
    *,
    max_bytes: int = MAX_IMAGE_BYTES,
) -> tuple[bool, int, int]:
    """Compress one image file. Returns (changed, before_bytes, after_bytes)."""
    if not path.is_file():
        return False, 0, 0

    before = path.stat().st_size
    if before <= max_bytes:
        return False, before, before

    if is_dimension_locked_asset(path):
        return compress_dimension_locked_file(path, max_bytes=max_bytes)

    try:
        return _compress_with_pillow(path, max_bytes)
    except ImportError:
        return _compress_with_sips(path, max_bytes)
    except OSError as exc:
        raise OSError(f"{path}: {exc}") from exc


def compress_workspace_images(
    workspace: Path,
    *,
    max_bytes: int = MAX_IMAGE_BYTES,
) -> CompressReport:
    """Scan workspace assets and compress any image over the size budget."""
    report = CompressReport(max_kb=max_bytes // 1024)
    for path in discover_workspace_images(workspace):
        report.scanned += 1
        try:
            changed, before, after = compress_image_file(path, max_bytes=max_bytes)
        except OSError as exc:
            report.errors.append(str(exc))
            continue

        if before <= max_bytes:
            report.skipped_ok += 1
            continue

        rel = path.relative_to(workspace.resolve())
        if after <= max_bytes:
            report.compressed += 1
            kb_before = before // 1024
            kb_after = max(after // 1024, 1)
            print(f">>> 图片压缩: {rel} {kb_before}KB → {kb_after}KB")
        elif changed:
            report.compressed += 1
            print(
                f">>> 图片压缩: {rel} {before // 1024}KB → {after // 1024}KB "
                f"(仍略超 {report.max_kb}KB 上限)"
            )
            report.still_over_limit.append(str(rel))
        else:
            report.still_over_limit.append(str(rel))
            print(
                f">>> 警告: 图片 {rel} 为 {before // 1024}KB，"
                f"未能压至 {report.max_kb}KB 以下"
            )

    return report


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("用法: python -m batch.image_compress <workspace>", file=sys.stderr)
        return 2
    workspace = Path(args[0]).resolve()
    if not workspace.is_dir():
        print(f"目录不存在: {workspace}", file=sys.stderr)
        return 1
    report = compress_workspace_images(workspace)
    print(
        f">>> 图片审查完成: 扫描 {report.scanned} 张，"
        f"压缩 {report.compressed} 张，"
        f"已合规 {report.skipped_ok} 张"
    )
    if report.still_over_limit:
        print(f">>> 仍超限: {', '.join(report.still_over_limit)}")
    if report.errors:
        print(f">>> 错误: {'; '.join(report.errors)}")
    return 1 if report.still_over_limit or report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
