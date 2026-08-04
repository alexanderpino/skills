// Chokepoint — a typed identity node (S8.1), and Route's sibling.
//
// WHAT MAKES IT DIFFERENT FROM ROUTE IS INTENT, NOT ARITHMETIC, and saying so plainly is the honest
// thing to do: ADR-004 calls both "generic typed identity nodes" and specifies exactly one contract
// for them — output kind, semantic, unit and bytes equal the input's. Route tidies a wire's path;
// a Chokepoint marks a place the author has decided everything upstream must pass through, so a
// later reader can see where a graph narrows. Inventing extra behaviour to justify a second node
// would be inventing terrain the story never asked for.
//
// The typed part is what stops it being decorative. Both ports declare `kindFrom: inherit`, so a
// Chokepoint carries a vectorRaster as faithfully as a scalar one — the story requires "scalar and
// vector fixtures" and, until that existed, connection-time checking refused the only vectorRaster
// in the registry from entering either identity node.
import { definePlugin } from '../../core/registry.js'
import { newField } from '../../legacy.js'

export default definePlugin({
  type: 'chokepoint',
  cat: 'comb',
  name: 'Chokepoint',
  ins: ['In'],
  desc: 'Mark a point every upstream branch passes through. Pure identity: value, type and unit are unchanged.',
  params: [],
  inputs: [
    // The nominal kind/storage pair still has to be consistent for validatePort; `kindFrom` is what
    // says the port adapts to whatever actually arrives.
    { id: 'in', name: 'In', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'anyScalarRaster', unit: 'none', role: 'data', required: true,
      kindFrom: { mode: 'inherit' } },
  ],
  outputs: [
    // No `semantic` or `unit` of its own — validatePortList rejects a port that declares both those
    // and semanticFrom, which is what keeps the inheritance claim from being decorative.
    { id: 'out', name: 'Out', kind: 'scalarRaster', storage: 'R32F', components: 1,
      primary: true, lens: 'derived',
      semanticFrom: { mode: 'inherit', port: 'in' }, kindFrom: { mode: 'inherit', port: 'in' } },
  ],
  // The SAME array object, not a copy. Identity means identity; copying would cost a full field
  // allocation per evaluation to produce a value that is already correct.
  eval: (p, ins) => (ins[0] || newField()),
})
