// d_temperature — Generates the base surface-temperature field from datum-aware elevation lapse rate plus so
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { encodeTemperatureC, evaluateTemperatureMap, fieldLen, newField, tagTemperatureField } from '../../legacy.js'

export default definePlugin({
  type: "d_temperature",
cat:"data",name:"Temperature",ins:["Relative height","Sun visibility"],desc:"Generates the base surface-temperature field from datum-aware elevation lapse rate plus solar exposure. The physical Celsius map remains editable downstream.",
    params:[P.slider("seaTemp","Sea-level temperature",-50,50,6,.5,v=>v.toFixed(1)+" °C"),
      P.slider("lapseRate","Altitude lapse rate",-10,15,6.5,.1,v=>v.toFixed(1)+" °C/km"),
      P.slider("warming","Solar warming",0,50,5,.5,v=>v.toFixed(1)+" °C")],
    eval:(p,ins,nd)=>{
      if(!ins[0]){
        nd._temperatureC=new Float32Array(fieldLen());nd._solarShadow=newField();nd._solarExposure=newField();
        const out=newField();out.fill(encodeTemperatureC(0));return tagTemperatureField(out,nd._temperatureC);
      }
      const maps=evaluateTemperatureMap(ins[0],p,ins[1]||null);
      nd._temperatureC=maps.temperatureC;nd._solarShadow=maps.solarShadow;nd._solarExposure=maps.solarExposure;
      return tagTemperatureField(maps.encoded,maps.temperatureC,{solarShadow:maps.solarShadow,solarExposure:maps.solarExposure,
        lapseRate:p.lapseRate,heightField:ins[0]});
    },
    note:"This node creates the <b>base</b> temperature map; it is not a terminal display effect. Its climate sliders stay in useful Earth-scale ranges: sea-level temperature −50…+50 °C, lapse rate −10…+15 °C/km (including inversions), and solar warming 0…50 °C. Its Celsius contract survives unit-preserving spatial operations such as Blur, Warp, and Transform; generic tonal/arithmetic nodes deliberately drop it unless both inputs are compatible Temperature fields. Snow and Water read the final physical field wired into them. The scalar encoding still spans −100…1400 °C so volcanic heat remains representable through <b>Temperature Modify</b>. Without a Sun visibility edge, the model assumes open sky while retaining slope/aspect incidence; connect <b>Sun Shadow</b> to make terrain occlusion explicit. Terrain Definition supplies latitude, north, and solar elevation."})
