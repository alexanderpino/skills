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
// POSITION, measured 2026-08-04: 2 of 4 compliant (`thermal`, `streampower`). The remaining two are
// separate commits by explicit decision (D21: one node per commit, each with a digest delta naming
// that node and nothing else — and both nodes so far have needed no re-bless at all, because the
// cover work is demand-gated and the published field never moved). `hydraulic`'s cover-first
// consumption landed in S3.3 and is gated by _verify_cover_erosion.js; only its LEDGER FLIP is
// outstanding, and it is deliberately not taken here because a commit that moved two rows could not
// say which change moved which gate.
//
// CLASSES
// -------
// `materialTransport`    moves material, and therefore MUST co-update the auxiliary maps its
//                        process touches (soil / sediment / wetness).
// `latticeConditioning`  conditions the lattice without transporting material.
// `surfaceExpression`    expresses authored surface detail.
// `generator`            creates height with nothing upstream.
//
// A NOTE ON THE TAXONOMY vs THE SPRINT TEXT
// -----------------------------------------
// `sprint-03-cover-layer.md:62` and `:197` name only THREE buckets — "generator, surface expression,
// or material transport". `latticeConditioning` is a fourth, added by the R0 review for `hydrofix`,
// which the sprint's S3.5 body (`:189-190`) instead lists among the transport nodes to migrate. The
// classification here is the reviewed one; the row records the dispute in `note` so the disagreement
// is a dated decision rather than an oversight. See the oracle report for the file:line citations.

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
    coUpdates: Object.freeze(['soilDepth', 'sedimentDepth', 'wetness']),
    compliant: false,
    ownerSprint: 'S3.3',
    why: 'Pipe/Droplet detach, carry and deposit solid material; the ledger is computed and discarded (C3).',
    note: 'Cover-aware consumption and in-pass co-update land in S3.3; the state outputs themselves in S3.1.',
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
    coUpdates: Object.freeze(['soilDepth', 'sedimentDepth', 'wetness']),
    compliant: false,
    ownerSprint: 'S3.5',
    why: 'Composes hydraulic and thermal stages and re-derives deposits from final height instead of carrying them.',
    note: 'Must expose/co-update the state of the stages it composes (sprint-03:188).',
  }),
  Object.freeze({
    node: 'hydrofix',
    class: 'latticeConditioning',
    coUpdates: Object.freeze([]),
    compliant: null,
    ownerSprint: null,
    why: 'Low-amplitude hydrological conditioning of the lattice: it removes sinks, it does not model a transporting process.',
    note: 'DISPUTED against sprint-03:28 and :189-190, which list HydroFix among the transport nodes and require '
      + 'a removed/exported volume ledger. R0 review classifies it as conditioning; the carved-volume report is '
      + 'still owed and is tracked by S3.5 as a conditioning delta, not as material transport.',
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

  const transportRows = manifest.filter(isTransport)
  const coUpdateTargets = []
  for (const row of transportRows) for (const target of (row.coUpdates || [])) {
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
