// terrace — Snap to stratified benches.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { maskApply, newField, terraceField } from '../../legacy.js'

export default definePlugin({
  type: "terrace",
cat:"filt",name:"Terrace",ins:["In","Mask"],desc:"Snap to stratified benches.",
    params:[P.int("steps","Steps",2,24,8),P.slider("sharp","Sharpness",0,1,0.6)],
    eval:(p,ins)=>ins[0]?maskApply(ins[0],terraceField(ins[0],p),ins[1]):newField()})
