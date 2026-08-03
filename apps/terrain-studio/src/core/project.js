// Versioned project document — the save/open format core.
//
// WHY THIS EXISTS
//
// Terrain Studio had no persistence at all: no save, no open, no project file, no schemaVersion,
// no migrate(). localStorage held three UI preferences. Yet S2.2, S8.5, S8.6, S9.1 and S9.6 all
// specify "load v1, save v2, reload, prove idempotence" against a saved-document format that had
// never been written. Those migration gates could not be armed, because there was nothing to
// migrate FROM. This module is that missing v1.
//
// It is deliberately PURE and DOM-FREE:
//   * no import from legacy.js, so it cannot join the legacy<->plugin cycle and cannot trip the
//     module-evaluation TDZ rule that `npm run plugins:tdz` enforces;
//   * no document/window/Blob, so it can be exercised in plain Node as well as in the page.
// legacy.js owns the bindings (nodes, edges, uid, terrainDef, RES, ...) and passes a plain state
// object in and out. That split is what makes the format testable without a browser.
//
// THE NORMAL-FORM RULE, which is the whole reason save->load->save is byte-identical:
// key order here is NORMATIVE, never Object.keys() order. Template graphs in legacy.js replace
// params wholesale (`out.params={norm:"on"}`), so the live app routinely holds nodes missing
// schema keys, and buildProps hydrates them lazily and only for the selected node. Both endpoints
// therefore map into this normal form: the writer emits declared keys in a fixed order, and the
// loader hydrates missing ones from the schema before anything evaluates.

export const PROJECT_KIND = 'terrain-studio-project'
export const PROJECT_SCHEMA_VERSION = 1
export const PROJECT_FILE_EXTENSION = '.tsproj.json'

// Embedded import sources are base64 and inflate ~4/3. A 4096² raw16 is 32 MiB before encoding,
// which is past what belongs in a JSON document; refuse rather than silently emit a file no
// editor can open.
export const PROJECT_SOURCE_BUDGET_BYTES = 24 * 1024 * 1024

export const PROJECT_ERROR_CODES = Object.freeze([
  'BAD_JSON',          // the text is not JSON at all
  'BAD_KIND',          // missing or wrong "kind" literal
  'BAD_VERSION',       // schemaVersion present but not a positive integer
  'FUTURE_VERSION',    // schemaVersion newer than this build understands
  'BAD_SHAPE',         // a required container is missing or the wrong type
  'UNKNOWN_TYPE',      // node.type is not a registered plugin
  'DUPLICATE_NODE_ID', // two nodes share an id
  'BAD_PARAM',         // a param value is non-finite, or undefined/function/symbol
  'EDGE_ENDPOINT',     // an edge names a node id that does not exist
  'EDGE_SLOT_RANGE',   // an edge slot is outside the destination's input arity
  'UID_RANGE',         // uid is not an integer strictly greater than every node id
  'SOURCE_BUDGET',     // an embedded import source exceeds PROJECT_SOURCE_BUDGET_BYTES
  'NO_MIGRATION',      // no migration step registered for a version on the path
  'MIGRATION_VERSION', // a migration step ran but did not stamp the version forward
])

export class ProjectError extends Error {
  constructor(code, message, detail) {
    super(message)
    this.name = 'ProjectError'
    this.code = code
    this.detail = detail
  }
}

const fail = (code, message, detail) => { throw new ProjectError(code, message, detail) }

// The terrain block's key order is createTerrainDef's declaration order. Any key a future build
// adds is emitted after these, sorted, so an unknown key round-trips instead of being dropped.
const TERRAIN_KEY_ORDER = [
  'scale', 'height', 'baseElevation', 'latitude', 'north',
  'seaTemp', 'lapseRate', 'solarElevation', 'windDirection', 'windSpeed',
  'lattice', 'seed',
]

const isPlainObject = value => value !== null && typeof value === 'object' && !Array.isArray(value)

// JSON has no -0, but JS does, and -0 !== 0 under Object.is. Normalising here keeps a value that
// arrived as -0 from producing a document that differs from its own reload.
const normNumber = (value, where) => {
  if (!Number.isFinite(value)) fail('BAD_PARAM', `${where} is not a finite number (got ${String(value)})`, { where, value: String(value) })
  return value === 0 ? 0 : value
}

