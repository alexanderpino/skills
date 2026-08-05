// Authored water sources and river guides — S4.3.
//
// Pure and DOM-free, like hydrology.js and water-conflict.js: it never imports legacy.js — and it
// imports nothing at all, so an oracle can load a patched copy of this file from a `data:` URL with
// no specifier rewriting and check the arithmetic under plain node.
//
// THE WHOLE IDEA IN ONE SENTENCE: a source is an extra term in the supply array, and nothing else
// changes. `03:673-676` writes it out:
//
//     Q[c] = localRain[c] * cellArea      # distributed source — the precip field
//          + pointSource[c]               # springs, authored inflows (m3/s injected at c)
//     # accumulate Q downstream with the SAME stack as A — sources just seed the accumulation
//
// There is no new router here, no second accumulation, no special case inside `mfdAccumulate`. This
// module produces the `pointSource[c]` term; `hydrology.js` pushes it downhill with exactly the
// weights it uses for drainage area. That is why `combineSupply` is a two-line add and why this file
// does NOT own the mm/yr -> m3/s conversion: `precipToSupply` already does, both of its factors are
// armed by the S4.2 gate, and a second copy here is a second place for them to drift.
//
// A SOURCE IS NOT A BUMP IN THE HEIGHT FIELD. `03:702-707`, verbatim: "A spring is not a bump in the
// height field — it is a source term in the flow field. Place it as discharge and let routing and
// erosion carve the valley below it... Stamp a riverbed into the height instead and you get a
// channel that ignores the hydrology and stops where you stopped drawing." Nothing in this module
// writes to the surface it is handed; the routing surface is read for one thing only — reporting the
// elevation each source sits at — and `_verify_water_sources.js` compares the caller's array bitwise
// before and after with a stamp armed as the mutation.
//
// SALINITY IS NOT HERE, deliberately. S4.3 says so in as many words: it stays a proposed registry
// extension in `BACKLOG §2` until a separate decision fixes its unit, its advection and its export
// contract. A field carried but never advected would be worse than its absence, because downstream
// nodes would read a number that means nothing.

/** Bumped when the serialized shape changes. `migrateWaterFeatures` is the only reader of it. */
export const WATER_FEATURE_SCHEMA_VERSION = 1
export const WATER_FEATURE_DOC_KIND = 'terrain-studio-water-features'

/**
 * The source kinds, exactly the corpus enum at `03:687-694` and in its order.
 *
 * This is a CLOSED set on purpose. An unrecognised kind is refused rather than passed through as a
 * free-form label, because every kind here carries a placement rule a downstream story can act on —
 * boundary inflow arrives at an edge, distributed rain covers a footprint, glacial melt will couple
 * to S5's snow field — and a kind nothing knows about is a promise the app cannot keep.
 */
export const SOURCE_KINDS = Object.freeze([
  'distributedRain', 'boundaryInflow', 'spring', 'karstResurgence', 'oasis', 'glacialSnowmelt',
])

/** Corpus wording, for the inspector. Kept beside the enum so a kind cannot be added without one. */
export const SOURCE_KIND_LABEL = Object.freeze({
  distributedRain: 'Distributed rain',
  boundaryInflow: 'Boundary inflow (river entering off-map)',
  spring: 'Spring',
  karstResurgence: 'Karst resurgence',
  oasis: 'Oasis / desert spring',
  glacialSnowmelt: 'Glacial / snowmelt',
})

/**
 * What a guide asserts. TWO members, and the shortness is the point.
 *
 * The plan is explicit that "guide control points are two-dimensional intent" and that "guides
 * constrain intent, not elevation". Both values below are CONSUMED today — `channel` is what S4.6's
 * conflict analyser measures a route against and what `includeGuideTargets` seeds flow from,
 * `reference` is the explicit opt-out that does neither. An intent nothing reads would be a taxonomy
 * rather than a feature, and the author would have no way to tell which of the two they had.
 */
export const GUIDE_INTENTS = Object.freeze(['channel', 'reference'])

/** A hex row is sqrt(3)/2 of a column. Same constant as hydrology.js and water-conflict.js. */
const HEX_ROW = Math.sqrt(3) / 2

/** Stable IDs are authored, printable and safe in a file name and a URL fragment. */
const ID_RE = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$/

