// S4.7 — is the water surface REGULARLY BANDED?
//
// Written red, before the fix. The user photographed evenly spaced parallel stripes across the
// water and asked why Gerstner waves plus a warped multi-layer field do not prevent them. The
// answer measured from the source is that they would, and do not apply here: the wave GEOMETRY is
// Gerstner, but the normal-perturbation layer on top of it is still `waveData`, and its default
// "wind" pattern is two plane sinusoids —
//
//     a = sin(dot(p,d1)*58*s + t*1.9)
//     b = sin(dot(p,d2)*24*s + t*0.74 + a*0.35)
//
// Two plane waves in fixed directions cannot produce anything but parallel bands. So this oracle
// does not test the Gerstner terms at all; it tests the thing actually on screen.
//
// THE METRIC IS PERIODICITY, NOT APPEARANCE. "Looks stripy" is not a gate. A row of water pixels
// from a banded surface correlates strongly with itself shifted by one band width; a row from a
// broadband surface does not correlate with itself at any shift. So: take the water pixels, remove
// the mean, and compute the normalised autocorrelation over a range of lags. The peak IS the
// banding. A pure sinusoid scores near 1.0; an irregular surface scores low and, importantly, has
// no single dominant lag.
//
// THE BOUND SITS BETWEEN TWO MEASURED BUILDS, not around a number chosen in advance:
//
//     two plane sinusoids (the build the user photographed)   medianPeak 0.369
//     warped multi-octave detail + the Gerstner normal in use medianPeak 0.000
//
// 0.15 is between them. Both endpoints were run with this oracle, unchanged, on this fixture. The
//  mutation was removed rather than faked: the sinusoid path no longer exists to
// switch back on, and a mutation that cannot reproduce the defect is worse than none, because it
// reads as armed. The red endpoint above is the real demonstration and it is recorded here.
//
// This is deliberately a property of the image rather than of the shader text. A fix that swaps
// sinusoids for a warped cellular field but leaves a dominant period behind has not fixed anything,
// and only measuring the pixels can tell.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:/Program Files/Google/Chrome/Application/chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'no-water-in-frame' // no water, so there are no pixels to measure and "not banded" is vacuous
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

