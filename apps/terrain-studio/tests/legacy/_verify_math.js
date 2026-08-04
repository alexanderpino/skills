// S8.4 — the Safe Math expression node.
//
// "Safe" is the load-bearing word, and it is a negative claim: an expression must not be able to
// reach a global, construct a function, or run arbitrary code. A gate that only checked "a + b
// gives the right numbers" would pass on a `new Function(expr)` implementation, which is the
// obvious way to build this node and the one that turns a shared terrain document into an
// execution vector. So the escapes are attempted here, explicitly, and must fail.
//
// The other half of S8.4's contract is UNITS: "reject ... unit-incompatible operations". An
// expression is the one place in the app where two fields meet with no wire between them, so it is
// the one place a unit rule can be broken without canConnect ever seeing it. The rules asserted
// below are the ones src/core/expr.js documents, and they are measured against ports.js:
// compatibility is IDENTITY (note 2 there), `dim` is never consulted, and `none` is the
// multiplicative identity rather than a wildcard.
//
// HOW THE CONTROLS WORK, because this project keeps rediscovering the vacuous gate. Every mutation
// here changes PRODUCTION state or PRODUCTION input and lets production compute the answer the
// assertion reads. None of them writes to the oracle's own copy of an answer — the five that used
// to (`r.ok = false`, `tooLarge = null`, `dynamicCode = true`) were the shape just found in
// _verify_variables.js and are rewritten:
//   * the policy and limit tables in src/core/expr.js (EXPR_FUNCTIONS, EXPR_OPERATOR_UNITS,
//     EXPR_UNIT_NAMES, EXPR_LIMITS) are perturbed in place — the parser reads them on every call
//   * the document variable table is perturbed through VARS.setDocumentVariables, which is how a
//     unit reaches an expression at all
//   * the legal-name set handed to the parser is perturbed, which is what an implementation that
//     leaks its enclosing environment would do
//   * the text the static scan reads carries an injected `new Function`, so the scan decides
// One control has no production handle — `/` is a switch arm in evalExpr, not a table entry — so
// divide-by-zero-allowed perturbs the DIVISOR to one that overflows without being zero. Production
// still evaluates and still names the failure; the name it returns is the one a build with no
// specific refusal would return for `a / 0`.
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
  'allow-globals',                    // the parser's legal names become its enclosing environment
  'skip-arity-check',                 // production's own arity table is relaxed to accept min(1)
  'unbounded-size',                   // production's own limit record is raised out of the way
  'divide-by-zero-allowed',           // the divisor overflows instead of being zero (see header)
  'dynamic-code-construction',        // the scanned source carries the defect; the scan decides
  'unit-not-carried',                 // a variable's declared unit never reaches the expression
  'additive-none-is-wildcard',        // `+` treats a dimensionless operand as compatible with all
  'unrepresentable-product-allowed',  // `*` claims a unit for m*m instead of refusing to name it
  'angle-units-conflated',            // sin() accepts degrees — the rad->deg implicit conversion
  'derived-unit-dropped',             // atan2 preserves its operands' unit instead of making rad
  'unit-vocabulary-drift',            // expr.js's unit index gains a name ports.js's UNITS lacks
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

// A defect the static scan must find. It lives in this string, not in production: the scan reads
// src/core/expr.js and src/plugins/comb/mathnode.js, so appending it to the SCANNED TEXT asks
// production's own detector whether it can see one.
const INJECTED_DYNAMIC_CODE = "\nconst compiled = new Function('a', 'return a + 1')\n"

