// S3.3 — cover-aware hydraulic consumption/deposition. WRITTEN RED-FIRST, before the kernel exists.
//
// Sprint 3's Ready condition (docs/plan/sprint-03-cover-layer.md:84-85) requires this fixture to be
// OBSERVED RED before the implementation lands. A gate first seen green is a gate that has never
// been seen to fail — this project's standing failure mode, found seven times. So this file must
// fail TODAY, and it must fail by a NAMED GATE printed in the table below, never by throwing. Every
// access to something S3.3 has not built yet is guarded so the run reaches the table.
//
// ---------------------------------------------------------------------------------------------
// THE MEASUREMENT SURFACE THIS ORACLE REQUIRES (nothing here exists on 2026-08-04; measured)
// ---------------------------------------------------------------------------------------------
// A red-first oracle has to name the contract it will go green against, because there is no code to
// read it off. These identifiers come from the documents, not from taste:
//
//   INPUT ports on TYPES.hydraulic.inputs   (sprint-03 S3.3, line 142-144)
//     id 'soilDepth'      scalarRaster, unit 'm'
//     id 'sedimentDepth'  scalarRaster, unit 'm'
//     id 'precipitation'  scalarRaster, unit 'mmPerYr'   (ADR-005 "Precipitation remains mm/yr")
//   OUTPUT ports on TYPES.hydraulic.outputs (ADR-002:120-123 names the atlas members)
//     id 'solidTop'       scalarRaster, unit 'm'
//     id 'soilDepth'      scalarRaster, unit 'm'
//     id 'sedimentDepth'  scalarRaster, unit 'm'
//     id 'sandDepth'      scalarRaster, unit 'm'   — ADR-005:70-71: "the identity never omits the
//                                                    term"; a fixture with no sand must ASSERT zero
//   VOCABULARY  PORTS.UNITS.mmPerYr and PORTS.SEMANTICS.{soilDepth,sedimentDepth,sandDepth,
//               solidTop,precipitation} — measured absent from src/core/ports.js:47-85 today.
//   LEDGER      hydroMassDiag.cover = { coverConsumedM3, bedrockDetachedM3, depositedM3,
//                                       exportedOrSuspendedM3, cellAreaM2, lattice, rows }
//               sprint-03:56-57 "Each process reports consumed cover, bedrock detached, deposited
//               cover, and named boundary/exported/suspended loss" in PHYSICAL VOLUME.
//   DISABLED-STAGE PASS  with both stages off, the node echoes cover unchanged and reports an
//               all-zero cover ledger. That pass is how this oracle obtains the BEFORE state in
//               production's own frame without inventing one.
//
// ---------------------------------------------------------------------------------------------
// WHY THE IDENTITY IS WRITTEN AS CONSERVATION AND NOT AS AN ELEVATION
// ---------------------------------------------------------------------------------------------
// The height frame is an OPEN PRODUCT DECISION. ADR-005:57-64 specifies the autolevel frame
//     heightM = baseElevationM + (legacy - fieldMin)/(fieldMax - fieldMin) * reliefHeightM
// implemented in metricHeightField (src/legacy.js:2357-2375). That frame is FIELD-DEPENDENT: eroding
// the terrain moves fieldMin/fieldMax, so an absolute bedrockHeightM shifts underneath the identity
// between the before and after passes even where no material moved. Baking either frame into this
// gate would be asserting a decision nobody has made.
//
// So the load-bearing gates here are FRAME-FREE. They use only
//   (a) layer THICKNESSES in metres — soilDepth/sedimentDepth/sandDepth are depths, not elevations,
//       and are invariant under any reframing of the height field; and
//   (b) the ledger's physical volumes, which are also thicknesses times area.
// Exactly one gate, `solidVolumeMatchesNetTransport`, compares solidTop ACROSS the two passes and is
// therefore the only frame-sensitive assertion in the file. It is labelled as such at its definition
// and in the report.
//
// COVER-BEFORE-BEDROCK IS ARMED BY THREE FIXTURES, not by one absolute comparison. A single
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
// LATTICE. Cell AREA is square s^2 and hex sqrt(3)/2*s^2, and a hex field is fieldW()*fieldH() with
// fieldH() = round(RES*2/sqrt(3)) rows, NOT RES (src/legacy.js:161-168). Both are asserted against
// values this file computes in double precision from terrainDef.scale/RES, never against whatever
// production reports about itself.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'bedrock-first-kernel',        // the story's named failure: bedrock is cut while loose cover remains
  'sand-nonzero',                // sandDepth stops being zero although no aeolian process ships
  'square-area-on-hex',          // the hex ledger integrates with s^2 instead of sqrt(3)/2*s^2
  'identity-ignores-deposition', // deposited material never reaches the explicit cover layer
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
    const DEEP_M = 500              // cover thickness that a single pass cannot locally exhaust
    const PRECIP_MM_YR = 1200
    const SQRT3_2 = Math.sqrt(3) / 2 // computed here in double, never read back from production

    // Float32 reduction bound, computed rather than inherited (sprint-03:108-111).
    // gamma_n = (n*2^-24)/(1 - n*2^-24); a sum of N Float32 terms carries at most
    // gamma_(N-1)*sum(|term|). Production reduces too, so the two-sided bound uses 2N terms.
    const U = Math.pow(2, -24)
    const gamma = n => (n * U) / (1 - n * U)
    const boundFor = (nTerms, absSum) => 2 * gamma(Math.max(1, 2 * nTerms)) * absSum + 1e-6

    const sumD = f => { let s = 0; for (let i = 0; i < f.length; i++) s += f[i]; return s }
    const absSumD = f => { let s = 0; for (let i = 0; i < f.length; i++) s += Math.abs(f[i]); return s }
    const allZero = f => { for (let i = 0; i < f.length; i++) if (f[i] !== 0) return false; return true }
    const bitEqual = (a, b) => {
      if (!a || !b || a.length !== b.length) return false
      for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false
      return true
    }
    const finiteAll = f => { for (let i = 0; i < f.length; i++) if (!Number.isFinite(f[i])) return false; return true }

    // ---- what production declares TODAY -------------------------------------------------------
    const def = (typeof TYPES !== 'undefined' && TYPES) ? TYPES.hydraulic : null
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
      soilIn: portOk(findIn('soilDepth'), 'm'),
      sedIn: portOk(findIn('sedimentDepth'), 'm'),
      precipIn: portOk(findIn('precipitation'), 'mmPerYr'),
      solidTopOut: portOk(findOut('solidTop'), 'm'),
      soilOut: portOk(findOut('soilDepth'), 'm'),
      sedOut: portOk(findOut('sedimentDepth'), 'm'),
      sandOut: portOk(findOut('sandDepth'), 'm'),
      primaryId,
      slots: { soil: slotOf('soilDepth'), sed: slotOf('sedimentDepth'), precip: slotOf('precipitation') },
    }

    // The port vocabulary itself. S3.3 cannot declare the ports above without these entries, and a
    // port descriptor naming an unregistered unit throws at registration (registry.js:108).
    const V = (typeof PORTS !== 'undefined' && PORTS) ? PORTS : {}
    const UN = V.UNITS || {}, SEM = V.SEMANTICS || {}
    const semOk = (id, unit) => !!SEM[id] && SEM[id].kind === 'scalarRaster' && SEM[id].defaultUnit === unit
    out.vocabulary = {
      mmPerYr: !!UN.mmPerYr,
      soilDepth: semOk('soilDepth', 'm'),
      sedimentDepth: semOk('sedimentDepth', 'm'),
      sandDepth: semOk('sandDepth', 'm'),
      solidTop: semOk('solidTop', 'm'),
      precipitation: semOk('precipitation', 'mmPerYr'),
    }

    // ---- MUTATIONS: every one of them perturbs PRODUCTION ------------------------------------
    // Each control replaces TYPES.hydraulic.eval in the LIVE registry with a wrapper around the real
    // evaluator and perturbs what production HANDS BACK — its output rasters and the ledger object
    // it publishes on hydroMassDiag. None of them writes to a variable this file later reads as its
    // own answer; every measurement below is taken from production's return value after the wrapper
    // has run, exactly as a downstream node would see it. (The house precedent is
    // _verify_flow_control.js's `route-copies-values`, which wraps the registry eval the same way.)
    const realEval = def ? def.eval : null
    out.mutationApplied = { requested: mutation || null, registryMoved: false, outputsMoved: false }
    if (mutation && def && typeof realEval === 'function') {
      def.eval = (p, ins, nd, ctx) => {
        const raw = realEval(p, ins, nd, ctx)
        const vals = (raw && raw.values instanceof Map) ? raw.values : new Map([[primaryId, raw]])
        const led = (typeof hydroMassDiag !== 'undefined' && hydroMassDiag && hydroMassDiag.cover)
          ? hydroMassDiag.cover : null
        const sSoil = slotOf('soilDepth'), sSed = slotOf('sedimentDepth')
        const soilIn = sSoil >= 0 ? ins[sSoil] : null
        const sedIn = sSed >= 0 ? ins[sSed] : null

        if (mutation === 'bedrock-first-kernel') {
          // A kernel that reaches for bedrock first: the loose cover comes back untouched and the
          // volume the pass removed is charged to bedrock instead. This is the shape of the pre-S3
          // build, where hydraulic lowered height with no cover layer to consume at all.
          if (soilIn) vals.set('soilDepth', Float32Array.from(soilIn))
          if (sedIn) vals.set('sedimentDepth', Float32Array.from(sedIn))
          if (led) {
            led.bedrockDetachedM3 = (led.bedrockDetachedM3 || 0) + (led.coverConsumedM3 || 0)
            led.coverConsumedM3 = 0
          }
        }
        if (mutation === 'identity-ignores-deposition') {
          // Deposition happens in the height field but is never credited to the explicit cover
          // layer — the `d_deposits`-as-prediction world S3.3 exists to end. The ledger still
          // claims the deposit, so the cover book no longer closes.
          if (sedIn) vals.set('sedimentDepth', Float32Array.from(sedIn))
        }
        if (mutation === 'sand-nonzero') {
          // An aeolian layer appears although no process in this sprint produces one. The output
          // port is REPLACED rather than written through, because a frozen descriptor would make
          // this a silent no-op under sloppy-mode page.evaluate.
          const n = (ins[0] && ins[0].length) || 0
          const sand = new Float32Array(n); sand.fill(0.25)
          vals.set('sandDepth', sand)
          if (!findOut('sandDepth')) {
            def.outputs = (def.outputs || []).concat([{ id: 'sandDepth', name: 'Sand depth',
              kind: 'scalarRaster', storage: 'R32F', components: 1, semantic: 'sandDepth',
              unit: 'm', lens: 'state' }])
          }
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
        return { values: vals }
      }
      out.mutationApplied.registryMoved = TYPES.hydraulic.eval !== realEval
    }

    // ---- fixtures -----------------------------------------------------------------------------
    // Three cover configurations over one analytic two-layer slope. The bedrock surface is a linear
    // ramp with a deterministic corrugation so the solver has structure to route; the cover is what
    // varies between fixtures.
    const makeBase = (W, H) => {
      const f = new Float32Array(W * H)
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        f[y * W + x] = 0.90 - 0.80 * (x / (W - 1)) + 0.05 * Math.sin(y * 0.40) * Math.cos(x * 0.21)
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

    const beforeParams = { pipeEnabled: false, dropletEnabled: false, feat: 1, engine: null }
    const afterParams = { pipeEnabled: true, dropletEnabled: false, engine: null, feat: 1,
      pipeIters: 48, pipeErode: 0.35, pipeDeposit: 0.28, pipeCapacity: 6, pipeInertia: 0.05,
      radius: 2, seed: 1 }

    const readValues = raw => (raw && raw.values instanceof Map)
      ? raw.values : new Map([[primaryId, raw]])
    const grab = (vals, id) => {
      const v = vals.get(id)
      return (v && typeof v.length === 'number' && v.length > 0) ? v : null
    }
    const grabLedger = () => {
      try {
        if (typeof hydroMassDiag === 'undefined' || !hydroMassDiag || !hydroMassDiag.cover) return null
        return JSON.parse(JSON.stringify(hydroMassDiag.cover))
      } catch (e) { return null }
    }

    const runOne = (lattice, useGpu, fixture) => {
      const r = { key: `${lattice}/${useGpu ? 'gpu' : 'cpu'}/${fixture}`, lattice, gpu: !!useGpu,
        fixture, error: null, ran: false }
      try {
        terrainDef.lattice = lattice
        terrainDef.scale = SCALE_M
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
        r.areaSquareWrong = sIndep * sIndep

        const base = makeBase(W, H)
        const { soil: soil0, sed: sed0 } = makeCover(fixture, W, H)
        r.coverInSum = sumD(soil0) + sumD(sed0)
        r.coverInDigest = (() => { let a = 0x811c9dc5
          for (let i = 0; i < soil0.length; i++) { a = (a ^ (Math.round(soil0[i] * 1e3) | 0)) >>> 0; a = Math.imul(a, 16777619) >>> 0 }
          return a.toString(16) })()
        const precip = new Float32Array(N).fill(PRECIP_MM_YR)

        const sSoil = slotOf('soilDepth'), sSed = slotOf('sedimentDepth'), sPre = slotOf('precipitation')
        r.slotsResolved = sSoil >= 0 && sSed >= 0 && sPre >= 0
        const width = Math.max(2, sSoil + 1, sSed + 1, sPre + 1)
        const ins = new Array(width).fill(null)
        ins[0] = base
        ins[1] = null                                  // Mask
        if (sSoil >= 0) ins[sSoil] = soil0
        if (sSed >= 0) ins[sSed] = sed0
        if (sPre >= 0) ins[sPre] = precip

        const nd = { id: 9001, type: 'hydraulic', params: null }
        const demanded = new Set([primaryId, 'out', 'height', 'solidTop', 'soilDepth', 'sedimentDepth', 'sandDepth'])

        // --- BEFORE: both stages disabled. Contractually an identity pass that echoes cover and
        //     publishes an all-zero cover ledger. It is also how the before-state solidTop is
        //     obtained in production's own frame, without this file inventing one.
        nd.params = { ...beforeParams }
        const rawB = TYPES.hydraulic.eval(nd.params, ins, nd, { demanded })
        const vB = readValues(rawB)
        const ledB = grabLedger()
        const soilB = grab(vB, 'soilDepth'), sedB = grab(vB, 'sedimentDepth')
        const sandB = grab(vB, 'sandDepth'), topB = grab(vB, 'solidTop')
        r.before = {
          hasState: !!(soilB && sedB && sandB && topB),
          echoesSoil: bitEqual(soilB, soil0),
          echoesSed: bitEqual(sedB, sed0),
          sandZero: !!sandB && allZero(sandB),
          lengthsOk: !!(soilB && sedB && sandB && topB)
            && soilB.length === N && sedB.length === N && sandB.length === N && topB.length === N,
          ledgerAllZero: !!ledB && ['coverConsumedM3', 'bedrockDetachedM3', 'depositedM3', 'exportedOrSuspendedM3']
            .every(k => ledB[k] === 0),
          topSum: topB ? sumD(topB) : null,
          topAbsSum: topB ? absSumD(topB) : null,
          topFinite: topB ? finiteAll(topB) : false,
        }

        // --- AFTER: one real transport step.
        nd.params = { ...afterParams }
        const rawA = TYPES.hydraulic.eval(nd.params, ins, nd, { demanded })
        const vA = readValues(rawA)
        const led = grabLedger()
        const soilA = grab(vA, 'soilDepth'), sedA = grab(vA, 'sedimentDepth')
        const sandA = grab(vA, 'sandDepth'), topA = grab(vA, 'solidTop')
        const primA = grab(vA, primaryId)
        r.after = {
          hasState: !!(soilA && sedA && sandA && topA),
          lengthsOk: !!(soilA && sedA && sandA && topA)
            && soilA.length === N && sedA.length === N && sandA.length === N && topA.length === N,
          primaryLength: primA ? primA.length : null,
          sandZero: !!sandA && allZero(sandA),
          sandAbsSum: sandA ? absSumD(sandA) : null,
          finite: !!(soilA && sedA && sandA && topA)
            && finiteAll(soilA) && finiteAll(sedA) && finiteAll(sandA) && finiteAll(topA),
          nonNegative: !!(soilA && sedA && sandA)
            && sumD(soilA) >= 0 && sumD(sedA) >= 0 && sumD(sandA) >= 0,
        }
        r.ledger = led
        r.ran = !!(led && r.after.hasState && r.before.hasState)

        // --- the frame-free readings -----------------------------------------------------------
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
          r.coverAbsTerms = absTerms
          r.minCoverAfter = minCoverAfter
          r.maxSedimentRiseM = maxSedRise
          r.coverBookBound = boundFor(N, absTerms)
          if (led) {
            r.coverBookErr = Math.abs(dCover - ((led.depositedM3 || 0) - (led.coverConsumedM3 || 0)))
            r.coverBookCloses = r.coverBookErr <= r.coverBookBound
          }
        }
        if (led) {
          const lhs = (led.coverConsumedM3 || 0) + (led.bedrockDetachedM3 || 0)
          const rhs = (led.depositedM3 || 0) + (led.exportedOrSuspendedM3 || 0)
          const abs = Math.abs(led.coverConsumedM3 || 0) + Math.abs(led.bedrockDetachedM3 || 0)
            + Math.abs(led.depositedM3 || 0) + Math.abs(led.exportedOrSuspendedM3 || 0)
          r.ledgerErr = Math.abs(lhs - rhs)
          r.ledgerBound = boundFor(N, abs)
          r.ledgerCloses = r.ledgerErr <= r.ledgerBound
          r.areaReportedOk = Math.abs((led.cellAreaM2 || 0) - r.areaExpected) <= 1e-9 * r.areaExpected
          r.ledgerLatticeOk = led.lattice === lattice
          r.ledgerRowsOk = led.rows === r.rowsExpected
        }
        // --- THE ONE FRAME-SENSITIVE READING ---------------------------------------------------
        // Net solid volume change must equal minus what left the domain or stayed suspended:
        //   consumed = deposited + exported  =>  dSolid = deposited - consumed = -exported.
        // This is the only assertion that compares solidTop across two passes, so it is the only
        // one that would move if the height frame is autolevel (ADR-005:57-64). Under an absolute
        // frame it holds as written; under autolevel it must be restated against the recorded
        // fieldMin/fieldMax metadata before it means anything.
        if (topA && topB && led) {
          const A = r.areaExpected
          let dSolid = 0, abs = 0
          for (let i = 0; i < N; i++) { dSolid += A * (topA[i] - topB[i]); abs += A * (Math.abs(topA[i]) + Math.abs(topB[i])) }
          r.dSolidM3 = dSolid
          r.solidBound = boundFor(N, abs)
          r.solidErr = Math.abs(dSolid + (led.exportedOrSuspendedM3 || 0))
          r.solidCloses = r.solidErr <= r.solidBound
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
      plan.push(['square', false, fx])
      if (out.gpuAvailable) plan.push(['square', true, fx])
      plan.push(['hex', false, fx])
    }
    for (const [lat, gpu, fx] of plan) out.runs.push(runOne(lat, gpu, fx))

    // restore
    try {
      if (mutation && def && typeof realEval === 'function') def.eval = realEval
      terrainDef.lattice = 'square'; USE_GPU = false
      RES = RES_FIX; TARGET_RES = RES_FIX
      if (typeof buildIndex === 'function') buildIndex()
    } catch (e) { out.notes.push('restore: ' + String(e && e.message || e)) }

    // Fixture corpus evidence: three fixtures that genuinely differ, non-empty.
    const digests = out.runs.filter(r => r.coverInDigest).map(r => r.fixture + ':' + r.coverInDigest)
    out.fixtureDigests = Array.from(new Set(digests)).sort()
    out.distinctFixtureCovers = new Set(out.runs.filter(r => r.coverInDigest && r.lattice === 'square' && !r.gpu)
      .map(r => r.coverInDigest)).size
    return out
  }, mutation)

  // ---------------------------------------------------------------------------------------------
  // GATES
  // ---------------------------------------------------------------------------------------------
  const runs = report.runs || []
  const byFixture = fx => runs.filter(r => r.fixture === fx)
  const every = (list, fn) => list.length > 0 && list.every(fn)
  const num = v => (typeof v === 'number' && Number.isFinite(v)) ? v : null
  const fmt = v => (num(v) === null ? 'n/a' : (Math.abs(v) >= 1e4 ? v.toExponential(3) : +v.toFixed(6)))

  const deep = byFixture('deep'), bare = byFixture('bare'), mixed = byFixture('mixed')
  const led = r => r.ledger || null
  const ledNum = (r, k) => (r.ledger && typeof r.ledger[k] === 'number') ? r.ledger[k] : null

  const maxCoverBookErr = Math.max(0, ...runs.map(r => num(r.coverBookErr) === null ? 0 : r.coverBookErr))
  const deepBedrock = deep.map(r => ledNum(r, 'bedrockDetachedM3'))
  const bareBedrock = bare.map(r => ledNum(r, 'bedrockDetachedM3'))

  const gates = {
    // --- the declared surface ------------------------------------------------------------------
    coverInputPortsDeclared: report.ports.soilIn === true && report.ports.sedIn === true
      && report.ports.precipIn === true,
    stateOutputPortsDeclared: report.ports.solidTopOut === true && report.ports.soilOut === true
      && report.ports.sedOut === true && report.ports.sandOut === true,
    portVocabularyRegistered: Object.values(report.vocabulary).every(v => v === true),

    // --- the identity pass, which is also how BEFORE is measured --------------------------------
    noTransportPassEchoesCover: every(runs, r => r.before && r.before.hasState === true
      && r.before.echoesSoil === true && r.before.echoesSed === true && r.before.sandZero === true
      && r.before.lengthsOk === true && r.before.ledgerAllZero === true && r.before.topFinite === true),

    // --- COVER BEFORE BEDROCK, armed by three fixtures ------------------------------------------
    // 1) the deep fixture must actually consume cover, or the next gate is about nothing;
    coverIsConsumedOnDeepFixture: every(deep, r => num(ledNum(r, 'coverConsumedM3')) !== null
      && ledNum(r, 'coverConsumedM3') > 0),
    // 2) and cover must never have reached zero anywhere, or "bedrock untouched" is unarmed;
    deepFixtureCoverNeverExhausted: every(deep, r => num(r.minCoverAfter) !== null && r.minCoverAfter > 0),
    // 3) THE STORY'S NAMED RED. Bedrock is not cut while local loose cover remains.
    bedrockUntouchedWhileCoverRemains: every(deep, r => ledNum(r, 'bedrockDetachedM3') === 0),
    // 4) and the kernel must be CAPABLE of cutting bedrock, or (3) passes by refusing to erode.
    bareBedrockDoesErode: every(bare, r => num(ledNum(r, 'bedrockDetachedM3')) !== null
      && ledNum(r, 'bedrockDetachedM3') > 0 && ledNum(r, 'coverConsumedM3') === 0),
    // 5) the mixed slope exercises the boundary between the two regimes in one pass.
    mixedFixtureCutsBothLayers: every(mixed, r => num(ledNum(r, 'coverConsumedM3')) !== null
      && ledNum(r, 'coverConsumedM3') > 0 && num(ledNum(r, 'bedrockDetachedM3')) !== null
      && ledNum(r, 'bedrockDetachedM3') > 0),

    // --- conservation, entirely in frame-free thicknesses and volumes ----------------------------
    coverBookCloses: every(runs, r => r.coverBookCloses === true),
    ledgerMassCloses: every(runs, r => r.ledgerCloses === true),
    // Deposition must land in the EXPLICIT sediment raster, not only in the height field. A build
    // that lowers solid height and predicts deposits morphologically passes every volume sum above
    // and fails here — which is the whole point of making cover state rather than a look-alike.
    depositionReachesTheCoverLayer: every(mixed.concat(deep), r => num(ledNum(r, 'depositedM3')) !== null
      && ledNum(r, 'depositedM3') > 0 && num(r.maxSedimentRiseM) !== null && r.maxSedimentRiseM > 0),

    // --- sand is zero because it is MEASURED zero, not because nothing produces it ---------------
    sandDepthIsZero: every(runs, r => r.after && r.after.sandZero === true && r.before.sandZero === true)
      && report.ports.sandOut === true,

    // --- lattice ---------------------------------------------------------------------------------
    latticeCellAreaCorrect: every(runs, r => r.areaReportedOk === true && r.ledgerLatticeOk === true
      && r.ledgerRowsOk === true
      && num(r.cellSizeProd) !== null && Math.abs(r.cellSizeProd - r.cellSizeIndep) <= 1e-9 * r.cellSizeIndep),
    // A PRECONDITION gate, green today and deliberately unarmed by a mutation: it establishes that
    // the run reached real production geometry on both lattices, so a red elsewhere means the
    // feature is absent rather than that the fixture never executed. Hex rows are round(RES*2/sqrt3)
    // = 74 at RES=64, and a hex field integrated over RES rows would be 14% short.
    hexRowCountIsNotRes: every(runs.filter(r => r.lattice === 'hex'), r => r.H === r.rowsExpected && r.H !== r.W)
      && every(runs.filter(r => r.lattice === 'square'), r => r.H === r.W && r.H === r.rowsExpected),
    bothLatticesMeasured: runs.some(r => r.lattice === 'square' && r.ran === true)
      && runs.some(r => r.lattice === 'hex' && r.ran === true),

    // --- the one frame-sensitive claim (see the header) ------------------------------------------
    solidVolumeMatchesNetTransport: every(runs, r => r.solidCloses === true),

    // --- the shipping square GPU path is separate evidence from the compatibility path -----------
    gpuSquarePathMeasured: report.gpuAvailable === true
      && runs.some(r => r.gpu === true && r.lattice === 'square' && r.ran === true),
    gpuSquarePathCloses: report.gpuAvailable === true
      && every(runs.filter(r => r.gpu === true), r => r.coverBookCloses === true && r.ledgerCloses === true),

    // --- absence of evidence is a failure --------------------------------------------------------
    // 3 cover configurations x 2 lattices = 6 genuinely different authored cover fields, and the
    // three on one lattice differ from each other. An empty or degenerate corpus reads as red.
    fixtureCorpusNonEmptyAndDistinct: runs.length >= 6 && report.distinctFixtureCovers === 3
      && report.fixtureDigests.length === 6
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

  console.log('== S3.3 cover-aware hydraulic transport ==')
  console.log(`ports in=[${report.ports.declaredInputIds.join(',')}] out=[${report.ports.declaredOutputIds.join(',')}] `
    + `soilIn=${report.ports.soilIn} sedIn=${report.ports.sedIn} precipIn=${report.ports.precipIn} `
    + `solidTopOut=${report.ports.solidTopOut} sandOut=${report.ports.sandOut}`)
  console.log('vocabulary ' + JSON.stringify(report.vocabulary))
  for (const r of runs) {
    console.log(`  ${r.key.padEnd(20)} W=${r.W} H=${r.H} area=${fmt(r.areaExpected)} `
      + `ledger=${r.ledger ? JSON.stringify(r.ledger) : 'ABSENT'} `
      + `dCover=${fmt(r.dCoverM3)} coverBookErr=${fmt(r.coverBookErr)} minCover=${fmt(r.minCoverAfter)} `
      + `err=${r.error || 'none'}`)
  }
  for (const [k, v] of Object.entries(gates)) console.log(`${v ? 'PASS' : 'FAIL'}  ${k}`)

  console.log(`${ok ? 'PASS' : 'FAIL'}  cover erosion coverPorts=${report.ports.soilIn && report.ports.sedIn && report.ports.precipIn} `
    + `statePorts=${report.ports.solidTopOut && report.ports.soilOut && report.ports.sedOut && report.ports.sandOut} `
    + `runs=${runs.length} ledgers=${runs.filter(r => r.ledger).length} `
    + `deepBedrockDetached=[${deepBedrock.map(v => v === null ? 'n/a' : fmt(v)).join(',')}] `
    + `bareBedrockDetached=[${bareBedrock.map(v => v === null ? 'n/a' : fmt(v)).join(',')}] `
    + `maxCoverBookErr=${fmt(maxCoverBookErr)} gpu=${report.gpuAvailable} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
