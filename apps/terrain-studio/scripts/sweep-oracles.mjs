// Run EVERY _verify_*.js and report each one's exit status.
//
// This exists because `npm run verify` runs _verify_all_canyon.js, which carries a hand-listed 12 of
// the 70 oracles on disk - and the 58 it omits include _verify_digest.js, the byte-identity gate of
// record. "The suite is green" therefore meant something much weaker than it read.
import { spawnSync } from 'node:child_process'
import { readdirSync, mkdirSync, writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const app = resolve(here, '..')
const legacy = resolve(app, 'tests/legacy')
const LOGS = resolve(app, '.sweep-logs')

const skip = new Set(['_verify_all_canyon.js'])

// Oracles that need a flag to BE a gate. _verify_bridge.js is a generator and a gate in one file:
// run bare it REWRITES the frozen contract and exits 0, so sweeping it without --check regenerates
// the baseline and then reports agreement with the thing it just wrote. It cannot fail. The first
// run of this sweep did exactly that, and the contract landed in the working tree as a side effect
// of "verifying" it.
// _verify_pwa.js is the other direction: it needs a flag to be RUNNABLE at all. The service worker
// registers only when import.meta.env.MODE === 'production', deliberately, so the rest of the suite
// never races a cached shell. Against the dev server the oracle is guaranteed to report
// "registrations=0" - a red line that says nothing about the service worker and everything about
// how it was launched. --preview-prod builds and serves production, which is the only mode in which
// its subject exists.
const FLAGS = { '_verify_bridge.js': ['--check'], '_verify_pwa.js': ['--preview-prod'] }
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
  // KEEP THE EVIDENCE. A sweep that reports THAT an oracle failed but not WHY sends you to
  // reproduce it by hand - and the ones that only fail inside a full sweep are exactly the ones
  // that will not reproduce. _verify_build_progress went red here and green every way it was run
  // alone; the reason was in this buffer and thrown away.
  if (code !== 0) {
    mkdirSync(LOGS, { recursive: true })
    writeFileSync(resolve(LOGS, `${f}.log`), out)
  }
  // Oracles do not share a failure vocabulary: some print `FAIL <gate>`, some `GATES FAILED:`,
  // some FATAL, and some only a JSON blob ending in "ok": false. Match all of them, and fall back
  // to the last non-empty line rather than reporting an empty reason.
  const why = code === 0 ? ''
    : (out.match(/^FATAL.*$/m) || out.match(/^\s*FAIL\s+\S.*$/m) || out.match(/GATES FAILED:.*$/m)
      || out.match(/^.*"ok":\s*false.*$/m) || out.match(/SETUP FAILURE.*$/m)
      || [out.trim().split('\n').filter(Boolean).pop() || '(no output)'])[0]
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
