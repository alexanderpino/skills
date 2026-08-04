// R0 transport classification manifest — the Sprint 3 precondition for S3.5.
//
// Pure and DOM-free; no legacy.js import, no registry import. It takes a list of height-writing
// node types (production's authority for that list is `HEIGHT_WRITERS` in ./doctrine.js) and
// answers one question: is every node that rewrites the surface reviewed, and does every node that
// claims to MOVE MATERIAL say which auxiliary state it must co-update?
//
// WHY THIS FILE EXISTS BEFORE THE WORK IT GOVERNS
// -----------------------------------------------
// `docs/plan/sprint-03-cover-layer.md:200` makes S3.5's acceptance "the final exemption ledger
// contains no material-transport entry". Measured on 2026-07-30, no such ledger existed anywhere in
// the tree: `grep -rniE "ownerSprint|exemptionLedger|EXEMPTION" src/ tests/ scripts/ index.html`
// returned only `_verify_shapescan.js`'s unrelated square-shape markers and four "NOTE (converted,
// not an exemption)" comments in legacy.js. An empty search over a structure that does not exist is
// green on day one and green forever — the vacuous gate this project keeps rediscovering. So the
// ledger is built FIRST, populated with the four debts that genuinely exist, and S3.5 is then
// measured by the ledger SHRINKING from 4 to 0 rather than by a grep finding nothing.
//
// THE RED BASELINE IS DATA, NOT ABSENCE
// -------------------------------------
// Every `materialTransport` row shipped `compliant: false`. That was not a placeholder: at the time
// none of the four transport nodes co-updated any cover state, because no cover state existed yet
// (see `DOCTRINE_STAGES.hydraulicCoEvolution` in ./doctrine.js — armed in S3, reason "no cover state
// to co-update yet"). S3.5 flips these to `true` one node at a time, and each flip is a measured
// before/after with the exemption ledger one entry shorter.
//
// POSITION, measured 2026-08-04: 4 of 4 compliant, and THE EXEMPTION LEDGER IS EMPTY. It went
// 4 -> 3 -> 2 -> 1 -> 0, one node per commit by explicit decision (D21: each commit's digest delta
// names that node and nothing else — and not one of the four needed a re-bless at all, because the
// cover work is demand-gated and the published field never moved). The last row to flip was
// `hydraulic`, whose cover-first consumption had shipped in S3.3 and been gated by
// _verify_cover_erosion.js since; only the ledger reading was outstanding, and it was held back to
// its own commit because a commit that moved two rows could not say which change moved which gate.
//
// AN EMPTY LEDGER IS THE VACUOUS-SEARCH SHAPE, AND THAT IS WHY THE EMPTINESS IS ARMED. S3.5's
// acceptance is "the final exemption ledger contains no material-transport entry", and this file
// exists because that clause was originally an empty grep over a structure nobody had built. Now
// that the list has genuinely reached zero the same hazard returns in a new form — a `ledger.length
// === 0` assertion is also true of a function that can no longer produce entries at all. So
// `_verify_transport_coevolution.js` keeps `transport-drops-compliance` and gains
// `hydraulic-drops-compliance`: either one makes `exemptionLedger` emit a real row again, from a
// different end of the manifest, which is what proves the zero is a reading. The control that used
// to push a row the other way, `transport-claims-compliant`, is RETIRED rather than repointed —
// with no exempt row left there is nothing for it to flip that production does not already hold,
// and a control that assigns the value production already has is a no-op reading as coverage.
//
// `coUpdates` IS A DELIVERED CLAIM, NOT A STATEMENT OF INTENT. Until S3.5c nothing anywhere
// checked that a row's co-update targets were things the node can actually publish, so a
// `compliant: true` row naming a map the node never produces would have read as coverage — the
// declared-but-never-filled half-gate, in manifest form. `_verify_transport_coevolution.js`'s
// `compliantRowsDeliverTheirCoUpdates` closes that: every target of a COMPLIANT row must be a
// declared output port semantic on that node's registered type. It removed `wetness` from the
// `erosion2` row in S3.5c and from the `hydraulic` row here — the second time on measured evidence
// about the field itself rather than on its absence, which the row records in full.
//
// S3.5e — THE LAST DISPUTED ROW, AND THE ONE THAT IS NOT A MOVER. `hydrofix` shipped
// `compliant: null` with an empty co-update list and a DISPUTED note, because the R0 review and
// sprint-03:28 disagreed about whether it transports. The kernel settles it: it does not. But it
// carves, so it changes the cover stack anyway, and its row now names the two targets it delivers.
// That made `hydrofix` the FIRST non-transport row to carry co-update targets, which is why both
// `coUpdateTargets` below and the oracle's delivery check widened from "transport rows" to "every
// row that names targets" — under the old scope this row's claims would have been invisible to the
// gates that grade them.
//
// CLASSES
// -------
// `materialTransport`    moves material, and therefore MUST co-update the auxiliary maps its
//                        process touches. All four rows resolved to `soilDepth` + `sedimentDepth`:
//                        the solid stack is what these kernels move. `wetness` was on two of them
//                        as an aspiration and is on neither now — see the `hydraulic` row for the
//                        measurement that settled it.
// `latticeConditioning`  conditions the lattice without transporting material.
// `surfaceExpression`    expresses authored surface detail.
// `generator`            creates height with nothing upstream.
//
// THE CLASS AND THE CO-UPDATE LIST ARE TWO DIFFERENT QUESTIONS, and S3.5e is where that stopped
// being a distinction without a difference. `class` answers "does this node MOVE material";
// `coUpdates` answers "does it change state somebody else owns". `hydrofix` answers NO to the first
// and YES to the second — it carves, so material leaves the cover stack, but nothing anywhere
// receives it. Its row therefore stays `latticeConditioning` and still names
// `soilDepth` + `sedimentDepth`. Only the `materialTransport` rows are REQUIRED to name targets
// (TRANSPORT_WITHOUT_COUPDATE); a row of any class that names them is graded on delivering them.
//
// A NOTE ON THE TAXONOMY vs THE SPRINT TEXT
// -----------------------------------------
// `sprint-03-cover-layer.md:62` and `:197` name only THREE buckets — "generator, surface expression,
// or material transport". `latticeConditioning` is a fourth, added by the R0 review for `hydrofix`,
// which the sprint's S3.5 story row (`:28`) instead lists among the transport nodes to migrate.
//
// THAT DISPUTE IS NOW SETTLED, ON THE KERNEL RATHER THAN ON EITHER DOCUMENT, and the sprint is the
// one that was wrong: `hydroFixField` cannot raise a cell on any path (src/legacy.js:3153,
// :3155-3156), and 14 measured runs found zero risen cells, so nothing is transported and `:28` is a
// misclassification. The sprint's S3.5 BODY at `:189-190` was right about the substance — it asks for
// "the low-amplitude conditioning delta and its removed/exported volume", calls the artefact a
// conditioning delta in its own words, and that ledger is now delivered. The `hydrofix` row carries
// the full evidence and the file:line citations.

