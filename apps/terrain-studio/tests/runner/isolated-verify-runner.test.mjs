import assert from 'node:assert/strict'
import { spawn, spawnSync } from 'node:child_process'
import { createServer as createHttpServer } from 'node:http'
import { mkdir, mkdtemp, readFile, readdir, rm, stat, symlink, writeFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'
import { CACHE_SCHEMA, CacheError, createBuildKey, ensureBuild } from '../../scripts/build-cache.mjs'
import {
  PLAYWRIGHT_PATH_RESERVE, VerifyError, classifyOracle, ownedProcessTree, queryWindowsProcesses, queryWindowsProcessesWithRetry,
  runBatch, runModePartitions, runWorker,
  windowsTerminationTargets,
} from '../../scripts/isolated-verify-runner.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const appDir = resolve(here, '../..')
const require = createRequire(import.meta.url)
const roots = []
const makeRoot = async prefix => { const root = await mkdtemp(join(tmpdir(), prefix)); roots.push(root); return root }
test.after(async () => Promise.all(roots.map(root => rm(root, { recursive: true, force: true }))))

async function fixtureApp() {
  const root = await makeRoot('studio-runner-fixture-')
  const app = join(root, 'apps', 'fixture')
  await mkdir(join(app, 'src'), { recursive: true })
  await mkdir(join(app, 'public'))
  await writeFile(join(root, 'package-lock.json'), '{}\n')
  await writeFile(join(app, 'package.json'), '{"type":"module"}\n')
  await writeFile(join(app, 'vite.config.ts'), 'export default {}\n')
  await writeFile(join(app, 'index.html'), '<main>fixture</main><script type="module" src="/src/main.js"></script>\n')
  await writeFile(join(app, 'src', 'main.js'), 'console.log("fixture")\n')
  await writeFile(join(app, 'public', 'asset.txt'), 'asset-one\n')
  return { app }
}

async function oracle(root, name = 'case.cjs', source = 'console.log("fixture evidence")\n') {
  const path = join(root, name)
  await writeFile(path, source)
  return path
}

test('empty and duplicate inventories are structured red', async () => {
  await assert.rejects(runWorker({ appDir, mode: 'source', cases: [] }), error => error.code === 'EMPTY_INVENTORY')
  const path = await oracle(await makeRoot('studio-oracle-'))
  await assert.rejects(runWorker({ appDir, mode: 'source', cases: [{ name: 'x', path }, { name: 'x', path }] }),
    error => error.code === 'DUPLICATE_DECLARATION')
})

test('stale selected root fails before server or case launch', async () => {
  const selectedRoot = await makeRoot('studio-stale-')
  await writeFile(join(selectedRoot, 'sentinel'), 'keep')
  const path = await oracle(await makeRoot('studio-oracle-'))
  await assert.rejects(runWorker({ appDir, mode: 'source', cases: [{ name: 'x', path }], selectedRoot }),
    error => error.code === 'STALE_PROFILE')
  assert.equal(await readFile(join(selectedRoot, 'sentinel'), 'utf8'), 'keep')
})

test('deep Windows temporary root shortens privately before Playwright launch', { skip: process.platform !== 'win32' }, async () => {
  const deepRoot = join(await makeRoot('studio-deep-root-'), ...Array.from({ length: 12 }, (_, index) => `integration-segment-${index.toString().padStart(2, '0')}`))
  const playwrightPath = require.resolve('playwright')
  const path = await oracle(await makeRoot('studio-playwright-path-'), 'playwright-path.cjs', `
const { statSync } = require('node:fs')
const { chromium } = require(${JSON.stringify(playwrightPath)})
;(async () => {
  if (!statSync(process.env.TEMP).isDirectory()) throw new Error('private TEMP missing')
  if (!statSync(process.env.STUDIO_VERIFY_PROFILE).isDirectory()) throw new Error('private profile missing')
  const browser = await chromium.launch({ headless: true })
  console.log('playwright path evidence', process.env.TEMP, process.env.STUDIO_VERIFY_PROFILE)
  await browser.close()
})().catch(error => { console.error(error); process.exitCode = 1 })
`)
  const result = await runWorker({ appDir, mode: 'file', temporaryRoot: deepRoot, cases: [{ name: 'playwright-path', path }] })
  assert.equal(result.completed, 1)
  assert.equal(result.worker.root.startsWith(resolve(deepRoot)), false)
  assert.equal(result.worker.temp.startsWith(result.worker.tokenRoot), true)
  assert.equal(result.worker.profile.startsWith(result.worker.tokenRoot), true)
  assert.notEqual(result.worker.temp, result.worker.profile)
  assert.equal(result.worker.temp.length + PLAYWRIGHT_PATH_RESERVE <= 259, true)
  assert.equal(result.worker.profile.length + PLAYWRIGHT_PATH_RESERVE <= 259, true)
  assert.equal(result.rows[0].outputBytes > 0, true)
})

test('occupied strict port is PORT_COLLISION and foreign server survives', async () => {
  const foreign = createHttpServer((request, response) => response.end('foreign'))
  await new Promise(resolvePromise => foreign.listen(0, '127.0.0.1', resolvePromise))
  const port = foreign.address().port
  const path = await oracle(await makeRoot('studio-oracle-'))
  await assert.rejects(runWorker({ appDir, mode: 'source', fixedPort: port, cases: [{ name: 'x', path }] }), error => {
    assert.equal(error.code, 'PORT_COLLISION')
    assert.equal(error.summary.started, 0)
    return true
  })
  assert.equal(foreign.listening, true)
  await new Promise(resolvePromise => foreign.close(resolvePromise))
})

test('parallel safe workers use distinct roots and OS-selected strict ports', async () => {
  const path = await oracle(await makeRoot('studio-oracle-'))
  const results = await runBatch({ appDir, mode: 'source', workers: 2, declarations: [
    { name: 'one', path, parallelSafe: true }, { name: 'two', path, parallelSafe: true },
  ] })
  assert.equal(results.length, 2)
  assert.notEqual(results[0].port, results[1].port)
  assert.notEqual(results[0].worker.root, results[1].worker.root)
  assert.equal(results.reduce((count, result) => count + result.completed, 0), 2)
})

test('recursive PID/PPID ownership includes descendants and exposes markerless rows', () => {
  const marker = 'owner-uuid'
  const processes = [
    { pid: 10, parentPid: 1, commandLine: `node --studio-verify-owner=${marker}`, creationDate: '/Date(1785664800000)/' },
    { pid: 11, parentPid: 10, commandLine: `node child --studio-verify-owner=${marker}`, creationDate: '/Date(1785664801000)/' },
    { pid: 12, parentPid: 11, commandLine: 'node markerless-child', creationDate: '/Date(1785664802000)/' },
    { pid: 13, parentPid: 11, commandLine: 'node stale-reused-parent', creationDate: '/Date(1785578400000)/' },
    { pid: 20, parentPid: 1, commandLine: 'node foreign' },
    { pid: 30, parentPid: 1, commandLine: `node orphan --studio-verify-owner=${marker}` },
  ]
  const tree = ownedProcessTree(processes, [10, 20], marker)
  assert.deepEqual(tree.map(row => row.pid), [10, 11, 12])
  assert.deepEqual(tree.filter(row => !row.commandLine.includes(marker)).map(row => row.pid), [12])
  assert.deepEqual(processes.filter(row => row.commandLine.includes(marker) && !tree.some(owned => owned.pid === row.pid)).map(row => row.pid), [30])
})

test('reused Windows root PID is excluded from ownership and termination', () => {
  const marker = 'owner-uuid'
  const expectedRoot = { pid: 10, parentPid: 1, commandLine: `node --studio-verify-owner=${marker}`, creationDate: '/Date(1785664800000)/' }
  const processes = [
    { ...expectedRoot, creationDate: '/Date(1785664900000)/' },
    { pid: 11, parentPid: 10, commandLine: `node child --studio-verify-owner=${marker}`, creationDate: '/Date(1785664901000)/' },
    { pid: 30, parentPid: 1, commandLine: `node orphan --studio-verify-owner=${marker}`, creationDate: '/Date(1785664802000)/' },
  ]
  assert.deepEqual(ownedProcessTree(processes, [expectedRoot], marker), [])
  assert.deepEqual(windowsTerminationTargets(processes, [expectedRoot], marker).map(row => row.pid), [30])
})

test('Windows process probe retries transient PROCESS_PROBE failures then returns rows', async () => {
  const rows = [{ pid: 10, parentPid: 1, commandLine: 'node marked', creationDate: '/Date(1785664800000)/' }]
  const waits = []
  let attempts = 0
  const result = await queryWindowsProcessesWithRetry({
    attempts: 3,
    backoffMs: 7,
    query: () => {
      attempts++
      if (attempts < 3) throw new VerifyError('PROCESS_PROBE', `transient ${attempts}`)
      return rows
    },
    sleep: async milliseconds => { waits.push(milliseconds) },
  })
  assert.equal(attempts, 3)
  assert.deepEqual(waits, [7, 7])
  assert.deepEqual(result, rows)
})

test('Windows process probe reports PROCESS_PROBE evidence after bounded attempts', async () => {
  let attempts = 0
  await assert.rejects(queryWindowsProcessesWithRetry({
    attempts: 3,
    backoffMs: 1,
    query: () => {
      attempts++
      throw new VerifyError('PROCESS_PROBE', `persistent ${attempts}`, { source: 'test' })
    },
    sleep: async () => {},
  }), error => {
    assert.equal(error.code, 'PROCESS_PROBE')
    assert.equal(error.details.maxAttempts, 3)
    assert.deepEqual(error.details.attempts.map(attempt => attempt.message), ['persistent 1', 'persistent 2', 'persistent 3'])
    return true
  })
  assert.equal(attempts, 3)
})

test('Windows process probe cancellation prevents further retry attempts', async () => {
  const controller = new AbortController()
  let attempts = 0
  await assert.rejects(queryWindowsProcessesWithRetry({
    attempts: 3,
    backoffMs: 1,
    signal: controller.signal,
    query: () => {
      attempts++
      throw new VerifyError('PROCESS_PROBE', 'transient before cancellation')
    },
    sleep: async () => { controller.abort() },
  }), error => error.code === 'RUN_CANCELLED')
  assert.equal(attempts, 1)
})

test('fast Windows root records a marked CIM creation identity before execution', { skip: process.platform !== 'win32' }, async () => {
  const path = await oracle(await makeRoot('studio-fast-root-'), 'fast.cjs', 'console.log("fast evidence")\n')
  const result = await runWorker({ appDir, mode: 'file', cases: [{ name: 'fast', path }] })
  assert.match(result.rows[0].rootCreationDate, /Date|\d{4}-\d{2}-\d{2}/)
  assert.equal(result.rows[0].outputBytes > 0, true)
})

test('environment-only descendant is OWNERSHIP_UNPROVEN and fully cleaned', { skip: process.platform !== 'win32' }, async () => {
  const root = await makeRoot('studio-owner-env-')
  const path = await oracle(root, 'environment-only.cjs', `
const { spawn } = require('node:child_process')
spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { stdio: 'ignore', env: process.env })
console.log('environment-only descendant started')
setTimeout(() => {}, 5000)
`)
  let marker
  await assert.rejects(runWorker({ appDir, mode: 'file', cases: [{ name: 'environment-only', path }] }), error => {
    marker = error.summary.worker.marker
    return error.code === 'OWNERSHIP_UNPROVEN'
  })
  assert.equal(queryWindowsProcesses().some(row => row.commandLine.includes(marker)), false)
})

test('short-lived markerless helper is red even when it exits between CIM snapshots', { skip: process.platform !== 'win32' }, async () => {
  const root = await makeRoot('studio-owner-short-helper-')
  const path = await oracle(root, 'short-helper.cjs', `
const { spawn } = require('node:child_process')
spawn(process.execPath, ['-e', 'process.exit(0)'], { stdio: 'ignore' })
console.log('short markerless helper launched')
`)
  await assert.rejects(runWorker({ appDir, mode: 'file', cases: [{ name: 'short-helper', path }] }), error => {
    assert.equal(error.code, 'OWNERSHIP_UNPROVEN')
    assert.equal(error.summary.rows[0].ownershipError.details.unmarkedSpawns.length, 1)
    return true
  })
})

test('preview descendant is proven by the exact private worker token', { skip: process.platform !== 'win32' }, async () => {
  const root = await makeRoot('studio-owner-private-token-')
  const cacheRoot = await makeRoot('studio-owner-private-cache-')
  const path = await oracle(root, 'private-token.cjs', `
const { spawn } = require('node:child_process')
const child = spawn(process.execPath, ['-e', 'setTimeout(() => {}, 300)', '--', process.env.STUDIO_VERIFY_PRIVATE_TOKEN], { stdio: 'ignore' })
child.once('exit', () => console.log('private-token descendant completed'))
`)
  const result = await runWorker({ appDir, mode: 'preview', cacheRoot, cases: [{ name: 'private-token', path }] })
  assert.equal(result.completed, 1)
  assert.match(result.worker.processToken, /^studio-process-token-[0-9a-f-]{36}$/)
  assert.equal(queryWindowsProcesses().some(row => row.commandLine.includes(result.worker.processToken)), false)
})

test('marked orphan is red, cleanup reaches zero, and foreign node survives', { skip: process.platform !== 'win32' }, async () => {
  const foreign = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { stdio: 'ignore', windowsHide: true })
  const root = await makeRoot('studio-owner-orphan-')
  const path = await oracle(root, 'owned-orphan.cjs', `
const { spawn } = require('node:child_process')
spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)', '--', process.env.STUDIO_VERIFY_BROWSER_MARKER], { stdio: 'ignore', detached: true }).unref()
console.log('owned orphan started')
setTimeout(() => {}, 5000)
`)
  let marker
  try {
    await assert.rejects(runWorker({ appDir, mode: 'file', cases: [{ name: 'owned-orphan', path }] }), error => {
      marker = error.summary.worker.marker
      return error.code === 'OWNED_PROCESS_LEAK'
    })
    assert.equal(queryWindowsProcesses().some(row => row.commandLine.includes(marker)), false)
    assert.equal(foreign.exitCode, null)
  } finally {
    foreign.kill()
  }
})

