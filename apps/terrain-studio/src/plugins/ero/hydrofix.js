// hydrofix — Low-amplitude drainage conditioning: promotes longer continuous flow paths without replaci
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P, GROUP } from '../../core/params.js'
import { toMetres } from '../../core/height-frame.js'
import { cellSizeM, fieldH, fieldW, HEX_ROW, hydroFixField, isHex, maskApply, newField,
  terrainDef } from '../../legacy.js'

// The adapter's frozen primary for this type (src/core/legacy-ports.js). ADR-002: "Display names
// and array positions are never identifiers" — a saved document's edges store this id, so it is a
// constant here rather than something recomputed from a descriptor list.
const PRIMARY_PORT = "out"

// ---- S3.5: the cover stack ---------------------------------------------------------------------
// Slot numbers are the adapter's `legacySlot` values, spelled here as constants for the same reason
// PRIMARY_PORT is. src/core/legacy-ports.js is where they are declared. These are erosion2's
// numbers, not stream power's: this row's frozen head is In/Mask with no Uplift to work around.
const SLOT_MASK = 1, SLOT_SOIL = 2, SLOT_SEDIMENT = 3
// The outputs whose demand turns the cover co-update on. Demanding none of them costs nothing: the
// node returns the bare Float32Array it always has, which is what keeps an unwired graph and
// _verify_digest.js's no-ctx evaluation byte-identical to the pre-S3.5 build.
const COVER_OUTPUTS = ["solidTop", "bedrockHeight", "soilDepth", "sedimentDepth", "sandDepth"]

const clamp01 = x => (x < 0 ? 0 : x > 1 ? 1 : x)

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
      throw new RangeError(`HydroFix ${label} must be a finite non-negative depth in metres; `
        + `sample ${i} is ${v[i]}`)
    }
  }
  return v
}

// THE HEIGHT FRAME, stated rather than assumed. ADR-005 / D20: two named frames — the viewport
// keeps `display-autolevel`, and a PHYSICAL node takes metres from a stable datum through the
// explicit adapter. This one is physical. Under autolevel, carving a spillway moves fieldMin/fieldMax,
// so bedrock nobody touched changes elevation and no conservation identity can close;
// frameDriftUnderLocalEdit measures that as 952.39 m of drift at untouched samples against 0.00 m
// here (src/core/height-frame.js:144). Same shape as src/plugins/ero/streampower.js:54 —
// deliberately duplicated rather than shared, because the only thing to share is a read of
// `terrainDef`, and a plugin importing another plugin's internals is what `npm run plugins:check`
// exists to refuse.
const physicalFrame = () => ({
  frame: "physical-stable",
  datumM: Number.isFinite(terrainDef.baseElevation) ? terrainDef.baseElevation : 0,
  reliefM: terrainDef.height || 1,
})

