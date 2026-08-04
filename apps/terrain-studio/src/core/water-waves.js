// The shared Gerstner wave core — ADR-006, story S4.7.
//
// Pure and DOM-free. It never imports legacy.js, so it stays outside the legacy<->plugin cycle and
// can be evaluated by an oracle under plain node with no browser.
//
// WHY THIS EXISTS. The shipped water is a flat plane with an animated ripple applied as SHADING:
// `waveData()` in the viewport shader perturbs colour and a crest term, and displaces no geometry.
// There are no coherent crests, no trough parallax, and the silhouette of the water against the
// terrain is a straight line. ADR-006 selects meshed Gerstner displacement for exactly that gap.
//
// ONE SOURCE, TWO PASSES. The forward colour pass and the deferred water-mask/depth pass must
// displace by the SAME function at the SAME time, or the mask and the shaded surface disagree along
// every crest. That is why the maths lives here as data-driven terms rather than inline in one
// shader: the GLSL is generated from this, so there is one definition and the CPU oracle can check
// it in double precision.
//
// AUTHORING STAYS SMALL. Artists set wind direction and speed, sea state, seed, maximum amplitude
// and body kind. They do not edit twelve arbitrary vectors — the twelve terms are EXPANDED from
// those six controls, deterministically, so a preset is reproducible from what a human chose.

export const WATER_WAVE_VERSION = 1
export const GRAVITY = 9.80665
export const TERM_COUNT = 12

// ADR-006's accepted project safety choice, and it is worth restating that it is a CHOICE. Chapter
// 12 puts the practical compression/foam threshold at 0.5-0.9 and warns that steepness past roughly
// 1.0 makes broad negative-Jacobian folding visible. 0.85 keeps authored crests at the high-quality
// end of that grounded range while retaining 0.15 of margin before the documented fold regime.
export const MAX_STEEPNESS = 0.85

export const BODY_KINDS = Object.freeze(['ocean', 'lake', 'river'])

// Wavelength bands in metres, per body. Three bands of four, as the ADR specifies: swell, mid, and
// capillary/chop. A lake has no ocean swell and a river has neither — the ranges, not the term
// count, are what makes a body kind mean something.
const BANDS = Object.freeze({
  ocean: [[62, 190], [11, 44], [1.6, 7.5]],
  lake: [[18, 52], [4.5, 15], [0.7, 3.2]],
  river: [[6, 17], [1.8, 5.2], [0.35, 1.4]],
})

// Directional spread per band, in radians either side of the wind. Swell is nearly unidirectional;
// chop is not. A single spread for all three would make every band look like the same wave.
const SPREAD = [0.22, 0.55, 1.05]

// Relative amplitude weight per band before normalisation to the authored maximum.
const BAND_WEIGHT = [1.0, 0.45, 0.16]

/** Deterministic 32-bit PRNG. Seeded expansion has to be reproducible from the seed alone. */
function rng(seed) {
  let s = (seed | 0) ^ 0x9e3779b9
  return () => {
    s = (Math.imul(s ^ (s >>> 15), 2246822519) + 374761393) | 0
    s = (Math.imul(s ^ (s >>> 13), 3266489917) + 668265263) | 0
    return ((s ^ (s >>> 16)) >>> 0) / 4294967296
  }
}

/**
 * Are any two wavelengths integer multiples?
 *
 * ADR-006 forbids it, and the reason is visual rather than numerical: harmonic components bring
 * their crests into coincidence at a fixed spatial period, so the twelve-term sum reads as one large
 * repeating wave instead of a sea. The same argument applies to speeds, and in deep water
 * omega = sqrt(g k), so a wavelength ratio of n gives a speed ratio of sqrt(n) — keeping wavelengths
 * non-harmonic is the binding constraint.
 */
