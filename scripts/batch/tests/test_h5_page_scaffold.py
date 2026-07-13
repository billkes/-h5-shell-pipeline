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
        '{"codeAntiCorrelation":{"dartCodePrefix":"demo"}}',
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


def test_sync_css_block(tmp_path: Path) -> None:
    project = _write_vite_project(
        tmp_path,
        router="import HubView from '../views/HubView.vue';\n",
    )
    sync_h5_page_scaffold_css(project, write=True)
    css = (project / "h5" / "src" / "styles" / "global.css").read_text(encoding="utf-8")
    assert "PAGE-SCAFFOLD:pipeline" in css
    assert ".c-demo-hub-hero" in css
