import { spawn, spawnSync } from 'node:child_process'
import { createHash, randomUUID } from 'node:crypto'
import { copyFile, mkdir, mkdtemp, open, readFile, readdir, rm, stat, writeFile } from 'node:fs/promises'
import { createServer as createHttpServer } from 'node:http'
import { createRequire } from 'node:module'
import { tmpdir } from 'node:os'
import { basename, dirname, join, parse as parsePath, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse } from 'acorn'
import { build as viteBuild, createServer as createViteServer, preview as vitePreview } from 'vite'
import { ensureBuild } from './build-cache.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const require = createRequire(import.meta.url)
const bootstrap = resolve(here, 'legacy-oracle-bootstrap.cjs')
const MODES = new Set(['source', 'preview', 'preview-prod', 'file'])
const WINDOWS_MAX_PATH = 259
const WORKER_ROOT_PREFIX = 'terrain-studio-verify-'
export const PLAYWRIGHT_PATH_RESERVE = 48
const sha256 = value => createHash('sha256').update(value).digest('hex')
const delay = milliseconds => new Promise(resolvePromise => setTimeout(resolvePromise, milliseconds))

function throwIfAborted(signal) {
  if (signal?.aborted) throw new VerifyError('RUN_CANCELLED', 'Verification was cancelled')
}

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

function workerPaths(root, marker, processToken) {
  const markerRoot = join(root, marker)
  const tokenRoot = join(markerRoot, processToken)
  return { markerRoot, tokenRoot, profile: join(tokenRoot, 'profile'), temp: join(tokenRoot, 'temp') }
}

function assertPlaywrightPathBudget(paths, base) {
  const measured = { temp: paths.temp.length, profile: paths.profile.length }
  const overBudget = Object.entries(measured).filter(([, length]) => length + PLAYWRIGHT_PATH_RESERVE > WINDOWS_MAX_PATH)
  if (overBudget.length) {
    throw new VerifyError('PROFILE_PATH_BUDGET', `Worker paths exceed the Windows Playwright path budget under ${base}`, {
      base,
      maxPath: WINDOWS_MAX_PATH,
      reservedSuffix: PLAYWRIGHT_PATH_RESERVE,
      measured,
      overBudget: overBudget.map(([name]) => name),
    })
  }
}

function baseFitsPlaywrightPathBudget(base) {
  const prospectiveRoot = join(base, `${WORKER_ROOT_PREFIX}${'x'.repeat(6)}`)
  const paths = workerPaths(prospectiveRoot, 'x'.repeat(36), `studio-process-token-${'x'.repeat(36)}`)
  return paths.temp.length + PLAYWRIGHT_PATH_RESERVE <= WINDOWS_MAX_PATH
    && paths.profile.length + PLAYWRIGHT_PATH_RESERVE <= WINDOWS_MAX_PATH
}

async function selectAutomaticTemporaryBase(temporaryRoot) {
  const requested = resolve(temporaryRoot || process.env.STUDIO_VERIFY_TMP || tmpdir())
  if (process.platform !== 'win32') {
    await mkdir(requested, { recursive: true })
    return requested
  }
  const driveRoot = parsePath(requested).root
  const candidates = [
    requested,
    process.env.STUDIO_VERIFY_TMP && resolve(process.env.STUDIO_VERIFY_TMP),
    driveRoot && join(driveRoot, '.studio-verify'),
    process.env.LOCALAPPDATA && join(resolve(process.env.LOCALAPPDATA), 'Temp', 'studio-verify'),
    join(resolve(tmpdir()), 'studio-verify'),
  ].filter((candidate, index, values) => candidate && values.indexOf(candidate) === index)
  const attempts = []
  for (const candidate of candidates) {
    if (!baseFitsPlaywrightPathBudget(candidate)) {
      attempts.push({ base: candidate, reason: 'path-budget' })
      continue
    }
    try {
      await mkdir(candidate, { recursive: true })
      return candidate
    } catch (error) {
      attempts.push({ base: candidate, reason: error.code || error.message })
    }
  }
  throw new VerifyError('PROFILE_PATH_BUDGET', 'No writable Windows temporary base can fit private Playwright paths', {
    maxPath: WINDOWS_MAX_PATH,
    reservedSuffix: PLAYWRIGHT_PATH_RESERVE,
    attempts,
  })
}