function harmonicPairs(lambdas, tol = 2e-3) {
  const hits = []
  for (let i = 0; i < lambdas.length; i++) {
    for (let j = i + 1; j < lambdas.length; j++) {
      const a = lambdas[i], b = lambdas[j]
      const r = a > b ? a / b : b / a
      const n = Math.round(r)
      if (n >= 2 && Math.abs(r - n) < tol) hits.push([i, j, r])
    }
  }
  return hits
}

/**
 * Expand six authored controls into twelve deterministic Gerstner terms.
 *
 * Returns a frozen preset. `steepness` is reported rather than left implicit, because it is the one
 * number that decides whether the surface folds, and a value worth clamping is worth printing.
 */
export function expandPreset(controls = {}) {
  const kind = BODY_KINDS.includes(controls.bodyKind) ? controls.bodyKind : 'ocean'
  const bands = BANDS[kind]
  const windRad = ((Number(controls.windDirectionDeg) || 0) * Math.PI) / 180
  const seaState = Math.min(1, Math.max(0, Number(controls.seaState) ?? 0.5))
  const maxA = Math.max(0, Number(controls.maxAmplitudeM) || 0)
  // Wind speed stretches the spectrum toward longer waves; it does not set amplitude, which the
  // author caps directly. Bounded so a silly speed cannot walk the wavelengths out of their band.
  const windPull = Math.min(1.5, Math.max(0.5, (Number(controls.windSpeedMps) || 0) / 12))
  const rand = rng(Number(controls.seed) || 0)

  const lambdas = [], dirs = [], phases = [], amps = []
  for (let b = 0; b < 3; b++) {
    const [lo, hi] = bands[b]
    for (let i = 0; i < 4; i++) {
      // Logarithmic distribution across the band, as the ADR specifies, with seeded jitter inside
      // each quarter so terms cannot collide at a band edge.
      const u = (i + 0.5 + (rand() - 0.5) * 0.7) / 4
      const lam = Math.exp(Math.log(lo) + u * (Math.log(hi) - Math.log(lo))) * windPull
      lambdas.push(lam)
      dirs.push(windRad + (rand() * 2 - 1) * SPREAD[b])
      phases.push(rand() * Math.PI * 2)
      // Sea state moves energy from swell into chop without changing the authored maximum.
      const tilt = b === 0 ? (1 - 0.35 * seaState) : (1 + 0.5 * seaState * b)
      amps.push(BAND_WEIGHT[b] * tilt * (0.75 + 0.5 * rand()))
    }
  }

  // Break any harmonic pair by nudging the LONGER member. Bounded and deterministic; the loop
  // terminates because each pass strictly reduces the count and the nudge is monotone.
  for (let guard = 0; guard < 24; guard++) {
    const hits = harmonicPairs(lambdas)
    if (!hits.length) break
    for (const [i, j] of hits) {
      const longer = lambdas[i] > lambdas[j] ? i : j
      lambdas[longer] *= 1.037
    }
  }

  // Normalise amplitudes to the authored maximum: the sum of the four largest is what a crest can
  // actually reach, and that is the number the author capped.
  const sorted = amps.slice().sort((a, b) => b - a)
  const crest = sorted.slice(0, 4).reduce((a, v) => a + v, 0) || 1
  const scale = maxA / crest
  const A = amps.map(v => v * scale)

  // Steepness allocation. Q starts at 1 and is scaled uniformly so sum(Q k A) <= MAX_STEEPNESS.
  // Uniform rather than per-term because a per-term clamp changes the RELATIVE shape of the
  // spectrum, and the spectrum is what the body kind and sea state authored.
  let raw = 0
  for (let i = 0; i < lambdas.length; i++) raw += (2 * Math.PI / lambdas[i]) * A[i]
  const q = raw > 0 ? Math.min(1, MAX_STEEPNESS / raw) : 0

  const terms = lambdas.map((lam, i) => Object.freeze({
    lambda: lam, dirRad: dirs[i], phase: phases[i], A: A[i], Q: q,
  }))
  let steepness = 0
  for (const t of terms) steepness += t.Q * (2 * Math.PI / t.lambda) * t.A

  return Object.freeze({
    version: WATER_WAVE_VERSION, bodyKind: kind, terms: Object.freeze(terms),
    steepness, controls: Object.freeze({ ...controls }),
  })
}

