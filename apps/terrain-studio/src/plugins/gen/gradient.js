// gradient — Linear or radial ramp — a base slope or falloff.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P, WHEN } from '../../core/params.js'
import { gradientField, radialField } from '../../legacy.js'

export default definePlugin({
  type: "gradient",
cat:"gen",name:"Gradient",ins:[],desc:"Linear or radial ramp — a base slope or falloff.",
    params:[P.tabs("kind","Kind",[["lin","Linear"],["rad","Radial"]],"lin"),
      WHEN(P.slider("angle","Angle",0,360,35,1,v=>v|0),"kind","lin")],
    eval:(p)=>p.kind==="rad"?radialField():gradientField(p.angle)})
