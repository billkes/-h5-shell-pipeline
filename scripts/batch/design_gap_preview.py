"""Side-by-side HTML: skill MASTER design vs pipeline H5 theme/kit (visual gap audit)."""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from typing import Any

from batch.h5_theme_tokens import THEME_END, THEME_START, build_theme_block, resolve_prefix
from batch.preview_tabs import preview_dir
from batch.uupm_design_system import (
    find_design_system_master,
    load_master_design_tokens,
    parse_master_palette,
    parse_master_typography,
)

GAP_PREVIEW_NAME = "design-gap-compare.html"


def design_gap_preview_path(project: Path) -> Path:
    return preview_dir(project) / GAP_PREVIEW_NAME


def _read_register_app(project: Path) -> str:
    path = project / "本包登记信息.json"
    if not path.is_file():
        return project.name
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return project.name
    return str(data.get("appName") or data.get("name") or project.name)


def _parse_theme_vars(css: str, prefix: str) -> dict[str, str]:
    if THEME_START in css and THEME_END in css:
        css = css.split(THEME_START, 1)[1].split(THEME_END, 1)[0]
    light = css.split("@media")[0] if "@media" in css else css
    out: dict[str, str] = {}
    for m in re.finditer(rf"(--{re.escape(prefix)}-[\w-]+)\s*:\s*([^;]+);", light):
        out[m.group(1)] = m.group(2).strip()
    return out


def _master_canvas_css(palette: dict[str, str], typo: dict[str, str]) -> str:
    primary = palette.get("primary", "#1E3A5F")
    accent = palette.get("accent", "#A16207")
    bg = palette.get("background", "#F8FAFC")
    fg = palette.get("foreground", "#0F172A")
    muted = palette.get("muted", "#E9EEF5")
    border = palette.get("border", "#CBD5E1")
    heading = typo.get("heading", "Outfit")
    body = typo.get("body", heading)
    font_url = typo.get("google_fonts_url", "")
    import_line = f"@import url('{font_url}');" if font_url else ""
    return f"""
{import_line}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: '{body}', system-ui, sans-serif;
  background: #eef1f5;
  color: {fg};
}}
.phone {{
  width: 360px;
  min-height: 640px;
  margin: 0 auto;
  background: {bg};
  border-radius: 24px;
  box-shadow: 0 20px 50px rgba(15,23,42,0.15);
  overflow: hidden;
  padding: 20px 16px 24px;
}}
.label {{
  text-align: center;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748B;
  margin-bottom: 12px;
}}
.greeting {{
  font-family: '{heading}', sans-serif;
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 16px;
  color: {fg};
}}
.empty {{
  text-align: center;
  padding: 48px 16px;
  border-radius: 12px;
  background: {bg};
  box-shadow: 0 4px 6px rgba(0,0,0,0.08);
}}
.empty p {{ margin: 0 0 16px; color: {fg}; opacity: 0.85; }}
.btn-primary {{
  background: {accent};
  color: #fff;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  font-family: '{body}', sans-serif;
  cursor: pointer;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}}
.panel {{
  margin-top: 16px;
  padding: 16px;
  background: #fff;
  border: 1px solid {border};
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.06);
}}
.input {{
  width: 100%;
  padding: 12px 16px;
  border: 1px solid {border};
  border-radius: 8px;
  font-size: 16px;
  margin-bottom: 12px;
}}
.chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }}
.chip {{
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid {border};
  background: {muted};
  font-size: 12px;
  font-weight: 600;
}}
.chip.active {{ background: {primary}; color: #fff; border-color: {primary}; }}
.palette-row {{ display: flex; gap: 6px; justify-content: center; margin-top: 12px; }}
.swatch {{ width: 28px; height: 28px; border-radius: 6px; border: 1px solid rgba(0,0,0,0.08); }}
"""


def _pipeline_canvas_css(vars_map: dict[str, str], prefix: str, kit_css: str) -> str:
    def v(name: str, fallback: str) -> str:
        return vars_map.get(f"--{prefix}-{name}", fallback)

    return f"""
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: {v('font-body', 'system-ui') if f'--{prefix}-font-body' in vars_map else 'Source Serif 4, system-ui'};
  background: #eef1f5;
  color: {v('foreground', '#0F172A')};
}}
.phone {{
  width: 360px;
  min-height: 640px;
  margin: 0 auto;
  background: {v('background', '#F5F5F7')};
  border-radius: 24px;
  box-shadow: 0 20px 50px rgba(15,23,42,0.15);
  overflow: hidden;
  padding: 20px 16px 24px;
}}
.label {{
  text-align: center;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748B;
  margin-bottom: 12px;
}}
.greeting {{
  font-family: {v('font-display', 'inherit') if f'--{prefix}-font-display' in vars_map else 'inherit'};
  font-size: 22px;
  margin: 0 0 16px;
}}
/* Inline kit subset from pipeline */
{kit_css}
.pipeline-empty {{
  text-align: center;
  padding: 32px 16px;
}}
.pipeline-panel {{
  margin-top: 16px;
  padding: 16px;
}}
.palette-row {{ display: flex; gap: 6px; justify-content: center; margin-top: 12px; }}
.swatch {{ width: 28px; height: 28px; border-radius: 6px; border: 1px solid rgba(0,0,0,0.08); }}
"""


