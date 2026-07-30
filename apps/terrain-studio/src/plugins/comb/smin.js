// smin — Crease-free INTERSECTION of two heightfields (Quilez smooth min).
//
// The legacy import is CALL-TIME only: every name below is used inside `eval`, which does not
// run until the graph is evaluated. That keeps the legacy<->plugin cycle safe. Anything needed
// at module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { combine, smin, smooth } from '../../legacy.js'

export default definePlugin({
  type: "smin",
  cat:"comb",name:"Smooth Min",ins:["A","B"],desc:"Crease-free smooth INTERSECTION \u2014 the lower envelope of two heightfields (Quilez smin). For merging peaks you want Smooth Max instead.",
    params:[P.slider("k","Smoothness",0.02,0.5,0.15)],
    eval:(p,ins)=>combine(ins[0],ins[1],(a,b)=>smin(a,b,p.k))})
