// water — Defines where fluid exists and uses an optional physical Temperature field for its liquid/
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P, WHEN, GROUP } from '../../core/params.js'
import { newField, terrainDef } from '../../legacy.js'

export default definePlugin({
  type: "water",
cat:"effect",name:"Water",ins:["In","Temperature"],desc:"Defines where fluid exists and uses an optional physical Temperature field for its liquid/ice phase. Hydrology fills selected basins; Sea adds one flat level. Waves and refraction are global renderer settings.",
    passthrough:true,effect:"water",
    params:[P.tabs("mode","Mode",[["hydro","Hydrology"],["sea","Sea level"]],"hydro"),
      WHEN(GROUP(P.seg("lakes","Lakes",[["on","On"],["off","Off"]],"on"),"Hydrology"),"mode","hydro"),
      WHEN(GROUP(P.slider("lakeMin","Minimum lake depth",0,.03,.001,.0005,v=>Math.round(v*terrainDef.height)+" m"),"Hydrology"),"mode","hydro"),
      WHEN(GROUP(P.slider("flow","River network",0,1,.5,.01),"Hydrology"),"mode","hydro"),
      WHEN(GROUP(P.slider("riverDepth","River depth",0,1,.7,.01),"Hydrology"),"mode","hydro"),
      WHEN(GROUP(P.slider("level","Sea level",0,0.6,0.12,.01,v=>Math.round(v*terrainDef.height)+" m"),"Sea"),"mode","sea"),
      GROUP(P.slider("shoreSmooth","Shore smoothing",0,2.5,1.35,.05),"Shoreline"),
      GROUP(P.slider("foam","Shore foam",0,1,.18,.01),"Shoreline")],
    eval:(p,ins)=>ins[0]||newField(),
    note:"<b>Hydrology</b> runs a priority-flood over the terrain: lakes sit at basin spill elevations, while the D8 accumulation field supplies a branching river network. <b>Minimum lake depth</b> removes tiny numerical puddles; <b>River network</b> changes the contributing-area threshold, and <b>River depth</b> changes the visible water film.<br><br>The optional <b>Temperature</b> input controls phase locally: standing water freezes cell by cell, independent of whether a Snow node exists. Without it, the clearly labelled fallback climate in Terrain Definition is used. <b>Sea level</b> is a separate mode and therefore hides hydrology controls. Shoreline smoothing and foam apply to both modes. Wave pattern, motion, and <b>refraction</b> are global viewport settings in the Water Surface flyout, because they describe the renderer rather than this node's hydrological field."})
