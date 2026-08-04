// Lakes and basins — S4.4.
//
// Pure and DOM-free, like hydrology.js and water-waves.js: it never imports legacy.js, so the oracle
// evaluates it under plain node, in double precision, with no browser at all.
//
// WHY THIS IS A SEPARATE MODULE AND NOT MORE OF hydrology.js. The priority flood is the same flood,
// and this module CALLS it rather than copying it. What differs is the contract on the flats.
// `depressionPolicy` tilts every filled flat by 2e-7 so a router can cross a lake instead of
// terminating on it; that tilt is exactly what a lake may not have, because it puts a gradient across
// still water and destroys the one property that defines a lake surface. Two callers of one flood
// with opposite requirements on its flats want two names, not a boolean.
//
// THE LEVEL IS THE SPILL, NEVER A SLIDER. A lake filled to an authored level is a paint effect: it
// floods unrelated low ground somewhere else in the domain, it moves when the terrain's range moves,
// and its surface bears no relation to the rim that is actually holding the water back. The level
// here comes straight out of the flood — it is the elevation of the lowest point on the basin's rim —
// and the gate asserts the water surface is bit-identical to that cell's elevation.
//
// NO HEIGHT IS WRITTEN. Guardrail 1: `solidTop` goes in and comes back untouched. Water surface,
// depth, shore distance, basin id and the spill features are all separate products. Nothing in here
// conditions terrain, and the gate reads the input array bitwise before and after to prove it.
import { fillDepressions, NB_SQUARE, HEX_ROW, hexNeighbours, cellAreaM2 } from './hydrology.js'

/** Sentinel for "this cell is not in any lake". Matches ports.js NO_LABEL, which the basinId
 *  labelRaster port declares as its noLabel value. */
export const NO_LAKE = -1

/** The flood epsilon a LAKE must use. Named rather than inlined because it is the difference between
 *  a flat water surface and a 2e-7-per-cell ramp, and a bare `0` in an options object reads like a
 *  default that could be tuned. It cannot: flatness is the product. */
export const LAKE_FLAT_EPSILON = 0

/**
 * The water surface of every closed basin, filled to its spill.
 *
 * This is `filledDem` out of priority flood, which is flat per basin BY CONSTRUCTION rather than by a
 * flattening pass afterwards: the flood pops cells in ascending elevation, so the first cell that can
 * reach a basin's interior is its lowest rim cell, and every interior cell below that elevation is
 * assigned `max(h, e)` with the same `e`. The value stored is the rim cell's own Float32 elevation,
 * unmodified, which is why the surface is bit-identical across the water body and bit-identical to
 * the spill elevation rather than merely close to it.
 */
export function lakeSurface(solidTop, w, hgt, { hex = false } = {}) {
  return fillDepressions(solidTop, w, hgt, { hex, flatEpsilon: LAKE_FLAT_EPSILON })
}

// --- exact Euclidean distance transform -------------------------------------------------------
//
// Felzenszwalb & Huttenlocher's lower-envelope transform, generalised to arbitrary sample positions.
// The generalisation is not decoration: on the hex lattice odd rows are offset half a cell in x, so
// the textbook version — which assumes sources and queries both sit on integers — is wrong by up to
// half a cell everywhere. Splitting the sources by row parity gives two regular sub-lattices, each
// with a constant x offset, and the transform of each is exact; the answer is their minimum.
//
// A chamfer/3-4 approximation was the alternative and is rejected: the gate compares this against a
// brute-force nearest-source search and asserts the maximum error is EXACTLY zero, which no
// approximation can satisfy.

/** Stand-in for +Infinity inside the envelope arithmetic. Infinity would make the parabola
 *  intersection 0/0 = NaN and silently corrupt the envelope; a large finite value cannot, and
 *  1e30 is ~18 orders of magnitude above any squared distance a real domain can produce. */
const EDT_INF = 1e30

/**
 * out[p] = min over q of ( (qpos[p] - spos[q])^2 + f[q] )
 * `spos` and `qpos` must both be strictly increasing.
 */
