// mountain — A cellular geological primitive: Mountain creates a hero landform from distorted, modulate
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P, WHEN } from '../../core/params.js'
import { mountainSkirtDefault } from '../../core/defaults.js'
import { mountainField, terrainDef } from '../../legacy.js'

export default definePlugin({
  type: "mountain",
cat:"gen",name:"Mountain",ins:[],desc:"A cellular geological primitive: Mountain creates a hero landform from distorted, modulated Voronoi structure; Mountain range creates a broader multi-crest base. Five mountain types change the generating geometry as well as its weathering.",
    params:[P.tabs("form","Landform",[["peak","Mountain"],["massif","Mountain range"]],"peak"),
      WHEN(P.seg("shape","Shape family",[["dominant","Dominant peak"],["compound","Compound peaks"],["ridge","Ridgeline"],["broad","Broad dome"]],"compound"),"form","peak"),
      P.seg("style","Mountain type",[["basic","Basic"],["eroded","Eroded"],["old","Old"],["alpine","Alpine"],["strata","Strata"]],"eroded"),
      P.seed("seed","Seed",7),
      P.slider("x","Position X",0,1,0.5,0.01,v=>Math.round(v*terrainDef.scale)+" m"),
      P.slider("y","Position Y",0,1,0.5,0.01,v=>Math.round(v*terrainDef.scale)+" m"),
      P.slider("size","Reach",0.08,0.9,0.40,0.01,v=>Math.round(v*terrainDef.scale)+" m"),
      P.slider("height","Peak height",0.1,2,0.72,0.01,v=>Math.round(v*terrainDef.height)+" m"),
      P.seg("bulk","Bulk",[["low","Low"],["medium","Medium"],["high","High"]],"medium"),
      P.slider("angle","Trend",0,180,25,1,v=>(v|0)+"\u00b0"),
      WHEN(P.int("ridges","Massif crests",1,5,2),"form","massif"),
      P.slider("detail","Drainage detail",0.4,3.5,2.6,0.1,v=>v.toFixed(1)+"\u00d7"),
      P.slider("aspect","Footprint aspect",0.4,2.5,1,0.05,v=>v.toFixed(2)+"\u00d7"),
      P.slider("relief","Valley depth",0.1,0.95,0.80,0.01),
      P.slider("character","Character",0,0.9,0.72,0.01,v=>v.toFixed(2)),
      P.slider("variation","Shape variation",0,1,0.55,0.01,v=>v.toFixed(2)),
      P.slider("reduce","Reduce details",0,1,0.08,0.01,v=>Math.round(v*100)+"%"),
      P.slider("weather","Weathering",0,2,1,0.05,v=>v.toFixed(2)+"\u00d7"),
      P.curve("skirt","Skirt profile",mountainSkirtDefault())],
    eval:(p)=>mountainField(p),
    note:"<b>Mountain</b> is a clean-room geological primitive based on Gaea's public contract: distorted, modulated cellular fields create the large faces and rock divisions inside an asymmetric uplift mass. It is not a cone with radial ridge stamps. Broad basins interrupt different shoulders, while the hydraulic pass supplies smaller flow detail. The default <b>Skirt profile</b> has separate upper-crag, shoulder, face, talus and pediment bands rather than one constant tent slope.<br><br>For the <b>Mountain</b> landform, two controls deliberately stay separate. <b>Shape family</b> selects the primary uplift algorithm: <b>Dominant peak</b> favours one strong cell, <b>Compound peaks</b> joins several high cells and saddles, <b>Ridgeline</b> favours a long connected cellular divide, and <b>Broad dome</b> favours cell interiors and wide shoulders. These are clean-room behavioural families, not claims about Gaea's unpublished Type internals. <b>Mountain type</b> changes the geomorphic expression: <b>Basic</b> keeps broad simple masses; <b>Eroded</b> deepens cellular faces and basins before hydraulic weathering; <b>Old</b> rounds the elevation profile while retaining residual gullies; <b>Alpine</b> narrows the profile, strengthens large and medium rock divisions, and preserves the summit divide; <b>Strata</b> uses a broader profile with a layered elevation response. Both settings change geometry, not materials.<br><br><b>Bulk</b> changes flank mass, <b>Drainage detail</b> changes basin and fracture scale, <b>Character</b> expands the uplift and cellular breakup, <b>Reduce details</b> suppresses the cellular/micro bands, <b>Valley depth</b> changes incision, and <b>Weathering</b> scales the type's process overprint. <b>Peak height</b> is shown in metres against the Terrain Definition.<br><br><b>Mountain range</b> uses the broader multi-crest generator; <i>Massif crests</i> applies only to it. Gaea documents MountainSide as a separate primitive, so a one-sided slope is not silently folded into this hero-mountain mode. Placement is built in (Position / Reach / Trend), so the feature is constructed at the requested world-space location."})
