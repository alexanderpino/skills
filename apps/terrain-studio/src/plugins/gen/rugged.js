import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { cellSizeM, terrainDef } from '../../legacy.js'
import { bounded, effectiveSeed, landformFbmAt, noiseOptions, randomStream, rasterFromWorld } from './crater.js'
import { poissonPlacement } from './craterfield.js'

export function ruggedOptions(params={}){
  return{blockCount:bounded(params.blockCount,36,1,512,true),minSpacingM:bounded(params.minSpacingM,300,10,5000),
    blockRadiusM:bounded(params.blockRadiusM,180,5,2500),blockVariation:bounded(params.blockVariation,.35,0,.9),
    blockHeightM:bounded(params.blockHeightM,180,0,2500),blockExponent:bounded(params.blockExponent,1.8,.25,8),
    blockNoise:bounded(params.blockNoise,.35,0,1),blockWavelengthM:bounded(params.blockWavelengthM,120,10,5000),
    baseElevationM:bounded(params.baseElevationM,120,0,2500),macroReliefM:bounded(params.macroReliefM,260,0,2500),
    macroWavelengthM:bounded(params.macroWavelengthM,900,10,10000),amount:bounded(params.amount,1,0,2),
    seed:bounded(params.seed,7,0,4294967295,true)>>>0,...noiseOptions(params)}
}
export function ruggedPlan(params={},nodeId=0,rootSeed=0){
  const o=ruggedOptions(params),seed=effectiveSeed('rugged',o.seed,nodeId,rootSeed)
  return poissonPlacement(o.blockCount,o.minSpacingM,seed)
}
export function ruggedBlockProfileM(distanceNormalized,params,noise){
  if(distanceNormalized>=1)return 0
  return params.blockHeightM*Math.pow(1-distanceNormalized,params.blockExponent)*(1+params.blockNoise*noise)
}
export function ruggedField(params={},nodeId=0,rootSeed=0){
  const o=ruggedOptions(params),seed=effectiveSeed('rugged',o.seed,nodeId,rootSeed),plan=poissonPlacement(o.blockCount,o.minSpacingM,seed)
  const variation=randomStream(seed+1907),blocks=plan.points.map((point,index)=>({x:point.x,y:point.y,index,
    radius:bounded(o.blockRadiusM*(1+o.blockVariation*(2*variation()-1)),o.blockRadiusM,5,2500)}))
  const cellM=cellSizeM()
  return rasterFromWorld((worldX,worldY)=>{
    const macro=landformFbmAt(worldX,worldY,o.macroWavelengthM,seed,o,cellM)
    const base=Math.max(0,o.baseElevationM+o.macroReliefM*macro);let block=0
    for(const item of blocks){
      const distance=Math.hypot(worldX-item.x,worldY-item.y)/item.radius
      if(distance>=1)continue
      const noise=landformFbmAt(worldX,worldY,o.blockWavelengthM,seed+4099*item.index,o,cellM)
      block=Math.max(block,ruggedBlockProfileM(distance,o,noise))
    }
    return o.amount*Math.max(0,base+block)/terrainDef.height
  })
}
const metre=value=>Math.round(value)+' m'
const def=definePlugin({type:'rugged',cat:'gen',name:'Rugged',ins:[],desc:'Authored scattered-block base.',
  params:[P.int('blockCount','Block count',1,512,36),P.slider('minSpacingM','Minimum spacing',10,5000,300,10,metre),
    P.slider('blockRadiusM','Block radius',5,2500,180,5,metre),P.slider('blockVariation','Block variation',0,.9,.35,.01),
    P.slider('blockHeightM','Block height',0,2500,180,5,metre),P.slider('blockExponent','Block exponent',.25,8,1.8,.05),
    P.slider('blockNoise','Block noise',0,1,.35,.01),P.slider('blockWavelengthM','Block wavelength',10,5000,120,5,metre),
    P.slider('baseElevationM','Base elevation',0,2500,120,5,metre),P.slider('macroReliefM','Macro relief',0,2500,260,5,metre),
    P.slider('macroWavelengthM','Macro wavelength',10,10000,900,10,metre),P.slider('amount','Amount',0,2,1,.01),
    P.int('octaves','Octaves',1,10,4),P.slider('lacunarity','Lacunarity',1.25,4,2,.05),P.slider('gain','Gain',.1,.9,.5,.01),P.seed('seed','Seed',7)],
  eval:(p,ins,node)=>ruggedField(p,node?.id,terrainDef.seed),note:'Authored scattered-block base. It is not fracture, talus, erosion, or a geological simulation, and makes no branded-internal claim.'})
def.options=ruggedOptions;def.planPlacement=ruggedPlan;def.blockProfile=ruggedBlockProfileM;def.field=ruggedField
export default def