function edt1d(f, spos, qpos, out) {
  const n = f.length, m = qpos.length
  const v = new Int32Array(n)      // indices of the parabolas currently on the lower envelope
  const z = new Float64Array(n + 1) // and the breakpoints between them
  let k = 0
  v[0] = 0; z[0] = -Infinity; z[1] = Infinity
  for (let q = 1; q < n; q++) {
    let s
    for (;;) {
      const p = v[k]
      s = ((f[q] + spos[q] * spos[q]) - (f[p] + spos[p] * spos[p])) / (2 * spos[q] - 2 * spos[p])
      if (s > z[k]) break
      k--                            // z[0] is -Infinity, so this always terminates at k = 0
    }
    k++; v[k] = q; z[k] = s; z[k + 1] = Infinity
  }
  k = 0
  for (let p = 0; p < m; p++) {
    const x = qpos[p]
    while (z[k + 1] < x) k++
    const q = v[k]
    out[p] = (x - spos[q]) * (x - spos[q]) + f[q]
  }
}

/** World position of a lattice cell, in metres. Odd hex rows are offset half a column, which is what
 *  makes `hexNeighbours` reach (x-1,y-1) and (x,y-1) from an even row. */
export function cellWorldX(x, y, hex, cellSizeM) {
  return x * cellSizeM + (hex && (y & 1) ? 0.5 * cellSizeM : 0)
}
export function cellWorldY(y, hex, cellSizeM) {
  return y * cellSizeM * (hex ? HEX_ROW : 1)
}

/** Squared distance in m² from every cell to the nearest cell where `isSource` is set. */
export function squaredDistanceToSet(isSource, w, hgt, { hex = false, cellSizeM = 1 } = {}) {
  const N = w * hgt
  const dy = cellSizeM * (hex ? HEX_ROW : 1)
  const best = new Float64Array(N).fill(EDT_INF)
  // One pass per source-row parity, each pass taking every SECOND row as its sources. On a square
  // lattice there is no stagger, so there is one pass and it takes every row — `rowStep` and not a
  // hard-coded 2 for that reason. Hard-coding it was the first version and it dropped every odd row
  // from the square transform: measured against brute force the worst cell was 60.8 m out on a 10 m
  // lattice, and every assertion that only checked sign or the shoreline zero still passed.
  const parities = hex ? [0, 1] : [0]
  const rowStep = hex ? 2 : 1
  const qposY = new Float64Array(hgt)
  for (let y = 0; y < hgt; y++) qposY[y] = y * dy
  const G = new Float64Array(N)
  const gcol = new Float64Array(hgt)
  const sposX = new Float64Array(w), qposX = new Float64Array(w)
  const row = new Float64Array(w), outRow = new Float64Array(w)

  for (const par of parities) {
    const srcRows = []
    for (let y = par; y < hgt; y += rowStep) srcRows.push(y)
    const nS = srcRows.length
    if (nS === 0) continue
    const sposY = new Float64Array(nS)
    for (let j = 0; j < nS; j++) sposY[j] = srcRows[j] * dy
    const fcol = new Float64Array(nS)

    // Pass 1 — down each column, over source rows of this parity only.
    for (let x = 0; x < w; x++) {
      for (let j = 0; j < nS; j++) fcol[j] = isSource[srcRows[j] * w + x] ? 0 : EDT_INF
      edt1d(fcol, sposY, qposY, gcol)
      for (let y = 0; y < hgt; y++) G[y * w + x] = gcol[y]
    }
    // Pass 2 — along each row. Sources carry this parity's x offset, queries carry their own row's.
    const srcShift = hex ? par * 0.5 * cellSizeM : 0
    for (let x = 0; x < w; x++) sposX[x] = x * cellSizeM + srcShift
    for (let y = 0; y < hgt; y++) {
      const qShift = hex && (y & 1) ? 0.5 * cellSizeM : 0
      for (let x = 0; x < w; x++) { qposX[x] = x * cellSizeM + qShift; row[x] = G[y * w + x] }
      edt1d(row, sposX, qposX, outRow)
      for (let x = 0; x < w; x++) { const i = y * w + x; if (outRow[x] < best[i]) best[i] = outRow[x] }
    }
  }
  return best
}

