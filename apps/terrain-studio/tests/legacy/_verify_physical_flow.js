// S4.1 + S4.2 — physical flow routing and the depression policy it runs over.
//
// The shipped `d_flow` node returns normalize(log1p(accumulation)): a picture. You cannot ask it how
// many square metres drain to a point. These are the typed physical products, and this oracle checks
// them as PHYSICS — against analytic surfaces whose answers are known in closed form, in double
// precision, with no browser.
//
// The plan names two mutations explicitly ("mutations omitting either conversion factor must fail"),
// and they are the reason the unit conversions are spelled out rather than folded into one constant:
// dropping 1e-3 is wrong by a thousand, dropping seconds-per-year by thirty million, and both look
// like tuning problems rather than unit problems when you only ever see a normalised picture.
const path = require('path')
const fs = require('fs')
const { pathToFileURL } = require('url')

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'no-mm-conversion',      // drop 1e-3: discharge wrong by 1000x
  'no-seconds-conversion', // drop /31536000: discharge wrong by 3.15e7
  'drop-by-elevation',     // weight receivers by drop instead of slope: diagonals win for being further
  'single-receiver',       // all water to the steepest neighbour: divergence becomes impossible
  'fill-writes-solid',     // the depression policy returns the conditioned surface as solid height
  'breach-is-fill',        // breach mapped onto priority fill -- the failure the plan names
  'fill-to-fixed-level',   // fill to a constant instead of the spill: the old count-based check passed this
  'direction-not-normalized', // dirX/dirZ keep the raw weighted sum: the declared unit vector is not one
  'sink-keeps-direction',  // a cell with nowhere to send water still reports a heading
]
const PATCHES = {
  'no-mm-conversion': [['out[i] = (mmYr * 1e-3) * cellAreaM2Value / SECONDS_PER_YEAR',
                        'out[i] = mmYr * cellAreaM2Value / SECONDS_PER_YEAR']],
  'no-seconds-conversion': [['out[i] = (mmYr * 1e-3) * cellAreaM2Value / SECONDS_PER_YEAR',
                             'out[i] = (mmYr * 1e-3) * cellAreaM2Value']],
  'drop-by-elevation': [['const ww = Math.pow(slope, exponent)', 'const ww = Math.pow(drop, exponent)']],
  'single-receiver': [['for (let k = 0; k < nbCount; k++) wgt[base + k] /= total',
                       'let bk = -1, bv = -1; for (let k = 0; k < nbCount; k++) { if (wgt[base + k] > bv) { bv = wgt[base + k]; bk = k } }\n' +
                       '      for (let k = 0; k < nbCount; k++) wgt[base + k] = (k === bk ? 1 : 0)']],
  'fill-writes-solid': [['return { routingSurface: filled, depressionDepth: depth, conditioningDelta: delta }',
                         'for (let i = 0; i < N; i++) h[i] = filled[i]\n    return { routingSurface: filled, depressionDepth: depth, conditioningDelta: delta }']],
  // NOT `rs[p] = ceiling`: ceiling is min'd with rs[p] on the line above, so that "mutation" is
  // bit-identical to the original and scored as armed while proving nothing.
  // The units/ranges clause had no assertion behind it, so neither of these could have been
  // detected: a direction that is not a unit vector, and a sink that claims a heading.
  'direction-not-normalized': [['      if (ml > 0) { dirX[i] = mx / ml; dirZ[i] = mz / ml }',
    '      if (ml > 0) { dirX[i] = mx; dirZ[i] = mz }']],
  'sink-keeps-direction': [['      if (total <= 0) { outlet[i] = 1; continue }',
    '      if (total <= 0) { outlet[i] = 1; dirX[i] = 1; dirZ[i] = 0; continue }']],
  // THE MUTATION THE OLD ASSERTION COULD NOT SEE. Filling to a fixed 0.62 still raises well over
  // 40 cells, so `fillRaised > 40` passed it happily. Only comparing the LEVEL to an
  // independently derived spill catches it.
  'fill-to-fixed-level': [['    for (let i = 0; i < N; i++) delta[i] = filled[i] - h[i]',
    '    for (let i = 0; i < N; i++) { filled[i] = Math.max(h[i], 0.62); delta[i] = filled[i] - h[i] }']],
  'breach-is-fill': [['  // BREACH. The basin floor stays put',
    "  if (mode === 'breach') { const d2 = new Float32Array(N); for (let i = 0; i < N; i++) d2[i] = filled[i] - h[i];"
    + " return { routingSurface: filled, depressionDepth: depth, conditioningDelta: d2 } }\n"
    + "  // BREACH. The basin floor stays put"]],
}
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

