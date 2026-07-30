// The parameter DSL and the node-category table.
//
// Extracted FIRST of the plugin work, and it is a prerequisite rather than a nicety. A plugin
// module declares its params at top level - `params: [P.slider("factor","Factor",0,1,0.5)]` - so P
// has to be initialised before that module body runs. If P stayed in legacy.js, legacy.js would
// import the plugins and the plugins would import legacy.js back: a cycle in which the PLUGIN
// evaluates first, as a dependency, while P is still in the temporal dead zone. Every plugin would
// throw "Cannot access P before initialization" at load. Its own module has no such cycle.
//
// Self-contained by inspection: pure factory functions and a lookup table, no field, no DOM, no
// graph. That is why it is the cheapest possible first cut for the plugin phase.

export const P={
  slider:(key,label,min,max,def,step=0.01,fmt)=>({key,label,type:"slider",min,max,def,step,fmt}),
  // Logarithmic slider for quantities whose useful range spans ratios or decades (snowfall: a
  // dusting is 0.05 m and a heavy winter 10 m; a DEM height multiplier may span 0.01x-100x).
  // `floor` is the smallest non-zero value; position 0 is exactly zero when `zero` is set. The
  // value stored in params is always the REAL quantity, so serialisation, digests and every
  // consumer are unaffected by how the track is warped.
  log:(key,label,floor,max,def,fmt,zero=true)=>({key,label,type:"slider",scale:"log",floor,max,def,fmt,zero,min:0,step:.0025}),
  number:(key,label,min,max,def,step=0.01,unit="",fmt)=>({key,label,type:"number",min,max,def,step,unit,fmt}),
  int:(key,label,min,max,def)=>({key,label,type:"slider",min,max,def,step:1,fmt:v=>v|0}),
  select:(key,label,opts,def)=>({key,label,type:"select",opts,def}),
  seg:(key,label,opts,def)=>({key,label,type:"seg",opts,def}),
  tabs:(key,label,opts,def)=>({key,label,type:"tabs",opts,def}),
  toggle:(key,label,def=false)=>({key,label,type:"toggle",def:!!def}),
  hidden:(key,def=null)=>({key,label:key,type:"hidden",def}),
  text:(key,label,def,rows=9)=>({key,label,type:"text",def,rows}),
  curve:(key,label,def)=>({key,label,type:"curve",def}),
  seed:(key,label,def)=>({key,label,type:"seed",def}),
};
// Conditional parameters are schema data: hidden values remain serialised and return unchanged when
// their tab becomes active again. This keeps every node consistent instead of hard-coding UI cases.
export const WHEN=(param,key,...values)=>({...param,when:{key,values:values.flat()}});
export const GROUP=(param,name)=>({...param,group:name});
export const SECTION=(param,name)=>({...param,section:name});
export const CAT={gen:{c:"--cat-gen",name:"Generator"},comb:{c:"--cat-comb",name:"Combine"},
  filt:{c:"--cat-filt",name:"Filter"},ero:{c:"--cat-ero",name:"Erosion"},
  mask:{c:"--cat-mask",name:"Mask"},data:{c:"--cat-data",name:"Data map"},effect:{c:"--cat-effect",name:"Effect"},out:{c:"--cat-out",name:"Output"}};

/* Node types that COMMUTE with a coordinate transform, so a Transform above them can be folded into
   their coordinate evaluation (exact) instead of resampling their output (lossy). Two families:
     * GENERATORS that are pure functions of position — evaluate them at any coordinate.
     * PER-PIXEL value ops, where T(op(f)) === op(T(f)) because the op never mixes neighbours.
   Everything else reads neighbours (blur, warp), runs a grid simulation (erosion), depends on the
   whole field (histogram EQ) or has no closed form (an imported DEM), so it exists only as a raster
   and has to be resampled. Honest caveat: Ridged/Voronoi/Gradient self-normalise, a whole-field
   reduction — geometry is exact, but the value range is re-stretched over the new window. */
