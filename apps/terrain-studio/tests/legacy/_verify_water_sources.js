// S4.3 — authored water sources and river guides.
//
// THE HEADLINE, in the story's words: "A big river crosses a desert." Zero rainfall, one source. The
// discharge immediately downstream of it equals the authored source flow, it is conserved to the
// outlet absent sinks, and removing the source returns EXACTLY zero. The story is explicit that this
// is stronger than a source/no-source ratio, and it is: a ratio is satisfied by any implementation
// that puts *some* water in the right general area, whereas "1200.000 m3/s at the outlet and exactly
// 0.0 with the source deleted" pins both the magnitude and the cause.
//
// WHY THE FIXTURE IS A SINGLE-THREAD VALLEY. `desert()` is a plane falling in +x with a shallow
// cross-valley V centred on row 32. The cross-slope (0.0078 per cell) is steeper than the downstream
// slope (0.0053 per cell), so a cell ON the valley axis has exactly ONE downslope neighbour — the
// next axis cell — while every off-axis cell still spreads across several. That gives a river whose
// route is known in closed form: the source at (200 m, 320 m) seeds cell (20, 32), and the only cells
// that may carry water are (20..95, 32). Anything else carrying discharge is a defect with a name.
// It also gives the domain exactly ONE outlet, cell (95, 32), so "conserved to the outlet" is a
// single number rather than a sum over an edge that double-counts water crossing a corner.
//
// Pure-module: it imports src/core/water-sources.js under plain node and routes with the REAL
// src/core/hydrology.js — unpatched, always — because the story's whole claim is that a source seeds
// the same accumulation stack as drainage area. Substituting a private accumulator here would be
// checking a different program than the one that ships.
//
// SALINITY IS OUT OF SCOPE and this file asserts its ABSENCE from the schema, because "we did not
// implement it" and "we implemented it badly" look identical on a serialized record until someone
// checks.
const path = require('path')
const fs = require('fs')
const { pathToFileURL } = require('url')

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  // --- the physics -------------------------------------------------------------------------------
  'source-stamps-height',        // stamp the source into the surface -- the story's named failure
  'source-scaled-by-cell-area',  // treat authored m3/s as a per-area rate: 100x on 10 m cells
  'source-cell-swaps-axes',      // world x/z swapped when indexing: the spring lands somewhere else
  'source-splats-one-ring',      // splat the source over its one-ring so it "reads" -- water upstream
  'epsilon-baseflow',            // a small constant everywhere: the desert is no longer exactly dry
  'disabled-source-still-injects',
  'boundary-inflow-anywhere',    // a river entering off-map, injected in the middle of the map
  // --- the guides --------------------------------------------------------------------------------
  'guide-seeds-tail',            // seed the guide's mouth instead of its head
  'reference-guide-seeds',       // a reference line silently becomes water
  // --- identity and persistence ------------------------------------------------------------------
  'positional-ids',              // mint an id from arrival order: deleting one renames the rest
  'duplicate-ids-allowed',       // two features answering to one document-wide handle
  'nondeterministic-serialization', // drop the sort: the file depends on editor insertion order
  'paste-keeps-id',              // copy/paste produces two features with the same id
  'accepts-unknown-kind',        // a kind outside the corpus enum, which nothing downstream can act on
  'accepts-negative-discharge',  // a "sink" as a negative seed: Q^0.5 of a negative reach
]
const PATCHES = {
  'source-stamps-height': { core: [[
    '      supply[ci] += each',
    '      supply[ci] += each\n      surface[ci] = surface[ci] - 0.01']] },
  'source-scaled-by-cell-area': { core: [[
    '    const each = seed.q / cells.length',
    '    const each = seed.q * cellSizeM * cellSizeM / cells.length']] },
  'source-cell-swaps-axes': { core: [
    ['  const v = zM / rowPitch', '  const v = xM / rowPitch'],
    ['  const u = xM / cellSizeM - off', '  const u = zM / cellSizeM - off'],
  ] },
  'source-splats-one-ring': { core: [[
    '    const cells = footprintCells(home, seed.radiusM, w, hgt, cellSizeM, hex)',
    '    const cells = footprintCells(home, seed.radiusM, w, hgt, cellSizeM, hex)\n'
    + '    for (const d of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {\n'
    + '      const cc = home.col + d[0], rr = home.row + d[1]\n'
    + '      if (cc >= 0 && rr >= 0 && cc < w && rr < hgt && cells.indexOf(rr * w + cc) < 0) cells.push(rr * w + cc)\n'
    + '    }']] },
  'epsilon-baseflow': { core: [[
    '  const supply = new Float64Array(N)\n  const placements = []',
    '  const supply = new Float64Array(N)\n  for (let i = 0; i < N; i++) supply[i] = 1e-9\n  const placements = []']] },
  'disabled-source-still-injects': { core: [['    if (!seed.enabled) {', '    if (false && !seed.enabled) {']] },
  'boundary-inflow-anywhere': { core: [[
    '    if (seed.requireEdge && !onEdge(home.col, home.row, w, hgt)) {',
    '    if (false && seed.requireEdge && !onEdge(home.col, home.row, w, hgt)) {']] },
  'guide-seeds-tail': { core: [[
    '        xM: g.points[0].x, zM: g.points[0].z,',
    '        xM: g.points[g.points.length - 1].x, zM: g.points[g.points.length - 1].z,']] },
  'reference-guide-seeds': { core: [["      if (g.intent !== 'channel') continue", '      if (false) continue']] },
  'positional-ids': { core: [[
    '  const id = raw.id\n'
    + '  if (typeof id !== \'string\' || !ID_RE.test(id)) {\n'
    + '    fail(\'ID_INVALID\', `water source id ${JSON.stringify(id)} must be an authored string matching ${ID_RE}`, { id })\n'
    + '  }',
    '  let id = raw.id\n'
    + '  if (typeof id !== \'string\' || !ID_RE.test(id)) {\n'
    + '    id = \'source\' + (normalizeSource.seq = (normalizeSource.seq || 0) + 1)\n'
    + '  }']] },
  'duplicate-ids-allowed': { core: [["    if (seen.has(f.id)) fail('ID_DUPLICATE'", "    if (false && seen.has(f.id)) fail('ID_DUPLICATE'"]] },
  'nondeterministic-serialization': { core: [[
    '  const sources = rawSources.map(normalizeSource).sort(byId)',
    '  const sources = rawSources.map(normalizeSource)']] },
  'paste-keeps-id': { core: [['  const id = mintFeatureId(normalized.id, takenSet)', '  const id = normalized.id']] },
  'accepts-unknown-kind': { core: [['  if (!SOURCE_KINDS.includes(kind)) {', '  if (false && !SOURCE_KINDS.includes(kind)) {']] },
  'accepts-negative-discharge': { core: [['  if (dischargeM3PerS < 0) {', '  if (false && dischargeM3PerS < 0) {']] },
}
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

