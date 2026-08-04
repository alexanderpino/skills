// S3.5, FIRST NODE — cover-aware THERMAL transport.
//
// WHY THIS IS A NEW FILE AND NOT AN EXTENSION OF _verify_thermal_contract.js
// -------------------------------------------------------------------------
// That oracle is about the relaxation KERNEL's numerics: that Feature Scale derives repose on the
// simulation grid, that the CPU and GPU kernels agree, that omitted off-grid neighbours really are a
// closed boundary, that a long run converges, and that non-finite input is refused. It runs no cover
// fixture and its mutation family is numerical. This one is about the BOOKS — which layer supplies
// the material, where it lands, and whether the published volumes close. Two different corpora, two
// different mutation sets, and `gate.py` reads exactly one MUTATIONS allowlist per file, so folding
// them together would mean either running the numerics fixtures under cover mutations that cannot
// touch them or losing half the controls.
//
// It also leaves the contract oracle standing UNCHANGED as an independent witness: if this story had
// moved the kernel, that file would have gone red on its own terms. It did not.
//
// ---------------------------------------------------------------------------------------------
// WHAT IS ASSERTED, AND WHY IN THIS FORM
// ---------------------------------------------------------------------------------------------
// COVER BEFORE BEDROCK IS ARMED BY THREE FIXTURES, never by one absolute comparison. A single
// "bedrock did not move" claim is satisfied for free by a kernel that never touches bedrock at all,
// so the discriminator is the PAIR:
//   deep  cover 500 m everywhere, never locally exhausted -> bedrockDetachedM3 must be exactly 0
//   bare  cover 0 everywhere                              -> bedrockDetachedM3 must be > 0
//   mixed half deep, half bare                            -> both layers must be active
// A cover-first kernel scores (0, >0, both). A bedrock-first kernel scores (>0, >0, both) and dies
// on `bedrockUntouchedWhileCoverRemains` — the story's named red. A kernel that simply refuses to
// erode bedrock scores (0, 0, ...) and dies on `bareBedrockDoesErode`. Neither can hide behind the
// other, and none of the three readings needs a height frame.
//
// THE BOUNDARY TERM. Thermal's boundary is CLOSED: `thermalErode` (src/legacy.js:2300),
// `thermalErodeHex` (:2277) and `gpuThermal` (src/core/gpu.js:206) all skip off-grid neighbours, and
// every transfer debits one on-grid cell and credits another. So the honest itemisation is a NAMED
// PHYSICAL ZERO, and the conservation closure is
//     coverConsumed + bedrockDetached = deposited + 0
// That closure CANNOT hold for an implementation that deletes the terrain: deleting it makes the
// left side the whole terrain and the right side zero. It is the strongest form available here, and
// it is exactly why the zero must never be replaced by `consumed + detached - deposited`, which
// holds by construction for any implementation at all. `loss-derived-from-field-sums` performs that
// substitution while REPAIRING every other book so they still close, and only the itemisation gate
// sees it — which is the whole reason itemisation is asserted rather than printed.
//
// AND WHERE THE CLAIM IS NOT AVAILABLE, NOTHING IS CLAIMED. A Feature Scale resample adds back an
// upsampled coarse-grid delta and a Mask blends the result toward the input; neither is conservative
// and neither difference is a quantity this node accumulated over anything. On those paths the node
// must publish NO boundary budget at all. `claims-closure-under-mask` is the control for that, and
// it is the reason the plan runs a masked fixture at all.
//
// THE CLOSURE BOUND SCALES WITH THE TRANSPORT, NOT WITH THE TERRAIN. `boundFor` is applied to the
// sum of the LEDGER'S OWN absolute terms — consumed, detached, deposited — which is the volume the
// pass displaced. It is never applied to a sum of elevations, which would make the bound a function
// of how tall the terrain is rather than of how much moved (a defect measured elsewhere in this
// suite at 277x too loose). `closureBoundIsSmallerThanTheTransport` asserts that ratio on every run,
// so the arming is measured continuously rather than argued once.
//
// LATTICE. Cell AREA is square s^2 and hex sqrt(3)/2*s^2, and a hex field is fieldW()*fieldH() with
// fieldH() = round(RES*2/sqrt(3)) rows, NOT RES (src/legacy.js:161-168). Both are computed here in
// double precision from terrainDef.scale/RES, never read back from production.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'bedrock-first-kernel',         // the story's named failure: bedrock is cut while loose cover remains
  'identity-ignores-deposition',  // what slid downslope never reaches the explicit cover layer
  'sand-nonzero',                 // sandDepth stops being zero although no aeolian process ships
  'square-area-on-hex',           // the hex ledger integrates with s^2 instead of sqrt(3)/2*s^2
  'boundary-leak',                // material vanishes while the ledger still claims a closed boundary
  'loss-derived-from-field-sums', // the loss becomes consumed+detached-deposited: closure for free
  'claims-closure-under-mask',    // a boundary budget is published for a field the kernel did not produce
  'cover-alters-published-height',// wiring cover moves the terrain: an unauthorised re-bless
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

