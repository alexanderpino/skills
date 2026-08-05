// S4.9 — shore, river, lake, ice and foam regimes.
//
// This is a PURE-MODULE oracle. It imports src/core/water-regimes.js, patches its source text for
// each mutation, and checks the physics in double precision with no browser. The plugin is loaded
// the same way, against the SAME patched core, so a mutation reaches the node exactly as it reaches
// the module — loading the node against a pristine core would leave every node assertion permanently
// green, which is coverage that cannot fail.
//
// THE PROPERTY THAT CARRIES THE STORY is the partition: every wet sample lands in EXACTLY ONE regime
// and every regime is reachable. A broken classifier violates it immediately, and the classic way to
// break it is five independent `if` tests in a shader, where a shallow fast cold cell is shore AND
// river AND ice at once. `regimes-overlap` is that mutation, written out.
//
// EVERY FIXTURE IS ANALYTIC. The beach is a linear depth ramp on dyadic depths, so the shoaling law's
// three bands are reached by construction and the breaking band's amplitude is exactly 0.78 x depth.
// The classification grid is six horizontal bands with one regime each, so the six counts are known
// before the module runs — 1024 lake, 1024 shore, 512 river, 512 rapids, 512 ice, 512 dry — and an
// off-by-one in the cascade moves them.
//
// WHAT IS ASSERTED EXACTLY, because each is a claim about ZERO or ONE rather than about a tolerance:
//
//   a river's swell, chop and surf foam            exactly 0   (fetch 0, not "very small")
//   displacement at full ice                       exactly 0
//   rapid foam on water with no gradient           exactly 0
//   a river detail band at zero speed              bit-identical across 1000 s
//   reversing the flow field                       exactly negates the phase travel
//   the calm/ripple/turbulent weights              sum to exactly 1
//   the five regime masks on a wet sample          sum to exactly 1
//
// -------------------------------------------------------------------------------------------------
// SECOND PASS — NINE DEFECTS THIS ORACLE LET THROUGH ON ITS FIRST VERSION.
//
// Each was injected into the shipped core one at a time and the suite stayed PASS with failed=[] —
// 45 assertions and 21 armed mutations saw none of them. They were not code defects: the code was
// right and NOTHING was holding it there. The pattern in all nine is one pattern. The fixture only
// ever visits the ENDS of a quantity, so everything about its middle is free.
//
//   ice is only ever exactly 0 or exactly 1 in the grid  -> partial-ice behaviour was unconstrained
//   aeration is only ever exactly 0 or exactly 1         -> FOAM_REGIME_MIN was unconstrained
//   persistence is called with one of its two terms 0    -> max and sum are equal there
//   depths are 2 and 20 against a shore depth of 12      -> the boundary comparison was free
//   the continuity bound separates smooth from a STEP    -> but not from a LINEAR wedge
//
// The additions below are marked `2ND PASS` and each carries the two measured builds its bound sits
// between. Ten new mutations arm them.
const path = require('path')
const fs = require('fs')
const { pathToFileURL } = require('url')

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  // --- the story's two named armed failures ----------------------------------------------------
  'ocean-waves-on-rivers',     // rivers given a fetch, so ocean displacement appears on them
  'river-gets-standing-swell', // the body kind ignores the regime -- the first draft's own defect
  'noise-foam',                // foam is whatever a hash produced, which is the shipped renderer
  'foam-has-a-floor',          // "water should always look alive": a base level under the ramp
  // --- displacement ------------------------------------------------------------------------------
  'lake-uses-ocean-fetch',     // a lake swells like open ocean
  'chop-ignores-swell',        // chop is not paid out of the remaining depth budget
  'foam-sums-causes',          // three alternatives added instead of maxed, so foam exceeds 1
  // --- flow --------------------------------------------------------------------------------------
  'speed-ignores-gradient',    // Manning without S^(1/2): every depth flows the same
  'speed-ignores-constriction',// a narrows runs no faster than a pool
  // --- ice ---------------------------------------------------------------------------------------
  'ice-is-a-step',             // the lake snaps from open water to mirror between two frames
  'ice-not-exact-at-full',     // "fully frozen" leaves 0.1% of the motion behind
  'ice-does-not-suppress',     // a frozen lake still ripples
  // --- river surface -----------------------------------------------------------------------------
  'advect-fixed-axis',         // advect by |v| along +x: identical on a straight reach, backwards on the bend
  'advect-when-still',         // a constant scroll added on top of the physical speed
  'foam-persistence-per-frame',// decay per FRAME, so a wake's length depends on the frame rate
  'ripple-weights-not-a-partition', // calm computed without the ripple term, so the weights sum > 1
  // --- the partition and the refusals ------------------------------------------------------------
  'regimes-overlap',           // five independent predicates instead of one cascade
  'dry-cells-are-wet',         // depth 0 classified as water, which floods the whole domain
  'short-raster-reads-zero',   // a raster shorter than the field read as zeros instead of refused
  // --- the node ----------------------------------------------------------------------------------
  'plugin-emits-height',       // guardrail 1: the water-family node grows a terrain-height output
  'plugin-ignores-temperature',// the node computes ice from nothing and reports open water
  // --- 2ND PASS: the nine defects the first version of this oracle stayed green on ---------------
  'ice-ramp-is-linear',        // a linear wedge: slope discontinuity exactly at the ice edge
  'partial-ice-claims-regime', // a 0.1%-frozen lake is masked as solid ice
  'foam-double-damped-by-ice', // surf damped twice, so a half-frozen shore goes grey
  'rapids-at-a-trickle',       // the rapids threshold collapses: lightly rippled river becomes whitewater
  'rapids-never-arrive',       // the rapids threshold runs away: near-critical flow stays a river
  'lake-chop-ignores-fetch',   // a lake swells correctly and chops like the open ocean
  'foam-persistence-sums',     // surviving foam ADDS to new foam, so foam exceeds 1
  'shore-swallows-the-lake-edge', // water exactly at the reference depth is shore, not lake
  'channel-q-excludes-threshold', // discharge exactly at the channel-forming value is not a river
  'absent-temperature-freezes',// an unwired Temperature port defaults to -10 degC and ices the world
]
const PATCHES = {
  // A river's fetch is EXACTLY zero on purpose; anything else and Gerstner displacement reaches it.
  'ocean-waves-on-rivers': [['river: 0 })', 'river: 2e3 })']],
  // The first draft's own defect, restored: the body kind stops following the regime, so a river
  // takes the standing-water fetch and every shallow river cell renders as breaking surf.
  'river-gets-standing-swell': [['  out.bodyKind = bodyKindFor(out.regime, opts)', '  out.bodyKind = standingBodyKind(opts)']],
  'lake-uses-ocean-fetch': [['ocean: 5e5, lake: 2e3,', 'ocean: 5e5, lake: 5e5,']],
  'chop-ignores-swell': [['  const roomM = Math.max(0, budgetM - swellM)', '  const roomM = budgetM']],
  // The shipped water's foam: a hash of position. It is the story's named armed failure, and it is
  // indistinguishable from causal foam in a screenshot and from nothing at all in a still frame.
  'noise-foam': [['    foam[i] = r.foam', '    foam[i] = ((Math.sin((i + 1) * 12.9898) * 43758.5453) % 1 + 1) % 1']],
  'foam-has-a-floor': [['  if (!(froude > foamFroudeOnset)) return 0', '  if (!(froude > foamFroudeOnset)) return 0.15']],
  'foam-sums-causes': [[
    '  const f = Math.max(rapidFoam(froude, opts), surfFoam(swellM, depthM), crestFoam(jacobian, opts))',
    '  const f = rapidFoam(froude, opts) + surfFoam(swellM, depthM) + crestFoam(jacobian, opts)']],
  'speed-ignores-gradient': [[
    '  return (Math.pow(depthM, 2 / 3) * Math.sqrt(slope) / n) * c',
    '  return (Math.pow(depthM, 2 / 3) / n) * c']],
  'speed-ignores-constriction': [[
    '  return (Math.pow(depthM, 2 / 3) * Math.sqrt(slope) / n) * c',
    '  return (Math.pow(depthM, 2 / 3) * Math.sqrt(slope) / n) * 1']],
  'ice-is-a-step': [[
    '  return smooth01((iceOnsetC - temperatureC) / (iceOnsetC - iceSolidC))',
    '  return temperatureC <= iceOnsetC ? 1 : 0']],
  'ice-not-exact-at-full': [[
    '  return smooth01((iceOnsetC - temperatureC) / (iceOnsetC - iceSolidC))',
    '  return Math.min(0.999, smooth01((iceOnsetC - temperatureC) / (iceOnsetC - iceSolidC)))']],
  'ice-does-not-suppress': [['  return 1 - clamp01(ice)', '  return 1']],
  'advect-fixed-axis': [['  const ux = len > 0 ? flowX / len : 0', '  const ux = 1']],
  'advect-when-still': [[
    '  const travel = speedMps * tSeconds + band.offsetM',
    '  const travel = (speedMps + 0.5) * tSeconds + band.offsetM']],
  'foam-persistence-per-frame': [['  const kept = prev * Math.exp(-dt / tau)', '  const kept = prev * 0.9']],
  'ripple-weights-not-a-partition': [[
    '  return { calm: 1 - (turbulent + ripple), ripple, turbulent }',
    '  return { calm: 1 - turbulent, ripple, turbulent }']],
  // The five-independent-`if` shader, written out. Nothing here is obviously wrong to read, which is
  // exactly why the partition has to be asserted rather than reasoned about.
  'regimes-overlap': [[
    '    const r = classified.regime[i]\n    if (r >= 0 && r < REGIME_COUNT) masks[REGIME_NAMES[r]][i] = 1',
    '    const dd = at(fields.depthM, i, 0)\n'
    + '    if (dd > 0) {\n'
    + '      if (classified.ice[i] > 0) masks.ice[i] = 1\n'
    + '      if (classified.foam[i] > 0) masks.foam[i] = 1\n'
    + '      if (at(fields.dischargeM3S, i, 0) >= channelFormingQ(opts)) masks.river[i] = 1\n'
    + '      if (dd < shoreDepth(opts)) masks.shore[i] = 1\n'
    + '      else masks.lake[i] = 1\n'
    + '    }']],
  'dry-cells-are-wet': [['  if (!(depthM > 0)) return out', '  if (depthM < 0) return out']],
  'short-raster-reads-zero': [["    if (typeof f.length !== 'number' || f.length < N) {", '    if (false) {']],
  // --- 2ND PASS ------------------------------------------------------------------------------------
  // Each of these was injected into the shipped core and the FIRST version of this oracle returned
  // PASS failed=[] on every one of them.
  'ice-ramp-is-linear': [[
    'const smooth01 = u => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u))',
    'const smooth01 = u => (u <= 0 ? 0 : u >= 1 ? 1 : u)']],
  'partial-ice-claims-regime': [[
    '  if (out.ice >= 1) out.regime = REGIME.ICE', '  if (out.ice > 0) out.regime = REGIME.ICE']],
  'foam-double-damped-by-ice': [['    swellM: disp.swellM,', '    swellM: out.swellM,']],
  'rapids-at-a-trickle': [['export const FOAM_REGIME_MIN = 0.5', 'export const FOAM_REGIME_MIN = 0.02']],
  'rapids-never-arrive': [['export const FOAM_REGIME_MIN = 0.5', 'export const FOAM_REGIME_MIN = 0.99']],
  'lake-chop-ignores-fetch': [[
    '  const chopM = Math.min(Math.max(chopAmpM, 0) * scale, roomM)',
    '  const chopM = Math.min(Math.max(chopAmpM, 0), roomM)']],
  'foam-persistence-sums': [['  return Math.max(cause, kept)', '  return cause + kept']],
  'shore-swallows-the-lake-edge': [[
    '  else if (depthM < shoreDepth(opts)) out.regime = REGIME.SHORE',
    '  else if (depthM <= shoreDepth(opts)) out.regime = REGIME.SHORE']],
  'channel-q-excludes-threshold': [[
    '  else if ((Number(sample.dischargeM3S) || 0) >= channelFormingQ(opts)) out.regime = REGIME.RIVER',
    '  else if ((Number(sample.dischargeM3S) || 0) > channelFormingQ(opts)) out.regime = REGIME.RIVER']],
  'absent-temperature-freezes': [[
    '      temperatureC: at(fields.temperatureC, i, 20),',
    '      temperatureC: at(fields.temperatureC, i, -10),']],
}
// Mutations that patch the PLUGIN rather than the core module.
const PLUGIN_PATCHES = {
  'plugin-emits-height': [
    ["    { id: 'foam', name: 'Foam', kind: 'scalarRaster', storage: 'R32F', components: 1,",
      "    { id: 'height', name: 'Height', kind: 'scalarRaster', storage: 'R32F', components: 1,\n"
      + "      semantic: 'relativeHeight', unit: 'none', lens: 'continued' },\n"
      + "    { id: 'foam', name: 'Foam', kind: 'scalarRaster', storage: 'R32F', components: 1,"],
    ["    const values = new Map([['waterDepth', src]])",
      "    const values = new Map([['waterDepth', src], ['height', src]])"],
  ],
  'plugin-ignores-temperature': [['      temperatureC: ins[2] || 20,', '      temperatureC: 20,']],
}
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

