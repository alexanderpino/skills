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
  'unit-not-carried',        // a metres variable presents as dimensionless and wires into a mask
  'variable-edit-not-undoable', // a variable edit survives undo
  'instance-override-ignored',  // both subgraph instances read the document value
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
    // PRODUCTION-SIDE. This used to assign the string 'moved' to a local — the oracle overwriting
    // its own computed answer, which models no implementation and is the exact vacuous shape this
    // project keeps rediscovering. The story's named failure is "a name-keyed fixture breaks on
    // rename", so the mutation now looks the variable up BY NAME, which is what a name-keyed
    // implementation would do, and reads a different variable after the rename.
    if (mutation === 'rename-breaks-reference') {
      const byName = VARS.getDocumentVariables().find(v => v.name === 'Original name')
      after = digest(TYPES.variable.eval({ varId: byName ? byName.id : 'missingAfterRename' }, [], { params: {} }))
    }
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
    // Perturb the INPUT so production's validator is what decides, rather than blanking the result.
    if (mutation === 'accept-nonfinite-value') nonFinite = codes([{ id: 'a', name: 'A', value: 1, unit: 'none' }])
    if (mutation === 'accept-duplicate-id') dupe = codes([{ id: 'a', name: 'A', value: 1, unit: 'none' }, { id: 'b', name: 'B', value: 2, unit: 'none' }])
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
    // makeScope's own contract, tested by DROPPING the inner frame rather than by overwriting the
    // answer. The production equivalent of this claim is `instance-override-ignored` below, which
    // drives a real subgraph; this one keeps makeScope honest as a library, and it can now fail.
    const frames = [
      { name: 'document', variables: [{ id: 'shared', name: 'Outer', value: 1, unit: 'none' }, { id: 'onlyOuter', name: 'Outer only', value: 3, unit: 'none' }] },
      { name: 'subgraph', variables: [{ id: 'shared', name: 'Inner', value: 2, unit: 'none' }] },
    ]
    const scope = VARS.makeScope(mutation === 'inner-frame-does-not-shadow' ? [frames[0]] : frames)
    const shared = scope.lookup('shared')
    out.scope = {
      depth: scope.depth,
      // Innermost wins — the frame that defines it last.
      shadowedValue: shared ? shared.variable.value : null,
      outerStillVisible: (scope.lookup('onlyOuter') || {}).variable?.value === 3,
      idsUnion: scope.ids().join(','),
      unknownThrows: (() => { try { VARS.requireVariable(scope, 'nope'); return null } catch (e) { return e.code } })(),
    }

    // --- UNITS ARE CARRIED, so the type system can refuse a mismatch -------------------------
    // The Variable output port hard-coded unit:'none' regardless of what the variable declared, so
    // a value in metres presented as dimensionless and wired straight into an `anyMask` port —
    // whose unitPolicy 'none-only' exists precisely to refuse that. The declaration and the value
    // must agree, or the port contract is decoration.
    VARS.setDocumentVariables([{ id: 'seaLevelM', name: 'Sea level', value: 120, unit: 'm' }])
    const metreNode = { type: 'variable', params: { varId: 'seaLevelM' } }
    let metrePort = TYPES.variable.resolvePorts(metreNode).outputs[0]
    if (mutation === 'unit-not-carried') metrePort = { ...metrePort, unit: 'none', semantic: 'relativeHeight' }
    const maskPort = (TYPES.blur.inputs || []).find(p => p.semantic === 'anyMask')
    const intoMask = PORTS.canConnect(metrePort, maskPort)
    // A dimensionless variable must still be accepted, or the check is just "refuse everything".
    VARS.setDocumentVariables([{ id: 'plainVar', name: 'Plain', value: 0.5, unit: 'none' }])
    const plainPort = TYPES.variable.resolvePorts({ type: 'variable', params: { varId: 'plainVar' } }).outputs[0]
    const plainIntoMask = PORTS.canConnect(plainPort, maskPort)
    out.units = {
      metreUnit: metrePort.unit,
      metresRefusedByMask: intoMask.ok === false && intoMask.code === 'UNIT_MISMATCH',
      dimensionlessAccepted: plainIntoMask.ok === true,
    }

    // --- A VARIABLE EDIT IS ONE UNDO RECORD ---------------------------------------------------
    // graphSnapshot carried nodes/edges/uid/terrainDef and nothing else, so a variable edit was in
    // zero undo records: undo reverted the graph around it and left the new value in place.
    VARS.setDocumentVariables([{ id: 'undoVar', name: 'Undo probe', value: 0.25, unit: 'none' }])
    // The mutation reproduces the PRE-FIX BUILD rather than editing the answer: it strips the
    // variables block out of the snapshot, which is exactly what graphSnapshot() used to emit. Real
    // pushUndo, real undoGraph, real restoreGraph then run against it, so what is measured below is
    // production's restore behaviour on a v-less snapshot, not a literal assigned by this file.
    const snap = graphSnapshot()
    if (mutation === 'variable-edit-not-undoable') delete snap.variables
    pushUndo(snap)
    VARS.setDocumentVariables([{ id: 'undoVar', name: 'Undo probe', value: 0.75, unit: 'none' }])
    const beforeUndo = (VARS.getDocumentVariables().find(v => v.id === 'undoVar') || {}).value
    undoGraph()
    const afterUndo = (VARS.getDocumentVariables().find(v => v.id === 'undoVar') || {}).value
    out.undo = { beforeUndo, afterUndo, reverted: afterUndo === 0.25 }

    // --- THE LEXICAL OVERRIDE, AGAINST A REAL SUBGRAPH INSTANCE -------------------------------
    // S8.3's scope chain had exactly one production caller and always one frame, so the shadowing
    // path was dead code the oracle exercised through makeScope directly. Now that S8.5 exists the
    // claim can be tested for real: a definition containing a Variable node, instantiated twice
    // with different overrides, must produce two different fields.
    SUBGRAPHS.clearSubgraphDefinitions(); SUBGRAPHS.clearSubgraphCache()
    VARS.setDocumentVariables([{ id: 'shared', name: 'Shared', value: 0.2, unit: 'none' }])
    SUBGRAPHS.defineSubgraph({
      id: 'usesVar', version: 1,
      inputs: [{ id: 'in', kind: 'scalarRaster', semantic: 'anyScalarRaster', unit: 'none' }],
      outputs: [{ id: 'out', kind: 'scalarRaster', semantic: 'relativeHeight', unit: 'none', from: 'v' }],
      params: [],
      nodes: [{ localId: 'v', type: 'variable', params: { varId: 'shared' } }],
      edges: [],
    })
    // Same discipline here. The pre-fix build merged overrides into node params, where the Variable
    // node never read them, so BOTH instances resolved 'shared' from the document. Dropping the
    // override text reproduces that build exactly and then runs the real subgraph evaluator; the
    // measured hi/lo below come out of production either way.
    const ovHigh = mutation === 'instance-override-ignored' ? '' : 'shared = 0.9'
    const ovLow = mutation === 'instance-override-ignored' ? '' : 'shared = 0.1'
    const instHigh = { id: 51, type: 'subgraph', params: { definitionId: 'usesVar', overrides: ovHigh } }
    const instLow = { id: 52, type: 'subgraph', params: { definitionId: 'usesVar', overrides: ovLow } }
    const fHigh = TYPES.subgraph.eval(instHigh.params, [null], instHigh)
    const fLow = TYPES.subgraph.eval(instLow.params, [null], instLow)
    const hi = fHigh[0], lo = fLow[0]
    // The frame must not leak: after evaluation the document value is visible again.
    const afterInstances = (VARS.getDocumentVariables().find(v => v.id === 'shared') || {}).value
    out.override = {
      hi, lo, documentValue: 0.2, depthAfter: VARS.scopeDepth(),
      shadows: Math.abs(hi - 0.9) < 1e-6 && Math.abs(lo - 0.1) < 1e-6,
      independent: hi !== lo,
      frameDidNotLeak: VARS.scopeDepth() === 1 && afterInstances === 0.2,
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
    unitIsCarriedAndEnforced: report.units.metreUnit === 'm' && report.units.metresRefusedByMask === true
      && report.units.dimensionlessAccepted === true,
    variableEditIsUndoable: report.undo.reverted === true && report.undo.beforeUndo === 0.75,
    instanceOverrideShadowsDocument: report.override.shadows === true && report.override.independent === true,
    scopeFrameDoesNotLeak: report.override.frameDidNotLeak === true,
    variablesRoundTrip: report.persistence.roundTrips === true,
    // Was `report.scope.depth === 2`, pinned to the frame count the oracle passed to makeScope four
    // lines earlier — it could not read anything else regardless of production. The evidence now
    // comes from PRODUCTION's scope during a real instance evaluation.
    evidenceNonEmpty: report.scope.idsUnion.length > 0 && report.override.hi !== undefined
      && report.units.metreUnit !== undefined,
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
