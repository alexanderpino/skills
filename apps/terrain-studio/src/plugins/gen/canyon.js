// canyon — An evolved plateau-canyon landscape: an antecedent trunk and environment-selected tributar
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P, GROUP } from '../../core/params.js'
import { canyonField, terrainDef } from '../../legacy.js'

export default definePlugin({
  type: "canyon",
cat:"gen",name:"Canyon",ins:[],desc:"An evolved plateau-canyon landscape: an antecedent trunk and environment-selected tributaries emerge from uplift, drainage area, slope, lithology, incision, and hillslope retreat.",
    params:[
      GROUP(P.select("style","Style",[["classic","Classic"],["eroded","Eroded"],["eroded2","Eroded 2"],["strata","Strata"],["both","Both"]],"classic"),"Structure"),
      GROUP(P.slider("scale","Scale",.05,1,.35,.01),"Structure"),
      GROUP(P.slider("slot","Slot",0,1,.36,.01),"Structure"),
      GROUP(P.slider("valley","Valley",0,1,.58,.01),"Structure"),
      GROUP(P.slider("surrounding","Surrounding",0,1,.60,.01),"Structure"),
      GROUP(P.slider("depth","Depth",0,1.25,1,.01,v=>Math.round((.10+.72*v)*terrainDef.height)+" m"),"Structure"),
      GROUP(P.slider("structural","Structural warp",0,1,.50,.01),"Structure"),
      GROUP(P.slider("tributaries","Tributary density",0,8,0,1,v=>Math.round(v)),"Structure"),
      GROUP(P.seed("seed","Seed",3),"Structure"),
      GROUP(P.text("waypoints","Trunk waypoints (x,y per line, blank = procedural)","",4),"Structure"),
      GROUP(P.slider("detailWarp","Detail warp",0,1,.50,.01),"Formation"),
      GROUP(P.seg("alternate","Alternate style",[["off","Off"],["on","On"]],"off"),"Formation")],
    eval:(p)=>canyonField(p),
    note:"<b>Canyon</b> is a clean-room landscape-evolution primitive. A shallow regional sag, uplift, hard/soft beds, and tiny initial relief establish potential drainage; outlet-seeded Priority-Flood and distance-corrected D8 create a depression-safe catchment; an area–slope channel-head condition (<b>Montgomery & Dietrich, 1988</b>) decides which convergent hollows become streams; and the implicit n=1 stream-power solve (<b>Braun & Willett, 2013</b>) magnifies those paths through repeated incision. Base level <i>falls</i> through the run rather than starting as a pre-dug notch, so every metre of depth is transmitted upstream by the incision solve. Slope-limited thermal erosion (<b>Musgrave, Kolb & Mace, 1989</b>) replaces linear diffusion and relaxes each wall to the repose angle of the bed exposed there, following the ridge/valley competition described by <b>Perron, Kirchner & Dietrich, 2009</b>. One bed table sets both erodibility and repose angle, which is what makes cliff bands stand over talus aprons instead of a uniformly faceted wall.<br><br>The through-going river is an <i>antecedent boundary condition</i>: external contributing area enters at one edge and follows the current receiver graph to the outlet. No interior trunk or tributary curve is authored by default \u2014 or set <b>Trunk waypoints</b> (x,y per line, top to bottom) to steer where that antecedent river runs; the process still incises, retreats and drains it, only the macro path is drawn instead of drawn from the structural seed. <b>Tributary density</b> changes the environmental area–slope initiation threshold; it never requests a branch count. Above each channel head, a tapering colluvial hollow follows the strongest real donor, so side canyons fade into divides rather than ending as rounded capsules. <b>Structural warp</b> changes the weak regional substrate, and <b>Detail warp</b> changes sub-catchment erodibility.<br><br><b>Style</b> changes process balance rather than adding noise: Classic is balanced; Eroded increases hillslope retreat; Eroded 2 lowers the initiation threshold and strengthens incision; Strata maximises differential hard/soft-bed retreat; Both combines dense incision with strong lithology. The global topology is solved on a cached process grid and resampled for 2K/4K output; the rendered height is an affine view of that solve, so changing Depth is a vertical gain and never re-runs the process. At render resolution a weathering pass retreats exposed faces at a rate set by their own material and deposits the debris at the foot of the face it came from, which is where benches, facets and talus aprons come from — no noise is added to height anywhere. Continue with <b>Erosion 2 → HydroFix</b> when a transported-sediment budget is needed downstream."})
