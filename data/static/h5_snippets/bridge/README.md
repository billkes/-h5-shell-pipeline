# H5 Bridge — browser mock snippet

Canonical **browser-only** fallback for Vite DEV. Copy into each pack as:

`h5/src/bridge/browserMock.ts`

Substitute `{{APP_NAME_LOWER}}` → app name lowercased (e.g. `Monthio` → `monthio`).

## Wire in `h5/src/bridge/index.ts`

When native channel is absent, **do not** `reject('Bridge unavailable')` for media / permissions:

```ts
import { tryBrowserBridgeMock, getBrowserMockDisplayUrl, isNativeShellPresent } from './browserMock';

export function bridgeCall(action: string, payload: Record<string, unknown> = {}): Promise<unknown> {
  return new Promise((resolve, reject) => {
    // 1) postMessage to window.{appLower}Bridge / webkit.messageHandlers.{appLower}Bridge
    // 2) if no native:
    if (action === 'shellReady') {
      resolve({});
      return;
    }
    void tryBrowserBridgeMock(action, payload).then(resolve, reject);
  });
}
```

## Display URLs

In `resolvePhotoDisplayUrl` / vault helpers, before custom scheme:

```ts
import { getBrowserMockDisplayUrl, isNativeShellPresent } from '../bridge/browserMock';

const mockUrl = getBrowserMockDisplayUrl(path);
if (mockUrl) return mockUrl;
if (!isNativeShellPresent() && import.meta.env.DEV) {
  // assets/img/... → http origin (existing DEV symlink behavior)
}
```

## Rules

| Environment | Behavior |
|-------------|----------|
| Native WKWebView / Flutter | Real Bridge only — mock must not run |
| Browser Vite DEV | Mock **resolves** pick/save/record/play so UI flows continue |
| Real device Plaza | Final native verification |

- Pages still call `bridgeCall` only — no raw `<input type="file">` in views.
- File input lives **inside** `browserMock.ts` only.
- `purchase` may still reject `USER_CANCELLED` in browser (IAP is device-only).

Pipeline: `ensure_h5_vite_scaffold` copies this file into existing `h5/` trees when missing.