export const WATER_FEATURE_ERROR_CODES = Object.freeze([
  'FEATURE_SHAPE', 'ID_INVALID', 'ID_DUPLICATE', 'KIND_UNKNOWN', 'INTENT_UNKNOWN',
  'COORD_INVALID', 'DISCHARGE_INVALID', 'TEMPERATURE_INVALID', 'RADIUS_INVALID',
  'POINTS_INVALID', 'ENABLED_INVALID', 'SOURCE_OFF_DOMAIN', 'BOUNDARY_NOT_ON_EDGE',
  'SUPPLY_SHAPE', 'TEXT_SYNTAX', 'SCHEMA_VERSION', 'DOC_KIND',
])

export class WaterFeatureError extends Error {
  constructor(code, message, detail) {
    super(message)
    this.name = 'WaterFeatureError'
    this.code = code
    this.detail = detail
  }
}

const fail = (code, message, detail) => { throw new WaterFeatureError(code, message, detail) }

/** Codepoint order. Deterministic serialization needs ONE ordering and this is it; locale-aware
 *  comparison is not, because it depends on where the machine thinks it is. */
const byId = (a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)

const firstDefined = (...vals) => { for (const v of vals) if (v !== undefined && v !== null) return v; return undefined }

/**
 * Validate and freeze one water source.
 *
 * `id` HAS NO FALLBACK. Minting one from the array index would make every id positional, so deleting
 * the first source would silently rename all the others — and every downstream reference, every undo
 * record and every saved document would then point at a different object than it did before. That is
 * exactly the failure "stable IDs" exists to prevent, so an unnamed source is refused. `mintFeatureId`
 * is how an editor gets a fresh one.
 */
export function normalizeSource(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    fail('FEATURE_SHAPE', 'a water source must be an object', { got: Array.isArray(raw) ? 'array' : typeof raw })
  }
  const id = raw.id
  if (typeof id !== 'string' || !ID_RE.test(id)) {
    fail('ID_INVALID', `water source id ${JSON.stringify(id)} must be an authored string matching ${ID_RE}`, { id })
  }
  const kind = raw.kind
  if (!SOURCE_KINDS.includes(kind)) {
    fail('KIND_UNKNOWN', `${id}: unknown source kind ${JSON.stringify(kind)} — expected one of ${SOURCE_KINDS.join(', ')}`, { id, kind })
  }
  const xM = Number(firstDefined(raw.xM, raw.x))
  const zM = Number(firstDefined(raw.zM, raw.z))
  if (!Number.isFinite(xM) || !Number.isFinite(zM)) {
    fail('COORD_INVALID', `${id}: a source needs finite world-metre x and z`, { id, xM, zM })
  }
  const dischargeM3PerS = Number(firstDefined(raw.dischargeM3PerS, raw.discharge, raw.q))
  if (!Number.isFinite(dischargeM3PerS)) {
    fail('DISCHARGE_INVALID', `${id}: discharge must be a finite number of m3/s`, { id, dischargeM3PerS })
  }
  // NEGATIVE DISCHARGE IS REFUSED, and a sink is not what it would mean. `03:709-711` describes a
  // sink as a cell that terminates accumulation and that depression handling must leave unfilled —
  // a routing rule, not a negative seed. Subtracting water from the supply array instead would let a
  // reach carry a negative discharge downstream of the sink, and every consumer of `Q` (channel
  // width goes as Q^0.5, stream power as Q^m) would then take a root or a power of a negative number.
  if (dischargeM3PerS < 0) {
    fail('DISCHARGE_INVALID', `${id}: discharge ${dischargeM3PerS} m3/s is negative — a sink is a routing rule, not a negative source; see 03:709-711`, { id, dischargeM3PerS })
  }
  const radiusM = Number(firstDefined(raw.radiusM, raw.radius, 0))
  if (!Number.isFinite(radiusM) || radiusM < 0) {
    fail('RADIUS_INVALID', `${id}: footprint radius must be a finite number of metres >= 0`, { id, radiusM })
  }
  // Distributed rain is distributed BY DEFINITION — `03:689` places it as `localRain = precip` per
  // cell, over an area. A point of "distributed rain" is a contradiction the author cannot see in
  // the result, because one cell of injected discharge looks exactly like a spring.
  if (kind === 'distributedRain' && !(radiusM > 0)) {
    fail('RADIUS_INVALID', `${id}: a distributedRain source needs a footprint radius > 0 — a point of distributed rain is a spring`, { id, radiusM })
  }
  const tRaw = firstDefined(raw.temperatureC, raw.temperature)
  let temperatureC = null
  if (tRaw !== undefined) {
    temperatureC = Number(tRaw)
    if (!Number.isFinite(temperatureC)) {
      fail('TEMPERATURE_INVALID', `${id}: temperature must be a finite number of degrees C or absent`, { id, temperatureC: tRaw })
    }
  }
  let enabled = true
  if (raw.enabled !== undefined) {
    if (typeof raw.enabled !== 'boolean') {
      fail('ENABLED_INVALID', `${id}: enabled must be a boolean, not ${JSON.stringify(raw.enabled)}`, { id, enabled: raw.enabled })
    }
    enabled = raw.enabled
  }
  return Object.freeze({
    feature: 'waterSource', id, kind, xM, zM, dischargeM3PerS, radiusM, temperatureC, enabled,
  })
}