const W = 64, H = 64, N = W * H, CELL = 10   // 10 m cells, 640 m square domain

/** An inclined plane draining due +x. Steepest descent is exactly +x everywhere. */
function plane() {
  const h = new Float32Array(N)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) h[y * W + x] = 1 - x / W
  return h
}
/** A single closed pit in an otherwise sloping surface. Its spill is known by construction. */
function pitted() {
  const h = plane()
  for (let y = 28; y < 36; y++) for (let x = 28; x < 36; x++) h[y * W + x] -= 0.30
  return h
}

/**
 * TWO BASINS IN SERIES, which the story calls for and no fixture had.
 *
 * The single-pit fixture cannot distinguish a correct fill from one that raises everything to a
 * single global level, because there IS only one level in it. This one has two, and they must come
 * out different:
 *
 *   the UPPER pit sits on high ground (small x) and spills downslope into the lower one
 *   the LOWER pit is deeper and further downslope, and spills to the domain edge
 *
 * A fill that solves each basin against its own rim produces two distinct levels. A fill that solves
 * one level for the whole domain — the failure mode the story names — produces one. The gap between
 * them is the assertion.
 *
 * The upper pit is deliberately shallow enough that the lower basin's fill NEVER reaches it: if the
 * lower level rose above the upper rim the two would merge into one body and the fixture would
 * quietly stop testing nesting at all.
 */
function nested() {
  const h = plane()
  for (let y = 26; y < 32; y++) for (let x = 12; x < 18; x++) h[y * W + x] -= 0.10   // upper, shallow
  for (let y = 30; y < 40; y++) for (let x = 40; x < 50; x++) h[y * W + x] -= 0.35   // lower, deep
  return h
}

