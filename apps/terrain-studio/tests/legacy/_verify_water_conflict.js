// S4.6 — does an impossible river guide TELL you, or does it get quietly fixed?
//
// The story's sentence is "conflicts are surfaced, not corrected", and the armed failure is a
// conflict that gets silently smoothed away. That is not a hypothetical failure mode: the whole
// reason the sprint exists is that the reference product writes water into height "on any terrain,
// whether it can sustain rivers or not", and the cheapest way to make an authored guide look valid
// is to average its deficit down until nobody notices.
//
// This is a PURE-MODULE oracle. It imports src/core/water-conflict.js, patches its source text for
// each mutation, and checks the arithmetic in double precision with no browser.
//
// EVERY FIXTURE IS DYADIC. Heights are built from 1/128, 1/256 and 0.75, and the vertical scale is
// 2048 m, so every stored sample is exact in Float32 and every bilinear midpoint is exact in
// double. That is what lets the closed forms below be asserted at 1e-10 instead of at a
// Float32-noise tolerance of 1e-4 — and the gap between those two numbers is the whole difference
// between a bound that catches a 1.5% error and one that does not.
//
// THE CLOSED FORMS, derived from the fixtures rather than from the implementation:
//
//   a guide climbing a constant slope        deficit[k] = k * (rise_per_step + eps_per_step)
//   a guide crossing dead-flat ground        deficit[k] = k * eps_per_step
//   after the crest, descending at s         deficit falls by (s - eps_per_step) per step and
//                                            first reaches zero at ceil(peak / (s - eps_per_step))
//
// where eps_per_step = epsCell * ds/cellSize and epsCell = relief/(max(res,2)*160) — HydroFix's own
// descent, so the reported deficit is the cut the offered branch would actually make.
const path = require('path')
const fs = require('fs')
const { pathToFileURL } = require('url')

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'smooth-deficits',          // the story's named failure: average the deficit and the peak shrinks
  'ignore-sample-spacing',    // eps per SAMPLE not per DISTANCE: the answer depends on resampling
  'apply-repair',             // the analyser helpfully writes the target back into the surface
  'no-metre-conversion',      // report normalized height and still call it metres
  'target-resets-to-terrain', // the ratchet restarts each step, so a long climb reads as one step
  'no-descent-epsilon',       // a dead-flat canal reports zero conflict
  'ignore-flow-opposition',   // a guide drawn backwards up its own river reports as aligned
  'plugin-emits-height',      // guardrail 1: the water-family node grows a terrain-height output
  'plugin-drops-deficit',     // the node evaluates cleanly and stamps an all-zero delta raster
]
const PATCHES = {
  // Three taps, centred, ends held. This is exactly the "remove sampling noise" filter someone adds
  // when a deficit profile looks spiky, and it turns a sharp one-sample obstruction into two-thirds
  // of itself while reporting nothing was removed.
  'smooth-deficits': [[
    '  const deficit = new Float64Array(n)\n  const deficitM = new Float64Array(n)\n  for (let i = 0; i < n; i++) {\n    deficit[i] = elevation[i] - target[i]\n    deficitM[i] = deficit[i] * heightScaleM\n  }',
    '  const deficit = new Float64Array(n)\n  const deficitM = new Float64Array(n)\n  const raw = new Float64Array(n)\n  for (let i = 0; i < n; i++) raw[i] = elevation[i] - target[i]\n'
    + '  for (let i = 0; i < n; i++) {\n    const a = raw[Math.max(0, i - 1)], b = raw[i], c = raw[Math.min(n - 1, i + 1)]\n'
    + '    deficit[i] = (a + b + c) / 3\n    deficitM[i] = deficit[i] * heightScaleM\n  }',
  ]],
  'ignore-sample-spacing': [['    const step = epsCell * (g.ds[i] / cellSizeM)', '    const step = epsCell']],
  'no-descent-epsilon': [['    const step = epsCell * (g.ds[i] / cellSizeM)', '    const step = 0']],
  'target-resets-to-terrain': [[
    '    target[i] = Math.min(elevation[i], target[i - 1] - step)',
    '    target[i] = Math.min(elevation[i], elevation[i - 1] - step)',
  ]],
  // The hidden in-node correction the verification matrix names. It writes the computed target back
  // into the caller's routing surface at the nearest cell — "while we are here, we may as well fix
  // it" — which is precisely the authority this node is not allowed to have.
  'apply-repair': [[
    '    target[i] = Math.min(elevation[i], target[i - 1] - step)',
    '    target[i] = Math.min(elevation[i], target[i - 1] - step)\n'
    + '    { const rr = Math.min(hgt - 1, Math.max(0, Math.round(g.z[i] / (cellSizeM * (hex ? HEX_ROW : 1)))))\n'
    + '      const cc = Math.min(w - 1, Math.max(0, Math.round(g.x[i] / cellSizeM - (hex && (rr & 1) ? 0.5 : 0))))\n'
    + '      surface[rr * w + cc] = target[i] }',
  ]],
  'no-metre-conversion': [['    deficitM[i] = deficit[i] * heightScaleM', '    deficitM[i] = deficit[i]']],
  'ignore-flow-opposition': [[
    '      alignment[i] = (tx / tl) * f.x + (tz / tl) * f.z',
    '      alignment[i] = 1',
  ]],
}
// Mutations that patch the PLUGIN rather than the core module. Both are sprint-level failures the
// core arithmetic cannot see: a water-family node that grows a height output, and a node that
// evaluates without error while reporting nothing.
const PLUGIN_PATCHES = {
  'plugin-emits-height': [
    ["    { id: 'conflicts', name: 'Conflicts', kind: 'featureSet', storage: 'RECORDS', components: 1,",
      "    { id: 'height', name: 'Height', kind: 'scalarRaster', storage: 'R32F', components: 1,\n"
      + "      semantic: 'relativeHeight', unit: 'none', lens: 'continued' },\n"
      + "    { id: 'conflicts', name: 'Conflicts', kind: 'featureSet', storage: 'RECORDS', components: 1,"],
    ["    const values = new Map([['conditioningDelta', delta]])",
      "    const values = new Map([['conditioningDelta', delta], ['height', src]])"],
  ],
  'plugin-drops-deficit': [['        if (!(rep.deficit[i] > 0)) continue', '        if (rep.deficit[i] >= 0) continue']],
}
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

