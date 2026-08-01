import { definePlugin } from '../../core/registry.js'
import { P, WHEN } from '../../core/params.js'
import { cellSizeM, terrainDef } from '../../legacy.js'
import { bounded, effectiveSeed, enumValue, landformFbmAt, noiseOptions, rasterFromWorld } from './crater.js'

export function volcanoOptions(params={}){
  const style=enumValue(params.style,'stratovolcano',['shield','stratovolcano'],'Volcano style')
  const value=(key,legacy,initial)=>params[key]??params[legacy]??initial
  const prefix=style==='shield'?'shield':'strato'
  const defaults=style==='shield'
    ? {radiusM:3500,heightM:300,craterRadiusM:180,craterDepthM:20,rimHeightM:8,rimWidthM:45}
    : {radiusM:2500,heightM:1000,craterRadiusM:100,craterDepthM:120,rimHeightM:30,rimWidthM:35}
  const noise=noiseOptions({octaves:value('stratoOctaves','octaves',4),lacunarity:value('stratoLacunarity','lacunarity',2),gain:value('stratoGain','gain',.5)})
  const o={style,x:bounded(params.x,.5,0,1),y:bounded(params.y,.5,0,1),
    radiusM:bounded(value(`${prefix}RadiusM`,'radiusM',defaults.radiusM),defaults.radiusM,50,5000),
    heightM:bounded(value(`${prefix}HeightM`,'heightM',defaults.heightM),defaults.heightM,1,5000),
    craterRadiusM:bounded(value(`${prefix}CraterRadiusM`,'craterRadiusM',defaults.craterRadiusM),defaults.craterRadiusM,1,2500),
    craterDepthM:bounded(value(`${prefix}CraterDepthM`,'craterDepthM',defaults.craterDepthM),defaults.craterDepthM,0,2500),
    rimHeightM:bounded(value(`${prefix}RimHeightM`,'rimHeightM',defaults.rimHeightM),defaults.rimHeightM,0,1000),
    rimWidthM:bounded(value(`${prefix}RimWidthM`,'rimWidthM',defaults.rimWidthM),defaults.rimWidthM,1,1000),
    barrancoCount:bounded(value('stratoBarrancoCount','barrancoCount',12),12,1,64,true),
    barrancoDepth:style==='shield'?0:bounded(value('stratoBarrancoDepth','barrancoDepth',.18),.18,0,.95),
    barrancoWavelengthM:bounded(value('stratoBarrancoWavelengthM','barrancoWavelengthM',700),700,10,5000),
    amount:bounded(params.amount,1,0,2),seed:bounded(params.seed,7,0,4294967295,true)>>>0,...noise}
  o.craterRadiusM=Math.min(o.craterRadiusM,Math.max(1,Math.fround(o.radiusM)-Math.abs(Math.fround(o.radiusM))*2**-23))
  return o
}
export function volcanoProfileM(worldX,worldY,params={},seedOverride=null,cellM=0){
  const o=params.radiusM==null?volcanoOptions(params):params,seed=seedOverride==null?o.seed:seedOverride
  const dx=worldX-o.x*terrainDef.scale,dy=worldY-o.y*terrainDef.scale,r=Math.hypot(dx,dy),rn=r/o.radiusM,theta=Math.atan2(dy,dx)
  const base=rn<=1?Math.max(0,o.style==='shield'?1-Math.pow(rn,1.7):Math.pow(1-rn,2.2)):0
  const noise=o.style==='shield'?0:landformFbmAt(worldX,worldY,o.barrancoWavelengthM,seed,o,cellM)
  const grooves=o.style==='shield'?0:.5*(1+Math.cos(o.barrancoCount*theta+2*Math.PI*noise))
  const edifice=o.heightM*base*(1-o.barrancoDepth*grooves*rn),craterRho=r/o.craterRadiusM
  const summit=craterRho<1?-o.craterDepthM*Math.pow(1-craterRho*craterRho,1.5):0
  const rim=o.rimHeightM*Math.exp(-.5*Math.pow((r-o.craterRadiusM)/o.rimWidthM,2))
  return o.amount*Math.max(0,edifice+summit+rim)
}
export function volcanoField(params={},nodeId=0,rootSeed=0){
  const o=volcanoOptions(params),seed=effectiveSeed('volcano',o.seed,nodeId,rootSeed),cellM=cellSizeM()
  return rasterFromWorld((worldX,worldY)=>volcanoProfileM(worldX,worldY,o,seed,cellM)/terrainDef.height)
}
const metre=value=>Math.round(value)+' m'
const profile=value=>value.toFixed(3)+'\u00b0'
const slope=(height,radius,a,b,kind)=>Math.atan(Math.abs(height/radius*((kind==='shield'?1-b**1.7:(1-b)**2.2)-(kind==='shield'?1-a**1.7:(1-a)**2.2))/(b-a)))*180/Math.PI
const def=definePlugin({type:'volcano',cat:'gen',name:'Volcano',ins:[],desc:'Builds either a broad shield dome or a summit-steepening stratovolcano with a central depression.',
  params:[P.select('style','Style',[['shield','Shield'],['stratovolcano','Stratovolcano']],'stratovolcano'),P.slider('x','Position X',0,1,.5,.01,value=>metre(value*terrainDef.scale)),
    P.slider('y','Position Y',0,1,.5,.01,value=>metre(value*terrainDef.scale)),
    WHEN(P.slider('shieldRadiusM','Radius',50,5000,3500,10,metre),'style','shield'),WHEN(P.slider('shieldHeightM','Height',1,5000,300,10,metre),'style','shield'),
    WHEN(P.slider('shieldCraterRadiusM','Depression radius',1,2500,180,1,metre),'style','shield'),WHEN(P.slider('shieldCraterDepthM','Depression depth',0,2500,20,1,metre),'style','shield'),
    WHEN(P.slider('shieldRimHeightM','Rim height',0,1000,8,1,metre),'style','shield'),WHEN(P.slider('shieldRimWidthM','Rim width',1,1000,45,1,metre),'style','shield'),
    WHEN(P.slider('stratoRadiusM','Radius',50,5000,2500,10,metre),'style','stratovolcano'),WHEN(P.slider('stratoHeightM','Height',1,5000,1000,10,metre),'style','stratovolcano'),
    WHEN(P.slider('stratoCraterRadiusM','Crater radius',1,2500,100,1,metre),'style','stratovolcano'),WHEN(P.slider('stratoCraterDepthM','Crater depth',0,2500,120,1,metre),'style','stratovolcano'),
    WHEN(P.slider('stratoRimHeightM','Rim height',0,1000,30,1,metre),'style','stratovolcano'),WHEN(P.slider('stratoRimWidthM','Rim width',1,1000,35,1,metre),'style','stratovolcano'),
    WHEN(P.int('stratoBarrancoCount','Barranco count',1,64,12),'style','stratovolcano'),WHEN(P.slider('stratoBarrancoDepth','Barranco depth',0,.95,.18,.01),'style','stratovolcano'),
    WHEN(P.slider('stratoBarrancoWavelengthM','Barranco wavelength',10,5000,700,10,metre),'style','stratovolcano'),P.slider('amount','Amount',0,2,1,.01),
    WHEN(P.int('stratoOctaves','Barranco octaves',1,10,4),'style','stratovolcano'),WHEN(P.slider('stratoLacunarity','Barranco lacunarity',1.25,4,2,.05),'style','stratovolcano'),
    WHEN(P.slider('stratoGain','Barranco gain',.1,.9,.5,.01),'style','stratovolcano'),P.seed('seed','Seed',7)],
  eval:(p,ins,node)=>volcanoField(p,node?.id,terrainDef.seed),
  info:node=>{const o=volcanoOptions(node?.params||{});if(o.style==='shield'){const angle=slope(o.heightM,o.radiusM,.25,.75,'shield');return `Shield flank ${profile(angle)} (grounded 2-10\u00b0 band): ${angle>=2&&angle<=10?'inside':'outside'}. Shallow summit depression; barrancos disabled.`}const upper=slope(o.heightM,o.radiusM,.2,.4,'stratovolcano'),lower=slope(o.heightM,o.radiusM,.6,.8,'stratovolcano');return `Stratovolcano upper flank ${profile(upper)} (grounded 20-35\u00b0 band): ${upper>=20&&upper<=35?'inside':'outside'}; lower ${profile(lower)}. Summit crater and ${o.barrancoCount} authored radial barrancos.`},
  note:'These are transparent parametric morphology families; barrancos are authored grooves intended to precede process erosion.'})
def.options=volcanoOptions;def.profile=volcanoProfileM;def.field=volcanoField
export default def