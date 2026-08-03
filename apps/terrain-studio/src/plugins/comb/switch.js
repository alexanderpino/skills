// Switch — select one of several branches without computing the others (S8.2).
//
// The point is not the selection; a Blend with a 0/1 factor could do that. The point is that an
// unselected branch is NEVER EVALUATED. Before this, every input of every node was evaluated
// eagerly, so a graph offering three expensive alternatives paid for all three and used one.
//
// `demandInputs` is what makes that real: the evaluator asks the plugin which slots can affect its
// result given its current params, and only recurses into those. All 82 other types have no such
// hook and therefore demand every slot, which is exactly what they meant before.
//
// TYPE DISCIPLINE. Branches must be mutually compatible — same value kind, semantic and unit —
// because the output is whichever one is selected, and a Switch whose output type depended on a
// dropdown would make every downstream connection conditionally legal. The output therefore
// inherits from branch A and canConnect refuses a B that disagrees with it.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField } from '../../legacy.js'

const BRANCHES = ['A', 'B', 'C']

export default definePlugin({
  type: 'switch',
  cat: 'comb',
  name: 'Switch',
  ins: BRANCHES,
  desc: 'Pass through exactly one branch. Unselected branches are never evaluated.',
  params: [P.seg('branch', 'Branch', BRANCHES.map((b, i) => [b, String(i)]), '0')],
  inputs: BRANCHES.map((name, i) => ({
    id: 'branch' + name, name, kind: 'scalarRaster', storage: 'R32F', components: 1,
    semantic: 'anyScalarRaster', unit: 'none', role: 'data', legacySlot: i,
  })),
  outputs: [
    { id: 'out', name: 'Out', kind: 'scalarRaster', storage: 'R32F', components: 1,
      primary: true, lens: 'derived', semanticFrom: { mode: 'inherit', port: 'branchA' } },
  ],
  // The whole story, in one function.
  demandInputs: (params) => [Math.max(0, Math.min(BRANCHES.length - 1, parseInt(params.branch, 10) || 0))],
  eval: (p, ins) => {
    const i = Math.max(0, Math.min(BRANCHES.length - 1, parseInt(p.branch, 10) || 0))
    return ins[i] || newField()
  },
})
