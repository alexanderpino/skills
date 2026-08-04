// ADR-005's measured height frame, and the property that forced there to be two of them.
//
// The decision on record: the viewport keeps autolevel, physical nodes take metres from a stable
// datum through an explicit adapter. This gate does not assert that decision — it MEASURES the
// property the decision rests on, so a future change that quietly re-merges the frames fails here
// rather than in a conservation identity three stories later.
//
// The load-bearing measurement is frameDriftUnderLocalEdit: change ONE sample and ask how much the
// metre value of every OTHER sample moved. Under a stable frame that is exactly zero. Under
// autolevel it is non-zero everywhere as soon as the edited sample moves the field's min or max —
// bedrock nobody touched changes elevation. That is the whole argument, expressed as a number.
//
// Runs under plain node: the module is pure, and a browser would add flake for nothing.
const path = require('path')
const { pathToFileURL } = require('url')

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'stable-frame-autolevels',      // the stable frame consults the field range after all
  'display-frame-loses-its-guard',// the || 1 guard goes, so a constant field divides by zero
  'roundtrip-drops-the-datum',    // fromMetres forgets the datum, so the round trip is offset
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

// Each mutation REWRITES THE PRODUCTION SOURCE to reproduce a specific defect, then loads that
// text as a module. Nothing here edits an answer: the gates below read what the defective module
// actually computes. Every anchor is asserted to match exactly once, so a patch can never silently
// apply to nothing — which would make the control read "not detected" when the truth is "not
// attempted", the shape that has already cost this project two vacuous rows.
const fs = require('fs')
const NL = '\n'
const PATCHES = {
  'stable-frame-autolevels': [[
    '    for (let i = 0; i < field.length; i++) out[i] = datumM + field[i] * reliefM',
    '    { const e = fieldExtremes(field); const r = (e.max - e.min) || 1' + NL
    + '      for (let i = 0; i < field.length; i++) out[i] = datumM + (field[i] - e.min) / r * reliefM }',
  ]],
  'display-frame-loses-its-guard': [[
    '  const range = (mx - mn) || 1',
    '  const range = (mx - mn)',
  ]],
  'roundtrip-drops-the-datum': [[
    "    for (let i = 0; i < metres.length; i++) out[i] = (metres[i] - datumM) / reliefM",
    "    for (let i = 0; i < metres.length; i++) out[i] = metres[i] / reliefM",
  ]],
}

