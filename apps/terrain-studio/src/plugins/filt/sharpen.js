import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { maskApply, newField, sharpenField } from '../../legacy.js'

export default definePlugin({
  type:"sharpen",cat:"filt",name:"Sharpen",ins:["In","Mask"],desc:"Unsharp detail enhancement with a world-space blur radius.",fieldSemantics:"preserve-primary",
  params:[P.slider("amount","Amount",0,4,1,.05,v=>v.toFixed(2)),P.number("radiusM","Radius",1,5000,100,1,"m")],
  eval:(p,ins)=>ins[0]?maskApply(ins[0],sharpenField(ins[0],p),ins[1]):newField()
})