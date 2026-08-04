// S8.2 / S8.5 — connection-time type rejection on the REAL authoring path.
//
// The audit found canConnect imported into legacy.js and re-exported through the test bridge, and
// called from nowhere else: `grep -nE "canConnect" src/legacy.js` returned exactly two lines, the
// import and the bridge export. So the library could refuse a wire and the application made it
// anyway. Both S8.2 ("incompatible branches are rejected at connection time") and S8.5 ("typed
// ports reject incompatible wires") were therefore gated by oracles exercising the library, not the
// app — the vacuous gate in its purest form.
//
// This oracle drives linkDrop(), the single mutating entry point the mouseup handler and the
// drag-out quick-create menu both call. Its halves are opposite endpoints:
//   * every wire in every shipped graph must SURVIVE the refusal — a type check that rejects the
//     product's own documents is an outage, not a gate;
//   * knowingly illegal wires must be REFUSED, leaving the graph and undo stack untouched.
//
// WHICH ILLEGAL WIRES ARE EVEN REACHABLE was measured, not assumed, and the answer pruned the first
// draft of this file:
//   * no shipped type declares an output in metres — every static `unit` in the registry is 'none'
//     — so UNIT_MISMATCH is unreachable from static descriptors. It IS reachable through a Variable,
//     whose unit is resolved live from the document (S8.3), and that is the fixture used here.
//   * no type declares a labelRaster or featureSet output, so LABEL_INTO_CONTINUOUS stays
//     unreachable. ports.js already says so in its own comments; this oracle does not pretend to
//     cover it.
//   * `normals` is the only vectorRaster output in the registry, which makes it the one available
//     KIND_MISMATCH source.
//
// The mutations all perturb the LIVE REGISTRY rather than this file's copy of the answer. That is
// the point: if the drop path did not consult the port table, mutating the table would change
// nothing and the illegal wire would be refused in the mutated run too.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'mask-port-accepts-any-unit',   // blend's mask input stops being anyMask -> metres wire lands
  'normals-declares-scalar',      // the only vector output claims scalar -> kind wire lands
  'every-input-demands-vectors',  // shipped graphs stop being legal under their own check
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
    const out = { mutation: mutation || null, shipped: [] }

    // --- live-registry mutations, applied before anything is measured -------------------------
    // Two of these were silently no-ops on the first run and the gate reported VACUOUS: assigning
    // to a port descriptor field does nothing when the descriptor is frozen, and page.evaluate
    // bodies run in sloppy mode where a frozen write throws nothing. So each mutation now REPLACES
    // the descriptor objects rather than writing through them, and records whether the registry
    // actually moved. A mutation that did not apply is asserted below as an error — the alternative
    // is a control that reports "not detected" when the truth is "not attempted".
    const remap = (arr, fn) => { if (!Array.isArray(arr)) return arr; for (let i = 0; i < arr.length; i++) arr[i] = fn(arr[i]); return arr }
    if (mutation === 'mask-port-accepts-any-unit') {
      TYPES.blend.inputs = remap((TYPES.blend.inputs || []).slice(),
        p => p.semantic === 'anyMask' ? { ...p, semantic: 'anyScalarRaster' } : p)
    }
    if (mutation === 'normals-declares-scalar') {
      // components must move with kind, or COMPONENTS_MISMATCH refuses the wire for a second reason
      // and the control would pass for the wrong one.
      TYPES.normals.outputs = remap((TYPES.normals.outputs || []).slice(),
        p => p.kind === 'vectorRaster' ? { ...p, kind: 'scalarRaster', components: 1 } : p)
    }
    if (mutation === 'every-input-demands-vectors') {
      for (const t of Object.keys(TYPES)) {
        if (!Array.isArray(TYPES[t].inputs) || !TYPES[t].inputs.length) continue
        TYPES[t].inputs = remap(TYPES[t].inputs.slice(), p => ({ ...p, kind: 'vectorRaster' }))
      }
    }
    out.applied = mutation === 'mask-port-accepts-any-unit'
      ? !(TYPES.blend.inputs || []).some(p => p.semantic === 'anyMask')
      : mutation === 'normals-declares-scalar'
        ? !(TYPES.normals.outputs || []).some(p => p.kind === 'vectorRaster')
        : mutation === 'every-input-demands-vectors'
          ? (TYPES.blend.inputs || []).every(p => p.kind === 'vectorRaster')
          : true

    // --- half one: every shipped wiring must remain legal --------------------------------------
    // newTerrainDocument(withDefault, template, alreadyConfirmed). The third argument matters:
    // without it the confirm() is auto-dismissed headless, the call returns false, and all three
    // "templates" silently measure the same boot graph — which is exactly what the first draft of
    // this oracle did, reporting 18 edges that were 6 edges counted three times.
    for (const [label, withDefault, template] of [['canyon', false, 'canyon'], ['default', true, ''], ['blank', false, '']]) {
      const built = newTerrainDocument(withDefault, template, true)
      const rows = []
      for (const e of edges) {
        const from = nodeById(e.from), to = nodeById(e.to)
        if (!from || !to) { rows.push({ edge: `${e.from}->${e.to}`, ok: false, code: 'DANGLING' }); continue }
        const v = wireVerdict(from, e.fromSlot || 0, to, e.slot)
        rows.push({ edge: `${from.type}->${to.type}:${e.slot}`, ok: !!(v && v.ok), code: v && v.code })
      }
      out.shipped.push({ template: label, built: built !== false, edges: rows.length, refused: rows.filter(r => !r.ok) })
    }

    // --- half two: illegal wires refused by the DROP PATH --------------------------------------
    newTerrainDocument(false, '', true)

    // (a) KIND_MISMATCH: normals publishes TWO outputs — slot 0 'height' is a scalarRaster and
    // slot 1 'normal' is the 3-component vectorRaster. Slot 1 is the one that must be refused, and
    // using slot 0 by mistake is why the first run of this gate reported the wire as accepted.
    const nrm = makeNode('normals', 60, 60), blend = makeNode('blend', 400, 60)
    let before = edges.length
    const kindDrop = linkDrop(nrm.id, 1, blend.id, 0)
    out.kind = { accepted: !!(kindDrop && kindDrop.ok), code: kindDrop && kindDrop.code,
      reason: kindDrop && kindDrop.reason ? String(kindDrop.reason).slice(0, 140) : null,
      unchanged: edges.length === before }

    // (b) UNIT_MISMATCH: a Variable declared in metres into blend's dimensionless mask input.
    VARS.setDocumentVariables([{ id: 'seaLevelM', name: 'Sea level', value: 120, unit: 'm' }])
    const vnode = makeNode('variable', 60, 300)
    vnode.params.varId = 'seaLevelM'
    before = edges.length
    const unitDrop = linkDrop(vnode.id, 0, blend.id, 2)
    out.unit = { accepted: !!(unitDrop && unitDrop.ok), code: unitDrop && unitDrop.code,
      reason: unitDrop && unitDrop.reason ? String(unitDrop.reason).slice(0, 140) : null,
      unchanged: edges.length === before,
      declaredUnit: (nodeOutputs(vnode)[0] || {}).unit }

    // (c) the same Variable made dimensionless must be ACCEPTED through the same call, or all of
    // the above is satisfied by a check that refuses everything.
    VARS.setDocumentVariables([{ id: 'plainVar', name: 'Plain', value: 0.5, unit: 'none' }])
    const pnode = makeNode('variable', 60, 460)
    pnode.params.varId = 'plainVar'
    before = edges.length
    const legal = linkDrop(pnode.id, 0, blend.id, 2)
    out.legal = { accepted: !!(legal && legal.ok), edgeAdded: edges.length === before + 1 }

    // (d) a refused drop must not have written history either.
    const undoBefore = undoStack.length
    linkDrop(nrm.id, 1, blend.id, 1)
    out.history = { undoBefore, undoAfter: undoStack.length, unchanged: undoStack.length === undoBefore }
    return out
  }, mutation)

  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }

  // Absence of evidence is a failure. Both the total and the DISTINCTNESS are asserted: three
  // templates that all report the same edge count are one graph counted three times.
  const totalEdges = report.shipped.reduce((n, s) => n + s.edges, 0)
  const counts = report.shipped.map(s => s.edges)
  check('every template actually built', report.shipped.every(s => s.built), report.shipped.map(s => s.built))
  check('shipped corpus non-empty', totalEdges >= 5, totalEdges)
  check('more than one template contributed wires', report.shipped.filter(s => s.edges > 0).length >= 2, counts)
  check('templates are distinct graphs', new Set(counts).size >= 2, counts)
  for (const s of report.shipped) {
    check(`shipped graph "${s.template}" is wholly legal`, s.refused.length === 0,
      s.refused.map(r => `${r.edge}:${r.code}`).join(','))
  }
  check('vector->scalar wire refused', report.kind && report.kind.accepted === false, report.kind)
  check('vector refusal names KIND_MISMATCH', report.kind && report.kind.code === 'KIND_MISMATCH', report.kind && report.kind.code)
  check('vector refusal did not mutate the graph', report.kind && report.kind.unchanged, report.kind)
  check('variable resolves its declared metre unit', report.unit && report.unit.declaredUnit === 'm', report.unit && report.unit.declaredUnit)
  check('metres->mask wire refused', report.unit && report.unit.accepted === false, report.unit)
  check('unit refusal names UNIT_MISMATCH', report.unit && report.unit.code === 'UNIT_MISMATCH', report.unit && report.unit.code)
  check('unit refusal carries a reason', !!(report.unit && report.unit.reason), report.unit && report.unit.reason)
  check('unit refusal did not mutate the graph', report.unit && report.unit.unchanged, report.unit)
  check('dimensionless wire through the same call lands', report.legal && report.legal.accepted && report.legal.edgeAdded, report.legal)
  check('a refused drop writes no undo record', report.history && report.history.unchanged, report.history)
  check('no page errors', errors.length === 0, errors)
  // A control that could not perturb production is a broken control, not a passing one.
  check('declared mutation actually applied', report.applied === true, { mutation, applied: report.applied })

  let ok = assertions.every(a => a.ok)
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = assertions.filter(a => !a.ok).map(a => a.name)
  console.log(`${ok ? 'PASS' : 'FAIL'}  connect-time shippedEdges=${counts.join('/')} `
    + `refusedShipped=${report.shipped.reduce((n, s) => n + s.refused.length, 0)} `
    + `kind=${report.kind && report.kind.code} unit=${report.unit && report.unit.code} `
    + `assertions=${assertions.length} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify({ report, failedDetail: assertions.filter(a => !a.ok) }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
