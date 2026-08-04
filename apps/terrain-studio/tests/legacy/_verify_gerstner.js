// S4.7 — the shared Gerstner wave core. RED-FIRST, as Sprint 4's Ready condition requires.
//
// This file is written before `src/core/water-waves.js` exists and must fail TODAY by NAMED GATES,
// never by throwing. Everything it touches is guarded, so an absent module reads as
// `failed=[moduleLoads, ...]` rather than as a stack trace, which would prove only that the test is
// broken.
//
// WHAT IS PINNED, AND WHY IT IS PINNED. An acceptance gate written before the implementation has to
// state the contract or it is unimplementable. ADR-006 states it, and this file restates only the
// parts that are checkable arithmetic:
//
//   theta_i = k_i * dot(D_i, xz) - omega_i * t + phi_i
//   x' = x + sum(Q_i A_i D_i.x cos theta_i)
//   y' = datum + sum(A_i sin theta_i)
//   z' = z + sum(Q_i A_i D_i.y cos theta_i)
//   k_i = 2*pi/lambda_i,  omega_i = sqrt(g * k_i)          [deep water]
//   N   = normalize(cross(dP/dz, dP/dx))                   [analytic; finite differences FORBIDDEN]
//
// THE ORACLE COMPUTES ITS OWN ANSWER in double precision from that text, and never reads production
// for it. That is the only way the position/normal gates mean anything: a gate that asked production
// what it produced and then checked production produced it is the shape this project keeps finding.
//
// STEEPNESS 0.85 IS A PROJECT SAFETY CHOICE, NOT A WATER CONSTANT, and ADR-006 says so: chapter 12
// puts the practical compression/foam threshold at 0.5-0.9 and warns that past ~1.0 broad
// negative-Jacobian folding becomes visible. 0.85 keeps crests at the high-quality end with 0.15
// margin. The gate therefore checks BOTH ends — every shipped preset is under it, and an injected
// 1.05 preset is refused — because a bound only one side of which is ever exercised is half a gate.
const path = require('path')
const { pathToFileURL } = require('url')

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'finite-difference-normal',   // the normal comes from sampling, not from the analytic tangents
  'steepness-unclamped',        // sum(Q k A) is allowed past 0.85
  'preset-not-deterministic',   // the same controls expand to different terms
  'harmonic-wavelengths',       // wavelength ratios become integer multiples, so crests repeat
  'zero-amplitude-drifts',      // amplitude 0 no longer returns the datum exactly
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

const G = 9.80665
const TERMS = 12

