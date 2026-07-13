"""Canonical H5 fixed AppBar / TabBar / page inset layout contract (Vite source).

Structural only: safe-area tokens, fixed chrome geometry, `.page-shell` / `.page-stack`
padding. No per-screen visual composition (hero/export/detail) — those belong in
Agent implementation per 视觉蓝图.md.
"""

from __future__ import annotations

import re
from pathlib import Path

from batch.h5_theme_tokens import resolve_prefix

LAYOUT_START = "/* LAYOUT:pipeline — auto-synced; do not hand-edit */"
LAYOUT_END = "/* LAYOUT:end */"

_APPBAR_HEIGHT = "48px"
_TABBAR_HEIGHT = "56px"


def build_layout_block(prefix: str) -> str:
    p = prefix.lower()
    return f"""{LAYOUT_START}
:root {{
  --safe-top: env(safe-area-inset-top, constant(safe-area-inset-top, 0px));
  --safe-bottom: env(safe-area-inset-bottom, constant(safe-area-inset-bottom, 0px));
  --{p}-appbar-height: {_APPBAR_HEIGHT};
  --{p}-tabbar-height: {_TABBAR_HEIGHT};
  --{p}-page-inset-top: calc(var(--{p}-appbar-height) + var(--safe-top));
  --{p}-page-inset-bottom: calc(var(--{p}-tabbar-height) + var(--safe-bottom));
  --{p}-page-content-gap: 12px;
}}

.c-{p}-topbar {{
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 40;
  display: grid;
  grid-template-columns: 44px 1fr 44px;
  align-items: end;
  height: var(--{p}-page-inset-top);
  padding: var(--safe-top) 8px 0;
  box-sizing: border-box;
  background: var(--{p}-sheet);
  border-bottom: 1px solid var(--{p}-border);
}}

.c-{p}-topbar__title {{
  grid-column: 2;
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  line-height: var(--{p}-appbar-height);
  max-height: var(--{p}-appbar-height);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}

.c-{p}-topbar__back {{
  grid-column: 1;
  justify-self: start;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  margin-bottom: 4px;
  padding: 0;
  border: 1px solid color-mix(in srgb, var(--{p}-primary) 24%, var(--{p}-border));
  border-radius: 12px;
  background: linear-gradient(
    145deg,
    color-mix(in srgb, var(--{p}-primary) 12%, var(--{p}-sheet)),
    color-mix(in srgb, var(--{p}-accent) 8%, var(--{p}-muted))
  );
  color: var(--{p}-primary);
  box-shadow:
    0 1px 3px rgba(15, 23, 42, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  transition: transform 0.15s ease, background 0.15s ease, border-color 0.15s ease;
}}

.c-{p}-topbar__back:active {{
  transform: scale(0.94);
  background: color-mix(in srgb, var(--{p}-primary) 20%, var(--{p}-muted));
  border-color: color-mix(in srgb, var(--{p}-primary) 40%, transparent);
}}

.c-{p}-topbar__back-icon {{
  width: 20px;
  height: 20px;
}}

.c-{p}-tabbar {{
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 40;
  display: flex;
  justify-content: space-around;
  align-items: center;
  height: var(--{p}-page-inset-bottom);
  padding: 0 0 var(--safe-bottom);
  box-sizing: border-box;
  background: var(--{p}-sheet);
  border-top: 1px solid var(--{p}-border);
}}

.c-{p}-tabbar__item {{
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 64px;
  min-height: 44px;
  color: var(--{p}-on-muted);
  text-decoration: none;
  font-size: 11px;
}}

.c-{p}-tabbar__item--active {{
  color: var(--{p}-primary);
}}

.page-shell {{
  min-height: 100%;
  overflow-x: hidden;
  max-width: 100%;
  padding: calc(var(--{p}-page-inset-top) + var(--{p}-page-content-gap)) 16px var(--{p}-page-inset-bottom);
  box-sizing: border-box;
}}

.page-full {{
  min-height: 100vh;
  padding: calc(16px + var(--safe-top)) 16px calc(16px + var(--safe-bottom));
  box-sizing: border-box;
}}

.page-stack {{
  min-height: 100vh;
  padding: calc(var(--{p}-page-inset-top) + var(--{p}-page-content-gap)) 16px calc(16px + var(--safe-bottom));
  box-sizing: border-box;
}}
{LAYOUT_END}"""


def _replace_layout_block(css: str, block: str) -> str:
    if LAYOUT_START in css and LAYOUT_END in css:
        pattern = re.compile(
            re.escape(LAYOUT_START) + r"[\s\S]*?" + re.escape(LAYOUT_END),
            re.MULTILINE,
        )
        css = pattern.sub("", css, count=1).rstrip()
    return css.rstrip() + "\n\n" + block + "\n"


def sync_h5_layout_contract(project: Path, *, write: bool = True) -> Path | None:
    """Inject canonical fixed topbar/tabbar + page-shell at end of global.css."""
    project = project.expanduser().resolve()
    css_path = project / "h5" / "src" / "styles" / "global.css"
    if not css_path.is_file():
        return None
    prefix = resolve_prefix(project)
    block = build_layout_block(prefix)
    raw = css_path.read_text(encoding="utf-8")
    updated = _replace_layout_block(raw, block)
    if write and updated != raw:
        css_path.write_text(updated, encoding="utf-8")
    return css_path


def verify_h5_layout_contract(project: Path) -> list[str]:
    """Fail when safe-area or page inset contract is missing / inconsistent."""
    project = project.expanduser().resolve()
    css_path = project / "h5" / "src" / "styles" / "global.css"
    if not css_path.is_file():
        return []

    css = css_path.read_text(encoding="utf-8", errors="ignore")
    prefix = resolve_prefix(project).lower()
    issues: list[str] = []

    if LAYOUT_START not in css or LAYOUT_END not in css:
        issues.append(
            "Layout Gate: global.css 缺少 LAYOUT:pipeline 块（fixed 顶栏与 page-shell 须由流水线同步）"
        )

    for token in ("--safe-top", "--safe-bottom", f"--{prefix}-page-inset-top", f"--{prefix}-page-inset-bottom"):
        if token not in css:
            issues.append(f"Layout Gate: global.css 缺少 {token}")

    topbar_re = re.compile(
        rf"\.c-{re.escape(prefix)}-topbar\s*\{{[^}}]*position\s*:\s*fixed",
        re.I | re.S,
    )
    if topbar_re.search(css):
        inset_token = f"var(--{prefix}-page-inset-top)"
        layout_slice = css
        if LAYOUT_START in css and LAYOUT_END in css:
            layout_slice = css.split(LAYOUT_START, 1)[1].split(LAYOUT_END, 1)[0]
        page_shell = re.search(r"\.page-shell\s*\{([^}]*)\}", layout_slice, re.I | re.S)
        if not page_shell or inset_token not in page_shell.group(1):
            issues.append(
                f"Layout Gate: fixed 顶栏存在但 .page-shell 未使用 {inset_token}（内容会被顶栏遮挡）"
            )
        topbar_block = re.search(
            rf"\.c-{re.escape(prefix)}-topbar\s*\{{([^}}]*)\}}",
            layout_slice,
            re.I | re.S,
        )
        if topbar_block:
            body = topbar_block.group(1)
            if "min-height" in body and "height:" not in body.replace("line-height", ""):
                issues.append(
                    "Layout Gate: 顶栏使用 min-height 而非固定 height（标题可能撑高遮挡内容）"
                )

    return issues
