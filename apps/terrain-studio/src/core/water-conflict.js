// S4.6 — conflict surfacing for authored river guides.
//
// Pure and DOM-free, like hydrology.js and water-waves.js: it never imports legacy.js, so an oracle
// can evaluate it under plain node, in double precision, with no browser involved.
//
// WHY THIS EXISTS. An author draws a river guide across the terrain. Sometimes the line they drew
// runs UPHILL — against the routed flow, or simply climbing ground that a channel cannot climb. The
// tempting thing to do is fix it: smooth the guide, lower the ridge, nudge the elevations until the
// line drains. `BACKLOG D5` forbids exactly that, and the sprint doctrine spells out why: water
// should not bake. A guide that cannot work is INFORMATION — it tells the author their intent and
// their terrain disagree, and where, and by how much. Silently resolving it destroys that
// information and produces terrain nobody chose.
//
// So this module MEASURES and REPORTS. It never writes to the surface it was handed, it never
// smooths what it measured, and it never applies the repair it can describe. Accepting the offer is
// a separate, explicit, undoable act performed by the caller — see `proposeConditioningBranch`,
// which returns a DESCRIPTION of a branch and cannot itself change anything.
//
// TWO INDEPENDENT CONFLICT SIGNALS, because they fail separately and a guide can trip either alone:
//
//   ELEVATION DEFICIT   the sprint plan's recurrence. Walking the guide, the routing surface must
//                       keep descending by at least the HydroFix descent epsilon per unit of
//                       distance. Where it does not, the deficit is how far the surface would have
//                       to be cut for the guide to drain. It is cumulative: a long steady climb is
//                       a large deficit at the top, not a small one at every step.
//   FLOW OPPOSITION     the dot product of the guide's direction of travel with the routed flow
//                       direction from `mfdWeights`. -1 means the author drew the river running
//                       exactly backwards. This can be true where the deficit is still zero (a
//                       guide crossing a valley floor sideways) and vice versa, so both are
//                       reported and neither is folded into the other.

/** HydroFix's descent divisor, from `hydroFixField` in legacy.js: eps = relief/(max(res,2)*160).
 *  Reused verbatim so a guide is judged against the SAME descent the conditioning node would
 *  enforce — a conflict report measured against a different slope would describe a repair that the
 *  offered branch does not perform. */
export const DESCENT_DIVISOR = 160

/** Sprint-4 contract: "Resample each guide at spacing ds <= 0.5 * cellSize." Half a cell is the
 *  coarsest spacing at which a one-cell rise cannot be stepped over unseen. */
export const GUIDE_SPACING_CELLS = 0.5

/** A hex row is sqrt(3)/2 of a column. Same constant as hydrology.js and legacy's HEX_ROW. */
const HEX_ROW = Math.sqrt(3) / 2

/** The floor legacy's `hydroFixField` applies to relief: `Math.max(mx-mn, 1e-5)`. Kept because a
 *  perfectly constant surface would otherwise produce eps = 0, and then a dead-flat canal — which
 *  drains nowhere — would report zero conflict. A conflict analysis that says a flat channel is
 *  fine is the failure this whole module exists to prevent. */
const RELIEF_FLOOR = 1e-5

/** Relief of a field, as `fieldRange` + the HydroFix floor computes it. */
export function fieldRelief(field) {
  let mn = Infinity, mx = -Infinity
  for (let i = 0; i < field.length; i++) { const v = field[i]; if (v < mn) mn = v; if (v > mx) mx = v }
  if (!Number.isFinite(mn) || !Number.isFinite(mx)) throw new Error('fieldRelief: field carries no finite samples')
  return Math.max(mx - mn, RELIEF_FLOOR)
}

/** The per-cell descent HydroFix enforces, in normalized height. */
export function descentEpsilon(relief, resolution) {
  return relief / (Math.max(resolution, 2) * DESCENT_DIVISOR)
}