/** The class ids this manifest claims to define. Every one of them must own at least one row. */
export const TRANSPORT_CLASS_IDS = Object.freeze([
  'materialTransport', 'latticeConditioning', 'surfaceExpression', 'generator',
])

/** Problem codes. Named, so a failure says which rule broke rather than "false". */
export const TRANSPORT_CODES = Object.freeze([
  'NO_HEIGHT_WRITERS',          // production reported an empty writer corpus — absence of evidence
  'WRITER_UNCLASSIFIED',        // a registered height writer with no row: the manifest went stale
  'WRITER_CLASSIFIED_TWICE',    // two rows claim the same node
  'ROW_NOT_A_HEIGHT_WRITER',    // a row for a node production does not consider a height writer
  'ROW_UNKNOWN_CLASS',          // a row whose class is not in TRANSPORT_CLASS_IDS
  'TRANSPORT_WITHOUT_COUPDATE', // material transport that names no state to co-update
  'TRANSPORT_WITHOUT_OWNER',    // an exemption with no later owner — forbidden by S3.5
  'CLASS_WITHOUT_ROWS',         // a declared class nobody owns
])

/** The rule name every outstanding transport debt is filed under in the exemption ledger. */
export const TRANSPORT_EXEMPTION_RULE = 'materialTransportCoEvolution'

