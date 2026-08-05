// S4.5 — rivers as FIELDS, not a carve.
//
// A PURE-MODULE oracle: it imports src/core/rivers.js under plain node and checks the hydraulic
// geometry in double precision with no browser. Mutations are applied by patching the module's
// source text and importing the patched copy, so every control is a real change to the real code.
//
// THE ASSERTION THIS ORACLE EXISTS FOR is the negative one. Every shipping river node this project
// has looked at downcuts — it reads a flow field and subtracts a trench from the height — and the
// whole of S4.5 is the claim that a river is a set of fields ABOUT water sitting on ground that
// nothing moved. So the bed is snapshotted before the call and compared BITWISE after, twice: once
// against the array the caller still holds, and once against the array the node publishes. Those are
// different failures. `carve-in-place` writes through the caller's array; `carve-copy` politely
// leaves it alone and ships a carved copy as its primary output, which is the same defect wearing a
// clean shirt, and only the second check sees it.
//
// THE LAW. Leopold & Maddock 1953 downstream hydraulic geometry: w = kw*Q^0.5, d = kd*Q^0.4, and by
// continuity v = kv*Q^0.1 with the three exponents summing to exactly 1 and kw*kd*kv = 1. The
// reference values here are computed from LITERAL exponents, never from the module's constants — an
// oracle that read the exponent it is checking would score every exponent mutation as a pass, which
// is the vacuous gate in its purest form.
//
// The at-a-station exponent (Q^0.26, how one cross-section responds to a passing flood) is armed as
// a mutation because it is the standard confusion and it under-widens every large river.
const path = require('path')
const fs = require('fs')
const { pathToFileURL } = require('url')

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'carve-in-place',        // the node digs the channel out of the caller's bed array
  'carve-copy',            // the caller's array survives; the PUBLISHED bed is carved
  'water-surface-is-trench', // depth read as "dig down": the free surface ends up below the bed
  'at-a-station-width',    // Q^0.26 instead of Q^0.5 -- the standard hydraulic-geometry confusion
  'depth-exponent-half',   // depth exponent copied from width: Q^0.5 instead of Q^0.4
  'constant-width',        // width independent of discharge -- the instant tell
  'binary-mask',           // channel stamped solid: every river one cell wide whatever its discharge
  'no-channel-head',       // channel initiation threshold removed: hillslopes become rivers
  'straight-guide',        // the mask is a drawn straight line, not derived from where water goes
  'ports-offer-carve',     // the node declares AND computes a carved-terrain output
  'mask-unclamped',        // coverage fraction left unclamped: a "fraction" of 8.5 on a real river
  'ignore-bankfull',       // the bankfull slider wired to nothing
  // The module's own stated refusals. Both were written as deliberate guards with comments
  // explaining why, and neither had an assertion until the Sprint 4 audit found them.
  'nan-propagates',        // `qb < t` instead of `!(qb >= t)`: NaN enters the channel and spreads
  'lattice-mismatch-clamped', // size to the shorter array instead of throwing: a river on wrong ground
]
const PATCHES = {
  // NaN fails BOTH comparisons, so the negated form skips the cell and the plain form enters it.
  'nan-propagates': [['    if (!(qb >= channelHeadQM3PerS)) continue',
    '    if (qb < channelHeadQM3PerS) continue']],
  'lattice-mismatch-clamped': [['  if (solidTopM.length < N || dischargeM3PerS.length < N) {',
    '  if (false) {']],
  'carve-in-place': [[
    '    waterSurface[i] = solidTopM[i] + dM',
    '    solidTopM[i] -= dM\n    waterSurface[i] = solidTopM[i] + dM',
  ]],
  'carve-copy': [[
    '  return { solidTop: solidTopM, channelMask,',
    '  const carved = new Float32Array(N)\n'
    + '  for (let i = 0; i < N; i++) carved[i] = solidTopM[i] - waterDepth[i]\n'
    + '  return { solidTop: carved, channelMask,',
  ]],
  'water-surface-is-trench': [[
    '    waterSurface[i] = solidTopM[i] + dM',
    '    waterSurface[i] = solidTopM[i] - dM',
  ]],
  'at-a-station-width': [['export const WIDTH_EXPONENT = 0.5', 'export const WIDTH_EXPONENT = 0.26']],
  'depth-exponent-half': [['export const DEPTH_EXPONENT = 0.4', 'export const DEPTH_EXPONENT = 0.5']],
  'constant-width': [[
    '    const wM = widthCoefficient * Math.pow(qb, WIDTH_EXPONENT)',
    '    const wM = widthCoefficient',
  ]],
  'binary-mask': [[
    '    channelMask[i] = Math.min(1, wM / cellSizeM)',
    '    channelMask[i] = 1',
  ]],
  'no-channel-head': [[
    '    if (!(qb >= channelHeadQM3PerS)) continue',
    '    if (!(qb > 0)) continue',
  ]],
  // A drawn guide down the middle of the domain: the shape a user asked for rather than the shape
  // the water takes. It keeps a non-empty channel, so it cannot be caught by "did anything happen" —
  // only by comparing the skeleton against where the discharge actually is.
  'straight-guide': [[
    '  return { solidTop: solidTopM, channelMask,',
    '  channelMask.fill(0); channelWidth.fill(0); waterDepth.fill(0)\n'
    + '  channelCells = 0\n'
    + '  for (let y = 0; y < hgt; y++) {\n'
    + '    const i = y * w + (w >> 1)\n'
    + '    channelMask[i] = 1; channelWidth[i] = cellSizeM; waterDepth[i] = 1; channelCells++\n'
    + '  }\n'
    + '  return { solidTop: solidTopM, channelMask,',
  ]],
  'ports-offer-carve': [
    ["    { id: 'channelMask', name: 'Channel',",
     "    { id: 'carvedHeight', name: 'Carved', kind: 'scalarRaster', storage: 'R32F', components: 1,\n"
     + "      semantic: 'solidTop', unit: 'm', lens: 'derived' },\n"
     + "    { id: 'channelMask', name: 'Channel',"],
    ['  return { solidTop: solidTopM, channelMask,',
     '  const carvedHeight = new Float32Array(N)\n'
     + '  for (let i = 0; i < N; i++) carvedHeight[i] = solidTopM[i] - waterDepth[i]\n'
     + '  return { carvedHeight, solidTop: solidTopM, channelMask,'],
  ],
  // The Y-valley's largest river is 0.28 m wide in a 10 m cell, so NO cell of it ever reaches the
  // clamp — measured, zero cells wide enough. Deleting the Math.min therefore changed nothing any
  // assertion could see: measured, the whole oracle stayed green with the clamp gone. That is the
  // regime a real river actually lives in (2.7*sqrt(1000) = 85 m on 10 m cells), and an unclamped
  // mask ships a "fraction of the cell covered" of 8.5.
  'mask-unclamped': [[
    '    channelMask[i] = Math.min(1, wM / cellSizeM)',
    '    channelMask[i] = wM / cellSizeM',
  ]],
  // The node exposes a 1-8 bankfull slider. Measured, raising it to 8 takes this fixture from 107
  // channel cells to 2223, so it changes what ships — and measured, deleting the factor from the code
  // left the whole oracle green. A parameter that can be wired to nothing without a gate noticing is
  // the vacuous gate wearing a slider.
  'ignore-bankfull': [[
    '    const qb = bankfullFactor * dischargeM3PerS[i]',
    '    const qb = dischargeM3PerS[i]',
  ]],
}
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

