import { spawn, spawnSync } from 'node:child_process'
import { createHash, randomUUID } from 'node:crypto'
import { copyFile, mkdir, mkdtemp, open, readFile, readdir, rm, stat, writeFile } from 'node:fs/promises'
import { createServer as createHttpServer } from 'node:http'
import { createRequire } from 'node:module'
import { tmpdir } from 'node:os'
import { basename, dirname, extname, isAbsolute, join, normalize, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse } from 'acorn'
import { build as viteBuild, createServer as createViteServer } from 'vite'
import { ensureBuild } from './build-cache.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const require = createRequire(import.meta.url)
const bootstrap = resolve(here, 'legacy-oracle-bootstrap.cjs')
const MODES = new Set(['source', 'preview', 'preview-prod', 'file'])
const sha256 = value => createHash('sha256').update(value).digest('hex')
const delay = milliseconds => new Promise(resolvePromise => setTimeout(resolvePromise, milliseconds))

export class VerifyError extends Error {
  constructor(code, message, details = {}) {
    super(message)
    this.name = 'VerifyError'
    this.code = code
    this.details = details
  }
}

export async function classifyOracle(path, explicit) {
  const bytes = await readFile(path)
  const source = bytes.toString('utf8')
  let script = false
  let module = false
  try { parse(source, { ecmaVersion: 'latest', sourceType: 'script', allowHashBang: true }); script = true } catch {}
  try { parse(source, { ecmaVersion: 'latest', sourceType: 'module', allowHashBang: true }); module = true } catch {}
  const inferred = script ? 'commonjs' : module ? 'module' : null
  if (!inferred) throw new VerifyError('ORACLE_PARSE', `Cannot parse oracle as script or module: ${path}`)
  if (explicit && explicit !== inferred && !(explicit === 'module' && script && module)) {
    throw new VerifyError('ORACLE_PARSE', `Declared ${explicit} contradicts parsed ${inferred}: ${path}`)
  }
  return { format: explicit || inferred, sha256: sha256(bytes), bytes }
}

async function isEmpty(directory) {
  return (await readdir(directory)).length === 0
}

export async function createWorkerRoot({ temporaryRoot = process.env.STUDIO_VERIFY_TMP || tmpdir(), selectedRoot } = {}) {
  if (!selectedRoot) await mkdir(resolve(temporaryRoot), { recursive: true })
  const root = selectedRoot ? resolve(selectedRoot) : await mkdtemp(join(resolve(temporaryRoot), 'terrain-studio-verify-'))
  if (selectedRoot) {
    try {
      const info = await stat(root)
      if (!info.isDirectory() || !(await isEmpty(root))) throw new VerifyError('STALE_PROFILE', `Selected worker root is not empty: ${root}`)
    } catch (error) {
      if (error.code === 'ENOENT') await mkdir(root, { recursive: true })
      else throw error
    }
  }
  const marker = randomUUID()
  const markerRoot = join(root, marker)
  const profile = join(markerRoot, 'profile')
  const temp = join(markerRoot, 'temp')
  const logs = join(root, 'logs')
  await mkdir(markerRoot)
  await Promise.all([mkdir(profile), mkdir(temp), mkdir(logs)])
  return { root, markerRoot, marker, markerArgument: `--studio-verify-owner=${marker}`, profile, temp, logs }
}

