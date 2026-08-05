// S4.10 — the metrics the water evidence, parity and frame-budget gate reasons over.
//
// Pure and DOM-free, and — unlike the rest of src/core — it imports NOTHING AT ALL. That is a
// requirement, not tidiness: the oracle patches this file's source text per mutation and imports the
// patched text from a `data:text/javascript` URL, which has no base URL, so any relative import in
// here would fail to resolve and every mutation would score red for the wrong reason ("module
// loads"), which reads as armed and proves nothing.
//
// WHY THIS EXISTS AS A MODULE RATHER THAN AS CODE INSIDE THE ORACLE. S4.10 is almost entirely a
// gate, so the way it fails is by measuring the wrong thing and reporting a number nobody can
// challenge. Every judgement it makes — what a p95 is, what counts as agreement between two water
// coverages, what a reset pulse is, and whether a frame time was measured on a GPU at all — lives
// here, in one place, where a mutation can be aimed at it. Metrics buried in a browser callback are
// metrics no mutation can reach.
//
// THE ONE RULE THROUGHOUT: an empty sample is an ERROR, never a default. Every function below
// throws or reports `empty` rather than returning a neutral value, because the failure mode this
// project keeps finding is a probe that compared nothing and reported agreement.

export const EVIDENCE_VERSION = 1

/* ------------------------------------------------------------------ renderer class --- */

// A frame time measured by a software rasteriser is not a frame time. The suite's house browser
// profile is `--use-angle=swiftshader`, so the DEFAULT way to run a WebGL oracle in this repo
// produces exactly the number that must never be allowed to discharge a millisecond budget.
//
// Matched against the UNMASKED renderer string, which is what actually names the device:
//   hardware  "ANGLE (Intel, Intel(R) Arc(TM) Pro 140T GPU (32GB) (0x00007D51) Direct3D11 ..., D3D11)"
//   software  "ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)"
export const SOFTWARE_RENDERER_RE =
  /swiftshader|llvmpipe|lavapipe|softpipe|soft ?ware|microsoft basic render|mesa offscreen|generic renderer|warp/i

/** 'hardware' | 'software' | 'unknown'. An empty or absent string is UNKNOWN, never hardware. */
export function classifyRenderer(renderer) {
  if (typeof renderer !== 'string' || renderer.trim() === '') return 'unknown'
  if (SOFTWARE_RENDERER_RE.test(renderer)) return 'software'
  return 'hardware'
}

/* ------------------------------------------------------------------ order statistics --- */

/**
 * Nearest-rank percentile — the ACTUAL order statistic, not a smoothed estimate and not a mean.
 *
 * S4.10 states its budget as a p95, and a p95 exists precisely to be sensitive to the tail: the
 * frame that stalls is the frame a reviewer sees. Reporting a mean under the name p95 hides exactly
 * the frames the budget is about, which is why `percentile-is-mean` is an armed mutation.
 */
export function percentile(values, p) {
  const list = values ? Array.prototype.slice.call(values) : []
  if (!list.length) throw new Error('percentile of an empty sample: nothing was measured')
  if (!(p >= 0 && p <= 1)) throw new Error(`percentile p must be in [0,1], got ${p}`)
  for (const v of list) if (!Number.isFinite(v)) throw new Error('percentile of a non-finite sample')
  list.sort((a, b) => a - b)
  const rank = Math.max(1, Math.ceil(p * list.length))
  return list[rank - 1]
}

/**
 * Paired A/B frame cost.
 *
 * PAIRED, not two separate blocks. A GPU's clock ramps, a laptop throttles, and a browser's
 * compositor drifts, so a block of 120 "water on" frames followed by a block of 120 "water off"
 * frames measures the machine's mood as much as the water. Alternating on/off within one loop and
 * differencing each pair cancels anything that varies slowly, which is everything that matters here.
 *
 * `onMs[i]` and `offMs[i]` must be the same pair index. Length mismatch and empty input both throw.
 */
