import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { cellSizeM, clamp, terrainDef } from '../../legacy.js'
import { bounded, effectiveSeed, landformFbmAt, noiseOptions, rasterFromWorld } from './crater.js'

const smoothstep=(a,b,value)=>{const t=clamp((value-a)/(b-a),0,1);return t*t*(3-2*t)}
export function islandOptions(params={}){
  const o={x:bounded(params.x,.5,0,1),y:bounded(params.y,.5,0,1),radiusXM:bounded(params.radiusXM,1600,50,5000),
    radiusYM:bounded(params.radiusYM,1200,50,5000),angleDeg:bounded(params.angleDeg,0,0,360),
    coastWidthM:bounded(params.coastWidthM,350,1,2500),elevationM:bounded(params.elevationM,700,0,5000),
    roughnessM:bounded(params.roughnessM,220,0,2500),detailWavelengthM:bounded(params.detailWavelengthM,700,10,5000),
    warpM:bounded(params.warpM,180,0,2500),warpWavelengthM:bounded(params.warpWavelengthM,1800,10,10000),
    seed:bounded(params.seed,7,0,4294967295,true)>>>0,...noiseOptions(params)}
  const radius=Math.min(o.radiusXM,o.radiusYM);o.coastWidthM=Math.min(o.coastWidthM,radius);o.warpM=Math.min(o.warpM,radius/2)
  if(o.angleDeg===360)o.angleDeg=0
  return o
}
export function islandProfileM(worldX,worldY,params={},seedOverride=null,cellM=0){
  const o=params.radiusXM==null?islandOptions(params):params,seed=seedOverride==null?o.seed:seedOverride
  const dx=worldX-o.x*terrainDef.scale,dy=worldY-o.y*terrainDef.scale,a=o.angleDeg*Math.PI/180
  const ca=Math.cos(a),sa=Math.sin(a),qx=(dx*ca-dy*sa)/o.radiusXM,qy=(dx*sa+dy*ca)/o.radiusYM
  const minimum=Math.min(o.radiusXM,o.radiusYM),warp=o.warpM/minimum
  const wx=warp*landformFbmAt(worldX,worldY,o.warpWavelengthM,seed+101,o,cellM)
  const wy=warp*landformFbmAt(worldX,worldY,o.warpWavelengthM,seed+202,o,cellM)
  const rho=Math.hypot(qx+wx,qy+wy),envelope=1-smoothstep(1-o.coastWidthM/minimum,1,rho)
  const relief=o.elevationM+o.roughnessM*landformFbmAt(worldX,worldY,o.detailWavelengthM,seed,o,cellM)
  return Math.max(0,envelope*relief)
}
export function islandField(params={},nodeId=0,rootSeed=0){
  const o=islandOptions(params),seed=effectiveSeed('island',o.seed,nodeId,rootSeed),cellM=cellSizeM()
  return rasterFromWorld((worldX,worldY)=>islandProfileM(worldX,worldY,o,seed,cellM)/terrainDef.height)
}
const metre=value=>Math.round(value)+' m',degree=value=>Math.round(value)+'\u00b0'
const def=definePlugin({type:'island',cat:'gen',name:'Island',ins:[],desc:'Openly authored asymmetric island mass with an elliptical warped coast.',
  params:[P.slider('x','Position X',0,1,.5,.01,value=>metre(value*terrainDef.scale)),P.slider('y','Position Y',0,1,.5,.01,value=>metre(value*terrainDef.scale)),
    P.slider('radiusXM','Radius X',50,5000,1600,10,metre),P.slider('radiusYM','Radius Y',50,5000,1200,10,metre),P.slider('angleDeg','Angle',0,360,0,1,degree),
    P.slider('coastWidthM','Coast width',1,2500,350,1,metre),P.slider('elevationM','Elevation',0,5000,700,10,metre),
    P.slider('roughnessM','Roughness',0,2500,220,1,metre),P.slider('detailWavelengthM','Detail wavelength',10,5000,700,10,metre),
    P.slider('warpM','Coast warp',0,2500,180,1,metre),P.slider('warpWavelengthM','Warp wavelength',10,10000,1800,10,metre),
    P.int('octaves','Octaves',1,10,4),P.slider('lacunarity','Lacunarity',1.25,4,2,.05),P.slider('gain','Gain',.1,.9,.5,.01),P.seed('seed','Seed',7)],
  eval:(p,ins,node)=>islandField(p,node?.id,terrainDef.seed),note:'An authored Terrain Studio composition, not a model of a specific real island or an unpublished branded algorithm.'})
def.options=islandOptions;def.profile=islandProfileM;def.field=islandField
export default def