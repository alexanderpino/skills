// d_height — Normalized relative elevation map (0 = tile minimum, 1 = tile maximum). Terrain Definition
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { newField, normalize } from '../../legacy.js'

export default definePlugin({
  type: "d_height",
cat:"data",name:"Height",ins:["In"],desc:"Normalized relative elevation map (0 = tile minimum, 1 = tile maximum). Terrain Definition's Base elevation supplies its physical datum for climate.",
    params:[],eval:(p,ins)=>ins[0]?normalize(ins[0]):newField()})
