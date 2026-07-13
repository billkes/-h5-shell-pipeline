"""H5 vanilla CSS brief — translate html-tailwind stack guidelines."""

from __future__ import annotations

import re
from pathlib import Path

from batch.uupm_design_system import design_system_dir_for_app


def translate_tailwind_to_h5_vanilla(stack_md: str, master_md: str = "") -> str:
    """Convert stack-html-tailwind.md rules into monolith HTML/CSS guidance."""
    lines = [
        "# Stack Guidelines — h5-vanilla (monolith CSS)",
        "",
        "Source: translated from `stack-html-tailwind.md` for Vite monolith entry.htm.",
        "",
        "## Rules",
        "",
        "- Use CSS custom properties from MASTER (`--color-*`, `--space-*`) — no Tailwind build step.",
        "- No `@apply`, no utility class framework; write explicit selectors in entry.htm `<style>`.",
        "- Mobile-first: base styles for 375px, then `@media (min-width: 768px)` etc.",
        "- Prefer `rem` / `px` spacing tokens from MASTER spacing scale.",
        "- Interactive elements: `cursor: pointer`, `:active` opacity, `transition` 150–300ms.",
        "- Z-index: ambient canvas z-0, content z-1, nav z-40, modal z-50.",
        "- Respect `prefers-reduced-motion: reduce` — disable decorative animations.",
        "",
        "## Tailwind → Vanilla mapping",
        "",
    ]

    mappings = [
        (r"bg-primary", "background: var(--color-primary)"),
        (r"text-sm\s+md:text-base", "font-size: 0.875rem; @media (min-width: 768px) { font-size: 1rem }"),
        (r"hidden\s+md:(?:block|flex)", "display: none; @media (min-width: 768px) { display: block/flex }"),
        (r"fixed\s+top-0\s+z-50", "position: fixed; top: 0; z-index: 50"),
        (r"group-hover", "parent:hover .child { /* state */ }"),
    ]
    for tw, css in mappings:
        if tw.replace("\\", "") in stack_md or re.search(tw, stack_md):
            lines.append(f"- `{tw}` → `{css}`")

    if "viewport" in stack_md.lower() or "responsive" in stack_md.lower():
        lines.append("- Viewport: `<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">`")

    if master_md and "--color-primary" in master_md:
        lines.append("- Colors: copy MASTER palette into `:root` in entry.htm")

    lines.extend(["", "## Anti-patterns", "", "- Do NOT add tailwind CDN or build pipeline.", "- Do NOT use `[var(--x)]` when plain `var(--x)` works in CSS.", ""])
    return "\n".join(lines)


def write_h5_vanilla_brief(workspace: Path, app_name: str) -> Path | None:
    ds_dir = design_system_dir_for_app(workspace, app_name)
    stack_path = next(ds_dir.glob("stack-*.md"), None)
    if stack_path is None or not stack_path.is_file():
        return None
    master_path = ds_dir / "MASTER.md"
    master_text = master_path.read_text(encoding="utf-8") if master_path.is_file() else ""
    stack_text = stack_path.read_text(encoding="utf-8")
    out = ds_dir / "stack-h5-vanilla.md"
    out.write_text(translate_tailwind_to_h5_vanilla(stack_text, master_text), encoding="utf-8")
    return out