test('sequential cases wait for short-lived marked descendants to exit', { skip: process.platform !== 'win32' }, async () => {
  const root = await makeRoot('studio-owner-drain-')
  const first = await oracle(root, 'short-lived-child.cjs', `
const { spawn } = require('node:child_process')
spawn(process.execPath, ['-e', 'setTimeout(() => {}, 1200)', '--', process.env.STUDIO_VERIFY_BROWSER_MARKER], { stdio: 'ignore', detached: true }).unref()
console.log('short-lived descendant started')
`)
  const second = await oracle(root, 'after-drain.cjs', 'console.log("second case started")\n')
  const result = await runWorker({ appDir, mode: 'file', cases: [
    { name: 'first', path: first }, { name: 'second', path: second },
  ] })
  assert.equal(result.started, 2)
  assert.equal(result.completed, 2)
  assert.equal(queryWindowsProcesses().some(row => row.commandLine.includes(result.worker.marker)), false)
})

test('failure, timeout, and simulated SIGINT cancellation all clean owned roots', async () => {
  const root = await makeRoot('studio-lifecycle-')
  const failing = await oracle(root, 'failure.cjs', 'console.log("failure evidence"); process.exit(3)\n')
  await assert.rejects(runWorker({ appDir, mode: 'file', cases: [{ name: 'failure', path: failing }] }), error => error.code === 'CASE_FAILED')
  const waiting = await oracle(root, 'waiting.cjs', 'console.log("waiting evidence"); setInterval(() => {}, 1000)\n')
  await assert.rejects(runWorker({ appDir, mode: 'file', timeoutMs: 150, cases: [{ name: 'timeout', path: waiting }] }), error => error.code === 'CASE_TIMEOUT')
  const controller = new AbortController()
  const never = await oracle(root, 'never.cjs', 'console.log("must not start")\n')
  const cancelled = runWorker({ appDir, mode: 'file', signal: controller.signal, cases: [
    { name: 'cancelled', path: waiting }, { name: 'never', path: never },
  ] })
  setTimeout(() => controller.abort(), 700)
  await assert.rejects(cancelled, error => {
    assert.equal(error.code, 'RUN_CANCELLED')
    assert.equal(error.summary.started, 1)
    assert.equal(error.summary.rows.some(row => row.name === 'never'), false)
    return true
  })
  const alreadyCancelled = new AbortController()
  alreadyCancelled.abort()
  await assert.rejects(runWorker({ appDir, mode: 'preview', signal: alreadyCancelled.signal, cases: [{ name: 'never', path: never }] }), error => {
    assert.equal(error.code, 'RUN_CANCELLED')
    return true
  })
})

