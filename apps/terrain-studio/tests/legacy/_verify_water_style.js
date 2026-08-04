// W19 — does the stylised look actually quantise, and does the realistic one actually not?
//
// The two looks are one shader path graded by uniforms, which is the maintainable choice but also
// the one where "the toggle does nothing" is easiest to ship unnoticed: no compile error, no missing
// symbol, just a uniform nothing reads. So the gate measures the PIXELS, and measures the property
// that distinguishes the looks rather than merely that they differ.
//
// THE METRIC IS FLATNESS, NOT DIFFERENCE. Two images differ for a thousand reasons. Posterisation
// has one signature: across a depth gradient, adjacent pixels sit at the SAME value inside a band
// and jump at the seam. So the fraction of adjacent water-pixel pairs that are flat (|delta| below
// a fraction of a luminance count) rises sharply under quantisation, while a continuous gradient
// keeps changing by a small amount everywhere.
//
// Both endpoints are measured in the same run, on the same frame, with only the look switched --
// so the comparison is not against a threshold chosen in advance.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:/Program Files/Google/Chrome/Application/chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'style-ignored',      // the look uniform is never switched, so both frames are the realistic one
  'no-water-in-frame',  // no water, so flatness is measured over terrain and means nothing
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

;(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 900, height: 560 } })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1600)

  const setup = await page.evaluate(mut => {
    USE_GPU = true
    nodes.length = 0; edges.length = 0; uid = 1; selected = null
    const gen = makeNode('perlin', 60, 60)
    const wat = makeNode('water', 380, 60)
    const out = makeNode('output', 700, 60)
    edges.push({ from: gen.id, to: wat.id, slot: 0 }, { from: wat.id, to: out.id, slot: 0 })
    // Liquid, not ice: a frozen sea has no depth ramp to band and the whole measurement is void.
    terrainDef.baseElevation = 0
    terrainDef.seaTemp = 22
    wat.params.mode = 'sea'
    wat.params.level = mut === 'no-water-in-frame' ? 0 : 0.80
    select(out)
    previewMode = 'output'
    nodes.forEach(n => { n._dirty = true })
    evalGraph()
    // Looking across open water so a long, smooth depth gradient fills the frame — that gradient is
    // the thing banding acts on, and without it both looks would measure the same.
    cam.target = [0.5, 0.30, 0.5]; cam.dist = 1.15; cam.pitch = 0.20; cam.yaw = 0.4
    if (typeof AUTO !== 'undefined' && AUTO) { AUTO = false }
    uTime = 3.5
    // The ripple is turned OFF. It adds high-frequency variation to every pixel, which destroys
    // flatness inside a band and would mask the very signature under test.
    waterLook.strength = 0
    waterLook.bandSteps = 5
    return { water: !!scene.water, level: scene.water ? scene.water.level : null }
  }, mutation)
  await page.waitForTimeout(1200)

  const grab = async style => {
    await page.evaluate(st => { waterLook.style = st; uTime = 3.5 }, style)
    await page.waitForTimeout(400)
    return page.evaluate(() => {
      const c = document.querySelector('#gl')
      const g = c.getContext('webgl2') || c.getContext('webgl')
      const w = c.width, h = c.height, px = new Uint8Array(w * h * 4)
      if (typeof renderGL === 'function') renderGL()
      g.readPixels(0, 0, w, h, g.RGBA, g.UNSIGNED_BYTE, px)
      const lum = new Float32Array(w * h)
      for (let i = 0, j = 0; j < w * h; i += 4, j++) lum[j] = 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]
      return { w, h, lum: Array.from(lum) }
    })
  }

  const real = await grab('realistic')
  const toon = await grab(mutation === 'style-ignored' ? 'realistic' : 'toon')
  const drained = await (async () => {
    await page.evaluate(() => { const n = nodes.find(x => x.type === 'water'); n.params.level = 0; n._dirty = true; evalGraph(); uTime = 3.5 })
    await page.waitForTimeout(900)
    return grab('realistic')
  })()

  // Water pixels only, identified by what changed when the water was drained. Measuring flatness
  // over sky or terrain would report whatever those happen to be, not what the look did.
  const { w, h } = real
  const isWater = new Uint8Array(w * h)
  let waterCount = 0
  for (let i = 0; i < w * h; i++) {
    if (Math.abs(real.lum[i] - drained.lum[i]) > 6) { isWater[i] = 1; waterCount++ }
  }

  const flatness = img => {
    let flat = 0, pairs = 0
    for (let y = 0; y < h; y++) {
      for (let x = 0; x + 1 < w; x++) {
        const i = y * w + x
        if (!isWater[i] || !isWater[i + 1]) continue
        pairs++
        if (Math.abs(img.lum[i] - img.lum[i + 1]) < 0.35) flat++
      }
    }
    return pairs ? flat / pairs : null
  }
  const flatReal = flatness(real)
  const flatToon = flatness(toon)

  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }

  // Absence of evidence: no water pixels means every ratio below is computed over nothing.
  check('water pixels were found to measure', waterCount > 8000, { waterCount })
  check('the fixture actually produced water', setup.water === true && setup.level > 0, setup)
  check('both looks produced a measurable surface', flatReal !== null && flatToon !== null,
    { flatReal, flatToon })
  // The realistic look must NOT already be flat, or "the stylised one is flatter" would be trivially
  // satisfied by a broken continuous ramp.
  check('the realistic look is a continuous ramp', flatReal !== null && flatReal < 0.55,
    { flatReal: flatReal === null ? null : +flatReal.toFixed(4) })
  check('the stylised look quantises the depth ramp',
    flatToon !== null && flatReal !== null && flatToon > flatReal * 1.25,
    { flatReal: flatReal === null ? null : +flatReal.toFixed(4),
      flatToon: flatToon === null ? null : +flatToon.toFixed(4) })
  check('no page errors', errors.length === 0, errors)

  let ok = assertions.every(a => a.ok)
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = assertions.filter(a => !a.ok).map(a => a.name)
  console.log(`${ok ? 'PASS' : 'FAIL'}  water style waterPx=${waterCount} `
    + `flatReal=${flatReal === null ? 'n/a' : flatReal.toFixed(4)} `
    + `flatToon=${flatToon === null ? 'n/a' : flatToon.toFixed(4)} `
    + `ratio=${flatReal ? (flatToon / flatReal).toFixed(2) : 'n/a'} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify(assertions.filter(a => !a.ok), null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
