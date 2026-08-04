// lake — S4.4, the Lake / Basin node.
//
// NOT YET REGISTERED. `src/plugins/data/index.js` is owned by another process, and three of the
// semantics below (`waterSurface`, `waterDepth`, `shoreDistance`) are not yet in `src/core/ports.js`,
// which is also owned elsewhere. Registering this file before those land would throw
// PORT_SEMANTIC_UNKNOWN at module load and take the whole page down. The two changes needed are
// written out in the story report; the oracle validates every port here that CAN be validated today
// and pins the three pending ones to the exact kind and unit the report asks for, so the request and
// the code cannot drift apart while they wait.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run until
// the graph is evaluated, so the legacy<->plugin cycle is safe.
//
// WHY THERE IS NO WATER-LEVEL SLIDER. A lake filled to an authored level is a paint effect: it floods
// unrelated low ground on the far side of the domain, it moves when the terrain's range moves, and
// its surface bears no relation to the rim that is holding the water back. The level here is the
// elevation of the basin's own lowest rim cell, taken out of the priority flood, and the gate asserts
// the surface is bit-identical to that cell's elevation. The only knob is a floor on how small a
// hollow still counts as a lake, which is a question about noise, not about water.
//
// THIS NODE NEVER WRITES HEIGHT. Guardrail 1. The primary output is the input `solidTop`, passed
// through by identity; water surface, depth, shore distance, basin id and the spill features are all
// separate products. The oracle reads the input array bitwise before and after to prove it.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { RANGE } from '../../core/ports.js'
import { newField, fieldW, fieldH, cellSizeM, isHex } from '../../legacy.js'
import { lakes } from '../../core/lakes.js'

export default definePlugin({
  type: 'lake',
  cat: 'data',
  name: 'Lake / Basin',
  ins: ['Solid top'],
  desc: 'Fill every closed basin to its own spill level. Emits water surface, water depth, signed shore distance in metres, a basin id raster and the basin and spill features. Never modifies terrain.',
  params: [
    // A one-cell hollow is not a lake. On a noisy DEM there are hundreds of thousands of them, and
    // without a floor the label raster is confetti and the feature set is unreadable. 1 keeps
    // everything, which is the honest default: suppression is a choice, not a hidden clean-up.
    P.slider('minCells', 'Smallest lake (cells)', 1, 512, 1, 1),
  ],

  inputs: [
    // The PHYSICAL frame, in metres — not `relativeHeight`. Depth and shore distance are quoted in
    // metres, and a depth derived from an autolevelled 0..1 field would change every time some
    // unrelated peak moved the field's range.
    { id: 'solidTop', name: 'Solid top', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'solidTop', unit: 'm', role: 'data', required: true },
  ],
  outputs: [
    // Primary is the UNTOUCHED input. Anything downstream that wants terrain gets terrain by
    // default and has to ask explicitly for water — which is guardrail 1 expressed in the ports.
    { id: 'solidTop', name: 'Solid top', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'solidTop', unit: 'm', primary: true, lens: 'continued' },
    { id: 'waterSurface', name: 'Surface', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'waterSurface', unit: 'm', lens: 'derived' },
    { id: 'waterDepth', name: 'Depth', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'waterDepth', unit: 'm', lens: 'derived' },
    // SIGNED METRES, not a mask. Positive offshore, zero on the shoreline, negative on land. A shore
    // mask is one threshold away and can be derived downstream; a mask cannot be turned back into a
    // distance, so metres is what the node produces.
    { id: 'shoreDistance', name: 'Shore dist', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'shoreDistance', unit: 'm', lens: 'derived' },
    // Categorical. ports.js refuses to let this reach any continuous input, because the average of
    // two basin ids is a third basin that does not exist.
    { id: 'basinId', name: 'Basin', kind: 'labelRaster', storage: 'I32', components: 1,
      semantic: 'basinId', unit: 'none', lens: 'derived',
      range: RANGE.labels(0, 2147483646, -1) },
    { id: 'basins', name: 'Basins', kind: 'featureSet', storage: 'RECORDS', components: 1,
      semantic: 'feature', unit: 'none', lens: 'derived' },
    { id: 'spills', name: 'Spills', kind: 'featureSet', storage: 'RECORDS', components: 1,
      semantic: 'feature', unit: 'none', lens: 'derived' },
  ],

  eval: (p, ins, node, ctx) => {
    const src = ins[0]
    const solid = src || newField()
    // The input array by identity, not a copy. A copy would satisfy a bitwise comparison just as well
    // and would hide an accidental write behind an extra allocation per evaluation.
    const values = new Map([['solidTop', solid]])
    // Demand-driven: the flood plus the distance transform is O(N log N) and a node parked in a graph
    // with only its pass-through wired should cost nothing. An absent ctx means "compute it", so a
    // direct eval — the digest oracle, an ad-hoc probe — still sees the whole result.
    const demanded = ctx && ctx.demanded
    const products = ['waterSurface', 'waterDepth', 'shoreDistance', 'basinId', 'basins', 'spills']
    if (src && (!demanded || products.some(k => demanded.has(k)))) {
      const r = lakes(src, fieldW(), fieldH(), {
        hex: isHex(),
        cellSizeM: cellSizeM(),
        minCells: Math.max(1, Math.round(Number(p.minCells) || 1)),
      })
      values.set('waterSurface', r.surface)
      values.set('waterDepth', r.depth)
      values.set('shoreDistance', r.shoreDistance)
      values.set('basinId', r.lakeId)
      values.set('basins', r.basins)
      values.set('spills', r.spills)
    }
    // The primary is chosen by the port carrying `primary: true`, not by a key in this object —
    // returning one here would be ignored and would read as if it were doing something.
    return { values }
  },
})
