/**
 * Browser-only Bridge fallback (no native WKWebView / Flutter shell).
 *
 * Goal: Vite DEV in Chrome/Safari must NOT block UI or business flows when
 * pickImage / save / record / play / permissions are unavailable.
 * Real device + Plaza remains the source of truth for native capability.
 *
 * Wire from bridgeCall when no native handler:
 *   return tryBrowserBridgeMock(action, payload)
 * Never reject media actions with "Bridge unavailable" in the browser.
 *
 * Placeholders (pipeline / Agent substitute):
 *   {{APP_NAME_LOWER}} — e.g. monthio
 */

const APP_BRIDGE = '{{APP_NAME_LOWER}}Bridge';

/** path → blob:/data: URL for <img> / <audio> in browser */
const displayUrls = new Map<string, string>();
/** path → base64 (no data: prefix) for readFile mock */
const base64ByPath = new Map<string, string>();

let recordActive = false;
let mockSeq = 0;

const FIXTURE_SVG =
  'data:image/svg+xml,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">' +
      '<rect fill="#64748b" width="480" height="360"/>' +
      '<text x="240" y="180" text-anchor="middle" fill="#f8fafc" font-family="system-ui" font-size="20">' +
      'Browser mock' +
      '</text></svg>',
  );

/** Minimal silent WAV (base64) for playAudio / stopRecord preview */
const SILENT_WAV_B64 =
  'UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';

function nextPath(folder: string, ext: string): string {
  mockSeq += 1;
  return `${folder}/browser_mock_${Date.now()}_${mockSeq}.${ext}`;
}

function rememberDisplay(path: string, url: string, base64?: string): void {
  displayUrls.set(path, url);
  if (base64) base64ByPath.set(path, base64);
}

function ensureFixturePhoto(): string {
  const path = 'photos/browser_mock_fixture.svg';
  if (!displayUrls.has(path)) {
    rememberDisplay(path, FIXTURE_SVG);
  }
  return path;
}

export function isNativeShellPresent(): boolean {
  if (typeof window === 'undefined') return false;
  const w = window as Window & {
    webkit?: { messageHandlers?: Record<string, { postMessage?: unknown }> };
  };
  const injected = (window as unknown as Record<string, { postMessage?: unknown }>)[APP_BRIDGE];
  if (injected && typeof injected.postMessage === 'function') return true;
  const handler = w.webkit?.messageHandlers?.[APP_BRIDGE];
  if (handler && typeof handler.postMessage === 'function') return true;
  return false;
}

/** Use in resolvePhotoDisplayUrl / vaultAsset when !native */
export function getBrowserMockDisplayUrl(path: string): string {
  if (!path) return '';
  if (/^(https?:|data:|blob:)/i.test(path)) return path;
  const rel = path.replace(/^\/+/, '');
  return displayUrls.get(rel) || displayUrls.get(path) || '';
}

function pickFile(accept: string): Promise<File | null> {
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = accept;
    input.style.display = 'none';
    let settled = false;
    const finish = (file: File | null) => {
      if (settled) return;
      settled = true;
      input.remove();
      resolve(file);
    };
    input.addEventListener('change', () => {
      finish(input.files?.[0] ?? null);
    });
    document.body.appendChild(input);
    input.click();
    const onFocus = () => {
      window.setTimeout(() => {
        if (!settled) finish(null);
      }, 600);
    };
    window.addEventListener('focus', onFocus, { once: true });
  });
}

async function fileToBase64(file: File): Promise<string> {
  const buf = await file.arrayBuffer();
  const bytes = new Uint8Array(buf);
  let binary = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

function pickImageFile(source: string): Promise<File | null> {
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    if (source === 'camera') {
      input.setAttribute('capture', 'environment');
    }
    input.style.display = 'none';
    let settled = false;
    const finish = (file: File | null) => {
      if (settled) return;
      settled = true;
      input.remove();
      resolve(file);
    };
    input.addEventListener('change', () => {
      finish(input.files?.[0] ?? null);
    });
    document.body.appendChild(input);
    input.click();
    window.addEventListener(
      'focus',
      () => {
        window.setTimeout(() => {
          if (!settled) finish(null);
        }, 600);
      },
      { once: true },
    );
  });
}