test('cancelled sweep partition does not launch a later mode', async () => {
  const controller = new AbortController()
  const started = []
  const completed = await runModePartitions(['source', 'preview', 'preview-prod'], controller.signal, async mode => {
    started.push(mode)
    controller.abort()
    return mode
  })
  assert.deepEqual(started, ['source'])
  assert.deepEqual(completed, ['source'])
})

test('positive output is required even when a case exits zero', async () => {
  const root = await makeRoot('studio-positive-evidence-')
  const silent = await oracle(root, 'silent.cjs', '')
  await assert.rejects(runWorker({ appDir, mode: 'file', cases: [{ name: 'silent', path: silent }] }), error => {
    assert.equal(error.code, 'EMPTY_EVIDENCE')
    assert.equal(error.summary.rows[0].code, 0)
    assert.equal(error.summary.rows[0].outputBytes, 0)
    return true
  })
  const noisy = await oracle(root, 'noisy.cjs', 'console.log("positive evidence")\n')
  const result = await runWorker({ appDir, mode: 'file', cases: [{ name: 'noisy', path: noisy }] })
  assert.equal(result.ok, true)
  assert.equal(result.rows[0].outputBytes > 0, true)
  assert.equal(result.rows[0].outputLines > 0, true)
})

test('mixed legacy formats classify without changing oracle bytes', async () => {
  // Every production oracle under tests/legacy/ is CommonJS, and must stay that way: the directory
  // ships its own package.json declaring "type": "commonjs", so a .js file there written with
  // top-level `await import(...)` does not load at all under Node 25. Five oracles were in exactly
  // that state and were converted. This test therefore pins the production side to commonjs and
  // supplies its own ESM fixture, so the mixed-format claim does not silently evaporate the next
  // time a real oracle changes shape.
  const names = ['_verify_bridge.js', '_verify_blur_isotropy.js', '_verify_digest.js', '_verify_surface.js']
  const before = new Map(await Promise.all(names.map(async name => [name, await readFile(join(appDir, 'tests/legacy', name))])))
  const formats = new Map()
  for (const name of names) formats.set(name, (await classifyOracle(join(appDir, 'tests/legacy', name))).format)
  for (const name of names) assert.equal(formats.get(name), 'commonjs', `${name} must be CommonJS to load under tests/legacy/package.json`)

  const root = await makeRoot('studio-mixed-formats-')
  const esm = await oracle(root, 'native-module.mjs', 'await Promise.resolve(); console.log("esm")\n')
  assert.equal((await classifyOracle(esm)).format, 'module')

  for (const name of names) assert.deepEqual(await readFile(join(appDir, 'tests/legacy', name)), before.get(name))
})

