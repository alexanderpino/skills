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
import { toMetres } from '../../core/height-frame.js'
import { BUILD_QUALITY, RES, atFeatureScale, hydraulicErode, maskApply, newField, resScale,
  cellSizeM, fieldW, fieldH, terrainDef, isHex, HEX_ROW } from '../../legacy.js'

// The adapter's frozen primary for this type (src/core/legacy-ports.js:303). ADR-002: "Display
// names and array positions are never identifiers" - a saved document's edges store this id, so it
// is a constant here rather than something recomputed from a descriptor list.
const PRIMARY_PORT = "out"

// ---- S3.3: the cover stack ------------------------------------------------------------------
// Slot numbers are the adapter's `legacySlot` values, spelled here as constants for the same reason
// PRIMARY_PORT is: a saved document's edges store them, so they are data, not a position that may
// be recomputed. src/core/legacy-ports.js is where they are declared.
const SLOT_SOIL = 2, SLOT_SEDIMENT = 3, SLOT_PRECIP = 4
// The outputs whose demand turns the cover co-update on. Demanding none of them costs nothing:
// the node returns the bare Float32Array it always has, which is what keeps an unwired graph and
// _verify_digest.js's no-ctx evaluation byte-identical to the pre-S3.3 build.
const COVER_OUTPUTS = ["solidTop", "bedrockHeight", "soilDepth", "sedimentDepth", "sandDepth"]

// THE HEIGHT FRAME, stated rather than assumed. ADR-005 / D20: two named frames — the viewport
// keeps `display-autolevel`, and a PHYSICAL node takes metres from a stable datum through the
// explicit adapter. This one is physical. Under autolevel, eroding the terrain moves
// fieldMin/fieldMax, so bedrock nobody touched changes elevation and no conservation identity can
// close; frameDriftUnderLocalEdit measures that as 952.39 m of drift at untouched samples against
// 0.00 m here (src/core/height-frame.js:144).
const physicalFrame = () => ({
  frame: "physical-stable",
  datumM: Number.isFinite(terrainDef.baseElevation) ? terrainDef.baseElevation : 0,
  reliefM: terrainDef.height || 1,
})

// A cover raster is USED only if it is a view of exactly the field's length. Anything else is
// reported as absent in the ledger rather than half-read: a short raster silently zero-padded is
// the "silent zeros" failure cover-state.js names, wearing a different hat.
const coverRaster = (v, N) => (v && ArrayBuffer.isView(v) && v.length === N) ? v : null

/**
 * The cover co-update, and the physical-volume ledger for it.
 *
 * CONTRACT: erosion consumes LOOSE COVER FIRST and cuts bedrock only where local cover has reached
 * zero; deposition lands in the explicit sediment layer. Both happen in this one evaluation,
 * alongside the height the node returns — an erosion node that lowers height and leaves soilDepth
 * untouched throws away path-dependent state no later analysis can reconstruct.
 *
 * WHY THIS IS AT NODE LEVEL AND NOT INSIDE THE KERNEL. The field the node PUBLISHES is not the
 * kernel's output in general: `atFeatureScale` runs the solve on a coarser grid and adds back an
 * upsampled delta, `maskApply` blends the result toward the input, and two stages in series leave
 * the first stage's field behind. The solid-stack identity has to close against the field that is
 * published, so the cover has to be partitioned from THAT delta. Doing it in the kernel would also
 * cost a second upload and a second readback, which ADR-002's one-synchronisation-point rule
 * forbids — this adds neither.
 *
 * STACK ORDER. solidTop = bedrockHeight + soilDepth + sedimentDepth + sandDepth, bedrock at the
 * bottom, so erosion strips from the TOP down: sand, then sediment, then soil, then bedrock.
 * Deposition from a hydraulic pass is transported material and lands in `sedimentDepth`.
 *
 * WHAT THIS DELIBERATELY DOES NOT DO: it does not make bedrock harder to erode than cover. Sprint 3
 * asks for transport ORDER ("loose cover first, bedrock second"), and a differential-erodibility
 * model is a physical law nobody has specified here — inventing a resistance ratio would be a
 * fabricated constant, and it is why an unwired graph stays byte-identical.
 */