/**
 * Resample an authored polyline to uniform spacing of at most `spacingCells` cells.
 *
 * Control points are TWO-DIMENSIONAL INTENT in world metres — the plan is explicit that a guide
 * carries no elevation of its own and that elevation comes only from sampling the routing surface.
 * Accepting a z-per-point here would let an author declare a river's height, which is precisely the
 * authority this story refuses to give them.
 *
 * The step is `length / ceil(length / target)`, not `target` with a short remainder: a final stub
 * step would give the last sample a smaller descent allowance than every other, and the deficit
 * there would depend on where the polyline happened to end.
 */
export function resampleGuide(points, { cellSizeM, spacingCells = GUIDE_SPACING_CELLS } = {}) {
  if (!Number.isFinite(cellSizeM) || cellSizeM <= 0) throw new Error('resampleGuide: cellSizeM must be a positive number of metres')
  if (!Number.isFinite(spacingCells) || spacingCells <= 0 || spacingCells > GUIDE_SPACING_CELLS) {
    throw new Error(`resampleGuide: spacingCells must be in (0, ${GUIDE_SPACING_CELLS}] — the plan caps guide spacing at half a cell`)
  }
  const pts = (points || []).map(p => (Array.isArray(p) ? { x: p[0], z: p[1] } : p))
  if (pts.length < 2) throw new Error('resampleGuide: a guide needs at least two control points')
  for (const p of pts) {
    if (!p || !Number.isFinite(p.x) || !Number.isFinite(p.z)) throw new Error('resampleGuide: every control point needs finite world-metre x and z')
  }
  const segLen = []
  let total = 0
  for (let i = 1; i < pts.length; i++) {
    const d = Math.hypot(pts[i].x - pts[i - 1].x, pts[i].z - pts[i - 1].z)
    segLen.push(d); total += d
  }
  // A zero-length guide is not "a guide with no conflict", it is no guide at all. Reporting a clean
  // result for it would be absence of evidence dressed up as a pass.
  if (!(total > 0)) throw new Error('resampleGuide: guide has zero length — nothing to sample')

  const target = spacingCells * cellSizeM
  const steps = Math.max(1, Math.ceil(total / target))
  const step = total / steps
  const count = steps + 1
  const x = new Float64Array(count), z = new Float64Array(count), ds = new Float64Array(count)
  let seg = 0, consumed = 0
  for (let i = 0; i < count; i++) {
    const s = i === steps ? total : i * step        // exact endpoint, never total - epsilon
    while (seg < segLen.length - 1 && s > consumed + segLen[seg]) { consumed += segLen[seg]; seg++ }
    const t = segLen[seg] > 0 ? (s - consumed) / segLen[seg] : 0
    const a = pts[seg], b = pts[seg + 1]
    x[i] = a.x + (b.x - a.x) * t
    z[i] = a.z + (b.z - a.z) * t
    ds[i] = i === 0 ? 0 : step
  }
  return { x, z, ds, count, lengthM: total, stepM: step }
}

/**
 * Bilinear sample of a scalar raster at a world-metre position.
 *
 * `a + (b - a) * t`, NOT `a*(1-t) + b*t`. The two differ only in rounding, and the rounding is the
 * point: with the second form a sample taken between two IDENTICAL stored values comes back a few
 * units in the last place away from them, so a guide crossing dead-flat ground reports a terrain
 * rise of ~1e-17 that it did not have. That is small, and it makes "this ground is exactly flat"
 * unprovable — the first form returns `a` exactly when `a === b`.
 *
 * The hex branch resolves each of the two rows with ITS OWN half-cell offset before interpolating
 * between them, because on a pointy-odd-r lattice odd rows are shifted by half a column; using one
 * offset for both would shear every sample by half a cell on alternate rows.
 */
