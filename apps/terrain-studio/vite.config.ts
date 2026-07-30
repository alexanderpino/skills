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
  plugins: [
    // Inject the precache list and cache version into public/sw.js AFTER the bundle exists.
    //
    // The worker cannot know its own precache list: asset names are content-hashed, so they are
    // only decided during the build. publicDir copies sw.js verbatim, which is what keeps its URL
    // stable (a hashed worker filename would look like a new worker every build and break the
    // update model) - so the file is rewritten in place in the output, not at its source.
    //
    // VERSION is derived from the emitted asset names rather than from a timestamp or the git SHA.
    // A timestamp makes every build a "new" version even when the bytes are identical, which
    // needlessly evicts a warm cache; the hash of the file list changes exactly when the output
    // does, which is the property the activate handler's cache-eviction relies on.
    {
      name: 'terrain-studio-sw-precache',
      apply: 'build',
      async generateBundle(_options, bundle) {
        const names = Object.keys(bundle).filter((n) => n !== 'sw.js').sort()
        const assets = ['index.html', ...names.filter((n) => n !== 'index.html')]
        const { createHash } = await import('node:crypto')
        const version = createHash('sha256').update(assets.join('\n')).digest('hex').slice(0, 12)

        const { readFileSync } = await import('node:fs')
        const swSrc = readFileSync(resolve(here, 'public/sw.js'), 'utf8')
        const filled = swSrc
          .replaceAll("'__VERSION__'", JSON.stringify(version))
          .replaceAll('__PRECACHE__', JSON.stringify(assets.map((a) => './' + a), null, 2))

        // Assert the placeholders were actually consumed. A silently un-substituted worker parses
        // fine (`__PRECACHE__` is just an undeclared identifier) and then throws at install time,
        // in a context most people never look at - so the PWA would appear to work until it was
        // needed offline.
        if (filled.includes('__PRECACHE__') || filled.includes('__VERSION__')) {
          this.error('sw.js placeholders were not substituted - refusing to emit a broken worker')
        }
        this.emitFile({ type: 'asset', fileName: 'sw.js', source: filled })
      },
    },
  ],
  build: {
    outDir: resolve(here, 'dist'),
    emptyOutDir: true,
    target: 'es2022',
    // The app is one 495 KB document today. Keep the report honest rather than silencing it.
    chunkSizeWarningLimit: 1500,
  },
})
