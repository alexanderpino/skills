// S3.4 — explicit cover-state selectors, and `d_deposits` as a LABELLED prediction fallback.
//
// RED-FIRST. Sprint 3's Ready condition (docs/plan/sprint-03-cover-layer.md:84-85) requires this
// fixture to be observed failing before the implementation exists, because a gate first seen green
// is a gate that has never been seen to fail. So this file is expected to print FAIL today, and it
// must do so by a NAMED GATE rather than by throwing: every access below to something S3.4 has not
// built yet is guarded, so the run always reaches the gate table and prints which named claims are
// unmet. A throw would prove the probe is broken; a named red proves the feature is absent.
//
// THE CONTRACT, in one sentence: typed wires, never a graph-global hidden lookup. A node that needs
// cover state reads it from a CONNECTED TYPED PORT. A disconnected required state is a typed
// missing-input error — never silent zeros, and never a walk of the graph to find "a nearby
// producer".
//
// WHY SILENT ZEROS ARE THE NAMED FAILURE, and not merely untidy. A zero cover field is physically
// meaningful: it is bare bedrock, the state every `soilDepth` map starts in and the state a slope
// returns to once transport has stripped it. If "not wired" also renders as zeros, the two are
// indistinguishable, and every downstream mass balance silently attributes real bedrock exposure to
// a missing wire. That is why `wiredZeroStateIsNotAnError` sits directly beside
// `disconnectedSelectorRaisesTypedMissingInput` below: the pair is the whole claim. One of them
// alone would be satisfied by a build that errors on every zero field, or by one that errors on
// nothing.
//
// WHAT THIS FILE DEMANDS OF THE IMPLEMENTATION, stated up front so the story is not guessing:
//
//   * A selector node type per cover state. Resolved from the registry either by the canonical id
//     (`s_soilDepth`, `s_sedimentDepth`, `s_sandDepth`) or by a def carrying
//     `stateSelector: '<auxMapId>'`. Either is accepted; inventing a third naming is not, because
//     then nothing can name what is missing.
//   * Its state input is declared `required: true`, `unit: 'm'`, `lens: 'state'`, and a NON-GENERIC
//     semantic whose SEMANTICS entry is a scalarRaster in metres. `anyScalarRaster` is not a typed
//     state port; it is the absence of one.
//   * With the port connected, `eval` returns the input's exact bytes. Identity, not approximation.
//   * With it disconnected, a typed problem with `code === 'MISSING_REQUIRED_INPUT'` naming the
//     input port id reaches the caller — through the eval return (`{ problems: [...] }`), through a
//     typed throw, or through a node stash (`_portProblem` / `_inputProblem` / `_stateProblem`).
//     Any of the three is accepted; the CODE and the named port are not negotiable.
//
//     MEASURED, and it decides the shape of that requirement: evalGraph catches every exception out
//     of `def.eval` and substitutes `newField()` — src/legacy.js:3467-3468,
//     `catch(err){console.error(...);f=newField();...}`. A typed error that is only ever THROWN
//     therefore arrives at the graph as exactly the silent zero field this story exists to forbid.
//     So `graphSurfacesTypedMissingInput` insists the graph path carries the problem on the node,
//     where the inspector already renders such things (src/legacy.js:4260).
//   * `d_deposits` keeps computing its morphological prediction, gains an OPTIONAL explicit sediment
//     state input that it returns byte-for-byte when connected, is labelled a prediction in the
//     registry, and reports which of the two branches ran. "Never substituted silently" means the
//     substitution is not silent — the node has to say.
//
// HOW THE ANSWERS ARE KNOWN. The prediction is not compared against whatever production returns.
// `depositsField` at radius 1 is a grey morphological closing with a 3x3 separable square element
// on square lattice (rd = round(1*(1-1/sqrt2)) = 0, so the diagonal pass drops out and r1 = 1), and
// one dilate/erode pass over the D6 one-ring on hex. Both are recomputed here in Float64 from the
// same fixture, and the comparison bound is derived rather than tuned: max/min select existing
// Float32 values exactly, `closed-inp` is exact in double, so production's only rounding is the
// single Float32 store of the final product — bounded by gamma_1, and gamma_2 is used for headroom.
//
// LATTICE. terrainDef.lattice changes the row count (fieldH = round(RES*2/sqrt3) on hex, not RES)
// AND the structuring element depositsField uses, so the selector claims and the prediction oracle
// both run on square and hex. The graph-wiring phase runs on square only: it exercises the
// edge -> ins plumbing, which is lattice-independent, and says so rather than pretending to cover it.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
// NOTE ON THIS BLOCK'S COMMENTS: scripts/gate.py captures the array with a NON-GREEDY `\[(.*?)\]`,
// so a square bracket anywhere inside it — including inside a `// comment` — truncates the
// allowlist silently. Writing `ins[1]` here cost three of the eight controls before it was
// measured. Prose only below; the rationale for each control lives at its install site.
//
// Every control except `prediction-fixture-degenerate` REPLACES a live TYPES or AUX_MAPS registry
// entry, so what the gates read afterwards is production's own behaviour on a perturbed build.
// None of them writes to a value this file has already computed — the audit that found eleven
// controls doing `r.ok = false` / `afterUndo = 0.75` / `hi = 0.2; lo = 0.2` is why each one is
// described by what it changes in production, and why `mutationPerturbedProduction` reads the
// registry back rather than trusting that the write landed.
const MUTATIONS = [
  // --- the three the story names ------------------------------------------------------------
  'disconnected-selector-returns-zeros', // the pre-fix selector: no input, no problem, a zero field
  'deposits-ignores-connected-state',    // d_deposits drops its state slot and always predicts
  'implicit-graph-lookup',               // the selector finds its producer by scanning the graph
  // --- three more, each arming a claim the three above leave unarmed --------------------------
  'state-port-untyped',               // the state port degrades to a generic, unit none, no lens
  'deposits-not-labelled-prediction', // the prediction label is stripped from the registry entry
  'prediction-fixture-degenerate',    // the fixture stops discriminating: state === prediction
  // --- and two that arm the gates which are GREEN today ---------------------------------------
  'deposits-radius-control-dead',   // the authored radius is ignored, so the closing element moves
  'registry-becomes-a-value-store', // AUX_MAPS grows a per-document field: the hidden global store
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

;(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1400)

  const report = await page.evaluate(mutation => {
    USE_GPU = false; RES = 32; TARGET_RES = 32
    // SCALE_RES false pins resScale() to 1, so d_deposits' `Math.round(p.radius*resScale())` is
    // exactly the radius authored below and the analytic oracle has no free parameter.
    SCALE_RES = false; BUILD_QUALITY = 'interactive'; XF = null; historyReady = false
    terrainDef.lattice = 'square'

    const out = { mutation: mutation || null, lattices: {}, mutationApplied: mutation == null, mutationMoved: null }
    const COVER_STATES = ['soilDepth', 'sedimentDepth', 'sandDepth']
    // The one alias the existing vocabulary already supplies: SEMANTICS.sediment is a scalarRaster
    // in metres (src/core/ports.js:79). soilDepth and sandDepth have no equivalent yet.
    const SEMANTIC_ALIAS = { soilDepth: 'soilDepth', sedimentDepth: 'sediment', sandDepth: 'sandDepth' }
    const CANON = { soilDepth: 's_soilDepth', sedimentDepth: 's_sedimentDepth', sandDepth: 's_sandDepth' }

    const digest = f => {
      if (!f || typeof f.length !== 'number') return 'null'
      let a = 0x811c9dc5, b = 0x01000193
      for (let i = 0; i < f.length; i++) {
        const v = Math.round(f[i] * 1e7) | 0
        a = (a ^ v) >>> 0; a = Math.imul(a, 16777619) >>> 0
        b = (b + Math.imul(v, 2654435761)) >>> 0
      }
      return a.toString(16) + ':' + b.toString(16)
    }
    const sameBytes = (a, b) => {
      if (!a || !b || a.length !== b.length || !a.length) return false
      for (let i = 0; i < a.length; i++) if (!Object.is(a[i], b[i])) return false
      return true
    }
    const isField = v => v && ArrayBuffer.isView(v) && typeof v.length === 'number'
    const allZero = f => isField(f) && f.length > 0 && Array.prototype.every.call(f, v => v === 0)
    const gamma = n => (n * Math.pow(2, -24)) / (1 - n * Math.pow(2, -24))

    // ---- registry resolution, entirely guarded -------------------------------------------------
    const findSelector = mapId => {
      if (TYPES[CANON[mapId]]) return CANON[mapId]
      const k = Object.keys(TYPES).find(t => TYPES[t] && TYPES[t].stateSelector === mapId)
      return k || null
    }
    const selType = {}
    for (const s of COVER_STATES) selType[s] = findSelector(s)
    out.selectorTypes = { ...selType }
    out.selectorsFound = COVER_STATES.filter(s => selType[s]).length

    // ---- MUTATIONS THAT REPLACE PRODUCTION REGISTRY ENTRIES -----------------------------------
    // A port descriptor that came through the legacy adapter is FROZEN (legacy-ports.js:540-541),
    // and a frozen object written through in sloppy-mode page.evaluate fails SILENTLY. So every
    // control here REPLACES the object and then reads the registry back to prove it moved; a
    // control that could not be installed is reported, and `mutationWasApplied` turns it red rather
    // than letting it pass for free.
    const anySel = COVER_STATES.map(s => selType[s]).filter(Boolean)
    const evalsBefore = Object.fromEntries(anySel.map(t => [t, TYPES[t].eval]))
    const inputsBefore = Object.fromEntries(anySel.map(t => [t, (TYPES[t].inputs || [])[0]]))
    const registryMoved = () => anySel.length > 0 && anySel.every(t => TYPES[t].eval !== evalsBefore[t])
    if (mutation === 'disconnected-selector-returns-zeros') {
      for (const t of anySel) {
        // The pre-fix build verbatim: ignore the input entirely, publish a plausible zero cover
        // field, raise nothing. Physically indistinguishable from bare bedrock, which is the point.
        TYPES[t] = { ...TYPES[t], eval: () => newField() }
      }
      out.mutationApplied = anySel.length > 0
      // Read the registry back: the perturbed entry must be the one production will now call, and
      // it must actually behave like the pre-fix build on a non-zero input.
      out.mutationMoved = registryMoved()
        && anySel.every(t => allZero(TYPES[t].eval({}, [newField(0.5)], {})))
    }
    if (mutation === 'implicit-graph-lookup') {
      for (const t of anySel) {
        // The anti-pattern named in the story: resolve the producer by SCANNING THE GRAPH instead
        // of reading the wire. Deterministically picks the first node in `nodes` that has published
        // a field, so a rewire cannot change the answer and a disconnected port cannot be detected.
        TYPES[t] = { ...TYPES[t], eval: (p, ins, nd) => {
          const donor = (typeof nodes !== 'undefined' ? nodes : []).find(n => n && n !== nd && isField(n._field))
          return donor ? donor._field : newField()
        } }
      }
      out.mutationApplied = anySel.length > 0
      out.mutationMoved = registryMoved()
    }
    if (mutation === 'state-port-untyped') {
      for (const t of anySel) {
        const ins0 = (TYPES[t].inputs || [])[0]
        if (!ins0) continue
        // REPLACE, never write through: these descriptors may be frozen.
        const stripped = { ...ins0, semantic: 'anyScalarRaster', unit: 'none', lens: null, required: false }
        TYPES[t] = { ...TYPES[t], inputs: [stripped, ...(TYPES[t].inputs || []).slice(1)] }
      }
      out.mutationApplied = anySel.length > 0
      // The frozen-descriptor trap: a write THROUGH a legacy-adapter port would have been a silent
      // no-op. This asserts the registry now hands out a DIFFERENT object with the stripped type.
      out.mutationMoved = anySel.length > 0 && anySel.every(t => {
        const now = (TYPES[t].inputs || [])[0] || {}
        return now !== inputsBefore[t] && now.semantic === 'anyScalarRaster' && now.unit === 'none'
      })
    }
    if (mutation === 'deposits-ignores-connected-state') {
      const real = TYPES.d_deposits && TYPES.d_deposits.eval
      if (real) {
        // Drop the state slot on the floor and always compute the prediction — which is exactly
        // what the shipping build does today, and exactly the silent substitution S3.4 forbids.
        TYPES.d_deposits = { ...TYPES.d_deposits, eval: (p, ins, nd, ctx) => real(p, [ins && ins[0]], nd, ctx) }
        out.mutationApplied = true
        out.mutationMoved = TYPES.d_deposits.eval !== real
      }
    }
    if (mutation === 'deposits-not-labelled-prediction') {
      if (TYPES.d_deposits) {
        const d = TYPES.d_deposits
        TYPES.d_deposits = { ...d, prediction: false, desc: 'Soil / sediment depth.', name: 'Deposits' }
        out.mutationApplied = true
        out.mutationMoved = TYPES.d_deposits.desc !== d.desc || TYPES.d_deposits.prediction !== d.prediction
      }
    }
    if (mutation === 'deposits-radius-control-dead') {
      const real = TYPES.d_deposits && TYPES.d_deposits.eval
      if (real) {
        // A dead radius control — the defect class this file's own subject already had once
        // ("a double round() of both radii made r=1..5 bit-identical"). Production then builds its
        // closing with the wrong structuring element while the analytic oracle keeps the AUTHORED
        // radius, so the comparison, not the oracle, is what must notice.
        TYPES.d_deposits = { ...TYPES.d_deposits, eval: (p, ins, nd, ctx) => real({ ...p, radius: 3 }, ins, nd, ctx) }
        out.mutationApplied = true
        out.mutationMoved = TYPES.d_deposits.eval !== real
      }
    }
    if (mutation === 'registry-becomes-a-value-store') {
      // AUX_MAPS is Object.freeze'd only at the top level, so its rows are writable — which is
      // exactly why this claim needs asserting rather than assuming. A row carrying an instance
      // value is the graph-global hidden store the contract forbids.
      const AMx = (typeof AUXMAPS !== 'undefined' && AUXMAPS.AUX_MAPS) || {}
      if (AMx.soilDepth) {
        AMx.soilDepth.field = new Float32Array(4)
        out.mutationApplied = true
        out.mutationMoved = 'field' in AMx.soilDepth
      }
    }
    // `prediction-fixture-degenerate` perturbs the FIXTURE production consumes (below), not a
    // result: it makes the state field equal the prediction, so "identity" and "prediction" stop
    // being distinguishable and the evidence gate must refuse the run.

    // ---- the declared port block, per state ----------------------------------------------------
    const SEM = (PORTS && PORTS.SEMANTICS) || {}
    const GEN = (PORTS && PORTS.GENERICS) || {}
    out.ports = {}
    for (const s of COVER_STATES) {
      const t = selType[s], def = t ? TYPES[t] : null
      const inputs = (def && def.inputs) || []
      const outputs = (def && def.outputs) || []
      const req = inputs.filter(p => p && p.required === true)
      const p0 = req[0] || inputs[0] || null
      const semKey = p0 ? p0.semantic : null
      const semRow = semKey ? SEM[semKey] : null
      out.ports[s] = {
        type: t,
        registered: !!def,
        insLabels: (def && def.ins) || null,
        inputCount: inputs.length,
        requiredCount: req.length,
        portId: p0 ? p0.id : null,
        portName: p0 ? (p0.name || p0.id) : null,
        semantic: semKey,
        isGeneric: !!(semKey && GEN[semKey]),
        unit: p0 ? p0.unit : null,
        lens: p0 ? (p0.lens == null ? null : p0.lens) : null,
        // The vocabulary must NAME the state. Today SEMANTICS has `sediment` (m) and nothing for
        // soil or sand — that gap is part of what S3.4 closes.
        semanticIsMetreScalar: !!(semRow && semRow.kind === 'scalarRaster' && semRow.defaultUnit === 'm'),
        vocabularyNamesState: !!SEM[SEMANTIC_ALIAS[s]],
        outputCount: outputs.length,
        outputLens: outputs[0] ? (outputs[0].lens == null ? null : outputs[0].lens) : null,
        outputUnit: outputs[0] ? (outputs[0].unit == null ? null : outputs[0].unit) : null,
      }
    }

    // ---- a typed problem, wherever the implementation chooses to publish it ---------------------
    const problemsFrom = (raw, nd, thrown) => {
      const list = []
      const push = (p, via) => {
        if (!p || typeof p !== 'object') return
        list.push({
          code: p.code == null ? null : String(p.code),
          port: p.port != null ? String(p.port) : (p.detail && p.detail.port != null ? String(p.detail.port) : null),
          message: String(p.message || p.reason || ''),
          via,
        })
      }
      if (thrown) push(thrown, 'throw')
      if (raw && !isField(raw) && typeof raw === 'object') {
        for (const key of ['problems', 'errors']) {
          if (Array.isArray(raw[key])) for (const p of raw[key]) push(p, 'return.' + key)
        }
      }
      for (const key of ['_portProblem', '_inputProblem', '_stateProblem', '_problem']) {
        if (nd && nd[key] && typeof nd[key] === 'object') push(nd[key], key)
      }
      return list
    }
    const namesMissingInput = (probs, portId, portName) => probs.some(p =>
      p.code === 'MISSING_REQUIRED_INPUT'
      && (p.port === portId
        || (portId && p.message.indexOf(portId) >= 0)
        || (portName && p.message.indexOf(portName) >= 0)))

    // Did the node say it fell back to the prediction? true = predicted, false = returned the
    // connected state, null = it did not say, which is the failure "never substituted silently"
    // names. Read from the node stash or the typed return, whichever the implementation chose.
    const predictedFlag = (nd, raw) => {
      for (const k of ['_predicted', '_prediction', '_isPrediction']) {
        if (nd && typeof nd[k] === 'boolean') return nd[k]
      }
      if (raw && !isField(raw) && typeof raw === 'object') {
        for (const k of ['predicted', 'prediction', 'isPrediction']) {
          if (typeof raw[k] === 'boolean') return raw[k]
        }
      }
      return null
    }

    // Call an eval without ever letting it take the run down.
    const call = (type, params, ins, nd) => {
      const def = type ? TYPES[type] : null
      if (!def || typeof def.eval !== 'function') return { ran: false, raw: null, thrown: null, field: null }
      let raw = null, thrown = null
      try { raw = def.eval(params, ins, nd, { demanded: new Set() }) } catch (e) { thrown = e || new Error('threw') }
      const field = isField(raw) ? raw
        : (raw && raw.values instanceof Map ? [...raw.values.values()].find(isField) || null : null)
      return { ran: !thrown, raw, thrown, field }
    }

    // ---- the analytic prediction oracle, recomputed in Float64 ---------------------------------
    // depositsField at radius 1: closing(h) - h, scaled to a [0,1] mask against refDepth. Square
    // uses the separable 3x3 square element (the diagonal pass drops out at r=1 because
    // rd = round(1 - 1/sqrt2) = 0); hex uses one dilate then one erode over the D6 one-ring.
    const morph1Dref = (inp, r, mx, n, nh) => {
      const cl = (v, lo, hi) => v < lo ? lo : (v > hi ? hi : v)
      const g = (f, x, y) => f[cl(y, 0, nh - 1) * n + cl(x, 0, n - 1)]
      const t = new Float64Array(n * nh), o = new Float64Array(n * nh)
      for (let y = 0; y < nh; y++) for (let x = 0; x < n; x++) {
        let v = inp[y * n + x]
        for (let k = -r; k <= r; k++) { const s = g(inp, x + k, y); v = mx ? Math.max(v, s) : Math.min(v, s) }
        t[y * n + x] = v
      }
      for (let y = 0; y < nh; y++) for (let x = 0; x < n; x++) {
        let v = t[y * n + x]
        for (let k = -r; k <= r; k++) { const s = g(t, x, y + k); v = mx ? Math.max(v, s) : Math.min(v, s) }
        o[y * n + x] = v
      }
      return o
    }
    const hexRingRef = (inp, mx, n, nh) => {
      const o = new Float64Array(n * nh)
      for (let y = 0; y < nh; y++) for (let x = 0; x < n; x++) {
        const nb = hexNb(y); let v = inp[y * n + x]
        for (let k = 0; k < 6; k++) {
          const xx = x + nb[k][0], yy = y + nb[k][1]
          if (xx < 0 || yy < 0 || xx >= n || yy >= nh) continue
          const s = inp[yy * n + xx]; v = mx ? Math.max(v, s) : Math.min(v, s)
        }
        o[y * n + x] = v
      }
      return o
    }
    const predictRef = (inp, refDepth, hex, n, nh) => {
      const dil = hex ? hexRingRef(inp, true, n, nh) : morph1Dref(inp, 1, true, n, nh)
      const closed = hex ? hexRingRef(dil, false, n, nh) : morph1Dref(dil, 1, false, n, nh)
      const toM = terrainDef.height / Math.max(1e-6, refDepth)
      const o = new Float64Array(n * nh)
      for (let i = 0; i < o.length; i++) o[i] = Math.min(Math.max(closed[i] - inp[i], 0) * toM, 1)
      return o
    }

    // ---- per-lattice measurement ---------------------------------------------------------------
    const runLattice = lat => {
      terrainDef.lattice = lat
      const n = fieldW(), nh = fieldH(), N = n * nh
      const hex = lat === 'hex'
      const r = { lattice: lat, W: n, H: nh, N, rowsAreNotRes: nh !== RES }

      // A RICH state fixture in metres: identity against a flat field would be satisfied by any
      // constant-returning stub.
      const state = new Float32Array(N)
      for (let i = 0; i < N; i++) state[i] = 0.35 + 0.3 * Math.sin(i * 0.037) + 0.05 * Math.cos(i * 0.211)
      // A second, DIFFERENT state field — the one the rewire claim moves to.
      const other = new Float32Array(N)
      for (let i = 0; i < N; i++) other[i] = 1.7 + 0.4 * Math.cos(i * 0.019)
      // Genuinely zero cover: bare bedrock. Must NOT be mistaken for a missing wire.
      const bare = new Float32Array(N)
      r.fixtures = {
        stateDigest: digest(state), otherDigest: digest(other),
        differ: digest(state) !== digest(other),
        stateVaries: (() => { let lo = Infinity, hi = -Infinity; for (const v of state) { if (v < lo) lo = v; if (v > hi) hi = v } return hi - lo > 0.1 })(),
        bareIsZero: allZero(bare),
      }

      r.selectors = {}
      for (const s of COVER_STATES) {
        const t = selType[s]
        const meta = out.ports[s]
        const nd1 = { id: 1001, type: t, params: {} }
        const c1 = call(t, {}, [state], nd1)
        const ndOther = { id: 1002, type: t, params: {} }
        const c2 = call(t, {}, [other], ndOther)
        const ndBare = { id: 1003, type: t, params: {} }
        const c3 = call(t, {}, [bare], ndBare)
        const ndNone = { id: 1004, type: t, params: {} }
        const c4 = call(t, {}, [null], ndNone)

        const probsBare = problemsFrom(c3.raw, ndBare, c3.thrown)
        const probsNone = problemsFrom(c4.raw, ndNone, c4.thrown)
        r.selectors[s] = {
          type: t,
          identityBytes: sameBytes(c1.field, state),
          identityIsSameObject: c1.field === state,
          identityDigest: digest(c1.field),
          // A selector that ignored its wire and answered from a graph scan, a registry read or a
          // constant would return the same thing for two different inputs.
          followsTheWire: !!(c1.field && c2.field) && digest(c1.field) !== digest(c2.field)
            && sameBytes(c2.field, other),
          // Bare bedrock is legal state, not an error.
          bareBedrockIdentity: sameBytes(c3.field, bare),
          bareBedrockProblems: probsBare.map(p => p.code),
          bareBedrockIsClean: probsBare.length === 0,
          // Disconnected is a NAMED typed error.
          disconnectedProblems: probsNone,
          disconnectedNamed: namesMissingInput(probsNone, meta.portId, meta.portName),
          disconnectedField: digest(c4.field),
          disconnectedIsSilentZeros: probsNone.length === 0 && allZero(c4.field),
          threwOnConnected: !!c1.thrown,
        }
      }

      // ---- d_deposits: prediction fallback, explicitly labelled -------------------------------
      const dd = TYPES.d_deposits || null
      const ddInputs = (dd && dd.inputs) || []
      // The optional explicit `Sediment state` input: any input past slot 0 that is not required
      // and is typed as a metre-scale cover state.
      const stateIn = ddInputs.slice(1).find(p => p && p.required !== true
        && p.unit === 'm' && p.semantic && !GEN[p.semantic]) || null

      const heights = new Float32Array(N)
      for (let i = 0; i < N; i++) {
        const x = i % n, y = (i / n) | 0
        heights[i] = 0.5 + 0.25 * Math.sin(x * 0.31) * Math.cos(y * 0.27) - 0.15 * Math.sin((x + y) * 0.11)
      }
      const refDepth = 25, radius = 1
      const predRef = predictRef(heights, refDepth, hex, n, nh)
      // The state a caller wires in. Deliberately NOT the prediction, so identity and fallback are
      // separable — and `prediction-fixture-degenerate` collapses that separation on purpose.
      let ddState = new Float32Array(N)
      for (let i = 0; i < N; i++) ddState[i] = 2.5 + 1.5 * Math.sin(i * 0.053)
      if (mutation === 'prediction-fixture-degenerate') { ddState = Float32Array.from(predRef); out.mutationApplied = true }

      const ndPred = { id: 2001, type: 'd_deposits', params: { radius, refDepth } }
      const pred = call('d_deposits', { radius, refDepth }, [heights], ndPred)
      const ndIdent = { id: 2002, type: 'd_deposits', params: { radius, refDepth } }
      const ident = call('d_deposits', { radius, refDepth }, [heights, ddState], ndIdent)

      // Derived bound, not a tuned one. Production's only rounding on this path is the single
      // Float32 store of the final product (max/min select existing Float32 values exactly and
      // `closed-inp` is exact in double), so gamma_1 suffices and gamma_2 is headroom.
      const bound = gamma(2)
      let maxRel = 0, worst = -1, compared = 0, zeroMismatch = 0
      if (pred.field && pred.field.length === predRef.length) {
        for (let i = 0; i < predRef.length; i++) {
          const a = pred.field[i], b = predRef[i]
          compared++
          if (b === 0) { if (a !== 0) zeroMismatch++; continue }
          const rel = Math.abs(a - b) / Math.abs(b)
          if (rel > maxRel) { maxRel = rel; worst = i }
        }
      }
      const label = dd ? `${dd.name || ''} ${dd.desc || ''}`.toLowerCase() : ''
      r.deposits = {
        registered: !!dd,
        inputCount: ddInputs.length,
        stateInputId: stateIn ? stateIn.id : null,
        stateInputOptional: !!stateIn,
        stateInputSemantic: stateIn ? stateIn.semantic : null,
        stateInputUnit: stateIn ? stateIn.unit : null,
        // "clearly labelled prediction" — the registry has to say so, in a field the inspector and
        // the search index both read.
        labelledPrediction: dd ? (dd.prediction === true || /prediction/.test(label)) : false,
        // The output of a PREDICTION is derived, not carried state. A prediction declaring
        // lens:'state' is precisely the silent substitution.
        outputNotState: dd ? ((dd.outputs || [])[0] ? (dd.outputs[0].lens !== 'state') : true) : false,
        // Still classified as a derived producer by the doctrine registry — d_deposits must not be
        // promoted into a state producer by this story.
        stillDerivedProducer: !!(typeof DOCTRINE !== 'undefined'
          && (DOCTRINE.DERIVED_PRODUCERS || []).indexOf('d_deposits') >= 0),
        // Which branch ran has to be REPORTED, not inferred. Accepted either on the node or on the
        // typed eval return, and the second channel is not a courtesy: aux-maps.js:88-89 says the
        // side-channel ledger "may only SHRINK", and _verify_aux_registry.js scans
        // `nd._x =` across src/plugins, so a new node stash here would turn THAT gate red. A flag
        // on the typed return costs the ledger nothing.
        predictedFlagWhenUnwired: predictedFlag(ndPred, pred.raw) === true,
        predictedFlagWhenWired: predictedFlag(ndIdent, ident.raw) === false,
        reportsBranch: predictedFlag(ndPred, pred.raw) === true
          && predictedFlag(ndIdent, ident.raw) === false,
        identityBytes: sameBytes(ident.field, ddState),
        identityDigest: digest(ident.field),
        predictionDigest: digest(pred.field),
        stateDigest: digest(ddState),
        // Absence of evidence is failure: if the fixture's state happens to equal the prediction,
        // "identity" proves nothing and the run must refuse.
        fixtureDiscriminates: digest(ddState) !== digest(predRef ? Float32Array.from(predRef) : null),
        predictionLength: pred.field ? pred.field.length : -1,
        compared, zeroMismatch, maxRel, worst, bound,
        predictionMatchesOracle: compared === N && zeroMismatch === 0 && maxRel <= bound,
        predictionIsNotFlat: (() => {
          if (!pred.field) return false
          let lo = Infinity, hi = -Infinity
          for (const v of pred.field) { if (v < lo) lo = v; if (v > hi) hi = v }
          return hi - lo > 1e-6
        })(),
        threw: !!pred.thrown,
      }
      return r
    }

    out.lattices.square = runLattice('square')
    out.lattices.hex = runLattice('hex')
    terrainDef.lattice = 'square'

    // ---- the wire, in a real graph ---------------------------------------------------------------
    // Square only, and stated as such: this phase exercises edge -> ins plumbing, which does not
    // depend on the lattice. Two producers are present in `nodes` the whole time, so a build that
    // resolved its state by scanning the graph would answer the same field before and after the
    // rewire — which is exactly what `implicit-graph-lookup` does.
    out.graph = { ran: false, reason: null }
    const gType = selType.sedimentDepth || selType.soilDepth || selType.sandDepth
    if (!gType) { out.graph.reason = 'no selector type registered' }
    else {
      try {
        nodes = []; edges = []; uid = 9000
        const a = makeNode('constant', 40, 60); a.params.value = 0.3
        const b = makeNode('constant', 40, 200); b.params.value = 0.7
        const sel = makeNode(gType, 260, 60)
        const outNd = makeNode('output', 460, 60)
        edges.push({ from: a.id, to: sel.id, slot: 0 })
        edges.push({ from: sel.id, to: outNd.id, slot: 0 })
        nodes.forEach(x => { x._dirty = true }); evalGraph()
        const wiredA = sel._field ? Float32Array.from(sel._field) : null
        const prodA = a._field ? Float32Array.from(a._field) : null
        const prodB = b._field ? Float32Array.from(b._field) : null

        // Re-wire to the OTHER producer. Nothing else changes.
        const e = edges.find(x => x.to === sel.id)
        if (e) e.from = b.id
        nodes.forEach(x => { x._dirty = true }); evalGraph()
        const wiredB = sel._field ? Float32Array.from(sel._field) : null

        // And now DISCONNECT, leaving both producers sitting in the graph.
        edges.splice(edges.indexOf(e), 1)
        nodes.forEach(x => { x._dirty = true }); evalGraph()
        const disc = sel._field ? Float32Array.from(sel._field) : null
        const meta = out.ports[gType === selType.sedimentDepth ? 'sedimentDepth'
          : (gType === selType.soilDepth ? 'soilDepth' : 'sandDepth')]
        const discProbs = problemsFrom(null, sel, null)

        out.graph = {
          ran: true, reason: null, type: gType,
          producersPresent: nodes.filter(x => x.type === 'constant').length,
          producersDiffer: digest(prodA) !== digest(prodB),
          readsConnectedProducer: sameBytes(wiredA, prodA),
          rewireMovesResult: digest(wiredA) !== digest(wiredB) && sameBytes(wiredB, prodB),
          disconnectedProblems: discProbs,
          disconnectedNamed: namesMissingInput(discProbs, meta && meta.portId, meta && meta.portName),
          disconnectedIsSilentZeros: discProbs.length === 0 && allZero(disc),
          inputErrorText: typeof sel._inputError === 'string' ? sel._inputError : null,
          digests: { a: digest(prodA), b: digest(prodB), wiredA: digest(wiredA), wiredB: digest(wiredB), disc: digest(disc) },
        }
      } catch (e) {
        out.graph = { ran: false, reason: String((e && e.message) || e) }
      }
    }

    // ---- the registry is metadata, not a store of instance values -------------------------------
    // The story's own words. If AUX_MAPS ever grew a per-document value, "read it from the port"
    // would have a hidden competitor.
    const AM = (typeof AUXMAPS !== 'undefined' && AUXMAPS.AUX_MAPS) || {}
    out.registryIsMetadata = COVER_STATES.every(s => {
      const row = AM[s]
      return !!row && row.lens === 'state' && row.unit === 'm'
        && !('value' in row) && !('field' in row) && !('data' in row)
    })
    out.auxRows = COVER_STATES.map(s => (AM[s] ? `${s}:${AM[s].lens}/${AM[s].unit}/${AM[s].status}` : `${s}:absent`))
    return out
  }, mutation)

  // Every control except `prediction-fixture-degenerate` replaces something in the live registry;
  // that one perturbs the fixture production consumes and has no registry readback to assert.
  const REGISTRY_MUTATIONS = new Set(MUTATIONS.filter(m => m !== 'prediction-fixture-degenerate'))

  const L = report.lattices || {}
  const both = fn => ['square', 'hex'].every(k => L[k] && fn(L[k]))
  const states = ['soilDepth', 'sedimentDepth', 'sandDepth']
  const perState = fn => states.every(s => both(l => l.selectors && l.selectors[s] && fn(l.selectors[s], l)))

  const gates = {
    // --- 1. a selector exists at all, and is a TYPED state port -------------------------------
    selectorsRegistered: report.selectorsFound === 3,
    selectorDeclaresRequiredTypedStatePort: states.every(s => {
      const p = report.ports && report.ports[s]
      return !!p && p.registered === true && p.requiredCount === 1 && p.unit === 'm'
        && p.lens === 'state' && p.isGeneric === false && p.semanticIsMetreScalar === true
        && typeof p.portId === 'string' && p.portId.length > 0
    }),
    coverStateVocabularyDeclared: states.every(s => report.ports && report.ports[s]
      && report.ports[s].vocabularyNamesState === true),

    // --- 2. identity: the exact bytes on the connected port ------------------------------------
    selectorReturnsExactBytes: perState(x => x.identityBytes === true && x.threwOnConnected === false),

    // --- 3. disconnected is a NAMED typed error, and bare bedrock is not --------------------------
    // The story's named red is `disconnected-selector-returns-zeros`. These two gates are one claim
    // split in half, and neither half is worth anything alone.
    disconnectedSelectorRaisesTypedMissingInput:
      perState(x => x.disconnectedNamed === true && x.disconnectedIsSilentZeros === false),
    wiredZeroStateIsNotAnError:
      perState(x => x.bareBedrockIdentity === true && x.bareBedrockIsClean === true),

    // --- 4. the wire, not the graph -------------------------------------------------------------
    selectorFollowsTheWireInIsolation: perState(x => x.followsTheWire === true),
    graphSelectorReadsTheConnectedProducer: report.graph && report.graph.ran === true
      && report.graph.producersDiffer === true && report.graph.readsConnectedProducer === true,
    rewiringToAnotherNodeMovesTheResult: report.graph && report.graph.rewireMovesResult === true,
    graphSurfacesTypedMissingInput: report.graph && report.graph.ran === true
      && report.graph.disconnectedNamed === true && report.graph.disconnectedIsSilentZeros === false,

    // --- 5. d_deposits stays a LABELLED prediction with an explicit override ---------------------
    depositsDeclaresOptionalStateInput: both(l => l.deposits.stateInputOptional === true
      && l.deposits.stateInputUnit === 'm'),
    depositsReturnsConnectedStateIdentity: both(l => l.deposits.identityBytes === true),
    depositsIsLabelledAPrediction: both(l => l.deposits.labelledPrediction === true
      && l.deposits.outputNotState === true && l.deposits.stillDerivedProducer === true),
    depositsReportsWhichBranchRan: both(l => l.deposits.reportsBranch === true),
    // The green endpoint of the pair: production's prediction still matches an independently
    // computed Float64 answer within a DERIVED bound, on both lattices.
    depositsPredictionMatchesAnalyticOracle: both(l => l.deposits.predictionMatchesOracle === true
      && l.deposits.threw === false),

    // --- 6. the registry is metadata --------------------------------------------------------------
    registryIsMetadataNotAValueStore: report.registryIsMetadata === true,

    // --- absence of evidence is a failure ---------------------------------------------------------
    evidenceNonEmpty: both(l => l.N > 0 && l.fixtures.differ === true && l.fixtures.stateVaries === true
      && l.fixtures.bareIsZero === true && l.deposits.compared === l.N
      && l.deposits.predictionIsNotFlat === true && l.deposits.fixtureDiscriminates === true)
      && L.hex && L.hex.rowsAreNotRes === true && L.square && L.square.rowsAreNotRes === false
      && report.auxRows.every(r => !/absent$/.test(r)),
    // A control that could not be installed proves nothing. Red rather than free.
    mutationWasApplied: mutation == null || report.mutationApplied === true,
    // ...and one that was "installed" onto a FROZEN object would be a silent no-op that still
    // reported success. Every registry-perturbing control reads the registry back.
    mutationPerturbedProduction: !REGISTRY_MUTATIONS.has(mutation) || report.mutationMoved === true,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  const sq = L.square || {}, hx = L.hex || {}
  const dsq = sq.deposits || {}, dhx = hx.deposits || {}
  console.log(`${ok ? 'PASS' : 'FAIL'}  cover reader selectors=${report.selectorsFound}/3 `
    + `types=[${states.map(s => report.selectorTypes[s] || '-').join(',')}] `
    + `identity=${(sq.selectors && sq.selectors.sedimentDepth || {}).identityBytes} `
    + `missingInput=${(sq.selectors && sq.selectors.sedimentDepth || {}).disconnectedNamed} `
    + `silentZeros=${(sq.selectors && sq.selectors.sedimentDepth || {}).disconnectedIsSilentZeros} `
    + `graph=${report.graph && report.graph.ran}/${report.graph && report.graph.rewireMovesResult} `
    + `depositsState=${dsq.stateInputOptional} depositsLabel=${dsq.labelledPrediction} `
    + `predErr=${(dsq.maxRel != null ? dsq.maxRel.toExponential(2) : 'n/a')}/${(dhx.maxRel != null ? dhx.maxRel.toExponential(2) : 'n/a')} `
    + `bound=${(dsq.bound != null ? dsq.bound.toExponential(2) : 'n/a')} `
    + `rows=${sq.H}/${hx.H} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
