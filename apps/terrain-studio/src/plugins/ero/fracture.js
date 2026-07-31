// fracture — Multi-scale rock joints cut into an existing height field.
//
// This is deliberately separate from Thermal. The fracture network is a procedural material
// weakness/look (warped Worley F2-F1); the optional shoulder pass recesses exposed joint edges.
// Thermal remains the later mass-wasting pass that moves loose material to the repose angle.
import { definePlugin } from '../../core/registry.js'
import { gpuReady, gpuRockFracture } from '../../core/gpu.js'
import { P, SECTION } from '../../core/params.js'
import { fieldH, fieldW, gnoise, maskApply, newField, terrainDef } from '../../legacy.js'

const S=(param,section)=>SECTION(param,section)
const metre=v=>v<10?v.toFixed(1)+" m":Math.round(v)+" m"

const hash01=(x,y,seed)=>{
  let h=(Math.imul(x,374761393)+Math.imul(y,668265263)+Math.imul(seed,1442695041))|0
  h=Math.imul(h^(h>>>13),1274126177)
  return((h^(h>>>16))>>>0)/4294967295
}
const smooth01=t=>t<=0?0:t>=1?1:t*t*(3-2*t)
const lineCoverage=(edge,widthM,cellM,spacing)=>{
  // F2-F1 changes at approximately 2 * perpendicular_distance / spacing. `widthM` is the
  // complete authored line width (not a radius). Centre the transition on that threshold so
  // one pixel of anti-aliasing does not silently add a pixel to both sides of every joint.
  const threshold=widthM/spacing,aa=Math.max(1e-5,cellM/spacing)
  return 1-smooth01((edge-(threshold-aa))/(2*aa))
}
const finiteNumber=(value,lo,hi,label)=>{
  if(!Number.isFinite(value)||value<lo||value>hi)
    throw new RangeError(`Rock Fracture ${label} must be finite and in [${lo}, ${hi}]`)
  return value
}
const finiteField=(field,label,mask=false)=>{
  if(!ArrayBuffer.isView(field))throw new TypeError(`Rock Fracture ${label} must be a typed field`)
  for(let i=0;i<field.length;i++){
    const value=field[i]
    if(!Number.isFinite(value))
      throw new RangeError(`Rock Fracture ${label} contains a non-finite value at sample ${i}`)
    if(mask&&(value<0||value>1))
      throw new RangeError(`Rock Fracture mask contains ${value} outside [0, 1] at sample ${i}`)
  }
  return field
}
const options=p=>{
  const o={
    patternEnabled:p.patternEnabled!==false,
    weatherEnabled:p.weatherEnabled!==false,
    scaleM:p.scaleM == null ? 600 : p.scaleM,
    octaves:p.octaves == null ? 3 : Math.round(p.octaves),
    lacunarity:p.lacunarity == null ? 2 : p.lacunarity,
    jitter:p.jitter == null ? .88 : p.jitter,
    warp:p.warp == null ? .28 : p.warp,
    warpScaleM:p.warpScaleM == null ? 900 : p.warpScaleM,
    widthM:p.widthM == null ? 12 : p.widthM,
    depthM:p.depthM == null ? 18 : p.depthM,
    depthFalloff:p.depthFalloff == null ? .58 : p.depthFalloff,
    breakdownM:p.breakdownM == null ? 32 : p.breakdownM,
    breakdown:p.breakdown == null ? .55 : p.breakdown,
    roughness:p.roughness == null ? .35 : p.roughness,
    seed:p.seed == null ? 11 : Math.round(p.seed)
  }
  finiteNumber(o.scaleM,.001,1e9,"largest spacing")
  finiteNumber(o.octaves,1,5,"scale count")
  finiteNumber(o.lacunarity,1.01,8,"scale ratio")
  finiteNumber(o.jitter,0,1,"cell jitter")
  finiteNumber(o.warp,0,1,"warp strength")
  finiteNumber(o.warpScaleM,.001,1e9,"warp scale")
  finiteNumber(o.widthM,0,1e9,"crack width")
  finiteNumber(o.depthM,0,1e9,"cut depth")
  finiteNumber(o.depthFalloff,0,1,"depth falloff")
  finiteNumber(o.breakdownM,0,1e9,"shoulder width")
  finiteNumber(o.breakdown,0,1,"breakdown strength")
  finiteNumber(o.roughness,0,1,"edge roughness")
  finiteNumber(o.seed,-2147483648,2147483647,"seed")
  finiteNumber(terrainDef.scale,Number.MIN_VALUE,Number.MAX_VALUE,"terrain scale")
  finiteNumber(terrainDef.height,Number.MIN_VALUE,Number.MAX_VALUE,"terrain relief height")
  return o
}

