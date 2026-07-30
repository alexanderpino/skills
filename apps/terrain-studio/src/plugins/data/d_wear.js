// d_wear — Exposed, convex, steep ground — the edges erosion strips first.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, wearField } from '../../legacy.js'

export default definePlugin({
  type: "d_wear",
cat:"data",name:"Wear",ins:["In"],desc:"Exposed, convex, steep ground — the edges erosion strips first.",
    params:[P.slider("strength","Strength",0.2,3,1,0.1)],
    eval:(p,ins)=>ins[0]?wearField(ins[0],p):newField()})
