// Rivers as FIELDS, not a carve — S4.5.
//
// Pure and DOM-free, like hydrology.js and water-waves.js: it never imports legacy.js, so an oracle
// can evaluate the hydraulic geometry under plain node, in double precision, with no browser.
//
// THE ONE THING THIS MODULE MUST NOT DO IS MOVE THE GROUND. Every river node in every shipping
// terrain tool this project has looked at is a DOWNCUT: it takes a flow field and subtracts a trench
// from the height, so the "river" is a hole. That is wrong twice over. It is wrong physically —
// a river is water sitting ON a bed, and the bed it sits on was shaped by erosion over geological
// time, not by the presence of today's flow — and it is wrong architecturally, because once the
// carve is baked into the height there is no way to change the discharge, the resolution or the
// climate without re-carving, and no way to ask what the terrain looked like before.
//
// So this module reads `solidTop` and returns THE SAME ARRAY, untouched. What it produces is a set
// of fields ABOUT the water: how wide the channel is, how deep the water in it is, how much of each
// cell it covers, and where its free surface sits. The tell that the design is right is one line:
//
//     waterSurface[i] = solidTopM[i] + depthM        // depth ADDED to make water
//     solidTopM[i]   -= depthM                       // the carve — what this must never be
//
// Same number, opposite sign, completely different claim. `_verify_rivers.js` arms exactly that
// mutation and asserts the input bed survives bitwise.
//
// HYDRAULIC GEOMETRY, AND WHY THESE EXPONENTS. Leopold & Maddock 1953 measured how channel form
// varies with discharge and found power laws with remarkably stable exponents:
//
//     width    w = kw * Q^0.5
//     depth    d = kd * Q^0.4
//     velocity v = kv * Q^0.1
//
// The exponents are the DOWNSTREAM set — how a river grows heading downstream, which is the terrain
// case — and NOT the at-a-station set (how one cross-section responds to a passing flood, where
// width goes as Q^~0.26). Confusing the two is the standard error and it under-widens every large
// river by a factor that grows with catchment size; `_verify_rivers.js` arms it as a mutation.
//
// The three exponents are not independent: discharge is width x depth x velocity by continuity, so
// 0.5 + 0.4 + 0.1 = 1 exactly, and kw * kd * kv = 1. That closure is a free correctness check on the
// exponent set and the oracle asserts it, which is why VELOCITY_EXPONENT is exported even though no
// port carries velocity yet (S4.9's flow-advected river motion is where it lands).
//
// The coefficients kw and kd are AUTHORED and carry SI units — m/(m3/s)^0.5 and m/(m3/s)^0.4. They
// are the only free parameters and they are not tuned after production output is seen.
import { SECONDS_PER_YEAR } from './hydrology.js'

/** Leopold & Maddock 1953 downstream exponents. Load-bearing: the laws below read them. */
export const WIDTH_EXPONENT = 0.5
export const DEPTH_EXPONENT = 0.4
/** Not carried by a port yet. Exported because it is what makes the exponent set closable. */
export const VELOCITY_EXPONENT = 0.1

// Midcontinent bankfull values, rounded to the two figures the source supports: w ~ 2.7*Q^0.5 and
// d ~ 0.30*Q^0.4, which imply kv = 1/(kw*kd) = 1.23 and reproduce the familiar "a few m/s in a big
// river" velocity. They are defaults, not constants: an author with a gauged basin should replace
// them, which is why they are sliders on the node rather than numbers buried here.
export const DEFAULT_WIDTH_COEFFICIENT = 2.7   // m / (m3/s)^0.5
export const DEFAULT_DEPTH_COEFFICIENT = 0.30  // m / (m3/s)^0.4

// CHANNEL INITIATION IS A THRESHOLD, not a fade. A hillslope is not a very small river: below some
// contributing area, flow is unchannelised sheetwash and there is no bank, no bed and no width to
// speak of. Montgomery & Dietrich put the channel-head support area between 1e3 and 1e5 m2 depending
// on climate and slope; 1e4 m2 is the middle of that range and the value used here.
//
// The node's parameter is a DISCHARGE, because discharge is what it is given — but a discharge
// threshold with no provenance is a magic number, so the default is computed from the area at a
// stated reference rainfall rather than typed in. Read it as: "the flow that 1e4 m2 of ground yields
// under 1000 mm/yr".
export const CHANNEL_HEAD_AREA_M2 = 1e4
export const CHANNEL_HEAD_REFERENCE_PRECIP_MM_YR = 1000
export const CHANNEL_HEAD_Q_M3PERS =
  CHANNEL_HEAD_REFERENCE_PRECIP_MM_YR * 1e-3 * CHANNEL_HEAD_AREA_M2 / SECONDS_PER_YEAR