/**
 * Deep-copy a param value into canonical form.
 * Object keys are sorted by code unit so two documents with the same content are the same bytes.
 * Rejects values JSON would silently corrupt: a non-finite number becomes null and comes back
 * wrong; undefined/function/symbol vanish from the output entirely.
 */
function canonicalValue(value, where) {
  if (value === null) return null
  const t = typeof value
  if (t === 'number') return normNumber(value, where)
  if (t === 'string' || t === 'boolean') return value
  if (t === 'undefined' || t === 'function' || t === 'symbol') {
    fail('BAD_PARAM', `${where} has unserialisable type ${t}`, { where, type: t })
  }
  if (Array.isArray(value)) return value.map((entry, i) => canonicalValue(entry, `${where}[${i}]`))
  if (ArrayBuffer.isView(value)) {
    // A TypedArray through JSON.stringify becomes {"0":123,...} — a 512² raw16 is ~2.7 MB of
    // numeric string keys, and it does not survive the round trip as a TypedArray anyway.
    fail('BAD_PARAM', `${where} is a TypedArray; binary belongs in the node's source channel, not in params`, { where })
  }
  if (isPlainObject(value)) {
    const out = {}
    for (const key of Object.keys(value).sort()) out[key] = canonicalValue(value[key], `${where}.${key}`)
    return out
  }
  fail('BAD_PARAM', `${where} is not a serialisable value`, { where })
  return null
}

function canonicalTerrain(terrain) {
  if (!isPlainObject(terrain)) fail('BAD_SHAPE', 'terrain block must be an object', { got: typeof terrain })
  const out = {}
  for (const key of TERRAIN_KEY_ORDER) {
    if (key in terrain) out[key] = canonicalValue(terrain[key], `terrain.${key}`)
  }
  for (const key of Object.keys(terrain).sort()) {
    if (!TERRAIN_KEY_ORDER.includes(key)) out[key] = canonicalValue(terrain[key], `terrain.${key}`)
  }
  return out
}

function canonicalSource(source, nodeId) {
  if (source == null) return undefined
  if (!isPlainObject(source)) fail('BAD_SHAPE', `node ${nodeId} source must be an object`, { nodeId })
  const out = {}
  for (const key of Object.keys(source).sort()) out[key] = canonicalValue(source[key], `node ${nodeId} source.${key}`)
  const encoded = typeof out.base64 === 'string' ? out.base64.length : (typeof out.dataUrl === 'string' ? out.dataUrl.length : 0)
  if (encoded > PROJECT_SOURCE_BUDGET_BYTES) {
    fail('SOURCE_BUDGET',
      `node ${nodeId} embedded source is ${encoded} bytes, over the ${PROJECT_SOURCE_BUDGET_BYTES}-byte budget`,
      { nodeId, bytes: encoded, budget: PROJECT_SOURCE_BUDGET_BYTES })
  }
  return out
}

function canonicalNode(node) {
  if (!isPlainObject(node)) fail('BAD_SHAPE', 'graph.nodes must contain objects', { got: typeof node })
  if (!Number.isInteger(node.id)) fail('BAD_SHAPE', `node id must be an integer (got ${String(node.id)})`, { id: String(node.id) })
  if (typeof node.type !== 'string' || !node.type) fail('BAD_SHAPE', `node ${node.id} has no type`, { id: node.id })

  const out = {
    id: node.id,
    type: node.type,
    x: normNumber(node.x, `node ${node.id}.x`),
    y: normNumber(node.y, `node ${node.id}.y`),
    w: normNumber(node.w, `node ${node.id}.w`),
    params: canonicalValue(isPlainObject(node.params) ? node.params : {}, `node ${node.id}.params`),
  }
  // Dynamic input arity (ColorMixer today) is document state: without it the mixer reverts to
  // three layers on load and any edge into slot 3+ becomes unroutable.
  const inputs = node.inputs ?? node._inputs
  if (Array.isArray(inputs)) out.inputs = inputs.map(String)
  const source = canonicalSource(node.source ?? node._demSrc, node.id)
  if (source !== undefined) out.source = source
  return out
}