/**
 * Validate and freeze one river guide.
 *
 * Control points carry NO ELEVATION. The plan: "Guide control points are two-dimensional intent;
 * elevation comes only from sampling `routingSurface`." Accepting a y per point here would let an
 * author declare a river's height, which is the authority this whole sprint refuses to hand over —
 * S4.6 measures the guide against the surface and reports the disagreement instead.
 *
 * The record shape is `{ id, points: [{x, z}, ...] }`, which is what `water_conflict.js` already
 * reads out of its guides port, and a one-point record is deliberately NOT a guide: that file drops
 * anything with fewer than two points, so a point source travelling on the same feature set can
 * never be analysed as a degenerate line.
 */
export function normalizeGuide(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    fail('FEATURE_SHAPE', 'a river guide must be an object', { got: Array.isArray(raw) ? 'array' : typeof raw })
  }
  const id = raw.id
  if (typeof id !== 'string' || !ID_RE.test(id)) {
    fail('ID_INVALID', `river guide id ${JSON.stringify(id)} must be an authored string matching ${ID_RE}`, { id })
  }
  const intent = raw.intent
  if (!GUIDE_INTENTS.includes(intent)) {
    fail('INTENT_UNKNOWN', `${id}: unknown guide intent ${JSON.stringify(intent)} — expected one of ${GUIDE_INTENTS.join(', ')}`, { id, intent })
  }
  const src = Array.isArray(raw.points) ? raw.points : null
  if (!src || src.length < 2) {
    fail('POINTS_INVALID', `${id}: a guide needs at least two ordered control points — a single point is a source, not a line`, { id, points: src ? src.length : 0 })
  }
  const points = []
  for (let i = 0; i < src.length; i++) {
    const p = src[i]
    const x = Number(Array.isArray(p) ? p[0] : (p && firstDefined(p.x, p.xM)))
    const z = Number(Array.isArray(p) ? p[1] : (p && firstDefined(p.z, p.zM)))
    if (!Number.isFinite(x) || !Number.isFinite(z)) {
      fail('POINTS_INVALID', `${id}: control point ${i} needs finite world-metre x and z`, { id, index: i, point: p })
    }
    points.push(Object.freeze({ x, z }))
  }
  let lengthM = 0
  for (let i = 1; i < points.length; i++) lengthM += Math.hypot(points[i].x - points[i - 1].x, points[i].z - points[i - 1].z)
  // A zero-length guide is not a guide with no conflict; it is no guide at all. water-conflict.js
  // refuses it for the same reason, and reporting a clean result for one would be absence of
  // evidence dressed up as a pass.
  if (!(lengthM > 0)) fail('POINTS_INVALID', `${id}: guide has zero length — every control point is the same place`, { id, lengthM })

  const tf = firstDefined(raw.targetFlowM3PerS, raw.targetFlow, raw.q)
  let targetFlowM3PerS = null
  if (tf !== undefined) {
    targetFlowM3PerS = Number(tf)
    if (!Number.isFinite(targetFlowM3PerS) || targetFlowM3PerS < 0) {
      fail('DISCHARGE_INVALID', `${id}: target flow must be a finite number of m3/s >= 0 or absent`, { id, targetFlowM3PerS: tf })
    }
  }
  return Object.freeze({
    feature: 'riverGuide', id, intent, points: Object.freeze(points), targetFlowM3PerS, lengthM,
  })
}

