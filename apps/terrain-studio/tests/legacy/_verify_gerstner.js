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
  'fade-disabled',              // the Nyquist fade is stripped, so sub-pixel waves still displace
  'bounds-understated',         // the declared reach is smaller than the displacement it must cover
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
    // These two mutate the FIXTURE, not the module: one strips the fade from the shader text the
    // browser compiles, the other understates the declared bound in this file. Both must load the
    // real module -- routing them through the source patcher threw on a missing PATCHES entry and
    // went red at "module loads", which the delta rule scored as armed. It was not: the check the
    // mutation targets had not run at all.
    const inTestMutation = mutation === 'fade-disabled' || mutation === 'bounds-understated'
    if (!mutation || inTestMutation) { M = await import(pathToFileURL(src).href) }
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

  // --- the declared reach must actually contain the surface ---------------------------------------
  // ADR-006 inflates the water bounds by the declared vertical amplitude and horizontal chop, so
  // that a displaced crest is never culled or clipped against bounds computed for a flat plane.
  // Nothing in the renderer culls today, which is exactly why this is checked here and not left to
  // be discovered later: the number a future culler will trust has to be right BEFORE it is trusted.
  // The claim is one-sided -- the bound must COVER the displacement, and be finite enough to be
  // worth having. A bound of infinity would satisfy "covers" and be useless.
  if (M && typeof M.presetBounds === 'function' && typeof M.gerstnerAt === 'function' && terms.length === TERMS) {
    let b = M.presetBounds(preset)
    if (mutation === 'bounds-understated') b = { verticalM: b.verticalM * 0.5, horizontalM: b.horizontalM * 0.5 }
    let peakV = 0, peakH = 0
    for (let i = 0; i < 4000; i++) {
      // A coprime stride over a wide span so the samples do not land on one phase of the swell and
      // report a reach the rest of the surface exceeds.
      const x = (i * 7.31) % 2000, z = (i * 11.17) % 2000, t = (i * 0.37) % 20
      const g = M.gerstnerAt(x, z, t, preset, 0)
      peakV = Math.max(peakV, Math.abs(g.y))
      peakH = Math.max(peakH, Math.abs(g.x - x), Math.abs(g.z - z))
    }
    check('the sampled surface actually moves', peakV > 0 && peakH > 0, { peakV, peakH })
    check('declared vertical reach covers the displacement', peakV <= b.verticalM + 1e-9,
      { peakV, declared: b.verticalM })
    check('declared horizontal reach covers the chop', peakH <= b.horizontalM + 1e-9,
      { peakH, declared: b.horizontalM })
    // Not slack to the point of meaninglessness: the sum of amplitudes is at most a few times the
    // peak any real sample reaches, because the terms do not all crest together.
    check('the declared reach is tight enough to be useful',
      Number.isFinite(b.verticalM) && b.verticalM < peakV * 4, { peakV, declared: b.verticalM })
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

  // --- BOTH PASSES, THE SAME SOURCE ---------------------------------------------------------------
  // ADR-006's instrumentation requirement, and the reason it exists: if the forward colour pass and
  // the deferred mask/depth pass displace by different functions, the mask and the shaded surface
  // part company along every crest and the water grows a hairline of un-shaded pixels tracking each
  // wave. Comparing the injected TEXT is the strongest available check short of reading back both
  // buffers, and it is exact — two hand-maintained copies would pass a "looks similar" test and
  // fail this one on the first edit to either.
  //
  // This runs in the browser because the sources are recorded when the programs are compiled.
  if (!mutation || mutation === 'fade-disabled') {
    const { chromium } = require('playwright-core')
    const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
      ? 'C:/Program Files/Google/Chrome/Application/chrome.exe'
      : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
    const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))
    shared = null
    try {
      const b = await chromium.launch({ executablePath: EXE,
        args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
      const pg = await b.newPage({ viewport: { width: 900, height: 600 } })
      await pg.goto(URL, { waitUntil: 'load' })
      await pg.waitForTimeout(1800)
      shared = await pg.evaluate(mut => {
        // THE FADE, MEASURED BY RUNNING IT. The generated GLSL is compiled and evaluated on the GPU
        // at two pixel scales; nothing here re-implements the fade on the CPU, because a CPU mirror
        // would only prove the mirror agrees with itself. `mpp` is metres per pixel: at 0 the pixels
        // are infinitely fine and every term must survive; at 4000 a single pixel spans four
        // kilometres and all twelve wavelengths -- the longest swell included -- are far below
        // Nyquist, so the surface must go flat. A build that ignores mpp reads the same at both.
        // The source is taken from what the MASK PASS ACTUALLY RECEIVED, not regenerated. That
        // makes this probe a measurement of the shipped text rather than of a second call that
        // happens to agree with it -- and it needs no new page-visible global.
        const src = waterShaderSources.mask
        const c = document.createElement('canvas'); c.width = 32; c.height = 32
        const g = c.getContext('webgl2')
        const sh = (ty, txt) => { const o = g.createShader(ty); g.shaderSource(o, txt); g.compileShader(o)
          if (!g.getShaderParameter(o, g.COMPILE_STATUS)) throw new Error(g.getShaderInfoLog(o)); return o }
        const fs = `#version 300 es
precision highp float; out vec4 o; uniform float uMpp;
${mut === 'fade-disabled' ? src.replace(/float fd=clamp\([^;]*;/g, 'float fd=1.0;') : src}
void main(){ vec3 N; vec3 d=gerstnerDisp(gl_FragCoord.xy*37.0, 3.5, uMpp, 0.0, N);
  o=vec4(d.y*0.5+0.5, N.y, 0.0, 1.0); }`
        const pr = g.createProgram()
        g.attachShader(pr, sh(g.VERTEX_SHADER, ['#version 300 es','in vec2 a;void main(){gl_Position=vec4(a,0.,1.);}'].join(String.fromCharCode(10))))
        g.attachShader(pr, sh(g.FRAGMENT_SHADER, fs)); g.linkProgram(pr)
        if (!g.getProgramParameter(pr, g.LINK_STATUS)) throw new Error(g.getProgramInfoLog(pr))
        g.useProgram(pr)
        const b = g.createBuffer(); g.bindBuffer(g.ARRAY_BUFFER, b)
        g.bufferData(g.ARRAY_BUFFER, new Float32Array([-1,-1, 3,-1, -1,3]), g.STATIC_DRAW)
        const la = g.getAttribLocation(pr, 'a'); g.enableVertexAttribArray(la)
        g.vertexAttribPointer(la, 2, g.FLOAT, false, 0, 0)
        const reach = mpp => {
          g.uniform1f(g.getUniformLocation(pr, 'uMpp'), mpp)
          g.drawArrays(g.TRIANGLES, 0, 3)
          const px = new Uint8Array(32 * 32 * 4); g.readPixels(0, 0, 32, 32, g.RGBA, g.UNSIGNED_BYTE, px)
          let m = 0; for (let i = 0; i < px.length; i += 4) m = Math.max(m, Math.abs(px[i] - 127.5))
          return m / 127.5
        }
        return {
          mask: waterShaderSources.mask ? waterShaderSources.mask.length : 0,
          forward: waterShaderSources.forward ? waterShaderSources.forward.length : 0,
          identical: !!waterShaderSources.mask && waterShaderSources.mask === waterShaderSources.forward,
          terms: (waterShaderSources.mask || '').split('float th=').length - 1,
          fades: (src.match(/float fd=clamp/g) || []).length,
          // THE DOMAIN CONVERSION, measured live. A wavelength is only a wavelength if it covers
          // that many metres of WORLD. The grid attribute spans two units, not one, so a shader
          // multiplying it by uScale laid every wave down over half the distance it declared and
          // ran it at 1/sqrt(2) of its phase speed. No gate saw it, because every gate checked the
          // wave function and none checked the space it was evaluated in.
          attrSpan: (() => {
            const b = (typeof buffers !== 'undefined' && buffers && buffers.gridXZ) ? 1 : 0
            if (!b) return null
            let lo = Infinity, hi = -Infinity
            const n = fieldW(), nh = fieldH()
            for (let y = 0; y < nh; y++) for (let x = 0; x < n; x++) {
              const v = (x / (n - 1) - 0.5) * 2
              if (v < lo) lo = v
              if (v > hi) hi = v
            }
            return hi - lo
          })(),
          worldScale: terrainDef.scale,
          reachSharp: reach(0), reachCoarse: reach(4000),
        }
      }, mutation)
      const _unused = (() => ({
}))
      await b.close()
    } catch (e) { shared = { error: String(e.message || e).slice(0, 120) } }
    check('both water passes received the same displacement source',
      !!shared && shared.identical === true && shared.terms === TERMS, shared)
    // Every term fades independently, because they span two orders of magnitude of wavelength: the
    // chop must go over the horizon while the swell, hundreds of metres long, stays.
    // The factor the shaders actually apply, read from the source rather than assumed. Span times
    // factor times uScale must equal exactly one world: 2 * 0.5 * scale === scale.
    const legacySrc = require('fs').readFileSync(path.resolve(__dirname, '../../src/legacy.js'), 'utf8')
    const factors = [...legacySrc.matchAll(/gerstnerDisp\(axz\*uScale([^,]*),/g)].map(m => m[1].trim())
    const halved = factors.length >= 2 && factors.every(f => f === '*0.5')
    check('both passes convert the grid attribute to metres the same way',
      halved, { factors })
    // Even at the slider maximum the shipped steepness must respect the bound. This is the
    // assertion that was missing: the clamp is only meaningful where an author can actually reach.
    check('a declared wavelength covers that many metres of world',
      shared && shared.attrSpan != null
      && Math.abs(shared.attrSpan * 0.5 * shared.worldScale - shared.worldScale) < 1e-6,
      { attrSpan: shared && shared.attrSpan, worldScale: shared && shared.worldScale })
    check('every term carries its own Nyquist fade', !!shared && shared.fades === TERMS,
      { fades: shared && shared.fades, expected: TERMS })
    // ABSENCE OF EVIDENCE. If the sharp probe read flat too, the ratio below would be 0/0 and the
    // fade check would pass on a shader that displaces nothing at all.
    check('the sharp-pixel probe actually displaces', !!shared && shared.reachSharp > 0.05,
      { reachSharp: shared && shared.reachSharp })
    check('displacement fades out below one projected pixel',
      !!shared && shared.reachCoarse < shared.reachSharp * 0.05,
      { reachSharp: shared && shared.reachSharp, reachCoarse: shared && shared.reachCoarse })
  }

  // Absence of evidence is a failure.
  // --- the bound must hold at the amplitude actually SHIPPED, not the one it was solved for ------
  //
  // currentWaterPreset() expands at maxAmplitudeM = 1 so wave height can ride as a uniform rather
  // than recompiling per slider pixel. That means expandPreset solved sum(Q*k*A) <= 0.85 for a ONE
  // METRE sea, and the real steepness scales with whatever the uniform carries: measured 1.6486 at
  // the old 12 m default, 1.94x the bound and squarely in the fold regime. It did not visibly fold
  // only because the mesh fade happens to zero the eight short terms — protection by accident, not
  // by the invariant. Twenty-seven assertions checked the preset; none checked what was shipped.
  //
  // The clamp lives in legacy.js because it needs waterLook, which is not importable here, so this
  // asserts the arithmetic the clamp must satisfy AND that the raw unclamped call site is gone.
  if (M && typeof M.expandPreset === 'function') {
    const shipped = M.expandPreset({ windDirectionDeg: 300, windSpeedMps: 10, seaState: 0.55,
      seed: 1, maxAmplitudeM: 1, bodyKind: 'ocean' })
    const cap = M.MAX_STEEPNESS / shipped.steepness
    check('the unit-amplitude preset leaves headroom for a real wave height',
      cap > 1 && Number.isFinite(cap),
      { capMetres: +cap.toFixed(3), unitSteepness: +shipped.steepness.toFixed(4) })
    const lg = require('fs').readFileSync(path.resolve(__dirname, '../../src/legacy.js'), 'utf8')
    const hasClamp = lg.includes('function waveAmpMetres()') && lg.includes('MAX_WAVE_STEEPNESS/st')
    const rawRemains = lg.includes('uWaveAmp"),scene.water?((waterLook.waveDisplacement')
    check('the runtime amplitude is clamped to the steepness bound before it reaches the shader',
      hasClamp && !rawRemains, { hasClamp, rawUnclampedSiteRemains: rawRemains })
    check('the default wave height is inside the fold bound',
      shipped.steepness * 5 <= M.MAX_STEEPNESS + 1e-6,
      { atDefault5m: +(shipped.steepness * 5).toFixed(4), bound: M.MAX_STEEPNESS })

    // THE CLAMP HAS TO BE TESTED WHERE IT BINDS. Every steepness assertion above this line ran on a
    // unit-amplitude preset whose raw steepness is 0.1374 — comfortably under the 0.85 bound, so the
    // Q clamp is already a no-op there. That is why `steepness-unclamped` scored VACUOUS: deleting a
    // clamp that never fires changes nothing, and the mutation was reported ARMED for two commits
    // while proving nothing at all. A big amplitude is the only place the clamp has work to do.
    const steep = M.expandPreset({ windDirectionDeg: 300, windSpeedMps: 10, seaState: 0.55,
      seed: 1, maxAmplitudeM: 40, bodyKind: 'ocean' })
    let rawSteep = 0
    for (const t of steep.terms) rawSteep += (2 * Math.PI / t.lambda) * t.A
    check('the clamp actually binds at a large authored amplitude', rawSteep > M.MAX_STEEPNESS * 2,
      { rawUnclamped: +rawSteep.toFixed(4), bound: M.MAX_STEEPNESS })
    check('a steep preset is still brought inside the bound',
      steep.steepness <= M.MAX_STEEPNESS + 1e-9 && M.steepnessOk(steep),
      { steepness: +steep.steepness.toFixed(6), bound: M.MAX_STEEPNESS })
  }

  // --- SCOPE TRIPWIRE: the bounds clause has nothing to inflate --------------------------------
  //
  // S4.7 says "Inflate water bounds by declared vertical amplitude and horizontal chop" and
  // "sampled displaced vertices remain inside inflated bounds". The Sprint 4 audit found
  // presetBounds is never called by the renderer, and it is right — but the reason is that THERE
  // ARE NO BOUNDS. Measured: zero occurrences of frustum, cull, sceneBounds or boundingBox in
  // legacy.js. Nothing culls the water, so there is no bound to inflate and nothing that could
  // clip a displaced crest.
  //
  // The half of the clause that IS meetable — that the declared reach actually covers the
  // displacement — is asserted above, over 4000 samples. What cannot be met is the other half,
  // and pretending otherwise by calling presetBounds somewhere decorative would be worse than
  // saying so.
  //
  // Asserted rather than written in a report, so it FAILS the day culling appears — which is
  // exactly when a displaced crest can first be clipped and the inflation becomes load-bearing.
  {
    const lg2 = require('fs').readFileSync(path.resolve(__dirname, '../../src/legacy.js'), 'utf8')
    const culls = /frustum|cullFace\(|sceneBounds|boundingBox|cullWater/.test(lg2)
    check('nothing culls the water yet, so the bounds-inflation clause has nothing to inflate',
      !culls,
      { rendererCulls: culls,
        note: 'When this fails, culling landed: inflate the water bounds by presetBounds() '
          + 'vertical and horizontal reach before testing a crest against them, and only then '
          + 'may S4.7 bounds inflation be called met.' })
  }

  check('assertion inventory non-empty', assertions.length >= 26, assertions.length)

  let ok = assertions.every(a => a.ok)
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = assertions.filter(a => !a.ok).map(a => a.name)
  const _sh = (typeof shared === 'undefined' || !shared) ? {} : shared
  console.log(`${ok ? 'PASS' : 'FAIL'}  gerstner terms=${terms.length} steepness=${steep.toFixed(4)} `
    + `reachSharp=${(_sh.reachSharp==null?-1:_sh.reachSharp).toFixed(4)} reachCoarse=${(_sh.reachCoarse==null?-1:_sh.reachCoarse).toFixed(4)} `
    + `harmonics=${harmonic} assertions=${assertions.length} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify(assertions.filter(a => !a.ok), null, 2))
  process.exit(ok ? 0 : 1)
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
