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

// EXPECTED-RED REGISTER — tests/legacy/expected-red.json.
//
// A story whose Ready condition demands "the fixture is observed red before implementation" leaves
// a genuinely failing oracle in the tree for a while. Registering it here keeps the sweep honest in
// both directions: a registered oracle that fails is reported as `red (expected)` and does not fail
// the sweep, and a registered oracle that PASSES fails the sweep, because a register nobody prunes
// turns into a standing excuse. An entry naming a file that is not on disk fails the sweep too.
const expectedRedPath = resolve(legacyDir, 'expected-red.json')
let expectedRed = new Map()
if (existsSync(expectedRedPath)) {
  let parsed
  try { parsed = JSON.parse(readFileSync(expectedRedPath, 'utf8')) }
  catch (error) {
    console.error(`EXPECTED_RED_UNREADABLE: ${expectedRedPath}: ${error.message}`)
    process.exit(1)
  }
  for (const entry of (parsed.entries || [])) {
    if (!entry || typeof entry.oracle !== 'string' || typeof entry.story !== 'string' || typeof entry.reason !== 'string') {
      console.error(`EXPECTED_RED_MALFORMED: every entry needs oracle, story and reason: ${JSON.stringify(entry)}`)
      process.exit(1)
    }
    expectedRed.set(entry.oracle, entry)
  }
}
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
// A register entry whose oracle is not on disk is stale, and a stale register is exactly how an
// expected-red exemption outlives the reason for it.
const orphanedRegistrations = [...expectedRed.keys()].filter(name => !discovered.includes(name))

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
    for (const row of error.summary?.rows || []) results.set(row.name, row)
    // A VerifyError means one or more CASES exited non-zero, and whether that fails the SWEEP is
    // decided per row below — a registered expected-red oracle is allowed to be one of them. This
    // used to set failed unconditionally here, which made the register unable to spare anything.
    // Anything that is not a VerifyError is a harness fault and still fails immediately.
    if (!(error instanceof VerifyError)) { failed = true; console.error(error.stack || error) }
  }
})

const expectedRedSeen = []
const unexpectedlyGreen = []
for (const declaration of declarations) {
  const row = results.get(declaration.name)
  if (!row) {
    failed = true
    console.log(`FAIL ${declaration.name.padEnd(36)} not executed`)
    continue
  }
  const output = readFileSync(row.logPath, 'utf8')
  const isRegistered = expectedRed.has(row.name)
  if (row.code !== 0) {
    // A registered expected-red oracle does not fail the sweep — but its log is still retained,
    // because "it is red for the reason we think" has to stay checkable.
    if (!isRegistered) failed = true
    mkdirSync(failureLogs, { recursive: true })
    copyFileSync(row.logPath, resolve(failureLogs, `${row.name}.log`))
  }
  const reason = row.code === 0 ? '' : (output.match(/^FATAL.*$/m) || output.match(/^\s*FAIL\s+\S.*$/m)
    || output.match(/GATES FAILED:.*$/m) || output.match(/^.*"ok":\s*false.*$/m)
    || output.match(/SETUP FAILURE.*$/m) || [output.trim().split('\n').filter(Boolean).pop() || '(no output)'])[0]
  const registered = expectedRed.get(row.name)
  if (registered && row.code !== 0) {
    // Red as declared. Not a sweep failure — but never silent either: it is printed every run with
    // the story that owes it, so it cannot fade into the background.
    expectedRedSeen.push(row.name)
    console.log(`red  ${row.name.padEnd(36)} EXPECTED for ${registered.story}: ${registered.reason.slice(0, 80)}`)
    continue
  }
  if (registered && row.code === 0) {
    failed = true
    unexpectedlyGreen.push(row.name)
    console.log(`FAIL ${row.name.padEnd(36)} registered expected-red for ${registered.story} but PASSED — remove the entry`)
    continue
  }
  console.log(`${row.code === 0 ? 'ok  ' : 'FAIL'} ${row.name.padEnd(36)} bytes=${row.outputBytes} lines=${row.outputLines} ${String(reason).trim().slice(0, 110)}`)
}
const completed = [...results.values()].filter(row => row.completedAt).length
const green = [...results.values()].filter(row => row.code === 0).length
if (orphanedRegistrations.length) {
  failed = true
  console.log(`\nFAIL expected-red register names ${orphanedRegistrations.length} oracle(s) that do not exist: ${orphanedRegistrations.join(', ')}`)
}
console.log(`\nSWEEP discovered=${discovered.length} declared=${declarations.length} started=${results.size} completed=${completed} skipped=${declarations.length - results.size}`)
const expectedRedCount = expectedRedSeen.length
console.log(`${green}/${declarations.length - expectedRedCount} green`
  + (expectedRedCount ? ` · ${expectedRedCount} red as registered (${expectedRedSeen.join(', ')})` : ''))
if (results.size !== declarations.length || completed !== declarations.length) failed = true
process.removeListener('SIGINT', onSigint)
process.removeListener('SIGTERM', onSigterm)
process.exit(signalExitCode || (failed ? 1 : 0))
