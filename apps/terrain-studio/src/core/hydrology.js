// Physical flow routing — S4.2, and the depression policy S4.1 routes over.
//
// Pure and DOM-free, like water-waves.js: it never imports legacy.js, so an oracle can evaluate it
// under plain node and check the physics in double precision with no browser involved.
//
// WHY THIS EXISTS. The shipped `d_flow` node returns `normalize(log1p(accumulation))` — a picture.
// It is genuinely useful for seeing where rivers go and useless for anything that needs a quantity:
// you cannot ask it how many square metres drain to a point, or how many cubic metres per second
// pass through one. ADR/S4.2 requires typed physical products, and the plan is explicit that
// `d_flow` stays as the log-compressed VISUALISATION and must not be relabelled as physical.
//
// SINGLE-RECEIVER ROUTING CANNOT EXPRESS DIVERGENCE. D8/D6 sends all of a cell's water to one
// neighbour, so on a hillslope or an alluvial fan — where water demonstrably spreads — it produces
// parallel one-cell threads and a drainage area that jumps by a factor of two across a ridge that
// is not there. Multiple-flow-direction weights each downslope neighbour by its slope, which is
// what lets area spread on divergent ground and still converge in valleys.

/** Slope exponent for MFD weighting. 1.1 is the standard Freeman value: >1 biases toward the
 *  steepest neighbour (convergent, river-like), =0 would spread water equally regardless of slope. */
export const MFD_EXPONENT = 1.1
export const SECONDS_PER_YEAR = 31536000   // the plan's exact figure, not 365.25 days

/** Square D8 offsets with their true centre-to-centre distances in cell units. */
const NB_SQUARE = [
  [-1, 0, 1], [1, 0, 1], [0, -1, 1], [0, 1, 1],
  [-1, -1, Math.SQRT2], [1, 1, Math.SQRT2], [-1, 1, Math.SQRT2], [1, -1, Math.SQRT2],
]
/** Hex D6 one-ring. Six equidistant neighbours, so there is no diagonal case to get wrong. */
const HEX_ROW = Math.sqrt(3) / 2
function hexNeighbours(y) {
  const odd = y & 1 ? 1 : 0
  return [
    [-1, 0, 1], [1, 0, 1],
    [odd - 1, -1, 1], [odd, -1, 1],
    [odd - 1, 1, 1], [odd, 1, 1],
  ]
}

/**
 * Per-cell downslope weights and the resulting flow direction.
 *
 * Returns flat arrays rather than objects per cell: at 4K a per-cell object array is 16M allocations
 * and the GC cost dominates the routing itself.
 *
 * `dirX`/`dirZ` are the NORMALISED FIRST MOMENT of the receiver weights — the weighted mean of the
 * unit vectors toward each receiver. On a plane that is steepest descent; on divergent ground it is
 * the actual mean direction of travel, which a single-receiver scheme cannot represent at all.
 * Lengths are in METRES throughout; the caller supplies cell size.
 */
export function mfdWeights(h, w, hgt, { hex = false, exponent = MFD_EXPONENT, cellSizeM = 1 } = {}) {
  const N = w * hgt
  const nbCount = hex ? 6 : 8
  const wgt = new Float32Array(N * nbCount)
  const rcv = new Int32Array(N * nbCount).fill(-1)
  const dirX = new Float32Array(N)
  const dirZ = new Float32Array(N)
  const outlet = new Uint8Array(N)          // cells with nowhere lower to send water

  for (let y = 0; y < hgt; y++) {
    const nb = hex ? hexNeighbours(y) : NB_SQUARE
    for (let x = 0; x < w; x++) {
      const i = y * w + x
      const base = i * nbCount
      let total = 0, mx = 0, mz = 0
      for (let k = 0; k < nb.length; k++) {
        const xx = x + nb[k][0], yy = y + nb[k][1]
        if (xx < 0 || yy < 0 || xx >= w || yy >= hgt) continue
        const ni = yy * w + xx
        // SLOPE, NOT DROP. Dividing by the true centre-to-centre distance is what stops the
        // diagonal from winning simply for being further away — the defect this codebase already
        // found once in its D8 router, where a cone drained down four diagonal spokes and the
        // axial directions were never chosen at all.
        const drop = h[i] - h[ni]
        if (drop <= 0) continue
        const dist = nb[k][2] * cellSizeM
        const slope = drop / dist
        const ww = Math.pow(slope, exponent)
        rcv[base + k] = ni
        wgt[base + k] = ww
        total += ww
        // Unit vector toward this receiver, in lattice space scaled to world.
        const len = Math.hypot(nb[k][0], nb[k][1] * (hex ? HEX_ROW : 1)) || 1
        mx += ww * (nb[k][0] / len)
        mz += ww * ((nb[k][1] * (hex ? HEX_ROW : 1)) / len)
      }
      if (total <= 0) { outlet[i] = 1; continue }
      for (let k = 0; k < nbCount; k++) wgt[base + k] /= total
      const ml = Math.hypot(mx, mz)
      if (ml > 0) { dirX[i] = mx / ml; dirZ[i] = mz / ml }
    }
  }
  return { wgt, rcv, dirX, dirZ, outlet, nbCount }
}