function coverPass(before, after, ins, loss) {
  const N = after.length, W = fieldW(), H = fieldH()
  const fr = physicalFrame(), relief = fr.reliefM
  const cellM = cellSizeM(), A = (isHex() ? HEX_ROW : 1) * cellM * cellM
  const soil0 = coverRaster(ins[SLOT_SOIL], N), sed0 = coverRaster(ins[SLOT_SEDIMENT], N)
  const soil = new Float32Array(N), sed = new Float32Array(N), sand = new Float32Array(N)
  // The delta is taken in the STABLE frame, where it is exactly (after-before)*relief: a difference
  // of two absolute elevations that share a datum. Under autolevel this subtraction would silently
  // include the frame's own motion.
  let consumedM = 0, detachedM = 0, depositedM = 0, minCoverM = Infinity
  for (let i = 0; i < N; i++) {
    const s0 = soil0 ? soil0[i] : 0, d0 = sed0 ? sed0[i] : 0, a0 = 0
    const dM = (after[i] - before[i]) * relief
    if (dM < 0) {
      let e = -dM
      // Strip from the top of the stack down. `take <= available` by construction, so where local
      // cover survives the pass `e` reaches zero and bedrockDetached picks up EXACTLY 0 — not a
      // small number that a tolerance would have to forgive.
      const ta = a0 < e ? a0 : e; e -= ta
      const td = d0 < e ? d0 : e; e -= td
      const ts = s0 < e ? s0 : e; e -= ts
      const a1 = Math.fround(a0 - ta), d1 = Math.fround(d0 - td), s1 = Math.fround(s0 - ts)
      sand[i] = a1; sed[i] = d1; soil[i] = s1
      // Accumulated from the values that are PUBLISHED, so the ledger is the integral of the
      // rasters rather than a parallel double-precision reckoning of them (the same rule gpu.js:542
      // and the sediment port already follow).
      consumedM += (a0 - a1) + (d0 - d1) + (s0 - s1)
      detachedM += e
    } else {
      sand[i] = a0; soil[i] = s0
      const d1 = dM > 0 ? Math.fround(d0 + dM) : d0
      sed[i] = d1
      depositedM += d1 - d0
    }
    const cover = sand[i] + sed[i] + soil[i]
    if (cover < minCoverM) minCoverM = cover
  }
  const top = toMetres(after, fr)
  const bedrock = new Float32Array(N)
  for (let i = 0; i < N; i++) bedrock[i] = Math.fround(top[i] - (soil[i] + sed[i] + sand[i]))
  const ledger = {
    coverConsumedM3: consumedM * A, bedrockDetachedM3: detachedM * A, depositedM3: depositedM * A,
    cellAreaM2: A, lattice: terrainDef.lattice, rows: H, cols: W, cells: N,
    latticeArea: isHex() ? "hexRowPitch" : "square",
    frame: fr.frame, datumM: fr.datumM, reliefHeightM: relief,
    stackOrder: ["sandDepth", "sedimentDepth", "soilDepth", "bedrockHeight"],
    soilWired: !!soil0, sedimentWired: !!sed0,
    // THE SLOTS THIS CODE ACTUALLY INDEXED, reported so a descriptor that says one thing while the
    // evaluator reads another is visible instead of silent. A port declared and never filled is one
    // of the half-gates this sprint has already found three times, and `precipitation` is the only
    // one of the three inputs whose arrival nothing else in the arithmetic would reveal — so it is
    // reported as WIRED and as NOT CONSUMED, both of which are claims a gate can fail on.
    soilSlot: SLOT_SOIL, sedimentSlot: SLOT_SEDIMENT, precipitationSlot: SLOT_PRECIP,
    precipitationWired: !!coverRaster(ins[SLOT_PRECIP], N),
    // S3.3 declares the port; it does not consume it. The pipe solver's rain is an uncalibrated
    // per-iteration depth (gpu.js:438, `0.0012/gk`) and the droplet solver has no rain term at all,
    // so turning mm/yr into either needs a REFERENCE precipitation that nobody has measured.
    // Inventing one would be a fabricated constant of exactly the kind this codebase refuses.
    // Sprint-03 puts the spatial Moisture producer in S5.2 and says the port exists so that
    // producer has somewhere to land; until then this flag says so out loud.
    precipitationConsumed: false,
    minCoverAfterM: Number.isFinite(minCoverM) ? minCoverM : null,
  }
  // THE LOSS TERM IS NEVER A SUBTRACTION OF THE TWO SUMS ABOVE. `loss` arrives already resolved
  // from quantities the SOLVER accumulated over cells or particles this block never touched (see
  // resolveCoverLoss). Where no engine names one, the ledger says so and claims no closure, rather
  // than publishing `eroded - deposited` and calling it export — a number that closes by
  // construction for any implementation, including one that deletes the terrain.
  if (loss && loss.claimed) {
    ledger.exportedOrSuspendedM3 = loss.netM * relief * A
    ledger.boundaryExportedM3 = loss.exportedM * relief * A
    ledger.suspendedM3 = loss.suspendedM * relief * A
    if (loss.gainM) ledger.brushClipGainM3 = loss.gainM * relief * A
    ledger.lossSource = loss.source
  } else {
    ledger.lossClaimed = false
    ledger.lossSource = loss ? loss.source : "unclaimed"
  }
  return { top, bedrock, soil, sed, sand, ledger }
}

