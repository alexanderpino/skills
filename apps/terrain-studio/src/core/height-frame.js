// The measured height frame — ADR-005, and the precondition Sprint 3 declared and never had.
//
// Pure and DOM-free. It never imports legacy.js.
//
// THE PROBLEM THIS EXISTS TO SOLVE, measured before it was written. ADR-005 specifies one
// compatibility conversion to absolute elevation:
//
//     heightM[i] = baseElevationM + (legacy[i] - fieldMin) / (fieldMax - fieldMin) * reliefHeightM
//
// and `metricHeightField` in legacy.js implements exactly that. It AUTOLEVELS: fieldMin and fieldMax
// are recomputed from whatever field is passed in. That is right for display — it is what the
// viewport agrees with, and legacy.js records a correction warning against changing it, because a
// previous attempt made the solver simulate a world 2.12x flatter than drawn.
//
// But it is wrong for physics, and the reason is not a matter of taste. S3.3's solid-top identity
//
//     solidTopM = bedrockHeightM + soilDepthM + sedimentDepthM + sandDepthM
//
// must close BEFORE AND AFTER a transport step. Under an autolevelled frame, eroding the terrain
// moves fieldMin/fieldMax, so bedrockHeightM changes for bedrock that nothing touched, and the
// identity fails for a reason that has nothing to do with the physics. A frame whose absolute
// values depend on the current range of the field cannot carry a conservation law.
//
// THE DECISION ON RECORD IS TWO NAMED FRAMES. The viewport keeps autolevel, unchanged. Physical
// nodes take metres from a stable datum through an explicit adapter. Neither is "the" frame, both
// are named, and converting between them is a visible operation rather than an assumption — which
// is ADR-005's own "versioned boundary adapter" option, taken literally.
//
// The type system already refuses the mistake this guards, and by accident rather than design:
// a legacy field is `relativeHeight` with unit `none`, a physical input is `bedrockHeight` with
// unit `m`, and canConnect's unit rule is IDENTITY, so none -> m is UNIT_MISMATCH. The adapter is
// what makes that wire legal, and it has to be placed deliberately.

export const HEIGHT_FRAME_VERSION = 1

export const HEIGHT_FRAMES = Object.freeze(['display-autolevel', 'physical-stable'])

export const HEIGHT_FRAME_ERROR_CODES = Object.freeze([
  'FRAME_UNKNOWN', 'FRAME_RELIEF_INVALID', 'FRAME_DATUM_INVALID', 'FRAME_RANGE_DEGENERATE',
])

export class HeightFrameError extends Error {
  constructor(code, message, detail) { super(message); this.name = 'HeightFrameError'; this.code = code; this.detail = detail }
}

/**
 * Is this frame's answer a function of the field's own range?
 *
 * The single most useful thing to be able to ask. A field-dependent frame cannot appear on either
 * side of a conservation identity, and a caller that needs one should be able to check rather than
 * remember.
 */
export function frameIsFieldDependent(frame) {
  if (!HEIGHT_FRAMES.includes(frame)) {
    throw new HeightFrameError('FRAME_UNKNOWN', `unknown height frame ${JSON.stringify(frame)}`, { frame })
  }
  return frame === 'display-autolevel'
}

/** Min and max of a field, in one pass, ignoring non-finite samples. */
export function fieldExtremes(field) {
  let min = Infinity, max = -Infinity
  for (let i = 0; i < field.length; i++) {
    const v = field[i]
    if (!Number.isFinite(v)) continue
    if (v < min) min = v
    if (v > max) max = v
  }
  return { min, max }
}

/**
 * Convert a normalized legacy field to metres in a NAMED frame.
 *
 * `display-autolevel` reproduces metricHeightField bit-for-bit, including its `|| 1` guard on a
 * degenerate range — that guard is load-bearing (a constant field maps to the datum rather than
 * dividing by zero) and ADR-005 calls it out as the explicit policy replacing hidden behaviour.
 *
 * `physical-stable` does NOT consult the field at all beyond the sample itself, which is the whole
 * point: two calls with the same datum and relief agree sample-for-sample regardless of what else
 * is in the field.
 */
