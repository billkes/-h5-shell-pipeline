"""Tests for h5_overlay_stack verify."""

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

from batch.h5_overlay_stack import verify_h5_overlay_stack  # noqa: E402

PAWIOO = PROJECT_ROOT / "output" / "Pawioo-Flutter" / "Pawioo"

GOOD_CORE = """
NS.ui.OVERLAY_PATHS = ['/legal', '/journal/filter'];
NS.ui.isOverlayPath = function (path) { return NS.ui.OVERLAY_PATHS.indexOf(path) >= 0; };
NS.ui.router = {
  _overlayBase: null,
  dispatch: function () {
    var path = this.parse();
    if (NS.ui.isOverlayPath(path)) {
      var base = this.resolveOverlayBase(path);
      root.innerHTML = NS.ui.render(base.path, base.params) + NS.ui.render(path, this.currentParams);
    }
  }
};
"""

BAD_CORE = """
NS.ui.router = {
  dispatch: function () {
    var path = this.parse();
    root.innerHTML = NS.ui.render(path, this.currentParams);
  }
};
"""

GOOD_RENDER = """
U.render = function (path) {
  switch (path) {
    case '/legal': return '<div class="u-demo-veil-dialog"></div>';
    case '/journal/filter': return '<div class="u-demo-veil-sheet"></div>';
  }
};
"""

NO_OVERLAY_RENDER = """
U.render = function (path) {
  switch (path) {
    case '/home': return '<div>home</div>';
  }
};
"""


def _write_project(root: Path, core: str, render: str) -> Path:
    project = root / "OverlayApp"
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
    (panels / "demo_core.js").write_text(core, encoding="utf-8")
    (panels / "demo_render.js").write_text(render, encoding="utf-8")
    (vault / "demo_baseline.css").write_text(
        ":root { --demo-veil-scrim: rgba(0, 0, 0, 0.5); --demo-veil-dialog-scrim: rgba(0, 0, 0, 0.6); }",
        encoding="utf-8",
    )
    return project


MONOLITH_ENTRY = """<!DOCTYPE html>
<html><head><style>
:root {{ --demo-veil-scrim: rgba(0, 0, 0, 0.5); }}
</style></head><body><script>
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
function matchRoute(path) {{
  if (path === '/legal') return '<div class="u-demo-veil-dialog"></div>';
  if (path === '/filter') return '<div class="u-demo-veil-sheet"></div>';
}}
</script></body></html>
"""


def _write_monolith_project(root: Path) -> Path:
    project = root / "MonoOverlayApp"
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


class H5OverlayStackTests(unittest.TestCase):
    def test_good_project_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _write_project(Path(tmp), GOOD_CORE, GOOD_RENDER)
            self.assertEqual(verify_h5_overlay_stack(project), [])

    def test_naive_dispatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _write_project(Path(tmp), BAD_CORE, GOOD_RENDER)
            issues = verify_h5_overlay_stack(project)
            self.assertTrue(any("dispatch" in i.lower() for i in issues))

    def test_no_overlay_routes_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _write_project(Path(tmp), BAD_CORE, NO_OVERLAY_RENDER)
            self.assertEqual(verify_h5_overlay_stack(project), [])

    def test_monolith_entry_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _write_monolith_project(Path(tmp))
            self.assertEqual(verify_h5_overlay_stack(project), [])

    @unittest.skipUnless(PAWIOO.is_dir(), "Pawioo output not present")
    def test_pawioo_passes(self) -> None:
        self.assertEqual(verify_h5_overlay_stack(PAWIOO), [])


if __name__ == "__main__":
    unittest.main()
