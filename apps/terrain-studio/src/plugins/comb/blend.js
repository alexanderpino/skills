// blend — Mix two fields by a constant factor or a mask input.
//
// The legacy import is CALL-TIME only: every name below is used inside `eval`, which does not
// run until the graph is evaluated. That keeps the legacy<->plugin cycle safe. Anything needed
// at module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { blendField } from '../../legacy.js'

export default definePlugin({
  type: "blend",
  cat:"comb",name:"Blend",ins:["A","B","Mask"],desc:"Mix A→B by a factor or a mask input.",fieldSemantics:"temperature-pair",
    params:[P.slider("factor","Factor",0,1,0.5)],
    eval:(p,ins)=>blendField(ins[0],ins[1],ins[2],p.factor)})
