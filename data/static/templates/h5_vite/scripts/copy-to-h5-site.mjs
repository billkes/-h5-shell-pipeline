#!/usr/bin/env node
/** Copy Vite singlefile build → h5_site/{appSlug}/ (monolith only; raster in Native bundle). */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const slug = (process.env.H5_APP_SLUG || '{{APP_SLUG}}').trim().toLowerCase();
const entry = (process.env.H5_SITE_ENTRY || 'index.html').trim();
const root = path.resolve(__dirname, '..');
const src = path.join(root, 'dist', 'index.html');
const siteDir = path.join(root, '..', 'h5_site', slug);
const dest = path.join(siteDir, entry);

if (!fs.existsSync(src)) {
  console.error(`Missing build output: ${src}`);
  process.exit(1);
}

fs.mkdirSync(path.dirname(dest), { recursive: true });
fs.copyFileSync(src, dest);
console.log(`Deployed ${src} → ${dest}`);