def _canvas_markup_pipeline(prefix: str) -> str:
    p = prefix.lower()
    return f"""
<div class="phone">
  <p class="greeting">Good morning</p>
  <div class="c-{p}-empty pipeline-empty">
    <p>Add your first habit to start the month</p>
    <button type="button" class="c-{p}-btn">Add first habit</button>
  </div>
  <div class="c-{p}-panel pipeline-panel">
    <label>Habit title</label>
    <input class="c-{p}-input" type="text" value="Morning run" />
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0">
      <button type="button" class="c-{p}-chip c-{p}-chip--active">Focus</button>
      <button type="button" class="c-{p}-chip">Health</button>
    </div>
    <button type="button" class="c-{p}-btn">Save habit</button>
  </div>
</div>
"""


def _canvas_markup_master() -> str:
    return """
<div class="phone">
  <p class="greeting">Good morning</p>
  <div class="empty">
    <p>Add your first habit to start the month</p>
    <button type="button" class="btn-primary">Add first habit</button>
  </div>
  <div class="panel">
    <label>Habit title</label>
    <input class="input" type="text" value="Morning run" />
    <div class="chips">
      <span class="chip active">Focus</span>
      <span class="chip">Health</span>
    </div>
    <button type="button" class="btn-primary">Save habit</button>
  </div>
</div>
"""


def _swatch_row(colors: dict[str, str], keys: tuple[str, ...]) -> str:
    cells = []
    for key in keys:
        hex_val = colors.get(key, "#ccc")
        cells.append(f'<div class="swatch" title="{escape(key)} {escape(hex_val)}" style="background:{escape(hex_val)}"></div>')
    return f'<div class="palette-row">{"".join(cells)}</div>'


def analyze_design_gap(project: Path) -> dict[str, Any]:
    """Return structured gap report: MASTER vs pipeline theme sources."""
    project = project.expanduser().resolve()
    prefix = resolve_prefix(project)
    master_tokens = load_master_design_tokens(project)
    master_palette = master_tokens.get("palette") or {}
    master_typo = master_tokens.get("typography") or {}

    candidate_path = project / "skill-adapt" / "selected-candidate.json"
    candidate_colors: dict[str, str] = {}
    if candidate_path.is_file():
        try:
            data = json.loads(candidate_path.read_text(encoding="utf-8"))
            candidate_colors = (data.get("designSystem") or {}).get("colors") or {}
        except json.JSONDecodeError:
            pass

    css_path = project / "h5" / "src" / "styles" / "global.css"
    pipeline_vars: dict[str, str] = {}
    if css_path.is_file():
        pipeline_vars = _parse_theme_vars(css_path.read_text(encoding="utf-8", errors="ignore"), prefix)

    expected_block = build_theme_block(prefix, project=project)
    expected_vars = _parse_theme_vars(expected_block, prefix)

    drift: list[str] = []
    for key in ("primary", "accent", "background", "foreground"):
        master_val = master_palette.get(key, "")
        pipe_val = pipeline_vars.get(f"--{prefix}-{key}", "")
        cand_val = str(candidate_colors.get(key) or "")
        if master_val and pipe_val and master_val.upper() != pipe_val.upper():
            drift.append(f"{key}: MASTER {master_val} ≠ pipeline {pipe_val} (candidate {cand_val})")

    font_defined = bool(re.search(rf"^\s*--{re.escape(prefix)}-font-display\s*:", css_path.read_text(encoding="utf-8"), re.M)) if css_path.is_file() else False

    return {
        "prefix": prefix,
        "master_palette": master_palette,
        "master_typography": master_typo,
        "candidate_colors": candidate_colors,
        "pipeline_vars": pipeline_vars,
        "expected_vars": expected_vars,
        "drift": drift,
        "font_vars_defined": font_defined,
        "root_cause": (
            "theme sync 读 selected-candidate（dark-first）而非 MASTER light palette"
            if drift and candidate_colors.get("accent") != master_palette.get("accent")
            else ("font CSS vars 未注入 global.css" if not font_defined else "")
        ),
    }


