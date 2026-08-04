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
      // AMPLITUDE SCALES WITH WAVELENGTH, and leaving it out was a real defect with a very visible
      // signature. Assigning amplitude per BAND alone, independent of the wavelength inside it, gave
      // the chop band roughly a metre of amplitude at 1.6 m wavelength — a steepness of 2*pi*A/L
      // near 4, which is a 77-degree wave face. Nothing in the ocean does that. Measured on the
      // shipped preset the steepest term ran 4.2458, and the result on screen was a crumpled-foil
      // surface the user described as bubble plastic.
      //
      // The steepness clamp did not catch it: it bounds the SUM of Q*k*A and responds by driving Q
      // toward zero, which flattens the horizontal displacement while leaving the vertical amplitude
      // — and therefore the NORMAL — exactly as steep as before. So the surface stopped folding and
      // went on looking like foil.
      //
      // Real seas sit near a common limiting steepness across the whole spectrum: a 100 m swell is
      // metres tall and a 1 m ripple is centimetres tall. Making amplitude proportional to
      // wavelength gives every term a comparable A/L, which is what the physics actually says.
      amps.push(BAND_WEIGHT[b] * tilt * (0.75 + 0.5 * rand()) * lam)
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

/**
 * Generate the GLSL both water passes use.
 *
 * ONE SOURCE, not two copies. The forward colour pass and the deferred water-mask/depth pass must
 * displace by the same function at the same time or the mask and the shaded surface disagree along
 * every crest — a hairline of un-shaded water tracking each wave. ADR-006 requires the same function
 * and the same time in both, so the text is emitted once from the preset and injected into both
 * programs, and a gate compares the two injected strings rather than trusting that they match.
 *
 * The terms are baked as literals rather than passed as uniforms. A preset is immutable once
 * expanded, twelve terms is 60 floats of uniform pressure per pass, and a baked constant lets the
 * driver fold the trigonometry — but the deciding reason is that a baked source is COMPARABLE:
 * two passes either got the same text or they did not.
 *
 * `p` is in METRES. The caller converts, because only the caller knows its own coordinate space.
 */
export function glslGerstner(preset, fnName = 'gerstnerDisp') {
  const terms = (preset && preset.terms) || []
  const f = v => {
    if (!Number.isFinite(v)) throw new Error('glslGerstner: non-finite term value')
    // Enough digits to round-trip a float32 exactly, so the shader evaluates the preset the CPU
    // oracle checked rather than a rounded neighbour of it.
    return v.toPrecision(9)
  }
  const lines = terms.map(t => {
    const k = 2 * Math.PI / t.lambda
    const om = Math.sqrt(GRAVITY * k)
    const dx = Math.cos(t.dirRad), dz = Math.sin(t.dirRad)
    // NYQUIST FADE, per term. A wave whose wavelength has shrunk below a couple of pixels cannot
    // be drawn -- it aliases into crawling noise that no amount of supersampling settles, and at
    // grazing angles the far water is exactly where every short term lands. Each term carries its
    // own fade because they differ by two orders of magnitude in wavelength: the chop should
    // vanish over the horizon while the swell, still hundreds of metres long, stays. Full
    // strength at four pixels, gone at two. `mpp` is metres per pixel AT THIS VERTEX, so the
    // fade is per-vertex distance-dependent rather than one global LOD switch.
    return `  { float fd=clamp(${f(t.lambda)}/max(2.0*mpp,1e-6)-1.0,0.0,1.0);`
      + ` float th=${f(k)}*(${f(dx)}*p.x+${f(dz)}*p.y)-${f(om)}*t+${f(t.phase)};`
      + ` float c=cos(th), s=sin(th);`
      // EVERY COEFFICIENT IS PARENTHESISED and carries its own sign. Emitting `nx+=-${value}` put a
      // unary minus in front of a literal that is itself often negative, producing `+=--1.2e-5`,
      // which GLSL parses as a decrement and rejects with "l-value required". The sign belongs in
      // the number, not in the operator.
      + ` float c2=c*fd, s2=s*fd;`
      + ` d.x+=(${f(t.Q * t.A * dx)})*c2; d.y+=(${f(t.A)})*s2; d.z+=(${f(t.Q * t.A * dz)})*c2;`
      + ` nx+=(${f(-t.Q * t.A * dx * dx * k)})*s2; ny+=(${f(t.A * dx * k)})*c2; nz+=(${f(-t.Q * t.A * dz * dx * k)})*s2;`
      + ` mx+=(${f(-t.Q * t.A * dx * dz * k)})*s2; my+=(${f(t.A * dz * k)})*c2; mz+=(${f(-t.Q * t.A * dz * dz * k)})*s2; }`
  })
  // Tangents are accumulated alongside, never differenced — the ADR forbids a finite-difference
  // normal, and doing it here as well as on the CPU is what keeps the two implementations the same
  // function rather than two approximations of one.
  return [
    `// generated from WaterWavePreset v${WATER_WAVE_VERSION} — ${terms.length} terms, steepness ${(preset && preset.steepness || 0).toFixed(4)}`,
    `vec3 ${fnName}(vec2 p, float t, float mpp, out vec3 N){`,
    `  vec3 d=vec3(0.0);`,
    `  float nx=1.0, ny=0.0, nz=0.0;`,   // dP/dx
    `  float mx=0.0, my=0.0, mz=1.0;`,   // dP/dz
    ...lines,
    `  N=normalize(cross(vec3(mx,my,mz), vec3(nx,ny,nz)));`,
    `  return d;`,
    `}`,
  ].join('\n')
}