/**
 * Push `supply` downslope through the MFD weights and return the accumulated total per cell.
 *
 * Processed in descending height order so every cell's inflow is complete before it is drained —
 * that is what makes one pass exact rather than an iterative approximation. Sorting indices by
 * height is O(N log N) and is the whole algorithm; there is no convergence criterion to get wrong.
 *
 * `supply[i]` is whatever each cell contributes locally, in the caller's units. Pass cell AREA to
 * get drainage area; pass volume per second to get discharge. The routing does not know or care,
 * which is exactly why it must not invent rain internally.
 */
export function mfdAccumulate(h, supply, w, hgt, weights) {
  const N = w * hgt
  const { wgt, rcv, nbCount } = weights
  const acc = new Float64Array(N)
  for (let i = 0; i < N; i++) acc[i] = supply[i]
  const order = new Int32Array(N)
  for (let i = 0; i < N; i++) order[i] = i
  // Descending height: water only ever moves to a strictly lower cell, so a cell can be drained
  // once everything above it has been.
  const idx = Array.prototype.slice.call(order)
  idx.sort((a, b) => h[b] - h[a])
  for (let s = 0; s < N; s++) {
    const i = idx[s]
    const a = acc[i]
    if (a === 0) continue
    const base = i * nbCount
    for (let k = 0; k < nbCount; k++) {
      const ni = rcv[base + k]
      if (ni < 0) continue
      acc[ni] += a * wgt[base + k]
    }
  }
  return acc
}

/** Area of one lattice cell in m². A hex row is sqrt(3)/2 of a column, so its cell is not s². */
export function cellAreaM2(cellSizeM, hex) {
  return hex ? cellSizeM * cellSizeM * HEX_ROW : cellSizeM * cellSizeM
}

/**
 * Volume supply per cell in m³/s from a precipitation raster in mm/yr.
 *
 * BOTH CONVERSIONS ARE EXPLICIT because the plan arms a mutation against each: 1e-3 turns
 * millimetres into metres, and dividing by seconds-per-year turns a yearly depth into a rate. Drop
 * either and the number is wrong by a factor of a thousand or thirty million, which is the kind of
 * error that looks like a tuning problem rather than a units problem.
 */
export function precipToSupply(precipMmYr, cellAreaM2Value, N) {
  const out = new Float64Array(N)
  for (let i = 0; i < N; i++) {
    const mmYr = typeof precipMmYr === 'number' ? precipMmYr : precipMmYr[i]
    out[i] = (mmYr * 1e-3) * cellAreaM2Value / SECONDS_PER_YEAR
  }
  return out
}

/**
 * Fill closed depressions to their lowest spill point (S4.1 `fill`).
 *
 * Priority flood from the domain edge. `flatEpsilon` tilts filled flats by an invisible amount so
 * routing can cross a lake instead of terminating on it; pass 0 when the caller is an iterative
 * solver, where re-tilting every flat each pass measurably destroys the steady state.
 */
export function fillDepressions(h, w, hgt, { hex = false, flatEpsilon = 2e-7 } = {}) {
  const N = w * hgt
  const filled = new Float32Array(N)
  const done = new Uint8Array(N)
  const heap = []
  const push = (e, i) => {
    heap.push([e, i]); let c = heap.length - 1
    while (c > 0) { const p = (c - 1) >> 1; if (heap[p][0] <= heap[c][0]) break; const t = heap[p]; heap[p] = heap[c]; heap[c] = t; c = p }
  }
  const pop = () => {
    const top = heap[0], last = heap.pop()
    if (heap.length) {
      heap[0] = last; let c = 0
      for (;;) {
        const l = 2 * c + 1, r = l + 1; let s = c
        if (l < heap.length && heap[l][0] < heap[s][0]) s = l
        if (r < heap.length && heap[r][0] < heap[s][0]) s = r
        if (s === c) break
        const t = heap[s]; heap[s] = heap[c]; heap[c] = t; c = s
      }
    }
    return top
  }
  const seed = (x, y) => { const i = y * w + x; if (!done[i]) { done[i] = 1; filled[i] = h[i]; push(h[i], i) } }
  for (let x = 0; x < w; x++) { seed(x, 0); seed(x, hgt - 1) }
  for (let y = 0; y < hgt; y++) { seed(0, y); seed(w - 1, y) }
  while (heap.length) {
    const it = pop(), e = it[0], c = it[1]
    const cy = (c / w) | 0, cx = c - cy * w
    const nb = hex ? hexNeighbours(cy) : NB_SQUARE
    for (const dd of nb) {
      const xx = cx + dd[0], yy = cy + dd[1]
      if (xx < 0 || yy < 0 || xx >= w || yy >= hgt) continue
      const ni = yy * w + xx
      if (done[ni]) continue
      done[ni] = 1
      filled[ni] = flatEpsilon > 0 ? (h[ni] <= e ? e + flatEpsilon : h[ni]) : Math.max(h[ni], e)
      push(filled[ni], ni)
    }
  }
  return filled
}