/** Put one coverPass result on a typed values map, under the declared port ids. */
function coverValues(values, c) {
  values.set("solidTop", c.top); values.set("bedrockHeight", c.bedrock)
  values.set("soilDepth", c.soil); values.set("sedimentDepth", c.sed); values.set("sandDepth", c.sand)
  return values
}

/**
 * Where the cover ledger's boundary term comes from, per engine. Each component is accumulated by
 * the solver over a cell set or a particle set that the published field does not control, which is
 * what makes the closure `consumed + detached = deposited + exported` a MEASUREMENT rather than an
 * identity.
 */
function resolveCoverLoss(raw, transformed) {
  // A transformed field is no longer the one the kernel budgeted, so no term describes it.
  if (transformed || !raw) return { claimed: false, source: transformed ? "field-transformed" : "no-ledger" }
  if (raw.engine === "pipes" && raw.exportedDerived === false && Number.isFinite(raw.exportedToApron)) {
    // The apron ring is DISJOINT from the core (gpu.js:516-522), so what left the core arriving in
    // the apron is an independent reading of the same quantity. `lost`/`nonConservation` must NOT
    // be added here: it is sumSimIn-sumSimOut, which reduces algebraically to
    // cropExchange - exportedToApron, and including it would make the closure hold for free.
    // Nothing is suspended relative to the PUBLISHED top on this path — gpuHydraulicPipes settles
    // the blue channel into the returned field (gpu.js:535, o = bed + suspended).
    return { claimed: true, source: "pipe-apron-ring", netM: raw.exportedToApron,
      exportedM: raw.exportedToApron, suspendedM: 0, gainM: 0 }
  }
  if (raw.engine === "droplets" && raw.exportedDerived === false) {
    // Per particle and per clipped brush cell, all three inside the solver's own loop:
    // `exported` when a droplet leaves the grid, `lost` when one is truncated with load still
    // suspended, and `brushClipGain` for every brush cell clipped at the border — mass the droplet
    // credited itself but never removed from the field, i.e. a boundary IMPORT. The net transfer
    // out of the published field is therefore exported + lost - brushClipGain, which is the same
    // named identity _verify_erosion_mass.js G2 already gates
    // (sumIn - sumOut = exported + lost - brushClipGain).
    const exportedM = raw.exported || 0, suspendedM = raw.lost || 0, gainM = raw.brushClipGain || 0
    return { claimed: true, source: "droplet-particle-counters",
      netM: exportedM + suspendedM - gainM, exportedM, suspendedM, gainM }
  }
  // gpu-droplets and gpu-combined define exported as sumIn-sumOut (`exportedDerived:true`), which
  // is exactly the closure-by-construction this refuses to publish.
  return { claimed: false, source: raw.exportedDerived === true ? "engine-export-is-derived" : "engine-unnamed" }
}

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
  // `ins` must stay label-for-label equal to the adapter's row: LEGACY_INS_LABELS is derived from
  // src/core/legacy-ports.js and _verify_port_contract.js's `insDrift` anchor compares the two.
  type:"hydraulic",cat:"ero",name:"Hydraulic erosion",
  ins:["In","Mask","Soil depth","Sediment depth","Precipitation"],
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
    // S3.3 — the SOLID STACK, co-updated with the height in this same evaluation. Every one is in
    // metres in the `physical-stable` frame (ADR-005 / D20), and the identity they close is
    //     solidTop = bedrockHeight + soilDepth + sedimentDepth + sandDepth
    // which `bedrockHeight` is what makes CHECKABLE rather than merely implied: without it the
    // identity is an invariant of code nobody can read off a port.
    {id:"solidTop",name:"Solid top",kind:"scalarRaster",storage:"R32F",components:1,
      semantic:"solidTop",unit:"m",lens:"state"},
    {id:"bedrockHeight",name:"Bedrock height",kind:"scalarRaster",storage:"R32F",components:1,
      semantic:"bedrockHeight",unit:"m",lens:"state"},
    {id:"soilDepth",name:"Soil depth",kind:"scalarRaster",storage:"R32F",components:1,
      semantic:"soilDepth",unit:"m",lens:"state"},
    // `sedimentDepth`, NOT `sediment`. The `sediment` port above is a TRANSPORT quantity — what this
    // pass put down — and this one is the standing LAYER THICKNESS that survives between passes.
    // ports.js keeps the two semantics apart on purpose and this node is where they meet: it reads
    // a carried thickness in, adds what it deposited, and hands the new thickness on.
    {id:"sedimentDepth",name:"Sediment depth",kind:"scalarRaster",storage:"R32F",components:1,
      semantic:"sedimentDepth",unit:"m",lens:"state"},
    // ADR-005: the identity never omits the term. Nothing in the pipeline produces sand yet (S7.3
    // owns the aeolian process), so there is no sandDepth INPUT to carry either, and this port is
    // MEASURED zero rather than asserted zero — _verify_cover_erosion.js reads the raster. When a
    // sand producer lands, the input slot has to land in the same story: a transport node that
    // published a zero sand layer over a real one would be destroying state, which is the defect
    // this whole sprint exists to stop.
    {id:"sandDepth",name:"Sand depth",kind:"scalarRaster",storage:"R32F",components:1,
      semantic:"sandDepth",unit:"m",lens:"state"},
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
    const stages=enabledStages(p)
    // DEMAND, and why the rule is not normals.js's. normals treats an ABSENT ctx as "compute
    // everything", which is right for a node whose vector port shipped WITH its digest baseline.
    // Hydraulic is an existing node: _verify_digest.js:200-213 calls def.eval(params, ins, nd)
    // with no ctx and folds every declared output of a TYPED return into that type's digest
    // string, so "no ctx means compute" would move a baseline this story must not move. No demand
    // therefore means no state, and the return stays the bare Float32Array it has always been -
    // which is also the only shape under which an undemanded output genuinely costs nothing.
    const demanded=ctx&&ctx.demanded
    const wantSed=!!(demanded&&demanded.has("sediment")),wantVel=!!(demanded&&demanded.has("velocity"))
    const wantCover=!!(demanded&&COVER_OUTPUTS.some(id=>demanded.has(id)))
    const wantState=wantSed||wantVel||wantCover
    if(!stages.pipes&&!stages.droplets){
      // BOTH STAGES OFF. Historically this returned a bare copy and touched nothing else, and it
      // still does when no cover output is demanded — the shape _verify_digest.js evaluates.
      // Under cover demand it is the IDENTITY PASS: cover comes back exactly as it arrived, sand is
      // the zero layer, solidTop is the input in metres, and the ledger reports an all-zero cover
      // book. A pass that moved no material must SAY it moved no material; leaving the previous
      // node's ledger standing would let a caller read someone else's transport as this node's.
      const idle=ins[0].slice()
      if(!wantCover)return idle
      const c=coverPass(ins[0],idle,ins,{claimed:true,source:"no-transport-stage-enabled",
        netM:0,exportedM:0,suspendedM:0,gainM:0})
      setHydroMassDiag({engine:"identity",settle:false,budgetScope:"node-identity",
        cellAreaM2:c.ledger.cellAreaM2,heightScaleM:c.ledger.reliefHeightM,
        latticeArea:c.ledger.latticeArea,erodedM3:0,depositedM3:0,readbacks:0,cover:c.ledger})
      return{values:coverValues(new Map([[PRIMARY_PORT,idle]]),c)}
    }
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
    // ---- S3.3: the cover co-update, in this same evaluation -----------------------------------
    // Driven by the delta of the field this node PUBLISHES (result vs ins[0]), not by the kernel's
    // own bed delta: on the pipes path the two differ - the returned height folds the still
    // suspended load in at settle time - and it is the published solid top the stack identity has
    // to close against. That is also why the `kernelBudget` shortcut above is not taken here.
    if(wantCover){
      const c=coverPass(ins[0],result,ins,resolveCoverLoss(raw,transformed))
      coverValues(values,c)
      const base=hydroMassDiag
      setHydroMassDiag(base?{...base,cover:c.ledger}:{engine:"unknown",cover:c.ledger})
    }
    return{values}
  },
  note:"Enable either hydraulic model or both. <b>Pipe / grid</b> moves standing water and suspended sediment across the field, producing broad connected drainage. <b>Droplet / particle</b> follows many individual downhill paths, adding finer stochastic gullies. When both are enabled the order is fixed: <b>Pipe → Droplet</b>. <b>Lifetime</b> is a work limit: remaining suspended load is reported at truncation, never force-deposited into a terminal cone. <b>Particles</b> increases path coverage; at high density the action budget saturates, so use Erode and Deposit for effect strength. On square terrain both stages stay in GPU textures and read back once; WebGL2 float-blend capability or a hexagonal lattice uses the labelled CPU compatibility fallback. <b>Sediment</b> publishes the cover this pass deposited, in metres, and costs nothing until something is wired to it. <b>Flow velocity</b> is the Pipe solver's own per-cell velocity in m/s and is produced only where that solver runs — not on the hexagonal compatibility path, which has no pipe stage. <b>Soil depth</b> and <b>Sediment depth</b> are optional carried cover, in metres: wire them and erosion consumes loose cover first, cutting bedrock only where local cover has reached zero, while deposition adds to the sediment layer — all co-updated with the height in the same pass. Leave them unwired and the node behaves exactly as before, on bare bedrock. The <b>Solid top / Bedrock height / Soil depth / Sediment depth / Sand depth</b> outputs are that stack in metres from a stable datum, and they close solidTop = bedrock + soil + sediment + sand. Sand is zero: no process here produces it. <b>Precipitation</b> (mm/yr) is declared for S5's Moisture producer and is not yet consumed by the solver — the rain term is an uncalibrated per-iteration rate and converting mm/yr into it would need a reference value nobody has measured."
})
