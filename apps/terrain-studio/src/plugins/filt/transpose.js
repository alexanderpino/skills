import { definePlugin } from '../../core/registry.js'
import { maskApply, newField, transposeWorldField } from '../../legacy.js'

export default definePlugin({
  type:"transpose",cat:"filt",name:"Transpose",ins:["In","Mask"],desc:"Reflect the field about the world diagonal.",fieldSemantics:"preserve-primary",
  params:[],eval:(p,ins)=>ins[0]?maskApply(ins[0],transposeWorldField(ins[0]),ins[1]):newField()
})