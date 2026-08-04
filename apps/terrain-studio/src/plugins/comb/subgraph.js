// Subgraph — instantiate a versioned definition (S8.5).
//
// Evaluates the definition's internal DAG in a private scope, once per instance, and returns the
// value at the definition's declared output port. Internal nodes are NOT part of the parent graph:
// they never appear in the palette, in selection, or in the parent's node list, which is what makes
// this encapsulation rather than a macro expansion.
//
// Instance overrides live in the instance's own params and are pushed as an inner SCOPE FRAME —
// the chain built in S8.3 for exactly this, so two instances of the same definition with different
// overrides cannot see each other's values.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, evaluateSubgraphInstance } from '../../legacy.js'

export default definePlugin({
  type: 'subgraph',
  cat: 'comb',
  name: 'Subgraph',
  ins: ['In'],
  desc: 'Instantiate a reusable subgraph definition. Internal nodes stay encapsulated.',
  params: [
    P.text('definitionId', 'Definition', '', 1),
    // ADR-004: instances pin (definitionId, version, fullHash) and old instances never float. Both
    // are stamped on first resolve rather than typed; they are shown so an author can SEE which
    // version an instance is bound to, which is the whole point of a pin.
    P.text('version', 'Version', '', 1),
    P.text('hash', 'Content hash', '', 1),
    P.text('overrides', 'Overrides', '', 3),
  ],
  inputs: [
    { id: 'in', name: 'In', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'anyScalarRaster', unit: 'none', role: 'data' },
  ],
  outputs: [
    { id: 'out', name: 'Out', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'relativeHeight', unit: 'none', primary: true, lens: 'derived' },
  ],
  eval: (p, ins, node) => {
    const result = evaluateSubgraphInstance(p, ins, node)
    return result || newField()
  },
})
