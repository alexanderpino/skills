// import — A real / external heightmap loaded as a base.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { buildDemFromSource, fieldLen, newField, radialField } from '../../legacy.js'

export default definePlugin({
  type: "import",
cat:"gen",name:"Import DEM",ins:[],desc:"A real / external heightmap loaded as a base.",
    // Keep the stable `scale` key: old documents retain their exact real multiplier while the
    // logarithmic track makes attenuation and amplification equally addressable around 1x.
    params:[P.log("scale","Height multiplier",.01,100,1,
      v=>(v<.1?v.toFixed(2):v<10?v.toFixed(1):v.toFixed(0))+"\u00d7",false)],
    eval:(p,ins,node)=>{if((!node._dem||node._dem.length!==fieldLen())&&(node._demImg||node._demRaw))buildDemFromSource(node);
      if(!node._dem)return radialField();const o=newField();for(let i=0;i<o.length;i++)o[i]=node._dem[i]*p.scale;return o;}})