;(async () => {
  // Static half: the source itself must contain no dynamic code construction. This cannot be
  // checked from inside the page, because a Function built there would simply work.
  const exprSrc = fs.readFileSync(path.join(APP, 'src/core/expr.js'), 'utf8')
  const nodeSrc = fs.readFileSync(path.join(APP, 'src/plugins/comb/mathnode.js'), 'utf8')
  const scanned = exprSrc + nodeSrc + (mutation === 'dynamic-code-construction' ? INJECTED_DYNAMIC_CODE : '')
  const dynamicCode = /new\s+Function|[^.\w]eval\s*\(|setTimeout\s*\(\s*['"]/.test(scanned)

  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1400)

  const report = await page.evaluate(async mutation => {
    USE_GPU = false; RES = 32; TARGET_RES = 32; terrainDef.lattice = 'square'
    const out = { mutation: mutation || null }
    const N = RES * RES
    const constant = v => { const f = newField(); f.fill(v); return f }

    // --- reach the production tables ----------------------------------------------------------
    // PORTS_EXPR publishes parseExpr/evalExpr/EXPR_FUNCTIONS; the unit tables are module exports
    // that legacy.js does not republish, so they are reached by importing the same module URL the
    // app imports. `moduleShared` proves it is the SAME instance and not a second copy — four
    // controls below perturb those tables (unbounded-size, additive-none-is-wildcard,
    // unrepresentable-product-allowed, unit-vocabulary-drift), and against a copy they would
    // perturb nothing and the run would go green. That is why it is a gate and not a note.
    let exprModule = null
    try { exprModule = await import(new URL('./src/core/expr.js', location.href).href) }
    catch (e) { out.moduleImportError = String((e && e.message) || e) }
    out.moduleShared = !!exprModule && exprModule.EXPR_FUNCTIONS === PORTS_EXPR.EXPR_FUNCTIONS

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
    // The defect modelled by divide-by-zero-allowed is an evaluator with NO specific refusal, where
    // `a / 0` runs into the finiteness check and comes back named EXPR_NOT_FINITE. `/` is a switch
    // arm with no production handle to turn, so the DIVISOR is perturbed to one that overflows
    // without being zero: production evaluates, production names the failure, and the name it
    // returns is the one the defective build would return for `a / 0`.
    const divisor = mutation === 'divide-by-zero-allowed' ? '1e-320' : '0'
    const attempts = [
      ['window', 'EXPR_UNKNOWN_NAME'],
      ['globalThis', 'EXPR_UNKNOWN_NAME'],
      ['document', 'EXPR_UNKNOWN_NAME'],
      ['fetch(1)', 'EXPR_UNKNOWN_FUNCTION'],
      ['constructor', 'EXPR_UNKNOWN_NAME'],
      ['nodes', 'EXPR_UNKNOWN_NAME'],
      ['min(1)', 'EXPR_ARITY'],
      [`a / ${divisor}`, 'EXPR_DIVIDE_BY_ZERO'],
    ]
    // PRODUCTION-SIDE. The defect modelled is an implementation that hands the expression its
    // ENCLOSING ENVIRONMENT'S names instead of an explicit allowlist — what every `with`-scope or
    // `new Function` version of this node does by construction. Production then resolves `window`
    // as an ordinary name and refuses nothing; nothing here overwrites a computed answer.
    const legalNames = mutation === 'allow-globals'
      ? ['a', 'b', 'c', 'x', 'y', 'i', 'window', 'globalThis', 'document', 'constructor', 'nodes']
      : ['a', 'b', 'c', 'x', 'y', 'i']
    // PRODUCTION-SIDE. Arity lives in EXPR_FUNCTIONS, which the parser reads on every call; a
    // declared arity of 1 for min() is exactly the table a build without the check would have.
    if (mutation === 'skip-arity-check') PORTS_EXPR.EXPR_FUNCTIONS.min.arity = 1
    const refused = []
    for (const [src, want] of attempts) {
      let code = null
      try {
        const parsed = PORTS_EXPR.parseExpr(src, { names: legalNames })
        PORTS_EXPR.evalExpr(parsed.ast, { a: 1, b: 1, c: 1, x: 0, y: 0, i: 0 })
      } catch (e) { code = e.code || String(e) }
      refused.push({ src, want, got: code, ok: code === want })
    }
    if (mutation === 'skip-arity-check') PORTS_EXPR.EXPR_FUNCTIONS.min.arity = 2   // restore: later gates use min()
    out.refused = refused

    // --- bounds -------------------------------------------------------------------------------
    // PRODUCTION-SIDE. EXPR_LIMITS is the record the parser reads on every call; raising it is the
    // build that declared a bound and never enforced one. Production then parses 400 terms and 60
    // parens happily and returns no code at all.
    if (mutation === 'unbounded-size' && exprModule && exprModule.EXPR_LIMITS) {
      exprModule.EXPR_LIMITS.maxNodes = 1e9
      exprModule.EXPR_LIMITS.maxDepth = 1e9
    }
    let tooLarge = null, tooDeep = null
    try { PORTS_EXPR.parseExpr('1' + '+1'.repeat(400), { names: [] }) } catch (e) { tooLarge = e.code }
    try { PORTS_EXPR.parseExpr('('.repeat(60) + '1' + ')'.repeat(60), { names: [] }) } catch (e) { tooDeep = e.code }
    out.bounds = { tooLarge, tooDeep, limits: exprModule && exprModule.EXPR_LIMITS ? { ...exprModule.EXPR_LIMITS } : null }

    // An unparseable expression must yield a zero field, not throw and not corrupt the graph.
    const broken = run('a +', A, B, C)
    out.brokenExpressionSafe = broken.length === N && broken.every(v => v === 0)

    // ==========================================================================================
    // UNITS
    // ==========================================================================================
    // The vocabulary is ports.js's UNITS and the rule is IDENTITY, not dimensional equality. The
    // fixture states its own evidence: K and degC have the SAME `dim`, so a checker that compared
    // dimensions would accept `kelvin + celsius`, and ADR-002's "no implicit unit conversions"
    // would be false inside the one node where two fields meet without a wire.
    const unitNames = ['hM', 'h2M', 'tC', 'kT', 'angDeg', 'angRad', 'w', 'a', 'b', 'c', 'x', 'y', 'i']
    const unitMap = { hM: 'm', h2M: 'm', tC: 'degC', kT: 'K', angDeg: 'deg', angRad: 'rad', w: 'none' }
    // PRODUCTION-SIDE. sin() takes radians; a `deg` argument must be refused rather than converted.
    // The defect modelled is the one ports.js note 2 names outright — treating rad and deg as the
    // same thing — and it is injected as the unit POLICY production reads for sin, not as an answer.
    if (mutation === 'angle-units-conflated') PORTS_EXPR.EXPR_FUNCTIONS.sin.units = 'scalarize'
    // PRODUCTION-SIDE. atan2 of two lengths is an angle; 'identity' is what a build that simply
    // forwarded its operands' unit would declare.
    if (mutation === 'derived-unit-dropped') PORTS_EXPR.EXPR_FUNCTIONS.atan2.units = 'identity'
    if (exprModule && exprModule.EXPR_OPERATOR_UNITS) {
      // PRODUCTION-SIDE. 'scale' is the tempting rule for `+`: it treats a dimensionless operand as
      // compatible with anything, which is precisely how `heightM + 2` slips through.
      if (mutation === 'additive-none-is-wildcard') exprModule.EXPR_OPERATOR_UNITS['+'].policy = 'scale'
      // PRODUCTION-SIDE. 'identity' makes m*m come back as m — a unit invented rather than refused.
      if (mutation === 'unrepresentable-product-allowed') exprModule.EXPR_OPERATOR_UNITS['*'].policy = 'identity'
    }
    // PRODUCTION-SIDE. expr.js indexes ports.js's UNITS; a name in the index that ports.js does not
    // have is the drift a second, hand-maintained list would produce.
    if (mutation === 'unit-vocabulary-drift' && exprModule && exprModule.EXPR_UNIT_NAMES) {
      exprModule.EXPR_UNIT_NAMES.add('furlongs')
    }

    const unitOf = src => {
      try { return { unit: PORTS_EXPR.parseExpr(src, { names: unitNames, units: unitMap }).unit, code: null } }
      catch (e) { return { unit: null, code: e.code || String(e) } }
    }

    // Derivation: what unit does an expression carry out? Every row is a rule from expr.js.
    const derivation = [
      ['hM + h2M', 'm'], ['2 * hM', 'm'], ['hM * 2', 'm'], ['hM / 2', 'm'], ['hM / h2M', 'none'],
      ['-hM', 'm'], ['abs(hM)', 'm'], ['floor(hM)', 'm'], ['min(hM, h2M)', 'm'],
      ['clamp(hM, h2M, hM)', 'm'], ['lerp(hM, h2M, w)', 'm'], ['w ? hM : h2M', 'm'],
      ['sign(hM)', 'none'], ['step(hM, h2M)', 'none'], ['hM < h2M', 'none'], ['tC == tC', 'none'],
      ['atan2(hM, h2M)', 'rad'], ['sin(angRad)', 'none'],
    ].map(([src, want]) => { const got = unitOf(src); return { src, want, got: got.unit, code: got.code, ok: got.unit === want } })
    out.derivation = derivation

    // Refusals: each must carry its OWN code, because each needs a different fix.
    const unitRefusals = [
      ['hM + tC', 'EXPR_UNIT_MISMATCH'],       // two units that do not match
      ['kT + tC', 'EXPR_UNIT_MISMATCH'],       // identity, not dimension: same dim, still refused
      ['hM + 2', 'EXPR_UNIT_MISMATCH'],        // `none` is not a wildcard under +
      ['hM - w', 'EXPR_UNIT_MISMATCH'],
      ['min(hM, tC)', 'EXPR_UNIT_MISMATCH'],
      ['hM * h2M', 'EXPR_UNIT_UNREPRESENTABLE'], // m*m has no name in UNITS
      ['2 / hM', 'EXPR_UNIT_UNREPRESENTABLE'],   // nor does 1/m
      ['sin(angDeg)', 'EXPR_UNIT_DOMAIN'],       // rad->deg is a refusal, not a conversion
      ['sqrt(hM)', 'EXPR_UNIT_DOMAIN'],
      ['hM ^ 2', 'EXPR_UNIT_DOMAIN'],
      ['lerp(hM, h2M, hM)', 'EXPR_UNIT_DOMAIN'], // a blend factor is a weight
      ['hM ? 1 : 0', 'EXPR_UNIT_DOMAIN'],        // a truth value is dimensionless
    ].map(([src, want]) => { const got = unitOf(src); return { src, want, got: got.code, ok: got.code === want } })
    out.unitRefusals = unitRefusals

    // The dimensional evidence, measured rather than asserted from memory.
    out.dimensions = { degC: PORTS.UNITS.degC.dim, K: PORTS.UNITS.K.dim, rad: PORTS.UNITS.rad.dim, deg: PORTS.UNITS.deg.dim }

    // A unit the vocabulary does not have is a named failure, not a silent dimensionless.
    let unknownUnit = null
    try { PORTS_EXPR.parseExpr('hM', { names: unitNames, units: { hM: 'furlongs' } }) } catch (e) { unknownUnit = e.code }
    out.unknownUnit = unknownUnit

    // INERTNESS. Every expression that could be written before units existed must still parse, and
    // still derive `none`. This is what makes the check safe to add to a shipped node — and it is
    // the gate that catches a table entry added without a unit policy, since an unknown policy is
    // refused rather than waved through.
    const inertCorpus = ['a + b', 'a * b', 'a / b', 'a - b', 'a % b', 'a ^ b', 'sqrt(a)', 'exp(a)',
      'log(a + 1)', 'sin(a)', 'cos(a)', 'tan(a)', 'atan2(a, b)', 'pow(a, b)', 'sign(a)', 'abs(a)',
      'min(a, b)', 'max(a, b)', 'clamp(a, b, c)', 'lerp(a, b, c)', 'step(a, b)', 'floor(a)',
      'ceil(a)', 'round(a)', 'a < b', 'a == b', 'a ? b : c', 'pi * a', 'x * y + i', '-a']
      .map(src => { const got = unitOf(src); return { src, unit: got.unit, code: got.code, ok: got.unit === 'none' && got.code === null } })
    out.inert = inertCorpus

    // --- through the real node ----------------------------------------------------------------
    // A unit only matters if it reaches the node. The document variable table is where one enters
    // an expression, and resolvePorts is where it leaves.
    const VARS_FIXTURE = [
      { id: 'seaLevelM', name: 'Sea level', value: 120, unit: 'm' },
      { id: 'baseLevelM', name: 'Base level', value: 40, unit: 'm' },
      { id: 'airTempC', name: 'Air temperature', value: 12, unit: 'degC' },
      { id: 'slopeDeg', name: 'Slope', value: 30, unit: 'deg' },
      { id: 'gain', name: 'Gain', value: 2, unit: 'none' },
    ]
    // PRODUCTION-SIDE. The defect modelled is S8.3's, one layer along: a declared unit that never
    // reaches its consumer. With every variable dimensionless the node's own parse sees two pure
    // numbers and — correctly, for that input — refuses nothing and derives `none`. Production
    // computes both readings below; nothing here edits them.
    const declared = mutation === 'unit-not-carried'
      ? VARS_FIXTURE.map(v => ({ ...v, unit: 'none' }))
      : VARS_FIXTURE
    out.varProblems = VARS.setDocumentVariables(declared)

    const nodeUnit = expr => {
      try { return TYPES.mathnode.resolvePorts({ type: 'mathnode', params: { expr } }).outputs[0].unit }
      catch (e) { return String(e && e.message) }
    }
    const nodeInfo = expr => {
      try { return TYPES.mathnode.info({ type: 'mathnode', params: { expr } }) } catch (e) { return String(e && e.message) }
    }
    out.node = {
      plainUnit: nodeUnit('a'),                       // no variable: dimensionless, as declared
      metreUnit: nodeUnit('2 * seaLevelM'),           // scaled metres are metres
      ratioUnit: nodeUnit('seaLevelM / baseLevelM'),  // metres cancel
      mismatchUnit: nodeUnit('seaLevelM + airTempC'), // refused -> zero field -> dimensionless
      mismatchInfo: nodeInfo('seaLevelM + airTempC'),
      okInfo: nodeInfo('2 * seaLevelM'),
      // The variable is READ, not merely typed: value 120 scaled by 2.
      metreValue: run('2 * seaLevelM', A, B, C)[0],
      // A refused expression yields a zero field, exactly as a syntax error does.
      mismatchField: (f => f.length === N && f.every(v => v === 0))(run('seaLevelM + airTempC', A, B, C)),
      // A built-in name wins over a variable of the same id — the node's port label is a promise.
      builtinWins: (() => {
        const problems = VARS.setDocumentVariables([...declared, { id: 'a', name: 'Shadow', value: 99, unit: 'none' }])
        const v = run('a', A, B, C)[0]
        VARS.setDocumentVariables(declared)
        return problems.length === 0 && Math.abs(v - 0.25) < 1e-9
      })(),
    }

    // And the consequence: a metre-carrying Math output must be refused by a mask input, whose
    // unitPolicy 'none-only' exists for exactly this. Production's canConnect decides.
    const metrePort = { ...TYPES.mathnode.resolvePorts({ type: 'mathnode', params: { expr: '2 * seaLevelM' } }).outputs[0], name: 'Out' }
    const plainPort = TYPES.mathnode.resolvePorts({ type: 'mathnode', params: { expr: 'a' } }).outputs[0]
    const maskPort = (TYPES.blur.inputs || []).find(p => p.semantic === 'anyMask')
    const intoMask = PORTS.canConnect(metrePort, maskPort)
    const plainIntoMask = PORTS.canConnect(plainPort, maskPort)
    out.wire = {
      maskPortFound: !!maskPort,
      metreRefused: intoMask.ok === false && intoMask.code === 'UNIT_MISMATCH',
      plainAccepted: plainIntoMask.ok === true,
      reason: intoMask.reason || null,
    }
    return out
  }, mutation)

  const every = (list, key) => Array.isArray(list) && list.length > 0 && list.every(r => r[key] === true)

  const gates = {
    arithmeticCorrect: every(report.arithmetic, 'allMatch'),
    positionalInputsSpanUnit: report.positional.spans === true,
    escapesRefused: every(report.refused, 'ok'),
    boundedSize: report.bounds.tooLarge === 'EXPR_TOO_LARGE',
    boundedDepth: report.bounds.tooDeep === 'EXPR_TOO_DEEP',
    // The static half. A parser cannot prove its own safety from inside the page.
    noDynamicCodeConstruction: dynamicCode === false,
    unparseableYieldsZeroField: report.brokenExpressionSafe === true,
    // Three controls perturb the production unit tables through this module handle. If it is not
    // the same instance the app runs, those controls are inert and everything below is theatre.
    productionTablesReachable: report.moduleShared === true,
    // --- units ---
    unitDerivationCorrect: every(report.derivation, 'ok'),
    unitRefusalsNamed: every(report.unitRefusals, 'ok'),
    // Identity, not dimensional equality — asserted together with the measurement that makes it a
    // real distinction: degC and K share a dim, and `kT + tC` is still refused.
    identityNotDimension: report.dimensions.degC === report.dimensions.K
      && report.dimensions.rad === report.dimensions.deg
      && (report.unitRefusals.find(r => r.src === 'kT + tC') || {}).got === 'EXPR_UNIT_MISMATCH'
      && (report.unitRefusals.find(r => r.src === 'sin(angDeg)') || {}).got === 'EXPR_UNIT_DOMAIN',
    unknownUnitRefused: report.unknownUnit === 'EXPR_UNIT_UNKNOWN',
    unitlessExpressionsInert: every(report.inert, 'ok'),
    variableFixtureAccepted: Array.isArray(report.varProblems) && report.varProblems.length === 0,
    nodeCarriesDerivedUnit: report.node.plainUnit === 'none' && report.node.metreUnit === 'm'
      && report.node.ratioUnit === 'none' && report.node.mismatchUnit === 'none'
      && /EXPR_UNIT_MISMATCH/.test(String(report.node.mismatchInfo))
      && /result in m/.test(String(report.node.okInfo)),
    nodeEvaluatesVariables: Math.abs(report.node.metreValue - 240) < 1e-6
      && report.node.mismatchField === true && report.node.builtinWins === true,
    derivedUnitReachesTheWire: report.wire.maskPortFound === true
      && report.wire.metreRefused === true && report.wire.plainAccepted === true,
    evidenceNonEmpty: report.arithmetic.length >= 8 && report.refused.length >= 8
      && report.derivation.length >= 18 && report.unitRefusals.length >= 12 && report.inert.length >= 30,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — that gate is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  console.log(`${ok ? 'PASS' : 'FAIL'}  math arithmetic=${report.arithmetic.filter(c => c.allMatch).length}/${report.arithmetic.length} `
    + `refused=${report.refused.filter(r => r.ok).length}/${report.refused.length} `
    + `units derived=${report.derivation.filter(r => r.ok).length}/${report.derivation.length} `
    + `refusals=${report.unitRefusals.filter(r => r.ok).length}/${report.unitRefusals.length} `
    + `inert=${report.inert.filter(r => r.ok).length}/${report.inert.length} `
    + `nodeUnits=${report.node.plainUnit}/${report.node.metreUnit}/${report.node.ratioUnit} `
    + `dynamicCode=${dynamicCode} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, dynamicCode, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
