// streampower — Fluvial incision — dh/dt = U − K·A^m·S. Drainage area makes valleys jo
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { toMetres } from '../../core/height-frame.js'
import { BUILD_QUALITY, cellSizeM, fieldH, fieldW, HEX_ROW, isHex, maskApply, newField, resScale,
  streamPowerErode, terrainDef } from '../../legacy.js'

// The adapter's frozen primary for this type (src/core/legacy-ports.js). ADR-002: "Display names
// and array positions are never identifiers" — a saved document's edges store this id, so it is a
// constant here rather than something recomputed from a descriptor list.
const PRIMARY_PORT = "out"

// ---- S3.5: the cover stack ---------------------------------------------------------------------
// Slot numbers are the adapter's `legacySlot` values, spelled here as constants for the same reason
// PRIMARY_PORT is. src/core/legacy-ports.js is where they are declared. Note the offset from
// thermal's 2/3: Stream Power's frozen row already owns slot 1 for Uplift.
const SLOT_UPLIFT = 1, SLOT_MASK = 2, SLOT_SOIL = 3, SLOT_SEDIMENT = 4
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
      throw new RangeError(`Stream power ${label} must be a finite non-negative depth in metres; `
        + `sample ${i} is ${v[i]}`)
    }
  }
  return v
}

// THE HEIGHT FRAME, stated rather than assumed. ADR-005 / D20: two named frames — the viewport
// keeps `display-autolevel`, and a PHYSICAL node takes metres from a stable datum through the
// explicit adapter. This one is physical. Under autolevel, incising a valley moves fieldMin/fieldMax,
// so bedrock nobody touched changes elevation and no conservation identity can close;
// frameDriftUnderLocalEdit measures that as 952.39 m of drift at untouched samples against 0.00 m
// here (src/core/height-frame.js:144). Same shape as src/plugins/ero/thermal.js:74 — deliberately
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
 * CONTRACT: incision consumes LOOSE COVER FIRST and cuts bedrock only where local cover has reached
 * zero. It DEPOSITS NOTHING — sprint-03:186 keeps this node detachment-limited and forbids inventing
 * a deposition field it does not model — so where the published surface RISES the cover thickness is
 * carried through untouched and the rise is itemised as `bedrockGainedM3`. All of it happens in this
 * one evaluation, alongside the height the node returns.
 *
 * WHY THE RISE GOES TO BEDROCK AND NOT TO SEDIMENT. Every term in this kernel that can raise a cell
 * acts on the ROCK COLUMN, not on a transported load:
 *   - the uplift source, `h[i] += Udt*uplift[i]` at every interior cell (src/legacy.js:2201-2202);
 *   - the implicit solve's floor, `if(h[i]<h[rec[i]])h[i]=h[rec[i]]` (:2213), which is the solver
 *     refusing to open a closed depression, not a deposit;
 *   - hillslope diffusion (:2215-2267), which in a detachment-limited landscape equation relaxes the
 *     bedrock interfluve between channels.
 * Crediting any of that to `sedimentDepth` would be exactly the invented deposition the sprint
 * forbids. Crediting it to bedrock is what `bedrockHeight = solidTop - cover` then does for free,
 * and `bedrockGainedM3` makes it a number a gate can read rather than an unstated side effect.
 *
 * WHY THIS IS AT NODE LEVEL AND NOT INSIDE THE KERNEL. The field the node PUBLISHES is not the
 * kernel's output in general: `maskApply` blends the result toward the input. The solid-stack
 * identity has to close against the field that is published, so the cover has to be partitioned from
 * THAT delta. (Stream Power runs no `atFeatureScale`, so the mask is the only transform — which is
 * why `transformedBy` below tests one condition where thermal tests two.)
 *
 * STACK ORDER. solidTop = bedrockHeight + soilDepth + sedimentDepth + sandDepth, bedrock at the
 * bottom, so incision strips from the TOP down: sand, then sediment, then soil, then bedrock.
 *
 * WHAT THIS DELIBERATELY DOES NOT DO: it does not make bedrock harder to incise than cover. Sprint 3
 * asks for transport ORDER ("loose cover first, bedrock second"); an erodibility K that differed
 * between regolith and rock is a physical law nobody has specified here, and inventing one would be
 * a fabricated constant. It is also why an unwired graph stays byte-identical.
 */