/**
 * Normalize a whole feature set: `{ sources, guides }`, or a flat array of mixed records.
 *
 * IDs are unique across BOTH lists, not within each. They are document-wide handles — an undo record,
 * a copy/paste buffer and a saved reference all name a feature by id alone — and a guide sharing an
 * id with a source would make every one of those ambiguous.
 *
 * Both lists come back sorted by id. That is what makes serialization deterministic, and it means the
 * order an editor happens to hold features in can never reach the file.
 */
export function normalizeWaterFeatures(raw) {
  let rawSources = [], rawGuides = []
  if (raw == null) { /* an empty document is a legal document */ }
  else if (Array.isArray(raw)) {
    for (const r of raw) {
      if (r && (r.feature === 'riverGuide' || Array.isArray(r.points))) rawGuides.push(r)
      else rawSources.push(r)
    }
  } else if (typeof raw === 'object') {
    if (raw.sources !== undefined && !Array.isArray(raw.sources)) fail('FEATURE_SHAPE', 'sources must be an array', { got: typeof raw.sources })
    if (raw.guides !== undefined && !Array.isArray(raw.guides)) fail('FEATURE_SHAPE', 'guides must be an array', { got: typeof raw.guides })
    rawSources = raw.sources || []
    rawGuides = raw.guides || []
  } else {
    fail('FEATURE_SHAPE', 'a water feature set must be an object or an array', { got: typeof raw })
  }

  const sources = rawSources.map(normalizeSource).sort(byId)
  const guides = rawGuides.map(normalizeGuide).sort(byId)
  const seen = new Set()
  for (const f of [...sources, ...guides]) {
    if (seen.has(f.id)) fail('ID_DUPLICATE', `feature id ${JSON.stringify(f.id)} appears more than once — ids are document-wide handles`, { id: f.id })
    seen.add(f.id)
  }
  return Object.freeze({
    schemaVersion: WATER_FEATURE_SCHEMA_VERSION,
    sources: Object.freeze(sources),
    guides: Object.freeze(guides),
  })
}

/** Every id in a set, for `mintFeatureId`. */
export function featureIds(features) {
  const set = normalizeWaterFeatures(features)
  return [...set.sources, ...set.guides].map(f => f.id)
}

/**
 * A fresh id derived from `base`, deterministic given the same taken set.
 *
 * `base`, then `base-2`, `base-3`... — not a random suffix and not a timestamp, because two authors
 * pasting the same feature into the same document must produce the same file, and a document whose
 * bytes depend on the clock cannot be diffed or compared.
 */
export function mintFeatureId(base, taken = []) {
  const takenSet = taken instanceof Set ? taken : new Set(taken)
  let stem = String(base || '').replace(/[^A-Za-z0-9_.:-]/g, '')
  if (!stem || !/^[A-Za-z0-9]/.test(stem)) stem = 'feature' + stem
  stem = stem.slice(0, 56)
  if (!takenSet.has(stem)) return stem
  for (let n = 2; n < 100000; n++) {
    const candidate = `${stem}-${n}`
    if (!takenSet.has(candidate)) return candidate
  }
  fail('ID_INVALID', `could not mint an id from ${JSON.stringify(base)}`, { base })
}

/**
 * Copy/paste. The copy is identical in every property EXCEPT the id, which is fresh.
 *
 * A paste that kept the id would produce two features answering to one handle: the second would be
 * refused by the duplicate check on save, or — worse, if the check were ever relaxed — would silently
 * shadow the first everywhere a feature is looked up by id.
 */
export function duplicateFeature(record, taken = []) {
  const isGuide = record && (record.feature === 'riverGuide' || Array.isArray(record.points))
  const normalized = isGuide ? normalizeGuide(record) : normalizeSource(record)
  const takenSet = taken instanceof Set ? new Set(taken) : new Set(taken)
  takenSet.add(normalized.id)
  const id = mintFeatureId(normalized.id, takenSet)
  return isGuide
    ? normalizeGuide({ ...normalized, id, points: normalized.points.map(p => ({ x: p.x, z: p.z })) })
    : normalizeSource({ ...normalized, id })
}

/** Move a source. Everything else — id, kind, discharge, temperature, footprint — is carried over
 *  unchanged, which is the property "only the downstream flow cone changes" rests on. */
export function moveSource(record, xM, zM) {
  const s = normalizeSource(record)
  return normalizeSource({ ...s, xM, zM })
}

