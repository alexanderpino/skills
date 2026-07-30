// satmap — Authors one colour gradient, driven by height, slope, or any field wired into Driver. Chai
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { clamp, histEqualizeField, newField, normalize, slopeOf } from '../../legacy.js'

export default definePlugin({
  type: "satmap",
cat:"effect",name:"SatMap",ins:["In","Driver","Mask"],desc:"Authors one colour gradient, driven by height, slope, or any field wired into Driver. Chain a masked SatMap over another for a simple overlay, or blend separate SatMap branches in Color Blend for explicit biome composition. Height passes through unchanged.",
    passthrough:true,effect:"satmap",
    params:[P.select("gradient","Gradient",null,"Temperate"),
      P.seg("source","Driven by",[["auto","Driver ▸ / Height"],["height","Height"],["slope","Slope"]],"auto"),
      P.select("enhance","Enhance",[["none","None"],["autolevel","Autolevel"],["equalize","Equalize"]],"autolevel"),
      P.seg("reverse","Reverse",[["off","Off"],["on","On"]],"off"),
      P.slider("rangeLo","Range low",0,1,0),P.slider("rangeHi","Range high",0,1,1),
      P.slider("shift","Bias",-0.5,0.5,0),
      P.select("rough","Roughness",[["none","None"],["low","Low"],["med","Medium"],["high","High"],["ultra","Ultra"]],"med"),
      P.slider("hue","Hue",-1,1,0,.01),P.slider("saturation","Saturation",-1,1,0,.01),
      P.slider("lightness","Lightness",-1,1,0,.01)],
    eval:(p,ins,nd)=>{const h=ins[0]||newField();
      const raw=p.source==="slope"?slopeOf(h):p.source==="height"?h:(ins[1]||h);
      if(p.enhance==="equalize")nd._driver=histEqualizeField(raw,{bins:256,amount:1});
      else if(p.enhance==="none"){nd._driver=new Float32Array(raw.length);for(let i=0;i<raw.length;i++)nd._driver[i]=clamp(raw[i],0,1);}
      else nd._driver=normalize(raw);
      nd._mask=ins[2]||null;return h;}})
