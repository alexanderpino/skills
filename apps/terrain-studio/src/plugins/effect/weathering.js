// weathering — A terrain-aware colour ageing pass: exposed relief can bleach or brighten, while sheltered
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField } from '../../legacy.js'

export default definePlugin({
  type: "weathering",
cat:"effect",name:"Weathering",ins:["In","Mask"],desc:"A terrain-aware colour ageing pass: exposed relief can bleach or brighten, while sheltered recesses collect dirt. Includes scale, creep, inversion, HSL post controls, opacity, and blend mode; height passes through unchanged.",
    passthrough:true,effect:"weathering",
    params:[P.slider("scale","Scale",.02,1,.72,.01),P.slider("creep","Creep",0,1,.27,.01),
      P.slider("amount","Amount",0,1,.26,.01),
      P.seg("washed","Washed out",[["off","Off"],["on","On"]],"on"),
      P.seg("inverse","Inverse",[["off","Off"],["on","On"]],"off"),
      P.slider("dirt","Dirt",0,1,.01,.01),P.seg("darker","Darker",[["off","Off"],["on","On"]],"on"),
      P.slider("hue","Hue",-1,1,0,.01),P.slider("saturation","Saturation",-1,1,0,.01),
      P.slider("lightness","Lightness",-1,1,0,.01),P.slider("opacity","Opacity",0,1,1,.01),
      P.select("blendMode","Blend mode",[["normal","Normal"],["max","Max"],["min","Min"],["multiply","Multiply"],["screen","Screen"],["overlay","Overlay"]],"normal")],
    eval:(p,ins,nd)=>{const h=ins[0]||newField();nd._height=h;nd._mask=ins[1]||null;return h;}})