function canonicalEdge(edge) {
  if (!isPlainObject(edge)) fail('BAD_SHAPE', 'graph.edges must contain objects', { got: typeof edge })
  const out = { from: edge.from, to: edge.to, slot: edge.slot }
  if (!Number.isInteger(out.from) || !Number.isInteger(out.to) || !Number.isInteger(out.slot)) {
    fail('BAD_SHAPE', 'edge from/to/slot must be integers', { edge: `${edge.from}>${edge.to}:${edge.slot}` })
  }
  // Emitted only when truthy, so an enabled edge has exactly one representation.
  if (edge.disabled) out.disabled = true
  return out
}

/**
 * Build the canonical document from live app state.
 * `state` is a plain object supplied by legacy.js: { terrain, build, nodes, edges, uid, palettes,
 * view }. Nothing here reads globals.
 */
export function canonicalProject(state) {
  if (!isPlainObject(state)) fail('BAD_SHAPE', 'project state must be an object', { got: typeof state })
  const nodes = Array.isArray(state.nodes) ? state.nodes : fail('BAD_SHAPE', 'state.nodes must be an array')
  const edges = Array.isArray(state.edges) ? state.edges : fail('BAD_SHAPE', 'state.edges must be an array')

  const canonNodes = nodes.map(canonicalNode).sort((a, b) => a.id - b.id)
  const seen = new Set()
  for (const node of canonNodes) {
    if (seen.has(node.id)) fail('DUPLICATE_NODE_ID', `node id ${node.id} appears more than once`, { id: node.id })
    seen.add(node.id)
  }

  const canonEdges = edges.map(canonicalEdge).sort((a, b) => (a.to - b.to) || (a.slot - b.slot) || (a.from - b.from))

  const maxId = canonNodes.reduce((m, n) => Math.max(m, n.id), 0)
  const uid = state.uid
  if (!Number.isInteger(uid) || uid <= maxId) {
    // A loader that recomputes uid as nodes.length+1 collides with a document whose ids are
    // sparse (delete a node, save, reload) and silently fuses two nodes into one.
    fail('UID_RANGE', `uid must be an integer greater than the highest node id (uid=${String(uid)}, maxId=${maxId})`, { uid: String(uid), maxId })
  }

  const doc = {
    kind: PROJECT_KIND,
    schemaVersion: PROJECT_SCHEMA_VERSION,
    terrain: canonicalTerrain(state.terrain),
  }
  if (isPlainObject(state.build)) doc.build = canonicalValue(state.build, 'build')
  doc.graph = { uid, nodes: canonNodes, edges: canonEdges }
  // Only palettes a node actually references and that are not built in; an empty set is omitted
  // entirely rather than written as {}, so the absent and empty cases are one representation.
  if (isPlainObject(state.palettes) && Object.keys(state.palettes).length) {
    doc.palettes = canonicalValue(state.palettes, 'palettes')
  }
  // Workspace is restored best-effort — a stale selectedId or edge key is a warning, never a
  // fatal load. It deliberately excludes the three localStorage UI preferences: opening someone
  // else's project must not move your panes around.
  if (isPlainObject(state.workspace) && Object.keys(state.workspace).length) {
    doc.workspace = canonicalValue(state.workspace, 'workspace')
  }
  return doc
}

/** Canonical text. The trailing newline is part of the format so files end like text files. */
export function serializeProject(state) {
  return JSON.stringify(canonicalProject(state), null, 2) + '\n'
}

/**
 * Parse and shape-check. Returns { doc, warnings }; warnings are non-fatal observations the UI
 * may surface. Structural problems throw ProjectError — this format never best-effort repairs a
 * document, because a silently rewired graph is worse than a refused load.
 */
export function parseProject(text) {
  let raw
  try { raw = JSON.parse(text) }
  catch (error) { fail('BAD_JSON', `not a valid project file: ${error.message}`, { message: error.message }) }

  if (!isPlainObject(raw)) fail('BAD_SHAPE', 'project document must be a JSON object', { got: Array.isArray(raw) ? 'array' : typeof raw })
  if (raw.kind !== PROJECT_KIND) {
    fail('BAD_KIND', `not a Terrain Studio project (kind=${JSON.stringify(raw.kind)})`, { kind: String(raw.kind) })
  }

  const warnings = []
  if (raw.schemaVersion === undefined || raw.schemaVersion === null) {
    // ADR-002: an absent version is v1 and migrates once.
    warnings.push({ code: 'NO_VERSION', message: 'document has no schemaVersion; treating it as version 1' })
    raw.schemaVersion = 1
  }
  if (!Number.isInteger(raw.schemaVersion) || raw.schemaVersion < 1) {
    fail('BAD_VERSION', `schemaVersion must be a positive integer (got ${JSON.stringify(raw.schemaVersion)})`, { schemaVersion: String(raw.schemaVersion) })
  }
  if (!isPlainObject(raw.graph)) fail('BAD_SHAPE', 'document has no graph block')
  if (!Array.isArray(raw.graph.nodes)) fail('BAD_SHAPE', 'graph.nodes must be an array')
  if (!Array.isArray(raw.graph.edges)) fail('BAD_SHAPE', 'graph.edges must be an array')
  if (!isPlainObject(raw.terrain)) fail('BAD_SHAPE', 'document has no terrain block')

  return { doc: raw, warnings }
}

