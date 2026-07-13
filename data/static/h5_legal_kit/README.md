# h5_shell Legal Modal Kit

Canonical Legal overlay for h5_shell vault bundles. Copy into `{prefix}_render.js` and `{prefix}_baseline.css`.

Replace `{prefix}` with dartCodePrefix (e.g. `paaow` → classes `c-paaow-legal-*`).

Spec: `docs/H5壳Legal弹层规范.md` · Blueprint Modal Interior Spec.

**FORBIDDEN:** `U.LEGAL[doc].replace(/\n/g, '<br>')` single-div dump.

**Scroll affordance:** bottom `mask-image` fade only — **no** `::-webkit-scrollbar { display: block }` (H5去风味 §4).
