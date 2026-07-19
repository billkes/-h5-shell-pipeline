"""Tests for Bridge Plaza purchase QA SKU 311400."""

from __future__ import annotations

from pathlib import Path

from batch.h5_plaza_purchase import (
    PLAZA_TEST_PURCHASE_PRODUCT_ID,
    collect_h5_plaza_purchase_violations,
)


def _minimal_vite_project(tmp_path: Path) -> Path:
    h5 = tmp_path / "h5"
    (h5 / "src" / "router").mkdir(parents=True)
    (h5 / "src" / "views").mkdir(parents=True)
    (h5 / "src" / "bridge").mkdir(parents=True)
    (h5 / "src" / "bridge" / "index.ts").write_text("export async function bridgeCall() {}", encoding="utf-8")
    (h5 / "src" / "router" / "index.ts").write_text(
        "export const routes = [{ path: '/plaza', component: () => import('../views/PlazaView.vue') }];\n",
        encoding="utf-8",
    )
    (h5 / "package.json").write_text('{"name":"demo-h5"}', encoding="utf-8")
    (h5 / "vite.config.ts").write_text("export default {}\n", encoding="utf-8")
    (tmp_path / "本包登记信息.json").write_text(
        '{"codeAntiCorrelation":{"dartCodePrefix":"demo"}}',
        encoding="utf-8",
    )
    (tmp_path / "功能文档.md").write_text(
        "## Screen Inventory\n\n| Route | Screen |\n| --- | --- |\n| #/plaza | Bridge Plaza |\n",
        encoding="utf-8",
    )
    return tmp_path


def test_collect_plaza_purchase_violation_wrong_sku(tmp_path: Path) -> None:
    project = _minimal_vite_project(tmp_path)
    plaza = project / "h5" / "src" / "views" / "PlazaView.vue"
    plaza.write_text(
        """
async function call(action: string) {
  const payload = action === 'purchase' ? { productId: 'Heat00' } : {};
}
""",
        encoding="utf-8",
    )
    issues = collect_h5_plaza_purchase_violations(project)
    assert issues
    assert "311400" in issues[0]


def test_collect_plaza_purchase_ok_const_ref(tmp_path: Path) -> None:
    project = _minimal_vite_project(tmp_path)
    plaza = project / "h5" / "src" / "views" / "PlazaView.vue"
    plaza.write_text(
        """
const PLAZA_TEST_PURCHASE_PRODUCT_ID = '311400';
async function call(action: string) {
  const payload = action === 'purchase' ? { productId: PLAZA_TEST_PURCHASE_PRODUCT_ID } : {};
}
""",
        encoding="utf-8",
    )
    assert collect_h5_plaza_purchase_violations(project) == []


def test_collect_plaza_purchase_ok_311400(tmp_path: Path) -> None:
    project = _minimal_vite_project(tmp_path)
    plaza = project / "h5" / "src" / "views" / "PlazaView.vue"
    plaza.write_text(
        """
async function call(action: string) {
  const payload = action === 'purchase' ? { productId: '311400' } : {};
}
""",
        encoding="utf-8",
    )
    assert collect_h5_plaza_purchase_violations(project) == []


def test_plaza_spec_index_lists_view(tmp_path: Path) -> None:
    from batch.h5_page_prompts import format_page_implementation_prompt_block

    project = _minimal_vite_project(tmp_path)
    block = format_page_implementation_prompt_block(project, "DemoApp")
    assert "index only" in block
    assert "311400" not in block
