// hydraulic — independently switchable pipe and droplet erosion stages.
//
// On a square lattice both stages are GPU kernels. If both switches are enabled they execute in
// the fixed physical order Pipe -> Droplet and remain texture-resident until one final readback.
// WebGL2 float blending is the capability required by the particle brush accumulator; unsupported
// contexts and the hex lattice retain the CPU droplet compatibility path.
import { definePlugin } from '../../core/registry.js'
import { gpuHydraulicPipes, gpuHydraulicDroplets, gpuHydraulicCombined,
  gpuReady, gpuDropletsReady, hydroMassDiag, setHydroMassDiag } from '../../core/gpu.js'
import { P, SECTION } from '../../core/params.js'
import { BUILD_QUALITY, RES, atFeatureScale, hydraulicErode, maskApply, newField, resScale,
  cellSizeM, fieldW, fieldH, terrainDef, isHex, HEX_ROW } from '../../legacy.js'

// The adapter's frozen primary for this type (src/core/legacy-ports.js:303). ADR-002: "Display
// names and array positions are never identifiers" - a saved document's edges store this id, so it
// is a constant here rather than something recomputed from a descriptor list.
const PRIMARY_PORT = "out"

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
  // S3.1 — the transport STATE the solvers were already computing and discarding, published as
  // ports. `extraOutputs` appends to the adapter's frozen row (src/core/registry.js): the primary
  // and the two input descriptors stay exactly what a v1 document's edges resolve against, and the
  // new rows are validated on the same path as any self-declared block.
  extraOutputs:[
    // Deposited cover, in metres. Semantic `sediment` - a TRANSPORT quantity, "how much this pass
    // put down" - and deliberately NOT `sedimentDepth`, which ports.js defines as a persistent
    // LAYER THICKNESS that survives between passes and is S3.3/S3.4's cover state. A hydraulic
    // pass reports what it deposited; it does not own the standing layer.
    {id:"sediment",name:"Sediment",kind:"scalarRaster",storage:"R32F",components:1,
      semantic:"sediment",unit:"m",lens:"state"},
    // Pipe cell velocity, xy interleaved, metres per second. A port list is static, so this is
    // declared once - but a VALUE is produced only where the pipe kernel actually ran. The hex
    // compatibility path has no pipe solver at all (the Pipe stage below routes into the droplet
    // kernel), and a droplet path has no per-cell velocity field: publishing one there would be
    // exactly the "raw per-particle terminal speed labelled as a cell field" sprint-03 forbids.
    {id:"velocity",name:"Flow velocity",kind:"vectorRaster",storage:"RG32F",components:2,
      semantic:"velocity",unit:"mPerS",lens:"state"},
  ],
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
  eval:(p,ins,node,ctx)=>{
    if(!ins[0])return newField()
    const stages=enabledStages(p);if(!stages.pipes&&!stages.droplets)return ins[0].slice()
    // DEMAND, and why the rule is not normals.js's. normals treats an ABSENT ctx as "compute
    // everything", which is right for a node whose vector port shipped WITH its digest baseline.
    // Hydraulic is an existing node: _verify_digest.js:200-213 calls def.eval(params, ins, nd)
    // with no ctx and folds every declared output of a TYPED return into that type's digest
    // string, so "no ctx means compute" would move a baseline this story must not move. No demand
    // therefore means no state, and the return stays the bare Float32Array it has always been -
    // which is also the only shape under which an undemanded output genuinely costs nothing.
    const demanded=ctx&&ctx.demanded
    const wantSed=!!(demanded&&demanded.has("sediment")),wantVel=!!(demanded&&demanded.has("velocity"))
    const wantState=wantSed||wantVel
    const k=resScale(),tier=BUILD_QUALITY==="final"?1:Math.max(1,RES/384),ke=k/tier
    const pp={...pipeParams(p),gridK:ke},dp0=dropletParams(p)
    const dp={...dp0,droplets:Math.round(dp0.droplets*ke*ke),
      radius:Math.max(1,Math.round(dp0.radius*ke)),gridK:ke}
    let kernelRuns=0,pipeState=null
    const run=f=>{
      if(stages.pipes&&stages.droplets&&gpuDropletsReady()){
        kernelRuns++
        return gpuHydraulicCombined(f,{pipes:pp,droplets:dp})
      }
      let out=f
      if(stages.pipes){
        kernelRuns++
        if(gpuReady()){
          // The kernel hands back its own BED channel only when the pipe stage is the last thing
          // that touches the field. With a droplet stage after it, the bed the pipes reported no
          // longer exists, so the node falls back to the net aggradation of what it publishes.
          const sink=wantState&&!stages.droplets?{}:null
          out=gpuHydraulicPipes(out,pp,sink)
          if(sink)pipeState=sink
        }else{
          // Existing compatibility behavior: without the square-grid GPU pipe kernel, use the
          // reference droplet path with the pipe panel's transport controls.
          out=hydraulicErode(out,{
            ...pp,droplets:dp.droplets,radius:dp.radius,seed:dp.seed,settle:true,gridK:ke})
        }
      }
      if(stages.droplets){
        kernelRuns++
        out=gpuDropletsReady()?gpuHydraulicDroplets(out,dp):hydraulicErode(out,{...dp,settle:false})
      }
      return out
    }
    const result=maskApply(ins[0],atFeatureScale(ins[0],p.feat*tier,run),ins[1])

    // ---- STATE + the mass ledger in physical volume ------------------------------------------
    // `transformed` means the published field is no longer the kernel's own output: a feature-scale
    // coarsening runs the sim on a smaller grid and adds back an upsampled delta, a mask blends the
    // result toward the input, and two kernels in series leave a last-run-wins ledger describing
    // only the second. In every one of those cases the kernel's boundary budget stops describing
    // the field it claims to describe, and a budget that no longer matches its field is worse than
    // no budget - so the node recomputes the field-side terms and declines to claim a closure.
    const transformed=(p.feat*tier>1.02)||!!ins[1]||kernelRuns!==1
    const W=fieldW(),H=fieldH(),N=W*H,hs=terrainDef.height||1
    const cellM=cellSizeM(),cellAreaM2=(isHex()?HEX_ROW:1)*cellM*cellM
    const raw=hydroMassDiag
    const kernelBudget=!!(raw&&raw.budgetScope==="kernel"&&!transformed)
    const kernelState=!transformed&&pipeState&&pipeState.deposited
      &&pipeState.w===W&&pipeState.h===H
    let sedM=kernelState&&wantSed?pipeState.deposited:null
    if(!kernelBudget||(wantSed&&!sedM)){
      // Net material added to the SOLID BED. On every engine except the pipes-only GPU path the
      // returned field IS the bed (the droplet kernels write it directly, and the combined path's
      // pipe settle folds suspended load in before the droplets run), so the node's own aggradation
      // is that quantity. `Math.fround` is applied whether or not the raster is allocated, so the
      // ledger's depositedM3 is the integral of exactly the float32 values the port publishes.
      const acc=wantSed?new Float32Array(N):null
      let ero=0,dep=0
      for(let i=0;i<N;i++){
        const d=result[i]-ins[0][i]
        if(d>0){const m=Math.fround(d*hs);if(acc)acc[i]=m;dep+=m}else ero-=d*hs
      }
      if(acc)sedM=acc
      if(raw&&!kernelBudget){
        const led={...raw,cellAreaM2,heightScaleM:hs,
          latticeArea:isHex()?"hexRowPitch":"square",
          budgetScope:transformed?"node-transformed":"node",
          erodedM3:ero*cellAreaM2,depositedM3:dep*cellAreaM2,
          readbacks:Number.isFinite(raw.readbacks)?raw.readbacks:0}
        // Any loss term inherited from a kernel budget describes a field this node no longer
        // publishes. Drop it rather than let a fresh eroded/deposited pair be closed against a
        // stale one - that is the shape of closure that holds for any implementation.
        delete led.exportedOrSuspendedM3;delete led.boundaryExportedM3
        delete led.brushClipGainM3;delete led.suspendedM3
        // A loss term is only published when the engine NAMES it independently. The CPU droplet
        // solver accumulates `exported` per departing particle and `brushClipGain` inside erode1;
        // the GPU droplet and combined engines define exported as sumIn-sumOut
        // (exportedDerived:true), which closes by construction for any implementation including
        // one that deletes the terrain, so they get no loss key at all.
        if(!transformed&&raw.exportedDerived===false){
          led.boundaryExportedM3=(raw.exported||0)*hs*cellAreaM2
          led.exportedOrSuspendedM3=((raw.exported||0)+(raw.lost||0))*hs*cellAreaM2
          if(Number.isFinite(raw.brushClipGain))led.brushClipGainM3=raw.brushClipGain*hs*cellAreaM2
        }
        setHydroMassDiag(led)
      }
    }
    if(!wantState)return result
    const values=new Map([[PRIMARY_PORT,result]])
    if(wantSed&&sedM)values.set("sediment",sedM)
    if(wantVel&&kernelState&&pipeState.velocity)values.set("velocity",pipeState.velocity)
    return{values}
  },
  note:"Enable either hydraulic model or both. <b>Pipe / grid</b> moves standing water and suspended sediment across the field, producing broad connected drainage. <b>Droplet / particle</b> follows many individual downhill paths, adding finer stochastic gullies. When both are enabled the order is fixed: <b>Pipe → Droplet</b>. <b>Lifetime</b> is a work limit: remaining suspended load is reported at truncation, never force-deposited into a terminal cone. <b>Particles</b> increases path coverage; at high density the action budget saturates, so use Erode and Deposit for effect strength. On square terrain both stages stay in GPU textures and read back once; WebGL2 float-blend capability or a hexagonal lattice uses the labelled CPU compatibility fallback. <b>Sediment</b> publishes the cover this pass deposited, in metres, and costs nothing until something is wired to it. <b>Flow velocity</b> is the Pipe solver's own per-cell velocity in m/s and is produced only where that solver runs — not on the hexagonal compatibility path, which has no pipe stage."
})