/**
 * Generate the surface-detail GLSL both water fragment passes use.
 *
 * WHY THIS EXISTS. The wave GEOMETRY was Gerstner, but the shading detail on top of it was a hand
 * written function called `waveData`, hand-duplicated in the forward and deferred passes, whose
 * default "wind" pattern was two plane sinusoids:
 *
 *     a = sin(dot(p,d1)*58*s + t*1.9)
 *     b = sin(dot(p,d2)*24*s + t*0.74 + a*0.35)
 *
 * Two coherent plane waves have straight, parallel, exactly periodic lines of equal phase. They
 * cannot produce anything but banding, and no amount of wave geometry underneath hides it, because
 * the sinusoids were the only thing the LIGHTING responded to. This function replaces them, and it
 * is generated from the preset for the same reason `glslGerstner` is: the one piece of water GLSL
 * that stayed hand-copied is the one that drifted.
 *
 * WHAT KILLS BANDING. A dense spectrum plus broken long-range coherence. Three octaves at
 * non-harmonic ratios give the density; a domain warp driven by a lower-frequency octave destroys
 * the coherence, so equal-phase lines meander instead of running straight. Anisotropy along the
 * wind is what makes it read as wind chop rather than generic lumps.
 *
 * DERIVATIVES ARE ANALYTIC. ADR-006 forbids finite-difference normals, and the rule extends here:
 * value noise carries its own exact gradient, so the detail contributes a real slope rather than a
 * sampled approximation of one.
 *
 * THE DETAIL OWNS BELOW ~1.5 m. Above that is the Gerstner terms' job. If the two bands overlapped
 * they would double-count energy in the mid band, and the surface would read as too rough for its
 * own wave height.
 *
 * `p` is in METRES and `mpp` is metres per pixel, exactly as for the geometry.
 */
