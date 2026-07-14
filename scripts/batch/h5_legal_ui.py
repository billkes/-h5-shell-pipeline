"""Verify h5_shell Legal overlay UI matches Modal Interior kit (not br-dump)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from batch.h5_site_paths import site_entry_path, site_root_from_register, vault_dir_path
from batch.h5_vite_gate import (
    h5_src_dir,
    is_h5_vite_project,
    vite_css_text,
    vite_legal_card_present,
    vite_vue_and_ts_text,
)
from batch.pack_type import is_h5_shell
from batch.screen_inventory import read_spec_text

REGISTER_FILE = "本包登记信息.json"

BR_DUMP_RE = re.compile(
    r"LEGAL\s*\[[^\]]+\]\s*\.replace\s*\(\s*/\\n/g\s*,\s*['\"]<br>['\"]\s*\)",
    re.IGNORECASE,
)
VISIBLE_SCROLLBAR_RE = re.compile(
    r"legal-scroll[^{]*\{[^}]*\}[^;]*::-webkit-scrollbar\s*\{[^}]*display\s*:\s*block",
    re.IGNORECASE | re.DOTALL,
)
SCROLLBAR_THUMB_RE = re.compile(
    r"legal-scroll::-webkit-scrollbar-thumb",
    re.IGNORECASE,
)
INLINE_STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
ROUTER_LEGAL_ROUTE_RE = re.compile(
    r"path\s*:\s*['\"]/legal['\"]",
    re.IGNORECASE,
)
OPEN_LEGAL_ROUTER_PUSH_RE = re.compile(
    r"openLegal[\s\S]{0,240}?router\.(?:push|replace)\s*\([\s\S]{0,120}?/legal",
    re.IGNORECASE,
)
LEGAL_MODAL_MARKERS_RE = re.compile(
    r"LegalOverlay|legalDoc|legal-veil|c-[a-z0-9]+-legal-veil",
    re.IGNORECASE,
)
LEGAL_ROUTE_MODAL_MARKERS_RE = re.compile(
    r"legal-veil|veil-dialog|role\s*=\s*['\"]dialog['\"]",
    re.IGNORECASE,
)


def _read_register(project: Path) -> dict:
    path = project / REGISTER_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def is_h5_shell_project(project: Path) -> bool:
    return is_h5_shell(str(_read_register(project).get("packType") or ""))


def resolve_prefix(project: Path) -> str:
    reg = _read_register(project)
    anti = reg.get("codeAntiCorrelation") or {}
    if isinstance(anti, dict):
        prefix = str(anti.get("dartCodePrefix") or "").strip()
        if prefix:
            return prefix
    from batch.workspace import dart_prefix

    return dart_prefix(project)


def panels_dir(project: Path) -> Path | None:
    reg = _read_register(project)
    vault = site_root_from_register(reg).rstrip("/")
    if not vault:
        return None
    prefix = resolve_prefix(project)
    return project / vault / f"{prefix}_panels"


def baseline_css_path(project: Path) -> Path | None:
    reg = _read_register(project)
    vault_path = vault_dir_path(project, reg)
    if not vault_path.is_dir():
        return None
    prefix = resolve_prefix(project)
    for name in (f"{prefix}_baseline.css", "paaow_baseline.css"):
        candidate = vault_path / name
        if candidate.is_file():
            return candidate
    for css in vault_path.glob("*_baseline.css"):
        return css
    return None


def find_render_js(project: Path) -> Path | None:
    panels = panels_dir(project)
    if panels is None or not panels.is_dir():
        return None
    prefix = resolve_prefix(project)
    preferred = panels / f"{prefix}_render.js"
    if preferred.is_file():
        return preferred
    matches = sorted(panels.glob("*_render.js"))
    return matches[0] if matches else None


def h5_vault_pattern(project: Path) -> str:
    return str(_read_register(project).get("h5VaultPattern") or "").strip()


def is_h5_monolith(project: Path) -> bool:
    return h5_vault_pattern(project) == "h5_monolith"


def entry_htm_path(project: Path) -> Path | None:
    path = site_entry_path(project)
    return path if path.is_file() else None


def extract_inline_css(html: str) -> str:
    return "\n".join(INLINE_STYLE_RE.findall(html))


def resolve_vault_js_text(project: Path) -> tuple[str | None, str]:
    if is_h5_vite_project(project):
        text = vite_vue_and_ts_text(project)
        if text.strip():
            return text, "h5_vite"
    render = find_render_js(project)
    if render is not None:
        return render.read_text(encoding="utf-8", errors="ignore"), "render.js"
    if is_h5_monolith(project):
        entry = entry_htm_path(project)
        if entry is not None:
            return entry.read_text(encoding="utf-8", errors="ignore"), "entry.htm"
    return None, ""


def resolve_vault_css_text(project: Path) -> str | None:
    if is_h5_vite_project(project):
        css = vite_css_text(project)
        if css.strip():
            return css
    css_path = baseline_css_path(project)
    if css_path is not None:
        return css_path.read_text(encoding="utf-8", errors="ignore")
    if is_h5_monolith(project):
        entry = entry_htm_path(project)
        if entry is not None:
            inline = extract_inline_css(
                entry.read_text(encoding="utf-8", errors="ignore")
            )
            if inline.strip():
                return inline
    return None


def router_file_has_legal_route(project: Path) -> bool:
    if not is_h5_vite_project(project):
        return False
    router_path = h5_src_dir(project) / "router" / "index.ts"
    if not router_path.is_file():
        return False
    return bool(ROUTER_LEGAL_ROUTE_RE.search(router_path.read_text(encoding="utf-8", errors="ignore")))


def project_needs_legal_ui(project: Path) -> bool:
    project = project.expanduser().resolve()
    if not is_h5_shell_project(project):
        return False
    if any(project.glob("*Privacy*")) or any(project.glob("*User*Agreement*")):
        return True
    if re.search(r"\blegal\b", read_spec_text(project), re.I):
        return True
    if router_file_has_legal_route(project):
        return True
    if is_h5_vite_project(project):
        text = vite_vue_and_ts_text(project)
        if "openLegal" in text or "LegalOverlay" in text:
            return True
    return False


def uses_legal_modal(project: Path) -> bool:
    if not is_h5_vite_project(project):
        return False
    text = vite_vue_and_ts_text(project)
    css = vite_css_text(project)
    surface = f"{text}\n{css}"
    return bool(LEGAL_MODAL_MARKERS_RE.search(surface))


def verify_h5_legal_view_mode(project: Path) -> list[str]:
    """Legal must be modal-without-route OR full-page route-without-modal — never both."""
    project = project.expanduser().resolve()
    issues: list[str] = []

    if not project_needs_legal_ui(project):
        return issues

    has_route = router_file_has_legal_route(project)
    has_modal = uses_legal_modal(project)
    src_text = vite_vue_and_ts_text(project) if is_h5_vite_project(project) else ""

    if OPEN_LEGAL_ROUTER_PUSH_RE.search(src_text):
        issues.append(
            "LEGAL_VIEW_MODE: openLegal must toggle local modal state, not router.push('/legal')"
        )

    if has_route and has_modal:
        issues.append(
            "LEGAL_VIEW_MODE: modal LegalOverlay must not register /legal route"
        )

    if has_route and not has_modal:
        for rel in (
            "views/LegalOverlay.vue",
            "views/LegalView.vue",
            "pages/LegalView.vue",
        ):
            candidate = h5_src_dir(project) / rel
            if not candidate.is_file():
                continue
            body = candidate.read_text(encoding="utf-8", errors="ignore")
            if LEGAL_ROUTE_MODAL_MARKERS_RE.search(body):
                issues.append(
                    "LEGAL_VIEW_MODE: /legal route page must be full-page, not modal veil/dialog"
                )
                break

    if not has_route and not has_modal and is_h5_vite_project(project):
        issues.append(
            "LEGAL_VIEW_MODE: missing legal viewer (LegalOverlay modal or dedicated /legal page)"
        )

    return issues


def verify_h5_legal_ui(project: Path) -> list[str]:
    project = project.expanduser().resolve()
    issues: list[str] = []

    if not is_h5_shell_project(project):
        return issues

    if not project_needs_legal_ui(project):
        return issues

    if router_file_has_legal_route(project) and not uses_legal_modal(project):
        return issues

    prefix = resolve_prefix(project)
    legal_token = f"{prefix}-legal" if prefix else "legal"
    class_token = f"c-{prefix}-legal" if prefix else "c-legal"

    render_text, source = resolve_vault_js_text(project)
    if render_text is None:
        if is_h5_vite_project(project):
            issues.append("RENDER: missing h5/src Vue/TS sources for Legal overlay")
        elif is_h5_monolith(project):
            issues.append("RENDER: missing vault entry.htm for Legal overlay (h5_monolith)")
        else:
            issues.append("RENDER: missing vault *_render.js for Legal overlay")
        return issues
    if BR_DUMP_RE.search(render_text):
        issues.append(
            "RENDER: forbidden LEGAL br-dump — use formatLegalBody + section/para HTML"
        )
    if "formatLegalBody" not in render_text:
        issues.append("RENDER: missing formatLegalBody() helper")
    for token in (f"{class_token}-header", f"{class_token}-scroll", f"{class_token}-title"):
        if token not in render_text:
            issues.append(f"RENDER: missing class {token} in renderLegal markup")

    css = resolve_vault_css_text(project)
    section_key = f"{class_token}-section"
    if section_key not in render_text and section_key not in (css or ""):
        issues.append(f"RENDER: missing {section_key} (Legal kit section headings)")
    if css is None:
        if is_h5_vite_project(project):
            issues.append("CSS: missing h5/src/styles CSS for Legal overlay (h5_vite)")
        elif is_h5_monolith(project):
            issues.append("CSS: missing inline <style> legal rules in entry.htm (h5_monolith)")
        else:
            issues.append("CSS: missing vault *_baseline.css")
    else:
        card_key = f"{class_token}-card"
        scroll_key = f"{class_token}-scroll"
        if not vite_legal_card_present(render_text, css, class_token, prefix=prefix):
            issues.append(f"CSS: missing .{card_key} (or dialog flex card with min(90vw, 340px))")
        if scroll_key not in css:
            issues.append(f"CSS: missing .{scroll_key}")
        if card_key in css and "flex-direction" not in css.split(card_key, 1)[-1][:400]:
            issues.append(f"CSS: .{card_key} should use flex column layout")
        width_surface = css if not is_h5_vite_project(project) else f"{render_text}\n{css}"
        if "340px" not in width_surface and "90vw" not in width_surface:
            issues.append("CSS: legal card width should use min(90vw, 340px) per blueprint")
        if VISIBLE_SCROLLBAR_RE.search(css) or SCROLLBAR_THUMB_RE.search(css):
            issues.append(
                "CSS: legal-scroll must not re-enable web scrollbars (H5去风味 §4)"
            )
        if scroll_key in css:
            scroll_chunk = css.split(scroll_key, 1)[-1][:500]
            if "mask-image" not in scroll_chunk and "linear-gradient" not in scroll_chunk:
                issues.append(
                    f"CSS: .{scroll_key} needs bottom fade (mask-image) for scroll affordance"
                )

    _ = (legal_token, source)
    return issues
