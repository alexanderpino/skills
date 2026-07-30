// add — Arithmetic combine: add, subtract or multiply.
//
// The legacy import is CALL-TIME only: every name below is used inside `eval`, which does not
// run until the graph is evaluated. That keeps the legacy<->plugin cycle safe. Anything needed
// at module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { combine, lerp } from '../../legacy.js'

export default definePlugin({
  type: "add",
  cat:"comb",name:"Combine",ins:["A","B"],desc:"Arithmetic combine of two fields.",
    params:[P.seg("op","Op",[["add","Add"],["sub","Sub"],["mul","Mul"]],"add"),P.slider("amt","Amount",0,1,0.5)],
    eval:(p,ins)=>combine(ins[0],ins[1],p.op==="add"?(a,b)=>a+b*p.amt:p.op==="sub"?(a,b)=>a-b*p.amt:(a,b)=>a*lerp(1,b,p.amt))})
