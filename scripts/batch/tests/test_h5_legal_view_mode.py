"""Tests for verify_h5_legal_view_mode — modal vs route mutual exclusion."""

from __future__ import annotations

import json
from pathlib import Path

from batch.h5_legal_ui import verify_h5_legal_view_mode


def _write_vite_shell(project: Path, *, router: str, welcome_logic: str = "") -> None:
    project.mkdir(parents=True, exist_ok=True)
    (project / "本包登记信息.json").write_text(
        json.dumps({"packType": "h5_swift_shell", "codeAntiCorrelation": {"dartCodePrefix": "demo"}}),
        encoding="utf-8",
    )
    (project / "Demo Privacy Agreement.md").write_text("# Privacy\n\nBody\n", encoding="utf-8")
    (project / "h5").mkdir(parents=True, exist_ok=True)
    (project / "h5" / "package.json").write_text("{}", encoding="utf-8")
    (project / "h5" / "vite.config.ts").write_text("export default {}\n", encoding="utf-8")
    h5 = project / "h5" / "src"
    (h5 / "router").mkdir(parents=True)
    (h5 / "router" / "index.ts").write_text(router, encoding="utf-8")
    (h5 / "components").mkdir(parents=True)
    (h5 / "components" / "LegalOverlay.vue").write_text(
        '<template><div class="c-demo-legal-veil"></div></template>\n',
        encoding="utf-8",
    )
    if welcome_logic:
        (h5 / "views").mkdir(parents=True, exist_ok=True)
        (h5 / "views" / "WelcomeView.logic.ts").write_text(welcome_logic, encoding="utf-8")
        (h5 / "views" / "WelcomeView.vue").write_text(
            '<template><LegalOverlay v-if="legalDoc" /></template>\n',
            encoding="utf-8",
        )


def test_modal_without_route_passes(tmp_path: Path) -> None:
    project = tmp_path / "App"
    _write_vite_shell(
        project,
        router="export const routes = [{ path: '/welcome', component: {} }];\n",
        welcome_logic=(
            "const legalDoc = null;\n"
            "function openLegal(doc) { legalDoc.value = doc; }\n"
        ),
    )
    assert verify_h5_legal_view_mode(project) == []


def test_modal_with_route_fails(tmp_path: Path) -> None:
    project = tmp_path / "App"
    _write_vite_shell(
        project,
        router=(
            "export const routes = ["
            "{ path: '/welcome', component: {} },"
            "{ path: '/legal', component: {} },"
            "];\n"
        ),
        welcome_logic="const legalDoc = null;\n",
    )
    issues = verify_h5_legal_view_mode(project)
    assert any("must not register /legal route" in i for i in issues)


def test_open_legal_router_push_fails(tmp_path: Path) -> None:
    project = tmp_path / "App"
    _write_vite_shell(
        project,
        router="export const routes = [{ path: '/welcome', component: {} }];\n",
        welcome_logic=(
            "function openLegal(doc) { router.push({ path: '/legal', query: { doc } }); }\n"
        ),
    )
    issues = verify_h5_legal_view_mode(project)
    assert any("router.push('/legal')" in i for i in issues)