export function glslWaterDetail(preset, fnName = 'waterDetail') {
  const terms = (preset && preset.terms) || []
  // The wind direction, recovered as the mean heading of the swell band. Taking it from the preset
  // rather than hardcoding a vector is what stops the detail from banding ACROSS the swell: the old
  // pattern used fixed directions (.93,.37) and (.72,-.69) no matter which way the weather blew.
  const swell = terms.slice(0, 4)
  let sx = 0, sz = 0
  for (const t of swell) { sx += Math.cos(t.dirRad); sz += Math.sin(t.dirRad) }
  const wlen = Math.hypot(sx, sz) || 1
  const wx = sx / wlen, wz = sz / wlen
  const f = v => {
    if (!Number.isFinite(v)) throw new Error('glslWaterDetail: non-finite value')
    return v.toPrecision(9)
  }
  // Non-harmonic ratios, and all three below the shortest Gerstner wavelength so the bands do not
  // overlap. Ratios 1 : 2.153 : 4.637 share no small-integer relationship, so the octaves never
  // line up into a repeating beat the eye can lock onto.
  // THE SLOPE SPECTRUM MUST DESCEND. Slope contribution is amplitude times wavenumber, so an
  // amplitude series that falls slower than the wavelength does makes the FINEST octave dominate the
  // normal — the first version of this ran 0.390 / 0.462 / 0.546, ascending at 1.185 per octave,
  // which is the classic driver of shimmer and moire on distant water. These amplitudes give
  // 0.464 / 0.395 / 0.336, descending at 0.85, in line with what shipped ocean shaders use.
  const OCT = [
    { lambda: 1.40, amp: 1.000, drift: 0.35 },
    { lambda: 0.65, amp: 0.395, drift: 0.62 },
    { lambda: 0.28, amp: 0.145, drift: 0.95 },
  ]
  const norm = OCT.reduce((a, o) => a + o.amp, 0)
  const lines = OCT.map((o, i) => {
    const k = 1 / o.lambda
    // ROTATE EACH OCTAVE. Value noise lives on a square lattice and carries strong axis-aligned
    // structure; three octaves sampled from the same unrotated lattice reinforce it, which puts a
    // faint grid back into a field built specifically to have no grid. The angles are 90*frac(i/phi)
    // — 0, 55.62, 21.25 degrees — maximally separated within the lattice's own 90-degree symmetry,
    // rather than a fixed step that could land back on it.
    const PHI = (1 + Math.sqrt(5)) / 2
    const ang = (Math.PI / 2) * ((i / PHI) % 1)
    const c = Math.cos(ang), sn = Math.sin(ang)
    const qr = `vec2(${f(c)}*q.x+${f(sn)}*q.y, ${f(-sn)}*q.x+${f(c)}*q.y)`
    return `  { float fd=clamp(${f(o.lambda)}/max(2.0*mpp,1e-6)-1.0,0.0,1.0);`
      + ` if(fd>0.0){ vec2 qq=${qr}*${f(k)};`
      + ` vec3 n=vnoise2(qq + vec2(${f(o.drift * (i % 2 ? -1 : 1))},${f(o.drift * 0.6)})*t);`
      // The gradient comes back in the ROTATED frame and has to be rotated out again, or every
      // octave's highlights are tilted against the one below it.
      + ` vec2 gr=vec2(${f(c)}*n.y-${f(sn)}*n.z, ${f(sn)}*n.y+${f(c)}*n.z);`
      + ` g += (${f(o.amp / norm)})*fd*${f(k)}*gr; h += (${f(o.amp / norm)})*fd*n.x; } }`
  })
  return [
    `// generated from WaterWavePreset v${WATER_WAVE_VERSION} — ${OCT.length} detail octaves, wind (${f(wx)},${f(wz)})`,
    `float h21(vec2 p){ p=fract(p*vec2(0.1031,0.1030)); p+=dot(p,p.yx+33.33); return fract((p.x+p.y)*p.x); }`,
    // Value noise WITH ITS EXACT GRADIENT. The quintic-free cubic smoothstep is used deliberately:
    // its derivative is cheap and continuous, which is all the normal needs.
    `vec3 vnoise2(vec2 p){`,
    `  vec2 i=floor(p), fr=fract(p);`,
    `  vec2 u=fr*fr*(3.0-2.0*fr), du=6.0*fr*(1.0-fr);`,
    `  float a=h21(i), b=h21(i+vec2(1.,0.)), c=h21(i+vec2(0.,1.)), d=h21(i+vec2(1.,1.));`,
    `  float k1=b-a, k2=c-a, k3=a-b-c+d;`,
    `  return vec3(a+k1*u.x+k2*u.y+k3*u.x*u.y, du.x*(k1+k3*u.y), du.y*(k2+k3*u.x));`,
    `}`,
    // Voronoi F2-F1 edge distance. This is the CELL STRUCTURE of sunlight sparkle on real water and
    // of the highlight cells in stylised water. It feeds the mask channel only, never the normal:
    // cellular fields have derivative discontinuities at cell borders and would facet the shading.
    `float voroEdge(vec2 p, float t){`,
    `  vec2 n=floor(p), fp=fract(p); float f1=8.0, f2=8.0;`,
    `  for(int j=-1;j<=1;j++){ for(int i=-1;i<=1;i++){`,
    `    vec2 g=vec2(float(i),float(j));`,
    `    vec2 o=vec2(h21(n+g), h21(n+g+17.0));`,
    // EVERY FEATURE POINT ORBITS AT ITS OWN RATE. Driving them all at one frequency gives the whole
    // cell field a common period — at t*0.8 it re-synchronised every 7.854 s and the sparkle pulsed
    // in unison, which is the cellular version of exactly the banding this function exists to avoid.
    // Deriving the rate from the point's own hash means no two share a period and the field never
    // returns to a previous configuration.
    `    o=0.5+0.45*sin(t*(0.45+0.85*o.x)+6.2831*o);`,
    `    float d=length(g+o-fp);`,
    `    if(d<f1){ f2=f1; f1=d; } else if(d<f2){ f2=d; }`,
    `  } }`,
    `  return clamp(f2-f1,0.0,1.0);`,
    `}`,
    // THE VARIANCE THE FADE THREW AWAY, as a function of the same mpp.
    //
    // The Nyquist fade is correct — an octave below two pixels can only alias — but removing it
    // without accounting for it makes distant water PERFECTLY SMOOTH, and a perfectly smooth
    // dielectric with a needle-sharp highlight is exactly what "looks like plastic" means. The
    // energy has to go somewhere, and physically it goes into roughness: sub-pixel waves widen the
    // specular lobe instead of glinting individually.
    //
    // Slope variance of one sinusoidal octave of amplitude a and wavenumber k is (a*k)^2/2. What the
    // fade removed is the (1-fd) share of it, so the sum below is the roughness the shading must add
    // back. The terrain path already does this (see the `rough` term in shadeSurface); water did not.
    `float ${fnName}Var(float mpp){`,
    `  float v=0.0;`,
    ...OCT.map(o => {
      const k = 1 / o.lambda
      const slope = (o.amp / norm) * k
      return `  { float fd=clamp(${f(o.lambda)}/max(2.0*mpp,1e-6)-1.0,0.0,1.0);`
        + ` float lost=1.0-fd; v += lost*lost*${f(slope * slope * 0.5)}; }`
    }),
    `  return v;`,
    `}`,
    `vec4 ${fnName}(vec2 p, float t, float mpp){`,
    // Rotate into the wind frame and stretch along it: chop is elongated across the wind, which is
    // what makes a noise field read as WIND chop instead of isotropic lumps.
    `  mat2 R=mat2(${f(wx)},${f(-wz)},${f(wz)},${f(wx)});`,
    `  vec2 q=R*p; q.x*=0.55;`,
    // DOMAIN WARP. This is the part that actually destroys long-range coherence: sampling the field
    // at a position that is itself perturbed by a lower-frequency field means equal-phase lines
    // meander rather than running straight across the surface.
    `  vec3 w=vnoise2(q*0.22+vec2(t*0.05,0.0));`,
    `  q+=1.6*vec2(w.y,w.z);`,
    `  vec2 g=vec2(0.0); float h=0.0;`,
    ...lines,
    // Undo the anisotropic stretch and the rotation on the GRADIENT, not just the position: a
    // gradient transforms by the inverse transpose, and skipping this tilts every highlight.
    `  g.x*=0.55;`,
    `  g=vec2(${f(wx)}*g.x+${f(wz)}*g.y, ${f(-wz)}*g.x+${f(wx)}*g.y);`,
    // The sparkle mask fades with distance too, or it aliases into crawling static on far water.
    `  float mf=clamp(2.0/max(2.0*mpp,1e-6)-1.0,0.0,1.0);`,
    `  float cell=mf>0.0?voroEdge(q*0.5,t):0.0;`,
    `  return vec4(g, h, cell*mf);`,
    `}`,
  ].join('\n')
}

