// Preview detail is a FRACTION of the document's grid. It is not the document's grid.
//
// The build-profile control used to offer absolute sample counts — 128 through 4096 — with no
// reference to the document at all. So on a world created at 512 samples, choosing 1024 doubled the
// resolution and HALVED THE SAMPLE SPACING, which is a physical property every erosion parameter in
// this app is denominated in. A different simulation, presented as a preview setting.
//
// It was worse than unclear, because the two numbers were never connected in the first place:
// `confirmNewTerrain` recorded the author's column count in the WorldDomain and never applied it to
// the evaluator, so a document created at 493 columns evaluated at whatever RES happened to be, and
// this control was the only thing that ever set the real grid.
//
// Both halves are gated here: creating applies the chosen count, and preview detail scales it
// without moving it.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'create-ignores-columns',   // the pre-fix path: build the document without applying the count
  'detail-mutates-document',  // the confusion itself: the preview result written back as the grid
  'detail-is-absolute',       // detail treated as a sample count rather than a fraction
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
    // A count that is NOT a power of two and NOT the shipped default, so "it happened to already be
    // 512" cannot masquerade as "the count was applied".
    const COLS = 300, WIDTH = 6000

    document.querySelector('#ntUnit').value = 'm'
    document.querySelector('#ntResMode').value = 'explicit-samples'
    document.querySelector('#ntWidth').value = String(WIDTH)
    document.querySelector('#ntHeight').value = String(WIDTH)
    document.querySelector('#ntCols').value = String(COLS)
    document.querySelector('#ntRows').value = String(COLS)
    document.querySelector('#ntTemplate').value = 'blank'
    previewCreation()

    if (mutation === 'create-ignores-columns') {
      // Exactly the pre-fix sequence: build the document, never apply the chosen count.
      newTerrainDocument(false, '', true)
    } else {
      confirmNewTerrain()
    }
    out.afterCreate = { RES, documentSamples: documentSamples(), detail: previewDetail() }

    // --- detail scales the grid without moving the document -----------------------------------
    if (mutation === 'detail-is-absolute') {
      // Treat the control's value as a sample count, which is what the old selector did.
      applyPreviewDetail(1); TARGET_RES = 512
      if (TARGET_RES !== RES) { RES = 512 }
      out.half = { RES, documentSamples: documentSamples(), detail: previewDetail() }
    } else {
      applyPreviewDetail(0.5)
      if (mutation === 'detail-mutates-document') setDocumentSamples(RES)   // the confusion, exactly
      out.half = { RES, documentSamples: documentSamples(), detail: previewDetail() }
    }

    applyPreviewDetail(1)
    out.full = { RES, documentSamples: documentSamples(), detail: previewDetail() }

    const readout = syncDetailReadout()
    const el = document.querySelector('#detailReadout')
    out.readout = { text: el ? el.textContent.trim() : null, ...(readout || {}) }
    return out
  }, mutation)

  const gates = {
    // The author's chosen count reaches the evaluator, not just the WorldDomain.
    createdGridMatchesChosenColumns: report.afterCreate.RES === 300
      && report.afterCreate.documentSamples === 300,
    // Half detail evaluates half the grid...
    halfDetailHalvesTheEvaluatedGrid: report.half.RES === 150 && report.half.detail === 0.5,
    // ...and leaves the DOCUMENT alone. This is the whole distinction.
    halfDetailLeavesTheDocumentGridAlone: report.half.documentSamples === 300,
    // Returning to full restores exactly the document grid — a fraction is reversible, an absolute
    // setting is not, which is the practical difference for an author.
    fullDetailRestoresTheDocumentGrid: report.full.RES === 300 && report.full.documentSamples === 300,
    // The readout must state the physical consequence, not just a percentage. Spacing over 300
    // vertex posts across 6000 m is 6000/299 = 20.07 m.
    readoutStatesSpacingInMetres: !!report.readout.text && /m per sample/.test(report.readout.text)
      && Math.abs(report.readout.spacing - 6000 / 299) < 0.01,
    readoutReportsTheDocumentGrid: report.readout.documentSamples === 300 && report.readout.cols === 300,
    noPageErrors: errors.length === 0,
  }

  let ok = Object.values(gates).every(Boolean)
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  console.log(`${ok ? 'PASS' : 'FAIL'}  preview detail created=${report.afterCreate.RES}/${report.afterCreate.documentSamples} `
    + `half=${report.half.RES}/${report.half.documentSamples} full=${report.full.RES}/${report.full.documentSamples} `
    + `spacing=${report.readout.spacing == null ? 'n/a' : report.readout.spacing.toFixed(2)} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify({ report, gates, errors }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
