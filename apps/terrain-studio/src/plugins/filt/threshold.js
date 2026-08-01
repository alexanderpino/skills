import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, thresholdField } from '../../legacy.js'

export default definePlugin({
  type:"threshold",cat:"filt",name:"Threshold",ins:["In"],desc:"Binary selection at an authored scalar cut.",
  params:[P.number("cut","Cut",-100000,100000,.5,.01)],
  eval:(p,ins)=>ins[0]?thresholdField(ins[0],p):newField()
})