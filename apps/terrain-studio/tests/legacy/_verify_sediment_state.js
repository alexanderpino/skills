// S3.1 — hydraulic STATE outputs on CPU/GPU. Written RED-FIRST: nothing declares these ports yet.
//
// WHAT THE SOURCE SAYS TODAY (measured before writing a line of this file, not taken from the
// sprint text). The sprint claims Pipe/Droplet "currently compute transport state and a ledger but
// expose only final height". That is true, and here is where:
//
//   * src/core/gpu.js:606 — the pipe STATE shader's fragment is `vec4(b+dep-er, water,
//     sediment+er-dep, 1.0)`: suspended sediment lives in BLUE, per cell, every iteration.
//     src/core/gpu.js:409-412 — `o[i]=rgba[si]+rgba[si+2]` folds that blue channel INTO the height
//     at readback and returns one scalar. The transport state exists and is destroyed at the
//     boundary of the function.
//   * src/core/gpu.js:598-601 — `transport`, `depth`, `speed` are computed per cell (a velocity in
//     cell/iteration units) and never leave the shader. C2's "velocity discarded", exactly.
//   * src/legacy.js:2931-3035 — the CPU droplet solver carries `sed` per particle, splats it
//     through `deposit1`, and ledgers {settled, exported, lost, brushClipGain}. It returns `h`.
//   * src/plugins/ero/hydraulic.js — declares NO `outputs:` block at all, so registry.js's
//     attachLegacyPorts (src/core/registry.js:120) gives it the frozen legacy row
//     src/core/legacy-ports.js:279-285, a single untyped `{id:'out'}`. There is no sediment port,
//     no velocity port, and no lens. THAT is the named red this oracle prints today.
//
// THREE THINGS THE SPRINT TEXT GETS WRONG ABOUT THE EXISTING LEDGER, all measured:
//   1. "assert erodedVolume = depositedVolume + exportedOrSuspendedVolume" is VACUOUS against the
//      shipped droplet ledgers: src/core/gpu.js:617 and :634 set `exported = sumIn - sumOut` with
//      `exportedDerived:true`. That identity closes by construction for any implementation,
//      including one that deletes the terrain. So `ledgerIsItemizedNotDerived` is gated FIRST and
//      the closure is only read from a ledger that names its loss independently.
//   2. The same is nearly true of the pipe ledger's cropped view: gpu.js:414 defines
//      `cropExchange = sumIn - sumOut`, and net-eroded minus net-deposited over the crop IS
//      sumIn - sumOut. A closure over height sums alone is therefore algebraically forced. The
//      only non-circular deposited term is one that arrives on its OWN channel — which is what
//      S3.1 is for, and why this gate cannot go green without the port.
//   3. "each with exactly one readPixels call" is asserted nowhere and counted nowhere:
//      `readbacks:1` at gpu.js:616 and :631 is a LITERAL in an object, and the pipe ledger has no
//      such field at all. This oracle counts gl.readPixels itself (src/core/gpu.js:77 is the only
//      call site in the app) and gates the ledger's claim against the count.
//
// THE ACCEPTANCE CONTRACT THIS FILE FIXES (S3.1 has latitude on names; it has none on meaning):
//   * TYPES.hydraulic.outputs declares a primary scalarRaster height plus a port with
//     semantic 'sediment', unit 'm', lens 'state' (the vocabulary already exists —
//     src/core/ports.js SEMANTICS.sediment / UNITS.m / LENSES 'state'), and, when the Pipe stage
//     runs, a port with semantic 'velocity', kind vectorRaster, unit 'mPerS', lens 'state'. On the
//     hex compatibility path there is NO pipe solver — hydraulic.js:98 sends the Pipe stage into
//     the droplet kernel, and the hex ledger measured here reads engine="droplets" — so a velocity
//     port there would be a fabricated cell field, which sprint line 99-100 forbids outright.
//   * The sediment port is demand-driven exactly as src/plugins/data/normals.js does it: absent
//     from `_outputs` when no edge names it, present when one does, `_field` still the primary.
//   * The mass ledger gains physical volumes: cellAreaM2, eroded/detached m3, deposited m3, and a
//     NAMED exported-or-suspended m3. Aliases are accepted (see LEDGER_KEYS) — the words are the
//     story's, the meaning is not negotiable.
//
// HOW EACH GATE IS ARMED. Every bound is a comparison between two MEASURED quantities or against
// an analytically known answer; there is no inherited tolerance:
//   * The zero-set test runs on a NO-TRANSPORT control (erode=0, deposit=0) and a FLAT control,
//     where the known answer is "sediment is identically zero" — no deposition can have occurred,
//     on either engine, by inspection of both kernels. `predictionFailsTheZeroTest` measures the
//     other endpoint TODAY: production's own d_deposits (the morphological prediction the sprint
//     says to replace) is non-zero on that same control, so the test demonstrably can fail.
//   * The float bound is computed: gamma_n = (n*2^-24)/(1 - n*2^-24) with n = N-1 for an N-term
//     Float32 reduction, times the sum of |terms|. N and n are printed.
//   * Cell area is the analytic lattice constant — square s^2, hex sqrt(3)/2*s^2 (legacy.js:5484
//     states the hex world footprint truthfully, and HEX_SQUARE_WORLD at legacy.js:160 makes the
//     row count round(RES*2/sqrt3), NOT RES). Production's claimed area is gated against it.
//
// RED-RUN NUMBERS (this build, RES=128, fbm seed 7, USE_GPU on square / CPU compatibility on hex):
//   square 16384 cells, s=39.0625 m, area 1525.8789 m2, n=16383, gamma=9.77e-4, one readback,
//     net eroded 2.6431e8 m3, ledger engine=pipes exportedDerived=false, NO volume keys at all;
//   hex 148 rows (NOT 128) x 128, area 1321.4499 m2, n=18943, gamma=1.13e-3, zero readbacks,
//     net eroded 1.8445e9 m3, ledger engine=droplets exportedDerived=false, NO volume keys;
//   both lattices: outputs = ['out'] only, ports.source='legacy-adapter', so the run is red at
//   sedimentPortDeclared and stays red through every state gate. 16 named gates red, 9 green.
//   The two inert controls both measure maxAbsHeightDelta EXACTLY 0, and production's own
//   d_deposits prediction is non-zero on 10501/16384 (square) and 12023/18944 (hex) of the cells
//   of that same inert control — which is the endpoint that arms the zero test.
//
// MUTATIONS. All five replace the live TYPES.hydraulic ENTRY (never write through it: the legacy
// port descriptors are Object.freeze'd at legacy-ports.js:540-541, so a write-through would be a
// silent no-op under sloppy-mode page.evaluate). `mutationPerturbedTheRegistry` proves the
// registry actually moved before any other gate is believed — measured ok for all five today.
//
// HONESTY ABOUT WHAT THE MUTATIONS PROVE TODAY. Only `ledger-readbacks-hardcoded` discriminates on
// this build: it moves `oneReadbackPerEvaluation` from a measured green (1 readback) to a measured
// red (2), which is a control armed between two measured endpoints right now. The other four
// perturb the sediment CHANNEL, and there is no channel yet — they land on the registry (proven by
// mutationPerturbedTheRegistry) and the run stays red at the declaration gate. They become
// discriminating the moment S3.1 declares the port, and NOT before; that is a property of writing
// the gate first, not of the controls being weak. Do not "fix" this by having the mutant supply a
// stand-in sediment raster: an oracle that grades its own stand-in is the vacuity this suite keeps
// finding.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'hex-area-as-square',        // depths divided by s^2 on hex: a square-area accounting of the same volume
  'smeared-prediction',        // the sediment channel carries production's own d_deposits map instead
  'sediment-omitted',          // the port and its value are dropped from the registry entry's result
  'ledger-readbacks-hardcoded',// two solver passes are run while the ledger still claims one readback
  'sediment-normalized-units', // the depth raster ships normalized instead of in metres
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