test('CommonJS helper and native ESM execute once with unchanged bytes and argv', async () => {
  const root = await makeRoot('studio-formats-')
  await writeFile(join(root, 'helper.js'), 'module.exports = __dirname\n')
  const commonjs = await oracle(root, 'commonjs.js', 'console.log("cjs", require("./helper.js"), __dirname, process.argv.slice(2).join(","))\n')
  const module = await oracle(root, 'module.js', 'await Promise.resolve(); console.log("esm", process.argv.slice(2).join(","))\n')
  const before = [await readFile(commonjs), await readFile(module), await readFile(join(root, 'helper.js'))]
  const result = await runWorker({ appDir, mode: 'file', cases: [
    { name: 'commonjs', path: commonjs, args: ['cjs-arg'] },
    { name: 'module', path: module, args: ['esm-arg'] },
  ] })
  assert.deepEqual(result.rows.map(row => row.format), ['commonjs', 'module'])
  assert.equal(result.rows.every(row => row.outputBytes > 0 && row.outputLines > 0), true)
  assert.deepEqual([await readFile(commonjs), await readFile(module), await readFile(join(root, 'helper.js'))], before)
})

test('parent rejects CommonJS source changed by a later exit listener', async () => {
  const root = await makeRoot('studio-post-exit-identity-')
  const path = await oracle(root, 'late-mutation.cjs', `
const fs = require('node:fs')
process.once('exit', () => fs.appendFileSync(__filename, '// changed after bootstrap exit check\\n'))
console.log('late mutation registered')
`)
  await assert.rejects(runWorker({ appDir, mode: 'file', cases: [{ name: 'late-mutation', path }] }), error => {
    assert.equal(error.code, 'ORACLE_BYTES_CHANGED')
    assert.notEqual(error.details.beforeSha256, error.details.afterSha256)
    return true
  })
})

