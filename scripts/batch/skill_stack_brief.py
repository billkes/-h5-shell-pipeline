"""H5 runtime brief — Vite deploy / Bridge only.

Style (Tailwind) and architecture (Vue) come from skill ``stack-*.md`` files.
This module does **not** translate Tailwind into hand-written CSS.
"""

from __future__ import annotations

from pathlib import Path

from batch.uupm_design_system import design_system_dir_for_app

H5_RUNTIME_FILENAME = "h5-runtime.md"


def write_h5_runtime_brief(workspace: Path, app_name: str) -> Path | None:
    """Write deploy/runtime contract only (singlefile Vite → h5_site)."""
    ds_dir = design_system_dir_for_app(workspace, app_name)
    ds_dir.mkdir(parents=True, exist_ok=True)
    out = ds_dir / H5_RUNTIME_FILENAME
    out.write_text(
        "\n".join(
            [
                "# H5 Runtime Contract (pipeline — deploy only)",
                "",
                "UI stack is **not** defined here. Read skill outputs:",
                "",
                "- `stack-vue.md` — Vue 3 Composition / SFC / router (skill `stacks/vue.csv`)",
                "- `stack-html-tailwind.md` — Tailwind utilities + theme (skill `stacks/html-tailwind.csv`)",
                "- `MASTER.md` + `typography-brief.md` — Google Fonts pairing",
                "- `icon-brief.md` + `skill-adapt/icon-manifest.json` — `@phosphor-icons/vue`",
                "- `skill-adapt/design-tokens.css` — CSS variables for Tailwind theme",
                "",
                "## Source vs deploy",
                "",
                "- Implement under `h5/` (Vue SFC + TypeScript + Tailwind).",
                "- Never hand-edit deploy output under `h5_site/`.",
                "- Pipeline `dev.h5.build` runs `npm run build:deploy` (vite-plugin-singlefile).",
                "- Local dev: `cd h5 && npm run dev` → Vite **Network** URL (LAN :5174).",
                "",
                "## Build commands",
                "",
                "```bash",
                "cd h5",
                "npm install",
                "npm run dev          # Vite :5174 — --host",
                "npm run build:deploy # → ../h5_site/{appSlug}/index.html",
                "```",
                "",
                "## Anti-patterns (runtime)",
                "",
                "- Do NOT invent a parallel CSS system that ignores `stack-html-tailwind.md`.",
                "- Do NOT replace Phosphor with iconfont / Font Awesome / Material Icons.",
                "- Do NOT skip `dev.h5.build` before gate.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    # Remove legacy compat artifact if present.
    legacy = ds_dir / "stack-h5-vite.md"
    if legacy.is_file():
        try:
            legacy.unlink()
        except OSError:
            pass
    return out


# Backward-compatible aliases (tests / legacy imports)
def write_h5_vite_brief(workspace: Path, app_name: str) -> Path | None:
    return write_h5_runtime_brief(workspace, app_name)


write_h5_vanilla_brief = write_h5_runtime_brief


def translate_tailwind_to_h5_vite(stack_md: str, master_md: str = "") -> str:
    """Deprecated: kept for tests — returns runtime contract stub, not a CSS rewrite."""
    del stack_md, master_md
    return (
        "# H5 Runtime Contract (pipeline — deploy only)\n\n"
        "Use skill `stack-html-tailwind.md` + `stack-vue.md`.\n"
        "vite-plugin-singlefile → h5_site; port 5174.\n"
    )


translate_tailwind_to_h5_vanilla = translate_tailwind_to_h5_vite
