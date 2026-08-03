// WorldDomain/1 — the authoritative horizontal and vertical frame (ADR-007, story S9.1).
//
// Pure and DOM-free.
//
// Today the app has ONE number for world size: `terrainDef.scale`, a single metre extent for both
// axes, plus a global square `RES`. Width and height are not independent — `fieldH()` is a pure
// function of `fieldW()` — so a 1573 x 13789 terrain cannot be expressed, let alone authored. This
// schema is what makes that expressible; S9.9 makes it evaluable.
//
// THREE THINGS THIS FIXES, each a measured property of the current build:
//
//   1. Independent axes. extentM.width and extentM.height are separate positive numbers.
//   2. Honest spacing. Spacing mode derives an INTEGRAL sample count and reports the spacing that
//      actually results. The dialog never rounds silently while continuing to display the requested
//      value as if it were exact — which is the specific dishonesty ADR-007 calls out.
//   3. A real vertical frame. `terrainDef.height` and `baseElevation` become a datum plus a range,
//      and an unknown datum is represented AS unknown rather than silently called sea level.
//
// MIGRATION PRESERVES NUMERICAL OUTPUT, which is the whole reason `posting` exists. An existing
// document becomes posting:'legacy-cell' with width = height = terrainDef.scale and spacing
// scale/RES — exactly what the current evaluator computes. Converting legacy-cell to vertex posting
// is a separate, explicit resample, never an automatic load mutation, because it moves every sample
// by half a cell.

export const WORLD_DOMAIN_VERSION = 1
export const AUTHORING_UNITS = Object.freeze({ m: 1, km: 1000, mi: 1609.344, ft: 0.3048 })
export const LATTICES = Object.freeze(['square', 'hex-pointy-odd-r'])
export const POSTINGS = Object.freeze(['vertex', 'legacy-cell'])
export const RESOLUTION_MODES = Object.freeze(['spacing', 'explicit-samples'])
export const DATUM_KINDS = Object.freeze(['unknown', 'seaLevel', 'ellipsoid', 'local'])

export const MIN_SAMPLES = 2

export const DOMAIN_ERROR_CODES = Object.freeze([
  'DOMAIN_EXTENT_INVALID', 'DOMAIN_SAMPLES_INVALID', 'DOMAIN_SPACING_INVALID',
  'DOMAIN_LATTICE_UNKNOWN', 'DOMAIN_POSTING_UNKNOWN', 'DOMAIN_MODE_UNKNOWN',
  'DOMAIN_UNIT_UNKNOWN', 'DOMAIN_VERTICAL_INVALID', 'DOMAIN_DATUM_UNKNOWN',
])

export class DomainError extends Error {
  constructor(code, message, detail) { super(message); this.name = 'DomainError'; this.code = code; this.detail = detail }
}

const finitePositive = v => Number.isFinite(v) && v > 0

/** Validate a WorldDomain. Returns problems rather than throwing so a dialog can show them all. */
export function validateDomain(d) {
  const problems = []
  if (!d || typeof d !== 'object') return [{ code: 'DOMAIN_EXTENT_INVALID', reason: 'not an object' }]
  const ex = d.extentM || {}
  if (!finitePositive(ex.width) || !finitePositive(ex.height)) {
    problems.push({ code: 'DOMAIN_EXTENT_INVALID', width: String(ex.width), height: String(ex.height) })
  }
  if (!LATTICES.includes(d.lattice)) problems.push({ code: 'DOMAIN_LATTICE_UNKNOWN', lattice: String(d.lattice) })
  if (!POSTINGS.includes(d.posting)) problems.push({ code: 'DOMAIN_POSTING_UNKNOWN', posting: String(d.posting) })
  for (const axis of ['horizontal', 'vertical']) {
    const u = d.authoringUnits && d.authoringUnits[axis]
    if (!Object.hasOwn(AUTHORING_UNITS, String(u))) problems.push({ code: 'DOMAIN_UNIT_UNKNOWN', axis, unit: String(u) })
  }

  const r = d.resolution || {}
  if (!RESOLUTION_MODES.includes(r.mode)) problems.push({ code: 'DOMAIN_MODE_UNKNOWN', mode: String(r.mode) })
  if (r.mode === 'explicit-samples') {
    const c = r.sampleCount || {}
    // >= 2 on each axis: one sample is a point, and a 1-wide raster has no spacing to speak of.
    if (!Number.isInteger(c.columns) || c.columns < MIN_SAMPLES || !Number.isInteger(c.rows) || c.rows < MIN_SAMPLES) {
      problems.push({ code: 'DOMAIN_SAMPLES_INVALID', columns: String(c.columns), rows: String(c.rows), min: MIN_SAMPLES })
    }
  } else if (r.mode === 'spacing') {
    const s = r.requestedSpacingM || {}
    if (!finitePositive(s.x) || !finitePositive(s.y)) {
      problems.push({ code: 'DOMAIN_SPACING_INVALID', x: String(s.x), y: String(s.y) })
    }
  }
  const a = r.actualSpacingM || {}
  if (!finitePositive(a.x) || !finitePositive(a.y)) {
    problems.push({ code: 'DOMAIN_SPACING_INVALID', which: 'actual', x: String(a.x), y: String(a.y) })
  }

  const v = d.vertical || {}
  const range = v.rangeM || {}
  if (!Number.isFinite(range.min) || !Number.isFinite(range.max) || !(range.min < range.max)) {
    problems.push({ code: 'DOMAIN_VERTICAL_INVALID', min: String(range.min), max: String(range.max) })
  }
  if (!v.datum || !DATUM_KINDS.includes(v.datum.kind)) {
    problems.push({ code: 'DOMAIN_DATUM_UNKNOWN', kind: String(v.datum && v.datum.kind) })
  }
  return problems
}

