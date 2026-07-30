// warp — Domain-warp the input by internal noise.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { maskApply, newField, warpField } from '../../legacy.js'

export default definePlugin({
  type: "warp",
cat:"filt",name:"Warp",ins:["In","Mask"],desc:"Domain-warp the input by internal noise.",fieldSemantics:"preserve-primary",
    params:[P.log("strength","Strength",.001,.4,.12,v=>v===0?"0":v<.01?v.toFixed(3):v.toFixed(2)),
      P.log("freq","Frequency",.5,8,3,v=>v<1?v.toFixed(2):v.toFixed(1),false),P.seed("seed","Seed",7)],
    eval:(p,ins)=>ins[0]?maskApply(ins[0],gpuReady()?gpuWarp(ins[0],p):warpField(ins[0],p),ins[1]):newField()})