async function startHost({ appDir, mode, token, identity, fixedPort }) {
  let vite
  let handler
  const httpServer = createHttpServer((request, response) => {
    response.setHeader('x-studio-verify-owner', token)
    response.setHeader('x-studio-verify-identity', identity)
    Promise.resolve(handler?.(request, response)).catch(error => {
      response.statusCode = 500
      response.end(error.message)
    })
  })
  try {
    if (mode === 'source') {
      vite = await createViteServer({
        root: appDir,
        configLoader: 'native',
        logLevel: 'error',
        esbuild: false,
        optimizeDeps: { noDiscovery: true, include: [] },
        server: { middlewareMode: true, hmr: { server: httpServer } },
      })
      handler = vite.middlewares
    } else {
      const dist = resolve(appDir, 'dist')
      const types = new Map([
        ['.css', 'text/css'], ['.html', 'text/html'], ['.ico', 'image/x-icon'], ['.js', 'text/javascript'],
        ['.json', 'application/json'], ['.map', 'application/json'], ['.png', 'image/png'], ['.svg', 'image/svg+xml'],
        ['.wasm', 'application/wasm'], ['.webmanifest', 'application/manifest+json'], ['.woff2', 'font/woff2'],
      ])
      handler = async (request, response) => {
        try {
          const requested = normalize(decodeURIComponent(new URL(request.url, 'http://localhost').pathname)).replace(/^[/\\]+/, '')
          let path = resolve(dist, requested || 'index.html')
          const fromDist = relative(dist, path)
          if (fromDist.startsWith('..') || isAbsolute(fromDist)) throw new Error('Path escapes dist')
          try {
            if (!(await stat(path)).isFile()) path = resolve(dist, 'index.html')
          } catch { path = resolve(dist, 'index.html') }
          const bytes = await readFile(path)
          response.statusCode = 200
          response.setHeader('content-type', types.get(extname(path)) || 'application/octet-stream')
          response.end(request.method === 'HEAD' ? undefined : bytes)
        } catch (error) {
          response.statusCode = 404
          response.end(error.message)
        }
      }
    }
  } catch (error) {
    await vite?.close()
    throw new VerifyError('SERVER_START', `Server preparation failed: ${error.message}`)
  }
  try {
    await new Promise((resolvePromise, reject) => {
      httpServer.once('error', reject)
      httpServer.listen(fixedPort ?? 0, '127.0.0.1', resolvePromise)
    })
  } catch (error) {
    await vite?.close()
    throw new VerifyError('PORT_COLLISION', `Server could not bind the requested port: ${error.message}`)
  }
  const address = httpServer.address()
  if (!address || typeof address === 'string' || address.port <= 0) {
    await new Promise(resolvePromise => httpServer.close(resolvePromise))
    await vite?.close()
    throw new VerifyError('SERVER_IDENTITY', 'Host did not report a positive bound port')
  }
  return {
    port: address.port,
    close: async () => {
      await new Promise(resolvePromise => httpServer.close(resolvePromise))
      await vite?.close()
    },
  }
}

async function listen(appDir, mode, worker, identity, fixedPort) {
  const config = Buffer.from(JSON.stringify({ appDir, mode, token: worker.marker, identity, fixedPort })).toString('base64url')
  const hostLogPath = join(worker.logs, 'host.log')
  const hostLog = await open(hostLogPath, 'w')
  const child = spawn(process.execPath, ['--', fileURLToPath(import.meta.url), '--studio-host', config, '--', worker.markerArgument], {
    cwd: appDir,
    env: childEnvironment(worker, '', process.env),
    windowsHide: true,
    detached: process.platform !== 'win32',
    stdio: ['ignore', hostLog.fd, hostLog.fd, 'ipc'],
  })
  let ready
  let readyTimer
  try {
    ready = await Promise.race([
      new Promise((resolvePromise, reject) => {
        child.once('error', reject)
        child.once('exit', code => reject(new VerifyError(code === 98 ? 'PORT_COLLISION' : 'SERVER_START', `Host exited before ready: ${code}`)))
        child.once('message', message => message?.ready ? resolvePromise(message) : reject(new VerifyError(message?.code || 'SERVER_START', message?.message || 'Invalid host response')))
      }),
      new Promise((resolvePromise, reject) => {
        readyTimer = setTimeout(() => reject(new VerifyError('SERVER_START', 'Timed out waiting for marked host')), 30000)
      }),
    ])
  } catch (error) {
    await hostLog.close()
    throw error
  } finally {
    clearTimeout(readyTimer)
  }
  const url = `http://127.0.0.1:${ready.port}/index.html`
  for (let attempt = 0; attempt < 100; attempt++) {
    try {
      const response = await fetch(url, { method: 'HEAD' })
      if (response.ok && response.headers.get('x-studio-verify-owner') === worker.marker
        && response.headers.get('x-studio-verify-identity') === identity) {
        return {
          server: { close: async () => {
            if (child.exitCode === null) {
              child.send({ close: true })
              let closeTimer
              await Promise.race([
                new Promise(resolvePromise => child.once('exit', resolvePromise)),
                new Promise(resolvePromise => { closeTimer = setTimeout(resolvePromise, 5000) }),
              ])
              clearTimeout(closeTimer)
            }
            await hostLog.close()
          } },
          url,
          port: ready.port,
          pid: child.pid,
          argv: child.spawnargs,
          logPath: hostLogPath,
        }
      }
      if (response.ok) break
    } catch {}
    await delay(50)
  }
  if (child.exitCode === null) child.send({ close: true })
  await hostLog.close()
  throw new VerifyError('SERVER_IDENTITY', `Server identity probe failed at ${url}`)
}

