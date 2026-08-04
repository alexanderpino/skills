// erosion2 — Advanced multi-scale hydraulic erosion: broad ravines first, nested gullies second, then s
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { hydroMassDiag } from '../../core/gpu.js'
import { P, GROUP } from '../../core/params.js'
import { toMetres } from '../../core/height-frame.js'
import { BUILD_QUALITY, RES, cellSizeM, clamp, erosion2Field, fieldH, fieldW, HEX_ROW, isHex, lerp,
  maskApply, newField, terrainDef } from '../../legacy.js'

// The adapter's frozen primary for this type (src/core/legacy-ports.js). ADR-002: "Display names
// and array positions are never identifiers" — a saved document's edges store this id, so it is a
// constant here rather than something recomputed from a descriptor list.
const PRIMARY_PORT = "out"

// ---- S3.5: the cover stack ---------------------------------------------------------------------
// Slot numbers are the adapter's `legacySlot` values, spelled here as constants for the same reason
// PRIMARY_PORT is. src/core/legacy-ports.js is where they are declared. Erosion 2's frozen row is
// In/Mask, so cover lands at 2 and 3 — thermal's numbers, not Stream Power's.
const SLOT_MASK = 1, SLOT_SOIL = 2, SLOT_SEDIMENT = 3
// The outputs whose demand turns the cover co-update on. Demanding none of them costs nothing: the
// node returns the bare Float32Array it always has, which is what keeps an unwired graph and
// _verify_digest.js's no-ctx evaluation byte-identical to the pre-S3.5 build.
const COVER_OUTPUTS = ["solidTop", "bedrockHeight", "soilDepth", "sedimentDepth", "sandDepth"]

// A cover raster is USED only if it is a view of exactly the field's length, and every sample of it
// is finite and non-negative. Anything else is reported as ABSENT in the ledger rather than
// half-read: a short raster silently zero-padded is the "silent zeros" failure cover-state.js names
// wearing a different hat, and a negative thickness is not a layer. A WIRED raster that fails the
// value test is a refusal rather than a silent demotion to absent, because "you wired rubbish" and
// "you wired nothing" are different facts. Checked ONLY on the demanded-cover path — this node
// deliberately gains no validation on the path _verify_digest.js walks, so the shipped field cannot
// move for a reason that is not the physics.
const coverRaster = (v, N, label) => {
  if (!(v && ArrayBuffer.isView(v) && v.length === N)) return null
  for (let i = 0; i < N; i++) {
    if (!(Number.isFinite(v[i]) && v[i] >= 0)) {
      throw new RangeError(`Erosion 2 ${label} must be a finite non-negative depth in metres; `
        + `sample ${i} is ${v[i]}`)
    }
  }
  return v
}

// THE HEIGHT FRAME, stated rather than assumed. ADR-005 / D20: two named frames — the viewport
// keeps `display-autolevel`, and a PHYSICAL node takes metres from a stable datum through the
// explicit adapter. This one is physical. Under autolevel, carving a ravine moves fieldMin/fieldMax,
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
 * WHICH STAGES OF THE COMPOSITION ARE RUNNING, read off the same expressions `erosion2Field` uses.
 *
 * This is not decoration. Two separate ledger claims below turn on it, and both would be
 * unsupportable without it:
 *
 *  1. `composedBy` — the transform list that REMOVES the stage boundary budget. `erosion2Field`
 *     leaves exactly one `hydroMassDiag` behind, from whichever hydraulic call ran LAST. That
 *     object describes the field IT received on the grid IT ran on, so it describes what this node
 *     publishes only when nothing stands between them: no feature-scale resample, no nested second
 *     pass, no thermal shaping, no sharpening and no mask.
 *  2. `manufacturedRiseStages` — the stages that RAISE THE SURFACE WITHOUT TRANSPORTING ANYTHING,
 *     and which are therefore folded into `depositedM3` with no way to separate them out.
 *
 * Every predicate is transcribed from the source, not from the sprint document:
 *   featureScale  `lerp(1,7,clamp(p.erosionScale,0,1))` (src/legacy.js:3072), handed to
 *                 `atFeatureScale(source, scale*tier, ...)` (:3086) which short-circuits at
 *                 `!(k>1.02)` (:1517)
 *   tier          `BUILD_QUALITY==="final"?1:Math.max(1,RES/384)` (:3080)
 *   fine pass     `if(detail>.02)` (:3096)
 *   thermal shape `if(p.shape>.01)` (:3100)
 *   sharpen       `if(p.shapeSharp>.01)` (:3106)
 */
