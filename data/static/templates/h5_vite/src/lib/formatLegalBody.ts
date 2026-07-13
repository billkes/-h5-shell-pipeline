/** Legal modal body formatter — mirrors data/static/h5_legal_kit/legal_render.js.snippet */

export function escapeHtml(text: string): string {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function isLegalSectionHeading(block: string): boolean {
  if (!block || block.length > 72) return false;
  if (/^Latest Updated:/i.test(block)) return false;
  if (/\.\s+[A-Z]/.test(block)) return false;
  if (block.length > 48 && block.indexOf('.') > 0) return false;
  return /^[A-Z]/.test(block);
}

export type LegalFormatted = { title: string; bodyHtml: string };

export function formatLegalBody(raw: string, prefix: string): LegalFormatted {
  const lines = String(raw || '').split('\n');
  const title = (lines[0] || '').trim();
  let i = 1;
  while (i < lines.length && !lines[i].trim()) i += 1;

  let meta = '';
  if (i < lines.length && /^Latest Updated:/i.test(lines[i].trim())) {
    meta = lines[i].trim();
    i += 1;
  }

  const blocks: string[] = [];
  let current: string[] = [];
  for (; i < lines.length; i += 1) {
    const line = lines[i].trim();
    if (!line) {
      if (current.length) {
        blocks.push(current.join(' '));
        current = [];
      }
      continue;
    }
    current.push(line);
  }
  if (current.length) blocks.push(current.join(' '));

  const sectionClass = `c-${prefix}-legal-section`;
  const paraClass = `c-${prefix}-legal-para`;
  const metaClass = `c-${prefix}-legal-meta`;

  let bodyHtml = '';
  if (meta) {
    bodyHtml += `<p class="${metaClass}">${escapeHtml(meta)}</p>`;
  }
  for (const block of blocks) {
    if (isLegalSectionHeading(block)) {
      bodyHtml += `<h2 class="${sectionClass}">${escapeHtml(block)}</h2>`;
    } else {
      bodyHtml += `<p class="${paraClass}">${escapeHtml(block)}</p>`;
    }
  }
  return { title, bodyHtml };
}
