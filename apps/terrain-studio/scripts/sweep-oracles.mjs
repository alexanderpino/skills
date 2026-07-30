// Run EVERY _verify_*.js and report each one's exit status.
//
// This exists because `npm run verify` runs _verify_all_canyon.js, which carries a hand-listed 12 of
// the 70 oracles on disk - and the 58 it omits include _verify_digest.js, the byte-identity gate of
// record. "The suite is green" therefore meant something much weaker than it read.
import { spawnSync } from 'node:child_process'
import { readdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const app = resolve(here, '..')
const legacy = resolve(app, 'tests/legacy')

const skip = new Set(['_verify_all_canyon.js'])

// Oracles that need a flag to BE a gate. _verify_bridge.js is a generator and a gate in one file:
// run bare it REWRITES the frozen contract and exits 0, so sweeping it without --check regenerates
// the baseline and then reports agreement with the thing it just wrote. It cannot fail. The first
// run of this sweep did exactly that, and the contract landed in the working tree as a side effect
// of "verifying" it.
const FLAGS = { '_verify_bridge.js': ['--check'] }
const only = process.argv.slice(2).filter((a) => !a.startsWith('--'))
const files = readdirSync(legacy)
  .filter((f) => /^_verify_.*\.js$/.test(f) && !skip.has(f))
  .filter((f) => !only.length || only.includes(f))
  .sort()

const rows = []
for (const f of files) {
  const t0 = Date.now()
  const r = spawnSync(process.execPath, [resolve(here, 'run-legacy-verify.mjs'), f, ...(FLAGS[f] || [])],
    { cwd: app, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 })
  const code = r.status ?? -1
  const out = `${r.stdout || ''}${r.stderr || ''}`
  const why = code === 0 ? ''
    : (out.match(/^FATAL.*$/m) || out.match(/^\s*FAIL\s+\S.*$/m) || out.match(/GATES FAILED:.*$/m) || [''])[0]
  rows.push({ f, code, s: ((Date.now() - t0) / 1000).toFixed(0), why: why.trim().slice(0, 110) })
  console.log(`${code === 0 ? 'ok  ' : 'FAIL'} ${f.padEnd(36)} ${rows.at(-1).s}s  ${rows.at(-1).why}`)
}

const bad = rows.filter((r) => r.code !== 0)
console.log(`\n${rows.length - bad.length}/${rows.length} green`)
if (bad.length) {
  console.log('\nFAILING:')
  for (const r of bad) console.log(`  ${r.f}  exit=${r.code}  ${r.why}`)
}
process.exit(bad.length ? 1 : 0)
