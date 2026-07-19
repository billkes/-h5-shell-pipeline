"""Generate static Tab1 (Canvas / Hub) preview HTML from MASTER + theme + layout contract."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

from batch.h5_site_paths import app_slug_from_name
from batch.h5_theme_tokens import (
    THEME_END,
    THEME_START,
    build_theme_block,
    resolve_prefix,
)
from batch.preview_tabs import (
    CANONICAL_NAME,
    preview_canonical_path,
    preview_dir,
    preview_html_path,
    sync_preview_colors_after_tabs,
)
from batch.uupm_design_system import (
    find_design_system_master,
    load_master_design_tokens,
    parse_master_palette,
    parse_master_typography,
)

PREVIEW_IMPL_LOCK = "<!-- PREVIEW-IMPL:pipeline -->"
TAB1_PREVIEW_SUFFIX = "-tab1-preview.html"


def tab1_preview_path(project: Path, app_name: str = "") -> Path:
    slug = _app_slug(project, app_name)
    return preview_dir(project) / f"{slug}{TAB1_PREVIEW_SUFFIX}"


def _app_slug(project: Path, app_name: str = "") -> str:
    if app_name.strip():
        return app_slug_from_name(app_name)
    reg_path = project / "本包登记信息.json"
    if reg_path.is_file():
        try:
            data = json.loads(reg_path.read_text(encoding="utf-8"))
            name = str(data.get("appName") or data.get("name") or "").strip()
            if name:
                return app_slug_from_name(name)
        except json.JSONDecodeError:
            pass
    return app_slug_from_name(project.name)


def _read_app_name(project: Path) -> str:
    reg_path = project / "本包登记信息.json"
    if reg_path.is_file():
        try:
            data = json.loads(reg_path.read_text(encoding="utf-8"))
            return str(data.get("appName") or data.get("name") or project.name)
        except json.JSONDecodeError:
            pass
    return project.name


def _extract_block(css: str, start: str, end: str) -> str:
    if start not in css or end not in css:
        return ""
    return css.split(start, 1)[1].split(end, 1)[0].strip()


def _theme_for_mode(project: Path, prefix: str, *, dark: bool) -> str:
    """Legacy helper — prefer _theme_scoped_vars."""
    sel = ".preview-dark" if dark else ".preview-light"
    return _theme_scoped_vars(project, prefix, dark=dark, selector=sel)


def _theme_scoped_vars(project: Path, prefix: str, *, dark: bool, selector: str) -> str:
    block = build_theme_block(prefix, project=project)
    if dark:
        m = re.search(r"@media\s*\(\s*prefers-color-scheme:\s*dark\s*\)\s*\{", block, re.I)
        chunk = block[m.end() :] if m else block
        m2 = re.search(r":root\s*\{([\s\S]*?)\}", chunk)
    else:
        chunk = block.split("@media")[0]
        m2 = re.search(r":root\s*\{([\s\S]*?)\}", chunk)
    if not m2:
        return ""
    body = m2.group(1).strip()
    return f"{selector} {{\n{body}\n}}"


def _collect_preview_css(project: Path, prefix: str) -> str:
    """Ambient, layout, habit grid — exclude THEME (scoped per device)."""
    path = project / "h5" / "src" / "styles" / "global.css"
    kit_path = project / "h5" / "src" / "styles" / "kit.css"
    if not path.is_file():
        return ""
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(
        re.escape(THEME_START) + r"[\s\S]*?" + re.escape(THEME_END),
        "",
        raw,
    )
    layout = _extract_block(
        path.read_text(encoding="utf-8", errors="ignore"),
        "/* LAYOUT:pipeline",
        "/* LAYOUT:end */",
    )
    # Ambient + components between THEME:end and LAYOUT:pipeline
    tail = path.read_text(encoding="utf-8", errors="ignore")
    if THEME_END in tail and "/* LAYOUT:pipeline" in tail:
        mid = tail.split(THEME_END, 1)[1].split("/* LAYOUT:pipeline", 1)[0]
    else:
        mid = ""
    parts = [mid.strip(), layout.strip()]
    if kit_path.is_file():
        kit = kit_path.read_text(encoding="utf-8", errors="ignore")
        kit = re.sub(r"/\* KIT:pipeline[\s\S]*?\*/", "", kit, count=1)
        parts.append(kit.strip())
    # Rewrite ambient class prefix if needed (already c-{prefix} in project)
    return "\n\n".join(p for p in parts if p)


def _google_fonts_import(project: Path) -> str:
    master = find_design_system_master(project)
    if not master or not master.is_file():
        return ""
    typo = parse_master_typography(master.read_text(encoding="utf-8", errors="ignore"))
    url = str(typo.get("google_fonts_url") or "").strip()
    if not url:
        return ""
    if not url.startswith("http"):
        url = f"https://{url.lstrip('/')}"
    return f"@import url('{url}');"


def _habit_tiles_html(prefix: str, *, variant: str) -> str:
    p = prefix.lower()
    if variant == "empty":
        return f"""
<div class="c-{p}-empty">
  <p>Add your first habit to start the month</p>
  <button type="button" class="c-{p}-btn">Add first habit</button>
