// R0 / S3.5 precondition — the transport classification manifest and its exemption ledger.
//
// WHAT THIS ORACLE IS FOR
// -----------------------
// `docs/plan/sprint-03-cover-layer.md:200` makes S3.5's acceptance "the final exemption ledger
// contains no material-transport entry", and `:82` requires "every height writer has one reviewed
// class". Measured on 2026-07-30, neither structure existed:
//   grep -rniE "ownerSprint|exemptionLedger|EXEMPTION" src/ tests/ scripts/ index.html
// returned only `_verify_shapescan.js`'s unrelated square-shape markers and four
// "NOTE (converted, not an exemption)" comments in legacy.js. So S3.5's acceptance line was an empty
// search over a structure that does not exist — green on day one, green forever, and a removal with
// no measured before. `src/core/transport-classes.js` makes it a data structure with four entries,
// and this oracle asserts the reading. S3.5's evidence is then the ledger going 4 -> 0, one node at
// a time, with this file red at every intermediate step until the last one lands.
//
// THE RED BASELINE IS ASSERTED, NOT MERELY PRINTED
// ------------------------------------------------
// Today all four material-transport nodes ship `compliant: false`, because no cover state exists for
// them to co-update (see `DOCTRINE_STAGES.hydraulicCoEvolution` in src/core/doctrine.js: armed in
// S3, reason "no cover state to co-update yet"). `redBaselineAllTransportNonCompliant` asserts
// compliantCount === 0 and transportCount === 4 as HARD NUMBERS. When S3.5 makes the first node
// compliant this oracle goes red and must be updated in the same commit as the implementation —
// that is the intended behaviour, and it is what makes the baseline a measurement rather than a
// comment. `--mutate=transport-claims-compliant` demonstrates it biting today.
//
// EXPECTATION SOURCE
// ------------------
// `REVIEWED` below is the classification read out of the sprint document and ADR-005, NOT out of
// production. It is the independently-known answer; the manifest is what is graded against it.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'unclassified-writer',          // drop a row: a registered writer with no reviewed class
  'transport-without-coupdate',   // a mover that names no state to co-update
  'class-without-owner',          // a declared class no row owns
  'writers-list-empty',           // production reports no height writers — absence of evidence
  'coupdate-target-unregistered', // a co-update target that is not a registered STATE aux map
  // The compliance reading, armed from BOTH sides. `transport-claims-compliant` targets a node that
  // is NOT yet compliant (so it moves the count up and the ledger down); `transport-drops-compliance`
  // targets the one that IS (so it moves them back the other way). Before S3.5 landed its first node
  // only the first of these was possible, and it targeted `thermal`; repointing it was mandatory,
  // because a control that flips a row to the value production already holds is not a control at
  // all — it is a silent no-op that reads as coverage.
  'transport-claims-compliant',   // a still-exempt transport row claims compliance
  'transport-drops-compliance',   // the compliant transport row reverts to exempt
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

// The reviewed classification, transcribed from the sprint document — the known answer.
//   materialTransport   sprint-03:28, :177-190  (Hydraulic, Thermal, Stream Power, Erosion 2)
//   surfaceExpression   sprint-03:192-194       (Rock Fracture as an authored surface expression)
//   generator           sprint-03:62            ("generator, surface expression, or material transport")
//   latticeConditioning R0 review               (hydrofix; DISPUTED against sprint-03:28/:189-190)
const REVIEWED = {
  hydraulic: 'materialTransport',
  thermal: 'materialTransport',
  streampower: 'materialTransport',
  erosion2: 'materialTransport',
  hydrofix: 'latticeConditioning',
  fracture: 'surfaceExpression',
  canyon: 'generator',
}
const SPRINT_FOUR = ['hydraulic', 'thermal', 'streampower', 'erosion2']
const EXPECTED_TRANSPORT_COUNT = SPRINT_FOUR.length   // 4
// S3.5 IN PROGRESS — the count moved, and that transition is the story's evidence.
//
// This shipped as `0` and was asserted as a hard number so that the first compliant node would turn
// this oracle RED and force the update into the same commit as the implementation. That has now
// happened twice:
//   thermal      consumes loose cover before bedrock and moves what slides into `sedimentDepth`
//                (tests/legacy/_verify_thermal_coevolution.js)
//   streampower  consumes loose cover before bedrock, stays detachment-limited so it deposits
//                nothing, itemises its uplift source and declines a boundary budget it cannot
//                support (tests/legacy/_verify_streampower_coevolution.js)
// The number is 2, and it is still a hard number: the next node to land turns this red again.
//
// The list is what makes the count non-vacuous. `compliantCount === 2` alone would be satisfied by
// ANY two of the four claiming compliance; naming which ones is what a mutation can contradict —
// `transport-claims-compliant` flips a node that is NOT yet compliant, and `transport-drops-compliance`
// flips one that is back, so the reading is armed from both sides.
const EXPECTED_COMPLIANT = ['thermal', 'streampower']
const EXPECTED_NON_COMPLIANT = SPRINT_FOUR.filter(node => !EXPECTED_COMPLIANT.includes(node))
const EXPECTED_COMPLIANT_COUNT = EXPECTED_COMPLIANT.length   // 1
const EXPECTED_LEDGER_COUNT = EXPECTED_TRANSPORT_COUNT - EXPECTED_COMPLIANT_COUNT   // 3