async function mockPickImage(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  const source = String(payload.source || 'gallery');
  const file = await pickImageFile(source);
  if (file) {
    const path = nextPath('photos', file.name.split('.').pop() || 'jpg');
    const url = URL.createObjectURL(file);
    const b64 = await fileToBase64(file);
    rememberDisplay(path, url, b64);
    return { path };
  }
  const path = ensureFixturePhoto();
  return { path };
}

async function mockStartRecord(): Promise<Record<string, unknown>> {
  recordActive = true;
  return { started: true };
}

async function mockStopRecord(): Promise<Record<string, unknown>> {
  recordActive = false;
  const path = nextPath('voice', 'wav');
  const url = `data:audio/wav;base64,${SILENT_WAV_B64}`;
  rememberDisplay(path, url, SILENT_WAV_B64);
  return { path };
}

async function mockPlayAudio(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  const path = String(payload.path || '').replace(/^\/+/, '');
  const url = getBrowserMockDisplayUrl(path) || `data:audio/wav;base64,${SILENT_WAV_B64}`;
  try {
    const audio = new Audio(url);
    void audio.play().catch(() => {
      /* autoplay policies — still resolve so UI continues */
    });
  } catch {
    /* ignore */
  }
  return { playing: true, path };
}

/**
 * Resolve (never reject) common Bridge actions in the browser.
 * Unknown actions resolve `{}` so business UI is not blocked.
 */
export async function tryBrowserBridgeMock(
  action: string,
  payload: Record<string, unknown> = {},
): Promise<unknown> {
  if (typeof console !== 'undefined' && console.info) {
    console.info(`[browserBridgeMock] ${action}`, payload);
  }

  switch (action) {
    case 'shellReady':
      return {};
    case 'pickImage':
    case 'takePhoto':
      return mockPickImage(payload);
    case 'pickVideo': {
      const file = await pickFile('video/*');
      if (file) {
        const path = nextPath('videos', file.name.split('.').pop() || 'mp4');
        rememberDisplay(path, URL.createObjectURL(file));
        return { path };
      }
      return { path: nextPath('videos', 'mp4') };
    }
    case 'saveImageToAlbum':
    case 'saveImage':
      return { saved: true, ok: true };
    case 'startRecord':
      return mockStartRecord();
    case 'stopRecord':
      return mockStopRecord();
    case 'playAudio':
      return mockPlayAudio(payload);
    case 'readFile': {
      const path = String(payload.path || '').replace(/^\/+/, '');
      const b64 = base64ByPath.get(path);
      if (b64) return { base64: b64, content: b64 };
      if (path === ensureFixturePhoto() || path.endsWith('browser_mock_fixture.svg')) {
        return { base64: '', content: '' };
      }
      return { base64: SILENT_WAV_B64, content: '' };
    }
    case 'writeFile':
      return { ok: true };
    case 'ensureSeedAssets':
      ensureFixturePhoto();
      return { ok: true };
    case 'getDeviceInfo':
      return {
        safeArea: { top: 47, bottom: 34, left: 0, right: 0 },
        appVersion: '0.0.0-browser',
        locale: typeof navigator !== 'undefined' ? navigator.language : 'en',
        platform: 'browser',
      };
    case 'requestPermission':
    case 'checkPermission':
    case 'getPermission':
      return { status: 'granted', granted: true };
    case 'openExternalUrl': {
      const url = String(payload.url || '');
      if (url) window.open(url, '_blank', 'noopener,noreferrer');
      return { ok: true };
    }
    case 'copyToClipboard': {
      const text = String(payload.text || '');
      try {
        if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
      } catch {
        /* ignore */
      }
      return { copied: true };
    }
    case 'purchase':
    case 'getProducts':
      return action === 'getProducts'
        ? { products: [] }
        : Promise.reject(Object.assign(new Error('USER_CANCELLED'), { code: 'USER_CANCELLED' }));
    case 'reload':
    case 'goBack':
      return {};
    default:
      return {};
  }
}

/** @deprecated recording flag for plaza UI if needed */
export function isBrowserMockRecording(): boolean {
  return recordActive;
}