/**
 * The cover co-update, and the physical-volume ledger for it.
 *
 * WHAT THE KERNEL DOES, MEASURED — this is the evidence that settles the S3.5 classification dispute
 * and it is stated here because every contract below follows from it. `hydroFixField`
 * (src/legacy.js:3119-3158) is MONOTONE NON-INCREASING. It has exactly two write paths and neither
 * can raise a cell:
 *   - the corridor downcut, `out[i] -= mask[i]*cut` (:3153), with mask in [0,1] and
 *     cut = relief*(.0003+.0072*downcut)*fix >= 0;
 *   - the descent enforcement, `if(out[r]>target) out[r]=target` (:3155-3156), which lowers a
 *     receiver to just under its donor and never the reverse.
 * The priority-flood fill at :3120 DOES raise — it raised 907 of 4096 cells on the measured square
 * fixture — but it is applied to `filled`, a WORKING COPY used only to derive receivers and flow
 * accumulation. Not one of those raises reaches the published field. Measured over 12 runs (square
 * and hex, pitted and ramp fixtures, fix at 0/.52/1): risen cells 0, max rise 0.000000, on every
 * single one.
 *
 * SO THIS NODE TRANSPORTS NOTHING AND STILL CHANGES A VOLUME. No cell anywhere receives material;
 * the total strictly decreases. That is why the manifest classifies it `latticeConditioning` and why
 * sprint-03:28's placement of it among the transport nodes is wrong — but sprint-03:190 is right
 * that it "may not silently discard carved bedrock", because what it carves through is the cover
 * stack.
 *
 * CONTRACT: the carve consumes LOOSE COVER FIRST and reaches bedrock only where local cover has
 * reached zero. It DEPOSITS NOTHING — there is no additive term in the kernel at all — so
 * `depositedM3` is a published constant zero and no cell's cover thickness may rise. All of it
 * happens in this one evaluation, alongside the height the node returns.
 *
 * THE RISE BRANCH IS NOT DEAD CODE AND MUST NOT BE OPTIMISED AWAY. The kernel cannot raise, but this
 * function does not ASSUME that — it measures `maxPublishedRiseM` over every sample and carries the
 * cover through untouched where a rise appears. That is what turns "hydrofix transports nothing"
 * from a claim in a comment into a reading a gate can fail: an edit that started depositing would
 * show up as a positive number here.
 *
 * WHY THIS IS AT NODE LEVEL AND NOT INSIDE THE KERNEL. The field the node PUBLISHES is not the
 * kernel's output in general: `maskApply` blends the result toward the input. The solid-stack
 * identity has to close against the field that is published, so the cover has to be partitioned from
 * THAT delta. (`maskApply` returns the kernel's array by reference for a null mask,
 * src/legacy.js:458, which is why the null test below is exactly "the published field IS the
 * kernel's own output".)
 *
 * STACK ORDER. solidTop = bedrockHeight + soilDepth + sedimentDepth + sandDepth, bedrock at the
 * bottom, so a carve strips from the TOP down: sand, then sediment, then soil, then bedrock.
 *
 * WHAT THIS DELIBERATELY DOES NOT DO: it does not make bedrock harder to breach than cover. Sprint 3
 * asks for consumption ORDER ("loose cover first, bedrock second"); a resistance that differed
 * between regolith and rock is a physical law nobody has specified here, and inventing one would be
 * a fabricated constant. It is also why an unwired graph stays byte-identical.
 */