export function sampleScalarWorld(field, w, hgt, xM, zM, { cellSizeM, hex = false } = {}) {
  const rowPitch = cellSizeM * (hex ? HEX_ROW : 1)
  const v = zM / rowPitch
  const r0 = Math.min(hgt - 1, Math.max(0, Math.floor(v)))
  const r1 = Math.min(hgt - 1, r0 + 1)
  const tz = Math.min(1, Math.max(0, v - r0))
  const rowValue = r => {
    const off = hex && (r & 1) ? 0.5 : 0
    const u = xM / cellSizeM - off
    const c0 = Math.min(w - 1, Math.max(0, Math.floor(u)))
    const c1 = Math.min(w - 1, c0 + 1)
    const tx = Math.min(1, Math.max(0, u - c0))
    const a = field[r * w + c0], b = field[r * w + c1]
    return a + (b - a) * tx
  }
  const a = rowValue(r0), b = rowValue(r1)
  return a + (b - a) * tz
}

/**
 * Nearest-cell sample of the routed flow direction.
 *
 * NEAREST, NOT BILINEAR, and this is a physics decision rather than a performance one. `dirX/dirZ`
 * are UNIT vectors; averaging the two either side of a divide gives a near-zero vector, which reads
 * as "no routed flow" at exactly the place where the routing is most certain. Sinks and outlets
 * already carry (0,0) from `mfdWeights`, and that zero has to keep meaning "nowhere to send water"
 * and nothing else, so it is reported as `known:false` rather than as a direction.
 */
export function sampleFlowWorld(flow, w, hgt, xM, zM, { cellSizeM, hex = false } = {}) {
  const rowPitch = cellSizeM * (hex ? HEX_ROW : 1)
  const r = Math.min(hgt - 1, Math.max(0, Math.round(zM / rowPitch)))
  const off = hex && (r & 1) ? 0.5 : 0
  const c = Math.min(w - 1, Math.max(0, Math.round(xM / cellSizeM - off)))
  const i = r * w + c
  const fx = flow.dirX[i], fz = flow.dirZ[i]
  const len = Math.hypot(fx, fz)
  if (!(len > 0)) return { x: 0, z: 0, known: false, index: i }
  return { x: fx / len, z: fz / len, known: true, index: i }
}

/** Unpack an interleaved N*components vector raster into the `{dirX, dirZ}` pair `mfdWeights`
 *  returns, so a graph-side flowDirection port and a direct routing call feed the same analyser. */
export function flowFromVectorRaster(vec, N, components = 3) {
  if (!vec || vec.length < N * components) throw new Error('flowFromVectorRaster: vector raster is shorter than the declared sample count')
  const dirX = new Float32Array(N), dirZ = new Float32Array(N)
  // Component 1 is y, which is zero by construction for flowDirection — see flow_physical.js.
  const zi = components >= 3 ? 2 : 1
  for (let i = 0; i < N; i++) { dirX[i] = vec[i * components]; dirZ[i] = vec[i * components + zi] }
  return { dirX, dirZ }
}

/**
 * Measure where and by how much an authored guide conflicts with the surface it is drawn on.
 *
 * `surface` is a ROUTING SURFACE in normalized height (the S4.1 product), never terrain, and it is
 * read only — the caller's array comes back bit-identical.
 *
 * `heightScaleM` HAS NO DEFAULT. A deficit is reported in metres, and the conversion from
 * normalized height to metres is the whole difference between "your guide climbs 64 m of hillside"
 * and "your guide climbs 0.032". Defaulting it to 1 would silently make every report dimensionless
 * while still calling the number metres, which is the same class of defect as the dropped mm->m and
 * per-year conversions the S4.2 gate arms against.
 */
