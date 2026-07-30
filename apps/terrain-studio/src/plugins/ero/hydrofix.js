// hydrofix — Low-amplitude drainage conditioning: promotes longer continuous flow paths without replaci
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P, GROUP } from '../../core/params.js'
import { hydroFixField, maskApply, newField } from '../../legacy.js'

export default definePlugin({
  type: "hydrofix",
cat:"ero",name:"HydroFix",ins:["In","Mask"],
    desc:"Low-amplitude drainage conditioning: promotes longer continuous flow paths without replacing the landscape.",
    params:[GROUP(P.slider("fix","Hydro fix",0,1,.52,.01),"Drainage"),
      GROUP(P.slider("downcut","Downcutting",0,1,.34,.01),"Drainage")],
    eval:(p,ins)=>ins[0]?maskApply(ins[0],hydroFixField(ins[0],p),ins[1]):newField(),
    note:"<b>HydroFix</b> routes on a priority-filled working copy, softly downcuts high-accumulation corridors in the original heightfield, and enforces only the tiny descent required for connected receivers. It is intentionally subtle: use it after Erosion 2 to repair broken flow paths, or before a flow-dependent node to prepare noisy terrain. It does not fill the rendered terrain or turn basins into flat plates."})
