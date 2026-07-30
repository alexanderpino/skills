// snow — A transient snow-depth layer in metres: snowfall accumulates, sun and temperature melt it,
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P, GROUP } from '../../core/params.js'
import { evaluateSnowLayer, fieldMetadata, newField, temperatureCFromField, windVectorFromField } from '../../legacy.js'

export default definePlugin({
  type: "snow",
cat:"effect",name:"Snow",ins:["In","Temperature","Wind"],desc:"A transient snow-depth layer in metres: snowfall accumulates, sun and temperature melt it, avalanches settle it, and an optional physical Wind field scours windward faces into lee cornices.",
    passthrough:true,effect:"snow",
    params:[GROUP(P.log("snowfall","Snowfall",.02,20,3,v=>v<.995?(v*100).toFixed(0)+" cm":v.toFixed(2)+" m"),"Accumulation"),
      GROUP(P.slider("meltDays","Melt period",0,120,45,1,v=>(v|0)+" days"),"Climate & melt"),
      GROUP(P.log("meltRate","Degree-day melt",.05,20,10,v=>v.toFixed(2)+" mm/°C/day"),"Climate & melt"),
      GROUP(P.slider("repose","Snow repose angle",20,60,38,1,v=>(v|0)+"°"),"Avalanche & settling"),
      GROUP(P.slider("adhesion","Adhesion depth",0,2,.6,.05,v=>v.toFixed(2)+" m"),"Avalanche & settling"),
      GROUP(P.int("iterations","Settling iterations",0,80,12),"Avalanche & settling"),
      GROUP(P.slider("settle","Settling rate",.1,1,.55,.05,v=>v.toFixed(2)),"Avalanche & settling"),
      GROUP(P.slider("windStrength","Fallback wind strength",0,1,.35,.05,v=>v.toFixed(2)),"Wind"),
      GROUP(P.slider("windDirection","Fallback wind from",0,360,300,5,v=>(v|0)+"° map"),"Wind")],
    eval:(p,ins,nd)=>{
      const h=ins[0]||newField(),meta=fieldMetadata(ins[1])||{};
      const temperature=temperatureCFromField(ins[1]),wind=windVectorFromField(ins[2]),errors=[];
      if(ins[1]&&!temperature)errors.push("Temperature input requires a physical Temperature field");
      if(ins[2]&&!wind)errors.push("Wind input requires a physical Wind field");
      nd._inputError=errors.length?errors.join(" · "):null;
      nd._snowLayer=evaluateSnowLayer(h,p,temperature,meta.solarShadow,meta.solarExposure,wind);return h;
    },
    note:"Snow is a separate transient <b>thickness field in metres</b>; it does not repaint or permanently alter bedrock. The renderer composes that thickness into a solid-surface heightfield, including above frozen water, so lighting, picking, and visible elevation follow the snow top. The underlying terrain output stays unchanged until an explicit bake/export-surface workflow is requested. <b>Snowfall</b> is settled vertical depth; precipitation transitions from rain to snow around freezing, and <b>degree-day melt</b> removes snow above 0 °C. Temperature consumes the final physical field wired into it. Wind consumes the final physical Wind field—including masked Wind Modify regions—and falls back to the local sliders only when no Wind edge exists.<br><br><b>Water is phase-aware.</b> Open liquid water masks terrain snow out. Frozen standing water is rendered as an ice surface and can receive its own snow thickness, so snow never floats on liquid but does accumulate on ice.<br><br><b>Solar warming is spatial.</b> Latitude and map north place an equator-side climate sun; its elevation is global. Surface incidence includes slope/aspect, a terrain-horizon march casts real ridge shadows, and a two-pass spatial blur supplies soft penumbra plus diffuse sky exposure. That map—not the cosmetic viewport shadow—raises surface temperature.<br><br>Settling conserves snow volume while relaxing the combined terrain + snow surface toward the snow repose angle, and transports only the surplus above a slope- and roughness-dependent <b>Adhesion depth</b> — the snow that clings to ledges and rough ground. Ridges and spurs therefore hold cover, cliffs thin to streaks rather than stripping bare, and snow COVERAGE no longer depends on iteration count. <b>Wind</b> then scours each cell along its local terrain-adjusted vector and loads the first lee cells—cornices—and deliberately is not re-relaxed afterwards. The implementation follows the placement/stability split of Fearing (2000), the five-step accumulate/melt/shed/avalanche/wind model of Cordonnier et al. (2018), and the shared terrain-wind field's Jackson–Hunt / Sherman-family approximation."})
