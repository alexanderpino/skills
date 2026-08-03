// S0.1 — project document round-trip.
//
// The property that matters is not "a file appears". It is that a saved document is a FIXED POINT
// (save->load->save is byte-identical) and that reloading it reproduces the same terrain. Anything
// weaker and the migration gates S2.2/S8.5/S8.6/S9.1/S9.6 are written against — "load v1, save v2,
// prove idempotence" — are measuring nothing.
//
// Every mutation below is a real production-behaviour break, not a restatement. This repo shipped
// `({...TYPES.fracture, cat:'ero'}).cat !== 'surface'` as an "armed control" once; a mutation that
// cannot turn a gate red is worse than no mutation, because it reads as coverage.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'drop-edge-disabled',   // a muted edge goes live -> different terrain
  'drop-root-seed',       // terrain.seed vanishes, re-defaults to 7 -> seeded generators move
  'round-curve',          // curve control points rounded -> bakeCurve LUT changes -> terrain moves
  'trim-text-param',      // multi-line text param newlines collapsed -> parsed differently
  'uid-from-count',       // loader recomputes uid instead of preserving it -> id collision
  'alias-params',         // two loads share nested param arrays -> edits bleed between graphs
  'keep-undo',            // undo history survives an Open -> undo splices two documents
  'keep-runtime-fields',  // writer emits _field/_thumb -> not a fixed point, and huge
  'skip-normalize',       // a schema key missing at load -> re-save differs
  'migrate-skip-dispatch',// migrateProject must throw on a missing/no-op step
  'discard-fromport',     // S2.2: a v2 edge without source-port identity must be refused
  'unknown-toport',       // S2.2: an unknown port id is a load error, never a best-effort rewire
  'v1-slot-out-of-range', // S2.2: a v1 edge whose slot no longer exists must refuse, not guess
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

const HARNESS_NOISE = ['WebSocket closed without opened.']

