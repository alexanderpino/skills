import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))

// PHASE 1 — the app is served IN PLACE from the skill tree, not copied.
//
// `root` points straight at terrain-architect/studio, so `npm run dev` serves exactly the file the
// skill ships and the file every legacy _verify_*.js script loads. A copy would be free to drift
// from its original the moment either side is edited, and the whole point of this phase is that the
// application is byte-for-byte unchanged while the toolchain is proven around it. The digest gate
// (`_verify_digest.js`) is what asserts that; a copy would make it assert nothing.
//
// From Phase 3 this flips: `root` moves to this directory, `src/` becomes the real source, and
// terrain-architect/studio/index.html becomes a GENERATED single-file build committed back into the
// skill tree — which is what keeps the skill installable and keeps `file://` working.
const STUDIO = resolve(here, '../../terrain-architect/studio')

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
