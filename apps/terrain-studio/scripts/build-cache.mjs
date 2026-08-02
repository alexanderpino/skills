import { spawnSync } from 'node:child_process'
import { createHash, randomUUID } from 'node:crypto'
import { mkdir, mkdtemp, readFile, readdir, rename, rm, stat, writeFile } from 'node:fs/promises'
import { dirname, join, relative, resolve, sep } from 'node:path'
import { tmpdir } from 'node:os'
import { createRequire } from 'node:module'
import { build as viteBuild } from 'vite'

const require = createRequire(import.meta.url)
export const CACHE_SCHEMA = 1
export const OUTPUT_HASH_SCHEMA = 1

export class CacheError extends Error {
  constructor(code, message, details = {}) {
    super(message)
    this.name = 'CacheError'
    this.code = code
    this.details = details
  }
}

const sha256 = value => createHash('sha256').update(value).digest('hex')
const normalize = value => value.split(sep).join('/')
const sleep = milliseconds => new Promise(resolvePromise => setTimeout(resolvePromise, milliseconds))

function throwIfAborted(signal) {
  if (signal?.aborted) throw new CacheError('RUN_CANCELLED', 'Build cache operation was cancelled')
}

export function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`
  }
  return JSON.stringify(value)
}

async function regularFiles(root, required = false) {
  const files = []
  const visit = async directory => {
    let entries
    try {
      entries = await readdir(directory, { withFileTypes: true })
    } catch (error) {
      if (!required && error.code === 'ENOENT') return
      throw new CacheError('CACHE_INPUT', `Cannot read cache input ${directory}: ${error.message}`)
    }
    for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
      const path = join(directory, entry.name)
      if (entry.isSymbolicLink()) throw new CacheError('CACHE_INPUT', `Symlink cache input is forbidden: ${path}`)
      if (entry.isDirectory()) await visit(path)
      else if (entry.isFile()) files.push(path)
    }
  }
  await visit(root)
  if (required && files.length === 0) throw new CacheError('CACHE_INPUT', `Required input inventory is empty: ${root}`)
  return files
}

async function inputRecord(appDir, path, required = false) {
  try {
    const info = await stat(path)
    if (!info.isFile()) throw new CacheError('CACHE_INPUT', `Cache input is not a regular file: ${path}`)
    return { path: normalize(relative(appDir, path)), present: true, sha256: sha256(await readFile(path)) }
  } catch (error) {
    if (error instanceof CacheError) throw error
    if (error.code === 'ENOENT' && !required) return { path: normalize(relative(appDir, path)), present: false }
    throw new CacheError('CACHE_INPUT', `Cannot hash cache input ${path}: ${error.message}`)
  }
}

function packageVersion(name, appDir) {
  try {
    return require(require.resolve(`${name}/package.json`, { paths: [appDir] })).version
  } catch (error) {
    throw new CacheError('CACHE_TOOL', `Cannot resolve ${name} version: ${error.message}`)
  }
}

export async function createBuildKey({
  appDir,
  mode,
  command,
  environment = process.env,
  tools,
  runtime,
  schema = CACHE_SCHEMA,
}) {
  if (!mode || !Array.isArray(command) || command.length === 0) {
    throw new CacheError('CACHE_INPUT', 'Build mode and non-empty command argv are required')
  }
  appDir = resolve(appDir)
  const rootDir = resolve(appDir, '..', '..')
  const inventory = []
  for (const directory of ['src', 'public']) {
    for (const path of await regularFiles(join(appDir, directory), directory === 'src')) {
      inventory.push(await inputRecord(appDir, path, true))
    }
  }
  const explicit = [
    [join(appDir, 'index.html'), true],
    [join(appDir, 'package.json'), true],
    [join(rootDir, 'package-lock.json'), true],
    [join(appDir, 'vite.config.ts'), true],
    ...['.env', '.env.local', `.env.${mode}`, `.env.${mode}.local`].map(name => [join(appDir, name), false]),
  ]
  for (const [path, required] of explicit) inventory.push(await inputRecord(appDir, path, required))
  inventory.sort((left, right) => left.path.localeCompare(right.path))
  const paths = inventory.map(record => record.path)
  if (new Set(paths).size !== paths.length) throw new CacheError('CACHE_INPUT', 'Duplicate normalized cache input path')
  const effectiveEnvironment = Object.fromEntries(Object.entries(environment)
    .filter(([key]) => key === 'NODE_ENV' || key.startsWith('VITE_'))
    .sort(([left], [right]) => left.localeCompare(right)))
  const descriptor = {
    schema,
    outputHashSchema: OUTPUT_HASH_SCHEMA,
    mode,
    command: [...command],
    runtime: runtime ?? { node: process.version, platform: process.platform, architecture: process.arch },
    tools: tools ?? { vite: packageVersion('vite', appDir), esbuild: packageVersion('esbuild', appDir) },
    environment: effectiveEnvironment,
    inputs: inventory,
  }
  return { key: sha256(canonicalJson(descriptor)), descriptor }
}

export async function hashDirectory(directory, { requireIndex = false } = {}) {
  const paths = await regularFiles(directory, true)
  const records = []
  const hash = createHash('sha256')
  for (const path of paths) {
    const relativePath = normalize(relative(directory, path))
    const bytes = await readFile(path)
    records.push({ path: relativePath, size: bytes.length, sha256: sha256(bytes) })
    hash.update(`${Buffer.byteLength(relativePath)}:${relativePath}:${bytes.length}:`)
    hash.update(bytes)
  }
  if (requireIndex && !records.some(record => record.path === 'index.html')) {
    throw new CacheError('CACHE_OUTPUT', `Build output has no index.html: ${directory}`)
  }
  return { hash: hash.digest('hex'), files: records }
}

async function copyDirectory(source, destination) {
  await mkdir(destination, { recursive: true })
  for (const path of await regularFiles(source, true)) {
    const target = join(destination, relative(source, path))
    await mkdir(dirname(target), { recursive: true })
    await writeFile(target, await readFile(path), { flag: 'wx' })
  }
}

async function validateEntry(entryDir, expectedKey) {
  let manifest
  try {
    manifest = JSON.parse(await readFile(join(entryDir, 'manifest.json'), 'utf8'))
  } catch (error) {
    throw new CacheError('CACHE_TAMPER', `Missing or invalid cache manifest: ${error.message}`)
  }
  if (manifest.schema !== CACHE_SCHEMA || manifest.key !== expectedKey) {
    throw new CacheError('CACHE_TAMPER', 'Cache manifest schema or key mismatch')
  }
  let actual
  try {
    actual = await hashDirectory(join(entryDir, 'dist'), { requireIndex: true })
  } catch (error) {
    throw new CacheError('CACHE_TAMPER', error.message)
  }
  if (canonicalJson(actual) !== canonicalJson(manifest.output)) {
    throw new CacheError('CACHE_TAMPER', 'Cached dist inventory or hash mismatch', { expected: manifest.output, actual })
  }
  const top = (await readdir(entryDir)).sort()
  if (canonicalJson(top) !== canonicalJson(['dist', 'manifest.json'])) {
    throw new CacheError('CACHE_TAMPER', `Cache entry contains forbidden paths: ${top.join(', ')}`)
  }
  return manifest
}

function processIsAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false
  try {
    process.kill(pid, 0)
    return true
  } catch (error) {
    return error.code === 'EPERM'
  }
}

function windowsProcessCreationDate(pid) {
  if (process.platform !== 'win32' || !Number.isInteger(pid) || pid <= 0) return null
  const command = `(Get-CimInstance Win32_Process -Filter "ProcessId = ${pid}").CreationDate.ToUniversalTime().ToString('o')`
  const result = spawnSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', command], {
    encoding: 'utf8', windowsHide: true,
  })
  return result.status === 0 && result.stdout.trim() ? result.stdout.trim() : null
}

function lockOwnerIsAlive(owner) {
  if (!processIsAlive(owner?.pid)) return false
  if (process.platform !== 'win32') return true
  const currentCreationDate = windowsProcessCreationDate(owner.pid)
  return Boolean(owner.processCreationDate && currentCreationDate === owner.processCreationDate)
}

async function recoverStaleLock(lockDir) {
  let owner
  try {
    owner = JSON.parse(await readFile(join(lockDir, 'owner.json'), 'utf8'))
  } catch {
    const info = await stat(lockDir).catch(() => null)
    if (!info || Date.now() - info.mtimeMs < 1000) return false
  }
  if (owner && lockOwnerIsAlive(owner)) return false
  const staleDir = `${lockDir}.stale-${randomUUID()}`
  try {
    await rename(lockDir, staleDir)
  } catch (error) {
    if (error.code === 'ENOENT' || error.code === 'EACCES' || error.code === 'EPERM') return false
    throw error
  }
  await rm(staleDir, { recursive: true, force: true })
  return true
}

async function withLock(lockDir, signal, callback) {
  const deadline = Date.now() + 120000
  const token = randomUUID()
  while (true) {
    throwIfAborted(signal)
    try {
      await mkdir(lockDir)
      await writeFile(join(lockDir, 'owner.json'), `${canonicalJson({
        pid: process.pid,
        token,
        createdAt: new Date().toISOString(),
        processStartedAt: new Date(Date.now() - process.uptime() * 1000).toISOString(),
        processCreationDate: windowsProcessCreationDate(process.pid),
      })}\n`, { flag: 'wx' })
      break
    } catch (error) {
      if (error.code !== 'EEXIST') throw error
      if (await recoverStaleLock(lockDir)) continue
      if (Date.now() >= deadline) throw new CacheError('CACHE_LOCK', `Timed out waiting for ${lockDir}`)
      await sleep(50)
    }
  }
  try {
    throwIfAborted(signal)
    return await callback()
  } finally {
    const owner = await readFile(join(lockDir, 'owner.json'), 'utf8').then(JSON.parse, () => null)
    if (owner?.token === token) await rm(lockDir, { recursive: true, force: true })
  }
}

async function restore(entryDir, destinationDir, manifest, signal) {
  destinationDir = resolve(destinationDir)
  const parent = dirname(destinationDir)
  await mkdir(parent, { recursive: true })
  const staging = await mkdtemp(join(parent, '.dist-restore-'))
  try {
    throwIfAborted(signal)
    await copyDirectory(join(entryDir, 'dist'), staging)
    throwIfAborted(signal)
    const restored = await hashDirectory(staging, { requireIndex: true })
    if (canonicalJson(restored) !== canonicalJson(manifest.output)) {
      throw new CacheError('CACHE_TAMPER', 'Restored dist does not match manifest')
    }
    await rename(staging, destinationDir)
  } catch (error) {
    await rm(staging, { recursive: true, force: true })
    if (error.code === 'EEXIST' || error.code === 'ENOTEMPTY') {
      throw new CacheError('CACHE_DESTINATION', `Private build destination already exists: ${destinationDir}`)
    }
    throw error
  }
}

export async function ensureBuild({
  appDir,
  cacheRoot = process.env.STUDIO_BUILD_CACHE || join(appDir, 'node_modules', '.cache', 'terrain-studio-builds'),
  mode,
  command = ['vite', 'build', ...(mode === 'test' ? ['--mode', 'test'] : [])],
  environment = process.env,
  tools,
  runtime,
  schema = CACHE_SCHEMA,
  repairTamper = false,
  destinationDir,
  signal,
  build,
}) {
  throwIfAborted(signal)
  const { key, descriptor } = await createBuildKey({ appDir, mode, command, environment, tools, runtime, schema })
  const entryDir = join(resolve(cacheRoot), key)
  const lockDir = `${entryDir}.lock`
  await mkdir(resolve(cacheRoot), { recursive: true })
  return withLock(lockDir, signal, async () => {
    let hit = false
    let manifest
    throwIfAborted(signal)
    try {
      manifest = await validateEntry(entryDir, key)
      hit = true
    } catch (error) {
      const exists = await stat(entryDir).then(() => true, () => false)
      if (exists && error.code === 'CACHE_TAMPER' && !repairTamper) throw error
      if (exists) await rename(entryDir, `${entryDir}.quarantine-${Date.now()}`)
      const staging = await mkdtemp(join(resolve(cacheRoot), `.${key}-`))
      try {
        const stagedDist = join(staging, 'dist')
        throwIfAborted(signal)
        if (build) await build(stagedDist, signal)
        else await viteBuild({ root: appDir, mode, logLevel: 'info', build: { outDir: stagedDist, emptyOutDir: true } })
        throwIfAborted(signal)
        const output = await hashDirectory(stagedDist, { requireIndex: true })
        manifest = { schema: CACHE_SCHEMA, key, descriptor, output, createdAt: new Date().toISOString() }
        await writeFile(join(staging, 'manifest.json'), `${canonicalJson(manifest)}\n`, { flag: 'wx' })
        await rename(staging, entryDir)
      } catch (buildError) {
        await rm(staging, { recursive: true, force: true })
        throw buildError
      }
    }
    throwIfAborted(signal)
    manifest = await validateEntry(entryDir, key)
    if (destinationDir) await restore(entryDir, destinationDir, manifest, signal)
    return {
      key,
      hit,
      outputHash: manifest.output.hash,
      manifest,
      entryDir,
      distDir: destinationDir ? resolve(destinationDir) : join(entryDir, 'dist'),
    }
  })
}