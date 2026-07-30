// erosion2 — Advanced multi-scale hydraulic erosion: broad ravines first, nested gullies second, then s
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P, GROUP } from '../../core/params.js'
import { erosion2Field, lerp, maskApply, newField } from '../../legacy.js'

export default definePlugin({
  type: "erosion2",
cat:"ero",name:"Erosion 2",ins:["In","Mask"],
    desc:"Advanced multi-scale hydraulic erosion: broad ravines first, nested gullies second, then sediment and shape relaxation.",
    params:[
      GROUP(P.slider("duration","Duration",0,1,.46,.01),"General"),
      GROUP(P.slider("downcut","Downcutting",0,1,.58,.01),"General"),
      GROUP(P.slider("erosionScale","Erosion scale",0,1,.38,.01,v=>lerp(1,7,v).toFixed(1)+"×"),"General"),
      GROUP(P.seed("seed","Seed",17),"General"),
      GROUP(P.slider("suspended","Suspended load",0,1,.36,.01),"Sediment discharge"),
      GROUP(P.slider("bed","Bed load",0,1,.30,.01),"Sediment discharge"),
      GROUP(P.slider("coarse","Coarse sediments",0,1,.22,.01),"Sediment discharge"),
      GROUP(P.slider("depositBoost","Deposition boost",0,1,.18,.01),"Sediment discharge"),
      GROUP(P.slider("shape","Shape",0,1,.28,.01),"Shape"),
      GROUP(P.slider("shapeSharp","Shape sharpness",0,1,.42,.01),"Shape"),
      GROUP(P.slider("shapeDetail","Shape detail scale",0,1,.72,.01),"Shape")],
    eval:(p,ins)=>ins[0]?maskApply(ins[0],erosion2Field(ins[0],p),ins[1]):newField(),
    note:"<b>Erosion 2</b> is a clean-room multi-scale composition over Terrain Studio's owned hydraulic and thermal kernels, following Gaea's public control contract rather than claiming its proprietary algorithm. <b>Duration</b> controls simulation travel; <b>Downcutting</b> controls incision; <b>Erosion scale</b> sets the largest ravines. A shorter near-native pass nests fine gullies inside those broad structures. Suspended, bed, and coarse loads jointly control deposition mobility; Shape adds hydraulic/thermal reshaping and Shape sharpness retains crisp interfluves.<br><br>For a Canyon, start with moderate Duration and Downcutting. Raise Erosion scale before Duration when you want wider ravines instead of noisy scratches. The bundled Canyon Landscape setup supplies a conservative starting point."})
