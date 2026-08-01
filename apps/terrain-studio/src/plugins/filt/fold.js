import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { foldField, maskApply, newField } from '../../legacy.js'

export default definePlugin({
  type:"fold",cat:"filt",name:"Fold",ins:["In","Mask"],desc:"Duplicate one world-space half-plane across an authored fold axis.",fieldSemantics:"preserve-primary",
  params:[P.slider("bearing","Bearing",0,360,0,1,v=>`${v|0}\u00b0`),P.number("offsetM","Offset",-5000,5000,0,1,"m")],
  eval:(p,ins)=>ins[0]?maskApply(ins[0],foldField(ins[0],p),ins[1]):newField()
})