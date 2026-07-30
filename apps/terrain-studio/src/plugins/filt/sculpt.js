// sculpt — Merge a masked Raise, Lower, Flatten, or Smooth operation into the incoming terrain. Pair 
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P, WHEN } from '../../core/params.js'
import { maskApply, newField, sculptField, terrainDef } from '../../legacy.js'

export default definePlugin({
  type: "sculpt",
cat:"filt",name:"Sculpt",ins:["In","Mask"],desc:"Merge a masked Raise, Lower, Flatten, or Smooth operation into the incoming terrain. Pair it with Draw Mask for roads and authored regions.",
    params:[P.tabs("mode","Tool",[["raise","Raise"],["lower","Lower"],["flatten","Flatten"],["smooth","Smooth"]],"smooth"),
      WHEN(P.slider("amount","Height",0,.25,.03,.002,v=>Math.round(v*terrainDef.height)+" m"),"mode","raise","lower"),
      WHEN(P.slider("target","Target height",0,1,.35,.01,v=>Math.round(v*terrainDef.height)+" m"),"mode","flatten"),
      WHEN(P.slider("radius","Smooth radius",1,16,4,1,v=>v|0),"mode","smooth"),
      P.slider("strength","Strength",0,1,1,.01)],
    eval:(p,ins)=>ins[0]?maskApply(ins[0],sculptField(ins[0],p),ins[1]):newField(),
    note:"This is a non-destructive merge modifier: <b>In</b> is the base terrain, <b>Mask</b> is the authored region, and the selected tool is blended back by Strength. Raise/Lower use a height delta, Flatten approaches one elevation, and Smooth merges a blurred copy only inside the mask."})
