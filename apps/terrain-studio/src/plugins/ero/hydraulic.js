// hydraulic — independently switchable pipe and droplet erosion stages.
//
// On a square lattice both stages are GPU kernels. If both switches are enabled they execute in
// the fixed physical order Pipe -> Droplet and remain texture-resident until one final readback.
// WebGL2 float blending is the capability required by the particle brush accumulator; unsupported
// contexts and the hex lattice retain the CPU droplet compatibility path.
import { definePlugin } from '../../core/registry.js'
import { gpuHydraulicPipes, gpuHydraulicDroplets, gpuHydraulicCombined,
  gpuReady, gpuDropletsReady } from '../../core/gpu.js'
import { P, SECTION } from '../../core/params.js'
import { BUILD_QUALITY, RES, atFeatureScale, hydraulicErode, maskApply, newField, resScale } from '../../legacy.js'

const S=(param,section)=>SECTION(param,section)
const pipeParams=p=>({
  iters:p.pipeIters==null?48:p.pipeIters,
  capacity:p.pipeCapacity==null?(p.capacity==null?6:p.capacity):p.pipeCapacity,
  erode:p.pipeErode==null?(p.erode==null ? .35 : p.erode):p.pipeErode,
  deposit:p.pipeDeposit==null?(p.deposit==null ? .28 : p.deposit):p.pipeDeposit,
  inertia:p.pipeInertia==null?(p.inertia==null ? .05 : p.inertia):p.pipeInertia
})
const dropletParams=p=>({
  droplets:p.droplets==null?18000:p.droplets,
  lifetime:p.lifetime==null?48:p.lifetime,
  capacity:p.dropletCapacity==null?(p.capacity==null?6:p.capacity):p.dropletCapacity,
  erode:p.dropletErode==null?(p.erode==null ? .35 : p.erode):p.dropletErode,
  deposit:p.dropletDeposit==null?(p.deposit==null ? .28 : p.deposit):p.dropletDeposit,
  inertia:p.dropletInertia==null?(p.inertia==null ? .05 : p.inertia):p.dropletInertia,
  evap:p.evap==null ? .02 : p.evap,gravity:p.gravity==null?4:p.gravity,
  radius:p.radius==null?2:p.radius,seed:p.seed==null?1:p.seed,minSlope:.01
})
const enabledStages=p=>{
  // The hidden engine field is a migration bridge for saved graphs and legacy verification calls.
  // New documents store null here and use the two booleans. Old "auto" means Pipe only; old
  // "droplets" means Droplet only.
  if(p.engine==="droplets")return{pipes:false,droplets:true}
  if(p.engine==="auto")return{pipes:true,droplets:false}
  if(p.pipeEnabled==null&&p.dropletEnabled==null)
    return{pipes:true,droplets:false}
  return{pipes:p.pipeEnabled!==false,droplets:!!p.dropletEnabled}
}

