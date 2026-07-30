// d_wind — Builds a physical horizontal wind-vector field from Terrain Definition's prevailing wind, 
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { evaluateTerrainWind, newField, tagWindField } from '../../legacy.js'

export default definePlugin({
  type: "d_wind",
cat:"data",name:"Wind",ins:["Height"],desc:"Builds a physical horizontal wind-vector field from Terrain Definition's prevailing wind, then adjusts it for windward speed-up, lee shelter, and valley channeling.",
    params:[P.slider("speedUp","Crest speed-up",0,1.5,.65,.05,v=>v.toFixed(2)+"×"),
      P.slider("shelter","Lee shelter",0,1,.7,.05,v=>Math.round(v*100)+"%"),
      P.slider("channeling","Valley channeling",0,1,.55,.05,v=>Math.round(v*100)+"%"),
      P.slider("reach","Terrain reach",100,5000,1500,25,v=>Math.round(v)+" m"),
      P.seg("consistency","Mass consistency",[["on","On"],["off","Off"]],"on")],
    eval:(p,ins,nd)=>{
      const h=ins[0]||newField(),wind=evaluateTerrainWind(h,p);nd._wind=wind;
      return tagWindField(wind.encoded,wind.u,wind.v,wind.speed,{heightField:h,
        baseDirection:wind.baseDirection,baseSpeed:wind.baseSpeed,
        divergenceRmsBefore:wind.divergenceRmsBefore,divergenceRmsAfter:wind.divergenceRmsAfter});
    },
    note:"Prevailing direction and speed belong to <b>Terrain Definition</b>, because air crosses biome borders. Wind modifies that regional flow using the heightfield: slopes and crests accelerate wind, upwind relief shelters lee cells, and concave relief turns flow toward valley axes. <b>Mass consistency</b> removes artificial sources and sinks with a bounded Helmholtz–Hodge projection; it is a terrain-climate approximation, not CFD. The scalar thumbnail shows speed, while Display → Wind shows direction as hue and speed as brightness."})
