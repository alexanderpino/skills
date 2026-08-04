// thermal — Talus: material above repose slides down.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { gpuReady, gpuThermal } from '../../core/gpu.js'
import { P, WHEN } from '../../core/params.js'
import { toMetres } from '../../core/height-frame.js'
import { BUILD_QUALITY, atFeatureScale, cellSizeM, fieldH, fieldW, isHex, HEX_ROW, maskApply,
  newField, resScale, terrainDef, thermalOn } from '../../legacy.js'

// The adapter's frozen primary for this type (src/core/legacy-ports.js). ADR-002: "Display names
// and array positions are never identifiers" — a saved document's edges store this id, so it is a
// constant here rather than something recomputed from a descriptor list.
const PRIMARY_PORT = "out"

// ---- S3.5: the cover stack ---------------------------------------------------------------------
// Slot numbers are the adapter's `legacySlot` values, spelled here as constants for the same reason
// PRIMARY_PORT is. src/core/legacy-ports.js is where they are declared.
const SLOT_SOIL = 2, SLOT_SEDIMENT = 3
// The outputs whose demand turns the cover co-update on. Demanding none of them costs nothing: the
// node returns the bare Float32Array it always has, which is what keeps an unwired graph and
// _verify_digest.js's no-ctx evaluation byte-identical to the pre-S3.5 build.
const COVER_OUTPUTS = ["solidTop", "bedrockHeight", "soilDepth", "sedimentDepth", "sandDepth"]

// HeightField values are not colour channels: negative elevations and values above one are valid.
// The only value-domain invariant thermal erosion requires is finiteness. Failing at the node
// boundary keeps a single NaN/Infinity from being redistributed through every neighbour for every
// iteration and becoming a terrain-sized forest of spikes.
const finiteHeightField = (field, label) => {
  if (!ArrayBuffer.isView(field)) throw new TypeError(`Thermal erosion ${label} must be a typed height field`)
  for (let i = 0; i < field.length; i++) {
    if (!Number.isFinite(field[i])) {
      throw new RangeError(`Thermal erosion ${label} contains a non-finite height at sample ${i}`)
    }
  }
  return field
}

const finiteInRange = (value, lo, hi, label) => {
  if (!Number.isFinite(value) || value < lo || value > hi) {
    throw new RangeError(`Thermal erosion ${label} must be finite and in [${lo}, ${hi}]`)
  }
  return value
}

// A cover raster is USED only if it is a view of exactly the field's length, and every sample of it
// is finite and non-negative. Anything else is reported as ABSENT in the ledger rather than
// half-read: a short raster silently zero-padded is the "silent zeros" failure cover-state.js names
// wearing a different hat, and a negative thickness is not a layer. A WIRED raster that fails the
// value test is a refusal rather than a silent demotion to absent, because "you wired rubbish" and
// "you wired nothing" are different facts and this node already refuses the same way on its height
// input. Checked only on the demanded-cover path, so an undemanded evaluation costs nothing.
const coverRaster = (v, N, label) => {
  if (!(v && ArrayBuffer.isView(v) && v.length === N)) return null
  for (let i = 0; i < N; i++) {
    if (!(Number.isFinite(v[i]) && v[i] >= 0)) {
      throw new RangeError(`Thermal erosion ${label} must be a finite non-negative depth in metres; `
        + `sample ${i} is ${v[i]}`)
    }
  }
  return v
}

// THE HEIGHT FRAME, stated rather than assumed. ADR-005 / D20: two named frames — the viewport
// keeps `display-autolevel`, and a PHYSICAL node takes metres from a stable datum through the
// explicit adapter. This one is physical. Under autolevel, relaxing a slope moves fieldMin/fieldMax,
// so bedrock nobody touched changes elevation and no conservation identity can close;
// frameDriftUnderLocalEdit measures that as 952.39 m of drift at untouched samples against 0.00 m
// here (src/core/height-frame.js:144). Same shape as src/plugins/ero/hydraulic.js:36 — deliberately
// duplicated rather than shared, because the only thing to share is a read of `terrainDef`, and a
// plugin importing another plugin's internals is what `npm run plugins:check` exists to refuse.
const physicalFrame = () => ({
  frame: "physical-stable",
  datumM: Number.isFinite(terrainDef.baseElevation) ? terrainDef.baseElevation : 0,
  reliefM: terrainDef.height || 1,
})

