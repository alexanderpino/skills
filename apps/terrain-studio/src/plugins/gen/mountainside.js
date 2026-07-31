import { definePlugin } from '../../core/registry.js'
import { mountainSkirtDefault } from '../../core/defaults.js'
import { P, WHEN } from '../../core/params.js'
import { clamp, fieldH, fieldW, mountainField, newField, terrainDef, worldSampleAt } from '../../legacy.js'
import { bounded, effectiveSeed, enumValue } from './crater.js'

const smoothstep=(a,b,value)=>{const t=clamp((value-a)/(b-a),0,1);return t*t*(3-2*t)}
const validCurve=curve=>Array.isArray(curve)&&curve.length>=2&&curve.every((point,index)=>Array.isArray(point)&&point.length===2
  &&Number.isFinite(point[0])&&Number.isFinite(point[1])&&(index===0||point[0]>=curve[index-1][0]))
export function mountainSideOptions(params={}){
  if(params.skirt!=null&&!validCurve(params.skirt))throw new RangeError('MountainSide skirt must be a finite, monotone curve')
  const skirt=params.skirt==null?mountainSkirtDefault():params.skirt
  return{bearingDeg:bounded(params.bearingDeg,90,0,360),featherM:bounded(params.featherM,300,1,5000),
    form:enumValue(params.form,'peak',['peak','massif'],'MountainSide form'),shape:enumValue(params.shape,'compound',['dominant','compound','ridge','broad'],'MountainSide shape'),
    style:enumValue(params.style,'eroded',['basic','eroded','old','alpine','strata'],'MountainSide style'),seed:bounded(params.seed,7,0,4294967295,true)>>>0,
    x:bounded(params.x,.5,0,1),y:bounded(params.y,.5,0,1),size:bounded(params.size,.4,.08,.9),height:bounded(params.height,.72,.1,2),
    bulk:enumValue(params.bulk,'medium',['low','medium','high'],'MountainSide bulk'),angle:bounded(params.angle,25,0,180),ridges:bounded(params.ridges,2,1,5,true),
    detail:bounded(params.detail,2.6,.4,3.5),aspect:bounded(params.aspect,1,.4,2.5),relief:bounded(params.relief,.8,.1,.95),
    character:bounded(params.character,.72,0,.9),variation:bounded(params.variation,.55,0,1),reduce:bounded(params.reduce,.08,0,1),
    weather:bounded(params.weather,1,0,2),skirt}
}
export function mountainSideField(params={},nodeId=0,rootSeed=0){
  const o=mountainSideOptions(params);o.seed=effectiveSeed('mountainside',o.seed,nodeId,rootSeed)
  const mountain=mountainField(o),n=fieldW(),nh=fieldH(),out=newField()
  const angle=o.bearingDeg*Math.PI/180,ux=Math.cos(angle),uy=Math.sin(angle),cx=o.x*terrainDef.scale,cy=o.y*terrainDef.scale
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const point=worldSampleAt(x,y),t=(point[0]-cx)*ux+(point[1]-cy)*uy
    out[y*n+x]=Math.fround(mountain[y*n+x]*smoothstep(-o.featherM,o.featherM,t))
  }
  return out
}
const metre=value=>Math.round(value)+' m',degree=value=>Math.round(value)+'\u00b0'
const def=definePlugin({type:'mountainside',cat:'gen',name:'Mountain Side',ins:[],desc:'The existing Mountain evaluator retained on one authored side of a world-space bearing.',
  params:[P.slider('bearingDeg','Facing bearing',0,360,90,1,degree),P.slider('featherM','Half-plane feather',1,5000,300,1,metre),
    P.tabs('form','Landform',[['peak','Mountain'],['massif','Mountain range']],'peak'),WHEN(P.seg('shape','Shape family',[['dominant','Dominant peak'],['compound','Compound peaks'],['ridge','Ridgeline'],['broad','Broad dome']],'compound'),'form','peak'),
    P.seg('style','Mountain type',[['basic','Basic'],['eroded','Eroded'],['old','Old'],['alpine','Alpine'],['strata','Strata']],'eroded'),P.seed('seed','Seed',7),
    P.slider('x','Position X',0,1,.5,.01,value=>metre(value*terrainDef.scale)),P.slider('y','Position Y',0,1,.5,.01,value=>metre(value*terrainDef.scale)),
    P.slider('size','Reach',.08,.9,.4,.01),P.slider('height','Peak height',.1,2,.72,.01),P.seg('bulk','Bulk',[['low','Low'],['medium','Medium'],['high','High']],'medium'),
    P.slider('angle','Trend',0,180,25,1,degree),WHEN(P.int('ridges','Massif crests',1,5,2),'form','massif'),P.slider('detail','Drainage detail',.4,3.5,2.6,.1),
    P.slider('aspect','Footprint aspect',.4,2.5,1,.05),P.slider('relief','Valley depth',.1,.95,.8,.01),P.slider('character','Character',0,.9,.72,.01),
    P.slider('variation','Shape variation',0,1,.55,.01),P.slider('reduce','Reduce details',0,1,.08,.01),P.slider('weather','Weathering',0,2,1,.05),
    P.curve('skirt','Skirt profile',mountainSkirtDefault())],eval:(p,ins,node)=>mountainSideField(p,node?.id,terrainDef.seed),
  note:'An authored directional mask over Terrain Studio Mountain. It does not rename, duplicate, or claim unpublished Mountain internals.'})
def.options=mountainSideOptions;def.field=mountainSideField
export default def