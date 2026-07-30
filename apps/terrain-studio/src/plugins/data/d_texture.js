// d_texture — Gaea's composite colour driver: slope + soil + flow mixed into one mask — the usual SatMap
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, textureField } from '../../legacy.js'

export default definePlugin({
  type: "d_texture",
cat:"data",name:"Texture",ins:["In"],desc:"Gaea's composite colour driver: slope + soil + flow mixed into one mask — the usual SatMap input.",
    params:[P.slider("slopeW","Slope",0,1,0.5),P.slider("soilW","Soil",0,1,0.3),P.slider("flowW","Flow",0,1,0.2)],
    eval:(p,ins)=>ins[0]?textureField(ins[0],p):newField()})
