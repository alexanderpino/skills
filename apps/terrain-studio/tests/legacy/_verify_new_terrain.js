// S9.2 — New Terrain dialog and hard feasibility preflight.
//
// The story's rule is "no allocation before confirm", and that is a claim about what does NOT
// happen. A gate that only checked the readout text would pass on an implementation that allocates
// the world to measure it — which is precisely today's behaviour: there is no preflight, so asking
// for a raster too large allocates until the tab dies and the author learns by losing their work.
//
// So Float32Array is INSTRUMENTED. Every construction is counted, and the preflight must add zero.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'allocate-during-preflight',
  'accept-invalid-dimensions',
  'reject-instead-of-paging',
  'wrong-terminal-page',
  'confirm-allocates-nothing',
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

;(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', e => { if (e.message !== 'WebSocket closed without opened.') errors.push(e.message) })
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1500)

  const report = await page.evaluate(mutation => {
    USE_GPU = false; RES = 128; TARGET_RES = 128; terrainDef.lattice = 'square'
    const out = { mutation: mutation || null }
    const F = FEASIBILITY_API

    // --- the allocation spy --------------------------------------------------------------------
    // Count every Float32Array construction. The preflight must add ZERO: it is arithmetic on
    // counts and byte sizes, and if it ever needs a buffer to answer, the story has been defeated.
    const RealF32 = Float32Array
    let allocs = 0, allocBytes = 0
    function SpyF32(...args) {
      allocs++
      const inst = new RealF32(...args)
      allocBytes += inst.byteLength
      return inst
    }
    SpyF32.prototype = RealF32.prototype
    SpyF32.BYTES_PER_ELEMENT = RealF32.BYTES_PER_ELEMENT
    SpyF32.from = RealF32.from.bind(RealF32); SpyF32.of = RealF32.of.bind(RealF32)

    const setDims = (cols, rows, w, h) => {
      document.querySelector('#ntCols').value = String(cols)
      document.querySelector('#ntRows').value = String(rows)
      document.querySelector('#ntWidth').value = String(w == null ? 5000 : w)
      document.querySelector('#ntHeight').value = String(h == null ? 5000 : h)
    }

    // Open the dialog and preflight several worlds — including ones far too large to allocate —
    // with the spy installed the whole time.
    openNewTerrainDialog()
    globalThis.Float32Array = SpyF32
    const before = allocs
    const verdicts = []
    for (const [cols, rows] of [[512, 512], [4096, 4096], [16384, 16384], [1573, 13789], [1, 4]]) {
      setDims(cols, rows)
      const p = previewCreation()
      verdicts.push({ cols, rows, mode: p.verdict.mode, code: p.verdict.code, bytes: p.verdict.totalBytes })
    }
    if (mutation === 'allocate-during-preflight') { const junk = new SpyF32(1024); void junk }
    let preflightAllocs = allocs - before
    globalThis.Float32Array = RealF32
    out.preflight = { allocs: preflightAllocs, bytes: allocBytes, verdicts }

    // --- the verdicts themselves ---------------------------------------------------------------
    const byDims = (c, r) => verdicts.find(v => v.cols === c && v.rows === r)
    let invalid = byDims(1, 4)
    if (mutation === 'accept-invalid-dimensions') invalid = { ...invalid, mode: 'monolithic' }
    let huge = F.assessCreation({ sampleCount: { columns: 16384, rows: 16384 }, liveFields: 8 })
    if (mutation === 'reject-instead-of-paging') huge = { ...huge, mode: 'rejected' }
    out.verdicts = {
      smallIsMonolithic: byDims(512, 512).mode === 'monolithic',
      invalidRejected: invalid.mode === 'rejected' && invalid.code === 'DIMENSIONS_INVALID',
      // Over budget is NOT a rejection — that is the entire reason gpu-required-paged exists.
      hugePages: huge.mode === 'gpu-required-paged',
      unaddressableRejected: F.assessCreation({ sampleCount: { columns: 100000, rows: 100000 } }).code === 'EXCEEDS_INDEX',
    }

    // --- page arithmetic, against ADR-009's two named fixtures --------------------------------
    let a = F.decomposePages({ sampleCount: { columns: 16384, rows: 16384 } })
    let b = F.decomposePages({ sampleCount: { columns: 1573, rows: 13789 } })
    if (mutation === 'wrong-terminal-page') a = { ...a, terminalCoreCells: { x: 256, y: 256 } }
    out.pages = {
      a: { grid: a.pagesX + 'x' + a.pagesY, terminal: a.terminalCoreCells, zeroArea: a.zeroAreaPage },
      b: { grid: b.pagesX + 'x' + b.pagesY, terminal: b.terminalCoreCells, zeroArea: b.zeroAreaPage },
      // ADR-009 states these exactly: 64x64 pages with 255 valid cells per terminal axis, and
      // 7x54 pages with a 36x220 terminal core. Independent derivation must agree.
      matchesAdr: a.pagesX === 64 && a.pagesY === 64 && a.terminalCoreCells.x === 255 && a.terminalCoreCells.y === 255
        && b.pagesX === 7 && b.pagesY === 54 && b.terminalCoreCells.x === 36 && b.terminalCoreCells.y === 220,
    }

    // --- confirm DOES allocate, and applies the domain -----------------------------------------
    setDims(256, 384, 8000, 12000)
    previewCreation()
    globalThis.Float32Array = SpyF32
    const beforeConfirm = allocs
    const created = confirmNewTerrain()
    let confirmAllocs = allocs - beforeConfirm
    globalThis.Float32Array = RealF32
    if (mutation === 'confirm-allocates-nothing') confirmAllocs = 0
    const dom = DOMAIN.getWorldDomain()
    out.confirm = {
      created, allocs: confirmAllocs,
      columns: dom.resolution.sampleCount.columns, rows: dom.resolution.sampleCount.rows,
      width: dom.extentM.width, height: dom.extentM.height,
      posting: dom.posting,
      // Independent axes actually applied — the point of the whole sprint.
      independentAxes: dom.resolution.sampleCount.columns !== dom.resolution.sampleCount.rows
        && dom.extentM.width !== dom.extentM.height,
      dialogClosed: document.querySelector('#newTerrainDialog').hidden === true,
    }
    return out
  }, mutation)

  const gates = {
    preflightAllocatesNothing: report.preflight.allocs === 0,
    preflightCoveredEveryCase: report.preflight.verdicts.length === 5,
    smallIsMonolithic: report.verdicts.smallIsMonolithic === true,
    invalidDimensionsRejected: report.verdicts.invalidRejected === true,
    overBudgetPagesRatherThanRejects: report.verdicts.hugePages === true,
    unaddressableRasterRejected: report.verdicts.unaddressableRejected === true,
    pageArithmeticMatchesAdr: report.pages.matchesAdr === true,
    noZeroAreaPage: report.pages.a.zeroArea === false && report.pages.b.zeroArea === false,
    // The converse: confirm must actually build something, or "no allocation before confirm" is
    // trivially satisfied by a button that does nothing.
    confirmDoesAllocate: report.confirm.created === true && report.confirm.allocs > 0,
    confirmAppliesIndependentAxes: report.confirm.independentAxes === true
      && report.confirm.columns === 256 && report.confirm.rows === 384,
    confirmClosesDialog: report.confirm.dialogClosed === true,
    evidenceNonEmpty: report.preflight.verdicts.every(v => typeof v.mode === 'string'),
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — that gate is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  console.log(`${ok ? 'PASS' : 'FAIL'}  new terrain preflightAllocs=${report.preflight.allocs} `
    + `confirmAllocs=${report.confirm.allocs} pages=${report.pages.a.grid}/${report.pages.b.grid} `
    + `domain=${report.confirm.columns}x${report.confirm.rows} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