/**
 * Derive sample counts and ACTUAL spacing from a requested resolution.
 *
 * The honesty rule lives here. In spacing mode the sample count must be an integer, so the spacing
 * that results is almost never the spacing requested — `deriveResolution` returns what the world
 * will actually have, and `requestedSpacingM` is retained separately so the UI can show both. A
 * dialog that displays the requested number as though it were achieved is the specific failure
 * ADR-007 names.
 *
 * Vertex posting spans (n-1) intervals across the extent; legacy-cell spans n. That single term is
 * the difference between reproducing current output and shifting every sample by half a cell.
 */
export function deriveResolution(domain) {
  const ex = domain.extentM, r = domain.resolution, posting = domain.posting
  const intervals = n => (posting === 'vertex' ? n - 1 : n)
  if (r.mode === 'explicit-samples') {
    const c = r.sampleCount
    return {
      sampleCount: { columns: c.columns, rows: c.rows },
      actualSpacingM: { x: ex.width / intervals(c.columns), y: ex.height / intervals(c.rows) },
    }
  }
  const s = r.requestedSpacingM
  // round, not floor: the nearest achievable spacing beats a systematically coarser one.
  const columns = Math.max(MIN_SAMPLES, Math.round(ex.width / s.x) + (posting === 'vertex' ? 1 : 0))
  const rows = Math.max(MIN_SAMPLES, Math.round(ex.height / s.y) + (posting === 'vertex' ? 1 : 0))
  return {
    sampleCount: { columns, rows },
    actualSpacingM: { x: ex.width / intervals(columns), y: ex.height / intervals(rows) },
  }
}

/** True when the achieved spacing differs from what was asked for — the UI must say so. */
export function spacingWasRounded(domain, tolerance = 1e-9) {
  if (!domain.resolution || domain.resolution.mode !== 'spacing') return false
  const want = domain.resolution.requestedSpacingM, got = domain.resolution.actualSpacingM
  return Math.abs(want.x - got.x) > tolerance || Math.abs(want.y - got.y) > tolerance
}

/**
 * Build WorldDomain/1 from a legacy document, preserving numerical output exactly.
 *
 * `terrainDef.scale` is one metre extent used for BOTH axes, and the row count is the lattice's
 * own: RES on square, round(RES*2/sqrt(3)) on hex. posting is 'legacy-cell' because that is what
 * the current evaluator does — spacing is scale/RES, spanning n cells rather than n-1 intervals.
 */
export function domainFromLegacy(terrainDef, res, latticeRows) {
  const scale = Number.isFinite(terrainDef.scale) && terrainDef.scale > 0 ? terrainDef.scale : 5000
  const hex = terrainDef.lattice === 'hex'
  const rows = latticeRows != null ? latticeRows : (hex ? Math.round(res * 2 / Math.sqrt(3)) : res)
  const height = Number.isFinite(terrainDef.height) ? terrainDef.height : 2600
  const base = Number.isFinite(terrainDef.baseElevation) ? terrainDef.baseElevation : 0
  return {
    version: WORLD_DOMAIN_VERSION,
    originM: { x: 0, y: 0 },
    // The hex world is truthfully rectangular: rows sit sqrt(3)/2 apart, so its metre height is
    // not `scale`. Recording it as `scale` would be the silent metric anisotropy the lattice
    // chapter flags as its first bug.
    extentM: { width: scale, height: hex ? scale * (Math.sqrt(3) / 2) * (rows / res) : scale },
    authoringUnits: { horizontal: 'm', vertical: 'm' },
    lattice: hex ? 'hex-pointy-odd-r' : 'square',
    posting: 'legacy-cell',
    resolution: {
      mode: 'explicit-samples',
      sampleCount: { columns: res, rows },
      actualSpacingM: { x: scale / res, y: scale / res },
    },
    vertical: {
      // Unknown is recorded AS unknown. The legacy build never knew whether baseElevation was
      // relative to sea level, and inventing a datum here would make a guess look like a survey.
      datum: { kind: 'unknown', offsetM: base },
      rangeM: { min: base, max: base + height },
    },
  }
}
