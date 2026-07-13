type SafeAreaPayload = {
  safeTop?: number | string;
  safeBottom?: number | string;
  safe_top?: number | string;
  safe_bottom?: number | string;
};

function toPx(value: number): string {
  return Number.isFinite(value) && value > 0 ? `${value}px` : '0px';
}

export function applySafeAreaInsets(top: number, bottom: number): void {
  const root = document.documentElement;
  root.style.setProperty('--safe-top', toPx(top));
  root.style.setProperty('--safe-bottom', toPx(bottom));
}

export function applySafeArea(payload: SafeAreaPayload = {}): void {
  const top = parseFloat(String(payload.safeTop ?? payload.safe_top ?? 0));
  const bottom = parseFloat(String(payload.safeBottom ?? payload.safe_bottom ?? 0));
  applySafeAreaInsets(top, bottom);
}

export function readEnvSafeInsets(): { top: number; bottom: number } {
  const el = document.createElement('div');
  el.style.cssText =
    'position:fixed;top:0;left:0;padding:env(safe-area-inset-top) 0 env(safe-area-inset-bottom);visibility:hidden;pointer-events:none;';
  document.documentElement.appendChild(el);
  const cs = getComputedStyle(el);
  const top = parseFloat(cs.paddingTop) || 0;
  const bottom = parseFloat(cs.paddingBottom) || 0;
  el.remove();
  return { top, bottom };
}

export async function bootstrapSafeArea(
  call?: (action: string, payload?: Record<string, unknown>) => Promise<unknown>,
): Promise<void> {
  if (call) {
    try {
      const raw = (await call('getDeviceInfo', {})) as SafeAreaPayload;
      const top = parseFloat(String(raw.safeTop ?? raw.safe_top ?? 0));
      const bottom = parseFloat(String(raw.safeBottom ?? raw.safe_bottom ?? 0));
      if (top > 0 || bottom > 0) {
        applySafeAreaInsets(top, bottom);
        return;
      }
    } catch {
      /* browser-only dev */
    }
  }

  const env = readEnvSafeInsets();
  if (env.top > 0 || env.bottom > 0) {
    applySafeAreaInsets(env.top, env.bottom);
  }
}
