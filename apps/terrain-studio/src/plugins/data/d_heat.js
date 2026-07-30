// d_heat — Modifies a Temperature field in physical °C. Driver supplies a biome, lava, geothermal, sh
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P, WHEN } from '../../core/params.js'
import { TEMP_MAX_C, TEMP_MIN_C, clamp, encodeTemperatureC, fieldMetadata, lerp, newField, tagTemperatureField, temperatureCFromField } from '../../legacy.js'

export default definePlugin({
  type: "d_heat",
cat:"data",name:"Temperature Modify",ins:["Temperature","Driver","Mask"],desc:"Modifies a Temperature field in physical °C. Driver supplies a biome, lava, geothermal, shade, or authored 0–1 footprint; Mask confines the exchange.",
    params:[P.tabs("mode","Operation",[["offset","Offset"],["set","Set"],["minimum","Minimum"],["maximum","Maximum"]],"offset"),
      WHEN(P.number("offsetC","Temperature offset",-500,1400,0,1,"°C"),"mode","offset"),
      WHEN(P.number("targetC","Target temperature",-100,1400,900,1,"°C"),"mode","set","minimum","maximum"),
      P.slider("amount","Amount",0,1,1,.01,v=>Math.round(v*100)+"%")],
    eval:(p,ins,nd)=>{
      const base=ins[0],baseC=temperatureCFromField(base);
      if(!baseC){
        nd._temperatureC=null;nd._inputError=base?"Temperature input requires a physical Temperature field":"Connect a Temperature field";
        return newField();
      }
      nd._inputError=null;
      const source=ins[1],mask=ins[2],outC=new Float32Array(baseC.length),out=new Float32Array(baseC.length);
      for(let i=0;i<out.length;i++){
        const w=clamp((source?source[i]:1)*(mask?mask[i]:1)*(p.amount==null?1:p.amount),0,1),c=baseC[i];
        let q=c;
        if(p.mode==="set")q=lerp(c,p.targetC,w);
        else if(p.mode==="minimum")q=c+Math.max(0,p.targetC-c)*w;
        else if(p.mode==="maximum")q=c-Math.max(0,c-p.targetC)*w;
        else q=c+p.offsetC*w;
        outC[i]=clamp(q,TEMP_MIN_C,TEMP_MAX_C);out[i]=encodeTemperatureC(outC[i]);
      }
      const meta=fieldMetadata(base)||{};nd._temperatureC=outC;nd._solarShadow=meta.solarShadow||null;nd._solarExposure=meta.solarExposure||null;
      return tagTemperatureField(out,outC,{solarShadow:nd._solarShadow,solarExposure:nd._solarExposure,
        lapseRate:meta.lapseRate,heightField:meta.heightField});
    },
    note:"Temperature Modify requires a physical Temperature field. <b>Offset</b> adds or removes degrees; <b>Set</b> approaches an absolute temperature; <b>Minimum</b> only heats colder cells; <b>Maximum</b> only cools warmer cells. Driver is a 0–1 spatial footprint, Mask confines the edit, and both multiply Amount. For authored climate regions, reuse the same Draw Mask that feeds the biome's SatMap layer: Set/Maximum can force an arctic cap, while Set/Minimum can force a hot desert. Chain regional edits over one global Temperature field so Snow and Water consume the final shared climate. A future Lava simulation can output a heat footprint into Driver—or emit a temperature field directly—without special cases in Snow, ice, biome selection, or the viewport."})