/** ADR-006's production check: a preset whose steepness exceeds the bound is refused. */
export function steepnessOk(preset) {
  if (!preset || !Array.isArray(preset.terms) || !preset.terms.length) return false
  let s = 0
  for (const t of preset.terms) s += (t.Q || 0) * (2 * Math.PI / (t.lambda || Infinity)) * (t.A || 0)
  return s <= MAX_STEEPNESS + 1e-9
}

/**
 * Position and ANALYTIC normal at one sample.
 *
 * The tangents are accumulated from the same terms as the position. ADR-006 forbids finite
 * differences for the Gerstner normal and the reason is not purity: a differenced normal is wrong by
 * O(step) exactly where the surface curves most, which is the crest — the one place the shading has
 * to be right. It also costs extra evaluations of the identical sum.
 */
export function gerstnerAt(x, z, t, preset, datumM = 0) {
  const terms = (preset && preset.terms) || []
  let px = x, py = datumM, pz = z
  let dxdx = 1, dydx = 0, dzdx = 0
  let dxdz = 0, dydz = 0, dzdz = 1
  for (const w of terms) {
    const k = 2 * Math.PI / w.lambda
    const om = Math.sqrt(GRAVITY * k)
    const dx = Math.cos(w.dirRad), dz = Math.sin(w.dirRad)
    const th = k * (dx * x + dz * z) - om * t + w.phase
    const c = Math.cos(th), s = Math.sin(th)
    px += w.Q * w.A * dx * c
    py += w.A * s
    pz += w.Q * w.A * dz * c
    dxdx += -w.Q * w.A * dx * dx * k * s
    dydx += w.A * dx * k * c
    dzdx += -w.Q * w.A * dz * dx * k * s
    dxdz += -w.Q * w.A * dx * dz * k * s
    dydz += w.A * dz * k * c
    dzdz += -w.Q * w.A * dz * dz * k * s
  }
  const nx = dydz * dzdx - dzdz * dydx
  const ny = dzdz * dxdx - dxdz * dzdx
  const nz = dxdz * dydx - dydz * dxdx
  const len = Math.hypot(nx, ny, nz) || 1
  return { x: px, y: py, z: pz, nx: nx / len, ny: ny / len, nz: nz / len }
}

/**
 * Determinant of the horizontal displacement map.
 *
 * This is the fold detector. Where it drops to zero or below, neighbouring samples have crossed and
 * the surface has folded through itself — visible as a hard black seam on a crest. ADR-006 gates it
 * positive outside the declared foam band, and the steepness clamp above is what keeps it so.
 */
export function horizontalJacobian(x, z, t, preset) {
  const terms = (preset && preset.terms) || []
  let dxdx = 1, dzdx = 0, dxdz = 0, dzdz = 1
  for (const w of terms) {
    const k = 2 * Math.PI / w.lambda
    const om = Math.sqrt(GRAVITY * k)
    const dx = Math.cos(w.dirRad), dz = Math.sin(w.dirRad)
    const s = Math.sin(k * (dx * x + dz * z) - om * t + w.phase)
    dxdx += -w.Q * w.A * dx * dx * k * s
    dzdx += -w.Q * w.A * dz * dx * k * s
    dxdz += -w.Q * w.A * dx * dz * k * s
    dzdz += -w.Q * w.A * dz * dz * k * s
  }
  return dxdx * dzdz - dxdz * dzdx
}

/** Vertical and horizontal reach, for inflating the water mesh's bounds. */
export function presetBounds(preset) {
  const terms = (preset && preset.terms) || []
  let vertical = 0, horizontal = 0
  for (const t of terms) { vertical += t.A; horizontal += t.Q * t.A }
  return { verticalM: vertical, horizontalM: horizontal }
}
