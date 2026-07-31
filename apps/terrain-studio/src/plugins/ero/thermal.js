// thermal — Talus: material above repose slides down.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { gpuReady, gpuThermal } from '../../core/gpu.js'
import { P, WHEN } from '../../core/params.js'
import { BUILD_QUALITY, atFeatureScale, cellSizeM, maskApply, newField, resScale, terrainDef, thermalOn } from '../../legacy.js'

// HeightField values are not colour channels: negative elevations and values above one are valid.
// The only value-domain invariant thermal erosion requires is finiteness. Failing at the node
// boundary keeps a single NaN/Infinity from being redistributed through every neighbour for every
// iteration and becoming a terrain-sized forest of spikes.
const finiteHeightField = (field, label) => {
  if (!ArrayBuffer.isView(field)) throw new TypeError(`Thermal erosion ${label} must be a typed height field`)
  for (let i = 0; i < field.length; i++) {
    if (!Number.isFinite(field[i])) {
      throw new RangeError(`Thermal erosion ${label} contains a non-finite height at sample ${i}`)
    }
  }
  return field
}

const finiteInRange = (value, lo, hi, label) => {
  if (!Number.isFinite(value) || value < lo || value > hi) {
    throw new RangeError(`Thermal erosion ${label} must be finite and in [${lo}, ${hi}]`)
  }
  return value
}

export default definePlugin({
  type: "thermal",
cat:"ero",name:"Thermal erosion",ins:["In","Mask"],desc:"Talus: material above repose slides down.",
    note:"Closed/no-flux terrain edges. Heights remain finite but unbounded. Mask is an effect composite, not a material wall.",
    // Real scale is the DEFAULT: with cell units shipping as default, the Repose slider did not
    // exist on a fresh node and repose 25 vs 45 measured IDENTICAL slope percentiles - the
    // node's only physical control was unreachable out of the box. Cell units stay as the
    // escape hatch (existing saved graphs keep their stored value).
    params:[P.tabs("realScale","Units",[["off","Cell units"],["on","Real scale"]],"on"),
      WHEN(P.slider("repose","Repose angle",15,60,35,1,v=>(v|0)+"\u00b0"),"realScale","on"),
      WHEN(P.slider("talus","Talus",0.002,0.05,0.012,0.001,v=>v.toFixed(3)),"realScale","off"),P.int("iters","Iterations",5,80,30),P.slider("rate","Rate",0.1,1,0.5),
      P.log("feat","Feature scale",1,8,1,v=>v.toFixed(1)+"\u00d7",false)],
    eval:(p,ins)=>{if(!ins[0])return newField();
    finiteHeightField(ins[0],"input");
    if(ins[1])finiteHeightField(ins[1],"mask");
    finiteInRange(p.rate,0,1,"Rate");
    finiteInRange(p.iters,0,100000,"Iterations");
    finiteInRange(p.feat,1,8,"Feature scale");
    if(p.realScale==="on"){
      finiteInRange(p.repose,0,89.999,"Repose angle");
      finiteInRange(terrainDef.height,Number.MIN_VALUE,Number.MAX_VALUE,"terrain height");
    }else finiteInRange(p.talus,0,Number.MAX_VALUE,"Talus");

    // Iteration travel belongs to the requested OUTPUT grid. A 2x final build needs roughly 2x
    // the transport distance even when Feature Scale temporarily evaluates on a coarser grid.
    const outputGridK=resScale();
    // Interactive is a preview-tier budget: enough relaxation to read the landform, bounded so a
    // 1024² property edit does not launch 117+ simulation steps. Final retains full scaled travel.
    const travel=BUILD_QUALITY==="final"?outputGridK:Math.min(1.5,Math.sqrt(outputGridK));
    const iters=Math.max(1,Math.round(p.iters*travel));
    const modified=atFeatureScale(ins[0],p.feat,f=>{
      // IMPORTANT: atFeatureScale has rebound RES here. Repose is a slope threshold per
      // SIMULATION cell, so it must be derived from this coarse grid's cellSizeM()/resScale().
      // Computing it before the callback made a 4x Feature Scale node relax to about one quarter
      // of the requested slope (35 degrees behaved like ~9.9 degrees).
      const simGridK=resScale();
      const talus=(p.realScale==="on")
        ? Math.tan(p.repose*Math.PI/180)*cellSizeM()/terrainDef.height
        : p.talus/simGridK;
      finiteInRange(talus,0,Number.MAX_VALUE,"repose threshold");
      const q={...p,talus,iters};
      // Both kernels omit off-grid neighbours: an explicit closed/no-flux boundary. Hex uses the
      // D6 CPU kernel (one neighbour distance); gpuReady() is already false on hex.
      return gpuReady()?gpuThermal(f,q):thermalOn(f,q);
    });
    const result=maskApply(ins[0],modified,ins[1]);
    return finiteHeightField(result,"output");}})