/**
 * The cover co-update, and the physical-volume ledger for it.
 *
 * CONTRACT: talus relaxation consumes LOOSE COVER FIRST and cuts bedrock only where local cover has
 * reached zero; what slides downslope lands in the explicit sediment layer. Both happen in this one
 * evaluation, alongside the height the node returns — a transport node that lowers height and leaves
 * soilDepth untouched throws away path-dependent state no later analysis can reconstruct.
 *
 * WHY THIS IS AT NODE LEVEL AND NOT INSIDE THE KERNEL. The field the node PUBLISHES is not the
 * kernel's output in general: `atFeatureScale` runs the relaxation on a coarser grid and adds back
 * an upsampled delta, and `maskApply` blends the result toward the input. The solid-stack identity
 * has to close against the field that is published, so the cover has to be partitioned from THAT
 * delta. Doing it in the kernel would also cost a second upload and a second readback on the GPU
 * path, which ADR-002's one-synchronisation-point rule forbids — this adds neither.
 *
 * STACK ORDER. solidTop = bedrockHeight + soilDepth + sedimentDepth + sandDepth, bedrock at the
 * bottom, so erosion strips from the TOP down: sand, then sediment, then soil, then bedrock.
 * Material a thermal pass puts down has been transported and lands in `sedimentDepth`.
 *
 * WHAT THIS DELIBERATELY DOES NOT DO: it does not make bedrock harder to relax than cover. Sprint 3
 * asks for transport ORDER ("loose cover first, bedrock second"); a repose angle that differed
 * between regolith and rock is a physical law nobody has specified here, and inventing one would be
 * a fabricated constant. It is also why an unwired graph stays byte-identical.
 */
