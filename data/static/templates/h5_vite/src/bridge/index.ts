import { applySafeArea, bootstrapSafeArea } from '../lib/safeArea';

type BridgePayload = Record<string, unknown>;

type Pending = { resolve: (v: unknown) => void; reject: (e: Error) => void };

declare global {
  interface Window {
    webkit?: {
      messageHandlers?: Record<string, { postMessage: (payload: BridgePayload) => void }>;
    };
  }
}

const prefix = '{{PREFIX}}';

let callbackSeq = 0;
const pending = new Map<string, Pending>();

function parseCallbackUrl(url: string): { code: number; payload: Record<string, string> } {
  try {
    const u = new URL(url);
    const q: Record<string, string> = {};
    u.searchParams.forEach((v, k) => {
      q[k] = v;
    });
    return { code: parseInt(q.code || '0', 10), payload: q };
  } catch {
    return { code: -1, payload: {} };
  }
}

function handleCallback(url: string) {
  const { code, payload } = parseCallbackUrl(url);
  const id = payload.callbackId;
  if (!id || !pending.has(id)) return;
  const p = pending.get(id)!;
  pending.delete(id);
  if (code === 0) p.resolve(payload);
  else {
    const err = new Error(payload.message || `Bridge error ${code}`) as Error & { bridgeCode?: number };
    err.bridgeCode = code;
    p.reject(err);
  }
}

export function bridgeCall(action: string, payload: BridgePayload = {}): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const callbackId = `cb_${++callbackSeq}`;
    pending.set(callbackId, { resolve, reject });
    const body = { ...payload, action, callbackId };
    const native = (window as unknown as Record<string, { call?: (a: string, p: BridgePayload) => void }>)[
      `${prefix}Native`
    ];
    if (native?.call) {
      native.call(action, body);
      return;
    }
    const handler = window.webkit?.messageHandlers?.[prefix];
    if (handler) {
      handler.postMessage(body);
      return;
    }
    pending.delete(callbackId);
    if (action === 'shellReady') resolve({});
    else reject(new Error('Bridge unavailable'));
  });
}

function wireKitUi(prefixLower: string, ui: Record<string, unknown>): void {
  ui.applySafeArea = applySafeArea;
  const kitRoot = (window as unknown as Record<string, Record<string, unknown>>)[`${prefixLower}_kit`];
  if (kitRoot) {
    const kitUi = (kitRoot.ui = kitRoot.ui || {}) as Record<string, unknown>;
    kitUi.applySafeArea = applySafeArea;
  }
}

export function attachUiNamespace(capPrefix: string): void {
  const root = window as unknown as Record<string, Record<string, unknown>>;
  root[capPrefix] = root[capPrefix] || {};
  const ui = (root[capPrefix].ui = root[capPrefix].ui || {}) as Record<string, unknown>;
  ui.bridge = { call: bridgeCall };
  ui.bus = createBus();
  ui.router = null;
  wireKitUi(prefix, ui);
  void bootstrapSafeArea(bridgeCall);
}

type BusHandler = (data?: unknown) => void;

function createBus() {
  const handlers: Record<string, BusHandler[]> = {};
  return {
    on(event: string, fn: BusHandler) {
      (handlers[event] = handlers[event] || []).push(fn);
    },
    emit(event: string, data?: unknown) {
      (handlers[event] || []).forEach((fn) => fn(data));
    },
  };
}

export { applySafeArea, bootstrapSafeArea };
export { showSnack } from '../lib/snack';
