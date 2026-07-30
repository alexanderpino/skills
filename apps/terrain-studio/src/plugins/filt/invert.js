// invert — 1 − height.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { invertField, newField } from '../../legacy.js'

export default definePlugin({
  type: "invert",
cat:"filt",name:"Invert",ins:["In"],desc:"1 − height.",params:[],
    eval:(p,ins)=>ins[0]?invertField(ins[0]):newField()})