/**
 * Signed distance to the shoreline, in METRES.
 *
 * The shoreline is the set of DRY cells that touch water. That definition is what makes the zero
 * exact rather than interpolated: `waterDepth` is identically zero on land, so a crossing found by
 * interpolating depth between a wet and a dry cell lands on the dry cell itself. Taking the shoreline
 * to be those cells puts the zero contour on real samples, and `shoreDistance === 0` is then a
 * statement about the field rather than about a tolerance.
 *
 * Sign: POSITIVE in water (how far offshore a cell is), zero on the shoreline, NEGATIVE on land (how
 * far from the water). A downstream shore mask is a threshold on this; the production output is the
 * metres, per the story.
 */
export function signedShoreDistanceM(depth, w, hgt, { hex = false, cellSizeM = 1 } = {}) {
  const N = w * hgt
  const isShore = new Uint8Array(N)
  let shoreCount = 0, wetCount = 0
  for (let y = 0; y < hgt; y++) {
    const nb = hex ? hexNeighbours(y) : NB_SQUARE
    for (let x = 0; x < w; x++) {
      const i = y * w + x
      if (depth[i] > 0) { wetCount++; continue }
      for (let k = 0; k < nb.length; k++) {
        const xx = x + nb[k][0], yy = y + nb[k][1]
        if (xx < 0 || yy < 0 || xx >= w || yy >= hgt) continue
        if (depth[yy * w + xx] > 0) { isShore[i] = 1; shoreCount++; break }
      }
    }
  }
  // Everything is clamped to the domain diagonal. Without a shoreline anywhere the transform returns
  // its own infinity, and a raster full of 1e15 is a number no consumer can render, threshold or
  // debug. `-diagonal` says the true thing — every cell is dry and further from water than the domain
  // is wide — in a value that stays inside the field's own scale.
  const farM = Math.hypot(w * cellSizeM, hgt * cellSizeM * (hex ? HEX_ROW : 1))
  const out = new Float32Array(N)
  if (shoreCount === 0) { out.fill(-farM); return { shoreDistance: out, isShore, shoreCount, wetCount, farM } }

  const d2 = squaredDistanceToSet(isShore, w, hgt, { hex, cellSizeM })
  for (let i = 0; i < N; i++) {
    const d = Math.min(Math.sqrt(d2[i]), farM)
    // `d === 0 ? 0 : -d` and not `-d`: negating zero gives -0, which compares equal to 0 but is a
    // different Float32 bit pattern. A shoreline cell must read as the same zero everywhere.
    out[i] = depth[i] > 0 ? d : (d === 0 ? 0 : -d)
  }
  return { shoreDistance: out, isShore, shoreCount, wetCount, farM }
}

/**
 * Every lake in a heightfield: surface, depth, shore distance, basin identity, and the spill features.
 *
 * `minCells` suppresses puddles. A one-cell hollow is not a lake, and on a noisy DEM there are
 * hundreds of thousands of them: without a floor the label raster is confetti and the feature set is
 * unreadable. Suppression also UNDOES the fill on those cells, because `depth = max(0, surface -
 * solidTop)` has to keep holding exactly for them — leaving the surface raised while zeroing the depth
 * would break the identity the gate checks bit for bit.
 */
