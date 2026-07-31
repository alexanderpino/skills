import { definePlugin } from '../../core/registry.js'
import { P, WHEN } from '../../core/params.js'
import { clamp, curvatureField, fieldH, fieldW, gnoise, maskApply, newField,
  occlusionField, slopeOf, terrainDef, wearField } from '../../legacy.js'

const STYLES=['roughen','distress','groundtexture','rocknoise','bulbous','pockmarks','contours','grid']
const RANDOM_STYLES=new Set(['roughen','distress','groundtexture','rocknoise','bulbous','pockmarks'])
const metre=v=>(v<10?v.toFixed(2):Math.round(v))+" m"
const deg=v=>Math.round(v)+"\u00b0"
const smoothstep=(a,b,value)=>{
  if(a===b)return value<a?0:1
  const t=clamp((value-a)/(b-a),0,1)
  return t*t*(3-2*t)
}
const hashText=text=>{
  let h=2166136261>>>0
  for(let i=0;i<text.length;i++){h^=text.charCodeAt(i);h=Math.imul(h,16777619)>>>0}
  return h
}
const mix32=value=>{
  let h=value>>>0
  h=Math.imul(h^(h>>>16),0x7feb352d)>>>0
  h=Math.imul(h^(h>>>15),0x846ca68b)>>>0
  return(h^(h>>>16))>>>0
}
const hash01=(x,y,seed)=>mix32((Math.imul(x,374761393)+Math.imul(y,668265263)+seed)>>>0)/4294967296
const finite=(value,initial,lo,hi,integer=false)=>{
  const n=Number.isFinite(value)?value:initial
  const bounded=clamp(n,lo,hi)
  return integer?Math.round(bounded):bounded
}
const float32Below=value=>{
  const f=Math.fround(value)
  if(!Number.isFinite(f)||f<=0)return 0
  const view=new DataView(new ArrayBuffer(4));view.setFloat32(0,f)
  view.setUint32(0,view.getUint32(0)-1)
  return view.getFloat32(0)
}

export function surfaceOptions(params={}){
  const style=params.style==null?'roughen':params.style
  if(!STYLES.includes(style))throw new RangeError(`Surface Detail unknown style "${style}"`)
  const o={style,
    amountM:finite(params.amountM,10,0,500),wavelengthM:finite(params.wavelengthM,80,10,5000),
    octaves:finite(params.octaves,4,1,10,true),lacunarity:finite(params.lacunarity,2,1.25,4),
    gain:finite(params.gain,.5,.1,.9),seed:(finite(params.seed,7,0,4294967295,true)>>>0),
    slopeLowDeg:finite(params.slopeLowDeg,5,0,89),slopeHighDeg:finite(params.slopeHighDeg,35,1,89),
    curvatureStrength:finite(params.curvatureStrength,1,0,4),curvatureWidth:finite(params.curvatureWidth,.25,.001,1),
    wearStrength:finite(params.wearStrength,1,0,4),occlusionRadiusM:finite(params.occlusionRadiusM,300,1,5000),
    occlusionDirections:finite(params.occlusionDirections,8,4,32,true),cellSpacingM:finite(params.cellSpacingM,100,10,5000),
    bulbRadiusM:finite(params.bulbRadiusM,40,1,2500),pitRadiusM:finite(params.pitRadiusM,25,1,2500),
    edgeFeatherM:finite(params.edgeFeatherM,8,0,1000),intervalM:finite(params.intervalM,100,2,5000),
    spacingM:finite(params.spacingM,250,2,5000),lineWidthM:finite(params.lineWidthM,10,.25,1000),
    angleDeg:finite(params.angleDeg,0,0,360)}
  o.slopeHighDeg=Math.max(o.slopeHighDeg,Math.min(89,o.slopeLowDeg+1))
  const halfCell=o.cellSpacingM/2
  o.bulbRadiusM=Math.min(o.bulbRadiusM,halfCell)
  o.pitRadiusM=Math.min(o.pitRadiusM,halfCell)
  o.edgeFeatherM=Math.min(o.edgeFeatherM,Math.max(0,halfCell-o.pitRadiusM))
  const active=style==='contours'?o.intervalM:o.spacingM
  o.lineWidthM=Math.min(o.lineWidthM,float32Below(active/2))
  if(o.angleDeg===360)o.angleDeg=0
  return o
}

export function surfaceEffectiveSeed(options,nodeId=0,rootSeed=0){
  return mix32((options.seed+Math.imul(Number(nodeId)||0,0x9e3779b1)+hashText(options.style)+Number(rootSeed||0))>>>0)
}

