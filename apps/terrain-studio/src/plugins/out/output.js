// output — The final terrain — drives the 3D viewport.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, normalize } from '../../legacy.js'

export default definePlugin({
  type: "output",
cat:"out",name:"Output",ins:["Height"],desc:"The final terrain — drives the 3D viewport.",
    params:[P.seg("norm","Normalize",[["on","On"],["off","Off"]],"on")],
    eval:(p,ins)=>{const f=ins[0]||newField();return p.norm==="on"?normalize(f):f;}})