test('cache miss, hit, complete entry, and key controls', async () => {
  const { app } = await fixtureApp()
  const cacheRoot = await makeRoot('studio-cache-')
  let builds = 0
  const build = async outDir => {
    builds++
    await mkdir(outDir, { recursive: true })
    await writeFile(join(outDir, 'index.html'), `build-${builds}\n`)
  }
  const common = { appDir: app, cacheRoot, mode: 'test', command: ['fixture', '--mode', 'test'], tools: { vite: 'v', esbuild: 'e' }, build }
  const miss = await ensureBuild(common)
  const hit = await ensureBuild(common)
  assert.equal(miss.hit, false)
  assert.equal(hit.hit, true)
  assert.equal(builds, 1)
  assert.equal(hit.key, miss.key)
  assert.equal(hit.outputHash, miss.outputHash)
  assert.deepEqual((await readdir(hit.entryDir)).sort(), ['dist', 'manifest.json'])
  const base = await createBuildKey({ appDir: app, mode: 'test', command: ['fixture'], tools: { vite: 'v', esbuild: 'e' } })
  const controls = await Promise.all([
    createBuildKey({ appDir: app, mode: 'production', command: ['fixture'], tools: { vite: 'v', esbuild: 'e' } }),
    createBuildKey({ appDir: app, mode: 'test', command: ['fixture', 'changed'], tools: { vite: 'v', esbuild: 'e' } }),
    createBuildKey({ appDir: app, mode: 'test', command: ['fixture'], tools: { vite: 'v2', esbuild: 'e' } }),
    createBuildKey({ appDir: app, mode: 'test', command: ['fixture'], tools: { vite: 'v', esbuild: 'e2' } }),
    createBuildKey({ appDir: app, mode: 'test', command: ['fixture'], tools: { vite: 'v', esbuild: 'e' }, environment: { VITE_CONTROL: 'changed' } }),
    createBuildKey({ appDir: app, mode: 'test', command: ['fixture'], tools: { vite: 'v', esbuild: 'e' }, runtime: { node: 'changed', platform: process.platform, architecture: process.arch } }),
    createBuildKey({ appDir: app, mode: 'test', command: ['fixture'], tools: { vite: 'v', esbuild: 'e' }, schema: CACHE_SCHEMA + 1 }),
  ])
  for (const control of controls) assert.notEqual(control.key, base.key)
  await writeFile(join(app, 'src', 'main.js'), 'console.log("source changed")\n')
  assert.notEqual((await createBuildKey({ appDir: app, mode: 'test', command: ['fixture'], tools: { vite: 'v', esbuild: 'e' } })).key, base.key)
  await writeFile(join(app, 'src', 'main.js'), 'console.log("fixture")\n')
  await writeFile(join(app, 'public', 'asset.txt'), 'public changed\n')
  assert.notEqual((await createBuildKey({ appDir: app, mode: 'test', command: ['fixture'], tools: { vite: 'v', esbuild: 'e' } })).key, base.key)
})

