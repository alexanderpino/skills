// shape — An SDF placement mask — circle/box/line positioned in the terrain, with a soft edge. Wire 
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { shapeField } from '../../legacy.js'

export default definePlugin({
  type: "shape",
cat:"gen",name:"Shape",ins:[],desc:"An SDF placement mask — circle/box/line positioned in the terrain, with a soft edge. Wire it into any node's Mask input to confine that effect, or erode it directly into a landform (Gaea's Mask-as-Primitive).",
    params:[P.seg("kind","Kind",[["circle","Circle"],["box","Box"],["line","Line"]],"circle"),
      P.slider("x","Position X",0,1,0.5),P.slider("y","Position Y",0,1,0.5),
      P.slider("size","Size",0.02,1.5,0.4),P.slider("aspect","Aspect",0.05,4,1,0.05),
      P.slider("angle","Angle",0,360,0,1,v=>(v|0)+"\u00b0"),
      P.slider("falloff","Falloff",0,1,0.25),
      P.seg("invert","Invert",[["off","Off"],["on","On"]],"off")],
    eval:(p)=>shapeField(p)})
