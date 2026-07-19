"""Tests for h5 page bootstrap sync and spec file index."""

from __future__ import annotations

import json
from pathlib import Path

from batch.h5_page_prompts import collect_page_spec_file_index, format_page_implementation_prompt_block
from batch.h5_page_scaffold import route_to_page_type, sync_h5_page_scaffold
from batch.welcome_canon import format_welcome_spec_doc_refs, resolve_welcome_layout_variant


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
    (src / "views" / "HubView.vue").write_text("<template>agent hub</template>\n", encoding="utf-8")
    return project


def test_route_to_page_type() -> None:
    assert route_to_page_type("/hub") == "hub"
    assert route_to_page_type("/runs") == "list"
    assert route_to_page_type("/settings") == "settings"


def test_sync_does_not_write_page_vue(tmp_path: Path) -> None:
    project = _write_vite_project(
        tmp_path,
        router=(
            "import HubView from '../views/HubView.vue';\n"
            "export const routes = [{ path: '/hub', component: HubView }];\n"
        ),
    )
    hub = project / "h5" / "src" / "views" / "HubView.vue"
    before = hub.read_text(encoding="utf-8")
    sync_h5_page_scaffold(project, app_name="Demo", write=True)
    assert hub.read_text(encoding="utf-8") == before


def test_spec_index_lists_paths_not_prose(tmp_path: Path) -> None:
    project = _write_vite_project(
        tmp_path,
        router=(
            "import HubView from '../views/HubView.vue';\n"
            "import WelcomeView from '../views/WelcomeView.vue';\n"
            "export const routes = ["
            "{ path: '/hub', component: HubView },"
            "{ path: '/welcome', component: WelcomeView },"
            "];\n"
        ),
    )
    pages = project / "design-system" / "demo" / "pages"
    pages.mkdir(parents=True)
    (pages / "welcome.md").write_text("# Welcome\n", encoding="utf-8")
    (project / "功能文档.md").write_text("# spec\n", encoding="utf-8")
    (project / "本包视觉锁.json").write_text("{}", encoding="utf-8")
    welcome = project / "h5" / "src" / "views" / "WelcomeView.vue"
    welcome.write_text("<template>x</template>", encoding="utf-8")

    block = format_page_implementation_prompt_block(project, "Demo")
    assert "index only" in block
    assert "design-system/demo/pages/welcome.md" in block
    assert "H5_PAGE_SPECS" not in block


def test_collect_page_spec_file_index(tmp_path: Path) -> None:
    project = _write_vite_project(
        tmp_path,
        router="export const routes = [{ path: '/hub', component: HubView }];\n",
    )
    index = collect_page_spec_file_index(project, "Demo")
    assert any("HubView.vue" in v for v in index["views"])


def test_welcome_spec_doc_refs(tmp_path: Path) -> None:
    project = tmp_path / "App"
    pages = project / "design-system" / "demo" / "pages"
    pages.mkdir(parents=True)
    (pages / "welcome.md").write_text("# welcome\n", encoding="utf-8")
    (project / "本包视觉锁.json").write_text("{}", encoding="utf-8")
    refs = format_welcome_spec_doc_refs(project)
    assert "design-system/demo/pages/welcome.md" in refs


def test_resolve_welcome_layout_from_pages_md(tmp_path: Path) -> None:
    project = tmp_path / "App"
    pages = project / "design-system" / "demo" / "pages"
    pages.mkdir(parents=True)
    (pages / "welcome.md").write_text(
        "- **Visual tone (uupm):** Horizontal Scroll Journey\n",
        encoding="utf-8",
    )
    assert resolve_welcome_layout_variant(project) == "hero-split-trust"