function coverPass(before, after, ins, softCut) {
  const N = after.length, W = fieldW(), H = fieldH()
  const fr = physicalFrame(), relief = fr.reliefM
  const cellM = cellSizeM(), A = (isHex() ? HEX_ROW : 1) * cellM * cellM
  const soil0 = coverRaster(ins[SLOT_SOIL], N, "Soil depth")
  const sed0 = coverRaster(ins[SLOT_SEDIMENT], N, "Sediment depth")
  const soil = new Float32Array(N), sed = new Float32Array(N), sand = new Float32Array(N)
  // The delta is taken in the STABLE frame, where it is exactly (after-before)*relief: a difference
  // of two absolute elevations that share a datum. Under autolevel this subtraction would silently
  // include the frame's own motion.
  let consumedM = 0, carvedM = 0, risenM = 0, risenCells = 0, loweredCells = 0
  let minCoverM = Infinity, maxRiseM = -Infinity, maxCoverRiseM = -Infinity, maxLoweringM = 0
  for (let i = 0; i < N; i++) {
    const s0 = soil0 ? soil0[i] : 0, d0 = sed0 ? sed0[i] : 0, a0 = 0
    const dM = (after[i] - before[i]) * relief
    if (dM > maxRiseM) maxRiseM = dM
    if (dM < 0) {
      loweredCells++
      if (-dM > maxLoweringM) maxLoweringM = -dM
      let e = -dM
      // Strip from the top of the stack down. `take <= available` by construction, so where local
      // cover survives the pass `e` reaches zero and bedrockCarved picks up EXACTLY 0 — not a small
      // number that a tolerance would have to forgive.
      const ta = a0 < e ? a0 : e; e -= ta
      const td = d0 < e ? d0 : e; e -= td
      const ts = s0 < e ? s0 : e; e -= ts
      const a1 = Math.fround(a0 - ta), d1 = Math.fround(d0 - td), s1 = Math.fround(s0 - ts)
      sand[i] = a1; sed[i] = d1; soil[i] = s1
      // Accumulated from the values that are PUBLISHED, so the ledger is the integral of the
      // rasters rather than a parallel double-precision reckoning of them.
      consumedM += (a0 - a1) + (d0 - d1) + (s0 - s1)
      carvedM += e
    } else {
      // THE BRANCH THE KERNEL NEVER TAKES, kept so that the claim is measured rather than assumed.
      // There is no term here that adds to any cover layer — hydrofix models no deposition, because
      // it has no additive term at all — so a carried thickness passes through unchanged and any
      // rise is itemised separately in `publishedRiseM3`.
      sand[i] = a0; sed[i] = d0; soil[i] = s0
      if (dM > 0) { risenCells++; risenM += dM }
    }
    const c1 = sand[i] + sed[i] + soil[i], c0 = a0 + d0 + s0
    if (c1 < minCoverM) minCoverM = c1
    if (c1 - c0 > maxCoverRiseM) maxCoverRiseM = c1 - c0
  }
  const top = toMetres(after, fr)
  const bedrock = new Float32Array(N)
  for (let i = 0; i < N; i++) bedrock[i] = Math.fround(top[i] - (soil[i] + sed[i] + sand[i]))
  const ledger = {
    // THE CONDITIONING DELTA, ITEMISED BY THE LAYER IT CAME OUT OF — sprint-03:190's "removed
    // volume", in the only decomposition this node can support without restating itself. The two
    // terms are accumulated independently: `coverConsumedM3` from the published cover rasters,
    // `bedrockCarvedM3` from what is left of the carve after local cover is exhausted.
    coverConsumedM3: consumedM * A, bedrockCarvedM3: carvedM * A,
    // A NAMED PHYSICAL ZERO, and not a residual of anything. The kernel has no additive term on any
    // path, so the honest published figure is the constant 0 — and it is a claim a gate can FAIL,
    // because the published cover rasters are read back and any cell whose cover rose contradicts it.
    depositedM3: 0, depositionModelled: false,
    // THE MONOTONICITY READING — the claim that makes "conditions without transporting" a
    // measurement. The kernel's two write paths can only lower, so the positive part of the
    // published delta must be empty; these are its integral, its count, and its extremum, each
    // accumulated separately over every sample rather than inferred from the others.
    publishedRiseM3: risenM * A, risenCells, maxPublishedRiseM: maxRiseM,
    // ...and the negative part's SHAPE. Order statistics and a count, deliberately not a sum: the
    // total lowered volume IS coverConsumed + bedrockCarved by construction, so publishing it as a
    // third figure would be a restatement of the two terms it would be checked against.
    loweredCells, maxLoweringM,
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
    maxCoverRiseM: Number.isFinite(maxCoverRiseM) ? maxCoverRiseM : null,
    // THE EXPORT BUDGET IS NEVER CLAIMED, ON ANY PATH, AND THAT IS THE HONEST ANSWER.
    //
    // Everything this node removes leaves the domain: nothing is deposited anywhere, so the carved
    // material is discarded outright. It is still not a publishable figure, because the only number
    // available is `coverConsumedM3 + bedrockCarvedM3` — a restatement of the two terms it would then
    // be checked against, and a closure that holds by construction for any implementation at all,
    // including one that deletes the terrain. That is the defect this suite keeps finding, and
    // refusing it is the point. `hydroFixField` accumulates nothing: neither :3153's subtraction nor
    // :3155-3156's enforcement keeps a running total, and this node cannot reconstruct one from the
    // field it publishes. What it WOULD take to claim one is an accumulator inside the kernel, which
    // lives in src/legacy.js and has a single serial owner.
    lossClaimed: false,
    lossSource: "carved-volume-is-discarded-and-not-accumulated-by-the-kernel",
    // AND NEITHER IS THE MECHANISM SPLIT, for the same reason and with a measured consequence. The
    // conditioning delta is the sum of two physically different operations — a soft corridor downcut
    // spread over a blurred channel band, and a one-cell-wide breach that enforces descent — and
    // separating them needs two accumulators inside the kernel. They are NOT the same size: the
    // measured maximum lowering runs 30x to 270x the corridor downcut's own per-cell ceiling across
    // the fixture set, so a split that reported the downcut term as the whole story would be wrong by
    // that factor. Publishing a fabricated split would hide exactly that.
    mechanismSplitClaimed: false,
    mechanismSplitSource: "downcut-and-breach-not-accumulated-separately-by-the-kernel",
  }
  // THE CORRIDOR DOWNCUT'S PER-CELL CEILING, itemised — the one budget line this node genuinely can
  // support, and the analogue of Stream Power's uplift source term. It is computed from the node's
  // OWN INPUTS (the two parameters and the range of the input field), never from the published
  // delta, which is what makes comparing it against the field a measurement rather than an identity.
  // See resolveSoftCutSource.
  if (softCut && softCut.claimed) {
    ledger.softCutCeilingM = softCut.ceilingNorm * relief
    ledger.softCutReliefNorm = softCut.reliefNorm
    ledger.softCutFix = softCut.fix
    ledger.softCutDowncut = softCut.downcut
    ledger.bypass = softCut.bypass
  } else {
    ledger.softCutClaimed = false
  }
  ledger.softCutSource = softCut ? softCut.source : "unclaimed"
  return { top, bedrock, soil, sed, sand, ledger }
}