</div>
"""
    return f"""
<div class="c-{p}-workspace-grid u-motion-rise">
  <article class="c-{p}-habit-tile c-{p}-habit-tile--done">
    <h3 class="c-{p}-habit-tile__title">Morning run</h3>
    <p class="c-{p}-habit-tile__streak">12 day streak</p>
  </article>
  <article class="c-{p}-habit-tile">
    <h3 class="c-{p}-habit-tile__title">Read 20 min</h3>
    <p class="c-{p}-habit-tile__streak">Tap to stamp today</p>
  </article>
  <article class="c-{p}-habit-tile c-{p}-habit-tile--done">
    <h3 class="c-{p}-habit-tile__title">Meditate</h3>
    <p class="c-{p}-habit-tile__streak">5 day streak</p>
  </article>
  <article class="c-{p}-habit-tile">
    <h3 class="c-{p}-habit-tile__title">Journal</h3>
    <p class="c-{p}-habit-tile__streak">Tap to stamp today</p>
  </article>
</div>
"""


def _phone_shell(prefix: str, *, mode: str, variant: str, greeting: str) -> str:
    p = prefix.lower()
    scene = "hub"
    tiles = _habit_tiles_html(prefix, variant=variant)
    banner = ""
    if variant == "filled":
        banner = f"""
<div class="c-{p}-banner">
  <strong>Close July with a review</strong>
  <div style="margin-top:8px;display:flex;gap:8px">
    <button type="button" class="c-{p}-btn">Open review</button>
    <button type="button" class="c-{p}-btn c-{p}-btn--secondary">Dismiss</button>
  </div>
</div>
"""
    return f"""
<div class="preview-device preview-{mode}" data-cjsyi-scene="{scene}">
  <div class="u-{p}-ambient" aria-hidden="true">
    <div class="u-{p}-ambient__base"></div>
    <div class="u-{p}-ambient__mesh"></div>
    <div class="u-{p}-ambient__grid"></div>
    <div class="u-{p}-ambient__lane"></div>
    <div class="u-{p}-ambient__spotlight"></div>
  </div>
  <div class="h5-app-shell">
    <header class="c-{p}-topbar">
      <span class="c-{p}-topbar__title">Canvas</span>
    </header>
    <main class="page-shell">
      <p class="preview-greeting">{escape(greeting)}</p>
      {banner}
      {tiles}
    </main>
    <nav class="c-{p}-tabbar">
      <a class="c-{p}-tabbar__item c-{p}-tabbar__item--active" href="#"><span>◆</span>Canvas</a>
      <a class="c-{p}-tabbar__item" href="#"><span>◇</span>Pulse</a>
      <a class="c-{p}-tabbar__item" href="#"><span>◇</span>Year</a>
      <a class="c-{p}-tabbar__item" href="#"><span>◇</span>Me</a>
    </nav>
  </div>
