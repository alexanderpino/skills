// S4.3 — authored water sources and river guides.
//
// THE HEADLINE, in the story's words: "A big river crosses a desert." Zero rainfall, one source. The
// discharge immediately downstream of it equals the authored source flow, it is conserved to the
// outlet absent sinks, and removing the source returns EXACTLY zero. The story is explicit that this
// is stronger than a source/no-source ratio, and it is: a ratio is satisfied by any implementation
// that puts *some* water in the right general area, whereas "1200.000 m3/s at the outlet and exactly
// 0.0 with the source deleted" pins both the magnitude and the cause.
//
// WHY THE FIXTURE IS A SINGLE-THREAD VALLEY. `desert()` is a plane falling in +x with a shallow
// cross-valley V centred on row 32. The cross-slope (0.0078 per cell) is steeper than the downstream
// slope (0.0053 per cell), so a cell ON the valley axis has exactly ONE downslope neighbour — the
// next axis cell — while every off-axis cell still spreads across several. That gives a river whose
// route is known in closed form: the source at (200 m, 320 m) seeds cell (20, 32), and the only cells
// that may carry water are (20..95, 32). Anything else carrying discharge is a defect with a name.
// It also gives the domain exactly ONE outlet, cell (95, 32), so "conserved to the outlet" is a
// single number rather than a sum over an edge that double-counts water crossing a corner.
//
// Pure-module: it imports src/core/water-sources.js under plain node and routes with the REAL
// src/core/hydrology.js — unpatched, always — because the story's whole claim is that a source seeds
// the same accumulation stack as drainage area. Substituting a private accumulator here would be
// checking a different program than the one that ships.
//
// SALINITY IS OUT OF SCOPE and this file asserts its ABSENCE from the schema, because "we did not
// implement it" and "we implemented it badly" look identical on a serialized record until someone
// checks.
const path = require('path')
const fs = require('fs')
const { pathToFileURL } = require('url')

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  // --- the physics -------------------------------------------------------------------------------
  'source-stamps-height',        // stamp the source into the surface -- the story's named failure
  'source-scaled-by-cell-area',  // treat authored m3/s as a per-area rate: 100x on 10 m cells
  'source-cell-swaps-axes',      // world x/z swapped when indexing: the spring lands somewhere else
  'source-splats-one-ring',      // splat the source over its one-ring so it "reads" -- water upstream
  'epsilon-baseflow',            // a small constant everywhere: the desert is no longer exactly dry
  'disabled-source-still-injects',
  'boundary-inflow-anywhere',    // a river entering off-map, injected in the middle of the map
  // --- the guides --------------------------------------------------------------------------------
  'guide-seeds-tail',            // seed the guide's mouth instead of its head
  'reference-guide-seeds',       // a reference line silently becomes water
  // --- identity and persistence ------------------------------------------------------------------
  'positional-ids',              // mint an id from arrival order: deleting one renames the rest
  'duplicate-ids-allowed',       // two features answering to one document-wide handle
  'nondeterministic-serialization', // drop the sort: the file depends on editor insertion order
  'paste-keeps-id',              // copy/paste produces two features with the same id
  'accepts-unknown-kind',        // a kind outside the corpus enum, which nothing downstream can act on
  'accepts-negative-discharge',  // a "sink" as a negative seed: Q^0.5 of a negative reach
  // --- the records that leave the node ------------------------------------------------------------
  // Every mutation below was first injected into water-sources.js as a silent defect and PASSED all
  // 68 assertions this file used to hold. They were values that reach an output port and were
  // constrained by nothing: an adversarial pass found fifteen in one sweep.
  'kind-label-always-spring',    // every source labelled "Spring" on the sources port
  'analyze-flag-inverted',       // S4.6 told to analyse reference lines and skip channel guides
  'per-cell-split-doubled',      // the placement reports twice the m3/s it injected
  'placement-cells-truncated',   // a 21-cell footprint reports as one cell
  'record-drops-temperature',    // the authored temperature never leaves the node
  'record-drops-radius',         // the authored footprint radius never leaves the node
  'text-r-key-moves-source',     // r= lands in zM: the source moves instead of gaining a footprint
  'text-on-key-ignored',         // on=false is parsed and discarded: a disabled source still injects
  'mint-id-nondeterministic',    // a random paste suffix: the same paste produces a different file
  'guide-paste-keeps-id',        // pasting a guide produces two features under one handle
  'boundary-edge-west-only',     // a river entering off-map is refused on three of the four edges
  'total-discharge-doubled',     // the reported total disagrees with the array it summarizes
  'feature-counts-zeroed',       // the node reports no sources while seeding them
  'disabled-placement-reports-q',// a disabled source reports the discharge it did not inject
  'migrate-swallows-foreign-doc',// a project file loads as an empty feature set
  // --- second adversarial round --------------------------------------------------------------------
  // The block above closed fifteen holes. A second sweep of fresh defects found twelve more that it
  // still did not reach — the hex footprint geometry, the guide length, move/paste property carry,
  // the id charset, and four refusals that nothing exercised.
  'guide-length-ignores-z',      // a diagonal guide reports its x extent as its length
  'records-drop-guide-length',   // the emitted guide carries a length of zero
  'hex-footprint-centre-unstaggered', // odd hex rows lose their half-column offset
  'hex-footprint-row-pitch-square',   // the hex row pitch becomes the square one
  'alias-precedence-inverted',   // the alias wins over the canonical field name
  'move-enables-disabled-source',// moving a disabled source turns it on
  'paste-drops-footprint',       // a pasted distributed source becomes a point
  'paste-enables-disabled-source', // a pasted disabled source starts injecting
  'id-charset-unchecked',        // an id with a slash or a space becomes a file name
  'guides-unsorted',             // guide order in the file follows editor insertion order
  'zero-length-guide-accepted',  // every control point in the same place is "a guide with no conflict"
  // NOT ARMED, on purpose: removing the empty-footprint fallback in footprintCells changes nothing.
  // The home cell is always inside the scan window at distance 0 from its own centre, so the list is
  // never empty — measured over 720 placements, zero behavioural difference. A bit-identical
  // mutation scores ARMED and proves nothing, which is the failure this file exists to avoid, so the
  // dead branch is reported rather than gated.
  // NB: no square brackets in comments in this block. See the truncation self-check below.
  'negative-target-flow-accepted', // a guide that removes water from its own head
  'surface-length-unchecked',    // sources read their elevation off the end of the array
  'canonical-doc-kind-wrong',    // the file is stamped with a kind no reader recognises
  // --- third adversarial round ---------------------------------------------------------------------
  // Nine more, two of them guardrail violations rather than wrong numbers.
  'kind-labels-swapped',         // a label that names the wrong kind, self-consistently
  'text-guide-q-key-dead',       // the guide target flow key in the authoring block goes nowhere
  'cell-floor-not-round',        // an off-centre source lands in the cell below and left
  'enabled-accepts-truthy',      // "yes" and 0 both become an enabled state nobody chose
  'zero-temperature-falsy',      // a 0 degrees C glacial source loses its temperature
  'zero-discharge-falsy',        // a 0 m3/s source loses its authored discharge
  'flat-array-misclassified',    // a guide in a flat feature list is read as a source
  'guide-point-takes-y',         // a control point accepts an authored elevation
  'mint-id-no-length-cap',       // a paste mints a handle the module then refuses
  // --- fourth adversarial round --------------------------------------------------------------------
  // The refusal paths, plus two format claims. Two further guards were found to be provably redundant
  // and are NOT armed — see the note beside the fourth-round assertions.
  'feature-ids-sources-only',    // a pasted guide can be minted onto an existing guide's id
  'paste-without-taken-collides',// a paste from a context menu keeps the id it was copied from
  'trailing-newline-dropped',    // the canonical text stops ending the way the format says
  'sources-field-array-unchecked', // a string where a list belongs becomes an empty feature set
  'supply-domain-shape-unchecked', // a fractional or zero domain indexes off the end of the array
  'combine-length-unchecked',    // two supply arrays of different lengths add anyway
  'schema-version-unchecked',    // a fractional or negative schema version is accepted
  'text-point-arity-unchecked',  // a three-part control point silently drops its third number
]
const PATCHES = {
  'source-stamps-height': { core: [[
    '      supply[ci] += each',
    '      supply[ci] += each\n      surface[ci] = surface[ci] - 0.01']] },
  'source-scaled-by-cell-area': { core: [[
    '    const each = seed.q / cells.length',
    '    const each = seed.q * cellSizeM * cellSizeM / cells.length']] },
  'source-cell-swaps-axes': { core: [
    ['  const v = zM / rowPitch', '  const v = xM / rowPitch'],
    ['  const u = xM / cellSizeM - off', '  const u = zM / cellSizeM - off'],
  ] },
  'source-splats-one-ring': { core: [[
    '    const cells = footprintCells(home, seed.radiusM, w, hgt, cellSizeM, hex)',
    '    const cells = footprintCells(home, seed.radiusM, w, hgt, cellSizeM, hex)\n'
    + '    for (const d of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {\n'
    + '      const cc = home.col + d[0], rr = home.row + d[1]\n'
    + '      if (cc >= 0 && rr >= 0 && cc < w && rr < hgt && cells.indexOf(rr * w + cc) < 0) cells.push(rr * w + cc)\n'
    + '    }']] },
  'epsilon-baseflow': { core: [[
    '  const supply = new Float64Array(N)\n  const placements = []',
    '  const supply = new Float64Array(N)\n  for (let i = 0; i < N; i++) supply[i] = 1e-9\n  const placements = []']] },
  'disabled-source-still-injects': { core: [['    if (!seed.enabled) {', '    if (false && !seed.enabled) {']] },
  'boundary-inflow-anywhere': { core: [[
    '    if (seed.requireEdge && !onEdge(home.col, home.row, w, hgt)) {',
    '    if (false && seed.requireEdge && !onEdge(home.col, home.row, w, hgt)) {']] },
  'guide-seeds-tail': { core: [[
    '        xM: g.points[0].x, zM: g.points[0].z,',
    '        xM: g.points[g.points.length - 1].x, zM: g.points[g.points.length - 1].z,']] },
  'reference-guide-seeds': { core: [["      if (g.intent !== 'channel') continue", '      if (false) continue']] },
  'positional-ids': { core: [[
    '  const id = raw.id\n'
    + '  if (typeof id !== \'string\' || !ID_RE.test(id)) {\n'
    + '    fail(\'ID_INVALID\', `water source id ${JSON.stringify(id)} must be an authored string matching ${ID_RE}`, { id })\n'
    + '  }',
    '  let id = raw.id\n'
    + '  if (typeof id !== \'string\' || !ID_RE.test(id)) {\n'
    + '    id = \'source\' + (normalizeSource.seq = (normalizeSource.seq || 0) + 1)\n'
    + '  }']] },
  'duplicate-ids-allowed': { core: [["    if (seen.has(f.id)) fail('ID_DUPLICATE'", "    if (false && seen.has(f.id)) fail('ID_DUPLICATE'"]] },
  'nondeterministic-serialization': { core: [[
    '  const sources = rawSources.map(normalizeSource).sort(byId)',
    '  const sources = rawSources.map(normalizeSource)']] },
  'paste-keeps-id': { core: [['  const id = mintFeatureId(normalized.id, takenSet)', '  const id = normalized.id']] },
  'accepts-unknown-kind': { core: [['  if (!SOURCE_KINDS.includes(kind)) {', '  if (false && !SOURCE_KINDS.includes(kind)) {']] },
  'accepts-negative-discharge': { core: [['  if (dischargeM3PerS < 0) {', '  if (false && dischargeM3PerS < 0) {']] },
  'kind-label-always-spring': { core: [[
    "      feature: 'waterSource', id: s.id, kind: s.kind, kindLabel: SOURCE_KIND_LABEL[s.kind],",
    "      feature: 'waterSource', id: s.id, kind: s.kind, kindLabel: SOURCE_KIND_LABEL.spring,"]] },
  'analyze-flag-inverted': { core: [[
    "      analyze: g.intent === 'channel',", "      analyze: g.intent !== 'channel',"]] },
  'per-cell-split-doubled': { core: [[
    '      index: home.index, cells: Object.freeze(cells.slice()), qM3PerS: seed.q, qPerCellM3PerS: each,',
    '      index: home.index, cells: Object.freeze(cells.slice()), qM3PerS: seed.q, qPerCellM3PerS: each * 2,']] },
  'placement-cells-truncated': { core: [[
    '      index: home.index, cells: Object.freeze(cells.slice()), qM3PerS: seed.q, qPerCellM3PerS: each,',
    '      index: home.index, cells: Object.freeze([home.index]), qM3PerS: seed.q, qPerCellM3PerS: each,']] },
  'record-drops-temperature': { core: [[
    '      xM: s.xM, zM: s.zM, dischargeM3PerS: s.dischargeM3PerS, radiusM: s.radiusM,\n'
    + '      temperatureC: s.temperatureC, enabled: s.enabled,',
    '      xM: s.xM, zM: s.zM, dischargeM3PerS: s.dischargeM3PerS, radiusM: s.radiusM,\n'
    + '      temperatureC: null, enabled: s.enabled,']] },
  'record-drops-radius': { core: [[
    '      xM: s.xM, zM: s.zM, dischargeM3PerS: s.dischargeM3PerS, radiusM: s.radiusM,\n'
    + '      temperatureC: s.temperatureC, enabled: s.enabled,',
    '      xM: s.xM, zM: s.zM, dischargeM3PerS: s.dischargeM3PerS, radiusM: 0,\n'
    + '      temperatureC: s.temperatureC, enabled: s.enabled,']] },
  'text-r-key-moves-source': { core: [[
    "  const SOURCE_KEYS = { id: 'id', kind: 'kind', x: 'xM', z: 'zM', q: 'dischargeM3PerS', t: 'temperatureC', r: 'radiusM', on: 'enabled' }",
    "  const SOURCE_KEYS = { id: 'id', kind: 'kind', x: 'xM', z: 'zM', q: 'dischargeM3PerS', t: 'temperatureC', r: 'zM', on: 'enabled' }"]] },
  'text-on-key-ignored': { core: [[
    "      if (field === 'enabled') {", "      if (false && field === 'enabled') {"]] },
  'mint-id-nondeterministic': { core: [[
    '    const candidate = `${stem}-${n}`',
    '    const candidate = `${stem}-${Math.floor(Math.random() * 1e9)}`']] },
  'guide-paste-keeps-id': { core: [[
    '    ? normalizeGuide({ ...normalized, id, points: normalized.points.map(p => ({ x: p.x, z: p.z })) })',
    '    ? normalizeGuide({ ...normalized, id: normalized.id, points: normalized.points.map(p => ({ x: p.x, z: p.z })) })']] },
  'boundary-edge-west-only': { core: [[
    'const onEdge = (col, row, w, hgt) => col === 0 || row === 0 || col === w - 1 || row === hgt - 1',
    'const onEdge = (col, row, w, hgt) => col === 0']] },
  'total-discharge-doubled': { core: [['    totalQM3PerS += seed.q', '    totalQM3PerS += seed.q * 2']] },
  'feature-counts-zeroed': { core: [[
    '    sourceCount: set.sources.length, guideCount: set.guides.length,',
    '    sourceCount: 0, guideCount: 0,']] },
  'disabled-placement-reports-q': { core: [[
    '        index: home.index, cells: Object.freeze([]), qM3PerS: 0, qPerCellM3PerS: 0,',
    '        index: home.index, cells: Object.freeze([]), qM3PerS: seed.q, qPerCellM3PerS: seed.q,']] },
  'migrate-swallows-foreign-doc': { core: [[
    '  if (doc.kind !== undefined && doc.kind !== WATER_FEATURE_DOC_KIND) {',
    '  if (false && doc.kind !== undefined && doc.kind !== WATER_FEATURE_DOC_KIND) {']] },
  'guide-length-ignores-z': { core: [[
    '  for (let i = 1; i < points.length; i++) lengthM += Math.hypot(points[i].x - points[i - 1].x, points[i].z - points[i - 1].z)',
    '  for (let i = 1; i < points.length; i++) lengthM += Math.abs(points[i].x - points[i - 1].x)']] },
  'records-drop-guide-length': { core: [[
    '      targetFlowM3PerS: g.targetFlowM3PerS, lengthM: g.lengthM,',
    '      targetFlowM3PerS: g.targetFlowM3PerS, lengthM: 0,']] },
  'hex-footprint-centre-unstaggered': { core: [[
    '    x: col * cellSizeM + (hex && (row & 1) ? 0.5 * cellSizeM : 0),', '    x: col * cellSizeM,']] },
  'hex-footprint-row-pitch-square': { core: [[
    '    z: row * cellSizeM * (hex ? HEX_ROW : 1),', '    z: row * cellSizeM,']] },
  'alias-precedence-inverted': { core: [[
    'const firstDefined = (...vals) => { for (const v of vals) if (v !== undefined && v !== null) return v; return undefined }',
    'const firstDefined = (...vals) => { let r; for (const v of vals) if (v !== undefined && v !== null) r = v; return r }']] },
  'move-enables-disabled-source': { core: [[
    '  return normalizeSource({ ...s, xM, zM })', '  return normalizeSource({ ...s, xM, zM, enabled: true })']] },
  'paste-drops-footprint': { core: [[
    '    : normalizeSource({ ...normalized, id })', '    : normalizeSource({ ...normalized, id, radiusM: 0 })']] },
  'paste-enables-disabled-source': { core: [[
    '    : normalizeSource({ ...normalized, id })', '    : normalizeSource({ ...normalized, id, enabled: true })']] },
  'id-charset-unchecked': { core: [[
    'const ID_RE = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$/', 'const ID_RE = /^.*$/']] },
  'guides-unsorted': { core: [[
    '  const guides = rawGuides.map(normalizeGuide).sort(byId)', '  const guides = rawGuides.map(normalizeGuide)']] },
  'zero-length-guide-accepted': { core: [['  if (!(lengthM > 0)) fail', '  if (false && !(lengthM > 0)) fail']] },
  'negative-target-flow-accepted': { core: [[
    '    if (!Number.isFinite(targetFlowM3PerS) || targetFlowM3PerS < 0) {', '    if (false) {']] },
  'surface-length-unchecked': { core: [['  if (!surface || surface.length !== N) {', '  if (false) {']] },
  'canonical-doc-kind-wrong': { core: [['    kind: WATER_FEATURE_DOC_KIND,', "    kind: 'terrain-studio-project',"]] },
  'kind-labels-swapped': { core: [[
    "  spring: 'Spring',\n  karstResurgence: 'Karst resurgence',",
    "  spring: 'Karst resurgence',\n  karstResurgence: 'Spring',"]] },
  'text-guide-q-key-dead': { core: [[
    "  const GUIDE_KEYS = { id: 'id', intent: 'intent', q: 'targetFlowM3PerS' }",
    "  const GUIDE_KEYS = { id: 'id', intent: 'intent', q: 'lengthM' }"]] },
  'cell-floor-not-round': { core: [
    ['  const row = Math.round(v) || 0', '  const row = Math.floor(v) || 0'],
    ['  const col = Math.round(u) || 0', '  const col = Math.floor(u) || 0']] },
  'enabled-accepts-truthy': { core: [["    if (typeof raw.enabled !== 'boolean') {", '    if (false) {']] },
  'zero-temperature-falsy': { core: [[
    '  const tRaw = firstDefined(raw.temperatureC, raw.temperature)',
    '  const tRaw = raw.temperatureC || raw.temperature']] },
  'zero-discharge-falsy': { core: [[
    '  const dischargeM3PerS = Number(firstDefined(raw.dischargeM3PerS, raw.discharge, raw.q))',
    '  const dischargeM3PerS = Number(raw.dischargeM3PerS || raw.discharge || raw.q)']] },
  'flat-array-misclassified': { core: [[
    "      if (r && (r.feature === 'riverGuide' || Array.isArray(r.points))) rawGuides.push(r)",
    "      if (r && r.feature === 'riverGuide') rawGuides.push(r)"]] },
  'guide-point-takes-y': { core: [[
    '    points.push(Object.freeze({ x, z }))',
    '    points.push(Object.freeze({ x, z, y: Number((p && p.y) || 0) }))']] },
  'mint-id-no-length-cap': { core: [['  stem = stem.slice(0, 56)', '  stem = stem']] },
  'feature-ids-sources-only': { core: [[
    '  return [...set.sources, ...set.guides].map(f => f.id)', '  return set.sources.map(f => f.id)']] },
  'paste-without-taken-collides': { core: [['  takenSet.add(normalized.id)', '  ']] },
  'trailing-newline-dropped': { core: [[
    "  return JSON.stringify(canonicalWaterFeatures(features), null, 2) + '\\n'",
    '  return JSON.stringify(canonicalWaterFeatures(features), null, 2)']] },
  'sources-field-array-unchecked': { core: [[
    "    if (raw.sources !== undefined && !Array.isArray(raw.sources)) fail('FEATURE_SHAPE', 'sources must be an array', { got: typeof raw.sources })",
    '    ']] },
  'supply-domain-shape-unchecked': { core: [[
    '  if (!Number.isInteger(w) || w <= 0 || !Number.isInteger(hgt) || hgt <= 0) {', '  if (false) {']] },
  'combine-length-unchecked': { core: [['  if (!a || !b || a.length !== b.length) {', '  if (false) {']] },
  'schema-version-unchecked': { core: [[
    '  if (!Number.isInteger(version) || version < 0) fail', '  if (false) fail']] },
  'text-point-arity-unchecked': { core: [[
    '        if (parts.length !== 2 || !Number.isFinite(x) || !Number.isFinite(z)) {',
    '        if (!Number.isFinite(x) || !Number.isFinite(z)) {']] },
}
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

