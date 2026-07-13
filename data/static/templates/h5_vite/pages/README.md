# H5 tab-root page scaffolds

Pipeline-owned Vue templates for **Hub / Runs / Settings** tab roots.

## Topology mapping

| page | T4_wizard | default |
|------|-----------|---------|
| hub | `hub.T4_wizard.vue.tpl` | same |
| list | `list.T4_wizard.vue.tpl` | same |
| settings | `settings.default.vue.tpl` | same |

## Sync

- `sync_h5_page_scaffold(project)` — runs at `lock.dimensions` (before Agent) and `dev.h5.build` (re-sync).
- Overwrites tab-root `*View.vue` `<template>` + script imports.
- Agent implements `*View.logic.ts` only (never overwritten by sync).
- Styles: `styles/page-scaffold.css.tpl` → `global.css` `PAGE-SCAFFOLD:pipeline` block.

## Agent scope

| Pipeline | Agent |
|----------|-------|
| Hub/Runs/Settings template | `*View.logic.ts` |
| Wizard / Live / Export / Detail | full Vue |
