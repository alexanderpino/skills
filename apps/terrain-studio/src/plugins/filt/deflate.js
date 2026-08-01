import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { deflateField, maskApply, newField } from '../../legacy.js'

export default definePlugin({
  type:"deflate",cat:"filt",name:"Deflate",ins:["In","Mask"],desc:"Grow greyscale pits over a physical lattice disc.",fieldSemantics:"preserve-primary",
  params:[P.number("radiusM","Radius",0,5000,100,1,"m")],
  eval:(p,ins)=>ins[0]?maskApply(ins[0],deflateField(ins[0],p),ins[1]):newField(),
  info:()=>"Radius is rounded to the nearest lattice step."
})