// layout — Author the terrain's SKELETON as vector shapes carrying elevation \u2014 World Machine's L
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { layoutField, maskApply, newField, parseLayout } from '../../legacy.js'

export default definePlugin({
  type: "layout",
cat:"gen",name:"Layout",ins:["Base","Mask"],
    desc:"Author the terrain's SKELETON as vector shapes carrying elevation \u2014 World Machine's Layout Generator, Houdini's project-from-curves, Gaea's vector drawing. Wire a Base to embed the shapes into existing terrain instead of generating from scratch.",
    params:[P.text("spec","Shapes",
`# path | point | poly, then vertices as x,y,elevation (0-1 of the tile)
# width= falloff= profile=linear|squared|sqrt|scurve op=max|add|sub|replace breakup= seed=
path width=0.03 falloff=0.26 profile=scurve op=max breakup=0.45 seed=3
  0.10,0.70,0.35  0.28,0.62,0.85  0.44,0.66,0.55
  0.62,0.52,1.00  0.80,0.46,0.62  0.93,0.52,0.30`, 10),
      P.slider("height","Height",0,1,1,0.01)],
    eval:(p,ins,node)=>{
      let shapes;try{shapes=parseLayout(p.spec);}catch(err){console.error("layout",err);shapes=[];}
      node._shapeCount=shapes.length;
      const f=layoutField(shapes,ins[0]||null);
      if(p.height!==1)for(let i=0;i<f.length;i++)f[i]*=p.height;
      return maskApply(ins[0]||newField(0),f,ins[1]);},
    note:"Elevation is <b>per vertex</b>, which is the whole point: a path is not a constant-height ribbon, it carries a height profile along its length. Summits fall out at the high vertices, saddles at the low ones, and faces fall away either side \u2014 so the node that art-directs a range is the same one that builds a single mountain. Overlapping shapes resolve by <b>greatest height wins</b>, as in World Machine. <b>Breakup</b> lets a fractal distort the outline so it is not geometric. With no <b>Base</b> wired it generates; wire one and it embeds instead."})
