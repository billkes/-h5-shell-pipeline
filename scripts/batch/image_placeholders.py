"""Placeholder PNG writer + image_prompts manifest collector.

The new pipeline does NOT download or synthesize real artwork inside the script.
For every Image.asset path the workspace will use (declared by Designer's
`本包视觉锁.json.assetBrief`, Programmer's `本包资源布局.json.assetSlots`, or
PM's `默认内容列表.json`), the script writes a uniform palette-tinted
placeholder PNG and appends one entry to ``image_prompts.{md,json}`` at the
Flutter project root.

A separate downstream agent then reads ``image_prompts.json`` and replaces each
placeholder PNG with a real image (Midjourney / Unsplash / Pexels / DALL-E /
designer hand-off).

Icon-class slots are intentionally skipped here — they render via icon fonts
(`font_awesome_flutter` or Flutter built-in `Icons.*`) at runtime and never
ship as raster PNGs.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEFAULT_SIZE: tuple[int, int] = (1024, 1024)
SIZE_HINTS: dict[str, tuple[int, int]] = {
    "splash": (1242, 2688),
    "splash_background": (1242, 2688),
    "global_background": (1242, 2688),
    "marketing_bg": (1242, 2688),
    "welcome": (1242, 2688),
    "hero_default": (1600, 1200),
    "profile_hero": (1200, 900),
    "template_thumb": (800, 800),
    "template": (800, 800),
    "bento_tile": (800, 600),
    "pack_header": (1600, 900),
    "packheader": (1600, 900),
    "compareslot": (1200, 900),
    "compare_slot": (1200, 900),
    "feed_card": (1200, 1500),
    "content_image": (800, 1000),
    "content_thumbnail": (1080, 1920),
    "export": (1200, 1500),
    "export_preview": (1200, 1500),
    "export_template": (1200, 1500),
    "sticker": (640, 640),
    "hero_motif": (1024, 1024),
    "hero_iso": (1024, 1024),
    "illustration": (800, 800),
    "empty_state": (640, 640),
    "onboarding": (1024, 1280),
    "chart": (1200, 900),
    "reference_lookup": (1200, 900),
    "texture": (1024, 1024),
    "grain": (1024, 1024),
    "gradient": (1200, 1600),
    "dot_grid": (1024, 1024),
    "decorative": (1200, 600),
    "divider": (1200, 96),
    "shape_mask": (1024, 1024),
}

ICON_ROLE_TOKENS: tuple[str, ...] = (
    "icon",
    "nav_tab",
    "nav_icon",
    "app_bar_action",
    "checklist",
    "checklist_row",
    "tool_category",
    "tool_category_icon",
    "category_icon",
    "empty_state_icon",
    "splash_icon",
    "media",
    "daymark",
    "priority_list",
    "iap",
    "iap_coin",
)
ICON_NAME_TOKENS: tuple[str, ...] = (
    "icon_",
    "_icon",
    "nav_",
    "tool_",
    "checklist_",
    "stat_icon",
    "coin_",
    "_glyph",
    "glyph_",
)


@dataclass
class ImagePromptEntry:
    """One row in ``image_prompts.{md,json}``."""

    path: str
    role: str
    basename: str
    recommendedSize: str
    paletteAnchors: list[str] = field(default_factory=list)
    prompt: str = ""
    sourceHints: list[str] = field(default_factory=list)
    description: str = ""
    skipped: bool = False
    skipReason: str = ""


@dataclass
class PromptManifest:
    """Per-app manifest written to image_prompts.{md,json}."""

    app: str
    iconFont: dict[str, str] = field(default_factory=dict)
    entries: list[ImagePromptEntry] = field(default_factory=list)

    def add(self, entry: ImagePromptEntry) -> None:
        self.entries.append(entry)

    def to_json(self) -> str:
        return json.dumps(
            {
                "app": self.app,
                "iconFont": self.iconFont,
                "entries": [asdict(e) for e in self.entries],
            },
            indent=2,
            ensure_ascii=False,
        )

    def to_markdown(self) -> str:
        lines: list[str] = []
        lines.append(f"# image_prompts — {self.app}")
        lines.append("")
        lines.append(
            "This file lists every raster asset declared by Designer / PM / Resource Layout."
        )
        lines.append(
            "A uniform PLACEHOLDER PNG has been written to each path. Replace it with a real"
        )
        lines.append(
            "image via Midjourney / DALL-E / Stable Diffusion / Unsplash / Pexels — keep the"
        )
        lines.append("same path so Dart code keeps working.")
        lines.append("")
        if self.iconFont:
            family = self.iconFont.get("family") or "—"
            package = self.iconFont.get("package") or "—"
            lines.append(
                f"> **Icons** are NOT in this manifest. They render via icon fonts at runtime "
                f"(`{package}` / `{family}`). Do not produce raster PNGs for icon-class slots."
            )
            lines.append("")
        live = [e for e in self.entries if not e.skipped]
        skipped = [e for e in self.entries if e.skipped]
        lines.append(f"- total: {len(self.entries)}  ·  live: {len(live)}  ·  skipped: {len(skipped)}")
        lines.append("")
        for idx, e in enumerate(live, start=1):
            lines.append(f"## {idx}. {e.basename}  (`{e.path}`)")
            lines.append(f"- role: `{e.role}`")
            lines.append(f"- recommendedSize: {e.recommendedSize}")
            if e.paletteAnchors:
                lines.append(
                    "- paletteAnchors: " + " ".join(f"`{c}`" for c in e.paletteAnchors)
                )
            if e.description:
                lines.append(f"- description: {e.description}")
            lines.append(f"- prompt: {e.prompt or '(generate per role + theme)'}")
            if e.sourceHints:
                lines.append("- sourceHints: " + " · ".join(e.sourceHints))
            lines.append("")
        if skipped:
            lines.append("---")
            lines.append("")
            lines.append("### Skipped (icon-class slots — render via icon font)")
            lines.append("")
            for e in skipped:
                lines.append(
                    f"- `{e.path}` — role `{e.role}` — {e.skipReason or 'icon font'}"
                )
            lines.append("")
        return "\n".join(lines) + "\n"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    raw = str(value or "").strip().lstrip("#")
    if len(raw) != 6:
        return (200, 200, 200)
    try:
        return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))
    except ValueError:
        return (200, 200, 200)


def is_icon_slot(role: str, path: str) -> bool:
    """True when this slot should be served by an icon font, not a raster PNG."""
    r = (role or "").strip().lower()
    p = (path or "").strip().lower()
    name = Path(p).stem.lower()
    if any(token in r for token in ICON_ROLE_TOKENS):
        return True
    if "/icons/" in p or "/glyph_" in p or "/icon_" in p:
        return True
    if any(name.startswith(token) for token in ICON_NAME_TOKENS):
        return True
    if any(name.endswith(token) for token in ICON_NAME_TOKENS):
        return True
    if name in {"coin", "coins"}:
        return True
    return False


def recommended_size_for(role: str, path: str, override: tuple[int, int] | None = None) -> tuple[int, int]:
    if override:
        return override
    r = (role or "").strip().lower()
    name = Path(path or "").stem.lower()
    for key, size in SIZE_HINTS.items():
        if key in r:
            return size
    for key, size in SIZE_HINTS.items():
        if key in name:
            return size
    return DEFAULT_SIZE


def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for cand in candidates:
        try:
            return ImageFont.truetype(cand, size)
        except OSError:
            continue
    return ImageFont.load_default()


def write_placeholder(
    dest: Path,
    *,
    role: str,
    basename: str,
    palette_anchors: list[tuple[int, int, int]],
    size: tuple[int, int] = DEFAULT_SIZE,
) -> None:
    """Write a uniform palette-tinted placeholder PNG with replace-hint watermark.

    Same look across every slot type so downstream tooling can detect placeholders
    cheaply (file size, mean color, watermark text).
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    fill = palette_anchors[0] if palette_anchors else (228, 220, 204)
    stripe = palette_anchors[1] if len(palette_anchors) > 1 else (180, 168, 148)
    w, h = max(64, size[0]), max(64, size[1])
    img = Image.new("RGB", (w, h), fill)
    draw = ImageDraw.Draw(img)

    step = max(48, min(w, h) // 12)
    for i in range(-h, w, step):
        draw.line([(i, 0), (i + h, h)], fill=stripe, width=2)

    border = palette_anchors[-1] if palette_anchors else (120, 110, 90)
    inset = max(8, min(w, h) // 80)
    draw.rectangle((inset, inset, w - inset, h - inset), outline=border, width=3)

    title_font = _load_font(max(28, min(w, h) // 14))
    body_font = _load_font(max(18, min(w, h) // 28))
    small_font = _load_font(max(14, min(w, h) // 40))
    text_color = (32, 24, 16)

    cw, ch = w // 2, h // 2

    def _centered(txt: str, fnt: ImageFont.ImageFont, dy: int) -> None:
        bbox = draw.textbbox((0, 0), txt, font=fnt)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((cw - tw / 2, ch - th / 2 + dy), txt, fill=text_color, font=fnt)

    _centered("PLACEHOLDER", title_font, -int(min(w, h) * 0.12))
    _centered(f"role · {role}", body_font, int(min(w, h) * 0.02))
    _centered(basename, body_font, int(min(w, h) * 0.08))
    _centered(f"{w}×{h}", small_font, int(min(w, h) * 0.14))

    hint = "Replace via image_prompts.md"
    draw.text((inset + 8, inset + 8), hint, fill=text_color, font=small_font)

    img.save(dest, format="PNG", optimize=True)


def write_prompts_manifest(workspace: Path, manifest: PromptManifest) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "image_prompts.json").write_text(manifest.to_json(), encoding="utf-8")
    (workspace / "image_prompts.md").write_text(manifest.to_markdown(), encoding="utf-8")


def palette_from_color_tokens(color_tokens: dict | None) -> list[tuple[int, int, int]]:
    """Pull a 2-3 color palette from `本包视觉锁.json.colorTokens.light` for placeholder tint."""
    light = ((color_tokens or {}).get("light")) or {}
    keys = ("primaryContainer", "surfaceVariant", "secondary", "primary", "surface", "outline")
    anchors: list[tuple[int, int, int]] = []
    for k in keys:
        v = light.get(k)
        if isinstance(v, str) and v.startswith("#"):
            anchors.append(hex_to_rgb(v))
        if len(anchors) >= 3:
            break
    if not anchors:
        anchors = [(228, 220, 204), (180, 168, 148), (120, 110, 90)]
    return anchors


def palette_anchors_hex(color_tokens: dict | None) -> list[str]:
    light = ((color_tokens or {}).get("light")) or {}
    keys = ("primary", "primaryContainer", "surface", "surfaceVariant", "secondary")
    out: list[str] = []
    for k in keys:
        v = light.get(k)
        if isinstance(v, str) and v.startswith("#") and len(v) == 7:
            out.append(v)
        if len(out) >= 3:
            break
    return out or ["#E4DCCC", "#B4A894", "#785A46"]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def build_prompt_text(
    *,
    app: str,
    role: str,
    basename: str,
    description: str,
    keyword: str,
    palette_hex: list[str],
) -> str:
    """Compose a 2-4 sentence English AI prompt for the downstream image agent."""
    role_l = (role or "").lower()
    parts: list[str] = []

    if "splash" in role_l or "splash" in basename.lower():
        parts.append(
            f"A vertical full-bleed splash background for the iOS app '{app}', "
            "tall composition with a clear focal zone in the top third for app title."
        )
    elif "background" in role_l or "background" in basename.lower() or "global" in basename.lower():
        parts.append(
            f"A subtle global background texture for the iOS app '{app}', "
            "very soft, low contrast, suitable behind UI cards and lists."
        )
    elif "feed" in role_l or "content_image" in basename.lower() or role_l == "content_image":
        parts.append(
            f"A vivid editorial photograph illustrating the content item '{_norm(description) or _norm(keyword)}' "
            f"for the iOS app '{app}'. Natural light, magazine quality."
        )
    elif "content_thumbnail" in basename.lower() or role_l == "content_thumbnail":
        parts.append(
            f"A 9:16 vertical thumbnail / first-frame still for a short video about "
            f"'{_norm(description) or _norm(keyword)}', cinematic lighting."
        )
    elif "sticker" in role_l or basename.lower().startswith("sticker_"):
        parts.append(
            f"A flat sticker illustration of '{_norm(description) or basename}', "
            "centered on transparent background equivalent, bold silhouette, soft inner shadow."
        )
    elif "illustration" in role_l or "hero" in role_l or "motif" in role_l:
        parts.append(
            f"A hero illustration for the iOS app '{app}' depicting "
            f"'{_norm(description) or _norm(keyword)}'. Editorial illustration style, ample negative space."
        )
    elif "texture" in role_l or "grain" in role_l or "texture" in basename.lower():
        parts.append(
            f"A seamless tileable texture, very subtle, low contrast, intended as a global skin "
            f"for the iOS app '{app}'. No focal subject."
        )
    elif "gradient" in role_l or "gradient" in basename.lower():
        parts.append(
            f"A soft vertical gradient backdrop using the app palette, optionally with subtle grain. "
            "No subject, no text."
        )
    elif "chart" in role_l or "reference" in role_l:
        parts.append(
            f"A reference chart graphic for the iOS app '{app}' showing "
            f"'{_norm(description) or _norm(keyword)}', clean infographic style on light surface."
        )
    elif "template" in role_l or "template" in basename.lower():
        parts.append(
            f"A square poster-style template thumbnail for '{_norm(description) or basename}', "
            "centered subject, minimal composition."
        )
    elif "export" in role_l or "export" in basename.lower():
        parts.append(
            f"A card / export sheet background for the iOS app '{app}', portrait composition, "
            "ample margin for overlaid text. No baked-in copy."
        )
    elif "decorative" in role_l or "divider" in role_l or "shape" in role_l:
        parts.append(
            f"A decorative shape / divider graphic matching the app's visual identity. "
            "Used as accent only."
        )
    else:
        parts.append(
            f"An image asset for the iOS app '{app}', slot role '{role}' "
            f"({_norm(description) or _norm(keyword)})."
        )

    if palette_hex:
        parts.append(
            "Dominant palette anchors: " + ", ".join(palette_hex) + "."
        )
    parts.append(
        "No baked-in text, watermark, logo, or trademark. No real-person likeness. Safe for App Store review."
    )
    return " ".join(parts)


def source_hints_for(role: str, basename: str, keyword: str) -> list[str]:
    role_l = (role or "").lower()
    name_l = (basename or "").lower()
    hints: list[str] = []
    if "splash" in role_l or "background" in role_l or "splash" in name_l or "background" in name_l:
        hints.append("Midjourney v6 — vertical 1242×2688")
        if keyword:
            hints.append(f"Unsplash search: \"{_norm(keyword)}\"")
    elif "feed" in role_l or "content_image" in name_l or role_l in {"content_image", "feed_card"}:
        hints.append("Unsplash / Pexels editorial photo")
        if keyword:
            hints.append(f"keyword: \"{_norm(keyword)}\"")
    elif "content_thumbnail" in name_l or role_l == "content_thumbnail":
        hints.append("Stock-video first-frame export / Midjourney 9:16")
        if keyword:
            hints.append(f"keyword: \"{_norm(keyword)}\"")
    elif "sticker" in role_l or name_l.startswith("sticker_"):
        hints.append("Midjourney --style raw, sticker on flat background")
    elif "illustration" in role_l or "hero" in role_l or "motif" in role_l:
        hints.append("Midjourney editorial illustration")
    elif "texture" in role_l or "grain" in role_l or "gradient" in role_l:
        hints.append("Procedural noise / gradient — small file size preferred")
    elif "chart" in role_l or "reference" in role_l:
        hints.append("Design tool export (Figma/Illustrator)")
    else:
        hints.append("Midjourney / DALL-E / Stable Diffusion")
    return hints