/**
 * The manifest. One row per entry of doctrine's HEIGHT_WRITERS, deliberately no more: the domain of
 * this table is exactly "what production says rewrites height", so a node added to HEIGHT_WRITERS
 * without a review here is a hard failure rather than a silent omission.
 *
 * Frozen at both levels. A control that perturbs a row must REPLACE it ({...row, x}) — writing
 * through a frozen object is a silent no-op under sloppy-mode page.evaluate and proves nothing.
 */
export const TRANSPORT_CLASSES = Object.freeze([
  Object.freeze({
    node: 'hydraulic',
    class: 'materialTransport',
    // `wetness` LEAVES this list in S3.5, and unlike erosion2's removal — which turned on the node
    // having no water field at all — this one had a real candidate and was settled by MEASURING it.
    // The pipe solver DOES carry a per-cell water column (GPU_PIPE_STATE_FS writes
    // `vec4(b+dep-er, water, sediment+er-dep, 1.0)`, src/core/gpu.js:368) and it is already inside
    // S3.1's single readback, so publishing it would have cost no second synchronisation point. It
    // is still not a wetness map, on five independent readings taken at RES 64, square, GPU pipe
    // kernel, shipped parameters:
    //
    //   1. ITS MAGNITUDE IS THE ITERATION SLIDER, NOT THE TERRAIN. Mean water column 0.00888 at
    //      8 iterations rising monotonically to 0.07870 at 360 — an 8.9x range across the node's own
    //      legal slider — and it tracks the NO-FLOW rain/evaporation accumulation
    //      `w_{n+1} = (w_n + rain) * evap` to within 0.3-1.0% at every one of those points
    //      (measured/analytic 0.990, 0.993, 0.995, 1.000, 1.002, 1.003). At the shipped default of
    //      48 iterations the field stands at 51.3% of its own equilibrium: an unconverged transient.
    //   2. THE SPATIAL PATTERN IS NOT STABLE EITHER, so there is no scale-free structure hiding
    //      under an iteration-dependent magnitude. Pearson r against the 48-iteration field:
    //      0.493 (8), 0.762 (24), 1.000 (48), 0.686 (96), 0.418 (192), 0.176 (360). Normalising
    //      each field by its own mean leaves per-cell differences of 1.9-2.9x.
    //   3. IT IS NOT RES-LOCK INVARIANT. At one authored iteration count, gridK 1/2/3 give means
    //      0.0404/0.0393/0.0373 and pattern correlations 1.000/0.433/0.316. Res Lock exists to hold
    //      the published result steady across resolution; this field moves with it.
    //   4. IT IS A DEPTH, AND THE REGISTRY ALREADY NAMES THAT FIELD SEPARATELY. The channel is in
    //      normalised height units (x terrainDef.height gives metres) driven by an uncalibrated
    //      per-iteration rain of `0.0012/gk`. That is `waterDepth` (unit 'm', owner S4.4), not
    //      `wetness` (unit 'none'). Turning a depth into a dimensionless index needs a REFERENCE
    //      depth nobody has measured — the identical fabricated constant this node's own
    //      `precipitation` port already refuses (`precipitationConsumed: false`).
    //   5. IT EXISTS ON ONE ENGINE OF THREE. A droplet sink comes back with no water key at all and
    //      the CPU droplet ledger has no water field; water there is a per-particle scalar in the
    //      dyn texture, never a cell field. Hex has no pipe solver by construction.
    //
    // AND THE DOCTRINE SAYS THIS IS THE WRONG FIELD, INDEPENDENTLY OF ALL FIVE. sprint-02:194-195
    // and BACKLOG §2 require `wetness` SPLIT, not averaged: the state map is path-dependent
    // SATURATION and the derived companion is TWI, and "a plugin declaring one does not satisfy the
    // other". Nothing carries wetness into this node — the state texture is uploaded with water = 0
    // on every call — and nothing carries it out, so there is no path-dependence for a state map to
    // be about. The co-evolution rule exists to stop a mover DESTROYING carried history; hydraulic
    // destroys none, because none exists. The producer the plan does name is S5.3/S5.4
    // (sprint-05:26, :27, :165, :172 — "melt co-updates wetness"), and src/core/aux-maps.js now
    // says so instead of naming S3.3, which shipped without it.
    coUpdates: Object.freeze(['soilDepth', 'sedimentDepth']),
    // S3.5, FOURTH AND LAST NODE — the flip that empties the ledger. The implementation is S3.3's
    // and is unchanged by this commit: cover-aware consumption strips sand, then sediment, then
    // soil, then bedrock from the PUBLISHED delta, deposition lands in the explicit sediment layer,
    // and the stack identity solidTop = bedrock + soil + sediment + sand is asserted per sample.
    // What was outstanding was only the ledger reading, and it is deliberately a commit of its own
    // (D21) so the digest delta and the gate delta each name one node.
    //
    // THE BOUNDARY TERM IS ITEMISED WHERE AN ENGINE NAMES ONE AND REFUSED WHERE NONE DOES. The pipe
    // path publishes the APRON RING, accumulated over a cell set disjoint from the core
    // (src/core/gpu.js:516-522); the CPU droplet path publishes per-particle `exported`, `lost` and
    // `brushClipGain`; the GPU droplet and combined paths are `exportedDerived: true` — their export
    // IS sumIn-sumOut — so they publish no claim and say which engine refused
    // (`resolveCoverLoss`, src/plugins/ero/hydraulic.js).
    // Evidence: tests/legacy/_verify_cover_erosion.js.
    compliant: true,
    ownerSprint: 'S3.5',
    why: 'Pipe/Droplet detach, carry and deposit solid material; the ledger was computed and discarded (C3).',
    note: 'Consumes loose cover before bedrock and deposits into the explicit sediment layer. '
      + 'Declares `precipitation` and reports it WIRED and NOT CONSUMED rather than inventing the '
      + 'reference rain a mm/yr conversion would need. Declines `wetness`: the pipe solver\'s water '
      + 'column is a rain-accumulation transient whose magnitude and pattern both move with the '
      + 'iteration slider, it is a depth rather than the split saturation state doctrine requires, '
      + 'and two of the three engines have no cell water field at all.',
  }),
  Object.freeze({
    node: 'thermal',
    class: 'materialTransport',
    coUpdates: Object.freeze(['soilDepth', 'sedimentDepth']),
    // S3.5, FIRST NODE. Talus relaxation now consumes loose cover before bedrock and moves the same
    // volume into downslope `sedimentDepth` in the relaxation pass, co-updated with the height it
    // publishes. The stack identity solidTop = bedrock + soil + sediment + sand is asserted per
    // sample, and the boundary term is a named physical zero (both kernels omit off-grid
    // neighbours) rather than a difference of the other terms.
    // Evidence: tests/legacy/_verify_thermal_coevolution.js.
    compliant: true,
    ownerSprint: 'S3.5',
    why: 'Talus relaxation moves the same volume downslope; sprint-03:184-185 requires it into sedimentDepth.',
    note: 'Consumes loose cover before bedrock; deposition lands in the explicit sediment layer. '
      + 'Declares no precipitation port: dry mass-wasting has no rain term in either kernel, and a '
      + 'port nothing consumes is a declared-but-never-filled half-gate.',
  }),
  Object.freeze({
    node: 'streampower',
    class: 'materialTransport',
    // Detachment-limited: it models no deposition (sprint-03:186 forbids inventing any), so its
    // co-update is the cover it CONSUMES.
    //
    // `sedimentDepth` joined this list in S3.5, and the reason is the stack, not the process. A
    // standing sediment layer sits ABOVE soil (ADR-005), so a channel cuts it first — the node has to
    // READ it to strip in the right order, and a node that published `sedimentDepth` without reading
    // it would write zeros over a real layer, which is the state destruction this sprint exists to
    // stop. It still never ADDS to it: `depositedM3` is a published constant zero and the oracle
    // reads the raster back to prove no cell's cover rose.
    coUpdates: Object.freeze(['soilDepth', 'sedimentDepth']),
    // S3.5, SECOND NODE. Fluvial incision now consumes loose cover before bedrock and carries the
    // thicknesses through untouched where the surface rises, co-updated with the height it publishes.
    // The stack identity solidTop = bedrock + soil + sediment + sand is asserted per sample. The
    // ledger itemises the UPLIFT SOURCE — Udt * iters * sum over the kernel's interior, computed from
    // the node's inputs and never from the published delta — and publishes NO boundary budget at all:
    // the rim is forced to base level every iteration (src/legacy.js:2198, :2269) and detached
    // material is credited to nobody, neither of which the solver accumulates, so a figure would be a
    // restatement of the terms it was compared against rather than a measurement.
    // Evidence: tests/legacy/_verify_streampower_coevolution.js.
    compliant: true,
    ownerSprint: 'S3.5',
    why: 'Incision detaches material and reports no destination for it.',
    note: 'Stays detachment-limited: consumes loose cover before bedrock and deposits nothing. '
      + 'Reports the uplift source it applied; declines a boundary budget rather than deriving one '
      + 'from the terms it would be checked against. Declares no precipitation port: the kernel has '
      + 'no rain term, and a port nothing consumes is a declared-but-never-filled half-gate.',
  }),
  Object.freeze({
    node: 'erosion2',
    class: 'materialTransport',
    // `wetness` LEAVES this list in S3.5, and that is a correction rather than a retreat. The row
    // inherited it from `hydraulic`, whose pipe solver carries a water column the node could in
    // principle publish. `erosion2Field` reaches the same kernels through `atFeatureScale`
    // (src/legacy.js:3086-3089) and hands back one height Float32Array (:3113); no water field
    // survives the call on either engine, and the thermal and sharpening stages that follow have no
    // water at all. Keeping a co-update target this node cannot produce would be the
    // declared-but-never-filled half-gate in manifest form — the thing the R0 table exists to catch.
    // The remaining two are what the node genuinely reads and writes.
    coUpdates: Object.freeze(['soilDepth', 'sedimentDepth']),
    // S3.5, THIRD NODE. The multi-scale composition now consumes loose cover before bedrock and
    // books what it aggrades into `sedimentDepth`, co-updated with the height it publishes. The
    // stack identity solidTop = bedrock + soil + sediment + sand is asserted per sample.
    //
    // IT DEPOSITS, and that is measured, not inherited: the pipe/droplet stage carries
    // `deposit = lerp(.08,.62,sediment)` (src/legacy.js:3084) and the shape stage is a thermal
    // relaxation (:3100-3105), so unlike Stream Power this node genuinely puts transported material
    // down and `maxCoverRiseM` is required to be strictly positive.
    //
    // THE SPRINT'S OTHER HALF IS OPEN AND SAID SO. sprint-03:188 asks for stage-resolved state
    // instead of deposits re-derived from final height; `erosion2Field` accumulates nothing per
    // stage, so the ledger publishes `depositionStageResolved:false` and names the two stages that
    // raise the surface WITHOUT transporting anything — the unconditional fbm injection at :3068-3070
    // and the asymmetric sharpening at :3106-3112 — rather than pretending the figure is clean.
    // Closing it needs accumulators inside `erosion2Field`, which lives in src/legacy.js.
    // Evidence: tests/legacy/_verify_erosion2_coevolution.js.
    compliant: true,
    ownerSprint: 'S3.5',
    why: 'Composes hydraulic and thermal stages and re-derives deposits from final height instead of carrying them.',
    note: 'Consumes loose cover before bedrock and deposits into the explicit sediment layer. '
      + 'Publishes NO node-level boundary budget: the fbm seed injection is unconditional and '
      + 'unaccumulated, so even with every transform off the solvers budget a field the node did not '
      + 'receive. Where the composition reduces to one hydraulic pass on the native grid it reports '
      + 'that STAGE\'s own solver counters, scoped as such. The stage-resolved deposit sprint-03:188 '
      + 'asks for stays open and is declared open.',
  }),
  Object.freeze({
    node: 'hydrofix',
    class: 'latticeConditioning',
    // S3.5, FIFTH NODE — and the row that closes the sprint's one open classification dispute. It is
    // a CONDITIONING row that nevertheless names co-update targets, which is not a contradiction:
    // the class answers "does it move material", the targets answer "does it change state that
    // somebody else owns". HydroFix answers no to the first and yes to the second.
    //
    // THE DISPUTE IS SETTLED ON THE KERNEL, AND THE KERNEL SAYS CONDITIONING. `hydroFixField`
    // (src/legacy.js:3119-3158) has exactly two write paths into the field it returns and NEITHER CAN
    // RAISE A CELL:
    //   :3153       `out[i] -= mask[i]*cut`, the corridor downcut, mask in [0,1] and
    //               cut = relief*(.0003+.0072*downcut)*fix >= 0
    //   :3155-3156  `target = out[i]-eps; if(out[r]>target) out[r]=target`, the descent enforcement,
    //               which lowers a RECEIVER to just under its donor and never the reverse
    // Measured over 14 runs (square and hex, deep/bare/mixed cover, both slider regimes, masked and
    // unmasked): risen cells 0 and max published rise 0.000000 on every one. NO CELL ANYWHERE
    // RECEIVES MATERIAL, so there is no transport to co-evolve and `materialTransport` would be the
    // wrong class. sprint-03:28, which lists HydroFix among the four "existing transport nodes", is
    // WRONG on that point and is recorded as wrong here rather than silently diverged from.
    //
    // THE PREVIOUS `why` WAS ALSO WRONG, IN A WAY THAT MATTERED. It said the node "removes sinks",
    // which describes the PRIORITY-FLOOD WORKING COPY at :3120 — that fill does raise, measured at
    // 907 of 4096 cells on square and 1041 of 4736 on hex — and not the published field, which is
    // monotone non-increasing. Reading the fill as the node's effect is what made "conditioning"
    // sound like "changes nothing anybody owns", and that inference is what this row got wrong.
    //
    // BECAUSE sprint-03:189-190 WAS RIGHT ON THE SUBSTANCE. "Report the low-amplitude conditioning
    // delta and its removed/exported volume; it may not silently discard carved bedrock" is exactly
    // what was owed: what the carve cuts through is the COVER STACK, and before S3.5 the node had no
    // cover ports at all, so a breach through five metres of soil charged itself to bedrock and
    // nothing said so. Note that :189-190 calls the artefact a "conditioning delta" in the sprint's
    // own words — the sprint text and the R0 review disagree only at :28, and only about the class.
    //
    // THE LEDGER ITEMISES BY THE LAYER THE MATERIAL CAME OUT OF — `coverConsumedM3` accumulated from
    // the published cover rasters and `bedrockCarvedM3` from what is left of the carve after local
    // cover is exhausted, each accumulated independently and each compared against a strip the oracle
    // recomputes from the input cover and the published delta. It publishes NO export budget (the
    // only figure available is consumed+carved, a restatement of the terms it would be checked
    // against) and NO split between its two mechanisms (the kernel accumulates neither; the measured
    // ratio between them runs 41x to 269x, so a guessed split would be wrong by that factor). What it
    // DOES claim is the corridor downcut's per-cell ceiling, computed from the node's own parameters
    // and the input field's range, and declined under a mask like Stream Power's uplift term.
    // Evidence: tests/legacy/_verify_hydrofix_coevolution.js.
    coUpdates: Object.freeze(['soilDepth', 'sedimentDepth']),
    compliant: true,
    ownerSprint: 'S3.5',
    why: 'Conditions drainage by CARVING: monotone non-increasing on every measured run, so it '
      + 'transports nothing — but it cuts through the cover stack and owed a removed-volume ledger.',
    note: 'RECORDED DECISION (was DISPUTED). Classified `latticeConditioning` on kernel evidence: '
      + 'src/legacy.js:3153 and :3155-3156 can only lower, and 14 measured runs found zero risen '
      + 'cells, so no cell receives material. sprint-03:28 is wrong to list it among the transport '
      + 'nodes; sprint-03:189-190 is right that a removed-volume ledger was owed, and it is now '
      + 'delivered. Consumes loose cover before bedrock and deposits nothing — there is no additive '
      + 'term in the kernel at all. Reports the corridor downcut ceiling it applied; declines both an '
      + 'export budget and a downcut/breach split rather than deriving either from the terms it would '
      + 'be checked against. Declares no precipitation port: the kernel has no rain term.',
  }),
  Object.freeze({
    node: 'fracture',
    class: 'surfaceExpression',
    coUpdates: Object.freeze([]),
    compliant: null,
    ownerSprint: null,
    why: 'Rock Fracture is authored surface detail, not a process that relocates mass (sprint-03:192-194).',
    note: 'Declares the classification explicitly so it cannot be mislabeled as material transport later.',
  }),
  Object.freeze({
    node: 'canyon',
    class: 'generator',
    coUpdates: Object.freeze([]),
    compliant: null,
    ownerSprint: null,
    why: 'Creates a surface from parameters; nothing upstream is required.',
    note: 'The only generator doctrine registers as a height writer — the other gen/* plugins are not in '
      + 'HEIGHT_WRITERS, so they are out of this table\'s domain by construction.',
  }),
])

