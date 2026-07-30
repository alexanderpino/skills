// histeq — CDF equalization — spread the tonal range.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { histEqualizeField, newField } from '../../legacy.js'

export default definePlugin({
  type: "histeq",
cat:"filt",name:"Histogram EQ",ins:["In"],desc:"CDF equalization — spread the tonal range.",
    params:[P.slider("amount","Amount",0,1,1),P.int("bins","Bins",16,256,256)],
    eval:(p,ins)=>ins[0]?histEqualizeField(ins[0],p):newField()})
