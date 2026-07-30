// blur — Separable Gaussian smoothing.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { blurField, maskApply, newField, resScale } from '../../legacy.js'

export default definePlugin({
  type: "blur",
cat:"filt",name:"Blur",ins:["In","Mask"],desc:"Separable Gaussian smoothing.",fieldSemantics:"preserve-primary",
    params:[P.slider("radius","Radius",1,10,2,1,v=>v|0)],
    eval:(p,ins)=>ins[0]?maskApply(ins[0],blurField(ins[0],{radius:Math.max(1,Math.round(p.radius*resScale()))}),ins[1]):newField()})