function coverPass(before, after, ins, uplift, lossSource) {
  const N = after.length, W = fieldW(), H = fieldH()
  const fr = physicalFrame(), relief = fr.reliefM
  const cellM = cellSizeM(), A = (isHex() ? HEX_ROW : 1) * cellM * cellM
  const soil0 = coverRaster(ins[SLOT_SOIL], N, "Soil depth")
  const sed0 = coverRaster(ins[SLOT_SEDIMENT], N, "Sediment depth")
  const soil = new Float32Array(N), sed = new Float32Array(N), sand = new Float32Array(N)
  // The delta is taken in the STABLE frame, where it is exactly (after-before)*relief: a difference
  // of two absolute elevations that share a datum. Under autolevel this subtraction would silently
  // include the frame's own motion.
  let consumedM = 0, detachedM = 0, gainedM = 0, minCoverM = Infinity, maxRiseM = -Infinity
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
      // DETACHMENT-LIMITED. There is no branch here that adds to any cover layer, and that absence
      // is the whole of the contract: the carried thicknesses pass through unchanged and the rise is
      // booked against the rock column. `maxCoverRiseM` below is what makes it MEASURED rather than
      // asserted — a later edit that quietly started depositing would show up as a positive number.
      sand[i] = a0; sed[i] = d0; soil[i] = s0
      gainedM += dM
    }
    const c1 = sand[i] + sed[i] + soil[i], c0 = a0 + d0 + s0
    if (c1 < minCoverM) minCoverM = c1
    if (c1 - c0 > maxRiseM) maxRiseM = c1 - c0
  }
  const top = toMetres(after, fr)
  const bedrock = new Float32Array(N)
  for (let i = 0; i < N; i++) bedrock[i] = Math.fround(top[i] - (soil[i] + sed[i] + sand[i]))
  const ledger = {
    coverConsumedM3: consumedM * A, bedrockDetachedM3: detachedM * A,
    // A NAMED PHYSICAL ZERO, and not a residual of anything. This node models no deposition, so the
    // honest published figure is the constant 0 — and it is a claim a gate can FAIL, because the
    // published `sedimentDepth` raster is read back and any cell whose cover rose contradicts it.
    depositedM3: 0, depositionModelled: false,
    // The positive part of the published delta, ITEMISED rather than folded into the terms above.
    // Booked against bedrock (see the block comment); reported so that a rise is visible instead of
    // silently vanishing into `bedrockHeight = solidTop - cover`.
    bedrockGainedM3: gainedM * A,
    cellAreaM2: A, lattice: terrainDef.lattice, rows: H, cols: W, cells: N,
    latticeArea: isHex() ? "hexRowPitch" : "square",
    frame: fr.frame, datumM: fr.datumM, reliefHeightM: relief,
    stackOrder: ["sandDepth", "sedimentDepth", "soilDepth", "bedrockHeight"],
    soilWired: !!soil0, sedimentWired: !!sed0,
    // THE SLOTS THIS CODE ACTUALLY INDEXED, reported so a descriptor that says one thing while the
    // evaluator reads another is visible instead of silent — a port declared and never filled is a
    // half-gate this sprint has already found repeatedly.
    soilSlot: SLOT_SOIL, sedimentSlot: SLOT_SEDIMENT, upliftSlot: SLOT_UPLIFT,
    minCoverAfterM: Number.isFinite(minCoverM) ? minCoverM : null,
    maxCoverRiseM: Number.isFinite(maxRiseM) ? maxRiseM : null,
    // THE BOUNDARY BUDGET IS NEVER CLAIMED, ON ANY PATH, AND THAT IS THE HONEST ANSWER.
    //
    // Thermal could publish a named physical zero because both its kernels omit off-grid neighbours,
    // so nothing can leave the domain. Stream Power's boundary is the opposite: the rim is FORCED to
    // base level before the loop and again after every iteration (src/legacy.js:2198 and :2269,
    // `for(let i=0;i<N;i++)if(isEdge[i])h[i]=0`), which removes whatever drained into it, and the
    // implicit incision step `h[i]=(h[i]+C*h[rec[i]])/(1+C)` (:2212) detaches material and credits it
    // to nobody — that IS what detachment-limited means. Neither quantity is accumulated anywhere in
    // the kernel, and this node cannot reconstruct either from the field it publishes.
    //
    // So it publishes NO NUMBER. `exportedOrSuspendedM3 = coverConsumed + bedrockDetached` would look
    // like a boundary budget and would be a restatement of the two terms it is compared against: a
    // closure that holds by construction for any implementation, including one that deletes the
    // terrain. That is the defect this suite keeps finding, and refusing it is the point.
    // What it WOULD take to claim one is stated in the note and in the oracle header: an accumulator
    // inside `streamPowerErode`, which lives in src/legacy.js.
    lossClaimed: false,
    lossSource,
  }
  // THE UPLIFT SOURCE TERM, itemised — the one budget line this node genuinely can support. It is
  // computed from the node's OWN INPUTS (the two parameters and the Uplift raster over the kernel's
  // interior), never from the published delta, which is what makes comparing it against the field a
  // measurement rather than an identity. See resolveUpliftSource.
  if (uplift && uplift.claimed) {
    ledger.upliftAppliedM3 = uplift.perColumnM * relief * A
    ledger.upliftInteriorCells = uplift.interiorCells
    ledger.upliftWired = uplift.upliftWired
  } else {
    ledger.upliftClaimed = false
  }
  ledger.upliftSource = uplift ? uplift.source : "unclaimed"
  return { top, bedrock, soil, sed, sand, ledger }
}

