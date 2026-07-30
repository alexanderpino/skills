// Run the legacy _verify_*.js suite against a real HTTP origin.
//
// The suite defaults to file://, which is right today and wrong from Phase 3 onward: once the app is
// an ES-module bundle, file:// cannot load it (module scripts are fetched with CORS semantics and a
// file:// origin is opaque, so the page comes up blank). This starts the dev server, points the suite
// at it via STUDIO_URL, and shuts the server down again — so "does it still pass when served?" is one
// command instead of a three-terminal ritual.
//
//   npm run verify                  whole suite over http
//   npm run verify -- --file        whole suite over file:// (no server)
//   npm run verify -- _verify_canyon_slopes.js
//   npm run verify -- --preview     against the BUILT bundle (--mode test: keeps the test bridge)
//   npm run verify -- --preview-prod  against a PRODUCTION build (service worker on, no bridge)
//                                    _verify_pwa.js is the only oracle that needs this
import { spawn, spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { existsSync } from 'node:fs'

const here = dirname(fileURLToPath(import.meta.url))
const app = resolve(here, '..')
const studio = resolve(app, 'tests/legacy')   // the legacy suite moved here with the app

const argv = process.argv.slice(2)
const useFile = argv.includes('--file')
const usePreviewProd = argv.includes('--preview-prod')
// --preview-prod implies a preview server; it differs only in the build mode below.
const usePreview = argv.includes('--preview') || usePreviewProd
const targets = argv.filter((a) => !a.startsWith('--'))
const script = targets[0] ?? '_verify_all_canyon.js'

// Flags this launcher consumes itself. EVERYTHING ELSE IS FORWARDED to the oracle, because several
// of them take their own and until now had no way to receive one: _verify_digest documents
// `--write` to re-bless the baseline and `--res=512`, and since A1 removed --file this launcher is
// the only way to reach the app at all. So the digest's own re-bless path was unreachable - the
// flag was silently swallowed here and the run compared instead of writing, reporting a FAIL that
// looked exactly like a real regression. A dropped flag is worse than a rejected one.
const OWN = new Set(['--file', '--preview', '--preview-prod'])
const forward = argv.filter((a) => a.startsWith('--') && !OWN.has(a.split('=')[0]))

if (!existsSync(resolve(studio, script))) {
  console.error(`No such verification script: ${script}`)
  process.exit(2)
}

const run = (env) => {
  const r = spawnSync(process.execPath, [script, ...forward], { cwd: studio, stdio: 'inherit', env })
  return r.status ?? 1
}

if (useFile) {
  console.log(`\n${script} over file://\n`)
  process.exit(run(process.env))
}

const port = usePreview ? 4173 : 5173
const url = `http://127.0.0.1:${port}/index.html`

if (usePreview) {
  // --mode test, NOT a plain production build. The test bridge in src/legacy.js is wrapped in
  // `if (import.meta.env && (import.meta.env.DEV || import.meta.env.MODE === "test"))`, and Vite
  // statically eliminates that whole block when MODE is "production". A production preview
  // therefore serves an app with NO bridge, and the suite does not fail cleanly against it:
  // every bare `RES = 192` writes a plain property nothing reads, and `gl` stops resolving to the
  // WebGL context and starts resolving to the CANVAS ELEMENT, because the element's id is "gl" and
  // the HTML parser publishes ids on window. The result is a wall of assertion failures that look
  // like terrain regressions and are a stripped bridge.
  //
  // `--mode test` keeps the bridge and still exercises the real bundle - minified, hashed asset
  // names, module preloads - which is the point of testing against the build at all.
  // --preview-prod builds PRODUCTION: no test bridge, but the service worker IS registered.
  // _verify_pwa.js needs exactly that and nothing else does, because the registration is gated
  // on import.meta.env.MODE === 'production' precisely to keep the oracle suite worker-free.
  const mode = usePreviewProd ? [] : ['--mode', 'test']
  console.log(usePreviewProd
    ? 'Building bundle (PRODUCTION - service worker active, NO test bridge)...'
    : 'Building bundle (--mode test, so the bridge survives)...')
  const b = spawnSync('npx', ['vite', 'build', ...mode], { cwd: app, stdio: 'inherit', shell: true })
  if (b.status !== 0) process.exit(b.status ?? 1)
}

// Reuse a server that is already serving this app rather than failing on --strictPort. Playwright's
// webServer binds the same port, so running `npm run test:e2e` and `npm run verify` back to back
// would otherwise race: the second one cannot bind, every page load fails, and the suite reports a
// wall of assertion failures that look like terrain regressions but are a port collision. Mirrors
// Playwright's own `reuseExistingServer`.
const alreadyServing = await fetch(url, { method: 'HEAD' })
  .then((r) => r.ok)
  .catch(() => false)

const server = alreadyServing
  ? null
  : spawn('npx', ['vite', usePreview ? 'preview' : '', '--port', String(port), '--strictPort']
      .filter(Boolean), { cwd: app, stdio: 'ignore', shell: true, detached: false })

if (alreadyServing) console.log(`Reusing the server already answering at ${url}`)

let stopped = false
const stop = () => {
  if (stopped || !server) return   // never tear down a server we did not start
  stopped = true
  // Vite spawns through a shell on Windows, so killing the shell alone can orphan the server and
  // hold the port. Kill the tree.
  if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(server.pid), '/t', '/f'], { stdio: 'ignore' })
  else try { process.kill(-server.pid, 'SIGTERM') } catch { server.kill('SIGTERM') }
}
process.on('exit', stop)
process.on('SIGINT', () => { stop(); process.exit(130) })

const ready = async () => {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(url, { method: 'HEAD' })
      if (r.ok) return true
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 500))
  }
  return false
}

if (!(await ready())) {
  console.error(`Server did not come up at ${url} within 30s.`)
  stop()
  process.exit(1)
}

console.log(`\n${script} over ${url}\n`)
const status = run({ ...process.env, STUDIO_URL: url })
stop()
process.exit(status)