// --- serialization ------------------------------------------------------------------------------

/**
 * The canonical document. Explicit key order, sorted lists, `null` written out rather than omitted.
 *
 * An absent optional field and a field that is known to be absent are the SAME representation here,
 * on purpose: `temperatureC: null` says "this source has no authored temperature", where omitting the
 * key would leave a reader unable to tell that from "this file predates temperatures".
 */
export function canonicalWaterFeatures(features) {
  const set = normalizeWaterFeatures(features)
  return {
    kind: WATER_FEATURE_DOC_KIND,
    schemaVersion: WATER_FEATURE_SCHEMA_VERSION,
    sources: set.sources.map(s => ({
      id: s.id, kind: s.kind, xM: s.xM, zM: s.zM,
      dischargeM3PerS: s.dischargeM3PerS, radiusM: s.radiusM,
      temperatureC: s.temperatureC, enabled: s.enabled,
    })),
    guides: set.guides.map(g => ({
      id: g.id, intent: g.intent, targetFlowM3PerS: g.targetFlowM3PerS,
      points: g.points.map(p => [p.x, p.z]),
    })),
  }
}

/** Canonical text. The trailing newline is part of the format, as in project.js. */
export function serializeWaterFeatures(features) {
  return JSON.stringify(canonicalWaterFeatures(features), null, 2) + '\n'
}

/**
 * Upgrade a stored document to the current schema.
 *
 * A document with NO `schemaVersion` is the pre-S4.3 shape and migrates forward. A document from a
 * FUTURE version is refused rather than best-effort read: silently ignoring fields a later build
 * added would load a river network that is missing pieces the author cannot see are missing.
 */
export function migrateWaterFeatures(doc) {
  if (!doc || typeof doc !== 'object' || Array.isArray(doc)) fail('FEATURE_SHAPE', 'a water feature document must be an object', { got: typeof doc })
  const version = doc.schemaVersion === undefined ? 0 : doc.schemaVersion
  if (!Number.isInteger(version) || version < 0) fail('SCHEMA_VERSION', `schemaVersion must be a non-negative integer, got ${JSON.stringify(doc.schemaVersion)}`, { version: doc.schemaVersion })
  if (version > WATER_FEATURE_SCHEMA_VERSION) {
    fail('SCHEMA_VERSION', `document schema ${version} is newer than this build understands (${WATER_FEATURE_SCHEMA_VERSION})`, { version })
  }
  if (doc.kind !== undefined && doc.kind !== WATER_FEATURE_DOC_KIND) {
    fail('DOC_KIND', `not a water feature document (kind=${JSON.stringify(doc.kind)})`, { kind: doc.kind })
  }
  // v0 -> v1 is a pure re-read: the v0 shape carried the same fields under the same names, without a
  // version stamp. `normalizeWaterFeatures` supplies every default and refuses anything it cannot.
  return normalizeWaterFeatures({ sources: doc.sources, guides: doc.guides })
}

/** Parse canonical text back into a normalized set. Round-trips byte-for-byte with serialize. */
export function parseWaterFeatures(text) {
  let raw
  try { raw = JSON.parse(String(text)) }
  catch (e) { fail('FEATURE_SHAPE', `not valid water feature JSON: ${e.message}`, { message: e.message }) }
  return migrateWaterFeatures(raw)
}

/**
 * The authoring text block, so the node is drivable before a spline editor exists.
 *
 * One record per line. `key=value` tokens in any order; a bare `x,z` token is a guide control point.
 *
 *   source id=nileHead kind=spring x=200 z=320 q=1200 t=24
 *   guide  id=nileCourse intent=channel q=1200 200,320 500,330 900,340
 *
 * An UNKNOWN KEY IS AN ERROR, with its line number. Ignoring it would let `dischage=1200` read as a
 * source with no discharge at all, and the author would see an empty river and blame the routing.
 */