const CORE = path.resolve(__dirname, '../../src/core/water-sources.js')
const HYDRO = path.resolve(__dirname, '../../src/core/hydrology.js')
const CONFLICT = path.resolve(__dirname, '../../src/core/water-conflict.js')
const PORTS = path.resolve(__dirname, '../../src/core/ports.js')
const PLUGIN = path.resolve(__dirname, '../../src/plugins/data/water_source.js')

function patch(text, pairs, label) {
  for (const [anchor, repl] of pairs) {
    const hits = text.split(anchor).length - 1
    if (hits !== 1) { console.error(`FATAL ${label} anchor for ${mutation} matched ${hits}, expected 1: ${anchor.slice(0, 80)}`); process.exit(2) }
    text = text.replace(anchor, repl)
  }
  return text
}

// --- the fixture ---------------------------------------------------------------------------------
// 96 x 64 on purpose: a NON-SQUARE domain, so swapping the world axes when indexing produces a
// different cell rather than a transposed one that happens to still be in range everywhere.
const W = 96, H = 64, N = W * H, CELL = 10        // 10 m cells, 960 m x 640 m
const AXIS = 32                                    // the valley floor row
const FALL = 0.5, VEE = 0.25                       // downstream drop and cross-valley rise
const HEX_ROW = Math.sqrt(3) / 2
const U32 = Math.pow(2, -24)
const gamma = n => (n * U32) / (1 - n * U32)

/** A valley falling in +x with a V cross-section on row 32. On the axis the cross-slope beats the
 *  downstream slope, so an axis cell has exactly one receiver and the river is one cell wide. */
function desert() {
  const h = new Float32Array(N)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    h[y * W + x] = FALL * (1 - x / (W - 1)) + VEE * Math.abs(y - AXIS) / (H / 2)
  }
  return h
}

// Independent world<->cell formulas. The module has its own; the point of writing them twice is that
// the placement assertions go red if the two ever disagree.
const colOf = (xM, row, hex) => Math.round(xM / CELL - (hex && (row & 1) ? 0.5 : 0))
const rowOf = (zM, hex) => Math.round(zM / (CELL * (hex ? HEX_ROW : 1)))
const centreX = (col, row, hex) => col * CELL + (hex && (row & 1) ? 0.5 * CELL : 0)
const centreZ = (row, hex) => row * CELL * (hex ? HEX_ROW : 1)

const SPRING_X = 200, SPRING_Z = 320, SPRING_Q = 1200      // cell (20, 32)
const SPRING_CELL = rowOf(SPRING_Z, false) * W + colOf(SPRING_X, rowOf(SPRING_Z, false), false)
const OUTLET_CELL = AXIS * W + (W - 1)