function stagesOf(p, hasMask) {
  const detail = clamp(p.shapeDetail, 0, 1)
  const tier = BUILD_QUALITY === "final" ? 1 : Math.max(1, RES / 384)
  const featureScale = lerp(1, 7, clamp(p.erosionScale, 0, 1))
  const composed = []
  if (featureScale * tier > 1.02) composed.push("erosion-scale-resample")
  if (detail > 0.02) composed.push("nested-detail-pass")
  if (p.shape > 0.01) composed.push("shape-thermal-blend")
  if (p.shapeSharp > 0.01) composed.push("shape-sharpen")
  if (hasMask) composed.push("mask-composite")
  // THE STAGES THAT MANUFACTURE RELIEF. Both raise the published surface without any process
  // having carried material to the cell, so both are inside `depositedM3` and neither can be
  // separated out of it at node level. Naming them is what makes `depositionStageResolved:false`
  // a specific claim rather than a shrug.
  //
  //   seed-perturbation  UNCONDITIONAL (src/legacy.js:3068-3070). `seedAmp = relief*(.0007 +
  //                      .0022*detail)` with `relief = Math.max(mx-mn,1e-5)` (:3065), so the
  //                      amplitude is never zero and the loop is not behind any `if`. A signed fbm
  //                      field is ADDED to the input before a single droplet runs; the comment at
  //                      :3066-3067 says it "is consumed by erosion", which is a statement about
  //                      magnitude, not a conservation claim — nothing accumulates it.
  //   shape-sharpen      `h[i] += residual>0 ? residual*shapeSharp*.24 : residual*shapeSharp*.07`
  //                      (:3110). The gain is ASYMMETRIC — 0.24 up against 0.07 down — so over a
  //                      blur whose residual sums to about zero the stage has a positive net.
  //
  // `shape-thermal-blend` is deliberately NOT here. `h = lerp(h, shaped, p.shape*.72)` (:3104) is a
  // convex blend of two fields whose sums agree (both thermal kernels omit off-grid neighbours), so
  // it redistributes rather than manufactures — and what it moves downslope IS transported material,
  // which belongs in the deposit.
  const manufactured = ["seed-perturbation"]
  if (p.shapeSharp > 0.01) manufactured.push("shape-sharpen")
  return { composed, manufactured, featureScale, tier, detail }
}

/**
 * The cover co-update, and the physical-volume ledger for it.
 *
 * CONTRACT: the composition consumes LOOSE COVER FIRST and cuts bedrock only where local cover has
 * reached zero; where the published surface RISES the material lands in the explicit sediment layer.
 * All of it happens in this one evaluation, alongside the height the node returns.
 *
 * WHY THE RISE IS A DEPOSIT HERE AND A BEDROCK GAIN IN STREAM POWER. That difference is the physics,
 * measured off the kernels rather than assumed from the family name:
 *   - `streamPowerErode` raises cells through an uplift SOURCE TERM and through hillslope diffusion
 *     of the rock column; it has no deposition term at all, and sprint-03:186 forbids inventing one.
 *   - `erosion2Field` composes the pipe/droplet solver (`gpuHydraulicPipes` / `hydraulicErode`,
 *     src/legacy.js:3086-3089) with `deposit = lerp(.08,.62,sediment)` (:3084) and then a thermal
 *     relaxation (:3100-3105). BOTH of those put transported material down. The node models
 *     deposition, so the honest destination for a rise is `sedimentDepth`, exactly as S3.3's
 *     Hydraulic and S3.5a's Thermal already book it.
 * `maxCoverRiseM` is what makes that a MEASUREMENT rather than a declaration: it is read back out of
 * the published rasters, and _verify_erosion2_coevolution.js requires it to be strictly positive.
 * Under the streampower shape it would be exactly zero.
 *
 * WHAT THIS DELIBERATELY DOES NOT CLAIM, AND WHY — sprint-03:188.
 * The sprint asks Erosion 2 to "expose/co-update the state of the hydraulic/thermal stages it
 * composes rather than re-deriving deposits from final height". HALF of that is possible here and
 * half is not, and the ledger says which is which instead of blurring them:
 *   - the CO-UPDATE is done, in this pass, against the field the node publishes;
 *   - the STAGE RESOLUTION is not. `erosion2Field` returns one Float32Array (src/legacy.js:3113)
 *     and accumulates nothing per stage. There are up to four surface-moving stages plus an
 *     unconditional fbm injection between `ins[0]` and the return, and the only artefact any of them
 *     leaves behind is a single last-run-wins `hydroMassDiag`. So `depositedM3` IS re-derived from
 *     the final height — which is the debt the sprint names — and `depositionStageResolved:false`
 *     with `manufacturedRiseStages` is this node saying so in a form a gate can read. Closing it
 *     needs per-stage accumulators inside `erosion2Field`, in src/legacy.js.
 *
 * WHY THIS IS AT NODE LEVEL AND NOT INSIDE THE KERNEL. The field the node PUBLISHES is not the
 * kernel's output in general: `atFeatureScale` runs each pass on a coarser grid and adds back an
 * upsampled delta, and `maskApply` blends the result toward the input. The solid-stack identity has
 * to close against the field that is published, so the cover has to be partitioned from THAT delta.
 *
 * STACK ORDER. solidTop = bedrockHeight + soilDepth + sedimentDepth + sandDepth, bedrock at the
 * bottom, so incision strips from the TOP down: sand, then sediment, then soil, then bedrock.
 *
 * WHAT THIS DELIBERATELY DOES NOT DO: it does not make bedrock harder to erode than cover. Sprint 3
 * asks for transport ORDER ("loose cover first, bedrock second"); an erodibility that differed
 * between regolith and rock is a physical law nobody has specified here, and inventing one would be
 * a fabricated constant. It is also why an unwired graph stays byte-identical.
 */
