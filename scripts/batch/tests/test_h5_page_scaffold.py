"""Tests for h5_page_scaffold sync."""

from __future__ import annotations

from pathlib import Path

from batch.h5_page_scaffold import (
    route_to_page_type,
    sync_h5_page_scaffold,
    sync_h5_page_scaffold_css,
)


def _write_vite_project(root: Path, *, router: str) -> Path:
    project = root / "ScaffoldApp"
    src = project / "h5" / "src"
    (src / "router").mkdir(parents=True)
    (src / "views").mkdir(parents=True)
    (src / "styles").mkdir(parents=True)
    (project / "h5" / "package.json").write_text("{}", encoding="utf-8")
    (project / "h5" / "vite.config.ts").write_text("export default {}\n", encoding="utf-8")
    (project / "skill-input").mkdir(parents=True)
    (project / "skill-input" / "context.json").write_text(
        '{"constraints":{"interactionTopology":"T4_wizard"}}',
        encoding="utf-8",
    )
    (project / "本包登记信息.json").write_text(
        '{"packType":"h5_swift_shell","codeAntiCorrelation":{"dartCodePrefix":"demo"}}',
        encoding="utf-8",
    )
    (src / "styles" / "global.css").write_text(":root {}\n", encoding="utf-8")
    (src / "router" / "index.ts").write_text(router, encoding="utf-8")
    (src / "views" / "HubView.vue").write_text("<template>old</template>\n", encoding="utf-8")
    return project


def test_route_to_page_type() -> None:
    assert route_to_page_type("/hub") == "hub"
    assert route_to_page_type("/runs") == "list"
    assert route_to_page_type("/settings") == "settings"


def test_sync_overwrites_hub_template(tmp_path: Path) -> None:
    project = _write_vite_project(
        tmp_path,
        router=(
            "import HubView from '../views/HubView.vue';\n"
            "export const routes = [{ path: '/hub', component: HubView }];\n"
        ),
    )
    written = sync_h5_page_scaffold(project, app_name="Demo", write=True)
    hub = project / "h5" / "src" / "views" / "HubView.vue"
    text = hub.read_text(encoding="utf-8")
    assert hub in written
    assert "SCAFFOLD:pipeline:start" in text
    assert "data-demo-landmark=\"hero\"" in text
    assert "useHubLogic" in text
    assert "<template>old</template>" not in text


def test_sync_list_template_rich_ia(tmp_path: Path) -> None:
    project = _write_vite_project(
        tmp_path,
        router=(
            "import RunsView from '../views/RunsView.vue';\n"
            "export const routes = [{ path: '/runs', component: RunsView }];\n"
        ),
    )
    sync_h5_page_scaffold(project, app_name="Demo", write=True)
    runs = project / "h5" / "src" / "views" / "RunsView.vue"
    text = runs.read_text(encoding="utf-8")
    css = (project / "h5" / "src" / "styles" / "global.css").read_text(encoding="utf-8")
    assert "list-hero" in text
    assert "list-kpi-strip" in text
    assert "run-card" in text
    assert "Go to Prepare" in text
    assert ".c-demo-run-card" in css


def test_sync_settings_composed(tmp_path: Path) -> None:
    project = _write_vite_project(
        tmp_path,
        router=(
            "import SettingsView from '../views/SettingsView.vue';\n"
            "export const routes = [{ path: '/settings', component: SettingsView }];\n"
        ),
    )
    sync_h5_page_scaffold(project, app_name="Demo", write=True)
    text = (project / "h5" / "src" / "views" / "SettingsView.vue").read_text(encoding="utf-8")
    assert "settings-hero" in text
    assert "settings-wallet" in text
    assert "settings-menu" in text


def test_sync_css_block(tmp_path: Path) -> None:
    project = _write_vite_project(
        tmp_path,
        router=(
            "import HubView from '../views/HubView.vue';\n"
            "export const routes = [{ path: '/hub', component: HubView }];\n"
        ),
    )
    sync_h5_page_scaffold_css(project, page_types=("hub",), topology="T4_wizard", write=True)
    css = (project / "h5" / "src" / "styles" / "global.css").read_text(encoding="utf-8")
    assert "PAGE-SCAFFOLD:pipeline" in css
    assert ".c-demo-hub-hero" in css
    assert "font-size: 10px" not in css


def test_sync_router_meta_blocks(tmp_path: Path) -> None:
    project = _write_vite_project(
        tmp_path,
        router=(
            "import HubView from '../views/HubView.vue';\n"
            "import RunsView from '../views/RunsView.vue';\n"
            "export const router = createRouter({ routes: [\n"
            "  { path: '/hub', component: HubView, meta: { scene: 'hub', tab: true } },\n"
            "  { path: '/runs', component: RunsView, meta: { scene: 'list', tab: true } },\n"
            "] });\n"
        ),
    )
    (project / "h5" / "src" / "views" / "RunsView.vue").write_text(
        "<template>old</template>\n", encoding="utf-8"
    )
    written = sync_h5_page_scaffold(project, app_name="Demo", write=True)
    assert project / "h5" / "src" / "views" / "HubView.vue" in written
    assert project / "h5" / "src" / "views" / "RunsView.vue" in written


def test_sync_legal_and_welcome(tmp_path: Path) -> None:
    project = _write_vite_project(
        tmp_path,
        router=(
            "import WelcomeView from '../views/WelcomeView.vue';\n"
            "export const routes = ["
            "{ path: '/welcome', component: WelcomeView },"
            "];\n"
        ),
    )
    (project / "Demo Privacy Agreement.md").write_text("# Privacy\n\nBody\n", encoding="utf-8")
    (project / "Demo User Agreement.md").write_text("# Terms\n\nBody\n", encoding="utf-8")
    (project / "h5" / "src" / "legal").mkdir(parents=True)
    (project / "h5" / "src" / "legal" / "demo_legal_bundled.ts").write_text(
        'export const LEGAL = { privacy: "p", terms: "t" };\n', encoding="utf-8"
    )
    written = sync_h5_page_scaffold(project, app_name="Demo", write=True)
    css = (project / "h5" / "src" / "styles" / "global.css").read_text(encoding="utf-8")
    welcome = (project / "h5" / "src" / "views" / "WelcomeView.vue").read_text(encoding="utf-8")
    legal = (project / "h5" / "src" / "components" / "LegalOverlay.vue").read_text(encoding="utf-8")
    assert "LEGAL:pipeline" in css
    assert ".c-demo-legal-scroll" in css
    assert project / "h5" / "src" / "components" / "LegalOverlay.vue" in written
    assert "welcome-trust" in welcome
    assert welcome.count("<li>") >= 2
    assert "18 years or older" in welcome
    assert "formatLegalBody" in legal
    assert "legal-section" in css or "legal-section" in legal
    assert "Load demo" not in welcome
    assert "showDemo" not in welcome
    logic = (project / "h5" / "src" / "views" / "WelcomeView.logic.ts").read_text(
        encoding="utf-8"
    )
    assert "loadDemo" not in logic
    assert "legalDoc" in logic
    assert "/legal" not in logic
