import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { runWorker, VerifyError } from './isolated-verify-runner.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const appDir = resolve(here, '..')
const legacyDir = resolve(appDir, 'tests/legacy')
const argv = process.argv.slice(2)
const modeFlags = argv.filter(argument => ['--source', '--file', '--preview', '--preview-prod'].includes(argument))
if (modeFlags.length > 1) {
  console.error(`INVALID_MODE contradictory modes: ${modeFlags.join(', ')}`)
  process.exit(2)
}
const mode = modeFlags[0]?.slice(2) || 'source'
const own = new Set(['--source', '--file', '--preview', '--preview-prod'])
const targets = argv.filter(argument => !argument.startsWith('--'))
if (targets.length > 1) {
  console.error(`Expected one oracle name, received: ${targets.join(', ')}`)
  process.exit(2)
}
const script = targets[0] || '_verify_all_canyon.js'
const oracle = resolve(legacyDir, script)
const args = argv.filter(argument => argument.startsWith('--') && !own.has(argument.split('=')[0]))
if (!existsSync(oracle)) {
  console.error(`No such verification script: ${script}`)
  process.exit(2)
}

const cancellation = new AbortController()
let signalExitCode = 0
const cancel = exitCode => {
  signalExitCode ||= exitCode
  cancellation.abort()
}
const onSigint = () => cancel(130)
const onSigterm = () => cancel(143)
process.once('SIGINT', onSigint)
process.once('SIGTERM', onSigterm)

try {
  const result = await runWorker({
    appDir,
    mode,
    cases: [{ name: script, path: oracle, args }],
    cacheRoot: process.env.STUDIO_BUILD_CACHE,
    temporaryRoot: process.env.STUDIO_VERIFY_TMP,
    keepWorkerRoot: true,
    signal: cancellation.signal,
  })
  const row = result.rows[0]
  process.stdout.write(readFileSync(row.logPath))
  console.log(`RUNNER mode=${mode} port=${result.port ?? 0} declared=${result.declared} started=${result.started} completed=${result.completed}`)
  if (result.cache) console.log(`BUILD_CACHE ${result.cache.hit ? 'hit' : 'miss'} key=${result.cache.key} output=${result.cache.outputHash}`)
} catch (error) {
  const row = error.summary?.rows?.at(-1)
  if (row?.logPath && existsSync(row.logPath)) process.stdout.write(readFileSync(row.logPath))
  const code = error instanceof VerifyError ? error.code : 'RUNNER_FAILURE'
  console.error(`${code}: ${error.message}`)
  if (error.summary) console.error(`RUNNER declared=${error.summary.declared} started=${error.summary.started} completed=${error.summary.completed}`)
  process.exit(signalExitCode || 1)
} finally {
  process.removeListener('SIGINT', onSigint)
  process.removeListener('SIGTERM', onSigterm)
}
