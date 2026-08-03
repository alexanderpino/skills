// S2.5 — staged doctrine validators.
//
// The Legal Order rule is the interesting one: "Analysis must run after the final geometry. Slope
// and curvature computed before erosion describe a landscape that no longer exists." That is a real
// law with real teeth, and nothing in this app enforced it.
//
// It is also the rule most likely to produce a confident false positive, so this oracle MEASURES
// the shipped template graphs and asserts the reading, rather than asserting a rule and hoping
// production agrees. If a shipped graph is flagged, that is either a genuine doctrine violation in
// content the app ships — worth knowing — or a rule that is too crude. Either way the number is
// recorded here rather than argued about.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'analysis-before-erosion',  // wire a derived product into an eroder — must be caught
  'shipped-graph-flagged',    // pretend a template graph is illegal — the reading must be asserted
  'carried-derived-lens',     // a derived map declared as carried state
  'stage-claims-armed',       // an unarmed stage claiming to be armed
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
    const { validateLegalOrder, validateLens, DOCTRINE_STAGES, DERIVED_PRODUCERS, HEIGHT_WRITERS } = DOCTRINE
    const out = { mutation: mutation || null }

    // --- 1. the shipped graphs, measured -----------------------------------------------------
    const shipped = []
    for (const [name, build] of [['default', () => defaultGraph()], ['canyon', () => newTerrainDocument(false, 'canyon')]]) {
      build()
      const v = validateLegalOrder({ nodes, edges })
      shipped.push({
        graph: name,
        nodes: nodes.length,
        producers: v.stats.producers,
        pathsWalked: v.stats.pathsWalked,
        problems: v.problems.map(p => ({ code: p.code, path: p.path.map(id => (nodes.find(n => n.id === id) || {}).type) })),
      })
    }
    if (mutation === 'shipped-graph-flagged') shipped[0].problems.push({ code: 'ORDER_DERIVED_BEFORE_GEOMETRY', path: ['fake'] })
    out.shipped = shipped

    // --- 2. a deliberately illegal graph MUST be caught ---------------------------------------
    // perlin -> d_slope -> hydraulic -> output. The slope is computed, then hydraulic rewrites the
    // very surface it described. This is the canonical violation.
    blankGraph()
    const gen = makeNode('perlin', 60, 60)
    const slope = makeNode('d_slope', 260, 60)
    const ero = makeNode('hydraulic', 460, 60)
    const sink = makeNode('output', 660, 60)
    edges.push({ from: gen.id, to: slope.id, slot: 0 })
    if (mutation !== 'analysis-before-erosion') edges.push({ from: slope.id, to: ero.id, slot: 0 })
    edges.push({ from: ero.id, to: sink.id, slot: 0 })
    const illegal = validateLegalOrder({ nodes, edges })
    out.illegalPathsWalked = illegal.stats.pathsWalked
    out.illegalProducers = illegal.stats.producers
    out.illegal = {
      caught: illegal.problems.some(p => p.code === 'ORDER_DERIVED_BEFORE_GEOMETRY'),
      problems: illegal.problems.map(p => ({ code: p.code, path: p.path.map(id => (nodes.find(n => n.id === id) || {}).type) })),
    }

    // A disabled edge must not be walked: muting the wire makes the graph legal again.
    edges[edges.length - 2].disabled = true
    out.illegal.mutedEdgeIsLegal = !validateLegalOrder({ nodes, edges }).problems.some(p => p.code === 'ORDER_DERIVED_BEFORE_GEOMETRY')

    // --- 3. the legal ordering must NOT be flagged --------------------------------------------
    // perlin -> hydraulic -> d_slope -> output. Analysis after geometry: correct, and must be quiet.
    blankGraph()
    const g2 = makeNode('perlin', 60, 60)
    const e2 = makeNode('hydraulic', 260, 60)
    const s2 = makeNode('d_slope', 460, 60)
    const o2 = makeNode('output', 660, 60)
    edges.push({ from: g2.id, to: e2.id, slot: 0 })
    edges.push({ from: e2.id, to: s2.id, slot: 0 })
    edges.push({ from: s2.id, to: o2.id, slot: 0 })
    const legalRun = validateLegalOrder({ nodes, edges })
    out.legalOrderingQuiet = legalRun.problems.length === 0
    out.legalPathsWalked = legalRun.stats.pathsWalked

    // --- 4. lens and staging -------------------------------------------------------------------
    const lensProblems = validateLens([{ mapId: 'slope', lens: 'state' }], AUXMAPS.AUX_MAPS).map(p => p.code)
    out.carriedDerivedRefused = mutation === 'carried-derived-lens' ? false : lensProblems.includes('LENS_CARRIED_DERIVED')
    out.derivedLensAccepted = validateLens([{ mapId: 'slope', lens: 'derived' }], AUXMAPS.AUX_MAPS).length === 0

    // Staging is a dated decision, not an oversight: an unarmed stage must name the sprint that
    // arms it and why it cannot be armed now.
    const stages = Object.entries(DOCTRINE_STAGES).map(([k, v]) => ({ id: k, armed: !!v.armed, sprint: v.sprint, hasReason: !!v.reason }))
    if (mutation === 'stage-claims-armed') { const s = stages.find(x => x.id === 'snowRule'); if (s) s.armed = true }
    out.stages = stages
    out.unarmedStagesExplained = stages.filter(s => !s.armed).every(s => s.sprint && s.hasReason)
    // The two stages the plan says are NOT yet armed must still be unarmed. Arming one early gives
    // a validator with no field to check, which passes vacuously and reads as coverage.
    out.stagedCorrectly = stages.find(s => s.id === 'hydraulicCoEvolution').armed === false
      && stages.find(s => s.id === 'snowRule').armed === false
    out.inventory = { producers: DERIVED_PRODUCERS.length, writers: HEIGHT_WRITERS.length }
    return out
  }, mutation)

  const shippedProblems = report.shipped.reduce((a, g) => a + g.problems.length, 0)
  const gates = {
    // The measured reading, asserted. If a shipped template ever starts violating Legal Order this
    // goes red, which is the point of measuring rather than assuming.
    shippedGraphsLegal: shippedProblems === 0,
    illegalOrderingCaught: report.illegal.caught === true,
    mutedEdgeNotWalked: report.illegal.mutedEdgeIsLegal === true,
    legalOrderingQuiet: report.legalOrderingQuiet === true,
    carriedDerivedRefused: report.carriedDerivedRefused === true,
    derivedLensAccepted: report.derivedLensAccepted === true,
    unarmedStagesExplained: report.unarmedStagesExplained === true,
    stagedCorrectly: report.stagedCorrectly === true,
    // Absence of evidence is failure: a validator that walked no paths proves nothing. The
    // evidence comes from the CONSTRUCTED graphs, because the shipped templates turn out to
    // contain no derived producer at all (measured: producers=0 on both), which makes their
    // "0 problems" reading vacuous. It is still asserted — a template that later grows an analysis
    // node must not quietly start violating Legal Order — but it is not what arms this gate.
    evidenceNonEmpty: report.shipped.every(g => g.nodes > 0)
      && report.illegalPathsWalked > 0 && report.legalPathsWalked > 0
      && report.illegalProducers > 0
      && report.inventory.producers > 0 && report.inventory.writers > 0,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — that gate is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  const shippedProducers = report.shipped.reduce((a, g) => a + g.producers, 0)
  console.log(`${ok ? 'PASS' : 'FAIL'}  doctrine shippedProblems=${shippedProblems} shippedProducers=${shippedProducers} `
    + `producers=${report.inventory.producers} writers=${report.inventory.writers} `
    + `armed=${report.stages.filter(s => s.armed).length}/${report.stages.length} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
