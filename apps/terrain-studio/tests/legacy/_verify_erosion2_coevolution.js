// S3.5, THIRD NODE — cover-aware DEPOSITING multi-scale composition.
//
// WHAT THE PHYSICS TURNED OUT TO BE, AND HOW IT WAS SETTLED
// --------------------------------------------------------
// The two nodes before this one landed on opposite answers and neither transfers. Thermal deposits
// (talus slides downslope and lands somewhere). Stream Power does not (sprint-03:186 keeps it
// detachment-limited and the kernel has no deposit term at all). Erosion 2 was read rather than
// assumed, and it is a THIRD case:
//
//   IT DEPOSITS.  `erosion2Field` composes the pipe/droplet solver with an explicit
//                 `deposit = lerp(.08,.62,sediment)` (src/legacy.js:3084, handed to the kernel at
//                 :3086-3089) and then, at `p.shape>.01`, a thermal relaxation blended in at
//                 `lerp(h,shaped,p.shape*.72)` (:3100-3105). Both put transported material down.
//   ...AND THE DEPOSIT IS CONTAMINATED, which is the finding that shaped this file. Two stages raise
//                 the published surface without transporting anything to the cell:
//                   src/legacy.js:3068-3070  an fbm rock-resistance field added to the INPUT before
//                                            any solver runs. UNCONDITIONAL — `seedAmp =
//                                            relief*(.0007+.0022*detail)` with `relief =
//                                            Math.max(mx-mn,1e-5)` (:3065), so it is never zero and
//                                            it sits behind no `if`.
//                   src/legacy.js:3106-3112  `h[i] += residual>0 ? residual*shapeSharp*.24
//                                            : residual*shapeSharp*.07`. The gain is ASYMMETRIC, so
//                                            over a blur residual that sums to about zero the stage
//                                            has a positive net.
//                 Neither is accumulated anywhere, so neither can be separated out of the published
//                 rise. THE MEASUREMENT that settles the deposition question is
//                 `maxCoverRiseMeasuredM`, read back out of the soil/sediment/sand rasters: this
//                 node is required to show it STRICTLY POSITIVE, where Stream Power is required to
//                 show it at exactly zero. Same reading, opposite required sign, both measured.
//
// SO THE NODE PUBLISHES `depositionStageResolved: false` AND NAMES WHAT IS INSIDE THE FIGURE. That
// is the honest form of sprint-03:188, which asks Erosion 2 to "expose/co-update the state of the
// hydraulic/thermal stages it composes rather than re-deriving deposits from final height". Half of
// that is done here — the co-update happens in the pass, against the published field — and half of
// it CANNOT be done at node level: `erosion2Field` returns one Float32Array (:3113) and accumulates
// nothing per stage. Closing the other half needs accumulators inside that function, which lives in
// src/legacy.js and has a single serial owner. This story did not touch it, and the digest is
// bit-identical.
//
// THE NODE-LEVEL BOUNDARY BUDGET IS REFUSED ON EVERY PATH, AND THE REASON IS NOT THE BOUNDARY
// ------------------------------------------------------------------------------------------
// Thermal can publish a named physical zero (closed kernels). Hydraulic can publish the droplet
// solver's per-particle counters when exactly one kernel ran on an untransformed field. Erosion 2
// can do neither at node level, and not because of the rim: the fbm injection stands between
// `ins[0]` and the field every solver actually sees, so even with every transform switched off the
// solver's books describe a field the node did not receive, and the volume between them is
// unrecorded. The only figure the node could otherwise print is `coverConsumed + bedrockDetached -
// deposited`, a restatement of the three terms it would then be checked against — a closure that
// holds by construction for any implementation, including one that deletes the terrain.
// `claims-derived-export-closure` performs exactly that substitution and
// `nodeBoundaryBudgetIsNeverClaimedAndNamesWhy` is what sees it.
//
// THE ONE BUDGET LINE THAT IS ITEMISABLE, AND THE LIVE CONTROL ON THE MASKED PATH
// ------------------------------------------------------------------------------
// There is a legal slider setting in which the whole composition reduces to ONE hydraulic pass on
// the native grid: Erosion scale 0 (`featureScale = lerp(1,7,0) = 1`, so `atFeatureScale`
// short-circuits at :1517), Shape detail 0 (no nested pass, :3096), Shape 0 (no thermal, :3100),
// Shape sharpness 0 (no sharpen, :3106). On that path — and ONLY there — the solver's own boundary
// counters describe the grid the node publishes on, and the node reports them under their own
// `stage*` names with `stageBudgetScope` saying whose books they are. Both engines itemise:
//   pipes     `exportedToApron = apronOut - apronIn` over a cell ring DISJOINT from the core
//             (src/core/gpu.js:546-553)
//   droplets  `exported` per departing particle, `lost` per truncated particle, `brushClipGain` per
//             clipped brush cell (src/legacy.js:3054)
// Under a MASK the published field is a blend toward the input, so the stage's figure stops
// describing it and the node must claim NOTHING — that is the live control the masked runs exist
// for (`claims-stage-budget-under-mask`). Under the SHIPPED DEFAULTS four stages stand between the
// last solver and the published field and the same refusal applies
// (`claims-stage-budget-under-composition`). And the claimed figure is required NOT to coincide with
// any combination of the cover book, so a derived number cannot be smuggled in behind a real name
// (`stage-budget-derived-from-the-cover-book`); the distances are printed on every run.
//
// THE IDENTITY PASS IS A ZERO MASK, AND THAT IS NOT A CONVENIENCE — IT IS THE ONLY ONE THERE IS.
// Erosion 2 has no slider setting that transports nothing: `erode = lerp(.12,.70,down) *
// lerp(.72,1.12,duration)` is 0.0864 at both sliders zero (:3083) and `coarseIters = max(8, ...)`
// is at least 16 (:3071), and the fbm injection runs regardless. `maskApply` at :461 computes
// `base[i] + (modified[i]-base[i])*m`, which at m = 0 is `base[i]` exactly, so a zero mask is a real
// production evaluation that publishes the input bit for bit. `heightUnmoved` is what proves it
// rather than asserts it.
//
// THE CLOSURE BOUNDS SCALE WITH WHAT MOVED, NOT WITH THE FIXTURE. Both endpoints are measured on
// every run, for the reason S3.5b recorded: the draft of that file used the float32 unit over the
// sum of STANDING cover thicknesses, which made the tolerance a function of how much soil was lying
// there rather than of how much the pass moved (1e9x too loose). The correct bound is the DOUBLE
// unit over the absolute per-cell CHANGE, because production accumulates the book from THE PUBLISHED
// FLOAT32 RASTER VALUES and so does this file — the float32 rounding is common to both sides and
// cancels term by term. `coverBookBoundIsSmallerThanTheTransport` reads the corrected bound and
// `theLooseCoverBookBoundIsDemonstrablyTooLoose` re-measures the rejected one on the same fixture in
// the same run, so the arming is a live delta rather than an argument made once.
//
// LATTICE. Cell AREA is square s^2 and hex sqrt(3)/2*s^2, and a hex field is fieldW()*fieldH() with
// fieldH() = round(RES*2/sqrt(3)) rows, NOT RES (src/legacy.js:161-168). Both are computed here in
// double precision from terrainDef.scale/RES, never read back from production.
//
// ENGINE COVERAGE IS MEASURED, NOT ASSUMED. Unlike Stream Power this node HAS a GPU path
// (`gpuReady()?gpuHydraulicPipes(...):hydraulicErode(...)`, :3086-3089). The ledger's
// `stageBudgetEngine` is what reports which kernel actually ran, so `bothEnginesMeasured` fails if
// the GPU run silently fell back to the CPU rather than passing on a path nobody exercised.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'bedrock-first-kernel',                // the story's named failure: bedrock cut while cover remains
  'deposition-discarded',                // the rise is carried through instead of deposited
  'ledger-consumption-inflated',         // the ledger stops being the integral of the rasters
  'sand-nonzero',                        // sandDepth stops being zero although no aeolian process ships
  'square-area-on-hex',                  // the hex ledger integrates with s^2 instead of sqrt(3)/2*s^2
  'claims-derived-export-closure',       // a node budget appears and it is consumed+detached-deposited
  'claims-stage-resolved-deposition',    // the deposit claims to be carried out of the stages
  'hides-manufactured-rise',             // the stages that raise the surface for free stop being named
  'stage-census-hides-the-resample',     // the composition under-reports which stages ran
  'claims-stage-budget-under-mask',      // a stage budget published for a field the kernel did not produce
  'claims-stage-budget-under-composition', // ...and for one four stages removed from the kernel
  'stage-budget-derived-from-the-cover-book', // the stage budget becomes a restatement of the book
  'cover-alters-published-height',       // wiring cover moves the terrain: an unauthorised re-bless
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
    const sameList = (a, b) => Array.isArray(a) && Array.isArray(b) && a.length === b.length
      && a.every((v, i) => v === b[i])

    // ---- what production declares -------------------------------------------------------------
    const def = (typeof TYPES !== 'undefined' && TYPES) ? TYPES.erosion2 : null
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
      maskIn: !!findIn('mask'),
      // A POSITIVE claim, not an omission. Erosion 2 must NOT declare precipitation: `erosion2Field`
      // hands the pipe/droplet kernels no rain term at all (src/legacy.js:3086-3089), and a port
      // nothing consumes is exactly the declared-but-never-filled half-gate this sprint keeps
      // finding. Hydraulic declares one and says in its own ledger that it is not consumed; this
      // node reaches the same kernels through a composition and would be declaring it twice over.
      noPrecipIn: findIn('precipitation') === null,
      // ...and it must NOT declare the `sediment` TRANSPORT port hydraulic publishes. That port means
      // "what THIS PASS put down", and this node has no per-stage books — publishing one would be the
      // published rise wearing a transport label the composition cannot support.
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
    // Each control replaces TYPES.erosion2.eval in the LIVE registry with a wrapper around the real
    // evaluator and perturbs what production HANDS BACK — its output rasters and the ledger object it
    // publishes on the typed return. None of them writes to a variable this file later reads as its
    // own answer; every measurement is taken from production's return value after the wrapper has
    // run, exactly as a downstream reader would see it. (House precedent:
    // _verify_streampower_coevolution.js and _verify_thermal_coevolution.js both wrap the registry
    // eval.)
    const realEval = def ? def.eval : null
    out.mutationApplied = { requested: mutation || null, registryMoved: false }
    if (mutation && def && typeof realEval === 'function') {
      def.eval = (p, ins, nd, ctx) => {
        const raw = realEval(p, ins, nd, ctx)
        if (!raw || !(raw.values instanceof Map)) return raw     // undemanded call: nothing to perturb
        const vals = raw.values
        const led = raw.ledger || null
        const sSoil = slotOf('soilDepth'), sSed = slotOf('sedimentDepth'), sMask = slotOf('mask')
        const soilIn = sSoil >= 0 ? ins[sSoil] : null
        const sedIn = sSed >= 0 ? ins[sSed] : null
        const N = (ins[0] && ins[0].length) || 0
        const relief = (led && Number.isFinite(led.reliefHeightM)) ? led.reliefHeightM : 1
        const area = (led && Number.isFinite(led.cellAreaM2)) ? led.cellAreaM2 : 1
        const composed = (led && Array.isArray(led.composedBy)) ? led.composedBy : []

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
          // A kernel that reaches for bedrock first: the loose cover comes back untouched where the
          // surface fell and the volume the pass removed is charged to bedrock instead. This is the
          // shape of the pre-S3.5 build, where erosion lowered height with no cover layer to consume
          // at all. The DEPOSIT side is left alone, so the cover rasters and the cover book stay
          // mutually consistent and only the cover-first family sees it — which is the point of
          // arming that family with three fixtures.
          const h = vals.get(primaryId), before = ins[0]
          const se = vals.get('sedimentDepth')
          if (h && before && se && soilIn && sedIn && se.length === N) {
            const so2 = Float32Array.from(soilIn), se2 = Float32Array.from(sedIn)
            for (let i = 0; i < N; i++) {
              const dM = (h[i] - before[i]) * relief
              if (dM > 0) se2[i] = Math.fround(sedIn[i] + dM)
            }
            vals.set('soilDepth', so2); vals.set('sedimentDepth', se2)
            if (led) {
              led.bedrockDetachedM3 = (led.bedrockDetachedM3 || 0) + (led.coverConsumedM3 || 0)
              led.coverConsumedM3 = 0
            }
            restack()
          }
        }
        if (mutation === 'deposition-discarded') {
          // THE STREAM POWER SHAPE, WRONGLY APPLIED. The rise is carried through untouched and the
          // node declares itself detachment-limited — which is true of Stream Power and false here,
          // because this composition's pipe/droplet stage carries a deposit term (src/legacy.js:3084)
          // and its shape stage is a thermal relaxation (:3100-3105). Staged COHERENTLY: the raster
          // stops rising, depositedM3 follows it to zero, bedrock is restacked, so the stack identity
          // still closes and only the deposition reading breaks.
          const se = vals.get('sedimentDepth'), h = vals.get(primaryId), before = ins[0]
          if (se && h && before && se.length === N) {
            const m = new Float32Array(N)
            for (let i = 0; i < N; i++) {
              const dM = (h[i] - before[i]) * relief
              m[i] = dM > 0 ? (sedIn ? sedIn[i] : 0) : se[i]
            }
            vals.set('sedimentDepth', m)
            if (led) { led.depositedM3 = 0; led.depositionModelled = false; led.maxCoverRiseM = 0 }
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
        if (mutation === 'cover-alters-published-height' && soilIn) {
          // WIRING COVER MOVES THE TERRAIN. D21 authorises a STATED re-bless for this node, and this
          // is the shape of one taken without saying so: the same graph erodes differently the moment
          // a soil field is attached, so every downstream digest, thumbnail and saved document changes
          // and nothing announces it. The perturbation is applied only where cover exists, so the
          // UNWIRED evaluation below — the pre-S3.5 call shape, two slots and no state demand — comes
          // back untouched and the two stop matching.
          const h = vals.get(primaryId)
          if (h && h.length === soilIn.length) {
            const m = Float32Array.from(h)
            for (let i = 0; i < m.length; i++) if (soilIn[i] > 0) m[i] = Math.fround(m[i] * 1.000001)
            vals.set(primaryId, m)
          }
        }
        if (mutation === 'claims-derived-export-closure' && led) {
          // THE DEFECT THIS SUITE KEEPS FINDING, in the one place this node could plausibly hide it.
          // A NODE-LEVEL boundary budget appears — and its value is `coverConsumed + bedrockDetached
          // - deposited`, a restatement of the three terms it would then be checked against. The
          // closure now holds EXACTLY, for any implementation, including one that deletes the
          // terrain. Nothing about the rasters changes, so only the itemisation gate can see it,
          // which is precisely why the refusal is asserted rather than merely printed.
          delete led.lossClaimed
          led.exportedOrSuspendedM3 = (led.coverConsumedM3 || 0) + (led.bedrockDetachedM3 || 0)
            - (led.depositedM3 || 0)
          led.boundaryExportedM3 = led.exportedOrSuspendedM3
          led.suspendedM3 = 0
          led.lossSource = 'detached-volume-is-exported'
          led.boundaryPolicy = 'open-composition'
        }
        if (mutation === 'claims-stage-resolved-deposition' && led) {
          // The deposit claims to have been CARRIED OUT OF THE STAGES rather than re-derived from the
          // final height — which is what sprint-03:188 asks for and what `erosion2Field` cannot
          // supply, since it returns one Float32Array (src/legacy.js:3113) and accumulates nothing.
          // No number moves; only the claim about where the number came from.
          led.depositionStageResolved = true
          led.depositionSource = 'stage-carried'
        }
        if (mutation === 'hides-manufactured-rise' && led) {
          // The two stages that raise the surface without transporting anything stop being named, so
          // `depositedM3` reads as clean transported volume. Nothing numeric changes — which is
          // exactly why this needs its own gate rather than riding on the closure.
          led.manufacturedRiseStages = []
        }
        if (mutation === 'stage-census-hides-the-resample' && led && Array.isArray(led.composedBy)) {
          // The composition under-reports itself: the feature-scale resample drops out of the census.
          // That census is what removes the stage budget claim, so a node that forgot a stage would
          // start publishing a budget for a field four stages away from the one it describes.
          led.composedBy = led.composedBy.filter(s => s !== 'erosion-scale-resample')
        }
        if (mutation === 'claims-stage-budget-under-mask' && led && sMask >= 0 && ins[sMask]) {
          // A stage boundary budget published for a field the kernel did not produce. The mask blended
          // the result toward the input, so the solver's transfer no longer describes what is
          // published — and this asserts it anyway.
          delete led.stageBudgetClaimed
          led.stageBoundaryExportedM3 = Math.abs(led.coverConsumedM3 || 0) * 0.017
          led.stageSuspendedM3 = 0
          led.stageBrushClipGainM3 = 0
          led.stageBudgetEngine = 'droplets'
          led.stageBudgetScope = 'sole-hydraulic-stage-over-the-seeded-field'
          led.stageBudgetSource = 'droplet-particle-counters'
        }
        if (mutation === 'claims-stage-budget-under-composition' && led && composed.length
            && !(sMask >= 0 && ins[sMask])) {
          // ...and the same claim on the SHIPPED DEFAULTS, where a feature-scale resample, a nested
          // second pass, a thermal blend and a sharpening stage all stand between the last solver and
          // the published field. `hydroMassDiag` is last-run-wins on a coarse sub-grid there, so the
          // figure describes neither this node's grid nor its whole transport.
          delete led.stageBudgetClaimed
          led.stageBoundaryExportedM3 = Math.abs(led.bedrockDetachedM3 || 0) * 0.023 + 1
          led.stageSuspendedM3 = 0
          led.stageBrushClipGainM3 = 0
          led.stageBudgetEngine = 'droplets'
          led.stageBudgetScope = 'sole-hydraulic-stage-over-the-seeded-field'
          led.stageBudgetSource = 'droplet-particle-counters'
        }
        if (mutation === 'stage-budget-derived-from-the-cover-book' && led
            && typeof led.stageBoundaryExportedM3 === 'number') {
          // The stage budget keeps its honest NAME and loses its honest SOURCE: the figure becomes
          // `coverConsumed + bedrockDetached - deposited`, the same closure-for-free substitution the
          // node refuses at node level, smuggled in behind a claim that is legitimate on this path.
          led.stageBoundaryExportedM3 = (led.coverConsumedM3 || 0) + (led.bedrockDetachedM3 || 0)
            - (led.depositedM3 || 0)
          led.stageSuspendedM3 = 0
          led.stageBrushClipGainM3 = 0
        }
        if (mutation === 'square-area-on-hex' && terrainDef.lattice === 'hex' && led) {
          // The hex ledger integrates depth with the SQUARE cell area over a square row count.
          // Every reported volume is then 1/(sqrt(3)/2) = 1.1547x too large, and stops matching the
          // raster integral this file computes with the true hex area over fieldH() rows.
          const s = SCALE_M / RES_FIX, f = 1 / SQRT3_2
          led.cellAreaM2 = s * s
          led.rows = RES_FIX
          for (const k of ['coverConsumedM3', 'bedrockDetachedM3', 'depositedM3',
            'stageBoundaryExportedM3', 'stageSuspendedM3', 'stageBrushClipGainM3']) {
            if (typeof led[k] === 'number') led[k] *= f
          }
        }
        return raw
      }
      out.mutationApplied.registryMoved = TYPES.erosion2.eval !== realEval
    }

    // ---- fixtures ------------------------------------------------------------------------------
    // A ramp that descends monotonically in +x, with a corrugation that depends ONLY ON y. Both
    // properties are load-bearing and neither is a taste:
    //   monotone in x   -> a consistent downhill direction, so droplets and pipe flow both organise
    //                      and a share of them LEAVE the grid at the +x edge. That is what makes the
    //                      droplet solver's `exported` counter non-zero and the stage budget a
    //                      reading rather than a printed zero.
    //   corrugated in y -> flow concentrates in the grooves, so erosion is differential and the pass
    //                      both cuts and aggrades. Without it the fixture would exercise the
    //                      accounting on a plane.
    // The rim is deliberately NOT forced to a base level: this node has no rim condition of its own
    // (unlike streamPowerErode, which zeroes the edge at src/legacy.js:2198), so pinning one here
    // would be inventing a boundary the kernel does not have.
    const AMP = 0.05
    const makeBase = (W, H) => {
      const f = new Float32Array(W * H)
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        f[y * W + x] = 0.55 - 0.30 * (x / (W - 1)) + AMP * Math.sin(y * 0.9)
      }
      return f
    }
    // COVER DEPTH. Unlike Stream Power, this node has no analytic bound on how far one pass can cut:
    // a droplet path can dig well below its starting elevation and the composition runs up to two
    // hydraulic passes. So DEEP is set to the whole relief plus 5% — deeper than any single pass can
    // reach on a fixture whose total relief is HEIGHT_M — and the reasoning is NOT trusted:
    // `deepFixtureCoverNeverExhausted` MEASURES minCoverAfter > 0 and the headroom is printed as
    // maxLoweringM against it on every run.
    const DEEP_M = Math.ceil(HEIGHT_M * 1.05)
    const makeCover = (kind, W, H) => {
      const soil = new Float32Array(W * H)
      if (kind === 'deep') soil.fill(DEEP_M)
      else if (kind === 'mixed') {
        for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (x < W / 2) soil[y * W + x] = DEEP_M
      }
      return { soil, sed: new Float32Array(W * H) }   // 'bare' leaves both at zero
    }

    // TWO REGIMES, and the second is not a convenience — it is the only configuration in which the
    // composition reduces to a single hydraulic stage, and therefore the only one where a solver
    // boundary budget describes the grid this node publishes on.
    //   defaults        the node exactly as it reaches an author. All four composition stages run:
    //                   erosionScale .38 -> featureScale 3.28 (resample), shapeDetail .72 (nested
    //                   pass), shape .28 (thermal blend), shapeSharp .42 (sharpen).
    //   bareComposition Erosion scale 0, Shape detail 0, Shape 0, Shape sharpness 0 — every one a
    //                   legal slider position, none invented. `composedBy` must come back EMPTY.
    const COMMON = { duration: .46, downcut: .58, seed: 17, suspended: .36, bed: .30, coarse: .22,
      depositBoost: .18 }
    const REGIMES = {
      defaults: { ...COMMON, erosionScale: .38, shape: .28, shapeSharp: .42, shapeDetail: .72 },
      bareComposition: { ...COMMON, erosionScale: 0, shape: 0, shapeSharp: 0, shapeDetail: 0 },
    }
    // The stage census this file predicts INDEPENDENTLY, from the source's own predicates rather than
    // from the ledger it is grading. tier is 1 on both build qualities at RES 64
    // (`BUILD_QUALITY==="final"?1:Math.max(1,RES/384)`, src/legacy.js:3080, and 64/384 < 1), and
    // featureScale is `lerp(1,7,erosionScale)` (:3072) tested against `k>1.02` (:1517).
    const censusFor = (params, masked) => {
      const c = []
      if (1 + 6 * params.erosionScale > 1.02) c.push('erosion-scale-resample')
      if (params.shapeDetail > 0.02) c.push('nested-detail-pass')
      if (params.shape > 0.01) c.push('shape-thermal-blend')
      if (params.shapeSharp > 0.01) c.push('shape-sharpen')
      if (masked) c.push('mask-composite')
      return c
    }
    const manufacturedFor = params => params.shapeSharp > 0.01
      ? ['seed-perturbation', 'shape-sharpen'] : ['seed-perturbation']

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

    const runOne = (lattice, fixture, masked, regime, useGpu) => {
      const params = REGIMES[regime] || REGIMES.defaults
      const r = { key: `${lattice}/${fixture}/${regime === 'bareComposition' ? 'bare' : 'def'}`
          + (masked ? '/masked' : '') + (useGpu ? '/gpu' : ''),
        lattice, fixture, masked: !!masked, regime, gpu: !!useGpu, error: null, ran: false }
      try {
        terrainDef.lattice = lattice
        terrainDef.scale = SCALE_M
        terrainDef.height = HEIGHT_M
        terrainDef.baseElevation = DATUM_M
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
        r.deepM = DEEP_M
        r.censusExpected = censusFor(params, !!masked)
        r.manufacturedExpected = manufacturedFor(params)

        const base = makeBase(W, H)
        const { soil: soil0, sed: sed0 } = makeCover(fixture, W, H)
        const mask = masked ? new Float32Array(N).fill(MASK_VALUE) : null
        // THE IDENTITY MASK. `maskApply` (src/legacy.js:461) computes base + (modified-base)*m, so at
        // m = 0 the published field IS the input, exactly, for any kernel output at all.
        const zeroMask = new Float32Array(N)
        r.coverInSum = sumD(soil0) + sumD(sed0)
        r.coverInDigest = (() => { let a = 0x811c9dc5
          for (let i = 0; i < soil0.length; i++) { a = (a ^ (Math.round(soil0[i] * 1e3) | 0)) >>> 0; a = Math.imul(a, 16777619) >>> 0 }
          return a.toString(16) })()

        const sMask = slotOf('mask'), sSoil = slotOf('soilDepth'), sSed = slotOf('sedimentDepth')
        r.slotsResolved = sMask >= 0 && sSoil >= 0 && sSed >= 0
        const width = Math.max(2, sMask + 1, sSoil + 1, sSed + 1)
        const mkIns = m => {
          const a = new Array(width).fill(null)
          a[0] = base
          if (sMask >= 0) a[sMask] = m
          if (sSoil >= 0) a[sSoil] = soil0
          if (sSed >= 0) a[sSed] = sed0
          return a
        }
        const ins = mkIns(mask), insIdentity = mkIns(zeroMask)

        const nd = { id: 9401, type: 'erosion2', params: null }
        const demanded = new Set([primaryId, 'out', 'solidTop', 'bedrockHeight',
          'soilDepth', 'sedimentDepth', 'sandDepth'])

        // --- BEFORE: the same regime under a ZERO MASK. Contractually an identity pass that echoes
        //     cover and publishes an all-zero cover ledger.
        nd.params = { ...params }
        const rawB = TYPES.erosion2.eval(nd.params, insIdentity, nd, { demanded })
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
          // Every transport term: a pass that moved nothing must say so on all of them.
          ledgerAllZero: !!ledB && ['coverConsumedM3', 'bedrockDetachedM3', 'depositedM3']
            .every(k => ledB[k] === 0),
          topFinite: topB ? finiteAll(topB) : false,
          // ...and an identity pass is a MASKED pass by construction, so it must decline the stage
          // budget and say the mask is why.
          stageBudgetDeclined: !!ledB && ledB.stageBudgetClaimed === false,
        }

        // --- AFTER: one real composition pass in this run's regime.
        nd.params = { ...params }
        const rawA = TYPES.erosion2.eval(nd.params, ins, nd, { demanded })
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

        // The pass must actually have run, and material must have gone BOTH WAYS — or the deposition
        // reading below is a claim about a fixture in which nothing rose.
        if (primA && primB) {
          let moved = 0, risen = 0, maxDrop = 0, risenIndep = 0
          for (let i = 0; i < N; i++) {
            const d = primA[i] - primB[i]
            if (d !== 0) moved++
            if (d > 0) { risen++; risenIndep += d * HEIGHT_M }
            if (-d > maxDrop) maxDrop = -d
          }
          r.samplesMoved = moved
          r.samplesRisen = risen
          r.maxLoweringM = maxDrop * HEIGHT_M
          r.risenIndepM3 = risenIndep * r.areaExpected
        }

        // --- the byte-identity control ----------------------------------------------------------
        // The SAME pass called the way the pre-S3.5 build was called: two slots, no cover attached,
        // and only the primary demanded. D21 authorises a STATED re-bless for this node, but a graph
        // that wires no cover must produce the terrain it produced yesterday, byte for byte, and that
        // has to be MEASURED rather than argued from the fact that the digest recipe happens not to
        // demand a state port. It is also this file's determinism reading: two independent
        // evaluations of a seeded stochastic solver with the same parameters must agree bit for bit.
        const rawU = TYPES.erosion2.eval(nd.params, [ins[0], mask], nd, { demanded: new Set([primaryId]) })
        const primU = grab(readValues(rawU), primaryId)
        r.unwiredLength = primU ? primU.length : null
        r.unwiredMatchesWired = bitEqual(primU, primA)

        // --- the digest-shape control -----------------------------------------------------------
        // With NO ctx at all — which is exactly how _verify_digest.js calls every evaluator — the
        // return must still be a bare typed array, not a values Map. If it became typed, the digest
        // would start folding five extra ports for this node and the baseline would move for a reason
        // that has nothing to do with the physics.
        const rawN = TYPES.erosion2.eval(nd.params, ins, nd)
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
        if (topB && ledB && Number.isFinite(ledB.datumM) && Number.isFinite(ledB.reliefHeightM)) {
          const dat = ledB.datumM, rel = ledB.reliefHeightM
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
          r.frame = { name: typeof ledB.frame === 'string' ? ledB.frame : null, datumM: dat, reliefHeightM: rel,
            maxErrVsStableM: maxStable, maxErrVsAutolevelM: maxAuto,
            tolM: 4 * F32_ULP * (Math.abs(dat) + Math.abs(rel)) + 1e-6 }
        }

        // --- the frame-free readings -------------------------------------------------------------
        if (soilA && sedA && sandA && soilB && sedB && sandB) {
          const A = r.areaExpected
          let dCover = 0, absChange = 0, minCoverAfter = Infinity, maxCoverRise = -Infinity
          let riseCells = 0
          for (let i = 0; i < N; i++) {
            const c1 = soilA[i] + sedA[i] + sandA[i]
            const c0 = soilB[i] + sedB[i] + sandB[i]
            dCover += A * (c1 - c0)
            absChange += A * Math.abs(c1 - c0)
            if (c1 < minCoverAfter) minCoverAfter = c1
            if (c1 - c0 > maxCoverRise) maxCoverRise = c1 - c0
            if (c1 - c0 > 0) riseCells++
          }
          r.dCoverM3 = dCover
          r.minCoverAfter = minCoverAfter
          // MEASURED FROM THE RASTERS, not read off the ledger. This is THE reading that settles the
          // deposition question for this node: it must be strictly positive here, where Stream Power
          // is required to show exactly zero.
          r.maxCoverRiseMeasuredM = maxCoverRise
          r.coverRiseCells = riseCells
          // THE COVER BOOK'S BOUND IS A DOUBLE-REDUCTION BOUND OVER THE ABSOLUTE CHANGE. Production
          // accumulates `(a0-a1)+(d0-d1)+(s0-s1)` and `d1-d0` in double FROM THE PUBLISHED FLOAT32
          // RASTER VALUES (src/plugins/ero/erosion2.js), and this file accumulates `c1-c0` in double
          // from those same values, so the float32 rounding is COMMON to both sides and cancels term
          // by term; the only residual is the reduction ordering, which is double. Summing |c1|+|c0|
          // instead would make the tolerance a function of how much cover is STANDING — on the deep
          // fixture that is DEEP_M over every cell — so the bound would grow with the fixture rather
          // than with what the pass moved. That is the defect S3.5b measured at 1e9x too loose, and
          // both endpoints are re-measured below rather than argued from its notes.
          r.coverBookBound = boundF64(N, absChange)
          let absStanding = 0
          for (let i = 0; i < N; i++) {
            absStanding += A * (Math.abs(soilA[i] + sedA[i] + sandA[i])
              + Math.abs(soilB[i] + sedB[i] + sandB[i]))
          }
          r.coverBookBoundLoose = boundF32(N, absStanding)
          if (led) {
            r.coverBookErr = Math.abs(dCover - ((led.depositedM3 || 0) - (led.coverConsumedM3 || 0)))
            r.coverBookCloses = r.coverBookErr <= r.coverBookBound
            const transported = Math.abs(led.coverConsumedM3 || 0) + Math.abs(led.bedrockDetachedM3 || 0)
              + Math.abs(led.depositedM3 || 0)
            r.transportedM3 = transported
            r.coverBookArming = r.coverBookBound > 0 ? transported / r.coverBookBound : 0
            r.coverBookArmingLoose = r.coverBookBoundLoose > 0 ? transported / r.coverBookBoundLoose : 0
          }
        }

        // --- the ledger read exactly as published -------------------------------------------------
        if (led) {
          const has = k => Object.prototype.hasOwnProperty.call(led, k)
          r.areaReportedOk = Math.abs((led.cellAreaM2 || 0) - r.areaExpected) <= 1e-9 * r.areaExpected
          r.ledgerLatticeOk = led.lattice === lattice
          r.ledgerRowsOk = led.rows === r.rowsExpected
          r.census = Array.isArray(led.composedBy) ? led.composedBy.slice() : null
          r.censusMatches = sameList(r.census, r.censusExpected)
          r.manufactured = Array.isArray(led.manufacturedRiseStages) ? led.manufacturedRiseStages.slice() : null
          r.manufacturedMatches = sameList(r.manufactured, r.manufacturedExpected)
          r.deposition = {
            modelled: led.depositionModelled === true,
            stageResolved: led.depositionStageResolved !== false,
            source: typeof led.depositionSource === 'string' ? led.depositionSource : null,
            depositedM3: has('depositedM3') ? led.depositedM3 : null,
            maxCoverRiseM: has('maxCoverRiseM') ? led.maxCoverRiseM : null,
          }
          // The NODE-level boundary claim, which must be absent on every path.
          r.loss = {
            claimed: led.lossClaimed !== false,
            source: typeof led.lossSource === 'string' ? led.lossSource : null,
            policy: typeof led.boundaryPolicy === 'string' ? led.boundaryPolicy : null,
            exported: has('exportedOrSuspendedM3') ? led.exportedOrSuspendedM3 : null,
            boundaryExported: has('boundaryExportedM3') ? led.boundaryExportedM3 : null,
            suspended: has('suspendedM3') ? led.suspendedM3 : null,
          }
          // The STAGE-level claim, which is present on the bare composition and absent everywhere else.
          r.stage = {
            claimed: led.stageBudgetClaimed !== false,
            source: typeof led.stageBudgetSource === 'string' ? led.stageBudgetSource : null,
            engine: typeof led.stageBudgetEngine === 'string' ? led.stageBudgetEngine : null,
            scope: typeof led.stageBudgetScope === 'string' ? led.stageBudgetScope : null,
            exportedM3: has('stageBoundaryExportedM3') ? led.stageBoundaryExportedM3 : null,
            suspendedM3: has('stageSuspendedM3') ? led.stageSuspendedM3 : null,
            gainM3: has('stageBrushClipGainM3') ? led.stageBrushClipGainM3 : null,
          }
          // ...AND THE CLAIMED FIGURE IS NOT A RESTATEMENT OF THE COVER BOOK. Every combination a
          // derived implementation would reach for is formed here and the DISTANCE to the published
          // stage figure is measured, relative to the transport. A solver counter accumulated over a
          // particle set or an apron ring has no reason to land on any of them; a derived one lands
          // on exactly one, to the last bit.
          if (typeof r.stage.exportedM3 === 'number' && Number.isFinite(r.transportedM3)) {
            const cons = led.coverConsumedM3 || 0, det = led.bedrockDetachedM3 || 0, dep = led.depositedM3 || 0
            const candidates = [cons, det, dep, cons + det, cons + det - dep, cons - dep, det - dep]
            const scale = Math.max(Math.abs(r.transportedM3), 1e-9)
            r.stageDerivedDistance = Math.min(...candidates.map(v => Math.abs(v - r.stage.exportedM3) / scale))
          }
          r.slotsReported = led.soilSlot === sSoil && led.sedimentSlot === sSed
            && led.maskSlot === sMask && led.soilWired === true && led.sedimentWired === true
        }
      } catch (e) {
        r.error = String((e && e.message) || e)
      }
      return r
    }

    const plan = []
    // The shipped defaults, on both lattices and all three cover fixtures: the composition at full
    // depth, where every stage claim must be declined.
    for (const fx of ['deep', 'bare', 'mixed']) {
      plan.push(['square', fx, false, 'defaults', false])
      plan.push(['hex', fx, false, 'defaults', false])
    }
    // The bare composition, same corpus: the one regime where a solver budget describes the published
    // grid, so this is where the stage claim has to appear.
    for (const fx of ['deep', 'bare', 'mixed']) {
      plan.push(['square', fx, false, 'bareComposition', false])
      plan.push(['hex', fx, false, 'bareComposition', false])
    }
    // The masked bare composition — the ONLY place `claims-stage-budget-under-mask` can bite, and the
    // reason a masked fixture is run at all.
    plan.push(['square', 'mixed', true, 'bareComposition', false])
    plan.push(['hex', 'mixed', true, 'bareComposition', false])
    // The GPU kernel. `erosion2Field` picks `gpuHydraulicPipes` over `hydraulicErode` at
    // src/legacy.js:3086-3089, so this node — unlike Stream Power — genuinely has two engines, and
    // the ledger's `stageBudgetEngine` is what proves which one ran rather than assuming the switch
    // took. Square only: gpuReady() is false on hex by construction.
    plan.push(['square', 'mixed', false, 'bareComposition', true])
    for (const [lat, fx, masked, reg, gpu] of plan) out.runs.push(runOne(lat, fx, masked, reg, gpu))

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
      const nd = { id: 9402, type: 'erosion2', params: { ...REGIMES.bareComposition } }
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
      try { TYPES.erosion2.eval(nd.params, mk(a => { a[13] = NaN }), nd, { demanded }) }
      catch (e) { out.rejects.nonFinite = /non-negative depth/.test(String(e && e.message)) }
      try { TYPES.erosion2.eval(nd.params, mk(a => { a[13] = -1 }), nd, { demanded }) }
      catch (e) { out.rejects.negative = /non-negative depth/.test(String(e && e.message)) }
      // ...and a clean wired cover still evaluates, so the two above are a refusal of BAD DATA and
      // not a node that refuses cover altogether.
      const okRaw = TYPES.erosion2.eval(nd.params, mk(null), nd, { demanded })
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
    // field has a different row count, so a single set over every run holds 3 fixtures x 2 lattices
    // and asserting 3 there would be measuring the wrong thing — the mistake found in thermal's own
    // corpus guard. What the corpus has to prove is that the three cover configurations genuinely
    // differ ON EACH LATTICE.
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
  const bare = runs.filter(r => r.regime === 'bareComposition' && !r.masked)
  const composed = runs.filter(r => r.regime === 'defaults')
  const byFixture = fx => unmasked.filter(r => r.fixture === fx)
  const every = (list, fn) => list.length > 0 && list.every(fn)
  const num = v => (typeof v === 'number' && Number.isFinite(v)) ? v : null
  const fmt = v => (num(v) === null ? 'n/a' : (Math.abs(v) >= 1e4 ? v.toExponential(3) : +v.toFixed(6)))

  const deepF = byFixture('deep'), bareF = byFixture('bare'), mixedF = byFixture('mixed')
  const ledNum = (r, k) => (r.ledger && typeof r.ledger[k] === 'number') ? r.ledger[k] : null

  const gates = {
    // --- the declared surface ------------------------------------------------------------------
    coverInputPortsDeclared: report.ports.soilIn === true && report.ports.sedIn === true
      && report.ports.maskIn === true && report.ports.noPrecipIn === true
      && report.ports.insLabels.join('|') === 'In|Mask|Soil depth|Sediment depth',
    stateOutputPortsDeclared: report.ports.solidTopOut === true && report.ports.bedrockOut === true
      && report.ports.soilOut === true && report.ports.sedOut === true && report.ports.sandOut === true
      && report.ports.noTransportSedimentOut === true,

    // --- the identity pass, which is also how BEFORE is measured ---------------------------------
    // A ZERO MASK, because this node has no slider setting that transports nothing — see the header.
    zeroMaskIsAnIdentityPassAndEchoesCover: every(runs, r => r.before && r.before.hasState === true
      && r.before.echoesSoil === true && r.before.echoesSed === true && r.before.sandZero === true
      && r.before.heightUnmoved === true && r.before.lengthsOk === true
      && r.before.ledgerAllZero === true && r.before.topFinite === true
      && r.before.stageBudgetDeclined === true),

    // --- the pass actually ran, and material went BOTH WAYS ---------------------------------------
    // A PRECONDITION for everything below, and deliberately unarmed by any mutation.
    compositionTransportedMaterial: every(runs, r => num(r.samplesMoved) !== null && r.samplesMoved > 0
      && num(r.transportedM3) !== null && r.transportedM3 > 0),

    // --- COVER BEFORE BEDROCK, armed by three fixtures --------------------------------------------
    // 1) the deep fixture must actually consume cover, or the next gate is about nothing;
    coverIsConsumedOnDeepFixture: every(deepF, r => num(ledNum(r, 'coverConsumedM3')) !== null
      && ledNum(r, 'coverConsumedM3') > 0),
    // 2) and cover must never have reached zero anywhere, or "bedrock untouched" is unarmed. The
    //    measured headroom is printed as maxLoweringM against the fixture's DEEP.
    deepFixtureCoverNeverExhausted: every(deepF, r => num(r.minCoverAfter) !== null && r.minCoverAfter > 0
      && num(r.maxLoweringM) !== null && num(r.deepM) !== null && r.maxLoweringM < r.deepM),
    // 3) THE STORY'S NAMED RED. Bedrock is not cut while local loose cover remains.
    bedrockUntouchedWhileCoverRemains: every(deepF, r => ledNum(r, 'bedrockDetachedM3') === 0),
    // 4) and the kernel must be CAPABLE of cutting bedrock, or (3) passes by refusing to move.
    bareBedrockDoesErode: every(bareF, r => num(ledNum(r, 'bedrockDetachedM3')) !== null
      && ledNum(r, 'bedrockDetachedM3') > 0 && ledNum(r, 'coverConsumedM3') === 0),
    // 5) the mixed slope exercises the boundary between the two regimes in one pass.
    mixedFixtureCutsBothLayers: every(mixedF, r => num(ledNum(r, 'coverConsumedM3')) !== null
      && ledNum(r, 'coverConsumedM3') > 0 && num(ledNum(r, 'bedrockDetachedM3')) !== null
      && ledNum(r, 'bedrockDetachedM3') > 0),

    // --- THIS NODE DEPOSITS, AND IT IS READ OFF THE RASTERS ---------------------------------------
    // The measurement that settles the physics question the brief refused to assume. Stream Power is
    // required to show maxCoverRise EXACTLY ZERO; this node is required to show it STRICTLY POSITIVE
    // over a substantial share of the field, because its pipe/droplet stage carries a deposit term
    // (src/legacy.js:3084) and its shape stage is a thermal relaxation (:3100-3105). Three
    // independent readings, all of which a non-depositing build breaks: the published flag, the
    // ledger's own measured maximum rise, and this file's measurement of the same quantity from the
    // soil/sediment/sand rasters. Armed by `deposition-discarded`.
    erosion2DepositsAndTheRiseIsMeasuredInTheRasters: every(runs, r => r.deposition
      && r.deposition.modelled === true
      && num(r.deposition.depositedM3) !== null && r.deposition.depositedM3 > 0
      && num(r.deposition.maxCoverRiseM) !== null && r.deposition.maxCoverRiseM > 0
      && num(r.maxCoverRiseMeasuredM) !== null && r.maxCoverRiseMeasuredM > 0
      && num(r.coverRiseCells) !== null && r.coverRiseCells >= 0.02 * r.N),
    // ...and the deposit does NOT claim to be carried out of the stages. sprint-03:188 asks for that
    // and `erosion2Field` cannot supply it: it returns one Float32Array (src/legacy.js:3113) and
    // accumulates nothing. Armed by `claims-stage-resolved-deposition`.
    depositIsDeclaredNotStageResolved: every(runs, r => r.deposition
      && r.deposition.stageResolved === false
      && r.deposition.source === 'published-delta-not-stage-resolved'),
    // ...and the stages that raise the surface WITHOUT transporting anything are named, so the
    // contamination inside `depositedM3` is a fact rather than a caveat. The list is DISCRIMINATING
    // across regimes — `seed-perturbation` on every run because :3068-3070 is unconditional, plus
    // `shape-sharpen` exactly where the slider is above :3106's threshold — so a build that hardcoded
    // one answer fails on the other regime. Armed by `hides-manufactured-rise`.
    manufacturedRiseStagesAreNamed: every(runs, r => r.manufacturedMatches === true
      && Array.isArray(r.manufactured) && r.manufactured.includes('seed-perturbation'))
      && runs.some(r => (r.manufactured || []).length === 2)
      && runs.some(r => (r.manufactured || []).length === 1),

    // --- the stage census, predicted here and graded there -----------------------------------------
    // Recomputed in this file from the source's own predicates, never read back. It is what removes
    // the stage budget claim, so a census that under-reports is a budget published for a field it does
    // not describe. Armed by `stage-census-hides-the-resample`.
    stageCensusMatchesTheSourcePredicates: every(runs, r => r.censusMatches === true)
      && every(bare, r => Array.isArray(r.census) && r.census.length === 0)
      && every(composed, r => Array.isArray(r.census) && r.census.length === 4),

    // --- conservation, entirely in frame-free thicknesses and volumes ------------------------------
    coverBookCloses: every(runs, r => r.coverBookCloses === true),
    // THE BOUND IS SMALLER THAN THE TERM IT CONSTRAINS, measured on every run rather than argued
    // once. WHAT IT SCALES WITH: the absolute per-cell cover CHANGE — the thickness this pass
    // actually moved — never a sum of standing thicknesses, which would make the tolerance a
    // function of how deep the fixture's cover is. The threshold sits at 1e6: far above anything a
    // terrain-scaled bound can reach and far below the arithmetic ceiling (boundF64 is 2*gamma64(2N)
    // relative, ~1.8e-12 at N ~ 4e3, so the ratio cannot exceed ~5.5e11 however tight the
    // implementation), so a silent loosening of four orders is caught rather than merely absent.
    // `ledger-consumption-inflated` moves 3%, which needs only ~33 and is therefore certain to bite.
    coverBookBoundIsSmallerThanTheTransport: every(runs, r => num(r.coverBookArming) !== null
      && r.coverBookArming > 1e6),
    // ...and the OTHER endpoint, so the arming is a delta measured live rather than a claim about a
    // draft nobody can re-run. On the fixtures that carry standing cover, the rejected bound must
    // still fail the threshold the corrected one passes. Restricted to `deep`, `mixed` and the masked
    // runs because `bare` has no standing cover for a terrain-scaled bound to grow with — on that
    // fixture the two bounds legitimately coincide at their 1e-6/1e-9 floors and the comparison would
    // be about nothing, which is the sort of vacuous term this gate exists to avoid.
    theLooseCoverBookBoundIsDemonstrablyTooLoose: every(deepF.concat(mixedF).concat(masked),
      r => num(r.coverBookArmingLoose) !== null && r.coverBookArmingLoose < 1e6
        && num(r.coverBookArming) !== null && r.coverBookArming > 1e6),

    // --- the NODE boundary budget, refused on every path and for a stated reason ---------------------
    // The reason is not the rim: the fbm injection at src/legacy.js:3068-3070 is unconditional, so
    // even with every transform off the solvers budget a field the node did not receive. The only
    // figure the node could print is a restatement of the terms it would be compared against. Armed by
    // `claims-derived-export-closure`.
    nodeBoundaryBudgetIsNeverClaimedAndNamesWhy: every(runs, r => !!r.loss && r.loss.claimed === false
      && r.loss.source === 'seed-injection-and-stage-composition-not-itemised'
      && r.loss.policy === null && r.loss.exported === null && r.loss.boundaryExported === null
      && r.loss.suspended === null),

    // --- the STAGE budget: claimed exactly where it describes something ------------------------------
    // The bare composition is one hydraulic pass on the native grid, so the solver's own counters
    // describe the grid this node publishes on. Both engines itemise over a set the published field
    // does not control (apron ring / particle counters). A PRECONDITION for the two refusals below —
    // without it they would be refusals of a claim nobody ever makes.
    bareCompositionPublishesTheStageBudget: every(bare, r => !!r.stage && r.stage.claimed === true
      && r.stage.scope === 'sole-hydraulic-stage-over-the-seeded-field'
      && (r.stage.source === 'droplet-particle-counters' || r.stage.source === 'pipe-apron-ring')
      && num(r.stage.exportedM3) !== null && num(r.stage.suspendedM3) !== null
      && num(r.stage.gainM3) !== null),
    // ...and it carries a real transfer rather than a printed zero, or the refusals below would be
    // refusals of nothing. The fixture descends monotonically in +x precisely so that material
    // reaches the boundary.
    stageBudgetIsANonZeroTransfer: every(bare, r => num(r.stage && r.stage.exportedM3) !== null
      && Math.abs(r.stage.exportedM3) > 0),
    // ...and it is NOT a restatement of the cover book. Every combination a derived implementation
    // would reach for is formed in the probe and the smallest relative distance to the published
    // figure is measured. A derived figure lands on one of them EXACTLY, so the mutation drives this
    // distance to 0 and the gate bites with certainty.
    //
    // THE THRESHOLD CANNOT BE RAISED, AND THE MEASUREMENT IS WHY. On the droplet runs the honest
    // counter sits 2.3e-3 .. 2.9e-3 away from the nearest derived combination; on the PIPE run it
    // sits 4.0e-5 away — `coverConsumed + bedrockDetached - deposited` is 1.200e6 m3 against an apron
    // transfer of 1.183e6 m3. That near-agreement is not the code cheating, it is the physics
    // corroborating itself: on an untransformed single-stage pass the cover book's residual IS the
    // material that left, and the apron ring measures the same quantity over a disjoint cell set.
    // So 4.0e-5 is the ceiling a CORRECT implementation may reach, the threshold sits at 1e-6 to keep
    // 40x of clearance under it, and raising it would turn a physical agreement into a false red.
    // Armed by `stage-budget-derived-from-the-cover-book`.
    stageBudgetIsNotARestatementOfTheCoverBook: every(bare, r => num(r.stageDerivedDistance) !== null
      && r.stageDerivedDistance > 1e-6),
    // TRANSFORMED BY A MASK: the published field is a blend toward the input, so the solver's transfer
    // no longer describes it. The node must claim NOTHING and say which transform removed the claim.
    // Armed by `claims-stage-budget-under-mask`.
    maskedPathPublishesNoStageBudget: every(masked, r => !!r.stage && r.stage.claimed === false
      && r.stage.source === 'mask-composite' && r.stage.exportedM3 === null
      && r.stage.suspendedM3 === null && r.stage.gainM3 === null && r.stage.engine === null),
    // TRANSFORMED BY THE COMPOSITION: at the shipped defaults four stages stand between the last
    // solver and the published field, and `hydroMassDiag` is last-run-wins on a coarse sub-grid.
    // Armed by `claims-stage-budget-under-composition`.
    composedPathPublishesNoStageBudget: every(composed, r => !!r.stage && r.stage.claimed === false
      && r.stage.source === 'erosion-scale-resample+nested-detail-pass+shape-thermal-blend+shape-sharpen'
      && r.stage.exportedM3 === null && r.stage.engine === null),
    // BOTH ENGINES MEASURED. This node has a GPU kernel where Stream Power has none, and the ledger's
    // engine name is what proves the switch actually took rather than silently falling back — a GPU
    // run that quietly ran the CPU kernel would otherwise read as coverage.
    bothEnginesMeasured: bare.some(r => r.stage && r.stage.engine === 'droplets' && r.ran === true)
      && bare.some(r => r.stage && r.stage.engine === 'pipes' && r.ran === true),

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
    // erodibility law, which nobody has specified and which would be a fabricated constant. So the
    // published height with cover attached must be the published height without it, bit for bit, and
    // D21's re-bless stays unspent. This is also the determinism reading for a seeded stochastic
    // solver: two independent evaluations with the same parameters must agree exactly. Armed by
    // `cover-alters-published-height`.
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
    // evaluator never reads would look exactly like a working port. The numbers are this row's own:
    // Erosion 2's frozen row is In/Mask, so cover lands at 2 and 3 — thermal's numbers, not Stream
    // Power's 3 and 4.
    coverSlotsAreDeclaredAndFilled: every(runs, r => r.slotsResolved === true && r.slotsReported === true)
      && report.ports.slots.mask === 1 && report.ports.slots.soil === 2 && report.ports.slots.sed === 3,

    // --- a wired cover raster that is not a depth is refused by name ---------------------------------
    badCoverRasterIsRefusedNotHalfRead: report.rejects.nonFinite === true
      && report.rejects.negative === true && report.rejects.cleanStillEvaluates === true,

    // --- absence of evidence is a failure -------------------------------------------------------------
    bothRegimesMeasured: runs.some(r => r.regime === 'defaults' && r.ran === true)
      && runs.some(r => r.regime === 'bareComposition' && r.ran === true),
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

  console.log('== S3.5 cover-aware DEPOSITING multi-scale composition (Erosion 2) ==')
  console.log(`ins=[${report.ports.insLabels.join(',')}] in=[${report.ports.declaredInputIds.join(',')}] `
    + `out=[${report.ports.declaredOutputIds.join(',')}] slots=${JSON.stringify(report.ports.slots)}`)
  for (const r of runs) {
    console.log(`  ${r.key.padEnd(26)} W=${r.W} H=${r.H} deepM=${r.deepM} moved=${r.samplesMoved} risen=${r.samplesRisen} `
      + `maxLoweringM=${fmt(r.maxLoweringM)} consumed=${fmt(ledNum(r, 'coverConsumedM3'))} `
      + `detached=${fmt(ledNum(r, 'bedrockDetachedM3'))} deposited=${fmt(ledNum(r, 'depositedM3'))} `
      + `riseCells=${r.coverRiseCells} maxCoverRise=${fmt(r.maxCoverRiseMeasuredM)} minCover=${fmt(r.minCoverAfter)} `
      + `census=[${(r.census || []).join('+') || '-'}] manufactured=[${(r.manufactured || []).join('+') || '-'}] `
      + `stageClaimed=${r.stage ? r.stage.claimed : 'n/a'} stageEngine=${(r.stage && r.stage.engine) || '-'} `
      + `stageExported=${fmt(r.stage && r.stage.exportedM3)} stageDerivedDist=${fmt(r.stageDerivedDistance)} `
      + `stageSrc=${(r.stage && r.stage.source) || '-'} lossClaimed=${r.loss ? r.loss.claimed : 'n/a'} `
      + `coverBookErr=${fmt(r.coverBookErr)} bound=${fmt(r.coverBookBound)} arming=${fmt(r.coverBookArming)} `
      + `armingLoose=${fmt(r.coverBookArmingLoose)} err=${r.error || 'none'}`)
  }
  for (const [k, v] of Object.entries(gates)) console.log(`${v ? 'PASS' : 'FAIL'}  ${k}`)

  console.log(`${ok ? 'PASS' : 'FAIL'}  erosion2 co-evolution runs=${runs.length} ledgers=${runs.filter(r => r.ledger).length} `
    + `deepBedrockDetached=[${deepF.map(r => fmt(ledNum(r, 'bedrockDetachedM3'))).join(',')}] `
    + `bareBedrockDetached=[${bareF.map(r => fmt(ledNum(r, 'bedrockDetachedM3'))).join(',')}] `
    + `maxCoverBookErr=${fmt(Math.max(0, ...runs.map(r => num(r.coverBookErr) === null ? 0 : r.coverBookErr)))} `
    + `minCoverBookArming=${fmt(Math.min(...runs.map(r => num(r.coverBookArming) === null ? 0 : r.coverBookArming)))} `
    + `maxCoverBookArmingLoose=${fmt(Math.max(0, ...deepF.concat(mixedF).concat(masked).map(r => num(r.coverBookArmingLoose) === null ? 1e99 : r.coverBookArmingLoose)))} `
    + `minCoverRise=${fmt(Math.min(...runs.map(r => num(r.maxCoverRiseMeasuredM) === null ? -1 : r.maxCoverRiseMeasuredM)))} `
    + `minCoverAfter=${fmt(Math.min(...deepF.map(r => num(r.minCoverAfter) === null ? -1 : r.minCoverAfter)))} `
    + `maxLoweringM=${fmt(Math.max(0, ...runs.map(r => num(r.maxLoweringM) === null ? 0 : r.maxLoweringM)))} `
    + `minStageDerivedDist=${fmt(Math.min(...bare.map(r => num(r.stageDerivedDistance) === null ? -1 : r.stageDerivedDistance)))} `
    + `engines=[${Array.from(new Set(bare.map(r => (r.stage && r.stage.engine) || '-'))).join(',')}] `
    + `stackViolations=${runs.reduce((a, r) => a + ((r.stackIdentity && r.stackIdentity.violations) || 0), 0)} `
    + `unwiredMatchesWired=${runs.filter(r => r.unwiredMatchesWired === true).length}/${runs.length} `
    + `frame=${(runs.find(r => r.frame) || { frame: {} }).frame.name || 'n/a'} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
