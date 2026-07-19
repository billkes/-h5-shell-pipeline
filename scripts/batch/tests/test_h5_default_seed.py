"""Tests for H5 default seed bootstrap gate (编组 I)."""

from __future__ import annotations

from pathlib import Path

from batch.h5_default_seed import (
    collect_h5_default_seed_violations,
    requires_default_seed,
    sync_default_seed_stub,
)


def _seed_project(tmp_path: Path, *, with_welcome: bool = True, with_seed: bool = True) -> Path:
    h5 = tmp_path / "h5"
    (h5 / "src" / "router").mkdir(parents=True)
    (h5 / "src" / "views").mkdir(parents=True)
    (h5 / "src" / "store").mkdir(parents=True)
    (h5 / "package.json").write_text('{"name":"demo-h5"}', encoding="utf-8")
    (h5 / "vite.config.ts").write_text("export default {}\n", encoding="utf-8")
    (tmp_path / "本包登记信息.json").write_text(
        '{"codeAntiCorrelation":{"dartCodePrefix":"demo"}}',
        encoding="utf-8",
    )
    (tmp_path / "Temioo - Demo.md").write_text(
        "**演示数据**\n\n| First launch | Welcome Continue | 静默预置 3 草稿 |\n",
        encoding="utf-8",
    )
    routes = "export const routes = [\n"
    if with_welcome:
        routes += "  { path: '/welcome', component: () => import('../views/WelcomeView.vue') },\n"
    routes += "  { path: '/hub', component: () => import('../views/HubView.vue') },\n"
    routes += "  { path: '/runs', component: () => import('../views/RunsView.vue') },\n"
    routes += "];\n"
    (h5 / "src" / "router" / "index.ts").write_text(routes, encoding="utf-8")
    if with_seed:
        (h5 / "src" / "store" / "defaultSeed.ts").write_text(
            """
export const BOOTSTRAP_KEY = 'demo_bootstrap_v1';
export function buildDefaultPlans() {
  return [{ id: 'p1', title: 'Demo Plan', courseTag: 'CS101', sections: [] }];
}
export function buildDefaultRuns(plans) {
  return [{ id: 'r1', planId: plans[0].id, startedAt: '2026-01-01' }];
}
export function ensureBootstrapData() {}
""",
            encoding="utf-8",
        )
    return tmp_path


def test_requires_default_seed_from_product_doc(tmp_path: Path) -> None:
    project = _seed_project(tmp_path, with_seed=False)
    assert requires_default_seed(project)


def test_collect_missing_default_seed_module(tmp_path: Path) -> None:
    project = _seed_project(tmp_path, with_seed=False)
    issues = collect_h5_default_seed_violations(project)
    assert issues
    assert "defaultSeed.ts" in issues[0]


def test_collect_missing_welcome_bootstrap_call(tmp_path: Path) -> None:
    project = _seed_project(tmp_path)
    (project / "h5" / "src" / "views" / "WelcomeView.logic.ts").write_text(
        """
export function useWelcomeLogic() {
  function continueFlow() {
    localStorage.setItem('demo_welcome_v1', 'true');
  }
  return { continueFlow };
}
""",
        encoding="utf-8",
    )
    issues = collect_h5_default_seed_violations(project)
    assert any("WelcomeView.logic.ts" in i for i in issues)


def test_collect_ok_wired_bootstrap(tmp_path: Path) -> None:
    project = _seed_project(tmp_path)
    (project / "h5" / "src" / "views" / "WelcomeView.logic.ts").write_text(
        """
import { ensureBootstrapData } from '../store/defaultSeed';
export function useWelcomeLogic() {
  function continueFlow() {
    ensureBootstrapData();
    localStorage.setItem('demo_welcome_v1', 'true');
  }
  return { continueFlow };
}
""",
        encoding="utf-8",
    )
    assert collect_h5_default_seed_violations(project) == []


def test_collect_missing_vault_asset(tmp_path: Path) -> None:
    project = _seed_project(tmp_path)
    seed = project / "h5" / "src" / "store" / "defaultSeed.ts"
    seed.write_text(
        seed.read_text(encoding="utf-8")
        + "\nconst SLIDE = vaultAssetPath('seed_slide_cs101.jpg');\n",
        encoding="utf-8",
    )
    (project / "h5" / "src" / "views" / "WelcomeView.logic.ts").write_text(
        "import { ensureBootstrapData } from '../store/defaultSeed';\n"
        "export function useWelcomeLogic() { function continueFlow() { ensureBootstrapData(); } return { continueFlow }; }\n",
        encoding="utf-8",
    )
    issues = collect_h5_default_seed_violations(project)
    assert any("seed_slide_cs101.jpg" in i for i in issues)


def test_sync_default_seed_stub_is_agent_owned(tmp_path: Path) -> None:
    """No repo template — Agent implements defaultSeed.ts per H5壳Vite工程规范."""
    project = _seed_project(tmp_path, with_seed=False)
    path = sync_default_seed_stub(project, app_name="Demo", write=True)
    assert path is None