/**
 * Semantic validation against the live registry.
 * `types` is the TYPES table; `arityOf(type, node)` reports how many input slots a node has,
 * which is dynamic for ColorMixer and therefore cannot be read from the descriptor alone.
 */
export function validateProject(doc, { types, arityOf } = {}) {
  const problems = []
  const byId = new Map()
  for (const node of doc.graph.nodes) {
    if (byId.has(node.id)) problems.push({ code: 'DUPLICATE_NODE_ID', id: node.id })
    byId.set(node.id, node)
    if (types && !types[node.type]) problems.push({ code: 'UNKNOWN_TYPE', id: node.id, type: node.type })
  }
  const maxId = doc.graph.nodes.reduce((m, n) => Math.max(m, n.id), 0)
  if (!Number.isInteger(doc.graph.uid) || doc.graph.uid <= maxId) {
    problems.push({ code: 'UID_RANGE', uid: doc.graph.uid, maxId })
  }
  for (const edge of doc.graph.edges) {
    if (!byId.has(edge.from)) problems.push({ code: 'EDGE_ENDPOINT', end: 'from', id: edge.from })
    if (!byId.has(edge.to)) { problems.push({ code: 'EDGE_ENDPOINT', end: 'to', id: edge.to }); continue }
    if (arityOf) {
      const to = byId.get(edge.to)
      const arity = arityOf(to.type, to)
      if (!(edge.slot >= 0 && edge.slot < arity)) {
        problems.push({ code: 'EDGE_SLOT_RANGE', to: edge.to, slot: edge.slot, arity })
      }
    }
  }
  if (problems.length) {
    const first = problems[0]
    fail(first.code, `project failed validation: ${problems.length} problem(s), first ${JSON.stringify(first)}`, { problems })
  }
  return true
}

/**
 * Version dispatch. `migrations` maps a FROM-version to a function producing the next version.
 * S2.2 adds `{ 1: migrateV1toV2 }` and changes nothing else here.
 *
 * Both failure modes throw rather than limping forward, because a half-migrated document that
 * still loads is how a schema migration silently corrupts a project:
 *   NO_MIGRATION        — a version on the path has no registered step
 *   MIGRATION_VERSION   — a step ran but did not stamp schemaVersion forward
 */
export function migrateProject(doc, { targetVersion = PROJECT_SCHEMA_VERSION, migrations = {} } = {}) {
  let current = doc
  let guard = 0
  while (current.schemaVersion < targetVersion) {
    const from = current.schemaVersion
    const step = migrations[from]
    if (typeof step !== 'function') {
      fail('NO_MIGRATION', `no migration registered from schemaVersion ${from} (target ${targetVersion})`, { from, targetVersion })
    }
    const next = step(current)
    if (!isPlainObject(next)) fail('BAD_SHAPE', `migration from ${from} did not return a document`, { from })
    if (!Number.isInteger(next.schemaVersion) || next.schemaVersion <= from) {
      fail('MIGRATION_VERSION',
        `migration from ${from} left schemaVersion at ${String(next.schemaVersion)}; it must advance`,
        { from, got: String(next.schemaVersion) })
    }
    current = next
    if (++guard > 64) fail('MIGRATION_VERSION', 'migration did not converge', { guard })
  }
  if (current.schemaVersion > targetVersion) {
    fail('FUTURE_VERSION',
      `document schemaVersion ${current.schemaVersion} is newer than this build understands (${targetVersion})`,
      { got: current.schemaVersion, supported: targetVersion })
  }
  return current
}