test('concurrent same-key cache requests build once and restore identical bytes', async () => {
  const { app } = await fixtureApp()
  const cacheRoot = await makeRoot('studio-cache-concurrent-')
  let builds = 0
  const options = {
    appDir: app, cacheRoot, mode: 'test', command: ['fixture'], tools: { vite: 'v', esbuild: 'e' },
    build: async outDir => {
      builds++
      await new Promise(resolvePromise => setTimeout(resolvePromise, 100))
      await mkdir(outDir, { recursive: true })
      await writeFile(join(outDir, 'index.html'), 'concurrent bytes')
    },
  }
  const results = await Promise.all([ensureBuild(options), ensureBuild(options)])
  assert.equal(builds, 1)
  assert.deepEqual(results.map(result => result.hit).sort(), [false, true])
  assert.equal(results[0].key, results[1].key)
  assert.equal(results[0].outputHash, results[1].outputHash)
})

test('different cache keys publish and restore into independent private directories', async () => {
  const { app } = await fixtureApp()
  const cacheRoot = await makeRoot('studio-cache-different-keys-')
  const privateRoot = await makeRoot('studio-cache-private-dist-')
  const invoke = mode => ensureBuild({
    appDir: app,
    cacheRoot,
    mode,
    command: ['fixture', mode],
    tools: { vite: 'v', esbuild: 'e' },
    destinationDir: join(privateRoot, mode),
    build: async outDir => {
      await new Promise(resolvePromise => setTimeout(resolvePromise, mode === 'test' ? 80 : 20))
      await mkdir(outDir, { recursive: true })
      await writeFile(join(outDir, 'index.html'), `${mode} bytes`)
    },
  })
  const [testBuild, productionBuild] = await Promise.all([invoke('test'), invoke('production')])
  assert.notEqual(testBuild.key, productionBuild.key)
  assert.notEqual(testBuild.distDir, productionBuild.distDir)
  assert.equal(await readFile(join(testBuild.distDir, 'index.html'), 'utf8'), 'test bytes')
  assert.equal(await readFile(join(productionBuild.distDir, 'index.html'), 'utf8'), 'production bytes')
  await assert.rejects(readFile(join(app, 'dist', 'index.html')), error => error.code === 'ENOENT')
})

