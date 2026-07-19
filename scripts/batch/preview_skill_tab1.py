"""Tab1 preview rendered purely from skill.design MASTER (no pipeline H5 CSS)."""

from __future__ import annotations

from html import escape
from pathlib import Path

from batch.h5_site_paths import app_slug_from_name
from batch.preview_tabs import preview_dir
from batch.uupm_design_system import (
    find_design_system_master,
    parse_master_palette,
    parse_master_shadows,
    parse_master_spacing,
    parse_master_typography,
)

PREVIEW_IMPL_SKILL = "<!-- PREVIEW-IMPL:skill-factory -->"
TAB1_SKILL_SUFFIX = "-tab1-preview.html"


def skill_tab1_preview_path(project: Path, app_name: str = "") -> Path:
    slug = app_slug_from_name(app_name) if app_name.strip() else _slug_from_register(project)
    return preview_dir(project) / f"{slug}{TAB1_SKILL_SUFFIX}"


def _slug_from_register(project: Path) -> str:
    import json

    reg = project / "本包登记信息.json"
    if reg.is_file():
        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
            name = str(data.get("appName") or data.get("name") or "").strip()
            if name:
                return app_slug_from_name(name)
        except json.JSONDecodeError:
            pass
    return app_slug_from_name(project.name)


def _read_app_name(project: Path) -> str:
    import json

    reg = project / "本包登记信息.json"
    if reg.is_file():
        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
            return str(data.get("appName") or data.get("name") or project.name)
        except json.JSONDecodeError:
            pass
    return project.name