/** Put one coverPass result on a typed values map, under the declared port ids. */
function coverValues(values, c) {
  values.set("solidTop", c.top); values.set("bedrockHeight", c.bedrock)
  values.set("soilDepth", c.soil); values.set("sedimentDepth", c.sed); values.set("sandDepth", c.sand)
  return values
}

/**
 * The per-cell ceiling of the corridor downcut term, in normalised height.
 *
 * MEASURED OFF THE KERNEL, not off the result. `hydroFixField` computes
 *     relief = max(fieldRange(inp)[1] - fieldRange(inp)[0], 1e-5)
 *     cut    = relief * (.0003 + .0072*downcut) * fix                      (src/legacy.js:3152)
 * and applies `out[i] -= mask[i]*cut` with the blurred channel mask in [0,1] (:3153). So `cut` is
 * the largest lowering the downcut term alone can inflict on any single cell, and every factor of it
 * comes from this node's inputs. THE `fix` FACTOR IS THE LOAD-BEARING PART: it multiplies the whole
 * expression, so at the shipped default of .52 an implementation that dropped it would overstate the
 * ceiling by 1/.52 = 1.92x — `--mutate=softcut-ceiling-ignores-fix` is the control that proves the
 * gate sees it.
 *
 * fix <= 0 IS AN EXACT BYPASS AND IS REPORTED AS ONE. The kernel returns `inp.slice()` at :3139
 * before computing anything, so the ceiling is a true zero rather than a small number, and the whole
 * published delta is empty. That is a claim a gate can fail in both directions.
 *
 * UNDER A MASK, NOTHING IS CLAIMED. `maskApply` blends the kernel's result toward the input, so the
 * downcut that reached the PUBLISHED field is some unrecorded fraction of the kernel's ceiling.
 * Publishing the kernel's figure against a field it no longer describes is the same error as
 * publishing an export budget for material the kernel never counted.
 */
function resolveSoftCutSource(p, inp, transformedBy) {
  if (transformedBy) return { claimed: false, source: transformedBy }
  const fix = clamp01(p.fix), down = clamp01(p.downcut)
  if (!(fix > 0)) {
    return { claimed: true, source: "kernel-exact-bypass", ceilingNorm: 0, reliefNorm: 0,
      fix: 0, downcut: down, bypass: true }
  }
  // The kernel's own `relief`, recomputed here rather than read back: a plain min/max matches
  // `fieldRange` (src/legacy.js:218) for any field inside its +-1e9 sentinels, and the 1e-5 floor is
  // :3152's.
  let mn = Infinity, mx = -Infinity
  for (let i = 0; i < inp.length; i++) {
    const v = inp[i]
    if (!Number.isFinite(v)) return { claimed: false, source: "input-raster-non-finite" }
    if (v < mn) mn = v
    if (v > mx) mx = v
  }
  if (!Number.isFinite(mn)) return { claimed: false, source: "empty-input-raster" }
  const reliefNorm = Math.max(mx - mn, 1e-5)
  return { claimed: true, source: "kernel-corridor-downcut-ceiling",
    ceilingNorm: reliefNorm * (0.0003 + 0.0072 * down) * fix,
    reliefNorm, fix, downcut: down, bypass: false }
}

