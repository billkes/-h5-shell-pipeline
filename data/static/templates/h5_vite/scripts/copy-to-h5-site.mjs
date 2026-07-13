#!/usr/bin/env node
/** Copy Vite singlefile build + bundled vault assets → h5_site/{appSlug}/ */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const slug = (process.env.H5_APP_SLUG || '{{APP_SLUG}}').trim().toLowerCase();
const prefix = (process.env.H5_PREFIX || '{{PREFIX}}').trim().toLowerCase();
const entry = (process.env.H5_SITE_ENTRY || 'index.html').trim();
const root = path.resolve(__dirname, '..');
const src = path.join(root, 'dist', 'index.html');
const siteDir = path.join(root, '..', 'h5_site', slug);
const dest = path.join(siteDir, entry);

function copyDirRecursive(srcDir, destDir) {
  if (!fs.existsSync(srcDir)) return 0;
  fs.mkdirSync(destDir, { recursive: true });
  let count = 0;
  for (const name of fs.readdirSync(srcDir)) {
    const from = path.join(srcDir, name);
    const to = path.join(destDir, name);
    const stat = fs.statSync(from);
    if (stat.isDirectory()) {
      count += copyDirRecursive(from, to);
    } else {
      fs.copyFileSync(from, to);
      count += 1;
    }
  }
  return count;
}

if (!fs.existsSync(src)) {
  console.error(`Missing build output: ${src}`);
  process.exit(1);
}

fs.mkdirSync(path.dirname(dest), { recursive: true });
fs.copyFileSync(src, dest);
console.log(`Deployed ${src} → ${dest}`);

const vaultSrc = path.join(root, 'assets', `${prefix}_vault`);
const vaultDest = path.join(siteDir, 'assets', `${prefix}_vault`);
const copied = copyDirRecursive(vaultSrc, vaultDest);
if (copied > 0) {
  console.log(`Deployed ${copied} vault asset(s) → ${vaultDest}`);
} else {
  console.warn(`WARN: no vault assets at ${vaultSrc}`);
}