// --- the analytic Y-valley --------------------------------------------------------------------
// Two straight tributaries meeting at a known confluence, then a trunk to the domain's base level.
// Heights are METRES from a stable datum, because that is what the node's `solidTop` port carries:
// water depth is in metres and adding it to a normalised [0,1] field would be a unit error.
const W = 64, H = 64, N = W * H, CELL = 10          // 10 m cells, 640 m square
const CX = 32, CONF_Y = 32, HEAD_Y = 4, HEAD_DX = 12
const DATUM_M = 400, DOWN_M = 0.6, CROSS_M = 1.0    // 6% down-valley, 10% cross-valley
const SEGMENTS = [
  [CX - HEAD_DX, HEAD_Y, CX, CONF_Y],               // west tributary
  [CX + HEAD_DX, HEAD_Y, CX, CONF_Y],               // east tributary
  [CX, CONF_Y, CX, H - 1],                          // trunk
]
function segDist(px, py, x1, y1, x2, y2) {
  const dx = x2 - x1, dy = y2 - y1
  const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
  return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
}
const thalwegDist = (x, y) => Math.min(...SEGMENTS.map(s => segDist(x, y, s[0], s[1], s[2], s[3])))

function yValley() {
  const h = new Float32Array(N)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    h[y * W + x] = DATUM_M - DOWN_M * y + CROSS_M * thalwegDist(x, y)
  }
  // BASE LEVEL. Without it the bottom row is a closed wall: water that cannot leave the domain runs
  // sideways ALONG the last row toward the trunk, and 28 cells of that row accumulate enough to
  // channelise. Measured, that put channel cells 14 lattice steps from the nearest thalweg — an
  // artefact of the boundary, not of the river. A flat row below everything is an open outlet: flow
  // arrives and stops, which is what a coastline does.
  let lo = Infinity
  for (let i = 0; i < N; i++) if (h[i] < lo) lo = h[i]
  for (let x = 0; x < W; x++) h[(H - 1) * W + x] = lo - 5
  return h
}

