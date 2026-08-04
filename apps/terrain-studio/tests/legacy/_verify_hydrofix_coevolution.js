// S3.5, FIFTH NODE — the cover-aware CONDITIONING CARVE, and the evidence that settles the
// classification dispute src/core/transport-classes.js carried against sprint-03:28 and :189-190.
//
// WHY THIS IS A NEW FILE AND NOT AN EXTENSION OF AN EXISTING HYDROFIX ORACLE
// -------------------------------------------------------------------------
// There is no hydrofix oracle to extend. `hydroFixField` is exercised today only as one step of
// `_verify_canyon_process.js`, which calls the KERNEL directly (never the plugin), asserts a
// pit-count reduction and a bounded MAD against the eroded input, declares no MUTATIONS and runs at
// RES 192 with USE_GPU on. Folding a cover corpus into it would mean running canyon fixtures under
// ledger mutations that cannot touch them, and `gate.py` reads exactly one MUTATIONS allowlist per
// file — so half the controls would be lost. It also leaves that oracle standing UNCHANGED as an
// independent witness: if this story had moved the kernel it would have gone red on its own terms.
// It did not — nothing in src/legacy.js was touched, and the digest is bit-identical.
//
// ---------------------------------------------------------------------------------------------
// THE CLASSIFICATION, SETTLED BY THE KERNEL
// ---------------------------------------------------------------------------------------------
// `hydroFixField` (src/legacy.js:3119-3158) has exactly two write paths into the field it returns,
// and NEITHER CAN RAISE A CELL:
//   :3153        `out[i] -= mask[i]*cut`, the corridor downcut, with mask in [0,1] and
//                cut = relief*(.0003+.0072*downcut)*fix >= 0
//   :3155-3156   `target = out[i]-eps; if(out[r]>target) out[r]=target`, the descent enforcement,
//                which lowers a RECEIVER to just under its donor and never the reverse
// The priority-flood fill at :3120 does raise — measured, it raised 907 of 4096 cells on the square
// fixture and 1041 of 4736 on hex — but it is applied to `filled`, a WORKING COPY used only to
// derive receivers and flow accumulation. Not one of those raises reaches the published field.
//
// SO THE NODE TRANSPORTS NOTHING AND STILL DESTROYS A VOLUME. No cell receives material anywhere, so
// `latticeConditioning` is the correct class and sprint-03:28's placement of HydroFix among the
// transport nodes is wrong. But sprint-03:190 — "report the low-amplitude conditioning delta and its
// removed/exported volume; it may not silently discard carved bedrock" — is right, because what the
// carve cuts through is the cover stack. Before S3.5 the node had no cover ports at all, so a breach
// through five metres of soil charged itself to bedrock and nothing anywhere said so.
//
// `publishedDeltaIsMonotoneNonIncreasing` is what makes all of that a READING rather than a
// transcription of this comment. src/plugins/ero/hydrofix.js does not assume the kernel cannot
// raise: it measures the positive part of the published delta on every sample, and the gate requires
// it to be empty. `publishes-a-rise` is the control, and it stages the rise COHERENTLY — the raster
// moves, the ledger's rise terms follow it — so no other gate can see it.
//
// ---------------------------------------------------------------------------------------------
// COVER BEFORE BEDROCK IS ARMED BY THREE FIXTURES, never by one absolute comparison. A single
// "bedrock did not move" claim is satisfied for free by a kernel that never touches bedrock at all,
// so the discriminator is the TRIPLE:
//   deep  cover thick enough that one pass cannot exhaust it -> bedrockCarvedM3 must be exactly 0
//   bare  cover 0 everywhere                                 -> bedrockCarvedM3 must be > 0
//   mixed half deep, half bare                               -> both layers must be active
// A cover-first kernel scores (0, >0, both). A bedrock-first kernel scores (>0, >0, both) and dies
// on `bedrockUntouchedWhileCoverRemains` — the story's named red. A kernel that simply refuses to
// carve bedrock scores (0, 0, ...) and dies on `bareBedrockIsCarved`.
//
// THE EXPORT BUDGET, AND WHY THIS NODE PUBLISHES NONE
// --------------------------------------------------
// Everything hydrofix removes leaves the world — it deposits nothing, so the carved material is
// discarded outright. That is still not a publishable figure. The only number available is
// `coverConsumedM3 + bedrockCarvedM3`, a restatement of the two terms it would then be checked
// against: `consumed + carved = deposited(0) + exported` would hold EXACTLY for any implementation,
// including one that deletes the terrain. The kernel accumulates nothing — neither :3153's
// subtraction nor :3155-3156's enforcement keeps a running total — and the node cannot reconstruct
// one from the field it publishes. So it publishes NO export budget and says why, on every path.
// `claims-derived-export-closure` performs exactly that forbidden substitution and
// `exportBudgetIsNeverClaimedAndNamesWhy` is what sees it.
//
// THE MECHANISM SPLIT IS REFUSED FOR THE SAME REASON, AND THE REFUSAL IS SIZED. The conditioning
// delta is the sum of two physically different operations — a soft corridor downcut spread over a
// blurred channel band, and a one-cell breach enforcing descent — and separating them needs two
// accumulators inside the kernel. `breachDominatesTheCorridorDowncut` MEASURES that they are not
// interchangeable: the maximum lowering runs 30x to 270x the corridor downcut's own per-cell ceiling
// across this fixture set, so a split reporting the downcut as the whole story would be wrong by
// that factor. `claims-mechanism-split` fabricates one and
// `mechanismSplitIsNeverClaimedAndNamesWhy` sees it.
//
// THE ONE BUDGET LINE THAT IS ITEMISABLE IS THE CORRIDOR DOWNCUT CEILING, and it is the strongest
// reading here because it is computed from the node's INPUTS and never from its output:
//     cut = max(max(inp)-min(inp), 1e-5) * (.0003 + .0072*downcut) * fix        (src/legacy.js:3152)
// is the largest lowering the downcut term alone can inflict on any one cell, and this file
// recomputes it in double from its own fixture and its own parameters. THE `fix` FACTOR IS THE
// LOAD-BEARING PART: it multiplies the whole expression, so at the shipped default of .52 an
// implementation that dropped it overstates the ceiling by 1/.52 = 1.92x. `softCutArming` measures
// that distance against the tolerance on every run rather than arguing it once, and
// `softcut-ceiling-ignores-fix` is the control.
//
// AND WHERE A CLAIM IS NOT AVAILABLE, NOTHING IS CLAIMED. Under a Mask the published field is a blend
// toward the input, so the downcut that reached it is an unrecorded fraction of the kernel's
// ceiling. On that path the node must publish NO ceiling. `claims-softcut-ceiling-under-mask` is the
// control, and it is why the plan runs a masked fixture at all. The masked path keeps three live
// claims — the cover partition, the monotonicity reading and the constant-zero deposit — so dropping
// the ceiling does not leave it ungated.
//
// fix = 0 IS AN EXACT BYPASS AND IS GATED AS ONE. The kernel returns `inp.slice()` at :3139 before
// computing anything, so the identity pass this file measures BEFORE with is a real production
// evaluation of the shipped node rather than a fixture this file invented. `bypass-not-exact` is the
// control, and `fixZeroIsAnExactBypass` reads the height, the ledger and the ceiling together.
//
// THE CLOSURE BOUNDS SCALE WITH WHAT MOVED, NOT WITH THE FIXTURE. This is the sprint's standing
// failure mode — three separate bounds were found scaling with a STANDING quantity, one of them 1e9x
// too loose — so both endpoints are MEASURED on every run rather than argued once:
//   boundF32 over the sum of STANDING thicknesses   `coverBookArmingLoose`  must FAIL the threshold
//   boundF64 over the absolute per-cell CHANGE      `coverBookArming`       must PASS it
// `theLooseCoverBookBoundIsDemonstrablyTooLoose` asserts the first and
// `coverBookBoundIsSmallerThanTheCarve` the second, on the same fixture in the same run. Double is
// the honest unit because production accumulates the book from THE PUBLISHED FLOAT32 RASTER VALUES
// and so does this file, so the float32 rounding is common to both sides and cancels term by term.
// The stack identity's own tolerance is sized the same way: `stackToleranceCannotHideALayer`
// measures the thinnest standing cover this fixture carries against the largest tolerance the
// per-sample check allows, so "the identity closed" cannot mean "the tolerance swallowed a layer".
//
// THERE IS NO GPU PATH. src/plugins/ero/hydrofix.js imports nothing from core/gpu.js and
// `hydroFixField` is CPU-only, so a "GPU path" plan entry would measure the CPU kernel twice while
// reading as coverage. Instead `kernelIsGpuFreeOnBothPaths` MEASURES the claim: the same evaluation
// under USE_GPU true and false must be bit-identical. That gate fails the day someone adds a GPU
// hydrofix kernel without bringing a ledger with it.
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
  'bedrock-first-kernel',            // the story's named failure: bedrock cut while loose cover remains
  'publishes-a-rise',                // the conditioning carve starts raising cells: it stops being conditioning
  'invents-deposition',              // cover thickness rises, which a node with no additive term cannot do
  'ledger-consumption-inflated',     // the ledger stops being the integral of the rasters it publishes
  'sand-nonzero',                    // sandDepth stops being zero although no aeolian process ships
  'square-area-on-hex',              // the hex ledger integrates with s^2 instead of sqrt(3)/2*s^2
  'claims-derived-export-closure',   // the export budget becomes consumed+carved: closure for free
  'claims-mechanism-split',          // a fabricated downcut/breach split the kernel never accumulated
  'softcut-ceiling-ignores-fix',     // the corridor ceiling drops the `fix` factor at src/legacy.js:3152
  'claims-softcut-ceiling-under-mask', // a kernel ceiling published for a field the kernel did not produce
  'cover-alters-published-height',   // wiring cover moves the terrain: an unauthorised re-bless
  'bypass-not-exact',                // fix = 0 stops being the exact identity src/legacy.js:3139 promises
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
    const DATUM_M = 120             // terrainDef.baseElevation — deliberately NOT zero, so the frame
                                    // gate below tests datum handling instead of multiplying by it
    const MASK_VALUE = 0.5          // a genuine partial composite, not a no-op mask
    const SQRT3_2 = Math.sqrt(3) / 2 // computed here in double, never read back from production

    // Reduction bounds, computed rather than inherited (sprint-03:108-111).
    // gamma_n = (n*u)/(1 - n*u); a sum of N terms each carrying unit roundoff u accumulates at most
    // gamma_(N-1)*sum(|term|). Production reduces too, so the two-sided bound uses 2N terms.
    // TWO UNITS, and which one applies is a property of the arithmetic being bounded:
    //   boundF32  the quantity passes through a Float32 raster on at least one side
    //   boundF64  both sides are double reductions over the same float32 samples
    const U32 = Math.pow(2, -24), U64 = Math.pow(2, -53)
    const gammaOf = (u, n) => (n * u) / (1 - n * u)
    const boundF32 = (nTerms, absSum) => 2 * gammaOf(U32, Math.max(1, 2 * nTerms)) * absSum + 1e-6
    const boundF64 = (nTerms, absSum) => 2 * gammaOf(U64, Math.max(1, 2 * nTerms)) * absSum + 1e-9

    const sumD = f => { let s = 0; for (let i = 0; i < f.length; i++) s += f[i]; return s }
    const allZero = f => { for (let i = 0; i < f.length; i++) if (f[i] !== 0) return false; return true }
    const bitEqual = (a, b) => {
      if (!a || !b || a.length !== b.length) return false
      for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false
      return true
    }
    const finiteAll = f => { for (let i = 0; i < f.length; i++) if (!Number.isFinite(f[i])) return false; return true }

    // ---- what production declares -------------------------------------------------------------
    const def = (typeof TYPES !== 'undefined' && TYPES) ? TYPES.hydrofix : null
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
      // A POSITIVE claim, not an omission. HydroFix must NOT declare precipitation: there is no rain
      // term anywhere in `hydroFixField` — the kernel's only forcings are the two sliders — and a
      // port nothing consumes is exactly the declared-but-never-filled half-gate this sprint has
      // already found repeatedly.
      noPrecipIn: findIn('precipitation') === null,
      // ...and it must NOT declare an Uplift input, which is Stream Power's and would be a slot this
      // evaluator never reads.
      noUpliftIn: findIn('uplift') === null,
      // ...nor the `sediment` TRANSPORT port hydraulic publishes: that port means "what this pass
      // deposited", and this node deposits nothing.
      noTransportSedimentOut: findOut('sediment') === null,
      solidTopOut: portOk(findOut('solidTop'), 'm'),
      bedrockOut: portOk(findOut('bedrockHeight'), 'm'),
      soilOut: portOk(findOut('soilDepth'), 'm'),
      sedOut: portOk(findOut('sedimentDepth'), 'm'),
      sandOut: portOk(findOut('sandDepth'), 'm'),
      primaryId,
      slots: { mask: slotOf('mask'), soil: slotOf('soilDepth'), sed: slotOf('sedimentDepth') },
    }

    // ---- MUTATIONS: every one of them perturbs PRODUCTION --------------------------------------
    // Each control replaces TYPES.hydrofix.eval in the LIVE registry with a wrapper around the real
    // evaluator and perturbs what production HANDS BACK — its output rasters and the ledger object
    // it publishes on the typed return. None of them writes to a variable this file later reads as
    // its own answer; every measurement is taken from production's return value after the wrapper
    // has run, exactly as a downstream reader would see it. (House precedent:
    // _verify_streampower_coevolution.js and _verify_cover_erosion.js both wrap the registry eval.)
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
        const relief = (led && Number.isFinite(led.reliefHeightM)) ? led.reliefHeightM : 1
        const area = (led && Number.isFinite(led.cellAreaM2)) ? led.cellAreaM2 : 1
        const carving = p && p.fix > 0

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
          // volume the carve removed is charged to bedrock instead. This is the shape of the
          // pre-S3.5 build, where hydrofix lowered height with no cover layer to consume at all. The
          // cover rasters and the cover book stay mutually consistent, so ONLY the cover-first family
          // sees it — which is the point of arming that family with three fixtures.
          if (soilIn) vals.set('soilDepth', Float32Array.from(soilIn))
          if (sedIn) vals.set('sedimentDepth', Float32Array.from(sedIn))
          if (led) {
            led.bedrockCarvedM3 = (led.bedrockCarvedM3 || 0) + (led.coverConsumedM3 || 0)
            led.coverConsumedM3 = 0
          }
          restack()
        }
        if (mutation === 'publishes-a-rise' && carving) {
          // THE CLASSIFICATION CONTROL. The published field starts rising — the node stops being the
          // monotone non-increasing carve `hydroFixField` is (src/legacy.js:3153, :3155-3156) and
          // quietly becomes something that puts material back. Staged COHERENTLY: the primary raster
          // rises, solidTop follows it, the ledger's three rise terms follow the raster and bedrock
          // is restacked, so every volume book still closes and the cover partition is untouched.
          // Only `publishedDeltaIsMonotoneNonIncreasing` can see it.
          const h = vals.get(primaryId), before = ins[0], top = vals.get('solidTop')
          if (h && before && h.length === N) {
            const m = Float32Array.from(h)
            let rise = 0, cells = 0, mx = -Infinity
            for (let i = 0; i < N; i++) {
              if (i % 7 === 0) m[i] = Math.fround(before[i] + 0.001)
              const d = (m[i] - before[i]) * relief
              if (d > 0) { rise += d; cells++ }
              if (d > mx) mx = d
            }
            vals.set(primaryId, m)
            if (top && top.length === N) {
              const t2 = new Float32Array(N)
              const dat = Number.isFinite(led && led.datumM) ? led.datumM : 0
              for (let i = 0; i < N; i++) t2[i] = Math.fround(dat + m[i] * relief)
              vals.set('solidTop', t2)
            }
            if (led) {
              led.publishedRiseM3 = rise * area; led.risenCells = cells; led.maxPublishedRiseM = mx
            }
            restack()
          }
        }
        if (mutation === 'invents-deposition' && carving) {
          // The node starts DEPOSITING: cover thickness rises where the surface fell, i.e. it stops
          // being a pure carve and quietly becomes a transporter. `hydroFixField` has no additive
          // term on any path, so this is invented physics. Staged coherently against the ledger's own
          // deposit line so the cover book still closes and only the no-deposition gate breaks.
          const se = vals.get('sedimentDepth')
          if (se && se.length === N) {
            const m = Float32Array.from(se)
            let dep = 0
            for (let i = 0; i < N; i++) { m[i] = Math.fround(se[i] + 0.5); dep += m[i] - se[i] }
            vals.set('sedimentDepth', m)
            if (led) { led.depositedM3 = dep * area; led.depositionModelled = true }
            restack()
          }
        }
        if (mutation === 'ledger-consumption-inflated') {
          // The ledger stops being the integral of the rasters this node publishes: 3% more cover is
          // claimed as consumed than the soil/sediment fields actually lost. Only the cover book can
          // see it — the cover-first family reads signs and zeros, not magnitudes.
          if (led && typeof led.coverConsumedM3 === 'number') led.coverConsumedM3 *= 1.03
        }
        if (mutation === 'sand-nonzero') {
          // An aeolian layer appears although no process in this sprint produces one.
          const sand = new Float32Array(N); sand.fill(0.25)
          vals.set('sandDepth', sand)
        }
        if (mutation === 'cover-alters-published-height' && soilIn && carving) {
          // WIRING COVER MOVES THE TERRAIN. D21 authorises a STATED re-bless for this node, and this
          // is the shape of one taken without saying so: the same graph conditions differently the
          // moment a soil field is attached, so every downstream digest, thumbnail and saved document
          // changes and nothing announces it. The perturbation is applied only where cover exists, so
          // the UNWIRED evaluation below — the pre-S3.5 call shape, two slots and no state demand —
          // comes back untouched and the two stop matching.
          const h = vals.get(primaryId)
          if (h && h.length === soilIn.length) {
            const m = Float32Array.from(h)
            for (let i = 0; i < m.length; i++) if (soilIn[i] > 0) m[i] = Math.fround(m[i] * 0.999999)
            vals.set(primaryId, m)
          }
        }
        if (mutation === 'bypass-not-exact' && p && !(p.fix > 0)) {
          // fix = 0 stops being the exact identity src/legacy.js:3139 promises. The BEFORE pass this
          // file measures cover with is that bypass, so an inexact one would mean the "before"
          // baseline was itself a carve — and every consumed/carved figure below would be measured
          // against a moved datum without anything saying so.
          const h = vals.get(primaryId)
          if (h && h.length === N) {
            const m = Float32Array.from(h)
            m[Math.floor(N / 3)] = Math.fround(m[Math.floor(N / 3)] - 1e-4)
            vals.set(primaryId, m)
          }
        }
        if (mutation === 'claims-derived-export-closure' && led) {
          // THE DEFECT THIS SUITE KEEPS FINDING, in the one place this node could plausibly hide it.
          // An export budget appears — and its value is `coverConsumed + bedrockCarved`, a
          // restatement of the two terms it would then be checked against. `consumed + carved =
          // deposited(0) + exported` now holds EXACTLY, for any implementation, including one that
          // deletes the terrain. Nothing about the rasters changes, so only the itemisation gate can
          // see it, which is precisely why the refusal is asserted rather than merely printed.
          delete led.lossClaimed
          led.exportedM3 = (led.coverConsumedM3 || 0) + (led.bedrockCarvedM3 || 0)
          led.boundaryExportedM3 = led.exportedM3
          led.suspendedM3 = 0
          led.lossSource = 'carved-volume-is-exported'
          led.boundaryPolicy = 'open-domain'
        }
        if (mutation === 'claims-mechanism-split' && led) {
          // A fabricated split of the conditioning delta into its two mechanisms. The kernel
          // accumulates neither, so the only way to produce these numbers is to invent a ratio — and
          // the two halves then sum to the total by construction, which is the same free closure in
          // a second costume.
          delete led.mechanismSplitClaimed
          const total = (led.coverConsumedM3 || 0) + (led.bedrockCarvedM3 || 0)
          led.softCutRemovedM3 = total * 0.5
          led.breachRemovedM3 = total * 0.5
          led.mechanismSplitSource = 'downcut-and-breach-itemised'
        }
        if (mutation === 'softcut-ceiling-ignores-fix' && led
            && typeof led.softCutCeilingM === 'number' && led.softCutFix > 0) {
          // The corridor ceiling drops the `fix` factor that multiplies the whole expression at
          // src/legacy.js:3152. At the shipped default of .52 that overstates it by 1.92x.
          led.softCutCeilingM /= led.softCutFix
        }
        if (mutation === 'claims-softcut-ceiling-under-mask' && led && ins[slotOf('mask')]) {
          // A kernel ceiling published for a field the kernel did not produce. The mask blended the
          // result toward the input, so the kernel's downcut ceiling no longer describes what is
          // published — and this asserts it anyway.
          delete led.softCutClaimed
          led.softCutCeilingM = (led.maxLoweringM || 0)
          led.softCutFix = 1; led.softCutDowncut = 1; led.softCutReliefNorm = 1; led.bypass = false
          led.softCutSource = 'kernel-corridor-downcut-ceiling'
        }
        if (mutation === 'square-area-on-hex' && terrainDef.lattice === 'hex' && led) {
          // The hex ledger integrates depth with the SQUARE cell area over a square row count.
          // Every reported volume is then 1/(sqrt(3)/2) = 1.1547x too large, and stops matching the
          // raster integral this file computes with the true hex area over fieldH() rows.
          const s = SCALE_M / RES_FIX, f = 1 / SQRT3_2
          led.cellAreaM2 = s * s
          led.rows = RES_FIX
          for (const k of ['coverConsumedM3', 'bedrockCarvedM3', 'publishedRiseM3']) {
            if (typeof led[k] === 'number') led[k] *= f
          }
        }
        return raw
      }
      out.mutationApplied.registryMoved = TYPES.hydrofix.eval !== realEval
    }

    // ---- fixtures ------------------------------------------------------------------------------
    // A ramp that descends in +x, corrugated in y, with a REAL CLOSED DEPRESSION punched into it.
    // All three properties are load-bearing and none is a taste:
    //   descending in x  -> a trunk drainage direction exists, so the priority-flood routing at
    //                       src/legacy.js:3120-3132 produces a connected receiver tree and the flow
    //                       accumulation A spans several orders — without which the channel mask
    //                       `A > threshold` (:3142) would be empty and the corridor downcut would
    //                       never fire at all.
    //   corrugated in y  -> flow concentrates along the grooves, so A varies and the downcut is
    //                       differential rather than a uniform sheet.
    //   a closed pit     -> the DESCENT ENFORCEMENT at :3155-3156 only does work where a receiver
    //                       sits above its donor, which on a strictly monotone surface never
    //                       happens. Without a pit the second of the node's two mechanisms would be
    //                       dormant and `breachDominatesTheCorridorDowncut` would be measuring one
    //                       mechanism against itself. `pitCells` below is asserted non-zero.
    const AMP = 0.05
    const makeBase = (W, H) => {
      const f = new Float32Array(W * H)
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        f[y * W + x] = 0.55 - 0.30 * (x / (W - 1)) + AMP * Math.sin(y * 0.9)
          + 0.08 * Math.sin(x * 0.31) * Math.cos(y * 0.27)
      }
      // Two closed depressions, off-centre and of different depths, so the breach cascade has more
      // than one basin to open and the enforcement is not a single-cell special case.
      for (const [cx, cy, rr, depth] of [[0.55, 0.50, 60, 0.18], [0.28, 0.72, 26, 0.11]]) {
        for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
          const dx = x - W * cx, dy = y - H * cy
          if (dx * dx + dy * dy < rr) f[y * W + x] -= depth
        }
      }
      return f
    }
    // COVER DEPTH IS DERIVED FROM THE FIXTURE, not guessed. The deepest a cell can be carved is
    // bounded by the field's own relief plus the enforcement's cumulative epsilon
    // (eps = relief/(max(n,2)*160) per link, src/legacy.js:3154), so 3x the relief in metres is a
    // bound with large headroom over both terms. The reasoning is NOT trusted:
    // `deepFixtureCoverNeverExhausted` MEASURES minCoverAfter > 0 and prints maxLoweringM against it.
    const deepFor = base => {
      let mn = Infinity, mx = -Infinity
      for (let i = 0; i < base.length; i++) { if (base[i] < mn) mn = base[i]; if (base[i] > mx) mx = base[i] }
      return Math.ceil((mx - mn) * HEIGHT_M * 3)
    }
    const makeCover = (kind, W, H, deepM) => {
      const soil = new Float32Array(W * H)
      if (kind === 'deep') soil.fill(deepM)
      else if (kind === 'mixed') {
        for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (x < W / 2) soil[y * W + x] = deepM
      }
      return { soil, sed: new Float32Array(W * H) }   // 'bare' leaves both at zero
    }

    // THE IDENTITY PASS IS THE NODE'S OWN EXACT BYPASS. `hydroFixField` returns `inp.slice()` the
    // moment fix <= 0 (src/legacy.js:3139), before it computes a mask, a threshold or a receiver —
    // so this is a real production evaluation of the shipped node that conditions nothing, which is
    // how the BEFORE cover is obtained in production's own frame without this file inventing one.
    // `heightUnmoved` is what proves it rather than asserts it.
    const beforeParams = { fix: 0, downcut: 0.34 }
    // TWO CARVING REGIMES, both legal slider settings and neither invented.
    //   defaults  the node exactly as it reaches an author: fix .52, downcut .34.
    //   full      both sliders at 1 — the widest corridor and the deepest downcut the node allows,
    //             which roughly doubles the cells the carve touches and is where the corridor term
    //             is largest relative to the breach. Running both is what keeps
    //             `breachDominatesTheCorridorDowncut` from being a statement about one ratio.
    const REGIMES = {
      defaults: { fix: 0.52, downcut: 0.34 },
      full: { fix: 1, downcut: 1 },
    }

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

    const runOne = (lattice, fixture, masked, regime) => {
      const after = REGIMES[regime] || REGIMES.defaults
      const r = { key: `${lattice}/${fixture}${masked ? '/masked' : ''}${regime === 'full' ? '/full' : ''}`,
        lattice, fixture, masked: !!masked, regime: regime || 'defaults', error: null, ran: false }
      try {
        terrainDef.lattice = lattice
        terrainDef.scale = SCALE_M
        terrainDef.height = HEIGHT_M
        terrainDef.baseElevation = DATUM_M
        RES = RES_FIX; TARGET_RES = RES_FIX
        USE_GPU = false
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

        const base = makeBase(W, H)
        const deepM = deepFor(base)
        r.deepM = deepM
        // The fixture genuinely contains closed depressions, so the descent-enforcement mechanism has
        // work to do. Counted on the 4-neighbourhood, which is a subset of every lattice's ring, so
        // the count is a floor on both.
        let pits = 0
        for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
          const i = y * W + x, v = base[i]
          if (base[i - 1] >= v && base[i + 1] >= v && base[i - W] >= v && base[i + W] >= v) pits++
        }
        r.pitCells = pits

        const { soil: soil0, sed: sed0 } = makeCover(fixture, W, H, deepM)
        const mask = masked ? new Float32Array(N).fill(MASK_VALUE) : null
        r.coverInSum = sumD(soil0) + sumD(sed0)
        r.coverInDigest = (() => { let a = 0x811c9dc5
          for (let i = 0; i < soil0.length; i++) { a = (a ^ (Math.round(soil0[i] * 1e3) | 0)) >>> 0; a = Math.imul(a, 16777619) >>> 0 }
          return a.toString(16) })()

        const sMask = slotOf('mask'), sSoil = slotOf('soilDepth'), sSed = slotOf('sedimentDepth')
        r.slotsResolved = sMask >= 0 && sSoil >= 0 && sSed >= 0
        const width = Math.max(2, sMask + 1, sSoil + 1, sSed + 1)
        const ins = new Array(width).fill(null)
        ins[0] = base
        if (sMask >= 0) ins[sMask] = mask
        if (sSoil >= 0) ins[sSoil] = soil0
        if (sSed >= 0) ins[sSed] = sed0

        // ---- THE INDEPENDENT CORRIDOR-DOWNCUT CEILING, from this file's fixture and parameters ----
        // src/legacy.js:3152: relief = max(max(inp)-min(inp), 1e-5); cut = relief*(.0003+.0072*down)*fix.
        // Both the correct figure and the fix-blind one are computed, so the error
        // `softcut-ceiling-ignores-fix` injects is a MEASURED arming distance rather than an argued one.
        let bmn = Infinity, bmx = -Infinity
        for (let i = 0; i < N; i++) { if (base[i] < bmn) bmn = base[i]; if (base[i] > bmx) bmx = base[i] }
        const reliefNorm = Math.max(bmx - bmn, 1e-5)
        r.reliefNormIndep = reliefNorm
        r.fixParam = after.fix
        r.softCutIndepM = reliefNorm * (0.0003 + 0.0072 * after.downcut) * after.fix * HEIGHT_M
        r.softCutFixBlindM = reliefNorm * (0.0003 + 0.0072 * after.downcut) * HEIGHT_M
        // The bound is over the handful of double operations that form the product on each side —
        // the min/max scan is exact — so it scales with the CEILING ITSELF and not with the terrain.
        r.softCutBound = boundF64(8, Math.abs(r.softCutIndepM))
        r.softCutArming = r.softCutBound > 0
          ? Math.abs(r.softCutFixBlindM - r.softCutIndepM) / r.softCutBound : 0

        const nd = { id: 9401, type: 'hydrofix', params: null }
        const demanded = new Set([primaryId, 'out', 'solidTop', 'bedrockHeight',
          'soilDepth', 'sedimentDepth', 'sandDepth'])

        // --- BEFORE: the node's own exact bypass. Contractually an identity pass that echoes cover
        //     and publishes an all-zero cover ledger.
        nd.params = { ...beforeParams }
        const rawB = TYPES.hydrofix.eval(nd.params, ins, nd, { demanded })
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
          // Every conditioning term AND the source term: a pass that removed nothing must say so on
          // all of them, and `softCutCeilingM` is the one a stale-constant implementation gets wrong.
          ledgerAllZero: !!ledB && ['coverConsumedM3', 'bedrockCarvedM3', 'depositedM3',
            'publishedRiseM3', 'maxLoweringM'].every(k => ledB[k] === 0)
            && ledB.loweredCells === 0 && ledB.risenCells === 0
            && (ledB.softCutCeilingM === 0 || masked),
          bypassFlag: !!ledB && (masked ? ledB.softCutClaimed === false : ledB.bypass === true),
          topFinite: topB ? finiteAll(topB) : false,
        }

        // --- AFTER: one real conditioning pass in this run's regime.
        nd.params = { ...after }
        const rawA = TYPES.hydrofix.eval(nd.params, ins, nd, { demanded })
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

        // --- THE PUBLISHED DELTA, MEASURED HERE AND PARTITIONED HERE -------------------------------
        // The independent reckoning of what the pass did: how many cells moved which way, and — from
        // the INPUT cover rasters and the published delta, never from the ledger — how much of the
        // carve each layer should have supplied. This is what makes the ledger a measurement rather
        // than a restatement of its own accumulator.
        if (primA && primB) {
          let moved = 0, risen = 0, maxDrop = 0, maxRise = -Infinity, riseIndep = 0
          let consumedIndep = 0, carvedIndep = 0, consumedDouble = 0
          for (let i = 0; i < N; i++) {
            const d = primA[i] - primB[i]
            const dM = d * HEIGHT_M
            if (d !== 0) moved++
            if (dM > maxRise) maxRise = dM
            if (d > 0) { risen++; riseIndep += dM }
            if (-dM > maxDrop) maxDrop = -dM
            if (dM < 0) {
              // THE STRIP, RECOMPUTED FROM THE INPUT COVER AND THE PUBLISHED DELTA — never from the
              // ledger's own accumulator. Sand is omitted because nothing wires a sandDepth input, so
              // production's first take is identically zero; the order is production's, sediment
              // before soil (ADR-005's stack, top down).
              //
              // PRODUCTION'S ARITHMETIC MODEL IS MIRRORED HERE, AND THAT IS LOAD-BEARING RATHER THAN
              // A CONVENIENCE. src/plugins/ero/hydrofix.js stores each residual thickness through
              // `Math.fround` and accumulates the consumption from THOSE stored values, so the
              // float32 rounding is a property of the published rasters and not an error in them. An
              // oracle stripping in pure double disagrees by one float32 ulp of the STANDING cover at
              // every carved cell — measured on this corpus at 18.8 to 82.6 m3, five orders above the
              // double bound. `consumedDoubleM3` keeps that rejected model live on every run so the
              // choice is a measured delta rather than an argument made once; see
              // `thePureDoubleStripModelIsDemonstrablyWrong`.
              let e = -dM
              const td = sed0[i] < e ? sed0[i] : e; e -= td
              const ts = soil0[i] < e ? soil0[i] : e; e -= ts
              const d1 = Math.fround(sed0[i] - td), s1 = Math.fround(soil0[i] - ts)
              consumedIndep += (sed0[i] - d1) + (soil0[i] - s1)
              carvedIndep += e
              consumedDouble += Math.min(-dM, soil0[i] + sed0[i])
            }
          }
          r.samplesMoved = moved
          r.samplesRisen = risen
          r.maxLoweringM = maxDrop
          r.maxPublishedRiseMeasuredM = maxRise
          r.riseIndepM3 = riseIndep * r.areaExpected
          r.consumedIndepM3 = consumedIndep * r.areaExpected
          r.consumedDoubleM3 = consumedDouble * r.areaExpected
          r.carvedIndepM3 = carvedIndep * r.areaExpected
          // WHAT THIS BOUND SCALES WITH: the volume the pass actually removed — never a standing
          // thickness. Both sides are double reductions over the same float32 stored thicknesses, so
          // the representation rounding cancels term by term and only the reduction ordering is left.
          r.partitionBound = boundF64(N, Math.abs(r.consumedIndepM3) + Math.abs(r.carvedIndepM3))
          r.partitionModelGapM3 = Math.abs(r.consumedDoubleM3 - r.consumedIndepM3)
          if (led) {
            r.consumedErr = Math.abs((led.coverConsumedM3 || 0) - r.consumedIndepM3)
            r.carvedErr = Math.abs((led.bedrockCarvedM3 || 0) - r.carvedIndepM3)
            r.partitionMatches = r.consumedErr <= r.partitionBound && r.carvedErr <= r.partitionBound
            r.partitionArming = r.partitionBound > 0
              ? (Math.abs(r.consumedIndepM3) + Math.abs(r.carvedIndepM3)) / r.partitionBound : 0
          }
          // THE MECHANISM RATIO, measured so the refusal to split is about a real second term.
          r.breachDominance = r.softCutIndepM > 0 ? maxDrop / r.softCutIndepM : 0
        }

        // --- the byte-identity control ----------------------------------------------------------
        // The SAME pass called the way the pre-S3.5 build was called: two slots, no cover attached,
        // and only the primary demanded. D21 authorises a STATED re-bless for this node, but a graph
        // that wires no cover must produce the terrain it produced yesterday, byte for byte, and that
        // has to be MEASURED rather than argued from the fact that the digest recipe happens not to
        // demand a state port.
        const rawU = TYPES.hydrofix.eval(nd.params, [ins[0], mask], nd, { demanded: new Set([primaryId]) })
        const primU = grab(readValues(rawU), primaryId)
        r.unwiredLength = primU ? primU.length : null
        r.unwiredMatchesWired = bitEqual(primU, primA)

        // --- the digest-shape control -----------------------------------------------------------
        // With NO ctx at all — which is exactly how _verify_digest.js calls every evaluator — the
        // return must still be a bare typed array, not a values Map. If it became typed, the digest
        // would start folding five extra ports for this node and the baseline would move for a reason
        // that has nothing to do with the physics.
        const rawN = TYPES.hydrofix.eval(nd.params, ins, nd)
        r.undemandedIsBareField = ArrayBuffer.isView(rawN) && !(rawN && rawN.values instanceof Map)
          && rawN.length === N
        r.undemandedMatchesWired = bitEqual(rawN, primA)

        // --- there is no GPU path, and that is MEASURED -------------------------------------------
        // hydrofix.js imports nothing from core/gpu.js, so the same evaluation under USE_GPU true
        // must be bit-identical. This fails the day a GPU hydrofix kernel lands without a ledger.
        USE_GPU = true
        const rawG = TYPES.hydrofix.eval(nd.params, ins, nd, { demanded: new Set([primaryId]) })
        USE_GPU = false
        r.gpuMatchesCpu = bitEqual(grab(readValues(rawG), primaryId), primA)

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
          const acc = { samples: 0, violations: 0, maxResidualM: 0, maxTolM: 0 }
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
            if (tol > acc.maxTolM) acc.maxTolM = tol
          }
          return acc
        }
        const sB = stack(topB, bedB, soilB, sedB, sandB), sA = stack(topA, bedA, soilA, sedA, sandA)
        r.stackIdentity = {
          samples: sB.samples + sA.samples, expected: 2 * N,
          violations: sB.violations + sA.violations,
          maxResidualM: Math.max(sB.maxResidualM, sA.maxResidualM),
          maxTolM: Math.max(sB.maxTolM, sA.maxTolM),
        }

        // --- WHICH FRAME solidTop is actually in -------------------------------------------------
        // D20: a physical node takes `physical-stable`. That is a claim about production's
        // arithmetic, so it is measured, not read off a label: the BEFORE pass moved no material, so
        // its solidTop must be the base field this file AUTHORED, mapped through the datum and
        // relief production reports. AND THE COMPARISON IS ARMED IN PLACE — the autolevelled
        // alternative is evaluated on the same fixture and required to DISAGREE by three orders of
        // magnitude more than the tolerance. If the two frames happened to coincide here, the
        // agreement would be evidence of nothing.
        if (topB && ledB && Number.isFinite(ledB.datumM) && Number.isFinite(ledB.reliefHeightM)) {
          const dat = ledB.datumM, rel = ledB.reliefHeightM
          const span = (bmx - bmn) || 1
          let maxStable = 0, maxAuto = 0
          for (let i = 0; i < N; i++) {
            const ds = Math.abs(topB[i] - (dat + base[i] * rel))
            const da = Math.abs(topB[i] - (dat + (base[i] - bmn) / span * rel))
            if (ds > maxStable) maxStable = ds
            if (da > maxAuto) maxAuto = da
          }
          r.frame = { name: typeof ledB.frame === 'string' ? ledB.frame : null, datumM: dat, reliefHeightM: rel,
            maxErrVsStableM: maxStable, maxErrVsAutolevelM: maxAuto,
            tolM: 4 * F32_ULP * (Math.abs(dat) + Math.abs(rel)) + 1e-6 }
        }

        // --- the frame-free readings -------------------------------------------------------------
        if (soilA && sedA && sandA && soilB && sedB && sandB) {
          const A = r.areaExpected
          let dCover = 0, absChange = 0, minCoverAfter = Infinity, maxCoverRise = -Infinity
          let minCoverStanding = Infinity
          for (let i = 0; i < N; i++) {
            const c1 = soilA[i] + sedA[i] + sandA[i]
            const c0 = soilB[i] + sedB[i] + sandB[i]
            dCover += A * (c1 - c0)
            absChange += A * Math.abs(c1 - c0)
            if (c1 < minCoverAfter) minCoverAfter = c1
            if (c0 > 0 && c0 < minCoverStanding) minCoverStanding = c0
            if (c1 - c0 > maxCoverRise) maxCoverRise = c1 - c0
          }
          r.dCoverM3 = dCover
          r.minCoverAfter = minCoverAfter
          r.minCoverStandingM = Number.isFinite(minCoverStanding) ? minCoverStanding : null
          // MEASURED FROM THE RASTERS, not read off the ledger. This is what makes "deposits
          // nothing" a reading of the published fields rather than a restatement of a flag.
          r.maxCoverRiseMeasuredM = maxCoverRise
          // THE COVER BOOK'S BOUND IS A DOUBLE-REDUCTION BOUND OVER THE ABSOLUTE CHANGE.
          //
          // WHAT IT SCALES WITH: the absolute per-cell cover CHANGE — the thickness this pass
          // actually moved. Summing |c1|+|c0| instead would make the tolerance a function of how much
          // cover is STANDING, which on the deep fixture is thousands of metres per cell and grows
          // with the fixture rather than with what the pass did. That is the "bound scales with the
          // terrain, not with the transport" defect this suite has now measured three times, once at
          // 1e9x too loose. `coverBookBoundLoose` below re-measures the rejected form on EVERY RUN so
          // the arming is a live delta between two endpoints rather than a note about a draft.
          //
          // WHY F64. Production accumulates `(a0-a1)+(d0-d1)+(s0-s1)` in double FROM THE PUBLISHED
          // FLOAT32 RASTER VALUES (src/plugins/ero/hydrofix.js) and this file accumulates `c1-c0` in
          // double from those same values, so the float32 rounding is COMMON to both sides and
          // cancels term by term; the only residual is the reduction ordering, which is double. It is
          // a STRONGER gate this way: an implementation computing the ledger from double
          // intermediates instead of from the rasters it publishes would break the cancellation.
          r.coverBookBound = boundF64(N, absChange)
          let absStanding = 0
          for (let i = 0; i < N; i++) {
            absStanding += A * (Math.abs(soilA[i] + sedA[i] + sandA[i])
              + Math.abs(soilB[i] + sedB[i] + sandB[i]))
          }
          r.coverBookBoundLoose = boundF32(N, absStanding)
          if (led) {
            // deposited is a published constant zero for this node, and it is INCLUDED in the book
            // rather than assumed away: a build that started depositing while leaving the raster
            // alone would show up here as well as in the no-deposition gate.
            r.coverBookErr = Math.abs(dCover - ((led.depositedM3 || 0) - (led.coverConsumedM3 || 0)))
            r.coverBookCloses = r.coverBookErr <= r.coverBookBound
            const removed = Math.abs(led.coverConsumedM3 || 0) + Math.abs(led.bedrockCarvedM3 || 0)
            r.removedM3 = removed
            r.coverBookArming = r.coverBookBound > 0 ? removed / r.coverBookBound : 0
            r.coverBookArmingLoose = r.coverBookBoundLoose > 0 ? removed / r.coverBookBoundLoose : 0
          }
          // THE STACK TOLERANCE, ARMED. "The identity closed" is only worth something if the
          // tolerance is far below the thinnest layer a dropped term would remove. This is that
          // ratio, measured on every run that carries standing cover.
          if (r.stackIdentity && r.stackIdentity.maxTolM > 0 && Number.isFinite(minCoverStanding)) {
            r.stackHeadroom = minCoverStanding / r.stackIdentity.maxTolM
          }
        }

        // --- the ledger read exactly as published -------------------------------------------------
        if (led) {
          const has = k => Object.prototype.hasOwnProperty.call(led, k)
          r.areaReportedOk = Math.abs((led.cellAreaM2 || 0) - r.areaExpected) <= 1e-9 * r.areaExpected
          r.ledgerLatticeOk = led.lattice === lattice
          r.ledgerRowsOk = led.rows === r.rowsExpected
          r.loss = {
            claimed: led.lossClaimed !== false,
            source: typeof led.lossSource === 'string' ? led.lossSource : null,
            policy: typeof led.boundaryPolicy === 'string' ? led.boundaryPolicy : null,
            exported: has('exportedM3') ? led.exportedM3 : null,
            boundaryExported: has('boundaryExportedM3') ? led.boundaryExportedM3 : null,
            suspended: has('suspendedM3') ? led.suspendedM3 : null,
          }
          r.split = {
            claimed: led.mechanismSplitClaimed !== false,
            source: typeof led.mechanismSplitSource === 'string' ? led.mechanismSplitSource : null,
            softCut: has('softCutRemovedM3') ? led.softCutRemovedM3 : null,
            breach: has('breachRemovedM3') ? led.breachRemovedM3 : null,
          }
          r.softCutClaim = {
            claimed: led.softCutClaimed !== false,
            source: typeof led.softCutSource === 'string' ? led.softCutSource : null,
            ceilingM: has('softCutCeilingM') ? led.softCutCeilingM : null,
            fix: has('softCutFix') ? led.softCutFix : null,
            downcut: has('softCutDowncut') ? led.softCutDowncut : null,
            bypass: has('bypass') ? led.bypass : null,
          }
          if (typeof led.softCutCeilingM === 'number' && Number.isFinite(r.softCutIndepM)) {
            r.softCutErr = Math.abs(led.softCutCeilingM - r.softCutIndepM)
            r.softCutMatches = r.softCutErr <= r.softCutBound
          }
          if (typeof led.publishedRiseM3 === 'number' && Number.isFinite(r.riseIndepM3)) {
            r.riseBound = boundF64(N, Math.abs(r.riseIndepM3))
            r.riseErr = Math.abs(led.publishedRiseM3 - r.riseIndepM3)
            r.riseMatches = r.riseErr <= r.riseBound
          }
          r.depositedZero = led.depositedM3 === 0 && led.depositionModelled === false
          r.slotsReported = led.soilSlot === sSoil && led.sedimentSlot === sSed
            && led.maskSlot === sMask && led.soilWired === true && led.sedimentWired === true
        }
      } catch (e) {
        r.error = String((e && e.message) || e)
      }
      return r
    }

    const plan = []
    for (const fx of ['deep', 'bare', 'mixed']) {
      plan.push(['square', fx, false, 'defaults'])
      plan.push(['hex', fx, false, 'defaults'])
    }
    // BOTH SLIDER REGIMES on all three cover fixtures. `full` roughly doubles the cells the carve
    // touches and is where the corridor term is largest against the breach, so
    // `breachDominatesTheCorridorDowncut` is measured across a real range rather than at one point.
    for (const fx of ['deep', 'bare', 'mixed']) {
      plan.push(['square', fx, false, 'full'])
      plan.push(['hex', fx, false, 'full'])
    }
    // The masked path, on the fixture that exercises both layers. This is the run where the node must
    // publish NO corridor ceiling, and it is the only place `claims-softcut-ceiling-under-mask` bites.
    plan.push(['square', 'mixed', true, 'defaults'])
    plan.push(['hex', 'mixed', true, 'defaults'])
    for (const [lat, fx, masked, reg] of plan) out.runs.push(runOne(lat, fx, masked, reg))

    // --- a wired cover raster that is not a depth must be REFUSED, not half-read ------------------
    // Zero cover is bare bedrock and is real data (core/cover-state.js), so the only way to tell
    // "you wired rubbish" from "you wired nothing" is to say so. Both a non-finite sample and a
    // negative thickness are refused by name.
    out.rejects = { nonFinite: false, negative: false, cleanStillEvaluates: false }
    try {
      terrainDef.lattice = 'square'; terrainDef.scale = SCALE_M; terrainDef.height = HEIGHT_M
      terrainDef.baseElevation = DATUM_M
      RES = RES_FIX; TARGET_RES = RES_FIX; USE_GPU = false
      if (typeof buildIndex === 'function') buildIndex()
      const W = fieldW(), H = fieldH(), N = W * H
      const base = makeBase(W, H)
      const nd = { id: 9402, type: 'hydrofix', params: { ...REGIMES.defaults } }
      const demanded = new Set(['solidTop', 'soilDepth'])
      const sSoil = slotOf('soilDepth'), sSed = slotOf('sedimentDepth')
      const mk = mutate => {
        const soil = new Float32Array(N).fill(10)
        if (mutate) mutate(soil)
        const ins = new Array(Math.max(2, sSoil + 1, sSed + 1)).fill(null)
        ins[0] = base
        if (sSoil >= 0) ins[sSoil] = soil
        if (sSed >= 0) ins[sSed] = new Float32Array(N)
        return ins
      }
      try { TYPES.hydrofix.eval(nd.params, mk(a => { a[13] = NaN }), nd, { demanded }) }
      catch (e) { out.rejects.nonFinite = /non-negative depth/.test(String(e && e.message)) }
      try { TYPES.hydrofix.eval(nd.params, mk(a => { a[13] = -1 }), nd, { demanded }) }
      catch (e) { out.rejects.negative = /non-negative depth/.test(String(e && e.message)) }
      // ...and a clean wired cover still evaluates, so the two above are a refusal of BAD DATA and
      // not a node that refuses cover altogether.
      const okRaw = TYPES.hydrofix.eval(nd.params, mk(null), nd, { demanded })
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
    out.distinctFixtures = new Set(out.runs.map(r => r.fixture)).size
    // PER LATTICE, not across them. The same fixture hashes differently on square and hex because the
    // field has a different row count, so a single set over every run would hold 3 fixtures x 2
    // lattices and asserting 3 there would be measuring the wrong thing. What the corpus has to prove
    // is that the three cover configurations genuinely differ ON EACH LATTICE.
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
  const withCover = deep.concat(mixed).concat(masked)
  const ledNum = (r, k) => (r.ledger && typeof r.ledger[k] === 'number') ? r.ledger[k] : null

  const gates = {
    // --- the declared surface ------------------------------------------------------------------
    coverInputPortsDeclared: report.ports.soilIn === true && report.ports.sedIn === true
      && report.ports.noPrecipIn === true && report.ports.noUpliftIn === true
      && report.ports.insLabels.join('|') === 'In|Mask|Soil depth|Sediment depth',
    stateOutputPortsDeclared: report.ports.solidTopOut === true && report.ports.bedrockOut === true
      && report.ports.soilOut === true && report.ports.sedOut === true && report.ports.sandOut === true
      && report.ports.noTransportSedimentOut === true,

    // --- fix = 0 is the node's own exact bypass, and it is how BEFORE is measured -----------------
    // src/legacy.js:3139 returns `inp.slice()` before computing anything. Armed by `bypass-not-exact`.
    fixZeroIsAnExactBypass: every(runs, r => r.before && r.before.heightUnmoved === true
      && r.before.ledgerAllZero === true && r.before.bypassFlag === true),
    noTransportPassEchoesCover: every(runs, r => r.before && r.before.hasState === true
      && r.before.echoesSoil === true && r.before.echoesSed === true && r.before.sandZero === true
      && r.before.lengthsOk === true && r.before.topFinite === true),

    // --- the pass actually ran, on a fixture with something to breach -----------------------------
    // A PRECONDITION for everything below, and deliberately unarmed by any mutation: it establishes
    // that the fixture was conditioned AND that it contained closed depressions, so the descent
    // enforcement — the node's second mechanism — was not dormant.
    conditioningRemovedMaterial: every(runs, r => num(r.samplesMoved) !== null && r.samplesMoved > 0
      && num(r.removedM3) !== null && r.removedM3 > 0 && num(r.pitCells) !== null && r.pitCells > 0),

    // --- THE CLASSIFICATION, READ OFF THE PUBLISHED FIELD -----------------------------------------
    // `hydroFixField`'s two write paths can only lower (src/legacy.js:3153, :3155-3156), so the
    // positive part of the published delta must be EMPTY. Four independent readings, all of which a
    // raising build breaks: the ledger's integral of the rise, its count, its extremum, and this
    // file's own measurement of the same quantity from the primary raster. This is the gate that
    // makes `latticeConditioning` a measurement rather than a label. Armed by `publishes-a-rise`,
    // which stages a coherent raising build in which every volume book still closes.
    publishedDeltaIsMonotoneNonIncreasing: every(runs, r => ledNum(r, 'publishedRiseM3') === 0
      && ledNum(r, 'risenCells') === 0
      && num(ledNum(r, 'maxPublishedRiseM')) !== null && ledNum(r, 'maxPublishedRiseM') <= 0
      && num(r.samplesRisen) !== null && r.samplesRisen === 0
      && num(r.maxPublishedRiseMeasuredM) !== null && r.maxPublishedRiseMeasuredM <= 0
      && r.riseMatches === true),

    // --- COVER BEFORE BEDROCK, armed by three fixtures --------------------------------------------
    // 1) the deep fixture must actually consume cover, or the next gate is about nothing;
    coverIsConsumedOnDeepFixture: every(deep, r => num(ledNum(r, 'coverConsumedM3')) !== null
      && ledNum(r, 'coverConsumedM3') > 0),
    // 2) and cover must never have reached zero anywhere, or "bedrock untouched" is unarmed. The
    //    measured headroom is printed as maxLoweringM against the fixture's derived DEEP.
    deepFixtureCoverNeverExhausted: every(deep, r => num(r.minCoverAfter) !== null && r.minCoverAfter > 0
      && num(r.maxLoweringM) !== null && num(r.deepM) !== null && r.maxLoweringM < r.deepM),
    // 3) THE STORY'S NAMED RED. Bedrock is not carved while local loose cover remains.
    bedrockUntouchedWhileCoverRemains: every(deep, r => ledNum(r, 'bedrockCarvedM3') === 0),
    // 4) and the kernel must be CAPABLE of carving bedrock, or (3) passes by refusing to move.
    bareBedrockIsCarved: every(bare, r => num(ledNum(r, 'bedrockCarvedM3')) !== null
      && ledNum(r, 'bedrockCarvedM3') > 0 && ledNum(r, 'coverConsumedM3') === 0),
    // 5) the mixed fixture exercises the boundary between the two regimes in one pass.
    mixedFixtureCutsBothLayers: every(mixed, r => num(ledNum(r, 'coverConsumedM3')) !== null
      && ledNum(r, 'coverConsumedM3') > 0 && num(ledNum(r, 'bedrockCarvedM3')) !== null
      && ledNum(r, 'bedrockCarvedM3') > 0),

    // --- THE LEDGER IS THE PARTITION OF THE PUBLISHED DELTA, RECOMPUTED HERE ----------------------
    // Both terms are compared against an independent reckoning taken from the INPUT cover rasters and
    // the published delta — never from the ledger's own accumulator. That is what makes
    // `coverConsumedM3` and `bedrockCarvedM3` measurements rather than two names for one number.
    // Armed by `ledger-consumption-inflated` and `bedrock-first-kernel`.
    ledgerPartitionMatchesTheField: every(runs, r => r.partitionMatches === true),
    // ...and the tolerance on that comparison is far smaller than the volume it partitions. WHAT IT
    // SCALES WITH: the removed volume itself, through boundF64 — both sides are double reductions
    // over the same float32 samples, so 2*gamma64(2N) ~ 1.8e-12 relative is the honest unit. The
    // threshold is 1e6, four orders below the arithmetic ceiling, so a bound silently loosened to the
    // float32 unit is a named red rather than an invisible relaxation.
    partitionBoundIsSmallerThanTheCarve: every(runs, r => num(r.partitionArming) !== null
      && r.partitionArming > 1e6),
    // ...and the OTHER endpoint of that bound, measured live rather than argued. The rejected
    // pure-double strip must still MISS by more than the bound the mirrored one passes, which is what
    // proves the float32 model is a property of the published rasters rather than a fudge that
    // happens to make the numbers agree. Restricted to the cover-carrying fixtures: `bare` consumes
    // nothing, both models give exactly 0, and the comparison would be about nothing.
    thePureDoubleStripModelIsDemonstrablyWrong: every(withCover, r => num(r.partitionModelGapM3) !== null
      && num(r.partitionBound) !== null && r.partitionModelGapM3 > r.partitionBound),

    // --- DEPOSITS NOTHING: there is no additive term in the kernel at all --------------------------
    // Three independent readings: the published constant, the ledger's own measured maximum cover
    // rise, and this file's measurement of the same quantity from the soil/sediment/sand rasters.
    // Armed by `invents-deposition`.
    conditioningDepositsNothing: every(runs, r => r.depositedZero === true
      && num(ledNum(r, 'maxCoverRiseM')) !== null && ledNum(r, 'maxCoverRiseM') <= 0
      && num(r.maxCoverRiseMeasuredM) !== null && r.maxCoverRiseMeasuredM <= 0),

    // --- conservation, entirely in frame-free thicknesses and volumes ------------------------------
    coverBookCloses: every(runs, r => r.coverBookCloses === true),
    // THE BOUND IS SMALLER THAN THE TERM IT CONSTRAINS, measured on every run rather than argued
    // once. WHAT IT SCALES WITH: the absolute per-cell cover CHANGE — the thickness this pass
    // actually moved — never a sum of standing thicknesses, which would make the tolerance a function
    // of how deep the fixture's cover is. `ledger-consumption-inflated` moves 3%, which needs only
    // ~33 to be seen, so a threshold of 1e6 is certain to bite while still catching a silent
    // loosening of four orders.
    coverBookBoundIsSmallerThanTheCarve: every(runs, r => num(r.coverBookArming) !== null
      && r.coverBookArming > 1e6),
    // ...and the OTHER endpoint, so the arming is a delta measured live rather than a claim about a
    // draft nobody can re-run. On the fixtures that carry standing cover, the rejected
    // terrain-scaled bound must still FAIL the threshold the corrected one passes. Restricted to the
    // cover-carrying fixtures because `bare` has no standing cover for such a bound to grow with —
    // there the two legitimately coincide at their 1e-6/1e-9 floors and the comparison would be
    // about nothing.
    theLooseCoverBookBoundIsDemonstrablyTooLoose: every(withCover,
      r => num(r.coverBookArmingLoose) !== null && r.coverBookArmingLoose < 1e6
        && num(r.coverBookArming) !== null && r.coverBookArming > 1e6),
    // AND THE STACK IDENTITY'S OWN TOLERANCE CANNOT HIDE A LAYER. "The identity closed" is worth
    // nothing if the per-sample tolerance is comparable to a cover thickness. WHAT IT SCALES WITH:
    // 4 float32 ulps of the sum of the five sampled magnitudes — a standing quantity, which is
    // correct here because it is bounding a float32 REPRESENTATION error and not a transport term.
    // This is the reading that proves it is nonetheless far under the thinnest layer present.
    stackToleranceCannotHideALayer: every(withCover, r => num(r.stackHeadroom) !== null
      && r.stackHeadroom > 1e3),

    // --- the corridor downcut ceiling, the one budget line this node can support --------------------
    // ITEMISED FROM THE KERNEL, NOT FROM THE FIELD: relief*(.0003+.0072*downcut)*fix, recomputed here
    // in double from this file's own fixture and parameters. Armed by `softcut-ceiling-ignores-fix`.
    softCutCeilingIsItemisedFromTheParameters: every(unmasked, r => !!r.softCutClaim
      && r.softCutClaim.claimed === true && r.softCutMatches === true
      && r.softCutClaim.source === 'kernel-corridor-downcut-ceiling'
      && r.softCutClaim.bypass === false
      && num(r.softCutClaim.ceilingM) !== null && r.softCutClaim.ceilingM > 0),
    // ...and the tolerance on that comparison is far smaller than the error a fix-blind
    // implementation makes. WHAT IT SCALES WITH: the ceiling itself through boundF64 over the handful
    // of double operations that form it, plus a 1e-9 m absolute floor. The fix-blind error is
    // (1/fix - 1) of the ceiling — 92% of about 2 m at the shipped default — so the ratio runs many
    // orders above the threshold.
    //
    // SCOPED TO fix < 1, AND THE SCOPE IS ITSELF ASSERTED NON-EMPTY. `(1/fix - 1)` is IDENTICALLY
    // ZERO at fix = 1, so on the `full` regime there is no fix-blind error to be clear of and an
    // arming ratio there would be measuring nothing — the first draft of this file asserted it
    // across every run and scored a legitimate 0 on those six. The `sub` list below is required to
    // be non-empty so the restriction cannot quietly become a scope that no run reaches, which is
    // the other half of the same hazard.
    softCutBoundIsSmallerThanTheFixError: (() => {
      const sub = unmasked.filter(r => num(r.fixParam) !== null && r.fixParam < 1)
      return sub.length > 0 && sub.every(r => num(r.softCutArming) !== null && r.softCutArming > 1e6)
    })(),
    // TRANSFORMED: the mask blended the result toward the input, so the kernel's ceiling no longer
    // describes what is published. The node must claim NOTHING and say which transform removed the
    // claim. Armed by `claims-softcut-ceiling-under-mask`.
    maskedPathPublishesNoSoftCutClaim: every(masked, r => !!r.softCutClaim
      && r.softCutClaim.claimed === false && r.softCutClaim.source === 'mask-composite'
      && r.softCutClaim.ceilingM === null && r.softCutClaim.fix === null
      && r.softCutClaim.bypass === null),

    // --- the export budget, refused on every path and for a stated reason ---------------------------
    // Everything removed leaves the world, but the only figure available is consumed+carved — a
    // restatement of the terms it would be checked against. The node prints none. Armed by
    // `claims-derived-export-closure`.
    exportBudgetIsNeverClaimedAndNamesWhy: every(runs, r => !!r.loss && r.loss.claimed === false
      && r.loss.source === 'carved-volume-is-discarded-and-not-accumulated-by-the-kernel'
      && r.loss.policy === null && r.loss.exported === null
      && r.loss.boundaryExported === null && r.loss.suspended === null),
    // --- and so is the mechanism split, for the same reason ------------------------------------------
    // Armed by `claims-mechanism-split`.
    mechanismSplitIsNeverClaimedAndNamesWhy: every(runs, r => !!r.split && r.split.claimed === false
      && r.split.source === 'downcut-and-breach-not-accumulated-separately-by-the-kernel'
      && r.split.softCut === null && r.split.breach === null),
    // ...and the refusal is about a term that genuinely matters. A PRECONDITION gate, unarmed by any
    // mutation: it MEASURES that the breach mechanism dominates the corridor downcut on every run, so
    // "the split is refused" is a refusal to guess at a large second term rather than a shrug about a
    // rounding artefact. Measured across this corpus the ratio runs roughly 30x to 270x.
    breachDominatesTheCorridorDowncut: every(runs, r => num(r.breachDominance) !== null
      && r.breachDominance > 2),

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
    // S3.5 implements consumption ORDER — loose cover first, bedrock second — and not a differential
    // resistance law, which nobody has specified and which would be a fabricated constant. So the
    // published height with cover attached must be the published height without it, bit for bit, and
    // D21's re-bless stays unspent. Armed by `cover-alters-published-height`.
    coverDoesNotMoveThePublishedHeight: every(runs, r => r.unwiredMatchesWired === true
      && r.unwiredLength === r.N),
    // ...and the no-ctx call shape — the one _verify_digest.js uses — still returns the bare field it
    // always did, so the baseline cannot move for a reason unrelated to the physics.
    undemandedEvaluationStaysUntyped: every(runs, r => r.undemandedIsBareField === true
      && r.undemandedMatchesWired === true),
    // There is no GPU hydrofix kernel; this MEASURES that rather than assuming it, so a GPU path
    // added without a ledger is a named red instead of a silent gap in this file's coverage.
    kernelIsGpuFreeOnBothPaths: every(runs, r => r.gpuMatchesCpu === true),

    // --- lattice -----------------------------------------------------------------------------------
    latticeCellAreaCorrect: every(runs, r => r.areaReportedOk === true && r.ledgerLatticeOk === true
      && r.ledgerRowsOk === true
      && num(r.cellSizeProd) !== null && Math.abs(r.cellSizeProd - r.cellSizeIndep) <= 1e-9 * r.cellSizeIndep),
    // A PRECONDITION gate, green today and deliberately unarmed: it establishes that the run reached
    // real production geometry on both lattices, so a red elsewhere means the feature is absent rather
    // than that the fixture never executed.
    hexRowCountIsNotRes: every(runs.filter(r => r.lattice === 'hex'), r => r.H === r.rowsExpected && r.H !== r.W)
      && every(runs.filter(r => r.lattice === 'square'), r => r.H === r.W && r.H === r.rowsExpected),
    bothLatticesMeasured: runs.some(r => r.lattice === 'square' && r.ran === true)
      && runs.some(r => r.lattice === 'hex' && r.ran === true),
    bothRegimesMeasured: runs.some(r => r.regime === 'defaults' && r.ran === true)
      && runs.some(r => r.regime === 'full' && r.ran === true),

    // --- the slots the evaluator actually indexed ---------------------------------------------------
    // "Declared" and "filled" are two separate measured claims. A descriptor pointing at a slot the
    // evaluator never reads would look exactly like a working port. The numbers are erosion2's, not
    // stream power's: this row's frozen head is In/Mask with no Uplift to work around.
    coverSlotsAreDeclaredAndFilled: every(runs, r => r.slotsResolved === true && r.slotsReported === true)
      && report.ports.slots.mask === 1 && report.ports.slots.soil === 2 && report.ports.slots.sed === 3,

    // --- a wired cover raster that is not a depth is refused by name ---------------------------------
    badCoverRasterIsRefusedNotHalfRead: report.rejects.nonFinite === true
      && report.rejects.negative === true && report.rejects.cleanStillEvaluates === true,

    // --- absence of evidence is a failure -------------------------------------------------------------
    fixtureCorpusNonEmptyAndDistinct: runs.length >= 8 && report.distinctFixtures === 3
      && report.perLatticeDistinct === true
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

  console.log('== S3.5 cover-aware CONDITIONING CARVE (hydrofix) ==')
  console.log(`ins=[${report.ports.insLabels.join(',')}] in=[${report.ports.declaredInputIds.join(',')}] `
    + `out=[${report.ports.declaredOutputIds.join(',')}] slots=${JSON.stringify(report.ports.slots)}`)
  for (const r of runs) {
    console.log(`  ${r.key.padEnd(22)} W=${r.W} H=${r.H} pits=${r.pitCells} deepM=${r.deepM} moved=${r.samplesMoved} risen=${r.samplesRisen} `
      + `maxLoweringM=${fmt(r.maxLoweringM)} maxRise=${fmt(r.maxPublishedRiseMeasuredM)} `
      + `consumed=${fmt(ledNum(r, 'coverConsumedM3'))} indep=${fmt(r.consumedIndepM3)} err=${fmt(r.consumedErr)} `
      + `carved=${fmt(ledNum(r, 'bedrockCarvedM3'))} indep=${fmt(r.carvedIndepM3)} err=${fmt(r.carvedErr)} `
      + `partArming=${fmt(r.partitionArming)} deposited=${fmt(ledNum(r, 'depositedM3'))} `
      + `softCut=${fmt(r.softCutClaim ? r.softCutClaim.ceilingM : null)} indep=${fmt(r.softCutIndepM)} `
      + `softErr=${fmt(r.softCutErr)} softArming=${fmt(r.softCutArming)} softSrc=${r.softCutClaim ? r.softCutClaim.source : 'n/a'} `
      + `breachDom=${fmt(r.breachDominance)} lossClaimed=${r.loss ? r.loss.claimed : 'n/a'} `
      + `splitClaimed=${r.split ? r.split.claimed : 'n/a'} `
      + `coverBookErr=${fmt(r.coverBookErr)} bound=${fmt(r.coverBookBound)} arming=${fmt(r.coverBookArming)} `
      + `armingLoose=${fmt(r.coverBookArmingLoose)} stackHeadroom=${fmt(r.stackHeadroom)} `
      + `maxCoverRise=${fmt(r.maxCoverRiseMeasuredM)} minCover=${fmt(r.minCoverAfter)} err=${r.error || 'none'}`)
  }
  for (const [k, v] of Object.entries(gates)) console.log(`${v ? 'PASS' : 'FAIL'}  ${k}`)

  console.log(`${ok ? 'PASS' : 'FAIL'}  hydrofix co-evolution runs=${runs.length} ledgers=${runs.filter(r => r.ledger).length} `
    + `deepBedrockCarved=[${deep.map(r => fmt(ledNum(r, 'bedrockCarvedM3'))).join(',')}] `
    + `bareBedrockCarved=[${bare.map(r => fmt(ledNum(r, 'bedrockCarvedM3'))).join(',')}] `
    + `maxRisenCells=${Math.max(0, ...runs.map(r => num(r.samplesRisen) === null ? 1 : r.samplesRisen))} `
    + `maxCoverBookErr=${fmt(Math.max(0, ...runs.map(r => num(r.coverBookErr) === null ? 0 : r.coverBookErr)))} `
    + `maxPartitionErr=${fmt(Math.max(0, ...runs.map(r => Math.max(num(r.consumedErr) || 0, num(r.carvedErr) || 0))))} `
    + `maxSoftCutErr=${fmt(Math.max(0, ...runs.map(r => num(r.softCutErr) === null ? 0 : r.softCutErr)))} `
    + `minPartitionArming=${fmt(Math.min(...runs.map(r => num(r.partitionArming) === null ? 0 : r.partitionArming)))} `
    + `minCoverBookArming=${fmt(Math.min(...runs.map(r => num(r.coverBookArming) === null ? 0 : r.coverBookArming)))} `
    + `minSoftCutArming(fix<1)=${fmt(Math.min(...unmasked.filter(r => r.fixParam < 1)
      .map(r => num(r.softCutArming) === null ? 0 : r.softCutArming)))} `
    + `minPartitionModelGap=${fmt(Math.min(...withCover.map(r => num(r.partitionModelGapM3) === null ? 0 : r.partitionModelGapM3)))} `
    + `minBreachDominance=${fmt(Math.min(...runs.map(r => num(r.breachDominance) === null ? 0 : r.breachDominance)))} `
    + `minStackHeadroom=${fmt(Math.min(...withCover.map(r => num(r.stackHeadroom) === null ? 0 : r.stackHeadroom)))} `
    + `maxCoverRise=${fmt(Math.max(...runs.map(r => num(r.maxCoverRiseMeasuredM) === null ? 1 : r.maxCoverRiseMeasuredM)))} `
    + `minCoverAfter=${fmt(Math.min(...deep.map(r => num(r.minCoverAfter) === null ? -1 : r.minCoverAfter)))} `
    + `maxLoweringM=${fmt(Math.max(0, ...runs.map(r => num(r.maxLoweringM) === null ? 0 : r.maxLoweringM)))} `
    + `stackViolations=${runs.reduce((a, r) => a + ((r.stackIdentity && r.stackIdentity.violations) || 0), 0)} `
    + `unwiredMatchesWired=${runs.filter(r => r.unwiredMatchesWired === true).length}/${runs.length} `
    + `frame=${(runs.find(r => r.frame) || { frame: {} }).frame.name || 'n/a'} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
