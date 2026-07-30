// streampower — Fluvial incision \u2014 dh/dt = U \u2212 K\u00b7A^m\u00b7S. Drainage area makes valleys jo
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { BUILD_QUALITY, maskApply, newField, resScale, streamPowerErode } from '../../legacy.js'

export default definePlugin({
  type: "streampower",
cat:"ero",name:"Stream power",ins:["In","Uplift","Mask"],
    desc:"Fluvial incision \u2014 dh/dt = U \u2212 K\u00b7A^m\u00b7S. Drainage area makes valleys join into a tree and deepen downstream, so ridges emerge as what is left between them. This is the process that organises a landscape, not a texture applied to one.",
    // Incision default halved from 0.15: Kdt = strength*2, and 0.3 marches every cell 23% toward
    // its receiver per iteration - at shipped iteration counts that removed 57-62% of a mountain's
    // relief out of the box. 0.08 still carves a connected network (gated) while defaults keep most
    // relief, which is the Gaea-baseline contract for an out-of-the-box erosion node.
    params:[P.slider("strength","Incision",0,1,0.08,0.01),
      P.slider("m","Area exponent",0.2,0.8,0.5,0.01),
      P.int("iters","Iterations",1,60,14),
      // Default RAISED from 0: with no uplift the implicit solve is pure decay toward base level
      // and the shipped defaults removed 62% of a mountain in 14 iterations - a destructive
      // out-of-the-box setting. 0.35 balances incision so defaults CARVE drainage while keeping
      // most relief (the equilibrium-landscape regime the solver exists for). Uplift 0 remains
      // available and documented as the erode-to-baselevel mode.
      P.slider("uplift","Uplift",0,1,0.35,0.01),
      P.slider("hillslope","Hillslope",0,1,0.9,0.01)],
    // Res Lock mapping (k = RES/REF_RES): the solver's length scales live in cells, so the
    // slider->physical mapping is where world units get restored. Iterations do NOT scale:
    // this is the Braun-Willett implicit cascade - receivers are solved before donors in one
    // ordered sweep, so a base-level signal crosses the whole network in a single iteration and
    // the "one cell per iteration" travel intuition is false for this kernel (K's per-cell decay
    // is real - which is exactly why K needs boosting beyond the steady-state exponent). The
    // steady-state theory alone (K*k^(1-2m), U fixed) under-erodes the 14-iteration TRANSIENT
    // the shipped defaults run, so K carries a CALIBRATED exponent, fitted by sweep over m in
    // {.2,.5,.8} x k in {2,3} on the reference input (phi*(m) ~ 1.018m - 1.198, re-fitted after
    // the diffusion substep bound moved the m=0.8 root - the calibration harness
    // _verify_streampower_calibration.js re-derives the roots live and gates the line) and gated
    // across m and k by _verify_erosion_gridscale.js. Calibration, not derivation - stated as
    // such. Uplift is untouched (same iterations = same total). Incision cost is resolution-
    // independent (iterations unchanged); the diffusion DOSE k^2 is the one k-growing cost term
    // (k^4 total Laplacian work - measured 41.6 s of diffusion at 2048 square Final), so the
    // DOSE takes the Interactive tier cap of 2 and Final pays it in full.
    eval:(p,ins)=>{if(!ins[0])return newField();const k=resScale();
      const kd=BUILD_QUALITY==="final"?k:Math.min(k,2);
      return maskApply(ins[0],streamPowerErode(ins[0],
      {Kdt:p.strength*2.0*Math.pow(k,1.198-1.018*p.m), Udt:p.uplift*0.004, m:p.m,
       iters:p.iters,
       uplift:ins[1]||null, Ddt:p.hillslope*0.24*kd*kd}),ins[2]);},
    note:"Edges are held at <b>base level</b> \u2014 without a fixed outlet there is nothing to incise toward, so relief cannot organise at all.<br><br><b>Uplift 0 will erode your terrain away.</b> That is not a bug, it is what rivers do to a landmass that stops rising: measured on a Mountain, peak height goes 0.69 \u2192 0.53 \u2192 0.20 \u2192 0.000 as Incision rises with Uplift at 0. Keep Incision and Iterations low to carve, or raise <b>Uplift</b> so the interior keeps rising while the rivers cut \u2014 that balance is what holds a real range up, and it is the regime where slope and area settle to S \u221d A<sup>\u2212m</sup>.<br><br>Wire a field into the <b>Uplift</b> input and it scales the uplift rate per cell. That is the node's real use: feed a broad high region in (a Mountain, a Layout, a Shape) and let the rivers carve it, so summits and ridges emerge as <i>residue between the valleys</i> instead of being authored. A mountain is what erosion leaves behind.<br><br><b>Hillslope</b> is the diffusion term of the same equation, and it is what stops the ridges becoming razor blades: stream power sharpens interfluves without limit, diffusion relaxes them and gives hillslopes a length and valleys a width. At 0 you get blades.<br><br>The shipped defaults are set against <b>real SRTM data</b>, not by eye: driven by a Tectonic uplift they reproduce a real tile's slope distribution to within about one unit at every percentile (p90 9.9 vs 9.3, p99 16.0 vs 15.7, max 24.2 vs 22.8)."})
