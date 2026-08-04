// Splice the generated accessor block into src/legacy.js.
//
// WHY A SEPARATE STEP. generate-bridge.mjs emits src/testing/bridge-block.js as a SNIPPET for
// textual concatenation, not an importable module — an accessor like `() => RES` only reaches the
// real binding when it is lexically inside the module that declares it. Imported, all 190 accessors
// would throw ReferenceError, because ES modules have no way to alias a live mutable binding into
// a foreign scope.
//
// WHY A MARKED REGION RATHER THAN AN APPEND. An append is not idempotent: run it twice and the file
// carries two accessor blocks, the second shadowing the first, and `Object.defineProperty` on an
// already-defined non-configurable property throws. A delimited region makes re-application a
// replacement, so `npm run bridge:gen && npm run bridge:apply` is safe to run any number of times
// and always leaves exactly one block, always last.
//
//   npm run bridge:apply          splice the current block into src/legacy.js
//   npm run bridge:apply -- --check   verify the spliced region matches the generated block
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const app = resolve(here, '..')
const legacyPath = resolve(app, 'src/legacy.js')
const blockPath = resolve(app, 'src/testing/bridge-block.js')

const BEGIN = '// ==== TEST BRIDGE BEGIN — generated, do not edit (npm run bridge:apply) ===='
const END = '// ==== TEST BRIDGE END ===='

for (const [label, p] of [['src/legacy.js', legacyPath], ['bridge-block.js', blockPath]]) {
  if (!existsSync(p)) {
    console.error(`FATAL: ${label} not found at ${p}`)
    process.exit(2)
  }
}

const block = readFileSync(blockPath, 'utf8').trimEnd()
let legacy = readFileSync(legacyPath, 'utf8')

const i = legacy.indexOf(BEGIN)
const j = legacy.indexOf(END)
if ((i === -1) !== (j === -1)) {
  console.error('FATAL: src/legacy.js has one bridge marker but not the other — refusing to guess.')
  process.exit(2)
}
if (i !== -1 && j < i) {
  console.error('FATAL: bridge markers are out of order in src/legacy.js.')
  process.exit(2)
}

// LINE ENDINGS ARE NOT CONTENT. src/legacy.js sits in the working tree as CRLF (`git ls-files
// --eol` reports `i/lf w/crlf`) while src/testing/bridge-block.js is LF, and there is no
// .gitattributes to reconcile them. Comparing the two raw made `current === region` impossible, so
// `npm run bridge:verify` reported the region stale on a tree where it had just been applied — a
// gate that is permanently red is as useless as one that never fails, and this one had gone unrun
// long enough that nothing noticed. Compare normalised; WRITE in the file's own ending so the next
// comparison is naturally equal and the file does not become half CRLF and half LF.
const fileUsesCrlf = /\r\n/.test(legacy)
const withFileEol = text => (fileUsesCrlf ? text.replace(/\r?\n/g, '\r\n') : text.replace(/\r\n/g, '\n'))
const sameIgnoringEol = (a, b) => a.replace(/\r\n/g, '\n') === b.replace(/\r\n/g, '\n')
const region = withFileEol(`${BEGIN}\n${block}\n${END}\n`)
const check = process.argv.includes('--check')

if (i === -1) {
  if (check) {
    console.error('FAIL: src/legacy.js carries no bridge region. Run: npm run bridge:apply')
    process.exit(1)
  }
  legacy = legacy.replace(/\s*$/, '\n\n') + region
  writeFileSync(legacyPath, legacy, 'utf8')
  console.log(`bridge: region CREATED in src/legacy.js (${block.split('\n').length} lines)`)
} else {
  // `j + END.length + 1` assumed the line ending after END was ONE character. Under CRLF it kept
  // the \r and dropped the \n, so `current` ended one byte short of `region` and no amount of
  // newline normalisation could make them equal — which is why the region still read as stale
  // immediately after a successful apply. Consume the whole terminator, however long it is.
  let endOfRegion = j + END.length
  if (legacy[endOfRegion] === '\r') endOfRegion++
  if (legacy[endOfRegion] === '\n') endOfRegion++
  const current = legacy.slice(i, endOfRegion)
  if (sameIgnoringEol(current, region)) {
    // Still NOT an early exit. The is-last assertion below has to run on this path too: the region
    // can be byte-identical and still be in the wrong place, because someone appended after it.
    // That is not hypothetical - it happened the first time this script was used, when the
    // service-worker registration was appended to the end of legacy.js and this branch reported
    // "already current" and returned 0 without looking.
    //
    // What it no longer does is FALL THROUGH TO THE WRITE. It used to: the if/else-if chain had no
    // branch that skipped writeFileSync, so `bridge:apply` printed "already current" and then
    // "REPLACED" in the same run, and `--check` would have rewritten a source file on its way to
    // reporting success. A check that mutates what it is checking is not a check.
    console.log(`bridge: region already current (${block.split('\n').length} lines)`)
  } else if (check) {
    console.error('FAIL: the bridge region in src/legacy.js is stale. Run: npm run bridge:apply')
    process.exit(1)
  } else {
    legacy = legacy.slice(0, i) + region + legacy.slice(endOfRegion)
    writeFileSync(legacyPath, legacy, 'utf8')
    console.log(`bridge: region REPLACED in src/legacy.js (${block.split('\n').length} lines)`)
  }
}

// The whole point is that the block ends up INSIDE the module and LAST. Assert both rather than
// trust the splice: anything after it could declare a binding the accessors were meant to close
// over, and a block that is not last would silently miss it.
const after = readFileSync(legacyPath, 'utf8')
const tail = after.slice(after.indexOf(END) + END.length).trim()
if (tail) {
  console.error(`FATAL: ${tail.split('\n').length} line(s) follow the bridge region; it must be last.`)
  process.exit(2)
}
console.log('        region is last in the file, as required')
