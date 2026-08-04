#!/usr/bin/env node
// Parse every source module, and say so when one does not.
//
// WHY THIS EXISTS. A syntax error in legacy.js does not present as a syntax error. The page loads,
// the module throws while evaluating, every global it was going to define is simply absent, and the
// first oracle to touch one reports `ReferenceError: nodes is not defined`. That points at the test,
// not at the file with the broken character in it, and it cost three separate debugging cycles.
//
// The specific trap, three times over: legacy.js builds its GLSL inside JS template literals, so a
// BACKTICK inside a GLSL comment terminates the literal early. `// wet is a 0..1 fade` reads fine in
// a diff and destroys the file. The same applies to an unescaped ${ in shader text.
//
// This check turns that into one line naming the file and the line number, before anything launches
// a browser.
import { readdirSync, statSync, readFileSync, writeFileSync, unlinkSync } from 'fs'
import { join, resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import { execFileSync } from 'child_process'
import { tmpdir } from 'os'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const roots = ['src', 'scripts']

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    if (name === 'node_modules' || name.startsWith('.')) continue
    const p = join(dir, name)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (name.endsWith('.js') || name.endsWith('.mjs')) out.push(p)
  }
  return out
}

const files = []
for (const r of roots) {
  try { walk(join(root, r), files) } catch { /* a missing root is reported below as zero files */ }
}

// ABSENCE OF EVIDENCE IS A FAILURE. A glob that matched nothing would otherwise report a clean pass
// over an empty set, which is the exact shape of the vacuous gate this project keeps finding.
if (files.length < 20) {
  console.log(`FAIL  check-syntax scanned only ${files.length} files — expected the whole source tree`)
  process.exit(1)
}

const failures = []
for (const f of files) {
  // `node --check` treats .js as CommonJS, which rejects `import`. Copying to a .mjs is how the
  // same parser is asked to read it as a module.
  const tmp = join(tmpdir(), 'syn-' + Math.abs(hash(f)) + '.mjs')
  try {
    writeFileSync(tmp, readFileSync(f))
    execFileSync(process.execPath, ['--check', tmp], { stdio: 'pipe' })
  } catch (e) {
    const msg = String((e.stderr && e.stderr.toString()) || e.message || '')
    const line = (msg.match(/\.mjs:(\d+)/) || [])[1]
    const why = (msg.match(/^(SyntaxError.*)$/m) || [])[1] || msg.split('\n')[0]
    failures.push({ file: f.slice(root.length + 1), line, why: why.trim().slice(0, 120) })
  } finally {
    try { unlinkSync(tmp) } catch { /* best effort */ }
  }
}

function hash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (Math.imul(h, 31) + s.charCodeAt(i)) | 0; return h }

if (failures.length) {
  for (const f of failures) console.log(`  ${f.file}:${f.line || '?'}  ${f.why}`)
  console.log(`FAIL  check-syntax ${failures.length} of ${files.length} modules do not parse`)
  process.exit(1)
}
console.log(`PASS  check-syntax ${files.length} modules parse`)