;(async () => {
  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }

  // --- load production, guarded ----------------------------------------------------------------
  // Each mutation REWRITES THE PRODUCTION SOURCE to reproduce a specific defect and loads that text
  // as a module. Nothing here edits an answer: the gates read what the defective module computes.
  // Every anchor must match exactly once, so a patch can never silently apply to nothing — the
  // "not detected when the truth is not attempted" shape that has cost this project real rows.
  const fs = require('fs')
  const NL = String.fromCharCode(10)
  const PATCHES = {
    'finite-difference-normal': [[
      '    dydx += w.A * dx * k * c',
      '    dydx += w.A * dx * k * c * 1.0002',
    ]],
    'steepness-unclamped': [[
      '  const q = raw > 0 ? Math.min(1, MAX_STEEPNESS / raw) : 0',
      '  const q = 1',
    ]],
    // The drift has to persist ACROSS calls. The first version declared it inside expandPreset, so
    // both expansions reset it and produced identical output — the control was vacuous and the
    // runner said so. A per-call seed offset is what "not deterministic" actually means here.
    'preset-not-deterministic': [[
      '  const rand = rng(Number(controls.seed) || 0)',
      '  globalThis.__wwDrift = (globalThis.__wwDrift || 0) + 1;' + NL
      + '  const rand = rng((Number(controls.seed) || 0) + globalThis.__wwDrift)',
    ]],
    'harmonic-wavelengths': [[
      '    const hits = harmonicPairs(lambdas)',
      '    const hits = []',
    ]],
    'zero-amplitude-drifts': [[
      '  let px = x, py = datumM, pz = z',
      '  let px = x, py = datumM + 1e-7, pz = z',
    ]],
  }

  const src = path.resolve(__dirname, '../../src/core/water-waves.js')
  let M = null, loadErr = null
  try {
    if (!mutation) { M = await import(pathToFileURL(src).href) }
    else {
      let text = fs.readFileSync(src, 'utf8')
      for (const [anchor, repl] of PATCHES[mutation]) {
        const hits = text.split(anchor).length - 1
        if (hits !== 1) { console.error(`FATAL patch anchor for ${mutation} matched ${hits} times, expected 1`); process.exit(2) }
        text = text.replace(anchor, repl)
      }
      M = await import('data:text/javascript;base64,' + Buffer.from(text, 'utf8').toString('base64'))
    }
  } catch (e) { loadErr = String(e.message || e).slice(0, 160) }
  if (!check('module loads', M !== null, loadErr)) {
    // Absent module: report the whole table rather than dying, so the red is diagnostic.
    for (const n of ['expandPreset exists', 'gerstnerAt exists', 'preset has 12 terms',
      'preset is deterministic', 'steepness within 0.85', 'an over-steep preset is refused',
      'position matches the double oracle', 'normal is analytic, not finite-differenced',
      'zero amplitude returns the datum exactly', 'no harmonic wavelength ratios',
      'horizontal Jacobian positive outside the foam band']) check(n, false, 'module absent')
  }

  const CONTROLS = { windDirectionDeg: 300, windSpeedMps: 11, seaState: 0.6, seed: 4242,
    maxAmplitudeM: 1.8, bodyKind: 'ocean' }

  let preset = null
  if (M && typeof M.expandPreset === 'function') {
    check('expandPreset exists', true)
    try { preset = M.expandPreset(CONTROLS) } catch (e) { check('expandPreset runs', false, String(e.message || e)) }
  } else if (M) check('expandPreset exists', false, Object.keys(M).join(','))

  const terms = (preset && Array.isArray(preset.terms)) ? preset.terms : []
  check('preset has 12 terms', terms.length === TERMS, terms.length)

  // --- determinism ------------------------------------------------------------------------------
  if (M && typeof M.expandPreset === 'function' && preset) {
    let again = null
    try { again = M.expandPreset(CONTROLS) } catch (e) { /* reported above */ }
    check('preset is deterministic',
      !!again && JSON.stringify(again.terms) === JSON.stringify(preset.terms),
      again ? 'differs' : 'second expansion threw')
    // ...and a different seed must actually change it, or "deterministic" is satisfied by a constant.
    let other = null
    try { other = M.expandPreset({ ...CONTROLS, seed: CONTROLS.seed + 1 }) } catch (e) {}
    check('a different seed produces a different preset',
      !!other && JSON.stringify(other.terms) !== JSON.stringify(preset.terms))
  }

  // --- the steepness bound, both ends ------------------------------------------------------------
  const steep = terms.reduce((a, t) => a + (t.Q || 0) * (2 * Math.PI / (t.lambda || Infinity)) * (t.A || 0), 0)
  check('steepness within 0.85', terms.length > 0 && steep <= 0.85 + 1e-9, steep)
  check('steepness is not trivially zero', steep > 0.05, steep)
  if (M && typeof M.steepnessOk === 'function') {
    // The named refusal: an injected 1.05 preset must be rejected by production's own check.
    const overSteep = { terms: terms.map(t => ({ ...t, Q: (t.Q || 0) * (1.05 / Math.max(steep, 1e-9)) })) }
    check('an over-steep preset is refused', M.steepnessOk(overSteep) === false)
    check('the shipped preset is accepted', M.steepnessOk(preset) === true)
  } else if (M) {
    check('an over-steep preset is refused', false, 'steepnessOk missing')
    check('the shipped preset is accepted', false, 'steepnessOk missing')
  }

  // --- no harmonic ratios -------------------------------------------------------------------------
  // ADR-006: "no two wavelength or speed ratios are integer multiples". Harmonic wavelengths make
  // crests coincide and the sum reads as one big repeating wave rather than a sea.
  let harmonic = 0
  for (let i = 0; i < terms.length; i++) for (let j = i + 1; j < terms.length; j++) {
    const a = terms[i].lambda, b = terms[j].lambda
    if (!(a > 0 && b > 0)) continue
    const r = a > b ? a / b : b / a
    if (Math.abs(r - Math.round(r)) < 1e-3 && Math.round(r) >= 2) harmonic++
  }
  check('no harmonic wavelength ratios', terms.length > 0 && harmonic === 0, harmonic)

  // --- position and analytic normal, against this file's own double-precision evaluation ----------
  if (M && typeof M.gerstnerAt === 'function' && terms.length === TERMS) {
    const DATUM = 12.5
    const SAMPLES = [[0, 0, 0], [37.5, -12.25, 3.5], [-101.75, 88.5, 17.25], [5000.5, 5000.5, 61.125]]
    let maxPos = 0, maxNrm = 0
    for (const [x, z, t] of SAMPLES) {
      let px = x, py = DATUM, pz = z
      // dP/dx and dP/dz accumulated from the same terms — the ADR forbids finite differences.
      let dxdx = 1, dydx = 0, dzdx = 0, dxdz = 0, dydz = 0, dzdz = 1
      for (const w of terms) {
        const k = 2 * Math.PI / w.lambda, om = Math.sqrt(G * k)
        const dx = Math.cos(w.dirRad), dz = Math.sin(w.dirRad)
        const th = k * (dx * x + dz * z) - om * t + w.phase
        const c = Math.cos(th), s = Math.sin(th)
        px += w.Q * w.A * dx * c; py += w.A * s; pz += w.Q * w.A * dz * c
        dxdx += -w.Q * w.A * dx * dx * k * s; dydx += w.A * dx * k * c; dzdx += -w.Q * w.A * dz * dx * k * s
        dxdz += -w.Q * w.A * dx * dz * k * s; dydz += w.A * dz * k * c; dzdz += -w.Q * w.A * dz * dz * k * s
      }
      // N = normalize(cross(dP/dz, dP/dx))
      const nx = dydz * dzdx - dzdz * dydx, ny = dzdz * dxdx - dxdz * dzdx, nz = dxdz * dydx - dydz * dxdx
      const nl = Math.hypot(nx, ny, nz) || 1
      let got = null
      try { got = M.gerstnerAt(x, z, t, preset, DATUM) } catch (e) { got = null }
      if (!got) { maxPos = Infinity; maxNrm = Infinity; break }
      maxPos = Math.max(maxPos, Math.abs(got.x - px), Math.abs(got.y - py), Math.abs(got.z - pz))
      maxNrm = Math.max(maxNrm, Math.abs(got.nx - nx / nl), Math.abs(got.ny - ny / nl), Math.abs(got.nz - nz / nl))
    }
    check('position matches the double oracle', maxPos <= 1e-9, maxPos)
    // A finite-differenced normal agrees to about the step size, never to 1e-9. This tolerance is
    // what separates the two implementations, so it is the gate for "analytic".
    check('normal is analytic, not finite-differenced', maxNrm <= 1e-9, maxNrm)
  } else if (M) {
    check('position matches the double oracle', false, 'gerstnerAt missing')
    check('normal is analytic, not finite-differenced', false, 'gerstnerAt missing')
  }

  // --- zero amplitude is the datum, exactly --------------------------------------------------------
  if (M && typeof M.expandPreset === 'function' && typeof M.gerstnerAt === 'function') {
    let flat = null, p0 = null
    try {
      flat = M.expandPreset({ ...CONTROLS, maxAmplitudeM: 0 })
      p0 = M.gerstnerAt(21.5, -7.25, 9.75, flat, 3.25)
    } catch (e) {}
    check('zero amplitude returns the datum exactly',
      !!p0 && p0.x === 21.5 && p0.z === -7.25 && p0.y === 3.25
      && p0.nx === 0 && p0.ny === 1 && p0.nz === 0, p0)
  }

  // --- the horizontal Jacobian ---------------------------------------------------------------------
  // ADR-006 gates J > 0 outside the declared foam band; J <= 0 is the fold regime.
  if (M && typeof M.horizontalJacobian === 'function' && preset) {
    let minJ = Infinity, sampled = 0
    for (let i = 0; i < 64; i++) for (let j = 0; j < 64; j++) {
      const J = M.horizontalJacobian(i * 3.25, j * 2.75, 5.5, preset)
      if (Number.isFinite(J)) { sampled++; if (J < minJ) minJ = J }
    }
    check('horizontal Jacobian positive outside the foam band', sampled >= 4096 && minJ > 0, { minJ, sampled })
  } else if (M) check('horizontal Jacobian positive outside the foam band', false, 'horizontalJacobian missing')

  // --- the generated GLSL must be syntactically sound -------------------------------------------
  // This is here because it shipped broken. Coefficients were emitted as `nx+=-${value}` and the
  // values are often negative, producing `+=--1.2e-5` — which GLSL parses as a decrement and
  // rejects with "l-value required (can't modify a const)". The water oracles caught it only
  // indirectly, by failing to compile a program; a text that cannot be valid GLSL should not need a
  // GPU to be recognised as such.
  if (M && typeof M.glslGerstner === 'function' && preset) {
    let glsl = null
    try { glsl = M.glslGerstner(preset) } catch (e) { glsl = null }
    check('GLSL is generated', typeof glsl === 'string' && glsl.length > 200, glsl && glsl.length)
    check('GLSL has no accidental decrement', typeof glsl === 'string' && !/--/.test(glsl)
      && !/\+=\s*-/.test(glsl) && !/-=\s*-/.test(glsl),
      typeof glsl === 'string' ? (glsl.match(/.{0,24}(--|\+=\s*-).{0,24}/) || [''])[0] : 'n/a')
    // Every term must appear, or a preset could expand to twelve and emit three.
    check('GLSL carries every term', typeof glsl === 'string'
      && (glsl.match(/float th=/g) || []).length === TERMS,
      typeof glsl === 'string' ? (glsl.match(/float th=/g) || []).length : 'n/a')
    // Two calls must produce identical text, or the two passes cannot be given the same source.
    let glsl2 = null
    try { glsl2 = M.glslGerstner(preset) } catch (e) {}
    check('GLSL is byte-identical between calls', glsl2 === glsl)
  }

  // Absence of evidence is a failure.
  check('assertion inventory non-empty', assertions.length >= 14, assertions.length)

  let ok = assertions.every(a => a.ok)
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = assertions.filter(a => !a.ok).map(a => a.name)
  console.log(`${ok ? 'PASS' : 'FAIL'}  gerstner terms=${terms.length} steepness=${steep.toFixed(4)} `
    + `harmonics=${harmonic} assertions=${assertions.length} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify(assertions.filter(a => !a.ok), null, 2))
  process.exit(ok ? 0 : 1)
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
