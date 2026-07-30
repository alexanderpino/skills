// hydraulic — GPU virtual-pipe flow or CPU droplets — carves valleys and transports sediment.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { gpuHydraulicPipes, gpuReady } from '../../core/gpu.js'
import { P, WHEN } from '../../core/params.js'
import { BUILD_QUALITY, RES, atFeatureScale, hydraulicErode, maskApply, newField, resScale } from '../../legacy.js'

export default definePlugin({
  type: "hydraulic",
cat:"ero",name:"Hydraulic erosion",ins:["In","Mask"],desc:"GPU virtual-pipe flow or CPU droplets — carves valleys and transports sediment.",
    params:[P.tabs("engine","Engine",[["auto","GPU pipes"],["droplets","CPU droplets"]],"auto"),
      // KNOWN CROSS-ENGINE GAP, measured and gated but not yet closed: at the same sliders the
      // pipe engine modifies the terrain at ~0.37x the depth of the droplet engine (delta corr
      // ~0.59 - they are different simulations: broad pipe valleys vs dendritic particle
      // tracks). Raising this default toward ~160 buys depth parity but breaks the A2 grid
      // invariance (measured 1.42 at k=2 - the invariance partly RESTS on the per-iteration
      // erosion cap clamping the fine grid, so dose and invariance are coupled and no cheap
      // knob buys both; cap-scaling was measured too: flat cross-depth, gridRatio ~2.0).
      // Closing it needs a re-derivation of the pipe dose family under clamp saturation -
      // queued. The slider max is raised to 360 so the trade is available BY CHOICE;
      // _verify_gpu.js gates the measured relationship against silent drift.
      WHEN(P.int("pipeIters","Pipe iterations",8,360,48),"engine","auto"),
      WHEN(P.int("droplets","CPU droplets",2000,60000,18000),"engine","droplets"),
      P.slider("erode","Erode",0.05,0.8,0.35),P.slider("deposit","Deposit",0.05,0.8,0.28),
      P.slider("capacity","Capacity",1,12,6,0.5),P.slider("inertia","Inertia",0,0.5,0.05),
      // This param was REFERENCED by the eval below since the node shipped, but never declared:
      // p.radius was undefined, Math.round(undefined*k) is NaN, and hydraulicErode clamps NaN to a
      // 1-cell brush - the corpus's #1 droplet defect (point scouring: +41% high-frequency scratch
      // energy vs radius 2), unconditionally, at every setting of every other slider. Declared at
      // the corpus default of 2; verified bit-identical to the old output only when forced to NaN.
      WHEN(P.slider("radius","Brush radius",1,5,2,1,v=>(v|0)+" px"),"engine","droplets"),
      WHEN(P.seed("seed","Seed",1),"engine","droplets"),
      P.log("feat","Feature scale",1,8,1,v=>v.toFixed(1)+"\u00d7",false)],
    eval:(p,ins)=>{if(!ins[0])return newField();const k=resScale();
    const usePipes=p.engine!=="droplets"&&gpuReady();
    // Interactive tier = a FULL-QUALITY simulation on a capped grid (<= 384), its delta
    // upsampled - NOT a starved simulation on the full grid. A2's grid invariance is the
    // contract that makes this a preview: a capped-grid sim lands within a few percent of the
    // full-res landform, where the old dose caps (droplet count min(4,k^2) + gridK min(k,2) on
    // the full grid) previewed at 0.64x of Final's depth at the default 512 (measured; rate
    // compensation cannot close it - capacity-limited dynamics saturate). ke = k/tier keeps the
    // node-level anchoring: at RES <= 384 it equals the old caps exactly (digest-identical),
    // at 192 it is exactly 1, and Final (tier=1) is byte-identical to before.
    const tier=BUILD_QUALITY==="final"?1:Math.max(1,RES/384),ke=k/tier;
    return maskApply(ins[0],atFeatureScale(ins[0],p.feat*tier,f=>usePipes
      ?gpuHydraulicPipes(f,{...p,iters:p.pipeIters,gridK:ke})
      :hydraulicErode(f,{...p,droplets:Math.round(p.droplets*ke*ke),
        radius:Math.max(1,Math.round((p.radius==null?2:p.radius)*ke)),settle:true,gridK:ke})),ins[1]);},
    note:"<b>GPU pipes</b> is the interactive production path: a Mei-style virtual-pipe water and sediment simulation kept in float textures until one final readback. It scales with pixels × iterations and uses the GPU coherently. <b>CPU droplets</b> keeps the older particle reference for comparison; at high resolution its droplet count scales with pixel area, so it is deliberately much slower."})
