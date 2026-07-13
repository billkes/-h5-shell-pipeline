/** Resolve bundled vault paths and native Documents paths for <img src>. */

const MEDIA_SCHEME = 'uhfnfasset';
const MEDIA_HOST = 'local';

export function isBundledVaultPath(path: string): boolean {
  return path.startsWith('assets/') || path.startsWith('/assets/');
}

export function isNativeMediaPath(path: string): boolean {
  if (!path) return false;
  if (path.startsWith(`${MEDIA_SCHEME}://`)) return true;
  if (/^(https?:|data:|blob:)/i.test(path)) return false;
  if (isBundledVaultPath(path)) return false;
  return true;
}

/** Directory of the current HTML entry (supports /temioo/index.html subpaths). */
function pageBasePath(): string {
  const pathname = window.location.pathname.replace(/\/$/, '');
  const slash = pathname.lastIndexOf('/');
  if (slash <= 0) return '/';
  return `${pathname.slice(0, slash + 1)}`;
}

/** Resolve a bundled vault path or native Documents path for <img src>. */
export function resolveVaultAssetUrl(path: string): string {
  if (!path) return '';
  if (/^(https?:|data:|blob:)/i.test(path)) return path;
  if (path.startsWith(`${MEDIA_SCHEME}://`)) return path;
  if (isBundledVaultPath(path)) {
    const rel = path.replace(/^\//, '');
    const base = pageBasePath();
    const prefix = base.endsWith('/') ? base : `${base}/`;
    return `${window.location.origin}${prefix}${rel}`;
  }
  const rel = path.replace(/^\/+/, '');
  return `${MEDIA_SCHEME}://${MEDIA_HOST}/${rel}`;
}

export function vaultAssetPath(filename: string): string {
  return `assets/{{PREFIX}}_vault/${filename}`;
}
