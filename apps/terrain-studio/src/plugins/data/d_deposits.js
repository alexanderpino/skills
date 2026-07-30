// d_deposits — Soil / sediment: the depth loose material piles into hollows (morphological closing − surf
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { depositsField, newField, resScale } from '../../legacy.js'

export default definePlugin({
  type: "d_deposits",
cat:"data",name:"Deposits",ins:["In"],desc:"Soil / sediment: the depth loose material piles into hollows (morphological closing − surface).",
    // refDepth is what keeps the mask PHYSICAL: the fill depth (metres) that saturates it.
    // The old normalize() output was identical for a terrain at any amplitude.
    params:[P.int("radius","Radius",1,10,3),
      P.slider("refDepth","Full-mask depth",5,120,25,1,v=>(v|0)+" m")],
    eval:(p,ins)=>ins[0]?depositsField(ins[0],{radius:Math.max(1,Math.round(p.radius*resScale())),
      refDepth:p.refDepth==null?25:p.refDepth}):newField()})
