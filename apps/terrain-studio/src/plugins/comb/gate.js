// Gate — pass a field through, or substitute a declared closed value (S8.2).
//
// Type-preserving by construction: the closed value is a constant field, so open and closed carry
// the same kind, semantic and unit. A Gate that emitted null or a differently-typed placeholder
// when closed would make every downstream connection conditionally valid, which is the failure the
// "declared closed value" wording exists to prevent.
//
// When closed, the input is not demanded — so a Gate is also the cheap way to switch off an
// expensive subtree without deleting it.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField } from '../../legacy.js'

export default definePlugin({
  type: 'gate',
  cat: 'comb',
  name: 'Gate',
  ins: ['In'],
  desc: 'Pass the input through when open; emit a declared constant when closed. The input is not evaluated while closed.',
  params: [
    P.seg('state', 'State', [['Open', 'open'], ['Closed', 'closed']], 'open'),
    P.number('closedValue', 'Closed value', -100000, 100000, 0, 0.01),
  ],
  inputs: [
    { id: 'in', name: 'In', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'anyScalarRaster', unit: 'none', role: 'data' },
  ],
  outputs: [
    { id: 'out', name: 'Out', kind: 'scalarRaster', storage: 'R32F', components: 1,
      primary: true, lens: 'derived', semanticFrom: { mode: 'inherit', port: 'in' } },
  ],
  demandInputs: (params) => (params.state === 'closed' ? [] : [0]),
  eval: (p, ins) => {
    if (p.state === 'closed') return newField(p.closedValue || 0)
    return ins[0] || newField()
  },
})