;(async () => {
  const src = path.resolve(__dirname, '../../src/core/hydrology.js')
  let M = null, loadErr = null
  try {
    if (!mutation) { M = await import(pathToFileURL(src).href) }
    else {
      let text = fs.readFileSync(src, 'utf8')
      for (const [anchor, repl] of PATCHES[mutation]) {
        const hits = text.split(anchor).length - 1
        if (hits !== 1) { console.error(`FATAL anchor for ${mutation} matched ${hits}, expected 1`); process.exit(2) }
        text = text.replace(anchor, repl)
      }
      M = await import('data:text/javascript;base64,' + Buffer.from(text, 'utf8').toString('base64'))
    }
  } catch (e) { loadErr = String(e.message || e).slice(0, 200) }

  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }
  if (!check('module loads', M !== null, loadErr)) return report()

  const area = M.cellAreaM2(CELL, false)
  check('square cell area is the square of the spacing', Math.abs(area - CELL * CELL) < 1e-9, area)
  // A hex row is sqrt(3)/2 of a column, so its cell is NOT s^2. Getting this wrong scales every
  // drainage area on the hex lattice by 15% — a bias small enough to look like a tuning constant.
  const hexArea = M.cellAreaM2(CELL, true)
  check('hex cell area carries the sqrt(3)/2 row pitch',
    Math.abs(hexArea - CELL * CELL * Math.sqrt(3) / 2) < 1e-9, hexArea)

  // --- direction on an analytic plane -----------------------------------------------------------
  const hp = plane()
  const wp = M.mfdWeights(hp, W, H, { cellSizeM: CELL })
  let worstAngle = 0
  for (let y = 8; y < H - 8; y++) for (let x = 8; x < W - 8; x++) {
    const i = y * W + x
    const ang = Math.abs(Math.atan2(wp.dirZ[i], wp.dirX[i]))
    if (ang > worstAngle) worstAngle = ang
  }
  // One lattice angular quantum on D8 is 45 degrees; the plan's bound. A correct router is far
  // inside it on a plane, but the bound is the one the plan states.
  check('flow direction on a plane matches steepest descent within one lattice quantum',
    worstAngle <= Math.PI / 4 + 1e-6, { worstAngleDeg: +(worstAngle * 180 / Math.PI).toFixed(4) })
  check('flow direction on a plane is essentially exact', worstAngle < 1e-3,
    { worstAngleDeg: +(worstAngle * 180 / Math.PI).toFixed(6) })

  // OFF-AXIS PLANE, at 22.5 degrees: exactly halfway between a lattice axis and a diagonal, which is
  // the direction of maximum ambiguity and therefore where a weighting error is largest. Weighting
  // receivers by DROP instead of SLOPE overweights the diagonal by its extra sqrt(2) of distance and
  // pulls the direction toward it. Measured, that is 0.000 degrees of error for slope-weighting and
  // 0.326 for drop-weighting; the bound below sits between two measured builds.
  //
  // The axis/diagonal accumulation balance does NOT distinguish them (0.9825 against 0.9808) because
  // MFD spreads to every downslope neighbour and the bias largely cancels in the totals. Direction is
  // where it survives, so direction is what this asserts.
  const tilt = 22.5 * Math.PI / 180, gx = Math.cos(tilt), gz = Math.sin(tilt)
  const ho = new Float32Array(N)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) ho[y * W + x] = 1 - (x * gx + y * gz) / W
  const wo = M.mfdWeights(ho, W, H, { cellSizeM: CELL })
  let sx = 0, sz = 0, cnt = 0
  for (let y = 8; y < H - 8; y++) for (let x = 8; x < W - 8; x++) {
    const i = y * W + x; sx += wo.dirX[i]; sz += wo.dirZ[i]; cnt++
  }
  const measuredDeg = Math.atan2(sz / cnt, sx / cnt) * 180 / Math.PI
  check('flow direction is unbiased on an off-axis plane',
    Math.abs(measuredDeg - 22.5) < 0.15, { trueDeg: 22.5, measuredDeg: +measuredDeg.toFixed(4) })

  // --- drainage area conserves ------------------------------------------------------------------
  const supply = new Float64Array(N).fill(area)
  const acc = M.mfdAccumulate(hp, supply, W, H, wp)
  // Every cell's area must arrive SOMEWHERE. Summing what leaves the domain is the mass-conservation
  // check the doctrine calls the most under-used assertion in terrain work: a router that loses
  // water silently still produces a plausible-looking river network.
  let exported = 0
  for (let y = 0; y < H; y++) exported += acc[y * W + (W - 1)]
  const domain = N * area
  check('drainage area at the outlets equals the domain area within one cell',
    Math.abs(exported - domain) <= area, { exported, domain, diff: exported - domain })

  // --- discharge units --------------------------------------------------------------------------
  const zero = M.mfdAccumulate(hp, M.precipToSupply(0, area, N), W, H, wp)
  let zmax = 0
  for (let i = 0; i < N; i++) zmax = Math.max(zmax, zero[i])
  check('zero precipitation gives exactly zero discharge', zmax === 0, { zmax })

  const P = 1000   // mm/yr
  const q = M.mfdAccumulate(hp, M.precipToSupply(P, area, N), W, H, wp)
  let qOut = 0
  for (let y = 0; y < H; y++) qOut += q[y * W + (W - 1)]
  // The plan's formula, written out: mm/yr -> m/yr -> m3/yr -> m3/s.
  const expected = P * 1e-3 * domain / M.SECONDS_PER_YEAR
  check('uniform precipitation integrates to the plan formula',
    Math.abs(qOut - expected) <= expected * 1e-6 + 1e-12,
    { qOut, expected, relErr: Math.abs(qOut - expected) / expected })
  check('seconds per year is the plan figure', M.SECONDS_PER_YEAR === 31536000, M.SECONDS_PER_YEAR)

  // --- MFD must actually spread on divergent ground ---------------------------------------------
  // A cone drains radially: every azimuth carries equal area. A single-receiver router cannot do
  // this and instead produces spokes — the failure this codebase already found once in its D8 path.
  const cone = new Float32Array(N)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    cone[y * W + x] = 1 - Math.hypot(x - W / 2, y - H / 2) / (W / 2)
  }
  const wc = M.mfdWeights(cone, W, H, { cellSizeM: CELL })
  let multi = 0, any = 0
  for (let i = 0; i < N; i++) {
    let nz = 0
    for (let k = 0; k < wc.nbCount; k++) if (wc.wgt[i * wc.nbCount + k] > 1e-6) nz++
    if (nz > 0) any++
    if (nz > 1) multi++
  }
  check('cells were routed at all', any > N * 0.5, { any, N })
  check('flow diverges on a cone rather than forming single threads',
    multi > any * 0.5, { multiReceiverCells: multi, routedCells: any })

  // --- axis/diagonal balance --------------------------------------------------------------------
  // Radial drainage must carry equal area along every azimuth. Weighting by DROP instead of SLOPE
  // makes the diagonal win everywhere simply for being sqrt(2) further away.
  const accCone = M.mfdAccumulate(cone, new Float64Array(N).fill(area), W, H, wc)
  const cx = W / 2 | 0, cy = H / 2 | 0, r = 24
  const axis = (accCone[cy * W + (cx + r)] + accCone[cy * W + (cx - r)]
    + accCone[(cy + r) * W + cx] + accCone[(cy - r) * W + cx]) / 4
  const dg = Math.round(r / Math.SQRT2)
  const diag = (accCone[(cy + dg) * W + (cx + dg)] + accCone[(cy - dg) * W + (cx - dg)]
    + accCone[(cy + dg) * W + (cx - dg)] + accCone[(cy - dg) * W + (cx + dg)]) / 4
  const ratio = axis > 0 && diag > 0 ? Math.min(axis, diag) / Math.max(axis, diag) : 0
  check('radial drainage is balanced between axes and diagonals', ratio > 0.55,
    { axis: +axis.toFixed(1), diag: +diag.toFixed(1), ratio: +ratio.toFixed(3) })

  // --- S4.1 depression policy -------------------------------------------------------------------
  const hpit = pitted()
  const solidBefore = Float32Array.from(hpit)
  const fill = M.depressionPolicy(hpit, W, H, { mode: 'fill', cellSizeM: CELL })
  const breach = M.depressionPolicy(hpit, W, H, { mode: 'breach', cellSizeM: CELL })
  const preserve = M.depressionPolicy(hpit, W, H, { mode: 'preserve', cellSizeM: CELL })

  // THE CONTRACT THAT MATTERS: no mode may touch the solid height. Conditioning is a derived
  // routing surface, not terrain — writing it back is the armed failure the plan names.
  let solidChanged = 0
  for (let i = 0; i < N; i++) if (hpit[i] !== solidBefore[i]) solidChanged++
  check('no policy mode alters the solid height', solidChanged === 0, { solidChanged })

  check('preserve leaves the routing surface bit-identical to the input',
    preserve.routingSurface.every((v, i) => v === solidBefore[i]), null)

  // Fill must RAISE the basin; breach must NOT.
  let fillRaised = 0, breachRaised = 0, breachLowered = 0
  for (let i = 0; i < N; i++) {
    if (fill.routingSurface[i] > solidBefore[i] + 1e-6) fillRaised++
    if (breach.routingSurface[i] > solidBefore[i] + 1e-6) breachRaised++
    if (breach.routingSurface[i] < solidBefore[i] - 1e-9) breachLowered++
  }
  check('fill raises the basin to its spill', fillRaised > 40, { fillRaised })

  // THE LEVEL, NOT THE COUNT. The line above asserts that more than 40 cells got raised, which a
  // fill to ANY level satisfies — a fill to a fixed 0.9, or to the domain maximum, passes it just as
  // happily as a fill to the spill. The story's clause is "Fill raises each basin EXACTLY to its
  // lowest spill", and that number was never compared to anything. The Sprint 4 audit found it.
  //
  // The spill is derived here INDEPENDENTLY of the module under test: walk the ring of cells that
  // border the pit and take the lowest of them. That is what "lowest spill" means, computed from
  // the original terrain rather than read back out of the thing being checked.
  const PIT = { x0: 28, x1: 36, y0: 28, y1: 36 }
  let independentSpill = Infinity
  for (let y = PIT.y0 - 1; y <= PIT.y1; y++) {
    for (let x = PIT.x0 - 1; x <= PIT.x1; x++) {
      const inside = x >= PIT.x0 && x < PIT.x1 && y >= PIT.y0 && y < PIT.y1
      const onRing = !inside && x >= PIT.x0 - 1 && x <= PIT.x1 && y >= PIT.y0 - 1 && y <= PIT.y1
      if (onRing) independentSpill = Math.min(independentSpill, solidBefore[y * W + x])
    }
  }
  // Every raised cell must sit at that one level. A fill that stopped short leaves cells below it;
  // one that overshot puts them above. Both are caught by the same comparison.
  let lo = Infinity, hi = -Infinity, raisedCells = 0
  for (let y = PIT.y0; y < PIT.y1; y++) for (let x = PIT.x0; x < PIT.x1; x++) {
    const i = y * W + x
    if (fill.routingSurface[i] > solidBefore[i] + 1e-6) {
      raisedCells++
      lo = Math.min(lo, fill.routingSurface[i]); hi = Math.max(hi, fill.routingSurface[i])
    }
  }
  check('the fixture basin actually filled', raisedCells > 20, { raisedCells })
  // The flat epsilon tilts a filled surface by 2e-7 per flood step so routing can cross it, so the
  // level is flat to that scale rather than bitwise. 1e-4 is far below the 0.30 pit depth and far
  // above the epsilon.
  check('the filled surface is one level across the basin', hi - lo < 1e-4,
    { lo: +lo.toFixed(6), hi: +hi.toFixed(6), spread: +(hi - lo).toExponential(2) })
  check('that level IS the independently derived lowest spill',
    Math.abs(lo - independentSpill) < 1e-3,
    { fillLevel: +lo.toFixed(6), independentSpill: +independentSpill.toFixed(6),
      diff: +Math.abs(lo - independentSpill).toExponential(2) })
  check('breach raises nothing', breachRaised === 0, { breachRaised })
  check('breach cuts an outlet path', breachLowered > 0, { breachLowered })

  // The three modes must give DIFFERENT routing topology, or the policy is a label.
  //
  // Counting outlet CELLS was the first metric here and it was too coarse to be a topology check:
  // breach and preserve both reported 72, because cutting a path out of a basin does not change how
  // many cells have nowhere lower to send water. What actually distinguishes the modes is WHERE THE
  // WATER ENDS UP — an endorheic basin traps its catchment, a filled or breached one does not.
  // Measured as what is TRAPPED, not what is exported. Summing the four domain edges was the first
  // attempt and it reported 1.67 of the domain area leaving: water that enters on one edge and
  // leaves by another gets counted at both. Trapping has no such ambiguity — an INTERIOR cell with
  // nowhere lower to send water is a pit, and whatever accumulates there never left.
  const trappedFraction = rs => {
    const wgt = M.mfdWeights(rs, W, H, { cellSizeM: CELL })
    const a = M.mfdAccumulate(rs, new Float64Array(N).fill(area), W, H, wgt)
    let trapped = 0
    for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
      const i = y * W + x
      if (wgt.outlet[i]) trapped += a[i]
    }
    return trapped / (N * area)
  }
  const ef = trappedFraction(fill.routingSurface)
  const eb = trappedFraction(breach.routingSurface)
  const ep = trappedFraction(preserve.routingSurface)
  check('preserve keeps the basin endorheic, trapping its catchment', ep > 0.01,
    { preserveTrapped: +ep.toFixed(4) })
  check('fill leaves nothing trapped', ef < 0.001, { fillTrapped: +ef.toFixed(6) })
  check('breach leaves nothing trapped', eb < 0.001, { breachTrapped: +eb.toFixed(6) })
  // ...and the surfaces themselves must be three different fields, not two aliases and a label.
  const differs = (a, b) => { for (let i = 0; i < N; i++) if (a[i] !== b[i]) return true; return false }
  check('the three routing surfaces are pairwise distinct',
    differs(fill.routingSurface, breach.routingSurface)
    && differs(breach.routingSurface, preserve.routingSurface)
    && differs(fill.routingSurface, preserve.routingSurface), null)

  // --- S4.1: the analytic NESTED-basin fixture the story asks for ---------------------------------
  //
  // The single-pit fixture cannot tell a per-basin fill from a fill-everything-to-one-level, because
  // it contains exactly one level. Two basins in series do: each must reach ITS OWN spill.
  {
    const hn = nested()
    const solidN = Float32Array.from(hn)
    const fn = M.depressionPolicy(hn, W, H, { mode: 'fill', cellSizeM: CELL })
    const levelIn = (x0, x1, y0, y1) => {
      let lo = Infinity, hi = -Infinity, n = 0
      for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
        const i = y * W + x
        if (fn.routingSurface[i] > solidN[i] + 1e-6) { n++; lo = Math.min(lo, fn.routingSurface[i]); hi = Math.max(hi, fn.routingSurface[i]) }
      }
      return { lo, hi, n }
    }
    const up = levelIn(12, 18, 26, 32), lowr = levelIn(40, 50, 30, 40)
    check('both nested basins filled', up.n > 8 && lowr.n > 20, { upperCells: up.n, lowerCells: lowr.n })
    check('each nested basin is flat within itself',
      up.hi - up.lo < 1e-4 && lowr.hi - lowr.lo < 1e-4,
      { upperSpread: +(up.hi - up.lo).toExponential(2), lowerSpread: +(lowr.hi - lowr.lo).toExponential(2) })
    // THE ASSERTION THE SINGLE-PIT FIXTURE COULD NOT MAKE. One global level gives a difference of
    // zero. The upper basin sits upslope on a plane falling in +x, so its level must be HIGHER.
    check('the two basins reach DIFFERENT levels, each its own spill',
      up.lo - lowr.lo > 0.05,
      { upperLevel: +up.lo.toFixed(5), lowerLevel: +lowr.lo.toFixed(5), gap: +(up.lo - lowr.lo).toFixed(5) })
    // ...and they must stay separate. If the lower fill rose above the upper basin's floor the two
    // would merge and this fixture would silently stop testing nesting.
    let upperFloor = Infinity
    for (let y = 26; y < 32; y++) for (let x = 12; x < 18; x++) upperFloor = Math.min(upperFloor, solidN[y * W + x])
    check('the lower fill never reaches the upper basin, so they remain two bodies',
      lowr.hi < upperFloor, { lowerLevel: +lowr.hi.toFixed(5), upperFloor: +upperFloor.toFixed(5) })
    // Solid height untouched here too — the guardrail applies to every fixture, not just the first.
    let changed = 0
    for (let i = 0; i < N; i++) if (hn[i] !== solidN[i]) changed++
    check('the nested fixture solid height is untouched', changed === 0, { changed })
  }

  // --- S4.2: "assert all output units/ranges" -----------------------------------------------------
  //
  // The Sprint 4 audit found this clause had NO assertion behind it at all. Every physical claim was
  // about the routing maths; nothing checked that the numbers leaving the ports were in their
  // declared units or inside possible bounds. A drainage area in CELLS rather than m2, or a
  // direction that is not a unit vector, would have passed everything above.
  //
  // Bounds are derived, not chosen: the smallest possible catchment is one cell's own area, the
  // largest is the whole domain, and both come from the fixture rather than from a constant.
  {
    const accU = M.mfdAccumulate(hp, new Float64Array(N).fill(area), W, H, wp)
    let minA = Infinity, maxA = -Infinity
    for (let i = 0; i < N; i++) { minA = Math.min(minA, accU[i]); maxA = Math.max(maxA, accU[i]) }
    check('drainage area is in m2, never below one cell nor above the domain',
      minA >= area - 1e-6 && maxA <= N * area + area,
      { minM2: +minA.toFixed(3), oneCellM2: area, maxM2: +maxA.toFixed(1), domainM2: N * area })
    // A ridge cell drains only itself. If the minimum were much larger, the units are not m2 --
    // in CELLS the minimum would be exactly 1, which this catches for any cell size but 1 m.
    check('the driest cell drains exactly its own area', Math.abs(minA - area) < 1e-6,
      { minM2: +minA.toFixed(6), expected: area })

    const qU = M.mfdAccumulate(hp, M.precipToSupply(1000, area, N), W, H, wp)
    let minQ = Infinity, maxQ = -Infinity
    for (let i = 0; i < N; i++) { minQ = Math.min(minQ, qU[i]); maxQ = Math.max(maxQ, qU[i]) }
    // Discharge cannot be negative, and the whole domain's rain is its ceiling.
    const domainQ = 1000 * 1e-3 * (N * area) / M.SECONDS_PER_YEAR
    check('discharge is non-negative and bounded by the domain rainfall',
      minQ >= 0 && maxQ <= domainQ * (1 + 1e-6),
      { minQ: +minQ.toExponential(3), maxQ: +maxQ.toExponential(3), domainQ: +domainQ.toExponential(3) })

    // flowDirection is declared a unit vector. Every routed cell must carry length 1; every sink
    // must carry exactly zero -- a sink with a direction is a cell claiming to send water somewhere
    // it does not send it.
    let badLen = 0, sinkNonZero = 0, routed = 0
    for (let i = 0; i < N; i++) {
      const L = Math.hypot(wp.dirX[i], wp.dirZ[i])
      if (wp.outlet[i]) { if (L > 1e-6) sinkNonZero++ } else { routed++; if (Math.abs(L - 1) > 1e-5) badLen++ }
    }
    check('routed cells exist to check', routed > N * 0.5, { routed, N })
    check('flow direction is a unit vector wherever water is routed', badLen === 0, { badLen, routed })
    check('sinks carry exactly zero direction, not a stale one', sinkNonZero === 0, { sinkNonZero })
  }

  check('assertion inventory non-empty', assertions.length >= 30, assertions.length)
  report()

  function report() {
    let ok = assertions.every(a => a.ok)
    if (mutation) {
      if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
      ok = false
    }
    const failed = assertions.filter(a => !a.ok).map(a => a.name)
    console.log(`${ok ? 'PASS' : 'FAIL'}  physical flow assertions=${assertions.length} `
      + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
    if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify(assertions.filter(a => !a.ok), null, 2))
    process.exit(ok ? 0 : 1)
  }
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