export function pairedCost(onMs, offMs) {
  const on = onMs ? Array.prototype.slice.call(onMs) : []
  const off = offMs ? Array.prototype.slice.call(offMs) : []
  if (!on.length) throw new Error('pairedCost measured no frames')
  if (on.length !== off.length) throw new Error(`pairedCost pairs ${on.length} against ${off.length}`)
  const diff = []
  for (let i = 0; i < on.length; i++) diff.push(on[i] - off[i])
  return {
    pairs: on.length,
    diff,
    costP50: percentile(diff, 0.5),
    costP95: percentile(diff, 0.95),
    onP50: percentile(on, 0.5),
    onP95: percentile(on, 0.95),
    offP50: percentile(off, 0.5),
    offP95: percentile(off, 0.95),
  }
}

/**
 * Drop A/B pairs that were measured while the machine was busy with something else.
 *
 * THIS IS LEGITIMATE HERE FOR ONE SPECIFIC REASON, and it would not be legitimate without it: the
 * fixture renders the IDENTICAL FRAME every time — same camera, same clock, same scene — so the
 * true cost of the pass is a single number and every millisecond of spread is measurement noise by
 * construction. There is no genuine tail to protect. Interference is also one-sided: another process
 * on the adapter can only make a frame slower, never faster, so a sample far above its own
 * configuration's median is contamination and not water.
 *
 * Symmetric: the same rule is applied to both sides, so it cannot bias the difference toward zero.
 * The retention is returned so the caller can refuse a measurement taken on a machine that was busy
 * for most of it — a filter that quietly kept three pairs would be the vacuous version of this.
 */
export function rejectContendedPairs(onMs, offMs, { factor = 1.5 } = {}) {
  const on = onMs ? Array.prototype.slice.call(onMs) : []
  const off = offMs ? Array.prototype.slice.call(offMs) : []
  if (!on.length || on.length !== off.length) throw new Error('rejectContendedPairs needs two equal, non-empty samples')
  const capOn = percentile(on, 0.5) * factor
  const capOff = percentile(off, 0.5) * factor
  const keptOn = [], keptOff = []
  for (let i = 0; i < on.length; i++) {
    if (on[i] <= capOn && off[i] <= capOff) { keptOn.push(on[i]); keptOff.push(off[i]) }
  }
  return {
    on: keptOn, off: keptOff, offered: on.length, kept: keptOn.length,
    dropped: on.length - keptOn.length, retention: keptOn.length / on.length, capOn, capOff,
  }
}

/* ------------------------------------------------------------------ coverage --- */

/**
 * Agreement between two water coverage masks.
 *
 * WHY COVERAGE AND NOT PIXELS. The forward and deferred paths shade differently ON PURPOSE — the
 * deferred pass composites refraction from a G-buffer, the forward pass blends translucent geometry
 * — so requiring equal pixels would either fail forever or be tuned into meaninglessness. What they
 * are not allowed to disagree about is WHERE THE WATER IS: both displace by the same generated
 * Gerstner source at the same time, so the set of samples the water surface occupies must be the
 * same set. That is a geometric claim and it is checkable exactly.
 *
 * TWO EMPTY MASKS ARE NOT AGREEMENT. A parity check between a path that drew nothing and another
 * path that drew nothing scores a perfect intersection-over-union of 0/0, and that has been the
 * shape of every vacuous gate this project has found. `empty` is reported and `agreement` is forced
 * to zero, so an empty comparison is red rather than perfect.
 */
export function coverageAgreement(a, b) {
  if (!a || !b) throw new Error('coverageAgreement needs two masks')
  if (a.length !== b.length) throw new Error(`coverageAgreement sizes differ: ${a.length} vs ${b.length}`)
  if (!a.length) throw new Error('coverageAgreement over a zero-length mask')
  let countA = 0, countB = 0, intersection = 0, union = 0, disagreeing = 0
  for (let i = 0; i < a.length; i++) {
    const x = a[i] ? 1 : 0, y = b[i] ? 1 : 0
    countA += x; countB += y
    if (x && y) intersection++
    if (x || y) union++
    if (x !== y) disagreeing++
  }
  const empty = countA === 0 || countB === 0
  const agreement = empty ? 0 : intersection / union
  return { samples: a.length, countA, countB, intersection, union, disagreeing, agreement, empty }
}

