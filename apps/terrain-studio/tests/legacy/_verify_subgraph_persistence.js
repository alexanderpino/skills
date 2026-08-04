// S8.6 — subgraph caching, persistence, copy/import and invalidation.
//
// S8.5's oracle proves a definition COMPUTES the right thing. This one proves the right thing
// SURVIVES: a saved document reproduces the same samples and the same wiring, an imported
// definition either deduplicates exactly or is refused without rewriting anything, two identical
// instances share one immutable cached result while two with different overrides never do, and
// changing a definition moves its own instances and their downstream cone and nothing else.
//
// The reference readings — `preSave` digests, `pristine` document bytes, `hash0` — are all taken
// BEFORE any mutation runs, so no control can move the answer it is being measured against. Every
// control perturbs an input that production consumes (the saved document text, a definition object
// handed to registerDefinition, an instance's override text, the effective seed) and the gate then
// reads what production did with it. None of them writes to the oracle's own copy of a result;
// that shape has already been found four times in this suite and is worth less than no control.
//
// MEASURED AND NOT GATED HERE — reported to the story owner rather than asserted, because the fix
// belongs in legacy.js and this file does not own it:
//   * legacy.js:4724 keys an instance on `String(ins[0].length)` as its "upstream port keys". Every
//     field is RES*RES long, so that term is a constant: two instances of the same definition with
//     the same overrides but DIFFERENT upstream inputs collide on one cache entry and the second
//     receives the first one's samples. Measured: identical Float32Array object, identical digest,
//     from a perlin source and a ridged source.
//   * a Subgraph instance stores only {definitionId, overrides}; it does not pin (version, hash),
//     so a definition registered at a higher version silently retunes every existing instance.
//   * an embedded definition's stated `hash` is never verified on load — registerDefinition
//     recomputes it from content and overwrites whatever the document claimed.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'definitions-dropped-on-load',    // the document arrives with no definitions block at all
  'nested-definition-dropped',      // only the definition a DEFINITION references is missing
  'definition-content-diverged',    // the embedded definition is not the one the hash was taken of
  'mute-instance-edge',             // the wire feeding the instance arrives muted
  'dangling-definition-present',    // the reference is NOT dangling, so the writer must accept it
  'import-identity-inverted',       // the exact copy diverges and the rival differs only in layout
  'version-bump-silently-adopted',  // a higher version arrives and rewrites the live definition
  'definition-change-only-cosmetic',// the "changed" definition computes exactly what it did before
  'definition-change-spills-to-others', // an unrelated definition changes at the same moment
  'seed-changes-between-instances', // the effective seed moves between two identical instances
  'override-does-not-reach-definition', // the override names a key no internal node declares
  'cache-key-fed-stale-hash',       // two different definitions present the same hash to the key
  'same-content-for-both-upstreams',// the two upstream fields stop differing, so sharing is right
  'field-key-length-only',          // the pre-fix expression: key an input by its length
  'closure-term-omitted',           // the pre-fix key: no transitive definition hashes
  'instance-pin-stripped',          // the pre-fix instance: no version/hash, so it floats to latest
  'embedded-hash-is-honest',        // the document states the hash its content really produces
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
    USE_GPU = false; RES = 64; TARGET_RES = 64; SCALE_RES = true
    BUILD_QUALITY = 'interactive'; XF = null; terrainDef.lattice = 'square'
    const out = { mutation: mutation || null }
    const N = RES * RES
    const SG = SUBGRAPHS
    const copy = o => JSON.parse(JSON.stringify(o))

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
    const byId = id => nodes.find(n => n.id === id)
    const graphDigests = () => Object.fromEntries(nodes.map(n => [n.id, digestField(n._field)]))
    const sameDigests = (a, b) => {
      const ka = Object.keys(a), kb = Object.keys(b)
      if (!ka.length || ka.length !== kb.length) return false     // absence of evidence is failure
      return ka.every(k => k in b && a[k] === b[k])
    }
    const changedIds = (a, b) => Object.keys(a).filter(k => a[k] !== b[k]).map(Number)
    // Topology as a string: node identity plus every wire's PORT identity and mute flag.
    const topologyOf = doc => !doc ? 'none'
      : doc.graph.nodes.map(n => n.id + ':' + n.type).sort().join(',')
        + '|' + doc.graph.edges.map(e => `${e.from}.${e.fromPort}>${e.to}.${e.toPort}${e.disabled ? '!' : ''}`).sort().join(',')

    // --- the definitions: outerPack NESTS innerPack, so the document has to embed a definition no
    //     node in the parent graph names directly. packB is the unrelated one. -------------------
    const port = (id, from) => ({ id, kind: 'scalarRaster', semantic: from ? 'relativeHeight' : 'anyScalarRaster', unit: 'none', ...(from ? { from } : {}) })
    const innerDef = {
      id: 'innerPack', version: 1,
      inputs: [port('in')], outputs: [port('out', 'i1')], params: [],
      nodes: [{ localId: 'i1', type: 'blur', params: { radius: 2 } }],
      edges: [],
    }
    // o2's gamma equals what instance A overrides it to, so an override that fails to bind produces
    // A's field exactly — which is what `override-does-not-reach-definition` relies on.
    const outerDef = {
      id: 'outerPack', version: 1,
      inputs: [port('in')], outputs: [port('out', 'o2')], params: [],
      nodes: [
        { localId: 'o1', type: 'subgraph', params: { definitionId: 'innerPack', overrides: '' } },
        { localId: 'o2', type: 'levels', params: { inLo: 0.1, inHi: 0.9, gamma: 0.6, outLo: 0, outHi: 1 } },
      ],
      edges: [{ from: 'o1', to: 'o2' }],
    }
    const packBDef = {
      id: 'packB', version: 1,
      inputs: [port('in')], outputs: [port('out', 'b1')], params: [],
      nodes: [{ localId: 'b1', type: 'levels', params: { inLo: 0.05, inHi: 0.95, gamma: 1, outLo: 0, outHi: 1 } }],
      edges: [],
    }
    SG.clearSubgraphDefinitions(); SG.clearSubgraphCache()
    SG.defineSubgraph(innerDef); SG.defineSubgraph(outerDef); SG.defineSubgraph(packBDef)
    const hash0 = Object.fromEntries(Object.entries(SG.getSubgraphDefinitions()).map(([k, d]) => [k, d.hash]))
    out.hash0 = hash0

    // --- the parent graph -----------------------------------------------------------------------
    terrainDef.seed = 4242
    const src = makeNode('perlin', 40, 60); src.params.seed = 11
    const alt = makeNode('ridged', 40, 460); alt.params.seed = 23
    const instA = makeNode('subgraph', 240, 60)
    instA.params.definitionId = 'outerPack'; instA.params.overrides = 'gamma = 0.6'
    const instB = makeNode('subgraph', 240, 200)
    instB.params.definitionId = 'outerPack'; instB.params.overrides = 'gamma = 1.8'
    const instC = makeNode('subgraph', 240, 340)
    instC.params.definitionId = 'packB'; instC.params.overrides = ''
    const downA = makeNode('blur', 440, 60); downA.params.radius = 3
    const downC = makeNode('blur', 440, 340); downC.params.radius = 4
    edges.push({ from: src.id, to: instA.id, slot: 0 })
    edges.push({ from: src.id, to: instB.id, slot: 0 })
    edges.push({ from: alt.id, to: instC.id, slot: 0 })
    edges.push({ from: instA.id, to: downA.id, slot: 0 })
    edges.push({ from: instC.id, to: downC.id, slot: 0 })
    const ids = { src: src.id, alt: alt.id, A: instA.id, B: instB.id, C: instC.id, downA: downA.id, downC: downC.id }
    out.ids = ids

    SG.clearSubgraphCache()
    nodes.forEach(n => { n._dirty = true })
    evalGraph()
    const preSave = graphDigests()
    out.nodeCount = nodes.length
    out.preSaveSample = { A: preSave[ids.A], B: preSave[ids.B], C: preSave[ids.C] }
    out.instancesDiffer = preSave[ids.A] !== preSave[ids.B]

    // --- PHASE 1: save / reload retains exact output and topology --------------------------------
    const pristine = saveProjectText()
    const pristineDoc = JSON.parse(pristine)
    out.bytes = pristine.length
    out.embeddedIds = (pristineDoc.definitions || []).map(d => d.id)

    let text1 = pristine
    const edit = fn => { const d = JSON.parse(text1); fn(d); text1 = JSON.stringify(d, null, 2) + '\n' }
    if (mutation === 'definitions-dropped-on-load') edit(d => { delete d.definitions })
    if (mutation === 'nested-definition-dropped') edit(d => { d.definitions = d.definitions.filter(x => x.id !== 'innerPack') })
    if (mutation === 'definition-content-diverged') {
      edit(d => { d.definitions.find(x => x.id === 'outerPack').nodes.find(n => n.localId === 'o2').params.inLo = 0.45 })
    }
    if (mutation === 'mute-instance-edge') edit(d => { d.graph.edges.find(e => e.to === ids.A).disabled = true })

    SG.clearSubgraphDefinitions()
    let loadErr = null
    try { loadProjectText(text1) } catch (e) { loadErr = (e && e.code) || String(e) }
    if (!loadErr) { nodes.forEach(n => { n._dirty = true }); evalGraph() }
    const postLoad = loadErr ? {} : graphDigests()
    let text2 = null, reSaveErr = null
    try { text2 = saveProjectText() } catch (e) { reSaveErr = (e && e.code) || String(e) }
    const restored = SG.getSubgraphDefinitions()
    out.roundTrip = {
      loadErr, reSaveErr,
      restoredIds: Object.keys(restored).sort(),
      restoredHashes: Object.fromEntries(Object.entries(restored).map(([k, d]) => [k, d.hash])),
      hashesRecomputeEqual: Object.entries(restored).every(([, d]) => d.hash === SG.definitionHash(d)),
      outputIdentical: sameDigests(preSave, postLoad),
      changed: changedIds(preSave, postLoad),
      topologyIdentical: topologyOf(pristineDoc) === topologyOf(text2 ? JSON.parse(text2) : null),
      fixedPoint: text2 !== null && text1 === text2,
    }
    out.roundTrip.hashesPreserved = ['innerPack', 'outerPack', 'packB'].every(
      id => restored[id] && restored[id].hash === hash0[id])
    out.roundTrip.nestedRestored = ['innerPack', 'outerPack', 'packB'].every(id => !!restored[id])

    // --- PHASE 2: a dangling definition reference fails visibly ----------------------------------
    // The writer refuses to emit a document whose graph names a definition it cannot embed, and the
    // instance renders flat rather than the stale samples it held a moment ago.
    loadProjectText(pristine)
    nodes.forEach(n => { n._dirty = true }); evalGraph()
    const healthyA = digestField(byId(ids.A)._field)
    const danglingDoc = JSON.parse(pristine)
    if (mutation !== 'dangling-definition-present') {
      danglingDoc.definitions = danglingDoc.definitions.filter(d => d.id !== 'outerPack')
    }
    let danglingLoadErr = null
    try { loadProjectText(JSON.stringify(danglingDoc, null, 2) + '\n') } catch (e) { danglingLoadErr = (e && e.code) || String(e) }
    nodes.forEach(n => { n._dirty = true }); evalGraph()
    let danglingSaveErr = null
    try { saveProjectText() } catch (e) { danglingSaveErr = (e && e.code) || String(e) }
    const danglingField = byId(ids.A) ? byId(ids.A)._field : null
    out.dangling = {
      loadErr: danglingLoadErr, saveErr: danglingSaveErr,
      registered: Object.keys(SG.getSubgraphDefinitions()).sort(),
      digest: digestField(danglingField), healthyA,
      flat: !!danglingField && danglingField.length === N && danglingField.every(v => v === 0),
      moved: digestField(danglingField) !== healthyA,
    }

    // --- PHASE 3: copy / import — exact dedupe, visible conflict, nothing rewritten ---------------
    loadProjectText(pristine)
    nodes.forEach(n => { n._dirty = true }); evalGraph()
    const liveHash = SG.getSubgraphDefinitions().outerPack.hash
    const liveDigest = digestField(byId(ids.A)._field)
    let twin = copy(outerDef)
    let rival = copy(outerDef); rival.nodes[1].params.inLo = 0.42
    if (mutation === 'import-identity-inverted') {
      // The copy now carries different content, and the rival differs only in where its nodes sit.
      // Production decides both verdicts; if the two gates read production they must both flip.
      twin = copy(outerDef); twin.nodes[1].params.inLo = 0.42
      rival = copy(outerDef); rival.nodes = rival.nodes.map(n => ({ ...n, x: 31, y: 97 }))
    }
    let dedupeErr = null
    try { SG.defineSubgraph(twin) } catch (e) { dedupeErr = (e && e.code) || String(e) }
    let conflictErr = null
    try { SG.defineSubgraph(rival) } catch (e) { conflictErr = (e && e.code) || String(e) }
    if (mutation === 'version-bump-silently-adopted') {
      const bumped = copy(outerDef); bumped.version = 2; bumped.nodes[1].params.inLo = 0.42
      try { SG.defineSubgraph(bumped) } catch (e) { /* measured through the table below */ }
    }
    nodes.forEach(n => { n._dirty = true }); evalGraph()
    out.import = {
      dedupeErr, conflictErr,
      tableSize: Object.keys(SG.getSubgraphDefinitions()).length,
      hashAfter: SG.getSubgraphDefinitions().outerPack.hash, liveHash,
      hashUnchanged: SG.getSubgraphDefinitions().outerPack.hash === liveHash,
      digestUnchanged: digestField(byId(ids.A)._field) === liveDigest,
    }

    // --- PHASE 4: cache identity — share when identical, never alias when not --------------------
    SG.clearSubgraphDefinitions(); SG.clearSubgraphCache()
    SG.defineSubgraph(innerDef); SG.defineSubgraph(outerDef); SG.defineSubgraph(packBDef)
    terrainDef.seed = 4242
    const source = newField()
    for (let i = 0; i < N; i++) source[i] = Math.sin(i * 0.031) * 0.5 + 0.5
    const inst = (id, overrides) => ({ id, type: 'subgraph', params: { definitionId: 'outerPack', overrides } })
    const n1 = inst(7001, 'gamma = 0.6'), n2 = inst(7002, 'gamma = 0.6'), n3 = inst(7003, 'gamma = 1.8')
    if (mutation === 'override-does-not-reach-definition') n3.params.overrides = 'notAParameter = 1.8'
    const f1 = TYPES.subgraph.eval(n1.params, [source], n1)
    const size1 = SG.subgraphCacheSize()
    if (mutation === 'seed-changes-between-instances') terrainDef.seed = 999983
    const f2 = TYPES.subgraph.eval(n2.params, [source], n2)
    const size2 = SG.subgraphCacheSize()
    terrainDef.seed = 4242
    const f3 = TYPES.subgraph.eval(n3.params, [source], n3)
    const size3 = SG.subgraphCacheSize()
    const probe3 = f3[0]
    f1[0] = f1[0] + 0.5
    const leaked = f3[0] !== probe3
    f1[0] = f1[0] - 0.5
    out.cache = {
      size1, size2, size3,
      shared: f1 === f2, sharedNoGrowth: size2 === size1,
      distinctObjects: f1 !== f3, grewByOne: size3 === size2 + 1,
      valuesDiffer: digestField(f1) !== digestField(f3), leaked,
      d1: digestField(f1), d3: digestField(f3),
    }

    // Every ADR-004 term, through production's own key function. A definition whose hash is stale
    // must not be mistaken for a different one, which is the story's named armed failure.
    const defV1 = SG.getSubgraphDefinitions().outerPack
    let defV2 = { ...copy(outerDef), version: 2 }
    defV2.nodes[1].params.inLo = 0.42
    defV2 = { ...defV2, hash: SG.definitionHash(defV2) }
    let keyDefA = defV1, keyDefB = defV2
    if (mutation === 'cache-key-fed-stale-hash') {
      keyDefA = { ...defV1, hash: 'stale' }; keyDefB = { ...defV2, hash: 'stale', version: defV1.version }
    }
    const base = { definition: keyDefA, overrides: { gamma: 0.6 }, demandedOutput: 'out', seed: 7,
      context: { res: 64, lattice: 'square' }, upstreamKeys: ['u1'] }
    const K = o => SG.instanceCacheKey({ ...base, ...o })
    out.keys = {
      stable: K({}) === K({}),
      definition: K({}) !== K({ definition: keyDefB }),
      overrides: K({}) !== K({ overrides: { gamma: 1.8 } }),
      demandedOutput: K({}) !== K({ demandedOutput: 'mask' }),
      seed: K({}) !== K({ seed: 8 }),
      context: K({}) !== K({ context: { res: 128, lattice: 'square' } }),
      upstream: K({}) !== K({ upstreamKeys: ['u2'] }),
      sample: K({}),
    }

    // --- PHASE 4c: DIFFERENT UPSTREAM MUST MEAN DIFFERENT TERRAIN ----------------------------
    // The `upstream` term above proves the KEY FUNCTION separates 'u1' from 'u2'. It said nothing
    // about what the caller passed, and the caller passed String(ins[0].length) — identical for
    // every field in the document, because every field is RES*RES. Two instances of one definition
    // with equal overrides and different inputs collided on one entry and the second returned the
    // first's Float32Array. This measures the instance evaluator itself.
    const mkField = mul => { const a = new Float32Array(RES * RES); for (let i = 0; i < a.length; i++) a[i] = Math.sin(i * mul) * 0.5 + 0.5; return a }
    SG.clearSubgraphCache()
    const inP = mkField(0.017)
    const inR = mutation === 'same-content-for-both-upstreams' ? mkField(0.017) : mkField(0.041)
    const inP2 = mkField(0.017)
    const instU = { id: 901, type: 'subgraph', params: { definitionId: 'outerPack', overrides: 'gamma = 0.6' } }
    const fA = TYPES.subgraph.eval(instU.params, [inP], instU)
    const fB = TYPES.subgraph.eval(instU.params, [inR], instU)
    const fA2 = TYPES.subgraph.eval(instU.params, [inP2], instU)
    // The pre-fix expression, reproduced verbatim at the defect site so the key claim has a red end.
    const FK = x => mutation === 'field-key-length-only' ? String(x.length) : SG.fieldKey(x)
    out.upstream = {
      lengthsEqual: inP.length === inR.length,          // the whole reason length was never a key
      differentObject: fA !== fB,
      differentValues: digestField(fA) !== digestField(fB),
      equalInputsShare: fA === fA2,
      keyDiffers: FK(inP) !== FK(inR),
      keyStableForEqualContent: FK(inP) === FK(inP2),
    }

    // --- PHASE 4e: A PINNED INSTANCE DOES NOT FOLLOW A VERSION BUMP --------------------------
    // ADR-004: "Instances pin (definitionId, version, fullHash). Old instances never float."
    // Measured before this existed: registering outerPack v2 moved the live hash from
    // 77337d1c317dcf0f to the v2 hash and every instance's output moved with it, silently.
    SG.clearSubgraphCache()
    const pinDefs = SG.getSubgraphDefinitions()
    const pinnedNode = { id: 902, type: 'subgraph', params: { definitionId: 'outerPack', overrides: 'gamma = 0.6' } }
    SG.stampInstancePin(pinnedNode)
    const pinnedV = pinnedNode.params.version, pinnedH = pinnedNode.params.hash
    // The pre-fix instance carried neither field, so it resolved to whatever was latest.
    if (mutation === 'instance-pin-stripped') { delete pinnedNode.params.version; delete pinnedNode.params.hash }
    const beforeBump = digestField(TYPES.subgraph.eval(pinnedNode.params, [inP], pinnedNode))
    let bumped = copy(pinDefs.outerPack)
    bumped.version = (pinDefs.outerPack.version || 1) + 1
    bumped.nodes[1].params.inLo = 0.19
    SG.defineSubgraph(bumped)
    SG.clearSubgraphCache()
    const afterBump = digestField(TYPES.subgraph.eval(pinnedNode.params, [inP], pinnedNode))
    // A FRESH instance must see the new version, or "did not move" would also be true of a build
    // that stopped evaluating definitions at all.
    const freshNode = { id: 903, type: 'subgraph', params: { definitionId: 'outerPack', overrides: 'gamma = 0.6' } }
    SG.stampInstancePin(freshNode)
    const freshDigest = digestField(TYPES.subgraph.eval(freshNode.params, [inP], freshNode))
    // A pin naming a version that is not in the archive must fail VISIBLY, not fall back.
    const ghost = { id: 904, type: 'subgraph', params: { definitionId: 'outerPack', version: 97, hash: 'deadbeef', overrides: '' } }
    TYPES.subgraph.eval(ghost.params, [inP], ghost)
    out.pin = {
      stamped: pinnedV != null && !!pinnedH,
      pinnedVersion: pinnedV, freshVersion: freshNode.params.version,
      beforeBump, afterBump, heldItsVersion: beforeBump === afterBump,
      freshFollowedTheBump: freshDigest !== beforeBump,
      ghostProblem: ghost._pinProblem ? ghost._pinProblem.code : null,
    }

    // --- PHASE 4f: A DOCUMENT'S STATED DEFINITION HASH IS VERIFIED ON LOAD -------------------
    // registerDefinition recomputes and stores its own hash, and applyProjectDocument clears the
    // table first, so the same-id/version conflict path is unreachable on load: a document stating
    // deadbeefdeadbeef loaded with loadErr null and the registry silently carrying the right hash.
    const corruptDoc = JSON.parse(pristine)
    if (Array.isArray(corruptDoc.definitions) && corruptDoc.definitions.length) {
      corruptDoc.definitions[0] = { ...corruptDoc.definitions[0] }
      if (mutation !== 'embedded-hash-is-honest') corruptDoc.definitions[0].hash = 'deadbeefdeadbeef'
    }
    let corruptErr = null
    try { loadProjectText(JSON.stringify(corruptDoc)) } catch (e) { corruptErr = String(e.message || e).slice(0, 160) }
    out.corrupt = {
      documentsCarryDefinitions: Array.isArray(corruptDoc.definitions) && corruptDoc.definitions.length > 0,
      refused: corruptErr !== null,
      message: corruptErr,
    }
    loadProjectText(pristine)

    // --- PHASE 4d: A NESTED DEFINITION IS PART OF ITS PARENT'S IDENTITY ----------------------
    // outerPack's own content does not change when innerPack does, so the parent's hash alone left
    // the key identical and the cache served a result computed from a definition that had gone.
    const liveDefs = SG.getSubgraphDefinitions()
    const parentDef = liveDefs.outerPack
    const closureNow = SG.closureHashes(liveDefs, parentDef)
    const defsMissing = { ...liveDefs }; delete defsMissing.innerPack
    const closureMissing = SG.closureHashes(defsMissing, parentDef)
    const KC = cl => SG.instanceCacheKey({ ...base, definitionClosure: mutation === 'closure-term-omitted' ? [] : cl })
    out.closure = {
      reachesNested: closureNow.length >= 2 && closureNow.some(e => e[0] === 'innerPack'),
      missingChangesKey: KC(closureNow) !== KC(closureMissing),
      ids: closureNow.map(e => e[0]),
    }

    // --- PHASE 5: changing a definition invalidates its instances and their cone, and nothing else
    loadProjectText(pristine)
    SG.clearSubgraphCache()
    nodes.forEach(n => { n._dirty = true }); evalGraph()
    const before = graphDigests()
    let packBv2 = copy(packBDef); packBv2.version = 2; packBv2.nodes[0].params.inLo = 0.35
    if (mutation === 'definition-change-only-cosmetic') {
      packBv2 = copy(packBDef); packBv2.version = 2
      packBv2.nodes = packBv2.nodes.map(n => ({ ...n, x: 12, y: 34 }))
    }
    SG.defineSubgraph(packBv2)
    if (mutation === 'definition-change-spills-to-others') {
      const outerV2 = copy(outerDef); outerV2.version = 2; outerV2.nodes[1].params.inLo = 0.4
      SG.defineSubgraph(outerV2)
    }
    evalGraph()
    const after = graphDigests()
    const moved = changedIds(before, after)
    const cone = [ids.C, ids.downC]
    const spared = [ids.src, ids.alt, ids.A, ids.B, ids.downA]
    out.invalidation = {
      moved,
      coneMoved: cone.every(id => before[id] !== after[id]),
      sparedIntact: spared.every(id => before[id] === after[id]),
      strayIds: moved.filter(id => !cone.includes(id)),
      cacheSize: SG.subgraphCacheSize(),
    }

    return out
  }, mutation)

  const gates = {
    outputIdenticalAfterReload: report.roundTrip.outputIdentical === true,
    topologyIdenticalAfterReload: report.roundTrip.topologyIdentical === true,
    documentIsFixedPoint: report.roundTrip.fixedPoint === true,
    definitionsEmbeddedTransitively: report.embeddedIds.join(',') === 'innerPack,outerPack,packB',
    nestedDefinitionRestored: report.roundTrip.nestedRestored === true,
    definitionHashesPreserved: report.roundTrip.hashesPreserved === true && report.roundTrip.hashesRecomputeEqual === true,
    danglingReferenceRefusesSave: report.dangling.saveErr === 'SUBGRAPH_MISSING_DEFINITION',
    danglingReferenceGoesFlat: report.dangling.flat === true && report.dangling.moved === true,
    identicalImportDeduplicates: report.import.dedupeErr === null,
    divergentImportRefused: report.import.conflictErr === 'SUBGRAPH_HASH_CONFLICT',
    refusedImportLeavesDocumentIntact: report.import.hashUnchanged === true
      && report.import.digestUnchanged === true && report.import.tableSize === 3,
    identicalInstancesShareCachedResult: report.cache.shared === true && report.cache.sharedNoGrowth === true,
    differentOverridesNeverAlias: report.cache.distinctObjects === true && report.cache.valuesDiffer === true
      && report.cache.leaked === false && report.cache.grewByOne === true,
    cacheIdentityCoversAdr004Terms: report.keys.stable === true && report.keys.definition === true
      && report.keys.overrides === true && report.keys.demandedOutput === true && report.keys.seed === true
      && report.keys.context === true && report.keys.upstream === true,
    definitionChangeInvalidatesItsInstances: report.invalidation.coneMoved === true,
    definitionChangeSparesUnrelated: report.invalidation.sparedIntact === true
      && report.invalidation.strayIds.length === 0,
    // Upstream content, not upstream length, is what separates two instances.
    upstreamContentSeparatesInstances: report.upstream.lengthsEqual === true
      && report.upstream.differentObject === true && report.upstream.differentValues === true,
    equalUpstreamStillSharesOneResult: report.upstream.equalInputsShare === true,
    fieldKeyDiscriminatesEqualLengthFields: report.upstream.keyDiffers === true
      && report.upstream.keyStableForEqualContent === true,
    nestedDefinitionIsPartOfParentIdentity: report.closure.reachesNested === true
      && report.closure.missingChangesKey === true,
    pinnedInstanceDoesNotFollowAVersionBump: report.pin.stamped === true
      && report.pin.heldItsVersion === true && report.pin.freshFollowedTheBump === true
      && report.pin.freshVersion > report.pin.pinnedVersion,
    unknownPinnedVersionFailsVisibly: report.pin.ghostProblem === 'SUBGRAPH_VERSION_UNSUPPORTED',
    statedDefinitionHashIsVerifiedOnLoad: report.corrupt.documentsCarryDefinitions === true
      && report.corrupt.refused === true,
    // Absence of evidence is failure: a run that compared nothing, saved nothing, or evaluated two
    // instances into the same picture proves none of the above.
    evidenceNonEmpty: report.bytes > 500 && report.nodeCount >= 7 && report.instancesDiffer === true
      && Object.keys(report.roundTrip.restoredHashes).length === 3 && report.cache.size3 > 0
      && report.keys.sample.length > 0,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  console.log(`${ok ? 'PASS' : 'FAIL'}  subgraph persistence bytes=${report.bytes} defs=${report.embeddedIds.join('+')} `
    + `roundTrip=${report.roundTrip.outputIdentical}/${report.roundTrip.topologyIdentical}/${report.roundTrip.fixedPoint} `
    + `cache=${report.cache.size1}/${report.cache.size2}/${report.cache.size3} shared=${report.cache.shared} `
    + `cone=${report.invalidation.moved.join('+') || 'none'} upstreamSep=${report.upstream.differentObject} `
    + `closure=${report.closure.ids.join('>')} pin=v${report.pin.pinnedVersion}->v${report.pin.freshVersion}/${report.pin.heldItsVersion} corrupt=${report.corrupt.refused} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
