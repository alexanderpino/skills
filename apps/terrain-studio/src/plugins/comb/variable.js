// Variable — read a document variable as a constant field (S8.3).
//
// Referenced by stable ID, never by display name, for the same reason edges carry port ids rather
// than slot indices: rename "sea level" to "base level" and every reference must keep working. A
// name-keyed design breaks silently on a rename, and the breakage looks like a terrain change.
//
// An unknown id yields a zero field rather than throwing, so deleting a variable leaves a graph
// that still opens and still renders — with a visible error in the inspector rather than a blank
// app. The `info` panel reports which id resolved and from which scope frame.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, currentScope } from '../../legacy.js'

export default definePlugin({
  type: 'variable',
  cat: 'comb',
  name: 'Variable',
  ins: [],
  desc: 'Emit a document variable as a constant field. Referenced by stable id, so renaming is safe.',
  params: [P.text('varId', 'Variable id', 'seaLevel', 1)],
  inputs: [],
  outputs: [
    { id: 'out', name: 'Out', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'relativeHeight', unit: 'none', primary: true, lens: 'derived' },
  ],
  info: (node) => {
    const hit = currentScope().lookup(String(node.params.varId || '').trim())
    if (!hit) return `<b>VAR_UNKNOWN</b> — no variable with id ${JSON.stringify(node.params.varId)}`
    return `<b>${hit.variable.name}</b> = ${hit.variable.value} ${hit.variable.unit} <span class="muted">(frame ${hit.frame})</span>`
  },
  // The declared output above is a PLACEHOLDER. A variable carries a unit, and hard-coding
  // unit:'none' here meant a variable declared in metres presented as dimensionless — so it wired
  // straight into an `anyMask` port, whose unitPolicy 'none-only' exists precisely to refuse that.
  // resolvePorts refines the descriptor per instance from the variable actually referenced, so the
  // declaration and the value agree.
  resolvePorts: (node) => {
    const hit = currentScope().lookup(String((node && node.params && node.params.varId) || '').trim())
    const unit = hit ? hit.variable.unit : 'none'
    return {
      inputs: [],
      outputs: [{ id: 'out', name: 'Out', kind: 'scalarRaster', storage: 'R32F', components: 1,
        semantic: unit === 'none' ? 'relativeHeight' : 'height', unit, primary: true, lens: 'derived' }],
    }
  },
  eval: (p) => {
    const hit = currentScope().lookup(String(p.varId || '').trim())
    return newField(hit ? hit.variable.value : 0)
  },
})
