// slopemask — Mask by steepness — cliffs vs benches.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, slopeSelect } from '../../legacy.js'

export default definePlugin({
  type: "slopemask",
cat:"mask",name:"Slope select",ins:["In"],desc:"Mask by steepness — cliffs vs benches.",
    params:[P.slider("lo","Low",0,1,0.12),P.slider("hi","High",0,1,0.55),P.slider("falloff","Falloff",0.01,0.4,0.12)],
    eval:(p,ins)=>ins[0]?slopeSelect(ins[0],p):newField()})