/**
 * Channel width in metres from channel-forming discharge in m3/s.
 *
 * Written with the exported exponent rather than Math.sqrt so the exponent is the single place the
 * law lives — a hard-coded sqrt would make WIDTH_EXPONENT decorative, and a mutation against a
 * decorative constant is bit-identical to the original and proves nothing.
 */
export function channelWidthM(qM3PerS, kw = DEFAULT_WIDTH_COEFFICIENT) {
  return qM3PerS > 0 ? kw * Math.pow(qM3PerS, WIDTH_EXPONENT) : 0
}

/** Hydraulic WATER depth in metres — how deep the water is, never how deep to dig. */
export function channelDepthM(qM3PerS, kd = DEFAULT_DEPTH_COEFFICIENT) {
  return qM3PerS > 0 ? kd * Math.pow(qM3PerS, DEPTH_EXPONENT) : 0
}

/**
 * Mean section velocity in m/s, by continuity: v = Q / (w*d).
 *
 * Not a port yet. It is here because it is the third leg of the hydraulic-geometry triple and the
 * only way to check that the exponent set is self-consistent: continuity forces w*d*v = Q, which
 * holds identically only if the exponents sum to 1. The oracle uses it as exactly that check.
 */
export function meanVelocityMPerS(qM3PerS, kw = DEFAULT_WIDTH_COEFFICIENT, kd = DEFAULT_DEPTH_COEFFICIENT) {
  const wM = channelWidthM(qM3PerS, kw), dM = channelDepthM(qM3PerS, kd)
  return wM > 0 && dM > 0 ? qM3PerS / (wM * dM) : 0
}

/**
 * River fields from a discharge raster and the bed they sit on.
 *
 * `solidTopM` is metres from a stable datum (the S3 physical frame) and is RETURNED AS GIVEN — the
 * same array object, never written to. Adding water depth to a normalised height would be a unit
 * error, which is why this takes `solidTop:m` rather than the legacy `relativeHeight` field.
 *
 * Returned fields, all Float32 like every other production raster:
 *   channelMask    fraction of the cell the channel covers, 0 off-channel
 *   channelWidth   metres, 0 off-channel
 *   waterDepth     metres of WATER, 0 off-channel
 *   waterSurface   metres — bed plus water depth, equal to the bed where there is no channel
 *   channelCells   how many cells are channelised (a count worth printing is worth asserting)
 */
export function riverFields(solidTopM, dischargeM3PerS, w, hgt, {
  widthCoefficient = DEFAULT_WIDTH_COEFFICIENT,
  depthCoefficient = DEFAULT_DEPTH_COEFFICIENT,
  // The relations take the CHANNEL-FORMING (bankfull) discharge — the 1-2 year flood that actually
  // sets a channel's size — not the mean annual flow, which under-sizes every river. This factor is
  // the explicit conversion when the wired discharge is a mean. It defaults to 1, meaning "what is
  // wired is already channel-forming", because no source in the corpus fixes a bankfull/mean ratio
  // and a guessed default would silently resize every river in the app.
  bankfullFactor = 1,
  channelHeadQM3PerS = CHANNEL_HEAD_Q_M3PERS,
  cellSizeM = 1,
} = {}) {
  const N = w * hgt
  // A length mismatch means the caller wired fields from two different lattices. Sizing the output
  // to whichever array happened to be shorter would produce a plausible-looking river over the wrong
  // ground, so it is a throw rather than a clamp.
  if (solidTopM.length < N || dischargeM3PerS.length < N) {
    throw new Error(`riverFields: expected ${N} samples, got solidTop=${solidTopM.length} discharge=${dischargeM3PerS.length}`)
  }
  const channelMask = new Float32Array(N)
  const channelWidth = new Float32Array(N)
  const waterDepth = new Float32Array(N)
  // Seeded with the bed: where there is no channel the free surface IS the ground, which is the
  // same statement as "depth is zero" and keeps the identity waterSurface - solidTop = waterDepth
  // true everywhere rather than only on wet cells.
  const waterSurface = new Float32Array(N)
  for (let i = 0; i < N; i++) waterSurface[i] = solidTopM[i]
  let channelCells = 0

  for (let i = 0; i < N; i++) {
    const qb = bankfullFactor * dischargeM3PerS[i]
    // Written as `!(qb >= t)` so a NaN discharge falls out here instead of propagating into a width.
    if (!(qb >= channelHeadQM3PerS)) continue
    const wM = widthCoefficient * Math.pow(qb, WIDTH_EXPONENT)
    const dM = depthCoefficient * Math.pow(qb, DEPTH_EXPONENT)
    channelWidth[i] = wM
    waterDepth[i] = dM
    // WATER IS ADDED ON TOP OF THE BED. The carve is this line with the sign flipped and the target
    // changed to solidTopM, and that is the whole difference between this node and every downcutting
    // river node it was written against.
    waterSurface[i] = solidTopM[i] + dM
    // SUB-CELL COVERAGE, not a binary stamp. A 4 m channel in a 30 m cell does not fill the cell, and
    // a mask that says it does makes every river exactly one cell wide whatever its discharge — the
    // constant-width tell, in mask form. Clamped at 1 because a channel wider than the cell covers
    // it completely and cannot cover it more than completely.
    channelMask[i] = Math.min(1, wM / cellSizeM)
    channelCells++
  }

  return { solidTop: solidTopM, channelMask, channelWidth, waterDepth, waterSurface, channelCells }
}