function coverPass(before, after, ins, stages, stage, lossSource) {
  const N = after.length, W = fieldW(), H = fieldH()
  const fr = physicalFrame(), relief = fr.reliefM
  const cellM = cellSizeM(), A = (isHex() ? HEX_ROW : 1) * cellM * cellM
  const soil0 = coverRaster(ins[SLOT_SOIL], N, "Soil depth")
  const sed0 = coverRaster(ins[SLOT_SEDIMENT], N, "Sediment depth")
  const soil = new Float32Array(N), sed = new Float32Array(N), sand = new Float32Array(N)
  // The delta is taken in the STABLE frame, where it is exactly (after-before)*relief: a difference
  // of two absolute elevations that share a datum. Under autolevel this subtraction would silently
  // include the frame's own motion.
  let consumedM = 0, detachedM = 0, depositedM = 0, minCoverM = Infinity, maxRiseM = -Infinity
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
    const c1 = sand[i] + sed[i] + soil[i], c0 = a0 + d0 + s0
    if (c1 < minCoverM) minCoverM = c1
    if (c1 - c0 > maxRiseM) maxRiseM = c1 - c0
  }
  const top = toMetres(after, fr)
  const bedrock = new Float32Array(N)
  for (let i = 0; i < N; i++) bedrock[i] = Math.fround(top[i] - (soil[i] + sed[i] + sand[i]))
  const ledger = {
    coverConsumedM3: consumedM * A, bedrockDetachedM3: detachedM * A, depositedM3: depositedM * A,
    // A CLAIM, not a flag copied from a sibling. This node's transport stages have a deposit term
    // and its published surface genuinely rises where they used it; `maxCoverRiseM` below is the
    // reading that has to agree.
    depositionModelled: true,
    // ...and the exact extent of what that claim covers. See the block comment: the deposit is the
    // integral of the published rise, NOT a stage-resolved figure, because nothing accumulates one.
    depositionStageResolved: false,
    depositionSource: "published-delta-not-stage-resolved",
    // The stages inside that figure which carried no material to the cell at all. Named, so the
    // contamination is a fact a gate can check rather than a caveat in prose.
    manufacturedRiseStages: stages.manufactured.slice(),
    composedBy: stages.composed.slice(),
    cellAreaM2: A, lattice: terrainDef.lattice, rows: H, cols: W, cells: N,
    latticeArea: isHex() ? "hexRowPitch" : "square",
    frame: fr.frame, datumM: fr.datumM, reliefHeightM: relief,
    stackOrder: ["sandDepth", "sedimentDepth", "soilDepth", "bedrockHeight"],
    soilWired: !!soil0, sedimentWired: !!sed0,
    // THE SLOTS THIS CODE ACTUALLY INDEXED, reported so a descriptor that says one thing while the
    // evaluator reads another is visible instead of silent — a port declared and never filled is a
    // half-gate this sprint has already found repeatedly.
    soilSlot: SLOT_SOIL, sedimentSlot: SLOT_SEDIMENT, maskSlot: SLOT_MASK,
    minCoverAfterM: Number.isFinite(minCoverM) ? minCoverM : null,
    maxCoverRiseM: Number.isFinite(maxRiseM) ? maxRiseM : null,
    // THE NODE-LEVEL BOUNDARY BUDGET IS NEVER CLAIMED, ON ANY PATH, AND THAT IS THE HONEST ANSWER.
    //
    // Thermal could publish a named physical zero because both its kernels omit off-grid neighbours.
    // Hydraulic can publish the droplet solver's per-particle counters when exactly one kernel ran
    // on an untransformed field. Erosion 2 can do neither at NODE level, and the reason is not the
    // boundary — it is the fbm injection at src/legacy.js:3068-3070, which adds a signed synthetic
    // field to `ins[0]` before any solver runs and is accumulated NOWHERE. Even in the one regime
    // where every transform is off, the solver's budget describes `seeded`, not the node's input, and
    // the volume between them is unrecorded.
    //
    // So the node publishes NO node-level figure. `exportedOrSuspendedM3 = coverConsumed +
    // bedrockDetached - deposited` would look like a boundary budget and would be a restatement of
    // the three terms it is compared against: a closure that holds by construction for any
    // implementation, including one that deletes the terrain. That is the defect this suite keeps
    // finding, and refusing it is the point. What it WOULD take to claim one is an accumulator for
    // the seed injection and one per stage inside `erosion2Field`, which lives in src/legacy.js.
    lossClaimed: false,
    lossSource,
  }
  // THE STAGE BOUNDARY BUDGET — the one budget line this node genuinely can support, and only where
  // it describes something. See resolveStageBudget. It is scoped in its own key names and in
  // `stageBudgetScope`, so it can never be mistaken for the node-level closure refused above.
  if (stage && stage.claimed) {
    ledger.stageBoundaryExportedM3 = stage.exportedM * relief * A
    ledger.stageSuspendedM3 = stage.suspendedM * relief * A
    ledger.stageBrushClipGainM3 = stage.gainM * relief * A
    ledger.stageBudgetEngine = stage.engine
    ledger.stageBudgetScope = "sole-hydraulic-stage-over-the-seeded-field"
  } else {
    ledger.stageBudgetClaimed = false
  }
  ledger.stageBudgetSource = stage ? stage.source : "unclaimed"
  return { top, bedrock, soil, sed, sand, ledger }
}