export function analyzeGuideConflict(surface, w, hgt, guidePoints, opts = {}) {
  const {
    cellSizeM, heightScaleM, hex = false, flow = null,
    resolution = w, relief = null, spacingCells = GUIDE_SPACING_CELLS,
  } = opts
  if (!Number.isFinite(cellSizeM) || cellSizeM <= 0) throw new Error('analyzeGuideConflict: cellSizeM must be a positive number of metres')
  if (!Number.isFinite(heightScaleM) || heightScaleM <= 0) {
    throw new Error('analyzeGuideConflict: heightScaleM must be a positive number of metres — a vertical scale nobody stated is not a scale of 1')
  }
  if (!surface || surface.length !== w * hgt) throw new Error('analyzeGuideConflict: surface length does not match w*hgt')

  const g = resampleGuide(guidePoints, { cellSizeM, spacingCells })
  const n = g.count
  const elevation = new Float64Array(n)
  for (let i = 0; i < n; i++) elevation[i] = sampleScalarWorld(surface, w, hgt, g.x[i], g.z[i], { cellSizeM, hex })

  const reliefUsed = relief != null ? relief : fieldRelief(surface)
  const epsCell = descentEpsilon(reliefUsed, resolution)

  // THE RECURRENCE, exactly as the sprint plan states it:
  //   target[0] = z[0];  target[i] = min(z[i], target[i-1] - epsCell * ds[i]/cellSize)
  //
  // `target[i-1]`, NOT `z[i-1]`. The target is a RATCHET: once the guide has been forced below the
  // ground it must stay below it, so a steady climb accumulates. Restarting from the terrain each
  // step turns a 64 m climb into sixteen separate 4 m steps and reports the largest of them — a
  // sixteenfold understatement that still looks like a plausible conflict report.
  //
  // `ds[i]/cellSize` makes the allowance proportional to DISTANCE TRAVELLED, not to sample count.
  // Without it, resampling the same guide more finely would change the answer, and the physical
  // question "can this channel drain" would depend on an authoring detail.
  const target = new Float64Array(n)
  target[0] = elevation[0]
  for (let i = 1; i < n; i++) {
    const step = epsCell * (g.ds[i] / cellSizeM)
    target[i] = Math.min(elevation[i], target[i - 1] - step)
  }

  // NOT SMOOTHED, NOT DEADBANDED, NOT CLIPPED. Every sample's deficit is reported as measured. A
  // filter here — even a three-tap average "to remove sampling noise" — is the armed failure of
  // this story: it turns a real one-cell obstruction into two-thirds of itself and hides the small
  // ones entirely, and the author is never told anything was removed.
  const deficit = new Float64Array(n)
  const deficitM = new Float64Array(n)
  for (let i = 0; i < n; i++) {
    deficit[i] = elevation[i] - target[i]
    deficitM[i] = deficit[i] * heightScaleM
  }

  // --- flow opposition ---------------------------------------------------------------------
  const alignment = new Float64Array(n).fill(NaN)
  const opposition = new Float64Array(n).fill(NaN)
  const flowKnown = new Uint8Array(n)
  const flowSupplied = !!(flow && flow.dirX && flow.dirZ)
  if (flowSupplied) {
    for (let i = 0; i < n; i++) {
      // Central difference where there is one on both sides; one-sided at the ends. A guide's
      // direction of travel is a property of the line, not of one sample.
      const a = Math.max(0, i - 1), b = Math.min(n - 1, i + 1)
      const tx = g.x[b] - g.x[a], tz = g.z[b] - g.z[a]
      const tl = Math.hypot(tx, tz)
      if (!(tl > 0)) continue
      const f = sampleFlowWorld(flow, w, hgt, g.x[i], g.z[i], { cellSizeM, hex })
      if (!f.known) continue
      flowKnown[i] = 1
      alignment[i] = (tx / tl) * f.x + (tz / tl) * f.z
      opposition[i] = (1 - alignment[i]) / 2
    }
  }

  let maxDeficit = 0, maxIndex = -1, conflictCount = 0, opposedCount = 0, unroutedCount = 0
  let totalCutVolumeProxyM = 0
  for (let i = 0; i < n; i++) {
    if (deficit[i] > maxDeficit) { maxDeficit = deficit[i]; maxIndex = i }
    if (deficit[i] > 0) { conflictCount++; totalCutVolumeProxyM += deficitM[i] }
    if (flowKnown[i]) { if (alignment[i] < 0) opposedCount++ } else unroutedCount++
  }

  // The per-sample record set: position, cause and severity. Severity IS the deficit in metres —
  // there is no invented 0..1 "score", because a score cannot be checked against the terrain and a
  // depth can.
  const conflicts = []
  for (let i = 0; i < n; i++) {
    const rises = deficit[i] > 0
    const opposed = flowKnown[i] === 1 && alignment[i] < 0
    if (!rises && !opposed) continue
    conflicts.push({
      index: i, xM: g.x[i], zM: g.z[i],
      elevation: elevation[i], targetElevation: target[i],
      deficit: deficit[i], deficitM: deficitM[i], severityM: deficitM[i],
      alignment: flowKnown[i] ? alignment[i] : null,
      opposition: flowKnown[i] ? opposition[i] : null,
      cause: rises && opposed ? 'rise+against-flow' : (rises ? 'rise' : 'against-flow'),
    })
  }

  return {
    count: n, spacingM: g.stepM, lengthM: g.lengthM,
    x: g.x, z: g.z, ds: g.ds,
    elevation, target, deficit, deficitM,
    alignment, opposition, flowKnown, flowSupplied,
    relief: reliefUsed, epsCell, heightScaleM,
    maxDeficit, maxDeficitM: maxDeficit * heightScaleM, maxIndex,
    maxAtM: maxIndex >= 0 ? { x: g.x[maxIndex], z: g.z[maxIndex] } : null,
    conflictCount, opposedCount, unroutedCount, totalCutVolumeProxyM,
    conflicts,
    hasConflict: conflictCount > 0 || opposedCount > 0,
  }
}

