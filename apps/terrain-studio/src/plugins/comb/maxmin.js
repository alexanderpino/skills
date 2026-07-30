// maxmin — Union (max) or intersection (min) of two fields.
//
// The legacy import is CALL-TIME only: every name below is used inside `eval`, which does not
// run until the graph is evaluated. That keeps the legacy<->plugin cycle safe. Anything needed
// at module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { combine } from '../../legacy.js'

export default definePlugin({
  type: "maxmin",
  cat:"comb",name:"Max / Min",ins:["A","B"],desc:"Union (max) or intersection (min).",fieldSemantics:"temperature-pair",
    params:[P.seg("op","Op",[["max","Max"],["min","Min"]],"max")],
    eval:(p,ins)=>combine(ins[0],ins[1],p.op==="max"?Math.max:Math.min)})
