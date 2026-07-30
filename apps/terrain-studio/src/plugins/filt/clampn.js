// clampn — Clip to a range.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { clampField, newField } from '../../legacy.js'

export default definePlugin({
  type: "clampn",
cat:"filt",name:"Clamp",ins:["In"],desc:"Clip to a range.",
    params:[P.slider("lo","Low",0,1,0),P.slider("hi","High",0,1,1)],
    eval:(p,ins)=>ins[0]?clampField(ins[0],p):newField()})
