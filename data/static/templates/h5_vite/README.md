# {{APP_NAME}} H5 — Vite source tree

Business UI is implemented under `h5/src/`. The pipeline compiles it to a deployable monolith:

```bash
cd h5
npm install
npm run dev          # LAN: http://<your-ip>:5174 (also shown as Network URL)
npm run build:deploy # → ../h5_site/{{PREFIX}}_entry.htm
```

- **Do not** hand-edit `h5_site/{{PREFIX}}_entry.htm` — it is build output.
- Legal strings: edit `../* Privacy Agreement.md` / `../* User Agreement.md` at workspace root; `npm run dev` auto-syncs via `legal-md-sync.plugin.mjs` → `src/legal/{{PREFIX}}_legal_bundled.ts` (or run `sync_h5_legal_bundled.py` manually)
- Kit namespace: `window.{{PREFIX_CAP}}.ui.*` (wired in `src/main.ts`)
- **Media attach**: `src/components/MediaSourceSheet.vue` + `src/lib/pickImage.ts` — camera/photo sheet before `pickImage` Bridge (see phase_h5_implementer §13)
