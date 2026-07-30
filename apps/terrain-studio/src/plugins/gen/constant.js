// constant — A flat level.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField } from '../../legacy.js'

export default definePlugin({
  type: "constant",
cat:"gen",name:"Constant",ins:[],desc:"A flat level.",
    params:[P.slider("value","Value",0,1,0.5)],eval:(p)=>newField(p.value)})
