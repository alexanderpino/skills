// colormixer — Ordered 2–15 layer biome/material stack. Layer 1 is the base; a standalone masked SatMap o
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { newField } from '../../legacy.js'

export default definePlugin({
  type: "colormixer",
cat:"effect",name:"Color Mixer",ins:["Layer 1","Layer 2","Layer 3"],
    desc:"Ordered 2–15 layer biome/material stack. Layer 1 is the base; a standalone masked SatMap on a higher layer applies only inside its region, with a world-space edge blend. Height passes through from Layer 1.",
    passthrough:true,effect:"colormixer",params:[],
    eval:(p,ins)=>ins[0]||newField()})
