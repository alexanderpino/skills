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

const region = `${BEGIN}\n${block}\n${END}\n`
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
  const current = legacy.slice(i, j + END.length + 1)
  if (current === region) {
    console.log(`bridge: region already current (${block.split('\n').length} lines)`)
    process.exit(0)
  }
  if (check) {
    console.error('FAIL: the bridge region in src/legacy.js is stale. Run: npm run bridge:apply')
    process.exit(1)
  }
  legacy = legacy.slice(0, i) + region + legacy.slice(j + END.length + 1)
  writeFileSync(legacyPath, legacy, 'utf8')
  console.log(`bridge: region REPLACED in src/legacy.js (${block.split('\n').length} lines)`)
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
