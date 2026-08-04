// depression — S4.1, the Depression Policy node.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run until
// the graph is evaluated, so the legacy<->plugin cycle is safe.
//
// WHY THIS IS A NODE AND NOT A CHECKBOX. Every flow result is an interpretation of a surface that
// has already had its closed depressions dealt with, and there are three defensible ways to deal
// with them that produce genuinely different drainage. Burying that choice inside the router means
// the author reads a river network without knowing which question it answered.
//
// THE SOLID HEIGHT IS NEVER TOUCHED. What this node conditions is a `routingSurface` — a derived
// field that exists so flow has somewhere consistent to run. It is not rendered, not collided
// against, and not exported as terrain. The primary height output is the input, unchanged, in all
// three modes, and the oracle asserts it bitwise.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, fieldW, fieldH, isHex } from '../../legacy.js'
import { depressionPolicy } from '../../core/hydrology.js'

export default definePlugin({
  type: 'depression',
  cat: 'data',
  name: 'Depression Policy',
  ins: ['Height'],
  desc: 'Decide how closed depressions are handled before flow is routed: fill to spill, breach an outlet, or preserve them as endorheic basins. Emits a routing surface, never terrain.',
  params: [
    P.select('mode', 'Mode', [
      ['fill', 'Fill to spill'],
      ['breach', 'Breach an outlet'],
      ['preserve', 'Preserve (endorheic)'],
    ], 'fill'),
  ],

  inputs: [
    { id: 'height', name: 'Height', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'relativeHeight', unit: 'none', role: 'data', required: true },
  ],
  outputs: [
    // Primary is the UNCONDITIONED height, deliberately. Anything downstream that wants terrain gets
    // terrain by default, and has to ask explicitly for the routing surface — which is the whole
    // point of separating them.
    { id: 'height', name: 'Height', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'relativeHeight', unit: 'none', primary: true, lens: 'continued' },
    { id: 'routingSurface', name: 'Routing', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'routingSurface', unit: 'none', lens: 'derived' },
    { id: 'depressionDepth', name: 'Depth', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'depressionDepth', unit: 'none', lens: 'derived' },
    // Signed, so the author can see what conditioning WOULD change: positive where fill raised the
    // surface, negative where breach cut it, zero under preserve.
    { id: 'conditioningDelta', name: 'Delta', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'conditioningDelta', unit: 'none', lens: 'derived' },
  ],

  eval: (p, ins, node, ctx) => {
    const src = ins[0]
    const height = src || newField()
    const values = new Map([['height', height]])
    // Demand-driven: the flood is O(N log N) and a node parked in a graph with only its height port
    // wired should cost nothing beyond passing that field through. An absent ctx means "compute it",
    // so a direct eval — the digest oracle, an ad-hoc probe — still sees the whole result.
    const demanded = ctx && ctx.demanded
    const wanted = !demanded || ['routingSurface', 'depressionDepth', 'conditioningDelta'].some(k => demanded.has(k))
    if (wanted && src) {
      const w = fieldW(), h = fieldH()
      const r = depressionPolicy(src, w, h, { mode: p.mode || 'fill', hex: isHex() })
      values.set('routingSurface', r.routingSurface)
      values.set('depressionDepth', r.depressionDepth)
      values.set('conditioningDelta', r.conditioningDelta)
    }
    // The primary is chosen by the port carrying `primary: true`, not by a key in this object —
    // returning one here would be ignored and would read as if it were doing something.
    return { values }
  },
})
