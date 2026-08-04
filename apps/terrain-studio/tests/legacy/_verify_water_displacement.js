// S4.7 / S4.10 — does the water mesh ACTUALLY displace on screen?
//
// _verify_gerstner.js proves the maths and proves both passes were handed one byte-identical
// generated source. Neither is evidence that a single pixel moved. This file is that evidence, and
// it exists because four attempts to confirm it by eye failed for reasons that had nothing to do
// with the waves: a hand-built graph left `scene.water` null because `collectScene` walks from the
// ACTIVE PREVIEW NODE and nothing had been selected, and the showcase graph renders at -4 degC
// where the sea is ice under snow.
//
// So the check is a PIXEL COMPARISON, not a screenshot: render the same frame twice, once with the
// wave amplitude at zero and once at full, and require the images to differ. A screenshot is how a
// human checks; this is how a gate checks. It also fails for the right reason if water stops being
// visible at all, because the two frames would then be identical.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:/Program Files/Google/Chrome/Application/chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'amplitude-ignored',   // the shader stops reading uWaveAmp, so both frames are the flat plane
  'no-water-in-frame',   // the fixture stops producing water, so "they differ" proves nothing
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
    wat.params.mode = 'sea'
    wat.params.level = mut === 'no-water-in-frame' ? 0 : 0.55
    // SELECT THE OUTPUT. collectScene walks the primary chain from the active preview node, so
    // without this `scene.water` stays null and every reading below is about a dry world.
    select(out)
    previewMode = 'output'
    nodes.forEach(n => { n._dirty = true })
    evalGraph()
    // Low and nearly level with the surface: the silhouette against the terrain is the thing a flat
    // plane cannot produce, so it is what the camera is pointed at.
    cam.target = [0.5, 0.30, 0.5]; cam.dist = 1.05; cam.pitch = 0.16; cam.yaw = 0.65
    // STOP THE SCENE MOVING. Two captures of an identical frame differed by 85% of bytes, so the
    // comparison was reading the renderer's own variability. AUTO keeps re-evaluating and the
    // viewport keeps re-rendering; both are pinned before anything is measured.
    if (typeof AUTO !== 'undefined' && AUTO) { AUTO = false }
    uTime = 3.5
    return { water: !!scene.water, level: scene.water ? scene.water.level : null }
  }, mutation)
  await page.waitForTimeout(900)

  // Two frames of the SAME scene, differing only in wave amplitude.
  // COMPARE DECODED PIXELS, NOT PNG BYTES. Byte-comparing two PNGs of the same scene reported 85%
  // difference: the codec amplifies any sub-pixel jitter into a wholly different bitstream, so it
  // measures the encoder, not the image. Reading the framebuffer and reducing it to a coarse tile
  // grid is robust to that jitter and still sensitive to a surface moving, which is the thing under
  // test. 16x16 tiles over the viewport, mean luminance each.
  const tiles = async () => page.evaluate(() => {
    const c = document.querySelector('#gl')
    const g = c.getContext('webgl2') || c.getContext('webgl')
    const w = c.width, h = c.height
    const px = new Uint8Array(w * h * 4)
    // READ INSIDE THE RENDER. The context is created without preserveDrawingBuffer, so by the time
    // a test reads the default framebuffer it has been discarded — the first attempt read all
    // zeros and reported a beautifully stable 0.000% noise over an empty image. Rendering
    // synchronously and reading immediately is what makes the pixels real.
    if (typeof renderGL === 'function') renderGL()
    g.readPixels(0, 0, w, h, g.RGBA, g.UNSIGNED_BYTE, px)
    const T = 16, out = new Array(T * T).fill(0), cnt = new Array(T * T).fill(0)
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4
      const t = Math.min(T - 1, (y * T / h) | 0) * T + Math.min(T - 1, (x * T / w) | 0)
      out[t] += 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]; cnt[t]++
    }
    return out.map((v, i) => cnt[i] ? v / cnt[i] : 0)
  })
  const tileDiff = (p, q) => {
    let m = 0
    for (let i = 0; i < p.length; i++) m = Math.max(m, Math.abs(p[i] - q[i]))
    return m
  }

  const frame = async amp => {
    // VARY THE DISPLACEMENT ALONE. The first version varied `strength`, which also drives the
    // legacy ripple SHADING — so it measured the ripple and reported 99% of pixels changed while
    // proving nothing about geometry. Everything else is held fixed, including the ripple.
    await page.evaluate(a => { waterLook.waveDisplacement = a; waterLook.strength = 0.55; 
      waterLook.seaState = 0.85 }, amp)
    await page.waitForTimeout(1400)
    // Pin the clock again: anything that re-rendered in the meantime must do so at the same time
    // value, or the wave phase moves between captures and the difference is phase, not amplitude.
    await page.evaluate(() => { uTime = 3.5 })
    await page.waitForTimeout(400)
  }
  // `amplitude-ignored` reproduces the observable behaviour of a build whose shader never reads
  // uWaveAmp: the second frame is rendered at zero amplitude too, so the two are identical and the
  // gate must go red. It is a fixture change rather than a source patch because this oracle drives
  // the built page rather than importing a module — and it reproduces exactly what that defect
  // looks like from outside, which is what the gate can see.
  // THE NOISE FLOOR FIRST. Two captures of an identical scene must agree, or "the frames differ"
  // measures the renderer's own variability rather than the waves. This control was missing from the
  // first version and the runner caught the consequence: the amplitude-ignored mutation rendered
  // both frames flat and they STILL differed, so the gate was reading noise.
  // THE SIGNAL MUST SCALE WITH THE CONTROL, which is a stronger claim than "it differs" and does
  // not need a threshold picked out of the air. A wave of 30 m on 2600 m of relief is 1.2% of the
  // height range, so the absolute change is legitimately small; what a working displacement cannot
  // do is stay the same when the authored height doubles.
  await frame(0); const tFlatA = await tiles()
  await frame(0); const tFlatB = await tiles()
  await page.evaluate(() => { waterLook.amplitudeM = 10 })   // INSIDE THE AUTHORED RANGE. This was 120 against 240, both far
  // outside the 0-60 m the slider offers, chosen when the wave normal carried no amplitude at all and
  // the signal was tiny. Now that it does, the normal saturates long before 120 m -- a normalised
  // normal can only tilt so far -- so doubling from 120 measured almost no further change. Testing a
  // control outside its own domain is not a stronger test, it is a different one.
  await frame(mutation === 'amplitude-ignored' ? 0 : 1); const tWaved = await tiles()
  await page.evaluate(() => { waterLook.amplitudeM = 30 })
  await frame(mutation === 'amplitude-ignored' ? 0 : 1); const tDouble = await tiles()
  const noiseFraction = tileDiff(tFlatA, tFlatB) / 255
  const changedFraction = tileDiff(tFlatB, tWaved) / 255
  const doubleFraction = tileDiff(tFlatB, tDouble) / 255


  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }

  // Absence of evidence: if the fixture produced no water, "the frames differ" would be measuring
  // the terrain, not the waves.
  // ABSENCE OF EVIDENCE. readPixels on the default framebuffer returns nothing useful unless the
  // drawing buffer was preserved, and an all-zero read would make both the noise and the signal
  // measure 0.00% — which reads as a clean, stable, meaningless pass. The tiles must contain an
  // actual image before any difference between them means anything.
  const tileMean = tFlatB.reduce((x, v) => x + v, 0) / tFlatB.length
  const tileSpread = Math.max(...tFlatB) - Math.min(...tFlatB)
  check('the framebuffer read back an actual image', tileMean > 5 && tileSpread > 10,
    { tileMean: +tileMean.toFixed(2), tileSpread: +tileSpread.toFixed(2) })
  check('the fixture actually produced water', setup.water === true && setup.level > 0, setup)
  check('the renderer is repeatable enough to compare', noiseFraction < 0.01, noiseFraction)
  check('waves change the rendered image', changedFraction > noiseFraction * 3,
    { changedFraction, noiseFraction })
  // Doubling the authored height must move the image further. A build that ignored the control
  // entirely, or clamped it, produces the same frame twice and fails here — which no absolute
  // threshold could distinguish from "the waves are simply small".
  check('the change scales with the authored height', doubleFraction > changedFraction * 1.3,
    { changedFraction, doubleFraction })
  check('no page errors', errors.length === 0, errors)

  let ok = assertions.every(x => x.ok)
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = assertions.filter(x => !x.ok).map(x => x.name)
  console.log(`${ok ? 'PASS' : 'FAIL'}  water displacement water=${setup.water} level=${setup.level} `
    + `doubled=${(doubleFraction * 100).toFixed(3)}% tileMean=${(tFlatB.reduce((x,v)=>x+v,0)/tFlatB.length).toFixed(1)} changed=${(changedFraction * 100).toFixed(2)}% noise=${(noiseFraction * 100).toFixed(3)}% `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify(assertions.filter(x => !x.ok), null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
