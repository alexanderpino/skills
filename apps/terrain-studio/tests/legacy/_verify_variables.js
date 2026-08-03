// S8.3 — typed graph variables and lexical scope.
//
// The property that makes variables worth having is that a RENAME IS SAFE. References are by
// stable id, so changing a variable's display name must not move a single sample of terrain. A
// name-keyed implementation breaks every reference on a rename, and the breakage looks like a
// terrain change rather than a rename — which is the failure this asserts against directly, by
// renaming and comparing field digests.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'rename-breaks-reference',
  'accept-nonfinite-value',
  'accept-duplicate-id',
  'inner-frame-does-not-shadow',
  'variables-not-persisted',
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
    USE_GPU = false; RES = 32; TARGET_RES = 32; terrainDef.lattice = 'square'
    const out = { mutation: mutation || null }
    const N = RES * RES
    const digest = f => { let a = 0x811c9dc5; for (let i = 0; i < f.length; i++) { a = (a ^ (Math.round(f[i] * 1e7) | 0)) >>> 0; a = Math.imul(a, 16777619) >>> 0 } return a.toString(16) }

    // --- a rename must not move terrain -------------------------------------------------------
    VARS.setDocumentVariables([{ id: 'probeVar', name: 'Original name', value: 0.4, unit: 'none' }])
    const nd = { params: { varId: 'probeVar' }, type: 'variable' }
    const before = digest(TYPES.variable.eval(nd.params, [], nd))
    VARS.setDocumentVariables([{ id: 'probeVar', name: 'Completely different name', value: 0.4, unit: 'none' }])
    let after = digest(TYPES.variable.eval(nd.params, [], nd))
    if (mutation === 'rename-breaks-reference') after = 'moved'
    out.rename = { before, after, unchanged: before === after }

    // Changing the VALUE must move it — otherwise the node is not reading the variable at all,
    // and "rename is safe" would be true of a constant.
    VARS.setDocumentVariables([{ id: 'probeVar', name: 'Original name', value: 0.9, unit: 'none' }])
    const changed = digest(TYPES.variable.eval(nd.params, [], nd))
    out.valueChangeMoves = changed !== before

    // An unknown id yields zero rather than throwing: deleting a variable must leave a graph that
    // still opens and still renders.
    const missing = TYPES.variable.eval({ varId: 'noSuchVariable' }, [], { params: {} })
    out.unknownIdSafe = missing.length === N && missing.every(v => v === 0)

    // --- validation ---------------------------------------------------------------------------
    const codes = list => VARS.validateVariables(list).map(p => p.code)
    let nonFinite = codes([{ id: 'a', name: 'A', value: NaN, unit: 'none' }])
    let dupe = codes([{ id: 'a', name: 'A', value: 1, unit: 'none' }, { id: 'a', name: 'B', value: 2, unit: 'none' }])
    if (mutation === 'accept-nonfinite-value') nonFinite = []
    if (mutation === 'accept-duplicate-id') dupe = []
    out.validation = {
      nonFinite, dupe,
      badId: codes([{ id: '9bad', name: 'X', value: 1, unit: 'none' }]),
      badUnit: codes([{ id: 'a', name: 'A', value: 1, unit: 'furlongs' }]),
      emptyName: codes([{ id: 'a', name: '   ', value: 1, unit: 'none' }]),
      goodAccepted: codes([{ id: 'seaLevel', name: 'Sea level', value: 0.3, unit: 'm' }]).length === 0,
    }
    // A refused table must not be half-applied.
    VARS.setDocumentVariables([{ id: 'keeper', name: 'Keeper', value: 0.5, unit: 'none' }])
    VARS.setDocumentVariables([{ id: 'keeper', name: 'Keeper', value: 0.7, unit: 'none' }, { id: 'bad', name: 'Bad', value: Infinity, unit: 'none' }])
    const survivor = VARS.getDocumentVariables()
    out.refusedTableNotApplied = survivor.length === 1 && survivor[0].value === 0.5

    // --- lexical scope: an inner frame shadows an outer one -----------------------------------
    const scope = VARS.makeScope([
      { name: 'document', variables: [{ id: 'shared', name: 'Outer', value: 1, unit: 'none' }, { id: 'onlyOuter', name: 'Outer only', value: 3, unit: 'none' }] },
      { name: 'subgraph', variables: [{ id: 'shared', name: 'Inner', value: 2, unit: 'none' }] },
    ])
    const shared = scope.lookup('shared')
    out.scope = {
      depth: scope.depth,
      // Innermost wins — the frame that defines it last.
      shadowedValue: mutation === 'inner-frame-does-not-shadow' ? 1 : (shared ? shared.variable.value : null),
      outerStillVisible: (scope.lookup('onlyOuter') || {}).variable?.value === 3,
      idsUnion: scope.ids().join(','),
      unknownThrows: (() => { try { VARS.requireVariable(scope, 'nope'); return null } catch (e) { return e.code } })(),
    }

    // --- persistence ---------------------------------------------------------------------------
    blankGraph()
    VARS.setDocumentVariables([{ id: 'persisted', name: 'Persisted', value: 0.625, unit: 'm' }])
    let text = saveProjectText()
    if (mutation === 'variables-not-persisted') text = text.replace(/"variables":\s*\[[\s\S]*?\],?\n/, '')
    VARS.setDocumentVariables([{ id: 'persisted', name: 'Persisted', value: 0.1, unit: 'm' }])
    let loadErr = null
    try { loadProjectText(text) } catch (e) { loadErr = e.code || String(e) }
    const restored = VARS.getDocumentVariables().find(v => v.id === 'persisted')
    out.persistence = {
      loadErr,
      restoredValue: restored ? restored.value : null,
      roundTrips: !!restored && restored.value === 0.625 && restored.unit === 'm' && restored.name === 'Persisted',
    }
    return out
  }, mutation)

  const gates = {
    renameDoesNotMoveTerrain: report.rename.unchanged === true,
    valueChangeDoesMoveTerrain: report.valueChangeMoves === true,
    unknownIdYieldsZeroField: report.unknownIdSafe === true,
    nonFiniteRefused: report.validation.nonFinite.includes('VAR_VALUE_NOT_FINITE'),
    duplicateIdRefused: report.validation.dupe.includes('VAR_ID_DUPLICATE'),
    badIdRefused: report.validation.badId.includes('VAR_ID_INVALID'),
    badUnitRefused: report.validation.badUnit.includes('VAR_UNIT_UNKNOWN'),
    emptyNameRefused: report.validation.emptyName.includes('VAR_NAME_EMPTY'),
    validTableAccepted: report.validation.goodAccepted === true,
    refusedTableNotHalfApplied: report.refusedTableNotApplied === true,
    innerFrameShadowsOuter: report.scope.shadowedValue === 2 && report.scope.outerStillVisible === true,
    unknownVariableThrowsNamed: report.scope.unknownThrows === 'VAR_UNKNOWN',
    variablesRoundTrip: report.persistence.roundTrips === true,
    evidenceNonEmpty: report.scope.depth === 2 && report.scope.idsUnion.length > 0,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — that gate is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  console.log(`${ok ? 'PASS' : 'FAIL'}  variables rename=${report.rename.unchanged} shadow=${report.scope.shadowedValue} `
    + `restored=${report.persistence.restoredValue} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
