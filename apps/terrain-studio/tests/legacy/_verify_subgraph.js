// S8.5 / S8.6 — versioned subgraph definitions, instances, caching and persistence.
//
// The story's headline claim is an EQUIVALENCE: "a three-node definition instantiated twice matches
// the equivalent inlined chain". That is the only check that proves encapsulation did not change
// the arithmetic, and it is asserted here sample-for-sample rather than by digest resemblance.
//
// The claims that need negative evidence are the ones about what must NOT happen: internal nodes
// must not leak into the parent, two instances with different overrides must not alias, and a
// definition that contains itself must be refused at registration rather than discovered as a stack
// overflow inside a render.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'inline-mismatch',
  'accept-direct-recursion',
  'accept-indirect-recursion',
  'accept-hash-conflict',
  'instances-alias-overrides',
  'internal-nodes-leak',
  'definitions-not-persisted',
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
    USE_GPU = false; RES = 64; TARGET_RES = 64; terrainDef.lattice = 'square'
    const out = { mutation: mutation || null }
    const N = RES * RES
    const SG = SUBGRAPHS
    SG.clearSubgraphDefinitions(); SG.clearSubgraphCache()

    // A three-node definition: blur -> levels -> invert, fed by the instance's input.
    const chain = [
      { localId: 'a', type: 'blur', params: { radius: 2 } },
      { localId: 'b', type: 'levels', params: { inLow: 0.1, inHigh: 0.9, gamma: 1 } },
      { localId: 'c', type: 'invert', params: {} },
    ]
    const def = {
      id: 'ridgePack', version: 1,
      inputs: [{ id: 'in', kind: 'scalarRaster', semantic: 'anyScalarRaster', unit: 'none' }],
      outputs: [{ id: 'out', kind: 'scalarRaster', semantic: 'relativeHeight', unit: 'none', from: 'c' }],
      params: [],
      nodes: chain,
      edges: [{ from: 'a', to: 'b' }, { from: 'b', to: 'c' }],
    }
    SG.defineSubgraph(def)

    // --- the equivalence: instance output === the inlined chain, sample for sample -------------
    const source = newField()
    for (let i = 0; i < N; i++) source[i] = Math.sin(i * 0.031) * 0.5 + 0.5
    const inlineA = TYPES.blur.eval(chain[0].params, [source, null], {})
    const inlineB = TYPES.levels.eval(chain[1].params, [inlineA, null], {})
    const inlined = TYPES.invert.eval(chain[2].params, [inlineB, null], {})

    const instanceNode = { id: 9001, type: 'subgraph', params: { definitionId: 'ridgePack', overrides: '' } }
    let viaInstance = TYPES.subgraph.eval(instanceNode.params, [source], instanceNode)
    if (mutation === 'inline-mismatch') viaInstance = Float32Array.from(viaInstance, v => v + 1e-3)
    let maxDiff = 0
    for (let i = 0; i < N; i++) maxDiff = Math.max(maxDiff, Math.abs(viaInstance[i] - inlined[i]))
    out.equivalence = { maxDiff, length: viaInstance.length, expected: N, exact: maxDiff === 0 }

    // Instantiated TWICE must give the same answer both times.
    SG.clearSubgraphCache()
    const second = TYPES.subgraph.eval(instanceNode.params, [source], { ...instanceNode, id: 9002 })
    let twiceDiff = 0
    for (let i = 0; i < N; i++) twiceDiff = Math.max(twiceDiff, Math.abs(second[i] - viaInstance[i]))
    out.twiceIdentical = twiceDiff === 0

    // --- internal nodes must not leak into the parent -------------------------------------------
    blankGraph()
    const parentBefore = nodes.length
    const host = makeNode('subgraph', 200, 200)
    host.params.definitionId = 'ridgePack'
    nodes.forEach(n => { n._dirty = true })
    evalGraph()
    const parentTypes = nodes.map(n => n.type)
    // Model the defect the gate actually measures: the definition's three internals arriving in the
    // parent's node list alongside the host. The mutation used to append to a type array the gate
    // stopped reading when it moved to a count delta, which left it tripping only the safety net.
    out.encapsulation = {
      parentBefore, parentAfter: nodes.length,
      types: parentTypes,
      // COUNT DELTA, not type membership. blankGraph() does not produce an empty graph — measured,
      // it leaves the 8-node L0 default — and that default already contains `levels`, so a
      // membership test reported a leak that was never there. Instantiating a subgraph must add
      // exactly ONE node to the parent: the host. Its three internals must not arrive with it.
      noInternalLeak: (nodes.length + (mutation === 'internal-nodes-leak' ? 3 : 0)) === parentBefore + 1,
      hostEvaluated: !!host._field && host._field.length === N,
    }

    // --- recursion is refused AT REGISTRATION ---------------------------------------------------
    const wellFormed = (id, innerId) => ({
      id, version: 1,
      inputs: [{ id: 'in', kind: 'scalarRaster', semantic: 'anyScalarRaster', unit: 'none' }],
      outputs: [{ id: 'out', kind: 'scalarRaster', semantic: 'relativeHeight', unit: 'none', from: 'z' }],
      params: [],
      nodes: [{ localId: 'y', type: 'subgraph', params: { definitionId: innerId } }, { localId: 'z', type: 'blur', params: {} }],
      edges: [{ from: 'y', to: 'z' }],
    })
    let directCode = null
    try { SG.defineSubgraph(wellFormed('selfRef', 'selfRef')) } catch (e) { directCode = e.code }
    if (mutation === 'accept-direct-recursion') directCode = null

    // Indirect: alpha -> beta -> alpha, built through the pure API so registration order does not
    // matter to the assertion.
    const defs = {}
    defs.alpha = { ...wellFormed('alpha', 'beta'), hash: 'x' }
    defs.beta = { ...wellFormed('beta', 'alpha'), hash: 'y' }
    let indirect = SG.findRecursion(defs, 'alpha')
    if (mutation === 'accept-indirect-recursion') indirect = null
    out.recursion = { directCode, indirect: indirect ? indirect.join(' -> ') : null }

    // --- content identity: dedupe vs conflict ---------------------------------------------------
    const same = JSON.parse(JSON.stringify(def))
    let dedupeOk = true, conflictCode = null
    try { SG.defineSubgraph(same) } catch (e) { dedupeOk = false }
    const divergent = JSON.parse(JSON.stringify(def))
    divergent.nodes[0].params.radius = 9
    try { SG.defineSubgraph(divergent) } catch (e) { conflictCode = e.code }
    if (mutation === 'accept-hash-conflict') conflictCode = null
    // Position-only edits must NOT change identity, or every drag would be a conflict.
    const moved = JSON.parse(JSON.stringify(def))
    moved.nodes = moved.nodes.map(n => ({ ...n, x: 77, y: 88 }))
    out.identity = {
      dedupeOk, conflictCode,
      positionIrrelevant: SG.definitionHash(moved) === SG.definitionHash(def),
    }

    // --- two instances with different overrides must not alias ----------------------------------
    SG.clearSubgraphCache()
    const nodeLow = { id: 1, type: 'subgraph', params: { definitionId: 'ridgePack', overrides: 'radius = 1' } }
    const nodeHigh = { id: 2, type: 'subgraph', params: { definitionId: 'ridgePack', overrides: 'radius = 6' } }
    const low = TYPES.subgraph.eval(nodeLow.params, [source], nodeLow)
    const high = TYPES.subgraph.eval(nodeHigh.params, [source], nodeHigh)
    let overrideDiff = 0
    for (let i = 0; i < N; i++) overrideDiff = Math.max(overrideDiff, Math.abs(low[i] - high[i]))
    if (mutation === 'instances-alias-overrides') overrideDiff = 0
    // Identical instances SHARE a cache key; different overrides never can.
    const keyA = SG.instanceCacheKey({ definition: SG.getSubgraphDefinitions().ridgePack, overrides: { radius: 1 } })
    const keyB = SG.instanceCacheKey({ definition: SG.getSubgraphDefinitions().ridgePack, overrides: { radius: 1 } })
    const keyC = SG.instanceCacheKey({ definition: SG.getSubgraphDefinitions().ridgePack, overrides: { radius: 6 } })
    out.instances = { overrideDiff, sameKey: keyA === keyB, differentKey: keyA !== keyC, notAliased: overrideDiff > 0 }

    // --- persistence -----------------------------------------------------------------------------
    blankGraph()
    const persistHost = makeNode('subgraph', 100, 100)
    persistHost.params.definitionId = 'ridgePack'
    let text = saveProjectText()
    const parsed = JSON.parse(text)
    if (mutation === 'definitions-not-persisted') delete parsed.definitions
    SG.clearSubgraphDefinitions()
    let loadErr = null
    try { loadProjectText(JSON.stringify(parsed, null, 2) + '\n') } catch (e) { loadErr = e.code || String(e) }
    const restored = SG.getSubgraphDefinitions().ridgePack
    out.persistence = {
      embedded: Array.isArray(parsed.definitions) && parsed.definitions.length === 1,
      loadErr,
      restoredHash: restored ? restored.hash : null,
      hashPreserved: !!restored && restored.hash === SG.definitionHash(def),
    }
    return out
  }, mutation)

  const gates = {
    instanceMatchesInlinedChain: report.equivalence.exact === true && report.equivalence.length === report.equivalence.expected,
    instantiatedTwiceIsIdentical: report.twiceIdentical === true,
    noInternalNodeLeak: report.encapsulation.noInternalLeak === true && report.encapsulation.hostEvaluated === true,
    directRecursionRefused: report.recursion.directCode === 'SUBGRAPH_RECURSION',
    indirectRecursionDetected: report.recursion.indirect === 'alpha -> beta -> alpha',
    identicalDefinitionDeduplicates: report.identity.dedupeOk === true,
    divergentSameVersionRefused: report.identity.conflictCode === 'SUBGRAPH_HASH_CONFLICT',
    positionDoesNotChangeIdentity: report.identity.positionIrrelevant === true,
    differentOverridesDoNotAlias: report.instances.notAliased === true,
    cacheKeyIdentityCorrect: report.instances.sameKey === true && report.instances.differentKey === true,
    definitionsEmbeddedAndRestored: report.persistence.embedded === true && report.persistence.hashPreserved === true
      && report.persistence.loadErr === null,
    evidenceNonEmpty: report.equivalence.length > 0 && report.instances.overrideDiff >= 0,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — that gate is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  console.log(`${ok ? 'PASS' : 'FAIL'}  subgraph maxDiff=${report.equivalence.maxDiff} overrideDiff=${report.instances.overrideDiff.toFixed(4)} `
    + `parent=${report.encapsulation.parentAfter} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
