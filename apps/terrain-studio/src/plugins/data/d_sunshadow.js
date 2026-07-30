// d_sunshadow — Deterministic terrain-space solar visibility. White is sunlit; black is occluded by the he
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { evaluateSunShadowMap, newField } from '../../legacy.js'

export default definePlugin({
  type: "d_sunshadow",
cat:"data",name:"Sun Shadow",ins:["Height"],desc:"Deterministic terrain-space solar visibility. White is sunlit; black is occluded by the heightfield horizon. Unlike a viewport cascade shadow, this field is stable, blendable, and exportable.",
    params:[P.slider("reach","Horizon reach",100,10000,2750,25,v=>Math.round(v)+" m"),
      P.slider("softness","Softness",0,3,1,.05,v=>v.toFixed(2)+"×")],
    eval:(p,ins,nd)=>{
      if(!ins[0]){nd._solarShadow=newField();nd._solarExposure=newField();return nd._solarShadow;}
      const maps=evaluateSunShadowMap(ins[0],p);
      nd._solarShadow=maps.solarShadow;nd._solarExposure=maps.solarExposure;return maps.solarShadow;
    },
    note:"This node is a <b>terrain-space analysis map</b>: white means the climate sun reaches the surface and black means terrain blocks it. It uses a logarithmic heightfield-horizon march followed by a spatial penumbra filter. A cascaded shadow map is intentionally not used here because cascades are fitted to the current camera frustum and therefore change as the view moves."})
