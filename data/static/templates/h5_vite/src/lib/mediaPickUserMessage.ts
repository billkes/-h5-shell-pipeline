export type MediaBridgeError = Error & { bridgeCode?: number };

export function mediaPickUserMessage(err: unknown): string | null {
  const code = (err as MediaBridgeError)?.bridgeCode;
  const raw = err instanceof Error ? err.message.trim() : String(err || '').trim();

  if (code === -2 || raw === 'USER_CANCELLED' || /\bcancel/i.test(raw)) {
    return null;
  }

  switch (raw) {
    case 'PERMISSION_DENIED':
      return 'Photo access denied. Enable Camera or Photos in Settings.';
    case 'Camera unavailable':
      return "Camera isn't available on this device.";
    case 'Bridge unavailable':
      return 'Photo picker requires the app shell.';
    default:
      break;
  }

  if (/permission/i.test(raw)) {
    return 'Photo access denied. Enable Camera or Photos in Settings.';
  }

  return 'Could not attach photo. Try again.';
}
