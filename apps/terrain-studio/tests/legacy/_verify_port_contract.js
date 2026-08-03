// S2.1 — typed port descriptors and the connection-compatibility matrix.
//
// The gate that matters is not "descriptors exist". It is that they describe the app that actually
// ships: every edge in the default and template graphs must remain legal under the matrix, and the
// illegal pairs ADR-002 names must be refused. A descriptor set that refuses production wiring is
// worse than none — it is a declaration contradicting the code.
//
// The `mask-strict-semantic` mutation below is the one that earns its place: declaring mask inputs
// as semantic 'mask' rather than the `anyMask` generic is the obvious reading of the story text,
// and it makes ~30 shipped wirings illegal. It is here so that reading can never be adopted by
// accident.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'drop-primary',          // adapted output loses primary -> v1 edges cannot resolve their source
  'rebuild-ins',           // port ids recomputed from labels -> saved edges point at nothing
  'mask-strict-semantic',  // mask inputs declared semantic 'mask' -> shipped wiring becomes illegal
  'unit-dimensional',      // accept dimensionally-equal units -> degC into K silently allowed
  'label-into-continuous', // categorical source into a continuous input silently allowed
  'single-output-geometry',// two outputs drawn on top of each other -> the second is unclickable
  'sink-without-primary',  // the graph sink loses its value -> the whole terrain goes undefined
  'eager-allocation',      // undemanded outputs computed anyway -> demand-driven is a claim only
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

const HARNESS_NOISE = ['WebSocket closed without opened.']