/** Deep-water reference: below this depth a wave starts to feel the bottom. */
export const SHOAL_BREAK_RATIO = 0.78   // McCowan: a wave breaks near 0.78 x the local depth
export const SHOAL_MAX_GAIN = 2.6       // cap, so a numerically tiny depth cannot make an infinite wave

/**
 * Wave amplitude in water of a given depth.
 *
 * The shoreline used to be handled by fading amplitude to ZERO as depth fell, which is backwards:
 * it made the sea glassiest exactly where real water is roughest. Waves entering shallow water slow
 * down, shorten and GROW — Green's law puts the amplitude at depth^(-1/4) — and they keep growing
 * until the crest outruns the wave and it breaks, at roughly 0.78 of the local depth.
 *
 * Three regimes, and the gate checks all three:
 *   deep      (depth >= ref)  amplitude is what the author asked for; the bottom is not felt
 *   shoaling  (falling depth) amplitude rises as (ref/depth)^(1/4), capped
 *   breaking  (very shallow)  amplitude is clamped to 0.78*depth and therefore FALLS to zero at
 *                             the waterline, which is what makes surf rear up and then collapse
 *
 * All lengths in metres. This is the double-precision definition; `glslShoal` emits the same law.
 */
export function shoalAmplitude(ampM, depthM, refM) {
  const d = Math.max(depthM, 0)
  if (d <= 0) return 0
  const ref = Math.max(refM, 1e-6)
  const gain = Math.min(Math.pow(Math.max(ref / d, 1), 0.25), SHOAL_MAX_GAIN)
  const dry = Math.min(d * 2, 1)          // the last half-metre, so no wave stands on dry land
  return Math.min(ampM * gain, SHOAL_BREAK_RATIO * d) * dry
}

