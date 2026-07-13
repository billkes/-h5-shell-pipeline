# {{APP_NAME}} H5 — Vite source tree

Business UI is implemented under `h5/src/`. The pipeline compiles it to a deployable monolith:

```bash
cd h5
npm install
npm run dev          # http://127.0.0.1:5174 — local dev (shell h5EntryUrlDev)
npm run build:deploy # → ../h5_site/{{PREFIX}}_entry.htm
```

- **Do not** hand-edit `h5_site/{{PREFIX}}_entry.htm` — it is build output.
- Legal strings: `sync_h5_legal_bundled.py` → `src/legal/{{PREFIX}}_legal_bundled.ts`
- Kit namespace: `window.{{PREFIX_CAP}}.ui.*` (wired in `src/main.ts`)
