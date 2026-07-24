# Legal links snippet

Copy into the package as `h5/src/legal/legalLinks.ts` (or merge the helpers).

- **Pipeline default:** `privacyUrl` / `termsUrl` = `''` → `openLegal` opens bundled overlay (branch A).
- **Post-pack:** set real `https://` Docs URLs → `openLegal` calls Bridge `openExternalUrl` (branch B).
- **Never** ship `example.com` / `TODO` / other stub URLs in source.

See `docs/H5壳Legal弹层规范.md`.
