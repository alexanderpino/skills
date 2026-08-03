// S8.2 — Switch / Gate conditional flow with lazy branch demand.
//
// The claim that matters is negative: an unselected branch is NEVER EVALUATED. A gate that only
// checked "the selected value comes out" would pass on an implementation that computes all three
// branches and throws two away — which is exactly what this app did before, and exactly what the
// story exists to stop. So the branches here are INSTRUMENTED: each records that it ran, and the
// gate asserts the unselected ones did not.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'eager-branches',
  'wrong-branch-selected',
  'gate-closed-still-demands',
  'gate-closed-wrong-type',
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

;(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', e => { if (e.message !== 'WebSocket closed without opened.') errors.push(e.message) })
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1400)

  const report = await page.evaluate(mutation => {
    USE_GPU = false; RES = 64; TARGET_RES = 64; terrainDef.lattice = 'square'
    const out = { mutation: mutation || null }
    const N = RES * RES

    // Three instrumented branch types. Each returns a distinct constant AND records that it ran,
    // so "was this branch computed" is a measured fact rather than an inference from timing.
    const ran = { A: 0, B: 0, C: 0 }
    for (const [name, value] of [['A', 0.25], ['B', 0.5], ['C', 0.75]]) {
      TYPES['__branch' + name] = {
        cat: 'gen', name: 'Branch ' + name, ins: [], params: [],
        eval: () => { ran[name]++; return newField(value) },
        outputs: [{ id: 'out', name: 'Out', kind: 'scalarRaster', storage: 'R32F', components: 1,
          semantic: 'relativeHeight', unit: 'none', primary: true }],
        ports: { version: 1, source: 'declared', roster: false, dynamic: null, groups: {} },
      }
    }

    const selections = []
    for (const sel of ['0', '1', '2']) {
      blankGraph()
      const a = makeNode('__branchA', 40, 40), b = makeNode('__branchB', 40, 140), c = makeNode('__branchC', 40, 240)
      const sw = makeNode('switch', 240, 140)
      const sink = makeNode('output', 440, 140)
      sw.params.branch = sel
      edges.push({ from: a.id, to: sw.id, slot: 0 })
      edges.push({ from: b.id, to: sw.id, slot: 1 })
      edges.push({ from: c.id, to: sw.id, slot: 2 })
      edges.push({ from: sw.id, to: sink.id, slot: 0 })
      ran.A = ran.B = ran.C = 0
      nodes.forEach(n => { n._dirty = true; n._field = null })
      // Evaluate the SWITCH itself. Two reasons. The Output sink normalises its input, which
      // would rewrite the very constants these fixtures use to identify a branch. And evalGraph's
      // blanket pass visits every node for its own thumbnail — which the story explicitly permits
      // ("thumbnail policy may request branch previews explicitly"). What must not happen is the
      // Switch DRAGGING an unselected branch in through its own input edge, and evaluating the
      // Switch's cone is exactly what measures that.
      const value = evalExact(sw.id, new Set())
      const expected = [0.25, 0.5, 0.75][parseInt(sel, 10)]
      let matches = 0
      for (let i = 0; i < N; i++) if (Math.abs(value[i] - expected) < 1e-6) matches++
      const counts = { A: ran.A, B: ran.B, C: ran.C }
      if (mutation === 'eager-branches') { counts.A = 1; counts.B = 1; counts.C = 1 }
      selections.push({
        sel, expected,
        correctValue: mutation === 'wrong-branch-selected' ? false : matches === N,
        ran: counts,
        onlySelectedRan: ['A', 'B', 'C'].every((k, i) => (i === parseInt(sel, 10) ? counts[k] > 0 : counts[k] === 0)),
      })
    }
    out.selections = selections

    // --- Gate: closed does not demand its input, and stays type-compatible --------------------
    blankGraph()
    const src = makeNode('__branchA', 40, 40)
    const g = makeNode('gate', 240, 40)
    const gsink = makeNode('output', 440, 40)
    edges.push({ from: src.id, to: g.id, slot: 0 })
    edges.push({ from: g.id, to: gsink.id, slot: 0 })

    g.params.state = 'open'
    ran.A = 0; nodes.forEach(n => { n._dirty = true; n._field = null })
    const openValue = evalExact(g.id, new Set())
    const openRan = ran.A

    g.params.state = 'closed'; g.params.closedValue = 0.125
    ran.A = 0; nodes.forEach(n => { n._dirty = true; n._field = null })
    const closedValue = evalExact(g.id, new Set())
    let closedRan = ran.A
    if (mutation === 'gate-closed-still-demands') closedRan = 1

    let openOk = 0, closedOk = 0
    for (let i = 0; i < N; i++) {
      if (Math.abs(openValue[i] - 0.25) < 1e-6) openOk++
      if (Math.abs(closedValue[i] - 0.125) < 1e-6) closedOk++
    }
    const gOut = (TYPES.gate.outputs || [])[0] || {}
    out.gate = {
      openRan, closedRan,
      openPassesThrough: openOk === N,
      closedEmitsDeclaredValue: closedOk === N,
      closedLength: closedValue.length === N,
      // Type preserved by construction: the closed value is a full field, not null or a scalar.
      typePreserved: mutation === 'gate-closed-wrong-type' ? false : closedValue.length === openValue.length,
      inheritsSemantic: !!(gOut.semanticFrom && gOut.semanticFrom.mode === 'inherit'),
    }

    for (const k of ['A', 'B', 'C']) delete TYPES['__branch' + k]
    return out
  }, mutation)

  const sels = report.selections
  const gates = {
    everyBranchReturnsItsValue: sels.every(s => s.correctValue === true),
    onlySelectedBranchEvaluated: sels.every(s => s.onlySelectedRan === true),
    gateOpenPassesThrough: report.gate.openPassesThrough === true && report.gate.openRan > 0,
    gateClosedEmitsDeclaredValue: report.gate.closedEmitsDeclaredValue === true,
    gateClosedDoesNotDemandInput: report.gate.closedRan === 0,
    gateTypePreserved: report.gate.typePreserved === true && report.gate.inheritsSemantic === true,
    evidenceNonEmpty: sels.length === 3 && report.gate.closedLength === true,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — that gate is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  console.log(`${ok ? 'PASS' : 'FAIL'}  switch/gate selections=${sels.length} `
    + `gateOpenRan=${report.gate.openRan} gateClosedRan=${report.gate.closedRan} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
