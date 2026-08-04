// Math — a bounded per-sample expression over up to three input fields (S8.4).
//
// The expression is PARSED to an AST and that AST is interpreted. Nothing here builds a Function
// or calls eval, so an expression cannot reach a global, a DOM node or the network. That matters
// because a terrain graph is a document people share: one that can execute arbitrary JavaScript
// when opened is a different kind of artefact than a heightfield.
//
// Parse ONCE per evaluation, not per sample. A 4096-square field is 16.7 million samples, and
// re-parsing per sample would make the node unusable while looking merely slow.
//
// UNITS. An expression's names come from two places and both declare a unit:
//   * a, b, c, x, y, i — the input ports and the positional inputs, all `unit: 'none'`
//   * every document variable in scope, each carrying the unit variables.js makes it declare
// So `seaLevelM + airTempC` is refused at parse with EXPR_UNIT_MISMATCH, and `2 * seaLevelM` is
// metres. Because the six built-in names are all dimensionless, every expression that could be
// written before variables existed still derives `none` and refuses nothing — the check is inert
// until a unit is declared, which is what makes it safe to add to a node that already ships.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, fieldW, fieldH, fieldLen, currentScope } from '../../legacy.js'
import { parseExpr, evalExpr, ExprError } from '../../core/expr.js'

// The names the node itself provides. They WIN over a document variable of the same id: `a` in an
// expression is the A input, whatever the document calls its variables, because the input is what
// the node's own port labels promise. (`pi`, `e` and `tau` shadow a variable too — EXPR_CONSTANTS
// is consulted before the name list.)
const BUILTIN_NAMES = ['a', 'b', 'c', 'x', 'y', 'i']

const DECLARED_INPUTS = ['A', 'B', 'C'].map((name, i) => ({
  id: name.toLowerCase(), name, kind: 'scalarRaster', storage: 'R32F', components: 1,
  semantic: 'anyScalarRaster', unit: 'none', role: 'data', legacySlot: i,
}))

// The result of arbitrary arithmetic has no inherited semantic — adding a temperature to a slope
// produces a number, not a temperature — so this declares a plain unitless scalar rather than
// pretending to preserve its inputs' meaning.
const DECLARED_OUTPUT = {
  id: 'out', name: 'Out', kind: 'scalarRaster', storage: 'R32F', components: 1,
  semantic: 'relativeHeight', unit: 'none', primary: true, lens: 'derived',
}

/** The expression environment: the legal names, and the unit each one declares. */
function exprEnv() {
  const names = [...BUILTIN_NAMES]
  const units = Object.create(null)
  for (const name of BUILTIN_NAMES) units[name] = 'none'
  const scope = currentScope()
  for (const id of scope.ids()) {
    if (units[id] !== undefined) continue                 // a built-in name wins — see above
    const hit = scope.lookup(id)
    if (!hit) continue
    names.push(id)
    units[id] = hit.variable.unit || 'none'
  }
  return { names, units }
}

export default definePlugin({
  type: 'mathnode',
  cat: 'comb',
  name: 'Math',
  ins: ['A', 'B', 'C'],
  desc: 'Evaluate a bounded expression per sample over inputs a, b, c plus x, y in [0,1] and any document variable. No eval, no globals.',
  params: [P.text('expr', 'Expression', 'a', 3)],
  inputs: DECLARED_INPUTS,
  outputs: [DECLARED_OUTPUT],
  info: (node) => {
    // Not `const { names, units } = ...`: scripts/check-plugin-imports.cjs binds only Identifier
    // declarators in a block, so a destructured const reads to it as two undefined names.
    const env = exprEnv()
    try {
      const parsed = parseExpr(node.params.expr, { names: env.names, units: env.units })
      return `<b>OK</b> — ${parsed.nodeCount} node(s), result in ${parsed.unit}`
    } catch (err) {
      return `<b>${err instanceof ExprError ? err.code : 'ERROR'}</b> — ${err.message}`
    }
  },
  // The declared output above is a PLACEHOLDER for the unit, the same way variable.js's is: an
  // expression over a metres variable produces metres, and a static descriptor cannot know that.
  //
  // Only the UNIT is refined, never the semantic. A unit does not determine a semantic — three
  // semantics declare defaultUnit 'm' (height, uplift and sediment), so `m` names no single one of
  // them — and this node's own comment above is the reason: arbitrary arithmetic inherits no
  // meaning. An unparseable or unit-incompatible expression evaluates to a zero field, and a field
  // of zeroes is dimensionless, so the placeholder is the honest answer in the failure case too.
  resolvePorts: (node) => {
    const env = exprEnv()
    let unit = 'none'
    try { unit = parseExpr(node && node.params ? node.params.expr : '', { names: env.names, units: env.units }).unit } catch { unit = 'none' }
    return { inputs: DECLARED_INPUTS, outputs: [{ ...DECLARED_OUTPUT, unit }] }
  },
  eval: (p, ins) => {
    const w = fieldW(), h = fieldH(), out = newField()
    const env = exprEnv()
    let ast
    try { ast = parseExpr(p.expr, { names: env.names, units: env.units }).ast }
    catch { return out }                       // an unparseable expression yields zero, not a crash
    const inA = ins[0], inB = ins[1], inC = ins[2]
    // Variables first, then the per-sample names on top: a built-in name must not be displaceable
    // by a document variable, which is the same precedence exprEnv() declares.
    const scope = Object.assign(Object.create(null), currentScope().values(), { a: 0, b: 0, c: 0, x: 0, y: 0, i: 0 })
    const n = fieldLen()
    for (let idx = 0; idx < n; idx++) {
      const px = idx % w, py = (idx / w) | 0
      scope.a = inA ? inA[idx] : 0; scope.b = inB ? inB[idx] : 0; scope.c = inC ? inC[idx] : 0
      scope.x = w > 1 ? px / (w - 1) : 0; scope.y = h > 1 ? py / (h - 1) : 0; scope.i = idx
      // Per-sample non-finite results are clamped to 0 rather than throwing: one bad sample must
      // not discard a whole field, and the parse-time gates already refuse the structural cases.
      try { const v = evalExpr(ast, scope, { checkFinite: false }); out[idx] = Number.isFinite(v) ? v : 0 }
      catch { out[idx] = 0 }
    }
    return out
  },
})