def build_design_gap_html(project: Path) -> str:
    project = project.expanduser().resolve()
    app = _read_register_app(project)
    report = analyze_design_gap(project)
    prefix = str(report["prefix"])
    master_palette = report["master_palette"] or {}
    master_typo = report["master_typography"] or {}

    master = find_design_system_master(project)
    if master and master.is_file() and not master_palette:
        master_palette = parse_master_palette(master.read_text(encoding="utf-8", errors="ignore"))
        master_typo = parse_master_typography(master.read_text(encoding="utf-8", errors="ignore"))

    kit_path = project / "h5" / "src" / "styles" / "kit.css"
    kit_css = kit_path.read_text(encoding="utf-8", errors="ignore") if kit_path.is_file() else ""

    css_path = project / "h5" / "src" / "styles" / "global.css"
    pipeline_vars = report["pipeline_vars"] or {}
    if css_path.is_file() and not pipeline_vars:
        pipeline_vars = _parse_theme_vars(css_path.read_text(encoding="utf-8", errors="ignore"), prefix)

    drift_lines = "".join(f"<li>{escape(d)}</li>" for d in report.get("drift") or [])
    root_cause = escape(str(report.get("root_cause") or "见下方色板对比"))
    swatch_keys = ("primary", "accent", "background", "foreground", "muted")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(app)} — 设计差距对比</title>
  <style>
    body {{ margin: 0; font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; }}
    header {{ padding: 24px 20px 12px; max-width: 960px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px; font-size: 20px; }}
    .sub {{ color: #94a3b8; font-size: 14px; line-height: 1.5; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; max-width: 960px; margin: 0 auto; padding: 12px 20px 32px; }}
    @media (max-width: 820px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    .col {{ background: #1e293b; border-radius: 16px; padding: 16px; }}
    .col h2 {{ margin: 0 0 4px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.06em; color: #cbd5e1; }}
    .col p.desc {{ margin: 0 0 12px; font-size: 12px; color: #94a3b8; }}
    iframe {{ width: 100%; height: 720px; border: 0; border-radius: 12px; background: #fff; }}
    .report {{ max-width: 960px; margin: 0 auto 24px; padding: 0 20px; }}
    .report ul {{ margin: 8px 0; padding-left: 20px; color: #fca5a5; font-size: 13px; }}
    .report .ok {{ color: #86efac; }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(app)} — 技能设计 vs 流水线落地</h1>
    <p class="sub">左：MASTER.md 组件规范 + 色板 · 右：当前 global.css THEME + kit.css（Canvas Tab 结构）</p>
  </header>
  <div class="report">
    <p><strong>根因：</strong>{root_cause}</p>
    {"<ul>" + drift_lines + "</ul>" if drift_lines else '<p class="ok">色板 token 与 MASTER 一致（或 MASTER 缺失）</p>'}
  </div>
  <div class="grid">
    <div class="col">
      <h2>Skill · MASTER</h2>
      <p class="desc">design-system/*/MASTER.md — Primary {escape(master_palette.get('primary','?'))} · Accent {escape(master_palette.get('accent','?'))} · {escape(master_typo.get('heading','?'))}</p>
      {_swatch_row(master_palette, swatch_keys)}
      <iframe title="master" srcdoc="{escape(_master_canvas_css(master_palette, master_typo) + _canvas_markup_master(), quote=True)}"></iframe>
    </div>
    <div class="col">
      <h2>Pipeline · H5</h2>
      <p class="desc">h5/src/styles/global.css + kit.css — Primary {escape(pipeline_vars.get(f'--{prefix}-primary','?'))} · Accent {escape(pipeline_vars.get(f'--{prefix}-accent','?'))}</p>
      {_swatch_row({k: pipeline_vars.get(f'--{prefix}-{k}', '') for k in swatch_keys}, swatch_keys)}
      <iframe title="pipeline" srcdoc="{escape(_pipeline_canvas_css(pipeline_vars, prefix, kit_css) + _canvas_markup_pipeline(prefix), quote=True)}"></iframe>
    </div>
  </div>
</body>
</html>
"""


def write_design_gap_preview(project: Path, *, write: bool = True) -> Path:
    """Write ``_preview/design-gap-compare.html`` for browser gap audit."""
    project = project.expanduser().resolve()
    out = design_gap_preview_path(project)
    html = build_design_gap_html(project)
    if write:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
    return out