def _tab_icon(name: str, active: bool = False) -> str:
    stroke = "currentColor"
    fill = "currentColor" if active and name == "canvas" else "none"
    icons = {
        "canvas": f'<svg width="20" height="20" viewBox="0 0 24 24" fill="{fill}" stroke="{stroke}" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
        "pulse": f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{stroke}" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
        "year": f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{stroke}" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
        "me": f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{stroke}" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    }
    return icons.get(name, "")


def build_skill_factory_tab1_html(project: Path, app_name: str = "") -> str:
    """Build Tab1 Canvas preview from design-system/*/MASTER.md only."""
    project = project.expanduser().resolve()
    app = app_name.strip() or _read_app_name(project)
    master = find_design_system_master(project, app)
    if not master or not master.is_file():
        raise FileNotFoundError(f"skill preview 缺少 MASTER.md: {project}/design-system/*/MASTER.md")

    text = master.read_text(encoding="utf-8", errors="ignore")
    palette = parse_master_palette(text)
    typo = parse_master_typography(text)
    shadows = parse_master_shadows(text)
    spacing = parse_master_spacing(text)

    primary = palette.get("primary", "#1E3A5F")
    accent = palette.get("accent", "#A16207")
    bg = palette.get("background", "#F8FAFC")
    fg = palette.get("foreground", "#0F172A")
    muted = palette.get("muted", "#E9EEF5")
    border = palette.get("border", "#CBD5E1")
    secondary = palette.get("secondary", "#2563EB")
    on_primary = palette.get("on_primary", "#FFFFFF")

    heading = typo.get("heading", "Outfit")
    body = typo.get("body", heading)
    font_url = typo.get(
        "google_fonts_url",
        "https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;900&display=swap",
    )
    if not font_url.startswith("http"):
        font_url = f"https://{font_url.lstrip('/')}"

    sh_md = shadows.get("--shadow-md", shadows.get("shadow_md", "0 4px 6px rgba(0,0,0,0.1)"))
    sh_lg = shadows.get("--shadow-lg", shadows.get("shadow_lg", "0 10px 15px rgba(0,0,0,0.1)"))
    sp_md = spacing.get("md", "16px")
    sp_lg = spacing.get("lg", "24px")
    sp_sm = spacing.get("sm", "8px")

    habits = (
        ("Morning run", "12 day streak", True),
        ("Read 20 min", "Tap to stamp today", False),
        ("Meditate", "5 day streak", True),
        ("Journal", "Tap to stamp today", False),
    )
    tiles = []
    for title, sub, done in habits:
        done_cls = " habit-card--done" if done else ""
        tiles.append(
            f'<article class="habit-card{done_cls}">'
            f'<h3>{escape(title)}</h3>'
            f'<p>{escape(sub)}</p></article>'
        )
    tiles_html = "\n".join(tiles)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(app)} — Tab1 Canvas (skill.design)</title>
  {PREVIEW_IMPL_SKILL}
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="{escape(font_url)}" rel="stylesheet" />
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      min-height: 100%;
      background: #eef2f6;
      font-family: '{body}', system-ui, sans-serif;
      color: {fg};
      -webkit-font-smoothing: antialiased;
    }}
    .stage {{
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px 16px 32px;
      gap: 16px;
    }}
    .meta {{
      text-align: center;
      max-width: 420px;
    }}
    .meta h1 {{
      margin: 0 0 4px;
      font-size: 15px;
      font-weight: 600;
      color: #64748b;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .meta p {{
      margin: 0;
      font-size: 13px;
      color: #94a3b8;
      line-height: 1.45;
    }}
    .phone {{
      width: 375px;
      height: 812px;
      max-width: 100%;
      border-radius: 32px;
      overflow: hidden;
      position: relative;
      background: {bg};
      box-shadow: 0 32px 64px rgba(15, 23, 42, 0.18), 0 0 0 1px rgba(15, 23, 42, 0.06);
    }}
    .ambient {{
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(circle at 18% 12%, color-mix(in srgb, {secondary} 14%, transparent), transparent 52%),
        radial-gradient(circle at 82% 88%, color-mix(in srgb, {accent} 12%, transparent), transparent 48%),
        {bg};
    }}
    .shell {{
      position: relative;
      z-index: 1;
      display: flex;
      flex-direction: column;
      height: 100%;
    }}
    .appbar {{
      flex-shrink: 0;
      height: 52px;
      padding: 0 {sp_md};
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.92);
      border-bottom: 1px solid {border};
      backdrop-filter: blur(8px);
    }}
    .appbar__title {{
      font-family: '{heading}', sans-serif;
      font-size: 17px;
      font-weight: 700;
      color: {primary};
      letter-spacing: -0.01em;
    }}
    .content {{
      flex: 1;
      overflow-y: auto;
      padding: {sp_md};
      padding-bottom: 88px;
    }}
    .greeting {{
      font-family: '{heading}', sans-serif;
      font-size: 22px;
      font-weight: 700;
      line-height: 1.25;
      color: {fg};
      margin: 0 0 {sp_md};
      letter-spacing: -0.02em;
    }}
    .banner {{
      background: #fff;
      border: 1px solid {border};
      border-radius: 12px;
      padding: {sp_md};
      margin-bottom: {sp_md};
      box-shadow: {sh_md};
    }}
    .banner strong {{
      display: block;
      font-family: '{heading}', sans-serif;
      font-size: 15px;
      font-weight: 700;
      color: {fg};
      margin-bottom: {sp_sm};
    }}
    .banner__actions {{
      display: flex;
      gap: {sp_sm};
      flex-wrap: wrap;
    }}
    .btn-primary {{
      background: {accent};
      color: {on_primary};
      border: none;
      padding: 12px 20px;
      border-radius: 8px;
      font-family: '{body}', sans-serif;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 200ms ease;
      min-height: 44px;
    }}
    .btn-primary:hover {{
      opacity: 0.92;
      transform: translateY(-1px);
      box-shadow: {sh_md};
    }}
    .btn-secondary {{
      background: transparent;
      color: {primary};
      border: 2px solid {primary};
      padding: 10px 18px;
      border-radius: 8px;
      font-family: '{body}', sans-serif;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 200ms ease;
      min-height: 44px;
    }}
    .btn-secondary:hover {{
      background: color-mix(in srgb, {primary} 6%, transparent);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: {sp_md};
    }}
    .habit-card {{
      background: #fff;
      border-radius: 12px;
      padding: {sp_md};
      min-height: 128px;
      border: 1px solid {border};
      box-shadow: {sh_md};
      cursor: pointer;
      transition: all 200ms ease;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .habit-card:hover {{
      box-shadow: {sh_lg};
      transform: translateY(-2px);
    }}
    .habit-card h3 {{
      margin: 0 0 {sp_sm};
      font-family: '{heading}', sans-serif;
      font-size: 16px;
      font-weight: 700;
      color: {fg};
      line-height: 1.2;
    }}
    .habit-card p {{
      margin: 0;
      font-size: 13px;
      font-weight: 500;
      color: {accent};
    }}
    .habit-card--done {{
      border-color: color-mix(in srgb, {accent} 45%, {border});
      background: color-mix(in srgb, {muted} 55%, #fff);
    }}
    .tabbar {{
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      height: 72px;
      padding: 8px 12px 20px;
      display: flex;
      justify-content: space-around;
      align-items: flex-start;
      background: rgba(255, 255, 255, 0.96);
      border-top: 1px solid {border};
      backdrop-filter: blur(10px);
    }}
    .tab {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      min-width: 56px;
      font-size: 11px;
      font-weight: 600;
      color: #94a3b8;
      text-decoration: none;
      cursor: pointer;
    }}
    .tab--active {{
      color: {primary};
    }}
    @media (prefers-reduced-motion: reduce) {{
      .habit-card, .btn-primary, .btn-secondary {{ transition: none; }}
      .habit-card:hover, .btn-primary:hover {{ transform: none; }}
    }}
  </style>
</head>
<body>
  <div class="stage">
    <div class="meta">
      <h1>{escape(app)} · Tab1 Canvas</h1>
      <p>ui-ux-pro-max skill.design · MASTER only · {escape(primary)} + {escape(accent)} · {escape(heading)}</p>
    </div>
    <div class="phone">
      <div class="ambient" aria-hidden="true"></div>
      <div class="shell">
        <header class="appbar">
          <div class="appbar__title">Canvas</div>
        </header>
        <main class="content">
          <p class="greeting">Good evening — stamp tonight's habits</p>
          <div class="banner">
            <strong>Close July with a review</strong>
            <div class="banner__actions">
              <button type="button" class="btn-primary">Open review</button>
              <button type="button" class="btn-secondary">Dismiss</button>
            </div>
          </div>
          <div class="grid">
            {tiles_html}
          </div>
        </main>
        <nav class="tabbar">
          <a class="tab tab--active" href="#">{_tab_icon("canvas", True)}<span>Canvas</span></a>
          <a class="tab" href="#">{_tab_icon("pulse")}<span>Pulse</span></a>
          <a class="tab" href="#">{_tab_icon("year")}<span>Year</span></a>
          <a class="tab" href="#">{_tab_icon("me")}<span>Me</span></a>
        </nav>
      </div>
    </div>
  </div>
</body>
</html>
"""


def write_skill_tab1_preview(project: Path, app_name: str = "", *, write: bool = True) -> Path:
    """Write ``_preview/{slug}-tab1-preview.html`` from MASTER only."""
    project = project.expanduser().resolve()
    out = skill_tab1_preview_path(project, app_name)
    html = build_skill_factory_tab1_html(project, app_name)
    if write:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
    return out