/** Put one coverPass result on a typed values map, under the declared port ids. */
function coverValues(values, c) {
  values.set("solidTop", c.top); values.set("bedrockHeight", c.bedrock)
  values.set("soilDepth", c.soil); values.set("sedimentDepth", c.sed); values.set("sandDepth", c.sand)
  return values
}

/**
 * The uplift the kernel added to the rock column, in normalised height summed over cells.
 *
 * MEASURED OFF THE KERNEL, not off the result. `streamPowerErode` applies uplift once per iteration
 * to every cell that is not on the rim — `if(uplift){...if(!isEdge[i])h[i]+=Udt*uplift[i];}` and
 * `else if(Udt){...if(!isEdge[i])h[i]+=Udt;}` (src/legacy.js:2201-2202) — with `isEdge` exactly the
 * border ring (:2196-2197). Nothing clamps or conditions it. So the total is
 *     Udt * iters * sum over the INTERIOR of (uplift ? uplift[i] : 1)
 * and every factor of that comes from this node's inputs. THE RIM EXCLUSION IS THE LOAD-BEARING
 * PART: counting the whole field instead of the interior overstates the source by the perimeter,
 * which at RES 64 is 252 of 4096 cells — 6.2%, a difference far larger than any float32 tolerance,
 * and `--mutate=uplift-counts-the-rim` is the control that proves the gate sees it.
 *
 * UNDER A MASK, NOTHING IS CLAIMED. `maskApply` blends the kernel's result toward the input, so the
 * uplift that reached the PUBLISHED field is some unrecorded fraction of what the kernel applied.
 * Publishing the kernel's figure against a field it no longer describes is the same error as
 * publishing a boundary budget for a field the kernel did not produce.
 */
function resolveUpliftSource(Udt, iters, upliftField, W, H, transformedBy) {
  if (transformedBy) return { claimed: false, source: transformedBy }
  const N = W * H
  if (upliftField && !(ArrayBuffer.isView(upliftField) && upliftField.length === N)) {
    return { claimed: false, source: "uplift-raster-length-mismatch" }
  }
  let sum = 0, cells = 0
  for (let y = 1; y < H - 1; y++) {
    for (let x = 1; x < W - 1; x++) {
      const u = upliftField ? upliftField[y * W + x] : 1
      if (!Number.isFinite(u)) return { claimed: false, source: "uplift-raster-non-finite" }
      sum += u; cells++
    }
  }
  // A degenerate grid with no interior is absence of evidence, not a zero source.
  if (cells === 0) return { claimed: false, source: "no-interior-cells" }
  return {
    claimed: true, source: upliftField ? "kernel-source-term-field" : "kernel-source-term-scalar",
    perColumnM: Udt * iters * sum, interiorCells: cells, upliftWired: !!upliftField,
  }
}