export default definePlugin({
  type: "hydrofix",
cat:"ero",name:"HydroFix",
    // `ins` must stay label-for-label equal to the adapter's row: LEGACY_INS_LABELS is derived from
    // src/core/legacy-ports.js and _verify_port_contract.js's `insDrift` anchor compares the two.
    ins:["In","Mask","Soil depth","Sediment depth"],
    desc:"Low-amplitude drainage conditioning: promotes longer continuous flow paths without replacing the landscape.",
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
      // carried thickness in, CONSUMES from it where it carves, and never adds to it.
      {id:"sedimentDepth",name:"Sediment depth",kind:"scalarRaster",storage:"R32F",components:1,
        semantic:"sedimentDepth",unit:"m",lens:"state"},
      // ADR-005: the identity never omits the term. Nothing in the pipeline produces sand yet (S7.3
      // owns the aeolian process), so there is no sandDepth INPUT to carry either, and this port is
      // MEASURED zero rather than asserted zero — _verify_hydrofix_coevolution.js reads the raster.
      {id:"sandDepth",name:"Sand depth",kind:"scalarRaster",storage:"R32F",components:1,
        semantic:"sandDepth",unit:"m",lens:"state"},
    ],
    params:[GROUP(P.slider("fix","Hydro fix",0,1,.52,.01),"Drainage"),
      GROUP(P.slider("downcut","Downcutting",0,1,.34,.01),"Drainage")],
    eval:(p,ins,node,ctx)=>{if(!ins[0])return newField();
      const result=maskApply(ins[0],hydroFixField(ins[0],p),ins[SLOT_MASK]);

      // DEMAND, and why the rule is not normals.js's. normals treats an ABSENT ctx as "compute
      // everything", which is right for a node whose vector port shipped WITH its digest baseline.
      // HydroFix is an existing node: _verify_digest.js calls def.eval(params, ins, nd) with no ctx
      // and folds every declared output of a TYPED return into that type's digest string, so "no ctx
      // means compute" would move a baseline. No demand therefore means no state, and the return
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
      // (src/legacy.js:458), so the null test here is exactly the condition under which the
      // published field IS the kernel's own output. HydroFix runs no `atFeatureScale`, so unlike
      // thermal there is no second transform to test for.
      const transformedBy=ins[SLOT_MASK]?"mask-composite":null;
      const c=coverPass(ins[0],result,ins,resolveSoftCutSource(p,ins[0],transformedBy));
      // The ledger travels on the typed return rather than on a module global, which would go stale
      // the moment a second hydrofix node evaluated. `values` is the only key the evaluator reads
      // (src/legacy.js:3232).
      return{values:coverValues(new Map([[PRIMARY_PORT,result]]),c),ledger:c.ledger};},
    note:"<b>HydroFix</b> routes on a priority-filled working copy, softly downcuts high-accumulation corridors in the original heightfield, and enforces only the tiny descent required for connected receivers. It is intentionally subtle: use it after Erosion 2 to repair broken flow paths, or before a flow-dependent node to prepare noisy terrain. It does not fill the rendered terrain or turn basins into flat plates.<br><br>It <b>only ever cuts down</b>. The priority-flood fill it routes on raises sinks, but that is a working copy — measured across both lattices and every slider setting, not one cell of the published terrain is ever raised. So HydroFix moves no material anywhere: it <i>removes</i> a small volume and that volume leaves the world. <b>Hydro fix</b> at 0 is an exact bypass, byte for byte.<br><br><b>Soil depth</b> and <b>Sediment depth</b> are optional carried cover, in metres: wire them and the carve consumes loose cover first, reaching bedrock only where local cover has run out — co-updated with the height in the same pass. Leave them unwired and the node behaves exactly as before, on bare bedrock. The <b>Solid top / Bedrock height / Soil depth / Sediment depth / Sand depth</b> outputs are that stack in metres from a stable datum, and they close solidTop = bedrock + soil + sediment + sand. Sand is zero: no process here produces it. The node reports the <b>corridor downcut ceiling</b> it applied as an itemised source term, but publishes <b>no export budget</b> and <b>no split between its two mechanisms</b>: the kernel accumulates neither, and rather than print a figure that would merely restate the terms it was checked against, it declines and says why."})
