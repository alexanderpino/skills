// d_peaks — Prominence above the local mean — isolates summits and crests.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, peaksField, resScale } from '../../legacy.js'

export default definePlugin({
  type: "d_peaks",
cat:"data",name:"Peaks",ins:["In"],desc:"Prominence above the local mean — isolates summits and crests.",
    params:[P.int("radius","Radius",1,12,4)],
    eval:(p,ins)=>ins[0]?peaksField(ins[0],{radius:Math.max(1,Math.round(p.radius*resScale()))}):newField()})
