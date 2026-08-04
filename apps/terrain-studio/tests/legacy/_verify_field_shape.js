// Recovering a field's WIDTH from its length, on both lattices.
//
// A bare Float32Array carries no shape, so a node handed one has to work out how wide it is. The
// obvious `Math.round(Math.sqrt(N))` is exact on square and WRONG on hex, where the field is
// RES x round(RES*2/sqrt(3)) and the cell count is never a perfect square. At RES 512 the guess
// returns 550 against a real width of 512 — measured in d_windmodify, where it made the divergence
// sum and the mass-consistency projection read across row boundaries. Every sample stayed finite,
// which is exactly why nothing caught it: the wind was simply wrong, quietly, on hex.
//
// fieldW() is not the answer either, and that was the first attempt at a fix: a node may legitimately
// be evaluated on a field that is NOT the working grid — atFeatureScale coarsens, and oracles pass
// fixtures of their own size — so the width has to come from the field itself. Using fieldW() turned
// _verify_wind.js red immediately, which is how the mistake was caught.
//
// This gate pins both halves: the recovery is exact across a range of widths on both lattices, and
// it does not silently invent a width for a length that no field of this lattice could have.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'sqrt-of-length',      // the defect itself: assume the field is square
  'working-grid-width',  // the first wrong fix: assume the field is the working grid
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
    const out = { square: [], hex: [], nonsense: null }
    // The rival readings, so the gate measures a difference rather than asserting a design.
    const recover = (N, real) => {
      if (mutation === 'sqrt-of-length') return Math.round(Math.sqrt(N))
      if (mutation === 'working-grid-width') return fieldW()
      return widthForLength(N)
    }
    const WIDTHS = [64, 100, 128, 192, 256, 333, 512]
    for (const lattice of ['square', 'hex']) {
      terrainDef.lattice = lattice
      for (const w of WIDTHS) {
        // latticeRows is production's own row rule — the same one fieldH() uses — so the fixture
        // length is built exactly as a real field of this width would be.
        const rows = latticeRows(w), N = w * rows
        out[lattice].push({ w, rows, N, got: recover(N, w), ok: recover(N, w) === w })
      }
    }
    // A length no field of this lattice could have must NOT get a confident answer. 7 is prime and
    // is not w * latticeRows(w) for any w > 1 on either lattice.
    terrainDef.lattice = 'hex'
    out.nonsense = { N: 7, got: widthForLength(7), workingGrid: fieldW() }
    terrainDef.lattice = 'square'
    return out
  }, mutation)

  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }

  const badSquare = report.square.filter(r => !r.ok)
  const badHex = report.hex.filter(r => !r.ok)
  check('every square width recovered exactly', badSquare.length === 0,
    badSquare.map(r => `${r.w}->${r.got}`).join(','))
  check('every hex width recovered exactly', badHex.length === 0,
    badHex.map(r => `${r.w}->${r.got}`).join(','))
  // Absence of evidence: a corpus that compared nothing, or one where hex and square agree at every
  // width, would prove nothing about the lattice-specific case this exists for.
  check('corpus non-empty', report.square.length >= 5 && report.hex.length >= 5, report.square.length)
  check('hex genuinely differs from a square assumption', report.hex.some(r => Math.round(Math.sqrt(r.N)) !== r.w),
    report.hex.map(r => `${r.w}:sqrt=${Math.round(Math.sqrt(r.N))}`).join(' '))
  check('an impossible length falls back to the working grid rather than inventing one',
    report.nonsense.got === report.nonsense.workingGrid, report.nonsense)
  check('no page errors', errors.length === 0, errors)

  let ok = assertions.every(a => a.ok)
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = assertions.filter(a => !a.ok).map(a => a.name)
  console.log(`${ok ? 'PASS' : 'FAIL'}  field shape square=${report.square.length - badSquare.length}/${report.square.length} `
    + `hex=${report.hex.length - badHex.length}/${report.hex.length} `
    + `hexSqrtWouldGive=${report.hex.map(r => Math.round(Math.sqrt(r.N))).join('/')} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify({ report, failed: assertions.filter(a => !a.ok) }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
