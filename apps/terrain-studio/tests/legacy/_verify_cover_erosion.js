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
// DECIDED SINCE, and the reason this paragraph is amended rather than deleted. The open decision was
// closed as TWO NAMED FRAMES (ADR-005 / src/core/height-frame.js): the viewport keeps
// `display-autolevel`, and a physical node takes metres from a stable datum through the explicit
// adapter. Hydraulic's solidTop is therefore `physical-stable`, and the assertion above holds as
// written. That is now itself gated — `physicalFrameIsStableNotAutolevel` measures which of the two
// frames production actually used, on this file's own authored base field, and requires the
// autolevelled alternative to disagree on the same fixture so the check is not vacuous. Nothing was
// baked in: the frame-free gates below are unchanged and remain frame-free.
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
//
// ---------------------------------------------------------------------------------------------
// S3.5d EXTENSION — this file is also the evidence for hydraulic's COMPLIANCE FLIP
// ---------------------------------------------------------------------------------------------
// S3.5's last node made `hydraulic` compliant in src/core/transport-classes.js, emptying the
// exemption ledger. No new implementation was needed — S3.3's cover pass is unchanged — so the
// question this file had to answer is whether the claims that row now makes were actually gated.
// Three were not, and it is the same file rather than a new one because a second oracle over the
// same node and the same fixtures is how a suite ends up with a gate nobody can locate.
//
// 1. THE COVER-BOOK BOUND SCALED WITH THE WRONG THING, and it was this file's own copy of the
//    defect S3.5b measured at 1e9x too loose elsewhere. `coverBookBound` used the Float32 unit over
//    the sum of STANDING cover thicknesses — on the deep fixture, 500 m under every cell whether or
//    not a grain moved. MEASURED on the shipping square GPU path: the shipped bound sat 2.26x under
//    the transport it constrains, so the closure could not have seen 40% of the book go missing.
//    The correct unit is DOUBLE over the absolute per-cell CHANGE (production accumulates its book
//    from the published float32 rasters and so does this file, so the float32 rounding is common to
//    both sides and cancels term by term). Corrected arming: 4.8e11 .. 2.2e12. Both endpoints are
//    re-measured on every run — `theLooseCoverBookBoundIsDemonstrablyTooLoose` recomputes the
//    rejected bound on the same fixture in the same pass — so this is a live delta, not a note.
// 2. THE LEDGER BOUND HAD NO ARMING AT ALL. `ledgerMassCloses` kept the Float32 unit, correctly —
//    the loss side comes from the solver's own float32 accumulations and the residual is dominated
//    by the kernel's real non-conservation, so a double unit would go red on physics — but nothing
//    checked it was smaller than the loss term. Measured: 4.2x on the pipe path, 282-340x on the
//    droplet paths. Tight, armed, and now asserted rather than assumed.
// 3. THE REFUSAL HAD NEVER BEEN EXERCISED. `resolveCoverLoss` publishes a boundary term only where
//    a solver names one independently, and publishes NOTHING for `gpu-droplets` and `gpu-combined`,
//    whose export is sumIn - sumOut (`exportedDerived: true`). Every run in this file was pipe-only,
//    so no run had ever reached either engine under cover demand: the refusal was a claim in the
//    manifest with no gate behind it — the declared-but-never-filled shape, one level up. Two runs
//    now reach them, and the refusal is graded on four readings (flag false, reason names the
//    derived export, none of the four loss keys present, and the engine that ran is the one
//    expected — so a silent fallback to the CPU droplet kernel, which WOULD publish an honest
//    itemised claim, cannot pass as a refusal).
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
  'loss-derived-from-field-sums',// the loss term becomes eroded-deposited: a closure that cannot fail
  'cover-alters-published-height',// wiring cover moves the terrain: an unauthorised C3 re-bless
  // S3.5d. The same defect on the OTHER side of the fence: an engine that has no itemised export
  // stops refusing and publishes one anyway.
  'derived-export-engine-claims-a-loss',
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

    // Reduction bounds, computed rather than inherited (sprint-03:108-111).
    // gamma_n = (n*u)/(1 - n*u); a sum of N terms each carrying unit roundoff u accumulates at most
    // gamma_(N-1)*sum(|term|). Production reduces too, so the two-sided bound uses 2N terms.
    //
    // TWO UNITS, AND WHICH ONE APPLIES IS A PROPERTY OF THE ARITHMETIC, NOT A DIAL.
    //   boundF32  the quantity passes through a Float32 accumulation on at least one side — the
    //             solver's own apron/particle sums are float32 texture reads, and the physical
    //             non-conservation of the GPU kernel lands here too.
    //   boundF64  BOTH sides are double reductions over the SAME float32 samples, so the float32
    //             rounding is common to both and cancels term by term; only the reduction ordering
    //             is left. This is the correct unit for the cover book, and using the float32 one
    //             there was this file's own instance of the defect S3.5b measured at 1e9x too loose.
    const U32 = Math.pow(2, -24), U64 = Math.pow(2, -53)
    const gammaOf = (u, n) => (n * u) / (1 - n * u)
    const boundFor = (nTerms, absSum) => 2 * gammaOf(U32, Math.max(1, 2 * nTerms)) * absSum + 1e-6
    const boundF64 = (nTerms, absSum) => 2 * gammaOf(U64, Math.max(1, 2 * nTerms)) * absSum + 1e-9

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
      // S3.3 EXTENSION. The stack identity solidTop = bedrockHeight + soilDepth + sedimentDepth +
      // sandDepth was, as this file first shipped, only ever checked as a VOLUME. It is a
      // per-sample statement and the term that makes it readable off a port is `bedrockHeight`,
      // which production now publishes; asserting it sample-by-sample is strictly stronger than
      // integrating it, and three of the five mutations turn the per-sample form red.
      bedrockOut: portOk(findOut('bedrockHeight'), 'm'),
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
        if (mutation === 'cover-alters-published-height' && soilIn) {
          // WIRING COVER MOVES THE TERRAIN. Sprint-03 pre-authorises a stated `C3` re-bless for
          // Hydraulic, and this is the shape of one taken without saying so: the same graph erodes
          // differently the moment a soil field is attached, so every downstream digest, thumbnail
          // and saved document changes and nothing announces it. The perturbation is applied only
          // where cover exists, so the UNWIRED evaluation below — which is the pre-S3.3 call shape,
          // two arguments and no state demand — comes back untouched and the two stop matching.
          const h = vals.get(primaryId)
          if (h && h.length === soilIn.length) {
            const m = Float32Array.from(h)
            for (let i = 0; i < m.length; i++) if (soilIn[i] > 0) m[i] = Math.fround(m[i] * 1.000001)
            vals.set(primaryId, m)
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
        if (mutation === 'loss-derived-from-field-sums' && led) {
          // THE DEFECT THIS SUITE KEEPS FINDING, in a new place. The boundary loss stops being a
          // quantity the solver accumulated over cells or particles the published field does not
          // control, and becomes `eroded - deposited` — a subtraction of the very two sums it is
          // then compared against. `ledgerMassCloses` CANNOT see this: under it that gate holds
          // exactly, for any implementation, including one that deletes the terrain. Only the
          // itemisation gate can, which is the whole reason itemisation is asserted and not merely
          // printed.
          led.exportedOrSuspendedM3 = (led.coverConsumedM3 || 0) + (led.bedrockDetachedM3 || 0)
            - (led.depositedM3 || 0)
        }
        if (mutation === 'derived-export-engine-claims-a-loss' && led && led.lossClaimed === false) {
          // THE REFUSAL COLLAPSES. `gpuHydraulicDroplets` and `gpuHydraulicCombined` both define
          // `exported` as sumIn - sumOut and flag it (`exportedDerived: true`), so the node declines
          // to publish a boundary term for them. Here it publishes one anyway, and the value is
          // `consumed + detached - deposited` — a restatement of the three terms it is then compared
          // against. `ledgerMassCloses` cannot see this: under it that identity holds EXACTLY, for
          // any implementation, including one that deletes the terrain. Only the refusal gate can,
          // which is the whole reason the refusal is asserted rather than merely printed.
          // Guarded on `lossClaimed === false` so it reaches only the runs that legitimately refuse;
          // on the itemised runs it is a no-op and the log says so.
          delete led.lossClaimed
          led.exportedOrSuspendedM3 = (led.coverConsumedM3 || 0) + (led.bedrockDetachedM3 || 0)
            - (led.depositedM3 || 0)
          led.boundaryExportedM3 = led.exportedOrSuspendedM3
          led.suspendedM3 = 0
          led.lossSource = 'gpu-sum-difference'
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
    // THREE STAGE CONFIGURATIONS, and the last two are not variety — they are the only way to reach
    // the engines whose boundary export is DERIVED. `resolveCoverLoss` (src/plugins/ero/hydraulic.js)
    // publishes a loss term only where the solver NAMES one independently: the pipe kernel's apron
    // ring, or the CPU droplet solver's per-particle counters. `gpuHydraulicDroplets` and
    // `gpuHydraulicCombined` both define `exported` as sumIn - sumOut and say so
    // (`exportedDerived: true`, src/core/gpu.js:775, :796), which is a closure that holds by
    // construction for any implementation including one that deletes the terrain — so on those two
    // the node must publish NO claim and name the reason. Until S3.5d nothing ran them under cover
    // demand, so that refusal was a claim in the manifest with no gate behind it.
    const DROPLET_COMMON = { droplets: 12000, lifetime: 48, dropletErode: 0.35, dropletDeposit: 0.28,
      dropletCapacity: 6, dropletInertia: 0.05, evap: 0.02, gravity: 4, radius: 2, seed: 1 }
    const STAGE_MODES = {
      // Pipe only. Square + GPU reaches `gpuHydraulicPipes` (apron ring, itemised); square + CPU and
      // hex fall to `hydraulicErode` (per-particle counters, itemised).
      pipe: { params: { pipeEnabled: true, dropletEnabled: false, engine: null, feat: 1,
        pipeIters: 48, pipeErode: 0.35, pipeDeposit: 0.28, pipeCapacity: 6, pipeInertia: 0.05,
        radius: 2, seed: 1 }, claim: 'itemised' },
      // Droplet only on the GPU -> `gpu-droplets`, exportedDerived.
      droplet: { params: { pipeEnabled: false, dropletEnabled: true, engine: null, feat: 1,
        ...DROPLET_COMMON }, claim: 'refused', engineExpected: 'gpu-droplets' },
      // Both stages on the GPU -> the single fused `gpu-combined` kernel, also exportedDerived.
      combined: { params: { pipeEnabled: true, dropletEnabled: true, engine: null, feat: 1,
        pipeIters: 48, pipeErode: 0.35, pipeDeposit: 0.28, pipeCapacity: 6, pipeInertia: 0.05,
        ...DROPLET_COMMON }, claim: 'refused', engineExpected: 'gpu-combined' },
    }

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
    // The RAW engine name, which lives beside `.cover` rather than inside it. Without it a GPU run
    // that silently fell back to the CPU kernel would read as coverage — the fallback is legitimate
    // production behaviour (`gpuReady()`, `gpuDropletsReady()`), so which kernel ran has to be
    // measured rather than inferred from the flags this file set.
    const grabEngine = () => {
      try {
        return (typeof hydroMassDiag !== 'undefined' && hydroMassDiag
          && typeof hydroMassDiag.engine === 'string') ? hydroMassDiag.engine : null
      } catch (e) { return null }
    }

    const runOne = (lattice, useGpu, fixture, stage) => {
      const mode = STAGE_MODES[stage || 'pipe']
      const afterParams = mode.params
      const r = { key: `${lattice}/${useGpu ? 'gpu' : 'cpu'}/${fixture}`
          + (stage && stage !== 'pipe' ? '/' + stage : ''),
        lattice, gpu: !!useGpu, stage: stage || 'pipe', claimExpected: mode.claim,
        engineExpected: mode.engineExpected || null,
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
        const demanded = new Set([primaryId, 'out', 'height', 'solidTop', 'bedrockHeight',
          'soilDepth', 'sedimentDepth', 'sandDepth'])

        // --- BEFORE: both stages disabled. Contractually an identity pass that echoes cover and
        //     publishes an all-zero cover ledger. It is also how the before-state solidTop is
        //     obtained in production's own frame, without this file inventing one.
        nd.params = { ...beforeParams }
        const rawB = TYPES.hydraulic.eval(nd.params, ins, nd, { demanded })
        const vB = readValues(rawB)
        const ledB = grabLedger()
        const soilB = grab(vB, 'soilDepth'), sedB = grab(vB, 'sedimentDepth')
        const sandB = grab(vB, 'sandDepth'), topB = grab(vB, 'solidTop')
        const bedB = grab(vB, 'bedrockHeight')
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
        r.engine = grabEngine()
        const soilA = grab(vA, 'soilDepth'), sedA = grab(vA, 'sedimentDepth')
        const sandA = grab(vA, 'sandDepth'), topA = grab(vA, 'solidTop')
        const bedA = grab(vA, 'bedrockHeight')
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

        // --- S3.3 EXTENSION: the byte-identity control ------------------------------------------
        // The SAME transport pass called the way the pre-S3.3 build was called: two arguments, no
        // cover attached, no state demanded. Sprint-03 pre-authorises a stated `C3` re-bless for
        // Hydraulic, but only as a stated one — a graph that wires no cover must produce the terrain
        // it produced yesterday, byte for byte, and that has to be MEASURED rather than argued from
        // the fact that the digest recipe happens not to demand a state port. Taken after the ledger
        // snapshot above, because a third evaluation replaces hydroMassDiag.
        const rawU = TYPES.hydraulic.eval(nd.params, [ins[0], null], nd, { demanded: new Set([primaryId]) })
        const primU = grab(readValues(rawU), primaryId)
        r.unwiredLength = primU ? primU.length : null
        r.unwiredMatchesWired = bitEqual(primU, primA)

        // --- S3.3 EXTENSION: the solid-stack identity, PER SAMPLE ------------------------------
        //   solidTop = bedrockHeight + soilDepth + sedimentDepth + sandDepth
        // asserted at every sample of BOTH passes, not integrated. The tolerance is derived, not
        // picked: each published raster is Float32, the sum is formed in double, so the largest
        // legitimate residual is a few units in the last place of the biggest term. 2^-23 is one
        // Float32 ulp relative, and 4x that over the sum of magnitudes covers the rounding of the
        // stored difference plus the reduction. A residual above it is a stack that does not close.
        //
        // ABSENCE OF EVIDENCE IS RED: `samples` must reach 2N, so a missing bedrockHeight raster or
        // a short one fails here rather than silently checking nothing.
        const F32_ULP = Math.pow(2, -23)
        const stack = (top, bed, so, se, sa) => {
          const acc = { samples: 0, violations: 0, maxResidualM: 0, maxRatio: 0 }
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
            const ratio = Math.abs(res) / tol
            if (ratio > acc.maxRatio) acc.maxRatio = ratio
          }
          return acc
        }
        // --- S3.3 EXTENSION: WHICH FRAME solidTop is actually in ---------------------------------
        // The header says exactly one gate here is frame-sensitive and that the decision was open
        // when this file was written. It is now taken — two named frames, and a physical node takes
        // `physical-stable`. That is a claim about production's arithmetic, so it is measured, not
        // read off a label: the BEFORE pass moved no material, so its solidTop must be the base
        // field this file AUTHORED, mapped through the datum and relief production reports.
        //
        // AND THE COMPARISON IS ARMED IN PLACE. A bound only means something between two measured
        // endpoints, so the autolevelled alternative is evaluated on the same fixture and required
        // to DISAGREE by three orders of magnitude more than the tolerance. If the two frames
        // happened to coincide here, the agreement above would be evidence of nothing.
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
            tolM: 4 * Math.pow(2, -23) * (Math.abs(dat) + Math.abs(rel)) + 1e-6 }
        }

        const sB = stack(topB, bedB, soilB, sedB, sandB), sA = stack(topA, bedA, soilA, sedA, sandA)
        r.stackIdentity = {
          samples: sB.samples + sA.samples, expected: 2 * N,
          violations: sB.violations + sA.violations,
          maxResidualM: Math.max(sB.maxResidualM, sA.maxResidualM),
          maxRatio: Math.max(sB.maxRatio, sA.maxRatio),
        }

        // --- S3.3 EXTENSION: the loss term must be ITEMISED, not derived -----------------------
        // Every number the ledger prints for the boundary is asserted here, because a quantity
        // worth printing is worth failing on. `exportedOrSuspendedM3` must equal its own named
        // components — boundary export plus still-suspended load minus the NAMED mass source the
        // CPU brush creates at the border (legacy.js erode1; the same term _verify_erosion_mass.js
        // G2 gates as `sumIn - sumOut = exported + lost - brushClipGain`). The three are each
        // accumulated by the solver over cells or particles the published field does not control.
        //
        // This is what `ledgerMassCloses` cannot do: replace the loss with `eroded - deposited` and
        // that gate holds by construction — the `loss-derived-from-field-sums` mutation is exactly
        // that substitution, and this is the gate it turns red.
        if (led) {
          const fin = v => (typeof v === 'number' && Number.isFinite(v)) ? v : null
          const b = fin(led.boundaryExportedM3), s = fin(led.suspendedM3), g = fin(led.brushClipGainM3) || 0
          const e = fin(led.exportedOrSuspendedM3)
          const itemSum = (b === null ? NaN : b) + (s === null ? NaN : s) - g
          const absSum = Math.abs(b || 0) + Math.abs(s || 0) + Math.abs(g) + Math.abs(e || 0)
          // Double-precision reassociation only: three products summed versus one product of the
          // sum. 8 * eps * sum(|term|) is that bound written out, plus a floor for an all-zero book.
          r.lossBound = 8 * Number.EPSILON * absSum + 1e-9
          r.lossItemErr = (e === null || !Number.isFinite(itemSum)) ? null : Math.abs(e - itemSum)
          r.lossSource = typeof led.lossSource === 'string' ? led.lossSource : null
          r.lossItemised = r.lossItemErr !== null && r.lossItemErr <= r.lossBound
            && !!r.lossSource && b !== null && s !== null
          // ...AND THE REFUSAL, READ AS PUBLISHED. On an engine whose export is sumIn - sumOut the
          // node must publish `lossClaimed: false`, name which engine refused, and carry NONE of the
          // four loss keys — a partially-populated refusal is a claim wearing a disclaimer.
          r.lossClaimed = led.lossClaimed !== false
          r.lossKeys = ['exportedOrSuspendedM3', 'boundaryExportedM3', 'suspendedM3', 'brushClipGainM3']
            .filter(k => Object.prototype.hasOwnProperty.call(led, k))
        }

        // --- the frame-free readings -----------------------------------------------------------
        if (soilA && sedA && sandA && soilB && sedB && sandB) {
          const A = r.areaExpected
          let dCover = 0, absChange = 0, absStanding = 0, minCoverAfter = Infinity, maxSedRise = -Infinity
          for (let i = 0; i < N; i++) {
            const c1 = soilA[i] + sedA[i] + sandA[i]
            const c0 = soilB[i] + sedB[i] + sandB[i]
            dCover += A * (c1 - c0)
            // WHAT THE BOUND SCALES WITH — the whole point of the S3.5d correction here.
            //   absChange    the cover this pass actually MOVED. Production accumulates its book
            //                from the published float32 rasters (src/plugins/ero/hydraulic.js
            //                coverPass) and so does this line, from the same values, so the only
            //                residual is double reduction ordering.
            //   absStanding  the cover LYING THERE. The bound this file shipped with. On the deep
            //                fixture that is 500 m over every cell whether or not a grain moved, so
            //                the tolerance grew with the fixture instead of with the transport.
            //                Kept, measured, and required BELOW the threshold the corrected one
            //                passes, so the correction is a live delta rather than a claim.
            absChange += A * Math.abs(c1 - c0)
            absStanding += A * (Math.abs(c1) + Math.abs(c0))
            if (c1 < minCoverAfter) minCoverAfter = c1
            const rise = sedA[i] - sedB[i]
            if (rise > maxSedRise) maxSedRise = rise
          }
          r.dCoverM3 = dCover
          r.coverAbsChange = absChange
          r.minCoverAfter = minCoverAfter
          r.maxSedimentRiseM = maxSedRise
          r.coverBookBound = boundF64(N, absChange)
          r.coverBookBoundLoose = boundFor(N, absStanding)
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
        if (led) {
          const lhs = (led.coverConsumedM3 || 0) + (led.bedrockDetachedM3 || 0)
          const rhs = (led.depositedM3 || 0) + (led.exportedOrSuspendedM3 || 0)
          const abs = Math.abs(led.coverConsumedM3 || 0) + Math.abs(led.bedrockDetachedM3 || 0)
            + Math.abs(led.depositedM3 || 0) + Math.abs(led.exportedOrSuspendedM3 || 0)
          r.ledgerErr = Math.abs(lhs - rhs)
          // FLOAT32 UNIT HERE, AND DELIBERATELY — unlike the cover book above. The loss side comes
          // from the SOLVER's own float32 accumulations (the apron ring sums texture reads over
          // simN^2 cells; the droplet counters accumulate per particle), and the residual is
          // dominated by the kernel's real non-conservation rather than by reduction ordering. A
          // double unit here would go red on physics. The ARMING is asserted separately below so the
          // looser unit cannot hide a dropped loss term.
          r.ledgerBound = boundFor(N, abs)
          r.ledgerCloses = r.ledgerErr <= r.ledgerBound
          r.ledgerArming = r.ledgerBound > 0
            ? Math.abs(led.exportedOrSuspendedM3 || 0) / r.ledgerBound : 0
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
          let dSolid = 0, abs = 0, moved = 0
          for (let i = 0; i < N; i++) {
            dSolid += A * (topA[i] - topB[i])
            abs += A * (Math.abs(topA[i]) + Math.abs(topB[i]))
            moved += A * Math.abs(topA[i] - topB[i])
          }
          r.dSolidM3 = dSolid
          r.solidBound = boundFor(N, abs)
          r.solidErr = Math.abs(dSolid + (led.exportedOrSuspendedM3 || 0))
          r.solidCloses = r.solidErr <= r.solidBound

          // S3.3 EXTENSION — THE SAME CLAIM, SCALED BY THE TRANSPORT INSTEAD OF THE ELEVATIONS.
          // `abs` above sums ELEVATIONS, which carry the datum and the full relief, so the bound it
          // produces is set by how high the terrain is rather than by how much material moved.
          // MEASURED on the shipping square GPU fixture: bound 6.351e7 m3 against an export term of
          // 2.292e5 m3 — a factor of 277. Zeroing the loss term there leaves solidErr at 2.292e5 and
          // the gate above still passes, so on that path it cannot see the quantity it is about.
          // (The suite is not blind to it — `ledgerMassCloses` scales its bound by the ledger's own
          // terms and does go red — but this gate is the only one that ties the published solidTop
          // RASTER to the ledger, and that tie was slack exactly where ADR-002 says CPU evidence
          // does not carry: the GPU path.)
          //
          // `moved` is the volume the pass actually displaced, which is the magnitude this identity
          // is made of. THE ARMING ENDPOINT IS MEASURED IN PLACE, on every run, as the second half
          // of the gate: |exported| must exceed the bound. That inequality is the proof that a build
          // which dropped the loss term would land at solidErr = |dSolid| = |exported| > bound and
          // go red — arming checked continuously rather than once in a control.
          r.movedVolumeM3 = moved
          r.solidTransportBound = boundFor(N, moved + Math.abs(led.exportedOrSuspendedM3 || 0))
          r.solidClosesAgainstTransport = r.solidErr <= r.solidTransportBound
          r.solidGateArming = Math.abs(led.exportedOrSuspendedM3 || 0) / r.solidTransportBound
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
    // The particle-brush accumulator needs WebGL2 float BLENDING, which is a separate capability
    // from a float render target. It is what selects `gpuHydraulicDroplets`/`gpuHydraulicCombined`
    // over the CPU compatibility path, so an unavailable one is absence of evidence for the two
    // derived-export engines and must read as red, not as a silent skip.
    out.gpuDropletsAvailable = false
    try { out.gpuDropletsAvailable = !!(typeof gpuDropletsReady === 'function' && gpuDropletsReady()) }
    catch (e) { out.gpuDropletsAvailable = false }

    const plan = []
    for (const fx of ['deep', 'bare', 'mixed']) {
      plan.push(['square', false, fx, 'pipe'])
      if (out.gpuAvailable) plan.push(['square', true, fx, 'pipe'])
      plan.push(['hex', false, fx, 'pipe'])
    }
    // The two engines whose export is DERIVED, on the mixed fixture so both cover regimes are live
    // in the same pass. Square + GPU only: `gpuDropletsReady()` is what routes to them and it is
    // false on hex by construction, which is also why the node's hex path has no such refusal.
    if (out.gpuAvailable && out.gpuDropletsAvailable) {
      plan.push(['square', true, 'mixed', 'droplet'])
      plan.push(['square', true, 'mixed', 'combined'])
    }
    for (const [lat, gpu, fx, stage] of plan) out.runs.push(runOne(lat, gpu, fx, stage))

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
  // THE TWO POPULATIONS, split by whether an engine NAMES its boundary export. Everything about the
  // cover stack — the stack identity, the cover book, cover-before-bedrock, sand, the frame — is
  // asserted over BOTH, because none of it involves the loss term. Everything that closes AGAINST
  // the loss term is asserted over the itemised population only, because on the other one there is
  // deliberately no such term to close against; that population is graded by the refusal gate.
  const itemised = runs.filter(r => r.claimExpected === 'itemised')
  const refused = runs.filter(r => r.claimExpected === 'refused')
  // THE REFUSED POPULATION IS NOT EXEMPT FROM BEING MEASURED, only from being closed. The Sprint 3
  // audit rated this story UNSUPPORTED for exactly this: every loss-dependent gate is scoped to the
  // itemised runs — correctly, there is no term to close against on the others — and the effect was
  // that the two SHIPPING GPU engines had no conservation reading at all. Measured there:
  // 7.085e8 m3 unaccounted, 85.96% of transported volume, ledgerErr 880x its own bound, oracle green.
  //
  // Refusing to ATTRIBUTE a loss is honest. Refusing to MEASURE the hole it leaves is not. The
  // residual is already computed on every run, so it is now reported and bounded by a pinned
  // ceiling. That ceiling records current state; it is a deficiency on the record, not a pass mark.
  // It falls when the droplet engines itemise their export the way the pipe path does with its
  // apron ring, and a change that makes it worse fails here.
  const unaccounted = runs.map(r => ({ key: r.key, claim: r.claimExpected,
    err: num(r.ledgerErr), transported: num(r.transportedM3),
    frac: (num(r.ledgerErr) !== null && num(r.transportedM3) > 0) ? r.ledgerErr / r.transportedM3 : null }))
  const refusedUn = unaccounted.filter(u => u.claim === 'refused')
  const maxRefusedFrac = refusedUn.length ? Math.max(...refusedUn.map(u => u.frac === null ? 1 : u.frac)) : null
  const maxItemisedFrac = unaccounted.filter(u => u.claim === 'itemised' && u.frac !== null).length
    ? Math.max(...unaccounted.filter(u => u.claim === 'itemised' && u.frac !== null).map(u => u.frac)) : null
  // PINNED FROM MEASUREMENT, and the two numbers say the whole thing:
  //     itemised paths   6.25e-7 of transported volume unaccounted
  //     refused paths    0.8596  of transported volume unaccounted   (gpu-droplets, gpu-combined)
  // A factor of 1.4 million between them. The ceiling sits just above the measured worst case so a
  // regression fails, and deliberately NOT at a round number that would look like a target.
  const UNACCOUNTED_CEILING = 0.87

  const maxCoverBookErr = Math.max(0, ...runs.map(r => num(r.coverBookErr) === null ? 0 : r.coverBookErr))
  const deepBedrock = deep.map(r => ledNum(r, 'bedrockDetachedM3'))
  const bareBedrock = bare.map(r => ledNum(r, 'bedrockDetachedM3'))

  const gates = {
    // --- the refused population is measured, even though it cannot be closed --------------------
    refusedPathsAreMeasuredNotSilent: refused.length > 0
      && refusedUn.every(u => u.frac !== null && Number.isFinite(u.frac) && u.transported > 0),
    unaccountedVolumeDoesNotGrow: maxRefusedFrac !== null && maxRefusedFrac <= UNACCOUNTED_CEILING,
    // The itemised paths must remain FAR better than the refused ones, or the ceiling above would be
    // quietly normalising the whole story rather than one population.
    itemisedPathsAccountForNearlyEverything: maxItemisedFrac !== null && maxItemisedFrac < 1e-3,

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
    // S3.5d — THE BOUND IS SMALLER THAN THE TERM IT CONSTRAINS, measured on every run rather than
    // argued once. WHAT IT SCALES WITH is the absolute per-cell cover CHANGE: the thickness this
    // pass moved. It used to scale with the sum of STANDING thicknesses, which on the deep fixture
    // is 500 m over every cell whether or not a grain moved — the defect S3.5b measured at 1e9x too
    // loose, sitting unnoticed in this file the whole time. The threshold is 1e6: far above anything
    // a terrain-scaled bound reaches and far below the arithmetic ceiling (boundF64 is
    // 2*gamma64(2N) relative, ~1.5e-12 at N ~ 4e3, so the ratio cannot exceed ~6.6e11 however tight
    // the implementation), so a silent loosening of four orders is caught rather than merely absent.
    coverBookBoundIsSmallerThanTheTransport: every(runs, r => num(r.coverBookArming) !== null
      && r.coverBookArming > 1e6),
    // ...and the OTHER endpoint, so the correction is a live delta rather than a claim about a
    // version nobody can re-run. The rejected bound is recomputed on the same fixture in the same
    // run and must FAIL the threshold the corrected one passes.
    theLooseCoverBookBoundIsDemonstrablyTooLoose: every(runs, r => num(r.coverBookArmingLoose) !== null
      && r.coverBookArmingLoose < 1e6 && num(r.coverBookArming) !== null && r.coverBookArming > 1e6),
    ledgerMassCloses: every(itemised, r => r.ledgerCloses === true),
    // ...and THAT bound is smaller than the loss term too, or the closure is insensitive to the very
    // quantity it exists to check. Measured on every itemised run: an implementation that dropped
    // the boundary term would land at ledgerErr = |exported| and must therefore exceed the bound.
    ledgerBoundIsSmallerThanTheLossItConstrains: every(itemised, r => num(r.ledgerArming) !== null
      && r.ledgerArming > 1),
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
    solidVolumeMatchesNetTransport: every(itemised, r => r.solidCloses === true),

    // --- S3.3 EXTENSIONS -------------------------------------------------------------------------
    // The frame decision the expected-red register left open, closed and MEASURED: solidTop is the
    // authored field through a stable datum, and the autolevelled alternative is evaluated on the
    // same fixture and shown to disagree, so the agreement is evidence rather than a coincidence.
    physicalFrameIsStableNotAutolevel: every(runs, r => !!r.frame && r.frame.name === 'physical-stable'
      && num(r.frame.maxErrVsStableM) !== null && r.frame.maxErrVsStableM <= r.frame.tolM
      && num(r.frame.maxErrVsAutolevelM) !== null && r.frame.maxErrVsAutolevelM > 1e3 * r.frame.tolM),
    // The same solid-volume claim under a bound scaled by the transport rather than by the
    // elevations, plus the arming endpoint measured on every run: the bound must be SMALLER than
    // the export term it constrains, or the closure above is insensitive to it. See the derivation
    // at the measurement — the shipped bound is 277x too loose on the square GPU path.
    solidVolumeBoundIsSmallerThanTheTermItConstrains: every(itemised,
      r => r.solidClosesAgainstTransport === true
        && num(r.solidGateArming) !== null && r.solidGateArming > 1),
    // The story's headline identity, at every sample of both passes rather than under an integral.
    // Armed by three of the six mutations: bedrock-first-kernel and identity-ignores-deposition
    // both hand back a cover raster that no longer matches the bedrock the node computed, and
    // sand-nonzero adds a quarter metre of aeolian cover to a stack that has none.
    solidStackIdentityClosesPerSample: report.ports.bedrockOut === true
      && every(runs, r => !!r.stackIdentity && r.stackIdentity.samples === r.stackIdentity.expected
        && r.stackIdentity.expected > 0 && r.stackIdentity.violations === 0),
    // The boundary loss must be the sum of its own NAMED components, never a difference of the two
    // field sums it is compared against. Armed by loss-derived-from-field-sums, which is the only
    // mutation `ledgerMassCloses` is structurally unable to detect.
    coverLossIsItemizedNotDerived: every(itemised, r => r.lossItemised === true),
    // S3.5d — AND WHERE NO ENGINE NAMES ONE, THE NODE PUBLISHES NOTHING AND SAYS WHY. This is the
    // other half of the same rule, and until now it was a claim in the manifest with no gate behind
    // it: no run reached `gpuHydraulicDroplets` or `gpuHydraulicCombined` under cover demand, so the
    // refusal path had never been exercised at all. Both define `exported` as sumIn - sumOut and
    // flag it (`exportedDerived: true`, src/core/gpu.js:775, :796), which closes by construction for
    // any implementation including one that deletes the terrain.
    //
    // FOUR SEPARATE READINGS, because a partial refusal is a claim wearing a disclaimer: the flag is
    // false, the reason names the derived export, NOT ONE of the four loss keys is present, and the
    // engine that actually ran is the one this file expected — a silent fallback to the CPU droplet
    // kernel would otherwise publish an honest itemised claim here and read as coverage.
    // Armed by `derived-export-engine-claims-a-loss`.
    derivedExportEnginesPublishNoLossClaim: every(refused, r => r.lossClaimed === false
      && r.lossSource === 'engine-export-is-derived'
      && Array.isArray(r.lossKeys) && r.lossKeys.length === 0
      && r.engine === r.engineExpected),
    // ...over BOTH of them, and over a real transport rather than a printed nothing. Without this
    // the gate above would be satisfied by a population of one, or of none.
    bothDerivedExportEnginesMeasured: report.gpuDropletsAvailable === true
      && refused.length === 2
      && new Set(refused.map(r => r.engine)).size === 2
      && refused.every(r => r.ran === true && num(r.transportedM3) !== null && r.transportedM3 > 0),
    // A PRECONDITION gate, in the same category as `hexRowCountIsNotRes` and deliberately unarmed by
    // a mutation: it establishes that the ITEMISED population reached both of its engines too — the
    // pipe kernel's apron ring on square+GPU, the CPU droplet solver's particle counters on square
    // +CPU and hex. A build where `gpuReady()` quietly went false would run one engine three times
    // and every closure above would still pass.
    bothItemisedEnginesMeasured: itemised.some(r => r.engine === 'pipes' && r.ran === true
      && r.lossSource === 'pipe-apron-ring')
      && itemised.some(r => r.engine === 'droplets' && r.ran === true
        && r.lossSource === 'droplet-particle-counters'),
    // Cover changes the BOOKS, not the terrain. S3.3 implements transport ORDER — loose cover first,
    // bedrock second — and not a differential-erodibility law, which nobody has specified and which
    // would be a fabricated constant. So the published height with cover attached must be the
    // published height without it, bit for bit, and the `C3` re-bless stays unspent. Armed by
    // cover-alters-published-height.
    coverDoesNotMoveThePublishedHeight: every(runs, r => r.unwiredMatchesWired === true
      && r.unwiredLength === r.N),
    // A PRECONDITION gate, in the same category as `hexRowCountIsNotRes` above and deliberately not
    // armed by a mutation. `coverInputPortsDeclared` reads DESCRIPTORS, and for soilDepth and
    // sedimentDepth the three fixtures prove the values reach the arithmetic — deep, bare and mixed
    // produce three different ledgers from the same terrain. `precipitation` has no such witness:
    // nothing consumes it in S3.3, so a descriptor pointing at a slot the evaluator never reads
    // would look exactly like a working port. This makes production say which slot it indexed and
    // whether a field of the right length arrived there, so "declared" and "filled" are two separate
    // measured claims rather than one.
    precipitationSlotIsFilledAndDeclaredUnconsumed: every(runs, r => !!r.ledger
      && r.ledger.precipitationWired === true && r.ledger.precipitationConsumed === false
      && r.ledger.precipitationSlot === report.ports.slots.precip
      && r.ledger.soilSlot === report.ports.slots.soil
      && r.ledger.sedimentSlot === report.ports.slots.sed),

    // --- the shipping square GPU path is separate evidence from the compatibility path -----------
    gpuSquarePathMeasured: report.gpuAvailable === true
      && runs.some(r => r.gpu === true && r.lattice === 'square' && r.ran === true),
    gpuSquarePathCloses: report.gpuAvailable === true
      && every(itemised.filter(r => r.gpu === true),
        r => r.coverBookCloses === true && r.ledgerCloses === true)
      && every(refused, r => r.coverBookCloses === true),

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
    console.log(`  ${r.key.padEnd(26)} W=${r.W} H=${r.H} area=${fmt(r.areaExpected)} `
      + `engine=${r.engine || '-'} claim=${r.claimExpected} lossClaimed=${r.lossClaimed} `
      + `lossSrc=${r.lossSource || '-'} lossKeys=[${(r.lossKeys || []).join(',')}] `
      + `dCover=${fmt(r.dCoverM3)} coverBookErr=${fmt(r.coverBookErr)} `
      + `bound=${fmt(r.coverBookBound)} arming=${fmt(r.coverBookArming)} `
      + `boundLoose=${fmt(r.coverBookBoundLoose)} armingLoose=${fmt(r.coverBookArmingLoose)} `
      + `ledgerArming=${fmt(r.ledgerArming)} minCover=${fmt(r.minCoverAfter)} `
      + `err=${r.error || 'none'}`)
  }
  for (const [k, v] of Object.entries(gates)) console.log(`${v ? 'PASS' : 'FAIL'}  ${k}`)

  console.log(`${ok ? 'PASS' : 'FAIL'}  cover erosion coverPorts=${report.ports.soilIn && report.ports.sedIn && report.ports.precipIn} `
    + `statePorts=${report.ports.solidTopOut && report.ports.soilOut && report.ports.sedOut && report.ports.sandOut} `
    + `runs=${runs.length} ledgers=${runs.filter(r => r.ledger).length} `
    + `deepBedrockDetached=[${deepBedrock.map(v => v === null ? 'n/a' : fmt(v)).join(',')}] `
    + `bareBedrockDetached=[${bareBedrock.map(v => v === null ? 'n/a' : fmt(v)).join(',')}] `
    + `unaccountedRefused=${maxRefusedFrac === null ? 'n/a' : maxRefusedFrac.toFixed(4)} unaccountedItemised=${maxItemisedFrac === null ? 'n/a' : maxItemisedFrac.toExponential(2)} maxCoverBookErr=${fmt(maxCoverBookErr)} gpu=${report.gpuAvailable} `
    + `stackViolations=${runs.reduce((a, r) => a + ((r.stackIdentity && r.stackIdentity.violations) || 0), 0)} `
    + `maxStackResidualM=${fmt(Math.max(0, ...runs.map(r => (r.stackIdentity && r.stackIdentity.maxResidualM) || 0)))} `
    + `maxLossItemErr=${fmt(Math.max(0, ...runs.map(r => (typeof r.lossItemErr === 'number' ? r.lossItemErr : 0))))} `
    + `lossSources=[${Array.from(new Set(runs.map(r => r.lossSource || 'none'))).sort().join(',')}] `
    + `engines=[${Array.from(new Set(runs.map(r => r.engine || '-'))).sort().join(',')}] `
    + `itemised=${itemised.length} refused=${refused.length} `
    + `unwiredMatchesWired=${runs.filter(r => r.unwiredMatchesWired === true).length}/${runs.length} `
    // Scoped to the itemised population, like the gates that read them: a refused run has no loss
    // term, so folding its absent arming into a MINIMUM would print 0 and read as an unarmed gate.
    + `minCoverBookArming=${fmt(Math.min(...runs.map(r => num(r.coverBookArming) === null ? 0 : r.coverBookArming)))} `
    + `maxCoverBookArmingLoose=${fmt(Math.max(0, ...runs.map(r => num(r.coverBookArmingLoose) === null ? 1e99 : r.coverBookArmingLoose)))} `
    + `minLedgerArming=${fmt(Math.min(...itemised.map(r => num(r.ledgerArming) === null ? 0 : r.ledgerArming)))} `
    + `minSolidArming=${fmt(Math.min(...itemised.map(r => num(r.solidGateArming) === null ? 0 : r.solidGateArming)))} `
    + `maxSolidErr=${fmt(Math.max(0, ...itemised.map(r => num(r.solidErr) === null ? 0 : r.solidErr)))} `
    + `frame=${(runs.find(r => r.frame) || { frame: {} }).frame.name || 'n/a'} `
    + `maxErrVsStableM=${fmt(Math.max(0, ...runs.map(r => (r.frame && r.frame.maxErrVsStableM) || 0)))} `
    + `maxErrVsAutolevelM=${fmt(Math.max(0, ...runs.map(r => (r.frame && r.frame.maxErrVsAutolevelM) || 0)))} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