/** Put one coverPass result on a typed values map, under the declared port ids. */
function coverValues(values, c) {
  values.set("solidTop", c.top); values.set("bedrockHeight", c.bedrock)
  values.set("soilDepth", c.soil); values.set("sedimentDepth", c.sed); values.set("sandDepth", c.sand)
  return values
}

/**
 * The boundary transfer of the composition's SOLE hydraulic stage, when there is exactly one.
 *
 * ITEMISED BY THE SOLVER, NOT BY THIS NODE. Both engines accumulate their boundary transfer over a
 * cell or particle set the published field does not control, which is what makes the number a
 * measurement rather than an identity:
 *   pipes     `exportedToApron = apronOut - apronIn` over the apron ring, a cell set DISJOINT from
 *             the core (src/core/gpu.js:546-553). `nonConservation` is deliberately not read: it
 *             reduces algebraically to cropExchange - exportedToApron.
 *   droplets  `exported` per departing particle, `lost` per particle truncated with load still
 *             suspended, and `brushClipGain` per brush cell clipped at the border — a boundary
 *             IMPORT (src/legacy.js:3054, set from erode1's own counters).
 * An engine whose `exportedDerived` is true defines export as sumIn - sumOut, which closes by
 * construction for any implementation including one that deletes the terrain; those get no claim.
 *
 * STALENESS IS REFUSED RATHER THAN RISKED. `hydroMassDiag` is a module global, so a diag left by an
 * EARLIER node would read exactly like one this evaluation produced. The caller snapshots it before
 * `erosion2Field` runs and the identity comparison here is what turns "nobody wrote one" into a
 * named decline instead of another node's transport reported as this one's.
 *
 * AND WHERE THE FIGURE WOULD NOT DESCRIBE ANYTHING, NOTHING IS CLAIMED. `composedBy` non-empty means
 * some stage stands between the budgeted field and the published one: a feature-scale resample (the
 * budget then describes a coarse sub-grid), a second hydraulic pass (last-run-wins, so the first
 * pass's transfer is simply gone), a thermal or sharpening stage after it, or a mask blending the
 * result back toward the input. Publishing the solver's figure against a field it no longer
 * describes is the same error as publishing a derived closure, wearing better clothes.
 */