export default definePlugin({
  type: "streampower",
cat:"ero",name:"Stream power",
    // `ins` must stay label-for-label equal to the adapter's row: LEGACY_INS_LABELS is derived from
    // src/core/legacy-ports.js and _verify_port_contract.js's `insDrift` anchor compares the two.
    ins:["In","Uplift","Mask","Soil depth","Sediment depth"],
    desc:"Fluvial incision — dh/dt = U − K·A^m·S. Drainage area makes valleys join into a tree and deepen downstream, so ridges emerge as what is left between them. This is the process that organises a landscape, not a texture applied to one.",
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
      // carried thickness in, CONSUMES from it where it incises, and never adds to it.
      {id:"sedimentDepth",name:"Sediment depth",kind:"scalarRaster",storage:"R32F",components:1,
        semantic:"sedimentDepth",unit:"m",lens:"state"},
      // ADR-005: the identity never omits the term. Nothing in the pipeline produces sand yet (S7.3
      // owns the aeolian process), so there is no sandDepth INPUT to carry either, and this port is
      // MEASURED zero rather than asserted zero — _verify_streampower_coevolution.js reads the raster.
      {id:"sandDepth",name:"Sand depth",kind:"scalarRaster",storage:"R32F",components:1,
        semantic:"sandDepth",unit:"m",lens:"state"},
    ],
    // Incision default halved from 0.15: Kdt = strength*2, and 0.3 marches every cell 23% toward
    // its receiver per iteration - at shipped iteration counts that removed 57-62% of a mountain's
    // relief out of the box. 0.08 still carves a connected network (gated) while defaults keep most
    // relief, which is the Gaea-baseline contract for an out-of-the-box erosion node.
    params:[P.slider("strength","Incision",0,1,0.08,0.01),
      P.slider("m","Area exponent",0.2,0.8,0.5,0.01),
      P.int("iters","Iterations",1,60,14),
      // Default RAISED from 0: with no uplift the implicit solve is pure decay toward base level
      // and the shipped defaults removed 62% of a mountain in 14 iterations - a destructive
      // out-of-the-box setting. 0.35 balances incision so defaults CARVE drainage while keeping
      // most relief (the equilibrium-landscape regime the solver exists for). Uplift 0 remains
      // available and documented as the erode-to-baselevel mode.
      P.slider("uplift","Uplift",0,1,0.35,0.01),
      P.slider("hillslope","Hillslope",0,1,0.9,0.01)],
    // Res Lock mapping (k = RES/REF_RES): the solver's length scales live in cells, so the
    // slider->physical mapping is where world units get restored. Iterations do NOT scale:
    // this is the Braun-Willett implicit cascade - receivers are solved before donors in one
    // ordered sweep, so a base-level signal crosses the whole network in a single iteration and
    // the "one cell per iteration" travel intuition is false for this kernel (K's per-cell decay
    // is real - which is exactly why K needs boosting beyond the steady-state exponent). The
    // steady-state theory alone (K*k^(1-2m), U fixed) under-erodes the 14-iteration TRANSIENT
    // the shipped defaults run, so K carries a CALIBRATED exponent, fitted by sweep over m in
    // {.2,.5,.8} x k in {2,3} on the reference input (phi*(m) ~ 1.018m - 1.198, re-fitted after
    // the diffusion substep bound moved the m=0.8 root - the calibration harness
    // _verify_streampower_calibration.js re-derives the roots live and gates the line) and gated
    // across m and k by _verify_erosion_gridscale.js. Calibration, not derivation - stated as
    // such. Uplift is untouched (same iterations = same total). Incision cost is resolution-
    // independent (iterations unchanged); the diffusion DOSE k^2 is the one k-growing cost term
    // (k^4 total Laplacian work - measured 41.6 s of diffusion at 2048 square Final), so the
    // DOSE takes the Interactive tier cap of 2 and Final pays it in full.
    eval:(p,ins,node,ctx)=>{if(!ins[0])return newField();const k=resScale();
      const kd=BUILD_QUALITY==="final"?k:Math.min(k,2);
      // Hoisted out of the call so the ledger's uplift term is computed from THE SAME expression the
      // kernel was handed, rather than from a second copy of it that could drift.
      const Udt=p.uplift*0.004;
      const result=maskApply(ins[0],streamPowerErode(ins[0],
      {Kdt:p.strength*2.0*Math.pow(k,1.198-1.018*p.m), Udt, m:p.m,
       iters:p.iters,
       uplift:ins[SLOT_UPLIFT]||null, Ddt:p.hillslope*0.24*kd*kd}),ins[SLOT_MASK]);

      // DEMAND, and why the rule is not normals.js's. normals treats an ABSENT ctx as "compute
      // everything", which is right for a node whose vector port shipped WITH its digest baseline.
      // Stream Power is an existing node: _verify_digest.js calls def.eval(params, ins, nd) with no
      // ctx and folds every declared output of a TYPED return into that type's digest string, so "no
      // ctx means compute" would move a baseline. No demand therefore means no state, and the return
      // stays the bare Float32Array it has always been — which is also the only shape under which an
      // undemanded output genuinely costs nothing.
      const demanded=ctx&&ctx.demanded;
      if(!(demanded&&COVER_OUTPUTS.some(id=>demanded.has(id))))return result;

      // ---- S3.5: the cover co-update, in this same evaluation ----------------------------------
      // Driven by the delta of the field this node PUBLISHES (result vs ins[0]), not by the kernel's
      // own output: `maskApply` stands between the two, and it is the published solid top the stack
      // identity has to close against.
      //
      // `transformedBy` is a STRING so the ledger can say WHY a claim was declined rather than only
      // that it was. maskApply returns the kernel's field unchanged for a null mask
      // (src/legacy.js:460), so the null test here is exactly the condition under which the
      // published field IS the kernel's own output. Stream Power runs no `atFeatureScale`, so unlike
      // thermal there is no second transform to test for.
      const transformedBy=ins[SLOT_MASK]?"mask-composite":null;
      const c=coverPass(ins[0],result,ins,
        resolveUpliftSource(Udt,p.iters,ins[SLOT_UPLIFT]||null,fieldW(),fieldH(),transformedBy),
        // The boundary budget is unavailable for a KERNEL reason, not a transform reason, so it says
        // so on every path — a mask does not make an uninstrumented rim any less uninstrumented.
        "open-base-level-boundary-not-itemised");
      // The ledger travels on the typed return rather than on a module global, which would go stale
      // the moment a second streampower node evaluated. `values` is the only key the evaluator reads
      // (src/legacy.js:3232).
      return{values:coverValues(new Map([[PRIMARY_PORT,result]]),c),ledger:c.ledger};},
    note:"Edges are held at <b>base level</b> — without a fixed outlet there is nothing to incise toward, so relief cannot organise at all.<br><br><b>Uplift 0 will erode your terrain away.</b> That is not a bug, it is what rivers do to a landmass that stops rising: measured on a Mountain, peak height goes 0.69 → 0.53 → 0.20 → 0.000 as Incision rises with Uplift at 0. Keep Incision and Iterations low to carve, or raise <b>Uplift</b> so the interior keeps rising while the rivers cut — that balance is what holds a real range up, and it is the regime where slope and area settle to S ∝ A<sup>−m</sup>.<br><br>Wire a field into the <b>Uplift</b> input and it scales the uplift rate per cell. That is the node's real use: feed a broad high region in (a Mountain, a Layout, a Shape) and let the rivers carve it, so summits and ridges emerge as <i>residue between the valleys</i> instead of being authored. A mountain is what erosion leaves behind.<br><br><b>Hillslope</b> is the diffusion term of the same equation, and it is what stops the ridges becoming razor blades: stream power sharpens interfluves without limit, diffusion relaxes them and gives hillslopes a length and valleys a width. At 0 you get blades.<br><br>The shipped defaults are set against <b>real SRTM data</b>, not by eye: driven by a Tectonic uplift they reproduce a real tile's slope distribution to within about one unit at every percentile (p90 9.9 vs 9.3, p99 16.0 vs 15.7, max 24.2 vs 22.8).<br><br><b>Soil depth</b> and <b>Sediment depth</b> are optional carried cover, in metres: wire them and incision consumes loose cover first, cutting bedrock only where local cover has reached zero — co-updated with the height in the same pass. Leave them unwired and the node behaves exactly as before, on bare bedrock. This node stays <b>detachment-limited</b>: it never adds to the cover layers, because it models no deposition and inventing one would be inventing physics. Where the surface rises — uplift, or diffusion relaxing an interfluve — that is the rock column, and it is reported as a bedrock gain. The <b>Solid top / Bedrock height / Soil depth / Sediment depth / Sand depth</b> outputs are that stack in metres from a stable datum, and they close solidTop = bedrock + soil + sediment + sand. Sand is zero: no process here produces it. The node reports the <b>uplift it applied</b> as an itemised source term, but publishes <b>no boundary budget</b>: the rim is forced to base level every iteration and detached material is credited to nobody, and neither quantity is accumulated by the solver — so rather than publish a figure it cannot support, it declines and says why."})
