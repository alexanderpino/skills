// transform — Translate, rotate and scale the terrain — Gaea's Transform. Scale >1 magnifies (same terra
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P, WHEN } from '../../core/params.js'
import { XF, setXF, evalExact, exactChain, inputEdge, maskApply, newField, terrainDef, transformField, xfFromParams, xfMul } from '../../legacy.js'

export default definePlugin({
  type: "transform",
cat:"filt",name:"Transform",ins:["In","Mask"],desc:"Translate, rotate and scale the terrain — Gaea's Transform. Scale >1 magnifies (same terrain over a smaller area); <1 shrinks it.",fieldSemantics:"preserve-primary",
    params:[P.tabs("mode","Sampling",[["auto","Exact"],["raster","Raster"]],"auto"),
      P.slider("scale","Scale",0.1,4,1,0.05,v=>v.toFixed(2)+"\u00d7"),
      P.slider("aspect","Scale Y",0.25,4,1,0.05,v=>v.toFixed(2)+"\u00d7"),
      P.slider("angle","Rotation",0,360,0,1,v=>(v|0)+"\u00b0"),
      P.slider("offX","Move X",-1,1,0,0.01,v=>Math.round(v*terrainDef.scale)+" m"),
      P.slider("offY","Move Y",-1,1,0,0.01,v=>Math.round(v*terrainDef.scale)+" m"),
      P.slider("pivX","Pivot X",0,1,0.5,0.01,v=>Math.round(v*terrainDef.scale)+" m"),
      P.slider("pivY","Pivot Y",0,1,0.5,0.01,v=>Math.round(v*terrainDef.scale)+" m"),
      WHEN(P.seg("edge","Edges",[["clamp","Clamp"],["wrap","Wrap"],["mirror","Mirror"]],"clamp"),"mode","raster")],
    // PLACE BEFORE YOU SAMPLE. If everything upstream is procedural, push this placement down into
    // the generators' coordinates and re-evaluate — exact, and the terrain simply continues past the
    // old tile edge instead of clamping. Otherwise fall back to resampling the finished raster.
    eval:(p,ins,node)=>{
      const src=inputEdge(node.id,0);
      // The Mask branch never has to be procedural: masking is a post-process lerp against the
      // UNtransformed input, so only slot 0 decides whether the exact path is available.
      if(p.mode!=="raster"&&src&&exactChain(src.from)){
        // setXF, not `XF=` — XF is an IMPORTED binding here and imported bindings are immutable in
        // the importing module. A direct assignment throws "Assignment to constant variable", which
        // is exactly how the digest caught this: 59 of 60 node types covered, transform SKIPPED.
        // The setter lives with the declaration in legacy.js; same rule that governs the test
        // bridge's written symbols.
        const prev=XF;setXF(xfMul(xfFromParams(p),prev));  // compose: N transforms, ONE evaluation
        let f;try{f=evalExact(src.from,new Set());}finally{setXF(prev);}
        node._xfMode="exact";
        return maskApply(ins[0]||newField(),f||newField(),ins[1]);
      }
      node._xfMode=ins[0]?"raster":"none";
      return ins[0]?maskApply(ins[0],transformField(ins[0],p),ins[1]):newField();},
    info:(nd)=>(nd._xfMode==="raster"
      ? "<b>Raster resample.</b> The input cannot be re-evaluated — an erosion sim, a blur, an imported DEM — so the finished heightmap is filtered. Bilinear resampling is a low-pass: on fBm here it costs ~25% of the fine detail for one non-integer move and ~54% over four. Put the Transform <i>below</i> the erosion to place exactly instead."
      : "<b>Exact placement.</b> Everything upstream is procedural, so it is re-evaluated at transformed coordinates rather than resampled: no filtering, no detail loss, and the terrain continues past the old tile edge instead of clamping (Edges is unused). Stacked Transforms compose into one matrix, so they still cost one evaluation.")
      + "<br><br>Rotation is about the <b>up axis</b> — the only rotation a heightfield admits, since tipping the surface would make it multi-valued (two heights over one point). <b>Pivot</b> is the point rotation and scale turn about: centred spins a feature in place, moved swings it around that point. <b>Mask</b> confines the move to where it is bright."})