export default definePlugin({
  type:"hydraulic",cat:"ero",name:"Hydraulic erosion",ins:["In","Mask"],
  desc:"Combine GPU pipe flow and GPU droplet erosion in one terrain pass.",
  paramSections:[
    {id:"pipe",label:"Pipe / grid erosion",toggle:"pipeEnabled",defaultOpen:true,device:"gpu"},
    {id:"droplet",label:"Droplet / particle erosion",toggle:"dropletEnabled",defaultOpen:false,device:"gpu-droplets"}
  ],
  params:[
    // Saved-graph bridge. Hidden schema data remains serialised until every existing document has
    // passed through migrateParams; it is not a third user-facing mode.
    P.hidden("engine",null),
    P.toggle("pipeEnabled","Pipe / grid erosion",true),
    S(P.int("pipeIters","Iterations",8,360,48),"pipe"),
    S(P.slider("pipeErode","Erode",0.05,0.8,0.35),"pipe"),
    S(P.slider("pipeDeposit","Deposit",0.05,0.8,0.28),"pipe"),
    S(P.slider("pipeCapacity","Capacity",1,12,6,0.5),"pipe"),
    S(P.slider("pipeInertia","Flow memory",0,0.5,0.05),"pipe"),
    P.toggle("dropletEnabled","Droplet / particle erosion",false),
    S(P.int("droplets","Particles",1000,60000,18000),"droplet"),
    S(P.int("lifetime","Lifetime",8,128,48),"droplet"),
    S(P.slider("dropletErode","Erode",0.05,0.8,0.35),"droplet"),
    S(P.slider("dropletDeposit","Deposit",0.05,0.8,0.28),"droplet"),
    S(P.slider("dropletCapacity","Capacity",1,12,6,0.5),"droplet"),
    S(P.slider("dropletInertia","Inertia",0,0.5,0.05),"droplet"),
    S(P.slider("evap","Evaporation",0.005,0.08,0.02,0.005),"droplet"),
    S(P.slider("gravity","Gravity",1,12,4,0.5),"droplet"),
    S(P.slider("radius","Brush radius",1,5,2,1,v=>(v|0)+" px"),"droplet"),
    S(P.seed("seed","Seed",1),"droplet"),
    P.log("feat","Feature scale",1,8,1,v=>v.toFixed(1)+"\u00d7",false)
  ],
  migrateParams:p=>{
    if(p.pipeEnabled==null&&p.dropletEnabled==null){
      p.pipeEnabled=p.engine!=="droplets";p.dropletEnabled=p.engine==="droplets"
    }
    const copy=(next,old,fallback)=>{if(p[next]==null)p[next]=p[old]==null?fallback:p[old]}
    copy("pipeErode","erode",.35);copy("pipeDeposit","deposit",.28)
    copy("pipeCapacity","capacity",6);copy("pipeInertia","inertia",.05)
    copy("dropletErode","erode",.35);copy("dropletDeposit","deposit",.28)
    copy("dropletCapacity","capacity",6);copy("dropletInertia","inertia",.05)
    if(p.lifetime==null)p.lifetime=48;if(p.evap==null)p.evap=.02;if(p.gravity==null)p.gravity=4
    p.engine=null
  },
  eval:(p,ins)=>{
    if(!ins[0])return newField()
    const stages=enabledStages(p);if(!stages.pipes&&!stages.droplets)return ins[0].slice()
    const k=resScale(),tier=BUILD_QUALITY==="final"?1:Math.max(1,RES/384),ke=k/tier
    const pp={...pipeParams(p),gridK:ke},dp0=dropletParams(p)
    const dp={...dp0,droplets:Math.round(dp0.droplets*ke*ke),
      radius:Math.max(1,Math.round(dp0.radius*ke)),gridK:ke}
    const run=f=>{
      if(stages.pipes&&stages.droplets&&gpuDropletsReady())
        return gpuHydraulicCombined(f,{pipes:pp,droplets:dp})
      let out=f
      if(stages.pipes){
        // Existing compatibility behavior: without the square-grid GPU pipe kernel, use the
        // reference droplet path with the pipe panel's transport controls.
        out=gpuReady()?gpuHydraulicPipes(out,pp):hydraulicErode(out,{
          ...pp,droplets:dp.droplets,radius:dp.radius,seed:dp.seed,settle:true,gridK:ke})
      }
      if(stages.droplets)out=gpuDropletsReady()?gpuHydraulicDroplets(out,dp)
        :hydraulicErode(out,{...dp,settle:false})
      return out
    }
    return maskApply(ins[0],atFeatureScale(ins[0],p.feat*tier,run),ins[1])
  },
  note:"Enable either hydraulic model or both. <b>Pipe / grid</b> moves standing water and suspended sediment across the field, producing broad connected drainage. <b>Droplet / particle</b> follows many individual downhill paths, adding finer stochastic gullies. When both are enabled the order is fixed: <b>Pipe → Droplet</b>. <b>Lifetime</b> is a work limit: remaining suspended load is reported at truncation, never force-deposited into a terminal cone. <b>Particles</b> increases path coverage; at high density the action budget saturates, so use Erode and Deposit for effect strength. On square terrain both stages stay in GPU textures and read back once; WebGL2 float-blend capability or a hexagonal lattice uses the labelled CPU compatibility fallback."
})
