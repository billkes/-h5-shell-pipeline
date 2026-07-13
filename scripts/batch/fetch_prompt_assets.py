"""Fetch production raster assets from Unsplash/Pexels for ``image_prompts.json``."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

from batch.config import BatchConfig
from batch.flutter_ops import _fetch_url_to_file, _search_image_url
from batch.image_prompts_sync import (
    MIN_RENDERED_ASSET_BYTES,
    load_live_manifest_entries,
)

GENERIC_PROMPT_MARK = "An image asset for the iOS app"

APP_THEME_QUERIES: dict[str, str] = {
    "Knitio": "knitting yarn",
    "Passoo": "travel passport",
    "Steepo": "tea teapot",
    "Pureio": "skincare serum",
}

SLOT_SHORT_QUERIES: dict[str, str] = {
    "grain": "linen paper texture",
    "texture": "paper texture minimal",
    "shell": "cream paper texture",
    "welcome": "soft light aesthetic",
    "hero": "hero banner mood",
    "empty": "minimal object still life",
    "alpha": "desk flat lay",
    "beta": "journal organized",
    "gamma": "shelf collection",
    "export": "decorative paper pattern",
    "card": "paper card texture",
    "strip": "horizontal pattern band",
    "desk": "desk still life",
    "travel": "backpack map travel",
}

ROLE_QUERY_HINTS: dict[str, str] = {
    "shell_background_texture": "seamless paper linen texture warm minimal",
    "hero_banner": "flat lay still life soft light wide banner",
    "welcome_hero": "vertical soft mood hero minimal aesthetic",
    "export_layout_decor": "decorative paper card border minimal pattern",
}


@dataclass
class FetchPromptAssetsReport:
    total_entries: int = 0
    fetched: int = 0
    skipped: int = 0
    failed: list[str] = field(default_factory=list)


def _parse_size(raw: str) -> tuple[int, int]:
    raw = str(raw or "").replace("×", "x").lower()
    match = re.match(r"(\d+)\s*x\s*(\d+)", raw)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 1024, 1024


def _search_page_for(basename: str) -> int:
    digest = hashlib.sha256(basename.encode()).hexdigest()
    return 1 + (int(digest[:4], 16) % 8)


def _basename_tokens(basename: str) -> str:
    parts = re.split(r"[_\-\s]+", basename.lower())
    return " ".join(p for p in parts if p and p not in {"lk", "wn", "wku", "ys", "mwq"})


def build_stock_query(app: str, entry: dict) -> str:
    """Turn one manifest entry into an English stock-photo search query."""
    prompt = str(entry.get("prompt") or "").strip()
    description = str(entry.get("description") or "").strip()
    role = str(entry.get("role") or "").strip()
    basename = str(entry.get("basename") or Path(entry.get("path", "")).stem)

    if description:
        words = re.sub(r"[^a-zA-Z0-9 ,\-']", " ", description).split()
        base = " ".join(words[:5])
    elif prompt and GENERIC_PROMPT_MARK not in prompt:
        words = re.sub(r"[^a-zA-Z0-9 ,\-']", " ", prompt).split()
        base = " ".join(words[:6])
    elif role in ROLE_QUERY_HINTS:
        base = ROLE_QUERY_HINTS[role]
    else:
        name = basename.lower()
        theme = APP_THEME_QUERIES.get(app, "minimal aesthetic")
        slot_hint = ""
        for key, query in SLOT_SHORT_QUERIES.items():
            if key in name or key in role.lower():
                slot_hint = query
                break
        if slot_hint:
            base = f"{theme} {slot_hint}"
        else:
            base = theme

    base = re.sub(r"[^a-zA-Z0-9 ,\-']", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    return base[:48] or APP_THEME_QUERIES.get(app, "minimal")


def _hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        return None
    try:
        return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    except ValueError:
        return None


def fit_stock_image(
    source: Path,
    dest: Path,
    size: tuple[int, int],
    palette_anchors: list[str] | None = None,
) -> None:
    """Center-crop to cover ``size`` and apply a subtle palette grade."""
    width, height = max(64, size[0]), max(64, size[1])
    with Image.open(source) as img:
        rgb = img.convert("RGB")
        fitted = ImageOps.fit(rgb, (width, height), method=Image.Resampling.LANCZOS)

        anchors = palette_anchors or []
        tint = None
        for raw in anchors:
            tint = _hex_to_rgb(str(raw))
            if tint:
                break
        if tint:
            overlay = Image.new("RGB", fitted.size, tint)
            fitted = Image.blend(fitted, overlay, alpha=0.12)
            fitted = ImageEnhance.Color(fitted).enhance(1.08)
            fitted = ImageEnhance.Contrast(fitted).enhance(1.04)

        dest.parent.mkdir(parents=True, exist_ok=True)
        fitted.save(dest, format="PNG", optimize=True)


def _entry_is_production(path: Path, *, min_bytes: int) -> bool:
    if not path.is_file():
        return False
    if path.stat().st_size < min_bytes:
        return False
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except OSError:
        return False


def fetch_prompt_assets(
    flutter_dir: Path,
    cfg: BatchConfig,
    *,
    force: bool = False,
    min_bytes: int = MIN_RENDERED_ASSET_BYTES,
    sleep_sec: float = 0.35,
) -> FetchPromptAssetsReport:
    """Download stock photos for live manifest entries and fit to slot sizes."""
    manifest_path = flutter_dir / "image_prompts.json"
    report = FetchPromptAssetsReport()
    if not manifest_path.is_file():
        return report
    if not cfg.unsplash_access_key and not cfg.pexels_api_key:
        report.failed.append("missing UNSPLASH_ACCESS_KEY / PEXELS_API_KEY")
        return report

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.failed.append(f"invalid image_prompts.json: {exc}")
        return report

    app = str(data.get("app") or flutter_dir.name)
    entries = load_live_manifest_entries(flutter_dir)
    report.total_entries = len(entries)

    for entry in entries:
        rel = str(entry.get("path") or "").strip()
        if not rel:
            continue
        dest = flutter_dir / rel
        basename = str(entry.get("basename") or dest.stem)
        if not force and _entry_is_production(dest, min_bytes=min_bytes):
            report.skipped += 1
            continue

        query = build_stock_query(app, entry)
        page = _search_page_for(basename)
        url = _search_image_url(query, cfg, page=page)
        if not url:
            fallback = APP_THEME_QUERIES.get(app, "minimal aesthetic")
            url = _search_image_url(fallback, cfg, page=page + 1)
        if not url:
            report.failed.append(f"{rel}(no stock hit: {query})")
            continue

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        try:
            if not _fetch_url_to_file(url, tmp_path):
                report.failed.append(f"{rel}(download failed)")
                continue
            fit_stock_image(
                tmp_path,
                dest,
                _parse_size(str(entry.get("recommendedSize", "1024×1024"))),
                entry.get("paletteAnchors") or [],
            )
            if dest.stat().st_size >= min_bytes:
                report.fetched += 1
            else:
                report.failed.append(f"{rel}(fit too small)")
        except OSError as exc:
            report.failed.append(f"{rel}({exc})")
        finally:
            tmp_path.unlink(missing_ok=True)
        if sleep_sec > 0:
            time.sleep(sleep_sec)

    return report