/**
 * The Rivers node's typed port block, declared HERE rather than in the plugin.
 *
 * The plugin cannot be imported by an oracle — it imports legacy.js, which needs a DOM — so port
 * descriptors written inside it are unreachable to any check cheaper than launching a browser. Kept
 * in the pure module they are ordinary data, and `_verify_rivers.js` asserts the no-carve fence
 * directly on them: exactly one output carries a solid-terrain semantic, and it is the untouched
 * pass-through.
 */
export const RIVER_PORTS = {
  inputs: [
    // METRES, not the legacy normalised field. Water depth is in metres; adding it to a [0,1]
    // autolevelled height would be a unit error the type system is there to refuse.
    { id: 'solidTop', name: 'Solid top', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'solidTop', unit: 'm', role: 'data', required: true },
    { id: 'discharge', name: 'Discharge', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'discharge', unit: 'm3PerS', role: 'data', required: true },
  ],
  outputs: [
    // Primary is the bed, UNCHANGED, so anything downstream that wants terrain gets terrain and the
    // node is transparent in a chain. It is the same array that arrived.
    { id: 'solidTop', name: 'Solid top', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'solidTop', unit: 'm', primary: true, lens: 'continued' },
    { id: 'channelMask', name: 'Channel', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'mask', unit: 'none', lens: 'derived' },
    { id: 'channelWidth', name: 'Width', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'channelWidth', unit: 'm', lens: 'derived' },
    { id: 'waterDepth', name: 'Water depth', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'waterDepth', unit: 'm', lens: 'derived' },
    { id: 'waterSurface', name: 'Water surface', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'waterSurface', unit: 'm', lens: 'derived' },
  ],
}

/** Semantics that do not exist in core/ports.js yet and are the wiring precondition for this node.
 *
 *  ports.js is owned by another process, so this is a REQUEST, not a change: the entries below are
 *  exactly what has to be added there before `rivers.js` may be registered in
 *  `src/plugins/data/index.js`. Registering it first throws at merge time — validatePortList refuses
 *  an unknown semantic — so the two edits land together or not at all.
 *
 *  The oracle asserts (a) every output semantic is either already in ports.js or listed here, so the
 *  request cannot silently go missing, and (b) any entry that HAS landed in ports.js agrees with
 *  this declaration, so a merge that lands a different kind or unit is caught rather than assumed. */
export const PENDING_PORT_SEMANTICS = Object.freeze({
  channelWidth: Object.freeze({ kind: 'scalarRaster', defaultUnit: 'm', continuous: true,
    why: 'Leopold-Maddock channel width in metres. Not `height`: it is a horizontal extent, and a '
       + 'consumer that tonemapped or hillshaded it would be reading a length as an elevation.' }),
  waterDepth: Object.freeze({ kind: 'scalarRaster', defaultUnit: 'm', continuous: true,
    why: 'Depth of WATER above the bed, in metres. Distinct from depressionDepth (how far a hollow '
       + 'sits below its spill, a routing quantity in normalised height) and from any carve depth, '
       + 'which this project does not have. S4.4 Lake needs the same semantic.' }),
  waterSurface: Object.freeze({ kind: 'scalarRaster', defaultUnit: 'm', continuous: true,
    why: 'Free-surface elevation in metres from the same stable datum as solidTop, so that '
       + 'waterSurface - solidTop = waterDepth closes. S4.4 Lake emits it too.' }),
})