export function toMetres(field, { frame, datumM = 0, reliefM, fieldMin, fieldMax } = {}) {
  if (!HEIGHT_FRAMES.includes(frame)) {
    throw new HeightFrameError('FRAME_UNKNOWN', `unknown height frame ${JSON.stringify(frame)}`, { frame })
  }
  if (!Number.isFinite(reliefM) || reliefM <= 0) {
    throw new HeightFrameError('FRAME_RELIEF_INVALID', `reliefHeightM must be a positive finite number, got ${reliefM}`, { reliefM })
  }
  if (!Number.isFinite(datumM)) {
    throw new HeightFrameError('FRAME_DATUM_INVALID', `baseElevationM must be finite, got ${datumM}`, { datumM })
  }
  const out = new Float32Array(field.length)
  if (frame === 'physical-stable') {
    for (let i = 0; i < field.length; i++) out[i] = datumM + field[i] * reliefM
    return out
  }
  let mn = fieldMin, mx = fieldMax
  if (!Number.isFinite(mn) || !Number.isFinite(mx)) { const e = fieldExtremes(field); mn = e.min; mx = e.max }
  // `|| 1` exactly as metricHeightField writes it: a constant field has zero range and must map to
  // the datum, not to NaN.
  const range = (mx - mn) || 1
  for (let i = 0; i < field.length; i++) out[i] = datumM + (field[i] - mn) / range * reliefM
  return out
}

/**
 * Back to the normalized legacy frame.
 *
 * Only exact for `physical-stable`. Round-tripping through `display-autolevel` needs the ORIGINAL
 * min and max, because the autolevelled result no longer carries them — which is another way of
 * saying the display frame loses information the physical frame keeps.
 */
export function fromMetres(metres, { frame, datumM = 0, reliefM, fieldMin, fieldMax } = {}) {
  if (!HEIGHT_FRAMES.includes(frame)) {
    throw new HeightFrameError('FRAME_UNKNOWN', `unknown height frame ${JSON.stringify(frame)}`, { frame })
  }
  if (!Number.isFinite(reliefM) || reliefM <= 0) {
    throw new HeightFrameError('FRAME_RELIEF_INVALID', `reliefHeightM must be a positive finite number, got ${reliefM}`, { reliefM })
  }
  const out = new Float32Array(metres.length)
  if (frame === 'physical-stable') {
    for (let i = 0; i < metres.length; i++) out[i] = (metres[i] - datumM) / reliefM
    return out
  }
  if (!Number.isFinite(fieldMin) || !Number.isFinite(fieldMax)) {
    throw new HeightFrameError('FRAME_RANGE_DEGENERATE',
      'display-autolevel cannot be inverted without the original fieldMin/fieldMax', { fieldMin, fieldMax })
  }
  const range = (fieldMax - fieldMin) || 1
  for (let i = 0; i < metres.length; i++) out[i] = (metres[i] - datumM) / reliefM * range + fieldMin
  return out
}

/**
 * The property that decides which frame a physical node may use.
 *
 * Returns the maximum absolute difference between converting `a` and converting `b` at the samples
 * they share, when b is a is with one sample changed. Under a stable frame this is exactly the
 * change at that sample and zero everywhere else; under autolevel it is non-zero at EVERY sample
 * whenever the changed sample moved the field's min or max. That is the defect stated as a number,
 * and it is what the gate measures rather than asserting the design.
 */
export function frameDriftUnderLocalEdit(field, { frame, datumM = 0, reliefM, index, delta }) {
  const before = toMetres(field, { frame, datumM, reliefM })
  const edited = Float32Array.from(field)
  edited[index] += delta
  const after = toMetres(edited, { frame, datumM, reliefM })
  let maxElsewhere = 0, atIndex = 0
  for (let i = 0; i < before.length; i++) {
    const d = Math.abs(after[i] - before[i])
    if (i === index) atIndex = d
    else if (d > maxElsewhere) maxElsewhere = d
  }
  return { atIndex, maxElsewhere }
}