export function parseFeatureText(text) {
  const sources = [], guides = []
  const lines = String(text == null ? '' : text).split('\n')
  const SOURCE_KEYS = { id: 'id', kind: 'kind', x: 'xM', z: 'zM', q: 'dischargeM3PerS', t: 'temperatureC', r: 'radiusM', on: 'enabled' }
  const GUIDE_KEYS = { id: 'id', intent: 'intent', q: 'targetFlowM3PerS' }
  for (let ln = 0; ln < lines.length; ln++) {
    const body = lines[ln].split('#')[0].trim()
    if (!body) continue
    const tokens = body.split(/\s+/)
    const head = tokens[0].toLowerCase()
    const at = `line ${ln + 1}`
    if (head !== 'source' && head !== 'guide') {
      fail('TEXT_SYNTAX', `${at}: a record must start with "source" or "guide", not ${JSON.stringify(tokens[0])}`, { line: ln + 1 })
    }
    const keys = head === 'source' ? SOURCE_KEYS : GUIDE_KEYS
    const rec = {}
    const points = []
    for (let i = 1; i < tokens.length; i++) {
      const tok = tokens[i]
      const eq = tok.indexOf('=')
      if (eq < 0) {
        if (head !== 'guide' || tok.indexOf(',') < 0) {
          fail('TEXT_SYNTAX', `${at}: ${JSON.stringify(tok)} is neither a key=value nor a guide "x,z" control point`, { line: ln + 1, token: tok })
        }
        const parts = tok.split(',')
        const x = Number(parts[0]), z = Number(parts[1])
        if (parts.length !== 2 || !Number.isFinite(x) || !Number.isFinite(z)) {
          fail('TEXT_SYNTAX', `${at}: control point ${JSON.stringify(tok)} must be two finite numbers "x,z"`, { line: ln + 1, token: tok })
        }
        points.push({ x, z })
        continue
      }
      const key = tok.slice(0, eq), value = tok.slice(eq + 1)
      const field = keys[key]
      if (!field) {
        fail('TEXT_SYNTAX', `${at}: unknown ${head} key ${JSON.stringify(key)} — expected one of ${Object.keys(keys).join(', ')}`, { line: ln + 1, key })
      }
      if (field === 'enabled') {
        if (value !== 'true' && value !== 'false') fail('TEXT_SYNTAX', `${at}: on= must be true or false, not ${JSON.stringify(value)}`, { line: ln + 1, value })
        rec.enabled = value === 'true'
      } else if (field === 'id' || field === 'kind' || field === 'intent') {
        rec[field] = value
      } else {
        const n = Number(value)
        if (!Number.isFinite(n)) fail('TEXT_SYNTAX', `${at}: ${key}=${JSON.stringify(value)} is not a finite number`, { line: ln + 1, key, value })
        rec[field] = n
      }
    }
    if (head === 'guide') { rec.points = points; guides.push(rec) } else sources.push(rec)
  }
  return { sources, guides }
}

// --- placement ----------------------------------------------------------------------------------

/** World-metre centre of a lattice cell. Odd hex rows are shifted half a column. */
export function cellCentre(col, row, { cellSizeM, hex = false } = {}) {
  return {
    x: col * cellSizeM + (hex && (row & 1) ? 0.5 * cellSizeM : 0),
    z: row * cellSizeM * (hex ? HEX_ROW : 1),
  }
}

/**
 * Which cell a world-metre position falls in.
 *
 * The row is resolved FIRST because on a pointy-odd-r hex lattice the column offset depends on it;
 * using one offset for both rows shears every odd row by half a cell. `inDomain` is decided on the
 * continuous coordinate — a point up to half a cell outside the outermost centre is still inside the
 * lattice footprint — so a source nudged one metre past the edge does not silently become an edge cell.
 */
export function cellOfWorld(xM, zM, w, hgt, { cellSizeM, hex = false } = {}) {
  const rowPitch = cellSizeM * (hex ? HEX_ROW : 1)
  const v = zM / rowPitch
  const row = Math.round(v) || 0
  const off = hex && (row & 1) ? 0.5 : 0
  const u = xM / cellSizeM - off
  const col = Math.round(u) || 0
  const inDomain = v >= -0.5 && v <= hgt - 0.5 && u >= -0.5 && u <= w - 0.5
    && row >= 0 && row < hgt && col >= 0 && col < w
  return { col, row, index: row * w + col, inDomain, u, v }
}

const onEdge = (col, row, w, hgt) => col === 0 || row === 0 || col === w - 1 || row === hgt - 1

