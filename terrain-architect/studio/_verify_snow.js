// Physical snow regression: the Snow node owns a world-metre depth field that displaces geometry,
// conserves avalanche mass, accumulates in hollows, and melts preferentially on equator-facing slopes.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');

(async()=>{
  const browser=await chromium.launch({executablePath:EXE,args:[
    '--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'
  ]});
  const page=await browser.newPage({viewport:{width:1280,height:820}});
  const errors=[];
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});
  await page.waitForTimeout(2200);

  const result=await page.evaluate(()=>{
    const mean=a=>a.reduce((s,v)=>s+v,0)/a.length;
    const snowNode=nodes.find(n=>n.type==='snow');
    const waterNode=nodes.find(n=>n.type==='water');
    const heightNode=nodes.find(n=>n.type==='d_height');
    const shadowNode=nodes.find(n=>n.type==='d_sunshadow');
    const temperatureNode=nodes.find(n=>n.type==='d_temperature');
    const temperatureModifyNode=nodes.find(n=>n.type==='d_heat');
    const outNode=nodes.find(n=>n.type==='output');
    const layer=snowNode&&snowNode._snowLayer;
    let displacement=0;
    if(curSurfaceY&&curHgt)for(let i=0;i<curSurfaceY.length;i++)
      displacement=Math.max(displacement,curSurfaceY[i]-curHgt[i]*H_SCALE);
    const volumeError=layer&&layer.preAvalancheM3
      ?Math.abs(layer.volumeM3-layer.preAvalancheM3)/layer.preAvalancheM3:1;
    let liquidSnow=0,liquidCells=0;
    if(curSnowDepthM&&curWaterLiquid)for(let i=0;i<curSnowDepthM.length;i++)if(curWaterLiquid[i]>.5){
      liquidCells++;liquidSnow=Math.max(liquidSnow,curSnowDepthM[i]);
    }
    const hasEdge=(from,to,slot)=>edges.some(e=>!e.disabled&&e.from===from.id&&e.to===to.id&&e.slot===slot);
    const defaultGraph={
      waterToSnow:hasEdge(waterNode,snowNode,0),snowToOutput:hasEdge(snowNode,outNode,0),
      heightToShadow:hasEdge(heightNode,shadowNode,0),heightToTemperature:hasEdge(heightNode,temperatureNode,0),
      shadowToTemperature:hasEdge(shadowNode,temperatureNode,1),
      temperatureToModify:hasEdge(temperatureNode,temperatureModifyNode,0),
      modifyToWater:hasEdge(temperatureModifyNode,waterNode,1),
      modifyToSnow:hasEdge(temperatureModifyNode,snowNode,1)
    };
    const mapRange=a=>{let lo=Infinity,hi=-Infinity;for(const v of a||[]){lo=Math.min(lo,v);hi=Math.max(hi,v);}return[lo,hi];};

    // The Temperature node must consume terrain shadow as climate data, not merely infer warmth
    // from slope/aspect. At identical elevation, an explicitly occluded cell is colder.
    const flatClimateHeight=new Float32Array(RES*RES).fill(.5),climateVisibility=new Float32Array(RES*RES).fill(1);
    const climateShadowI=((RES/2)|0)*RES+((RES/2)|0),climateOpenI=climateShadowI+8;
    climateVisibility[climateShadowI]=0;
    const climateProbe={};
    TYPES.d_temperature.eval({seaTemp:6,lapseRate:6.5,warming:10},[flatClimateHeight,climateVisibility],climateProbe);
    const terrainShadowTemperature={shadowC:climateProbe._temperatureC[climateShadowI],
      openC:climateProbe._temperatureC[climateOpenI]};
    const openSkyProbe={};
    TYPES.d_temperature.eval({seaTemp:6,lapseRate:6.5,warming:10},[flatClimateHeight,null],openSkyProbe);
    const openSkyShadowRange=mapRange(openSkyProbe._solarShadow);
    const shadowOnlyProbe={};
    TYPES.d_sunshadow.eval({reach:2750,softness:1},[flatClimateHeight],shadowOnlyProbe);
    const savedDatum=terrainDef.baseElevation;
    terrainDef.baseElevation=0;const datumLow={};
    TYPES.d_temperature.eval({seaTemp:6,lapseRate:6.5,warming:0},[flatClimateHeight,null],datumLow);
    terrainDef.baseElevation=1000;const datumHigh={};
    TYPES.d_temperature.eval({seaTemp:6,lapseRate:6.5,warming:0},[flatClimateHeight,null],datumHigh);
    terrainDef.baseElevation=savedDatum;
    const climateContracts={openSkyShadowRange,shadowNodeComputedTemperature:!!shadowOnlyProbe._temperatureC,
      datumCoolingC:datumLow._temperatureC[0]-datumHigh._temperatureC[0]};

    // Default north points toward the top of the heightfield. In the northern hemisphere,
    // a plane falling toward +Y is equator-facing and must lose more snow to solar warming.
    const n=33,N=n*n,def={scale:320,height:100,latitude:46,north:0,seaTemp:-4,lapseRate:0,solarElevation:45};
    const south=new Float32Array(N),north=new Float32Array(N);
    for(let y=0;y<n;y++)for(let x=0;x<n;x++){
      south[y*n+x]=1-y/(n-1);
      north[y*n+x]=y/(n-1);
    }
    const aspectParams={snowfall:8,meltDays:60,meltRate:10,
      solarMelt:6,repose:60,iterations:0,settle:.55};
    const southLayer=simulateSnowLayer(south,aspectParams,{res:n,terrainDef:def,quality:'interactive',resScale:1});
    const northLayer=simulateSnowLayer(north,aspectParams,{res:n,terrainDef:def,quality:'interactive',resScale:1});
    const rotatedLayer=simulateSnowLayer(south,aspectParams,{res:n,terrainDef:{...def,north:180},quality:'interactive',resScale:1});

    // A cold V-shaped valley starts with uniform snowfall. Stability relaxation may move snow,
    // but not bedrock or total snow mass; the hollow must deepen as its steep walls unload.
    const valley=new Float32Array(N),mid=(n-1)/2;
    for(let y=0;y<n;y++)for(let x=0;x<n;x++)valley[y*n+x]=Math.abs(x-mid)/mid;
    const valleyLayer=simulateSnowLayer(valley,{snowfall:6,seaTemp:-12,lapseRate:0,meltDays:0,
      meltRate:0,solarMelt:0,repose:25,iterations:60,settle:.7},
      {res:n,terrainDef:{scale:320,height:120,latitude:46,north:0,seaTemp:-12,lapseRate:0,solarElevation:45},quality:'interactive',resScale:1});
    let centre=0,edge=0,count=0;
    for(let y=0;y<n;y++){centre+=valleyLayer.depthM[y*n+mid];edge+=valleyLayer.depthM[y*n]+valleyLayer.depthM[y*n+n-1];count++;}
    centre/=count;edge/=count*2;
    const valleyMassError=Math.abs(valleyLayer.volumeM3-valleyLayer.preAvalancheM3)/valleyLayer.preAvalancheM3;

    // Aspect is necessary but insufficient: an equator-facing cell behind a ridge must be colder
    // than an equally flat, equally high cell on the sunward side.
    const sn=65,sN=sn*sn,ridge=new Float32Array(sN);
    for(let x=0;x<sn;x++){ridge[32*sn+x]=1;ridge[31*sn+x]=.65;ridge[33*sn+x]=.65;}
    const shadowLayer=simulateSnowLayer(ridge,{snowfall:8,meltDays:60,meltRate:12,solarMelt:10,
      repose:60,iterations:0,settle:.55},{res:sn,terrainDef:{scale:650,height:300,latitude:46,
        north:0,seaTemp:-4,lapseRate:0,solarElevation:20},quality:'interactive',resScale:1});
    const shadeI=20*sn+32,openI=45*sn+32;

    // The overlay responds to both camera orbit and authored map orientation.
    syncCompass();
    const compassA=$('#compassNorth').style.transform;
    const savedNorth=terrainDef.north;terrainDef.north=90;syncCompass();
    const compassB=$('#compassNorth').style.transform;terrainDef.north=savedNorth;syncCompass();

    select(snowNode);
    const labels=Array.from(document.querySelectorAll('#props label')).map(e=>e.textContent.trim());
    select(temperatureNode);
    const temperatureLabels=Array.from(document.querySelectorAll('#props label')).map(e=>e.textContent.trim());
    const temperatureEditors={numbers:document.querySelectorAll('#props input[type="number"]').length,
      ranges:document.querySelectorAll('#props input[type="range"]').length};
    const temperatureRanges={};
    document.querySelectorAll('#props .field').forEach(f=>{
      const i=f.querySelector('input[type="range"]');if(i)temperatureRanges[f.dataset.paramKey]={min:+i.min,max:+i.max,step:+i.step};
    });
    select(null);
    const terrainLabels=Array.from(document.querySelectorAll('#props label')).map(e=>e.textContent.trim());

    // Shared climate freezes standing water; a connected Snow node adds a raised snow-on-ice field.
    const savedClimate={seaTemp:terrainDef.seaTemp,lapseRate:terrainDef.lapseRate};
    const savedSceneSnow=scene.snow,savedWaterTemperature=scene.water.temperatureField;
    const coldEncoded=new Float32Array(RES*RES).fill(encodeTemperatureC(-20));
    const coldC=new Float32Array(RES*RES).fill(-20);tagTemperatureField(coldEncoded,coldC,{lapseRate:6.5});
    scene.water.temperatureField=coldEncoded;scene.snow=savedSceneSnow;updateViewport(curField,activePreviewNode());
    let snowOnIce=0;for(const d of curIceSnow)snowOnIce=Math.max(snowOnIce,d);
    let layeredCells=0,maxLayerError=0,minWaterAboveTerrain=Infinity,minSnowAboveIce=Infinity;
    for(let i=0;i<curIceSnow.length;i++)if(curIceSnow[i]>.1&&curWaterIce[i]>.5){
      layeredCells++;
      const terrainY=curHgt[i]*H_SCALE,iceY=curWater[i]*H_SCALE,expected=iceY+curIceSnow[i]/terrainDef.scale;
      maxLayerError=Math.max(maxLayerError,Math.abs(curIceSnowSurfaceY[i]-expected));
      minWaterAboveTerrain=Math.min(minWaterAboveTerrain,iceY-terrainY);
      minSnowAboveIce=Math.min(minSnowAboveIce,curIceSnowSurfaceY[i]-iceY);
    }
    let composedIceSnowCells=0,minComposedAboveIce=Infinity;
    for(let i=0;i<curIceSnow.length;i++)if(curIceSnow[i]>.1&&curWaterIce[i]>.5
      &&curSolidSurfaceY[i]>=curIceSnowSurfaceY[i]-1e-7){
      composedIceSnowCells++;minComposedAboveIce=Math.min(minComposedAboveIce,curSolidSurfaceY[i]-curWater[i]*H_SCALE);
    }
    const iceLayerRendering={layeredCells,maxLayerError,minWaterAboveTerrain,minSnowAboveIce,
      composedIceSnowCells,minComposedAboveIce,
      snowNormalAttribute:gl.getAttribLocation(waterProg,'asnowN'),
      forwardTop:gl.getShaderSource(gl.getAttachedShaders(waterProg).find(s=>gl.getShaderParameter(s,gl.SHADER_TYPE)===gl.VERTEX_SHADER)).includes('aw*uH+ais/uScale'),
      deferredSurfaceLighting:gl.getShaderSource(gl.getAttachedShaders(compProg).find(s=>gl.getShaderParameter(s,gl.SHADER_TYPE)===gl.FRAGMENT_SHADER)).includes('surfaceAo=aoAt(wuv,Pwater.y)')};
    scene.snow=null;refreshWater();
    let withoutSnow=0;for(const d of curIceSnow)withoutSnow=Math.max(withoutSnow,d);
    terrainDef.seaTemp=savedClimate.seaTemp;terrainDef.lapseRate=savedClimate.lapseRate;
    scene.snow=savedSceneSnow;scene.water.temperatureField=savedWaterTemperature;updateViewport(curField,activePreviewNode());

    // Fallback climate and datum edits must invalidate both the viewport buffer and Water phase even
    // when the terrain field identity does not change.
    const weatheringNode=nodes.find(n=>n.type==='weathering'),savedFallback={baseElevation:terrainDef.baseElevation,
      seaTemp:terrainDef.seaTemp,lapseRate:terrainDef.lapseRate},savedFallbackSnow=scene.snow;
    scene.snow=null;scene.water.temperatureField=null;
    const readTemperature0=()=>{const a=new Float32Array(1);gl.bindBuffer(gl.ARRAY_BUFFER,buffers.temperature);
      gl.getBufferSubData(gl.ARRAY_BUFFER,0,a);return a[0];};
    terrainDef.baseElevation=0;terrainDef.seaTemp=12;terrainDef.lapseRate=6.5;
    updateViewport(curField,weatheringNode);const fallbackWarm=readTemperature0();
    let warmIce=0;for(const v of curWaterIce)warmIce+=v;
    terrainDef.baseElevation=3000;updateViewport(curField,weatheringNode);const fallbackHigh=readTemperature0();
    let highIce=0;for(const v of curWaterIce)highIce+=v;
    const fallbackInvalidation={temperatureDelta:fallbackWarm-fallbackHigh,warmIce,highIce,
      signature:lastFallbackClimateSig};
    Object.assign(terrainDef,savedFallback);scene.snow=savedFallbackSnow;
    scene.water.temperatureField=savedWaterTemperature;updateViewport(curField,activePreviewNode());

    TEMP_UNIT='C';syncClimateReadout();const tempC=$('#climateReadout').textContent;
    $('#climateReadout').click();const tempF=$('#climateReadout').textContent;
    TEMP_UNIT='C';syncClimateReadout();

    // The temperature is a modifiable graph field, not metadata stranded on its generator.
    // A localized "lava" source heats the connected Temperature Modify node to 900 °C; Snow and
    // the viewport scene must consume that modified field while cells outside the source stay cold.
    const lava=makeNode('shape',1040,510);Object.assign(lava.params,{kind:'circle',x:.5,y:.5,size:.2,aspect:1,falloff:.12,invert:'off'});
    temperatureModifyNode.params.mode='minimum';temperatureModifyNode.params.targetC=900;temperatureModifyNode.params.amount=1;
    edges.push({from:lava.id,to:temperatureModifyNode.id,slot:1});markDirtyFrom(lava.id);evalGraph();
    const modifierC=temperatureCFromField(temperatureModifyNode._field),centreI=((RES/2)|0)*RES+((RES/2)|0),cornerI=2*RES+2;
    const soften=makeNode('blur',1200,510);soften.params.radius=2;soften.params.strength=1;
    edges=edges.filter(e=>!(e.to===snowNode.id&&e.slot===1));
    edges.push({from:temperatureModifyNode.id,to:soften.id,slot:0},{from:soften.id,to:snowNode.id,slot:1});
    markDirtyFrom(soften.id);evalGraph();
    const modifiedC=temperatureCFromField(soften._field);
    const biomeMask=TYPES.tempmask.eval({lo:850,hi:1000,falloff:10,invert:'off'},[soften._field]);
    const modification={kind:fieldMetadata(soften._field)&&fieldMetadata(soften._field).kind,
      sourceCentreC:modifierC[centreI],centreC:modifiedC[centreI],cornerC:modifiedC[cornerI],
      baseCornerC:temperatureNode._temperatureC[cornerI],biomeCentre:biomeMask[centreI],biomeCorner:biomeMask[cornerI],
      snowReadsModified:Math.abs(snowNode._snowLayer.temperatureC[centreI]-modifiedC[centreI])<1e-4,
      sceneReadsModified:scene.snow&&scene.snow.temperatureField===soften._field,
      waterReadsModified:scene.water&&scene.water.temperatureField===temperatureModifyNode._field};
    // Only unit-preserving graph operations may retain Celsius. Tonal remapping and arbitrary
    // grayscale inputs must not silently become physical temperatures.
    const remapped=TYPES.levels.eval({inLo:0,inHi:1,gamma:.5,outLo:0,outHi:1},[temperatureModifyNode._field]);
    propagateFieldMetadata(remapped,[temperatureModifyNode._field],TYPES.levels);
    const invalidModifier={};
    const invalidModified=TYPES.d_heat.eval({mode:'offset',offsetC:10,amount:1},[heightNode._field],invalidModifier);
    const invalidSelect=TYPES.tempmask.eval({lo:-10,hi:10,falloff:2,invert:'off'},[heightNode._field]);
    let invalidSelectMax=0;for(const v of invalidSelect)invalidSelectMax=Math.max(invalidSelectMax,v);
    const fieldContracts={remapKind:fieldMetadata(remapped)&&fieldMetadata(remapped).kind,
      invalidModifyKind:fieldMetadata(invalidModified)&&fieldMetadata(invalidModified).kind,
      invalidModifyWarning:invalidModifier._inputError,
      invalidSelectMax};
    const boxes=[document.getElementById('viewportCompass'),document.getElementById('climateReadout'),
      document.querySelector('.vp-rail')].map(el=>el.getBoundingClientRect());
    const overlaps=(a,b)=>a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top;
    return{
      layer:{length:layer&&layer.depthM.length,maxDepthM:layer&&layer.maxDepthM,
        coverage:layer&&layer.coverage,iterationsRun:layer&&layer.iterationsRun,volumeError},
      rendering:{displacement,snowAttribute:gl.getAttribLocation(terrainProg,'snow'),
        temperatureAttribute:gl.getAttribLocation(terrainProg,'temperature'),
        sunVisibilityAttribute:gl.getAttribLocation(terrainProg,'sunvis'),
        linked:gl.getProgramParameter(terrainProg,gl.LINK_STATUS)},
      aspect:{south:mean(southLayer.depthM),north:mean(northLayer.depthM),rotated:mean(rotatedLayer.depthM)},
      insolation:{shadeTemp:shadowLayer.temperatureC[shadeI],openTemp:shadowLayer.temperatureC[openI],
        shade:shadowLayer.solarShadow[shadeI],open:shadowLayer.solarShadow[openI],
        mapLength:shadowLayer.temperatureC.length},
      valley:{centre,edge,massError:valleyMassError,movedM3:valleyLayer.movedM3},
      compass:{before:compassA,after:compassB,label:$('#viewportCompass').getAttribute('aria-label')},
      climate:{snowOnIce,withoutSnow,liquidSnow,liquidCells,tempC,tempF,terrainLabels,
        temperatureRange:mapRange(temperatureNode&&temperatureNode._temperatureC),
        shadowRange:mapRange(shadowNode&&shadowNode._solarShadow),terrainShadowTemperature,climateContracts,
        fallbackInvalidation},
      defaultGraph,
      temperatureField:{...modification,labels:temperatureLabels,editors:temperatureEditors,ranges:temperatureRanges,
        fieldContracts},
      iceLayerRendering,
      hud:{compassTemperature:overlaps(boxes[0],boxes[1]),compassRail:overlaps(boxes[0],boxes[2]),temperatureRail:overlaps(boxes[1],boxes[2])},
      labels
    };
  });

  const ok=result.layer.length===512*512
    &&result.layer.maxDepthM>0.1&&result.layer.coverage>.01&&result.layer.volumeError<1e-5
    &&result.rendering.linked&&result.rendering.snowAttribute>=0&&result.rendering.temperatureAttribute>=0
    &&result.rendering.sunVisibilityAttribute>=0&&result.rendering.displacement>1e-5
    &&result.aspect.north>result.aspect.south+1&&result.aspect.rotated>result.aspect.south+1
    &&result.insolation.openTemp>result.insolation.shadeTemp+3
    &&result.insolation.open>result.insolation.shade+.35&&result.insolation.mapLength===65*65
    &&result.valley.centre>6.05&&result.valley.centre>result.valley.edge
    &&result.valley.movedM3>0&&result.valley.massError<1e-5
    &&result.compass.before!==result.compass.after&&result.compass.label.includes('Map north')
    &&['Snowfall','Melt period','Degree-day melt',
      'Snow repose angle','Settling iterations','Settling rate'].every(label=>result.labels.includes(label))
    &&['Base elevation','Fallback sea-level temperature','Fallback temperature lapse',
      'Climate sun elevation'].every(label=>result.climate.terrainLabels.includes(label))
    &&result.climate.snowOnIce>.1&&result.climate.withoutSnow===0
    &&result.climate.liquidCells>0&&result.climate.liquidSnow===0
    &&result.climate.temperatureRange[1]>result.climate.temperatureRange[0]
    &&result.climate.shadowRange[1]>result.climate.shadowRange[0]
    &&result.climate.terrainShadowTemperature.openC>result.climate.terrainShadowTemperature.shadowC+5
    &&result.climate.climateContracts.openSkyShadowRange[0]===1
    &&result.climate.climateContracts.openSkyShadowRange[1]===1
    &&!result.climate.climateContracts.shadowNodeComputedTemperature
    &&Math.abs(result.climate.climateContracts.datumCoolingC-6.5)<.01
    &&Math.abs(result.climate.fallbackInvalidation.temperatureDelta-19.5)<.01
    &&result.climate.fallbackInvalidation.highIce>result.climate.fallbackInvalidation.warmIce
    &&result.climate.fallbackInvalidation.signature.startsWith('3000|')
    &&result.climate.tempC.includes('°C')&&result.climate.tempF.includes('°F')
    &&Object.values(result.defaultGraph).every(Boolean)
    &&result.temperatureField.kind==='temperature'&&result.temperatureField.sourceCentreC>899&&result.temperatureField.centreC>850
    &&Math.abs(result.temperatureField.cornerC-result.temperatureField.baseCornerC)<2
    &&result.temperatureField.biomeCentre>.9&&result.temperatureField.biomeCorner<.01
    &&result.temperatureField.snowReadsModified&&result.temperatureField.sceneReadsModified
    &&result.temperatureField.waterReadsModified
    &&result.temperatureField.fieldContracts.remapKind==null
    &&result.temperatureField.fieldContracts.invalidModifyKind==null
    &&result.temperatureField.fieldContracts.invalidModifyWarning.includes('physical Temperature')
    &&result.temperatureField.fieldContracts.invalidSelectMax===0
    &&['Sea-level temperature','Altitude lapse rate','Solar warming'].every(label=>result.temperatureField.labels.includes(label))
    &&result.temperatureField.editors.numbers===0&&result.temperatureField.editors.ranges===3
    &&result.temperatureField.ranges.seaTemp.min===-50&&result.temperatureField.ranges.seaTemp.max===50
    &&result.temperatureField.ranges.lapseRate.min===-10&&result.temperatureField.ranges.lapseRate.max===15
    &&result.temperatureField.ranges.warming.min===0&&result.temperatureField.ranges.warming.max===50
    &&result.iceLayerRendering.layeredCells>0&&result.iceLayerRendering.maxLayerError<1e-7
    &&result.iceLayerRendering.minWaterAboveTerrain>0&&result.iceLayerRendering.minSnowAboveIce>0
    &&result.iceLayerRendering.composedIceSnowCells>0&&result.iceLayerRendering.minComposedAboveIce>0
    &&result.iceLayerRendering.snowNormalAttribute>=0&&result.iceLayerRendering.forwardTop
    &&result.iceLayerRendering.deferredSurfaceLighting
    &&!result.hud.compassTemperature&&!result.hud.compassRail&&!result.hud.temperatureRail
    &&!errors.length;
  console.log(JSON.stringify({result,errors,ok},null,2));
  await browser.close();
  process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
