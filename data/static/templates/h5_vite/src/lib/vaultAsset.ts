/** Resolve native bundle paths (mediaServe) and Documents paths for <img src>. */

const MEDIA_SCHEME = '{{PREFIX}}asset';
const MEDIA_HOST = 'local';
const NATIVE_BUNDLE_IMG_PREFIX = 'assets/img/';

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

/** Seed / export raster paths under Native app bundle (OC/Swift mediaServe). */
export function vaultAssetPath(filename: string): string {
  return `${NATIVE_BUNDLE_IMG_PREFIX}${filename}`;
}
