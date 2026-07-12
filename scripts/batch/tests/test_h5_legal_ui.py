"""Tests for h5_legal_ui verify."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from batch.h5_legal_ui import verify_h5_legal_ui  # noqa: E402

PAWIOO = PROJECT_ROOT / "output" / "Pawioo-Flutter" / "Pawioo"

GOOD_RENDER = """
function formatLegalBody(raw) { return { title: 'T', bodyHtml: '' }; }
function renderLegal(params) {
  return '<div class="c-demo-legal-card"><div class="c-demo-legal-header">' +
    '<h1 class="c-demo-legal-title">T</h1></div><div class="c-demo-legal-scroll"></div></div>';
}
"""

BAD_RENDER = """
function renderLegal(params) {
  var text = U.LEGAL[doc].replace(/\\n/g, '<br>');
  return text;
}
"""

GOOD_CSS = """
.c-demo-legal-card { display: flex; flex-direction: column; width: min(90vw, 340px); }
.c-demo-legal-scroll {
  mask-image: linear-gradient(to bottom, #000 calc(100% - 28px), transparent 100%);
  scrollbar-width: none;
}
.c-demo-legal-scroll::-webkit-scrollbar { display: none; width: 0; height: 0; }
"""

BAD_CSS_SCROLL = """
.c-demo-legal-card { display: flex; flex-direction: column; width: min(90vw, 340px); }
.c-demo-legal-scroll::-webkit-scrollbar { display: block; width: 4px; }
.c-demo-legal-scroll::-webkit-scrollbar-thumb { background: #000; }
"""


def _write_ui_project(root: Path, render: str, css: str) -> Path:
    project = root / "UiApp"
    vault = project / "assets" / "demo_vault"
    panels = vault / "demo_panels"
    panels.mkdir(parents=True)
    (project / "本包登记信息.json").write_text(
        json.dumps(
            {
                "packType": "h5_shell",
                "bundleVaultDir": "assets/demo_vault/",
                "codeAntiCorrelation": {"dartCodePrefix": "demo"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (panels / "demo_render.js").write_text(render, encoding="utf-8")
    (vault / "demo_baseline.css").write_text(css, encoding="utf-8")
    return project


MONOLITH_ENTRY = """<!DOCTYPE html>
<html><head><style>
.c-demo-legal-card {{ display: flex; flex-direction: column; width: min(90vw, 340px); }}
.c-demo-legal-scroll {{
  mask-image: linear-gradient(to bottom, #000 calc(100% - 28px), transparent 100%);
  scrollbar-width: none;
}}
.c-demo-legal-scroll::-webkit-scrollbar {{ display: none; }}
</style></head><body><script>
function formatLegalBody(raw) {{ return {{ title: 'T', bodyHtml: '' }}; }}
function renderLegal(params) {{
  return '<div class="u-demo-veil-dialog"><div class="c-demo-legal-card"><div class="c-demo-legal-header">' +
    '<h1 class="c-demo-legal-title">T</h1></div><div class="c-demo-legal-scroll"></div></div></div>';
}}
Kit.ui.OVERLAY_PATHS = ['/legal', '/filter'];
Kit.ui.isOverlayPath = function(path) {{ return Kit.ui.OVERLAY_PATHS.indexOf(path) >= 0; }};
var router = {{
  _overlayBase: null,
  dispatch: function() {{
    if (Kit.ui.isOverlayPath(path)) {{
      var base = this.resolveOverlayBase(path);
      root.innerHTML = Kit.ui.render(base.path, base.params) + Kit.ui.render(path, this.currentParams);
    }}
  }}
}};
function matchRoute(path, params) {{
  if (path === '/legal') return renderLegal(params);
  if (path === '/filter') return '<div class="u-demo-veil-sheet"></div>';
}}
</script></body></html>
"""


def _write_monolith_project(root: Path) -> Path:
    project = root / "MonoApp"
    vault = project / "assets" / "demo_vault"
    vault.mkdir(parents=True)
    (project / "本包登记信息.json").write_text(
        json.dumps(
            {
                "packType": "h5_shell",
                "h5VaultPattern": "h5_monolith",
                "bundleEntryPath": "assets/demo_vault/demo_entry.htm",
                "bundleVaultDir": "assets/demo_vault/",
                "codeAntiCorrelation": {"dartCodePrefix": "demo"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (vault / "demo_entry.htm").write_text(MONOLITH_ENTRY, encoding="utf-8")
    return project


class H5LegalUiTests(unittest.TestCase):
    def test_good_project_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _write_ui_project(Path(tmp), GOOD_RENDER, GOOD_CSS)
            self.assertEqual(verify_h5_legal_ui(project), [])

    def test_br_dump_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _write_ui_project(Path(tmp), BAD_RENDER, GOOD_CSS)
            issues = verify_h5_legal_ui(project)
            self.assertTrue(any("br-dump" in i for i in issues))

    def test_visible_scrollbar_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _write_ui_project(Path(tmp), GOOD_RENDER, BAD_CSS_SCROLL)
            issues = verify_h5_legal_ui(project)
            self.assertTrue(any("scrollbar" in i.lower() for i in issues))

    def test_monolith_entry_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _write_monolith_project(Path(tmp))
            self.assertEqual(verify_h5_legal_ui(project), [])


if __name__ == "__main__":
    unittest.main()
