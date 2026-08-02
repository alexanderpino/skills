const Module = require('node:module')
const fs = require('node:fs')
const path = require('node:path')
const crypto = require('node:crypto')

const markerPrefix = '--studio-verify-owner='
const marker = process.argv.find(argument => argument.startsWith(markerPrefix))
if (marker) process.argv = process.argv.filter(argument => argument !== marker)

const ownershipGate = process.env.STUDIO_VERIFY_OWNERSHIP_GATE
if (ownershipGate) {
  const gateDeadline = Date.now() + 30000
  while (!fs.existsSync(ownershipGate)) {
    if (Date.now() >= gateDeadline) throw new Error('OWNERSHIP_GATE timed out')
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10)
  }
  fs.rmSync(ownershipGate, { force: true })
  delete process.env.STUDIO_VERIFY_OWNERSHIP_GATE
}

const browserMarker = process.env.STUDIO_VERIFY_BROWSER_MARKER
const processTokens = (() => {
  try { return JSON.parse(process.env.STUDIO_VERIFY_PROCESS_TOKENS || '[]') }
  catch { return [] }
})()
const spawnAudit = process.env.STUDIO_VERIFY_SPAWN_AUDIT
if (spawnAudit) {
  const childProcess = require('node:child_process')
  const originalSpawn = childProcess.spawn
  childProcess.spawn = function auditedSpawn(command, args) {
    const child = Reflect.apply(originalSpawn, this, arguments)
    const commandLine = [command, ...(Array.isArray(args) ? args : [])].map(String).join(' ')
    const proof = processTokens.find(token => token.value && commandLine.includes(token.value))
    fs.appendFileSync(spawnAudit, `${JSON.stringify({
      pid: child.pid,
      commandLine,
      marked: Boolean(browserMarker && commandLine.includes(browserMarker)),
      proven: Boolean(proof),
      ownershipProof: proof?.name || null,
    })}\n`)
    return child
  }
  Module.syncBuiltinESMExports()
}

if (browserMarker) {
  try {
    const { chromium } = require('playwright-core')
    const launch = chromium.launch.bind(chromium)
    chromium.launch = options => launch({ ...options, args: [...(options?.args || []), browserMarker] })
  } catch {
    // Static oracles do not load Playwright.
  }
}

if (require.main === module) {
  const separator = process.argv.indexOf('--oracle')
  if (separator < 0 || !process.argv[separator + 1]) {
    console.error('ORACLE_BOOTSTRAP missing --oracle path')
    process.exit(2)
  }
  const oracle = path.resolve(process.argv[separator + 1])
  const oracleArgs = process.argv.slice(separator + 2)
  const legacyRoot = path.dirname(oracle)
  const before = fs.readFileSync(oracle)
  const beforeHash = crypto.createHash('sha256').update(before).digest('hex')
  const originalLoader = Module._extensions['.js']
  let checked = false
  const finish = () => {
    if (checked) return
    checked = true
    Module._extensions['.js'] = originalLoader
    const after = fs.readFileSync(oracle)
    const afterHash = crypto.createHash('sha256').update(after).digest('hex')
    if (beforeHash !== afterHash || !before.equals(after)) {
      console.error(`ORACLE_BYTES_CHANGED before=${beforeHash} after=${afterHash}`)
      process.exitCode = 1
    }
  }
  process.once('beforeExit', finish)
  process.once('exit', finish)
  Module._extensions['.js'] = (module, filename) => {
    if (!path.resolve(filename).startsWith(`${legacyRoot}${path.sep}`) && path.resolve(filename) !== oracle) {
      return originalLoader(module, filename)
    }
    module._compile(fs.readFileSync(filename, 'utf8'), filename)
  }
  process.argv = [process.execPath, oracle, ...oracleArgs]
  try {
    const target = new Module(oracle, module)
    target.filename = oracle
    target.paths = Module._nodeModulePaths(path.dirname(oracle))
    target._compile(before.toString('utf8'), oracle)
  } catch (error) {
    finish()
    throw error
  }
}