function childEnvironment(worker, url, environment = process.env) {
  const result = {
    ...environment,
    STUDIO_URL: url,
    STUDIO_VERIFY_OWNER: worker.marker,
    STUDIO_VERIFY_BROWSER_MARKER: worker.markerArgument,
    TEMP: worker.temp,
    TMP: worker.temp,
    TMPDIR: worker.temp,
  }
  if (!environment.PLAYWRIGHT_BROWSERS_PATH) delete result.PLAYWRIGHT_BROWSERS_PATH
  return result
}

function parsePowerShellJson(text) {
  if (!text.trim()) return []
  const parsed = JSON.parse(text)
  return Array.isArray(parsed) ? parsed : [parsed]
}

export function queryWindowsProcesses() {
  if (process.platform !== 'win32') return []
  const command = "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,CommandLine,CreationDate | ConvertTo-Json -Compress"
  const result = spawnSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', command], {
    encoding: 'utf8', maxBuffer: 64 * 1024 * 1024,
  })
  if (result.status !== 0) throw new VerifyError('PROCESS_PROBE', result.stderr || 'CIM process probe failed')
  return parsePowerShellJson(result.stdout).map(row => ({
    pid: Number(row.ProcessId), parentPid: Number(row.ParentProcessId), commandLine: row.CommandLine || '', creationDate: row.CreationDate || '',
  }))
}

function processCreationTime(value) {
  const cimEpoch = /^\/Date\((-?\d+)\)\/$/.exec(value)
  return cimEpoch ? Number(cimEpoch[1]) : Date.parse(value)
}

export function ownedProcessTree(processes, roots, marker) {
  const owned = new Map()
  const rootSet = new Set(roots)
  for (const processInfo of processes) {
    if (rootSet.has(processInfo.pid) && processInfo.commandLine.includes(marker)) owned.set(processInfo.pid, processInfo)
  }
  let changed = true
  while (changed) {
    changed = false
    for (const processInfo of processes) {
      const parent = owned.get(processInfo.parentPid)
      const parentCreated = processCreationTime(parent?.creationDate)
      const childCreated = processCreationTime(processInfo.creationDate)
      const staleParentLink = Number.isFinite(parentCreated) && Number.isFinite(childCreated) && childCreated < parentCreated
      if (parent && !owned.has(processInfo.pid) && !staleParentLink) {
        owned.set(processInfo.pid, processInfo)
        changed = true
      }
    }
  }
  return [...owned.values()].sort((left, right) => left.pid - right.pid)
}

async function processEvidence(worker, roots, phase) {
  if (process.platform !== 'win32') return []
  const all = queryWindowsProcesses()
  const tree = ownedProcessTree(all, roots, worker.marker)
  await writeFile(join(worker.logs, `processes-${phase}.json`), `${JSON.stringify(tree, null, 2)}\n`)
  const treePids = new Set(tree.map(processInfo => processInfo.pid))
  const strayMarked = all.filter(processInfo => processInfo.commandLine.includes(worker.marker) && !treePids.has(processInfo.pid))
  if (strayMarked.length) {
    const code = phase.startsWith('live-') ? 'OWNERSHIP_UNPROVEN' : 'OWNED_PROCESS_LEAK'
    throw new VerifyError(code, `Marked processes are outside the owned tree: ${strayMarked.map(row => row.pid).join(',')}`, { tree, strayMarked })
  }
  const missingMarker = tree.filter(processInfo => !processInfo.commandLine.includes(worker.marker))
  if (missingMarker.length) {
    throw new VerifyError('OWNERSHIP_UNPROVEN', `Owned descendants lack marker: ${missingMarker.map(row => row.pid).join(',')}`, { tree })
  }
  return tree
}

