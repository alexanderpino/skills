// tectonic — Voronoi plates with noise-warped boundaries, each classified into collision / subduction /
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { plateUplift } from '../../legacy.js'

export default definePlugin({
  type: "tectonic",
cat:"gen",name:"Tectonic uplift",ins:[],
    desc:"Voronoi plates with noise-warped boundaries, each classified into collision / subduction / island arc / rift / transform, with the boundary uplift diffused inland over the orogen width. Wire it into Stream power's Uplift input: this gives the structure, the rivers give the topography.",
    params:[P.seed("seed","Seed",3),
      P.int("plates","Plates",3,24,10),
      P.slider("warp","Boundary warp",0,1,0.5,0.01),
      P.slider("orogen","Orogen width",0.05,1,0.35,0.01),
      P.slider("ocean","Oceanic fraction",0,0.9,0.45,0.01),
      P.slider("land","Continental uplift",0,1,0.45,0.01),
      P.seg("output","Output",[["orogen","Orogen"],["elev","Elevation"]],"orogen")],
    eval:(p)=>plateUplift(p),
    note:"Raw Voronoi edges are dead straight, which is the giveaway in any plate map \u2014 so the coordinates are <b>domain-warped</b> before assignment and the sites are Lloyd-relaxed so plates come out evenly sized instead of slivered. <b>Orogen</b> spreads the boundary uplift inland, because a mountain belt is a broad welt rather than a line. <b>Orogen</b> output is the uplift field; <b>Elevation</b> adds the per-plate base (oceanic low, continental high) if you want to render it directly. F-tier: a plausible planar plate sketch, not plate physics."})