// --- fixture constants -------------------------------------------------------------------------
const W = 64, H = 64, N = W * H
const CELL = 16                 // metres per cell; dyadic so half-cell world positions are exact
const HEIGHT_M = 2048           // terrainDef.height: metres spanned by one unit of normalized height
const S_CELL = 1 / 128          // downhill drop per cell
const U_CELL = 1 / 256          // uphill rise per cell on the ramp fixture
const XB = 24, XC = 32          // the ramp's foot and crest, in cells
const GX0 = 4, GX1 = 56         // the guide spans these columns

const plane = () => {
  const h = new Float32Array(N)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) h[y * W + x] = 0.75 - x * S_CELL
  return h
}
/** Down, then one analytic uphill segment, then down again. The story's fixture. */
const ramp = () => {
  const h = new Float32Array(N)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const v = x <= XB ? 0.75 - x * S_CELL
      : x <= XC ? 0.75 - XB * S_CELL + (x - XB) * U_CELL
        : 0.75 - XB * S_CELL + (XC - XB) * U_CELL - (x - XC) * S_CELL
    h[y * W + x] = v
  }
  return h
}
/** Descends in ROWS only, so a guide running along a row crosses ground that is exactly flat. */
const flatline = () => {
  const h = new Float32Array(N)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) h[y * W + x] = 0.75 - y * S_CELL
  return h
}

/** Patch a module's source text and return an importable data URL, or the plain file URL when this
 *  run has no patch for it. Every anchor must match exactly once: an anchor that has drifted out of
 *  the source would otherwise leave the module unmodified and score the mutation as armed. */
const dataUrl = text => 'data:text/javascript;base64,' + Buffer.from(text, 'utf8').toString('base64')
const patched = (file, patches) => {
  if (!patches) return pathToFileURL(file).href
  let text = fs.readFileSync(file, 'utf8')
  for (const [anchor, repl] of patches) {
    const hits = text.split(anchor).length - 1
    if (hits !== 1) { console.error(`FATAL anchor for ${mutation} matched ${hits}, expected 1`); process.exit(2) }
    text = text.replace(anchor, repl)
  }
  return dataUrl(text)
}

