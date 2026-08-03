// Math — a bounded per-sample expression over up to three input fields (S8.4).
//
// The expression is PARSED to an AST and that AST is interpreted. Nothing here builds a Function
// or calls eval, so an expression cannot reach a global, a DOM node or the network. That matters
// because a terrain graph is a document people share: one that can execute arbitrary JavaScript
// when opened is a different kind of artefact than a heightfield.
//
// Parse ONCE per evaluation, not per sample. A 4096-square field is 16.7 million samples, and
// re-parsing per sample would make the node unusable while looking merely slow.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, fieldW, fieldH, fieldLen } from '../../legacy.js'
import { parseExpr, evalExpr, ExprError } from '../../core/expr.js'

export default definePlugin({
  type: 'mathnode',
  cat: 'comb',
  name: 'Math',
  ins: ['A', 'B', 'C'],
  desc: 'Evaluate a bounded expression per sample over inputs a, b, c plus x, y in [0,1]. No eval, no globals.',
  params: [P.text('expr', 'Expression', 'a', 3)],
  inputs: ['A', 'B', 'C'].map((name, i) => ({
    id: name.toLowerCase(), name, kind: 'scalarRaster', storage: 'R32F', components: 1,
    semantic: 'anyScalarRaster', unit: 'none', role: 'data', legacySlot: i,
  })),
  outputs: [
    // The result of arbitrary arithmetic has no inherited semantic — adding a temperature to a
    // slope produces a number, not a temperature — so this declares a plain unitless scalar rather
    // than pretending to preserve its inputs' meaning.
    { id: 'out', name: 'Out', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'relativeHeight', unit: 'none', primary: true, lens: 'derived' },
  ],
  info: (node) => {
    try {
      const parsed = parseExpr(node.params.expr, { names: ['a', 'b', 'c', 'x', 'y', 'i'] })
      return `<b>OK</b> — ${parsed.nodeCount} node(s)`
    } catch (err) {
      return `<b>${err instanceof ExprError ? err.code : 'ERROR'}</b> — ${err.message}`
    }
  },
  eval: (p, ins) => {
    const w = fieldW(), h = fieldH(), out = newField()
    let ast
    try { ast = parseExpr(p.expr, { names: ['a', 'b', 'c', 'x', 'y', 'i'] }).ast }
    catch { return out }                       // an unparseable expression yields zero, not a crash
    const inA = ins[0], inB = ins[1], inC = ins[2]
    const scope = { a: 0, b: 0, c: 0, x: 0, y: 0, i: 0 }
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
