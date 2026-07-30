// worley — Cellular / Worley noise — plates and cracks.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { worleyField } from '../../legacy.js'

export default definePlugin({
  type: "worley",
cat:"gen",name:"Voronoi",ins:[],desc:"Cellular / Worley noise — plates and cracks.",
    params:[P.seed("seed","Seed",5),P.log("freq","Cell density",2,16,6,v=>v.toFixed(2),false),P.seg("mode","Mode",[["f2f1","F2−F1"],["f1","F1"],["invf1","1−F1"]],"f2f1")],
    eval:(p)=>worleyField({seed:p.seed,freq:p.freq,mode:p.mode})})