export function lakes(solidTop, w, hgt, { hex = false, cellSizeM = 1, minCells = 1 } = {}) {
  const N = w * hgt
  const surface = lakeSurface(solidTop, w, hgt, { hex })
  const depth = new Float32Array(N)
  for (let i = 0; i < N; i++) depth[i] = Math.max(0, surface[i] - solidTop[i])

  const lakeId = new Int32Array(N).fill(NO_LAKE)
  const nbOf = y => (hex ? hexNeighbours(y) : NB_SQUARE)

  // CONNECTED COMPONENTS OF WET CELLS ONLY. Dry cells are never enqueued, which is the whole reason
  // two basins either side of a dry sill stay two basins: they can share a rim, sit at the same
  // elevation, and still be different water bodies with different spills.
  const components = []
  const stack = []
  for (let s = 0; s < N; s++) {
    if (depth[s] <= 0 || lakeId[s] !== NO_LAKE) continue
    const id = components.length
    const cells = []
    lakeId[s] = id
    stack.length = 0
    stack.push(s)
    while (stack.length) {
      const c = stack.pop()
      cells.push(c)
      const cy = (c / w) | 0, cx = c - cy * w
      const nb = nbOf(cy)
      for (let k = 0; k < nb.length; k++) {
        const xx = cx + nb[k][0], yy = cy + nb[k][1]
        if (xx < 0 || yy < 0 || xx >= w || yy >= hgt) continue
        const ni = yy * w + xx
        if (depth[ni] <= 0 || lakeId[ni] !== NO_LAKE) continue
        lakeId[ni] = id
        stack.push(ni)
      }
    }
    components.push(cells)
  }

  // Apply the floor and compact the ids to 0..lakeCount-1 so the label raster's declared range means
  // something. A sparse id space would make `labels(0, count-1)` a lie.
  const kept = []
  for (const cells of components) {
    if (cells.length >= minCells) {
      const id = kept.length
      for (const i of cells) lakeId[i] = id
      kept.push(cells)
    } else {
      for (const i of cells) { surface[i] = solidTop[i]; depth[i] = 0; lakeId[i] = NO_LAKE }
    }
  }

  const cellArea = cellAreaM2(cellSizeM, hex)
  const basins = [], spills = []
  for (let id = 0; id < kept.length; id++) {
    const cells = kept[id]
    const level = surface[cells[0]]
    let volumeM3 = 0, floor = Infinity, maxDepth = 0
    const rim = new Set()
    for (const i of cells) {
      volumeM3 += depth[i] * cellArea
      if (solidTop[i] < floor) floor = solidTop[i]
      if (depth[i] > maxDepth) maxDepth = depth[i]
      const cy = (i / w) | 0, cx = i - cy * w
      const nb = nbOf(cy)
      for (let k = 0; k < nb.length; k++) {
        const xx = cx + nb[k][0], yy = cy + nb[k][1]
        if (xx < 0 || yy < 0 || xx >= w || yy >= hgt) continue
        const ni = yy * w + xx
        if (lakeId[ni] !== id) rim.add(ni)
      }
    }
    // THE SPILL IS THE LOWEST RIM CELL, and among cells tied at that elevation the one with the
    // lowest escape beyond it. The tiebreak is not cosmetic: on the analytic bowl the gate uses,
    // 12 of the 120 rim cells sit at exactly the fill elevation (counted, not estimated — an
    // earlier version of this comment said ~90), so "lowest rim" alone has twelve equally valid
    // answers and only one of them is the notch the water actually leaves through. Ranking ties by
    // the lowest surface among their own non-lake neighbours picks the notch, because that is what
    // "downhill from here leads away" means. Index order is the final tiebreak so the result is
    // deterministic even on a perfectly flat sill.
    let spillIndex = -1, spillH = Infinity, spillOut = Infinity
    for (const r of rim) {
      const rh = solidTop[r]
      if (rh > spillH) continue
      const ry = (r / w) | 0, rx = r - ry * w
      const nb = nbOf(ry)
      let out = Infinity
      for (let k = 0; k < nb.length; k++) {
        const xx = rx + nb[k][0], yy = ry + nb[k][1]
        if (xx < 0 || yy < 0 || xx >= w || yy >= hgt) continue
        const ni = yy * w + xx
        if (lakeId[ni] === id) continue
        if (surface[ni] < out) out = surface[ni]
      }
      const better = spillIndex < 0 || rh < spillH
        || (rh === spillH && (out < spillOut || (out === spillOut && r < spillIndex)))
      if (better) { spillIndex = r; spillH = rh; spillOut = out }
    }
    const sy = spillIndex >= 0 ? (spillIndex / w) | 0 : -1
    const sx = spillIndex >= 0 ? spillIndex - sy * w : -1
    const spill = { lakeId: id, index: spillIndex, x: sx, y: sy, elevation: spillH }
    spills.push(spill)
    basins.push({
      id, level, cellCount: cells.length, areaM2: cells.length * cellArea, volumeM3,
      floorElevation: floor, maxDepth, rimCells: rim.size,
      spillIndex, spillX: sx, spillY: sy, spillElevation: spillH,
    })
  }

  const shore = signedShoreDistanceM(depth, w, hgt, { hex, cellSizeM })
  return {
    surface, depth, lakeId, lakeCount: kept.length, basins, spills,
    shoreDistance: shore.shoreDistance, shoreCount: shore.shoreCount, wetCount: shore.wetCount,
  }
}