;(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1200, height: 800 } })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1500)

  const report = await page.evaluate(mutation => {
    const out = { mutation: mutation || null, notes: [], fatal: null, lattices: {} }
    const HEX_ROW = Math.sqrt(3) / 2                       // legacy.js:5487, restated analytically
    const REF_DEPTH = 25                                   // d_deposits' own default full-mask depth

    // ---- generic helpers (double precision throughout; JS numbers ARE doubles) ---------------
    const digest = f => {
      if (!f || !f.length) return 'empty'
      let a = 0x811c9dc5
      for (let i = 0; i < f.length; i++) { a = (a ^ (Math.round(f[i] * 1e7) | 0)) >>> 0; a = Math.imul(a, 16777619) >>> 0 }
      return a.toString(16) + ':' + f.length
    }
    const bytesEqual = (a, b) => {
      if (!a || !b || a.length !== b.length) return false
      const x = new Uint8Array(a.buffer, a.byteOffset, a.byteLength)
      const y = new Uint8Array(b.buffer, b.byteOffset, b.byteLength)
      for (let i = 0; i < x.length; i++) if (x[i] !== y[i]) return false
      return true
    }
    const scaled = (f, k) => { const o = new Float32Array(f.length); for (let i = 0; i < f.length; i++) o[i] = f[i] * k; return o }
    const stats = f => {
      if (!f || !f.length) return null
      let mn = Infinity, mx = -Infinity, sum = 0, abs = 0, nz = 0, finite = true, neg = 0
      for (let i = 0; i < f.length; i++) {
        const v = f[i]
        if (!Number.isFinite(v)) { finite = false; continue }
        if (v < mn) mn = v; if (v > mx) mx = v
        sum += v; abs += Math.abs(v); if (v !== 0) nz++; if (v < 0) neg++
      }
      return { len: f.length, min: mn, max: mx, sum, abs, nonZero: nz, negatives: neg, finite }
    }
    // The morphological PREDICTION the sprint says a state channel must not be — taken from the
    // live registry, not reimplemented here, and expressed in metres so it is a credible impostor.
    const predictionMetres = surf => {
      const mask = TYPES.d_deposits.eval({ radius: 3, refDepth: REF_DEPTH }, [surf], { params: {} },
        { demanded: new Set(['out']) })
      return scaled(mask, REF_DEPTH)
    }

    // ---- port discovery on the LIVE registry -------------------------------------------------
    const outsOf = () => (TYPES.hydraulic && TYPES.hydraulic.outputs) || []
    const primaryId = () => { const o = outsOf(); const p = o.find(x => x && x.primary) || o[0]; return p ? p.id : 'out' }
    const portBySemantic = sem => outsOf().find(x => x && x.semantic === sem) || null
    const descriptorOf = p => p ? {
      id: p.id, kind: p.kind || null, storage: p.storage || null, components: p.components == null ? null : p.components,
      semantic: p.semantic || null, unit: p.unit || null, lens: p.lens || null, primary: !!p.primary,
    } : null

    // ---- MUTATIONS: replace the registry entry, never write through it -----------------------
    const ORIGINAL = TYPES.hydraulic
    const ORIGINAL_OUTPUTS = ORIGINAL && ORIGINAL.outputs
    if (mutation) {
      const mutantOutputs = mutation === 'sediment-omitted'
        ? (ORIGINAL_OUTPUTS || []).filter(p => !p || p.semantic !== 'sediment').map(p => ({ ...p }))
        : ORIGINAL_OUTPUTS
      const wrapped = (p, ins, node, ctx) => {
        const raw = ORIGINAL.eval(p, ins, node, ctx)
        // A two-pass implementation: the height pass and the state pass each read back, while the
        // ledger goes on claiming one synchronisation point. The claim is a literal today
        // (gpu.js:616,631), so only an independent COUNT can catch this.
        if (mutation === 'ledger-readbacks-hardcoded') ORIGINAL.eval(p, ins, node, ctx)
        const pid = (mutantOutputs || []).length
          ? ((mutantOutputs.find(x => x && x.primary) || mutantOutputs[0]).id) : 'out'
        const values = raw && raw.values instanceof Map ? new Map(raw.values) : new Map([[pid, raw]])
        const sed = (mutantOutputs || []).find(x => x && x.semantic === 'sediment')
        const height = values.get(pid)
        if (sed) {
          if (mutation === 'sediment-omitted') values.delete(sed.id)
          else if (values.has(sed.id)) {
            const v = values.get(sed.id)
            if (mutation === 'smeared-prediction' && height) values.set(sed.id, predictionMetres(height))
            // depth = volume / s^2 instead of volume / (sqrt3/2 s^2): the same deposited volume
            // divided by the square cell area on a hex lattice.
            else if (mutation === 'hex-area-as-square' && terrainDef.lattice === 'hex') values.set(sed.id, scaled(v, HEX_ROW))
            else if (mutation === 'sediment-normalized-units') values.set(sed.id, scaled(v, 1 / (terrainDef.height || 1)))
          }
        }
        return { values }
      }
      TYPES.hydraulic = { ...ORIGINAL, eval: wrapped, outputs: mutantOutputs }
    }
    out.registryMoved = mutation ? (TYPES.hydraulic !== ORIGINAL && TYPES.hydraulic.eval !== ORIGINAL.eval) : null
    out.outputsIdentityMoved = mutation === 'sediment-omitted'
      ? (TYPES.hydraulic.outputs !== ORIGINAL_OUTPUTS) : null

    // ---- production parameter block ----------------------------------------------------------
    const baseParams = extra => {
      const p = {}
      for (const pr of TYPES.hydraulic.params) p[pr.key] = pr.def
      p.engine = null; p.pipeEnabled = true; p.dropletEnabled = false
      p.seed = 1; p.feat = 1
      return Object.assign(p, extra || {})
    }

    // One production evaluation. Counts gl.readPixels around it (gpu.js:77 is the only call site),
    // then snapshots the ledger production wrote.
    const evaluate = (params, base, demandState) => {
      const pid = primaryId()
      const sedPort = portBySemantic('sediment')
      const velPort = portBySemantic('velocity')
      const demanded = new Set([pid])
      if (demandState && sedPort) demanded.add(sedPort.id)
      if (demandState && velPort) demanded.add(velPort.id)
      let readbacks = 0, restore = null
      try {
        if (typeof GPU !== 'undefined' && GPU && typeof GPU.init === 'function') GPU.init()
        if (typeof gl !== 'undefined' && gl && typeof gl.readPixels === 'function') {
          const orig = gl.readPixels, ctxGl = gl
          ctxGl.readPixels = function (...a) { readbacks++; return orig.apply(this, a) }
          restore = () => { ctxGl.readPixels = orig }
        }
      } catch (e) { out.notes.push('readback instrument: ' + e.message) }
      let raw = null, err = null
      try { raw = TYPES.hydraulic.eval(params, [base, null], { id: -1, type: 'hydraulic', params }, { demanded }) }
      catch (e) { err = String((e && e.message) || e) }
      finally { if (restore) restore() }
      const values = raw && raw.values instanceof Map ? raw.values
        : (raw ? new Map([[pid, raw]]) : new Map())
      const led = (typeof hydroMassDiag !== 'undefined' && hydroMassDiag)
        ? JSON.parse(JSON.stringify(hydroMassDiag)) : null
      return {
        primaryId: pid, sediment: sedPort ? values.get(sedPort.id) || null : null,
        velocity: velPort ? values.get(velPort.id) || null : null,
        height: values.get(pid) || null, keys: [...values.keys()], readbacks, err, ledger: led,
        typed: !!(raw && raw.values instanceof Map),
      }
    }

    // ---- ledger key resolution (the story's words, aliases accepted) --------------------------
    const LEDGER_KEYS = {
      cellArea: ['cellAreaM2', 'cellAreaM²', 'cellArea'],
      eroded: ['erodedM3', 'detachedM3', 'bedrockDetachedM3', 'consumedM3', 'erodedVolumeM3'],
      deposited: ['depositedM3', 'depositedCoverM3', 'depositedVolumeM3'],
      loss: ['exportedOrSuspendedM3', 'exportedM3', 'boundaryExportM3', 'exportedOrSuspendedVolumeM3'],
    }
    const pick = (led, names) => {
      for (const k of names) if (led && Number.isFinite(led[k])) return { key: k, value: led[k] }
      return null
    }
    const readVolumes = led => ({
      present: !!led, engine: led ? led.engine : null,
      exportedDerived: led ? led.exportedDerived : null,
      readbacksClaimed: led && Number.isFinite(led.readbacks) ? led.readbacks : null,
      cellArea: pick(led, LEDGER_KEYS.cellArea), eroded: pick(led, LEDGER_KEYS.eroded),
      deposited: pick(led, LEDGER_KEYS.deposited), loss: pick(led, LEDGER_KEYS.loss),
    })

    // ---- one lattice ------------------------------------------------------------------------
    const measure = lattice => {
      const m = { lattice }
      terrainDef.lattice = lattice
      RES = 128; TARGET_RES = 128; SCALE_RES = false; BUILD_QUALITY = 'final'; XF = null
      USE_GPU = lattice === 'square'
      buildIndex()
      const W = fieldW(), H = fieldH(), N = W * H, s = cellSizeM()
      // The analytic known answer. legacy.js:160-165 makes the hex row count round(RES*2/sqrt3) so
      // the world stays square; legacy.js:5484 states the footprint is scale x scale*sqrt(3)/2 in
      // metres for `rows = RES`. Cell area is the lattice constant either way.
      const cellAreaM2 = lattice === 'hex' ? HEX_ROW * s * s : s * s
      m.res = RES; m.rows = H; m.cells = N; m.cellSizeM = s
      m.cellAreaOracleM2 = cellAreaM2
      m.heightScaleM = terrainDef.height
      m.worldFootprintM2 = (W * s) * (lattice === 'hex' ? H * s * HEX_ROW : H * s)
      m.gpuPath = lattice === 'square' && typeof gpuReady === 'function' ? !!gpuReady() : false
      // n for the float bound: the largest reduction here is an N-term Float32 sum.
      m.gammaTerms = N - 1
      m.gamma = (m.gammaTerms * Math.pow(2, -24)) / (1 - m.gammaTerms * Math.pow(2, -24))

      // ---- fixtures ------------------------------------------------------------------------
      const fbm = fbmField(gnoise, { seed: 7, freq: 3, octaves: 6, lac: 2, gain: 0.5 })
      const flat = newField(0.5)
      m.fixtures = { fbm: digest(fbm), flat: digest(flat), fbmStats: stats(fbm) }

      // ---- the working run, with state demanded ---------------------------------------------
      const work = evaluate(baseParams(), fbm, true)
      m.work = {
        typed: work.typed, keys: work.keys, err: work.err, readbacks: work.readbacks,
        heightDigest: digest(work.height), hasSediment: !!work.sediment, hasVelocity: !!work.velocity,
        sedimentStats: stats(work.sediment), velocityLen: work.velocity ? work.velocity.length : null,
        ledger: work.ledger, volumes: readVolumes(work.ledger),
      }
      // Height-side quantities the oracle derives itself, in double, in m3.
      if (work.height && work.height.length === N) {
        let ePos = 0, dPos = 0, maxRise = 0
        for (let i = 0; i < N; i++) {
          const d = work.height[i] - fbm[i]
          if (d < 0) ePos -= d; else { dPos += d; if (d > maxRise) maxRise = d }
        }
        m.work.netErodedM3 = ePos * m.heightScaleM * cellAreaM2
        m.work.netDepositedM3 = dPos * m.heightScaleM * cellAreaM2
        m.work.maxRiseNormalized = maxRise
      }
      // The independent deposited term: the state channel integrated with the LATTICE-CORRECT area.
      if (work.sediment && work.sediment.length === N) {
        let sum = 0, abs = 0
        for (let i = 0; i < N; i++) { sum += work.sediment[i]; abs += Math.abs(work.sediment[i]) }
        m.work.sedimentVolumeM3 = sum * cellAreaM2
        m.work.sedimentAbsVolumeM3 = abs * cellAreaM2
      }
      // Support comparison against production's own prediction on the SAME surface.
      if (work.height && work.height.length === N) {
        const pred = predictionMetres(work.height)
        const ps = stats(pred)
        m.work.predictionSupport = ps ? ps.nonZero / N : null
        m.work.predictionStats = ps
        m.work.sedimentSupport = m.work.sedimentStats ? m.work.sedimentStats.nonZero / N : null
      }

      // ---- repeatability: same seed, same device --------------------------------------------
      const again = evaluate(baseParams(), fbm, true)
      m.repeat = {
        heightIdentical: bytesEqual(work.height, again.height),
        sedimentPresent: !!again.sediment,
        sedimentIdentical: !!(work.sediment && again.sediment) && bytesEqual(work.sediment, again.sediment),
      }

      // ---- NO-TRANSPORT control: erode = deposit = 0 -----------------------------------------
      // Known answer, by inspection of both kernels: gpu.js:604-606 gives er=dep=0 when the rates
      // are 0, legacy.js:3009-3014 gives amt=0 in both branches, so NO deposition can occur and a
      // deposited-cover state must be identically zero. A morphological prediction is not.
      const inert = evaluate(baseParams({ pipeErode: 0, pipeDeposit: 0, dropletErode: 0, dropletDeposit: 0 }), fbm, true)
      let inertMaxDelta = 0
      if (inert.height && inert.height.length === N) {
        for (let i = 0; i < N; i++) { const d = Math.abs(inert.height[i] - fbm[i]); if (d > inertMaxDelta) inertMaxDelta = d }
      }
      const inertPred = stats(predictionMetres(inert.height && inert.height.length === N ? inert.height : fbm))
      m.inert = {
        err: inert.err, maxAbsHeightDelta: inertMaxDelta, hasSediment: !!inert.sediment,
        sedimentStats: stats(inert.sediment),
        sedimentAllZero: !!inert.sediment && inert.sediment.length === N && inert.sediment.every(v => v === 0),
        predictionNonZero: inertPred ? inertPred.nonZero : 0,
        predictionShare: inertPred ? inertPred.nonZero / N : 0,
      }

      // ---- FLAT control: zero slope, full transport ------------------------------------------
      const still = evaluate(baseParams(), flat, true)
      let stillMaxDelta = 0
      if (still.height && still.height.length === N) {
        for (let i = 0; i < N; i++) { const d = Math.abs(still.height[i] - flat[i]); if (d > stillMaxDelta) stillMaxDelta = d }
      }
      m.flat = {
        err: still.err, maxAbsHeightDelta: stillMaxDelta, hasSediment: !!still.sediment,
        sedimentAllZero: !!still.sediment && still.sediment.length === N && still.sediment.every(v => v === 0),
      }

      m.ports = {
        primary: descriptorOf(outsOf().find(x => x && x.primary) || outsOf()[0] || null),
        sediment: descriptorOf(portBySemantic('sediment')),
        velocity: descriptorOf(portBySemantic('velocity')),
        declaredIds: outsOf().map(p => p && p.id),
        source: TYPES.hydraulic.ports ? TYPES.hydraulic.ports.source : null,
      }
      return m
    }

    // ---- demand-driven wiring, on the real graph (square only: this is port plumbing) --------
    const demandProbe = () => {
      const d = { err: null }
      try {
        terrainDef.lattice = 'square'; RES = 128; TARGET_RES = 128; SCALE_RES = false
        USE_GPU = true; buildIndex()
        nodes.length = 0; edges.length = 0
        const src = makeNode('perlin', 60, 60); src.params.seed = 7
        const hyd = makeNode('hydraulic', 260, 60)
        Object.assign(hyd.params, baseParams())
        const sink = makeNode('output', 460, 60)
        const pid = primaryId()
        edges.push({ from: src.id, fromPort: 'out', to: hyd.id, toPort: 'in', slot: 0 })
        edges.push({ from: hyd.id, fromPort: pid, to: sink.id, toPort: 'height', slot: 0 })
        nodes.forEach(n => { n._dirty = true })
        evalGraph()
        const sedPort = portBySemantic('sediment')
        d.primaryId = pid
        d.sedPortId = sedPort ? sedPort.id : null
        d.undemandedKeys = hyd._outputs ? [...hyd._outputs.keys()] : []
        d.undemandedHasSediment = !!(hyd._outputs && sedPort && hyd._outputs.get(sedPort.id))
        d.fieldIsPrimary = !!(hyd._outputs && hyd._field === hyd._outputs.get(pid))
        if (sedPort) {
          const sink2 = makeNode('output', 460, 260)
          edges.push({ from: hyd.id, fromPort: sedPort.id, to: sink2.id, toPort: 'height', slot: 0 })
          nodes.forEach(n => { n._dirty = true })
          evalGraph()
          const v = hyd._outputs && hyd._outputs.get(sedPort.id)
          d.demandedHasSediment = !!v
          d.demandedLength = v ? v.length : null
          d.expectedLength = fieldW() * fieldH()
          d.fieldStillPrimary = !!(hyd._outputs && hyd._field === hyd._outputs.get(pid))
        } else {
          d.demandedHasSediment = false; d.demandedLength = null
          d.expectedLength = fieldW() * fieldH(); d.fieldStillPrimary = d.fieldIsPrimary
        }
      } catch (e) { d.err = String((e && e.message) || e) }
      return d
    }

    try {
      out.lattices.square = measure('square')
      out.lattices.hex = measure('hex')
      out.demand = demandProbe()
      out.fixturesDistinct = out.lattices.square.fixtures.fbm !== out.lattices.hex.fixtures.fbm
        && out.lattices.square.fixtures.fbm !== out.lattices.square.fixtures.flat
    } catch (e) {
      out.fatal = String((e && e.stack) || e)
    }
    return out
  }, mutation)

  // ================================ GATES (Node side) ========================================
  const sq = (report.lattices && report.lattices.square) || null
  const hx = (report.lattices && report.lattices.hex) || null
  const dm = report.demand || {}
  const L = [sq, hx].filter(Boolean)

  const isStatePort = p => !!p && p.kind === 'scalarRaster' && p.semantic === 'sediment'
    && p.unit === 'm' && p.lens === 'state'
  const isVelocityPort = p => !!p && p.kind === 'vectorRaster' && p.semantic === 'velocity'
    && p.unit === 'mPerS' && p.lens === 'state' && p.components >= 2
  // |a - b| <= gamma_(N-1) * sum|terms| — the bound is computed from the term count, never chosen.
  const within = (delta, absSum, gamma) => Number.isFinite(delta) && Number.isFinite(absSum)
    && Math.abs(delta) <= gamma * Math.max(absSum, 0)

  const closureOf = m => {
    const v = m && m.work && m.work.volumes
    if (!v || !v.present || v.exportedDerived !== false) return null
    if (!v.eroded || !v.deposited || !v.loss) return null
    const residual = v.eroded.value - v.deposited.value - v.loss.value
    const scale = Math.abs(v.eroded.value) + Math.abs(v.deposited.value) + Math.abs(v.loss.value)
    return { residual, scale, ok: within(residual, scale, m.gamma), terms: v }
  }
  const integralOf = m => {
    const v = m && m.work && m.work.volumes
    if (!v || !v.deposited || !Number.isFinite(m.work.sedimentVolumeM3)) return null
    const delta = m.work.sedimentVolumeM3 - v.deposited.value
    return { delta, absSum: m.work.sedimentAbsVolumeM3, ok: within(delta, m.work.sedimentAbsVolumeM3, m.gamma) }
  }
  const areaOk = m => {
    const v = m && m.work && m.work.volumes
    if (!v || !v.cellArea) return false
    const g1 = (1 * Math.pow(2, -24)) / (1 - 1 * Math.pow(2, -24))
    return Math.abs(v.cellArea.value - m.cellAreaOracleM2) <= g1 * m.cellAreaOracleM2
  }

  const closureSq = sq && closureOf(sq), closureHx = hx && closureOf(hx)
  const integralSq = sq && integralOf(sq), integralHx = hx && integralOf(hx)

  const gates = {
    // --- the declaration: nothing declares these today ---------------------------------------
    sedimentPortDeclared: L.length === 2 && L.every(m => !!m.ports.sediment),
    sedimentPortIsPhysicalState: L.length === 2 && L.every(m => isStatePort(m.ports.sediment)),
    // Velocity is a PIPE cell field. It is required exactly where the pipe kernel runs (the square
    // GPU path) and must NOT be fabricated on the hex compatibility path, which routes the Pipe
    // stage into the DROPLET kernel (src/plugins/ero/hydraulic.js:98 — measured: the hex ledger
    // reads engine="droplets"). Sprint line 99-100: "never label raw per-particle terminal speed as
    // a cell field". Requiring it on both lattices would force exactly that fabrication.
    velocityPortDeclaredWherePipeRuns: !!sq && sq.gpuPath === true && isVelocityPort(sq.ports.velocity),
    hexDeclaresNoPipeVelocity: !!hx && !!hx.ports.sediment && hx.work.hasSediment === true
      && hx.work.hasVelocity === false,
    primaryStaysScalarHeight: L.length === 2 && L.every(m => !!m.ports.primary
      && m.ports.primary.kind === 'scalarRaster' && m.ports.primary.primary === true),

    // --- demand-driven, on the real graph ----------------------------------------------------
    sedimentIsDemandDriven: dm.err === null && dm.sedPortId !== null
      && dm.undemandedHasSediment === false && dm.demandedHasSediment === true
      && dm.demandedLength === dm.expectedLength && dm.fieldStillPrimary === true,

    // --- the zero set: a state channel is zero where no deposition happened -------------------
    sedimentZeroWithoutTransport: L.length === 2 && L.every(m => m.inert.hasSediment && m.inert.sedimentAllZero),
    sedimentZeroOnFlatTerrain: L.length === 2 && L.every(m => m.flat.hasSediment && m.flat.sedimentAllZero),
    // ARMED BY MEASUREMENT (green today): the same test applied to production's own morphological
    // prediction fails on the same control, so the zero test demonstrably discriminates.
    predictionFailsTheZeroTest: L.length === 2 && L.every(m => m.inert.predictionNonZero > 0
      && m.inert.predictionShare > 0.01),
    noTransportControlIsInert: L.length === 2 && L.every(m => m.inert.err === null && m.inert.maxAbsHeightDelta === 0),
    flatControlIsInert: L.length === 2 && L.every(m => m.flat.err === null && m.flat.maxAbsHeightDelta === 0),
    sedimentSupportSparserThanPrediction: L.length === 2 && L.every(m => Number.isFinite(m.work.sedimentSupport)
      && Number.isFinite(m.work.predictionSupport) && m.work.sedimentSupport < m.work.predictionSupport),

    // --- physical volume, with the lattice-correct cell area ----------------------------------
    ledgerIsItemizedNotDerived: L.length === 2 && L.every(m => m.work.volumes.present
      && m.work.volumes.exportedDerived === false),
    ledgerCellAreaMatchesLattice: L.length === 2 && L.every(areaOk),
    volumeClosureSquare: !!(closureSq && closureSq.ok),
    volumeClosureHex: !!(closureHx && closureHx.ok),
    sedimentIntegralMatchesLedgerSquare: !!(integralSq && integralSq.ok),
    sedimentIntegralMatchesLedgerHex: !!(integralHx && integralHx.ok),
    sedimentIsFiniteNonNegativeMetres: L.length === 2 && L.every(m => {
      const s = m.work.sedimentStats
      return !!s && s.finite && s.negatives === 0 && s.max > 0 && s.max < m.heightScaleM
    }),

    // --- ADR-002: one synchronisation point, COUNTED not claimed ------------------------------
    // ARMED BY MEASUREMENT (green today): one state-demanding evaluation of the square GPU path
    // costs exactly one gl.readPixels, and the hex compatibility path costs none. Both endpoints
    // are measured on this build, so a second solver pass moves this gate and nothing else has to.
    oneReadbackPerEvaluation: !!sq && sq.gpuPath === true && sq.work.readbacks === 1
      && !!hx && hx.work.readbacks === 0,
    ledgerReadbackClaimMatchesCount: !!sq && sq.work.volumes.readbacksClaimed === sq.work.readbacks
      && sq.work.volumes.readbacksClaimed === 1,

    // --- repeatability -----------------------------------------------------------------------
    sedimentRepeatableSameSeed: L.length === 2 && L.every(m => m.repeat.sedimentPresent && m.repeat.sedimentIdentical),
    heightRepeatableSameSeed: L.length === 2 && L.every(m => m.repeat.heightIdentical),

    // --- absence of evidence is a failure -----------------------------------------------------
    evidenceNonEmpty: L.length === 2 && report.fatal === null
      && L.every(m => m.cells > 1000 && m.fixtures.fbmStats && m.fixtures.fbmStats.finite
        && m.fixtures.fbmStats.max > m.fixtures.fbmStats.min
        && Number.isFinite(m.work.netErodedM3) && m.work.netErodedM3 > 0
        && m.work.err === null)
      && report.fixturesDistinct === true && hx.rows !== hx.res && sq.rows === sq.res,
    productionEvaluatedWithoutThrowing: report.fatal === null && L.length === 2
      && L.every(m => m.work.err === null && m.inert.err === null && m.flat.err === null) && dm.err === null,
  }
  if (mutation) {
    gates.mutationPerturbedTheRegistry = report.registryMoved === true
      && (mutation !== 'sediment-omitted' || report.outputsIdentityMoved === true)
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)

  // ---- readable evidence -------------------------------------------------------------------
  const num = v => (Number.isFinite(v) ? (Math.abs(v) >= 1e6 || (v !== 0 && Math.abs(v) < 1e-4) ? v.toExponential(4) : +v.toFixed(6)) : String(v))
  console.log('== S3.1 hydraulic state outputs ==')
  for (const m of L) {
    console.log(`  ${m.lattice}: RES=${m.res} rows=${m.rows} cells=${m.cells} cell=${num(m.cellSizeM)}m `
      + `areaOracle=${num(m.cellAreaOracleM2)}m2 heightScale=${m.heightScaleM}m gpuPath=${m.gpuPath} `
      + `n=${m.gammaTerms} gamma=${num(m.gamma)}`)
    console.log(`    ports: ${JSON.stringify(m.ports)}`)
    console.log(`    work:  typed=${m.work.typed} keys=[${m.work.keys}] readbacks=${m.work.readbacks} `
      + `sediment=${m.work.hasSediment} velocity=${m.work.hasVelocity} `
      + `netEroded=${num(m.work.netErodedM3)}m3 netDeposited=${num(m.work.netDepositedM3)}m3 `
      + `sedimentVol=${num(m.work.sedimentVolumeM3)}m3 predSupport=${num(m.work.predictionSupport)} `
      + `sedSupport=${num(m.work.sedimentSupport)}`)
    console.log(`    ledger: ${JSON.stringify(m.work.ledger)}`)
    console.log(`    volumes: ${JSON.stringify(m.work.volumes)}`)
    console.log(`    inert(erode=deposit=0): maxHeightDelta=${num(m.inert.maxAbsHeightDelta)} `
      + `sediment=${m.inert.hasSediment} allZero=${m.inert.sedimentAllZero} `
      + `predictionNonZero=${m.inert.predictionNonZero}/${m.cells} (${num(m.inert.predictionShare)})`)
    console.log(`    flat: maxHeightDelta=${num(m.flat.maxAbsHeightDelta)} sediment=${m.flat.hasSediment} allZero=${m.flat.sedimentAllZero}`)
    console.log(`    repeat: height=${m.repeat.heightIdentical} sediment=${m.repeat.sedimentIdentical}`)
  }
  console.log(`  demand: ${JSON.stringify(dm)}`)
  console.log(`  closure square: ${JSON.stringify(closureSq)}`)
  console.log(`  closure hex:    ${JSON.stringify(closureHx)}`)
  console.log(`  integral square: ${JSON.stringify(integralSq)}  hex: ${JSON.stringify(integralHx)}`)
  for (const [name, pass] of Object.entries(gates)) console.log(`  ${pass ? 'ok  ' : 'RED '} ${name}`)
  if (report.fatal) console.log('  FATAL-IN-PAGE ' + report.fatal)
  if (report.notes.length) console.log('  notes ' + JSON.stringify(report.notes))
  console.log('  errors ' + (errors.length ? JSON.stringify(errors) : 'none'))

  const sedDeclared = sq ? !!sq.ports.sediment : false
  console.log(`${ok ? 'PASS' : 'FAIL'}  sediment state: sedimentPort=${sedDeclared} velocityPort=${sq ? !!sq.ports.velocity : false} `
    + `square[cells=${sq ? sq.cells : 0} area=${sq ? num(sq.cellAreaOracleM2) : 'n/a'}m2 readbacks=${sq ? sq.work.readbacks : 'n/a'} `
    + `netEroded=${sq ? num(sq.work.netErodedM3) : 'n/a'}m3] `
    + `hex[rows=${hx ? hx.rows : 0} area=${hx ? num(hx.cellAreaOracleM2) : 'n/a'}m2 netEroded=${hx ? num(hx.work.netErodedM3) : 'n/a'}m3] `
    + `gamma=${sq ? num(sq.gamma) : 'n/a'}/${hx ? num(hx.gamma) : 'n/a'} n=${sq ? sq.gammaTerms : 0}/${hx ? hx.gammaTerms : 0} `
    + `predictionSmear=${hx ? hx.inert.predictionNonZero : 0}cells failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', (error && error.stack) || error); process.exit(2) })