// THE RUNNER'S VIEW OF THIS LIST MUST MATCH THIS LIST.
//
// gate.py discovers the allowlist with `const MUTATIONS\s*=\s*\[(.*?)\]` — NON-GREEDY, so it stops
// at the FIRST closing square bracket after the opening one. A bracket inside a comment in that
// block therefore truncates the set of mutations the runner executes, and the runner then prints
// ALL GATES GREEN over the subset it did run. This is not hypothetical: a single `[home.index]` in
// an explanatory comment here cut the executed set from 61 to 41 and the gate stayed green, which
// is exactly the vacuous gate this suite exists to prevent — 20 armed controls silently not run.
// Re-derive the runner's view with its own regex and refuse to start if it disagrees.
{
  const selfSrc = fs.readFileSync(__filename, 'utf8')
  const block = /const MUTATIONS\s*=\s*\[([\s\S]*?)\]/.exec(selfSrc)
  const runnerSees = []
  for (const line of (block ? block[1] : '').split('\n')) {
    const code = line.split('//')[0].trim()
    for (const q of code.match(/['"]([^'"]+)['"]/g) || []) runnerSees.push(q.slice(1, -1))
  }
  if (runnerSees.length !== MUTATIONS.length || runnerSees.some((n, i) => n !== MUTATIONS[i])) {
    console.error(`FATAL gate.py would discover ${runnerSees.length} of ${MUTATIONS.length} declared `
      + `mutations. A ']' inside a comment in the MUTATIONS block truncates the runner's list while `
      + `it still reports green. Last one the runner sees: ${runnerSees[runnerSees.length - 1]}`)
    process.exit(2)
  }
}
// A VACUOUS-ARM GENERATOR, CLOSED. A name in MUTATIONS with no entry in PATCHES used to load the
// CLEAN module, run every assertion green, and then report FAIL anyway because `report()` forces it
// whenever a mutation is named — which gate.py scores as ARMED. One typo in a mutation name was
// enough to manufacture a gate that had never been seen to fail for the right reason. It is now a
// hard error instead.
if (mutation && !(PATCHES[mutation] && PATCHES[mutation].core)) {
  console.error(`FATAL mutation ${mutation} is listed in MUTATIONS but has no PATCHES entry: it would `
    + `load the unpatched module, pass everything, and still be scored ARMED`)
  process.exit(2)
}
// Every listed mutation must be patchable at all: an anchor that stopped matching after a refactor
// would otherwise only be discovered the next time that one mutation happened to be run.
if (!mutation) {
  const unpatchable = MUTATIONS.filter(m => !(PATCHES[m] && PATCHES[m].core))
  if (unpatchable.length) { console.error(`FATAL mutations with no patch: ${unpatchable.join(', ')}`); process.exit(2) }
}

const CORE = path.resolve(__dirname, '../../src/core/water-sources.js')
const HYDRO = path.resolve(__dirname, '../../src/core/hydrology.js')
const CONFLICT = path.resolve(__dirname, '../../src/core/water-conflict.js')
const PORTS = path.resolve(__dirname, '../../src/core/ports.js')
const PLUGIN = path.resolve(__dirname, '../../src/plugins/data/water_source.js')

