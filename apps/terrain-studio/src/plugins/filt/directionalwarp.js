import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { directionalWarpField, maskApply, newField } from '../../legacy.js'

export default definePlugin({
  type:"directionalwarp",cat:"filt",name:"Directional Warp",ins:["In","Driver","Mask"],desc:"Displace world coordinates along a bearing by a connected signed scalar driver.",fieldSemantics:"preserve-primary",
  params:[P.slider("bearing","Bearing",0,360,0,1,v=>`${v|0}\u00b0`),P.number("amplitudeM","Amplitude",-5000,5000,100,1,"m")],
  eval:(p,ins)=>ins[0]&&ins[1]?maskApply(ins[0],directionalWarpField(ins[0],ins[1],p),ins[2]):newField()
})