// tempmask — Selects a physical Celsius band from a Temperature field for snow, vegetation, biome, mate
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { clamp, newField, temperatureCFromField } from '../../legacy.js'

export default definePlugin({
  type: "tempmask",
cat:"mask",name:"Temperature select",ins:["Temperature"],desc:"Selects a physical Celsius band from a Temperature field for snow, vegetation, biome, material, or scatter masks.",
    params:[P.number("lo","Minimum temperature",-100,1400,-10,.5,"°C"),
      P.number("hi","Maximum temperature",-100,1400,15,.5,"°C"),
      P.number("falloff","Transition",0,100,3,.5,"°C"),
      P.seg("invert","Invert",[["off","Off"],["on","On"]],"off")],
    eval:(p,ins)=>{
      const c=temperatureCFromField(ins[0]);if(!c)return newField();
      const out=new Float32Array(c.length),lo=Math.min(p.lo,p.hi),hi=Math.max(p.lo,p.hi),f=Math.max(0,p.falloff);
      const ss=(a,b,x)=>{if(b<=a)return x>=b?1:0;const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);};
      for(let i=0;i<out.length;i++){
        const v=ss(lo-f,lo,c[i])*(1-ss(hi,hi+f,c[i]));
        out[i]=p.invert==="on"?1-v:v;
      }
      return out;
    },
    note:"Temperature Select converts a physical temperature interval into a regular 0–1 mask. Feed it into SatMap, Color Blend, Color Mixer branches, scatter, or any Mask port. Multiple selectors over one modified Temperature field are the basis for consistent tundra, alpine, temperate, arid, and volcanic biome bands."})
