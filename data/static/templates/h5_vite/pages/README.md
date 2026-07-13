# Tab-root page scaffolds (section composer)

**Source of truth:** `sections/` fragment library + `TAB_ROOT_BLUEPRINT` in `scripts/batch/h5_page_sections.py`.

Legacy monolith templates under `pages/hub.T4_wizard.vue.tpl` etc. are **deprecated** — kept for reference only; `sync_h5_page_scaffold` composes from sections.

## Architecture

```
skill_pages.H5_PAGE_SPECS  →  TAB_ROOT_BLUEPRINT (section ids)
sections/vue/*.vue.frag    →  composed into HubView / RunsView / SettingsView
sections/css/*.css.frag    →  union → global.css PAGE-SCAFFOLD block
sections/scripts/*.script.tpl → logic hook imports per page type
```

## Adding a tab-root page

1. Extend `H5_PAGE_SPECS` in `skill_pages.py` (prose for Agent).
2. Add section ids to `TAB_ROOT_BLUEPRINT[page_type]` in `h5_page_sections.py`.
3. Add matching `sections/vue/{id}.vue.frag` (+ optional `sections/css/*.css.frag`).
4. Extend `SPEC_REQUIRED_MARKERS` + `verify_tab_root_blueprint()` test guard.
5. Add `sections/scripts/{page_type}.script.tpl` if new logic hook name.

**Do not** add another 160-line monolith `.vue.tpl`.

## Sync

- `sync_h5_page_scaffold(project)` — `lock.dimensions` + `dev.h5.build`
- Agent writes `*View.logic.ts` only