async function terminateRoots(worker, roots) {
  if (process.platform === 'win32') {
    const before = queryWindowsProcesses()
    const tree = ownedProcessTree(before, roots, worker.marker)
    const marked = before.filter(processInfo => processInfo.commandLine.includes(worker.marker))
    const targets = [...new Set([...roots, ...tree.map(row => row.pid), ...marked.map(row => row.pid)])]
    for (const pid of targets) spawnSync('taskkill.exe', ['/PID', String(pid), '/T', '/F'], { stdio: 'ignore' })
    await delay(150)
    const after = queryWindowsProcesses()
    const remainingMarked = after.filter(processInfo => processInfo.commandLine.includes(worker.marker))
    const remainingPids = after.filter(processInfo => targets.includes(processInfo.pid))
    if (remainingMarked.length || remainingPids.length) {
      throw new VerifyError('OWNED_PROCESS_LEAK', `Owned marker/PIDs remain: ${[...new Set([...remainingMarked, ...remainingPids].map(row => row.pid))].join(',')}`, { remainingMarked, remainingPids })
    }
  } else {
    for (const pid of roots) {
      try { process.kill(-pid, 'SIGKILL') } catch {}
    }
  }
}

async function waitForCaseProcesses(worker, roots, timeoutMs = 5000) {
  if (process.platform !== 'win32') return
  const deadline = Date.now() + timeoutMs
  while (true) {
    const processes = queryWindowsProcesses()
    const persistentPids = new Set(ownedProcessTree(processes, roots, worker.marker).map(processInfo => processInfo.pid))
    const remaining = processes.filter(processInfo => processInfo.commandLine.includes(worker.marker) && !persistentPids.has(processInfo.pid))
    if (remaining.length === 0) return
    if (Date.now() >= deadline) {
      throw new VerifyError('OWNED_PROCESS_LEAK', `Marked case processes remain: ${remaining.map(row => row.pid).join(',')}`, { remaining })
    }
    await delay(100)
  }
}

