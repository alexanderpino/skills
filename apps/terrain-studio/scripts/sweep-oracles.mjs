import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { runModePartitions, runWorker, VerifyError } from './isolated-verify-runner.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const appDir = resolve(here, '..')
const legacyDir = resolve(appDir, process.env.STUDIO_LEGACY_DIR || 'tests/legacy')
const failureLogs = resolve(appDir, '.sweep-logs')
const requested = process.argv.slice(2).filter(argument => !argument.startsWith('--'))
const skip = new Set(['_verify_all_canyon.js'])
const discovered = existsSync(legacyDir) ? readdirSync(legacyDir)
  .filter(name => /^_verify_.*\.js$/.test(name) && !skip.has(name)).sort() : []

if (discovered.length === 0) {
  console.error('EMPTY_INVENTORY: no legacy oracles discovered')
  process.exit(1)
}
const unknown = requested.filter(name => !discovered.includes(name))
if (unknown.length) {
  console.error(`UNKNOWN_ORACLE: ${unknown.join(', ')}`)
  process.exit(1)
}
if (new Set(requested).size !== requested.length) {
  console.error('DUPLICATE_DECLARATION: requested oracle names must be unique')
  process.exit(1)
}
const selected = requested.length ? discovered.filter(name => requested.includes(name)) : discovered
const declarations = selected.map(name => ({
  name,
  path: resolve(legacyDir, name),
  args: name === '_verify_bridge.js' ? ['--check'] : [],
  mode: name === '_verify_pwa.js' ? 'preview-prod' : 'source',
  parallelSafe: false,
}))
if (declarations.length === 0) {
  console.error('EMPTY_INVENTORY: no selected legacy oracles')
  process.exit(1)
}

const workersArgument = process.argv.find(argument => argument.startsWith('--workers='))
const workers = workersArgument ? Number(workersArgument.slice('--workers='.length)) : 1
if (!Number.isInteger(workers) || workers < 1 || workers > 1) {
  console.error('UNSAFE_PARALLELISM: legacy sweep declarations are not parallel-safe')
  process.exit(1)
}
const cancellation = new AbortController()
let signalExitCode = 0
const cancel = exitCode => { signalExitCode ||= exitCode; cancellation.abort() }
const onSigint = () => cancel(130)
const onSigterm = () => cancel(143)
process.once('SIGINT', onSigint)
process.once('SIGTERM', onSigterm)

const results = new Map()
let failed = false
await runModePartitions(['source', 'preview', 'preview-prod'], cancellation.signal, async mode => {
  const cases = declarations.filter(declaration => declaration.mode === mode)
  if (!cases.length) return
  try {
    const summary = await runWorker({
      appDir,
      mode,
      cases,
      cacheRoot: process.env.STUDIO_BUILD_CACHE,
      temporaryRoot: process.env.STUDIO_VERIFY_TMP,
      keepWorkerRoot: true,
      signal: cancellation.signal,
    })
    for (const row of summary.rows) results.set(row.name, row)
  } catch (error) {
    failed = true
    for (const row of error.summary?.rows || []) results.set(row.name, row)
    if (!(error instanceof VerifyError)) console.error(error.stack || error)
  }
})

for (const declaration of declarations) {
  const row = results.get(declaration.name)
  if (!row) {
    failed = true
    console.log(`FAIL ${declaration.name.padEnd(36)} not executed`)
    continue
  }
  const output = readFileSync(row.logPath, 'utf8')
  if (row.code !== 0) {
    failed = true
    mkdirSync(failureLogs, { recursive: true })
    copyFileSync(row.logPath, resolve(failureLogs, `${row.name}.log`))
  }
  const reason = row.code === 0 ? '' : (output.match(/^FATAL.*$/m) || output.match(/^\s*FAIL\s+\S.*$/m)
    || output.match(/GATES FAILED:.*$/m) || output.match(/^.*"ok":\s*false.*$/m)
    || output.match(/SETUP FAILURE.*$/m) || [output.trim().split('\n').filter(Boolean).pop() || '(no output)'])[0]
  console.log(`${row.code === 0 ? 'ok  ' : 'FAIL'} ${row.name.padEnd(36)} bytes=${row.outputBytes} lines=${row.outputLines} ${String(reason).trim().slice(0, 110)}`)
}
const completed = [...results.values()].filter(row => row.completedAt).length
const green = [...results.values()].filter(row => row.code === 0).length
console.log(`\nSWEEP discovered=${discovered.length} declared=${declarations.length} started=${results.size} completed=${completed} skipped=${declarations.length - results.size}`)
console.log(`${green}/${declarations.length} green`)
if (results.size !== declarations.length || completed !== declarations.length) failed = true
process.removeListener('SIGINT', onSigint)
process.removeListener('SIGTERM', onSigterm)
process.exit(signalExitCode || (failed ? 1 : 0))
