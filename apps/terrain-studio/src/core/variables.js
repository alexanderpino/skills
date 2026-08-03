// Typed graph variables and lexical scope — ADR-004, story S8.3.
//
// Pure and DOM-free. A variable is a named, typed, unit-carrying value stored in the document, so
// one number can drive many nodes and be changed in one place.
//
// STABLE IDs, for the same reason edges carry port ids rather than slot indices: a variable is
// referenced by id, never by display name. Rename "sea level" to "base level" and every reference
// must keep working. A name-keyed design silently breaks every reference on a rename, and the
// breakage looks like a terrain change rather than a rename.
//
// LEXICAL SCOPE is a chain, resolved innermost-first. Today the chain is always one deep — the
// document — because subgraphs do not exist until S8.5. The chain is built now anyway: retrofitting
// scope onto a flat lookup means revisiting every call site, whereas a one-element chain costs
// nothing and makes S8.5's instance-parameter override a new frame rather than a new mechanism.
// This is the same staging discipline as the doctrine validators: the shape is here, the frame that
// uses it arrives with the story that needs it.

export const VARIABLE_UNITS = Object.freeze(['none', 'm', 'degC', 'mPerS', 'rad', 'deg', 'percent', 'days'])
export const VARIABLE_ID_RE = /^[a-z][A-Za-z0-9_]*$/

export const VARIABLE_ERROR_CODES = Object.freeze([
  'VAR_ID_INVALID', 'VAR_ID_DUPLICATE', 'VAR_UNKNOWN', 'VAR_UNIT_UNKNOWN',
  'VAR_VALUE_NOT_FINITE', 'VAR_NAME_EMPTY',
])

export class VariableError extends Error {
  constructor(code, message, detail) { super(message); this.name = 'VariableError'; this.code = code; this.detail = detail }
}
const fail = (code, message, detail) => { throw new VariableError(code, message, detail) }

/** Validate a variable table. Returns problems rather than throwing, so a UI can show them all. */
export function validateVariables(list) {
  const problems = []
  const seen = new Set()
  for (const v of (list || [])) {
    if (!v || typeof v.id !== 'string' || !VARIABLE_ID_RE.test(v.id)) {
      problems.push({ code: 'VAR_ID_INVALID', id: String(v && v.id) }); continue
    }
    if (seen.has(v.id)) problems.push({ code: 'VAR_ID_DUPLICATE', id: v.id })
    seen.add(v.id)
    if (typeof v.name !== 'string' || !v.name.trim()) problems.push({ code: 'VAR_NAME_EMPTY', id: v.id })
    if (!VARIABLE_UNITS.includes(v.unit)) problems.push({ code: 'VAR_UNIT_UNKNOWN', id: v.id, unit: v.unit })
    // A non-finite variable is refused at the source. It would otherwise reach every consumer at
    // once — that is the entire point of a variable — and turn a whole graph to NaN from one field.
    if (!Number.isFinite(v.value)) problems.push({ code: 'VAR_VALUE_NOT_FINITE', id: v.id, value: String(v && v.value) })
  }
  return problems
}

/**
 * A scope chain. `frames` are ordered outermost-first; resolution walks innermost-first so an inner
 * frame shadows an outer one. S8.5 pushes a subgraph instance's parameters as an inner frame.
 */
export function makeScope(frames) {
  const chain = (frames || []).filter(Boolean)
  return {
    frames: chain,
    depth: chain.length,
    /** Resolve by ID. Returns the variable record plus the frame index that supplied it. */
    lookup(id) {
      for (let i = chain.length - 1; i >= 0; i--) {
        const hit = (chain[i].variables || []).find(v => v.id === id)
        if (hit) return { variable: hit, frame: i, shadowed: i < chain.length - 1 ? false : chain.length > 1 }
      }
      return null
    },
    /** Every id visible from here, innermost definition winning. */
    ids() {
      const out = new Map()
      for (const frame of chain) for (const v of (frame.variables || [])) out.set(v.id, v)
      return [...out.keys()].sort()
    },
    /** A plain {id: value} bag for the expression evaluator. */
    values() {
      const out = Object.create(null)
      for (const frame of chain) for (const v of (frame.variables || [])) out[v.id] = v.value
      return out
    },
  }
}

/** Resolve one id or throw a named error — used where a missing variable must not silently be 0. */
export function requireVariable(scope, id) {
  const hit = scope.lookup(id)
  if (!hit) fail('VAR_UNKNOWN', `unknown variable ${JSON.stringify(id)}`, { id, known: scope.ids() })
  return hit.variable
}
