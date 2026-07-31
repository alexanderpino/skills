import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { cellSizeM, terrainDef } from '../../legacy.js'
import { bounded, effectiveSeed, enumValue, landformFbmAt, noiseOptions, rasterFromWorld } from './crater.js'

export function volcanoOptions(params={}){
  const o={style:enumValue(params.style,'stratovolcano',['stratovolcano'],'Volcano style'),x:bounded(params.x,.5,0,1),y:bounded(params.y,.5,0,1),
    radiusM:bounded(params.radiusM,1700,50,5000),heightM:bounded(params.heightM,1200,1,5000),profileExponent:bounded(params.profileExponent,2.2,.25,8),
    craterRadiusM:bounded(params.craterRadiusM,180,1,2500),craterDepthM:bounded(params.craterDepthM,90,0,2500),rimHeightM:bounded(params.rimHeightM,35,0,1000),
    rimWidthM:bounded(params.rimWidthM,45,1,1000),barrancoCount:bounded(params.barrancoCount,12,1,64,true),barrancoDepth:bounded(params.barrancoDepth,.18,0,.95),
    barrancoWavelengthM:bounded(params.barrancoWavelengthM,700,10,5000),amount:bounded(params.amount,1,0,2),seed:bounded(params.seed,7,0,4294967295,true)>>>0,
    ...noiseOptions(params)}
  o.craterRadiusM=Math.min(o.craterRadiusM,Math.max(1,Math.fround(o.radiusM)-Math.abs(Math.fround(o.radiusM))*2**-23))
  return o
}
export function volcanoProfileM(worldX,worldY,params={},seedOverride=null,cellM=0){
  const o=params.radiusM==null?volcanoOptions(params):params,seed=seedOverride==null?o.seed:seedOverride
  const dx=worldX-o.x*terrainDef.scale,dy=worldY-o.y*terrainDef.scale,r=Math.hypot(dx,dy),rn=r/o.radiusM,theta=Math.atan2(dy,dx)
  const base=rn<=1?Math.max(0,Math.pow(1-rn,o.profileExponent)):0
  const noise=landformFbmAt(worldX,worldY,o.barrancoWavelengthM,seed,o,cellM)
  const grooves=.5*(1+Math.cos(o.barrancoCount*theta+2*Math.PI*noise))
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
const def=definePlugin({type:'volcano',cat:'gen',name:'Volcano',ins:[],desc:'A stratovolcano primitive with central crater, rim, and authored radial barrancos.',
  params:[P.select('style','Style',[['stratovolcano','Stratovolcano']],'stratovolcano'),P.slider('x','Position X',0,1,.5,.01,value=>metre(value*terrainDef.scale)),
    P.slider('y','Position Y',0,1,.5,.01,value=>metre(value*terrainDef.scale)),P.slider('radiusM','Radius',50,5000,1700,10,metre),
    P.slider('heightM','Height',1,5000,1200,10,metre),P.slider('profileExponent','Profile exponent',.25,8,2.2,.05),
    P.slider('craterRadiusM','Crater radius',1,2500,180,1,metre),P.slider('craterDepthM','Crater depth',0,2500,90,1,metre),
    P.slider('rimHeightM','Rim height',0,1000,35,1,metre),P.slider('rimWidthM','Rim width',1,1000,45,1,metre),
    P.int('barrancoCount','Barranco count',1,64,12),P.slider('barrancoDepth','Barranco depth',0,.95,.18,.01),
    P.slider('barrancoWavelengthM','Barranco wavelength',10,5000,700,10,metre),P.slider('amount','Amount',0,2,1,.01),
    P.int('octaves','Octaves',1,10,4),P.slider('lacunarity','Lacunarity',1.25,4,2,.05),P.slider('gain','Gain',.1,.9,.5,.01),P.seed('seed','Seed',7)],
  eval:(p,ins,node)=>volcanoField(p,node?.id,terrainDef.seed),note:'This named stratovolcano is a transparent terrain primitive, not an impact crater or a claim about unpublished branded internals.'})
def.options=volcanoOptions;def.profile=volcanoProfileM;def.field=volcanoField
export default def