/** Fraction of a mask that is set. Throws on a zero-length mask rather than reporting 0. */
export function coverageFraction(mask) {
  if (!mask || !mask.length) throw new Error('coverageFraction of an empty mask')
  let n = 0
  for (let i = 0; i < mask.length; i++) if (mask[i]) n++
  return n / mask.length
}

/* ------------------------------------------------------------------ frame partition --- */

/**
 * Split a rendered frame into the pixels the water changed and the pixels it did not.
 *
 * S4.10 requires that water pixels move under a time advance WHILE DRY TERRAIN PIXELS STAY
 * IDENTICAL, and that second half is the interesting one: an animated term leaking into terrain
 * shading is invisible to every "did the water move" check ever written. So the partition is
 * derived by differencing the frame against the same frame rendered with no water in the scene at
 * all — no projection maths, no screen-space guess about where the sea is, just the pixels that
 * demonstrably depend on the water existing.
 *
 * `tol` is a per-channel tolerance in 8-bit counts.
 */
export function partitionByWater(withWater, withoutWater, { tol = 0, channels = 4 } = {}) {
  if (!withWater || !withoutWater) throw new Error('partitionByWater needs two frames')
  if (withWater.length !== withoutWater.length) throw new Error('partitionByWater frame sizes differ')
  if (!withWater.length) throw new Error('partitionByWater over an empty frame')
  const pixels = (withWater.length / channels) | 0
  if (!pixels) throw new Error('partitionByWater over a frame with no pixels')
  const waterMask = new Uint8Array(pixels)
  let waterCount = 0
  for (let i = 0; i < pixels; i++) {
    const o = i * channels
    let differs = 0
    for (let c = 0; c < 3; c++) if (Math.abs(withWater[o + c] - withoutWater[o + c]) > tol) differs = 1
    waterMask[i] = differs
    waterCount += differs
  }
  return { pixels, waterMask, waterCount, dryCount: pixels - waterCount }
}

/** How many pixels of `mask` changed between two frames, and how many were compared. */
export function changedWithin(frameA, frameB, mask, { tol = 0, channels = 4 } = {}) {
  if (!frameA || !frameB || !mask) throw new Error('changedWithin needs two frames and a mask')
  if (frameA.length !== frameB.length) throw new Error('changedWithin frame sizes differ')
  const pixels = (frameA.length / channels) | 0
  if (mask.length !== pixels) throw new Error(`changedWithin mask ${mask.length} against ${pixels} pixels`)
  let considered = 0, changed = 0, worst = 0
  for (let i = 0; i < pixels; i++) {
    if (!mask[i]) continue
    considered++
    const o = i * channels
    let d = 0
    for (let c = 0; c < 3; c++) d = Math.max(d, Math.abs(frameA[o + c] - frameB[o + c]))
    if (d > tol) changed++
    if (d > worst) worst = d
  }
  // An empty consideration set is not "nothing changed", it is "nothing was compared".
  return { considered, changed, worst, fraction: considered ? changed / considered : 0, empty: considered === 0 }
}

/** Is a frame blank? Non-blank means it carries more than one distinct luminance and is finite. */
export function frameStats(frame, { channels = 4 } = {}) {
  if (!frame || !frame.length) throw new Error('frameStats of an empty frame')
  const pixels = (frame.length / channels) | 0
  let sum = 0, min = 255, max = 0, nonZero = 0, nonFinite = 0
  const seen = new Set()
  for (let i = 0; i < pixels; i++) {
    const o = i * channels
    const lum = 0.299 * frame[o] + 0.587 * frame[o + 1] + 0.114 * frame[o + 2]
    if (!Number.isFinite(lum)) { nonFinite++; continue }
    sum += lum
    if (lum < min) min = lum
    if (lum > max) max = lum
    if (lum > 2) nonZero++
    if (seen.size < 4096) seen.add(Math.round(lum))
  }
  return {
    pixels, meanLum: pixels ? sum / pixels : 0, minLum: min, maxLum: max,
    nonZeroFraction: pixels ? nonZero / pixels : 0, distinctLevels: seen.size, nonFinite,
    blank: !(pixels > 0) || seen.size <= 1 || nonZero === 0,
  }
}

