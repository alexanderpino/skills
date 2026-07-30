// drawmask — Paint resolution-independent roads, corridors, and regions as editable vector brush stroke
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { drawMaskField } from '../../legacy.js'

export default definePlugin({
  type: "drawmask",
cat:"mask",name:"Draw Mask",ins:["Reference"],referenceOnly:[0],desc:"Paint resolution-independent roads, corridors, and regions as editable vector brush strokes. The optional Reference input is shown beneath the drawing; the output is a reusable mask.",
    params:[],eval:(p,ins,nd)=>{nd._reference=ins[0]||null;return drawMaskField(p);},
    note:"Draw Mask outputs a reusable 0–1 region field and may fan out to any number of Mask inputs. For an authored biome, use one Draw Mask for that region and connect it to its masked <b>SatMap</b>, <b>Temperature Modify</b>, and—when regional circulation differs—<b>Wind Modify</b>; material and climate then share the same footprint. For a road, connect the pre-road terrain to <b>Reference</b>, draw the corridor, then wire the mask into Sculpt, Blur, Blend, or Stamp. Strokes are vectors in terrain space rather than pixels, so 512² authoring survives a 4K build."})
