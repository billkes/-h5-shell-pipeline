/**
 * Vite plugin: sync workspace * Agreement.md → h5/src/legal/*_legal_bundled.ts
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function findSyncScript(startDir) {
  let dir = path.resolve(startDir);
  for (let i = 0; i < 10; i += 1) {
    const script = path.join(dir, 'scripts', 'batch', 'sync_h5_legal_bundled.py');
    if (fs.existsSync(script)) {
      return { script, pythonpath: path.join(dir, 'scripts') };
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

function runLegalSync(workspaceRoot, h5Dir) {
  const workspace = path.resolve(workspaceRoot);
  const found = findSyncScript(h5Dir);
  if (!found) {
    console.warn('[legal-md-sync] sync_h5_legal_bundled.py not found');
    return;
  }
  try {
    execFileSync('python3', [found.script, workspace], {
      stdio: 'pipe',
      encoding: 'utf-8',
      env: { ...process.env, PYTHONPATH: found.pythonpath },
    });
  } catch (err) {
    const msg = err.stderr?.toString?.() || err.stdout?.toString?.() || String(err);
    console.warn('[legal-md-sync] sync failed:', msg.trim());
  }
}

function isLegalMd(file) {
  return /(?:Privacy Agreement|User Agreement)\.md$/i.test(file);
}

export function legalMdSyncPlugin(options = {}) {
  const h5Dir = options.h5Dir || process.cwd();
  const workspaceRoot = options.workspaceRoot || path.resolve(h5Dir, '..');

  return {
    name: 'legal-md-sync',
    buildStart() {
      runLegalSync(workspaceRoot, h5Dir);
    },
    configureServer(server) {
      runLegalSync(workspaceRoot, h5Dir);
      server.watcher.add(path.join(workspaceRoot, '* Privacy Agreement.md'));
      server.watcher.add(path.join(workspaceRoot, '* User Agreement.md'));
      server.watcher.on('change', (file) => {
        if (!isLegalMd(file)) return;
        runLegalSync(workspaceRoot, h5Dir);
        server.ws.send({ type: 'full-reload', path: '*' });
      });
    },
  };
}
