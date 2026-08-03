// S8.4 — the Safe Math expression node.
//
// "Safe" is the load-bearing word, and it is a negative claim: an expression must not be able to
// reach a global, construct a function, or run arbitrary code. A gate that only checked "a + b
// gives the right numbers" would pass on a `new Function(expr)` implementation, which is the
// obvious way to build this node and the one that turns a shared terrain document into an
// execution vector. So the escapes are attempted here, explicitly, and must fail.
const { chromium } = require('playwright-core')
const path = require('path')
const fs = require('fs')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))
const APP = path.resolve(__dirname, '../..')

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'allow-globals',
  'skip-arity-check',
  'unbounded-size',
  'divide-by-zero-allowed',
  'dynamic-code-construction',
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

;(async () => {
  // Static half: the source itself must contain no dynamic code construction. This cannot be
  // checked from inside the page, because a Function built there would simply work.
  const exprSrc = fs.readFileSync(path.join(APP, 'src/core/expr.js'), 'utf8')
  const nodeSrc = fs.readFileSync(path.join(APP, 'src/plugins/comb/mathnode.js'), 'utf8')
  let dynamicCode = /new\s+Function|[^.\w]eval\s*\(|setTimeout\s*\(\s*['"]/.test(exprSrc + nodeSrc)
  if (mutation === 'dynamic-code-construction') dynamicCode = true

  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1400)

  const report = await page.evaluate(mutation => {
    USE_GPU = false; RES = 32; TARGET_RES = 32; terrainDef.lattice = 'square'
    const out = { mutation: mutation || null }
    const N = RES * RES
    const constant = v => { const f = newField(); f.fill(v); return f }

    // --- arithmetic, through the real node ----------------------------------------------------
    const run = (expr, a, b, c) => {
      const nd = { params: { expr }, type: 'mathnode' }
      return TYPES.mathnode.eval(nd.params, [a, b, c], nd)
    }
    const A = constant(0.25), B = constant(0.5), C = constant(2)
    const cases = [
      ['a + b', 0.75], ['a * 4', 1], ['max(a, b)', 0.5], ['clamp(c, 0, 1)', 1],
      ['a > b ? 1 : 0', 0], ['lerp(a, b, 0.5)', 0.375], ['abs(0 - b)', 0.5], ['2 ^ 3', 8],
    ]
    out.arithmetic = cases.map(([expr, want]) => {
      const f = run(expr, A, B, C)
      let match = 0
      for (let i = 0; i < N; i++) if (Math.abs(f[i] - want) < 1e-6) match++
      return { expr, want, allMatch: match === N }
    })

    // x and y must span [0,1] across the field — the positional inputs.
    const xf = run('x', A, B, C)
    out.positional = { x0: xf[0], xLast: xf[RES - 1], spans: Math.abs(xf[0]) < 1e-6 && Math.abs(xf[RES - 1] - 1) < 1e-6 }

    // --- the escapes, attempted ---------------------------------------------------------------
    // Each of these must be refused at PARSE time with a named code, not silently evaluated.
    const attempts = [
      ['window', 'EXPR_UNKNOWN_NAME'],
      ['globalThis', 'EXPR_UNKNOWN_NAME'],
      ['document', 'EXPR_UNKNOWN_NAME'],
      ['fetch(1)', 'EXPR_UNKNOWN_FUNCTION'],
      ['constructor', 'EXPR_UNKNOWN_NAME'],
      ['nodes', 'EXPR_UNKNOWN_NAME'],
      ['min(1)', 'EXPR_ARITY'],
      ['a / 0', 'EXPR_DIVIDE_BY_ZERO'],
    ]
    const refused = []
    for (const [src, want] of attempts) {
      let code = null
      try {
        const parsed = PORTS_EXPR.parseExpr(src, { names: ['a', 'b', 'c', 'x', 'y', 'i'] })
        PORTS_EXPR.evalExpr(parsed.ast, { a: 1, b: 1, c: 1, x: 0, y: 0, i: 0 })
      } catch (e) { code = e.code || String(e) }
      refused.push({ src, want, got: code, ok: code === want })
    }
    if (mutation === 'allow-globals') { const r = refused.find(x => x.src === 'window'); if (r) r.ok = false }
    if (mutation === 'skip-arity-check') { const r = refused.find(x => x.src === 'min(1)'); if (r) r.ok = false }
    if (mutation === 'divide-by-zero-allowed') { const r = refused.find(x => x.src === 'a / 0'); if (r) r.ok = false }
    out.refused = refused

    // --- bounds -------------------------------------------------------------------------------
    let tooLarge = null, tooDeep = null
    try { PORTS_EXPR.parseExpr('1' + '+1'.repeat(400), { names: [] }) } catch (e) { tooLarge = e.code }
    try { PORTS_EXPR.parseExpr('('.repeat(60) + '1' + ')'.repeat(60), { names: [] }) } catch (e) { tooDeep = e.code }
    if (mutation === 'unbounded-size') { tooLarge = null; tooDeep = null }
    out.bounds = { tooLarge, tooDeep }

    // An unparseable expression must yield a zero field, not throw and not corrupt the graph.
    const broken = run('a +', A, B, C)
    out.brokenExpressionSafe = broken.length === N && broken.every(v => v === 0)
    return out
  }, mutation)

  const gates = {
    arithmeticCorrect: report.arithmetic.every(c => c.allMatch === true),
    positionalInputsSpanUnit: report.positional.spans === true,
    escapesRefused: report.refused.every(r => r.ok === true),
    boundedSize: report.bounds.tooLarge === 'EXPR_TOO_LARGE',
    boundedDepth: report.bounds.tooDeep === 'EXPR_TOO_DEEP',
    // The static half. A parser cannot prove its own safety from inside the page.
    noDynamicCodeConstruction: dynamicCode === false,
    unparseableYieldsZeroField: report.brokenExpressionSafe === true,
    evidenceNonEmpty: report.arithmetic.length >= 8 && report.refused.length >= 8,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — that gate is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  console.log(`${ok ? 'PASS' : 'FAIL'}  math arithmetic=${report.arithmetic.filter(c => c.allMatch).length}/${report.arithmetic.length} `
    + `refused=${report.refused.filter(r => r.ok).length}/${report.refused.length} dynamicCode=${dynamicCode} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, dynamicCode, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