function patch(text, pairs, label) {
  for (const [anchor, repl] of pairs) {
    const hits = text.split(anchor).length - 1
    if (hits !== 1) { console.error(`FATAL ${label} anchor for ${mutation} matched ${hits}, expected 1: ${anchor.slice(0, 80)}`); process.exit(2) }
    text = text.replace(anchor, repl)
  }
  return text
}

// --- the fixture ---------------------------------------------------------------------------------
// 96 x 64 on purpose: a NON-SQUARE domain, so swapping the world axes when indexing produces a
// different cell rather than a transposed one that happens to still be in range everywhere.
const W = 96, H = 64, N = W * H, CELL = 10        // 10 m cells, 960 m x 640 m
const AXIS = 32                                    // the valley floor row
const FALL = 0.5, VEE = 0.25                       // downstream drop and cross-valley rise
const HEX_ROW = Math.sqrt(3) / 2
const U32 = Math.pow(2, -24)
const gamma = n => (n * U32) / (1 - n * U32)

/** A valley falling in +x with a V cross-section on row 32. On the axis the cross-slope beats the
 *  downstream slope, so an axis cell has exactly one receiver and the river is one cell wide. */
function desert() {
  const h = new Float32Array(N)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    h[y * W + x] = FALL * (1 - x / (W - 1)) + VEE * Math.abs(y - AXIS) / (H / 2)
  }
  return h
}

// Independent world<->cell formulas. The module has its own; the point of writing them twice is that
// the placement assertions go red if the two ever disagree.
const colOf = (xM, row, hex) => Math.round(xM / CELL - (hex && (row & 1) ? 0.5 : 0))
const rowOf = (zM, hex) => Math.round(zM / (CELL * (hex ? HEX_ROW : 1)))
const centreX = (col, row, hex) => col * CELL + (hex && (row & 1) ? 0.5 * CELL : 0)
const centreZ = (row, hex) => row * CELL * (hex ? HEX_ROW : 1)

const SPRING_X = 200, SPRING_Z = 320, SPRING_Q = 1200      // cell (20, 32)
const SPRING_CELL = rowOf(SPRING_Z, false) * W + colOf(SPRING_X, rowOf(SPRING_Z, false), false)
const OUTLET_CELL = AXIS * W + (W - 1)

