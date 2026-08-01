import { definePlugin } from '../../core/registry.js'
import { aspectField, aspectPreviewField, newField } from '../../legacy.js'

export default definePlugin({
  type:"aspect",cat:"data",name:"Aspect",ins:["In"],desc:"Downslope direction in radians, recomputed from final geometry.",unit:"rad",
  params:[],eval:(p,ins)=>ins[0]?aspectField(ins[0]):newField(),previewAdapter:(field,def)=>aspectPreviewField(field,def),previewRange:[0,1]
})