;(async () => {
  const srcPath = path.resolve(__dirname, '../../src/core/height-frame.js')
  let M
  if (!mutation) {
    M = await import(pathToFileURL(srcPath).href)
  } else {
    let text = fs.readFileSync(srcPath, 'utf8')
    for (const [anchor, replacement] of PATCHES[mutation]) {
      const hits = text.split(anchor).length - 1
      if (hits !== 1) { console.error(`FATAL patch anchor for ${mutation} matched ${hits} times, expected exactly 1`); process.exit(2) }
      text = text.replace(anchor, replacement)
    }
    M = await import('data:text/javascript;base64,' + Buffer.from(text, 'utf8').toString('base64'))
  }

  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }

  const DATUM = 120, RELIEF = 2600
  // A field whose min and max sit at known indices, so a local edit can be aimed at one that moves
  // the range and one that does not.
  const N = 64
  const field = new Float32Array(N)
  for (let i = 0; i < N; i++) field[i] = 0.25 + 0.5 * Math.sin(i * 0.37) * 0.5 + 0.25
  // The min and max must NOT be 0 and 1. A field spanning exactly [0,1] has range 1 and offset 0,
  // which makes autolevel algebraically identical to the stable frame — the first run of this gate
  // used 0.0/1.0 and failed its own "the two frames genuinely differ" check, correctly. A fixture
  // that cannot distinguish the two things under test proves nothing about either.
  field[7] = 0.12       // the minimum
  field[41] = 0.83      // the maximum

  // --- the two frames, converted -------------------------------------------------------------
  const stable = M.toMetres(field, { frame: 'physical-stable', datumM: DATUM, reliefM: RELIEF })
  const display = M.toMetres(field, { frame: 'display-autolevel', datumM: DATUM, reliefM: RELIEF })

  // The display frame must reproduce metricHeightField's arithmetic exactly. Computed here in
  // double precision from the same inputs rather than copied from production.
  let mn = Infinity, mx = -Infinity
  for (let i = 0; i < N; i++) { if (field[i] < mn) mn = field[i]; if (field[i] > mx) mx = field[i] }
  const range = (mx - mn) || 1
  let maxDisplayErr = 0, maxStableErr = 0
  for (let i = 0; i < N; i++) {
    maxDisplayErr = Math.max(maxDisplayErr, Math.abs(display[i] - (DATUM + (field[i] - mn) / range * RELIEF)))
    maxStableErr = Math.max(maxStableErr, Math.abs(stable[i] - (DATUM + field[i] * RELIEF)))
  }
  // float32 storage of a value near DATUM+RELIEF: one ulp at 2720 is ~2.4e-4.
  const ULP_BOUND = 3e-4
  check('display frame matches the autolevel formula', maxDisplayErr <= ULP_BOUND, maxDisplayErr)
  check('stable frame matches datum + f * relief', maxStableErr <= ULP_BOUND, maxStableErr)
  check('the two frames genuinely differ', (() => {
    for (let i = 0; i < N; i++) if (Math.abs(stable[i] - display[i]) > 1) return true
    return false
  })(), null)

  // --- THE PROPERTY ---------------------------------------------------------------------------
  // Edit the sample that IS the maximum. Under a stable frame nothing else may move at all.
  const editIndex = 41, delta = 0.5
  const stableDrift = M.frameDriftUnderLocalEdit(field, { frame: 'physical-stable', datumM: DATUM, reliefM: RELIEF, index: editIndex, delta })
  const displayDrift = M.frameDriftUnderLocalEdit(field, { frame: 'display-autolevel', datumM: DATUM, reliefM: RELIEF, index: editIndex, delta })

  check('a local edit moves only that sample in the stable frame', stableDrift.maxElsewhere <= ULP_BOUND, stableDrift)
  check('the stable frame did register the edit itself', stableDrift.atIndex > 1, stableDrift)
  // The converse, and the reason two frames exist: under autolevel, untouched bedrock moves.
  check('the same edit moves untouched samples under autolevel', displayDrift.maxElsewhere > 1, displayDrift)
  check('frameIsFieldDependent agrees with what was measured',
    M.frameIsFieldDependent('display-autolevel') === true && M.frameIsFieldDependent('physical-stable') === false, null)

  // --- degenerate range -----------------------------------------------------------------------
  const constant = new Float32Array(16).fill(0.5)
  let constDisplay = null, constThrew = null
  try { constDisplay = M.toMetres(constant, { frame: 'display-autolevel', datumM: DATUM, reliefM: RELIEF }) }
  catch (e) { constThrew = String(e.message || e) }
  check('a constant field maps to the datum, not NaN',
    constThrew === null && constDisplay && constDisplay.every(v => Number.isFinite(v) && Math.abs(v - DATUM) <= ULP_BOUND),
    constThrew || (constDisplay && constDisplay[0]))

  // --- round trip -----------------------------------------------------------------------------
  const back = M.fromMetres(stable, { frame: 'physical-stable', datumM: DATUM, reliefM: RELIEF })
  let maxRoundTrip = 0
  for (let i = 0; i < N; i++) maxRoundTrip = Math.max(maxRoundTrip, Math.abs(back[i] - field[i]))
  check('the stable frame round-trips', maxRoundTrip <= 1e-6, maxRoundTrip)
  // And the display frame refuses to be inverted without the information it discarded.
  let invErr = null
  try { M.fromMetres(display, { frame: 'display-autolevel', datumM: DATUM, reliefM: RELIEF }) }
  catch (e) { invErr = e.code }
  check('autolevel refuses to invert without its original range', invErr === 'FRAME_RANGE_DEGENERATE', invErr)

  // --- refusals -------------------------------------------------------------------------------
  const codeOf = fn => { try { fn(); return null } catch (e) { return e.code } }
  check('an unknown frame is refused', codeOf(() => M.toMetres(field, { frame: 'guess', reliefM: RELIEF })) === 'FRAME_UNKNOWN')
  check('a zero relief is refused', codeOf(() => M.toMetres(field, { frame: 'physical-stable', reliefM: 0 })) === 'FRAME_RELIEF_INVALID')
  check('a non-finite datum is refused', codeOf(() => M.toMetres(field, { frame: 'physical-stable', reliefM: RELIEF, datumM: NaN })) === 'FRAME_DATUM_INVALID')

  // Absence of evidence is a failure: a run that compared nothing is red.
  check('assertion inventory non-empty', assertions.length >= 13, assertions.length)

  let ok = assertions.every(a => a.ok)
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = assertions.filter(a => !a.ok).map(a => a.name)
  console.log(`${ok ? 'PASS' : 'FAIL'}  height-frame displayErr=${maxDisplayErr.toExponential(2)} stableErr=${maxStableErr.toExponential(2)} `
    + `stableDrift=${stableDrift.maxElsewhere.toExponential(2)} autolevelDrift=${displayDrift.maxElsewhere.toFixed(2)} `
    + `roundTrip=${maxRoundTrip.toExponential(2)} assertions=${assertions.length} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify(assertions.filter(a => !a.ok), null, 2))
  process.exit(ok ? 0 : 1)
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
