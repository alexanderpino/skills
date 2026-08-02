import { createHash } from 'node:crypto'
import { mkdir, mkdtemp, open, readFile, readdir, rename, rm, stat, writeFile } from 'node:fs/promises'
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

async function withLock(lockDir, callback) {
  const deadline = Date.now() + 120000
  while (true) {
    try {
      await mkdir(lockDir)
      break
    } catch (error) {
      if (error.code !== 'EEXIST') throw error
      if (Date.now() >= deadline) throw new CacheError('CACHE_LOCK', `Timed out waiting for ${lockDir}`)
      await sleep(50)
    }
  }
  try {
    return await callback()
  } finally {
    await rm(lockDir, { recursive: true, force: true })
  }
}

async function restore(entryDir, appDir, manifest) {
  const parent = dirname(join(appDir, 'dist'))
  const staging = await mkdtemp(join(parent, '.dist-restore-'))
  try {
    await copyDirectory(join(entryDir, 'dist'), staging)
    const restored = await hashDirectory(staging, { requireIndex: true })
    if (canonicalJson(restored) !== canonicalJson(manifest.output)) {
      throw new CacheError('CACHE_TAMPER', 'Restored dist does not match manifest')
    }
    await rm(join(appDir, 'dist'), { recursive: true, force: true })
    await rename(staging, join(appDir, 'dist'))
  } catch (error) {
    await rm(staging, { recursive: true, force: true })
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
  build,
}) {
  const { key, descriptor } = await createBuildKey({ appDir, mode, command, environment, tools, runtime, schema })
  const entryDir = join(resolve(cacheRoot), key)
  const lockDir = `${entryDir}.lock`
  await mkdir(resolve(cacheRoot), { recursive: true })
  return withLock(lockDir, async () => {
    let hit = false
    let manifest
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
        if (build) await build(stagedDist)
        else await viteBuild({ root: appDir, mode, logLevel: 'info', build: { outDir: stagedDist, emptyOutDir: true } })
        const output = await hashDirectory(stagedDist, { requireIndex: true })
        manifest = { schema: CACHE_SCHEMA, key, descriptor, output, createdAt: new Date().toISOString() }
        await writeFile(join(staging, 'manifest.json'), `${canonicalJson(manifest)}\n`, { flag: 'wx' })
        await rename(staging, entryDir)
      } catch (buildError) {
        await rm(staging, { recursive: true, force: true })
        throw buildError
      }
    }
    manifest = await validateEntry(entryDir, key)
    await restore(entryDir, appDir, manifest)
    return { key, hit, outputHash: manifest.output.hash, manifest, entryDir }
  })
}