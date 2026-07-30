// satmapblend — Blend any two colour branches — SatMap, Color Erosion, Weathering, or a mixed chain. A is 
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField } from '../../legacy.js'

export default definePlugin({
  type: "satmapblend",
cat:"effect",name:"Color Blend",ins:["A","B","Mask"],desc:"Blend any two colour branches — SatMap, Color Erosion, Weathering, or a mixed chain. A is underneath; B composites over it by Mask × Opacity using the selected mode. Height passes through from A.",
    passthrough:true,effect:"satmapblend",
    params:[P.select("blend","Blend",[["normal","Blend"],["add","Add"],["screen","Screen"],["subtract","Subtract"],
      ["difference","Difference"],["multiply","Multiply"],["divide","Divide"],["divide2","Divide 2"],
      ["max","Max"],["min","Min"],["hypotenuse","Hypotenuse"],["overlay","Overlay"],["power","Power"]],"normal"),
      P.slider("opacity","Opacity",0,1,1)],
    eval:(p,ins,nd)=>{nd._mask=ins[2]||null;return ins[0]||newField();}})