const isTransport = row => row && row.class === 'materialTransport'

/**
 * The exemption ledger, in the shape sprint-02:198 fixes: `{node, rule, ownerSprint}`. One entry per
 * material-transport node that has not yet been made compliant. S3.5's acceptance is that this list
 * is empty; today it has four entries, which is the measured "before".
 */
export function exemptionLedger(manifest = TRANSPORT_CLASSES) {
  return manifest
    .filter(row => isTransport(row) && row.compliant !== true)
    .map(row => ({ node: row.node, rule: TRANSPORT_EXEMPTION_RULE, ownerSprint: row.ownerSprint || null }))
}

/** Compliance roll-up over the transport rows only; the other classes have nothing to comply with. */
export function complianceSummary(manifest = TRANSPORT_CLASSES) {
  const transport = manifest.filter(isTransport)
  return {
    transportCount: transport.length,
    compliantCount: transport.filter(row => row.compliant === true).length,
    nonCompliant: transport.filter(row => row.compliant !== true).map(row => row.node),
    unowned: transport.filter(row => row.compliant !== true && !row.ownerSprint).map(row => row.node),
  }
}

/**
 * Classify a writer corpus against the manifest.
 *
 * `writers` is production's list — doctrine's HEIGHT_WRITERS. The manifest and class-id list default
 * to the production constants above; they are parameters so a control can perturb the INPUT
 * production consumes rather than the answer this function computes.
 *
 * Never throws: a stale manifest is exactly the condition this is meant to report, and a throw would
 * replace a named finding with a stack trace.
 */
