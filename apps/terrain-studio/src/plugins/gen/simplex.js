// simplex — Fractal simplex gradient noise — isotropic, efficient terrain detail without Perlin's squa
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { gpuFbm, gpuReady } from '../../core/gpu.js'
import { P } from '../../core/params.js'
import { fbmField, snoise } from '../../legacy.js'

export default definePlugin({
  type: "simplex",
cat:"gen",name:"Simplex fBm",ins:[],desc:"Fractal simplex gradient noise — isotropic, efficient terrain detail without Perlin's square-grid bias.",
    params:[P.seed("seed","Seed",11),P.log("freq","Frequency",0.5,12,3,v=>v<10?v.toFixed(2):v.toFixed(1),false),P.int("octaves","Octaves",1,9,6),
      P.slider("lac","Lacunarity",1.5,3,2,0.05),P.slider("gain","Gain",0.2,0.8,0.5,0.01)],
    eval:(p)=>{const a={seed:p.seed,freq:p.freq,octaves:p.octaves,lac:p.lac,gain:p.gain,simplex:true};return gpuReady()?gpuFbm(a):fbmField(snoise,a);}})
