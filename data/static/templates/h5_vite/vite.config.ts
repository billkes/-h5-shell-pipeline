import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { viteSingleFile } from 'vite-plugin-singlefile';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { legalMdSyncPlugin } from './legal-md-sync.plugin.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Bundled vault JPEGs live in h5/assets/{prefix}_vault/ and are symlinked to public/assets/ for dev/preview. */

export default defineConfig({
  plugins: [
    legalMdSyncPlugin({ h5Dir: __dirname, workspaceRoot: path.resolve(__dirname, '..') }),
    vue(),
    viteSingleFile(),
  ],
  build: {
    target: 'es2018',
    cssCodeSplit: false,
    assetsInlineLimit: 100_000_000,
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
  server: {
    host: true,
    port: 5174,
    strictPort: true,
  },
  preview: {
    host: true,
    port: 5174,
    strictPort: true,
  },
});