;(async () => {
  let M = null, HYD = null, CFL = null, Ports = null, loadErr = null, pluginSrc = null
  try {
    const p = mutation ? (PATCHES[mutation] || {}) : {}
    if (!p.core) {
      M = await import(pathToFileURL(CORE).href)
    } else {
      // water-sources.js imports nothing, so the patched copy loads from a data: URL with no
      // specifier rewriting at all.
      const text = patch(fs.readFileSync(CORE, 'utf8'), p.core, 'core')
      M = await import('data:text/javascript;base64,' + Buffer.from(text, 'utf8').toString('base64'))
    }
    // NEVER PATCHED. The story's claim is that a source seeds the SAME accumulation stack as area, so
    // the accumulation used here has to be the shipping one.
    HYD = await import(pathToFileURL(HYDRO).href)
    CFL = await import(pathToFileURL(CONFLICT).href)
    Ports = await import(pathToFileURL(PORTS).href)
    pluginSrc = fs.readFileSync(PLUGIN, 'utf8')
    if (p.plugin) pluginSrc = patch(pluginSrc, p.plugin, 'plugin')
  } catch (e) { loadErr = String((e && e.message) || e).slice(0, 300) }

  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }
  const attempt = fn => { try { return { ok: true, value: fn() } } catch (e) { return { ok: false, code: e && e.code, message: String((e && e.message) || e).slice(0, 200) } } }
  const measured = {}

  if (!check('module loads', M !== null && HYD !== null && Ports !== null, loadErr)) return report()

  try { await body() } catch (e) {
    check('the oracle ran to completion', false, String((e && e.stack) || e).slice(0, 400))
  }
  return report()

  async function body() {
    // === the corpus enum ==========================================================================
    check('the source kinds are the corpus enum in corpus order',
      Array.isArray(M.SOURCE_KINDS) && M.SOURCE_KINDS.join(',')
        === 'distributedRain,boundaryInflow,spring,karstResurgence,oasis,glacialSnowmelt',
      { kinds: M.SOURCE_KINDS && [...M.SOURCE_KINDS] })
    check('every source kind carries a label',
      M.SOURCE_KINDS.every(k => typeof M.SOURCE_KIND_LABEL[k] === 'string' && M.SOURCE_KIND_LABEL[k].length > 2),
      M.SOURCE_KIND_LABEL)

    // === the fixture routes =======================================================================
    const surface = desert()
    const before = Float32Array.from(surface)
    const weights = HYD.mfdWeights(surface, W, H, { cellSizeM: CELL })
    const area = HYD.cellAreaM2(CELL, false)
    let routed = 0, outletCount = 0, outletIndex = -1
    for (let i = 0; i < N; i++) {
      let nz = 0
      for (let k = 0; k < weights.nbCount; k++) if (weights.wgt[i * weights.nbCount + k] > 0) nz++
      if (nz > 0) routed++
      if (weights.outlet[i]) { outletCount++; outletIndex = i }
    }
    // Absence of evidence is a failure: a fixture that routed nothing would satisfy every
    // conservation assertion below trivially, because zero is conserved perfectly.
    check('the desert fixture routes almost every cell', routed === N - 1, { routed, N })
    check('the desert fixture has exactly one outlet and it is the valley mouth',
      outletCount === 1 && outletIndex === OUTLET_CELL, { outletCount, outletIndex, expected: OUTLET_CELL })
    // The single-receiver valley axis is what makes the river's route known in closed form. If the
    // fixture ever stopped having it, every "only these cells carry water" assertion below would be
    // measuring a different claim than the one documented at the top of this file.
    let axisSingle = 0
    for (let x = 1; x < W - 1; x++) {
      const i = AXIS * W + x
      let nz = 0
      for (let k = 0; k < weights.nbCount; k++) if (weights.wgt[i * weights.nbCount + k] > 0) nz++
      if (nz === 1) axisSingle++
    }
    check('the valley axis is a single-receiver thread', axisSingle === W - 2, { axisSingle, expected: W - 2 })

    // === placement ================================================================================
    const spring = { id: 'nileSpring', kind: 'spring', xM: SPRING_X, zM: SPRING_Z, dischargeM3PerS: SPRING_Q, temperatureC: 24 }
    const seeded = M.sourceSupply(surface, W, H, { sources: [spring] }, { cellSizeM: CELL })
    const place = seeded.placements.find(p => p.id === 'nileSpring')
    check('the source lands in the cell the oracle computes independently',
      !!place && place.col === 20 && place.row === 32 && place.index === SPRING_CELL,
      { got: place && { col: place.col, row: place.row, index: place.index }, expected: { col: 20, row: 32, index: SPRING_CELL } })
    check('the source reports the surface elevation it sits at',
      !!place && place.surfaceValue === surface[SPRING_CELL], { got: place && place.surfaceValue, expected: surface[SPRING_CELL] })

    // The supply term itself: one cell, the authored number, nothing anywhere else. Exact, because
    // a point source is a single store of a single authored double.
    let nzSupply = 0, supplySum = 0
    for (let i = 0; i < N; i++) if (seeded.supply[i] !== 0) { nzSupply++; supplySum += seeded.supply[i] }
    check('the source supply is the authored discharge in exactly one cell',
      nzSupply === 1 && seeded.supply[SPRING_CELL] === SPRING_Q && supplySum === SPRING_Q,
      { nzSupply, atSource: seeded.supply[SPRING_CELL], supplySum, authored: SPRING_Q })

    check('a source outside the domain is refused',
      (() => { const r = attempt(() => M.sourceSupply(surface, W, H, { sources: [{ ...spring, id: 'offMap', xM: 5000, zM: 5000 }] }, { cellSizeM: CELL })); return !r.ok && r.code === 'SOURCE_OFF_DOMAIN' })(),
      attempt(() => M.sourceSupply(surface, W, H, { sources: [{ ...spring, id: 'offMap', xM: 5000, zM: 5000 }] }, { cellSizeM: CELL })))

    // `03:691` — a boundary inflow is a river entering off-map. Injecting one in the middle of the
    // map is not a boundary inflow, it is a spring with the wrong label, and every downstream reader
    // of `kind` would be told something untrue.
    const inland = attempt(() => M.sourceSupply(surface, W, H,
      { sources: [{ id: 'nile', kind: 'boundaryInflow', xM: 400, zM: 320, dischargeM3PerS: 100 }] }, { cellSizeM: CELL }))
    check('a boundary inflow away from the domain edge is refused',
      !inland.ok && inland.code === 'BOUNDARY_NOT_ON_EDGE', inland)
    const onEdge = attempt(() => M.sourceSupply(surface, W, H,
      { sources: [{ id: 'nile', kind: 'boundaryInflow', xM: 0, zM: 320, dischargeM3PerS: 100 }] }, { cellSizeM: CELL }))
    check('a boundary inflow on the domain edge seeds the edge cell',
      onEdge.ok && onEdge.value.supply[AXIS * W] === 100, { ok: onEdge.ok, at: onEdge.ok ? onEdge.value.supply[AXIS * W] : null, code: onEdge.code })

    // Hex: odd rows are shifted half a column. One offset for both rows shears every odd row.
    const hexRow = 33, hexCol = 20
    const hexX = centreX(hexCol, hexRow, true), hexZ = centreZ(hexRow, true)
    const hexSeed = attempt(() => M.sourceSupply(surface, W, H,
      { sources: [{ ...spring, xM: hexX, zM: hexZ }] }, { cellSizeM: CELL, hex: true }))
    check('a source on the hex lattice lands in the staggered cell the oracle computes',
      hexSeed.ok && hexSeed.value.placements[0].col === hexCol && hexSeed.value.placements[0].row === hexRow,
      { got: hexSeed.ok && { col: hexSeed.value.placements[0].col, row: hexSeed.value.placements[0].row }, expected: { col: hexCol, row: hexRow }, hexX, hexZ: +hexZ.toFixed(3) })

    // === A BIG RIVER CROSSES A DESERT =============================================================
    const dry = new Float64Array(N)                       // zero rainfall. A desert.
    const qDesert = HYD.mfdAccumulate(surface, M.combineSupply(dry, seeded.supply), W, H, weights)
    // The plan's bound, verbatim: gamma_(N-1) * sum(abs(sourceQ)).
    const bound = gamma(N - 1) * SPRING_Q
    measured.bound = bound

    // "Discharge immediately downstream equals the authored source flow." On the single-receiver
    // axis, the cell immediately downstream is one named cell, so this is a scalar comparison rather
    // than a sum over a fan.
    const qDown = qDesert[SPRING_CELL + 1]
    measured.qDownstream = qDown
    measured.downRelErr = Math.abs(qDown - SPRING_Q) / SPRING_Q
    check('discharge immediately downstream equals the authored source flow',
      Math.abs(qDown - SPRING_Q) <= bound, { qDown, authored: SPRING_Q, diff: qDown - SPRING_Q, bound })
    // MEASURED, and stronger than the bound above: the first hop loses nothing at all. A cell with a
    // single receiver normalizes that receiver's weight as ww/ww, which rounds to exactly 1.0f, so
    // the authored 1200 m3/s arrives in the next cell as the same double it was authored as. This is
    // the story's sentence — "discharge immediately downstream equals the authored source flow" — in
    // its exact form rather than its tolerant one.
    check('the first hop carries the authored flow exactly', qDown === SPRING_Q,
      { qDown, authored: SPRING_Q, ulps: (qDown - SPRING_Q) / Number.EPSILON })

    const qOut = qDesert[OUTLET_CELL]
    measured.qOutlet = qOut
    measured.outRelErr = Math.abs(qOut - SPRING_Q) / SPRING_Q
    check('the authored discharge is conserved to the outlet absent sinks',
      Math.abs(qOut - SPRING_Q) <= bound, { qOut, authored: SPRING_Q, diff: qOut - SPRING_Q, bound })
    // A SECOND, TIGHTER BOUND BETWEEN TWO MEASURED ENDPOINTS. gamma_(N-1) is the plan's conservative
    // Float32 reduction bound and works out at 3.663e-4 relative — loose enough that a build losing
    // three parts in ten thousand of the Nile would still pass it. Both endpoints were measured on
    // this fixture: the correct build carries 1199.998927 m3/s to the outlet, a relative error of
    // 8.941e-7 accumulated over 75 hops of Float32 weight normalization, and the nearest wrong build
    // in the mutation list — authored m3/s treated as a per-area rate — carries 119999.89, a relative
    // error of 9.900e+1. 1e-5 sits eleven times above the passing reading and seven decades below
    // the failing one.
    check('the conserved discharge is not merely inside the conservative bound',
      measured.outRelErr <= 1e-5, { relErr: measured.outRelErr, tight: 1e-5, planBound: bound / SPRING_Q })

    // The river is exactly the cells downstream of the spring, and nothing else is wet. This is what
    // a "flow cone" means, asserted as a cell count rather than as a picture.
    let wet = 0, wetOffAxis = 0, wetUpstream = 0
    for (let i = 0; i < N; i++) {
      if (qDesert[i] === 0) continue
      wet++
      const row = (i / W) | 0, col = i - row * W
      if (row !== AXIS) wetOffAxis++
      else if (col < 20) wetUpstream++
    }
    check('the desert river wets exactly the axis cells downstream of the spring',
      wet === W - 20 && wetOffAxis === 0 && wetUpstream === 0,
      { wet, expected: W - 20, wetOffAxis, wetUpstream })

    // "Removing the source returns exactly zero." Not "small", not "below a threshold": every one of
    // the 6144 samples is the zero double.
    const empty = M.sourceSupply(surface, W, H, { sources: [] }, { cellSizeM: CELL })
    const qEmpty = HYD.mfdAccumulate(surface, M.combineSupply(dry, empty.supply), W, H, weights)
    let nonZero = 0, worst = 0
    for (let i = 0; i < N; i++) if (qEmpty[i] !== 0) { nonZero++; worst = Math.max(worst, Math.abs(qEmpty[i])) }
    check('removing the source returns exactly zero everywhere', nonZero === 0, { nonZero, worst })
    check('the empty desert seeded nothing at all',
      empty.seededCount === 0 && empty.totalQM3PerS === 0, { seededCount: empty.seededCount, totalQ: empty.totalQM3PerS })

    // === no height was written ====================================================================
    // Guardrail 1, and `03:702-707`: a spring is a source term in the flow field, not a bump in the
    // height field. Compared bitwise across a full seed AND route, not within a tolerance.
    let surfaceChanged = 0
    for (let i = 0; i < N; i++) if (surface[i] !== before[i]) surfaceChanged++
    check('the routing surface is bit-identical after seeding and routing', surfaceChanged === 0, { surfaceChanged })

    // === Q proportional to A under rain; divergent with a source ==================================
    const areaAcc = HYD.mfdAccumulate(surface, new Float64Array(N).fill(area), W, H, weights)
    let minArea = Infinity
    for (let i = 0; i < N; i++) minArea = Math.min(minArea, areaAcc[i])
    check('every cell has a positive drainage area', minArea >= area * 0.999, { minArea, area })

    const PRECIP = 1000
    const rain = HYD.precipToSupply(PRECIP, area, N)
    const qRain = HYD.mfdAccumulate(surface, M.combineSupply(rain, empty.supply), W, H, weights)
    const c = PRECIP * 1e-3 / HYD.SECONDS_PER_YEAR
    let worstProp = 0
    for (let i = 0; i < N; i++) worstProp = Math.max(worstProp, Math.abs(qRain[i] - c * areaAcc[i]) / (c * areaAcc[i]))
    measured.worstProp = worstProp
    // The story: "Under uniform rain Q is proportional to A and nothing changes."
    check('under uniform rain and no sources Q is proportional to A',
      worstProp <= gamma(8), { worstProp, bound: gamma(8), constant: c })

    const qBoth = HYD.mfdAccumulate(surface, M.combineSupply(rain, seeded.supply), W, H, weights)
    let divergeOn = 0, worstOff = 0
    for (let i = 0; i < N; i++) {
      const rel = Math.abs(qBoth[i] - c * areaAcc[i]) / (c * areaAcc[i])
      const row = (i / W) | 0, col = i - row * W
      if (row === AXIS && col >= 20) divergeOn = Math.max(divergeOn, rel)
      else worstOff = Math.max(worstOff, rel)
    }
    measured.divergeOn = divergeOn
    // Two MEASURED endpoints, not a chosen threshold: off the river Q/A is the rain constant to
    // within gamma_8 (1e-6 relative), on the river it is 1.6e4 times it. The claim is that a source
    // makes Q and A diverge, and both halves of it are read off the same field.
    check('with a source Q and A diverge on the river and nowhere else',
      divergeOn > 100 && worstOff <= gamma(8), { divergeOn, worstOff, bound: gamma(8) })

    // === move: id and properties survive; only the flow cones change ==============================
    const moved = M.moveSource(spring, 500, 200)
    check('moving a source keeps its id kind discharge and temperature',
      moved.id === spring.id && moved.kind === spring.kind
      && moved.dischargeM3PerS === SPRING_Q && moved.temperatureC === 24
      && moved.xM === 500 && moved.zM === 200,
      { moved })
    const seededB = M.sourceSupply(surface, W, H, { sources: [moved] }, { cellSizeM: CELL })
    const qMoved = HYD.mfdAccumulate(surface, M.combineSupply(dry, seededB.supply), W, H, weights)
    const coneA = coneFrom(SPRING_CELL, weights)
    const coneB = coneFrom(seededB.placements[0].index, weights)
    let changed = 0, changedOutsideCones = 0
    for (let i = 0; i < N; i++) {
      if (qDesert[i] === qMoved[i]) continue
      changed++
      if (!coneA[i] && !coneB[i]) changedOutsideCones++
    }
    check('moving the source changed the discharge field at all', changed > 0, { changed })
    check('moving the source changes only the two downstream flow cones',
      changedOutsideCones === 0, { changed, changedOutsideCones })

    // === serialization, reload, copy/paste ========================================================
    const guideChannel = { id: 'nileCourse', intent: 'channel', targetFlowM3PerS: 300, points: [[200, 320], [500, 320], [900, 320]] }
    const guideRef = { id: 'oldCourse', intent: 'reference', points: [[100, 100], [400, 140]] }
    // Every world position in this file is chosen to stay inside the 96x64 domain when the x and z
    // axes are SWAPPED. That is not cosmetic: the `source-cell-swaps-axes` mutation must be caught by
    // the placement assertions, and a fixture that instead threw SOURCE_OFF_DOMAIN would abort the
    // run at the first swapped source and leave every later gate unevaluated.
    const doc = { sources: [spring, { id: 'karstEye', kind: 'karstResurgence', xM: 500, zM: 320, dischargeM3PerS: 45 }], guides: [guideChannel, guideRef] }
    const text = M.serializeWaterFeatures(doc)
    const shuffled = M.serializeWaterFeatures({ sources: [doc.sources[1], doc.sources[0]], guides: [guideRef, guideChannel] })
    check('serialization is deterministic under input reordering', text === shuffled,
      { equal: text === shuffled, lenA: text.length, lenB: shuffled.length })
    check('serialization round-trips through parse',
      M.serializeWaterFeatures(M.parseWaterFeatures(text)) === text, { bytes: text.length })
    check('the serialized document carries both features and a schema version',
      /"schemaVersion": 1/.test(text) && /"nileSpring"/.test(text) && /"nileCourse"/.test(text)
      && /"temperatureC": 24/.test(text), { bytes: text.length })
    // SALINITY IS OUT OF SCOPE. Asserted on the SURFACE — the serialized document and the module's
    // exported names — because "we did not implement it" and "we implemented it badly" are
    // indistinguishable on a record until someone looks. The file's prose says why it is absent; the
    // schema and the API are what must not carry it.
    check('salinity is absent from the schema and the exported surface',
      !/salin/i.test(text) && !Object.keys(M).some(k => /salin/i.test(k))
      && !/salin/i.test(JSON.stringify(M.waterFeatureRecords(doc))),
      { exports: Object.keys(M).filter(k => /salin/i.test(k)) })

    const reloaded = M.parseWaterFeatures(text)
    const seededReload = M.sourceSupply(surface, W, H, reloaded, { cellSizeM: CELL })
    const qReload = HYD.mfdAccumulate(surface, M.combineSupply(dry, seededReload.supply), W, H, weights)
    const seededDoc = M.sourceSupply(surface, W, H, doc, { cellSizeM: CELL })
    const qDoc = HYD.mfdAccumulate(surface, M.combineSupply(dry, seededDoc.supply), W, H, weights)
    let reloadDiff = 0
    for (let i = 0; i < N; i++) if (qReload[i] !== qDoc[i]) reloadDiff++
    check('save and reload reproduce the discharge field bit-identically', reloadDiff === 0, { reloadDiff })
    const rs = reloaded.sources.find(s => s.id === 'nileSpring')
    check('a reloaded source keeps its id kind discharge and temperature',
      !!rs && rs.kind === 'spring' && rs.dischargeM3PerS === SPRING_Q && rs.temperatureC === 24
      && rs.xM === SPRING_X && rs.zM === SPRING_Z, { rs })

    const copy = M.duplicateFeature(spring, M.featureIds(doc))
    check('a pasted copy gets a fresh id and identical properties',
      copy.id !== spring.id && copy.kind === spring.kind && copy.dischargeM3PerS === SPRING_Q
      && copy.xM === SPRING_X && copy.temperatureC === 24, { copy })
    const pasteOk = attempt(() => M.normalizeWaterFeatures({ sources: [spring, copy], guides: [] }))
    check('a document containing the original and its paste is legal', pasteOk.ok, pasteOk)

    // A versionless blob is the pre-S4.3 shape and migrates; a future one is refused rather than
    // partially read, because a river network missing pieces looks exactly like a river network.
    const v0 = attempt(() => M.migrateWaterFeatures({ sources: [spring], guides: [] }))
    check('a versionless document migrates to the current schema',
      v0.ok && v0.value.schemaVersion === M.WATER_FEATURE_SCHEMA_VERSION && v0.value.sources.length === 1, v0)
    const vNext = attempt(() => M.migrateWaterFeatures({ schemaVersion: M.WATER_FEATURE_SCHEMA_VERSION + 1, sources: [] }))
    check('a future schema version is refused', !vNext.ok && vNext.code === 'SCHEMA_VERSION', vNext)

    // === identity and validation refusals =========================================================
    const noId = attempt(() => M.normalizeSource({ kind: 'spring', xM: 10, zM: 10, dischargeM3PerS: 1 }))
    check('a source with no authored id is refused', !noId.ok && noId.code === 'ID_INVALID', noId)
    const dup = attempt(() => M.normalizeWaterFeatures({ sources: [spring, { ...spring, xM: 300 }], guides: [] }))
    check('a duplicate id is refused', !dup.ok && dup.code === 'ID_DUPLICATE', dup)
    const dupCross = attempt(() => M.normalizeWaterFeatures({ sources: [spring], guides: [{ ...guideChannel, id: 'nileSpring' }] }))
    check('a guide sharing a source id is refused', !dupCross.ok && dupCross.code === 'ID_DUPLICATE', dupCross)
    const badKind = attempt(() => M.normalizeSource({ ...spring, kind: 'waterfall' }))
    check('an unknown source kind is refused', !badKind.ok && badKind.code === 'KIND_UNKNOWN', badKind)
    const negative = attempt(() => M.normalizeSource({ ...spring, dischargeM3PerS: -50 }))
    check('a negative discharge is refused', !negative.ok && negative.code === 'DISCHARGE_INVALID', negative)
    const pointRain = attempt(() => M.normalizeSource({ ...spring, kind: 'distributedRain' }))
    check('distributed rain without a footprint is refused', !pointRain.ok && pointRain.code === 'RADIUS_INVALID', pointRain)

    const off = M.sourceSupply(surface, W, H, { sources: [{ ...spring, enabled: false }] }, { cellSizeM: CELL })
    let offSum = 0
    for (let i = 0; i < N; i++) offSum += off.supply[i]
    check('a disabled source contributes exactly zero',
      offSum === 0 && off.seededCount === 0 && off.placements[0].enabled === false,
      { offSum, seededCount: off.seededCount })

    // === a distributed footprint conserves its total ==============================================
    const RAD = 25, fx = centreX(48, 32, false), fz = centreZ(32, false)
    const rain2 = M.sourceSupply(surface, W, H,
      { sources: [{ id: 'monsoonCell', kind: 'distributedRain', xM: fx, zM: fz, dischargeM3PerS: 210, radiusM: RAD }] },
      { cellSizeM: CELL })
    // Independent expected footprint: every cell whose centre is within the radius, found by scanning
    // the whole domain rather than by asking the module which cells it used.
    const expectCells = []
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      if (Math.hypot(centreX(x, y, false) - fx, centreZ(y, false) - fz) <= RAD) expectCells.push(y * W + x)
    }
    let footSum = 0, footCells = 0, footUneven = 0
    const each = 210 / expectCells.length
    for (let i = 0; i < N; i++) if (rain2.supply[i] !== 0) { footCells++; footSum += rain2.supply[i]; if (Math.abs(rain2.supply[i] - each) > 1e-12) footUneven++ }
    check('a distributed source covers the footprint the oracle computes independently',
      footCells === expectCells.length && expectCells.length === 21 && footUneven === 0,
      { footCells, expected: expectCells.length, footUneven })
    check('a distributed source conserves its authored total',
      Math.abs(footSum - 210) <= gamma(expectCells.length) * 210, { footSum, authored: 210, bound: gamma(expectCells.length) * 210 })

    // === guides ===================================================================================
    const gset = M.normalizeWaterFeatures({ sources: [], guides: [guideChannel, guideRef] })
    check('a guide keeps its ordered control points and measures its own length',
      gset.guides.length === 2 && gset.guides[0].id === 'nileCourse'
      && gset.guides[0].points.length === 3 && Math.abs(gset.guides[0].lengthM - 700) < 1e-9,
      { guides: gset.guides.map(g => ({ id: g.id, pts: g.points.length, lengthM: g.lengthM })) })
    const shortGuide = attempt(() => M.normalizeGuide({ id: 'stub', intent: 'channel', points: [[1, 2]] }))
    check('a one-point guide is refused', !shortGuide.ok && shortGuide.code === 'POINTS_INVALID', shortGuide)
    const badIntent = attempt(() => M.normalizeGuide({ ...guideChannel, intent: 'suggestion' }))
    check('an unknown guide intent is refused', !badIntent.ok && badIntent.code === 'INTENT_UNKNOWN', badIntent)

    // Target flow is OPT-IN.
    const noSeed = M.sourceSupply(surface, W, H, { sources: [], guides: [guideChannel] }, { cellSizeM: CELL })
    let noSeedSum = 0
    for (let i = 0; i < N; i++) noSeedSum += noSeed.supply[i]
    check('a guide target flow is not seeded unless asked', noSeedSum === 0 && noSeed.guideSeededCount === 0,
      { noSeedSum, guideSeeded: noSeed.guideSeededCount })

    const headSeed = M.sourceSupply(surface, W, H, { sources: [], guides: [guideChannel] }, { cellSizeM: CELL, includeGuideTargets: true })
    const headCell = rowOf(320, false) * W + colOf(200, rowOf(320, false), false)
    let headNz = 0
    for (let i = 0; i < N; i++) if (headSeed.supply[i] !== 0) headNz++
    check('a channel guide seeds its head cell with the target flow',
      headNz === 1 && headSeed.supply[headCell] === 300 && headSeed.guideSeededCount === 1,
      { headNz, atHead: headSeed.supply[headCell], headCell, guideSeeded: headSeed.guideSeededCount })

    const refSeed = M.sourceSupply(surface, W, H, { sources: [], guides: [{ ...guideRef, targetFlowM3PerS: 500 }] }, { cellSizeM: CELL, includeGuideTargets: true })
    let refSum = 0
    for (let i = 0; i < N; i++) refSum += refSeed.supply[i]
    check('a reference guide never seeds flow', refSum === 0 && refSeed.guideSeededCount === 0,
      { refSum, guideSeeded: refSeed.guideSeededCount })

    // The emitted guide record must be the shape S4.6's conflict analyser already consumes; a guide
    // that needs a translation layer to reach it is a guide that will one day stop reaching it.
    const records = M.waterFeatureRecords(doc)
    const guideRec = records.guides.find(g => g.id === 'nileCourse')
    check('the emitted guide record has the shape water_conflict.js reads',
      !!guideRec && Array.isArray(guideRec.points) && guideRec.points.length === 3
      && Number.isFinite(guideRec.points[0].x) && Number.isFinite(guideRec.points[0].z), { guideRec })
    check('a source record is not mistaken for a guide',
      records.sources.every(s => !Array.isArray(s.points)) && records.sources.length === 2,
      { sources: records.sources.map(s => s.id) })
    const analysed = attempt(() => CFL.analyzeGuideConflict(surface, W, H, guideRec.points,
      { cellSizeM: CELL, heightScaleM: 1000, resolution: W, flow: { dirX: weights.dirX, dirZ: weights.dirZ } }))
    check('the S4.6 conflict analyser consumes the emitted guide',
      analysed.ok && analysed.value.count > 1 && analysed.value.flowSupplied === true,
      { ok: analysed.ok, count: analysed.ok ? analysed.value.count : null, code: analysed.code, message: analysed.message })
    // The guide runs straight down the valley axis, which drains: an authored route that agrees with
    // the terrain must report NO conflict, or the analyser is calling everything a problem.
    check('a guide drawn down the valley reports no elevation deficit',
      analysed.ok && analysed.value.conflictCount === 0,
      { conflictCount: analysed.ok ? analysed.value.conflictCount : null, maxDeficitM: analysed.ok ? analysed.value.maxDeficitM : null })

    // === the authoring text block =================================================================
    const parsed = attempt(() => M.parseFeatureText(
      '# a desert river\nsource id=nileSpring kind=spring x=200 z=320 q=1200 t=24\n'
      + 'guide id=nileCourse intent=channel q=300 200,320 500,320 900,320\n'))
    check('the authoring text block parses one source and one guide',
      parsed.ok && parsed.value.sources.length === 1 && parsed.value.guides.length === 1
      && parsed.value.sources[0].dischargeM3PerS === 1200 && parsed.value.guides[0].points.length === 3, parsed)
    const typo = attempt(() => M.parseFeatureText('source id=a kind=spring x=1 z=1 dischage=5\n'))
    check('a mistyped key in the text block is refused with its line number',
      !typo.ok && typo.code === 'TEXT_SYNTAX' && /line 1/.test(typo.message), typo)

    // === the plugin's port block ==================================================================
    check('the Water Sources plugin source was read', typeof pluginSrc === 'string' && pluginSrc.length > 1000,
      { bytes: pluginSrc ? pluginSrc.length : 0 })
    const stripped = pluginSrc.replace(/^\s*\/\/.*$/gm, '')
    let inputs = null, outputs = null, params = null, parseErr = null
    try {
      inputs = new Function('RANGE', 'return ' + literalAfter(stripped, 'inputs:'))(Ports.RANGE)
      outputs = new Function('RANGE', 'return ' + literalAfter(stripped, 'outputs:'))(Ports.RANGE)
      const stub = key => ({ id: key })
      params = new Function('P', 'return ' + literalAfter(stripped, 'params:'))({ slider: stub, text: stub, toggle: stub })
    } catch (e) { parseErr = String((e && e.message) || e).slice(0, 200) }
    if (!check('the Water Sources port block parses',
      Array.isArray(inputs) && Array.isArray(outputs) && Array.isArray(params),
      { parseErr, inputs: inputs && inputs.length, outputs: outputs && outputs.length })) {
      for (const n of ['the plugin declares three inputs and five outputs',
        'the primary output is the untouched routing surface',
        'every Water Sources port validates against ports.js',
        'the discharge outputs are typed in m3PerS',
        'the feature ports carry the featureSet kind']) check(n, false, 'port block did not parse')
      return
    }
    check('the plugin declares three inputs and five outputs',
      inputs.length === 3 && outputs.length === 5, { inputs: inputs.length, outputs: outputs.length })
    const primary = outputs.filter(p => p.primary)
    check('the primary output is the untouched routing surface',
      primary.length === 1 && primary[0].id === 'routingSurface'
      && primary[0].semantic === 'routingSurface' && primary[0].lens === 'continued',
      { primary: primary.map(p => p.id) })
    const problems = Ports.validatePortList({ inputs, outputs, source: 'declared' })
    check('every Water Sources port validates against ports.js', problems.length === 0, problems)
    const qPorts = outputs.filter(p => p.semantic === 'discharge')
    check('the discharge outputs are typed in m3PerS',
      qPorts.length === 2 && qPorts.every(p => p.unit === 'm3PerS' && p.storage === 'R32F'),
      { qPorts: qPorts.map(p => ({ id: p.id, unit: p.unit })) })
    const featurePorts = outputs.filter(p => p.kind === 'featureSet')
    check('the feature ports carry the featureSet kind',
      featurePorts.length === 2 && featurePorts.every(p => p.storage === 'RECORDS' && p.semantic === 'feature' && p.unit === 'none'),
      { featurePorts: featurePorts.map(p => p.id) })
    check('the plugin exposes no salinity parameter and no water-level knob',
      params.every(p => !/salin|level/i.test(p.id)) && params.length === 3, { params: params.map(p => p.id) })
    // TRIPWIRE. The unrouted source term is m3/s at a cell, which is NOT a discharge, and ports.js
    // has no semantic for it today — so `sourceSupply` ships as `discharge` and nothing can refuse it
    // being wired into a Rivers node. The story report asks for `waterSupply`. When it lands this
    // goes red and forces the port and this assertion to be updated together, rather than leaving a
    // comment describing a world that has moved on.
    check('waterSupply is not yet a ports.js semantic',
      Ports.SEMANTICS.waterSupply === undefined, { present: Ports.SEMANTICS.waterSupply || null })

    check('assertion inventory non-empty', assertions.length >= 45, assertions.length)
  }

  /** Every cell reachable downslope of `index` through the MFD receiver graph. Computed from the
   *  routing weights, independently of anything the source module reports. */
  function coneFrom(index, weights) {
    const seen = new Uint8Array(N)
    const stack = [index]
    seen[index] = 1
    while (stack.length) {
      const i = stack.pop()
      for (let k = 0; k < weights.nbCount; k++) {
        const ni = weights.rcv[i * weights.nbCount + k]
        if (ni < 0 || weights.wgt[i * weights.nbCount + k] <= 0) continue
        if (!seen[ni]) { seen[ni] = 1; stack.push(ni) }
      }
    }
    return seen
  }

  function literalAfter(src, key) {
    const at = src.indexOf(key)
    if (at < 0) return 'null'
    const start = src.indexOf('[', at)
    let depth = 0
    for (let i = start; i < src.length; i++) {
      if (src[i] === '[') depth++
      else if (src[i] === ']') { depth--; if (depth === 0) return src.slice(start, i + 1) }
    }
    return 'null'
  }

  function report() {
    let ok = assertions.every(a => a.ok)
    if (mutation) {
      if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
      ok = false
    }
    const failed = assertions.filter(a => !a.ok).map(a => a.name)
    const f = (v, d = 6) => (Number.isFinite(v) ? v.toFixed(d) : 'n/a')
    console.log(`${ok ? 'PASS' : 'FAIL'}  water sources qDown=${f(measured.qDownstream, 6)} `
      + `downRelErr=${Number.isFinite(measured.downRelErr) ? measured.downRelErr.toExponential(3) : 'n/a'} `
      + `qOutlet=${f(measured.qOutlet, 6)} authored=${SPRING_Q} outRelErr=${Number.isFinite(measured.outRelErr) ? measured.outRelErr.toExponential(3) : 'n/a'} `
      + `planBound=${Number.isFinite(measured.bound) ? (measured.bound / SPRING_Q).toExponential(3) : 'n/a'} `
      + `propErr=${Number.isFinite(measured.worstProp) ? measured.worstProp.toExponential(3) : 'n/a'} `
      + `divergeOn=${Number.isFinite(measured.divergeOn) ? measured.divergeOn.toExponential(3) : 'n/a'} `
      + `assertions=${assertions.length} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
    if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify(assertions.filter(a => !a.ok), null, 2))
    process.exit(ok ? 0 : 1)
  }
})().catch(e => { console.error('FATAL', (e && e.stack) || e); process.exit(2) })
