// stampn — Composite a patch onto a base through a mask.
//
// The legacy import is CALL-TIME only: every name below is used inside `eval`, which does not
// run until the graph is evaluated. That keeps the legacy<->plugin cycle safe. Anything needed
// at module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { lerp, maskApply, newField } from '../../legacy.js'

export default definePlugin({
  type: "stampn",
  cat:"comb",name:"Stamp",ins:["Base","Patch","Mask"],
    desc:"Drop a placed feature onto a base terrain. This is the other half of placement: a Transform says WHERE the feature goes, a Shape mask says HOW FAR it reaches, and Stamp composites it in.",
    params:[P.seg("op","Mode",[["max","Max"],["add","Add"],["replace","Replace"]],"max"),
      P.slider("amount","Amount",0,1,1)],
    // Mirrors reference-impl/placement.py `stamp`. Max is the default because it unions a landform in
    // WITHOUT trenching what is already there; Add accumulates relief (two overlapping fans build up);
    // Replace overwrites, which only reads well inside a soft-edged mask.
    eval:(p,ins)=>{
      const base=ins[0]||newField();if(!ins[1])return base;
      const patch=ins[1],o=newField();
      for(let i=0;i<o.length;i++){
        const v=p.op==="max"?Math.max(base[i],patch[i]):p.op==="add"?base[i]+patch[i]:patch[i];
        o[i]=base[i]+(v-base[i])*p.amount;}
      return maskApply(base,o,ins[2]);},
    note:"Without a <b>Mask</b> the patch applies everywhere it is defined, so a Shape (or any mask) is what turns this from a global combine into a <i>placement</i>. Because masking is a post-process lerp, dragging the mask never re-runs whatever generated the patch."})
