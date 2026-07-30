// d_curvature — Zevenbergen–Thorne curvature: convex ridges/lips vs concave valley floors (0.5 = flat).
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { curvatureField, newField } from '../../legacy.js'

export default definePlugin({
  type: "d_curvature",
cat:"data",name:"Curvature",ins:["In"],desc:"Zevenbergen–Thorne curvature: convex ridges/lips vs concave valley floors (0.5 = flat).",
    params:[P.seg("kind","Kind",[["profile","Profile"],["plan","Plan"],["mean","Mean"]],"profile"),
      P.slider("strength","Strength",0.1,4,1,0.1)],
    eval:(p,ins)=>ins[0]?curvatureField(ins[0],p):newField()})