/**
 * The `pointSource[c]` term: authored discharge, in m3/s, injected at the cells each feature covers.
 *
 * `surface` is READ ONLY and comes back bitwise identical. It is read for exactly one thing — the
 * elevation to report each source at — and the oracle arms a stamp against that access.
 *
 * A source whose footprint straddles the domain edge keeps its whole discharge: the in-domain cells
 * split it evenly. The alternative — dropping the outside share — would make a river's flow depend on
 * how close its spring sits to the map border, which is the sort of quiet non-conservation
 * `03:691` warns about ("Real water arriving — conserve it").
 *
 * A source that lands OFF the domain entirely is refused rather than contributing nothing. A silent
 * zero is indistinguishable from a source that is working, and the author would be looking for a
 * river that no code ever intended to produce.
 */
export function sourceSupply(surface, w, hgt, features, {
  cellSizeM, hex = false, includeGuideTargets = false,
} = {}) {
  if (!Number.isInteger(w) || w <= 0 || !Number.isInteger(hgt) || hgt <= 0) {
    fail('SUPPLY_SHAPE', `sourceSupply: w and hgt must be positive integers (got ${w}x${hgt})`, { w, hgt })
  }
  if (!Number.isFinite(cellSizeM) || cellSizeM <= 0) {
    fail('SUPPLY_SHAPE', 'sourceSupply: cellSizeM must be a positive number of metres', { cellSizeM })
  }
  const N = w * hgt
  if (!surface || surface.length !== N) {
    fail('SUPPLY_SHAPE', `sourceSupply: surface has ${surface ? surface.length : 0} samples, expected ${N}`, { got: surface ? surface.length : 0, want: N })
  }
  const set = normalizeWaterFeatures(features)
  const supply = new Float64Array(N)
  const placements = []
  let totalQM3PerS = 0, seededCount = 0, guideSeededCount = 0

  const seeds = []
  for (const s of set.sources) {
    seeds.push({
      id: s.id, feature: 'waterSource', kind: s.kind, xM: s.xM, zM: s.zM,
      q: s.dischargeM3PerS, radiusM: s.radiusM, temperatureC: s.temperatureC,
      enabled: s.enabled, requireEdge: s.kind === 'boundaryInflow',
    })
  }
  // GUIDE TARGET FLOW IS OPT-IN, and `reference` guides never seed whatever the flag says. A guide is
  // a statement about where a river should run; turning that into water out of nowhere is a second,
  // much larger claim, and it must be one the author made on purpose.
  if (includeGuideTargets) {
    for (const g of set.guides) {
      if (g.intent !== 'channel') continue
      if (g.targetFlowM3PerS == null) continue
      // THE HEAD, which is `points[0]`. Seeding the tail would put the river's water at its mouth, so
      // the reach the author drew would carry nothing and the flow would appear from the last vertex.
      seeds.push({
        id: g.id, feature: 'riverGuide', kind: 'channelGuide',
        xM: g.points[0].x, zM: g.points[0].z,
        q: g.targetFlowM3PerS, radiusM: 0, temperatureC: null, enabled: true, requireEdge: false,
      })
    }
  }

  for (const seed of seeds) {
    const home = cellOfWorld(seed.xM, seed.zM, w, hgt, { cellSizeM, hex })
    if (!home.inDomain) {
      fail('SOURCE_OFF_DOMAIN', `${seed.id}: world position (${seed.xM}, ${seed.zM}) m is outside the ${w}x${hgt} domain`, { id: seed.id, xM: seed.xM, zM: seed.zM, w, hgt })
    }
    if (seed.requireEdge && !onEdge(home.col, home.row, w, hgt)) {
      fail('BOUNDARY_NOT_ON_EDGE', `${seed.id}: a boundaryInflow is a river entering off-map and must sit on a domain edge cell, not (${home.col}, ${home.row}) — see 03:691`, { id: seed.id, col: home.col, row: home.row, w, hgt })
    }
    if (!seed.enabled) {
      placements.push(Object.freeze({
        id: seed.id, feature: seed.feature, kind: seed.kind, enabled: false,
        xM: seed.xM, zM: seed.zM, radiusM: seed.radiusM, col: home.col, row: home.row,
        index: home.index, cells: Object.freeze([]), qM3PerS: 0, qPerCellM3PerS: 0,
        temperatureC: seed.temperatureC, surfaceValue: surface[home.index],
      }))
      continue
    }
    const cells = footprintCells(home, seed.radiusM, w, hgt, cellSizeM, hex)
    const each = seed.q / cells.length
    for (let k = 0; k < cells.length; k++) {
      const ci = cells[k]
      supply[ci] += each
    }
    totalQM3PerS += seed.q
    seededCount++
    if (seed.feature === 'riverGuide') guideSeededCount++
    placements.push(Object.freeze({
      id: seed.id, feature: seed.feature, kind: seed.kind, enabled: true,
      xM: seed.xM, zM: seed.zM, radiusM: seed.radiusM, col: home.col, row: home.row,
      index: home.index, cells: Object.freeze(cells.slice()), qM3PerS: seed.q, qPerCellM3PerS: each,
      temperatureC: seed.temperatureC, surfaceValue: surface[home.index],
    }))
  }

  return {
    supply, placements: Object.freeze(placements),
    totalQM3PerS, seededCount, guideSeededCount,
    sourceCount: set.sources.length, guideCount: set.guides.length,
  }
}

