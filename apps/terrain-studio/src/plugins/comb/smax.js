// smax — Crease-free UNION of two heightfields (Quilez smooth max).
//
// The legacy import is CALL-TIME only: every name below is used inside `eval`, which does not
// run until the graph is evaluated. That keeps the legacy<->plugin cycle safe. Anything needed
// at module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { combine, smax } from '../../legacy.js'

export default definePlugin({
  type: "smax",
  cat:"comb",name:"Smooth Max",ins:["A","B"],desc:"Crease-free UNION of two heightfields (Quilez smax) \u2014 the node for merging placed peaks into one massif without a seam.",
    params:[P.slider("k","Smoothness",0.02,0.5,0.15)],
    eval:(p,ins)=>combine(ins[0],ins[1],(a,b)=>smax(a,b,p.k)),
    note:"Union of two <i>surfaces</i> is a <b>max</b>: the merged terrain is whichever is higher. A hard Max/Min at Max does that but leaves a curvature crease where the two cross \u2014 measured across three placed Mountains, this smooths the seam by <b>75%</b>. Use Smooth <i>Min</i> only when you want the lower envelope (carving, intersections); on two peaks it deletes both summits."})
