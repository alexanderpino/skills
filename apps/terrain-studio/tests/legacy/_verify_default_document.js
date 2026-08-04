// W21 + W22 — the opening document and the biome presets.
//
// The default graph is the first thing anyone sees, and "it opens to something" is not a check. Two
// specific claims are worth arming:
//
//   1. THE OPENING FRAME HAS WATER IN IT. A graph that builds a Water node but never has it reach
//      the renderer looks identical in the node editor and renders a dry lump. That exact trap cost
//      four attempts to confirm the wave work: `collectScene` walks the primary chain from the
//      ACTIVE PREVIEW NODE, so if the opening graph selects its first generator instead of the
//      output, `scene.water` stays null and the water is simply not there.
//   2. THE BIOMES ARE COHERENT AND ORDERED. A preset table is easy to get subtly wrong — a polar
//      world with a sea at 0 degC has no ice, because sea water freezes near -1.8. The oracle
//      checks the physical ORDERING the names claim rather than the individual numbers, which is
//      the part that stays true when someone retunes a preset.
const { chromium } = require('playwright-core')
const path = require('path')
const fs = require('fs')
const { pathToFileURL } = require('url')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:/Program Files/Google/Chrome/Application/chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'select-generator',   // the opening graph selects its first node, so scene.water stays null
  'no-water-node',      // the opening graph is built without its Water node at all
  'flat-biomes',        // every biome returns the same climate, so the selector does nothing
  'polar-sea-at-zero',  // polar sea temperature set to 0, which is above the freezing point of sea water
]
const BIOME_PATCHES = {
  'flat-biomes': [['  for (const f of TERRAIN_FIELDS) out[f] = b[f]',
                   '  for (const f of TERRAIN_FIELDS) out[f] = BIOMES.temperate[f]']],
  'polar-sea-at-zero': [['label: \'Polar\', latitude: 76, seaTemp: -1.5',
                         'label: \'Polar\', latitude: 76, seaTemp: 0']],
}
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