function fractureMasks(worldX,worldY,cellM,o){
  let core=0,weathered=0,spacing=o.scaleM,amp=1
  for(let octave=0;octave<o.octaves;octave++){
    const octaveSeed=(o.seed+Math.imul(octave,1013))|0
    const warpU=worldX/o.warpScaleM,warpV=worldY/o.warpScaleM
    const dx=(gnoise(warpU,warpV,octaveSeed+37)-.5)*2*o.warp*spacing
    const dy=(gnoise(warpU,warpV,octaveSeed+109)-.5)*2*o.warp*spacing
    const px=(worldX+dx)/spacing,py=(worldY+dy)/spacing
    const cx=Math.floor(px),cy=Math.floor(py)
    let f1=1e9,f2=1e9
    for(let oy=-1;oy<=1;oy++)for(let ox=-1;ox<=1;ox++){
      const gx=cx+ox,gy=cy+oy
      const fx=gx+(.5+(hash01(gx,gy,octaveSeed)-.5)*o.jitter)
      const fy=gy+(.5+(hash01(gx,gy,octaveSeed+91)-.5)*o.jitter)
      const d=Math.hypot(px-fx,py-fy)
      if(d<f1){f2=f1;f1=d}else if(d<f2)f2=d
    }
    const edge=Math.max(0,f2-f1)
    // Fine joint sets are shallower AND narrower. Keeping the largest crack/shoulder width at
    // every octave turns a multiscale network into an almost uniform lowering operation.
    const crackWidth=o.widthM*amp
    const weatherWidth=crackWidth+2*o.breakdownM*amp
    const crack=lineCoverage(edge,crackWidth,cellM,spacing)
    const broken=lineCoverage(edge,weatherWidth,cellM,spacing)
    core=1-(1-core)*(1-crack*amp)
    weathered=1-(1-weathered)*(1-broken*amp)
    spacing/=o.lacunarity
    amp*=o.depthFalloff
  }
  return{core,shoulder:Math.max(0,weathered-core)}
}

export function rockFractureField(input,params={}){
  finiteField(input,"input")
  const o=options(params)
  if(!o.patternEnabled)return input.slice()
  const n=fieldW(),nh=fieldH(),out=newField(),cellM=terrainDef.scale/n
  const hex=terrainDef.lattice==="hex",rowM=cellM*Math.sqrt(3)*.5
  const depth=o.depthM/terrainDef.height
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const worldX=(x+.5+(hex?.5*(y&1):0))*cellM
    const worldY=(y+.5)*(hex?rowM:cellM)
    const masks=fractureMasks(worldX,worldY,cellM,o)
    const shoulder=o.weatherEnabled?masks.shoulder*o.breakdown:0
    const noise=gnoise(worldX/Math.max(1,o.scaleM*.37),
      worldY/Math.max(1,o.scaleM*.37),o.seed+2081)
    const variation=1+o.roughness*(noise*1.4-.7)
    out[y*n+x]=input[y*n+x]-depth*(masks.core+shoulder)*variation
  }
  return finiteField(out,"output")
}

export default definePlugin({
  type:"fracture",cat:"ero",name:"Rock Fracture",ins:["In","Mask"],
  desc:"Warped multi-scale Voronoi joints with optional edge breakdown.",
  paramSections:[
    {id:"network",label:"Fracture network",toggle:"patternEnabled",defaultOpen:true,device:"gpu"},
    {id:"weather",label:"Edge weathering",toggle:"weatherEnabled",defaultOpen:true,device:"gpu"}
  ],
  params:[
    P.toggle("patternEnabled","Fracture network",true),
    S(P.log("scaleM","Largest spacing",40,4000,600,metre,false),"network"),
    S(P.int("octaves","Scale count",1,5,3),"network"),
    S(P.slider("lacunarity","Scale ratio",1.5,3,2,.05,v=>v.toFixed(2)+"×"),"network"),
    S(P.slider("jitter","Cell jitter",0,1,.88,.01),"network"),
    S(P.slider("warp","Warp strength",0,.75,.28,.01),"network"),
    S(P.log("warpScaleM","Warp scale",30,8000,900,metre,false),"network"),
    S(P.log("widthM","Crack width",.5,200,12,metre,false),"network"),
    S(P.log("depthM","Cut depth",.25,300,18,metre,false),"network"),
    S(P.slider("depthFalloff","Fine-scale depth",.15,1,.58,.01),"network"),
    S(P.seed("seed","Seed",11),"network"),
    P.toggle("weatherEnabled","Edge weathering",true),
    S(P.log("breakdownM","Shoulder width",.25,400,32,metre,true),"weather"),
    S(P.slider("breakdown","Breakdown",0,1,.55,.01),"weather"),
    S(P.slider("roughness","Edge roughness",0,1,.35,.01),"weather")
  ],
  eval:(p,ins)=>{
    if(!ins[0])return newField()
    finiteField(ins[0],"input")
    if(ins[1])finiteField(ins[1],"mask",true)
    const o=options(p)
    if(!o.patternEnabled)return ins[0].slice()
    const modified=gpuReady()?gpuRockFracture(ins[0],o):rockFractureField(ins[0],o)
    return finiteField(maskApply(ins[0],modified,ins[1]),"output")
  },
  note:"<b>Rock Fracture</b> cuts a deterministic, multi-scale Worley/Voronoi joint network into "
    +"the current terrain. Spacing, width, depth, warp scale, and weathering shoulder are world "
    +"metres, so the structure survives resolution changes. <b>Edge weathering</b> recesses the "
    +"rock beside each joint; it does not move talus or claim mass conservation. Add <b>Thermal "
    +"erosion after this node</b> when the loosened material should settle downslope. The operation "
    +"continues procedurally through the terrain boundary and never samples a clamped neighbour, "
    +"so it does not create an edge frame. A heightfield can show joint grooves and breakup but "
    +"cannot create separated 3D blocks, undercuts, or open fissure voids."
})
