// normalizen — Remap the field minimum to 0 and maximum to 1, optionally through a biome mask.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { lerp, maskApply, newField, normalize } from '../../legacy.js'

export default definePlugin({
  type: "normalizen",
cat:"filt",name:"Normalize",ins:["In","Mask"],desc:"Remap the field minimum to 0 and maximum to 1, optionally through a biome mask.",
    params:[P.slider("amount","Amount",0,1,1,.01)],
    eval:(p,ins)=>{
      if(!ins[0])return newField();
      const base=ins[0],normal=normalize(base);
      if(p.amount<1)for(let i=0;i<normal.length;i++)normal[i]=lerp(base[i],normal[i],p.amount);
      return maskApply(base,normal,ins[1]);
    },
    note:"The range is measured over the whole input field, then blended through <b>Mask</b>: black preserves the original height, white applies the normalized height, and grey makes a soft transition. Keeping range measurement independent of the mask prevents biome borders from changing the normalization whenever their falloff is edited."})