const dataUrl = text => 'data:text/javascript;base64,' + Buffer.from(text, 'utf8').toString('base64')
/** Patch a module's source text and return an importable data URL. Every anchor must match exactly
 *  once: an anchor that has drifted out of the source would leave the module unmodified and score
 *  the mutation as armed while proving nothing. */
const patchText = (text, patches, label) => {
  for (const [anchor, repl] of patches || []) {
    const hits = text.split(anchor).length - 1
    if (hits !== 1) { console.error(`FATAL ${label} anchor for ${mutation} matched ${hits}, expected 1`); process.exit(2) }
    text = text.replace(anchor, repl)
  }
  return text
}

// --- fixture constants ---------------------------------------------------------------------------
const W = 64, H = 64, N = W * H
const REF_M = 12                 // deep-water reference: half the longest authored wavelength
const SWELL_M = 1.5              // authored ocean swell amplitude
const CHOP_M = 0.35              // authored chop amplitude
const DEPTH_STEP = 0.125         // dyadic, so every fixture depth is exact in double AND in Float32
const DEPTH_SAMPLES = 321        // 0 .. 40 m
const MANNING_N = 0.035
const CHANNEL_Q = 0.1
const SHORE_DEPTH = 12

// The six analytic bands of the classification grid. Rows are half-open [y0, y1).
const BANDS = [
  { name: 'lake', y0: 0, y1: 16, depth: 20, q: 0, temp: 20, slope: 0 },
  { name: 'shore', y0: 16, y1: 32, depth: 2, q: 0, temp: 20, slope: 0 },
  { name: 'river', y0: 32, y1: 40, depth: 1.5, q: 5, temp: 20, slope: 0.001 },
  { name: 'foam', y0: 40, y1: 48, depth: 1.5, q: 5, temp: 20, slope: 0.05 },
  { name: 'ice', y0: 48, y1: 56, depth: 5, q: 0, temp: -10, slope: 0 },
  { name: 'dry', y0: 56, y1: 64, depth: 0, q: 0, temp: 20, slope: 0 },
]
const bandAt = y => BANDS.find(b => y >= b.y0 && y < b.y1)
const gridField = key => {
  const f = new Float64Array(N)
  for (let y = 0; y < H; y++) { const b = bandAt(y); for (let x = 0; x < W; x++) f[y * W + x] = b[key] }
  return f
}

