// d_windmodify — Sets a regional wind direction and speed inside a biome, weather, or authored mask while p
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { WIND_MAX_MPS, clamp, lerp, newField, projectWindMassConsistent, tagWindField, terrainDef, windBearingVector, widthForLength, windDivergenceRms, windVectorFromField } from '../../legacy.js'

export default definePlugin({
  type: "d_windmodify",
cat:"data",name:"Wind Modify",ins:["Wind","Driver","Mask"],desc:"Sets a regional wind direction and speed inside a biome, weather, or authored mask while preserving the physical vector field outside it.",
    params:[P.slider("direction","Target wind from",0,359,300,1,v=>(v|0)+"° map"),
      P.slider("speed","Target speed",0,60,10,.5,v=>v.toFixed(1)+" m/s"),
      P.slider("amount","Amount",0,1,1,.01,v=>Math.round(v*100)+"%"),
      // Project (default): mass consistency survives the override, at the cost of flow bleeding
      // across the mask seam (a hard half-map override measured -22% on the far side - that IS
      // conservation talking). Preserve exactly: the authored values hold to 1e-3 everywhere,
      // and the divergence the seam introduces (+39% measured) is knowingly kept.
      P.tabs("consistency","Mass consistency",[["on","Project"],["off","Preserve exactly"]],"on")],
    eval:(p,ins,nd)=>{
      const base=ins[0],meta=windVectorFromField(base);
      if(!meta){
        nd._wind=null;nd._inputError=base?"Wind input requires a physical Wind field":"Connect a Wind field";
        return newField();
      }
      nd._inputError=null;
      const source=ins[1],mask=ins[2],N=base.length,u=new Float32Array(N),v=new Float32Array(N);
      const speed=new Float32Array(N),encoded=new Float32Array(N),target=windBearingVector(p.direction);
      for(let i=0;i<N;i++){
        const w=clamp((source?source[i]:1)*(mask?mask[i]:1)*(p.amount==null?1:p.amount),0,1);
        const s0=meta.speed[i],a0=s0>1e-6?Math.atan2(meta.v[i],meta.u[i]):Math.atan2(target[1],target[0]);
        const a1=Math.atan2(target[1],target[0]),da=Math.atan2(Math.sin(a1-a0),Math.cos(a1-a0));
        const a=a0+da*w,s=lerp(s0,p.speed,w);
        u[i]=Math.cos(a)*s;v[i]=Math.sin(a)*s;speed[i]=s;encoded[i]=s/WIND_MAX_MPS;
      }
      // The override reintroduces divergence at every mask seam (+39% measured at a hard
      // half-map mask - the exact biome workflow the note prescribes), so RE-PROJECT after the
      // blend: mass consistency must survive regional editing. The diagnostics are stamped with
      // THIS projection's before/after - the first version stamped before=inherited and
      // after=post-override, an inverted signal under the shared key names.
      // fieldW(), NOT sqrt(N). A hex field is RES x round(RES*2/sqrt(3)), so its cell count is
      // never a perfect square and this guessed 550 where the width is 512 — measured. Both
      // helpers below take a WIDTH and derive the row count themselves via latticeRows, so they
      // were already hex-correct; handing them a fabricated width made the divergence sum and the
      // mass-consistency projection read across row boundaries. Every sample stayed finite, which
      // is why nothing caught it: the wind was simply wrong, quietly, on hex.
      // widthForLength, NOT sqrt(N) and NOT fieldW(). sqrt(N) is exact on square and returns 550
      // against a real 512 on hex, so both helpers below — which take a WIDTH and derive rows
      // themselves — read across row boundaries. fieldW() is equally wrong: this node is also
      // evaluated on fields that are not the working grid, by atFeatureScale and by fixtures.
      const n2=widthForLength(N),cell=terrainDef.scale/n2;
      const before=windDivergenceRms(u,v,n2,cell);
      const doProject=p.consistency!=="off";
      const proj=doProject?projectWindMassConsistent(u,v,n2,cell,Math.min(96,Math.max(36,Math.round(Math.sqrt(n2)*6)))):{u,v};
      const uP=proj.u,vP=proj.v;
      for(let i=0;i<N;i++){let sp=Math.hypot(uP[i],vP[i]);
        if(sp>WIND_MAX_MPS){const f2=WIND_MAX_MPS/sp;uP[i]*=f2;vP[i]*=f2;sp=WIND_MAX_MPS;}
        speed[i]=sp;encoded[i]=sp/WIND_MAX_MPS;}
      const after=windDivergenceRms(uP,vP,n2,cell);
      nd._wind={u:uP,v:vP,speed,encoded,baseDirection:meta.baseDirection,baseSpeed:meta.baseSpeed,
        divergenceRmsBefore:before,divergenceRmsAfter:after,simulationResolution:n2};
      return tagWindField(encoded,uP,vP,speed,{heightField:meta.heightField,
        baseDirection:meta.baseDirection,baseSpeed:meta.baseSpeed,
        divergenceRmsBefore:before,divergenceRmsAfter:after});
    },
    note:"Use this for a regional circulation override, not as a property baked into a SatMap. Reuse the biome's Draw Mask in <b>Mask</b>, set its local wind, and chain further Wind Modify nodes for other regions. Direction follows the shortest angular path through soft mask edges, so an ecotone rotates the flow rather than snapping it."})
