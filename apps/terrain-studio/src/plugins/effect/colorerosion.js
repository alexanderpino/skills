// colorerosion — Transports the upstream SatMap stack downhill as mineral pigment, then deposits it along c
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField } from '../../legacy.js'

export default definePlugin({
  type: "colorerosion",
cat:"effect",name:"Color Erosion",ins:["In","Sediment","Mask"],desc:"Transports the upstream SatMap stack downhill as mineral pigment, then deposits it along convergent flow paths. Optional Sediment accepts Deposits, Flow, Soil, or any mask; height passes through unchanged.",
    passthrough:true,effect:"colorerosion",
    params:[P.slider("transport","Transport distance",0,3,1.43,.01),
      P.slider("density","Sediment density",0,1,.2,.01),P.slider("blend","Blend",0,1,.89,.01),
      P.slider("hold","Color hold",0,1,.89,.01),P.slider("flow","Flow volume",0,1,0,.01),
      P.seg("laminar","Laminar flow",[["off","Off"],["on","On"]],"off"),
      P.slider("diffusion","Diffusion",0,1,0,.01),P.seed("seed","Seed",7),
      P.select("blendMode","Blend mode",[["normal","Normal"],["max","Max"],["min","Min"],["multiply","Multiply"],["screen","Screen"],["overlay","Overlay"]],"normal")],
    eval:(p,ins,nd)=>{const h=ins[0]||newField();nd._height=h;nd._sediment=ins[1]||null;nd._mask=ins[2]||null;return h;},
    note:"The <b>Mask</b> gates the final colour effect: black preserves the upstream SatMap, white applies the transported pigment, and grey interpolates. It does not alter terrain height or rerun the transport route. Select the Mask connection to inspect its live range and coverage."})
