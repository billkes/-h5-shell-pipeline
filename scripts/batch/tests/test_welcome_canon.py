"""Tests for welcome_canon H5 audits — static dump + step logic."""

from __future__ import annotations

import json
from pathlib import Path

from batch.welcome_canon import verify_h5_welcome_canon


def _write_welcome_project(root: Path, welcome_vue: str, *, with_context: bool = True) -> Path:
    project = root / "MonthioLike"
    h5 = project / "h5"
    (h5 / "src" / "views").mkdir(parents=True)
    (h5 / "src" / "styles").mkdir(parents=True)
    (h5 / "src" / "router").mkdir(parents=True)
    (project / "design-system" / "app").mkdir(parents=True)

    (project / "本包登记信息.json").write_text(
        json.dumps({"packType": "h5_swift_shell", "codeAntiCorrelation": {"dartCodePrefix": "demo"}}),
        encoding="utf-8",
    )
    (project / "功能文档.md").write_text(
        "## Screen Inventory\n\n| Route | Screen |\n| --- | --- |\n| #/welcome | Welcome Gate |\n",
        encoding="utf-8",
    )
    (h5 / "package.json").write_text('{"name":"demo-h5"}', encoding="utf-8")
    (h5 / "src" / "router" / "index.ts").write_text(
        "{ path: '/welcome', name: 'welcome', meta: { scene: 'welcome' } },\n",
        encoding="utf-8",
    )
    (h5 / "src" / "styles" / "global.css").write_text(
        """
/* THEME:pipeline — auto-synced; do not hand-edit */
:root {
  --demo-bg: #F5F5F7;
  --demo-fg: #0F172A;
  --demo-background: #F5F5F7;
  --demo-foreground: #0F172A;
  --demo-on-primary: #FFFFFF;
  --demo-on-ambient: #F8FAFC;
}
@media (prefers-color-scheme: dark) {
  :root {
    --demo-bg: #020617;
    --demo-fg: #F8FAFC;
    --demo-background: #020617;
    --demo-foreground: #F8FAFC;
    --demo-on-primary: #FFFFFF;
    --demo-on-ambient: #F8FAFC;
  }
}
/* THEME:end */
""",
        encoding="utf-8",
    )
    (h5 / "src" / "views" / "WelcomeView.vue").write_text(welcome_vue, encoding="utf-8")
    if with_context:
        (project / "skill-input").mkdir(parents=True)
        (project / "skill-input" / "context.json").write_text(
            json.dumps(
                {
                    "product": {
                        "coreScene": "month-end habit review",
                        "audience": "self-improvers",
                    }
                }
            ),
            encoding="utf-8",
        )
    return project


_MONTHIO_SKELETON = """
<template>
  <div class="page-full">
    <div class="c-demo-welcome-hex" />
    <h1 class="c-demo-welcome-title">Close the month with clarity</h1>
    <div class="welcome-step c-demo-welcome-steps">
      <p class="c-demo-welcome-beat welcome-step">Pain beat one.</p>
      <p class="c-demo-welcome-beat welcome-step">Value beat two.</p>
      <p class="c-demo-welcome-beat welcome-step">Trust beat three.</p>
    </div>
    <ul class="c-demo-welcome-trust welcome-trust">
      <li>Local-only data</li>
      <li>Month-end review</li>
    </ul>
    <label><input v-model="ageChecked" type="checkbox" /><span>I am 18 years or older</span></label>
    <label><input v-model="policyChecked" type="checkbox" />
      <span><a href="#" @click.prevent="openLegal('privacy')">Privacy Agreement</a></span></label>
    <button :disabled="!(ageChecked && policyChecked)">Continue</button>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue';
const ageChecked = ref(false);
const policyChecked = ref(false);
function openLegal(doc: string) { void doc; }
</script>
<style scoped>
.c-demo-welcome-title { animation: demo-fade 0.2s ease; }
@keyframes demo-fade { from { opacity: 0; } to { opacity: 1; } }
</style>
"""


def test_welcome_canon_rejects_static_beat_dump(tmp_path: Path) -> None:
    project = _write_welcome_project(tmp_path, _MONTHIO_SKELETON)
    issues = verify_h5_welcome_canon(project)
    assert any("一屏堆叠" in i for i in issues)
    assert any("引导结构" in i for i in issues)


def test_welcome_canon_accepts_stepped_narrative(tmp_path: Path) -> None:
    stepped = _MONTHIO_SKELETON.replace(
        '<div class="welcome-step c-demo-welcome-steps">',
        '<div class="c-demo-welcome-steps">',
    ).replace(
        '<p class="c-demo-welcome-beat welcome-step">Pain beat one.</p>',
        '<p v-if="currentStep === 0" class="c-demo-welcome-beat">Pain beat one.</p>',
    ).replace(
        '<p class="c-demo-welcome-beat welcome-step">Value beat two.</p>',
        '<p v-if="currentStep === 1" class="c-demo-welcome-beat">Value beat two.</p>',
    ).replace(
        '<p class="c-demo-welcome-beat welcome-step">Trust beat three.</p>',
        '<p v-if="currentStep === 2" class="c-demo-welcome-beat">Trust beat three.</p>',
    ).replace(
        '<ul class="c-demo-welcome-trust welcome-trust">',
        '<ul v-if="currentStep === 3" class="c-demo-welcome-trust welcome-trust">',
    ).replace(
        "const ageChecked = ref(false);",
        "const currentStep = ref(0);\nconst ageChecked = ref(false);",
    )
    project = _write_welcome_project(tmp_path, stepped)
    issues = verify_h5_welcome_canon(project)
    assert not any("一屏堆叠" in i for i in issues)
    assert not any("引导结构" in i for i in issues)