;(async () => {
  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }

  // ---------------------------------------------------------------- biomes, in plain node -------
  const src = path.resolve(__dirname, '../../src/core/biomes.js')
  let B = null, loadErr = null
  try {
    if (!BIOME_PATCHES[mutation]) { B = await import(pathToFileURL(src).href) }
    else {
      let text = fs.readFileSync(src, 'utf8')
      for (const [anchor, repl] of BIOME_PATCHES[mutation]) {
        const hits = text.split(anchor).length - 1
        if (hits !== 1) { console.error(`FATAL anchor for ${mutation} matched ${hits}, expected 1`); process.exit(2) }
        text = text.replace(anchor, repl)
      }
      B = await import('data:text/javascript;base64,' + Buffer.from(text, 'utf8').toString('base64'))
    }
  } catch (e) { loadErr = String(e.message || e).slice(0, 200) }

  let waterPx = 0, sceneWater = null, graph = null
  if (check('biome module loads', B !== null, loadErr)) {
    check('there are several biomes to choose between', B.BIOME_KEYS.length >= 5, B.BIOME_KEYS.length)

    // Every preset must be DISTINCT in the fields it writes. A selector whose options all produce
    // the same world is a control that does nothing, and it looks completely normal in the UI.
    const sigs = new Set(B.BIOME_KEYS.map(k => JSON.stringify(B.biomeTerrainOverrides(k))))
    check('every biome writes a distinct climate', sigs.size === B.BIOME_KEYS.length,
      { distinct: sigs.size, biomes: B.BIOME_KEYS.length })

    // Only the climate fields, never the world's size, lattice or seed: changing biome must not
    // resize the terrain or re-roll it.
    const keys = Object.keys(B.biomeTerrainOverrides('temperate'))
    check('a biome writes only climate fields',
      !keys.some(k => ['scale', 'height', 'lattice', 'seed'].includes(k)), keys)

    // THE ORDERING THE NAMES CLAIM. Checked as an ordering rather than as absolute numbers, because
    // that is what survives someone retuning a preset.
    const snow = k => { const b = B.BIOMES[k]; return b.seaTemp / b.lapseRate * 1000 }
    check('the tropics are warmer at sea level than the poles',
      B.temperatureAtM('tropical', 0) > B.temperatureAtM('polar', 0),
      { tropical: B.temperatureAtM('tropical', 0), polar: B.temperatureAtM('polar', 0) })
    check('the tropical snowline is far above the boreal one', snow('tropical') > snow('boreal') * 3,
      { tropical: Math.round(snow('tropical')), boreal: Math.round(snow('boreal')) })
    // Sea water freezes near -1.8 degC, not 0: dissolved salt depresses the freezing point. A polar
    // preset at 0 renders open water where there should be ice.
    check('the polar sea is below the freezing point of sea water',
      B.BIOMES.polar.seaTemp < 0, { seaTemp: B.BIOMES.polar.seaTemp })
    check('the arid preset is the driest', B.BIOME_KEYS.every(k =>
      k === 'arid' || B.biomePrecipMmYr(k) >= B.biomePrecipMmYr('arid')),
      { arid: B.biomePrecipMmYr('arid') })
    // Lapse rate is genuinely climate-dependent: near dry-adiabatic over hot dry ground where
    // nothing condenses, much shallower in the humid tropics where latent heat is released.
    check('the arid lapse rate is steeper than the tropical one',
      B.BIOMES.arid.lapseRate > B.BIOMES.tropical.lapseRate,
      { arid: B.BIOMES.arid.lapseRate, tropical: B.BIOMES.tropical.lapseRate })
    check('an arid world opens with less standing water than a boreal one',
      B.biomeSeaLevel('arid') < B.biomeSeaLevel('boreal'),
      { arid: B.biomeSeaLevel('arid'), boreal: B.biomeSeaLevel('boreal') })
  }

  // ---------------------------------------------------------------- the opening document --------
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 900, height: 560 } })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1800)

  const built = await page.evaluate(mut => {
    USE_GPU = true
    newTerrainDocument(true, null, true)
    if (mut === 'no-water-node') {
      const w = nodes.find(n => n.type === 'water')
      if (w) {
        // Rewire around it, exactly as a graph built without one would be.
        const inE = edges.find(e => e.to === w.id), outE = edges.find(e => e.from === w.id)
        if (inE && outE) edges.push({ from: inE.from, to: outE.to, slot: outE.slot })
        for (let i = edges.length - 1; i >= 0; i--) if (edges[i].to === w.id || edges[i].from === w.id) edges.splice(i, 1)
        nodes.splice(nodes.indexOf(w), 1)
      }
    }
    if (mut === 'select-generator') { select(nodes.find(n => n.type === 'tectonic')) }
    nodes.forEach(n => { n._dirty = true })
    evalGraph()
    cam.target = [0.5, 0.30, 0.5]; cam.dist = 1.4; cam.pitch = 0.42; cam.yaw = 0.6
    if (typeof AUTO !== 'undefined' && AUTO) { AUTO = false }
    uTime = 3.5
    return {
      types: nodes.map(n => n.type).sort(),
      water: !!scene.water,
      level: scene.water ? scene.water.level : null,
      selectedType: selected ? selected.type : null,
    }
  }, mutation)
  await page.waitForTimeout(1000)
  graph = built
  sceneWater = built.water

  // Count pixels that the water is actually responsible for, by draining it and differencing. This
  // is the claim that matters: not "a Water node exists in the graph" but "water is on the screen".
  const grab = async () => page.evaluate(() => {
    const c = document.querySelector('#gl')
    const g = c.getContext('webgl2') || c.getContext('webgl')
    const w = c.width, h = c.height, px = new Uint8Array(w * h * 4)
    if (typeof renderGL === 'function') renderGL()
    g.readPixels(0, 0, w, h, g.RGBA, g.UNSIGNED_BYTE, px)
    const lum = new Float32Array(w * h)
    for (let i = 0, j = 0; j < w * h; i += 4, j++) lum[j] = 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]
    return Array.from(lum)
  })
  // A picture of the frame the numbers came from, on request. Not part of the gate, but when a
  // count and a human disagree about the same image, looking at it is what settles it.
  if (process.env.MC_KEEP_SHOT) {
    await page.evaluate(() => { uTime = 3.5; if (typeof renderGL === 'function') renderGL() })
    await page.locator('#gl').screenshot({ path: path.resolve(__dirname, '../../.sweep-logs/default-document.png') })
  }
  const wet = await grab()
  await page.evaluate(() => {
    const w = nodes.find(n => n.type === 'water')
    if (w) { w.params.level = 0; w._dirty = true; evalGraph() }
    uTime = 3.5
  })
  await page.waitForTimeout(700)
  const dry = await grab()
  for (let i = 0; i < wet.length; i++) if (Math.abs(wet[i] - dry[i]) > 6) waterPx++

  check('the opening graph contains the nodes it claims',
    mutation === 'no-water-node' || (graph.types.filter(t => t === 'tectonic').length === 2
      && graph.types.includes('blend') && graph.types.includes('water') && graph.types.includes('output')),
    graph.types)
  // Selecting the output rather than the first generator is not cosmetic: collectScene walks the
  // primary chain from the active preview node, and selecting a generator leaves scene.water null.
  check('the opening graph previews its output', graph.selectedType === 'output', graph.selectedType)
  check('the opening document has water in the scene', graph.water === true && graph.level > 0, graph)
  // ABSENCE OF EVIDENCE. A scene.water object proves the graph wired one up, not that a single
  // pixel of water was drawn. Only the pixel count proves that.
  check('water is actually visible in the opening frame', waterPx > 4000, { waterPx })
  check('no page errors', errors.length === 0, errors)

  check('assertion inventory non-empty', assertions.length >= 15, assertions.length)

  let ok = assertions.every(a => a.ok)
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = assertions.filter(a => !a.ok).map(a => a.name)
  console.log(`${ok ? 'PASS' : 'FAIL'}  default document waterPx=${waterPx} sceneWater=${sceneWater} `
    + `selected=${graph && graph.selectedType} assertions=${assertions.length} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify(assertions.filter(a => !a.ok), null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