/**
 * The S4.1 depression policy, as three named modes over one input.
 *
 * The contract that matters is that the SOLID HEIGHT IS NEVER TOUCHED. What varies is the
 * `routingSurface` — a derived field that exists so flow has somewhere consistent to run — and the
 * plan arms a mutation against exactly the failure of writing conditioning back into the terrain.
 *
 *   fill      raise each basin to its lowest spill
 *   breach    cut a monotone path from the basin's low point to its spill, leaving the basin floor
 *             where it is: the outlet is opened rather than the hollow drowned
 *   preserve  routing surface equals the input; closed basins stay closed and endorheic
 */
export function depressionPolicy(h, w, hgt, { mode = 'fill', hex = false, flatEpsilon = 2e-7 } = {}) {
  const N = w * hgt
  if (mode === 'preserve') {
    const rs = new Float32Array(h)
    return { routingSurface: rs, depressionDepth: new Float32Array(N), conditioningDelta: new Float32Array(N) }
  }
  const filled = fillDepressions(h, w, hgt, { hex, flatEpsilon })
  const depth = new Float32Array(N)
  for (let i = 0; i < N; i++) depth[i] = Math.max(0, filled[i] - h[i])

  if (mode === 'fill') {
    const delta = new Float32Array(N)
    for (let i = 0; i < N; i++) delta[i] = filled[i] - h[i]
    return { routingSurface: filled, depressionDepth: depth, conditioningDelta: delta }
  }

  // BREACH. The basin floor stays put; only a path out of it is lowered. Walking down the FILLED
  // surface from each depressed cell reaches that basin's spill point, because the fill made the
  // surface monotone to the outlet — so the path is found on the filled surface and applied to the
  // original one. Lowering along it is capped by the original height so a breach can only ever cut,
  // never raise, which is the property that distinguishes it from fill.
  const rs = new Float32Array(h)
  const nbFor = y => (hex ? hexNeighbours(y) : NB_SQUARE)
  const order = []
  for (let i = 0; i < N; i++) if (depth[i] > 0) order.push(i)
  order.sort((a, b) => h[a] - h[b])          // deepest points of each basin first
  for (const start of order) {
    if (rs[start] <= h[start] && depth[start] === 0) continue
    let cur = start, guard = 0
    const path = [cur]
    while (guard++ < N) {
      const cy = (cur / w) | 0, cx = cur - cy * w
      let best = -1, bestH = filled[cur]
      for (const dd of nbFor(cy)) {
        const xx = cx + dd[0], yy = cy + dd[1]
        if (xx < 0 || yy < 0 || xx >= w || yy >= hgt) continue
        const ni = yy * w + xx
        if (filled[ni] < bestH) { bestH = filled[ni]; best = ni }
      }
      if (best < 0) break                    // reached the spill: nothing lower on the filled surface
      path.push(best)
      // KEEP GOING UNTIL THE GROUND IS ALREADY LOWER THAN THE BASIN FLOOR. Stopping at the first
      // cell outside the depression cut a notch through the rim and made THAT cell the new pit: it
      // had been lowered below the basin floor while the cell beyond it was still at full height,
      // so the water reached the rim and stopped. Measured, that left 8 fresh interior pits exactly
      // one column downslope of the basin. The channel is only finished when it meets terrain that
      // can carry the water away without further cutting.
      if (h[best] < h[start]) break
      cur = best
      if (path.length > 4 * (w + hgt)) break // a channel longer than two domain crossings is a bug
    }
    // Cut monotonically along the path, never raising anything.
    let ceiling = Infinity
    for (const p of path) {
      ceiling = Math.min(ceiling, rs[p])
      rs[p] = Math.min(rs[p], ceiling)
      ceiling -= flatEpsilon
    }
  }
  const delta = new Float32Array(N)
  for (let i = 0; i < N; i++) delta[i] = rs[i] - h[i]
  return { routingSurface: rs, depressionDepth: depth, conditioningDelta: delta }
}
