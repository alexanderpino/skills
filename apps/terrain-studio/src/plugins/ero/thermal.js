// thermal — Talus: material above repose slides down.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { gpuReady, gpuThermal } from '../../core/gpu.js'
import { P, WHEN } from '../../core/params.js'
import { BUILD_QUALITY, atFeatureScale, cellSizeM, maskApply, newField, resScale, terrainDef, thermalOn } from '../../legacy.js'

export default definePlugin({
  type: "thermal",
cat:"ero",name:"Thermal erosion",ins:["In","Mask"],desc:"Talus: material above repose slides down.",
    // Real scale is the DEFAULT: with cell units shipping as default, the Repose slider did not
    // exist on a fresh node and repose 25 vs 45 measured IDENTICAL slope percentiles - the
    // node's only physical control was unreachable out of the box. Cell units stay as the
    // escape hatch (existing saved graphs keep their stored value).
    params:[P.tabs("realScale","Units",[["off","Cell units"],["on","Real scale"]],"on"),
      WHEN(P.slider("repose","Repose angle",15,60,35,1,v=>(v|0)+"\u00b0"),"realScale","on"),
      WHEN(P.slider("talus","Talus",0.002,0.05,0.012,0.001,v=>v.toFixed(3)),"realScale","off"),P.int("iters","Iterations",5,80,30),P.slider("rate","Rate",0.1,1,0.5),
      P.log("feat","Feature scale",1,8,1,v=>v.toFixed(1)+"\u00d7",false)],
    eval:(p,ins)=>{if(!ins[0])return newField();const k=resScale();
    // Real Scale ON: `repose` is a true angle, so the per-cell drop is tan(angle) * cellSize / height
    // — physically meaningful AND inherently resolution independent (it already carries the 1/RES).
    // OFF: `talus` is a raw per-cell drop, divided by k to hold the same angle as the reference grid.
    const talus=(p.realScale==="on")
      ? Math.tan(p.repose*Math.PI/180)*cellSizeM()/terrainDef.height
      : p.talus/k;
    // Interactive is a preview-tier budget: enough relaxation to read the landform, bounded so a
    // 1024² property edit does not launch 117+ simulation steps. Final retains full scaled travel.
    const travel=BUILD_QUALITY==="final"?k:Math.min(1.5,Math.sqrt(k));
    const q={...p,talus,iters:Math.max(1,Math.round(p.iters*travel))};
    // Hex: the D6 kernel (one distance, one threshold); gpuReady() is already false on hex.
    return maskApply(ins[0],atFeatureScale(ins[0],p.feat,f=>gpuReady()?gpuThermal(f,q):thermalOn(f,q)),ins[1]);}})
