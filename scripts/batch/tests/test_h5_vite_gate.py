"""Tests for h5_vite gate paths (legal UI, welcome, bundled, UX)."""

from __future__ import annotations

import json
from pathlib import Path

from batch.h5_legal_ui import verify_h5_legal_ui
from batch.skill_ux_gate import verify_skill_ux_gate
from batch.sync_h5_legal_bundled import verify_h5_legal_bundled
from batch.welcome_canon import verify_h5_welcome_canon


def _write_vite_project(root: Path) -> Path:
    project = root / "ViteApp"
    h5 = project / "h5"
    (h5 / "src" / "legal").mkdir(parents=True)
    (h5 / "src" / "styles").mkdir(parents=True)
    (h5 / "src" / "views").mkdir(parents=True)
    (project / "design-system" / "app").mkdir(parents=True)

    (project / "本包登记信息.json").write_text(
        json.dumps(
            {
                "packType": "h5_oc_shell",
                "codeAntiCorrelation": {"dartCodePrefix": "demo"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (project / "Demo Privacy Agreement.md").write_text(
        "# Demo Privacy Agreement\n\n## Children's Privacy\n\nNo collection.\n",
        encoding="utf-8",
    )
    (project / "Demo User Agreement.md").write_text(
        "# Demo User Agreement\n\n## Limitation of Liability\n\nAs-is.\n",
        encoding="utf-8",
    )
    (h5 / "package.json").write_text('{"name":"demo-h5"}', encoding="utf-8")
    (project / "design-system" / "app" / "ux-checklist.md").write_text("# ux", encoding="utf-8")

    (h5 / "src" / "legal" / "demo_legal_bundled.ts").write_text(
        'export const LEGAL = { privacy: "Children\'s Privacy\\nNo collection.", '
        'terms: "Limitation of Liability\\nAs-is." };\n',
        encoding="utf-8",
    )
    (h5 / "src" / "views" / "LegalOverlay.vue").write_text(
        """
<template>
  <div class="c-demo-dialog" style="width:min(90vw,340px);display:flex;flex-direction:column">
    <div class="c-demo-legal-header"><span class="c-demo-legal-title">T</span></div>
    <div class="c-demo-legal-scroll"></div>
  </div>
</template>
<script setup lang="ts">
import { LEGAL } from '../legal/demo_legal_bundled';
function formatLegalBody(raw: string) { return raw; }
void LEGAL;
</script>
""",
        encoding="utf-8",
    )
    (h5 / "src" / "views" / "WelcomeView.vue").write_text(
        """
<template>
  <div>
    <h1>Welcome</h1>
    <ul><li>One</li><li>Two</li></ul>
    <a @click.prevent="openLegal('privacy')">Privacy</a>
    <input v-model="checked" type="checkbox" />
    <span>I am 18 or older</span>
    <button :disabled="!checked">Continue</button>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue';
const checked = ref(false);
function openLegal(doc: string) { location.hash = '#/legal?doc=' + doc; }
</script>
""",
        encoding="utf-8",
    )
    (h5 / "src" / "styles" / "global.css").write_text(
        """
.c-demo-legal-scroll {
  mask-image: linear-gradient(to bottom, #000 calc(100% - 28px), transparent 100%);
  scrollbar-width: none;
}
.c-demo-legal-scroll::-webkit-scrollbar { display: none; }
.c-demo-tabbar__item { font-size: 11px; }
button { cursor: pointer; }
@media (prefers-reduced-motion: reduce) { * { animation: none; } }
""",
        encoding="utf-8",
    )
    return project


def test_vite_legal_ui_passes(tmp_path: Path) -> None:
    project = _write_vite_project(tmp_path)
    assert verify_h5_legal_ui(project) == []


def test_vite_welcome_canon_passes(tmp_path: Path) -> None:
    project = _write_vite_project(tmp_path)
    assert verify_h5_welcome_canon(project) == []


def test_vite_legal_bundled_skips_entry_htm(tmp_path: Path) -> None:
    project = _write_vite_project(tmp_path)
    issues = verify_h5_legal_bundled(project)
    assert not any("ENTRY:" in i for i in issues)
    assert not any("MISSING: entry htm" in i for i in issues)


def test_vite_ux_gate_allows_tabbar_micro_font(tmp_path: Path) -> None:
    project = _write_vite_project(tmp_path)
    issues = verify_skill_ux_gate(project)
    assert not any("font-size" in i for i in issues)