;(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', e => { if (!HARNESS_NOISE.includes(e.message)) errors.push(e.message) })
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1600)

  const report = await page.evaluate(mutation => {
    const { canConnect, validatePortList, RANGE, LEGACY_ROSTER, LEGACY_INS_LABELS } = PORTS
    const out = { mutation: mutation || null }
    const types = Object.keys(TYPES)

    // --- registration ---------------------------------------------------------------------
    out.typeCount = types.length
    out.rosterCount = LEGACY_ROSTER.length
    out.withPorts = types.filter(t => TYPES[t].ports).length
    out.adapted = types.filter(t => TYPES[t].ports && TYPES[t].ports.source === 'legacy-adapter').length
    out.unregistered = types.filter(t => TYPES[t].ports && TYPES[t].ports.source === 'unregistered')

    // The adapter must not have rewritten arity. This is the bit-identity anchor: `ins` is what the
    // three evaluators index, so if the adapter touched it the digest would move.
    const insDrift = []
    for (const t of types) {
      const frozen = LEGACY_INS_LABELS[t]
      if (!frozen) continue
      const live = TYPES[t].ins || []
      if (mutation === 'rebuild-ins' && t === 'blend') live.push('Injected')
      if (live.length !== frozen.length || live.some((l, i) => l !== frozen[i])) insDrift.push(t)
    }
    out.insDrift = insDrift

    // Exactly one primary output per adapted type that has one.
    const primaryProblems = []
    for (const t of types) {
      const def = TYPES[t]
      if (!def.ports || def.ports.source !== 'legacy-adapter') continue
      let outputs = def.outputs || []
      if (mutation === 'drop-primary' && t === 'perlin') outputs = outputs.map(p => ({ ...p, primary: false }))
      const probs = validatePortList({ inputs: def.inputs || [], outputs, source: 'legacy-adapter' })
      if (probs.length) primaryProblems.push({ type: t, codes: probs.map(p => p.code) })
    }
    out.registrationProblems = primaryProblems

    // --- every shipped edge must stay legal --------------------------------------------------
    // Build each template graph the app can produce and check every edge against the matrix.
    const checked = []
    const refusedShipped = []
    const maskSemantic = mutation === 'mask-strict-semantic' ? 'mask' : null
    const portFor = (def, slot) => {
      const list = def.inputs || []
      const p = list[slot] || list[list.length - 1]
      if (!p) return null
      return maskSemantic && p.semantic === 'anyMask' ? { ...p, semantic: maskSemantic, unit: 'none' } : p
    }
    for (const build of [() => defaultGraph(), () => newTerrainDocument(false, 'canyon')]) {
      build()
      for (const e of edges) {
        const from = nodeById(e.from), to = nodeById(e.to)
        if (!from || !to) continue
        const src = (TYPES[from.type].outputs || [])[0]
        const dst = portFor(TYPES[to.type], e.slot)
        if (!src || !dst) continue
        const r = canConnect(src, dst)
        checked.push(1)
        if (!r.ok) refusedShipped.push({ from: from.type, to: to.type, slot: e.slot, code: r.code })
      }
    }
    out.shippedEdgesChecked = checked.length
    out.refusedShipped = refusedShipped

    // Every mask slot in the REGISTRY must accept an ordinary generator output. The template
    // graphs turn out to wire no mask slots at all — measured, 24 shipped edges and not one of
    // them a mask — so checking only those left `mask-strict-semantic` with nothing to break, and
    // it passed as a vacuous control. The wiring that actually exercises masks is the digest
    // oracle's: _verify_digest.js drives a plain perlin ('M') into every mask slot it can reach.
    // This gate holds that open.
    const genOut = (TYPES.perlin.outputs || [])[0]
    const maskRefusals = []
    let maskSlots = 0
    for (const t of types) {
      for (const port of (TYPES[t].inputs || [])) {
        if (port.semantic !== 'anyMask') continue
        maskSlots++
        const dst = maskSemantic ? { ...port, semantic: maskSemantic, unit: 'none' } : port
        const r = canConnect(genOut, dst)
        if (!r.ok) maskRefusals.push({ type: t, port: port.id, code: r.code })
      }
    }
    out.maskSlots = maskSlots
    out.maskRefusals = maskRefusals

    // --- the illegal pairs ADR-002 names must be refused --------------------------------------
    const P = o => ({ kind: 'scalarRaster', storage: 'R32F', components: 1, range: RANGE.unbounded(), ...o })
    const refusal = (s, d) => {
      const r = canConnect(s, d)
      if (mutation === 'unit-dimensional' && r.code === 'UNIT_MISMATCH') return true   // pretend it was allowed
      if (mutation === 'label-into-continuous' && r.code === 'KIND_MISMATCH') return true
      return r.ok
    }
    const illegal = {
      heightIntoMask: refusal(P({ id: 'o', semantic: 'height', unit: 'm' }), P({ id: 'm', semantic: 'anyMask', unit: 'none' })),
      degCIntoK: refusal(P({ id: 'o', semantic: 'temperature', unit: 'degC' }), P({ id: 'i', semantic: 'temperature', unit: 'K' })),
      radIntoDeg: refusal(P({ id: 'o', semantic: 'aspect', unit: 'rad' }), P({ id: 'i', semantic: 'aspect', unit: 'deg' })),
      heightIntoTemperature: refusal(P({ id: 'o', semantic: 'height', unit: 'm' }), P({ id: 'i', semantic: 'temperature', unit: 'degC' })),
      labelIntoContinuous: refusal(
        { id: 'o', kind: 'labelRaster', storage: 'I32', components: 1, semantic: 'basinId', unit: 'none', range: RANGE.labels(0, 99) },
        P({ id: 'i', semantic: 'anyScalarRaster', unit: 'none' })),
    }
    out.illegalAccepted = Object.entries(illegal).filter(([, accepted]) => accepted).map(([k]) => k)

    // --- demand-driven allocation, on a REAL node ------------------------------------------
    // Normals is the first shipped node with two outputs, and its vector output costs 3N floats.
    // With nothing wired to it that field must not be computed at all — otherwise "demand-driven"
    // is a word in an ADR rather than a property of the runtime. A probe type could not prove this;
    // it takes a node the evaluator actually schedules.
    blankGraph()
    const src = makeNode('perlin', 60, 60)
    const nrm = makeNode('normals', 260, 60)
    const outNode = makeNode('output', 460, 60)
    edges.push({ from: src.id, fromPort: 'out', to: nrm.id, toPort: 'in', slot: 0 })
    edges.push({ from: nrm.id, fromPort: 'height', to: outNode.id, toPort: 'height', slot: 0 })
    nodes.forEach(n => { n._dirty = true })
    evalGraph()
    const undemanded = {
      hasPrimary: !!(nrm._outputs && nrm._outputs.get('height')),
      hasVector: !!(nrm._outputs && nrm._outputs.get('normal')),
      fieldIsPrimary: nrm._field === nrm._outputs.get('height'),
    }

    // Now wire the vector port to something and it MUST appear, with the right length and shape.
    const sink2 = makeNode('output', 460, 260)
    edges.push({ from: nrm.id, fromPort: 'normal', to: sink2.id, toPort: 'height', slot: 0 })
    nodes.forEach(n => { n._dirty = true })
    evalGraph()
    const vec = nrm._outputs && nrm._outputs.get('normal')
    const n3 = RES * (terrainDef.lattice === 'hex' ? Math.round(RES * 2 / Math.sqrt(3)) : RES) * 3
    let unitLength = true
    if (vec) for (let i = 0; i < vec.length; i += 3 * 997) {
      const m = Math.hypot(vec[i], vec[i + 1], vec[i + 2])
      if (!(Math.abs(m - 1) < 1e-5)) { unitLength = false; break }
    }
    const demanded = {
      hasVector: !!vec,
      interleavedLength: !!vec && vec.length === n3,
      unitLength,
      // A flat field must give straight-up normals; anything else means the world spacing is wrong.
      finite: !!vec && Number.isFinite(vec[0]) && Number.isFinite(vec[vec.length - 1]),
    }
    if (mutation === 'eager-allocation') undemanded.hasVector = true
    out.demand = { undemanded, demanded }

    // --- the graph sink still carries a value ----------------------------------------------
    // `output` (cat:"out") publishes NO port — it has no outgoing wire, which is why drawNode and
    // portAt have always refused to draw one. But its eval returns the final terrain that the
    // renderer, the exporter and collectScene all read through nd._field. Typing the runtime made
    // it briefly possible to have zero declared outputs AND therefore no value, and the digest
    // could not see it: the digest calls def.eval directly and never evaluates through a sink.
    // Every reading in _verify_water, _verify_snow and _verify_workflow went to zero instead.
    defaultGraph()
    nodes.forEach(n => { n._dirty = true })
    evalGraph()
    const sink = nodes.find(n => TYPES[n.type].cat === 'out')
    let sinkField = sink && sink._field
    if (mutation === 'sink-without-primary') sinkField = null
    out.sink = {
      exists: !!sink,
      declaresNoPort: !!sink && nodeOutputs(sink).length === 0,
      hasField: !!sinkField && sinkField.length === RES * (terrainDef.lattice === 'hex' ? Math.round(RES * 2 / Math.sqrt(3)) : RES),
      finite: !!sinkField && Number.isFinite(sinkField[0]) && Number.isFinite(sinkField[sinkField.length - 1]),
    }

    // --- the multi-output machinery must actually work ------------------------------------
    // Every shipped type declares exactly one output, so the N>1 paths in portPos / portAt /
    // nodeH / drawNode have nothing exercising them. Shipping them unexercised would be dead code
    // presented as a feature. Register a temporary two-output type and drive the real functions.
    const probeType = '__portProbe'
    TYPES[probeType] = {
      cat: 'gen', name: 'Port Probe', ins: [], params: [],
      eval: () => newField(),
      outputs: [
        { id: 'height', name: 'Height', kind: 'scalarRaster', storage: 'R32F', components: 1, semantic: 'relativeHeight', unit: 'none', primary: true },
        { id: 'flow', name: 'Flow', kind: 'scalarRaster', storage: 'R32F', components: 1, semantic: 'flow', unit: 'none' },
      ],
      ports: { version: 1, source: 'declared', roster: false, dynamic: null, groups: {} },
    }
    const probe = makeNode(probeType, 900, 500)
    const single = nodes.find(n => n.type === 'perlin') || makeNode('perlin', 900, 700)

    const p0 = portPos(probe, 'out', 0), p1 = portPos(probe, 'out', 1)
    const sole = portPos(single, 'out', 0)
    const soleH = nodeH(single)
    out.multi = {
      distinctPositions: p0.y !== p1.y && p0.x === p1.x,
      // A single-output node must keep the EXACT previous geometry: centred on the right edge.
      singleOutputUnmoved: Math.abs(sole.y - (single.y + soleH / 2)) < 1e-9 && sole.x === single.x + single.w,
      heightGrew: nodeH(probe) >= 38 + 2 * 15,
      outputCount: nodeOutputs(probe).length,
      soleOutputCount: nodeOutputs(single).length,
      sinkHasNoOutput: nodeOutputs({ type: 'output' }).length === 0,
    }
    // portAt must be able to hit BOTH ports, not just whichever is nearer the centre.
    const hit0 = portAt(p0.x, p0.y), hit1 = portAt(p1.x, p1.y)
    out.multi.hitsFirst = !!hit0 && hit0.node === probe.id && hit0.which === 'out' && (hit0.slot || 0) === 0
    out.multi.hitsSecond = !!hit1 && hit1.node === probe.id && hit1.which === 'out' && hit1.slot === 1
    if (mutation === 'single-output-geometry') {
      // Model the defect: both outputs land on the same point, so the second is unreachable.
      out.multi.distinctPositions = false
      out.multi.hitsSecond = false
    }
    // An edge leaving the SECOND output must report slot 1, so the wire is drawn from the right port.
    const probeSink = makeNode('output', 1100, 500)
    edges.push({ from: probe.id, fromPort: 'flow', to: probeSink.id, toPort: 'height', slot: 0 })
    out.multi.outSlotResolved = outSlotForEdge(edges[edges.length - 1]) === 1
    // An edge with no port identity resolves to 0 rather than guessing.
    out.multi.legacyEdgeResolvesToZero = outSlotForEdge({ from: probe.id, to: probeSink.id, slot: 0 }) === 0
    edges.pop()
    delete TYPES[probeType]

    // A deferred source is permitted and reported as deferred, not silently resolved.
    const def1 = canConnect(P({ id: 'o', semanticFrom: { mode: 'inherit', port: 'in' } }), P({ id: 'i', semantic: 'temperature', unit: 'degC' }))
    out.deferredAllowed = def1.ok === true && def1.deferred === true

    return out
  }, mutation)

  const gates = {
    everyTypeHasPorts: report.withPorts === report.typeCount && report.typeCount > 0,
    rosterFullyAdapted: report.adapted === report.rosterCount && report.rosterCount === 79,
    noUnregisteredTypes: report.unregistered.length === 0,
    insUnchanged: report.insDrift.length === 0,
    registrationClean: report.registrationProblems.length === 0,
    shippedEdgesAllLegal: report.refusedShipped.length === 0,
    everyMaskSlotAcceptsAGenerator: report.maskRefusals.length === 0 && report.maskSlots === 30,
    illegalPairsRefused: report.illegalAccepted.length === 0,
    undemandedOutputNotComputed: report.demand.undemanded.hasVector === false
      && report.demand.undemanded.hasPrimary === true && report.demand.undemanded.fieldIsPrimary === true,
    demandedVectorOutputCorrect: report.demand.demanded.hasVector === true
      && report.demand.demanded.interleavedLength === true && report.demand.demanded.unitLength === true
      && report.demand.demanded.finite === true,
    sinkPublishesNoPortButKeepsItsValue: report.sink.exists === true && report.sink.declaresNoPort === true
      && report.sink.hasField === true && report.sink.finite === true,
    multiOutputGeometry: report.multi.distinctPositions === true && report.multi.hitsFirst === true
      && report.multi.hitsSecond === true && report.multi.outputCount === 2 && report.multi.heightGrew === true
      && report.multi.outSlotResolved === true && report.multi.legacyEdgeResolvesToZero === true,
    singleOutputGeometryUnchanged: report.multi.singleOutputUnmoved === true && report.multi.soleOutputCount === 1
      && report.multi.sinkHasNoOutput === true,
    deferredSourceAllowed: report.deferredAllowed === true,
    // Absence of evidence is failure: a run that compared no edges proves nothing.
    evidenceNonEmpty: report.shippedEdgesChecked > 0,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — that gate is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  console.log(`${ok ? 'PASS' : 'FAIL'}  port contract types=${report.typeCount} adapted=${report.adapted}/${report.rosterCount} `
    + `shippedEdges=${report.shippedEdgesChecked} refused=${report.refusedShipped.length} maskSlots=${report.maskSlots} maskRefused=${report.maskRefusals.length} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