/** The conditioning branches a conflict report may offer. `hydrofix` is the ONLY one that writes
 *  terrain height, and it is labelled as such here so no caller can offer it as if it were free. */
export const CONDITIONING_BRANCHES = Object.freeze({
  fill: { nodeType: 'depression', params: { mode: 'fill' }, writesHeight: false,
    label: 'Depression Policy — fill to spill', effect: 'Raises the routing surface to each basin\'s spill. Terrain is untouched.' },
  breach: { nodeType: 'depression', params: { mode: 'breach' }, writesHeight: false,
    label: 'Depression Policy — breach an outlet', effect: 'Cuts a monotone outlet on the routing surface only. Terrain is untouched.' },
  hydrofix: { nodeType: 'hydrofix', params: {}, writesHeight: true,
    label: 'HydroFix — bedrock drainage conditioning', effect: 'Low-amplitude downcut along accumulated corridors. THIS ONE WRITES TERRAIN HEIGHT.' },
})

/**
 * Describe — never perform — the conditioning branch that would resolve a reported conflict.
 *
 * This returns DATA. It adds no node, edits no graph and touches no field; the caller creates the
 * branch as one explicit, undoable record if the author accepts. That separation is the story: the
 * failure being guarded against is a node that quietly conditions the terrain because it noticed a
 * problem, and a function that both detects and repairs cannot be prevented from doing so.
 *
 * Returns `null` when there is nothing wrong. An offer to fix a guide that is already fine is
 * noise, and worse, it trains the author to accept offers without reading them.
 */
export function proposeConditioningBranch(report, { mode = 'breach' } = {}) {
  if (!report || typeof report !== 'object') throw new Error('proposeConditioningBranch: needs a conflict report')
  const branch = CONDITIONING_BRANCHES[mode]
  if (!branch) throw new Error(`proposeConditioningBranch: unknown branch ${JSON.stringify(mode)} — expected one of ${Object.keys(CONDITIONING_BRANCHES).join(', ')}`)
  if (!report.hasConflict) return null
  return {
    mode,
    nodeType: branch.nodeType,
    params: { ...branch.params },
    writesHeight: branch.writesHeight,
    label: branch.label,
    effect: branch.effect,
    undoable: true,
    applied: false,          // this object never becomes `true`; the caller's undo record does
    maxDeficitM: report.maxDeficitM,
    maxAtM: report.maxAtM ? { ...report.maxAtM } : null,
    conflictCount: report.conflictCount,
    opposedCount: report.opposedCount,
    reason: report.conflictCount > 0
      ? `Guide rises against its own drainage: ${report.conflictCount} of ${report.count} samples, worst deficit ${report.maxDeficitM.toFixed(2)} m.`
      : `Guide runs against the routed flow at ${report.opposedCount} of ${report.count} samples.`,
  }
}
