// levels — Clip range + gamma + output range.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { levelsField, newField } from '../../legacy.js'

export default definePlugin({
  type: "levels",
cat:"filt",name:"Levels",ins:["In"],desc:"Clip range + gamma + output range.",
    params:[P.slider("inLo","In low",0,1,0),P.slider("inHi","In high",0,1,1),P.slider("gamma","Gamma",0.2,3,1),
      P.slider("outLo","Out low",0,1,0),P.slider("outHi","Out high",0,1,1)],
    eval:(p,ins)=>ins[0]?levelsField(ins[0],p):newField()})