/** Row-major list of cells whose CENTRE lies within `radiusM` of the seed, never empty: a radius
 *  smaller than a cell falls back to the cell the point is in, so a small footprint is a point source
 *  rather than a source that vanished. */
function footprintCells(home, radiusM, w, hgt, cellSizeM, hex) {
  if (!(radiusM > 0)) return [home.index]
  const rowPitch = cellSizeM * (hex ? HEX_ROW : 1)
  const r0 = Math.max(0, Math.floor((home.row * rowPitch - radiusM) / rowPitch))
  const r1 = Math.min(hgt - 1, Math.ceil((home.row * rowPitch + radiusM) / rowPitch))
  const centre = cellCentre(home.col, home.row, { cellSizeM, hex })
  const out = []
  for (let row = r0; row <= r1; row++) {
    const off = hex && (row & 1) ? 0.5 : 0
    const c0 = Math.max(0, Math.floor((centre.x - radiusM) / cellSizeM - off))
    const c1 = Math.min(w - 1, Math.ceil((centre.x + radiusM) / cellSizeM - off))
    for (let col = c0; col <= c1; col++) {
      const p = cellCentre(col, row, { cellSizeM, hex })
      if (Math.hypot(p.x - centre.x, p.z - centre.z) <= radiusM) out.push(row * w + col)
    }
  }
  return out.length ? out : [home.index]
}

/**
 * Add two supply arrays. That is the entire coupling between rain and sources.
 *
 * It is a separate two-line function rather than a parameter of `sourceSupply` because the mm/yr ->
 * m3/s conversion belongs to `precipToSupply` in hydrology.js, where both of its factors are already
 * armed by the S4.2 gate. Re-deriving them here would put the same physics in two files, and the
 * copy that is wrong is always the one nobody is looking at.
 */
export function combineSupply(a, b) {
  if (!a || !b || a.length !== b.length) {
    fail('SUPPLY_SHAPE', `combineSupply: length mismatch (${a ? a.length : 0} vs ${b ? b.length : 0})`, { a: a ? a.length : 0, b: b ? b.length : 0 })
  }
  const out = new Float64Array(a.length)
  for (let i = 0; i < a.length; i++) out[i] = a[i] + b[i]
  return out
}

/**
 * The records for the two `featureSet` ports.
 *
 * A record is the normalized feature plus the two derived fields a reader wants (`kindLabel`,
 * `analyze`) — NOT a reshaped copy. That matters twice over: `normalizeWaterFeatures` accepts these
 * records back unchanged, so a feature set can be routed through a graph and re-read without a
 * translation layer to drift, and the guide shape is exactly the `{ id, points: [{x, z}, ...] }` that
 * `water_conflict.js` already pulls off its guides port. A point source carries ONE point and no
 * `points` array at all, so the conflict node cannot mistake it for a degenerate line.
 */
export function waterFeatureRecords(features) {
  const set = normalizeWaterFeatures(features)
  return {
    sources: set.sources.map(s => ({
      feature: 'waterSource', id: s.id, kind: s.kind, kindLabel: SOURCE_KIND_LABEL[s.kind],
      xM: s.xM, zM: s.zM, dischargeM3PerS: s.dischargeM3PerS, radiusM: s.radiusM,
      temperatureC: s.temperatureC, enabled: s.enabled,
    })),
    guides: set.guides.map(g => ({
      feature: 'riverGuide', id: g.id, intent: g.intent,
      points: g.points.map(p => ({ x: p.x, z: p.z })),
      targetFlowM3PerS: g.targetFlowM3PerS, lengthM: g.lengthM,
      analyze: g.intent === 'channel',
    })),
  }
}
