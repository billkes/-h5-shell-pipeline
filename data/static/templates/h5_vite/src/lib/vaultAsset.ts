/** Resolve native bundle paths (mediaServe) and Documents paths for <img src>. */

const MEDIA_SCHEME = '{{ASSET_SCHEME}}';
const MEDIA_HOST = 'local';
const NATIVE_BUNDLE_IMG_PREFIX = 'assets/img/';
const SEED_DOC_PREFIX = 'photos/seed/';
const BRIDGE_PREFIX = '{{PREFIX}}';

export function isNativeShell(): boolean {
  if (typeof window === 'undefined') return false;
  const w = window as Window & {
    __teavooNative?: boolean;
    webkit?: { messageHandlers?: Record<string, unknown> };
  };
  return Boolean(w.__teavooNative || w.webkit?.messageHandlers?.[BRIDGE_PREFIX]);
}

export function isNativeBundleImgPath(path: string): boolean {
  return path.startsWith(NATIVE_BUNDLE_IMG_PREFIX) || path.startsWith(`/${NATIVE_BUNDLE_IMG_PREFIX}`);
}

export function isNativeMediaPath(path: string): boolean {
  if (!path) return false;
  if (path.startsWith(`${MEDIA_SCHEME}://`)) return true;
  if (/^(https?:|data:|blob:)/i.test(path)) return false;
  if (isNativeBundleImgPath(path)) return false;
  return true;
}

function normalizeVaultPath(path: string): string {
  return path
    .replace(new RegExp(`^${MEDIA_SCHEME}://local/?`, 'i'), '')
    .replace(/^\/+/, '');
}

function mimeForPath(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase();
  if (ext === 'png') return 'image/png';
  if (ext === 'webp') return 'image/webp';
  if (ext === 'gif') return 'image/gif';
  return 'image/jpeg';
}

async function readNativeFileDataUrl(path: string): Promise<string | null> {
  const { bridgeCall } = await import('../bridge');
  try {
    const res = (await bridgeCall('readFile', { path })) as { base64?: string };
    const b64 = String(res?.base64 || '').trim();
    if (!b64) return null;
    return `data:${mimeForPath(path)};base64,${b64}`;
  } catch {
    return null;
  }
}

function bundledSeedFilename(path: string): string | null {
  const rel = normalizeVaultPath(path);
  if (isNativeBundleImgPath(rel)) {
    return rel.split('/').pop() || null;
  }
  if (rel.startsWith(SEED_DOC_PREFIX)) {
    const name = rel.slice(SEED_DOC_PREFIX.length);
    return name || null;
  }
  return null;
}

async function ensureNativeSeedCopied(): Promise<void> {
  const { bridgeCall } = await import('../bridge');
  try {
    await bridgeCall('ensureSeedAssets', {});
  } catch {
    /* optional */
  }
}

/** True when URL is safe for <img src> (never use custom teavoo-asset scheme in WKWebView). */
export function isDisplayablePhotoUrl(url: string): boolean {
  if (!url) return false;
  return /^(https?:|data:|blob:)/i.test(url);
}

/** Directory of the current HTML entry (supports /temioo/index.html subpaths). */
function pageBasePath(): string {
  const pathname = window.location.pathname.replace(/\/$/, '');
  const slash = pathname.lastIndexOf('/');
  if (slash <= 0) return '/';
  return `${pathname.slice(0, slash + 1)}`;
}

/** Resolve a native bundle path or Documents path for <img src>. */
export function resolveVaultAssetUrl(path: string): string {
  if (!path) return '';
  if (/^(https?:|data:|blob:)/i.test(path)) return path;
  if (path.startsWith(`${MEDIA_SCHEME}://`)) return path;

  const rel = path.replace(/^\/+/, '');
  if (isNativeBundleImgPath(rel)) {
    if (import.meta.env.DEV) {
      const base = pageBasePath();
      const prefix = base.endsWith('/') ? base : `${base}/`;
      return `${window.location.origin}${prefix}${rel}`;
    }
    return `${MEDIA_SCHEME}://${MEDIA_HOST}/${rel}`;
  }

  return `${MEDIA_SCHEME}://${MEDIA_HOST}/${rel}`;
}

/** Reliable preview URL for picked photos and bundled seed rasters in Native shell. */
export async function resolvePhotoDisplayUrl(path: string): Promise<string> {
  if (!path) return '';
  if (/^(https?:|data:|blob:)/i.test(path)) return path;

  const rel = normalizeVaultPath(path);

  if (isNativeBundleImgPath(rel) && import.meta.env.DEV) {
    return resolveVaultAssetUrl(rel);
  }

  if (isNativeShell()) {
    const seedFilename = bundledSeedFilename(rel);

    if (seedFilename) {
      await ensureNativeSeedCopied();
      if (rel.startsWith(SEED_DOC_PREFIX)) {
        const docUrl = await readNativeFileDataUrl(rel);
        if (docUrl) return docUrl;
      }
      const seedRel = `${SEED_DOC_PREFIX}${seedFilename}`;
      const copied = await readNativeFileDataUrl(seedRel);
      if (copied) return copied;
    }

    const direct = await readNativeFileDataUrl(rel);
    if (direct) return direct;

    if (seedFilename) {
      const byName = await readNativeFileDataUrl(seedFilename);
      if (byName) return byName;
      const vaultRel = `${NATIVE_BUNDLE_IMG_PREFIX}${seedFilename}`;
      const fromVault = await readNativeFileDataUrl(vaultRel);
      if (fromVault) return fromVault;
    }

    return '';
  }

  return resolveVaultAssetUrl(path);
}

/** Seed / export raster paths — logical URL prefix; OC/Swift on-disk files live in ios/{AppName}/SeedBundle/. */
export function vaultAssetPath(filename: string): string {
  return `${NATIVE_BUNDLE_IMG_PREFIX}${filename}`;
}