;(async () => {
  const coreFile = path.resolve(__dirname, '../../src/core/water-regimes.js')
  const wavesHref = pathToFileURL(path.resolve(__dirname, '../../src/core/water-waves.js')).href
  // ALWAYS loaded as a data URL, mutated or not, so the pristine run and the mutated runs take the
  // identical code path. The relative import has to become absolute for a data: URL to resolve it.
  let coreText = patchText(fs.readFileSync(coreFile, 'utf8'), mutation ? PATCHES[mutation] : null, 'core')
  if (coreText.split("'./water-waves.js'").length - 1 !== 1) {
    console.error('FATAL the water-waves import rewrite did not match exactly once'); process.exit(2)
  }
  coreText = coreText.replace("'./water-waves.js'", JSON.stringify(wavesHref))
  const coreHref = dataUrl(coreText)

  let M = null, loadErr = null
  try { M = await import(coreHref) } catch (e) { loadErr = String(e.message || e).slice(0, 200) }

  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }
  if (!check('module loads', M !== null, loadErr)) return report()

  const WAVES = await import(wavesHref)
  const BREAK = WAVES.SHOAL_BREAK_RATIO

  // ================================================================================================
  // ANALYTIC BEACH — a linear depth ramp, so the shoaling law's three bands are reached by
  // construction and the breaking band's amplitude is exactly BREAK x depth.
  // ================================================================================================
  const depths = []
  for (let j = 0; j < DEPTH_SAMPLES; j++) depths.push(j * DEPTH_STEP)
  const dispFor = kind => depths.map(d =>
    M.surfaceDisplacement(kind, { ampM: SWELL_M, chopAmpM: CHOP_M, depthM: d, refM: REF_M }))
  const sea = dispFor('ocean')
  const lakeD = dispFor('lake')
  const riverD = dispFor('river')

  // ABSENCE OF EVIDENCE IS A FAILURE: a beach that produced no wave has proved nothing about waves.
  let wavy = 0, deepSwell = sea[DEPTH_SAMPLES - 1].swellM, maxSwell = 0, maxSwellDepth = -1
  for (let j = 0; j < DEPTH_SAMPLES; j++) {
    if (sea[j].swellM > 0) wavy++
    if (sea[j].swellM > maxSwell) { maxSwell = sea[j].swellM; maxSwellDepth = depths[j] }
  }
  check('the beach fixture produced a wave at every wet depth',
    wavy === DEPTH_SAMPLES - 1 && deepSwell > 0, { wavy, expected: DEPTH_SAMPLES - 1, deepSwell })
  // Green's law: amplitude rises as depth^(-1/4) into shallow water, so the peak is NOT in deep
  // water. Without shoaling the maximum would sit at the authored amplitude in the deepest cell.
  check('the swell shoals: its maximum is inshore and above the deep-water amplitude',
    maxSwell > deepSwell * 1.3 && maxSwellDepth > 0 && maxSwellDepth < REF_M / 2,
    { deepSwell, maxSwell, maxSwellDepth })

  // Exactly zero on dry ground, and on negative depth, which is what a signed shore distance gives.
  const dry = M.surfaceDisplacement('ocean', { ampM: SWELL_M, chopAmpM: CHOP_M, depthM: 0, refM: REF_M })
  const inland = M.surfaceDisplacement('ocean', { ampM: SWELL_M, chopAmpM: CHOP_M, depthM: -3, refM: REF_M })
  check('liquid displacement is exactly zero on dry and inland samples',
    dry.swellM === 0 && dry.chopM === 0 && dry.totalM === 0
    && inland.swellM === 0 && inland.chopM === 0 && inland.totalM === 0, { dry, inland })

  // THE WAVE NEVER REACHES THE BED. Total displacement over depth peaks at exactly the McCowan
  // ratio in the breaking band and is far below it everywhere else, so the bound is two-sided: the
  // upper side catches a surface pushed through the sand, the lower side catches a fixture that
  // never reached the breaking band at all and therefore proved nothing.
  let maxRatio = 0, ratioDepth = -1
  for (let j = 1; j < DEPTH_SAMPLES; j++) {
    const r = sea[j].totalM / depths[j]
    if (r > maxRatio) { maxRatio = r; ratioDepth = depths[j] }
  }
  check('the water surface never reaches the bed, and the breaking band was reached',
    maxRatio <= BREAK * (1 + 1e-12) && maxRatio >= BREAK * (1 - 1e-12),
    { maxRatio, breakRatio: BREAK, ratioDepth })

  // CHOP DIES BEFORE THE SWELL DOES — the story's "faster chop suppression near shore". Chop is paid
  // out of what is left of the depth budget once the swell has taken its share, so through the whole
  // breaking band the allowance is exactly zero while the swell is still at full height.
  let chopZeroDepth = -1, chopZeroIndex = -1, chopFullDeep = sea[DEPTH_SAMPLES - 1].chopM
  for (let j = 1; j < DEPTH_SAMPLES; j++) if (sea[j].chopM === 0) { chopZeroDepth = depths[j]; chopZeroIndex = j }
  // There may be NO chop-free band — that is precisely what `chop-ignores-swell` produces — so this
  // has to report a missing band as a failed measurement rather than indexing off the front of the
  // array and killing the run. A probe that crashes names no gate and proves nothing.
  const swellAtChopZero = chopZeroIndex > 0 ? sea[chopZeroIndex].swellM : 0
  check('chop reaches exactly zero well offshore of the waterline, while the swell is still full',
    chopZeroDepth > 1 && swellAtChopZero > 0 && chopFullDeep === CHOP_M,
    { chopZeroDepth, swellAtChopZero, chopFullDeep })
  // ...and it is monotone in the sense that matters: no sample seaward of the surf band is dry of
  // chop while a shallower one carries it.
  let chopOutOfOrder = 0
  for (let j = 1; j < DEPTH_SAMPLES; j++) if (sea[j].chopM === 0 && depths[j] > chopZeroDepth) chopOutOfOrder++
  check('the chop-free band is a single band against the shore', chopOutOfOrder === 0, { chopOutOfOrder })

  // LAKE vs OCEAN, the acceptance clause. In deep water neither is clamped and neither is shoaling,
  // so the ratio is the sqrt(fetch) law EXACTLY and nothing else.
  const fetchRatio = Math.sqrt(M.BODY_FETCH_M.lake / M.BODY_FETCH_M.ocean)
  const deepRatio = lakeD[DEPTH_SAMPLES - 1].swellM / sea[DEPTH_SAMPLES - 1].swellM
  check('a lake carries exactly the sqrt(fetch) fraction of the same ocean preset',
    Math.abs(deepRatio - Math.sqrt(0.004)) < 1e-15 && Math.abs(fetchRatio - Math.sqrt(0.004)) < 1e-15,
    { deepRatio, fetchRatio, closed: Math.sqrt(0.004) })
  let lakeAbove = 0, lakeStrictlyBelow = 0, deepEnough = 0
  for (let j = 1; j < DEPTH_SAMPLES; j++) {
    if (lakeD[j].swellM > sea[j].swellM) lakeAbove++
    if (depths[j] >= 1) { deepEnough++; if (lakeD[j].swellM < sea[j].swellM) lakeStrictlyBelow++ }
  }
  check('lake amplitude is never above and always below the same ocean preset',
    lakeAbove === 0 && deepEnough > 0 && lakeStrictlyBelow === deepEnough,
    { lakeAbove, lakeStrictlyBelow, deepEnough })
  // 2ND PASS — ...AND SO DOES THE CHOP. Everything above measures the SWELL. A lake that swells at
  // the correct sqrt(fetch) fraction and chops like the open ocean satisfies every one of them, and
  // chop is the term a lake is supposed to be made of. Measured: drop the fetch scale from the chop
  // term alone and this ratio goes from 0.063245553203 to exactly 1 while nothing else moves.
  const deepChopRatio = lakeD[DEPTH_SAMPLES - 1].chopM / sea[DEPTH_SAMPLES - 1].chopM
  check('a lake carries the same sqrt(fetch) fraction of the CHOP as of the swell',
    sea[DEPTH_SAMPLES - 1].chopM > 0 && lakeD[DEPTH_SAMPLES - 1].chopM > 0
    && Math.abs(deepChopRatio - Math.sqrt(0.004)) < 1e-15 && Math.abs(deepChopRatio - deepRatio) < 1e-15,
    { deepChopRatio, deepRatio, closed: Math.sqrt(0.004) })

  // A RIVER RECEIVES NOTHING. Not "a little" — exactly zero, at every depth, for both bands.
  let riverNonZero = 0
  for (let j = 0; j < DEPTH_SAMPLES; j++) if (riverD[j].swellM !== 0 || riverD[j].chopM !== 0 || riverD[j].totalM !== 0) riverNonZero++
  check('a river receives exactly zero ambient wave displacement at every depth',
    riverNonZero === 0 && M.BODY_FETCH_M.river === 0 && M.fetchAmplitudeScale('river') === 0,
    { riverNonZero, riverFetch: M.BODY_FETCH_M.river, riverScale: M.fetchAmplitudeScale('river') })

  // ================================================================================================
  // FOAM — three named causes, and it is the MAXIMUM of them
  // ================================================================================================
  const jac = 0.2, dFoam = 3
  const combos = [
    { froude: 0.9, swellM: BREAK * dFoam, jacobian: jac },
    { froude: 0.8, swellM: 0.3, jacobian: jac },
    { froude: 0.2, swellM: 0.9, jacobian: 1 },
    { froude: 1.4, swellM: 0, jacobian: 1 },
  ]
  let foamWorst = 0, foamMax = 0
  for (const c of combos) {
    const want = Math.max(M.rapidFoam(c.froude), M.surfFoam(c.swellM, dFoam), M.crestFoam(c.jacobian))
    const got = M.foamIntensity({ ...c, depthM: dFoam })
    foamWorst = Math.max(foamWorst, Math.abs(got - want))
    foamMax = Math.max(foamMax, got)
  }
  check('foam is exactly the largest of its three causes, never their sum',
    foamWorst === 0 && foamMax <= 1 && foamMax > 0.9, { foamWorst, foamMax })
  // The three causes must each be reachable, or "the maximum of three" is the maximum of one.
  check('all three foam causes are individually reachable',
    M.rapidFoam(1.4) === 1 && M.surfFoam(BREAK * dFoam, dFoam) === 1
    && M.crestFoam(0) === 1 && M.crestFoam(1) === 0 && M.rapidFoam(0) === 0,
    { rapid: M.rapidFoam(1.4), surf: M.surfFoam(BREAK * dFoam, dFoam), crest: M.crestFoam(0) })
  // Ice damps foam by the same factor it damps displacement: a frozen rapid is as still as a frozen
  // lake. Exactly zero at full cover.
  check('ice damps foam by the same factor as displacement, exactly to zero at full cover',
    M.foamIntensity({ froude: 1.4, depthM: dFoam, ice: 1 }) === 0
    && M.foamIntensity({ froude: 1.4, depthM: dFoam, ice: 0.5 }) === 0.5
    && M.iceSuppression(1) === 0 && M.iceSuppression(0) === 1,
    { atFull: M.foamIntensity({ froude: 1.4, depthM: dFoam, ice: 1 }),
      atHalf: M.foamIntensity({ froude: 1.4, depthM: dFoam, ice: 0.5 }) })

  // ================================================================================================
  // OPEN-CHANNEL FLOW — zero gradient is exactly still; constriction and gradient both raise foam
  // ================================================================================================
  const dCh = 1.5
  check('water with no gradient has exactly zero speed, Froude number and rapid foam',
    M.manningVelocity(dCh, 0, { manningN: MANNING_N }) === 0
    && M.froudeNumber(0, dCh) === 0 && M.rapidFoam(0) === 0
    && M.manningVelocity(0, 0.05, { manningN: MANNING_N }) === 0, null)

  // Manning, written out from the fixture rather than read back from the module.
  const manningClosed = (d, s, c) => Math.pow(d, 2 / 3) * Math.sqrt(s) / MANNING_N * c
  const speeds = []
  let gradWorst = 0
  for (let k = 0; k <= 200; k++) {
    const s = k * 1e-4
    const v = M.manningVelocity(dCh, s, { manningN: MANNING_N })
    const want = k === 0 ? 0 : manningClosed(dCh, s, 1)
    gradWorst = Math.max(gradWorst, want > 0 ? Math.abs(v - want) / want : Math.abs(v - want))
    speeds.push(v)
  }
  let gradRise = 0, gradMonotone = true
  for (let k = 1; k < speeds.length; k++) {
    if (speeds[k] < speeds[k - 1]) gradMonotone = false
    if (speeds[k] > speeds[k - 1]) gradRise++
  }
  check('flow speed follows Manning exactly and rises with gradient',
    gradWorst < 1e-12 && gradMonotone && gradRise === 200 && speeds[0] === 0,
    { gradWorst, gradMonotone, gradRise, atZeroGradient: speeds[0] })

  // A NARROWS FOAMS AND A POOL DOES NOT. Constriction multiplies the speed directly (continuity at
  // fixed Q and d), so the Froude number and the rapid foam both rise with it.
  const cs = [], froudes = [], foams = []
  for (let k = 0; k <= 400; k++) {
    const c = k * 0.01
    const v = M.manningVelocity(dCh, 0.002, { manningN: MANNING_N, constriction: c })
    const fr = M.froudeNumber(v, dCh)
    cs.push(c); froudes.push(fr); foams.push(M.rapidFoam(fr))
  }
  let foamRise = 0, foamDrop = 0
  for (let k = 1; k < foams.length; k++) { if (foams[k] > foams[k - 1]) foamRise++; if (foams[k] < foams[k - 1]) foamDrop++ }
  check('a constriction raises the Froude number and the rapid foam, monotonically',
    foams[0] === 0 && foams[100] === 0 && foams[250] === 1 && foamDrop === 0 && foamRise > 50,
    { atZero: foams[0], atOne: foams[100], atTwoAndAHalf: foams[250], foamRise, foamDrop,
      froudeAtOne: froudes[100], froudeAtTwoAndAHalf: froudes[250] })

  // ================================================================================================
  // ICE — continuous in temperature, exactly 1 at the solid point, exactly zero displacement there
  // ================================================================================================
  const temps = [], ices = []
  for (let k = 0; k <= 800; k++) { const t = 2 - k * 0.01; temps.push(t); ices.push(M.iceFraction(t)) }
  let iceJump = 0, iceBack = 0
  for (let k = 1; k < ices.length; k++) {
    iceJump = Math.max(iceJump, Math.abs(ices[k] - ices[k - 1]))
    if (ices[k] < ices[k - 1]) iceBack++
  }
  check('the ice fraction is monotone and exact at both ends of the transition',
    M.iceFraction(2) === 0 && M.iceFraction(0) === 0 && M.iceFraction(-4) === 1 && M.iceFraction(-40) === 1
    && iceBack === 0 && M.iceFraction(-2) > 0.4 && M.iceFraction(-2) < 0.6,
    { at0: M.iceFraction(0), atMinus2: M.iceFraction(-2), atMinus4: M.iceFraction(-4), iceBack })
  // The bound sits between two MEASURED builds: smoothstep over 4 degrees sampled every 0.01 degree
  // steps by at most 1.5*0.0025 = 0.00375 per sample; a threshold steps by exactly 1.
  check('the ice transition is continuous rather than a threshold', iceJump < 0.05, { iceJump })
  // 2ND PASS — THE RAMP'S SHAPE, NOT JUST ITS CONTINUITY. The bound above separates smoothstep from
  // a THRESHOLD, whose step is 1.0. It does not separate it from a LINEAR wedge: measured, a linear
  // ramp over the same four degrees steps 0.0025 per 0.01 degC against smoothstep's 0.00375, and
  // both sail under 0.05. But C1 at the ENDS is the entire stated reason smoothstep was chosen — a
  // linear ramp has a slope discontinuity exactly where the temperature field crosses the threshold,
  // which is a hard line drawn across the ice edge in the one place the transition must be invisible.
  // The end slope over the largest slope is what tells them apart, and both endpoints are measured:
  // the shipped cubic gives 4.9917e-3, the same ramp made linear gives exactly 1.
  const iceEndStep = Math.max(Math.abs(M.iceFraction(-0.01) - M.iceFraction(0)),
    Math.abs(M.iceFraction(M.ICE_SOLID_C) - M.iceFraction(M.ICE_SOLID_C + 0.01)))
  const iceEndRatio = iceJump > 0 ? iceEndStep / iceJump : 1
  check('the phase ramp flattens at BOTH ends — it is C1, not a linear wedge',
    iceJump > 0 && iceEndStep > 0 && iceEndRatio < 0.05,
    { iceEndStep, iceJump, iceEndRatio, cubicMeasured: 4.991708e-3, linearMeasured: 1 })

  const baseAmp = M.regimeAmplitude('ocean', SWELL_M, 20, REF_M, 0)
  let iceAmpWorst = 0, iceAmpBack = 0, prevAmp = Infinity
  for (const ice of ices) {
    const a = M.regimeAmplitude('ocean', SWELL_M, 20, REF_M, ice)
    iceAmpWorst = Math.max(iceAmpWorst, Math.abs(a - baseAmp * (1 - ice)))
    if (a > prevAmp) iceAmpBack++
    prevAmp = a
  }
  check('displacement falls continuously with ice and is EXACTLY zero at full cover',
    baseAmp > 0 && M.regimeAmplitude('ocean', SWELL_M, 20, REF_M, 1) === 0
    && iceAmpWorst < 1e-15 && iceAmpBack === 0,
    { baseAmp, atFullIce: M.regimeAmplitude('ocean', SWELL_M, 20, REF_M, 1), iceAmpWorst, iceAmpBack })

  // THE ACCEPTANCE CLAUSE READ END TO END: ice 0 -> 1 driven by TEMPERATURE, through the classifier,
  // suppresses displacement continuously and exactly at 1. The check above passes the ice fraction in
  // by hand, so it cannot see a phase curve that never quite reaches 1 — this one can.
  const iceOpts = { ampM: SWELL_M, chopAmpM: CHOP_M, refM: REF_M, shoreDepthM: SHORE_DEPTH, standingKind: 'ocean' }
  const iceAmps = temps.map(t => M.classifyCell({ depthM: 20, temperatureC: t }, iceOpts).totalM)
  const openWater = iceAmps[0]
  let tempAmpJump = 0, tempAmpBack = 0, tempAmpFrozen = 0, tempAmpOpen = 0
  for (let k = 0; k < iceAmps.length; k++) {
    if (k > 0) {
      tempAmpJump = Math.max(tempAmpJump, Math.abs(iceAmps[k] - iceAmps[k - 1]))
      if (iceAmps[k] > iceAmps[k - 1]) tempAmpBack++
    }
    if (temps[k] <= M.ICE_SOLID_C) { if (iceAmps[k] === 0) tempAmpFrozen++ }
    else if (temps[k] >= M.ICE_ONSET_C && iceAmps[k] === openWater) tempAmpOpen++
  }
  const frozenSamples = temps.filter(t => t <= M.ICE_SOLID_C).length
  const openSamples = temps.filter(t => t >= M.ICE_ONSET_C).length
  check('a falling temperature suppresses displacement continuously and to EXACTLY zero at the solid point',
    openWater > 0 && frozenSamples > 0 && openSamples > 0
    && tempAmpFrozen === frozenSamples && tempAmpOpen === openSamples
    && tempAmpBack === 0 && tempAmpJump < openWater * 0.05,
    { openWater, frozenSamples, tempAmpFrozen, openSamples, tempAmpOpen, tempAmpBack,
      tempAmpJump, continuityBound: openWater * 0.05 })

  // ================================================================================================
  // RIVER SURFACE — advected detail bands
  // ================================================================================================
  const PX = 37.5, PZ = -12.25, T = 3, V = 2
  // TRAVEL IS MEASURED AGAINST EACH FIELD'S OWN t=0, and that distinction is not pedantry: the
  // band's phase offset is carried ALONG the flow too, so a reversed field starts from a different
  // place. Differencing the reversed sample against the forward field's t=0 mixes the offset into
  // the travel and reports -2.58 against +5.762 for band 1 — which is what this oracle did on its
  // first run, and it was the oracle that was wrong, not the module.
  for (const band of [0, 1]) {
    const fwd0 = M.riverAdvect(PX, PZ, 0, 1, 0, V, band)
    const fwd = M.riverAdvect(PX, PZ, T, 1, 0, V, band)
    const rev0 = M.riverAdvect(PX, PZ, 0, -1, 0, V, band)
    const rev = M.riverAdvect(PX, PZ, T, -1, 0, V, band)
    const scale = M.RIVER_DETAIL_BANDS[band].scale
    const dFwd = fwd.u - fwd0.u, dRev = rev.u - rev0.u
    check(`band ${band}: reversing the flow field exactly reverses the phase travel`,
      dFwd === -dRev && Math.abs(dFwd + V * T * scale) < 1e-12 && dFwd !== 0,
      { dFwd, dRev, closed: -V * T * scale })
  }
  // Zero speed is a STATIC pattern, bit-identical across a thousand seconds. Not "slow".
  const still0 = M.riverAdvect(PX, PZ, 0, 1, 0, 0, 0)
  const still1 = M.riverAdvect(PX, PZ, 1000, 1, 0, 0, 0)
  check('zero flow speed leaves the river pattern bit-identical across 1000 seconds',
    still0.u === still1.u && still0.v === still1.v, { still0, still1 })
  // A diagonal flow must carry the pattern equally on both axes; advecting along a fixed axis does
  // not, and a straight reach is exactly where that is invisible.
  const diag0 = M.riverAdvect(0, 0, 0, 1, 1, V, 0)
  const diag = M.riverAdvect(0, 0, T, 1, 1, V, 0)
  check('a diagonal flow advects the pattern equally on both axes',
    (diag.u - diag0.u) === (diag.v - diag0.v) && (diag.u - diag0.u) !== 0,
    { du: diag.u - diag0.u, dv: diag.v - diag0.v })
  // The two bands must not travel together, or they re-synchronise into one pattern.
  check('the two detail bands are distinct in scale and offset',
    M.RIVER_DETAIL_BANDS.length === 2
    && M.RIVER_DETAIL_BANDS[0].scale !== M.RIVER_DETAIL_BANDS[1].scale
    && M.RIVER_DETAIL_BANDS[0].offsetM !== M.RIVER_DETAIL_BANDS[1].offsetM, null)

  // Calm / ripple / turbulent, as a partition of unity.
  let wSumWorst = 0, wNegative = 0, wSamples = 0
  for (let k = 0; k <= 200; k++) {
    const fr = k * 0.01
    const w = M.riverSurfaceWeights(fr)
    wSumWorst = Math.max(wSumWorst, Math.abs(w.calm + w.ripple + w.turbulent - 1))
    if (w.calm < -1e-15 || w.ripple < -1e-15 || w.turbulent < -1e-15) wNegative++
    wSamples++
  }
  const glass = M.riverSurfaceWeights(0), white = M.riverSurfaceWeights(1.2)
  check('the calm/ripple/turbulent weights are a partition of unity over the whole Froude range',
    wSamples === 201 && wSumWorst < 1e-15 && wNegative === 0
    && glass.calm === 1 && glass.turbulent === 0 && white.turbulent === 1 && white.calm === 0,
    { wSumWorst, wNegative, glass, white })

  // ================================================================================================
  // FOAM PERSISTENCE — decay in TIME, not per frame
  // ================================================================================================
  const TAU = M.FOAM_DECAY_SECONDS
  const oneStep = M.foamPersistence(1, 0, 1)
  let manySteps = 1
  for (let k = 0; k < 10; k++) manySteps = M.foamPersistence(manySteps, 0, 0.1)
  check('foam decay is frame-rate independent: ten steps of 0.1 s land where one step of 1 s does',
    Math.abs(oneStep - manySteps) < 1e-12 && Math.abs(oneStep - Math.exp(-1 / TAU)) < 1e-15
    && oneStep > 0.5 && oneStep < 0.7,
    { oneStep, manySteps, closed: Math.exp(-1 / TAU), tau: TAU })
  check('new foam appears instantly and old foam decays to nothing',
    M.foamPersistence(0, 1, 10) === 1 && M.foamPersistence(1, 0, 0) === 1
    && M.foamPersistence(1, 0, 5 * TAU) < 0.01 && M.foamPersistence(1, 0, 5 * TAU) > 0,
    { instant: M.foamPersistence(0, 1, 10), after5Tau: M.foamPersistence(1, 0, 5 * TAU) })
  // 2ND PASS — BOTH TERMS LIVE AT ONCE, which is the only case that distinguishes MAX from SUM.
  // Every persistence call above has either no new foam or no surviving foam, and max and sum agree
  // identically whenever one of them is zero — so the choice between them, which is the whole design
  // of the function, was tested by none of them. A wake trailing a boat is exactly the case where
  // both are live. Measured: max 0.8561064820506427, sum 1.6561064820506428 — foam above 1, which is
  // out of range for a mask port and reads as a solid white river.
  const survivingA = 0.9 * Math.exp(-0.1 / TAU), survivingB = 0.6 * Math.exp(-0.05 / TAU)
  const bothLive = M.foamPersistence(0.9, 0.8, 0.1)
  check('persistence takes the MAX of new and surviving foam, never their sum, and stays inside [0,1]',
    survivingA > 0.8 && bothLive === Math.max(0.8, survivingA)
    && M.foamPersistence(0.6, 0.5, 0.05) === Math.max(0.5, survivingB) && bothLive <= 1,
    { bothLive, max: Math.max(0.8, survivingA), sumWouldBe: 0.8 + survivingA })

  // ================================================================================================
  // THE PARTITION — six analytic bands, one regime each, counts known before the module runs
  // ================================================================================================
  const fields = {
    depthM: gridField('depth'), dischargeM3S: gridField('q'),
    temperatureC: gridField('temp'), slope: gridField('slope'),
  }
  const opts = {
    manningN: MANNING_N, channelFormingQM3S: CHANNEL_Q, shoreDepthM: SHORE_DEPTH, refM: REF_M,
    standingKind: 'lake', ampM: SWELL_M, chopAmpM: CHOP_M,
  }
  const masks = M.regimeMasks(fields, N, opts)
  const cls = masks.classified

  const wantCounts = { dry: 0, ice: 0, foam: 0, river: 0, shore: 0, lake: 0 }
  for (const b of BANDS) wantCounts[b.name] += (b.y1 - b.y0) * W
  const countsMatch = M.REGIME_NAMES.concat(['dry']).every(k => cls.counts[k] === wantCounts[k])
  const allPopulated = M.REGIME_NAMES.every(k => cls.counts[k] > 0)
  check('every regime is populated and every count matches the constructed fixture',
    countsMatch && allPopulated && cls.wet === N - wantCounts.dry && cls.N === N,
    { got: cls.counts, want: wantCounts, wet: cls.wet })

  // MUTUALLY EXCLUSIVE AND EXHAUSTIVE. The masks must sum to exactly 1 on every wet sample and
  // exactly 0 on every dry one — no tolerance, because a cell shaded twice sums to 2.
  let notOneHot = 0, dryNotZero = 0, wetSeen = 0
  for (let i = 0; i < N; i++) {
    let s = 0
    for (const name of M.REGIME_NAMES) s += masks[name][i]
    if (fields.depthM[i] > 0) { wetSeen++; if (s !== 1) notOneHot++ } else if (s !== 0) dryNotZero++
  }
  check('the five regime masks are mutually exclusive and exhaustive over wet samples',
    wetSeen === N - wantCounts.dry && notOneHot === 0 && dryNotZero === 0,
    { wetSeen, notOneHot, dryNotZero })
  // ...and the sum of the six counts must be the whole field, or a sample fell out of the partition.
  const total = Object.values(cls.counts).reduce((a, b) => a + b, 0)
  check('the six counts account for every sample in the field', total === N, { total, N })

  // NO SWELL ON RUNNING WATER, AND NONE UNDER ICE. Exactly zero, counted.
  let zeroSwell = 0, zeroFoam = 0, zeroSpeed = 0
  for (let i = 0; i < N; i++) {
    if (cls.swell[i] === 0 && cls.chop[i] === 0) zeroSwell++
    if (cls.foam[i] === 0) zeroFoam++
    if (cls.speed[i] === 0) zeroSpeed++
  }
  // river + rapids + ice + dry = 512*4. The two standing bands must NOT be in there, or the fixture
  // proves zero by having no waves anywhere.
  check('swell and chop are exactly zero on rivers, rapids, ice and dry ground — and nowhere else',
    zeroSwell === 2048 && cls.swell[0] > 0 && cls.swell[16 * W] > 0,
    { zeroSwell, lakeSwell: cls.swell[0], shoreSwell: cls.swell[16 * W] })
  // river + ice + dry = 512*3 carry exactly zero foam. A river has no surf because it has no swell,
  // no rapid foam because it is subcritical, and no crest foam because it is not folded.
  check('foam is exactly zero on subcritical rivers, ice and dry ground — and nowhere else',
    zeroFoam === 1536 && cls.foam[40 * W] === 1 && cls.foam[0] > 0 && cls.foam[16 * W] > 0,
    { zeroFoam, rapidFoam: cls.foam[40 * W], lakeFoam: cls.foam[0], shoreFoam: cls.foam[16 * W] })
  check('speed is exactly zero wherever the fixture has no gradient',
    zeroSpeed === 3072, { zeroSpeed })

  // The two flowing bands, against Manning and Froude written out from the fixture.
  const vRiver = manningClosed(1.5, 0.001, 1), vRapid = manningClosed(1.5, 0.05, 1)
  const frRiver = vRiver / Math.sqrt(WAVES.GRAVITY * 1.5), frRapid = vRapid / Math.sqrt(WAVES.GRAVITY * 1.5)
  check('the two flowing bands match the closed-form speed and Froude number',
    Math.abs(cls.speed[32 * W] - vRiver) / vRiver < 1e-12
    && Math.abs(cls.speed[40 * W] - vRapid) / vRapid < 1e-12
    && Math.abs(cls.froude[32 * W] - frRiver) / frRiver < 1e-12
    && frRiver < M.FOAM_FROUDE_ONSET && frRapid > M.FOAM_FROUDE_FULL,
    { vRiver, vRapid, frRiver, frRapid, gotRiver: cls.speed[32 * W], gotRapid: cls.speed[40 * W] })
  // The regime split between them is the Froude number and nothing else: same depth, same discharge,
  // same temperature, different gradient.
  check('subcritical and supercritical water of the same depth land in different regimes',
    cls.regime[32 * W] === M.REGIME.RIVER && cls.regime[40 * W] === M.REGIME.FOAM
    && cls.regime[0] === M.REGIME.LAKE && cls.regime[16 * W] === M.REGIME.SHORE
    && cls.regime[48 * W] === M.REGIME.ICE && cls.regime[56 * W] === M.REGIME.DRY, null)
  // The body kind follows the REGIME, which is what makes "no ocean waves on rivers" structural.
  check('running water is classified as a river body whatever its surface is doing',
    M.bodyKindFor(M.REGIME.RIVER) === 'river' && M.bodyKindFor(M.REGIME.FOAM) === 'river'
    && M.bodyKindFor(M.REGIME.LAKE) === 'lake' && M.bodyKindFor(M.REGIME.SHORE, { standingKind: 'ocean' }) === 'ocean'
    && M.bodyKindFor(M.REGIME.DRY) === null, null)
  // Displacement must never put the surface through the bed on ANY classified cell either.
  let throughBed = 0
  for (let i = 0; i < N; i++) if (fields.depthM[i] > 0 && cls.total[i] > BREAK * fields.depthM[i] * (1 + 1e-12)) throughBed++
  check('no classified sample displaces the surface past its own breaking limit', throughBed === 0, { throughBed })

  // ================================================================================================
  // 2ND PASS — THE MIDDLE OF EVERY QUANTITY THE GRID ONLY VISITS THE ENDS OF
  //
  // Every ice cell in the grid is exactly 1 frozen and every other cell exactly 0. Every flowing
  // cell is exactly 0 or exactly 1 aerated. Every depth is 2 or 20 against a shore depth of 12.
  // That is why the five defects below were all invisible: each lives strictly between two ends the
  // fixture never samples. Each check names the two measured builds its bound sits between.
  // ================================================================================================

  // ONLY FULL COVER CLAIMS THE ICE REGIME. A lake at 99.9% ice is still a lake whose motion is
  // damped; firing the regime on ANY ice snaps a whole basin to solid mirror the instant a
  // temperature field dips below zero — which is precisely the snap the smooth ramp exists to
  // prevent, arriving one line further down. Measured: at -3.9265 degC the fraction is 0.99900 and
  // the regime is LAKE; at exactly -4 it is 1 and the regime is ICE. Fire it on any ice at all and
  // the first of those becomes ICE while all six grid counts stay identical.
  const barelyCold = M.classifyCell({ depthM: 20, temperatureC: -0.0735 }, opts)
  const nearlyFrozen = M.classifyCell({ depthM: 20, temperatureC: -3.9265 }, opts)
  const fullyFrozen = M.classifyCell({ depthM: 20, temperatureC: M.ICE_SOLID_C }, opts)
  check('only FULL ice cover claims the ice regime — a 99.9% frozen lake is still a lake',
    barelyCold.ice > 0 && barelyCold.ice < 0.01 && barelyCold.regime === M.REGIME.LAKE
    && nearlyFrozen.ice > 0.99 && nearlyFrozen.ice < 1 && nearlyFrozen.regime === M.REGIME.LAKE
    && fullyFrozen.ice === 1 && fullyFrozen.regime === M.REGIME.ICE,
    { barelyIce: barelyCold.ice, barelyRegime: barelyCold.regime, nearlyIce: nearlyFrozen.ice,
      nearlyRegime: nearlyFrozen.regime, fullRegime: fullyFrozen.regime })

  // FOAM IS DAMPED BY ICE EXACTLY ONCE. `foamIntensity` applies the suppression itself, so the swell
  // handed to it must be the PRE-ice amplitude; handing it the post-ice swell damps the surf twice
  // and a half-frozen shore goes quietly grey. Nothing above can see it, because at full ice both
  // spellings give exactly zero and the grid has no other kind of ice cell. Measured: shore foam
  // 0.0951775385353801 open and 0.04758876926769005 at half cover — EXACTLY half. Damped twice it is
  // 0.023794384633845023, exactly a quarter, and the ratio below moves from 0.5 to 0.25.
  const shoreOpen = M.classifyCell({ depthM: 2, temperatureC: 20 }, opts)
  const shoreHalfIce = M.classifyCell({ depthM: 2, temperatureC: -2 }, opts)
  check('foam under PARTIAL ice is damped exactly once — a half-frozen shore keeps half its surf',
    shoreOpen.foam > 0 && shoreOpen.regime === M.REGIME.SHORE && shoreHalfIce.ice === 0.5
    && shoreHalfIce.foam === shoreOpen.foam * 0.5,
    { open: shoreOpen.foam, half: shoreHalfIce.foam, ratio: shoreHalfIce.foam / shoreOpen.foam })

  // THE RAPIDS THRESHOLD, TESTED WHERE IT BINDS. Every flowing cell in the grid has an aeration
  // fraction of exactly 0 (Fr 0.309) or exactly 1 (Fr 2.183), so FOAM_REGIME_MIN is constrained by
  // nothing whatever: measured, ANY value in (0, 1] leaves all six counts byte-identical. These two
  // cells straddle it, and their gradients are SOLVED from the target Froude number rather than
  // chosen, so the fixture stays analytic. Measured: Fr 0.70 gives aeration 0.15625 and must stay a
  // RIVER — a rippled reach is not whitewater; Fr 0.95 gives 0.95703 and must be a RAPID. Collapse
  // the threshold to 0.02 and the first becomes a rapid; run it out to 0.99 and the second stays a
  // river. Both directions are armed.
  const slopeForFroude = (fr, d) => Math.pow(fr * Math.sqrt(WAVES.GRAVITY * d) * MANNING_N / Math.pow(d, 2 / 3), 2)
  const lightlyAerated = M.classifyCell({ depthM: 1.5, dischargeM3S: 5, slope: slopeForFroude(0.70, 1.5) }, opts)
  const heavilyAerated = M.classifyCell({ depthM: 1.5, dischargeM3S: 5, slope: slopeForFroude(0.95, 1.5) }, opts)
  const lightAeration = M.rapidFoam(lightlyAerated.froude), heavyAeration = M.rapidFoam(heavilyAerated.froude)
  check('the rapids threshold binds: a lightly aerated river is a river, a heavily aerated one is a rapid',
    Math.abs(lightlyAerated.froude - 0.70) < 1e-12 && Math.abs(heavilyAerated.froude - 0.95) < 1e-12
    && lightAeration > 0.05 && lightAeration < 0.45 && heavyAeration > 0.55 && heavyAeration <= 1
    && lightlyAerated.regime === M.REGIME.RIVER && heavilyAerated.regime === M.REGIME.FOAM,
    { lightFr: lightlyAerated.froude, lightAeration, lightRegime: lightlyAerated.regime,
      heavyFr: heavilyAerated.froude, heavyAeration, heavyRegime: heavilyAerated.regime })

  // THE TWO AUTHORED THRESHOLDS ARE REACHED, NOT EXCEEDED. The grid's depths are 2 and 20 against a
  // shore depth of 12 and its discharges are 0 and 5 against a channel-forming 0.1, so both
  // comparisons could be strict or not and not one count would move. Water exactly AT the reference
  // depth is a LAKE, and that is not a convention: it is the depth where `shoalAmplitude`'s gain is
  // exactly 1, i.e. where the bottom is not yet felt. Measured: 11.999 m -> shore, 12 m -> lake;
  // 0.0999 m3/s -> shore, 0.1 -> river.
  check('the shore band stops short of the reference depth: water exactly at it is a lake',
    M.classifyCell({ depthM: SHORE_DEPTH - 0.001 }, opts).regime === M.REGIME.SHORE
    && M.classifyCell({ depthM: SHORE_DEPTH }, opts).regime === M.REGIME.LAKE
    && M.shoreDepth(opts) === SHORE_DEPTH,
    { justUnder: M.classifyCell({ depthM: SHORE_DEPTH - 0.001 }, opts).regime,
      exactly: M.classifyCell({ depthM: SHORE_DEPTH }, opts).regime })
  check('discharge that REACHES the channel-forming value is a river, not merely discharge above it',
    M.classifyCell({ depthM: 1.5, dischargeM3S: CHANNEL_Q * 0.999 }, opts).regime === M.REGIME.SHORE
    && M.classifyCell({ depthM: 1.5, dischargeM3S: CHANNEL_Q }, opts).regime === M.REGIME.RIVER
    && M.channelFormingQ(opts) === CHANNEL_Q,
    { justUnder: M.classifyCell({ depthM: 1.5, dischargeM3S: CHANNEL_Q * 0.999 }, opts).regime,
      exactly: M.classifyCell({ depthM: 1.5, dischargeM3S: CHANNEL_Q }, opts).regime })

  // AN OMITTED FIELD IS OPEN WATER, NOT ICE. `classifyRegimes` fills an absent temperature from a
  // default, and that default is the single number deciding what an UNWIRED Temperature port does to
  // a domain. Every fixture above supplies the raster, so the default was reached by nothing.
  // Measured: omitted -> ice 0 and 8 lake cells; a default of -10 degC -> ice 1 and 8 ice cells.
  const noTemp = M.classifyRegimes({ depthM: Float64Array.from({ length: 8 }, () => 20) }, 8, opts)
  check('an omitted temperature raster is open water, not ice',
    noTemp.counts.lake === 8 && noTemp.counts.ice === 0 && noTemp.ice[0] === 0 && noTemp.wet === 8,
    { counts: noTemp.counts, ice0: noTemp.ice[0] })

  // A SHORT RASTER IS REFUSED, not read as zeros. Half a domain silently classified as dry is the
  // doctrine's "framebuffer read zeros" — red, not green.
  let threwShort = false, threwEmpty = false
  try { M.classifyRegimes({ depthM: new Float64Array(N - 1) }, N, opts) } catch (_) { threwShort = true }
  try { M.classifyRegimes({ depthM: new Float64Array(4) }, 0, opts) } catch (_) { threwEmpty = true }
  check('a raster shorter than the field, and a field of nothing, are both refused',
    threwShort && threwEmpty, { threwShort, threwEmpty })

  // ================================================================================================
  // THE NODE — loaded with legacy stubbed, against the SAME core this run is measuring
  // ================================================================================================
  const pluginPath = path.resolve(__dirname, '../../src/plugins/data/water_regimes.js')
  const coreDir = p => pathToFileURL(path.resolve(__dirname, '../../src/core/' + p)).href
  const legacyStub = dataUrl(
    `export const newField=()=>new Float32Array(${N});export const fieldW=()=>${W};export const fieldH=()=>${H};`
    + `export const cellSizeM=()=>10;export const isHex=()=>false;`)
  let pluginText = patchText(fs.readFileSync(pluginPath, 'utf8'),
    (mutation && PLUGIN_PATCHES[mutation]) || null, 'plugin')
  const rewrites = [
    ["'../../core/registry.js'", JSON.stringify(coreDir('registry.js'))],
    ["'../../core/params.js'", JSON.stringify(coreDir('params.js'))],
    ["'../../core/water-regimes.js'", JSON.stringify(coreHref)],
    ["'../../legacy.js'", JSON.stringify(legacyStub)],
  ]
  for (const [from, to] of rewrites) {
    if (pluginText.split(from).length - 1 !== 1) { console.error(`FATAL plugin import rewrite ${from} did not match exactly once`); process.exit(2) }
    pluginText = pluginText.replace(from, to)
  }
  const PORTS = await import(coreDir('ports.js'))
  const def = (await import(dataUrl(pluginText))).default

  const portProblems = PORTS.validatePortList({ inputs: def.inputs, outputs: def.outputs, source: 'declared' })
  check("the node's declared ports validate against the S2.1 vocabulary",
    portProblems.length === 0 && def.inputs.length === 5 && def.outputs.length === 8,
    { problems: portProblems, inputs: def.inputs.length, outputs: def.outputs.length })

  const depthIn = Float32Array.from(fields.depthM)
  const before = Float32Array.from(depthIn)
  const dirIn = new Float32Array(N * 3)
  for (let i = 0; i < N; i++) { dirIn[i * 3] = 1; dirIn[i * 3 + 2] = 0 }
  const nodeOut = def.eval({
    manningN: MANNING_N, channelQ: CHANNEL_Q, shoreDepth: SHORE_DEPTH,
    standing: 'lake', swellM: SWELL_M, chopM: CHOP_M,
  }, [depthIn, Float32Array.from(fields.dischargeM3S), Float32Array.from(fields.temperatureC),
    Float32Array.from(fields.slope), dirIn], null, null)

  // GUARDRAIL 1, at the node boundary: no height port declared, no height value returned, and the
  // depth handed in comes back by identity and bitwise unchanged.
  const heightish = k => /height/i.test(String(k))
  let depthTouched = 0
  for (let i = 0; i < N; i++) if (depthIn[i] !== before[i]) depthTouched++
  check('the water-family node declares no terrain-height output, returns none, and moves no sample',
    def.outputs.every(o => !heightish(o.id) && !heightish(o.semantic))
    && ![...nodeOut.values.keys()].some(heightish)
    && nodeOut.values.get('waterDepth') === depthIn && depthTouched === 0,
    { outputs: def.outputs.map(o => o.id), values: [...nodeOut.values.keys()], depthTouched })

  // The node's masks must BE the core's classification, and they must be one-hot in their own right.
  const portFor = { ice: 'ice', foam: 'rapids', river: 'river', shore: 'shore', lake: 'lake' }
  let nodeMismatch = 0, nodeNotOneHot = 0, nodeOnes = 0
  for (let i = 0; i < N; i++) {
    let s = 0
    for (const name of M.REGIME_NAMES) {
      const v = nodeOut.values.get(portFor[name])[i]
      if (v !== masks[name][i]) nodeMismatch++
      s += v
    }
    if (s !== (fields.depthM[i] > 0 ? 1 : 0)) nodeNotOneHot++
    nodeOnes += s
  }
  check("the node's five masks are the core classification, one-hot on every wet sample",
    nodeMismatch === 0 && nodeNotOneHot === 0 && nodeOnes === N - wantCounts.dry,
    { nodeMismatch, nodeNotOneHot, nodeOnes })

  const nodeFoam = nodeOut.values.get('foam')
  let foamDiff = 0, foamNonZero = 0
  for (let i = 0; i < N; i++) {
    if (nodeFoam[i] !== Math.fround(cls.foam[i])) foamDiff++
    if (nodeFoam[i] !== 0) foamNonZero++
  }
  check("the node's foam field is the core's causal foam, and it is not empty",
    foamDiff === 0 && foamNonZero === N - 1536, { foamDiff, foamNonZero, expected: N - 1536 })

  // Velocity: direction from the wired field, magnitude from Manning. Exactly zero where the water
  // is standing, so a lake never advects a river band across itself.
  const vel = nodeOut.values.get('velocity')
  let velWorst = 0, velMoving = 0, velStandingNonZero = 0
  for (let i = 0; i < N; i++) {
    const mag = Math.hypot(vel[i * 3], vel[i * 3 + 2])
    if (cls.speed[i] > 0) { velMoving++; velWorst = Math.max(velWorst, Math.abs(mag - cls.speed[i]) / cls.speed[i]) }
    else if (mag !== 0) velStandingNonZero++
    if (vel[i * 3 + 1] !== 0) velStandingNonZero++
  }
  check('the node emits a horizontal velocity of the Manning magnitude, exactly zero on still water',
    velMoving === 1024 && velWorst < 1e-6 && velStandingNonZero === 0,
    { velMoving, velWorst, velStandingNonZero })

  check('assertion inventory non-empty', assertions.length >= 30, assertions.length)

  // The readings this gate turns on, printed so a reviewer can see the fixture actually produced
  // them. Every one of them is asserted above; none is diagnostic-only.
  console.log('READINGS ' + JSON.stringify({
    deepSwellM: +deepSwell.toFixed(6), maxSwellM: +maxSwell.toFixed(6), maxSwellDepthM: maxSwellDepth,
    maxTotalOverDepth: +maxRatio.toFixed(12), breakRatio: BREAK, atDepthM: ratioDepth,
    chopZeroDepthM: chopZeroDepth, swellThereM: +swellAtChopZero.toFixed(6), chopDeepM: chopFullDeep,
    lakeOverOcean: +deepRatio.toFixed(12), iceMaxStep: +iceJump.toFixed(8),
    vRiverMps: +vRiver.toFixed(6), vRapidMps: +vRapid.toFixed(6),
    frRiver: +frRiver.toFixed(6), frRapid: +frRapid.toFixed(6),
    counts: cls.counts, wet: cls.wet, zeroSwellCells: zeroSwell, zeroFoamCells: zeroFoam,
    foamDecay1s: +oneStep.toFixed(12), foamDecay10x100ms: +manySteps.toFixed(12),
    // 2ND PASS readings. Every one is asserted above; none is diagnostic-only.
    lakeChopOverOcean: +deepChopRatio.toFixed(12), iceEndSlopeRatio: +iceEndRatio.toFixed(9),
    nearlyFrozenIce: +nearlyFrozen.ice.toFixed(9), nearlyFrozenRegime: nearlyFrozen.regime,
    shoreFoamOpen: +shoreOpen.foam.toFixed(12), shoreFoamHalfIce: +shoreHalfIce.foam.toFixed(12),
    lightAeration: +lightAeration.toFixed(9), lightRegime: lightlyAerated.regime,
    heavyAeration: +heavyAeration.toFixed(9), heavyRegime: heavilyAerated.regime,
    foamPersistBothLive: +bothLive.toFixed(12), foamPersistSumWouldBe: +(0.8 + survivingA).toFixed(12),
  }))
  report()

  function report() {
    let ok = assertions.every(a => a.ok)
    if (mutation) {
      if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
      ok = false
    }
    const failed = assertions.filter(a => !a.ok).map(a => a.name)
    console.log(`${ok ? 'PASS' : 'FAIL'}  water regimes assertions=${assertions.length} `
      + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
    if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify(assertions.filter(a => !a.ok), null, 2))
    process.exit(ok ? 0 : 1)
  }
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