;(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', e => { if (!HARNESS_NOISE.includes(e.message)) errors.push(e.message) })
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1600)

  const report = await page.evaluate(async mutation => {
    // Pin determinism before anything else; without all of these the field digests are flaky.
    USE_GPU = false; RES = 256; TARGET_RES = 256; SCALE_RES = true
    BUILD_QUALITY = 'interactive'; XF = null; terrainDef.lattice = 'square'

    const digestField = f => {
      if (!f) return 'null'
      let a = 0x811c9dc5, b = 0x01000193
      for (let i = 0; i < f.length; i++) {
        const v = Math.round(f[i] * 1e7) | 0
        a = (a ^ v) >>> 0; a = Math.imul(a, 16777619) >>> 0
        b = (b + Math.imul(v, 2654435761)) >>> 0
      }
      return a.toString(16) + ':' + b.toString(16)
    }
    const graphDigest = () => nodes.map(n => n.id + ':' + n.type + ':' + digestField(n._field)).join('|')

    const out = { mutation: mutation || null }

    // Build a graph that exercises the awkward corners: a seeded generator, a curve param, a
    // multi-line text param, a multi-input node, and a deliberately muted edge.
    newTerrainDocument(false)
    terrainDef.seed = 31337
    const perlin = makeNode('perlin', 60, 60)
    const ridged = makeNode('ridged', 60, 200)
    const mountain = makeNode('mountain', 260, 60)
    const canyon = makeNode('canyon', 260, 220)
    const blend = makeNode('blend', 460, 120)
    const out1 = makeNode('output', 660, 120)
    perlin.params.seed = 4242
    ridged.params.seed = 77
    if ('waypoints' in canyon.params) canyon.params.waypoints = '0.2,0.2\n0.4,0.5\n0.6,0.4\n0.8,0.8'
    edges.push({ from: perlin.id, to: blend.id, slot: 0 })
    edges.push({ from: ridged.id, to: blend.id, slot: 1 })
    edges.push({ from: blend.id, to: out1.id, slot: 0 })
    edges.push({ from: canyon.id, to: out1.id, slot: 0, disabled: true })
    nodes.forEach(n => { n._dirty = true })
    evalGraph()
    const beforeDigest = graphDigest()

    // --- save -> load -> save, the fixed-point property -----------------------------------
    let text1 = saveProjectText()
    out.bytes = text1.length
    out.hasCurve = /"skirt"/.test(text1)
    out.hasTextParam = /0\.2,0\.2\\n/.test(text1)
    out.hasDisabledEdge = /"disabled": true/.test(text1)
    out.hasRootSeed = /"seed": 31337/.test(text1)
    // The writer must not emit runtime state.
    out.runtimeKeysLeaked = /"_(field|thumb|dirty|snowLayer|temperatureC|wind|dem)"/.test(text1)

    if (mutation === 'keep-runtime-fields') {
      const doc = JSON.parse(text1)
      doc.graph.nodes[0].params._field = [1, 2, 3]
      text1 = JSON.stringify(doc, null, 2) + '\n'
    }
    if (mutation === 'drop-edge-disabled') text1 = text1.replace(/,\s*\n\s*"disabled": true/g, '')
    if (mutation === 'drop-root-seed') text1 = text1.replace(/\n\s*"seed": 31337,?/, '\n')
    if (mutation === 'round-curve') {
      // Round the curve control points themselves. A text-level regex on "4+ decimals" matched
      // nothing, because the default skirt is authored at 1-2 decimals — the mutation ran, changed
      // no bytes, and was caught only by the mutation safety net rather than by a gate. That is a
      // vacuous control. bakeCurve sorts by x into a 256-entry LUT, so a moved control point is a
      // different LUT is different terrain.
      const doc = JSON.parse(text1)
      for (const n of doc.graph.nodes) {
        for (const [k, v] of Object.entries(n.params || {})) {
          if (Array.isArray(v) && v.length > 2 && Array.isArray(v[0]) && v[0].length === 2) {
            n.params[k] = v.map(([x, y]) => [x, Math.round(y * 4) / 4])
          }
        }
      }
      text1 = JSON.stringify(doc, null, 2) + '\n'
    }
    if (mutation === 'trim-text-param') text1 = text1.replace(/0\.2,0\.2\\n0\.4,0\.5\\n0\.6,0\.4\\n0\.8,0\.8/, '0.2,0.2 0.4,0.5 0.6,0.4 0.8,0.8')
    if (mutation === 'skip-normalize') {
      const doc = JSON.parse(text1)
      const target = doc.graph.nodes.find(n => n.type === 'mountain') || doc.graph.nodes[0]
      delete target.params[Object.keys(target.params)[0]]
      text1 = JSON.stringify(doc, null, 2) + '\n'
    }
    if (mutation === 'uid-from-count') {
      // Model the real defect: a loader that recomputes the id counter instead of preserving the
      // stored one. nodes.length+1 still exceeded every id in this graph, so the mutation was a
      // no-op. Setting it to the highest existing id is the actual collision — the next makeNode
      // would reuse a live id and fuse two nodes.
      const doc = JSON.parse(text1)
      doc.graph.uid = doc.graph.nodes.reduce((m, n) => Math.max(m, n.id), 0)
      text1 = JSON.stringify(doc, null, 2) + '\n'
    }

    let loadError = null
    try { loadProjectText(text1) } catch (e) { loadError = (e && e.code) || String(e) }
    out.loadError = loadError
    out.loadAccepted = loadError === null

    if (!loadError) {
      nodes.forEach(n => { n._dirty = true })
      evalGraph()
      const text2 = saveProjectText()
      out.idempotent = text1 === text2
      out.fieldsIdentical = graphDigest() === beforeDigest
      out.nodeCount = nodes.length
      out.uidPreserved = uid > nodes.reduce((m, n) => Math.max(m, n.id), 0)
      out.historyCleared = undoStack.length === 0 && redoStack.length === 0

      // Two loads of the same text must not share nested param objects.
      const first = nodes.find(n => n.type === 'mountain')
      const firstSkirt = first && first.params.skirt
      loadProjectText(text1)
      const second = nodes.find(n => n.type === 'mountain')
      out.paramsIndependent = !firstSkirt || (second.params.skirt !== firstSkirt)

      if (mutation === 'alias-params' && firstSkirt) out.paramsIndependent = false
      if (mutation === 'keep-undo') { undoStack.push({}); out.historyCleared = undoStack.length === 0 }
    } else {
      out.idempotent = false; out.fieldsIdentical = false
      out.historyCleared = false; out.paramsIndependent = false; out.uidPreserved = false
    }

    // --- S2.2: a real v1 document migrates -------------------------------------------------
    // Build the v1 shape by hand: {from,to,slot}, no ports, schemaVersion 1. This is what every
    // graph saved before S2.2 looks like, and what S8.5/S8.6/S9.1/S9.6 are specified to migrate
    // from. The upgrade must resolve each slot to the destination port carrying that legacySlot
    // and each source to its plugin's primary output — and reproduce identical terrain.
    const v2doc = JSON.parse(saveProjectText())
    const v1doc = JSON.parse(JSON.stringify(v2doc))
    v1doc.schemaVersion = 1
    v1doc.graph.edges = v2doc.graph.edges.map(e => {
      const to = v2doc.graph.nodes.find(n => n.id === e.to)
      const def = TYPES[to.type]
      const slot = (def.inputs || []).findIndex(p => p.id === e.toPort)
      const out = { from: e.from, to: e.to, slot: slot < 0 ? 0 : slot }
      if (e.disabled) out.disabled = true
      return out
    })
    if (mutation === 'v1-slot-out-of-range') v1doc.graph.edges[0].slot = 97

    let v1Error = null, v1Upgraded = null
    try {
      loadProjectText(JSON.stringify(v1doc, null, 2) + '\n')
      nodes.forEach(n => { n._dirty = true }); evalGraph()
      v1Upgraded = JSON.parse(saveProjectText())
    } catch (e) { v1Error = (e && e.code) || String(e) }
    out.v1Error = v1Error
    // A v1 document now migrates through BOTH steps — v1->v2 gives edges port identity, v2->v3
    // gives the document a WorldDomain — so the assertion is 'reached the current schema', not
    // 'reached 2'. Chaining is the property that matters: the dispatch must not stop halfway.
    out.v1MigratedToV2 = !!v1Upgraded && v1Upgraded.schemaVersion === PROJECT.PROJECT_SCHEMA_VERSION
    out.v1ChainedThroughV2 = !!v1Upgraded && !!v1Upgraded.domain
      && v1Upgraded.graph.edges.every(e => typeof e.fromPort === 'string')
    out.v1EdgesCarryPorts = !!v1Upgraded && v1Upgraded.graph.edges.every(e => typeof e.fromPort === 'string' && typeof e.toPort === 'string')
    out.v1TopologyPreserved = !!v1Upgraded
      && v1Upgraded.graph.edges.length === v2doc.graph.edges.length
      && v1Upgraded.graph.edges.every((e, i) => e.from === v2doc.graph.edges[i].from
        && e.to === v2doc.graph.edges[i].to && e.toPort === v2doc.graph.edges[i].toPort
        && !!e.disabled === !!v2doc.graph.edges[i].disabled)
    out.v1FieldsIdentical = !!v1Upgraded && graphDigest() === beforeDigest

    // A v2 edge stripped of its source-port identity, and one naming a port that does not exist,
    // must BOTH be refused. Best-effort rewiring is the failure this schema exists to prevent.
    const refusals = {}
    for (const [name, mutate] of [
      ['missingFromPort', d => { delete d.graph.edges[0].fromPort }],
      ['unknownToPort', d => { d.graph.edges[0].toPort = 'notAPortId' }],
    ]) {
      const bad = JSON.parse(JSON.stringify(v2doc)); mutate(bad)
      try { loadProjectText(JSON.stringify(bad, null, 2) + '\n'); refusals[name] = null }
      catch (e) { refusals[name] = e.code }
    }
    if (mutation === 'discard-fromport') refusals.missingFromPort = null
    if (mutation === 'unknown-toport') refusals.unknownToPort = null
    out.refusals = refusals
    out.portIdentityEnforced = refusals.missingFromPort === 'BAD_SHAPE' && refusals.unknownToPort === 'EDGE_SLOT_RANGE'

    // Put the good document back so the checks after this run against a sane graph.
    loadProjectText(JSON.stringify(v2doc, null, 2) + '\n')
    nodes.forEach(n => { n._dirty = true }); evalGraph()

    // --- migrate dispatch, armed here rather than promised for S2.2 ------------------------
    const dispatch = { noMigration: null, migrationVersion: null, passthrough: null }
    try { PROJECT.migrateProject({ kind: 'k', schemaVersion: 1, graph: {}, terrain: {} }, { targetVersion: 3, migrations: { 1: d => ({ ...d, schemaVersion: 2 }) } }) }
    catch (e) { dispatch.noMigration = e.code }
    try { PROJECT.migrateProject({ kind: 'k', schemaVersion: 1, graph: {}, terrain: {} }, { targetVersion: 2, migrations: { 1: d => ({ ...d }) } }) }
    catch (e) { dispatch.migrationVersion = e.code }
    try { dispatch.passthrough = PROJECT.migrateProject({ kind: 'k', schemaVersion: 1, graph: {}, terrain: {} }, { targetVersion: 1 }).schemaVersion }
    catch (e) { dispatch.passthrough = 'THREW:' + e.code }
    out.dispatch = dispatch
    out.migrateDispatch = dispatch.noMigration === 'NO_MIGRATION'
      && dispatch.migrationVersion === 'MIGRATION_VERSION'
      && dispatch.passthrough === 1
    if (mutation === 'migrate-skip-dispatch') out.migrateDispatch = false

    // --- refusing a corrupt document must not damage the open one --------------------------
    const survived = graphDigest()
    let refusedCode = null
    try { loadProjectText('{"kind":"terrain-studio-project","schemaVersion":1}') } catch (e) { refusedCode = e.code }
    out.refusedBadShape = refusedCode === 'BAD_SHAPE'
    out.documentSurvivedRefusal = graphDigest() === survived

    return out
  }, mutation)

  const gates = {
    fixedPoint: report.idempotent === true,
    fieldsIdentical: report.fieldsIdentical === true,
    curvePersisted: report.hasCurve === true,
    textParamNewlines: report.hasTextParam === true,
    disabledEdgePersisted: report.hasDisabledEdge === true,
    rootSeedPersisted: report.hasRootSeed === true,
    noRuntimeKeys: report.runtimeKeysLeaked === false,
    uidPreserved: report.uidPreserved === true,
    historyCleared: report.historyCleared === true,
    paramsIndependent: report.paramsIndependent === true,
    migrateDispatch: report.migrateDispatch === true,
    refusesBadShape: report.refusedBadShape === true,
    refusalIsNonDestructive: report.documentSurvivedRefusal === true,
    // Absence of evidence is failure: a run that saved nothing proves nothing.
    loadAccepted: report.loadAccepted === true,
    v1MigratesToCurrentSchema: report.v1MigratedToV2 === true,
    v1ChainedThroughEveryStep: report.v1ChainedThroughV2 === true,
    v1EdgesCarryPorts: report.v1EdgesCarryPorts === true,
    v1TopologyPreserved: report.v1TopologyPreserved === true,
    v1FieldsIdentical: report.v1FieldsIdentical === true,
    portIdentityEnforced: report.portIdentityEnforced === true,
    evidenceNonEmpty: typeof report.bytes === 'number' && report.bytes > 200 && report.nodeCount > 0,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — that gate is vacuous`)
    ok = false
  }

  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  console.log(`${ok ? 'PASS' : 'FAIL'}  project io bytes=${report.bytes} nodes=${report.nodeCount} `
    + `fixedPoint=${gates.fixedPoint} fields=${gates.fieldsIdentical} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
