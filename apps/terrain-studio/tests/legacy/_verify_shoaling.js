// S4.7 — do waves shoal and break, or go glassy at the beach?
//
// The shoreline was handled backwards: amplitude was faded to ZERO as the water grew shallower, so
// the sea was flattest exactly where real water is roughest. This oracle fixes the shape of the
// correct behaviour so it cannot quietly revert.
//
// THE PHYSICS, and each clause below is a separate assertion because each can fail alone:
//
//   deep water     depth >= ref: the bottom is not felt and the amplitude is what the author set.
//                  `ref` is HALF THE LONGEST WAVELENGTH — the real deep-water criterion. Referencing
//                  it to wave HEIGHT instead was the first attempt, and the curve exposed it: the
//                  breaking limit bound before Green's law could lift anything, so the wave never
//                  grew, it only got clipped. A gate that only checked "amplitude changes with
//                  depth" would have passed that.
//   shoaling       falling depth: amplitude RISES as (ref/depth)^(1/4). This is the clause the old
//                  code had inverted, so it is the one that matters most.
//   breaking       very shallow: amplitude is capped at 0.78 x depth (McCowan), so it necessarily
//                  falls back to zero at the waterline. Surf rears up and then collapses.
//
// The law is checked in double precision against the module, and the GENERATED GLSL is checked to be
// the same law rather than a second copy of it — the two passes and the oracle all read one source.
const path = require('path')
const fs = require('fs')
const { pathToFileURL } = require('url')

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'no-shoaling',       // the Green's-law gain is removed, so waves never grow in shallow water
  'no-breaking',       // the 0.78*depth cap is removed, so waves tower over dry sand
  'fade-to-zero',      // the ORIGINAL defect: amplitude falls monotonically as depth falls
]
const PATCHES = {
  'no-shoaling': [[
    // ANCHORED ON THE LINE THAT FOLLOWS, because the Green's-law gain is now written twice: once
    // in shoalAmplitude and once in breakFraction, which was added later for the surf criterion.
    // The bare gain line matched both, the patcher refused to guess, and the mutation ABORTED at
    // exit 2 — so gate.py saw a red with no failed=[] and reported 'red but named no gate'. It
    // had been half-armed ever since. The `dry` damping exists only in shoalAmplitude.
    'const gain = Math.min(Math.pow(Math.max(ref / d, 1), 0.25), SHOAL_MAX_GAIN)\n  const dry = Math.min(d * 2, 1)',
    'const gain = 1\n  const dry = Math.min(d * 2, 1)',
  ]],
  'no-breaking': [[
    'return Math.min(ampM * gain, SHOAL_BREAK_RATIO * d) * dry',
    'return ampM * gain * dry',
  ]],
  'fade-to-zero': [[
    'const gain = Math.min(Math.pow(Math.max(ref / d, 1), 0.25), SHOAL_MAX_GAIN)\n  const dry = Math.min(d * 2, 1)',
    'const gain = Math.min(d / Math.max(ref, 1e-6), 1)\n  const dry = Math.min(d * 2, 1)',
  ]],
}
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

;(async () => {
  const src = path.resolve(__dirname, '../../src/core/water-waves.js')
  let M = null, loadErr = null
  try {
    if (!mutation) { M = await import(pathToFileURL(src).href) }
    else {
      let text = fs.readFileSync(src, 'utf8')
      for (const [anchor, repl] of PATCHES[mutation]) {
        const hits = text.split(anchor).length - 1
        if (hits !== 1) { console.error(`FATAL anchor for ${mutation} matched ${hits}, expected 1`); process.exit(2) }
        text = text.replace(anchor, repl)
      }
      M = await import('data:text/javascript;base64,' + Buffer.from(text, 'utf8').toString('base64'))
    }
  } catch (e) { loadErr = String(e.message || e).slice(0, 200) }

  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }
  if (!check('module loads', M !== null, loadErr)) { report(); return }

  const A = 12, REF = 69.3          // a 12 m swell on ~139 m ocean waves
  const f = d => M.shoalAmplitude(A, d, REF)

  // --- deep water is untouched ---------------------------------------------------------------
  check('deep water carries the authored amplitude',
    Math.abs(f(REF * 4) - A) < 1e-9 && Math.abs(f(REF) - A) < 1e-9,
    { atFourRef: f(REF * 4), atRef: f(REF) })

  // --- shoaling: the wave must actually GROW --------------------------------------------------
  // Sampled between the deep-water reference and the depth where breaking takes over. The peak has
  // to exceed the authored height, or nothing shoaled — it only ever got clipped.
  let peak = 0, peakDepth = 0
  for (let d = REF; d > 0.05; d *= 0.97) {
    const a = f(d)
    if (a > peak) { peak = a; peakDepth = d }
  }
  check('waves grow above the authored height as they shoal', peak > A * 1.05,
    { authored: A, peak: +peak.toFixed(3), atDepth: +peakDepth.toFixed(2) })
  check('the peak occurs in shallow water, not deep', peakDepth < REF * 0.6,
    { peakDepth: +peakDepth.toFixed(2), ref: REF })

  // --- breaking: nothing may stand taller than the water under it -----------------------------
  let worstRatio = 0, worstDepth = 0
  for (let d = 0.02; d < REF * 3; d *= 1.05) {
    const r = f(d) / d
    if (r > worstRatio) { worstRatio = r; worstDepth = d }
  }
  check('no wave exceeds the breaking limit', worstRatio <= M.SHOAL_BREAK_RATIO + 1e-9,
    { worstRatio: +worstRatio.toFixed(4), limit: M.SHOAL_BREAK_RATIO, atDepth: +worstDepth.toFixed(3) })

  // --- the waterline is dry --------------------------------------------------------------------
  check('amplitude reaches zero at zero depth', f(0) === 0 && f(-1) === 0, { atZero: f(0), atNegative: f(-1) })
  check('the last half-metre is damped', f(0.1) < A * 0.05, { at10cm: +f(0.1).toFixed(4) })

  // --- the shaders read the same law, not a copy of it -----------------------------------------
  // Comparing the generated text to the constants the CPU used is what stops the two from drifting:
  // a GLSL copy edited by hand would still satisfy every numeric assertion above.
  const glsl = typeof M.glslShoal === 'function' ? M.glslShoal() : ''
  check('the generated GLSL carries the same breaking ratio',
    glsl.includes(M.SHOAL_BREAK_RATIO.toFixed(4)), { has: glsl.includes(M.SHOAL_BREAK_RATIO.toFixed(4)) })
  check('the generated GLSL carries the same gain cap',
    glsl.includes(M.SHOAL_MAX_GAIN.toFixed(4)), { has: glsl.includes(M.SHOAL_MAX_GAIN.toFixed(4)) })
  check('the generated GLSL is deterministic', glsl === M.glslShoal(), null)

  check('assertion inventory non-empty', assertions.length >= 9, assertions.length)
  report()

  function report() {
    let ok = assertions.every(a => a.ok)
    if (mutation) {
      if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
      ok = false
    }
    const failed = assertions.filter(a => !a.ok).map(a => a.name)
    console.log(`${ok ? 'PASS' : 'FAIL'}  shoaling peak=${peak === undefined ? 'n/a' : peak.toFixed(2)}m `
      + `authored=${A}m worstRatio=${worstRatio === undefined ? 'n/a' : worstRatio.toFixed(3)} `
      + `assertions=${assertions.length} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
    if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify(assertions.filter(a => !a.ok), null, 2))
    process.exit(ok ? 0 : 1)
  }
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