export function surfaceFbmAt(worldX,worldY,wavelengthM,seed,options,cellM=0){
  let octaveCount=options.octaves
  if(cellM>0){
    octaveCount=0
    for(let k=0;k<options.octaves;k++){
      if(wavelengthM/Math.pow(options.lacunarity,k)<2*cellM)break
      octaveCount++
    }
    octaveCount=Math.max(1,octaveCount)
  }
  let sum=0,weight=1,total=0
  for(let k=0;k<octaveCount;k++){
    const frequency=Math.pow(options.lacunarity,k)/wavelengthM
    sum+=weight*gnoise(worldX*frequency,worldY*frequency,(seed+7*k)>>>0)
    total+=weight;weight*=options.gain
  }
  return{value:2*sum/total-1,octaves:octaveCount}
}

export function surfaceNearestSeedDistance(worldX,worldY,spacingM,seed){
  const px=worldX/spacingM,py=worldY/spacingM,cx=Math.floor(px),cy=Math.floor(py)
  let nearest=Infinity
  for(let oy=-1;oy<=1;oy++)for(let ox=-1;ox<=1;ox++){
    const gx=cx+ox,gy=cy+oy
    const fx=(gx+hash01(gx,gy,seed))*spacingM
    const fy=(gy+hash01(gx,gy,seed+91))*spacingM
    nearest=Math.min(nearest,Math.hypot(worldX-fx,worldY-fy))
  }
  return nearest
}

export function surfacePatternAt(worldX,worldY,heightM,options,seed,cellM=0){
  if(RANDOM_STYLES.has(options.style)&&options.style!=='bulbous'&&options.style!=='pockmarks'){
    const fbm=surfaceFbmAt(worldX,worldY,options.wavelengthM,seed,options,cellM)
    return{pattern:options.style==='rocknoise'?1-Math.abs(fbm.value):fbm.value,octaves:fbm.octaves}
  }
  if(options.style==='bulbous'){
    const distance=surfaceNearestSeedDistance(worldX,worldY,options.cellSpacingM,seed)
    return{pattern:1-smoothstep(0,options.bulbRadiusM,distance),octaves:0}
  }
  if(options.style==='pockmarks'){
    const distance=surfaceNearestSeedDistance(worldX,worldY,options.cellSpacingM,seed)
    return{pattern:-(1-smoothstep(options.pitRadiusM,options.pitRadiusM+options.edgeFeatherM,distance)),octaves:0}
  }
  if(options.style==='contours'){
    const d=Math.abs(((heightM+options.intervalM/2)%options.intervalM+options.intervalM)%options.intervalM-options.intervalM/2)
    return{pattern:1-smoothstep(options.lineWidthM/2,options.lineWidthM,d),octaves:0}
  }
  const angle=options.angleDeg*Math.PI/180,ca=Math.cos(angle),sa=Math.sin(angle)
  const px=worldX*ca-worldY*sa,py=worldX*sa+worldY*ca
  const dx=Math.abs(((px+options.spacingM/2)%options.spacingM+options.spacingM)%options.spacingM-options.spacingM/2)
  const dy=Math.abs(((py+options.spacingM/2)%options.spacingM+options.spacingM)%options.spacingM-options.spacingM/2)
  return{pattern:1-smoothstep(options.lineWidthM/2,options.lineWidthM,Math.min(dx,dy)),octaves:0}
}

export function surfaceDetailField(input,params={},mask=null,nodeId=0,rootSeed=0){
  const o=surfaceOptions(params)
  if(o.amountM===0)return input
  if(mask){let any=false;for(let i=0;i<mask.length;i++)if(mask[i]!==0){any=true;break}if(!any)return input}
  const n=fieldW(),nh=fieldH(),out=newField(),cellM=terrainDef.scale/n,hex=terrainDef.lattice==='hex'
  const seed=surfaceEffectiveSeed(o,nodeId,rootSeed)
  let slope=null,curvature=null,wear=null,occlusion=null
  if(['roughen','groundtexture','rocknoise'].includes(o.style))slope=slopeOf(input)
  if(['distress','rocknoise'].includes(o.style))curvature=curvatureField(input,{kind:'profile',strength:o.curvatureStrength})
  if(['groundtexture','bulbous'].includes(o.style))wear=wearField(input,{strength:o.wearStrength})
  if(o.style==='pockmarks')occlusion=occlusionField(input,{radius:o.occlusionRadiusM/terrainDef.scale,dirs:o.occlusionDirections})
  const low=Math.tan(o.slopeLowDeg*Math.PI/180),high=Math.tan(o.slopeHighDeg*Math.PI/180)
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const i=y*n+x,worldX=(x+.5+(hex?.5*(y&1):0))*cellM
    const worldY=(y+.5)*cellM*(hex?Math.sqrt(3)/2:1)
    const pattern=surfacePatternAt(worldX,worldY,input[i]*terrainDef.height,o,seed,cellM).pattern
    const slopeMask=slope?smoothstep(low,high,slope[i]*terrainDef.height/terrainDef.scale):0
    let driver=1
    if(o.style==='roughen')driver=slopeMask
    else if(o.style==='distress')driver=smoothstep(0,o.curvatureWidth,Math.max(0,.5-curvature[i])*2)
    else if(o.style==='groundtexture')driver=(1-slopeMask)*(1-wear[i])
    else if(o.style==='rocknoise')driver=slopeMask*smoothstep(0,o.curvatureWidth,Math.max(0,.5-curvature[i])*2)
    else if(o.style==='bulbous')driver=wear[i]
    else if(o.style==='pockmarks')driver=1-occlusion[i]
    out[i]=Math.fround((input[i]*terrainDef.height+o.amountM*driver*pattern)/terrainDef.height)
  }
  return maskApply(input,out,mask)
}