function coverPass(before, after, ins, loss) {
  const N = after.length, W = fieldW(), H = fieldH()
  const fr = physicalFrame(), relief = fr.reliefM
  const cellM = cellSizeM(), A = (isHex() ? HEX_ROW : 1) * cellM * cellM
  const soil0 = coverRaster(ins[SLOT_SOIL], N, "Soil depth"), sed0 = coverRaster(ins[SLOT_SEDIMENT], N, "Sediment depth")
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
      // rasters rather than a parallel double-precision reckoning of them.
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
    // evaluator reads another is visible instead of silent — a port declared and never filled is a
    // half-gate this sprint has already found three times.
    soilSlot: SLOT_SOIL, sedimentSlot: SLOT_SEDIMENT,
    minCoverAfterM: Number.isFinite(minCoverM) ? minCoverM : null,
  }
  // THE LOSS TERM IS NEVER A SUBTRACTION OF THE TWO SUMS ABOVE. See resolveThermalLoss: on the
  // untransformed path thermal's boundary term is a NAMED PHYSICAL ZERO — both kernels omit
  // off-grid neighbours, so nothing can leave the domain — and everywhere else the node publishes
  // NO CLAIM rather than a number it cannot support. Publishing `consumed + detached - deposited`
  // would close by construction for any implementation, including one that deletes the terrain.
  if (loss && loss.claimed) {
    ledger.exportedOrSuspendedM3 = loss.netM * relief * A
    ledger.boundaryExportedM3 = loss.exportedM * relief * A
    ledger.suspendedM3 = loss.suspendedM * relief * A
    ledger.lossSource = loss.source
    ledger.boundaryPolicy = loss.boundaryPolicy
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
 * Where the cover ledger's boundary term comes from.
 *
 * UNTRANSFORMED: the claim is a MEASURED PROPERTY OF BOTH KERNELS, not an accounting convenience.
 * `thermalErode` (src/legacy.js:2300), `thermalErodeHex` (:2277) and `gpuThermal`
 * (src/core/gpu.js:206) all skip off-grid neighbours — `if(xx<0||yy<0||xx>=n||yy>=nh)continue` and
 * GLSL `if(!inb(q,uN))continue` — and every transfer that does happen debits one on-grid cell and
 * credits another. Nothing can leave the domain, so `exported` is exactly 0. That zero is a claim a
 * gate can FAIL: a kernel that leaked at the rim would leave consumed + detached > deposited and the
 * closure would not hold. It is independently corroborated by _verify_thermal_contract.js, which
 * already gates `massRel <= 2e-6` on the CPU and GPU paths of an edge-touching fixture.
 *
 * TRANSFORMED: a feature-scale resample adds back an upsampled coarse-grid delta and a mask blends
 * the result toward the input. Neither is conservative, and neither difference is a quantity this
 * node accumulated over anything — so it publishes NO CLAIM and says which transform removed it,
 * rather than asserting a number it cannot support.
 */
function resolveThermalLoss(transformedBy) {
  if (transformedBy) return { claimed: false, source: transformedBy }
  return { claimed: true, source: "closed-boundary-no-flux",
    boundaryPolicy: "closed-no-flux", netM: 0, exportedM: 0, suspendedM: 0 }
}

export default definePlugin({
  type: "thermal",
cat:"ero",name:"Thermal erosion",
    // `ins` must stay label-for-label equal to the adapter's row: LEGACY_INS_LABELS is derived from
    // src/core/legacy-ports.js and _verify_port_contract.js's `insDrift` anchor compares the two.
    ins:["In","Mask","Soil depth","Sediment depth"],
    desc:"Talus: material above repose slides down.",
    note:"Closed/no-flux terrain edges. Heights remain finite but unbounded. Mask is an effect composite, not a material wall. <b>Soil depth</b> and <b>Sediment depth</b> are optional carried cover, in metres: wire them and relaxation consumes loose cover first, cutting bedrock only where local cover has reached zero, while what slides downslope adds to the sediment layer — all co-updated with the height in the same pass. Leave them unwired and the node behaves exactly as before, on bare bedrock. The <b>Solid top / Bedrock height / Soil depth / Sediment depth / Sand depth</b> outputs are that stack in metres from a stable datum, and they close solidTop = bedrock + soil + sediment + sand. Sand is zero: no process here produces it. The boundary is closed, so a pass with neither Mask nor Feature Scale exports nothing and says so; with either of those the published field is no longer the kernel's, and the node declines to claim a boundary budget rather than publishing one it cannot itemise.",
    // S3.5 — the SOLID STACK, co-updated with the height in this same evaluation. Every one is in
    // metres in the `physical-stable` frame (ADR-005 / D20), and the identity they close is
    //     solidTop = bedrockHeight + soilDepth + sedimentDepth + sandDepth
    // which `bedrockHeight` is what makes CHECKABLE rather than merely implied: without it the
    // identity is an invariant of code nobody can read off a port.
    extraOutputs:[
      {id:"solidTop",name:"Solid top",kind:"scalarRaster",storage:"R32F",components:1,
        semantic:"solidTop",unit:"m",lens:"state"},
      {id:"bedrockHeight",name:"Bedrock height",kind:"scalarRaster",storage:"R32F",components:1,
        semantic:"bedrockHeight",unit:"m",lens:"state"},
      {id:"soilDepth",name:"Soil depth",kind:"scalarRaster",storage:"R32F",components:1,
        semantic:"soilDepth",unit:"m",lens:"state"},
      // `sedimentDepth`, the standing LAYER THICKNESS that survives between passes — not the
      // `sediment` TRANSPORT quantity ports.js keeps deliberately separate. This node reads a
      // carried thickness in, adds what slid downslope, and hands the new thickness on.
      {id:"sedimentDepth",name:"Sediment depth",kind:"scalarRaster",storage:"R32F",components:1,
        semantic:"sedimentDepth",unit:"m",lens:"state"},
      // ADR-005: the identity never omits the term. Nothing in the pipeline produces sand yet (S7.3
      // owns the aeolian process), so there is no sandDepth INPUT to carry either, and this port is
      // MEASURED zero rather than asserted zero — _verify_thermal_coevolution.js reads the raster.
      {id:"sandDepth",name:"Sand depth",kind:"scalarRaster",storage:"R32F",components:1,
        semantic:"sandDepth",unit:"m",lens:"state"},
    ],
    // Real scale is the DEFAULT: with cell units shipping as default, the Repose slider did not
    // exist on a fresh node and repose 25 vs 45 measured IDENTICAL slope percentiles - the
    // node's only physical control was unreachable out of the box. Cell units stay as the
    // escape hatch (existing saved graphs keep their stored value).
    params:[P.tabs("realScale","Units",[["off","Cell units"],["on","Real scale"]],"on"),
      WHEN(P.slider("repose","Repose angle",15,60,35,1,v=>(v|0)+"°"),"realScale","on"),
      WHEN(P.slider("talus","Talus",0.002,0.05,0.012,0.001,v=>v.toFixed(3)),"realScale","off"),P.int("iters","Iterations",5,80,30),P.slider("rate","Rate",0.1,1,0.5),
      P.log("feat","Feature scale",1,8,1,v=>v.toFixed(1)+"×",false)],
    eval:(p,ins,node,ctx)=>{if(!ins[0])return newField();
    finiteHeightField(ins[0],"input");
    if(ins[1])finiteHeightField(ins[1],"mask");
    finiteInRange(p.rate,0,1,"Rate");
    finiteInRange(p.iters,0,100000,"Iterations");
    finiteInRange(p.feat,1,8,"Feature scale");
    if(p.realScale==="on"){
      finiteInRange(p.repose,0,89.999,"Repose angle");
      finiteInRange(terrainDef.height,Number.MIN_VALUE,Number.MAX_VALUE,"terrain height");
    }else finiteInRange(p.talus,0,Number.MAX_VALUE,"Talus");

    // DEMAND, and why the rule is not normals.js's. normals treats an ABSENT ctx as "compute
    // everything", which is right for a node whose vector port shipped WITH its digest baseline.
    // Thermal is an existing node: _verify_digest.js calls def.eval(params, ins, nd) with no ctx and
    // folds every declared output of a TYPED return into that type's digest string, so "no ctx means
    // compute" would move a baseline. No demand therefore means no state, and the return stays the
    // bare Float32Array it has always been — which is also the only shape under which an undemanded
    // output genuinely costs nothing.
    const demanded=ctx&&ctx.demanded
    const wantCover=!!(demanded&&COVER_OUTPUTS.some(id=>demanded.has(id)))

    // Iteration travel belongs to the requested OUTPUT grid. A 2x final build needs roughly 2x
    // the transport distance even when Feature Scale temporarily evaluates on a coarser grid.
    const outputGridK=resScale();
    // Interactive is a preview-tier budget: enough relaxation to read the landform, bounded so a
    // 1024² property edit does not launch 117+ simulation steps. Final retains full scaled travel.
    const travel=BUILD_QUALITY==="final"?outputGridK:Math.min(1.5,Math.sqrt(outputGridK));
    const iters=Math.max(1,Math.round(p.iters*travel));
    const modified=atFeatureScale(ins[0],p.feat,f=>{
      // IMPORTANT: atFeatureScale has rebound RES here. Repose is a slope threshold per
      // SIMULATION cell, so it must be derived from this coarse grid's cellSizeM()/resScale().
      // Computing it before the callback made a 4x Feature Scale node relax to about one quarter
      // of the requested slope (35 degrees behaved like ~9.9 degrees).
      const simGridK=resScale();
      const talus=(p.realScale==="on")
        ? Math.tan(p.repose*Math.PI/180)*cellSizeM()/terrainDef.height
        : p.talus/simGridK;
      finiteInRange(talus,0,Number.MAX_VALUE,"repose threshold");
      const q={...p,talus,iters};
      // Both kernels omit off-grid neighbours: an explicit closed/no-flux boundary. Hex uses the
      // D6 CPU kernel (one neighbour distance); gpuReady() is already false on hex.
      return gpuReady()?gpuThermal(f,q):thermalOn(f,q);
    });
    const result=maskApply(ins[0],modified,ins[1]);
    finiteHeightField(result,"output");
    if(!wantCover)return result;

    // ---- S3.5: the cover co-update, in this same evaluation ------------------------------------
    // Driven by the delta of the field this node PUBLISHES (result vs ins[0]), not by the kernel's
    // own output: `atFeatureScale` and `maskApply` both stand between the two, and it is the
    // published solid top the stack identity has to close against.
    //
    // `transformedBy` names which of those two removed the boundary claim, and it is a STRING so the
    // ledger can say WHY it declined rather than only that it did. atFeatureScale short-circuits at
    // k <= 1.02 (src/legacy.js:1518) and maskApply returns `modified` unchanged for a null mask
    // (:460), so the untransformed test here is exactly the condition under which the published
    // field IS the kernel's own output.
    const transforms=[];
    if(p.feat>1.02)transforms.push("feature-scale-resample");
    if(ins[1])transforms.push("mask-composite");
    const c=coverPass(ins[0],result,ins,resolveThermalLoss(transforms.join("+")||null));
    // The ledger travels on the typed return rather than on a module global. Hydraulic's
    // `hydroMassDiag` lives in core/gpu.js because the GPU kernels themselves write it; thermal's
    // book is computed here at node level, and a global would go stale the moment a second thermal
    // node evaluated — the exact hazard _verify_cover_erosion.js has to work around by snapshotting
    // between passes. `values` is the only key the evaluator reads (src/legacy.js:3232).
    return{values:coverValues(new Map([[PRIMARY_PORT,result]]),c),ledger:c.ledger};}})