test('concurrent built modes serve matching identities from Vite private outputs', async () => {
  const root = await makeRoot('studio-served-identity-')
  const cacheRoot = await makeRoot('studio-served-cache-')
  const path = await oracle(root, 'served-identity.cjs', `
fetch(process.env.STUDIO_URL).then(async response => {
  const body = await response.text()
  const owner = response.headers.get('x-studio-verify-owner')
  const identity = response.headers.get('x-studio-verify-identity')
  process.stdout.write('served ' + owner + ' ' + identity + ' ' + body.length + '\\n')
  if (owner !== process.env.STUDIO_VERIFY_OWNER || !/^[a-f0-9]{64}$/.test(identity) || body.length === 0) process.exitCode = 1
}).catch(error => { console.error(error); process.exitCode = 1 })
`)
  const [testMode, productionMode] = await Promise.all(['preview', 'preview-prod'].map(mode => runWorker({
    appDir,
    mode,
    cacheRoot,
    cases: [{ name: mode, path }],
  })))
  assert.notEqual(testMode.cache.key, productionMode.cache.key)
  assert.notEqual(testMode.cache.distDir, productionMode.cache.distDir)
  for (const result of [testMode, productionMode]) {
    assert.equal(result.hostImplementation, 'vite-preview')
    assert.equal(result.cache.distDir.startsWith(result.worker.root), true)
    const output = await readFile(result.rows[0].logPath, 'utf8')
    assert.match(output, new RegExp(`served ${result.worker.marker} ${result.cache.outputHash} [1-9]\\d*`))
  }
})

test('dead cache lock owner is recovered without waiting for lock timeout', async () => {
  const { app } = await fixtureApp()
  const cacheRoot = await makeRoot('studio-cache-stale-lock-')
  const key = (await createBuildKey({
    appDir: app,
    mode: 'test',
    command: ['fixture'],
    tools: { vite: 'v', esbuild: 'e' },
  })).key
  const lockDir = join(cacheRoot, `${key}.lock`)
  await mkdir(lockDir)
  await writeFile(join(lockDir, 'owner.json'), JSON.stringify({ pid: 2147483647, token: 'dead-owner', createdAt: '2000-01-01T00:00:00.000Z' }))
  const result = await ensureBuild({
    appDir: app,
    cacheRoot,
    mode: 'test',
    command: ['fixture'],
    tools: { vite: 'v', esbuild: 'e' },
    build: async outDir => { await mkdir(outDir, { recursive: true }); await writeFile(join(outDir, 'index.html'), 'recovered') },
  })
  assert.equal(result.hit, false)
  assert.equal(await readFile(join(result.distDir, 'index.html'), 'utf8'), 'recovered')
  await assert.rejects(stat(lockDir), error => error.code === 'ENOENT')
})

test('reused live Windows PID does not retain a stale cache lock', { skip: process.platform !== 'win32' }, async () => {
  const { app } = await fixtureApp()
  const cacheRoot = await makeRoot('studio-cache-reused-lock-')
  const options = { appDir: app, mode: 'test', command: ['fixture'], tools: { vite: 'v', esbuild: 'e' } }
  const key = (await createBuildKey(options)).key
  const lockDir = join(cacheRoot, `${key}.lock`)
  await mkdir(lockDir)
  await writeFile(join(lockDir, 'owner.json'), JSON.stringify({
    pid: process.pid,
    token: 'reused-owner',
    processCreationDate: '2000-01-01T00:00:00.0000000Z',
  }))
  const result = await ensureBuild({
    ...options,
    cacheRoot,
    build: async outDir => { await mkdir(outDir, { recursive: true }); await writeFile(join(outDir, 'index.html'), 'reused recovered') },
  })
  assert.equal(result.hit, false)
  assert.equal(await readFile(join(result.distDir, 'index.html'), 'utf8'), 'reused recovered')
  await assert.rejects(stat(lockDir), error => error.code === 'ENOENT')
})

test('cache tamper is red and deliberate repair is a visible miss', async () => {
  const { app } = await fixtureApp()
  const cacheRoot = await makeRoot('studio-cache-tamper-')
  let builds = 0
  const options = {
    appDir: app, cacheRoot, mode: 'test', command: ['fixture'], tools: { vite: 'v', esbuild: 'e' },
    build: async outDir => { builds++; await mkdir(outDir, { recursive: true }); await writeFile(join(outDir, 'index.html'), `bytes-${builds}`) },
  }
  const first = await ensureBuild(options)
  await writeFile(join(first.entryDir, 'dist', 'index.html'), 'tampered')
  await assert.rejects(ensureBuild(options), error => error instanceof CacheError && error.code === 'CACHE_TAMPER')
  const repaired = await ensureBuild({ ...options, repairTamper: true })
  assert.equal(repaired.hit, false)
  assert.equal(builds, 2)
  assert.notEqual(repaired.outputHash, first.outputHash)
})

