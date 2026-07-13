/** Visible H5 UI must stay English regardless of device locale. */
export const H5_UI_LOCALE = 'en-US';

export function formatShortDate(value: number | Date): string {
  const d = value instanceof Date ? value : new Date(value);
  return d.toLocaleDateString(H5_UI_LOCALE, { month: 'short', day: 'numeric' });
}

export function formatShortDateTime(value: number | Date): string {
  const d = value instanceof Date ? value : new Date(value);
  return d.toLocaleString(H5_UI_LOCALE, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