export function classifyHeightWriters(writers, options = {}) {
  const manifest = Array.isArray(options.manifest) ? options.manifest : TRANSPORT_CLASSES
  const classIds = Array.isArray(options.classIds) ? options.classIds : TRANSPORT_CLASS_IDS
  const list = Array.isArray(writers) ? writers.slice() : []
  const problems = []

  // Absence of evidence is a failure. A classification run over an empty corpus would otherwise
  // report "every writer classified" while having classified nothing.
  if (list.length === 0) problems.push({ code: 'NO_HEIGHT_WRITERS' })

  const rowsByNode = new Map()
  for (const row of manifest) {
    if (!rowsByNode.has(row.node)) rowsByNode.set(row.node, [])
    rowsByNode.get(row.node).push(row)
  }

  const classified = []
  for (const node of list) {
    const rows = rowsByNode.get(node) || []
    if (rows.length === 0) { problems.push({ code: 'WRITER_UNCLASSIFIED', node }); continue }
    if (rows.length > 1) problems.push({ code: 'WRITER_CLASSIFIED_TWICE', node, classes: rows.map(r => r.class) })
    classified.push({
      node,
      class: rows[0].class,
      coUpdates: (rows[0].coUpdates || []).slice(),
      compliant: rows[0].compliant,
      ownerSprint: rows[0].ownerSprint || null,
    })
  }

  const writerSet = new Set(list)
  for (const row of manifest) {
    if (!writerSet.has(row.node)) problems.push({ code: 'ROW_NOT_A_HEIGHT_WRITER', node: row.node, class: row.class })
    if (!classIds.includes(row.class)) problems.push({ code: 'ROW_UNKNOWN_CLASS', node: row.node, class: row.class })
    if (!isTransport(row)) continue
    if (!Array.isArray(row.coUpdates) || row.coUpdates.length === 0) {
      problems.push({ code: 'TRANSPORT_WITHOUT_COUPDATE', node: row.node })
    }
    if (row.compliant !== true && !row.ownerSprint) problems.push({ code: 'TRANSPORT_WITHOUT_OWNER', node: row.node })
  }

  const populated = new Set(manifest.map(row => row.class))
  for (const id of classIds) if (!populated.has(id)) problems.push({ code: 'CLASS_WITHOUT_ROWS', class: id })

  // THE UNION OVER EVERY ROW THAT DECLARES TARGETS, not only the transport rows. It was
  // transport-only until S3.5e, when `hydrofix` — a `latticeConditioning` row — became the first
  // non-transport node to name co-update state: it carves through the cover stack without moving
  // material anywhere. Under the old scope its targets would have been invisible to gate 6, so the
  // manifest could have named an unregistered map on that row and read as coverage, which is the
  // declared-but-never-graded half-gate one class to the left. The VALUE is unchanged at
  // ['soilDepth','sedimentDepth'] because hydrofix names the same pair the four movers do — this
  // widens what is checked, not what is claimed.
  const transportRows = manifest.filter(isTransport)
  const coUpdateTargets = []
  for (const row of manifest) for (const target of (row.coUpdates || [])) {
    if (!coUpdateTargets.includes(target)) coUpdateTargets.push(target)
  }

  return {
    writers: list,
    classified,
    unclassified: problems.filter(p => p.code === 'WRITER_UNCLASSIFIED').map(p => p.node),
    duplicated: problems.filter(p => p.code === 'WRITER_CLASSIFIED_TWICE').map(p => p.node),
    orphanRows: problems.filter(p => p.code === 'ROW_NOT_A_HEIGHT_WRITER').map(p => p.node),
    unknownClassRows: problems.filter(p => p.code === 'ROW_UNKNOWN_CLASS').map(p => p.node),
    transportWithoutCoUpdate: problems.filter(p => p.code === 'TRANSPORT_WITHOUT_COUPDATE').map(p => p.node),
    emptyClasses: problems.filter(p => p.code === 'CLASS_WITHOUT_ROWS').map(p => p.class),
    classCounts: Object.fromEntries(classIds.map(id => [id, manifest.filter(row => row.class === id).length])),
    coUpdateTargets,
    compliance: complianceSummary(manifest),
    ledger: exemptionLedger(manifest),
    problems,
  }
}
