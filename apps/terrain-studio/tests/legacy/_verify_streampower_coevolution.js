// S3.5, SECOND NODE — cover-aware DETACHMENT-LIMITED fluvial incision.
//
// WHY THIS IS A NEW FILE AND NOT AN EXTENSION OF _verify_streampower.js
// --------------------------------------------------------------------
// That oracle is about the solver's NUMERICS: that a steady-state landscape reproduces the
// slope-area relation S ~ A^(-m/n) on a log-log fit, that the fit is converged rather than lucky at
// one iteration count, that the drainage network concentrates like a tree, that no cell is left
// below its receiver and that the rim is held at base level. It calls `streamPowerErode` directly,
// runs no cover fixture, and declares no mutations. This one is about the BOOKS — which layer
// supplies the material, what happens where the surface rises, and which budget lines the node may
// honestly publish. Two different corpora, and `gate.py` reads exactly one MUTATIONS allowlist per
// file, so folding them together would mean either running the numerics fixtures under cover
// mutations that cannot touch them or losing half the controls.
//
// It also leaves that oracle standing UNCHANGED as an independent witness: if this story had moved
// the kernel, it would have gone red on its own terms. It did not — nothing in src/legacy.js was
// touched, and the digest is bit-identical.
//
// ---------------------------------------------------------------------------------------------
// WHAT IS ASSERTED, AND WHY IN THIS FORM
// ---------------------------------------------------------------------------------------------
// COVER BEFORE BEDROCK IS ARMED BY THREE FIXTURES, never by one absolute comparison. A single
// "bedrock did not move" claim is satisfied for free by a kernel that never touches bedrock at all,
// so the discriminator is the TRIPLE:
//   deep  cover thick enough that one pass cannot exhaust it -> bedrockDetachedM3 must be exactly 0
//   bare  cover 0 everywhere                                 -> bedrockDetachedM3 must be > 0
//   mixed half deep, half bare                               -> both layers must be active
// A cover-first kernel scores (0, >0, both). A bedrock-first kernel scores (>0, >0, both) and dies
// on `bedrockUntouchedWhileCoverRemains` — the story's named red. A kernel that simply refuses to
// erode bedrock scores (0, 0, ...) and dies on `bareBedrockDoesErode`.
//
// DETACHMENT-LIMITED IS THE OTHER HALF OF THE STORY, and it is asserted as a MEASUREMENT, not as an
// omission. sprint-03:186 requires Stream Power to keep modelling no deposition, so the published
// `depositedM3` is a constant zero and no cell's cover thickness may rise. "No cell's cover rose" is
// worthless if nothing in the fixture rose at all, so `surfaceRoseSomewhereSoTheClaimIsArmed` is a
// precondition gate: the shipped defaults run uplift 0.35, every interior cell is lifted every
// iteration, and the run is required to SHOW risen samples before the no-deposition gate is read.
//
// THE BOUNDARY TERM, AND WHY THIS NODE PUBLISHES NONE
// --------------------------------------------------
// Thermal could publish a named physical zero: both its kernels omit off-grid neighbours, so nothing
// can leave the domain, and `consumed + detached = deposited + 0` is then a closure that fails for an
// implementation which deletes the terrain. Stream Power has the opposite boundary and cannot borrow
// that shape:
//   - the rim is FORCED to base level before the loop and after every iteration
//     (src/legacy.js:2198 and :2269, `for(let i=0;i<N;i++)if(isEdge[i])h[i]=0`), which discards
//     whatever drained into it;
//   - the implicit incision step `h[i]=(h[i]+C*h[rec[i]])/(1+C)` (:2212) detaches material and
//     credits it to no cell — that IS what detachment-limited means.
// Neither quantity is accumulated anywhere in `streamPowerErode`, and the node cannot reconstruct
// either from the field it publishes. The only figure it could print is
// `coverConsumed + bedrockDetached`, which is a RESTATEMENT of the two terms it would then be
// checked against — a closure that holds by construction for any implementation at all. So the node
// publishes NO boundary budget and says why, on every path. `claims-derived-export-closure` performs
// exactly that forbidden substitution and `boundaryBudgetIsNeverClaimedAndNamesWhy` is what sees it.
//
// WHAT WOULD BE NEEDED TO CLAIM ONE: two accumulators inside `streamPowerErode` — the volume zeroed
// out of the rim at :2198/:2269, and the per-cell decrement of the implicit step at :2212 — reported
// on the return the way `gpuHydraulicPipes` reports its apron ring. That file has a single serial
// owner and this story did not touch it.
//
// THE ONE BUDGET LINE THAT IS ITEMISABLE IS THE UPLIFT SOURCE, and it is the strongest reading here
// because it is computed from the node's INPUTS and never from its output. `streamPowerErode` applies
// uplift once per iteration to every cell that is not on the rim (:2201-2202), unconditionally, so
//     upliftApplied = Udt * iters * sum over the INTERIOR of (uplift ? uplift[i] : 1)
// and this file recomputes that in double from its own fixture and its own parameters. The rim
// exclusion is the load-bearing part: at RES 64 the perimeter is 252 of 4096 cells, so counting it
// overstates the source by 6.56% — `upliftSourceArming` measures that distance against the
// tolerance on every run rather than arguing it once, and `uplift-counts-the-rim` is the control.
//
// AND WHERE A CLAIM IS NOT AVAILABLE, NOTHING IS CLAIMED. Under a Mask the published field is a blend
// toward the input, so the uplift that reached it is an unrecorded fraction of what the kernel
// applied. On that path the node must publish NO uplift figure. `claims-uplift-under-mask` is the
// control, and it is the reason the plan runs a masked fixture at all.
//
// THE CLOSURE BOUNDS SCALE WITH WHAT MOVED, NOT WITH THE FIXTURE — and this file got that wrong on
// its first run, which is the reason both endpoints are now measured on every pass rather than
// argued once. The draft used the float32 unit over the sum of STANDING cover thicknesses and scored
// armings of 61.5 .. 146.7; on the deep fixture that made the tolerance a function of how much soil
// was lying there (1622 m over 4096 cells) instead of how much the pass moved. The corrected bound
// is the DOUBLE unit over the absolute per-cell CHANGE and scores ~5.5e11 — 1e9x tighter. The reason
// double is the honest unit is that production accumulates the book from THE PUBLISHED FLOAT32
// RASTER VALUES and so does this file, so the float32 rounding is common to both sides and cancels
// term by term; measured residual 1.5e-15 relative against a 1.8e-12 bound. The same argument makes
// `boundF64` right for the uplift comparison: the float32 unit there would have left the 6.56% rim
// error only 72x clear of the tolerance instead of 3.6e10x.
// Both endpoints stay live: `coverBookBoundIsSmallerThanTheTransport` reads the corrected bound and
// `theLooseCoverBookBoundIsDemonstrablyTooLoose` asserts that the rejected one still fails the same
// threshold, so the arming is a delta between two measurements taken on the same fixture in the same
// run rather than a claim about a draft nobody can re-execute.
//
// THERE IS NO GPU PATH. src/plugins/ero/streampower.js imports nothing from core/gpu.js and
// `streamPowerErode` is CPU-only, so a "GPU square path" plan entry would measure the CPU kernel
// twice while reading as coverage. Instead `kernelIsGpuFreeOnBothPaths` MEASURES the claim: the same
// evaluation under USE_GPU true and false must be bit-identical. That gate fails the day someone adds
// a GPU stream-power kernel without bringing a ledger with it.
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
  'bedrock-first-kernel',          // the story's named failure: bedrock is cut while loose cover remains
  'invents-deposition',            // the node starts depositing, which sprint-03:186 forbids for this node
  'ledger-consumption-inflated',   // the ledger stops being the integral of the rasters it publishes
  'bedrock-gain-hidden',           // the risen volume vanishes from the books instead of being itemised
  'sand-nonzero',                  // sandDepth stops being zero although no aeolian process ships
  'square-area-on-hex',            // the hex ledger integrates with s^2 instead of sqrt(3)/2*s^2
  'claims-derived-export-closure', // the boundary budget becomes consumed+detached: closure for free
  'uplift-counts-the-rim',         // the uplift source counts cells the kernel never lifts
  'claims-uplift-under-mask',      // an uplift budget published for a field the kernel did not produce
  'cover-alters-published-height', // wiring cover moves the terrain: an unauthorised re-bless
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
    //   boundF64  both sides are double reductions over the same float32 samples (the uplift source)
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
    const def = (typeof TYPES !== 'undefined' && TYPES) ? TYPES.streampower : null
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
      upliftIn: !!findIn('uplift'),
      // A POSITIVE claim, not an omission. Stream Power must NOT declare precipitation: the kernel's
      // only forcing terms are Udt and the Uplift raster (src/legacy.js:2201-2202), there is no rain
      // term anywhere in it, and a port nothing consumes is exactly the declared-but-never-filled
      // half-gate this sprint has already found repeatedly.
      noPrecipIn: findIn('precipitation') === null,
      // ...and it must NOT declare the `sediment` TRANSPORT port hydraulic publishes: that port means
      // "what this pass deposited", and this node deposits nothing.
      noTransportSedimentOut: findOut('sediment') === null,
      solidTopOut: portOk(findOut('solidTop'), 'm'),
      bedrockOut: portOk(findOut('bedrockHeight'), 'm'),
      soilOut: portOk(findOut('soilDepth'), 'm'),
      sedOut: portOk(findOut('sedimentDepth'), 'm'),
      sandOut: portOk(findOut('sandDepth'), 'm'),
      primaryId,
      slots: { uplift: slotOf('uplift'), mask: slotOf('mask'), soil: slotOf('soilDepth'), sed: slotOf('sedimentDepth') },
    }

    // ---- MUTATIONS: every one of them perturbs PRODUCTION --------------------------------------
    // Each control replaces TYPES.streampower.eval in the LIVE registry with a wrapper around the
    // real evaluator and perturbs what production HANDS BACK — its output rasters and the ledger
    // object it publishes on the typed return. None of them writes to a variable this file later
    // reads as its own answer; every measurement is taken from production's return value after the
    // wrapper has run, exactly as a downstream reader would see it. (House precedent:
    // _verify_thermal_coevolution.js and _verify_cover_erosion.js both wrap the registry eval.)
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
          // build, where incision lowered height with no cover layer to consume at all. The cover
          // rasters and the cover book stay mutually consistent, so ONLY the cover-first family sees
          // it — which is the point of arming that family with three fixtures.
          if (soilIn) vals.set('soilDepth', Float32Array.from(soilIn))
          if (sedIn) vals.set('sedimentDepth', Float32Array.from(sedIn))
          if (led) {
            led.bedrockDetachedM3 = (led.bedrockDetachedM3 || 0) + (led.coverConsumedM3 || 0)
            led.coverConsumedM3 = 0
          }
          restack()
        }
        if (mutation === 'invents-deposition') {
          // The node starts depositing where the surface rose — i.e. it stops being detachment-limited
          // and quietly becomes thermal. sprint-03:186 forbids exactly this for Stream Power, because
          // the kernel models no deposition and a deposit field would be invented physics. Staged
          // COHERENTLY: the raster rises, the ledger's depositedM3 follows it and bedrock is
          // restacked, so every volume book still closes and only the detachment-limited claim breaks.
          const se = vals.get('sedimentDepth'), h = vals.get(primaryId), before = ins[0]
          if (se && h && before && se.length === N && h.length === N) {
            // The rise is taken from the PUBLISHED delta, exactly the way production takes it.
            const m = new Float32Array(N)
            let dep = 0
            for (let i = 0; i < N; i++) {
              const dM = (h[i] - before[i]) * relief
              m[i] = dM > 0 ? Math.fround(se[i] + dM) : se[i]
              dep += m[i] - se[i]
            }
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
        if (mutation === 'bedrock-gain-hidden') {
          // The volume the pass ADDED disappears from the books. bedrockHeight still rises, because
          // it is solidTop minus cover and neither moved — so the stack identity still closes and the
          // cover book still closes. Only the itemisation gate sees the missing line.
          if (led) led.bedrockGainedM3 = 0
        }
        if (mutation === 'sand-nonzero') {
          // An aeolian layer appears although no process in this sprint produces one.
          const sand = new Float32Array(N); sand.fill(0.25)
          vals.set('sandDepth', sand)
        }
        if (mutation === 'cover-alters-published-height' && soilIn) {
          // WIRING COVER MOVES THE TERRAIN. D21 authorises a STATED re-bless for this node, and this
          // is the shape of one taken without saying so: the same graph incises differently the
          // moment a soil field is attached, so every downstream digest, thumbnail and saved document
          // changes and nothing announces it. The perturbation is applied only where cover exists, so
          // the UNWIRED evaluation below — the pre-S3.5 call shape, three slots and no state demand —
          // comes back untouched and the two stop matching.
          const h = vals.get(primaryId)
          if (h && h.length === soilIn.length) {
            const m = Float32Array.from(h)
            for (let i = 0; i < m.length; i++) if (soilIn[i] > 0) m[i] = Math.fround(m[i] * 1.000001)
            vals.set(primaryId, m)
          }
        }
        if (mutation === 'claims-derived-export-closure' && led) {
          // THE DEFECT THIS SUITE KEEPS FINDING, in the one place this node could plausibly hide it.
          // A boundary budget appears — and its value is `coverConsumed + bedrockDetached`, a
          // restatement of the two terms it would then be checked against. `consumed + detached =
          // deposited(0) + exported` now holds EXACTLY, for any implementation, including one that
          // deletes the terrain. Nothing about the rasters changes, so only the itemisation gate can
          // see it, which is precisely why the refusal is asserted rather than merely printed.
          delete led.lossClaimed
          led.exportedOrSuspendedM3 = (led.coverConsumedM3 || 0) + (led.bedrockDetachedM3 || 0)
          led.boundaryExportedM3 = led.exportedOrSuspendedM3
          led.suspendedM3 = 0
          led.lossSource = 'detached-volume-is-exported'
          led.boundaryPolicy = 'open-base-level'
        }
        if (mutation === 'uplift-counts-the-rim' && led && typeof led.upliftAppliedM3 === 'number'
            && led.upliftInteriorCells > 0) {
          // The uplift source counts the whole field instead of the interior — the rim cells the
          // kernel skips at src/legacy.js:2201-2202. At RES 64 that is 252 of 4096 cells.
          const cells = (led.cols || 0) * (led.rows || 0)
          if (cells > 0) {
            led.upliftAppliedM3 *= cells / led.upliftInteriorCells
            led.upliftInteriorCells = cells
          }
        }
        if (mutation === 'claims-uplift-under-mask' && led && ins[slotOf('mask')]) {
          // An uplift budget published for a field the kernel did not produce. The mask blended the
          // result toward the input, so the kernel's source term no longer describes what is
          // published — and this asserts it anyway.
          delete led.upliftClaimed
          led.upliftAppliedM3 = (led.bedrockGainedM3 || 0)
          led.upliftInteriorCells = Math.max(0, (led.cols - 2)) * Math.max(0, (led.rows - 2))
          led.upliftWired = true
          led.upliftSource = 'kernel-source-term-field'
        }
        if (mutation === 'square-area-on-hex' && terrainDef.lattice === 'hex' && led) {
          // The hex ledger integrates depth with the SQUARE cell area over a square row count.
          // Every reported volume is then 1/(sqrt(3)/2) = 1.1547x too large, and stops matching the
          // raster integral this file computes with the true hex area over fieldH() rows.
          const s = SCALE_M / RES_FIX, f = 1 / SQRT3_2
          led.cellAreaM2 = s * s
          led.rows = RES_FIX
          for (const k of ['coverConsumedM3', 'bedrockDetachedM3', 'bedrockGainedM3', 'upliftAppliedM3']) {
            if (typeof led[k] === 'number') led[k] *= f
          }
        }
        return raw
      }
      out.mutationApplied.registryMoved = TYPES.streampower.eval !== realEval
    }

    // ---- fixtures ------------------------------------------------------------------------------
    // A ramp that descends monotonically in +x, with a corrugation that depends ONLY ON y, inside a
    // rim held at base level. All three properties are load-bearing and none is a taste:
    //   monotone in x   -> every interior cell has a strictly lower +x neighbour, so the field
    //                      contains NO interior depression. That matters because the implicit solve's
    //                      floor `if(h[i]<h[rec[i]])h[i]=h[rec[i]]` (src/legacy.js:2213) fires
    //                      independently of Kdt, so on a pitted fixture even a zero-rate pass would
    //                      move material and there would be no identity pass to measure BEFORE with.
    //   corrugated in y -> flow concentrates along the grooves, so drainage area A varies and the
    //                      incision is differential rather than a uniform sheet. Without it the
    //                      fixture would exercise the accounting on a plane.
    //   rim at 0        -> the kernel zeroes the rim before its first iteration (:2198). A fixture
    //                      whose rim is already at base level therefore takes no one-time step from
    //                      that line, which is the other half of what makes the identity pass exact.
    const AMP = 0.05
    const makeBase = (W, H) => {
      const f = new Float32Array(W * H)
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        f[y * W + x] = 0.55 - 0.30 * (x / (W - 1)) + AMP * Math.sin(y * 0.9)
      }
      for (let x = 0; x < W; x++) { f[x] = 0; f[(H - 1) * W + x] = 0 }
      for (let y = 0; y < H; y++) { f[y * W] = 0; f[y * W + W - 1] = 0 }
      return f
    }
    // A spatially varying uplift, so the ledger's source term is a real sum over a raster rather
    // than a constant that a rim-blind implementation could still get right by accident.
    const makeUplift = (W, H) => {
      const f = new Float32Array(W * H)
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        f[y * W + x] = 0.35 + 0.30 * Math.sin(x * 0.21) * Math.cos(y * 0.17)
      }
      return f
    }
    // COVER DEPTH IS DERIVED FROM THE FIXTURE, not guessed. The published field can never go below
    // the rim's base level — the incision step never puts a cell under its receiver (:2213), uplift
    // only adds, and the diffusion stencil is a convex combination at c = Ddt <= 1/4 — so the largest
    // lowering any sample can suffer in one pass is its own initial elevation, i.e. max(base)*relief.
    // DEEP is that bound with 5% headroom, which is why one pass cannot locally exhaust it. The
    // reasoning is not trusted: `deepFixtureCoverNeverExhausted` MEASURES minCoverAfter > 0 and the
    // headroom is printed as maxLoweringM against it.
    const deepFor = base => {
      let mx = 0
      for (let i = 0; i < base.length; i++) if (base[i] > mx) mx = base[i]
      return Math.ceil(mx * HEIGHT_M * 1.05)
    }
    const makeCover = (kind, W, H, deepM) => {
      const soil = new Float32Array(W * H)
      if (kind === 'deep') soil.fill(deepM)
      else if (kind === 'mixed') {
        for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (x < W / 2) soil[y * W + x] = deepM
      }
      return { soil, sed: new Float32Array(W * H) }   // 'bare' leaves both at zero
    }

    // THE IDENTITY PASS. Stream Power has no "stage off" switch, but every rate it owns has 0 as a
    // legal slider value: Incision 0 makes Kdt 0 so the implicit step is h[i]=(h[i]+0)/(1+0), Uplift
    // 0 makes Udt 0 so the source term adds nothing, and Hillslope 0 skips the diffusion block
    // entirely (`if(Ddt>0)`). With one iteration on a pit-free fixture whose rim is already at base
    // level, that is a real production evaluation which transports nothing — which is how the BEFORE
    // cover is obtained in production's own frame without this file inventing one. `heightUnmoved`
    // is what proves it rather than asserts it.
    const beforeParams = { strength: 0, m: 0.5, iters: 1, uplift: 0, hillslope: 0 }
    // TWO AFTER REGIMES, and the second exists because the first left a gate barely armed.
    //   defaults        the node exactly as it reaches an author. Incision dominates so completely
    //                   that only ONE sample of 4096 nets a rise — measured, not assumed. That is
    //                   enough to make "no cell's cover rose" a real claim, but only just, and a
    //                   corpus in which the no-deposition gate hangs on one cell is a corpus that
    //                   would go quietly vacuous the day the defaults moved.
    //   upliftDominant  Incision 0.01 against Uplift 1.0 — the equilibrium regime the note describes
    //                   ("raise Uplift so the interior keeps rising while the rivers cut"). Thousands
    //                   of cells rise, so `invents-deposition` has thousands of cells to deposit into
    //                   and the detachment-limited claim is armed across the whole field rather than
    //                   at a single sample. Both are legal slider settings; neither is invented.
    const REGIMES = {
      defaults: { strength: 0.08, m: 0.5, iters: 14, uplift: 0.35, hillslope: 0.9 },
      upliftDominant: { strength: 0.01, m: 0.5, iters: 14, uplift: 1, hillslope: 0.9 },
    }
    const afterParams = REGIMES.defaults        // the rejects probe below uses the shipped defaults
    const UDT_SCALE = 0.004     // src/plugins/ero/streampower.js: Udt = p.uplift * 0.004

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

    const runOne = (lattice, fixture, masked, upliftWired, regime) => {
      const after = REGIMES[regime] || REGIMES.defaults
      const r = { key: `${lattice}/${fixture}${masked ? '/masked' : ''}${upliftWired ? '' : '/scalarU'}`
          + (regime === 'upliftDominant' ? '/upliftDom' : ''),
        lattice, fixture, masked: !!masked, upliftWired: !!upliftWired, regime: regime || 'defaults',
        error: null, ran: false }
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
        const { soil: soil0, sed: sed0 } = makeCover(fixture, W, H, deepM)
        const upl = upliftWired ? makeUplift(W, H) : null
        const mask = masked ? new Float32Array(N).fill(MASK_VALUE) : null
        r.coverInSum = sumD(soil0) + sumD(sed0)
        r.coverInDigest = (() => { let a = 0x811c9dc5
          for (let i = 0; i < soil0.length; i++) { a = (a ^ (Math.round(soil0[i] * 1e3) | 0)) >>> 0; a = Math.imul(a, 16777619) >>> 0 }
          return a.toString(16) })()

        const sUpl = slotOf('uplift'), sMask = slotOf('mask')
        const sSoil = slotOf('soilDepth'), sSed = slotOf('sedimentDepth')
        r.slotsResolved = sUpl >= 0 && sMask >= 0 && sSoil >= 0 && sSed >= 0
        const width = Math.max(3, sUpl + 1, sMask + 1, sSoil + 1, sSed + 1)
        const ins = new Array(width).fill(null)
        ins[0] = base
        if (sUpl >= 0) ins[sUpl] = upl
        if (sMask >= 0) ins[sMask] = mask
        if (sSoil >= 0) ins[sSoil] = soil0
        if (sSed >= 0) ins[sSed] = sed0

        // ---- THE INDEPENDENT UPLIFT SOURCE, computed here from the fixture and the parameters ----
        // The kernel lifts every cell that is NOT on the rim, once per iteration
        // (src/legacy.js:2196-2197 for isEdge, :2201-2202 for the application). Both the
        // interior-only figure and the rim-inclusive one are computed, so the distance between them
        // — the error `uplift-counts-the-rim` injects — is a MEASURED arming distance rather than an
        // argued one.
        const Udt = after.uplift * UDT_SCALE
        let sumInterior = 0, cellsInterior = 0, sumAll = 0
        for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
          sumInterior += upl ? upl[y * W + x] : 1; cellsInterior++
        }
        for (let i = 0; i < N; i++) sumAll += upl ? upl[i] : 1
        r.upliftInteriorCellsIndep = cellsInterior
        r.upliftIndepM3 = Udt * after.iters * sumInterior * HEIGHT_M * r.areaExpected
        r.upliftRimInclusiveM3 = Udt * after.iters * sumAll * HEIGHT_M * r.areaExpected
        r.upliftBound = boundF64(N, Math.abs(r.upliftIndepM3))
        r.upliftSourceArming = r.upliftBound > 0
          ? Math.abs(r.upliftRimInclusiveM3 - r.upliftIndepM3) / r.upliftBound : 0

        const nd = { id: 9301, type: 'streampower', params: null }
        const demanded = new Set([primaryId, 'out', 'solidTop', 'bedrockHeight',
          'soilDepth', 'sedimentDepth', 'sandDepth'])

        // --- BEFORE: every rate at zero. Contractually an identity pass that echoes cover and
        //     publishes an all-zero cover ledger.
        nd.params = { ...beforeParams }
        const rawB = TYPES.streampower.eval(nd.params, ins, nd, { demanded })
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
          // Every transport term AND the source term: a pass that moved nothing must say so on all
          // of them, and `upliftAppliedM3` is the one a stale-constant implementation would get wrong.
          ledgerAllZero: !!ledB && ['coverConsumedM3', 'bedrockDetachedM3', 'depositedM3',
            'bedrockGainedM3'].every(k => ledB[k] === 0)
            && (ledB.upliftAppliedM3 === 0 || masked),
          topFinite: topB ? finiteAll(topB) : false,
        }

        // --- AFTER: one real incision pass in this run's regime.
        nd.params = { ...after }
        const rawA = TYPES.streampower.eval(nd.params, ins, nd, { demanded })
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

        // The pass must actually have run, or every ledger reading below is about nothing — and
        // material must have gone BOTH WAYS, or "the node deposits nothing" is a claim about a
        // fixture in which nothing rose.
        if (primA && primB) {
          let moved = 0, risen = 0, maxDrop = 0, gainedIndep = 0
          for (let i = 0; i < N; i++) {
            const d = primA[i] - primB[i]
            if (d !== 0) moved++
            if (d > 0) { risen++; gainedIndep += d * HEIGHT_M }
            if (-d > maxDrop) maxDrop = -d
          }
          r.samplesMoved = moved
          r.samplesRisen = risen
          r.maxLoweringM = maxDrop * HEIGHT_M
          r.gainedIndepM3 = gainedIndep * r.areaExpected
        }

        // --- the byte-identity control ----------------------------------------------------------
        // The SAME pass called the way the pre-S3.5 build was called: three slots, no cover attached,
        // and only the primary demanded. D21 authorises a STATED re-bless for this node, but a graph
        // that wires no cover must produce the terrain it produced yesterday, byte for byte, and that
        // has to be MEASURED rather than argued from the fact that the digest recipe happens not to
        // demand a state port.
        const rawU = TYPES.streampower.eval(nd.params, [ins[0], upl, mask], nd, { demanded: new Set([primaryId]) })
        const primU = grab(readValues(rawU), primaryId)
        r.unwiredLength = primU ? primU.length : null
        r.unwiredMatchesWired = bitEqual(primU, primA)

        // --- the digest-shape control -----------------------------------------------------------
        // With NO ctx at all — which is exactly how _verify_digest.js:199 calls every evaluator —
        // the return must still be a bare typed array, not a values Map. If it became typed, the
        // digest would start folding five extra ports for this node and the baseline would move for
        // a reason that has nothing to do with the physics.
        const rawN = TYPES.streampower.eval(nd.params, ins, nd)
        r.undemandedIsBareField = ArrayBuffer.isView(rawN) && !(rawN && rawN.values instanceof Map)
          && rawN.length === N
        r.undemandedMatchesWired = bitEqual(rawN, primA)

        // --- there is no GPU path, and that is MEASURED -------------------------------------------
        // streampower.js imports nothing from core/gpu.js, so the same evaluation under USE_GPU true
        // must be bit-identical. This fails the day a GPU stream-power kernel lands without a ledger.
        USE_GPU = true
        const rawG = TYPES.streampower.eval(nd.params, ins, nd, { demanded: new Set([primaryId]) })
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
          for (let i = 0; i < N; i++) {
            const c1 = soilA[i] + sedA[i] + sandA[i]
            const c0 = soilB[i] + sedB[i] + sandB[i]
            dCover += A * (c1 - c0)
            absChange += A * Math.abs(c1 - c0)
            if (c1 < minCoverAfter) minCoverAfter = c1
            if (c1 - c0 > maxCoverRise) maxCoverRise = c1 - c0
          }
          r.dCoverM3 = dCover
          r.minCoverAfter = minCoverAfter
          // MEASURED FROM THE RASTERS, not read off the ledger. This is what makes "detachment
          // limited" a reading of the published fields rather than a restatement of a flag.
          r.maxCoverRiseMeasuredM = maxCoverRise
          // THE COVER BOOK'S BOUND IS A DOUBLE-REDUCTION BOUND OVER THE ABSOLUTE CHANGE, and both
          // halves of that sentence were wrong on the first draft of this file. The measured
          // endpoints are on the record because this is the project's standing failure mode:
          //
          //   boundF32 over sum(|c1|+|c0|)   armings 61.5 .. 146.7   -- FAILS the gate below
          //   boundF64 over sum(|c1-c0|)     armings ~5.5e11         -- passes
          //
          // WHY F64. Production accumulates `(a0-a1)+(d0-d1)+(s0-s1)` in double FROM THE PUBLISHED
          // FLOAT32 RASTER VALUES (src/plugins/ero/streampower.js), and this file accumulates
          // `c1-c0` in double from those same values. The float32 rounding is therefore COMMON to
          // both sides and cancels term by term; the only residual is the reduction ordering, which
          // is double. Measured relative residual 1.5e-15, against a double bound of 1.8e-12 —
          // three orders of headroom. The float32 bound was 1e9x too loose, and it is a STRONGER
          // gate this way: an implementation that computed the ledger from double intermediates
          // instead of from the rasters it publishes would break the cancellation and be caught.
          //
          // WHY THE ABSOLUTE CHANGE. A reduction bound scales with sum(|term|), and the terms here
          // are per-cell CHANGES. Summing |c1|+|c0| instead makes the tolerance a function of how
          // much cover is STANDING — on the deep fixture that is 1622 m over 4096 cells, so the
          // bound grew with the fixture rather than with what the pass moved. That is precisely the
          // "bound scales with the terrain, not with the transport" defect this suite has measured
          // elsewhere at 277x too loose; here it was 1e9x.
          r.coverBookBound = boundF64(N, absChange)
          // THE REJECTED BOUND, RE-MEASURED ON EVERY RUN rather than left as a historical note in a
          // comment. `coverBookArmingLoose` below is what this file would have scored had it kept
          // the float32 unit over the sum of standing thicknesses, and
          // `theLooseCoverBookBoundIsDemonstrablyTooLoose` asserts that it still fails the threshold
          // the corrected bound passes. That turns "the bound is tight enough" from an argument made
          // once into a delta between two endpoints measured on every run.
          let absStanding = 0
          for (let i = 0; i < N; i++) {
            absStanding += r.areaExpected * (Math.abs(soilA[i] + sedA[i] + sandA[i])
              + Math.abs(soilB[i] + sedB[i] + sandB[i]))
          }
          r.coverBookBoundLoose = boundF32(N, absStanding)
          if (led) {
            // deposited is a published constant zero for this node, and it is INCLUDED in the book
            // rather than assumed away: a build that started depositing while leaving the raster
            // alone would show up here as well as in the detachment gate.
            r.coverBookErr = Math.abs(dCover - ((led.depositedM3 || 0) - (led.coverConsumedM3 || 0)))
            r.coverBookCloses = r.coverBookErr <= r.coverBookBound
            const transported = Math.abs(led.coverConsumedM3 || 0) + Math.abs(led.bedrockDetachedM3 || 0)
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
          r.loss = {
            claimed: led.lossClaimed !== false,
            source: typeof led.lossSource === 'string' ? led.lossSource : null,
            policy: typeof led.boundaryPolicy === 'string' ? led.boundaryPolicy : null,
            exported: has('exportedOrSuspendedM3') ? led.exportedOrSuspendedM3 : null,
            boundaryExported: has('boundaryExportedM3') ? led.boundaryExportedM3 : null,
            suspended: has('suspendedM3') ? led.suspendedM3 : null,
          }
          r.upliftClaim = {
            claimed: led.upliftClaimed !== false,
            source: typeof led.upliftSource === 'string' ? led.upliftSource : null,
            appliedM3: has('upliftAppliedM3') ? led.upliftAppliedM3 : null,
            interiorCells: has('upliftInteriorCells') ? led.upliftInteriorCells : null,
            wired: has('upliftWired') ? led.upliftWired : null,
          }
          if (typeof led.upliftAppliedM3 === 'number' && Number.isFinite(r.upliftIndepM3)) {
            r.upliftErr = Math.abs(led.upliftAppliedM3 - r.upliftIndepM3)
            r.upliftMatches = r.upliftErr <= r.upliftBound
          }
          if (typeof led.bedrockGainedM3 === 'number' && Number.isFinite(r.gainedIndepM3)) {
            r.gainBound = boundF64(N, Math.abs(r.gainedIndepM3))
            r.gainErr = Math.abs(led.bedrockGainedM3 - r.gainedIndepM3)
            r.gainMatches = r.gainErr <= r.gainBound
          }
          r.depositedZero = led.depositedM3 === 0 && led.depositionModelled === false
          r.slotsReported = led.soilSlot === sSoil && led.sedimentSlot === sSed
            && led.upliftSlot === sUpl && led.soilWired === true && led.sedimentWired === true
        }
      } catch (e) {
        r.error = String((e && e.message) || e)
      }
      return r
    }

    const plan = []
    for (const fx of ['deep', 'bare', 'mixed']) {
      plan.push(['square', fx, false, true, 'defaults'])
      plan.push(['hex', fx, false, true, 'defaults'])
    }
    // The SCALAR uplift path — `else if(Udt)` at src/legacy.js:2202, a different branch of the kernel
    // and a different `upliftSource` string, so leaving it unrun would leave half the source term
    // unmeasured.
    plan.push(['square', 'mixed', false, false, 'defaults'])
    plan.push(['hex', 'mixed', false, false, 'defaults'])
    // The UPLIFT-DOMINANT regime, on the three cover fixtures. This is what makes the
    // detachment-limited claim an assertion about a field in which thousands of cells rose rather
    // than about the single sample the shipped defaults leave above water.
    for (const fx of ['deep', 'bare', 'mixed']) {
      plan.push(['square', fx, false, true, 'upliftDominant'])
      plan.push(['hex', fx, false, true, 'upliftDominant'])
    }
    // The masked path, on the fixture that exercises both layers. This is the run where the node must
    // publish NO uplift budget, and it is the only place `claims-uplift-under-mask` bites.
    plan.push(['square', 'mixed', true, true, 'defaults'])
    plan.push(['hex', 'mixed', true, true, 'defaults'])
    for (const [lat, fx, masked, upl, reg] of plan) out.runs.push(runOne(lat, fx, masked, upl, reg))

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
      const nd = { id: 9302, type: 'streampower', params: { ...afterParams } }
      const demanded = new Set(['solidTop', 'soilDepth'])
      const sSoil = slotOf('soilDepth'), sSed = slotOf('sedimentDepth')
      const mk = mutate => {
        const soil = new Float32Array(N).fill(10)
        if (mutate) mutate(soil)
        const ins = new Array(Math.max(3, sSoil + 1, sSed + 1)).fill(null)
        ins[0] = base
        if (sSoil >= 0) ins[sSoil] = soil
        if (sSed >= 0) ins[sSed] = new Float32Array(N)
        return ins
      }
      try { TYPES.streampower.eval(nd.params, mk(a => { a[13] = NaN }), nd, { demanded }) }
      catch (e) { out.rejects.nonFinite = /non-negative depth/.test(String(e && e.message)) }
      try { TYPES.streampower.eval(nd.params, mk(a => { a[13] = -1 }), nd, { demanded }) }
      catch (e) { out.rejects.negative = /non-negative depth/.test(String(e && e.message)) }
      // ...and a clean wired cover still evaluates, so the two above are a refusal of BAD DATA and
      // not a node that refuses cover altogether.
      const okRaw = TYPES.streampower.eval(nd.params, mk(null), nd, { demanded })
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
    // differ ON EACH LATTICE; a corpus where they collapsed on hex would leave every hex gate below
    // satisfied by one fixture wearing three names.
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
      && report.ports.upliftIn === true && report.ports.noPrecipIn === true
      && report.ports.insLabels.join('|') === 'In|Uplift|Mask|Soil depth|Sediment depth',
    stateOutputPortsDeclared: report.ports.solidTopOut === true && report.ports.bedrockOut === true
      && report.ports.soilOut === true && report.ports.sedOut === true && report.ports.sandOut === true
      && report.ports.noTransportSedimentOut === true,

    // --- the identity pass, which is also how BEFORE is measured ---------------------------------
    noTransportPassEchoesCover: every(runs, r => r.before && r.before.hasState === true
      && r.before.echoesSoil === true && r.before.echoesSed === true && r.before.sandZero === true
      && r.before.heightUnmoved === true && r.before.lengthsOk === true
      && r.before.ledgerAllZero === true && r.before.topFinite === true),

    // --- the pass actually ran, and material went BOTH WAYS ---------------------------------------
    // A PRECONDITION for everything below, and deliberately unarmed by any mutation: it establishes
    // that the fixture incised AND that the surface rose somewhere, so `detachmentLimitedDeposits-
    // Nothing` is a claim about a run in which deposition was possible rather than one in which
    // nothing went up.
    incisionTransportedMaterial: every(runs, r => num(r.samplesMoved) !== null && r.samplesMoved > 0
      && num(r.transportedM3) !== null && r.transportedM3 > 0),
    // TWO STRENGTHS, because "somewhere" is not the same claim as "across the field". Every run must
    // have risen somewhere, AND the uplift-dominant regime must have risen over at least a tenth of
    // its cells — otherwise `detachmentLimitedDepositsNothing` would be resting on the single sample
    // the shipped defaults leave above water, which is how a gate goes quietly vacuous when a
    // default moves.
    surfaceRoseSomewhereSoTheClaimIsArmed: every(runs, r => num(r.samplesRisen) !== null
      && r.samplesRisen > 0 && num(r.gainedIndepM3) !== null && r.gainedIndepM3 > 0)
      && every(runs.filter(r => r.regime === 'upliftDominant'),
        r => r.samplesRisen >= 0.1 * r.N),
    // ...and both regimes actually executed, so the paragraph above is describing runs that happened.
    bothRegimesMeasured: runs.some(r => r.regime === 'defaults' && r.ran === true)
      && runs.some(r => r.regime === 'upliftDominant' && r.ran === true),

    // --- COVER BEFORE BEDROCK, armed by three fixtures --------------------------------------------
    // 1) the deep fixture must actually consume cover, or the next gate is about nothing;
    coverIsConsumedOnDeepFixture: every(deep, r => num(ledNum(r, 'coverConsumedM3')) !== null
      && ledNum(r, 'coverConsumedM3') > 0),
    // 2) and cover must never have reached zero anywhere, or "bedrock untouched" is unarmed. The
    //    measured headroom is printed as maxLoweringM against the fixture's derived DEEP.
    deepFixtureCoverNeverExhausted: every(deep, r => num(r.minCoverAfter) !== null && r.minCoverAfter > 0
      && num(r.maxLoweringM) !== null && num(r.deepM) !== null && r.maxLoweringM < r.deepM),
    // 3) THE STORY'S NAMED RED. Bedrock is not cut while local loose cover remains.
    bedrockUntouchedWhileCoverRemains: every(deep, r => ledNum(r, 'bedrockDetachedM3') === 0),
    // 4) and the kernel must be CAPABLE of cutting bedrock, or (3) passes by refusing to move.
    bareBedrockDoesErode: every(bare, r => num(ledNum(r, 'bedrockDetachedM3')) !== null
      && ledNum(r, 'bedrockDetachedM3') > 0 && ledNum(r, 'coverConsumedM3') === 0),
    // 5) the mixed slope exercises the boundary between the two regimes in one pass.
    mixedFixtureCutsBothLayers: every(mixed, r => num(ledNum(r, 'coverConsumedM3')) !== null
      && ledNum(r, 'coverConsumedM3') > 0 && num(ledNum(r, 'bedrockDetachedM3')) !== null
      && ledNum(r, 'bedrockDetachedM3') > 0),

    // --- DETACHMENT-LIMITED: the node deposits nothing, and that is READ OFF THE RASTERS -----------
    // sprint-03:186. Three independent readings, all of which a depositing build breaks: the
    // published constant, the ledger's own measured maximum cover rise, and this file's measurement
    // of the same quantity from the soil/sediment/sand rasters. The gate is armed by
    // `invents-deposition`, which stages a coherent depositing build in which every volume book still
    // closes — so only this gate can see it.
    detachmentLimitedDepositsNothing: every(runs, r => r.depositedZero === true
      && num(ledNum(r, 'maxCoverRiseM')) !== null && ledNum(r, 'maxCoverRiseM') <= 0
      && num(r.maxCoverRiseMeasuredM) !== null && r.maxCoverRiseMeasuredM <= 0),

    // --- conservation, entirely in frame-free thicknesses and volumes ------------------------------
    coverBookCloses: every(runs, r => r.coverBookCloses === true),
    // THE BOUND IS SMALLER THAN THE TERM IT CONSTRAINS, measured on every run rather than argued
    // once. WHAT IT SCALES WITH: the absolute per-cell cover CHANGE — the thickness this pass
    // actually moved — never a sum of standing thicknesses, which would make the tolerance a
    // function of how deep the fixture's cover is. The ratio says how large a discrepancy the book
    // can still see. Its ceiling is arithmetic: boundF64 is 2*gamma64(2N) relative, which at N ~ 4e3
    // is 1.8e-12, so on the deep fixture (where the whole transport IS cover change) the ratio
    // cannot exceed ~5.5e11 however tight the implementation, and that is what it measures.
    //
    // THIS GATE IS ARMED BETWEEN TWO MEASURED ENDPOINTS, both taken on this fixture. The first draft
    // of this file used boundF32 over the sum of standing thicknesses and scored 61.5 .. 146.7 — it
    // FAILED this gate, which is how the loose bound was found. The corrected bound scores ~5.5e11.
    // The threshold sits at 1e6: far above anything a terrain-scaled bound can reach, and far below
    // the true ceiling, so a silent loosening of four orders is caught rather than merely absent.
    // `ledger-consumption-inflated` moves 3%, which needs only ~33 and is therefore certain to bite.
    coverBookBoundIsSmallerThanTheTransport: every(runs, r => num(r.coverBookArming) !== null
      && r.coverBookArming > 1e6),
    // ...and the OTHER endpoint, so the arming is a delta measured live rather than a claim about a
    // draft nobody can re-run. On the fixtures that carry standing cover, the rejected bound must
    // still fail the threshold the corrected one passes. Restricted to `deep` and `mixed` because
    // `bare` has no standing cover for a terrain-scaled bound to grow with — on that fixture the two
    // bounds legitimately coincide at their 1e-6/1e-9 floors and the comparison would be about
    // nothing, which is the sort of vacuous term this gate exists to avoid.
    theLooseCoverBookBoundIsDemonstrablyTooLoose: every(deep.concat(mixed).concat(masked),
      r => num(r.coverBookArmingLoose) !== null && r.coverBookArmingLoose < 1e6
        && num(r.coverBookArming) !== null && r.coverBookArming > 1e6),
    // The volume the pass ADDED is itemised and equals this file's own integral of the positive part
    // of the published delta. Armed by `bedrock-gain-hidden`.
    bedrockGainIsItemisedAndMatchesTheField: every(runs, r => r.gainMatches === true
      && num(ledNum(r, 'bedrockGainedM3')) !== null && ledNum(r, 'bedrockGainedM3') > 0),

    // --- the uplift source, the one budget line this node can support -------------------------------
    // ITEMISED FROM THE KERNEL, NOT FROM THE FIELD: Udt * iters * sum over the INTERIOR, recomputed
    // here in double from this file's own fixture and parameters. The rim exclusion is what a
    // rim-blind implementation gets wrong, and `upliftSourceArming` measures how far that error sits
    // above the tolerance on every run. Armed by `uplift-counts-the-rim`.
    upliftSourceIsItemisedAndExcludesTheRim: every(unmasked, r => !!r.upliftClaim
      && r.upliftClaim.claimed === true && r.upliftMatches === true
      && r.upliftClaim.interiorCells === r.upliftInteriorCellsIndep
      && r.upliftClaim.wired === r.upliftWired
      && r.upliftClaim.source === (r.upliftWired ? 'kernel-source-term-field' : 'kernel-source-term-scalar')),
    // ...and the tolerance on that comparison is far smaller than the error a rim-blind
    // implementation makes. WHAT IT SCALES WITH: the uplift volume itself, through boundF64 — both
    // sides are double reductions over the same float32 samples, so 2*gamma64(2N) ~ 1.8e-12 relative
    // is the honest unit and the rim error is 6.56% of the total, giving a ceiling of ~3.6e10. The
    // threshold is 1e6: four orders below the measured value, so a bound loosened to the float32
    // unit (which would score ~72 and let a 6.56% error sit inside the tolerance) is a named red.
    upliftSourceBoundIsSmallerThanTheRimError: every(unmasked, r => num(r.upliftSourceArming) !== null
      && r.upliftSourceArming > 1e6),
    // TRANSFORMED: the mask blended the result toward the input, so the kernel's source term no
    // longer describes what is published. The node must claim NOTHING and say which transform removed
    // the claim. Armed by `claims-uplift-under-mask`.
    maskedPathPublishesNoUpliftClaim: every(masked, r => !!r.upliftClaim
      && r.upliftClaim.claimed === false && r.upliftClaim.source === 'mask-composite'
      && r.upliftClaim.appliedM3 === null && r.upliftClaim.interiorCells === null),

    // --- the boundary budget, refused on every path and for a stated reason --------------------------
    // Unlike thermal, this node's rim is OPEN and its detachment is credited to nobody, and neither is
    // accumulated by the solver — so the only number it could print is a restatement of the terms it
    // would be compared against. It prints none. Armed by `claims-derived-export-closure`.
    boundaryBudgetIsNeverClaimedAndNamesWhy: every(runs, r => !!r.loss && r.loss.claimed === false
      && r.loss.source === 'open-base-level-boundary-not-itemised' && r.loss.policy === null
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
    // erodibility law, which nobody has specified and which would be a fabricated constant. So the
    // published height with cover attached must be the published height without it, bit for bit, and
    // D21's re-bless stays unspent. Armed by cover-alters-published-height.
    coverDoesNotMoveThePublishedHeight: every(runs, r => r.unwiredMatchesWired === true
      && r.unwiredLength === r.N),
    // ...and the no-ctx call shape — the one _verify_digest.js uses — still returns the bare field it
    // always did, so the baseline cannot move for a reason unrelated to the physics.
    undemandedEvaluationStaysUntyped: every(runs, r => r.undemandedIsBareField === true
      && r.undemandedMatchesWired === true),
    // There is no GPU stream-power kernel; this MEASURES that rather than assuming it, so a GPU path
    // added without a ledger is a named red instead of a silent gap in this file's coverage.
    kernelIsGpuFreeOnBothPaths: every(runs, r => r.gpuMatchesCpu === true),

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
    // evaluator never reads would look exactly like a working port. The numbers are Stream Power's
    // own, NOT thermal's: this row already owned slot 1 for Uplift, so cover lands at 3 and 4.
    coverSlotsAreDeclaredAndFilled: every(runs, r => r.slotsResolved === true && r.slotsReported === true)
      && report.ports.slots.uplift === 1 && report.ports.slots.mask === 2
      && report.ports.slots.soil === 3 && report.ports.slots.sed === 4,

    // --- a wired cover raster that is not a depth is refused by name ---------------------------------
    badCoverRasterIsRefusedNotHalfRead: report.rejects.nonFinite === true
      && report.rejects.negative === true && report.rejects.cleanStillEvaluates === true,

    // --- absence of evidence is a failure -------------------------------------------------------------
    // BOTH uplift branches must have been measured — the wired raster (`if(uplift)`) and the scalar
    // (`else if(Udt)`) at src/legacy.js:2201-2202 — or half the source term is untested.
    bothUpliftBranchesMeasured: runs.some(r => r.upliftWired === true && r.ran === true)
      && runs.some(r => r.upliftWired === false && r.ran === true),
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

  console.log('== S3.5 cover-aware DETACHMENT-LIMITED stream power ==')
  console.log(`ins=[${report.ports.insLabels.join(',')}] in=[${report.ports.declaredInputIds.join(',')}] `
    + `out=[${report.ports.declaredOutputIds.join(',')}] slots=${JSON.stringify(report.ports.slots)}`)
  for (const r of runs) {
    console.log(`  ${r.key.padEnd(22)} W=${r.W} H=${r.H} deepM=${r.deepM} moved=${r.samplesMoved} risen=${r.samplesRisen} `
      + `maxLoweringM=${fmt(r.maxLoweringM)} consumed=${fmt(ledNum(r, 'coverConsumedM3'))} `
      + `detached=${fmt(ledNum(r, 'bedrockDetachedM3'))} deposited=${fmt(ledNum(r, 'depositedM3'))} `
      + `gained=${fmt(ledNum(r, 'bedrockGainedM3'))} gainErr=${fmt(r.gainErr)} `
      + `uplift=${fmt(ledNum(r, 'upliftAppliedM3'))} upliftIndep=${fmt(r.upliftIndepM3)} upliftErr=${fmt(r.upliftErr)} `
      + `upliftArming=${fmt(r.upliftSourceArming)} upliftSrc=${r.upliftClaim ? r.upliftClaim.source : 'n/a'} `
      + `lossClaimed=${r.loss ? r.loss.claimed : 'n/a'} lossSrc=${r.loss ? r.loss.source : 'n/a'} `
      + `coverBookErr=${fmt(r.coverBookErr)} bound=${fmt(r.coverBookBound)} arming=${fmt(r.coverBookArming)} `
      + `armingLoose=${fmt(r.coverBookArmingLoose)} `
      + `maxCoverRise=${fmt(r.maxCoverRiseMeasuredM)} minCover=${fmt(r.minCoverAfter)} err=${r.error || 'none'}`)
  }
  for (const [k, v] of Object.entries(gates)) console.log(`${v ? 'PASS' : 'FAIL'}  ${k}`)

  console.log(`${ok ? 'PASS' : 'FAIL'}  streampower co-evolution runs=${runs.length} ledgers=${runs.filter(r => r.ledger).length} `
    + `deepBedrockDetached=[${deep.map(r => fmt(ledNum(r, 'bedrockDetachedM3'))).join(',')}] `
    + `bareBedrockDetached=[${bare.map(r => fmt(ledNum(r, 'bedrockDetachedM3'))).join(',')}] `
    + `maxCoverBookErr=${fmt(Math.max(0, ...runs.map(r => num(r.coverBookErr) === null ? 0 : r.coverBookErr)))} `
    + `maxUpliftErr=${fmt(Math.max(0, ...runs.map(r => num(r.upliftErr) === null ? 0 : r.upliftErr)))} `
    + `maxGainErr=${fmt(Math.max(0, ...runs.map(r => num(r.gainErr) === null ? 0 : r.gainErr)))} `
    + `minCoverBookArming=${fmt(Math.min(...runs.map(r => num(r.coverBookArming) === null ? 0 : r.coverBookArming)))} `
    + `minUpliftArming=${fmt(Math.min(...unmasked.map(r => num(r.upliftSourceArming) === null ? 0 : r.upliftSourceArming)))} `
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