async function runChild({ worker, oracle, classification, args, cwd, env, timeoutMs, roots, signal }) {
  const logPath = join(worker.logs, `${basename(oracle)}-${Date.now()}.log`)
  const log = await open(logPath, 'w')
  const marker = worker.markerArgument
  const nodeArgs = classification.format === 'commonjs'
    ? ['--', bootstrap, marker, '--oracle', oracle, ...args]
    : ['--require', bootstrap, '--', oracle, marker, ...args]
  const startedAt = new Date().toISOString()
  const child = spawn(process.execPath, nodeArgs, {
    cwd, env, windowsHide: true, detached: process.platform !== 'win32', stdio: ['ignore', log.fd, log.fd],
  })
  let timedOut = false
  let cancelled = false
  let ownershipError
  const stopChild = () => {
    if (child.exitCode !== null) return
    if (process.platform === 'win32') spawnSync('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], { stdio: 'ignore' })
    else try { process.kill(-child.pid, 'SIGKILL') } catch {}
  }
  const timeout = setTimeout(() => {
    timedOut = true
    stopChild()
  }, timeoutMs)
  const abort = () => { cancelled = true; stopChild() }
  signal?.addEventListener('abort', abort, { once: true })
  if (signal?.aborted) abort()
  const liveEvidence = delay(350).then(async () => {
    if (child.exitCode !== null || process.platform !== 'win32') return
    try {
      await processEvidence(worker, [...roots, child.pid], `live-${child.pid}`)
    } catch (error) {
      ownershipError = error
      stopChild()
    }
  })
  const exit = await new Promise((resolvePromise, reject) => {
    child.once('error', reject)
    child.once('exit', (code, signal) => resolvePromise({ code: code ?? 1, signal }))
  })
  clearTimeout(timeout)
  signal?.removeEventListener('abort', abort)
  await liveEvidence
  await log.close()
  const output = await readFile(logPath)
  return {
    ...exit, pid: child.pid, argv: [process.execPath, ...nodeArgs], startedAt, completedAt: new Date().toISOString(),
    outputBytes: output.length, outputLines: output.length ? output.toString('utf8').split(/\r?\n/).filter(Boolean).length : 0, logPath,
    timedOut, cancelled, ownershipError,
  }
}

async function runBuildChild({ worker, roots, appDir, mode, outDir, environment }) {
  const logPath = join(worker.logs, `build-${mode}.log`)
  const log = await open(logPath, 'w')
  const config = Buffer.from(JSON.stringify({ appDir, mode, outDir })).toString('base64url')
  const child = spawn(process.execPath, ['--', fileURLToPath(import.meta.url), '--studio-build', config, '--', worker.markerArgument], {
    cwd: appDir,
    env: childEnvironment(worker, '', environment),
    windowsHide: true,
    detached: process.platform !== 'win32',
    stdio: ['ignore', log.fd, log.fd],
  })
  let ownershipError
  const liveEvidence = delay(350).then(async () => {
    if (child.exitCode !== null || process.platform !== 'win32') return
    try { await processEvidence(worker, [...roots, child.pid], `live-build-${child.pid}`) } catch (error) { ownershipError = error }
  })
  const exit = await new Promise((resolvePromise, reject) => {
    child.once('error', reject)
    child.once('exit', code => resolvePromise(code ?? 1))
  })
  await liveEvidence
  await log.close()
  if (ownershipError) throw ownershipError
  if (exit !== 0) throw new VerifyError('BUILD_FAILED', `Marked Vite build exited ${exit}`, { logPath })
  if ((await readFile(logPath)).length === 0) throw new VerifyError('EMPTY_EVIDENCE', 'Marked Vite build produced no output', { logPath })
}

async function markedBuildEnvironment(worker, environment) {
  if (process.platform !== 'win32') return environment
  const packagePath = require.resolve('@esbuild/win32-x64/package.json')
  const source = resolve(dirname(packagePath), 'esbuild.exe')
  const target = join(worker.markerRoot, `${worker.markerArgument}.exe`)
  await copyFile(source, target)
  return { ...environment, ESBUILD_BINARY_PATH: target }
}

function validateCases(cases) {
  if (!Array.isArray(cases) || cases.length === 0) throw new VerifyError('EMPTY_INVENTORY', 'No verification cases declared')
  const names = cases.map(item => item.name)
  if (names.some(name => !name) || new Set(names).size !== names.length) throw new VerifyError('DUPLICATE_DECLARATION', 'Case names must be non-empty and unique')
}

export async function runWorker({
  appDir,
  mode,
  cases,
  temporaryRoot,
  selectedRoot,
  fixedPort,
  cacheRoot,
  repairCache = false,
  timeoutMs = 10 * 60 * 1000,
  keepWorkerRoot = false,
  environment = process.env,
  signal,
}) {
  if (!MODES.has(mode)) throw new VerifyError('INVALID_MODE', `Explicit mode required: ${mode || '(missing)'}`)
  validateCases(cases)
  appDir = resolve(appDir)
  const worker = await createWorkerRoot({ temporaryRoot, selectedRoot })
  const roots = []
  const rows = []
  let serverInfo
  let cache = null
  let failure
  try {
    if (mode === 'preview' || mode === 'preview-prod') {
      const buildMode = mode === 'preview' ? 'test' : 'production'
      const command = ['vite', 'build', ...(buildMode === 'test' ? ['--mode', 'test'] : [])]
      const buildEnvironment = await markedBuildEnvironment(worker, environment)
      cache = await ensureBuild({
        appDir,
        cacheRoot,
        mode: buildMode,
        command,
        environment,
        repairTamper: repairCache,
        build: outDir => runBuildChild({ worker, roots, appDir, mode: buildMode, outDir, environment: buildEnvironment }),
      })
    }
    const identity = cache?.outputHash || 'source'
    if (mode !== 'file') {
      serverInfo = await listen(appDir, mode, worker, identity, fixedPort)
      roots.push(serverInfo.pid)
    }
    const url = serverInfo?.url || ''
    for (const declaration of cases) {
      const oracle = resolve(declaration.path)
      const classification = await classifyOracle(oracle, declaration.format)
      const result = await runChild({
        worker, oracle, classification, args: declaration.args || [], cwd: dirname(oracle),
        env: childEnvironment(worker, url, environment), timeoutMs: declaration.timeoutMs || timeoutMs, roots, signal,
      })
      if (!result.ownershipError) {
        try { await waitForCaseProcesses(worker, roots) } catch (error) { result.ownershipError = error }
      }
      rows.push({ name: declaration.name, path: oracle, format: classification.format, sourceSha256: classification.sha256, ...result })
      if (result.outputBytes <= 0 || result.outputLines <= 0) failure ||= new VerifyError('EMPTY_EVIDENCE', `${declaration.name} produced no evidence`, { result })
      if (result.ownershipError) failure ||= result.ownershipError
      else if (result.timedOut) failure ||= new VerifyError('CASE_TIMEOUT', `${declaration.name} timed out`, { result })
      else if (result.cancelled) failure ||= new VerifyError('RUN_CANCELLED', `${declaration.name} was cancelled`, { result })
      else if (result.code !== 0) failure ||= new VerifyError('CASE_FAILED', `${declaration.name} exited ${result.code}`, { result })
    }
    if (rows.length !== cases.length) throw new VerifyError('INCOMPLETE_INVENTORY', `Executed ${rows.length}/${cases.length} declarations`)
    await processEvidence(worker, roots, 'before-cleanup')
    if (failure) throw failure
  } catch (error) {
    failure = error instanceof VerifyError ? error : new VerifyError(error.code || 'RUNNER_FAILURE', error.message)
  } finally {
    try {
      await serverInfo?.server.close()
      if (serverInfo) roots.splice(roots.indexOf(serverInfo.pid), 1)
    } catch (error) { failure ||= new VerifyError('SERVER_CLEANUP', error.message) }
    try { await terminateRoots(worker, roots) } catch (error) { failure = error }
    try {
      if (process.platform === 'win32') {
        const remaining = queryWindowsProcesses().filter(processInfo => processInfo.commandLine.includes(worker.marker))
        if (remaining.length) throw new VerifyError('OWNED_PROCESS_LEAK', `Marker remains after cleanup: ${worker.marker}`)
      }
    } catch (error) { failure = error }
    if (!failure) await rm(worker.markerRoot, { recursive: true, force: true })
  }
  const summary = {
    ok: !failure,
    reason: failure?.code || null,
    message: failure?.message || null,
    mode,
    worker: { root: worker.root, marker: worker.marker, profile: worker.profile, temp: worker.temp },
    port: serverInfo?.port || null,
    identity: cache?.outputHash || (serverInfo ? 'source' : 'file'),
    cache: cache && { key: cache.key, hit: cache.hit, outputHash: cache.outputHash },
    declared: cases.length,
    started: rows.length,
    completed: rows.filter(row => row.completedAt).length,
    rows,
  }
  await writeFile(join(worker.logs, 'summary.json'), `${JSON.stringify(summary, null, 2)}\n`)
  if (failure) throw Object.assign(failure, { summary })
  return summary
}

export async function runBatch({ workers = 1, declarations, ...options }) {
  validateCases(declarations)
  if (workers > 1 && declarations.some(item => item.parallelSafe !== true)) {
    throw new VerifyError('UNSAFE_PARALLELISM', 'Every case must declare parallelSafe=true when workers > 1')
  }
  if (workers <= 1) return [await runWorker({ ...options, cases: declarations })]
  const groups = Array.from({ length: Math.min(workers, declarations.length) }, () => [])
  declarations.forEach((item, index) => groups[index % groups.length].push(item))
  return Promise.all(groups.map(cases => runWorker({ ...options, cases })))
}

if (process.argv.includes('--studio-host')) {
  const index = process.argv.indexOf('--studio-host')
  const config = JSON.parse(Buffer.from(process.argv[index + 1], 'base64url').toString('utf8'))
  let host
  try {
    host = await startHost(config)
    process.send?.({ ready: true, port: host.port })
    process.on('message', async message => {
      if (!message?.close) return
      await host.close()
      process.exit(0)
    })
  } catch (error) {
    process.send?.({ ready: false, code: error.code || 'SERVER_START', message: error.message })
    process.exit(error.code === 'PORT_COLLISION' ? 98 : 1)
  }
}

if (process.argv.includes('--studio-build')) {
  const index = process.argv.indexOf('--studio-build')
  const config = JSON.parse(Buffer.from(process.argv[index + 1], 'base64url').toString('utf8'))
  try {
    await viteBuild({
      root: config.appDir,
      mode: config.mode,
      configLoader: 'native',
      logLevel: 'info',
      build: { outDir: config.outDir, emptyOutDir: true },
    })
    await delay(1500)
    process.exit(0)
  } catch (error) {
    console.error(error.stack || error)
    process.exit(1)
  }
}