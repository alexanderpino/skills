// S9.3 — an imported height source's provenance must survive undo, redo, duplicate and save/load.
//
// S9.3's gate says "Save/load/undo retain source and override separately". Save/load did; undo and
// duplicate did not, and both were silent:
//
//   graphSnapshot()  copied _dem, _demImg and _demRaw and omitted _demSrc      (legacy.js:3269-3270)
//   duplicateSel()   copied the same three and omitted _demSrc                 (legacy.js:4551)
//
// _demSrc is the record of WHERE the height came from, and it is also what the project writer reads
// when embedding an import in a saved document. So an undo stripped an import's provenance, and a
// save taken after that undo lost the source bytes entirely — the node kept rendering from the
// already-decoded field, so nothing looked wrong until the document was reloaded somewhere else.
//
// This is the same defect shape as S8.3's variables: a snapshot built from an EXPLICIT FIELD LIST
// silently drops whatever was added to nodes after the list was written. It is the third time this
// list has been the cause, which is why the gate is here rather than in a comment.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'snapshot-drops-source',   // the pre-fix snapshot: _demSrc absent, restored through real production
  'document-drops-source',   // the saved document arrives with no source block
  'origin-has-no-source',    // the node being duplicated carries no provenance, so the copy rightly has none
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

;(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1400)

  const report = await page.evaluate(mutation => {
    USE_GPU = false
    const out = { mutation: mutation || null }
    newTerrainDocument(false, '', true)

    // A real raw16 source record: 4x4 samples, 16 bits each = 32 bytes. rebuildDemFromProjectSource
    // decodes exactly this shape on load, so the fixture exercises the real reload path rather than
    // a shape only this test would ever produce.
    const side = 4
    const bytes = new Uint8Array(side * side * 2)
    for (let i = 0; i < bytes.length; i++) bytes[i] = (i * 37) & 0xff
    let bin = ''
    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i])
    const base64 = btoa(bin)
    const SRC = { kind: 'raw16', name: 'probe-dem.raw', side, base64 }

    const nd = makeNode('import', 80, 80)
    nd._demSrc = mutation === 'origin-has-no-source' ? null : { ...SRC }
    out.originHasSource = !!nd._demSrc

    // --- UNDO / REDO ---------------------------------------------------------------------------
    // The mutation reproduces the PRE-FIX BUILD rather than editing the answer: it strips _demSrc
    // from the snapshot, which is exactly what graphSnapshot() used to emit. Real pushUndo, real
    // undoGraph, real restoreGraph then run against it.
    const snap = graphSnapshot()
    if (mutation === 'snapshot-drops-source') snap.nodes.forEach(n => { delete n._demSrc })
    pushUndo(snap)
    // The graph must now change WITHOUT recording, or the perturbed snapshot is not the one undo
    // pops. The first version of this called makeNode() here, which records a snapshot of its own —
    // so undoGraph() restored THAT one, complete with _demSrc, and the control read as vacuous.
    // Pushing a node straight onto `nodes` changes nodes.length (so the restore is not editor-only)
    // and leaves the undo stack alone.
    nd.x = 400
    nodes.push({ id: uid++, type: 'perlin', x: 700, y: 80, w: 150, params: {},
      _field: null, _thumb: null, _dirty: true, _inputs: null })
    undoGraph()
    const afterUndo = nodes.find(n => n.type === 'import')
    out.undo = {
      nodeSurvived: !!afterUndo,
      sourceSurvived: !!(afterUndo && afterUndo._demSrc),
      nameSurvived: afterUndo && afterUndo._demSrc ? afterUndo._demSrc.name : null,
      base64Survived: !!(afterUndo && afterUndo._demSrc && afterUndo._demSrc.base64 === base64),
    }
    redoGraph()
    const afterRedo = nodes.find(n => n.type === 'import')
    out.redo = { sourceSurvived: !!(afterRedo && afterRedo._demSrc) }

    // --- DUPLICATE -----------------------------------------------------------------------------
    newTerrainDocument(false, '', true)
    const orig = makeNode('import', 80, 80)
    orig._demSrc = mutation === 'origin-has-no-source' ? null : { ...SRC }
    select(orig)
    duplicateSel()
    const copy = nodes.find(n => n.type === 'import' && n.id !== orig.id)
    out.duplicate = {
      copyExists: !!copy,
      copyHasSource: !!(copy && copy._demSrc),
      copyNameMatches: !!(copy && copy._demSrc && orig._demSrc && copy._demSrc.name === orig._demSrc.name),
      // A duplicate must not ALIAS the original's record, or editing one would edit both.
      distinctObject: !!(copy && orig._demSrc && copy._demSrc !== orig._demSrc),
    }

    // --- SAVE / LOAD ---------------------------------------------------------------------------
    newTerrainDocument(false, '', true)
    const saveNode = makeNode('import', 80, 80)
    saveNode._demSrc = mutation === 'origin-has-no-source' ? null : { ...SRC }
    let text = saveProjectText()
    if (mutation === 'document-drops-source') {
      // Nodes live at doc.graph.nodes, not doc.nodes — the canonical writer nests them
      // (project.js:210). The first version iterated doc.nodes, deleted nothing, and re-stringified
      // an unchanged document, which is why this control read as vacuous rather than red.
      const doc = JSON.parse(text)
      const docNodes = (doc.graph && doc.graph.nodes) || []
      if (!docNodes.length) throw new Error('document carries no nodes — the mutation would be inert')
      for (const n of docNodes) delete n.source
      text = JSON.stringify(doc)
    }
    out.documentMentionsSource = text.includes('probe-dem.raw')
    loadProjectText(text)
    const loaded = nodes.find(n => n.type === 'import')
    out.roundTrip = {
      sourceSurvived: !!(loaded && loaded._demSrc),
      base64Survived: !!(loaded && loaded._demSrc && loaded._demSrc.base64 === base64),
    }
    return out
  }, mutation)

  const gates = {
    // Absence of evidence is a failure: if the origin node never had a source, everything below is
    // trivially satisfiable and proves nothing.
    originActuallyCarriedASource: report.originHasSource === true,
    undoRetainsImportSource: report.undo.nodeSurvived === true && report.undo.sourceSurvived === true
      && report.undo.nameSurvived === 'probe-dem.raw' && report.undo.base64Survived === true,
    redoRetainsImportSource: report.redo.sourceSurvived === true,
    duplicateCarriesSource: report.duplicate.copyExists === true && report.duplicate.copyHasSource === true
      && report.duplicate.copyNameMatches === true,
    duplicateDoesNotAliasSource: report.duplicate.distinctObject === true,
    savedDocumentEmbedsSource: report.documentMentionsSource === true,
    reloadRestoresSourceBytes: report.roundTrip.sourceSurvived === true && report.roundTrip.base64Survived === true,
    noPageErrors: errors.length === 0,
  }

  let ok = Object.values(gates).every(Boolean)
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  console.log(`${ok ? 'PASS' : 'FAIL'}  import provenance undo=${report.undo.sourceSurvived} `
    + `redo=${report.redo.sourceSurvived} dup=${report.duplicate.copyHasSource}/${report.duplicate.distinctObject} `
    + `doc=${report.documentMentionsSource} reload=${report.roundTrip.sourceSurvived} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify({ report, gates, errors }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