;(async () => {
  let M = null, HYD = null, CFL = null, Ports = null, loadErr = null, pluginSrc = null
  try {
    const p = mutation ? (PATCHES[mutation] || {}) : {}
    if (!p.core) {
      M = await import(pathToFileURL(CORE).href)
    } else {
      // water-sources.js imports nothing, so the patched copy loads from a data: URL with no
      // specifier rewriting at all.
      const text = patch(fs.readFileSync(CORE, 'utf8'), p.core, 'core')
      M = await import('data:text/javascript;base64,' + Buffer.from(text, 'utf8').toString('base64'))
    }
    // NEVER PATCHED. The story's claim is that a source seeds the SAME accumulation stack as area, so
    // the accumulation used here has to be the shipping one.
    HYD = await import(pathToFileURL(HYDRO).href)
    CFL = await import(pathToFileURL(CONFLICT).href)
    Ports = await import(pathToFileURL(PORTS).href)
    pluginSrc = fs.readFileSync(PLUGIN, 'utf8')
    if (p.plugin) pluginSrc = patch(pluginSrc, p.plugin, 'plugin')
  } catch (e) { loadErr = String((e && e.message) || e).slice(0, 300) }

  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }
  const attempt = fn => { try { return { ok: true, value: fn() } } catch (e) { return { ok: false, code: e && e.code, message: String((e && e.message) || e).slice(0, 200) } } }
  const measured = {}

  if (!check('module loads', M !== null && HYD !== null && Ports !== null, loadErr)) return report()

  try { await body() } catch (e) {
    check('the oracle ran to completion', false, String((e && e.stack) || e).slice(0, 400))
  }
  return report()

  async function body() {
    // === the corpus enum ==========================================================================
    check('the source kinds are the corpus enum in corpus order',
      Array.isArray(M.SOURCE_KINDS) && M.SOURCE_KINDS.join(',')
        === 'distributedRain,boundaryInflow,spring,karstResurgence,oasis,glacialSnowmelt',
      { kinds: M.SOURCE_KINDS && [...M.SOURCE_KINDS] })
    check('every source kind carries a label',
      M.SOURCE_KINDS.every(k => typeof M.SOURCE_KIND_LABEL[k] === 'string' && M.SOURCE_KIND_LABEL[k].length > 2),
      M.SOURCE_KIND_LABEL)

    // === the fixture routes =======================================================================
    const surface = desert()
    const before = Float32Array.from(surface)
    const weights = HYD.mfdWeights(surface, W, H, { cellSizeM: CELL })
    const area = HYD.cellAreaM2(CELL, false)
    let routed = 0, outletCount = 0, outletIndex = -1
    for (let i = 0; i < N; i++) {
      let nz = 0
      for (let k = 0; k < weights.nbCount; k++) if (weights.wgt[i * weights.nbCount + k] > 0) nz++
      if (nz > 0) routed++
      if (weights.outlet[i]) { outletCount++; outletIndex = i }
    }
    // Absence of evidence is a failure: a fixture that routed nothing would satisfy every
    // conservation assertion below trivially, because zero is conserved perfectly.
    check('the desert fixture routes almost every cell', routed === N - 1, { routed, N })
    check('the desert fixture has exactly one outlet and it is the valley mouth',
      outletCount === 1 && outletIndex === OUTLET_CELL, { outletCount, outletIndex, expected: OUTLET_CELL })
    // The single-receiver valley axis is what makes the river's route known in closed form. If the
    // fixture ever stopped having it, every "only these cells carry water" assertion below would be
    // measuring a different claim than the one documented at the top of this file.
    let axisSingle = 0
    for (let x = 1; x < W - 1; x++) {
      const i = AXIS * W + x
      let nz = 0
      for (let k = 0; k < weights.nbCount; k++) if (weights.wgt[i * weights.nbCount + k] > 0) nz++
      if (nz === 1) axisSingle++
    }
    check('the valley axis is a single-receiver thread', axisSingle === W - 2, { axisSingle, expected: W - 2 })

    // === placement ================================================================================
    const spring = { id: 'nileSpring', kind: 'spring', xM: SPRING_X, zM: SPRING_Z, dischargeM3PerS: SPRING_Q, temperatureC: 24 }
    const seeded = M.sourceSupply(surface, W, H, { sources: [spring] }, { cellSizeM: CELL })
    const place = seeded.placements.find(p => p.id === 'nileSpring')
    check('the source lands in the cell the oracle computes independently',
      !!place && place.col === 20 && place.row === 32 && place.index === SPRING_CELL,
      { got: place && { col: place.col, row: place.row, index: place.index }, expected: { col: 20, row: 32, index: SPRING_CELL } })
    check('the source reports the surface elevation it sits at',
      !!place && place.surfaceValue === surface[SPRING_CELL], { got: place && place.surfaceValue, expected: surface[SPRING_CELL] })

    // The supply term itself: one cell, the authored number, nothing anywhere else. Exact, because
    // a point source is a single store of a single authored double.
    let nzSupply = 0, supplySum = 0
    for (let i = 0; i < N; i++) if (seeded.supply[i] !== 0) { nzSupply++; supplySum += seeded.supply[i] }
    check('the source supply is the authored discharge in exactly one cell',
      nzSupply === 1 && seeded.supply[SPRING_CELL] === SPRING_Q && supplySum === SPRING_Q,
      { nzSupply, atSource: seeded.supply[SPRING_CELL], supplySum, authored: SPRING_Q })

    check('a source outside the domain is refused',
      (() => { const r = attempt(() => M.sourceSupply(surface, W, H, { sources: [{ ...spring, id: 'offMap', xM: 5000, zM: 5000 }] }, { cellSizeM: CELL })); return !r.ok && r.code === 'SOURCE_OFF_DOMAIN' })(),
      attempt(() => M.sourceSupply(surface, W, H, { sources: [{ ...spring, id: 'offMap', xM: 5000, zM: 5000 }] }, { cellSizeM: CELL })))

    // `03:691` — a boundary inflow is a river entering off-map. Injecting one in the middle of the
    // map is not a boundary inflow, it is a spring with the wrong label, and every downstream reader
    // of `kind` would be told something untrue.
    const inland = attempt(() => M.sourceSupply(surface, W, H,
      { sources: [{ id: 'nile', kind: 'boundaryInflow', xM: 400, zM: 320, dischargeM3PerS: 100 }] }, { cellSizeM: CELL }))
    check('a boundary inflow away from the domain edge is refused',
      !inland.ok && inland.code === 'BOUNDARY_NOT_ON_EDGE', inland)
    const onEdge = attempt(() => M.sourceSupply(surface, W, H,
      { sources: [{ id: 'nile', kind: 'boundaryInflow', xM: 0, zM: 320, dischargeM3PerS: 100 }] }, { cellSizeM: CELL }))
    check('a boundary inflow on the domain edge seeds the edge cell',
      onEdge.ok && onEdge.value.supply[AXIS * W] === 100, { ok: onEdge.ok, at: onEdge.ok ? onEdge.value.supply[AXIS * W] : null, code: onEdge.code })

    // Hex: odd rows are shifted half a column. One offset for both rows shears every odd row.
    const hexRow = 33, hexCol = 20
    const hexX = centreX(hexCol, hexRow, true), hexZ = centreZ(hexRow, true)
    const hexSeed = attempt(() => M.sourceSupply(surface, W, H,
      { sources: [{ ...spring, xM: hexX, zM: hexZ }] }, { cellSizeM: CELL, hex: true }))
    check('a source on the hex lattice lands in the staggered cell the oracle computes',
      hexSeed.ok && hexSeed.value.placements[0].col === hexCol && hexSeed.value.placements[0].row === hexRow,
      { got: hexSeed.ok && { col: hexSeed.value.placements[0].col, row: hexSeed.value.placements[0].row }, expected: { col: hexCol, row: hexRow }, hexX, hexZ: +hexZ.toFixed(3) })

    // === A BIG RIVER CROSSES A DESERT =============================================================
    const dry = new Float64Array(N)                       // zero rainfall. A desert.
    const qDesert = HYD.mfdAccumulate(surface, M.combineSupply(dry, seeded.supply), W, H, weights)
    // The plan's bound, verbatim: gamma_(N-1) * sum(abs(sourceQ)).
    const bound = gamma(N - 1) * SPRING_Q
    measured.bound = bound

    // "Discharge immediately downstream equals the authored source flow." On the single-receiver
    // axis, the cell immediately downstream is one named cell, so this is a scalar comparison rather
    // than a sum over a fan.
    const qDown = qDesert[SPRING_CELL + 1]
    measured.qDownstream = qDown
    measured.downRelErr = Math.abs(qDown - SPRING_Q) / SPRING_Q
    check('discharge immediately downstream equals the authored source flow',
      Math.abs(qDown - SPRING_Q) <= bound, { qDown, authored: SPRING_Q, diff: qDown - SPRING_Q, bound })
    // MEASURED, and stronger than the bound above: the first hop loses nothing at all. A cell with a
    // single receiver normalizes that receiver's weight as ww/ww, which rounds to exactly 1.0f, so
    // the authored 1200 m3/s arrives in the next cell as the same double it was authored as. This is
    // the story's sentence — "discharge immediately downstream equals the authored source flow" — in
    // its exact form rather than its tolerant one.
    check('the first hop carries the authored flow exactly', qDown === SPRING_Q,
      { qDown, authored: SPRING_Q, ulps: (qDown - SPRING_Q) / Number.EPSILON })

    const qOut = qDesert[OUTLET_CELL]
    measured.qOutlet = qOut
    measured.outRelErr = Math.abs(qOut - SPRING_Q) / SPRING_Q
    check('the authored discharge is conserved to the outlet absent sinks',
      Math.abs(qOut - SPRING_Q) <= bound, { qOut, authored: SPRING_Q, diff: qOut - SPRING_Q, bound })
    // A SECOND, TIGHTER BOUND BETWEEN TWO MEASURED ENDPOINTS. gamma_(N-1) is the plan's conservative
    // Float32 reduction bound and works out at 3.663e-4 relative — loose enough that a build losing
    // three parts in ten thousand of the Nile would still pass it. Both endpoints were measured on
    // this fixture: the correct build carries 1199.998927 m3/s to the outlet, a relative error of
    // 8.941e-7 accumulated over 75 hops of Float32 weight normalization, and the nearest wrong build
    // in the mutation list — authored m3/s treated as a per-area rate — carries 119999.89, a relative
    // error of 9.900e+1. 1e-5 sits eleven times above the passing reading and seven decades below
    // the failing one.
    check('the conserved discharge is not merely inside the conservative bound',
      measured.outRelErr <= 1e-5, { relErr: measured.outRelErr, tight: 1e-5, planBound: bound / SPRING_Q })

    // The river is exactly the cells downstream of the spring, and nothing else is wet. This is what
    // a "flow cone" means, asserted as a cell count rather than as a picture.
    let wet = 0, wetOffAxis = 0, wetUpstream = 0
    for (let i = 0; i < N; i++) {
      if (qDesert[i] === 0) continue
      wet++
      const row = (i / W) | 0, col = i - row * W
      if (row !== AXIS) wetOffAxis++
      else if (col < 20) wetUpstream++
    }
    check('the desert river wets exactly the axis cells downstream of the spring',
      wet === W - 20 && wetOffAxis === 0 && wetUpstream === 0,
      { wet, expected: W - 20, wetOffAxis, wetUpstream })

    // "Removing the source returns exactly zero." Not "small", not "below a threshold": every one of
    // the 6144 samples is the zero double.
    const empty = M.sourceSupply(surface, W, H, { sources: [] }, { cellSizeM: CELL })
    const qEmpty = HYD.mfdAccumulate(surface, M.combineSupply(dry, empty.supply), W, H, weights)
    let nonZero = 0, worst = 0
    for (let i = 0; i < N; i++) if (qEmpty[i] !== 0) { nonZero++; worst = Math.max(worst, Math.abs(qEmpty[i])) }
    check('removing the source returns exactly zero everywhere', nonZero === 0, { nonZero, worst })
    check('the empty desert seeded nothing at all',
      empty.seededCount === 0 && empty.totalQM3PerS === 0, { seededCount: empty.seededCount, totalQ: empty.totalQM3PerS })

    // === no height was written ====================================================================
    // Guardrail 1, and `03:702-707`: a spring is a source term in the flow field, not a bump in the
    // height field. Compared bitwise across a full seed AND route, not within a tolerance.
    let surfaceChanged = 0
    for (let i = 0; i < N; i++) if (surface[i] !== before[i]) surfaceChanged++
    check('the routing surface is bit-identical after seeding and routing', surfaceChanged === 0, { surfaceChanged })

    // === Q proportional to A under rain; divergent with a source ==================================
    const areaAcc = HYD.mfdAccumulate(surface, new Float64Array(N).fill(area), W, H, weights)
    let minArea = Infinity
    for (let i = 0; i < N; i++) minArea = Math.min(minArea, areaAcc[i])
    check('every cell has a positive drainage area', minArea >= area * 0.999, { minArea, area })

    const PRECIP = 1000
    const rain = HYD.precipToSupply(PRECIP, area, N)
    const qRain = HYD.mfdAccumulate(surface, M.combineSupply(rain, empty.supply), W, H, weights)
    const c = PRECIP * 1e-3 / HYD.SECONDS_PER_YEAR
    let worstProp = 0
    for (let i = 0; i < N; i++) worstProp = Math.max(worstProp, Math.abs(qRain[i] - c * areaAcc[i]) / (c * areaAcc[i]))
    measured.worstProp = worstProp
    // The story: "Under uniform rain Q is proportional to A and nothing changes."
    check('under uniform rain and no sources Q is proportional to A',
      worstProp <= gamma(8), { worstProp, bound: gamma(8), constant: c })

    const qBoth = HYD.mfdAccumulate(surface, M.combineSupply(rain, seeded.supply), W, H, weights)
    let divergeOn = 0, worstOff = 0
    for (let i = 0; i < N; i++) {
      const rel = Math.abs(qBoth[i] - c * areaAcc[i]) / (c * areaAcc[i])
      const row = (i / W) | 0, col = i - row * W
      if (row === AXIS && col >= 20) divergeOn = Math.max(divergeOn, rel)
      else worstOff = Math.max(worstOff, rel)
    }
    measured.divergeOn = divergeOn
    // Two MEASURED endpoints, not a chosen threshold: off the river Q/A is the rain constant to
    // within gamma_8 (1e-6 relative), on the river it is 1.6e4 times it. The claim is that a source
    // makes Q and A diverge, and both halves of it are read off the same field.
    check('with a source Q and A diverge on the river and nowhere else',
      divergeOn > 100 && worstOff <= gamma(8), { divergeOn, worstOff, bound: gamma(8) })

    // === move: id and properties survive; only the flow cones change ==============================
    const moved = M.moveSource(spring, 500, 200)
    check('moving a source keeps its id kind discharge and temperature',
      moved.id === spring.id && moved.kind === spring.kind
      && moved.dischargeM3PerS === SPRING_Q && moved.temperatureC === 24
      && moved.xM === 500 && moved.zM === 200,
      { moved })
    const seededB = M.sourceSupply(surface, W, H, { sources: [moved] }, { cellSizeM: CELL })
    const qMoved = HYD.mfdAccumulate(surface, M.combineSupply(dry, seededB.supply), W, H, weights)
    const coneA = coneFrom(SPRING_CELL, weights)
    const coneB = coneFrom(seededB.placements[0].index, weights)
    let changed = 0, changedOutsideCones = 0
    for (let i = 0; i < N; i++) {
      if (qDesert[i] === qMoved[i]) continue
      changed++
      if (!coneA[i] && !coneB[i]) changedOutsideCones++
    }
    check('moving the source changed the discharge field at all', changed > 0, { changed })
    check('moving the source changes only the two downstream flow cones',
      changedOutsideCones === 0, { changed, changedOutsideCones })

    // === serialization, reload, copy/paste ========================================================
    const guideChannel = { id: 'nileCourse', intent: 'channel', targetFlowM3PerS: 300, points: [[200, 320], [500, 320], [900, 320]] }
    const guideRef = { id: 'oldCourse', intent: 'reference', points: [[100, 100], [400, 140]] }
    // Every world position in this file is chosen to stay inside the 96x64 domain when the x and z
    // axes are SWAPPED. That is not cosmetic: the `source-cell-swaps-axes` mutation must be caught by
    // the placement assertions, and a fixture that instead threw SOURCE_OFF_DOMAIN would abort the
    // run at the first swapped source and leave every later gate unevaluated.
    const doc = { sources: [spring, { id: 'karstEye', kind: 'karstResurgence', xM: 500, zM: 320, dischargeM3PerS: 45 }], guides: [guideChannel, guideRef] }
    const text = M.serializeWaterFeatures(doc)
    const shuffled = M.serializeWaterFeatures({ sources: [doc.sources[1], doc.sources[0]], guides: [guideRef, guideChannel] })
    check('serialization is deterministic under input reordering', text === shuffled,
      { equal: text === shuffled, lenA: text.length, lenB: shuffled.length })
    // Wrapped: a canonical document that stamps the wrong `kind` makes the re-read THROW rather than
    // differ, and an uncaught throw here would abort the run and leave everything below unevaluated.
    const roundTrip = attempt(() => M.serializeWaterFeatures(M.parseWaterFeatures(text)))
    check('serialization round-trips through parse',
      roundTrip.ok && roundTrip.value === text,
      { ok: roundTrip.ok, code: roundTrip.code, message: roundTrip.message, bytes: text.length })
    // The stamp itself, so a document that round-trips within this build but is unreadable by any
    // other reader of the format is caught here rather than by whoever opens it next.
    check('the canonical document is stamped with this format\'s own kind',
      M.canonicalWaterFeatures(doc).kind === M.WATER_FEATURE_DOC_KIND
      && M.WATER_FEATURE_DOC_KIND === 'terrain-studio-water-features',
      { stamped: M.canonicalWaterFeatures(doc).kind, constant: M.WATER_FEATURE_DOC_KIND })
    check('the serialized document carries both features and a schema version',
      /"schemaVersion": 1/.test(text) && /"nileSpring"/.test(text) && /"nileCourse"/.test(text)
      && /"temperatureC": 24/.test(text), { bytes: text.length })
    // SALINITY IS OUT OF SCOPE. Asserted on the SURFACE — the serialized document and the module's
    // exported names — because "we did not implement it" and "we implemented it badly" are
    // indistinguishable on a record until someone looks. The file's prose says why it is absent; the
    // schema and the API are what must not carry it.
    check('salinity is absent from the schema and the exported surface',
      !/salin/i.test(text) && !Object.keys(M).some(k => /salin/i.test(k))
      && !/salin/i.test(JSON.stringify(M.waterFeatureRecords(doc))),
      { exports: Object.keys(M).filter(k => /salin/i.test(k)) })

    // Wrapped: a document stamped with the wrong kind cannot be re-read at all, and an uncaught throw
    // here would abort before the assertions below it ever ran.
    const reloadAttempt = attempt(() => M.parseWaterFeatures(text))
    check('the saved document can be read back', reloadAttempt.ok, reloadAttempt)
    const reloaded = reloadAttempt.ok ? reloadAttempt.value : { sources: [], guides: [] }
    const seededReload = M.sourceSupply(surface, W, H, reloaded, { cellSizeM: CELL })
    const qReload = HYD.mfdAccumulate(surface, M.combineSupply(dry, seededReload.supply), W, H, weights)
    const seededDoc = M.sourceSupply(surface, W, H, doc, { cellSizeM: CELL })
    const qDoc = HYD.mfdAccumulate(surface, M.combineSupply(dry, seededDoc.supply), W, H, weights)
    let reloadDiff = 0, reloadWet = 0
    for (let i = 0; i < N; i++) { if (qReload[i] !== qDoc[i]) reloadDiff++; if (qReload[i] !== 0) reloadWet++ }
    // Absence of evidence: two all-zero fields are bit-identical too. The reload must have produced a
    // river before "identical" means anything.
    check('save and reload reproduce the discharge field bit-identically',
      reloadDiff === 0 && reloadWet > 0, { reloadDiff, reloadWet })
    const rs = reloaded.sources.find(s => s.id === 'nileSpring')
    check('a reloaded source keeps its id kind discharge and temperature',
      !!rs && rs.kind === 'spring' && rs.dischargeM3PerS === SPRING_Q && rs.temperatureC === 24
      && rs.xM === SPRING_X && rs.zM === SPRING_Z, { rs })

    const copy = M.duplicateFeature(spring, M.featureIds(doc))
    check('a pasted copy gets a fresh id and identical properties',
      copy.id !== spring.id && copy.kind === spring.kind && copy.dischargeM3PerS === SPRING_Q
      && copy.xM === SPRING_X && copy.temperatureC === 24, { copy })
    const pasteOk = attempt(() => M.normalizeWaterFeatures({ sources: [spring, copy], guides: [] }))
    check('a document containing the original and its paste is legal', pasteOk.ok, pasteOk)

    // A versionless blob is the pre-S4.3 shape and migrates; a future one is refused rather than
    // partially read, because a river network missing pieces looks exactly like a river network.
    const v0 = attempt(() => M.migrateWaterFeatures({ sources: [spring], guides: [] }))
    check('a versionless document migrates to the current schema',
      v0.ok && v0.value.schemaVersion === M.WATER_FEATURE_SCHEMA_VERSION && v0.value.sources.length === 1, v0)
    const vNext = attempt(() => M.migrateWaterFeatures({ schemaVersion: M.WATER_FEATURE_SCHEMA_VERSION + 1, sources: [] }))
    check('a future schema version is refused', !vNext.ok && vNext.code === 'SCHEMA_VERSION', vNext)

    // === identity and validation refusals =========================================================
    const noId = attempt(() => M.normalizeSource({ kind: 'spring', xM: 10, zM: 10, dischargeM3PerS: 1 }))
    check('a source with no authored id is refused', !noId.ok && noId.code === 'ID_INVALID', noId)
    const dup = attempt(() => M.normalizeWaterFeatures({ sources: [spring, { ...spring, xM: 300 }], guides: [] }))
    check('a duplicate id is refused', !dup.ok && dup.code === 'ID_DUPLICATE', dup)
    const dupCross = attempt(() => M.normalizeWaterFeatures({ sources: [spring], guides: [{ ...guideChannel, id: 'nileSpring' }] }))
    check('a guide sharing a source id is refused', !dupCross.ok && dupCross.code === 'ID_DUPLICATE', dupCross)
    const badKind = attempt(() => M.normalizeSource({ ...spring, kind: 'waterfall' }))
    check('an unknown source kind is refused', !badKind.ok && badKind.code === 'KIND_UNKNOWN', badKind)
    const negative = attempt(() => M.normalizeSource({ ...spring, dischargeM3PerS: -50 }))
    check('a negative discharge is refused', !negative.ok && negative.code === 'DISCHARGE_INVALID', negative)
    const pointRain = attempt(() => M.normalizeSource({ ...spring, kind: 'distributedRain' }))
    check('distributed rain without a footprint is refused', !pointRain.ok && pointRain.code === 'RADIUS_INVALID', pointRain)

    const off = M.sourceSupply(surface, W, H, { sources: [{ ...spring, enabled: false }] }, { cellSizeM: CELL })
    let offSum = 0
    for (let i = 0; i < N; i++) offSum += off.supply[i]
    check('a disabled source contributes exactly zero',
      offSum === 0 && off.seededCount === 0 && off.placements[0].enabled === false,
      { offSum, seededCount: off.seededCount })

    // === a distributed footprint conserves its total ==============================================
    const RAD = 25, fx = centreX(48, 32, false), fz = centreZ(32, false)
    // Wrapped: an alias-resolution defect makes the authored radius resolve to 0, which a
    // distributedRain source refuses outright — a throw, not a wrong number — and it would otherwise
    // abort the run here and take every later assertion with it.
    const rain2A = attempt(() => M.sourceSupply(surface, W, H,
      { sources: [{ id: 'monsoonCell', kind: 'distributedRain', xM: fx, zM: fz, dischargeM3PerS: 210, radiusM: RAD }] },
      { cellSizeM: CELL }))
    check('the distributed footprint fixture seeded at all',
      rain2A.ok && rain2A.value.seededCount === 1,
      { ok: rain2A.ok, code: rain2A.code, message: rain2A.message })
    const rain2 = rain2A.ok ? rain2A.value : { supply: new Float64Array(N), placements: [{ cells: [], qM3PerS: 0, qPerCellM3PerS: 0 }] }
    // Independent expected footprint: every cell whose centre is within the radius, found by scanning
    // the whole domain rather than by asking the module which cells it used.
    const expectCells = []
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      if (Math.hypot(centreX(x, y, false) - fx, centreZ(y, false) - fz) <= RAD) expectCells.push(y * W + x)
    }
    let footSum = 0, footCells = 0, footUneven = 0
    const each = 210 / expectCells.length
    for (let i = 0; i < N; i++) if (rain2.supply[i] !== 0) { footCells++; footSum += rain2.supply[i]; if (Math.abs(rain2.supply[i] - each) > 1e-12) footUneven++ }
    check('a distributed source covers the footprint the oracle computes independently',
      footCells === expectCells.length && expectCells.length === 21 && footUneven === 0,
      { footCells, expected: expectCells.length, footUneven })
    check('a distributed source conserves its authored total',
      Math.abs(footSum - 210) <= gamma(expectCells.length) * 210, { footSum, authored: 210, bound: gamma(expectCells.length) * 210 })

    // === guides ===================================================================================
    const gset = M.normalizeWaterFeatures({ sources: [], guides: [guideChannel, guideRef] })
    check('a guide keeps its ordered control points and measures its own length',
      gset.guides.length === 2 && gset.guides[0].id === 'nileCourse'
      && gset.guides[0].points.length === 3 && Math.abs(gset.guides[0].lengthM - 700) < 1e-9,
      { guides: gset.guides.map(g => ({ id: g.id, pts: g.points.length, lengthM: g.lengthM })) })
    const shortGuide = attempt(() => M.normalizeGuide({ id: 'stub', intent: 'channel', points: [[1, 2]] }))
    check('a one-point guide is refused', !shortGuide.ok && shortGuide.code === 'POINTS_INVALID', shortGuide)
    const badIntent = attempt(() => M.normalizeGuide({ ...guideChannel, intent: 'suggestion' }))
    check('an unknown guide intent is refused', !badIntent.ok && badIntent.code === 'INTENT_UNKNOWN', badIntent)

    // Target flow is OPT-IN.
    const noSeed = M.sourceSupply(surface, W, H, { sources: [], guides: [guideChannel] }, { cellSizeM: CELL })
    let noSeedSum = 0
    for (let i = 0; i < N; i++) noSeedSum += noSeed.supply[i]
    check('a guide target flow is not seeded unless asked', noSeedSum === 0 && noSeed.guideSeededCount === 0,
      { noSeedSum, guideSeeded: noSeed.guideSeededCount })

    const headSeed = M.sourceSupply(surface, W, H, { sources: [], guides: [guideChannel] }, { cellSizeM: CELL, includeGuideTargets: true })
    const headCell = rowOf(320, false) * W + colOf(200, rowOf(320, false), false)
    let headNz = 0
    for (let i = 0; i < N; i++) if (headSeed.supply[i] !== 0) headNz++
    check('a channel guide seeds its head cell with the target flow',
      headNz === 1 && headSeed.supply[headCell] === 300 && headSeed.guideSeededCount === 1,
      { headNz, atHead: headSeed.supply[headCell], headCell, guideSeeded: headSeed.guideSeededCount })

    const refSeed = M.sourceSupply(surface, W, H, { sources: [], guides: [{ ...guideRef, targetFlowM3PerS: 500 }] }, { cellSizeM: CELL, includeGuideTargets: true })
    let refSum = 0
    for (let i = 0; i < N; i++) refSum += refSeed.supply[i]
    check('a reference guide never seeds flow', refSum === 0 && refSeed.guideSeededCount === 0,
      { refSum, guideSeeded: refSeed.guideSeededCount })

    // The emitted guide record must be the shape S4.6's conflict analyser already consumes; a guide
    // that needs a translation layer to reach it is a guide that will one day stop reaching it.
    const records = M.waterFeatureRecords(doc)
    const guideRec = records.guides.find(g => g.id === 'nileCourse')
    check('the emitted guide record has the shape water_conflict.js reads',
      !!guideRec && Array.isArray(guideRec.points) && guideRec.points.length === 3
      && Number.isFinite(guideRec.points[0].x) && Number.isFinite(guideRec.points[0].z), { guideRec })
    check('a source record is not mistaken for a guide',
      records.sources.every(s => !Array.isArray(s.points)) && records.sources.length === 2,
      { sources: records.sources.map(s => s.id) })
    const analysed = attempt(() => CFL.analyzeGuideConflict(surface, W, H, guideRec.points,
      { cellSizeM: CELL, heightScaleM: 1000, resolution: W, flow: { dirX: weights.dirX, dirZ: weights.dirZ } }))
    check('the S4.6 conflict analyser consumes the emitted guide',
      analysed.ok && analysed.value.count > 1 && analysed.value.flowSupplied === true,
      { ok: analysed.ok, count: analysed.ok ? analysed.value.count : null, code: analysed.code, message: analysed.message })
    // The guide runs straight down the valley axis, which drains: an authored route that agrees with
    // the terrain must report NO conflict, or the analyser is calling everything a problem.
    check('a guide drawn down the valley reports no elevation deficit',
      analysed.ok && analysed.value.conflictCount === 0,
      { conflictCount: analysed.ok ? analysed.value.conflictCount : null, maxDeficitM: analysed.ok ? analysed.value.maxDeficitM : null })

    // === THE RECORDS AND SUMMARIES THAT LEAVE THE NODE ============================================
    // Everything in this section was found by injecting defects into water-sources.js one at a time
    // and watching the 68 assertions above stay green. Fifteen did. They were all values that reach
    // an output port or a documented promise: the inspector label, the analyse flag S4.6 reads, the
    // per-cell split, the footprint cell list, the temperature, the radius, two of the eight
    // authoring-text keys, the paste suffix, guide paste, three of the four domain edges, the
    // reported total, the feature counts and the document-kind check. A field that is emitted and
    // unconstrained is a field that can be silently wrong for as long as nobody looks at it.

    // The label is what the inspector shows for a kind. `doc` carries TWO kinds on purpose: a
    // constant label satisfies any check that only ever looks at one record.
    check('every emitted source record carries the label of its own kind',
      records.sources.length === 2
      && records.sources.every(r => r.kindLabel === M.SOURCE_KIND_LABEL[r.kind])
      && new Set(records.sources.map(r => r.kindLabel)).size === 2,
      { labels: records.sources.map(r => [r.kind, r.kindLabel]) })
    // BOTH WAYS. `analyze` is the flag S4.6 acts on; asserting only that the channel guide is true
    // passes an implementation that analyses everything, and only that the reference guide is false
    // passes one that analyses nothing.
    check('the analyse flag follows the guide intent, both ways',
      records.guides.length === 2
      && records.guides.find(g => g.id === 'nileCourse').analyze === true
      && records.guides.find(g => g.id === 'oldCourse').analyze === false,
      { analyze: records.guides.map(g => [g.id, g.intent, g.analyze]) })

    // The module's prose promises "normalizeWaterFeatures accepts these records back unchanged", and
    // that promise is what lets a feature set be routed through a graph and re-read. Measured on a
    // document rich enough to carry every optional field — a temperature, a footprint radius, a
    // disabled source and a guide target flow — so a record that drops one shows up as a byte diff.
    const rich = {
      sources: [spring,
        { id: 'monsoonCell', kind: 'distributedRain', xM: 480, zM: 320, dischargeM3PerS: 210, radiusM: 25 },
        { id: 'winterSpring', kind: 'spring', xM: 300, zM: 200, dischargeM3PerS: 7, enabled: false }],
      guides: [guideChannel, guideRef],
    }
    // Wrapped: a record that drops a REQUIRED field (a distributedRain footprint) makes the re-read
    // throw rather than differ, and an uncaught throw here would abort the run and leave every
    // assertion below it unevaluated — absence of evidence dressed up as a single red.
    const richDoc = attempt(() => M.serializeWaterFeatures(rich))
    const richRecords = attempt(() => M.serializeWaterFeatures(M.waterFeatureRecords(rich)))
    check('the emitted records re-normalize to the identical document',
      richDoc.ok && richRecords.ok && richRecords.value === richDoc.value && richDoc.value.length > 800,
      { docOk: richDoc.ok, docCode: richDoc.code, ok: richRecords.ok, code: richRecords.code,
        message: richRecords.message,
        equal: richDoc.ok && richRecords.ok && richRecords.value === richDoc.value,
        bytes: richDoc.ok ? richDoc.value.length : null,
        recordBytes: richRecords.ok ? richRecords.value.length : null })

    // The placement is what the node hangs on its `sources` port: which cell, how the footprint was
    // split, what elevation. Both endpoints are measured — a point source puts the whole 1200 m3/s in
    // one cell, the 25 m footprint puts 210/21 = 10 in each of 21 — and the record must be internally
    // consistent, because a per-cell figure that does not multiply back to the authored discharge is
    // a number shown to the author that no cell ever received.
    const fp = rain2.placements[0]
    check('a placement reports the discharge and the per-cell split it actually injected',
      place.qM3PerS === SPRING_Q && place.qPerCellM3PerS === SPRING_Q && place.cells.length === 1
      && fp.qM3PerS === 210 && fp.qPerCellM3PerS === each && fp.cells.length === expectCells.length
      && Math.abs(fp.qPerCellM3PerS * fp.cells.length - 210) <= gamma(expectCells.length) * 210,
      { point: { q: place.qM3PerS, qpc: place.qPerCellM3PerS, cells: place.cells.length },
        footprint: { q: fp.qM3PerS, qpc: fp.qPerCellM3PerS, cells: fp.cells.length, expected: expectCells.length, each } })
    check('a placement lists exactly the footprint cells the oracle computes independently',
      fp.cells.length > 1 && [...fp.cells].join(',') === expectCells.join(','),
      { got: fp.cells.length, expected: expectCells.length })
    check('a disabled placement reports the zero it injected',
      off.placements[0].qM3PerS === 0 && off.placements[0].qPerCellM3PerS === 0
      && off.placements[0].cells.length === 0,
      { q: off.placements[0].qM3PerS, qpc: off.placements[0].qPerCellM3PerS, cells: off.placements[0].cells.length })

    // A quantity worth printing is worth asserting. The reported total is checked against the sum of
    // the array it summarizes, so the headline number and the field cannot drift apart.
    let docSupplySum = 0
    for (let i = 0; i < N; i++) docSupplySum += seededDoc.supply[i]
    check('the reported totals and counts are the ones actually seeded',
      seededDoc.totalQM3PerS === SPRING_Q + 45
      && Math.abs(docSupplySum - seededDoc.totalQM3PerS) <= gamma(N) * seededDoc.totalQM3PerS
      && seededDoc.sourceCount === 2 && seededDoc.guideCount === 2 && seededDoc.seededCount === 2
      && seeded.totalQM3PerS === SPRING_Q && seeded.sourceCount === 1 && seeded.guideCount === 0,
      { docTotal: seededDoc.totalQM3PerS, docSupplySum, sourceCount: seededDoc.sourceCount,
        guideCount: seededDoc.guideCount, springTotal: seeded.totalQM3PerS })
    const withTargets = M.sourceSupply(surface, W, H, doc, { cellSizeM: CELL, includeGuideTargets: true })
    check('a seeded guide target is counted in the total it added',
      withTargets.totalQM3PerS === SPRING_Q + 45 + 300 && withTargets.seededCount === 3
      && withTargets.guideSeededCount === 1,
      { total: withTargets.totalQM3PerS, seeded: withTargets.seededCount, guideSeeded: withTargets.guideSeededCount })

    // `r=` and `on=` are two of the eight authoring-text keys and the only route an author has to a
    // footprint or a disabled source before a placement tool exists. Asserted END TO END — text in,
    // supply array out — because a key that lands in the wrong field produces a perfectly valid
    // source somewhere else, which is exactly what nobody notices.
    // Wrapped for the same reason: a misrouted key throws (a distributedRain with no radius, or a
    // number parse of "false") instead of producing a wrong number, and a throw that escapes here
    // would take the rest of the file's assertions with it.
    const textFoot = attempt(() => M.sourceSupply(surface, W, H,
      M.parseFeatureText('source id=m kind=distributedRain x=480 z=320 q=210 r=25\n'), { cellSizeM: CELL }))
    let textFootCells = 0, textFootSum = 0
    if (textFoot.ok) for (let i = 0; i < N; i++) if (textFoot.value.supply[i] !== 0) { textFootCells++; textFootSum += textFoot.value.supply[i] }
    check('an r= footprint authored as text lands where the same source authored as an object does',
      textFoot.ok && textFootCells === expectCells.length
      && Math.abs(textFootSum - 210) <= gamma(expectCells.length) * 210
      && textFoot.value.placements[0].col === 48 && textFoot.value.placements[0].row === 32,
      { ok: textFoot.ok, code: textFoot.code, message: textFoot.message, textFootCells,
        expected: expectCells.length, textFootSum,
        col: textFoot.ok ? textFoot.value.placements[0].col : null,
        row: textFoot.ok ? textFoot.value.placements[0].row : null })
    const textOff = attempt(() => M.sourceSupply(surface, W, H,
      M.parseFeatureText('source id=w kind=spring x=300 z=200 q=7 on=false\n'), { cellSizeM: CELL }))
    const textOn = attempt(() => M.sourceSupply(surface, W, H,
      M.parseFeatureText('source id=w kind=spring x=300 z=200 q=7 on=true\n'), { cellSizeM: CELL }))
    let textOffSum = 0, textOnSum = 0
    if (textOff.ok) for (let i = 0; i < N; i++) textOffSum += textOff.value.supply[i]
    if (textOn.ok) for (let i = 0; i < N; i++) textOnSum += textOn.value.supply[i]
    check('on=false disables a text-authored source and on=true leaves it seeding',
      textOff.ok && textOn.ok && textOffSum === 0 && textOff.value.seededCount === 0
      && textOnSum === 7 && textOn.value.seededCount === 1,
      { offOk: textOff.ok, offCode: textOff.code, onOk: textOn.ok, onCode: textOn.code,
        offSum: textOffSum, onSum: textOnSum,
        offSeeded: textOff.ok ? textOff.value.seededCount : null,
        onSeeded: textOn.ok ? textOn.value.seededCount : null })

    // Two authors pasting the same feature into the same document must produce the same file. A
    // random or clock-derived suffix passes "the copy has a different id" while making every saved
    // document undiffable, so the SEQUENCE is asserted and the same call is made twice.
    check('a minted id is the documented sequence and is deterministic across calls',
      M.mintFeatureId('nileSpring', ['nileSpring']) === 'nileSpring-2'
      && M.mintFeatureId('nileSpring', ['nileSpring']) === 'nileSpring-2'
      && M.mintFeatureId('nileSpring', ['nileSpring', 'nileSpring-2']) === 'nileSpring-3',
      { once: M.mintFeatureId('nileSpring', ['nileSpring']),
        twice: M.mintFeatureId('nileSpring', ['nileSpring', 'nileSpring-2']) })

    // Copy/paste was proven for sources only. A guide travels the same duplicateFeature path down a
    // different branch, and that branch was reachable by no assertion at all.
    const gcopy = attempt(() => M.duplicateFeature(guideChannel, M.featureIds(doc)))
    check('a pasted guide gets a fresh id and keeps its intent points and target flow',
      gcopy.ok && gcopy.value.id !== guideChannel.id && gcopy.value.intent === 'channel'
      && gcopy.value.targetFlowM3PerS === 300 && gcopy.value.points.length === 3
      && gcopy.value.points[2].x === 900 && Math.abs(gcopy.value.lengthM - 700) < 1e-9, gcopy)
    const gPasteOk = attempt(() => M.normalizeWaterFeatures(
      { sources: [], guides: [guideChannel, gcopy.ok ? gcopy.value : guideChannel] }))
    check('a document containing a guide and its paste is legal', gPasteOk.ok, gPasteOk)

    // "A river entering off-map" is any of FOUR edges. Checking only the west edge — which is what
    // the single on-edge assertion above did — passes an implementation that refuses the other three,
    // and an author placing an inflow on the north edge would be told their map has no such place.
    const edges = [['west', 0, 320], ['east', 950, 320], ['north', 400, 0], ['south', 400, 630]]
      .map(([name, x, z]) => ({ name, r: attempt(() => M.sourceSupply(surface, W, H,
        { sources: [{ id: 'inflow', kind: 'boundaryInflow', xM: x, zM: z, dischargeM3PerS: 100 }] },
        { cellSizeM: CELL })) }))
    check('a boundary inflow is accepted on every domain edge, not just one',
      edges.length === 4 && edges.every(e => e.r.ok && e.r.value.seededCount === 1
        && e.r.value.totalQM3PerS === 100),
      { refused: edges.filter(e => !e.r.ok).map(e => [e.name, e.r.code]) })

    // A project file and a water feature file are both JSON objects with arrays in them. Reading one
    // as the other yields an empty feature set, which is indistinguishable from a document that
    // genuinely has no sources — the author sees no river and no reason.
    const foreign = attempt(() => M.parseWaterFeatures(JSON.stringify({ kind: 'terrain-studio-project', nodes: [] })))
    check('a foreign document is refused rather than read as an empty feature set',
      !foreign.ok && foreign.code === 'DOC_KIND', foreign)
    const ownDoc = attempt(() => M.migrateWaterFeatures(
      { kind: M.WATER_FEATURE_DOC_KIND, schemaVersion: 1, sources: [spring] }))
    check('a document carrying this build\'s own kind is accepted',
      ownDoc.ok && ownDoc.value.sources.length === 1, ownDoc)

    // === SECOND ADVERSARIAL ROUND =================================================================
    // The section above closed fifteen holes; a second sweep of fresh defects found twelve more that
    // it still did not reach. Same rule as before — every assertion here corresponds to a defect that
    // was injected, ran green, and is now a mutation.

    // The only guide whose length is asserted above runs due east, so a length that ignores z is
    // exactly right for it. `oldCourse` runs diagonally on purpose: hypot(300, 40) is not 300.
    const refGuide = gset.guides.find(g => g.id === 'oldCourse')
    const refLen = Math.hypot(400 - 100, 140 - 100)
    check('a guide length measures both axes, not just x',
      !!refGuide && Math.abs(refGuide.lengthM - refLen) < 1e-9 && Math.abs(refLen - 300) > 1,
      { got: refGuide && refGuide.lengthM, expected: refLen, xOnly: 300 })
    const refRec = M.waterFeatureRecords({ guides: [guideChannel, guideRef] }).guides
    check('the emitted guide records carry the lengths the normalized guides measured',
      refRec.length === 2
      && Math.abs(refRec.find(g => g.id === 'oldCourse').lengthM - refLen) < 1e-9
      && Math.abs(refRec.find(g => g.id === 'nileCourse').lengthM - 700) < 1e-9,
      { lengths: refRec.map(g => [g.id, g.lengthM]) })

    // The lattice geometry `footprintCells` measures distance from, pinned directly. On a pointy-odd-r
    // hex lattice an odd row is staggered half a column and every row sits sqrt(3)/2 of a column
    // apart; both constants live in `cellCentre` and neither was reachable by any assertion.
    check('cellCentre staggers odd hex rows and uses the sqrt(3)/2 row pitch',
      M.cellCentre(1, 1, { cellSizeM: 10, hex: true }).x === 15
      && Math.abs(M.cellCentre(1, 1, { cellSizeM: 10, hex: true }).z - 10 * HEX_ROW) < 1e-12
      && M.cellCentre(1, 1, { cellSizeM: 10, hex: false }).x === 10
      && M.cellCentre(1, 1, { cellSizeM: 10, hex: false }).z === 10,
      { hex: M.cellCentre(1, 1, { cellSizeM: 10, hex: true }), square: M.cellCentre(1, 1, { cellSizeM: 10, hex: false }),
        pitch: 10 * HEX_ROW })

    // A HEX FOOTPRINT, which no assertion above reached.
    //
    // THE RADIUS IS 30 m AND THAT IS THE WHOLE POINT. At the 25 m radius the square footprint test
    // uses, the hex row pitch is a NO-OP: dropping sqrt(3)/2 from cellCentre leaves the covered set
    // at the same 19 cells, because the lattice quantization absorbs the difference. Measured across
    // radii 9..50 m, the pitch binds at 18, 20, 22, 28, 30, 35, 40, 45 and 50 and does not at 9, 12,
    // 15 and 25. At 30 m the three builds separate cleanly — correct 37 cells, square row pitch 29,
    // unstaggered columns 33 — so this fixture tests the geometry where it BINDS rather than where
    // it happens not to matter.
    const HEX_RAD = 30
    const hexCentreOf = (col, row) => ({ x: col * CELL + ((row & 1) ? 0.5 * CELL : 0), z: row * CELL * HEX_ROW })
    const hCentre = hexCentreOf(48, 32)
    const expectHex = []
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const p = hexCentreOf(x, y)
      if (Math.hypot(p.x - hCentre.x, p.z - hCentre.z) <= HEX_RAD) expectHex.push(y * W + x)
    }
    const hexFoot = attempt(() => M.sourceSupply(surface, W, H,
      { sources: [{ id: 'hexMonsoon', kind: 'distributedRain', xM: hCentre.x, zM: hCentre.z, dischargeM3PerS: 210, radiusM: HEX_RAD }] },
      { cellSizeM: CELL, hex: true }))
    let hexCells = 0, hexSum = 0
    if (hexFoot.ok) for (let i = 0; i < N; i++) if (hexFoot.value.supply[i] !== 0) { hexCells++; hexSum += hexFoot.value.supply[i] }
    check('a hex footprint covers the staggered cells the oracle computes independently',
      hexFoot.ok && expectHex.length === 37 && hexCells === expectHex.length
      && [...hexFoot.value.placements[0].cells].join(',') === expectHex.join(',')
      && Math.abs(hexSum - 210) <= gamma(expectHex.length) * 210,
      { ok: hexFoot.ok, code: hexFoot.code, hexCells, expectedHex: expectHex.length, hexSum })

    // A radius smaller than a cell is a point source, not a source that vanished.
    //
    // NOTE, because it is the kind of thing that becomes a vacuous mutation later: the
    // `out.length ? out : [home.index]` fallback inside `footprintCells` is DEAD CODE. The scan
    // window always contains the home cell and the home cell's centre is always distance 0 from
    // itself, so `out` is never empty. Measured: 720 placements over radii 0.001..9.9 m, offsets
    // 0..7.5 m and both lattices, with the fallback removed — zero behavioural difference. The
    // property below is real and asserted; the branch that appears to provide it is not reachable,
    // so it is deliberately NOT armed as a mutation.
    const tiny = attempt(() => M.sourceSupply(surface, W, H,
      { sources: [{ id: 'seep', kind: 'spring', xM: SPRING_X, zM: SPRING_Z, dischargeM3PerS: 50, radiusM: 1 }] },
      { cellSizeM: CELL }))
    let tinyCells = 0, tinySum = 0
    if (tiny.ok) for (let i = 0; i < N; i++) if (tiny.value.supply[i] !== 0) { tinyCells++; tinySum += tiny.value.supply[i] }
    check('a sub-cell footprint still seeds exactly one cell with the whole discharge',
      tiny.ok && tinyCells === 1 && tinySum === 50 && tiny.value.supply[SPRING_CELL] === 50
      && tiny.value.placements[0].cells.length === 1,
      { ok: tiny.ok, code: tiny.code, tinyCells, tinySum })

    // A move carries everything but the position, and a paste everything but the id. Both were proven
    // only on a plain enabled spring — the two properties most worth carrying, a footprint and a
    // disabled flag, were carried by nothing.
    const movedOff = attempt(() => M.moveSource({ id: 'winterSpring', kind: 'spring', xM: 300, zM: 200, dischargeM3PerS: 7, enabled: false }, 500, 200))
    check('moving a disabled source leaves it disabled',
      movedOff.ok && movedOff.value.enabled === false && movedOff.value.xM === 500, movedOff)
    const pasteFoot = attempt(() => M.duplicateFeature(
      { id: 'monsoonCell', kind: 'distributedRain', xM: 480, zM: 320, dischargeM3PerS: 210, radiusM: 25 }, ['monsoonCell']))
    check('a pasted source keeps its footprint radius',
      pasteFoot.ok && pasteFoot.value.radiusM === 25 && pasteFoot.value.id === 'monsoonCell-2', pasteFoot)
    const pasteOff = attempt(() => M.duplicateFeature(
      { id: 'winterSpring', kind: 'spring', xM: 300, zM: 200, dischargeM3PerS: 7, enabled: false }, ['winterSpring']))
    check('a pasted source stays disabled if the original was',
      pasteOff.ok && pasteOff.value.enabled === false && pasteOff.value.id === 'winterSpring-2', pasteOff)

    // IDs are handles that end up in file names and URL fragments. The refusal above only ever passed
    // `undefined`, which the typeof guard catches on its own — the character set was unconstrained.
    const idCases = [['has space', false], ['a/b', false], ['-leading', false], ['', false], ['ok.id:1-2', true]]
      .map(([id, want]) => ({ id, want, r: attempt(() => M.normalizeSource({ ...spring, id })) }))
    check('a source id is held to the printable handle charset',
      idCases.every(c => c.r.ok === c.want) && idCases.filter(c => !c.want).length === 4
      && idCases.filter(c => !c.want).every(c => c.r.code === 'ID_INVALID'),
      { wrong: idCases.filter(c => c.r.ok !== c.want).map(c => [c.id, c.r.ok, c.r.code]) })

    // A guide every one of whose control points is the same place is not a clean guide, it is no
    // guide; reporting no conflict for one would be absence of evidence dressed up as a pass.
    const zeroLen = attempt(() => M.normalizeGuide({ id: 'pin', intent: 'channel', points: [[5, 5], [5, 5]] }))
    check('a zero-length guide is refused', !zeroLen.ok && zeroLen.code === 'POINTS_INVALID', zeroLen)
    const negTarget = attempt(() => M.normalizeGuide({ ...guideChannel, targetFlowM3PerS: -5 }))
    check('a negative guide target flow is refused',
      !negTarget.ok && negTarget.code === 'DISCHARGE_INVALID', negTarget)
    // A surface of the wrong length would index off the end of the array and read undefined as the
    // elevation of every source on it.
    const shortSurface = attempt(() => M.sourceSupply(new Float32Array(10), W, H, { sources: [spring] }, { cellSizeM: CELL }))
    check('a surface of the wrong length is refused',
      !shortSurface.ok && shortSurface.code === 'SUPPLY_SHAPE', shortSurface)

    // The short field aliases the authoring text and older documents use. `firstDefined` decides
    // which name wins when both are present, and nothing constrained either half of that.
    const aliased = attempt(() => M.normalizeSource({ id: 'aliasCheck', kind: 'spring', x: 7, z: 9, q: 11, temperature: 3, radius: 4 }))
    check('the short field aliases resolve to the canonical fields',
      aliased.ok && aliased.value.xM === 7 && aliased.value.zM === 9
      && aliased.value.dischargeM3PerS === 11 && aliased.value.temperatureC === 3
      && aliased.value.radiusM === 4, aliased)
    const bothNames = attempt(() => M.normalizeSource(
      { id: 'aliasCheck', kind: 'spring', xM: 7, x: 99, zM: 9, z: 88, dischargeM3PerS: 11, q: 77, radiusM: 4, radius: 66 }))
    check('the canonical field name wins when an alias is also present',
      bothNames.ok && bothNames.value.xM === 7 && bothNames.value.zM === 9
      && bothNames.value.dischargeM3PerS === 11 && bothNames.value.radiusM === 4,
      { got: bothNames.ok && { xM: bothNames.value.xM, zM: bothNames.value.zM, q: bothNames.value.dischargeM3PerS, r: bothNames.value.radiusM } })

    // === THIRD ADVERSARIAL ROUND ==================================================================
    // A third sweep found nine more. Two of them are guardrail violations rather than wrong numbers:
    // a guide control point that accepts an elevation, and falsy-zero handling that silently discards
    // a 0 degrees C glacial source's temperature and a 0 m3/s source's discharge.

    // A label that names the WRONG kind is self-consistent — every record still gets the label its
    // own kind maps to — so the check above passes with two labels swapped. Each label must actually
    // contain the kind it stands for.
    const labelStem = k => k.replace(/([a-z])([A-Z])/g, '$1 $2').split(' ')[0].toLowerCase()
    const badLabels = M.SOURCE_KINDS.filter(k => !String(M.SOURCE_KIND_LABEL[k]).toLowerCase().includes(labelStem(k)))
    check('each source kind label names the kind it stands for',
      badLabels.length === 0 && new Set(M.SOURCE_KINDS.map(k => M.SOURCE_KIND_LABEL[k])).size === M.SOURCE_KINDS.length,
      { badLabels: badLabels.map(k => [k, M.SOURCE_KIND_LABEL[k], labelStem(k)]) })

    // The guide `q=` key, end to end: text in, seeded head out. The parse assertion above only ever
    // counted the guide's control points, so the key that carries its target flow was unconstrained.
    const textGuide = attempt(() => M.sourceSupply(surface, W, H,
      M.parseFeatureText('guide id=c intent=channel q=300 200,320 500,320\n'),
      { cellSizeM: CELL, includeGuideTargets: true }))
    let textGuideSum = 0
    if (textGuide.ok) for (let i = 0; i < N; i++) textGuideSum += textGuide.value.supply[i]
    check('a guide target flow authored as text reaches the head cell',
      textGuide.ok && textGuideSum === 300 && textGuide.value.guideSeededCount === 1
      && textGuide.value.supply[SPRING_CELL] === 300,
      { ok: textGuide.ok, code: textGuide.code, sum: textGuideSum,
        guideSeeded: textGuide.ok ? textGuide.value.guideSeededCount : null })

    // EVERY source in this file so far sits exactly on a cell centre, where rounding down and
    // rounding to nearest agree. An author clicking a map does not. Two off-centre placements where
    // the two disagree, computed independently.
    const offCentre = [[206, 326, 21, 33], [215, 335, 22, 34]].map(([x, z, col, row]) => ({
      x, z, col, row, floorCol: Math.floor(x / CELL), floorRow: Math.floor(z / CELL),
      r: attempt(() => M.sourceSupply(surface, W, H, { sources: [{ ...spring, xM: x, zM: z }] }, { cellSizeM: CELL })),
    }))
    check('a source off the cell centre lands in the nearest cell, not the one below it',
      offCentre.every(o => o.r.ok && o.r.value.placements[0].col === o.col && o.r.value.placements[0].row === o.row
        && (o.floorCol !== o.col || o.floorRow !== o.row)),
      { got: offCentre.map(o => [o.x, o.z, o.r.ok && o.r.value.placements[0].col, o.r.ok && o.r.value.placements[0].row,
        'nearest', o.col, o.row, 'floor', o.floorCol, o.floorRow]) })

    // `enabled` is a tri-state in disguise unless it is a strict boolean: "yes", 1 and 0 all have an
    // obvious intent and all of them would be read as the wrong one.
    const enabledCases = [[true, true], [false, true], ['yes', false], [1, false], [0, false], [null, false]]
      .map(([v, want]) => ({ v, want, r: attempt(() => M.normalizeSource({ ...spring, enabled: v })) }))
    check('enabled is held to a strict boolean',
      enabledCases.every(c => c.r.ok === c.want)
      && enabledCases.filter(c => !c.want).every(c => c.r.code === 'ENABLED_INVALID'),
      { wrong: enabledCases.filter(c => c.r.ok !== c.want).map(c => [JSON.stringify(c.v), c.r.ok, c.r.code]) })

    // ZERO IS A VALUE, NOT AN ABSENCE. A glacial source at 0 degrees C is the whole point of the
    // glacialSnowmelt kind, and `||` would turn its temperature into null; a 0 m3/s source is a
    // placed, named feature an author has switched down rather than one that does not exist.
    const zeroT = attempt(() => M.normalizeSource({ id: 'melt', kind: 'glacialSnowmelt', xM: 100, zM: 100, dischargeM3PerS: 5, temperatureC: 0 }))
    const zeroTAlias = attempt(() => M.normalizeSource({ id: 'melt', kind: 'glacialSnowmelt', xM: 100, zM: 100, dischargeM3PerS: 5, temperature: 0 }))
    const zeroTText = attempt(() => M.serializeWaterFeatures({ sources: [{ id: 'melt', kind: 'glacialSnowmelt', xM: 100, zM: 100, dischargeM3PerS: 5, temperatureC: 0 }] }))
    check('a zero degree source keeps its zero rather than losing it to falsiness',
      zeroT.ok && zeroT.value.temperatureC === 0 && zeroTAlias.ok && zeroTAlias.value.temperatureC === 0
      && zeroTText.ok && /"temperatureC": 0\b/.test(zeroTText.value),
      { direct: zeroT.ok && zeroT.value.temperatureC, alias: zeroTAlias.ok && zeroTAlias.value.temperatureC,
        serialized: zeroTText.ok && /"temperatureC": 0\b/.test(zeroTText.value) })
    const zeroQ = attempt(() => M.sourceSupply(surface, W, H, { sources: [{ ...spring, dischargeM3PerS: 0 }] }, { cellSizeM: CELL }))
    let zeroQSum = 0
    if (zeroQ.ok) for (let i = 0; i < N; i++) zeroQSum += zeroQ.value.supply[i]
    check('a zero discharge source is placed and counted, and seeds zero',
      zeroQ.ok && zeroQSum === 0 && zeroQ.value.seededCount === 1 && zeroQ.value.totalQM3PerS === 0
      && zeroQ.value.placements[0].index === SPRING_CELL,
      { ok: zeroQ.ok, code: zeroQ.code, sum: zeroQSum,
        seeded: zeroQ.ok ? zeroQ.value.seededCount : null })

    // The flat mixed-array input shape, which nothing reached: a feature set can arrive as one list.
    const flatSet = attempt(() => M.normalizeWaterFeatures([spring, { id: 'flatGuide', intent: 'channel', points: [[1, 1], [2, 2]] }]))
    check('a flat mixed array is split into sources and guides',
      flatSet.ok && flatSet.value.sources.length === 1 && flatSet.value.guides.length === 1
      && flatSet.value.sources[0].id === 'nileSpring' && flatSet.value.guides[0].id === 'flatGuide', flatSet)

    // GUARDRAIL: "guide control points are two-dimensional intent; elevation comes only from sampling
    // routingSurface." A point that accepted a y would let an author declare a river's height, which
    // is the one authority this sprint refuses to hand over. Asserted on all three surfaces a y could
    // survive on — the normalized guide, the emitted record and the serialized file.
    const yGuide = { id: 'yGuide', intent: 'channel', points: [{ x: 1, z: 2, y: 999 }, { x: 3, z: 4, y: 888 }] }
    const yNorm = attempt(() => M.normalizeGuide(yGuide))
    const yRec = attempt(() => M.waterFeatureRecords({ guides: [yGuide] }))
    const yText = attempt(() => M.serializeWaterFeatures({ guides: [yGuide] }))
    check('a guide control point carries x and z only, on every surface it appears',
      yNorm.ok && Object.keys(yNorm.value.points[0]).join(',') === 'x,z'
      && yRec.ok && Object.keys(yRec.value.guides[0].points[0]).join(',') === 'x,z'
      && yText.ok && !/999|888/.test(yText.value),
      { normalized: yNorm.ok && Object.keys(yNorm.value.points[0]),
        record: yRec.ok && Object.keys(yRec.value.guides[0].points[0]),
        serializedCarriesY: yText.ok && /999|888/.test(yText.value) })

    // A minted id must be an id this module will accept back. Without the length cap, a long base
    // mints a handle that `normalizeSource` then refuses — a paste that produces an unsaveable
    // document.
    const longBase = 'a'.repeat(200)
    const longMint = attempt(() => M.mintFeatureId(longBase, []))
    const longRoundTrip = attempt(() => M.normalizeSource({ ...spring, id: longMint.ok ? longMint.value : 'x' }))
    check('a minted id is always an id this module accepts back',
      longMint.ok && longMint.value.length <= 56 && longRoundTrip.ok
      && longRoundTrip.value.id === longMint.value,
      { minted: longMint.ok && longMint.value.length, accepted: longRoundTrip.ok, code: longRoundTrip.code })

    // === FOURTH ADVERSARIAL ROUND =================================================================
    // Mostly the refusal paths: guards this module implements, with a named error code each, that no
    // assertion ever ran. A guard nothing exercises is a guard that can be deleted by accident.
    //
    // TWO GUARDS ARE DELIBERATELY NOT ARMED because they are provably redundant — arming them would
    // put a bit-identical mutation in the list, which is the exact failure this file exists to catch:
    //   * the continuous half-cell test in `cellOfWorld`'s `inDomain` (`v >= -0.5 && v <= hgt - 0.5
    //     && u >= -0.5 && u <= w - 0.5`). Measured over 25,926 positions from -60 m to 1020 m on
    //     both axes: removing it changes `inDomain` for none of them, because `Math.round` plus the
    //     integer row/col bounds already decide exactly the same set.
    //   * `normalizeGuide`'s `src.length < 2` test. A one-point guide has no segments, so `lengthM`
    //     is 0 and the zero-length guard below refuses it with the SAME `POINTS_INVALID` code.
    //     Measured over six point lists: identical behaviour with the guard removed.

    // Ids are document-wide handles, so the taken set a paste consults must span BOTH lists —
    // otherwise a pasted guide can be minted straight onto an existing guide's id.
    check('featureIds spans sources and guides',
      M.featureIds({ sources: [spring], guides: [guideChannel] }).join(',') === 'nileSpring,nileCourse',
      { ids: M.featureIds({ sources: [spring], guides: [guideChannel] }) })
    // A paste with no taken set is the common case from a context menu, and it must still not collide
    // with the feature it was copied from.
    const bareCopy = attempt(() => M.duplicateFeature(spring))
    const bareGuideCopy = attempt(() => M.duplicateFeature(guideChannel))
    check('a paste with no taken set still mints a fresh id',
      bareCopy.ok && bareCopy.value.id === 'nileSpring-2'
      && bareGuideCopy.ok && bareGuideCopy.value.id === 'nileCourse-2',
      { source: bareCopy.ok && bareCopy.value.id, guide: bareGuideCopy.ok && bareGuideCopy.value.id })
    // The trailing newline is part of the format, in this module's own words.
    check('the canonical text ends with the newline the format specifies',
      M.serializeWaterFeatures({ sources: [spring] }).endsWith('}\n'),
      { tail: JSON.stringify(M.serializeWaterFeatures({ sources: [spring] }).slice(-3)) })

    // The refusal table. Every row is a guard with a named code; each was unexercised.
    const guards = [
      ['a sources field that is not an array', 'FEATURE_SHAPE', () => M.normalizeWaterFeatures({ sources: 'nope' })],
      ['a guides field that is not an array', 'FEATURE_SHAPE', () => M.normalizeWaterFeatures({ guides: 'nope' })],
      ['a non-integer domain width', 'SUPPLY_SHAPE', () => M.sourceSupply(surface, 96.5, H, { sources: [spring] }, { cellSizeM: CELL })],
      ['a zero domain width', 'SUPPLY_SHAPE', () => M.sourceSupply(new Float32Array(0), 0, H, { sources: [spring] }, { cellSizeM: CELL })],
      ['a zero cell size', 'SUPPLY_SHAPE', () => M.sourceSupply(surface, W, H, { sources: [spring] }, { cellSizeM: 0 })],
      ['two supply arrays of different lengths', 'SUPPLY_SHAPE', () => M.combineSupply(new Float64Array(4), new Float64Array(5))],
      ['a fractional schema version', 'SCHEMA_VERSION', () => M.migrateWaterFeatures({ schemaVersion: 1.5, sources: [] })],
      ['a negative schema version', 'SCHEMA_VERSION', () => M.migrateWaterFeatures({ schemaVersion: -1, sources: [] })],
      ['a three-part control point', 'TEXT_SYNTAX', () => M.parseFeatureText('guide id=g intent=channel 1,2,3 4,5\n')],
    ].map(([name, code, fn]) => ({ name, code, r: attempt(fn) }))
    const wrongGuards = guards.filter(g => g.r.ok || g.r.code !== g.code)
    check('every declared guard refuses its own malformed input with its own code',
      guards.length === 9 && wrongGuards.length === 0,
      { checked: guards.length, wrong: wrongGuards.map(g => [g.name, g.r.ok ? 'ACCEPTED' : g.r.code, 'want ' + g.code]) })

    // === the authoring text block =================================================================
    const parsed = attempt(() => M.parseFeatureText(
      '# a desert river\nsource id=nileSpring kind=spring x=200 z=320 q=1200 t=24\n'
      + 'guide id=nileCourse intent=channel q=300 200,320 500,320 900,320\n'))
    check('the authoring text block parses one source and one guide',
      parsed.ok && parsed.value.sources.length === 1 && parsed.value.guides.length === 1
      && parsed.value.sources[0].dischargeM3PerS === 1200 && parsed.value.guides[0].points.length === 3, parsed)
    const typo = attempt(() => M.parseFeatureText('source id=a kind=spring x=1 z=1 dischage=5\n'))
    check('a mistyped key in the text block is refused with its line number',
      !typo.ok && typo.code === 'TEXT_SYNTAX' && /line 1/.test(typo.message), typo)

    // === the plugin's port block ==================================================================
    check('the Water Sources plugin source was read', typeof pluginSrc === 'string' && pluginSrc.length > 1000,
      { bytes: pluginSrc ? pluginSrc.length : 0 })
    const stripped = pluginSrc.replace(/^\s*\/\/.*$/gm, '')
    let inputs = null, outputs = null, params = null, parseErr = null
    try {
      inputs = new Function('RANGE', 'return ' + literalAfter(stripped, 'inputs:'))(Ports.RANGE)
      outputs = new Function('RANGE', 'return ' + literalAfter(stripped, 'outputs:'))(Ports.RANGE)
      const stub = key => ({ id: key })
      params = new Function('P', 'return ' + literalAfter(stripped, 'params:'))({ slider: stub, text: stub, toggle: stub })
    } catch (e) { parseErr = String((e && e.message) || e).slice(0, 200) }
    if (!check('the Water Sources port block parses',
      Array.isArray(inputs) && Array.isArray(outputs) && Array.isArray(params),
      { parseErr, inputs: inputs && inputs.length, outputs: outputs && outputs.length })) {
      for (const n of ['the plugin declares three inputs and five outputs',
        'the primary output is the untouched routing surface',
        'every Water Sources port validates against ports.js',
        'the discharge outputs are typed in m3PerS',
        'the feature ports carry the featureSet kind']) check(n, false, 'port block did not parse')
      return
    }
    check('the plugin declares three inputs and five outputs',
      inputs.length === 3 && outputs.length === 5, { inputs: inputs.length, outputs: outputs.length })
    const primary = outputs.filter(p => p.primary)
    check('the primary output is the untouched routing surface',
      primary.length === 1 && primary[0].id === 'routingSurface'
      && primary[0].semantic === 'routingSurface' && primary[0].lens === 'continued',
      { primary: primary.map(p => p.id) })
    const problems = Ports.validatePortList({ inputs, outputs, source: 'declared' })
    check('every Water Sources port validates against ports.js', problems.length === 0, problems)
    const qPorts = outputs.filter(p => p.semantic === 'discharge')
    check('the discharge outputs are typed in m3PerS',
      qPorts.length === 2 && qPorts.every(p => p.unit === 'm3PerS' && p.storage === 'R32F'),
      { qPorts: qPorts.map(p => ({ id: p.id, unit: p.unit })) })
    const featurePorts = outputs.filter(p => p.kind === 'featureSet')
    check('the feature ports carry the featureSet kind',
      featurePorts.length === 2 && featurePorts.every(p => p.storage === 'RECORDS' && p.semantic === 'feature' && p.unit === 'none'),
      { featurePorts: featurePorts.map(p => p.id) })
    check('the plugin exposes no salinity parameter and no water-level knob',
      params.every(p => !/salin|level/i.test(p.id)) && params.length === 3, { params: params.map(p => p.id) })
    // TRIPWIRE. The unrouted source term is m3/s at a cell, which is NOT a discharge, and ports.js
    // has no semantic for it today — so `sourceSupply` ships as `discharge` and nothing can refuse it
    // being wired into a Rivers node. The story report asks for `waterSupply`. When it lands this
    // goes red and forces the port and this assertion to be updated together, rather than leaving a
    // comment describing a world that has moved on.
    check('waterSupply is not yet a ports.js semantic',
      Ports.SEMANTICS.waterSupply === undefined, { present: Ports.SEMANTICS.waterSupply || null })

    check("assertion inventory non-empty", assertions.length >= 110, assertions.length)
  }

  /** Every cell reachable downslope of `index` through the MFD receiver graph. Computed from the
   *  routing weights, independently of anything the source module reports. */
  function coneFrom(index, weights) {
    const seen = new Uint8Array(N)
    const stack = [index]
    seen[index] = 1
    while (stack.length) {
      const i = stack.pop()
      for (let k = 0; k < weights.nbCount; k++) {
        const ni = weights.rcv[i * weights.nbCount + k]
        if (ni < 0 || weights.wgt[i * weights.nbCount + k] <= 0) continue
        if (!seen[ni]) { seen[ni] = 1; stack.push(ni) }
      }
    }
    return seen
  }

  function literalAfter(src, key) {
    const at = src.indexOf(key)
    if (at < 0) return 'null'
    const start = src.indexOf('[', at)
    let depth = 0
    for (let i = start; i < src.length; i++) {
      if (src[i] === '[') depth++
      else if (src[i] === ']') { depth--; if (depth === 0) return src.slice(start, i + 1) }
    }
    return 'null'
  }

  function report() {
    let ok = assertions.every(a => a.ok)
    if (mutation) {
      if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
      ok = false
    }
    const failed = assertions.filter(a => !a.ok).map(a => a.name)
    const f = (v, d = 6) => (Number.isFinite(v) ? v.toFixed(d) : 'n/a')
    console.log(`${ok ? 'PASS' : 'FAIL'}  water sources qDown=${f(measured.qDownstream, 6)} `
      + `downRelErr=${Number.isFinite(measured.downRelErr) ? measured.downRelErr.toExponential(3) : 'n/a'} `
      + `qOutlet=${f(measured.qOutlet, 6)} authored=${SPRING_Q} outRelErr=${Number.isFinite(measured.outRelErr) ? measured.outRelErr.toExponential(3) : 'n/a'} `
      + `planBound=${Number.isFinite(measured.bound) ? (measured.bound / SPRING_Q).toExponential(3) : 'n/a'} `
      + `propErr=${Number.isFinite(measured.worstProp) ? measured.worstProp.toExponential(3) : 'n/a'} `
      + `divergeOn=${Number.isFinite(measured.divergeOn) ? measured.divergeOn.toExponential(3) : 'n/a'} `
      + `assertions=${assertions.length} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
    if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify(assertions.filter(a => !a.ok), null, 2))
    process.exit(ok ? 0 : 1)
  }
})().catch(e => { console.error('FATAL', (e && e.stack) || e); process.exit(2) })
