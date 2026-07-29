import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))

// PHASE 3 — the app now LIVES here. Vite's root is this directory, index.html sits beside this
// config as Vite expects, and the legacy _verify_*.js suite moved to tests/legacy/ alongside its
// baselines and screenshots.
//
// Phases 1-2 served the app in place from terrain-architect/studio so it could not drift from what
// the skill shipped while the toolchain was proven around it. That is over: main deleted that
// directory, so serving in place now points at nothing. The app moved here instead of being copied,
// which is what the no-drift rule actually wanted - one copy, in the right place.
const STUDIO = here

export default defineConfig({
  root: STUDIO,
  // Served from GitHub Pages under a subpath; a relative base keeps the artifact position-independent
  // so the same build works from `file://`, from a preview server, and from the Pages subpath.
  base: './',
  // Static assets served at the served-root, WITHOUT editing the app document. Browsers request
  // /favicon.ico by convention rather than by <link>, so serving it here silences a real 404 that
  // fires on any http origin (including Pages) while leaving index.html byte-identical, which is
  // what this phase is protecting. Phase 9 adds the PWA icon set alongside it.
  publicDir: resolve(here, 'public'),
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    fs: { allow: [STUDIO, here] },
  },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true },
  build: {
    outDir: resolve(here, 'dist'),
    emptyOutDir: true,
    target: 'es2022',
    // The app is one 495 KB document today. Keep the report honest rather than silencing it.
    chunkSizeWarningLimit: 1500,
  },
})
