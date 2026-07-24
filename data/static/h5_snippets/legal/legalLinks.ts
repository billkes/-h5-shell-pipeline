/**
 * Legal link config — pipeline ships empty strings (branch A = bundled overlay).
 * After pack, fill real https:// Privacy / Terms URLs to enable Bridge openExternalUrl (branch B).
 * NEVER put placeholder / example / TODO URLs here.
 */
export const legalLinks = {
  privacyUrl: '',
  termsUrl: '',
} as const

const FAKE_URL_RE =
  /example\.com|example\.org|localhost|127\.0\.0\.1|TODO|placeholder|your[-_]?link|changeme/i

/** True only for a real non-empty https URL that is not an obvious stub. */
export function isExternalLegalUrl(url: unknown): url is string {
  if (typeof url !== 'string') return false
  const u = url.trim()
  if (!u) return false
  if (!/^https:\/\//i.test(u)) return false
  if (u === 'https://' || FAKE_URL_RE.test(u)) return false
  return true
}

/**
 * Unified entry — call from Welcome / Settings.
 * Implement `openLegalOverlay` and `bridgeCall` in the app.
 *
 * async function openLegal(kind: 'privacy' | 'terms') {
 *   const url = kind === 'privacy' ? legalLinks.privacyUrl : legalLinks.termsUrl
 *   if (isExternalLegalUrl(url)) {
 *     await bridgeCall('openExternalUrl', { url })
 *     return
 *   }
 *   openLegalOverlay(kind)
 * }
 */
