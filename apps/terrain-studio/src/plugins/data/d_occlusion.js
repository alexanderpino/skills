// d_occlusion — Horizon-based ambient occlusion — crevices and enclosed valleys dark, open peaks light.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, occlusionField } from '../../legacy.js'

export default definePlugin({
  type: "d_occlusion",
cat:"data",name:"Occlusion",ins:["In"],desc:"Horizon-based ambient occlusion — crevices and enclosed valleys dark, open peaks light.",
    params:[P.slider("radius","Radius",0.01,0.2,0.06,0.01),P.int("dirs","Directions",4,16,8)],
    eval:(p,ins)=>ins[0]?occlusionField(ins[0],p):newField()})
