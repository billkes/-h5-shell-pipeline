"""H5 Vite stack brief — translate html-tailwind stack guidelines for Vue + Vite build."""

from __future__ import annotations

import re
from pathlib import Path

from batch.uupm_design_system import design_system_dir_for_app


def translate_tailwind_to_h5_vite(stack_md: str, master_md: str = "") -> str:
    """Convert stack-html-tailwind.md rules into Vite + Vue monolith guidance."""
    lines = [
        "# Stack Guidelines — h5-vite (Vue 3 + Vite singlefile)",
        "",
        "Source: translated from `stack-html-tailwind.md` for **Vite** build → `h5_site/{appSlug}/index.html`.",
        "",
        "## Source vs deploy",
        "",
        "- **Implement** under `h5/src/` (Vue SFC + TypeScript).",
        "- **Never** hand-edit deploy output under `h5_site/{appSlug}/`.",
        "- Pipeline step `dev.h5.build` runs `npm run build:deploy` (vite-plugin-singlefile).",
        "- Local dev: `cd h5 && npm run dev` → Vite **Network** URL (LAN IP :5174); `h5EntryUrlDev` synced on `lock.dimensions`.",
        "",
        "## Rules",
        "",
        "- Use CSS custom properties from MASTER / `skill-adapt/design-tokens.css` in `src/styles/global.css`.",
        "- Prefer Vue SFC `<style scoped>` + shared tokens; no Tailwind CDN unless stack draw explicitly requires it.",
        "- Mobile-first: base styles for 375px, then `@media (min-width: 768px)`.",
        "- Interactive elements: min-height 44px, `:active` opacity, transitions 150–300ms.",
        "- Z-index: ambient canvas z-0, content z-1, nav z-40, modal z-50.",
        "- Respect `prefers-reduced-motion: reduce`.",
        "- Import legal text from `src/legal/{prefix}_legal_bundled.ts` (sync script output).",
        "",
        "## Tailwind → Vue/CSS mapping",
        "",
    ]

    mappings = [
        (r"bg-primary", "background: var(--color-primary)"),
        (r"text-sm\s+md:text-base", "font-size: 0.875rem; @media (min-width: 768px) { font-size: 1rem }"),
        (r"hidden\s+md:(?:block|flex)", "display: none; @media (min-width: 768px) { display: block/flex }"),
        (r"fixed\s+top-0\s+z-50", "position: fixed; top: 0; z-index: 50"),
    ]
    for tw, css in mappings:
        if tw.replace("\\", "") in stack_md or re.search(tw, stack_md):
            lines.append(f"- `{tw}` → `{css}`")

    if master_md and "--color-primary" in master_md:
        lines.append("- Colors: map MASTER palette into `:root` in global.css")

    lines.extend(
        [
            "",
            "## Build commands",
            "",
            "```bash",
            "cd h5",
            "npm install",
            "npm run dev          # Vite :5174 — binds LAN (--host); use Network URL on phone",
            "npm run build:deploy # → ../h5_site/{appSlug}/index.html",
            "```",
            "",
            "## Anti-patterns",
            "",
            "- Do NOT write business UI directly into `h5_site/` (except build output).",
            "- Do NOT skip `dev.h5.build` before gate — entry.htm must come from Vite.",
            "- Do NOT use external iconfont libraries — inline SVG sprite in Vue components.",
            "",
        ]
    )
    return "\n".join(lines)


def write_h5_vite_brief(workspace: Path, app_name: str) -> Path | None:
    ds_dir = design_system_dir_for_app(workspace, app_name)
    stack_path = next(ds_dir.glob("stack-*.md"), None)
    if stack_path is None or not stack_path.is_file():
        return None
    master_path = ds_dir / "MASTER.md"
    master_text = master_path.read_text(encoding="utf-8") if master_path.is_file() else ""
    stack_text = stack_path.read_text(encoding="utf-8")
    out = ds_dir / "stack-h5-vite.md"
    out.write_text(translate_tailwind_to_h5_vite(stack_text, master_text), encoding="utf-8")
    return out


# Backward-compatible alias (tests / legacy imports)
write_h5_vanilla_brief = write_h5_vite_brief
translate_tailwind_to_h5_vanilla = translate_tailwind_to_h5_vite