export async function createWorkerRoot({ temporaryRoot, selectedRoot } = {}) {
  const base = selectedRoot ? null : await selectAutomaticTemporaryBase(temporaryRoot)
  const root = selectedRoot ? resolve(selectedRoot) : await mkdtemp(join(base, WORKER_ROOT_PREFIX))
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
  const processToken = `studio-process-token-${randomUUID()}`
  const { markerRoot, tokenRoot, profile, temp } = workerPaths(root, marker, processToken)
  if (process.platform === 'win32') assertPlaywrightPathBudget({ temp, profile }, root)
  const logs = join(root, 'logs')
  await mkdir(markerRoot)
  await mkdir(tokenRoot)
  await Promise.all([mkdir(profile), mkdir(temp), mkdir(logs)])
  return Object.freeze({
    root, markerRoot, marker, markerArgument: `--studio-verify-owner=${marker}`, processToken, tokenRoot, profile, temp, logs,
    ownershipTokens: Object.freeze([
      Object.freeze({ name: 'uuid-marker', value: `--studio-verify-owner=${marker}` }),
      Object.freeze({ name: 'private-root', value: processToken }),
    ]),
  })
}

async function startHost({ appDir, mode, token, identity, fixedPort, distDir }) {
  let vite
  let sourceServer
  const host = '127.0.0.1'
  const headers = { 'x-studio-verify-owner': token, 'x-studio-verify-identity': identity }
  try {
    if (mode === 'source') {
      vite = await createViteServer({
        root: appDir,
        configLoader: 'native',
        logLevel: 'error',
        esbuild: false,
        optimizeDeps: { noDiscovery: true, include: [] },
        server: { host, middlewareMode: true, strictPort: true, headers, hmr: false },
      })
      sourceServer = createHttpServer(vite.middlewares)
      await new Promise((resolvePromise, reject) => {
        sourceServer.once('error', reject)
        sourceServer.listen(fixedPort ?? 0, host, resolvePromise)
      })
    } else {
      if (!distDir) throw new VerifyError('SERVER_START', 'Built preview requires a private dist directory')
      vite = await vitePreview({
        root: appDir,
        configLoader: 'native',
        logLevel: 'error',
        build: { outDir: distDir, emptyOutDir: false },
        preview: { host, port: fixedPort ?? 0, strictPort: true, headers },
      })
    }
  } catch (error) {
    sourceServer?.close()
    await vite?.close()
    const collision = error.code === 'EADDRINUSE' || /port .* already in use/i.test(error.message)
    throw new VerifyError(collision ? 'PORT_COLLISION' : 'SERVER_START', `Server preparation failed: ${error.message}`)
  }
  const httpServer = sourceServer || vite.httpServer
  const address = httpServer.address()
  if (!address || typeof address === 'string' || address.port <= 0) {
    sourceServer?.close()
    await vite?.close()
    throw new VerifyError('SERVER_IDENTITY', 'Host did not report a positive bound port')
  }
  return {
    port: address.port,
    implementation: mode === 'source' ? 'vite-createServer' : 'vite-preview',
    close: async () => {
      if (sourceServer) await new Promise(resolvePromise => sourceServer.close(resolvePromise))
      await vite.close()
    },
  }
}