</div>
"""


def _static_font_vars(project: Path, prefix: str) -> str:
    path = project / "h5" / "src" / "styles" / "global.css"
    if not path.is_file():
        return ""
    css = path.read_text(encoding="utf-8", errors="ignore")
    if THEME_END not in css:
        return ""
    tail = css.split(THEME_END, 1)[1]
    m = re.search(r":root\s*\{([^}]*--" + re.escape(prefix) + r"-font[^}]*)\}", tail, re.I)
    return m.group(1).strip() if m else ""


def build_tab1_preview_html(project: Path, app_name: str = "") -> str:
    project = project.expanduser().resolve()
    app = app_name.strip() or _read_app_name(project)
    prefix = resolve_prefix(project)
    master_tokens = load_master_design_tokens(project)
    palette = master_tokens.get("palette") or {}
    if not palette:
        master = find_design_system_master(project)
        if master and master.is_file():
            palette = parse_master_palette(master.read_text(encoding="utf-8", errors="ignore"))

    shared_css = _collect_preview_css(project, prefix)
    font_import = _google_fonts_import(project)
    light_vars = _theme_scoped_vars(project, prefix, dark=False, selector=".preview-light")
    dark_vars = _theme_scoped_vars(project, prefix, dark=True, selector=".preview-dark")
    font_vars = _static_font_vars(project, prefix)
    if font_vars:
        for idx, block in enumerate((light_vars, dark_vars)):
            if block.endswith("}"):
                block = block[:-1] + f"\n{font_vars}\n}}"
            if idx == 0:
                light_vars = block
            else:
                dark_vars = block

    greeting = "Good evening — stamp tonight's habits"
    accent = palette.get("accent", "")
    primary = palette.get("primary", "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(app)} — Tab1 Canvas Preview</title>
  {PREVIEW_IMPL_LOCK}
  <style>
    {font_import}
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: system-ui, sans-serif;
      background: #0b1220;
      color: #e2e8f0;
    }}
    .page-header {{
      padding: 20px 24px 8px;
      max-width: 920px;
      margin: 0 auto;
    }}
    .page-header h1 {{ margin: 0 0 6px; font-size: 20px; }}
    .page-header p {{ margin: 0; color: #94a3b8; font-size: 14px; line-height: 1.5; }}
    .palette {{ display: flex; gap: 8px; margin-top: 10px; }}
    .palette span {{
      width: 28px; height: 28px; border-radius: 6px;
      border: 1px solid rgba(255,255,255,0.12);
    }}
    .preview-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 24px;
      max-width: 920px;
      margin: 0 auto;
      padding: 16px 24px 40px;
    }}
    .preview-col h2 {{
      margin: 0 0 12px;
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #94a3b8;
      text-align: center;
    }}
    .preview-device {{
      position: relative;
      width: 375px;
      max-width: 100%;
      height: 812px;
      margin: 0 auto;
      border-radius: 28px;
      overflow: hidden;
      box-shadow: 0 24px 60px rgba(0,0,0,0.45);
      border: 1px solid rgba(255,255,255,0.08);
      background: var(--{prefix}-background, #f8fafc);
      color: var(--{prefix}-foreground, #0f172a);
    }}
    {light_vars}
    {dark_vars}
    .preview-greeting {{
      font-family: var(--{prefix}-font-display, serif);
      font-size: 20px;
      font-weight: 700;
      margin: 0 0 12px;
    }}
    {shared_css}
  </style>
</head>
<body>
  <header class="page-header">
    <h1>{escape(app)} · Tab1 Canvas</h1>
    <p>Hub Home Canon — workspace stamp grid, ambient journey lane, AppBar + 4-tab bar. Primary {escape(primary)} · Accent {escape(accent)}.</p>
    <div class="palette">
      <span style="background:{escape(primary or '#1E3A5F')}" title="primary"></span>
      <span style="background:{escape(accent or '#A16207')}" title="accent"></span>
      <span style="background:{escape(palette.get('background', '#F8FAFC'))}" title="background"></span>
    </div>
  </header>
  <div class="preview-grid">
    <section class="preview-col">
      <h2>Light · Filled</h2>
      {_phone_shell(prefix, mode='light', variant='filled', greeting=greeting)}
    </section>
    <section class="preview-col">
      <h2>Dark · Filled</h2>
      {_phone_shell(prefix, mode='dark', variant='filled', greeting=greeting)}
    </section>
    <section class="preview-col">
      <h2>Light · Empty</h2>
      {_phone_shell(prefix, mode='light', variant='empty', greeting='Good morning')}
    </section>
  </div>
</body>
</html>
"""


def _build_preview_canonical(project: Path, app_name: str) -> str:
    master_tokens = load_master_design_tokens(project)
    palette = master_tokens.get("palette") or {}
    typo = master_tokens.get("typography") or {}
    heading = typo.get("heading", "Outfit")
    light_bg = palette.get("background", "#F8FAFC")
    light_primary = palette.get("primary", "#1E3A5F")
    light_accent = palette.get("accent", "#A16207")
    light_fg = palette.get("foreground", "#0F172A")
    return f"""# Preview Canonical — {app_name}

## Tabs
| Label | Route | Role |
|-------|-------|------|
| Canvas | #/ | hub / Tab1 workspace |
| Pulse | #/pulse | list |
| Year | #/year | list |
| Me | #/me | settings |

## Colors
### Light mode
| background | `{light_bg}` |
| primary | `{light_primary}` |
| accent | `{light_accent}` |
| foreground | `{light_fg}` |
| muted | `{palette.get('muted', '#E9EEF5')}` |
| border | `{palette.get('border', '#CBD5E1')}` |

### Dark mode
| background | `#020617` |
| primary | `#0F172A` |
| accent | `#16A34A` |
| foreground | `#F8FAFC` |
| muted | `#1A1E2F` |
| border | `#334155` |

## Typography
{heading}

## Key Components
home-hero
gallery-hub
kpi-strip
segment
cta-game

## Allowed MASTER Deviations
Tab1 preview generated by pipeline from MASTER + Hub Home Canon.
"""


def write_tab1_preview(project: Path, app_name: str = "", *, write: bool = True) -> Path:
    """Write ``_preview/{slug}-tab1-preview.html`` (skill.design MASTER only)."""
    from batch.preview_skill_tab1 import write_skill_tab1_preview

    return write_skill_tab1_preview(project, app_name, write=write)


def write_tabs_preview_bundle(project: Path, app_name: str = "", *, write: bool = True) -> list[Path]:
    """Write Tab1 preview + tabs-preview alias + preview-canonical.md."""
    project = project.expanduser().resolve()
    app = app_name.strip() or _read_app_name(project)
    written: list[Path] = []

    tab1 = write_tab1_preview(project, app, write=write)
    written.append(tab1)

    slug = _app_slug(project, app)
    tabs_html = preview_html_path(project, app)
    canonical = preview_canonical_path(project)

    if write:
        preview_dir(project).mkdir(parents=True, exist_ok=True)
        tabs_html.write_text(tab1.read_text(encoding="utf-8"), encoding="utf-8")
        canonical.write_text(_build_preview_canonical(project, app), encoding="utf-8")
        try:
            sync_preview_colors_after_tabs(project, write=True)
        except OSError:
            pass
    written.extend([tabs_html, canonical])
    return written