// Peak normalised autocorrelation of one row — but only at a LOCAL MAXIMUM.
//
// The first version of this took the largest autocorrelation at any lag, and it was measuring the
// wrong thing: it reported a dominant lag of 4 px, the smallest lag it was allowed to consider.
// Any smooth image correlates strongly with itself at small shifts, and more strongly the smaller
// the shift, so a plain maximum just rediscovers that the picture is smooth. Water shading over a
// depth gradient is smooth everywhere, banded or not.
//
// Periodicity is different in kind: it puts a LOCAL PEAK at the repeat distance, standing above the
// decay curve on both sides. So the row is high-passed to remove the depth gradient, and only lags
// that are local maxima count. A sinusoid at period P scores near 1 at P; a smooth gradient with no
// repeat scores nothing at all, because its autocorrelation only ever decreases.
function peakAutocorr(row) {
  const n = row.length
  if (n < 64) return null
  // High-pass by subtracting a moving average. The window is wider than any band we care about, so
  // it removes the shading gradient without removing the stripes themselves.
  // The window must be WIDER than any band being looked for, or the high-pass removes the signal.
  // At 41 px it was narrower than the ~63 px band period and attenuated it into nothing: every row
  // reported no local maximum at all. The isolated ripple difference carries no depth gradient to
  // subtract in the first place, so this only needs to remove very long-scale drift.
  const W = 161, half = W >> 1
  const d = new Float64Array(n)
  for (let i = 0; i < n; i++) {
    let s = 0, c = 0
    for (let k = Math.max(0, i - half); k <= Math.min(n - 1, i + half); k++) { s += row[k]; c++ }
    d[i] = row[i] - s / c
  }
  let denom = 0
  for (const v of d) denom += v * v
  if (denom <= 1e-9) return { peak: 0, lag: 0 }   // genuinely featureless: no periodicity present
  const maxLag = Math.min(96, Math.floor(n / 3))
  const r = new Float64Array(maxLag + 2)
  for (let lag = 1; lag <= maxLag + 1; lag++) {
    let s = 0
    for (let i = 0; i + lag < n; i++) s += d[i] * d[i + lag]
    r[lag] = (s / (n - lag)) / (denom / n)
  }
  let best = 0, bestLag = 0
  for (let lag = 6; lag <= maxLag; lag++) {
    if (r[lag] > r[lag - 1] && r[lag] >= r[lag + 1] && r[lag] > best) { best = r[lag]; bestLag = lag }
  }
  return { peak: best, lag: bestLag }
}

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
    // WARM IT, OR MEASURE ICE. The first run of this oracle rendered at -4.5 degC and 1612 m, where
    // the sea is frozen and `waveAmt = uRipple*coverage*(1.0-ice)` is identically zero. It reported
    // a clean pass on a surface that had no ripples on it at all. The temperature is part of the
    // fixture, not a detail of the preset.
    terrainDef.baseElevation = 0
    terrainDef.seaTemp = 22
    wat.params.mode = 'sea'
    wat.params.level = mut === 'no-water-in-frame' ? 0 : 0.80
    select(out)
    previewMode = 'output'
    nodes.forEach(n => { n._dirty = true })
    evalGraph()
    // Looking across a wide expanse of open water, which is where banding is visible and where a
    // detail layer has to hold up. Close to the surface, so the bands subtend many pixels.
    cam.target = [0.5, 0.30, 0.5]; cam.dist = 1.15; cam.pitch = 0.20; cam.yaw = 0.4
    if (typeof AUTO !== 'undefined' && AUTO) { AUTO = false }
    uTime = 3.5
    // The detail layer is what is under test, so it is turned up rather than left at whatever the
    // last preference happened to be — a gate that depends on a stored UI value is not a gate.
    waterLook.strength = 0.85
    waterLook.scale = 1
    if (mut === 'force-sinusoid') waterLook.pattern = 'wind'
    return { water: !!scene.water, level: scene.water ? scene.water.level : null, pattern: waterLook.pattern,
      seaTemp: terrainDef.seaTemp, baseElevation: terrainDef.baseElevation }
  }, mutation)
  await page.waitForTimeout(1200)

  // Two reads: with water, and with the water surface pushed below the terrain so nothing is wet.
  // Differencing them is what identifies water pixels without hardcoding a screen region — the
  // camera framing can change without silently making this oracle measure the sky.
  // Mean blueness of the water pixels. Liquid water is blue -- the shader mixes teal to deep blue by
  // depth -- while ice and snow are neutral white, with red and blue within a few counts of each
  // other. This is the check that would have caught the frozen first run, so it is a gate now.
  const blueness = async () => page.evaluate(() => {
    const c = document.querySelector('#gl')
    const g = c.getContext('webgl2') || c.getContext('webgl')
    const w = c.width, h = c.height, px = new Uint8Array(w * h * 4)
    if (typeof renderGL === 'function') renderGL()
    g.readPixels(0, 0, w, h, g.RGBA, g.UNSIGNED_BYTE, px)
    let sum = 0, n = 0
    for (let i = 0; i < px.length; i += 4) {
      if (px[i + 3] < 8) continue
      sum += px[i + 2] - px[i]; n++
    }
    return n ? sum / n : 0
  })

  const grab = async () => page.evaluate(() => {
    const c = document.querySelector('#gl')
    const g = c.getContext('webgl2') || c.getContext('webgl')
    const w = c.width, h = c.height
    const px = new Uint8Array(w * h * 4)
    if (typeof renderGL === 'function') renderGL()
    g.readPixels(0, 0, w, h, g.RGBA, g.UNSIGNED_BYTE, px)
    const lum = new Float32Array(w * h)
    for (let i = 0, j = 0; j < w * h; i += 4, j++) lum[j] = 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]
    return { w, h, lum: Array.from(lum) }
  })

  // A picture of exactly what was measured, on request. Not part of the gate — the gate is the
  // numbers — but when a number and a human disagree about the same frame, being able to look at
  // the frame the number came from is what settles it.
  if (process.env.MC_KEEP_SHOT) {
    await page.evaluate(() => { uTime = 3.5; if (typeof renderGL === 'function') renderGL() })
    await page.locator('#gl').screenshot({ path: path.resolve(__dirname, '../../.sweep-logs/banding-fixture.png') })
  }
  const blue = await blueness()
  // ISOLATE THE DETAIL LAYER. Measuring the whole frame measured mostly terrain: depth shading and
  // relief swamped the ripple, and the oracle scored 0.179 on a surface a human called obviously
  // striped. The detail layer is the only thing `strength` controls, so differencing strength 0
  // against strength 1 leaves EXACTLY its contribution and nothing else -- same camera, same
  // geometry, same depth ramp, same sun. Periodicity is then measured on that difference, where
  // two plane sinusoids have nowhere to hide.
  const atStrength = async v => {
    await page.evaluate(x => { waterLook.strength = x; uTime = 3.5 }, v)
    await page.waitForTimeout(500)
    await page.evaluate(() => { uTime = 3.5 })
    return grab()
  }
  const rippled = await atStrength(0.85)
  const plain = await atStrength(0)
  await page.evaluate(() => { waterLook.strength = 0.85 })
  // THE MASK AND THE SIGNAL ARE DIFFERENT MEASUREMENTS, and conflating them broke the first attempt.
  // Selecting water pixels by "the ripple changed this pixel" fragments the run at every zero
  // crossing of the ripple -- which is to say, twice per period of exactly the thing being measured.
  // 44731 pixels moved and not one row survived. So: presence of WATER defines the population
  // (compare against a drained frame), and the ripple's contribution is the signal measured on it.
  await page.evaluate(() => { const n = nodes.find(x => x.type === 'water'); n.params.level = 0; n._dirty = true; evalGraph(); uTime = 3.5 })
  await page.waitForTimeout(900)
  const drained = await grab()
  const wet = { w: rippled.w, h: rippled.h, lum: rippled.lum.map((v, i) => v - plain.lum[i] + 128) }
  const dry = drained

  // Diagnose before thresholding: how much did the detail layer move the image at all?
  let maxDiff = 0, movedPx = 0
  for (let i = 0; i < wet.lum.length; i++) {
    const d = Math.abs(wet.lum[i] - 128)
    if (d > maxDiff) maxDiff = d
    if (d > 1.5) movedPx++
  }
  const { w, h } = wet
  // SCAN BOTH AXES. Bands have a direction, and a scanline parallel to them crosses no band at all:
  // scanning rows only, 83% of them reported no periodicity on a surface built from two plane
  // sinusoids, purely because the ripple's world direction happened to project along the scanline.
  // The banding score is the worse (higher) of the two axes, since a surface is banded if it is
  // banded in ANY direction.
  const scan = (len, cross, at) => {
    const out = []
    for (let a = 0; a < cross; a++) {
      // The longest contiguous run of water pixels. Contiguity matters: a run broken by terrain
      // would inject a step edge that autocorrelates like a band and inflate the score.
      let run = [], best = []
      for (let b = 0; b < len; b++) {
        const i = at(a, b)
        if (Math.abs(rippled.lum[i] - drained.lum[i]) > 6) run.push(wet.lum[i])
        else { if (run.length > best.length) best = run; run = [] }
      }
      if (run.length > best.length) best = run
      if (best.length >= 64) out.push(best)
    }
    return out
  }
  const rowRuns = scan(w, h, (y, x) => y * w + x)
  const colRuns = scan(h, w, (x, y) => y * w + x)
  const scoreAxis = runs => {
    const sc = runs.map(peakAutocorr).filter(Boolean)
    sc.sort((a, b) => b.peak - a.peak)
    const med = sc.length ? sc[Math.floor(sc.length / 2)].peak : null
    const counts = {}
    for (const x of sc) counts[x.lag] = (counts[x.lag] || 0) + 1
    const dom = Object.keys(counts).sort((a, b) => counts[b] - counts[a])[0]
    return { med, dom, share: sc.length ? counts[dom] / sc.length : 0, n: sc.length }
  }
  const axisRow = scoreAxis(rowRuns), axisCol = scoreAxis(colRuns)
  const worst = (axisCol.med ?? -1) > (axisRow.med ?? -1) ? axisCol : axisRow
  const rows = rowRuns.concat(colRuns)

  // The median, not the max: one scanline crossing a specular highlight can look periodic by accident.
  const median = worst.med
  // How much the scanlines AGREE on a single period is the other half of the signal. Real banding
  // puts the same lag in line after line; incidental structure scatters. Lag 0 means "no periodicity
  // found", so it is excluded -- a surface where most lines find nothing is the PASSING case, and
  // counting those agreements as a dominant period would invert the test.
  const domLag = worst.dom === '0' ? null : worst.dom
  const domShare = worst.dom === '0' ? 0 : worst.share

  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }

  // ABSENCE OF EVIDENCE IS A FAILURE. If no water pixels were found, every banding number below is
  // computed over nothing and "not banded" would be the most vacuous possible pass.
  check('water pixels were found to measure', rows.length >= 40, { rows: rows.length, rowLines: axisRow.n, colLines: axisCol.n })
  check('the fixture actually produced water', setup.water === true && setup.level > 0, setup)
  // ABSENCE OF EVIDENCE. A frozen sea carries no ripples, so every banding number below would be
  // computed over a flat white sheet and pass for the worst possible reason.
  check('the water is liquid, not ice', blue > 8, { meanBlueMinusRed: +blue.toFixed(2), seaTemp: setup.seaTemp })
  check('no page errors', errors.length === 0, errors)

  // The gate proper. A surface built from two plane sinusoids correlates with itself at the band
  // spacing in nearly every row; a warped, multi-layer field does not.
  check('the water is not regularly banded', median !== null && median < 0.15,
    { medianPeakAutocorr: median === null ? null : +median.toFixed(3) })
  check('no single period dominates the surface', domShare < 0.45,
    { dominantLagPx: domLag === undefined ? null : +domLag, share: +domShare.toFixed(3) })

  let ok = assertions.every(a => a.ok)
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = assertions.filter(a => !a.ok).map(a => a.name)
  console.log(`${ok ? 'PASS' : 'FAIL'}  water banding rows=${rows.length} `
    + `maxDiff=${maxDiff.toFixed(1)} movedPx=${movedPx} blue=${blue.toFixed(1)} medianPeak=${median === null ? 'n/a' : median.toFixed(3)} domLag=${domLag}px share=${domShare.toFixed(2)} `
    + `pattern=${setup.pattern} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify(assertions.filter(a => !a.ok), null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