;(async () => {
  const src = path.resolve(__dirname, '../../src/core/water-conflict.js')
  // ONE core href, shared by the direct import below and by the plugin's rewritten import, so a
  // mutation reaches the node exactly as it reaches the module. Loading the plugin against the
  // pristine file would leave every plugin assertion permanently green — coverage that cannot fail.
  const coreHref = patched(src, mutation ? PATCHES[mutation] : null)
  let M = null, loadErr = null
  try { M = await import(coreHref) } catch (e) { loadErr = String(e.message || e).slice(0, 200) }

  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }
  if (!check('module loads', M !== null, loadErr)) return report()

  const HY = await import(pathToFileURL(path.resolve(__dirname, '../../src/core/hydrology.js')).href)

  // Every analyse call goes through here so the read-only contract is checked on EVERY fixture, not
  // on one chosen example. `before` is a pristine copy taken before the call.
  const touched = []
  const analyse = (label, field, guide, opts) => {
    const before = Float32Array.from(field)
    const rep = M.analyzeGuideConflict(field, W, H, guide, opts)
    let changed = 0
    for (let i = 0; i < N; i++) if (field[i] !== before[i]) changed++
    touched.push({ label, changed })
    return rep
  }

  const eps = f => {
    // The oracle derives epsCell ITSELF from the fixture — never from the report — so a mutation
    // that zeroes the descent inside the recurrence cannot also move the yardstick.
    let mn = Infinity, mx = -Infinity
    for (let i = 0; i < f.length; i++) { const v = f[i]; if (v < mn) mn = v; if (v > mx) mx = v }
    return Math.max(mx - mn, 1e-5) / (Math.max(W, 2) * 160)
  }
  // The plan's recurrence, recomputed from the module's own sampled elevations. It is deliberately
  // a second implementation of the same three lines: it catches every mutation that perturbs the
  // recurrence, while the CLOSED FORMS below — which are derived from the fixture geometry and not
  // from these lines at all — carry the independent weight.
  const recurrence = (rep, epsCell) => {
    const n = rep.count, tgt = new Float64Array(n), def = new Float64Array(n)
    tgt[0] = rep.elevation[0]
    for (let i = 1; i < n; i++) tgt[i] = Math.min(rep.elevation[i], tgt[i - 1] - epsCell * (rep.ds[i] / CELL))
    for (let i = 0; i < n; i++) def[i] = rep.elevation[i] - tgt[i]
    return def
  }
  const worstRel = (a, b) => {
    let worst = 0
    for (let i = 0; i < a.length; i++) {
      const d = Math.abs(a[i] - b[i]), s = Math.max(Math.abs(a[i]), Math.abs(b[i]))
      const r = s > 0 ? d / s : d
      if (r > worst) worst = r
    }
    return worst
  }
  const line = (x0, x1, row) => [{ x: x0 * CELL, z: row * CELL }, { x: x1 * CELL, z: row * CELL }]
  const ROW = 32
  const baseOpts = { cellSizeM: CELL, heightScaleM: HEIGHT_M }

  // --- the vertical scale has no default -------------------------------------------------------
  // A deficit is quoted in metres. If the normalized->metres factor may be omitted, every report is
  // dimensionless while still reading as metres — the same defect class as the dropped mm->m and
  // per-year conversions the S4.2 gate arms against.
  let threwNoScale = false, threwZeroScale = false
  try { M.analyzeGuideConflict(plane(), W, H, line(GX0, GX1, ROW), { cellSizeM: CELL }) } catch (_) { threwNoScale = true }
  try { M.analyzeGuideConflict(plane(), W, H, line(GX0, GX1, ROW), { cellSizeM: CELL, heightScaleM: 0 }) } catch (_) { threwZeroScale = true }
  check('an omitted vertical scale is refused, not defaulted to 1', threwNoScale && threwZeroScale,
    { threwNoScale, threwZeroScale })

  // A guide with no length is not a guide with no conflict.
  let threwDegenerate = false, threwCoarse = false
  try { M.resampleGuide([{ x: 100, z: 100 }, { x: 100, z: 100 }], { cellSizeM: CELL }) } catch (_) { threwDegenerate = true }
  try { M.resampleGuide(line(GX0, GX1, ROW), { cellSizeM: CELL, spacingCells: 1 }) } catch (_) { threwCoarse = true }
  check('a zero-length guide is refused rather than reported clean', threwDegenerate, { threwDegenerate })
  check('spacing coarser than half a cell is refused', threwCoarse && M.GUIDE_SPACING_CELLS === 0.5,
    { threwCoarse, cap: M.GUIDE_SPACING_CELLS })

  // --- sampling geometry ------------------------------------------------------------------------
  const gTest = M.resampleGuide(line(GX0, GX1, ROW), { cellSizeM: CELL })
  check('the guide resamples at exactly half a cell over the whole span',
    gTest.count === 105 && gTest.stepM === 0.5 * CELL && gTest.lengthM === (GX1 - GX0) * CELL,
    { count: gTest.count, stepM: gTest.stepM, lengthM: gTest.lengthM })

  // A hex row is offset by half a column. Sampling every cell at its OWN world position must return
  // that cell's stored value exactly; a sampler that forgets the odd-row offset shears alternate
  // rows by half a cell and this is where that shows up.
  const HEXROW = Math.sqrt(3) / 2
  const hexField = new Float32Array(N)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) hexField[y * W + x] = 0.75 - (x + y * 7) * (1 / 1024)
  let hexWorst = 0, hexSamples = 0
  for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
    const wx = (x + (y & 1 ? 0.5 : 0)) * CELL, wz = y * HEXROW * CELL
    const got = M.sampleScalarWorld(hexField, W, H, wx, wz, { cellSizeM: CELL, hex: true })
    hexWorst = Math.max(hexWorst, Math.abs(got - hexField[y * W + x])); hexSamples++
  }
  check('hex sampling honours the odd-row half-column offset', hexSamples > 3000 && hexWorst < 1e-9,
    { hexSamples, hexWorst })

  // ==============================================================================================
  // PLANE — a guide drawn downhill, and the same guide drawn backwards
  // ==============================================================================================
  const hPlane = plane()
  const epsPlane = eps(hPlane)
  const wPlane = HY.mfdWeights(hPlane, W, H, { cellSizeM: CELL })
  let routedPlane = 0
  for (let i = 0; i < N; i++) if (!wPlane.outlet[i]) routedPlane++
  check('the plane fixture actually routed', routedPlane > N * 0.9, { routedPlane, N })

  const down = analyse('plane-downhill', hPlane, line(GX0, GX1, ROW), { ...baseOpts, flow: wPlane })
  check('the downhill fixture produced samples with real relief',
    down.count === 105 && Math.abs(down.elevation[0] - down.elevation[down.count - 1]) > 0.3,
    { count: down.count, drop: down.elevation[0] - down.elevation[down.count - 1] })
  // The plan: "A valid downhill guide emits zero conflict."
  let downMaxDeficit = 0
  for (let i = 0; i < down.count; i++) downMaxDeficit = Math.max(downMaxDeficit, down.deficit[i])
  check('a valid downhill guide emits exactly zero deficit',
    downMaxDeficit === 0 && down.maxDeficit === 0 && down.maxDeficitM === 0 && down.conflictCount === 0,
    { downMaxDeficit, maxDeficit: down.maxDeficit, conflictCount: down.conflictCount })
  let downAlignMin = Infinity
  for (let i = 0; i < down.count; i++) if (down.flowKnown[i]) downAlignMin = Math.min(downAlignMin, down.alignment[i])
  check('a downhill guide runs exactly with the routed flow',
    downAlignMin === 1 && down.opposedCount === 0 && down.unroutedCount === 0,
    { downAlignMin, opposedCount: down.opposedCount, unroutedCount: down.unroutedCount })
  check('a downhill guide is not offered a conditioning branch',
    down.hasConflict === false && M.proposeConditioningBranch(down) === null, { hasConflict: down.hasConflict })

  const up = analyse('plane-uphill', hPlane, line(GX1, GX0, ROW), { ...baseOpts, flow: wPlane })
  // CLOSED FORM: climbing a constant slope, deficit[k] = k * (rise_per_step + eps_per_step).
  const stepRise = S_CELL * 0.5, stepEps = epsPlane * 0.5
  const upClosed = new Float64Array(up.count)
  for (let k = 0; k < up.count; k++) upClosed[k] = k * (stepRise + stepEps)
  const upRel = worstRel(Array.from(up.deficit), Array.from(upClosed))
  check('a guide climbing a constant slope accumulates the closed-form deficit', upRel < 1e-10,
    { worstRelErr: upRel, lastDeficit: up.deficit[up.count - 1], closed: upClosed[up.count - 1] })
  check('the uphill maximum sits at the far end of the climb',
    up.maxIndex === up.count - 1 && up.maxAtM.x === GX0 * CELL && up.maxAtM.z === ROW * CELL,
    { maxIndex: up.maxIndex, maxAtM: up.maxAtM })
  let upAlignMax = -Infinity, upRouted = 0
  for (let i = 0; i < up.count; i++) if (up.flowKnown[i]) { upAlignMax = Math.max(upAlignMax, up.alignment[i]); upRouted++ }
  check('a guide drawn against the routed flow reports exact opposition',
    upAlignMax === -1 && up.opposedCount === upRouted && upRouted === up.count,
    { upAlignMax, opposedCount: up.opposedCount, upRouted, count: up.count })
  let oppWorst = 0
  for (let i = 0; i < up.count; i++) oppWorst = Math.max(oppWorst, Math.abs(up.opposition[i] - 1))
  check('opposition severity is 1 where the guide is exactly reversed', oppWorst === 0, { oppWorst })

  // --- metres ------------------------------------------------------------------------------------
  // The floor sits BETWEEN TWO MEASURED BUILDS: with the conversion the worst deficit on this
  // fixture is 837.12 m, without it the same report says 0.4087 and still calls it metres. 100 is
  // between them and neither endpoint was chosen to make a test pass.
  check('the deficit in metres is the normalized deficit times the vertical scale',
    up.maxDeficitM === up.maxDeficit * HEIGHT_M && up.deficitM[10] === up.deficit[10] * HEIGHT_M
    && up.maxDeficitM > 100,
    { maxDeficit: up.maxDeficit, maxDeficitM: up.maxDeficitM, heightScaleM: HEIGHT_M })
  const upClosedM = upClosed[up.count - 1] * HEIGHT_M
  check('the maximum deficit in metres matches the closed form',
    Math.abs(up.maxDeficitM - upClosedM) / upClosedM < 1e-10,
    { maxDeficitM: up.maxDeficitM, closedM: upClosedM })

  // --- the offered branch --------------------------------------------------------------------
  const proposal = M.proposeConditioningBranch(up, { mode: 'breach' })
  check('a conflicted guide is offered an explicit, undoable, height-safe branch',
    !!proposal && proposal.nodeType === 'depression' && proposal.params.mode === 'breach'
    && proposal.writesHeight === false && proposal.undoable === true && proposal.applied === false
    && proposal.maxDeficitM === up.maxDeficitM,
    proposal && { nodeType: proposal.nodeType, writesHeight: proposal.writesHeight, undoable: proposal.undoable })
  const hydro = M.proposeConditioningBranch(up, { mode: 'hydrofix' })
  check('the one branch that writes terrain says so', hydro.writesHeight === true && hydro.nodeType === 'hydrofix',
    { nodeType: hydro.nodeType, writesHeight: hydro.writesHeight })
  let threwBadMode = false
  try { M.proposeConditioningBranch(up, { mode: 'carve' }) } catch (_) { threwBadMode = true }
  check('an unknown conditioning branch is refused', threwBadMode, { threwBadMode })

  // --- flow that was never supplied is not flow that agrees ------------------------------------
  const noFlow = analyse('plane-uphill-noflow', hPlane, line(GX1, GX0, ROW), { ...baseOpts })
  check('a report built without a flow field says so rather than reporting agreement',
    noFlow.flowSupplied === false && noFlow.opposedCount === 0 && noFlow.unroutedCount === noFlow.count
    && Number.isNaN(noFlow.alignment[5]) && up.flowSupplied === true,
    { flowSupplied: noFlow.flowSupplied, unroutedCount: noFlow.unroutedCount, count: noFlow.count })

  // ==============================================================================================
  // RAMP — the story's fixture: one analytic uphill segment on an otherwise draining guide
  // ==============================================================================================
  const hRamp = ramp()
  const epsRamp = eps(hRamp)
  const wRamp = HY.mfdWeights(hRamp, W, H, { cellSizeM: CELL })
  const rmp = analyse('ramp', hRamp, line(GX0, GX1, ROW), { ...baseOpts, flow: wRamp })
  check('the ramp report has the expected sample count and epsilon',
    rmp.count === 105 && rmp.epsCell === epsRamp && rmp.relief === 0.75 - hRamp[63],
    { count: rmp.count, epsCell: rmp.epsCell, epsOracle: epsRamp, relief: rmp.relief })

  const rampRec = recurrence(rmp, epsRamp)
  let recExact = true, firstRecMismatch = -1
  for (let i = 0; i < rmp.count; i++) if (rmp.deficit[i] !== rampRec[i]) { recExact = false; if (firstRecMismatch < 0) firstRecMismatch = i }
  check('every ramp deficit sample equals the plan recurrence exactly', recExact,
    { firstMismatch: firstRecMismatch, got: firstRecMismatch >= 0 ? rmp.deficit[firstRecMismatch] : null,
      want: firstRecMismatch >= 0 ? rampRec[firstRecMismatch] : null })

  // Index arithmetic: sample i sits at column GX0 + i/2. The foot of the ramp is column XB.
  const iFoot = (XB - GX0) * 2, iCrest = (XC - GX0) * 2
  let zeroBeforeFoot = true
  for (let i = 0; i <= iFoot; i++) if (rmp.deficit[i] !== 0) zeroBeforeFoot = false
  check('the draining part of the guide reports exactly zero deficit', zeroBeforeFoot && iFoot === 40,
    { iFoot, deficitAtFoot: rmp.deficit[iFoot], deficitJustBefore: rmp.deficit[iFoot - 1] })

  // CLOSED FORM: 16 half-cell steps of rise U_CELL/2 each, plus the descent allowance each step.
  const rampSteps = (XC - XB) * 2
  const rampPeak = rampSteps * (U_CELL * 0.5 + epsRamp * 0.5)
  check('the ramp maximum matches the closed form and sits at the crest',
    Math.abs(rmp.maxDeficit - rampPeak) / rampPeak < 1e-10 && rmp.maxIndex === iCrest
    && rmp.maxAtM.x === XC * CELL && rmp.maxAtM.z === ROW * CELL,
    { maxDeficit: rmp.maxDeficit, closed: rampPeak, maxIndex: rmp.maxIndex, iCrest, maxAtM: rmp.maxAtM })
  check('the ramp maximum in metres matches the closed form',
    Math.abs(rmp.maxDeficitM - rampPeak * HEIGHT_M) / (rampPeak * HEIGHT_M) < 1e-10 && rmp.maxDeficitM > 60,
    { maxDeficitM: rmp.maxDeficitM, closedM: rampPeak * HEIGHT_M })

  // Every sample on the climb, not just the peak.
  let rampRel = 0
  for (let k = 1; k <= rampSteps; k++) {
    const want = k * (U_CELL * 0.5 + epsRamp * 0.5), got = rmp.deficit[iFoot + k]
    rampRel = Math.max(rampRel, Math.abs(got - want) / want)
  }
  check('every sample on the climb matches k*(rise+eps)', rampRel < 1e-10, { worstRelErr: rampRel })

  // CLOSED FORM: past the crest the deficit falls by (s - eps) per step and first reaches zero at
  // ceil(peak/(s-eps)). Measured 8.20, so 9 — not near an integer, which is why the index is
  // assertable rather than a coin toss.
  const decayPerStep = S_CELL * 0.5 - epsRamp * 0.5
  const closedFirstZero = Math.ceil(rampPeak / decayPerStep)
  let firstZero = -1
  for (let j = 1; iCrest + j < rmp.count; j++) if (rmp.deficit[iCrest + j] === 0) { firstZero = j; break }
  check('the deficit decays past the crest and reaches exactly zero where the closed form says',
    firstZero === closedFirstZero && firstZero === 9 && rmp.deficit[iCrest + firstZero - 1] > 0,
    { firstZero, closedFirstZero, ratio: rampPeak / decayPerStep, lastPositive: rmp.deficit[iCrest + firstZero - 1] })
  check('the conflict runs the length of the climb plus its decay, and no further',
    rmp.conflictCount === rampSteps + closedFirstZero - 1 && rmp.conflictCount === 24,
    { conflictCount: rmp.conflictCount, expected: rampSteps + closedFirstZero - 1 })

  // The conflict records are the surfaced product: positions, cause and severity in metres.
  const worstRecord = rmp.conflicts.reduce((a, b) => (b.deficitM > a.deficitM ? b : a), rmp.conflicts[0] || { deficitM: -1 })
  check('the conflict records carry position, cause and severity in metres',
    rmp.conflicts.length >= rmp.conflictCount && worstRecord.index === iCrest
    && worstRecord.xM === XC * CELL && worstRecord.deficitM === rmp.maxDeficitM
    && worstRecord.severityM === rmp.maxDeficitM && worstRecord.cause.includes('rise'),
    { records: rmp.conflicts.length, worst: worstRecord && { index: worstRecord.index, xM: worstRecord.xM, deficitM: worstRecord.deficitM, cause: worstRecord.cause } })

  // Flow opposition on the ramp: every sample whose nearest cell lies STRICTLY inside the uphill
  // span is on ground that rises in +x, so the routed flow there points -x and the guide, drawn +x,
  // is exactly reversed.
  //
  // 14, derived: the climb is 8 cells sampled every half cell, so 16 samples sit above the foot,
  // and the two nearest the crest column (u = 31.5 and u = 32, both rounding to column 32) are
  // excluded because the crest itself drains both ways. Nearest-column rounding is half-up, which
  // is why the boundary samples land where they do.
  let insideSpan = 0, insideWorst = -Infinity
  for (let i = 0; i < rmp.count; i++) {
    const cell = Math.round(rmp.x[i] / CELL)
    if (cell <= XB || cell >= XC) continue
    insideSpan++
    insideWorst = Math.max(insideWorst, rmp.alignment[i])
  }
  check('inside the uphill span the guide is reported exactly opposed to the routed flow',
    insideSpan === 14 && insideWorst === -1 && rmp.opposedCount >= insideSpan,
    { insideSpan, insideWorst, opposedCount: rmp.opposedCount })
  // The trough column has nowhere lower to send water at all, and TWO samples (u = 23.5 and u = 24)
  // round to it. `mfdWeights` gives those cells (0,0), and that zero has to keep meaning "no
  // receiver" rather than being read as a direction that happens to agree with the guide.
  check('the trough column is reported as unrouted, not as agreeing flow',
    rmp.unroutedCount === 2 && rmp.flowKnown[iFoot] === 0 && rmp.flowKnown[iFoot - 1] === 0,
    { unroutedCount: rmp.unroutedCount, atFoot: rmp.flowKnown[iFoot] })

  // ==============================================================================================
  // FLATLINE — dead-flat ground. Only the descent epsilon can produce a deficit here.
  // ==============================================================================================
  const hFlat = flatline()
  const epsFlat = eps(hFlat)
  const flat = analyse('flatline', hFlat, line(GX0, GX1, ROW), { ...baseOpts, flow: HY.mfdWeights(hFlat, W, H, { cellSizeM: CELL }) })
  let flatSpread = 0
  for (let i = 0; i < flat.count; i++) flatSpread = Math.max(flatSpread, Math.abs(flat.elevation[i] - flat.elevation[0]))
  check('the flat guide really is flat and really was sampled',
    flatSpread === 0 && flat.count === 105 && flat.elevation[0] === 0.75 - ROW * S_CELL,
    { flatSpread, count: flat.count, elevation0: flat.elevation[0] })
  // A channel that neither rises nor falls does not drain. Without the descent epsilon this reports
  // zero and a dead-flat canal reads as a valid river.
  const flatClosed = new Float64Array(flat.count)
  for (let k = 0; k < flat.count; k++) flatClosed[k] = k * epsFlat * 0.5
  const flatRel = worstRel(Array.from(flat.deficit), Array.from(flatClosed))
  check('a dead-flat guide accumulates exactly the descent epsilon per step',
    flat.deficit[flat.count - 1] > 0 && flatRel < 1e-10,
    { worstRelErr: flatRel, last: flat.deficit[flat.count - 1], closed: flatClosed[flat.count - 1] })
  check('the flat guide reports a strictly positive conflict in metres',
    flat.maxDeficitM > 4 && flat.maxDeficitM === flat.maxDeficit * HEIGHT_M && flat.conflictCount === flat.count - 1,
    { maxDeficitM: flat.maxDeficitM, conflictCount: flat.conflictCount })
  // Crossing the contour: the guide runs along a row, the flow runs down the rows. Neither with nor
  // against — and a report that cannot tell 0 from -1 cannot tell a crossing from a reversal.
  let flatAlignWorst = 0
  for (let i = 0; i < flat.count; i++) if (flat.flowKnown[i]) flatAlignWorst = Math.max(flatAlignWorst, Math.abs(flat.alignment[i]))
  check('a guide crossing the contour is neither with nor against the flow',
    flatAlignWorst === 0 && flat.opposedCount === 0, { flatAlignWorst, opposedCount: flat.opposedCount })

  // ==============================================================================================
  // THE NODE — loaded with legacy stubbed, so the plugin's own wiring is measured, not assumed
  // ==============================================================================================
  // A plugin that computes the right thing and returns an empty field passes every assertion above.
  // The only way to know the node works is to run the node, so its two impure imports are replaced:
  // `legacy.js` by a stub built from THIS FILE's fixture constants (it cannot drift from them), and
  // `core/water-conflict.js` by whichever href this run is using.
  const pluginPath = path.resolve(__dirname, '../../src/plugins/data/water_conflict.js')
  const coreDir = p => pathToFileURL(path.resolve(__dirname, '../../src/core/' + p)).href
  const legacyStub = dataUrl(
    `export const newField=()=>new Float32Array(${W * H});export const fieldW=()=>${W};export const fieldH=()=>${H};`
    + `export const cellSizeM=()=>${CELL};export const isHex=()=>false;export const terrainDef={height:${HEIGHT_M}};`
    + 'export const HEX_ROW=Math.sqrt(3)/2;')
  let pluginText = fs.readFileSync(pluginPath, 'utf8')
  for (const [anchor, repl] of (mutation && PLUGIN_PATCHES[mutation]) || []) {
    const hits = pluginText.split(anchor).length - 1
    if (hits !== 1) { console.error(`FATAL plugin anchor for ${mutation} matched ${hits}, expected 1`); process.exit(2) }
    pluginText = pluginText.replace(anchor, repl)
  }
  const rewrites = [
    ["'../../core/registry.js'", JSON.stringify(coreDir('registry.js'))],
    ["'../../core/params.js'", JSON.stringify(coreDir('params.js'))],
    ["'../../core/water-conflict.js'", JSON.stringify(coreHref)],
    ["'../../legacy.js'", JSON.stringify(legacyStub)],
  ]
  for (const [from, to] of rewrites) {
    if (pluginText.split(from).length - 1 !== 1) { console.error(`FATAL plugin import rewrite ${from} did not match exactly once`); process.exit(2) }
    pluginText = pluginText.replace(from, to)
  }
  const PORTS = await import(coreDir('ports.js'))
  const def = (await import(dataUrl(pluginText))).default

  const portProblems = PORTS.validatePortList({ inputs: def.inputs, outputs: def.outputs, source: 'declared' })
  check('the node\'s declared ports validate against the S2.1 vocabulary',
    portProblems.length === 0 && def.inputs.length === 3 && def.outputs.length >= 2,
    { problems: portProblems, inputs: def.inputs.length, outputs: def.outputs.length })

  const flowRaster = new Float32Array(N * 3)
  for (let i = 0; i < N; i++) { flowRaster[i * 3] = wRamp.dirX[i]; flowRaster[i * 3 + 2] = wRamp.dirZ[i] }
  const guideText = `${GX0 * CELL},${ROW * CELL}\n${GX1 * CELL},${ROW * CELL}`
  const featureGuide = [{ id: 'g1', points: [{ x: GX0 * CELL, z: ROW * CELL }, { x: GX1 * CELL, z: ROW * CELL }] }]

  const runNode = (field, params, ins) => {
    const before = Float32Array.from(field)
    const out = def.eval(params, ins, null, null)
    let changed = 0
    for (let i = 0; i < N; i++) if (field[i] !== before[i]) changed++
    touched.push({ label: `node:${params.branch}`, changed })
    return out
  }

  const hRampNode = ramp()
  const nodeOut = runNode(hRampNode, { branch: 'breach', guide: '' }, [hRampNode, flowRaster, featureGuide])
  const nodeDelta = nodeOut.values.get('conditioningDelta')
  const nodeRecords = nodeOut.values.get('conflicts')
  // GUARDRAIL 1, at the node boundary: no height port declared, no height value returned.
  const heightish = k => /height/i.test(String(k))
  check('the water-family node declares no terrain-height output and returns none',
    def.outputs.every(o => !heightish(o.id) && !heightish(o.semantic))
    && ![...nodeOut.values.keys()].some(heightish),
    { outputs: def.outputs.map(o => o.id), values: [...nodeOut.values.keys()] })

  // The delta raster must actually carry the measured cut. An all-zero raster from a node that
  // exited cleanly is the doctrine's "framebuffer read all zeros" — red, not green.
  let stamped = 0, deepest = 0, deepestCell = -1
  for (let i = 0; i < N; i++) {
    if (nodeDelta[i] === 0) continue
    stamped++
    if (nodeDelta[i] < deepest) { deepest = nodeDelta[i]; deepestCell = i }
  }
  const crestCell = ROW * W + XC
  // 12, derived: the 24 conflicted samples sit at half-cell spacing, so they pair up two to a
  // column (round-half-up puts u=24.5 and u=25 both on column 25), covering columns 25..36.
  check('the node stamps the measured deficit into its delta raster',
    stamped === 12 && deepestCell === crestCell && deepest === -Math.fround(rmp.maxDeficit)
    && deepest < 0 && nodeDelta[ROW * W + GX0] === 0,
    { stamped, deepest, deepestCell, crestCell, coreMax: -Math.fround(rmp.maxDeficit), conflictSamples: rmp.conflictCount })

  check('the node reports the same conflict the core module measured',
    Array.isArray(nodeRecords) && nodeRecords.length === 1
    && nodeRecords[0].maxDeficitM === rmp.maxDeficitM && nodeRecords[0].conflictCount === rmp.conflictCount
    && nodeRecords[0].flowSupplied === true && nodeRecords[0].conflicts.length === rmp.conflicts.length,
    nodeRecords && nodeRecords[0] && { maxDeficitM: nodeRecords[0].maxDeficitM, conflictCount: nodeRecords[0].conflictCount })
  check('the node offers the branch the author selected, and says it does not write terrain',
    nodeRecords[0].proposal && nodeRecords[0].proposal.mode === 'breach'
    && nodeRecords[0].proposal.writesHeight === false && nodeRecords[0].proposal.undoable === true,
    nodeRecords[0].proposal && { mode: nodeRecords[0].proposal.mode, writesHeight: nodeRecords[0].proposal.writesHeight })

  // The text fallback has to reach the same guide as the feature set, or the gate is testing one
  // input path and the app is using the other.
  const hRampText = ramp()
  const textOut = runNode(hRampText, { branch: 'hydrofix', guide: guideText }, [hRampText, flowRaster, null])
  const textRecords = textOut.values.get('conflicts')
  check('an authored text guide reaches the same measurement as a feature-set guide',
    textRecords.length === 1 && textRecords[0].maxDeficitM === rmp.maxDeficitM
    && textRecords[0].samples === rmp.count,
    { maxDeficitM: textRecords[0].maxDeficitM, samples: textRecords[0].samples })
  check('selecting the HydroFix branch labels it as the one that writes terrain',
    textRecords[0].proposal.writesHeight === true && textRecords[0].proposal.nodeType === 'hydrofix',
    { nodeType: textRecords[0].proposal.nodeType, writesHeight: textRecords[0].proposal.writesHeight })

  // A guide that drains: empty delta raster, no offer. This is the negative control for the stamp
  // assertion above — without it "all zeros" and "correct" are indistinguishable.
  const hPlaneNode = plane()
  const cleanOut = runNode(hPlaneNode, { branch: 'breach', guide: '' }, [hPlaneNode, null,
    [{ id: 'clean', points: [{ x: GX0 * CELL, z: ROW * CELL }, { x: GX1 * CELL, z: ROW * CELL }] }]])
  const cleanDelta = cleanOut.values.get('conditioningDelta')
  const cleanRecords = cleanOut.values.get('conflicts')
  let cleanNonZero = 0
  for (let i = 0; i < N; i++) if (cleanDelta[i] !== 0) cleanNonZero++
  check('a draining guide produces an empty delta raster and no offer',
    cleanNonZero === 0 && cleanRecords[0].proposal === null && cleanRecords[0].conflictCount === 0
    && cleanRecords[0].flowSupplied === false,
    { cleanNonZero, proposal: cleanRecords[0].proposal, flowSupplied: cleanRecords[0].flowSupplied })

  // ==============================================================================================
  // GUARDRAIL 1 — the surface handed in comes back untouched, on every fixture
  // ==============================================================================================
  const dirty = touched.filter(t => t.changed !== 0)
  check('no analysis wrote a single sample back into the routing surface',
    touched.length >= 8 && dirty.length === 0,
    { calls: touched.length, dirty: dirty.map(d => `${d.label}:${d.changed}`) })

  check('assertion inventory non-empty', assertions.length >= 38, assertions.length)
  report()

  function report() {
    let ok = assertions.every(a => a.ok)
    if (mutation) {
      if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
      ok = false
    }
    const failed = assertions.filter(a => !a.ok).map(a => a.name)
    console.log(`${ok ? 'PASS' : 'FAIL'}  water conflict assertions=${assertions.length} `
      + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
    if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify(assertions.filter(a => !a.ok), null, 2))
    process.exit(ok ? 0 : 1)
  }
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