async function listen(appDir, mode, worker, identity, fixedPort, distDir, signal) {
  throwIfAborted(signal)
  const config = Buffer.from(JSON.stringify({ appDir, mode, token: worker.marker, identity, fixedPort, distDir })).toString('base64url')
  const hostLogPath = join(worker.logs, 'host.log')
  const hostLog = await open(hostLogPath, 'w')
  const ownershipGate = join(worker.markerRoot, `ownership-host-${randomUUID()}.ready`)
  const child = spawn(process.execPath, ['--require', bootstrap, '--', fileURLToPath(import.meta.url), '--studio-host', config, '--', worker.markerArgument], {
    cwd: appDir,
    env: childEnvironment(worker, '', process.env, ownershipGate),
    windowsHide: true,
    detached: process.platform !== 'win32',
    stdio: ['ignore', hostLog.fd, hostLog.fd, 'ipc'],
  })
  const rootIdentity = await establishSpawnOwnership(child, worker, ownershipGate)
  let ready
  let readyTimer
  const abort = () => {
    if (child.exitCode === null) killOwnedRoot(worker, rootIdentity)
  }
  signal?.addEventListener('abort', abort, { once: true })
  if (signal?.aborted) abort()
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
    throw signal?.aborted ? new VerifyError('RUN_CANCELLED', 'Verification was cancelled during host startup') : error
  } finally {
    clearTimeout(readyTimer)
    signal?.removeEventListener('abort', abort)
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
          implementation: ready.implementation,
          pid: child.pid,
          rootIdentity,
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

function childEnvironment(worker, url, environment = process.env, ownershipGate) {
  const result = {
    ...environment,
    STUDIO_URL: url,
    STUDIO_VERIFY_OWNER: worker.marker,
    STUDIO_VERIFY_BROWSER_MARKER: worker.markerArgument,
    STUDIO_VERIFY_PRIVATE_TOKEN: worker.processToken,
    STUDIO_VERIFY_PROCESS_TOKENS: JSON.stringify(worker.ownershipTokens),
    STUDIO_VERIFY_PROFILE: worker.profile,
    TEMP: worker.temp,
    TMP: worker.temp,
    TMPDIR: worker.temp,
  }
  if (ownershipGate) result.STUDIO_VERIFY_OWNERSHIP_GATE = ownershipGate
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
  const rootRecords = new Map(roots.map(root => [typeof root === 'number' ? root : root.pid, root]))
  for (const processInfo of processes) {
    const expected = rootRecords.get(processInfo.pid)
    const identityMatches = typeof expected === 'number' || sameProcessIdentity(processInfo, expected)
    if (expected && identityMatches && processInfo.commandLine.includes(marker)) owned.set(processInfo.pid, processInfo)
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

export function sameProcessIdentity(current, expected) {
  return current?.pid === expected?.pid
    && Number.isFinite(processCreationTime(current.creationDate))
    && processCreationTime(current.creationDate) === processCreationTime(expected.creationDate)
}

function ownershipProof(processInfo, marker, ownershipTokens = []) {
  const tokens = typeof marker === 'object' ? marker.ownershipTokens : [
    { name: 'uuid-marker', value: marker },
    ...ownershipTokens,
  ]
  return tokens.find(token => token.value && processInfo.commandLine.includes(token.value)) || null
}

function workerOwnedProcesses(processes, worker) {
  return processes.filter(processInfo => ownershipProof(processInfo, worker))
}

export function windowsTerminationTargets(processes, roots, marker, ownershipTokens = []) {
  const expectedRoots = new Map(roots.map(root => [typeof root === 'number' ? root : root.pid, root]))
  const excluded = new Set(processes.filter(row => {
    const expected = expectedRoots.get(row.pid)
    return expected && typeof expected !== 'number' && !sameProcessIdentity(row, expected)
  }).map(row => row.pid))
  let changed = true
  while (changed) {
    changed = false
    for (const row of processes) {
      if (excluded.has(row.parentPid) && !excluded.has(row.pid)) {
        excluded.add(row.pid)
        changed = true
      }
    }
  }
  const markerValue = typeof marker === 'object' ? marker.markerArgument : marker
  const rootTargets = ownedProcessTree(processes, roots, markerValue)
    .filter(row => expectedRoots.has(row.pid))
  const markedTargets = processes.filter(row => {
    if (!ownershipProof(row, marker, ownershipTokens) || excluded.has(row.pid)) return false
    const expected = expectedRoots.get(row.pid)
    return !expected || typeof expected === 'number' || sameProcessIdentity(row, expected)
  })
  return [...new Map([...rootTargets, ...markedTargets].map(row => [row.pid, row])).values()]
}

async function establishSpawnOwnership(child, worker, ownershipGate) {
  try {
    let rootIdentity = { pid: child.pid }
    if (process.platform === 'win32') {
      rootIdentity = queryWindowsProcesses().find(row => row.pid === child.pid)
      if (!rootIdentity || !rootIdentity.commandLine.includes(worker.markerArgument)
        || !Number.isFinite(processCreationTime(rootIdentity.creationDate))) {
        throw new VerifyError('OWNERSHIP_UNPROVEN', `Spawned root ${child.pid} has no marked CIM creation identity`)
      }
    }
    await writeFile(ownershipGate, 'owned\n', { flag: 'wx' })
    return rootIdentity
  } catch (error) {
    try { await terminateRoots(worker, []) } catch {}
    throw error
  }
}

function killOwnedRoot(worker, rootIdentity) {
  if (process.platform === 'win32') {
    const current = queryWindowsProcesses().find(row => row.pid === rootIdentity.pid)
    if (sameProcessIdentity(current, rootIdentity) && current.commandLine.includes(worker.markerArgument)) {
      spawnSync('taskkill.exe', ['/PID', String(rootIdentity.pid), '/T', '/F'], { stdio: 'ignore' })
    }
  } else {
    try { process.kill(-rootIdentity.pid, 'SIGKILL') } catch {}
  }
}

async function processEvidence(worker, roots, phase, { allowMarkedStrays = false } = {}) {
  if (process.platform !== 'win32') return []
  let all = queryWindowsProcesses()
  let tree = ownedProcessTree(all, roots, worker.markerArgument)
  if (tree.some(processInfo => !processInfo.commandLine)) {
    const confirmed = queryWindowsProcesses()
    const confirmedByPid = new Map(confirmed.map(processInfo => [processInfo.pid, processInfo]))
    all = all.flatMap(processInfo => {
      if (processInfo.commandLine) return [processInfo]
      const current = confirmedByPid.get(processInfo.pid)
      return sameProcessIdentity(current, processInfo) ? [current] : []
    })
    tree = ownedProcessTree(all, roots, worker.markerArgument)
  }
  const evidence = tree.map(processInfo => ({
    ...processInfo,
    ownershipProof: ownershipProof(processInfo, worker)?.name || null,
  }))
  await writeFile(join(worker.logs, `processes-${phase}.json`), `${JSON.stringify(evidence, null, 2)}\n`)
  const treePids = new Set(tree.map(processInfo => processInfo.pid))
  const strayMarked = workerOwnedProcesses(all, worker).filter(processInfo => !treePids.has(processInfo.pid))
  if (strayMarked.length && !allowMarkedStrays) {
    const code = phase.startsWith('live-') ? 'OWNERSHIP_UNPROVEN' : 'OWNED_PROCESS_LEAK'
    throw new VerifyError(code, `Marked processes are outside the owned tree: ${strayMarked.map(row => row.pid).join(',')}`, { tree, strayMarked })
  }
  const missingMarker = tree.filter(processInfo => !ownershipProof(processInfo, worker))
  if (missingMarker.length) {
    throw new VerifyError('OWNERSHIP_UNPROVEN', `Owned descendants lack marker: ${missingMarker.map(row => row.pid).join(',')}`, { tree })
  }
  return evidence
}

async function terminateRoots(worker, roots) {
  if (process.platform === 'win32') {
    const before = queryWindowsProcesses()
    const targets = windowsTerminationTargets(before, roots, worker)
    for (const target of targets) {
      const current = queryWindowsProcesses().find(row => row.pid === target.pid)
      if (sameProcessIdentity(current, target) && ownershipProof(current, worker)) {
        spawnSync('taskkill.exe', ['/PID', String(target.pid), '/T', '/F'], { stdio: 'ignore' })
      }
    }
    await delay(150)
    const after = queryWindowsProcesses()
    const remainingMarked = workerOwnedProcesses(after, worker)
    if (remainingMarked.length) {
      throw new VerifyError('OWNED_PROCESS_LEAK', `Owned marker remains: ${remainingMarked.map(row => row.pid).join(',')}`, { remainingMarked })
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
    const persistentPids = new Set(ownedProcessTree(processes, roots, worker.markerArgument).map(processInfo => processInfo.pid))
    const remaining = workerOwnedProcesses(processes, worker).filter(processInfo => !persistentPids.has(processInfo.pid))
    if (remaining.length === 0) return
    if (Date.now() >= deadline) {
      throw new VerifyError('OWNED_PROCESS_LEAK', `Marked case processes remain: ${remaining.map(row => row.pid).join(',')}`, { remaining })
    }
    await delay(100)
  }
}

async function runChild({ worker, oracle, classification, args, cwd, env, timeoutMs, roots, signal }) {
  const logPath = join(worker.logs, `${basename(oracle)}-${Date.now()}.log`)
  const spawnAuditPath = join(worker.logs, `spawns-${basename(oracle)}-${Date.now()}.jsonl`)
  const log = await open(logPath, 'w')
  const marker = worker.markerArgument
  const nodeArgs = classification.format === 'commonjs'
    ? ['--', bootstrap, marker, '--oracle', oracle, ...args]
    : ['--require', bootstrap, '--', oracle, marker, ...args]
  const startedAt = new Date().toISOString()
  const ownershipGate = join(worker.markerRoot, `ownership-case-${randomUUID()}.ready`)
  const child = spawn(process.execPath, nodeArgs, {
    cwd, env: { ...env, STUDIO_VERIFY_OWNERSHIP_GATE: ownershipGate, STUDIO_VERIFY_SPAWN_AUDIT: spawnAuditPath }, windowsHide: true,
    detached: process.platform !== 'win32', stdio: ['ignore', log.fd, log.fd],
  })
  const rootIdentity = await establishSpawnOwnership(child, worker, ownershipGate)
  let timedOut = false
  let cancelled = false
  let ownershipError
  const stopChild = () => {
    if (child.exitCode !== null) return
    killOwnedRoot(worker, rootIdentity)
  }
  const timeout = setTimeout(() => {
    timedOut = true
    stopChild()
  }, timeoutMs)
  const abort = () => { cancelled = true; stopChild() }
  signal?.addEventListener('abort', abort, { once: true })
  if (signal?.aborted) abort()
  const liveEvidence = (async () => {
    if (process.platform !== 'win32') return
    let sequence = 0
    while (child.exitCode === null && !ownershipError) {
      try { await processEvidence(worker, [...roots, rootIdentity], `live-${child.pid}-${sequence++}`, { allowMarkedStrays: true }) } catch (error) {
        ownershipError = error
        stopChild()
      }
      if (child.exitCode === null && !ownershipError) await delay(25)
    }
  })()
  const exit = await new Promise((resolvePromise, reject) => {
    child.once('error', reject)
    child.once('exit', (code, signal) => resolvePromise({ code: code ?? 1, signal }))
  })
  clearTimeout(timeout)
  signal?.removeEventListener('abort', abort)
  await liveEvidence
  await log.close()
  const spawnAudit = await readFile(spawnAuditPath, 'utf8').catch(error => error.code === 'ENOENT' ? '' : Promise.reject(error))
  const unmarkedSpawns = spawnAudit.split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line)).filter(row => !row.proven)
  if (unmarkedSpawns.length) {
    ownershipError ||= new VerifyError('OWNERSHIP_UNPROVEN', `Child spawned markerless processes: ${unmarkedSpawns.map(row => row.pid).join(',')}`, { unmarkedSpawns })
  }
  const output = await readFile(logPath)
  return {
    ...exit, pid: child.pid, rootCreationDate: rootIdentity.creationDate || null,
    argv: [process.execPath, ...nodeArgs], startedAt, completedAt: new Date().toISOString(),
    outputBytes: output.length, outputLines: output.length ? output.toString('utf8').split(/\r?\n/).filter(Boolean).length : 0, logPath,
    timedOut, cancelled, ownershipError,
  }
}

async function runBuildChild({ worker, roots, appDir, mode, outDir, environment, signal }) {
  throwIfAborted(signal)
  const logPath = join(worker.logs, `build-${mode}.log`)
  const log = await open(logPath, 'w')
  const config = Buffer.from(JSON.stringify({ appDir, mode, outDir })).toString('base64url')
  const ownershipGate = join(worker.markerRoot, `ownership-build-${randomUUID()}.ready`)
  const child = spawn(process.execPath, ['--require', bootstrap, '--', fileURLToPath(import.meta.url), '--studio-build', config, '--', worker.markerArgument], {
    cwd: appDir,
    env: childEnvironment(worker, '', environment, ownershipGate),
    windowsHide: true,
    detached: process.platform !== 'win32',
    stdio: ['ignore', log.fd, log.fd],
  })
  const rootIdentity = await establishSpawnOwnership(child, worker, ownershipGate)
  let ownershipError
  let cancelled = false
  const abort = () => {
    cancelled = true
    if (child.exitCode === null) killOwnedRoot(worker, rootIdentity)
  }
  signal?.addEventListener('abort', abort, { once: true })
  if (signal?.aborted) abort()
  const liveEvidence = (async () => {
    if (process.platform !== 'win32') return
    let sequence = 0
    while (child.exitCode === null && !ownershipError) {
      try { await processEvidence(worker, [...roots, rootIdentity], `live-build-${child.pid}-${sequence++}`) } catch (error) { ownershipError = error }
      if (child.exitCode === null && !ownershipError) await delay(25)
    }
  })()
  const exit = await new Promise((resolvePromise, reject) => {
    child.once('error', reject)
    child.once('exit', code => resolvePromise(code ?? 1))
  })
  await liveEvidence
  signal?.removeEventListener('abort', abort)
  await log.close()
  if (cancelled) throw new VerifyError('RUN_CANCELLED', 'Verification was cancelled during build', { logPath })
  if (ownershipError) throw ownershipError
  if (exit !== 0) throw new VerifyError('BUILD_FAILED', `Marked Vite build exited ${exit}`, { logPath })
  if ((await readFile(logPath)).length === 0) throw new VerifyError('EMPTY_EVIDENCE', 'Marked Vite build produced no output', { logPath })
}

async function markedBuildEnvironment(worker, environment) {
  if (process.platform !== 'win32') return environment
  const packagePath = require.resolve('@esbuild/win32-x64/package.json')
  const source = resolve(dirname(packagePath), 'esbuild.exe')
  const target = join(worker.tokenRoot, 'esbuild.exe')
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
  throwIfAborted(signal)
  appDir = resolve(appDir)
  const worker = await createWorkerRoot({ temporaryRoot, selectedRoot })
  const roots = []
  const rows = []
  let serverInfo
  let cache = null
  let failure
  try {
    if (mode === 'preview' || mode === 'preview-prod') {
      throwIfAborted(signal)
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
        destinationDir: join(worker.markerRoot, `dist-${buildMode}`),
        signal,
        build: (outDir, buildSignal) => runBuildChild({
          worker, roots, appDir, mode: buildMode, outDir, environment: buildEnvironment, signal: buildSignal,
        }),
      })
    }
    const identity = cache?.outputHash || 'source'
    if (mode !== 'file') {
      throwIfAborted(signal)
      serverInfo = await listen(appDir, mode, worker, identity, fixedPort, cache?.distDir, signal)
      roots.push(serverInfo.rootIdentity)
    }
    const url = serverInfo?.url || ''
    for (const declaration of cases) {
      throwIfAborted(signal)
      const oracle = resolve(declaration.path)
      const classification = await classifyOracle(oracle, declaration.format)
      const result = await runChild({
        worker, oracle, classification, args: declaration.args || [], cwd: dirname(oracle),
        env: childEnvironment(worker, url, environment), timeoutMs: declaration.timeoutMs || timeoutMs, roots, signal,
      })
      const sourceAfterExit = await readFile(oracle)
      if (sha256(sourceAfterExit) !== classification.sha256 || !sourceAfterExit.equals(classification.bytes)) {
        result.sourceIdentityError = new VerifyError('ORACLE_BYTES_CHANGED', `${declaration.name} changed after execution`, {
          beforeSha256: classification.sha256,
          afterSha256: sha256(sourceAfterExit),
        })
      }
      if (!result.ownershipError) {
        try { await waitForCaseProcesses(worker, roots) } catch (error) { result.ownershipError = error }
      }
      rows.push({ name: declaration.name, path: oracle, format: classification.format, sourceSha256: classification.sha256, ...result })
      if (result.outputBytes <= 0 || result.outputLines <= 0) failure ||= new VerifyError('EMPTY_EVIDENCE', `${declaration.name} produced no evidence`, { result })
      if (result.ownershipError) failure ||= result.ownershipError
      else if (result.sourceIdentityError) failure ||= result.sourceIdentityError
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
      if (serverInfo) roots.splice(roots.indexOf(serverInfo.rootIdentity), 1)
    } catch (error) { failure ||= new VerifyError('SERVER_CLEANUP', error.message) }
    try { await terminateRoots(worker, roots) } catch (error) { failure = error }
    try {
      if (process.platform === 'win32') {
        const remaining = workerOwnedProcesses(queryWindowsProcesses(), worker)
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
    worker: {
      root: worker.root, marker: worker.marker, profile: worker.profile, temp: worker.temp,
      processToken: worker.processToken, tokenRoot: worker.tokenRoot,
    },
    port: serverInfo?.port || null,
    hostImplementation: serverInfo?.implementation || null,
    identity: cache?.outputHash || (serverInfo ? 'source' : 'file'),
    cache: cache && { key: cache.key, hit: cache.hit, outputHash: cache.outputHash, distDir: cache.distDir },
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

export async function runModePartitions(modes, signal, execute) {
  const completed = []
  for (const mode of modes) {
    if (signal?.aborted) break
    completed.push(await execute(mode))
    if (signal?.aborted) break
  }
  return completed
}

if (process.argv.includes('--studio-host')) {
  const index = process.argv.indexOf('--studio-host')
  const config = JSON.parse(Buffer.from(process.argv[index + 1], 'base64url').toString('utf8'))
  let host
  try {
    host = await startHost(config)
    process.send?.({ ready: true, port: host.port, implementation: host.implementation })
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