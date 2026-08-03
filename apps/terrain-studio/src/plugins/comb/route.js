// Route — a typed identity node (S8.1).
//
// It moves wires, not values. Output bytes, type and unit equal the input's, exactly. That sounds
// like it does nothing, and doing nothing is precisely the contract: a Route that "helpfully"
// normalised, clamped or re-typed its input would silently change terrain wherever an author used
// it to tidy a graph.
//
// The typed part is what makes it useful rather than decorative. Its output declares
// `semanticFrom: inherit`, so whatever semantic and unit arrive on the input come out the other
// side — a Route carrying a temperature field is still carrying degC, and wiring it into a mask
// slot is still refused. A Route that dropped source type/unit is the armed failure in the story.
import { definePlugin } from '../../core/registry.js'
import { newField } from '../../legacy.js'

export default definePlugin({
  type: 'route',
  cat: 'comb',
  name: 'Route',
  ins: ['In'],
  desc: 'Reroute a wire without changing its value, type or unit. Pure identity.',
  params: [],
  // Declared ports: this is a new plugin and may not use the legacy adapter.
  inputs: [
    { id: 'in', name: 'In', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'anyScalarRaster', unit: 'none', role: 'data', required: true },
  ],
  outputs: [
    // No `semantic` or `unit` of its own — they are inherited from the input at evaluation time.
    // validatePortList rejects a port that declares both, which is what keeps this honest.
    { id: 'out', name: 'Out', kind: 'scalarRaster', storage: 'R32F', components: 1,
      primary: true, lens: 'derived', semanticFrom: { mode: 'inherit', port: 'in' } },
  ],
  // Returns the SAME array object, not a copy: identity means identity, and copying would make a
  // Route cost a full field allocation per evaluation for no reason.
  eval: (p, ins) => (ins[0] || newField()),
})
