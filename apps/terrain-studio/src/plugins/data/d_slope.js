// d_slope — Steepness as a grayscale field (0 flat → 1 vertical). The classic cliff/bench colour drive
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { newField, normalize, slopeOf } from '../../legacy.js'

export default definePlugin({
  type: "d_slope",
cat:"data",name:"Slope",ins:["In"],desc:"Steepness as a grayscale field (0 flat → 1 vertical). The classic cliff/bench colour driver.",
    params:[],eval:(p,ins)=>ins[0]?normalize(slopeOf(ins[0])):newField()})
