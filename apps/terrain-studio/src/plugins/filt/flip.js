import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { flipField, maskApply, newField } from '../../legacy.js'

export default definePlugin({
  type:"flip",cat:"filt",name:"Flip",ins:["In","Mask"],desc:"Reflect the field about the horizontal or vertical world axis.",fieldSemantics:"preserve-primary",
  params:[P.seg("axis","Axis",[["horizontal","Horizontal"],["vertical","Vertical"]],"horizontal")],
  eval:(p,ins)=>ins[0]?maskApply(ins[0],flipField(ins[0],p),ins[1]):newField()
})