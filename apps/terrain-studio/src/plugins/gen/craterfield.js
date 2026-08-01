import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { terrainDef } from '../../legacy.js'
import { bounded, craterProfileM, effectiveSeed, randomStream, rasterFromWorld } from './crater.js'

export function poissonPlacement(requested,minSpacingM,seed,extentM=terrainDef.scale){
  const wanted=Math.max(1,Math.round(requested)),spacing=Math.max(1,minSpacingM)
  const cell=spacing/Math.SQRT2,cols=Math.ceil(extentM/cell),rows=Math.ceil(extentM/cell)
  const grid=new Int32Array(cols*rows);grid.fill(-1)
  const points=[],active=[],random=randomStream(seed)
  const add=(x,y)=>{const point={x,y};points.push(point);active.push(points.length-1)
    grid[Math.floor(y/cell)*cols+Math.floor(x/cell)]=points.length-1}
  add(random()*extentM,random()*extentM)
  while(active.length&&points.length<wanted){
    const activeSlot=Math.floor(random()*active.length),origin=points[active[activeSlot]]
    let accepted=false
    for(let attempt=0;attempt<30;attempt++){
      const radius=spacing*Math.sqrt(1+3*random()),angle=2*Math.PI*random()
      const x=origin.x+radius*Math.cos(angle),y=origin.y+radius*Math.sin(angle)
      if(x<0||y<0||x>=extentM||y>=extentM)continue
      const gx=Math.floor(x/cell),gy=Math.floor(y/cell);let valid=true
      for(let oy=-2;oy<=2&&valid;oy++)for(let ox=-2;ox<=2;ox++){
        const cx=gx+ox,cy=gy+oy;if(cx<0||cy<0||cx>=cols||cy>=rows)continue
        const index=grid[cy*cols+cx];if(index<0)continue
        const point=points[index]
        if(Math.hypot(x-point.x,y-point.y)<spacing){valid=false;break}
      }
      if(valid){add(x,y);accepted=true;break}
    }
    if(!accepted){active[activeSlot]=active[active.length-1];active.pop()}
  }
  return{requested:wanted,placed:points.length,saturated:points.length<wanted,minSpacingM:spacing,points}
}

export function craterFieldOptions(params={}){
  return{count:bounded(params.count,24,1,512,true),minSpacingM:bounded(params.minSpacingM,400,10,5000),
    diameterM:bounded(params.diameterM,240,10,3000),diameterVariation:bounded(params.diameterVariation,.35,0,1),
    gravity:bounded(params.gravity,9.81,.1,30),depositFraction:bounded(params.depositFraction,.9,0,1),
    amount:bounded(params.amount,1,0,2),seed:bounded(params.seed,7,0,4294967295,true)>>>0}
}

export function craterFieldPlan(params={},nodeId=0,rootSeed=0){
  const o=craterFieldOptions(params),seed=effectiveSeed('craterfield',o.seed,nodeId,rootSeed)
  return poissonPlacement(o.count,o.minSpacingM,seed)
}

export function craterField(params={},nodeId=0,rootSeed=0){
  const o=craterFieldOptions(params),seed=effectiveSeed('craterfield',o.seed,nodeId,rootSeed)
  const plan=poissonPlacement(o.count,o.minSpacingM,seed),variation=randomStream(seed+1907)
  const craters=plan.points.map(point=>({x:point.x,y:point.y,
    diameterM:bounded(o.diameterM*(1+o.diameterVariation*(2*variation()-1)),o.diameterM,10,3000)}))
  return rasterFromWorld((worldX,worldY)=>{
    let metres=0
    for(const crater of craters)metres+=craterProfileM(Math.hypot(worldX-crater.x,worldY-crater.y),{
      diameterM:crater.diameterM,gravity:o.gravity,depositFraction:o.depositFraction,amount:o.amount})
    return metres/terrainDef.height
  })
}

const metre=value=>Math.round(value)+' m'
const def=definePlugin({type:'craterfield',cat:'gen',name:'Crater Field',ins:[],
  desc:'Deterministic Poisson-disc placement of reduced vertical crater profiles.',
  params:[P.int('count','Crater count',1,512,24),P.slider('minSpacingM','Minimum spacing',10,5000,400,10,metre),
    P.slider('diameterM','Diameter',10,3000,240,10,metre),P.slider('diameterVariation','Diameter variation',0,1,.35,.01),
    P.slider('gravity','Gravity',.1,30,9.81,.01,value=>value.toFixed(2)+' m/s\u00b2'),
    P.slider('depositFraction','Deposit fraction',0,1,.9,.01),P.slider('amount','Amount',0,2,1,.01),P.seed('seed','Seed',7)],
  eval:(p,ins,node)=>craterField(p,node?.id,terrainDef.seed),
  note:'Placement defaults are authored for the five-kilometre fixture, not an impact-population model. Saturation is explicit; requested craters are never silently fabricated.'})
def.options=craterFieldOptions
def.planPlacement=craterFieldPlan
def.field=craterField
export default def