import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { maskApply, newField, softClipField } from '../../legacy.js'

export default definePlugin({
  type:"softclip",cat:"filt",name:"Soft Clip",ins:["In","Mask"],desc:"Product-defined blend between hard clamp and cubic Hermite clipping.",fieldSemantics:"preserve-primary",
  params:[P.number("lo","Low",-100000,100000,0,.01),P.number("hi","High",-100000,100000,1,.01),P.slider("softness","Softness",0,1,.5,.01,v=>v.toFixed(2))],
  eval:(p,ins)=>ins[0]?maskApply(ins[0],softClipField(ins[0],p),ins[1]):newField()
})