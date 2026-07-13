"""skill.tokens — MASTER colors → design-tokens.json + CSS."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from batch.skill_resolve import integration_enabled, resolve_subskill_dir

if TYPE_CHECKING:
    from batch.config import BatchConfig

_TOKEN_KEYS = (
    ("primary", "color-primary"),
    ("secondary", "color-secondary"),
    ("accent", "color-accent"),
    ("background", "color-background"),
    ("foreground", "color-foreground"),
    ("muted", "color-muted"),
    ("border", "color-border"),
    ("destructive", "color-destructive"),
    ("ring", "color-ring"),
)


def _tokens_from_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    colors = candidate.get("colors") or {}
    primitive: dict[str, str] = {}
    semantic: dict[str, str] = {}
    for key, css_var in _TOKEN_KEYS:
        val = str(colors.get(key) or "").strip()
        if not val:
            continue
        prim_key = f"color.{key}"
        primitive[prim_key] = val
        semantic[css_var] = f"{{primitive.{prim_key}}}"

    spacing = candidate.get("spacing_scale") or {}
    for tok, val in spacing.items():
        if val:
            primitive[f"space.{tok}"] = str(val)

    return {
        "primitive": primitive,
        "semantic": semantic,
        "component": {
            "button-primary-bg": "{semantic.color-primary}",
            "button-primary-fg": "{semantic.color-on-primary}",
            "card-bg": "{semantic.color-background}",
        },
    }


def _css_from_tokens(tokens: dict[str, Any]) -> str:
    lines = [":root {"]
    primitive = tokens.get("primitive") or {}
    for key, val in sorted(primitive.items()):
        css_name = key.replace(".", "-")
        if re.match(r"^#[0-9A-Fa-f]{3,8}$", str(val)):
            lines.append(f"  --{css_name}: {val};")
        else:
            lines.append(f"  --{css_name}: {val};")
    for key, val in sorted((tokens.get("semantic") or {}).items()):
        ref = str(val).strip("{}")
        if ref.startswith("primitive."):
            css_ref = ref.replace("primitive.", "").replace(".", "-")
            lines.append(f"  --{key}: var(--{css_ref});")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def _css_has_declarations(text: str) -> bool:
    """True when CSS contains at least one custom property assignment."""
    return bool(re.search(r"--[\w-]+:\s*[^;}\s][^;]*;", text))


def _write_token_css(css_path: Path, tokens: dict[str, Any]) -> None:
    css_path.write_text(_css_from_tokens(tokens), encoding="utf-8")


def _try_node_generate(cfg: BatchConfig, tokens_path: Path, css_path: Path) -> bool:
    sub = resolve_subskill_dir(cfg, "design-system")
    if sub is None:
        return False
    script = sub / "scripts" / "generate-tokens.cjs"
    if not script.is_file():
        return False
    try:
        subprocess.run(
            ["node", str(script), "--config", str(tokens_path), "-o", str(css_path)],
            check=True,
            capture_output=True,
            timeout=30,
        )
        return css_path.is_file()
    except (OSError, subprocess.SubprocessError):
        return False


def run_skill_tokens(*, cfg: BatchConfig, workspace: Path) -> Path:
    """Write skill-adapt/design-tokens.json + design-tokens.css."""
    root = workspace / "skill-adapt"
    root.mkdir(parents=True, exist_ok=True)
    if not integration_enabled(cfg, "token_sync"):
        return root / "design-tokens.json"

    sel_path = root / "selected-candidate.json"
    if not sel_path.is_file():
        raise RuntimeError("skill.tokens 缺少 selected-candidate.json")
    data = json.loads(sel_path.read_text(encoding="utf-8"))
    candidate = data.get("designSystem") or {}
    tokens = _tokens_from_candidate(candidate)

    tokens_path = root / "design-tokens.json"
    tokens_path.write_text(json.dumps(tokens, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    css_path = root / "design-tokens.css"
    if _try_node_generate(cfg, tokens_path, css_path):
        generated = css_path.read_text(encoding="utf-8")
        if not _css_has_declarations(generated):
            _write_token_css(css_path, tokens)
    else:
        _write_token_css(css_path, tokens)

    impl_lines = [
        "# Token Implementation Block (skill.tokens)",
        "",
        "Paste into entry.htm `<style>` :root section:",
        "",
        "```css",
        css_path.read_text(encoding="utf-8").strip(),
        "```",
        "",
    ]
    (root / "token-impl-block.md").write_text("\n".join(impl_lines), encoding="utf-8")

    from batch.skill_brand import run_brand_check

    run_brand_check(cfg=cfg, workspace=workspace)
    return tokens_path


def format_token_impl_block(workspace: Path) -> str:
    path = workspace / "skill-adapt" / "token-impl-block.md"
    if not path.is_file():
        return ""
    rel = path.relative_to(workspace).as_posix()
    return f"[Design Tokens — read `{rel}` before entry.htm styles]"
