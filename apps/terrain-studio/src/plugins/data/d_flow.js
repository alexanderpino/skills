// d_flow — Flow accumulation — the drainage network (priority-flood fill + D8), log-compressed. Where
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { flowField, newField } from '../../legacy.js'

export default definePlugin({
  type: "d_flow",
cat:"data",name:"Flow",ins:["In"],desc:"Flow accumulation — the drainage network (priority-flood fill + D8), log-compressed. Where water runs.",
    params:[P.slider("gain","Gain",0.1,8,1,0.1)],
    eval:(p,ins)=>ins[0]?flowField(ins[0],p):newField()})
