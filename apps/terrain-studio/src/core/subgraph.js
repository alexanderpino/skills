// Versioned subgraph definitions — ADR-004, stories S8.5 and S8.6.
//
// Pure and DOM-free. A definition is a reusable internal DAG with typed MacroPorts and a parameter
// surface; an instance binds override values and evaluates the definition without duplicating it.
//
// IDENTITY IS CONTENT, NOT NAME. A definition's hash covers its version, its ports, its parameter
// surface and its whole internal DAG. That hash is what a document records and what an import
// compares, so:
//   * two identical definitions arriving by different routes DEDUPLICATE rather than collide;
//   * the same id at the same version with DIFFERENT content is a conflict and is refused, not
//     merged — a silent merge there would rewrite one author's graph with another's.
// ADR-004 is explicit that migrations are deliberate and never best-effort rewiring, which is the
// same rule S2.2's edges follow: an unresolvable reference is a load error.
//
// RECURSION IS REJECTED AT REGISTRATION, both direct and indirect. A definition that contains
// itself has no finite evaluation, and discovering that during evaluation means discovering it as a
// stack overflow inside a render.

export const SUBGRAPH_VERSION = 1

export const SUBGRAPH_ERROR_CODES = Object.freeze([
  'SUBGRAPH_ID_INVALID', 'SUBGRAPH_UNKNOWN', 'SUBGRAPH_RECURSION',
  'SUBGRAPH_HASH_CONFLICT', 'SUBGRAPH_VERSION_UNSUPPORTED', 'SUBGRAPH_PORT_UNKNOWN',
  'SUBGRAPH_MISSING_DEFINITION',
])

export class SubgraphError extends Error {
  constructor(code, message, detail) { super(message); this.name = 'SubgraphError'; this.code = code; this.detail = detail }
}
const fail = (code, message, detail) => { throw new SubgraphError(code, message, detail) }

const SUBGRAPH_ID_RE = /^[a-z][A-Za-z0-9_]*$/

/**
 * Content hash over everything that can change what a definition computes.
 *
 * Deliberately NOT a hash of the whole object: node x/y positions and display names are authoring
 * comfort, not behaviour, and including them would make two behaviourally identical definitions
 * conflict because someone dragged a node. Ports, params and wiring are included because each
 * changes the result.
 */
export function definitionHash(def) {
  const canonical = {
    version: def.version,
    inputs: (def.inputs || []).map(p => [p.id, p.kind, p.semantic, p.unit]),
    outputs: (def.outputs || []).map(p => [p.id, p.kind, p.semantic, p.unit]),
    params: (def.params || []).map(p => [p.key, p.def]),
    // Param keys SORTED. JSON.stringify preserves insertion order, so an unsorted hash changed
    // whenever a definition made a round trip through the canonical document writer — which sorts
    // keys — and every reloaded document then read as a hash CONFLICT against its own definition.
    // Content identity that is not stable across save/load is not content identity.
    nodes: (def.nodes || []).map(n => [n.localId, n.type,
      JSON.stringify(Object.keys(n.params || {}).sort().map(k => [k, n.params[k]]))]).sort(),
    edges: (def.edges || []).map(e => [e.from, e.fromPort || 'out', e.to, e.toPort || 'in', !!e.disabled]).sort(),
  }
  const text = JSON.stringify(canonical)
  // FNV-1a, 64 bits as two 32-bit halves. Not cryptographic — this detects divergence between two
  // definitions, it does not defend against someone constructing a collision on purpose.
  let a = 0x811c9dc5, b = 0x01000193
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i)
    a = Math.imul(a ^ c, 16777619) >>> 0
    b = (Math.imul(b + c, 2654435761) ^ (b >>> 7)) >>> 0
  }
  return a.toString(16).padStart(8, '0') + b.toString(16).padStart(8, '0')
}

/** Direct and indirect recursion, over the definition table a registration would produce. */
export function findRecursion(defs, startId) {
  const seen = new Set(), stack = []
  const walk = id => {
    if (stack.includes(id)) return stack.concat(id)
    if (seen.has(id)) return null
    seen.add(id); stack.push(id)
    const def = defs[id]
    for (const node of ((def && def.nodes) || [])) {
      // A node inside a definition may itself be a subgraph instance; that is the indirect case.
      if (node.type === 'subgraph' && node.params && node.params.definitionId) {
        const cycle = walk(node.params.definitionId)
        if (cycle) return cycle
      }
    }
    stack.pop()
    return null
  }
  return walk(startId)
}

export function validateDefinition(def) {
  const problems = []
  if (!def || typeof def.id !== 'string' || !SUBGRAPH_ID_RE.test(def.id)) {
    problems.push({ code: 'SUBGRAPH_ID_INVALID', id: String(def && def.id) })
    return problems
  }
  if (!Number.isInteger(def.version) || def.version < 1) {
    problems.push({ code: 'SUBGRAPH_VERSION_UNSUPPORTED', id: def.id, version: String(def.version) })
  }
  if (!Array.isArray(def.nodes) || def.nodes.length === 0) {
    // Absence of evidence: an empty definition computes nothing and is almost always a mistake.
    problems.push({ code: 'SUBGRAPH_ID_INVALID', id: def.id, reason: 'definition has no internal nodes' })
  }
  for (const port of (def.outputs || [])) {
    const target = (def.nodes || []).find(n => n.localId === port.from)
    if (!target) problems.push({ code: 'SUBGRAPH_PORT_UNKNOWN', id: def.id, port: port.id, from: port.from })
  }
  return problems
}