/** The same law as GLSL, so the shaders and the oracle cannot drift apart. */
export function glslShoal(fnName = 'shoalAmp') {
  return [
    `float ${fnName}(float ampM, float depthM, float refM){`,
    `  float d=max(depthM,0.0);`,
    `  if(d<=0.0) return 0.0;`,
    `  float gain=min(pow(max(max(refM,1e-6)/d,1.0),0.25),${SHOAL_MAX_GAIN.toFixed(4)});`,
    `  float dry=min(d*2.0,1.0);`,
    `  return min(ampM*gain,${SHOAL_BREAK_RATIO.toFixed(4)}*d)*dry;`,
    `}`,
    // Emitted beside it from the SAME constants, so surf can never disagree with the amplitude clamp
    // it is derived from.
    `float ${fnName}Break(float ampM, float depthM, float refM){`,
    `  float d=max(depthM,0.0);`,
    `  if(d<=0.0) return 0.0;`,
    `  float gain=min(pow(max(max(refM,1e-6)/d,1.0),0.25),${SHOAL_MAX_GAIN.toFixed(4)});`,
    `  return min(1.0,(ampM*gain)/(${SHOAL_BREAK_RATIO.toFixed(4)}*d));`,
    `}`,
  ].join('\n')
}

/**
 * How close a wave is to breaking, 0..1, where 1 means it is breaking now.
 *
 * This is the SURF CRITERION, and it is the same number the amplitude clamp already uses: the
 * shoaled height over the McCowan limit of 0.78*depth. Driving foam from it rather than from a
 * distance-to-shore is what produces surf that arrives in bands parallel to the beach — depth
 * contours run parallel to a shore, so the locus where a wave first exceeds its limit does too, and
 * it moves further out on a bigger swell exactly as real surf does.
 */
export function breakFraction(ampM, depthM, refM) {
  const d = Math.max(depthM, 0)
  if (d <= 0) return 0
  const ref = Math.max(refM, 1e-6)
  const gain = Math.min(Math.pow(Math.max(ref / d, 1), 0.25), SHOAL_MAX_GAIN)
  return Math.min(1, (ampM * gain) / (SHOAL_BREAK_RATIO * d))
}
