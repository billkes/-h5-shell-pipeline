type BridgePayload = Record<string, unknown>;

declare global {
  interface Window {
    webkit?: {
      messageHandlers?: Record<string, { postMessage: (payload: BridgePayload) => void }>;
    };
  }
}

const prefix = '{{PREFIX}}';

export function bridgeCall(action: string, payload: BridgePayload = {}): void {
  const body = { ...payload, action };
  const native = (window as unknown as Record<string, { call?: (a: string, p: BridgePayload) => void }>)[
    `${prefix}Native`
  ];
  if (native?.call) {
    native.call(action, body);
    return;
  }
  const handler = window.webkit?.messageHandlers?.[prefix];
  handler?.postMessage(body);
}

export function attachUiNamespace(capPrefix: string): void {
  const root = window as unknown as Record<string, Record<string, unknown>>;
  root[capPrefix] = root[capPrefix] || {};
  const ui = (root[capPrefix].ui = root[capPrefix].ui || {}) as Record<string, unknown>;
  ui.bridge = { call: bridgeCall };
  ui.bus = createBus();
  ui.router = null;
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
