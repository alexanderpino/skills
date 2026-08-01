import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { dilateField, maskApply, newField } from '../../legacy.js'

export default definePlugin({
  type:"dilate",cat:"filt",name:"Dilate",ins:["In","Mask"],desc:"Grow greyscale peaks over a physical lattice disc.",fieldSemantics:"preserve-primary",
  params:[P.number("radiusM","Radius",0,5000,100,1,"m")],
  eval:(p,ins)=>ins[0]?maskApply(ins[0],dilateField(ins[0],p),ins[1]):newField(),
  info:()=>"Radius is rounded to the nearest lattice step."
})