/**
 * Register a definition into a table, refusing recursion and hash conflicts.
 * Returns a NEW table; the input is not mutated, so a rejected registration cannot half-apply.
 */
export function registerDefinition(defs, def) {
  const problems = validateDefinition(def)
  if (problems.length) fail(problems[0].code, `definition ${def && def.id} is invalid: ${JSON.stringify(problems[0])}`, { problems })

  const hash = definitionHash(def)
  const existing = defs[def.id]
  if (existing && existing.version === def.version) {
    const existingHash = existing.hash || definitionHash(existing)
    if (existingHash === hash) return defs                      // exact identity: deduplicate
    fail('SUBGRAPH_HASH_CONFLICT',
      `definition ${def.id} v${def.version} already exists with different content`,
      { id: def.id, version: def.version, existing: existingHash, incoming: hash })
  }
  const next = { ...defs, [def.id]: { ...def, hash } }
  const cycle = findRecursion(next, def.id)
  if (cycle) fail('SUBGRAPH_RECURSION', `definition ${def.id} contains itself: ${cycle.join(' -> ')}`, { cycle })
  return next
}

/**
 * Content key for ONE upstream field.
 *
 * The caller used to pass `[String(ins[0].length)]`, which is the same string for every field in the
 * document because every field is RES*RES.  shape-ok: prose describing a fixed defect, no alloc.
 * Two instances of the same definition with the same overrides and DIFFERENT inputs therefore
 * collided on one cache entry, and the second silently
 * rendered the first's terrain — measured with instance A fed by perlin and instance D fed by
 * ridged returning the identical Float32Array object, not merely equal values.
 *
 * The digest reads the raw 32-bit words, so it is bit-exact rather than tolerance-based; -0 and NaN
 * payloads key differently from 0 and NaN, which costs a cache miss and never a wrong result. It is
 * O(N) against an evaluation that is O(N x definition nodes), so it is a fraction of what it guards.
 */
export function fieldKey(field) {
  if (field == null) return 'null'
  if (!ArrayBuffer.isView(field)) return 'x' + String(field)
  const words = new Uint32Array(field.buffer, field.byteOffset, field.byteLength >>> 2)
  let a = 0x811c9dc5, b = 0x01000193
  for (let i = 0; i < words.length; i++) {
    const w = words[i]
    a = Math.imul(a ^ (w & 0xffff), 16777619) >>> 0
    a = Math.imul(a ^ (w >>> 16), 16777619) >>> 0
    b = (Math.imul(b + w, 2654435761) ^ (b >>> 7)) >>> 0
  }
  return words.length.toString(16) + ':' + a.toString(16).padStart(8, '0') + b.toString(16).padStart(8, '0')
}

/**
 * Cache identity for one instance evaluation. ADR-004 names every term: full definition
 * hash/version, instance overrides, context/substrate, effective seed, demanded output, and the
 * upstream port keys.
 *
 * Two identical instances therefore share a key and may share an immutable cached result; two
 * instances with different overrides never can, which is what keeps them from aliasing state.
 *
 * `definitionClosure` is the TRANSITIVE set of definitions this one instantiates, as [id, hash]
 * pairs. The top-level hash alone was not enough: a definition's own content is unchanged when a
 * definition it *contains* changes or disappears, so a nested edit left the parent's key identical
 * and the cache returned a result computed from a definition that no longer existed. Measured — a
 * document reloaded with the inner definition dropped produced byte-identical output with every
 * node forced dirty.
 */
export function instanceCacheKey({ definition, overrides = {}, demandedOutput = 'out', seed = 0, context = {}, upstreamKeys = [], definitionClosure = [] } = {}) {
  const hash = definition.hash || definitionHash(definition)
  const parts = [
    'sg', hash, 'v' + definition.version,
    JSON.stringify(Object.keys(overrides).sort().map(k => [k, overrides[k]])),
    demandedOutput, String(seed),
    JSON.stringify(Object.keys(context).sort().map(k => [k, context[k]])),
    upstreamKeys.join(','),
    JSON.stringify([...definitionClosure].sort()),
  ]
  return parts.join('|')
}

/** [id, hash] for every definition reachable from `def`, itself included, sorted and stable. */
export function closureHashes(defs, def) {
  const out = []
  const seen = new Set()
  const visit = id => {
    if (!id || seen.has(id)) return
    seen.add(id)
    const d = defs[id]
    // A MISSING definition is recorded as such rather than skipped. Skipping it would make "the
    // definition vanished" and "the definition was never referenced" produce the same key, which is
    // the precise shape of the staleness bug this term exists to prevent.
    out.push([id, d ? (d.hash || definitionHash(d)) : 'MISSING'])
    for (const n of ((d && d.nodes) || [])) if (n.type === 'subgraph' && n.params) visit(n.params.definitionId)
  }
  visit(def && def.id)
  return out.sort()
}

/** Definitions a document must embed: every one an instance references, transitively. */
export function referencedDefinitions(defs, nodes) {
  const out = new Set()
  const visit = id => {
    if (!id || out.has(id)) return
    const def = defs[id]
    if (!def) fail('SUBGRAPH_MISSING_DEFINITION', `graph references unknown definition ${id}`, { id })
    out.add(id)
    for (const n of (def.nodes || [])) if (n.type === 'subgraph' && n.params) visit(n.params.definitionId)
  }
  for (const n of (nodes || [])) if (n.type === 'subgraph' && n.params) visit(n.params.definitionId)
  return [...out].sort()
}
