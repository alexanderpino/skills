import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { clamp, fieldH, fieldW, gnoise, newField, terrainDef, worldSampleAt } from '../../legacy.js'

export const bounded=(value,initial,lo,hi,integer=false)=>{
  const finite=Number.isFinite(value)?value:initial
  const result=clamp(finite,lo,hi)
  return integer?Math.round(result):result
}
export const enumValue=(value,initial,values,label)=>{
  const result=value==null?initial:value
  if(!values.includes(result))throw new RangeError(`${label} unknown value "${result}"`)
  return result
}
export const mix32=value=>{
  let h=value>>>0
  h=Math.imul(h^(h>>>16),0x7feb352d)>>>0
  h=Math.imul(h^(h>>>15),0x846ca68b)>>>0
  return(h^(h>>>16))>>>0
}
export const hashText=text=>{
  let h=2166136261>>>0
  for(let i=0;i<text.length;i++){h^=text.charCodeAt(i);h=Math.imul(h,16777619)>>>0}
  return h
}
export const effectiveSeed=(type,seed,nodeId=0,rootSeed=0)=>mix32((seed+hashText(type)
  +Math.imul(Number(nodeId)||0,0x9e3779b1)+Number(rootSeed||0))>>>0)
export const randomStream=seed=>{
  let state=mix32(seed)
  return()=>{state=(Math.imul(state^(state>>>15),2246822519)+374761393)>>>0;return state/4294967296}
}
export function landformFbmAt(worldX,worldY,wavelengthM,seed,options,cellM=0){
  let count=options.octaves
  if(cellM>0){count=0;for(let k=0;k<options.octaves;k++){
    if(wavelengthM/Math.pow(options.lacunarity,k)<2*cellM)break
    count++
  }}
  if(count===0)return 0
  let sum=0,total=0,weight=1
  for(let k=0;k<count;k++){
    const f=Math.pow(options.lacunarity,k)/wavelengthM
    sum+=weight*gnoise(worldX*f,worldY*f,(seed+7*k)>>>0);total+=weight;weight*=options.gain
  }
  return 2*sum/total-1
}
export const noiseOptions=params=>({octaves:bounded(params.octaves,4,1,10,true),
  lacunarity:bounded(params.lacunarity,2,1.25,4),gain:bounded(params.gain,.5,.1,.9)})
export function rasterFromWorld(sample){
  const n=fieldW(),nh=fieldH(),out=newField()
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const point=worldSampleAt(x,y)
    out[y*n+x]=Math.fround(sample(point[0],point[1],x,y))
  }
  return out
}

export function craterOptions(params={}){
  return{x:bounded(params.x,.5,0,1),y:bounded(params.y,.5,0,1),
    diameterM:bounded(params.diameterM,1000,10,5000),gravity:bounded(params.gravity,9.81,.1,30),
    depositFraction:bounded(params.depositFraction,.9,0,1),amount:bounded(params.amount,1,0,2)}
}

export function craterProfileM(radiusM,params={}){
  const o=params.diameterM==null?craterOptions(params):params,D=o.diameterM,R=D/2,u=radiusM/R
  const transition=3200*(9.81/o.gravity)
  const depth=D<transition?.2*D:.2*transition*Math.pow(D/transition,.3)
  const bowl=u<1?-depth*(1-u*u):0
  const amplitude=3*o.depositFraction*depth/8
  const ejecta=u>=1&&u<=3?amplitude*Math.pow(u,-3):0
  const uplift=D>=transition?.5*depth*Math.exp(-Math.pow(u/.18,2)):0
  return o.amount*(bowl+ejecta+uplift)
}

export function craterField(params={}){
  const o=craterOptions(params),cx=o.x*terrainDef.scale,cy=o.y*terrainDef.scale
  return rasterFromWorld((worldX,worldY)=>craterProfileM(Math.hypot(worldX-cx,worldY-cy),o)/terrainDef.height)
}

const metre=value=>Math.round(value)+' m'
const def=definePlugin({
  type:'crater',cat:'gen',name:'Crater',ins:[],
  desc:'Reduced vertical impact profile with a bowl, grounded ejecta decay, and complex-crater uplift.',
  params:[P.slider('x','Position X',0,1,.5,.01,value=>metre(value*terrainDef.scale)),
    P.slider('y','Position Y',0,1,.5,.01,value=>metre(value*terrainDef.scale)),
    P.slider('diameterM','Diameter',10,5000,1000,10,metre),
    P.slider('gravity','Gravity',.1,30,9.81,.01,value=>value.toFixed(2)+' m/s\u00b2'),
    P.slider('depositFraction','Deposit fraction',0,1,.9,.01),
    P.slider('amount','Amount',0,2,1,.01)],
  eval:p=>craterField(p),
  note:'A transparent reduced vertical radial model. It does not model oblique ejecta, rays, terraces, secondaries, or any unpublished branded implementation.'
})
def.options=craterOptions
def.profile=craterProfileM
def.field=craterField
def.worldSampleAt=(...args)=>worldSampleAt(...args)

export default def