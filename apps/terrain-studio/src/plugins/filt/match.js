import { definePlugin } from '../../core/registry.js'
import { matchField, newField } from '../../legacy.js'

export default definePlugin({
  type:"match",cat:"filt",name:"Match",ins:["Source","Target"],desc:"Assign target values to source samples by stable rank.",
  params:[],eval:(p,ins)=>ins[0]&&ins[1]?matchField(ins[0],ins[1]):newField()
})