/* ------------------------------------------------------------------ temporal path --- */

/**
 * Reset-pulse detection over a sampled temporal path.
 *
 * A "reset pulse" is what a viewer sees when an animation clock wraps: the surface is continuous for
 * a minute and then jumps in one frame. It is invisible to every check that samples one instant, and
 * invisible to an average over the path, because it is ONE step out of thousands.
 *
 * THE TEST IS RELATIVE, and that is the whole design. A pulse detector with an absolute threshold in
 * metres is blind to a calm sea: reduce the amplitude by a hundred and the discontinuity shrinks
 * with it while remaining just as visible on screen, because everything else shrank too. Comparing
 * the largest step to the MEDIAN step is scale-free, so the same tolerance holds for a millpond and
 * a gale. `pulse-absolute-threshold` is the armed mutation for exactly that.
 *
 * The median is used rather than the mean only because it is the robust centre; with one outlier in
 * a few thousand samples the two barely differ, so nothing here leans on that choice.
 */
export function pulseScan(samples, { tolerance = 8 } = {}) {
  const list = samples ? Array.prototype.slice.call(samples) : []
  if (list.length < 3) throw new Error(`pulseScan needs at least 3 samples, got ${list.length}`)
  for (const v of list) if (!Number.isFinite(v)) throw new Error('pulseScan over a non-finite path')
  const steps = []
  // THE LAST STEP COUNTS. An off-by-one here silently exempts the end of the path, and a clock that
  // wraps at exactly the sampled horizon is the most likely place for a wrap to be: `pulse-skips-
  // last-step` is the armed mutation, and it is a real off-by-one, not a synthetic one.
  for (let i = 1; i < list.length; i++) steps.push(Math.abs(list[i] - list[i - 1]))
  const sorted = steps.slice().sort((a, b) => a - b)
  const medianStep = sorted[(sorted.length / 2) | 0]
  let maxStep = 0, at = -1
  for (let i = 0; i < steps.length; i++) if (steps[i] > maxStep) { maxStep = steps[i]; at = i + 1 }
  const ratio = medianStep > 0 ? maxStep / medianStep : (maxStep > 0 ? Infinity : 0)
  return { samples: list.length, steps: steps.length, medianStep, maxStep, at, ratio, pulse: ratio > tolerance }
}

/** Strictly-increasing check for a clock trace, with the largest and smallest advance. */
export function clockScan(times, { maxStepS = 0.1 } = {}) {
  const list = times ? Array.prototype.slice.call(times) : []
  if (list.length < 2) throw new Error(`clockScan needs at least 2 readings, got ${list.length}`)
  let minAdvance = Infinity, maxAdvance = -Infinity, backwards = 0, stalled = 0
  for (let i = 1; i < list.length; i++) {
    const d = list[i] - list[i - 1]
    if (d < minAdvance) minAdvance = d
    if (d > maxAdvance) maxAdvance = d
    if (d < 0) backwards++
    if (d === 0) stalled++
  }
  return {
    readings: list.length, minAdvance, maxAdvance, backwards, stalled,
    monotone: backwards === 0 && stalled === 0,
    clamped: maxAdvance <= maxStepS + 1e-9,
    span: list[list.length - 1] - list[0],
  }
}

/* ------------------------------------------------------------------ budget verdict --- */

/**
 * The frame-budget verdict.
 *
 * THREE SEPARATE CLAIMS, deliberately not collapsed into one boolean:
 *   measured    a finite number came back at all
 *   admissible  it came from a GPU — a SwiftShader millisecond is not a millisecond
 *   withinBudget the number is under the plan's figure
 *
 * The oracle asserts each on its own, because "the water is within budget" reported by a software
 * rasteriser and "the water is within budget" measured on the capture machine are different claims
 * and only one of them discharges S4.10.
 */
export function budgetVerdict({ p95Ms, budgetMs, rendererClass } = {}) {
  const measured = Number.isFinite(p95Ms)
  const admissible = measured && rendererClass === 'hardware'
  const withinBudget = measured && p95Ms <= budgetMs
  return { p95Ms, budgetMs, rendererClass, measured, admissible, withinBudget, ok: admissible && withinBudget }
}