;(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1400)

  const report = await page.evaluate(async mutation => {
    const out = { mutation: mutation || null, moduleError: null }
    // The module is not on the legacy global surface (legacy.js has a single serial owner and this
    // file may not touch it), so it is loaded through the dev server the runner already hosts. Any
    // failure is CAPTURED, never thrown: a throw would replace the gate table with a stack trace,
    // and "the feature is absent" must read as a named red, not as a broken probe.
    let TC = null
    for (const specifier of ['/src/core/transport-classes.js', './src/core/transport-classes.js']) {
      if (TC) break
      try { TC = await import(specifier) } catch (e) { out.moduleError = String((e && e.message) || e) }
    }
    if (!TC || typeof TC.classifyHeightWriters !== 'function') {
      out.moduleLoaded = false
      return out
    }
    out.moduleLoaded = true
    out.moduleError = null
    try { USE_GPU = false } catch (e) { /* not required for a pure-data probe */ }

    // --- production surfaces ------------------------------------------------------------------
    // DOCTRINE is legacy.js's live export of src/core/doctrine.js — production's authority on which
    // node types write height. AUXMAPS.AUX_MAPS is the registry that says which auxiliary maps exist
    // and under which lens.
    const AUX = (typeof AUXMAPS !== 'undefined' && AUXMAPS && AUXMAPS.AUX_MAPS) || {}
    const knownTypes = (typeof TYPES !== 'undefined' && TYPES) ? TYPES : {}

    // --- the immutability probe, MEASURED on both endpoints ------------------------------------
    // A control that perturbs a frozen row by writing through it is a silent no-op under
    // sloppy-mode page.evaluate. This performs that exact illegal write and records that it did not
    // land, which is why every control below REPLACES objects instead.
    const row0Before = TC.TRANSPORT_CLASSES[0] && TC.TRANSPORT_CLASSES[0].compliant
    try { TC.TRANSPORT_CLASSES[0].compliant = true } catch (e) { /* strict-mode hosts throw; sloppy ones do not */ }
    try { TC.TRANSPORT_CLASSES.push({ node: 'bogus', class: 'generator' }) } catch (e) { /* frozen array */ }
    out.immutability = {
      rowFrozen: Object.isFrozen(TC.TRANSPORT_CLASSES[0]),
      arrayFrozen: Object.isFrozen(TC.TRANSPORT_CLASSES),
      writeThroughLanded: TC.TRANSPORT_CLASSES[0].compliant !== row0Before,
      pushLanded: TC.TRANSPORT_CLASSES.length !== 7,
      length: TC.TRANSPORT_CLASSES.length,
    }

    // --- controls: every one perturbs an INPUT PRODUCTION CONSUMES ------------------------------
    // The manifest and the class-id list are production data; `classifyHeightWriters` is production
    // code. Each control hands the production classifier a perturbed production table (replacing
    // rows, never writing through them) or perturbs the live DOCTRINE ledger itself. None of them
    // touches a value this file later asserts on.
    let manifest = TC.TRANSPORT_CLASSES
    let classIds = TC.TRANSPORT_CLASS_IDS
    if (mutation === 'unclassified-writer') manifest = manifest.filter(r => r.node !== 'thermal')
    if (mutation === 'transport-without-coupdate') manifest = manifest.map(r => r.node === 'thermal' ? { ...r, coUpdates: [] } : r)
    if (mutation === 'coupdate-target-unregistered') manifest = manifest.map(r => r.node === 'thermal' ? { ...r, coUpdates: ['topsoilThickness'] } : r)
    // REPOINTED IN S3.5b. This targeted `streampower` until that node became compliant; a control
    // that flips a row to the value production already holds is not a control at all, it is a silent
    // no-op that reads as coverage. `erosion2` is still exempt, so claiming compliance for it
    // genuinely moves the count up and the ledger down.
    if (mutation === 'transport-claims-compliant') manifest = manifest.map(r => r.node === 'erosion2' ? { ...r, compliant: true } : r)
    // ...and `thermal` is the one node that IS compliant, so reverting it moves the count the other way.
    if (mutation === 'transport-drops-compliance') manifest = manifest.map(r => r.node === 'thermal' ? { ...r, compliant: false } : r)
    if (mutation === 'class-without-owner') classIds = classIds.concat('aeolianTransport')
    if (mutation === 'writers-list-empty') {
      // The LIVE ledger legacy.js exposes. DOCTRINE is a read-only global binding but a plain
      // mutable object, so the property is REPLACED rather than written through a frozen array.
      DOCTRINE.HEIGHT_WRITERS = Object.freeze([])
    }

    const writers = (typeof DOCTRINE !== 'undefined' && DOCTRINE && Array.isArray(DOCTRINE.HEIGHT_WRITERS))
      ? DOCTRINE.HEIGHT_WRITERS.slice() : []

    // Did the control actually move production? Reported so a control that silently no-ops is
    // visible in the log rather than being mistaken for a gate that failed to bite.
    out.perturbation = {
      manifestRows: manifest.length,
      productionManifestRows: TC.TRANSPORT_CLASSES.length,
      manifestMoved: manifest.length !== TC.TRANSPORT_CLASSES.length
        || manifest.some((r, i) => JSON.stringify(r) !== JSON.stringify(TC.TRANSPORT_CLASSES[i])),
      classIdsMoved: classIds.length !== TC.TRANSPORT_CLASS_IDS.length,
      writersMoved: writers.length !== 7,
      writersSeen: writers.slice(),
    }

    // --- production computes the classification -------------------------------------------------
    const r = TC.classifyHeightWriters(writers, { manifest, classIds })
    out.classification = {
      writers: r.writers,
      classified: r.classified,
      unclassified: r.unclassified,
      duplicated: r.duplicated,
      orphanRows: r.orphanRows,
      unknownClassRows: r.unknownClassRows,
      transportWithoutCoUpdate: r.transportWithoutCoUpdate,
      emptyClasses: r.emptyClasses,
      classCounts: r.classCounts,
      coUpdateTargets: r.coUpdateTargets,
      compliance: r.compliance,
      ledger: r.ledger,
      problemCodes: r.problems.map(p => p.code),
    }

    // The exported defaults must BE the production constants, or a caller that omits the options
    // would be graded against a different table from the one asserted here.
    const viaDefaults = TC.classifyHeightWriters(writers)
    const viaExplicit = TC.classifyHeightWriters(writers, { manifest: TC.TRANSPORT_CLASSES, classIds: TC.TRANSPORT_CLASS_IDS })
    out.defaultsAreProduction = JSON.stringify(viaDefaults) === JSON.stringify(viaExplicit)

    // --- co-update targets vs the auxiliary registry --------------------------------------------
    // A mover must co-update REGISTERED STATE. A name that is not in the aux registry, or that is
    // registered under the derived/continued lens, is not cover state and cannot be co-updated.
    out.coUpdate = r.coUpdateTargets.map(id => ({
      id, registered: !!AUX[id], lens: AUX[id] ? AUX[id].lens : null, unit: AUX[id] ? AUX[id].unit : null,
    }))
    out.unregisteredCoUpdateTargets = out.coUpdate.filter(t => !t.registered || t.lens !== 'state').map(t => t.id)

    // --- every writer is a real registered node type ---------------------------------------------
    out.writersRegistered = writers.map(w => ({ node: w, inTypes: !!knownTypes[w] }))
    out.writersNotInTypes = out.writersRegistered.filter(w => !w.inTypes).map(w => w.node)

    // --- fixture distinctness: the rows must genuinely differ from one another --------------------
    const rowSignatures = r.classified.map(c => c.class + '|' + c.coUpdates.join('+'))
    out.distinct = {
      rows: r.classified.length,
      distinctSignatures: new Set(rowSignatures).size,
      distinctClasses: new Set(r.classified.map(c => c.class)).size,
      distinctCoUpdateSets: new Set(r.classified.filter(c => c.class === 'materialTransport').map(c => c.coUpdates.join('+'))).size,
    }

    // --- graded against the reviewed answer, which lives in the ORACLE, not in production ---------
    return out
  }, mutation)

  // ---------------------------------------------------------------------------------------------
  // Everything below guards against `report.classification` being absent, so a module that failed
  // to load still reaches the gate table and prints a named red rather than throwing.
  const c = report.classification || {}
  const comp = c.compliance || {}
  const ledger = c.ledger || []
  const classified = c.classified || []
  const writers = c.writers || []
  const classIdsExpected = ['materialTransport', 'latticeConditioning', 'surfaceExpression', 'generator']
  const classOf = Object.fromEntries(classified.map(x => [x.node, x.class]))

  const mismatches = writers.filter(w => classOf[w] !== REVIEWED[w])
  const reviewedButNotAWriter = Object.keys(REVIEWED).filter(k => !writers.includes(k))
  const transportRows = classified.filter(x => x.class === 'materialTransport')
  const counts = c.classCounts || {}

  const gates = {
    // 1. The probe itself reached production. A false here means the module is absent — which is a
    //    named red, not a throw.
    transportModuleLoads: report.moduleLoaded === true && !report.moduleError,

    // 2. Complete classification (sprint-03:82). This is what stops the manifest going stale as
    //    nodes are added: a writer with no row, or with two, is red.
    everyHeightWriterHasExactlyOneClass: writers.length > 0 && classified.length === writers.length
      && (c.unclassified || []).length === 0 && (c.duplicated || []).length === 0,

    // 3. And the class each one got is the REVIEWED class, transcribed from the sprint document
    //    above rather than read back out of production.
    manifestMatchesReviewedClassification: writers.length > 0 && mismatches.length === 0
      && reviewedButNotAWriter.length === 0,

    // 4. No row outside the domain, no class outside the declared set.
    noOrphanOrUnknownClassRows: (c.orphanRows || []).length === 0 && (c.unknownClassRows || []).length === 0,

    // 5. Every mover names the state it must co-update. An empty list would let a "compliant"
    //    transport node co-update nothing.
    everyTransportRowCoUpdates: transportRows.length > 0
      && (c.transportWithoutCoUpdate || []).length === 0
      && transportRows.every(x => Array.isArray(x.coUpdates) && x.coUpdates.length > 0),

    // 6. ...and those names are REGISTERED STATE maps in production's aux registry, not prose. The
    //    `length > 0` term keeps this from passing vacuously on an empty target set.
    coUpdateTargetsAreRegisteredStateMaps: (c.coUpdateTargets || []).length > 0
      && (report.unregisteredCoUpdateTargets || []).length === 0,

    // 7. A class the manifest claims to define with no row is an exemption with no owner.
    everyDeclaredClassHasRows: (c.emptyClasses || []).length === 0
      && classIdsExpected.every(id => counts[id] > 0)
      && Object.values(counts).every(n => n > 0),

    // 8. THE COMPLIANCE COUNT, ASSERTED AS NUMBERS AND AS NAMES. Four movers; exactly the nodes in
    //    EXPECTED_COMPLIANT are compliant and exactly the rest are not. Started at 0/4, now 1/4.
    complianceCountIsTheMeasuredPosition: comp.transportCount === EXPECTED_TRANSPORT_COUNT
      && comp.compliantCount === EXPECTED_COMPLIANT_COUNT
      && (comp.nonCompliant || []).slice().sort().join(',') === EXPECTED_NON_COMPLIANT.slice().sort().join(',')
      && transportRows.filter(x => x.compliant === true).map(x => x.node).sort().join(',')
        === EXPECTED_COMPLIANT.slice().sort().join(','),

    // 9. The ledger S3.5 drains: one entry per mover that is not yet compliant, each filed under the
    //    transport rule and each with a later owner. "An exemption without a later owner is
    //    forbidden" (sprint-03:194). It was 4; it is now 3; S3.5's acceptance is 0.
    exemptionLedgerIsTheMeasuredPosition: ledger.length === EXPECTED_LEDGER_COUNT
      && ledger.map(e => e.node).sort().join(',') === EXPECTED_NON_COMPLIANT.slice().sort().join(',')
      && ledger.every(e => e.rule === 'materialTransportCoEvolution' && !!e.ownerSprint)
      && (comp.unowned || []).length === 0,

    // 10. The corpus is real: non-empty, and every entry is a node type the registry actually ships.
    writerCorpusNonEmptyAndRegistered: writers.length > 0 && (report.writersNotInTypes || []).length === 0,

    // 11. Structural, and measured on both endpoints in one run: the illegal write-through was
    //     ATTEMPTED and is recorded as not having landed. That is why the controls above replace
    //     objects — a control that wrote through would be a silent no-op.
    manifestIsImmutable: !!report.immutability && report.immutability.rowFrozen === true
      && report.immutability.arrayFrozen === true && report.immutability.writeThroughLanded === false
      && report.immutability.pushLanded === false,

    // 12. Structural: the module's default manifest IS the production constant.
    defaultManifestIsProductionManifest: report.defaultsAreProduction === true,

    // 13. Absence of evidence is failure. A corpus, distinct rows, and more than one class.
    //     WHAT THESE NUMBERS ARE, checked against what the collections actually hold rather than
    //     left as round figures. A signature is `class|coUpdates`, so the achievable count is
    //     (distinct transport co-update sets) + (the three non-transport classes, each with an empty
    //     set). S3.5b gave streampower the same co-update set as thermal — both consume soil and
    //     sediment, only hydraulic and erosion2 also touch wetness — so there are 2 transport sets
    //     and the signature count is 2 + 3 = 5, which is the MAXIMUM the current manifest can
    //     produce, not a floor with slack under it. `>= 5` therefore reads "no two classes have
    //     collapsed onto each other"; if a later story adds a third co-update set it should move to
    //     6. Measured 2026-08-04: signatures 5, transport co-update sets 2, co-update targets 3.
    evidenceNonEmpty: writers.length > 0 && classified.length > 0
      && (report.distinct || {}).distinctClasses === 4
      && (report.distinct || {}).distinctSignatures >= 5
      && (report.distinct || {}).distinctCoUpdateSets >= 2
      && (c.coUpdateTargets || []).length >= 3,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)

  // Reporting requirement: any node doctrine lists that is NOT one of the sprint's four movers.
  const outsideSprintFour = writers.filter(w => !SPRINT_FOUR.includes(w))
  console.log(`writers (${writers.length}): ${writers.join(', ') || '(none)'}`)
  for (const row of classified) {
    console.log(`  ${row.node.padEnd(12)} ${row.class.padEnd(20)} coUpdates=[${row.coUpdates.join(',')}] `
      + `compliant=${row.compliant} owner=${row.ownerSprint || '-'}`)
  }
  console.log(`height writers outside the sprint's four movers (${outsideSprintFour.length}): ${outsideSprintFour.join(', ') || '(none)'}`)
  console.log(`exemption ledger (${ledger.length}): ` + (ledger.map(e => `${e.node}/${e.rule}@${e.ownerSprint}`).join(' ') || '(empty)'))

  console.log(`${ok ? 'PASS' : 'FAIL'}  transport co-evolution writers=${writers.length} classified=${classified.length} `
    + `unclassified=[${(c.unclassified || []).join(',')}] transport=${comp.transportCount} compliant=${comp.compliantCount} `
    + `ledger=${ledger.length} coUpdateTargets=${(c.coUpdateTargets || []).length} emptyClasses=[${(c.emptyClasses || []).join(',')}] `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