function resolveStageBudget(diag, diagBefore, composedBy) {
  if (composedBy.length) return { claimed: false, source: composedBy.join("+") }
  if (!diag || diag === diagBefore) return { claimed: false, source: "no-stage-budget-produced" }
  if (diag.exportedDerived !== false) {
    return { claimed: false,
      source: diag.exportedDerived === true ? "engine-export-is-derived" : "engine-unnamed" }
  }
  if (diag.engine === "pipes" && Number.isFinite(diag.exportedToApron)) {
    return { claimed: true, source: "pipe-apron-ring", engine: "pipes",
      exportedM: diag.exportedToApron, suspendedM: 0, gainM: 0 }
  }
  if (diag.engine === "droplets") {
    const exportedM = diag.exported || 0, suspendedM = diag.lost || 0, gainM = diag.brushClipGain || 0
    if (!(Number.isFinite(exportedM) && Number.isFinite(suspendedM) && Number.isFinite(gainM))) {
      return { claimed: false, source: "engine-counters-non-finite" }
    }
    return { claimed: true, source: "droplet-particle-counters", engine: "droplets",
      exportedM, suspendedM, gainM }
  }
  return { claimed: false, source: "engine-unnamed" }
}

export default definePlugin({
  type: "erosion2",
cat:"ero",name:"Erosion 2",
    // `ins` must stay label-for-label equal to the adapter's row: LEGACY_INS_LABELS is derived from
    // src/core/legacy-ports.js and _verify_port_contract.js's `insDrift` anchor compares the two.
    ins:["In","Mask","Soil depth","Sediment depth"],
    desc:"Advanced multi-scale hydraulic erosion: broad ravines first, nested gullies second, then sediment and shape relaxation.",
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
      // carried thickness in, CONSUMES from it where it cuts and ADDS to it where it aggrades.
      //
      // It deliberately does NOT declare Hydraulic's `sediment` port. That port means "how much THIS
      // PASS put down", and this node is a composition of up to four surface-moving stages plus an
      // fbm injection with no per-stage accounting between them — so a `sediment` raster here would
      // be the published rise wearing a transport label it cannot support. The ledger says the same
      // thing in `depositionStageResolved:false`.
      {id:"sedimentDepth",name:"Sediment depth",kind:"scalarRaster",storage:"R32F",components:1,
        semantic:"sedimentDepth",unit:"m",lens:"state"},
      // ADR-005: the identity never omits the term. Nothing in the pipeline produces sand yet (S7.3
      // owns the aeolian process), so there is no sandDepth INPUT to carry either, and this port is
      // MEASURED zero rather than asserted zero — _verify_erosion2_coevolution.js reads the raster.
      {id:"sandDepth",name:"Sand depth",kind:"scalarRaster",storage:"R32F",components:1,
        semantic:"sandDepth",unit:"m",lens:"state"},
    ],
    params:[
      GROUP(P.slider("duration","Duration",0,1,.46,.01),"General"),
      GROUP(P.slider("downcut","Downcutting",0,1,.58,.01),"General"),
      GROUP(P.slider("erosionScale","Erosion scale",0,1,.38,.01,v=>lerp(1,7,v).toFixed(1)+"×"),"General"),
      GROUP(P.seed("seed","Seed",17),"General"),
      GROUP(P.slider("suspended","Suspended load",0,1,.36,.01),"Sediment discharge"),
      GROUP(P.slider("bed","Bed load",0,1,.30,.01),"Sediment discharge"),
      GROUP(P.slider("coarse","Coarse sediments",0,1,.22,.01),"Sediment discharge"),
      GROUP(P.slider("depositBoost","Deposition boost",0,1,.18,.01),"Sediment discharge"),
      GROUP(P.slider("shape","Shape",0,1,.28,.01),"Shape"),
      GROUP(P.slider("shapeSharp","Shape sharpness",0,1,.42,.01),"Shape"),
      GROUP(P.slider("shapeDetail","Shape detail scale",0,1,.72,.01),"Shape")],
    eval:(p,ins,node,ctx)=>{if(!ins[0])return newField();
      // Snapshotted BEFORE the composition runs, so `resolveStageBudget` can tell "this evaluation
      // produced a solver budget" from "some earlier node's budget is still sitting in the global".
      // Read unconditionally rather than behind the demand test: reading a module binding costs
      // nothing, and putting it inside the branch would make the snapshot depend on whether cover
      // was demanded, which is exactly the sort of path-dependent difference this node must not have.
      const diagBefore=hydroMassDiag;
      const result=maskApply(ins[0],erosion2Field(ins[0],p),ins[SLOT_MASK]);

      // DEMAND, and why the rule is not normals.js's. normals treats an ABSENT ctx as "compute
      // everything", which is right for a node whose vector port shipped WITH its digest baseline.
      // Erosion 2 is an existing node: _verify_digest.js calls def.eval(params, ins, nd) with no ctx
      // and folds every declared output of a TYPED return into that type's digest string, so "no ctx
      // means compute" would move a baseline. No demand therefore means no state, and the return
      // stays the bare Float32Array it has always been — which is also the only shape under which an
      // undemanded output genuinely costs nothing.
      const demanded=ctx&&ctx.demanded;
      if(!(demanded&&COVER_OUTPUTS.some(id=>demanded.has(id))))return result;

      // ---- S3.5: the cover co-update, in this same evaluation ----------------------------------
      // Driven by the delta of the field this node PUBLISHES (result vs ins[0]), not by any stage's
      // own output: `atFeatureScale` and `maskApply` both stand between the two, and it is the
      // published solid top the stack identity has to close against.
      const stages=stagesOf(p,!!ins[SLOT_MASK]);
      const c=coverPass(ins[0],result,ins,stages,
        resolveStageBudget(hydroMassDiag,diagBefore,stages.composed),
        // The node-level budget is unavailable for a COMPOSITION reason that no slider can remove —
        // the fbm injection is unconditional — so it says so on every path. A mask does not make an
        // unaccumulated seed volume any more accumulated.
        "seed-injection-and-stage-composition-not-itemised");
      // The ledger travels on the typed return rather than on a module global, which would go stale
      // the moment a second erosion2 node evaluated. `values` is the only key the evaluator reads
      // (src/legacy.js:3232).
      return{values:coverValues(new Map([[PRIMARY_PORT,result]]),c),ledger:c.ledger};},
    note:"<b>Erosion 2</b> is a clean-room multi-scale composition over Terrain Studio's owned hydraulic and thermal kernels, following Gaea's public control contract rather than claiming its proprietary algorithm. <b>Duration</b> controls simulation travel; <b>Downcutting</b> controls incision; <b>Erosion scale</b> sets the largest ravines. A shorter near-native pass nests fine gullies inside those broad structures. Suspended, bed, and coarse loads jointly control deposition mobility; Shape adds hydraulic/thermal reshaping and Shape sharpness retains crisp interfluves.<br><br>For a Canyon, start with moderate Duration and Downcutting. Raise Erosion scale before Duration when you want wider ravines instead of noisy scratches. The bundled Canyon Landscape setup supplies a conservative starting point.<br><br><b>Soil depth</b> and <b>Sediment depth</b> are optional carried cover, in metres: wire them and erosion consumes loose cover first, cutting bedrock only where local cover has reached zero, while what the pass aggrades adds to the sediment layer — all co-updated with the height in the same pass. Leave them unwired and the node behaves exactly as before, on bare bedrock. The <b>Solid top / Bedrock height / Soil depth / Sediment depth / Sand depth</b> outputs are that stack in metres from a stable datum, and they close solidTop = bedrock + soil + sediment + sand. Sand is zero: no process here produces it.<br><br>What this node <b>cannot</b> tell you is stated rather than glossed. The deposit is measured from the height this node publishes, not carried out of the stages that made it, because the composition keeps no per-stage books — and two of its stages raise the surface without transporting anything: the seeded rock-resistance perturbation, which is always on, and Shape sharpness, whose gain is deliberately asymmetric. Both are inside the reported deposit and cannot be separated from it. The node therefore publishes <b>no boundary budget</b> of its own; where the composition reduces to a single hydraulic pass on the native grid it reports <b>that stage's</b> own exported and suspended volume, clearly scoped as the stage's, and everywhere else it declines and says which stage removed the claim."})