;(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1500)

  const report = await page.evaluate(mutation => {
    const out = { mutation: mutation || null, runs: [], notes: [] }

    // ---- fixed experiment constants, chosen once and used by every run ------------------------
    const RES_FIX = 64
    const SCALE_M = 5000            // terrainDef.scale, metres across the world
    const HEIGHT_M = 2600           // terrainDef.height, the relief the stable frame uses
    const DEEP_M = 500              // cover thickness a single pass cannot locally exhaust
    const MASK_VALUE = 0.5          // a genuine partial composite, not a no-op mask
    const SQRT3_2 = Math.sqrt(3) / 2 // computed here in double, never read back from production

    // Float32 reduction bound, computed rather than inherited (sprint-03:108-111).
    // gamma_n = (n*2^-24)/(1 - n*2^-24); a sum of N Float32 terms carries at most
    // gamma_(N-1)*sum(|term|). Production reduces too, so the two-sided bound uses 2N terms.
    const U = Math.pow(2, -24)
    const gamma = n => (n * U) / (1 - n * U)
    const boundFor = (nTerms, absSum) => 2 * gamma(Math.max(1, 2 * nTerms)) * absSum + 1e-6

    const sumD = f => { let s = 0; for (let i = 0; i < f.length; i++) s += f[i]; return s }
    const allZero = f => { for (let i = 0; i < f.length; i++) if (f[i] !== 0) return false; return true }
    const bitEqual = (a, b) => {
      if (!a || !b || a.length !== b.length) return false
      for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false
      return true
    }
    const finiteAll = f => { for (let i = 0; i < f.length; i++) if (!Number.isFinite(f[i])) return false; return true }

    // ---- what production declares -------------------------------------------------------------
    const def = (typeof TYPES !== 'undefined' && TYPES) ? TYPES.thermal : null
    const inPorts = (def && Array.isArray(def.inputs)) ? def.inputs : []
    const outPorts = (def && Array.isArray(def.outputs)) ? def.outputs : []
    const findIn = id => inPorts.find(p => p && p.id === id) || null
    const findOut = id => outPorts.find(p => p && p.id === id) || null
    const slotOf = id => {
      const i = inPorts.findIndex(p => p && p.id === id)
      if (i < 0) return -1
      const p = inPorts[i]
      return (p.legacySlot != null) ? p.legacySlot : i
    }
    const primaryId = (outPorts.find(p => p && p.primary) || outPorts[0] || { id: 'out' }).id
    const portOk = (p, unit) => !!p && p.kind === 'scalarRaster' && p.unit === unit
    out.ports = {
      declaredInputIds: inPorts.map(p => p && p.id).filter(Boolean),
      declaredOutputIds: outPorts.map(p => p && p.id).filter(Boolean),
      insLabels: Array.isArray(def && def.ins) ? def.ins.slice() : [],
      soilIn: portOk(findIn('soilDepth'), 'm'),
      sedIn: portOk(findIn('sedimentDepth'), 'm'),
      // A POSITIVE claim, not an omission. Thermal must NOT declare precipitation: dry mass-wasting
      // has no rain term in either kernel, and a port nothing consumes is exactly the
      // declared-but-never-filled half-gate this sprint has already found three times.
      noPrecipIn: findIn('precipitation') === null,
      solidTopOut: portOk(findOut('solidTop'), 'm'),
      bedrockOut: portOk(findOut('bedrockHeight'), 'm'),
      soilOut: portOk(findOut('soilDepth'), 'm'),
      sedOut: portOk(findOut('sedimentDepth'), 'm'),
      sandOut: portOk(findOut('sandDepth'), 'm'),
      primaryId,
      slots: { soil: slotOf('soilDepth'), sed: slotOf('sedimentDepth') },
    }

    // ---- MUTATIONS: every one of them perturbs PRODUCTION --------------------------------------
    // Each control replaces TYPES.thermal.eval in the LIVE registry with a wrapper around the real
    // evaluator and perturbs what production HANDS BACK — its output rasters and the ledger object
    // it publishes on the typed return. None of them writes to a variable this file later reads as
    // its own answer; every measurement is taken from production's return value after the wrapper
    // has run, exactly as a downstream reader would see it. (House precedent:
    // _verify_cover_erosion.js and _verify_flow_control.js both wrap the registry eval this way.)
    const realEval = def ? def.eval : null
    out.mutationApplied = { requested: mutation || null, registryMoved: false }
    if (mutation && def && typeof realEval === 'function') {
      def.eval = (p, ins, nd, ctx) => {
        const raw = realEval(p, ins, nd, ctx)
        if (!raw || !(raw.values instanceof Map)) return raw     // undemanded call: nothing to perturb
        const vals = raw.values
        const led = raw.ledger || null
        const sSoil = slotOf('soilDepth'), sSed = slotOf('sedimentDepth')
        const soilIn = sSoil >= 0 ? ins[sSoil] : null
        const sedIn = sSed >= 0 ? ins[sSed] : null
        const N = (ins[0] && ins[0].length) || 0

        // Recompute bedrockHeight from the published solidTop and the (possibly perturbed) cover, so
        // a mutation that is NOT about the stack identity does not turn that gate red by accident.
        const restack = () => {
          const top = vals.get('solidTop'), so = vals.get('soilDepth')
          const se = vals.get('sedimentDepth'), sa = vals.get('sandDepth')
          if (!top || !so || !se || !sa) return
          const bed = new Float32Array(top.length)
          for (let i = 0; i < top.length; i++) bed[i] = Math.fround(top[i] - (so[i] + se[i] + sa[i]))
          vals.set('bedrockHeight', bed)
        }

        if (mutation === 'bedrock-first-kernel') {
          // A kernel that reaches for bedrock first: the loose cover comes back untouched and the
          // volume the pass removed is charged to bedrock instead. This is the shape of the pre-S3.5
          // build, where thermal lowered height with no cover layer to consume at all.
          if (soilIn) vals.set('soilDepth', Float32Array.from(soilIn))
          if (sedIn) vals.set('sedimentDepth', Float32Array.from(sedIn))
          if (led) {
            led.bedrockDetachedM3 = (led.bedrockDetachedM3 || 0) + (led.coverConsumedM3 || 0)
            led.coverConsumedM3 = 0
          }
        }
        if (mutation === 'identity-ignores-deposition') {
          // Material slides downslope in the height field but is never credited to the explicit
          // cover layer — the "deposits are predicted from the final surface" world S3.5 ends.
          if (sedIn) vals.set('sedimentDepth', Float32Array.from(sedIn))
        }
        if (mutation === 'sand-nonzero') {
          // An aeolian layer appears although no process in this sprint produces one.
          const sand = new Float32Array(N); sand.fill(0.25)
          vals.set('sandDepth', sand)
        }
        if (mutation === 'cover-alters-published-height' && soilIn) {
          // WIRING COVER MOVES THE TERRAIN. D21 authorises a STATED re-bless for this node, and this
          // is the shape of one taken without saying so: the same graph relaxes differently the
          // moment a soil field is attached, so every downstream digest, thumbnail and saved document
          // changes and nothing announces it. The perturbation is applied only where cover exists,
          // so the UNWIRED evaluation below — the pre-S3.5 call shape, two slots and no state
          // demand — comes back untouched and the two stop matching.
          const h = vals.get(primaryId)
          if (h && h.length === soilIn.length) {
            const m = Float32Array.from(h)
            for (let i = 0; i < m.length; i++) if (soilIn[i] > 0) m[i] = Math.fround(m[i] * 1.000001)
            vals.set(primaryId, m)
          }
        }
        if (mutation === 'boundary-leak' && led) {
          // A kernel that lost 3% of what it moved over the rim while the ledger still asserts the
          // closed-boundary zero. Modelled on the LEDGER because production computes the book from
          // the published field before this wrapper can see it — and a genuinely leaky kernel would
          // hand production exactly this state: the same consumed/detached, less deposited, and the
          // boundary claim still zero. The conservation closure is what must notice.
          led.depositedM3 = (led.depositedM3 || 0) * 0.97
        }
        if (mutation === 'loss-derived-from-field-sums' && led) {
          // THE DEFECT THIS SUITE KEEPS FINDING, in a new place — and staged so that it is visible
          // to exactly ONE gate. A 3% leak is introduced and then papered over: the boundary term
          // stops being the named physical zero and becomes `consumed + detached - deposited`, a
          // subtraction of the very two sums it is then compared against. Every other book is
          // REPAIRED in the same breath — the sediment raster is scaled by the same factor so the
          // cover book still closes, and bedrock is recomputed so the stack identity still closes —
          // which is precisely the point: `ledgerMassCloses` now holds EXACTLY, for any
          // implementation, including one that deletes the terrain. Only
          // `closedBoundaryLossIsNamedZeroNotDerived` can see it.
          const f = 0.97
          const se = vals.get('sedimentDepth')
          if (se && sedIn && se.length === sedIn.length) {
            const m = new Float32Array(se.length)
            for (let i = 0; i < se.length; i++) m[i] = Math.fround(sedIn[i] + (se[i] - sedIn[i]) * f)
            vals.set('sedimentDepth', m)
          } else if (se) {
            const m = new Float32Array(se.length)
            for (let i = 0; i < se.length; i++) m[i] = Math.fround(se[i] * f)
            vals.set('sedimentDepth', m)
          }
          led.depositedM3 = (led.depositedM3 || 0) * f
          led.exportedOrSuspendedM3 = (led.coverConsumedM3 || 0) + (led.bedrockDetachedM3 || 0)
            - led.depositedM3
          restack()
        }
        if (mutation === 'claims-closure-under-mask' && led && ins[1]) {
          // A boundary budget published for a field the kernel did not produce. The mask blended the
          // result toward the input, so the kernel's closed boundary no longer describes what is
          // published — and this asserts the zero anyway.
          delete led.lossClaimed
          led.exportedOrSuspendedM3 = 0
          led.boundaryExportedM3 = 0
          led.suspendedM3 = 0
          led.lossSource = 'closed-boundary-no-flux'
          led.boundaryPolicy = 'closed-no-flux'
        }
        if (mutation === 'square-area-on-hex' && terrainDef.lattice === 'hex' && led) {
          // The hex ledger integrates depth with the SQUARE cell area over a square row count.
          // Every reported volume is then 1/(sqrt(3)/2) = 1.1547x too large, and stops matching the
          // raster integral this file computes with the true hex area over fieldH() rows.
          const s = SCALE_M / RES_FIX, f = 1 / SQRT3_2
          led.cellAreaM2 = s * s
          led.rows = RES_FIX
          for (const k of ['coverConsumedM3', 'bedrockDetachedM3', 'depositedM3', 'exportedOrSuspendedM3']) {
            if (typeof led[k] === 'number') led[k] *= f
          }
        }
        return raw
      }
      out.mutationApplied.registryMoved = TYPES.thermal.eval !== realEval
    }

    // ---- fixtures ------------------------------------------------------------------------------
    // A gently descending slope with a fixed corrugation whose LOCAL slope is above the angle of
    // repose while its AMPLITUDE is small. Both properties are load-bearing and neither is a taste:
    //   above repose  -> the relaxation actually runs, so `coverIsConsumedOnDeepFixture` is about
    //                    something. At RES 64 over 5000 m with 2600 m of relief the 35-degree
    //                    threshold is tan(35)*(5000/64)/2600 = 0.02104 per cell; the corrugation's
    //                    peak slope is AMP*0.9 = 0.045, i.e. 2.1x that.
    //   small amplitude -> the total lowering at any one sample is bounded by roughly 2*AMP in
    //                    normalised units, which is 2*0.05*2600 = 260 m. That is what keeps 500 m of
    //                    cover from being locally exhausted, and `deepFixtureCoverNeverExhausted`
    //                    MEASURES it rather than trusting the arithmetic.
    const AMP = 0.05
    const makeBase = (W, H) => {
      const f = new Float32Array(W * H)
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        f[y * W + x] = 0.55 - 0.30 * (x / (W - 1)) + AMP * Math.sin(x * 0.9) * Math.cos(y * 0.7)
      }
      return f
    }
    const makeCover = (kind, W, H) => {
      const soil = new Float32Array(W * H)
      if (kind === 'deep') soil.fill(DEEP_M)
      else if (kind === 'mixed') {
        for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (x < W / 2) soil[y * W + x] = DEEP_M
      }
      return { soil, sed: new Float32Array(W * H) }   // 'bare' leaves both at zero
    }

    // THE IDENTITY PASS. Thermal has no "stage off" switch, but it does have `rate`, and the node
    // accepts rate 0 (finiteInRange(p.rate,0,1)). Both kernels then compute a move budget of
    // 0.5*rate*maxDrop = 0 and every cell keeps its exact value, so this is a real production
    // evaluation that transports nothing — which is how the BEFORE cover is obtained in production's
    // own frame without this file inventing one.
    const beforeParams = { realScale: 'on', repose: 35, iters: 30, rate: 0, feat: 1 }
    const afterParams = { realScale: 'on', repose: 35, iters: 30, rate: 0.5, feat: 1 }

    const readValues = raw => (raw && raw.values instanceof Map)
      ? raw.values : new Map([[primaryId, raw]])
    const grab = (vals, id) => {
      const v = vals.get(id)
      return (v && typeof v.length === 'number' && v.length > 0) ? v : null
    }
    const grabLedger = raw => {
      try { return (raw && raw.ledger) ? JSON.parse(JSON.stringify(raw.ledger)) : null }
      catch (e) { return null }
    }

    const runOne = (lattice, useGpu, fixture, masked) => {
      const r = { key: `${lattice}/${useGpu ? 'gpu' : 'cpu'}/${fixture}${masked ? '/masked' : ''}`,
        lattice, gpu: !!useGpu, fixture, masked: !!masked, error: null, ran: false }
      try {
        terrainDef.lattice = lattice
        terrainDef.scale = SCALE_M
        terrainDef.height = HEIGHT_M
        RES = RES_FIX; TARGET_RES = RES_FIX
        USE_GPU = !!useGpu
        if (typeof buildIndex === 'function') buildIndex()

        const W = fieldW(), H = fieldH(), N = W * H
        // Independent geometry, in double, from the authored world size — not read back from
        // production. cellSizeM() is then compared against it rather than trusted.
        const sIndep = SCALE_M / RES_FIX
        r.W = W; r.H = H; r.N = N
        r.rowsExpected = lattice === 'hex' ? Math.round(RES_FIX * 2 / Math.sqrt(3)) : RES_FIX
        r.cellSizeIndep = sIndep
        r.cellSizeProd = (typeof cellSizeM === 'function') ? cellSizeM() : null
        r.areaExpected = (lattice === 'hex' ? SQRT3_2 : 1) * sIndep * sIndep
        r.reposeThresholdIndep = Math.tan(35 * Math.PI / 180) * sIndep / HEIGHT_M

        const base = makeBase(W, H)
        const { soil: soil0, sed: sed0 } = makeCover(fixture, W, H)
        const mask = masked ? new Float32Array(N).fill(MASK_VALUE) : null
        r.coverInSum = sumD(soil0) + sumD(sed0)
        r.coverInDigest = (() => { let a = 0x811c9dc5
          for (let i = 0; i < soil0.length; i++) { a = (a ^ (Math.round(soil0[i] * 1e3) | 0)) >>> 0; a = Math.imul(a, 16777619) >>> 0 }
          return a.toString(16) })()

        const sSoil = slotOf('soilDepth'), sSed = slotOf('sedimentDepth')
        r.slotsResolved = sSoil >= 0 && sSed >= 0
        const width = Math.max(2, sSoil + 1, sSed + 1)
        const ins = new Array(width).fill(null)
        ins[0] = base
        ins[1] = mask
        if (sSoil >= 0) ins[sSoil] = soil0
        if (sSed >= 0) ins[sSed] = sed0

        const nd = { id: 9101, type: 'thermal', params: null }
        const demanded = new Set([primaryId, 'out', 'solidTop', 'bedrockHeight',
          'soilDepth', 'sedimentDepth', 'sandDepth'])

        // --- BEFORE: rate 0. Contractually an identity pass that echoes cover and publishes an
        //     all-zero cover ledger.
        nd.params = { ...beforeParams }
        const rawB = TYPES.thermal.eval(nd.params, ins, nd, { demanded })
        const vB = readValues(rawB)
        const ledB = grabLedger(rawB)
        const soilB = grab(vB, 'soilDepth'), sedB = grab(vB, 'sedimentDepth')
        const sandB = grab(vB, 'sandDepth'), topB = grab(vB, 'solidTop')
        const bedB = grab(vB, 'bedrockHeight'), primB = grab(vB, primaryId)
        r.before = {
          hasState: !!(soilB && sedB && sandB && topB),
          echoesSoil: bitEqual(soilB, soil0),
          echoesSed: bitEqual(sedB, sed0),
          heightUnmoved: bitEqual(primB, base),
          sandZero: !!sandB && allZero(sandB),
          lengthsOk: !!(soilB && sedB && sandB && topB)
            && soilB.length === N && sedB.length === N && sandB.length === N && topB.length === N,
          ledgerAllZero: !!ledB && ['coverConsumedM3', 'bedrockDetachedM3', 'depositedM3']
            .every(k => ledB[k] === 0),
          topFinite: topB ? finiteAll(topB) : false,
        }

        // --- AFTER: one real relaxation pass.
        nd.params = { ...afterParams }
        const rawA = TYPES.thermal.eval(nd.params, ins, nd, { demanded })
        const vA = readValues(rawA)
        const led = grabLedger(rawA)
        const soilA = grab(vA, 'soilDepth'), sedA = grab(vA, 'sedimentDepth')
        const sandA = grab(vA, 'sandDepth'), topA = grab(vA, 'solidTop')
        const bedA = grab(vA, 'bedrockHeight'), primA = grab(vA, primaryId)
        r.after = {
          hasState: !!(soilA && sedA && sandA && topA),
          lengthsOk: !!(soilA && sedA && sandA && topA)
            && soilA.length === N && sedA.length === N && sandA.length === N && topA.length === N,
          primaryLength: primA ? primA.length : null,
          sandZero: !!sandA && allZero(sandA),
          finite: !!(soilA && sedA && sandA && topA)
            && finiteAll(soilA) && finiteAll(sedA) && finiteAll(sandA) && finiteAll(topA),
          nonNegative: !!(soilA && sedA && sandA)
            && sumD(soilA) >= 0 && sumD(sedA) >= 0 && sumD(sandA) >= 0,
        }
        r.ledger = led
        r.ran = !!(led && r.after.hasState && r.before.hasState)

        // The relaxation must actually have run, or every ledger reading below is about nothing.
        if (primA && primB) {
          let moved = 0, maxDrop = 0
          for (let i = 0; i < N; i++) {
            const d = primA[i] - primB[i]
            if (Math.abs(d) > 0) moved++
            if (-d > maxDrop) maxDrop = -d
          }
          r.samplesMoved = moved
          r.maxLoweringM = maxDrop * HEIGHT_M
        }

        // --- the byte-identity control ----------------------------------------------------------
        // The SAME pass called the way the pre-S3.5 build was called: two slots, no cover attached,
        // and only the primary demanded. D21 authorises a STATED re-bless for this node, but a graph
        // that wires no cover must produce the terrain it produced yesterday, byte for byte, and
        // that has to be MEASURED rather than argued from the fact that the digest recipe happens
        // not to demand a state port.
        const rawU = TYPES.thermal.eval(nd.params, [ins[0], mask], nd, { demanded: new Set([primaryId]) })
        const primU = grab(readValues(rawU), primaryId)
        r.unwiredLength = primU ? primU.length : null
        r.unwiredMatchesWired = bitEqual(primU, primA)

        // --- the digest-shape control -----------------------------------------------------------
        // With NO ctx at all — which is exactly how _verify_digest.js:199 calls every evaluator —
        // the return must still be a bare typed array, not a values Map. If it became typed, the
        // digest would start folding five extra ports for this node and the baseline would move for
        // a reason that has nothing to do with the physics.
        const rawN = TYPES.thermal.eval(nd.params, ins, nd)
        r.undemandedIsBareField = ArrayBuffer.isView(rawN) && !(rawN && rawN.values instanceof Map)
          && rawN.length === N
        r.undemandedMatchesWired = bitEqual(rawN, primA)

        // --- the solid-stack identity, PER SAMPLE ------------------------------------------------
        //   solidTop = bedrockHeight + soilDepth + sedimentDepth + sandDepth
        // asserted at every sample of BOTH passes, not integrated. The tolerance is derived, not
        // picked: each published raster is Float32, the sum is formed in double, so the largest
        // legitimate residual is a few units in the last place of the biggest term. 2^-23 is one
        // Float32 ulp relative, and 4x that over the sum of magnitudes covers the rounding of the
        // stored difference plus the reduction.
        //
        // ABSENCE OF EVIDENCE IS RED: `samples` must reach 2N, so a missing bedrockHeight raster or
        // a short one fails here rather than silently checking nothing.
        const F32_ULP = Math.pow(2, -23)
        const stack = (top, bed, so, se, sa) => {
          const acc = { samples: 0, violations: 0, maxResidualM: 0 }
          if (!top || !bed || !so || !se || !sa) return acc
          const n = Math.min(top.length, bed.length, so.length, se.length, sa.length)
          if (n !== N) return acc
          for (let i = 0; i < n; i++) {
            const res = top[i] - (bed[i] + so[i] + se[i] + sa[i])
            const mag = Math.abs(top[i]) + Math.abs(bed[i]) + Math.abs(so[i]) + Math.abs(se[i]) + Math.abs(sa[i])
            const tol = 4 * F32_ULP * mag + 1e-6
            acc.samples++
            if (!(Math.abs(res) <= tol)) acc.violations++
            if (Math.abs(res) > acc.maxResidualM) acc.maxResidualM = Math.abs(res)
          }
          return acc
        }
        const sB = stack(topB, bedB, soilB, sedB, sandB), sA = stack(topA, bedA, soilA, sedA, sandA)
        r.stackIdentity = {
          samples: sB.samples + sA.samples, expected: 2 * N,
          violations: sB.violations + sA.violations,
          maxResidualM: Math.max(sB.maxResidualM, sA.maxResidualM),
        }

        // --- WHICH FRAME solidTop is actually in -------------------------------------------------
        // D20: a physical node takes `physical-stable`. That is a claim about production's
        // arithmetic, so it is measured, not read off a label: the BEFORE pass moved no material, so
        // its solidTop must be the base field this file AUTHORED, mapped through the datum and
        // relief production reports. AND THE COMPARISON IS ARMED IN PLACE — the autolevelled
        // alternative is evaluated on the same fixture and required to DISAGREE by three orders of
        // magnitude more than the tolerance. If the two frames happened to coincide here, the
        // agreement would be evidence of nothing.
        if (topB && led && Number.isFinite(led.datumM) && Number.isFinite(led.reliefHeightM)) {
          const dat = led.datumM, rel = led.reliefHeightM
          let mn = Infinity, mx = -Infinity
          for (let i = 0; i < N; i++) { const v = base[i]; if (v < mn) mn = v; if (v > mx) mx = v }
          const span = (mx - mn) || 1
          let maxStable = 0, maxAuto = 0
          for (let i = 0; i < N; i++) {
            const ds = Math.abs(topB[i] - (dat + base[i] * rel))
            const da = Math.abs(topB[i] - (dat + (base[i] - mn) / span * rel))
            if (ds > maxStable) maxStable = ds
            if (da > maxAuto) maxAuto = da
          }
          r.frame = { name: typeof led.frame === 'string' ? led.frame : null, datumM: dat, reliefHeightM: rel,
            maxErrVsStableM: maxStable, maxErrVsAutolevelM: maxAuto,
            tolM: 4 * F32_ULP * (Math.abs(dat) + Math.abs(rel)) + 1e-6 }
        }

        // --- the frame-free readings -------------------------------------------------------------
        if (soilA && sedA && sandA && soilB && sedB && sandB) {
          const A = r.areaExpected
          let dCover = 0, absTerms = 0, minCoverAfter = Infinity, maxSedRise = -Infinity
          for (let i = 0; i < N; i++) {
            const c1 = soilA[i] + sedA[i] + sandA[i]
            const c0 = soilB[i] + sedB[i] + sandB[i]
            dCover += A * (c1 - c0)
            absTerms += A * (Math.abs(c1) + Math.abs(c0))
            if (c1 < minCoverAfter) minCoverAfter = c1
            const rise = sedA[i] - sedB[i]
            if (rise > maxSedRise) maxSedRise = rise
          }
          r.dCoverM3 = dCover
          r.minCoverAfter = minCoverAfter
          r.maxSedimentRiseM = maxSedRise
          r.coverBookBound = boundFor(N, absTerms)
          if (led) {
            r.coverBookErr = Math.abs(dCover - ((led.depositedM3 || 0) - (led.coverConsumedM3 || 0)))
            r.coverBookCloses = r.coverBookErr <= r.coverBookBound
          }
        }

        // --- the conservation closure, and its arming --------------------------------------------
        if (led) {
          const consumed = led.coverConsumedM3 || 0, detached = led.bedrockDetachedM3 || 0
          const deposited = led.depositedM3 || 0, exported = led.exportedOrSuspendedM3 || 0
          // THE BOUND SCALES WITH THE TRANSPORT. Its only input is the sum of the ledger's own
          // absolute terms — the volume this pass displaced — never a sum of elevations. That is
          // what `closureBoundIsSmallerThanTheTransport` then asserts as a ratio.
          const transported = Math.abs(consumed) + Math.abs(detached) + Math.abs(deposited)
          r.transportedM3 = transported
          r.ledgerErr = Math.abs((consumed + detached) - (deposited + exported))
          r.ledgerBound = boundFor(N, transported + Math.abs(exported))
          r.ledgerCloses = r.ledgerErr <= r.ledgerBound
          r.closureArming = transported / r.ledgerBound
          r.areaReportedOk = Math.abs((led.cellAreaM2 || 0) - r.areaExpected) <= 1e-9 * r.areaExpected
          r.ledgerLatticeOk = led.lattice === lattice
          r.ledgerRowsOk = led.rows === r.rowsExpected
          // The boundary itemisation, read exactly as published.
          r.loss = {
            claimed: led.lossClaimed !== false,
            source: typeof led.lossSource === 'string' ? led.lossSource : null,
            policy: typeof led.boundaryPolicy === 'string' ? led.boundaryPolicy : null,
            exported: Object.prototype.hasOwnProperty.call(led, 'exportedOrSuspendedM3')
              ? led.exportedOrSuspendedM3 : null,
            boundaryExported: Object.prototype.hasOwnProperty.call(led, 'boundaryExportedM3')
              ? led.boundaryExportedM3 : null,
            suspended: Object.prototype.hasOwnProperty.call(led, 'suspendedM3')
              ? led.suspendedM3 : null,
          }
          r.slotsReported = led.soilSlot === sSoil && led.sedimentSlot === sSed
            && led.soilWired === true && led.sedimentWired === true
        }
      } catch (e) {
        r.error = String((e && e.message) || e)
      }
      return r
    }

    // GPU availability is measured, not assumed: an unavailable GPU is absence of evidence for the
    // shipping square path and must read as red, not as a silent skip.
    out.gpuAvailable = false
    try { out.gpuAvailable = !!(typeof GPU !== 'undefined' && GPU && GPU.init && GPU.init()) } catch (e) { out.gpuAvailable = false }

    const plan = []
    for (const fx of ['deep', 'bare', 'mixed']) {
      plan.push(['square', false, fx, false])
      if (out.gpuAvailable) plan.push(['square', true, fx, false])
      plan.push(['hex', false, fx, false])
    }
    // The masked path, on the fixture that exercises both layers. This is the run where the node
    // must publish NO boundary budget, and it is the only place `claims-closure-under-mask` bites.
    plan.push(['square', false, 'mixed', true])
    plan.push(['hex', false, 'mixed', true])
    for (const [lat, gpu, fx, masked] of plan) out.runs.push(runOne(lat, gpu, fx, masked))

    // --- a wired cover raster that is not a depth must be REFUSED, not half-read ------------------
    // Zero cover is bare bedrock and is real data (core/cover-state.js), so the only way to tell
    // "you wired rubbish" from "you wired nothing" is to say so. Both a non-finite sample and a
    // negative thickness are refused by name.
    out.rejects = { nonFinite: false, negative: false, cleanStillEvaluates: false }
    try {
      terrainDef.lattice = 'square'; terrainDef.scale = SCALE_M; terrainDef.height = HEIGHT_M
      RES = RES_FIX; TARGET_RES = RES_FIX; USE_GPU = false
      if (typeof buildIndex === 'function') buildIndex()
      const W = fieldW(), H = fieldH(), N = W * H
      const base = makeBase(W, H)
      const nd = { id: 9102, type: 'thermal', params: { ...afterParams } }
      const demanded = new Set(['solidTop', 'soilDepth'])
      const sSoil = slotOf('soilDepth'), sSed = slotOf('sedimentDepth')
      const mk = mutate => {
        const soil = new Float32Array(N).fill(10)
        if (mutate) mutate(soil)
        const ins = new Array(Math.max(2, sSoil + 1, sSed + 1)).fill(null)
        ins[0] = base; ins[1] = null
        if (sSoil >= 0) ins[sSoil] = soil
        if (sSed >= 0) ins[sSed] = new Float32Array(N)
        return ins
      }
      try { TYPES.thermal.eval(nd.params, mk(a => { a[13] = NaN }), nd, { demanded }) }
      catch (e) { out.rejects.nonFinite = /non-negative depth/.test(String(e && e.message)) }
      try { TYPES.thermal.eval(nd.params, mk(a => { a[13] = -1 }), nd, { demanded }) }
      catch (e) { out.rejects.negative = /non-negative depth/.test(String(e && e.message)) }
      // ...and a clean wired cover still evaluates, so the two above are a refusal of BAD DATA and
      // not a node that refuses cover altogether.
      const okRaw = TYPES.thermal.eval(nd.params, mk(null), nd, { demanded })
      out.rejects.cleanStillEvaluates = !!(okRaw && okRaw.values instanceof Map
        && okRaw.values.get('soilDepth') && okRaw.values.get('soilDepth').length === N)
    } catch (e) { out.notes.push('rejects probe: ' + String(e && e.message || e)) }

    // restore
    try {
      if (mutation && def && typeof realEval === 'function') def.eval = realEval
      terrainDef.lattice = 'square'; USE_GPU = false
      RES = RES_FIX; TARGET_RES = RES_FIX
      if (typeof buildIndex === 'function') buildIndex()
    } catch (e) { out.notes.push('restore: ' + String(e && e.message || e)) }

    // Fixture corpus evidence: three cover configurations that genuinely differ, non-empty.
    const digests = out.runs.filter(r => r.coverInDigest).map(r => r.fixture + ':' + r.coverInDigest)
    out.fixtureDigests = Array.from(new Set(digests)).sort()
    out.distinctFixtureCovers = new Set(out.runs.filter(r => r.coverInDigest && r.lattice === 'square' && !r.gpu && !r.masked)
      .map(r => r.coverInDigest)).size
    // PER LATTICE, not across them. The same fixture hashes differently on square and hex because
    // the field has a different row count, so `fixtureDigests` holds 3 fixtures x 2 lattices = 6
    // entries and asserting 3 there was measuring the wrong thing. What the corpus has to prove is
    // that the three cover configurations genuinely differ ON EACH LATTICE — a corpus where they
    // collapsed on hex would leave every hex gate below satisfied by one fixture wearing three names.
    out.distinctFixtures = new Set(out.runs.map(r => r.fixture)).size
    out.perLatticeDistinct = ['square', 'hex'].every(lat =>
      new Set(out.runs.filter(r => r.lattice === lat && !r.masked && r.coverInDigest)
        .map(r => r.coverInDigest)).size === 3)
    return out
  }, mutation)

  // ---------------------------------------------------------------------------------------------
  // GATES
  // ---------------------------------------------------------------------------------------------
  const runs = report.runs || []
  const unmasked = runs.filter(r => !r.masked)
  const masked = runs.filter(r => r.masked)
  const byFixture = fx => unmasked.filter(r => r.fixture === fx)
  const every = (list, fn) => list.length > 0 && list.every(fn)
  const num = v => (typeof v === 'number' && Number.isFinite(v)) ? v : null
  const fmt = v => (num(v) === null ? 'n/a' : (Math.abs(v) >= 1e4 ? v.toExponential(3) : +v.toFixed(6)))

  const deep = byFixture('deep'), bare = byFixture('bare'), mixed = byFixture('mixed')
  const ledNum = (r, k) => (r.ledger && typeof r.ledger[k] === 'number') ? r.ledger[k] : null

  const gates = {
    // --- the declared surface ------------------------------------------------------------------
    coverInputPortsDeclared: report.ports.soilIn === true && report.ports.sedIn === true
      && report.ports.noPrecipIn === true
      && report.ports.insLabels.join('|') === 'In|Mask|Soil depth|Sediment depth',
    stateOutputPortsDeclared: report.ports.solidTopOut === true && report.ports.bedrockOut === true
      && report.ports.soilOut === true && report.ports.sedOut === true && report.ports.sandOut === true,

    // --- the identity pass, which is also how BEFORE is measured ---------------------------------
    noTransportPassEchoesCover: every(runs, r => r.before && r.before.hasState === true
      && r.before.echoesSoil === true && r.before.echoesSed === true && r.before.sandZero === true
      && r.before.heightUnmoved === true && r.before.lengthsOk === true
      && r.before.ledgerAllZero === true && r.before.topFinite === true),

    // --- the relaxation actually ran, or every reading below is about nothing ---------------------
    relaxationTransportedMaterial: every(runs, r => num(r.samplesMoved) !== null && r.samplesMoved > 0
      && num(r.transportedM3) !== null && r.transportedM3 > 0),

    // --- COVER BEFORE BEDROCK, armed by three fixtures --------------------------------------------
    // 1) the deep fixture must actually consume cover, or the next gate is about nothing;
    coverIsConsumedOnDeepFixture: every(deep, r => num(ledNum(r, 'coverConsumedM3')) !== null
      && ledNum(r, 'coverConsumedM3') > 0),
    // 2) and cover must never have reached zero anywhere, or "bedrock untouched" is unarmed. The
    //    measured headroom is printed as maxLoweringM against DEEP_M = 500.
    deepFixtureCoverNeverExhausted: every(deep, r => num(r.minCoverAfter) !== null && r.minCoverAfter > 0),
    // 3) THE STORY'S NAMED RED. Bedrock is not cut while local loose cover remains.
    bedrockUntouchedWhileCoverRemains: every(deep, r => ledNum(r, 'bedrockDetachedM3') === 0),
    // 4) and the kernel must be CAPABLE of cutting bedrock, or (3) passes by refusing to move.
    bareBedrockDoesErode: every(bare, r => num(ledNum(r, 'bedrockDetachedM3')) !== null
      && ledNum(r, 'bedrockDetachedM3') > 0 && ledNum(r, 'coverConsumedM3') === 0),
    // 5) the mixed slope exercises the boundary between the two regimes in one pass.
    mixedFixtureCutsBothLayers: every(mixed, r => num(ledNum(r, 'coverConsumedM3')) !== null
      && ledNum(r, 'coverConsumedM3') > 0 && num(ledNum(r, 'bedrockDetachedM3')) !== null
      && ledNum(r, 'bedrockDetachedM3') > 0),

    // --- conservation, entirely in frame-free thicknesses and volumes ------------------------------
    coverBookCloses: every(runs, r => r.coverBookCloses === true),
    ledgerMassCloses: every(runs, r => r.ledgerCloses === true),
    // THE BOUND IS SMALLER THAN THE TERM IT CONSTRAINS, measured on every run rather than argued
    // once. WHAT IT SCALES WITH: the ledger's own absolute terms, i.e. the volume this pass
    // displaced — never a sum of elevations, which would make the bound a function of how tall the
    // terrain is. The ratio therefore says how large a leak the closure can still see. Its ceiling
    // is arithmetic: boundFor is 2*gamma(2N) relative, which at N ~ 4e3 is 9.8e-4, so the ratio
    // cannot exceed ~1.0e3 however tight the implementation. The gate is set at 100 — the closure
    // sees any loss above 1% of what moved — and the measured value is printed, so a bound that
    // silently loosened toward the transport it constrains is visible rather than merely absent.
    // `boundary-leak` removes 3%, comfortably above both.
    closureBoundIsSmallerThanTheTransport: every(runs, r => num(r.closureArming) !== null
      && r.closureArming > 100),
    // Material that slid downslope must land in the EXPLICIT sediment raster, not only in the height
    // field. A build that lowers solid height and predicts deposits morphologically passes every
    // volume sum above and fails here.
    depositionReachesTheCoverLayer: every(mixed.concat(deep), r => num(ledNum(r, 'depositedM3')) !== null
      && ledNum(r, 'depositedM3') > 0 && num(r.maxSedimentRiseM) !== null && r.maxSedimentRiseM > 0),

    // --- the boundary term ------------------------------------------------------------------------
    // UNTRANSFORMED: a NAMED PHYSICAL ZERO, itemised into its own components, and never a difference
    // of the field sums it is compared against. Armed by loss-derived-from-field-sums, which is the
    // only mutation `ledgerMassCloses` is structurally unable to detect.
    closedBoundaryLossIsNamedZeroNotDerived: every(unmasked, r => !!r.loss && r.loss.claimed === true
      && r.loss.source === 'closed-boundary-no-flux' && r.loss.policy === 'closed-no-flux'
      && r.loss.exported === 0 && r.loss.boundaryExported === 0 && r.loss.suspended === 0),
    // TRANSFORMED: the mask blended the result toward the input, so the kernel's closed boundary no
    // longer describes what is published. The node must claim NOTHING and say which transform
    // removed the claim — not publish a number it cannot support. Armed by claims-closure-under-mask.
    maskedPathPublishesNoBoundaryClaim: every(masked, r => !!r.loss && r.loss.claimed === false
      && r.loss.source === 'mask-composite'
      && r.loss.exported === null && r.loss.boundaryExported === null && r.loss.suspended === null),

    // --- sand is zero because it is MEASURED zero, not because nothing produces it ------------------
    sandDepthIsZero: every(runs, r => r.after && r.after.sandZero === true && r.before.sandZero === true)
      && report.ports.sandOut === true,

    // --- the headline identity, at every sample of both passes rather than under an integral --------
    solidStackIdentityClosesPerSample: report.ports.bedrockOut === true
      && every(runs, r => !!r.stackIdentity && r.stackIdentity.samples === r.stackIdentity.expected
        && r.stackIdentity.expected > 0 && r.stackIdentity.violations === 0),

    // --- the frame, measured and armed in place ----------------------------------------------------
    physicalFrameIsStableNotAutolevel: every(runs, r => !!r.frame && r.frame.name === 'physical-stable'
      && num(r.frame.maxErrVsStableM) !== null && r.frame.maxErrVsStableM <= r.frame.tolM
      && num(r.frame.maxErrVsAutolevelM) !== null && r.frame.maxErrVsAutolevelM > 1e3 * r.frame.tolM),

    // --- cover changes the BOOKS, not the terrain --------------------------------------------------
    // S3.5 implements transport ORDER — loose cover first, bedrock second — and not a differential
    // repose law, which nobody has specified and which would be a fabricated constant. So the
    // published height with cover attached must be the published height without it, bit for bit, and
    // D21's re-bless stays unspent. Armed by cover-alters-published-height.
    coverDoesNotMoveThePublishedHeight: every(runs, r => r.unwiredMatchesWired === true
      && r.unwiredLength === r.N),
    // ...and the no-ctx call shape — the one _verify_digest.js uses — still returns the bare field it
    // always did, so the baseline cannot move for a reason unrelated to the physics.
    undemandedEvaluationStaysUntyped: every(runs, r => r.undemandedIsBareField === true
      && r.undemandedMatchesWired === true),

    // --- lattice -----------------------------------------------------------------------------------
    latticeCellAreaCorrect: every(runs, r => r.areaReportedOk === true && r.ledgerLatticeOk === true
      && r.ledgerRowsOk === true
      && num(r.cellSizeProd) !== null && Math.abs(r.cellSizeProd - r.cellSizeIndep) <= 1e-9 * r.cellSizeIndep),
    // A PRECONDITION gate, green today and deliberately unarmed by a mutation: it establishes that
    // the run reached real production geometry on both lattices, so a red elsewhere means the
    // feature is absent rather than that the fixture never executed.
    hexRowCountIsNotRes: every(runs.filter(r => r.lattice === 'hex'), r => r.H === r.rowsExpected && r.H !== r.W)
      && every(runs.filter(r => r.lattice === 'square'), r => r.H === r.W && r.H === r.rowsExpected),
    bothLatticesMeasured: runs.some(r => r.lattice === 'square' && r.ran === true)
      && runs.some(r => r.lattice === 'hex' && r.ran === true),

    // --- the slots the evaluator actually indexed ---------------------------------------------------
    // "Declared" and "filled" are two separate measured claims. A descriptor pointing at a slot the
    // evaluator never reads would look exactly like a working port.
    coverSlotsAreDeclaredAndFilled: every(runs, r => r.slotsResolved === true && r.slotsReported === true)
      && report.ports.slots.soil === 2 && report.ports.slots.sed === 3,

    // --- a wired cover raster that is not a depth is refused by name ---------------------------------
    badCoverRasterIsRefusedNotHalfRead: report.rejects.nonFinite === true
      && report.rejects.negative === true && report.rejects.cleanStillEvaluates === true,

    // --- the shipping square GPU path is separate evidence from the compatibility path ---------------
    gpuSquarePathMeasured: report.gpuAvailable === true
      && runs.some(r => r.gpu === true && r.lattice === 'square' && r.ran === true),
    gpuSquarePathCloses: report.gpuAvailable === true
      && every(runs.filter(r => r.gpu === true), r => r.coverBookCloses === true && r.ledgerCloses === true),

    // --- absence of evidence is a failure -------------------------------------------------------------
    fixtureCorpusNonEmptyAndDistinct: runs.length >= 8 && report.distinctFixtureCovers === 3
      && report.distinctFixtures === 3 && report.perLatticeDistinct === true
      && runs.every(r => num(r.coverInSum) !== null && r.N > 0),
    noRunThrew: runs.length > 0 && runs.every(r => r.error === null) && errors.length === 0,
    stateRastersFiniteAndNonNegative: every(runs, r => r.after && r.after.finite === true
      && r.after.nonNegative === true && r.after.lengthsOk === true),
  }

  // A mutation that perturbed nothing in the registry is not a control at all.
  if (mutation) gates.mutationReachedProduction = report.mutationApplied.registryMoved === true

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)

  console.log('== S3.5 cover-aware THERMAL transport ==')
  console.log(`ins=[${report.ports.insLabels.join(',')}] in=[${report.ports.declaredInputIds.join(',')}] `
    + `out=[${report.ports.declaredOutputIds.join(',')}] slots=${JSON.stringify(report.ports.slots)}`)
  for (const r of runs) {
    console.log(`  ${r.key.padEnd(24)} W=${r.W} H=${r.H} moved=${r.samplesMoved} maxLoweringM=${fmt(r.maxLoweringM)} `
      + `consumed=${fmt(ledNum(r, 'coverConsumedM3'))} detached=${fmt(ledNum(r, 'bedrockDetachedM3'))} `
      + `deposited=${fmt(ledNum(r, 'depositedM3'))} exported=${r.loss ? fmt(r.loss.exported) : 'n/a'} `
      + `lossClaimed=${r.loss ? r.loss.claimed : 'n/a'} src=${r.loss ? r.loss.source : 'n/a'} `
      + `ledgerErr=${fmt(r.ledgerErr)} bound=${fmt(r.ledgerBound)} arming=${fmt(r.closureArming)} `
      + `minCover=${fmt(r.minCoverAfter)} err=${r.error || 'none'}`)
  }
  for (const [k, v] of Object.entries(gates)) console.log(`${v ? 'PASS' : 'FAIL'}  ${k}`)

  console.log(`${ok ? 'PASS' : 'FAIL'}  thermal co-evolution runs=${runs.length} ledgers=${runs.filter(r => r.ledger).length} `
    + `deepBedrockDetached=[${deep.map(r => fmt(ledNum(r, 'bedrockDetachedM3'))).join(',')}] `
    + `bareBedrockDetached=[${bare.map(r => fmt(ledNum(r, 'bedrockDetachedM3'))).join(',')}] `
    + `maxCoverBookErr=${fmt(Math.max(0, ...runs.map(r => num(r.coverBookErr) === null ? 0 : r.coverBookErr)))} `
    + `maxLedgerErr=${fmt(Math.max(0, ...runs.map(r => num(r.ledgerErr) === null ? 0 : r.ledgerErr)))} `
    + `minClosureArming=${fmt(Math.min(...runs.map(r => num(r.closureArming) === null ? 0 : r.closureArming)))} `
    + `minCoverAfter=${fmt(Math.min(...deep.map(r => num(r.minCoverAfter) === null ? -1 : r.minCoverAfter)))} `
    + `maxLoweringM=${fmt(Math.max(0, ...runs.map(r => num(r.maxLoweringM) === null ? 0 : r.maxLoweringM)))} `
    + `stackViolations=${runs.reduce((a, r) => a + ((r.stackIdentity && r.stackIdentity.violations) || 0), 0)} `
    + `unwiredMatchesWired=${runs.filter(r => r.unwiredMatchesWired === true).length}/${runs.length} `
    + `gpu=${report.gpuAvailable} frame=${(runs.find(r => r.frame) || { frame: {} }).frame.name || 'n/a'} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