test('empty and symlink build outputs are red before cache publication', async () => {
  for (const [name, build] of [
    ['empty', async outDir => mkdir(outDir, { recursive: true })],
    ['symlink', async outDir => {
      await mkdir(outDir, { recursive: true })
      await writeFile(join(outDir, 'index.html'), 'output')
      await symlink('index.html', join(outDir, 'linked.html'), 'file')
    }],
  ]) {
    const { app } = await fixtureApp()
    const cacheRoot = await makeRoot(`studio-cache-output-${name}-`)
    await assert.rejects(ensureBuild({
      appDir: app,
      cacheRoot,
      mode: 'test',
      command: ['fixture'],
      tools: { vite: 'v', esbuild: 'e' },
      build,
    }), error => error instanceof CacheError)
    assert.deepEqual(await readdir(cacheRoot), [])
  }
})

test('removed, added, modified, corrupt-manifest, and missing-manifest cache entries are independently red', async () => {
  const mutations = [
    async entry => rm(join(entry, 'dist', 'index.html')),
    async entry => writeFile(join(entry, 'dist', 'extra.txt'), 'extra'),
    async entry => writeFile(join(entry, 'dist', 'index.html'), 'modified'),
    async entry => writeFile(join(entry, 'manifest.json'), '{broken'),
    async entry => rm(join(entry, 'manifest.json')),
  ]
  for (const [index, mutate] of mutations.entries()) {
    const { app } = await fixtureApp()
    const cacheRoot = await makeRoot(`studio-cache-tamper-${index}-`)
    const options = {
      appDir: app, cacheRoot, mode: 'test', command: ['fixture'], tools: { vite: 'v', esbuild: 'e' },
      build: async outDir => { await mkdir(outDir, { recursive: true }); await writeFile(join(outDir, 'index.html'), 'original') },
    }
    const first = await ensureBuild(options)
    await mutate(first.entryDir)
    await assert.rejects(ensureBuild(options), error => error instanceof CacheError && error.code === 'CACHE_TAMPER')
  }
})

test('sweep empty discovery, unknown names, duplicate names, and unsafe workers are red before execution', async () => {
  const sweep = join(appDir, 'scripts', 'sweep-oracles.mjs')
  const empty = await makeRoot('studio-empty-discovery-')
  const emptyResult = spawnSync(process.execPath, [sweep], { encoding: 'utf8', env: { ...process.env, STUDIO_LEGACY_DIR: empty } })
  assert.equal(emptyResult.status, 1)
  assert.match(`${emptyResult.stdout}${emptyResult.stderr}`, /EMPTY_INVENTORY/)
  const unknown = spawnSync(process.execPath, [sweep, '_verify_missing.js'], { encoding: 'utf8' })
  assert.equal(unknown.status, 1)
  assert.match(`${unknown.stdout}${unknown.stderr}`, /UNKNOWN_ORACLE/)
  const duplicate = spawnSync(process.execPath, [sweep, '_verify_digest.js', '_verify_digest.js'], { encoding: 'utf8' })
  assert.equal(duplicate.status, 1)
  assert.match(`${duplicate.stdout}${duplicate.stderr}`, /DUPLICATE_DECLARATION/)
  const unsafe = spawnSync(process.execPath, [sweep, '_verify_digest.js', '--workers=2'], { encoding: 'utf8' })
  assert.equal(unsafe.status, 1)
  assert.match(`${unsafe.stdout}${unsafe.stderr}`, /UNSAFE_PARALLELISM/)
})

test('preview cache hit reruns mutation, visual, digest, and oracle declarations without verdict cache files', async () => {
  const root = await makeRoot('studio-fresh-counters-')
  const cacheRoot = await makeRoot('studio-counter-cache-')
  const counter = join(root, 'counter.txt')
  const path = await oracle(root, 'counter.cjs', `
require('node:fs').appendFileSync(process.env.STUDIO_COUNTER, process.argv[2] + '\\n')
console.log('counter', process.argv[2])
`)
  const cases = ['mutation', 'visual', 'digest', 'oracle'].map(name => ({ name, path, args: [name] }))
  const options = { appDir, mode: 'preview', cacheRoot, cases, environment: { ...process.env, STUDIO_COUNTER: counter } }
  const first = await runWorker(options)
  const second = await runWorker(options)
  assert.equal(first.cache.hit, false)
  assert.equal(second.cache.hit, true)
  assert.equal(first.completed, 4)
  assert.equal(second.completed, 4)
  assert.deepEqual((await readFile(counter, 'utf8')).trim().split(/\r?\n/), [...cases.map(item => item.name), ...cases.map(item => item.name)])
  const entry = join(cacheRoot, second.cache.key)
  assert.deepEqual((await readdir(entry)).sort(), ['dist', 'manifest.json'])
})