;(async () => {
  const coreDir = path.resolve(__dirname, '../../src/core')
  const src = path.join(coreDir, 'rivers.js')
  let M = null, Hy = null, PORTS = null, loadErr = null
  try {
    Hy = await import(pathToFileURL(path.join(coreDir, 'hydrology.js')).href)
    PORTS = await import(pathToFileURL(path.join(coreDir, 'ports.js')).href)
    if (!mutation) { M = await import(pathToFileURL(src).href) }
    else {
      let text = fs.readFileSync(src, 'utf8')
      for (const [anchor, repl] of PATCHES[mutation]) {
        const hits = text.split(anchor).length - 1
        if (hits !== 1) { console.error(`FATAL anchor for ${mutation} matched ${hits}, expected 1`); process.exit(2) }
        text = text.replace(anchor, repl)
      }
      // A data: URL module has no base to resolve `./hydrology.js` against, so relative specifiers
      // are rewritten to absolute file URLs first. Without this EVERY mutation would die at import
      // and score as armed for a reason that has nothing to do with the mutation — a whole gate
      // that is red for the wrong cause is worth less than no gate at all.
      const base = pathToFileURL(coreDir + path.sep).href
      let rewrites = 0
      text = text.replace(/from '\.\/([^']+)'/g, (m, rel) => { rewrites++; return `from '${base}${rel}'` })
      if (rewrites < 1) { console.error('FATAL relative-import rewrite matched nothing'); process.exit(2) }
      M = await import('data:text/javascript;base64,' + Buffer.from(text, 'utf8').toString('base64'))
    }
  } catch (e) { loadErr = String(e.message || e).slice(0, 200) }

  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }
  if (!check('module loads', M !== null, loadErr)) return report()

  // gamma_n = (n*u)/(1 - n*u) with u the Float32 unit roundoff. The plan's bound for the Float32
  // production path is gamma_8; a single store of a correctly-rounded product costs gamma_1, so this
  // is eight times the headroom actually needed and is not tuned.
  const U32 = Math.pow(2, -24)
  const gamma = n => (n * U32) / (1 - n * U32)
  const GAMMA8 = gamma(8)

  // --- the law, in closed form ------------------------------------------------------------------
  // LITERAL exponents. Reading them from the module would make every exponent mutation invisible.
  check('exponents are the Leopold-Maddock DOWNSTREAM set',
    M.WIDTH_EXPONENT === 0.5 && M.DEPTH_EXPONENT === 0.4 && M.VELOCITY_EXPONENT === 0.1,
    { width: M.WIDTH_EXPONENT, depth: M.DEPTH_EXPONENT, velocity: M.VELOCITY_EXPONENT })
  // Continuity forces Q = w*d*v, which holds for all Q only if the exponents sum to one. This is the
  // free check on the exponent set: a wrong width or depth exponent breaks it without any data.
  const expSum = M.WIDTH_EXPONENT + M.DEPTH_EXPONENT + M.VELOCITY_EXPONENT
  check('the exponents close continuity (they sum to 1)', Math.abs(expSum - 1) < 1e-12, { expSum })
  check('authored coefficients are the documented midcontinent defaults',
    M.DEFAULT_WIDTH_COEFFICIENT === 2.7 && M.DEFAULT_DEPTH_COEFFICIENT === 0.30,
    { kw: M.DEFAULT_WIDTH_COEFFICIENT, kd: M.DEFAULT_DEPTH_COEFFICIENT })
  // The channel-head default is a computed provenance, not a typed-in number: the flow 1e4 m2 yields
  // under 1000 mm/yr. Recomputed here from literals so a silent edit to either factor shows up.
  check('the channel-head discharge default carries its stated provenance',
    Math.abs(M.CHANNEL_HEAD_Q_M3PERS - (1000 * 1e-3 * 1e4 / 31536000)) < 1e-18,
    { value: M.CHANNEL_HEAD_Q_M3PERS, area: M.CHANNEL_HEAD_AREA_M2 })

  const KW = 2.7, KD = 0.30
  const THREE_Q = [0.5, 50, 5000]           // a creek, a river, a large river
  let worstW = 0, worstD = 0, worstV = 0, worstQ = 0
  const lawRows = []
  for (const q of THREE_Q) {
    const refW = KW * Math.sqrt(q)          // Q^0.5, correctly rounded
    const refD = KD * Math.pow(q, 0.4)      // literal 0.4
    const refV = (1 / (KW * KD)) * Math.pow(q, 0.1)
    const gotW = M.channelWidthM(q, KW), gotD = M.channelDepthM(q, KD), gotV = M.meanVelocityMPerS(q, KW, KD)
    worstW = Math.max(worstW, Math.abs(gotW - refW) / refW)
    worstD = Math.max(worstD, Math.abs(gotD - refD) / refD)
    worstV = Math.max(worstV, Math.abs(gotV - refV) / refV)
    // Continuity, closed: width x depth x velocity must give the discharge back.
    worstQ = Math.max(worstQ, Math.abs(gotW * gotD * gotV - q) / q)
    lawRows.push({ q, widthM: +gotW.toFixed(4), depthM: +gotD.toFixed(4), velocityMPerS: +gotV.toFixed(4) })
  }
  check('width follows kw*Q^0.5 at three discharges', worstW <= GAMMA8, { worstW, bound: GAMMA8, lawRows })
  check('water depth follows kd*Q^0.4 at three discharges', worstD <= GAMMA8, { worstD, bound: GAMMA8, lawRows })
  check('mean velocity is kv*Q^0.1 with kv = 1/(kw*kd)', worstV <= GAMMA8, { worstV, bound: GAMMA8 })
  check('width x depth x velocity returns the discharge', worstQ <= GAMMA8, { worstQ, bound: GAMMA8 })

  // --- channel initiation is a threshold, not a fade --------------------------------------------
  const qHead = M.CHANNEL_HEAD_Q_M3PERS
  const belowField = new Float32Array(N).fill(qHead * 0.999)
  const aboveField = new Float32Array(N).fill(qHead * 1.001)
  // A FRESH BED PER CALL. Sharing one would let a carve mutation poison the next fixture's input and
  // turn an unrelated assertion red — a mutation that goes red for the wrong reason is not evidence.
  const flatBed = () => new Float32Array(N).fill(DATUM_M)
  const belowBedIn = flatBed()
  const below = M.riverFields(belowBedIn, belowField, W, H, { widthCoefficient: KW, depthCoefficient: KD, cellSizeM: CELL })
  const above = M.riverFields(flatBed(), aboveField, W, H, { widthCoefficient: KW, depthCoefficient: KD, cellSizeM: CELL })
  let belowNonZero = 0
  for (let i = 0; i < N; i++) {
    if (below.channelMask[i] !== 0 || below.channelWidth[i] !== 0 || below.waterDepth[i] !== 0) belowNonZero++
    if (below.waterSurface[i] !== DATUM_M) belowNonZero++
  }
  check('below the channel head every river field is EXACTLY zero',
    below.channelCells === 0 && belowNonZero === 0, { channelCells: below.channelCells, belowNonZero })
  check('one part in a thousand above the channel head, every cell is a channel',
    above.channelCells === N, { channelCells: above.channelCells, N })
  const zeroQ = M.riverFields(flatBed(), new Float32Array(N), W, H, { widthCoefficient: KW, depthCoefficient: KD, cellSizeM: CELL })
  check('zero discharge gives exactly zero channel', zeroQ.channelCells === 0, { channelCells: zeroQ.channelCells })

  // --- the mask is a COVERAGE FRACTION, so one is its ceiling ------------------------------------
  // A SEPARATE FIXTURE, because the Y-valley cannot reach this regime: its largest river is 0.28 m in
  // a 10 m cell and zero of its cells are wider than their cell, so the clamp in the mask is dead
  // code under that fixture. Measured: with `Math.min(1, ...)` deleted the entire oracle stayed green.
  // Q = 1000 m3/s gives 2.7*sqrt(1000) = 85.4 m, 8.5 cells wide — an ordinary large river on a 10 m
  // lattice — and the unclamped mask there reads 8.538, which is not a fraction of anything.
  const bigField = new Float32Array(N).fill(1000)
  const big = M.riverFields(flatBed(), bigField, W, H, { widthCoefficient: KW, depthCoefficient: KD, cellSizeM: CELL })
  let wideCells = 0, maskOverOne = 0, notFullyCovered = 0, bigMaxMask = 0
  for (let i = 0; i < N; i++) {
    if (big.channelWidth[i] > CELL) wideCells++
    if (big.channelMask[i] > 1) maskOverOne++
    if (big.channelMask[i] !== 1) notFullyCovered++
    if (big.channelMask[i] > bigMaxMask) bigMaxMask = big.channelMask[i]
  }
  // Absence of evidence is a failure: prove the fixture REACHED the clamp regime before reading it.
  // Without this the two checks below would pass on a fixture whose channels are all sub-cell, which
  // is exactly the hole they exist to close.
  check('the wide-channel fixture actually exceeds one cell of width',
    wideCells === N && big.channelWidth[0] > CELL,
    { wideCells, N, widthM: +big.channelWidth[0].toFixed(4), cellSizeM: CELL })
  check('the channel mask never exceeds one', maskOverOne === 0,
    { maskOverOne, maxMask: bigMaxMask })
  check('a channel wider than its cell covers the cell exactly', notFullyCovered === 0,
    { notFullyCovered, maxMask: bigMaxMask })

  // --- the analytic Y-valley --------------------------------------------------------------------
  const bed = yValley()
  const bedBefore = Float32Array.from(bed)
  const area = Hy.cellAreaM2(CELL, false)
  const weights = Hy.mfdWeights(bed, W, H, { cellSizeM: CELL })
  // FIXTURE SANITY FIRST. A fixture with interior pits traps its own water, and every skeleton
  // reading below would then be measuring a defect in the fixture. Absence of evidence is a failure.
  let interiorPits = 0
  for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) if (weights.outlet[y * W + x]) interiorPits++
  check('the Y-valley fixture has no interior pits', interiorPits === 0, { interiorPits })

  const PRECIP = 1000
  const q64 = Hy.mfdAccumulate(bed, Hy.precipToSupply(PRECIP, area, N), W, H, weights)
  const discharge = new Float32Array(N)
  for (let i = 0; i < N; i++) discharge[i] = q64[i]
  let qOutlet = 0
  for (let x = 0; x < W; x++) qOutlet += q64[(H - 1) * W + x]
  const qDomain = PRECIP * 1e-3 * N * area / Hy.SECONDS_PER_YEAR
  check('the fixture routes its whole catchment to base level',
    Math.abs(qOutlet - qDomain) <= qDomain * 1e-6, { qOutlet, qDomain })

  const r = M.riverFields(bed, discharge, W, H, {
    widthCoefficient: KW, depthCoefficient: KD, cellSizeM: CELL,
  })

  // --- GUARDRAIL 1: nothing moved the ground ----------------------------------------------------
  let inputChanged = 0, publishedChanged = 0
  for (let i = 0; i < N; i++) {
    if (bed[i] !== bedBefore[i]) inputChanged++
    if (r.solidTop[i] !== bedBefore[i]) publishedChanged++
  }
  check('the input bed survives BITWISE', inputChanged === 0, { inputChanged })
  check('the published bed is BITWISE the input bed', publishedChanged === 0, { publishedChanged })
  // Water is ADDED on top of the bed. A free surface below the ground is the carve, expressed in the
  // one field that is allowed to move.
  let surfaceBelowBed = 0, identityViolations = 0, worstIdentity = 0, worstIdentityBound = 0
  for (let i = 0; i < N; i++) {
    if (r.waterSurface[i] < r.solidTop[i]) surfaceBelowBed++
    const err = Math.abs((r.waterSurface[i] - r.solidTop[i]) - r.waterDepth[i])
    // The surface is a Float32 store of bed+depth, so recovering depth by subtraction costs the
    // rounding of that store against the much larger bed value; gamma_2 covers it with headroom.
    const bound = gamma(2) * (Math.abs(r.solidTop[i]) + Math.abs(r.waterDepth[i]))
    if (err > bound) identityViolations++
    if (err > worstIdentity) { worstIdentity = err; worstIdentityBound = bound }
  }
  check('the water surface never sits below the bed', surfaceBelowBed === 0, { surfaceBelowBed })
  check('waterSurface - solidTop closes to waterDepth', identityViolations === 0,
    { identityViolations, worstAbsErr: worstIdentity, boundAtWorst: worstIdentityBound })

  // --- the fields on the fixture ----------------------------------------------------------------
  let maskCells = 0, worstFieldW = 0, worstFieldD = 0, worstCoverage = 0, maxMask = 0, maxWidthM = 0
  for (let i = 0; i < N; i++) {
    if (r.channelMask[i] <= 0) continue
    maskCells++
    const q = discharge[i]
    const refW = KW * Math.sqrt(q), refD = KD * Math.pow(q, 0.4)
    worstFieldW = Math.max(worstFieldW, Math.abs(r.channelWidth[i] - refW) / refW)
    worstFieldD = Math.max(worstFieldD, Math.abs(r.waterDepth[i] - refD) / refD)
    // RELATIVE. The mask is a Float32 store of (double width)/cell, while this reference divides the
    // Float32 width — one extra rounding apart, so the identity is exact to gamma, not to the bit.
    const refCover = Math.min(1, r.channelWidth[i] / CELL)
    worstCoverage = Math.max(worstCoverage, Math.abs(r.channelMask[i] - refCover) / refCover)
    maxMask = Math.max(maxMask, r.channelMask[i])
    maxWidthM = Math.max(maxWidthM, r.channelWidth[i])
  }
  // Absence of evidence is a failure: every reading below is measured over these cells.
  check('the fixture produced a non-empty channel',
    r.channelCells > 0 && maskCells === r.channelCells, { channelCells: r.channelCells, maskCells })
  check('the Float32 field width matches the double-precision law', worstFieldW <= GAMMA8,
    { worstFieldW, bound: GAMMA8 })
  check('the Float32 field depth matches the double-precision law', worstFieldD <= GAMMA8,
    { worstFieldD, bound: GAMMA8 })
  // Sub-cell coverage, not a binary stamp. maxMask is reported because it is the physical reading:
  // a 0.28 m creek in a 10 m cell covers 2.8% of it, and a mask that said 1 would be a lie about
  // how much of the ground is water.
  check('the mask is sub-cell coverage of the channel width', worstCoverage <= GAMMA8,
    { worstCoverage, bound: GAMMA8, maxMask: +maxMask.toFixed(6), maxWidthM: +maxWidthM.toFixed(4) })

  // --- the skeleton -----------------------------------------------------------------------------
  // The base-level row is the sea, not the river: flow arrives there and stops, and it spreads along
  // it by construction. Skeleton readings are over the terrain rows.
  const rowsX = new Map()
  let maxThalwegDist = 0
  for (let y = 0; y < H - 1; y++) for (let x = 0; x < W; x++) {
    if (r.channelMask[y * W + x] <= 0) continue
    maxThalwegDist = Math.max(maxThalwegDist, thalwegDist(x, y))
    if (!rowsX.has(y)) rowsX.set(y, [])
    rowsX.get(y).push(x)
  }
  const channelRows = [...rowsX.keys()].sort((a, b) => a - b)
  check('the channel is present on many rows, not a handful of cells',
    channelRows.length > (H - 1) * 0.5, { channelRows: channelRows.length, terrainRows: H - 1 })
  // The plan's bound: within ONE cell of the known thalweg. Measured 0.919 on the correct path and
  // 9.8+ with a drawn straight guide, so the bound sits between two measured builds.
  check('every channel cell is within one cell of an analytic thalweg', maxThalwegDist <= 1.0,
    { maxThalwegDist: +maxThalwegDist.toFixed(4) })

  const clustersAt = y => {
    const xs = (rowsX.get(y) || []).slice().sort((a, b) => a - b)
    let c = 0
    for (let k = 0; k < xs.length; k++) if (k === 0 || xs[k] - xs[k - 1] > 1) c++
    return c
  }
  // Two threads above the confluence, one below, and the transition is where the analytic segments
  // meet. A guide-only straight line is one thread everywhere and fails all three.
  let twoAbove = 0, oneBelow = 0, notOneBelow = 0, joinRow = -1
  for (const y of channelRows) {
    const c = clustersAt(y)
    if (y < CONF_Y - 2) { if (c === 2) twoAbove++ }
    if (y > CONF_Y + 2) { if (c === 1) oneBelow++; else notOneBelow++ }
    if (joinRow < 0 && y > HEAD_Y && c === 1 && clustersAt(y - 1) === 2) joinRow = y
  }
  const aboveRows = channelRows.filter(y => y < CONF_Y - 2).length
  const belowRows = channelRows.filter(y => y > CONF_Y + 2).length
  check('both tributaries carry a channel above the confluence',
    aboveRows > 8 && twoAbove === aboveRows, { aboveRows, twoAbove })
  check('below the confluence there is exactly one thread',
    belowRows > 8 && notOneBelow === 0, { belowRows, oneBelow, notOneBelow })
  check('the threads join at the analytic confluence',
    joinRow >= 0 && Math.abs(joinRow - CONF_Y) <= 1, { joinRow, analyticConfluenceRow: CONF_Y })
  check('the channel reaches base level', (rowsX.get(H - 2) || []).length > 0,
    { lastTerrainRow: H - 2, cells: (rowsX.get(H - 2) || []).length })

  // --- downstream growth ------------------------------------------------------------------------
  let monotone = true, prev = -Infinity, trunkFirst = 0, trunkLast = 0
  for (let y = CONF_Y + 1; y < H - 1; y++) {
    const wM = r.channelWidth[y * W + CX]
    if (wM < prev) monotone = false
    if (y === CONF_Y + 1) trunkFirst = wM
    trunkLast = wM
    prev = wM
  }
  check('trunk width never decreases downstream', monotone, { trunkFirst, trunkLast })
  // ...and it must actually GROW. A constant-width river is monotone too.
  check('trunk width grows from confluence to base level', trunkLast > trunkFirst * 1.2,
    { trunkFirst: +trunkFirst.toFixed(4), trunkLast: +trunkLast.toFixed(4),
      ratio: +(trunkLast / trunkFirst).toFixed(4) })

  // --- the bankfull factor is a discharge scaling, and it is load-bearing -----------------------
  // The relations take the channel-forming flood, not the mean annual flow, and the node ships a 1-8
  // slider for that conversion. Measured, the slider matters: at 8 this fixture goes from 107 channel
  // cells to 2223. Measured, nothing gated it — with the factor deleted from the code the whole
  // oracle stayed green, so the slider could have been wired to nothing and every gate would have
  // agreed. Stated as an IDENTITY rather than a tolerance: scaling the factor by B is the same
  // computation as scaling the discharge by B. B = 8 is a power of two, so the Float32 rescale shifts
  // the exponent and touches no mantissa bit — which is what makes the comparison bitwise.
  const B = 8
  const scaledQ = new Float32Array(N)
  for (let i = 0; i < N; i++) scaledQ[i] = B * discharge[i]
  const opts = { widthCoefficient: KW, depthCoefficient: KD, cellSizeM: CELL }
  const viaFactor = M.riverFields(yValley(), discharge, W, H, { ...opts, bankfullFactor: B })
  const viaField = M.riverFields(yValley(), scaledQ, W, H, { ...opts, bankfullFactor: 1 })
  let bankfullMismatch = 0
  for (let i = 0; i < N; i++) {
    if (viaFactor.channelWidth[i] !== viaField.channelWidth[i]) bankfullMismatch++
    if (viaFactor.waterDepth[i] !== viaField.waterDepth[i]) bankfullMismatch++
    if (viaFactor.channelMask[i] !== viaField.channelMask[i]) bankfullMismatch++
  }
  check('the bankfull factor scales discharge exactly',
    bankfullMismatch === 0 && viaFactor.channelCells === viaField.channelCells,
    { bankfullMismatch, viaFactorCells: viaFactor.channelCells, viaFieldCells: viaField.channelCells })
  // ...and it must MOVE something. Two empty fields satisfy the identity above perfectly. Measured
  // endpoints: 107 cells at factor 1, 2223 at factor 8 — a ratio of 20.8 — against 1.0 with the
  // factor ignored, so the bound sits between two measured builds and is nowhere near either.
  check('the bankfull factor changes the channel it produces',
    viaFactor.channelCells > r.channelCells * 1.5,
    { atFactor1: r.channelCells, atFactor8: viaFactor.channelCells,
      ratio: +(viaFactor.channelCells / r.channelCells).toFixed(4) })

  // --- the declared port block ------------------------------------------------------------------
  // The plugin cannot be imported here (it pulls in legacy.js, which needs a DOM), so the port block
  // lives in the pure module and is checked as data. This is the declarative half of guardrail 1:
  // a node that OFFERS a carved terrain output has already lost the argument.
  const outs = M.RIVER_PORTS.outputs, insP = M.RIVER_PORTS.inputs
  const TERRAIN_SEMANTICS = ['height', 'relativeHeight', 'solidTop', 'bedrockHeight']
  const terrainOuts = outs.filter(p => TERRAIN_SEMANTICS.includes(p.semantic))
  check('exactly one solid-terrain output, and it is the primary pass-through',
    terrainOuts.length === 1 && terrainOuts[0].id === 'solidTop' && terrainOuts[0].primary === true,
    { terrainOuts: terrainOuts.map(p => p.id) })
  check('the node emits width, water depth, surface and a channel mask',
    ['channelMask', 'channelWidth', 'waterDepth', 'waterSurface'].every(id => outs.some(p => p.id === id)),
    { outputs: outs.map(p => p.id) })
  check('the bed input is in metres, not the normalised legacy field',
    insP.some(p => p.id === 'solidTop' && p.unit === 'm')
    && insP.some(p => p.id === 'discharge' && p.unit === 'm3PerS'),
    { inputs: insP.map(p => `${p.id}:${p.unit}`) })

  // Every declared semantic must be accounted for: already in ports.js, or on the pending list this
  // module publishes as its wiring precondition. A request that quietly vanished would leave the
  // plugin unregisterable with nothing saying why.
  const pending = M.PENDING_PORT_SEMANTICS
  const unaccounted = [...outs, ...insP].map(p => p.semantic)
    .filter(s => !PORTS.SEMANTICS[s] && !pending[s])
  check('every declared semantic is either in ports.js or on the pending list',
    unaccounted.length === 0, { unaccounted, pending: Object.keys(pending) })
  // ...and where a pending entry HAS landed in ports.js, the two must agree. This is the check that
  // survives the merge: it is inert today and becomes the real gate the moment ports.js gains them.
  const disagreements = Object.entries(pending)
    .filter(([name, want]) => PORTS.SEMANTICS[name]
      && (PORTS.SEMANTICS[name].kind !== want.kind || PORTS.SEMANTICS[name].defaultUnit !== want.defaultUnit))
    .map(([name]) => name)
  const landed = Object.keys(pending).filter(n => !!PORTS.SEMANTICS[n])
  check('any pending semantic already landed in ports.js agrees with this declaration',
    disagreements.length === 0, { disagreements, landed })
  // Full port validation, minus exactly the semantics that are still pending. Filtering by name
  // rather than skipping validation keeps id, kind, storage, components and primary-count checked.
  const problems = PORTS.validatePortList({ inputs: insP.slice(), outputs: outs.slice(), source: 'declared' })
  const unexpected = problems.filter(p => !(p.code === 'PORT_SEMANTIC_UNKNOWN' && pending[p.detail && p.detail.semantic]))
  check('the port block is valid apart from the pending semantics', unexpected.length === 0,
    { unexpected: unexpected.map(p => `${p.code} ${p.message}`), pendingReported: problems.length - unexpected.length })

  // --- the module's own stated refusals, which nothing was checking ------------------------------
  //
  // Both of these are written in rivers.js as deliberate guards with comments explaining why they
  // exist, and the Sprint 4 audit found neither had an assertion. A guard nobody tests is a comment.
  //
  // NaN DISCHARGE. The threshold is written `!(qb >= t)` rather than `qb < t` specifically so a NaN
  // falls out of the channel instead of propagating: NaN fails both comparisons, so the negated form
  // skips the cell while the plain form would enter it and produce NaN width, depth and mask. The
  // audit injected exactly that and it passed — measured, the mutated guard channelises every cell
  // and puts NaN on three output ports.
  {
    const bed = flatBed()
    const qNaN = new Float32Array(N)
    for (let i = 0; i < N; i++) qNaN[i] = Number.NaN
    // A few real cells alongside, so this is not "everything is NaN so nothing happens".
    for (let x = 10; x < 20; x++) qNaN[32 * W + x] = 500
    const rn = M.riverFields(bed, qNaN, W, H, { widthCoefficient: KW, depthCoefficient: KD, cellSizeM: CELL })
    const finite = arr => { for (let i = 0; i < arr.length; i++) if (!Number.isFinite(arr[i])) return false; return true }
    check('a NaN discharge produces no NaN on any output port',
      finite(rn.channelWidth) && finite(rn.waterDepth) && finite(rn.channelMask) && finite(rn.waterSurface),
      { width: finite(rn.channelWidth), depth: finite(rn.waterDepth),
        mask: finite(rn.channelMask), surface: finite(rn.waterSurface) })
    // ABSENCE OF EVIDENCE: if the ten real cells produced no channel either, "no NaN" would be
    // satisfied by a function that did nothing at all.
    let channelled = 0
    for (let i = 0; i < N; i++) if (rn.channelMask[i] > 0) channelled++
    check('the finite cells alongside the NaNs still form a channel', channelled > 0 && channelled < N / 4,
      { channelled, N })
  }

  // LATTICE MISMATCH. Fields wired from two different lattices arrive as arrays of different
  // lengths. Sizing the output to whichever is shorter would draw a plausible river over the wrong
  // ground, so rivers.js throws. Nothing asserted that it throws.
  {
    let threw = false, msg = ''
    try {
      M.riverFields(flatBed(), new Float32Array(N - W), W, H,
        { widthCoefficient: KW, depthCoefficient: KD, cellSizeM: CELL })
    } catch (e) { threw = true; msg = String(e.message || e) }
    check('a lattice-mismatched discharge field is refused, not silently truncated',
      threw && /expected/.test(msg), { threw, msg: msg.slice(0, 90) })
    let threwBed = false
    try {
      M.riverFields(new Float32Array(N - 1), new Float32Array(N), W, H,
        { widthCoefficient: KW, depthCoefficient: KD, cellSizeM: CELL })
    } catch (e) { threwBed = true }
    check('a lattice-mismatched BED is refused too, not only the discharge', threwBed, { threwBed })
  }

  check('assertion inventory non-empty', assertions.length >= 32, assertions.length)
  report()

  function report() {
    let ok = assertions.every(a => a.ok)
    if (mutation) {
      if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
      ok = false
    }
    const failed = assertions.filter(a => !a.ok).map(a => a.name)
    console.log(`${ok ? 'PASS' : 'FAIL'}  rivers assertions=${assertions.length} `
      + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
    // Verbose prints EVERY row, not just the failures: the readings on the passing rows are the
    // record of what was measured, and a gate whose numbers are never shown is a gate nobody checked.
    if (process.env.MC_VERBOSE) console.log(JSON.stringify(assertions, null, 2))
    else if (!ok) console.log(JSON.stringify(assertions.filter(a => !a.ok), null, 2))
    process.exit(ok ? 0 : 1)
  }
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