const def=definePlugin({
  type:'surface',cat:'surface',name:'Surface Detail',ins:['In','Mask'],
  desc:'Process-aware finish detail with six deterministic patterns and two non-physical relief overlays.',
  params:[
    P.select('style','Style',STYLES.map(style=>[style,({roughen:'Roughen',distress:'Distress',groundtexture:'Ground Texture',rocknoise:'Rock Noise',bulbous:'Bulbous',pockmarks:'Pockmarks',contours:'Contours',grid:'Grid'})[style]]),'roughen'),
    P.slider('amountM','Amount',0,500,10,1,metre),
    WHEN(P.slider('wavelengthM','Wavelength',10,5000,80,1,metre),'style',['roughen','distress','groundtexture','rocknoise']),
    WHEN(P.int('octaves','Octaves',1,10,4),'style',['roughen','distress','groundtexture','rocknoise']),
    WHEN(P.slider('lacunarity','Lacunarity',1.25,4,2,.05),'style',['roughen','distress','groundtexture','rocknoise']),
    WHEN(P.slider('gain','Gain',.1,.9,.5,.01),'style',['roughen','distress','groundtexture','rocknoise']),
    P.seed('seed','Seed',7),
    WHEN(P.slider('slopeLowDeg','Slope low',0,89,5,1,deg),'style',['roughen','groundtexture','rocknoise']),
    WHEN(P.slider('slopeHighDeg','Slope high',1,89,35,1,deg),'style',['roughen','groundtexture','rocknoise']),
    WHEN(P.slider('curvatureStrength','Curvature strength',0,4,1,.05),'style',['distress','rocknoise']),
    WHEN(P.slider('curvatureWidth','Curvature width',.001,1,.25,.001),'style',['distress','rocknoise']),
    WHEN(P.slider('wearStrength','Wear strength',0,4,1,.05),'style',['groundtexture','bulbous']),
    WHEN(P.slider('occlusionRadiusM','Occlusion radius',1,5000,300,1,metre),'style','pockmarks'),
    WHEN(P.int('occlusionDirections','Occlusion directions',4,32,8),'style','pockmarks'),
    WHEN(P.slider('cellSpacingM','Cell spacing',10,5000,100,1,metre),'style',['bulbous','pockmarks']),
    WHEN(P.slider('bulbRadiusM','Bulb radius',1,2500,40,1,metre),'style','bulbous'),
    WHEN(P.slider('pitRadiusM','Pit radius',1,2500,25,1,metre),'style','pockmarks'),
    WHEN(P.slider('edgeFeatherM','Edge feather',0,1000,8,1,metre),'style','pockmarks'),
    WHEN(P.slider('intervalM','Contour interval',2,5000,100,1,metre),'style','contours'),
    WHEN(P.slider('spacingM','Grid spacing',2,5000,250,1,metre),'style','grid'),
    WHEN(P.slider('lineWidthM','Line width',.25,1000,10,.25,metre),'style',['contours','grid']),
    WHEN(P.slider('angleDeg','Angle',0,360,0,1,deg),'style','grid')],
  eval:(p,ins,nd)=>ins[0]?surfaceDetailField(ins[0],p,ins[1],nd?.id,terrainDef.seed):newField(),
  note:'Roughen, Distress, Ground Texture, Rock Noise, Bulbous, and Pockmarks are authored Terrain Studio compositions. Contours and Grid are explicitly non-physical relief overlays. This node makes no claim about unpublished branded algorithms.'
})
def.options=surfaceOptions
def.effectiveSeed=surfaceEffectiveSeed
def.fbmAt=surfaceFbmAt
def.nearestSeedDistance=surfaceNearestSeedDistance
def.patternAt=surfacePatternAt
def.field=surfaceDetailField

export default def