// Rock Fracture node contract:
//   * deterministic, multi-scale Worley joints expressed in world metres;
//   * finite HeightField output without a cosmetic [0,1] clamp;
//   * no boundary-frame special case, exact mask compositing, and resolution stability;
//   * square CPU/GPU paths agree within float-shader tolerance.
const { chromium } = require('playwright-core')
const path = require('path')
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

;(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1100, height: 760 } })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1200)

  const result = await page.evaluate(() => {
    const saved = {
      RES, USE_GPU, BUILD_QUALITY, SCALE_RES,
      lattice: terrainDef.lattice, scale: terrainDef.scale, height: terrainDef.height
    }
    const out = {
      schema: null, base: null, deterministic: null, seedVariation: null,
      bypass: null, weathering: null, ranges: [], mask: null, edges: null,
      resolution: null, parity: null, hex: null, rejects: {}
    }
    const params = overrides => {
      const p = {}
      for (const d of TYPES.fracture.params) p[d.key] = structuredClone(d.def)
      return Object.assign(p, overrides)
    }
    const runNode = (field, overrides = {}, gpu = false, mask = null) => {
      USE_GPU = gpu
      return TYPES.fracture.eval(params(overrides), [field, mask])
    }
    const stats = f => {
      let min = Infinity, max = -Infinity, sum = 0, sumAbs = 0, finite = true
      for (let i = 0; i < f.length; i++) {
        const v = f[i]
        finite = finite && Number.isFinite(v)
        min = Math.min(min, v); max = Math.max(max, v)
        sum += v; sumAbs += Math.abs(v)
      }
      return { min, max, mean: sum / f.length, sum, sumAbs, finite }
    }
    const diff = (a, b) => {
      let max = 0, ss = 0, mean = 0, changed = 0
      for (let i = 0; i < a.length; i++) {
        const d = Math.abs(a[i] - b[i])
        max = Math.max(max, d); ss += d * d; mean += d
        if (d > 1e-7) changed++
      }
      return { max, rms: Math.sqrt(ss / a.length), mean: mean / a.length,
        changed, changedFraction: changed / a.length }
    }
    const fractionAbove = (before, after, threshold) => {
      let count = 0
      for (let i = 0; i < before.length; i++) if (before[i] - after[i] > threshold) count++
      return count / before.length
    }
    const downsample2 = fine => {
      const coarseN = RES / 2
      const coarse = new Float32Array(coarseN * coarseN)
      for (let y = 0; y < coarseN; y++) for (let x = 0; x < coarseN; x++) {
        const i = (y * 2) * RES + x * 2
        coarse[y * coarseN + x] = .25 * (fine[i] + fine[i + 1] + fine[i + RES] + fine[i + RES + 1])
      }
      return coarse
    }
    const edgeMeans = (before, after, ring) => {
      const n = RES
      let edge = 0, edgeCount = 0, inner = 0, innerCount = 0
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const drop = before[y * n + x] - after[y * n + x]
        const d = Math.min(x, y, n - 1 - x, n - 1 - y)
        if (d < ring) { edge += drop; edgeCount++ }
        else if (d >= ring * 2) { inner += drop; innerCount++ }
      }
      return { edge: edge / edgeCount, inner: inner / innerCount,
        ratio: (edge / edgeCount) / Math.max(1e-12, inner / innerCount) }
    }

    try {
      terrainDef.lattice = 'square'
      terrainDef.scale = 5000
      terrainDef.height = 2600
      BUILD_QUALITY = 'final'
      SCALE_RES = true
      out.schema = {
        present: !!TYPES.fracture,
        category: TYPES.fracture.cat,
        inputs: TYPES.fracture.ins.slice(),
        sections: TYPES.fracture.paramSections.map(s => ({
          id: s.id, toggle: s.toggle, device: s.device
        }))
      }

      RES = 192
      const flat = new Float32Array(RES * RES).fill(.75)
      const overrides = { scaleM: 620, octaves: 3, lacunarity: 2, jitter: .9,
        warp: .31, warpScaleM: 840, widthM: 13, depthM: 24, depthFalloff: .58,
        breakdownM: 34, breakdown: .5, roughness: .3, seed: 37 }
      const cpu = runNode(flat, overrides, false)
      const cpuStats = stats(cpu)
      const maxAllowedDrop = overrides.depthM / terrainDef.height * 1.3
      out.base = { field: cpuStats, delta: diff(flat, cpu),
        maxAllowedDrop,
        strongFraction: fractionAbove(flat, cpu, maxAllowedDrop * .1) }
      const repeat = runNode(flat, overrides, false)
      out.deterministic = diff(cpu, repeat)
      const otherSeed = runNode(flat, { ...overrides, seed: 38 }, false)
      out.seedVariation = diff(cpu, otherSeed)
      const bypass = runNode(flat, { ...overrides, patternEnabled: false }, false)
      out.bypass = diff(flat, bypass)

      const hard = runNode(flat, { ...overrides, weatherEnabled: false }, false)
      const weathered = runNode(flat, { ...overrides, weatherEnabled: true }, false)
      out.weathering = {
        hardDrop: diff(flat, hard), weatheredDrop: diff(flat, weathered),
        hardToWeathered: diff(hard, weathered)
      }

      // Legitimate bathymetry and absolute-elevation-like values are cut in-place, never
      // normalised or colour-clamped to [0,1].
      RES = 64
      for (const value of [-2.5, 2.5]) {
        const source = new Float32Array(RES * RES).fill(value)
        const cut = runNode(source, { ...overrides, depthM: 30 }, false)
        out.ranges.push({ value, field: stats(cut), delta: diff(source, cut) })
      }

      // maskApply is the effect compositing contract: an all-zero outside region is byte-exact.
      const source = new Float32Array(RES * RES).fill(.4)
      const mask = new Float32Array(RES * RES)
      for (let y = 0; y < RES; y++) for (let x = 0; x < RES; x++) {
        const dx = x - (RES - 1) / 2, dy = y - (RES - 1) / 2
        if (Math.hypot(dx, dy) < RES * .28) mask[y * RES + x] = 1
      }
      const masked = runNode(source, overrides, false, mask)
      let outsideMax = 0, insideMax = 0
      for (let i = 0; i < source.length; i++) {
        const d = Math.abs(masked[i] - source[i])
        if (mask[i] === 0) outsideMax = Math.max(outsideMax, d)
        else insideMax = Math.max(insideMax, d)
      }
      out.mask = { outsideMax, insideMax, finite: stats(masked).finite }

      // The field is evaluated beyond the authored rectangle by integer Voronoi cells. Outer
      // samples therefore have the same statistical crack dose as an interior strip—no clamped
      // neighbour, drain, wall, or copied edge participates.
      RES = 256
      const edgeSource = new Float32Array(RES * RES).fill(.8)
      const edgeCut = runNode(edgeSource, { ...overrides, seed: 91 }, false)
      out.edges = { ...edgeMeans(edgeSource, edgeCut, 12),
        finite: stats(edgeCut).finite, delta: diff(edgeSource, edgeCut) }

      // The authored dimensions are metres. Average the 256 result to the 128 pixel footprint
      // before comparing, so sub-pixel anti-alias coverage—not one chosen point sample—is tested.
      const fine = edgeCut
      const fineDown = downsample2(fine)
      RES = 128
      const coarseSource = new Float32Array(RES * RES).fill(.8)
      const coarse = runNode(coarseSource, { ...overrides, seed: 91 }, false)
      out.resolution = diff(coarse, fineDown)

      RES = 192
      const paritySource = new Float32Array(RES * RES)
      for (let y = 0; y < RES; y++) for (let x = 0; x < RES; x++) {
        paritySource[y * RES + x] = -1.2 + x / RES * 3.4 + y / RES * .2
      }
      const parityCpu = runNode(paritySource, overrides, false)
      USE_GPU = true
      const ready = gpuReady()
      const parityGpu = runNode(paritySource, overrides, true)
      out.parity = { ready, ...diff(parityCpu, parityGpu),
        cpu: stats(parityCpu), gpu: stats(parityGpu) }

      // Hex uses physical odd-r coordinates and intentionally stays on the CPU compatibility path.
      terrainDef.lattice = 'hex'
      RES = 96
      const hexSource = new Float32Array(fieldW() * fieldH()).fill(1.5)
      const hexCut = runNode(hexSource, overrides, true)
      out.hex = { length: hexCut.length, expected: fieldW() * fieldH(),
        field: stats(hexCut), delta: diff(hexSource, hexCut) }

      const valid = new Float32Array(hexSource.length).fill(2)
      const badInput = valid.slice(); badInput[17] = NaN
      try { runNode(badInput, overrides, false) }
      catch (e) { out.rejects.input = /non-finite/.test(String(e.message)) }
      const badMask = new Float32Array(valid.length).fill(1); badMask[29] = 1.01
      try { runNode(valid, overrides, false, badMask) }
      catch (e) { out.rejects.maskRange = /outside \[0, 1\]/.test(String(e.message)) }
      badMask[29] = Infinity
      try { runNode(valid, overrides, false, badMask) }
      catch (e) { out.rejects.maskFinite = /non-finite/.test(String(e.message)) }
    } finally {
      RES = saved.RES; USE_GPU = saved.USE_GPU; BUILD_QUALITY = saved.BUILD_QUALITY
      SCALE_RES = saved.SCALE_RES
      terrainDef.lattice = saved.lattice; terrainDef.scale = saved.scale; terrainDef.height = saved.height
    }
    return out
  })

  result.ui = await page.evaluate(() => {
    RES = 256; TARGET_RES = 256; USE_GPU = true; buildIndex()
    terrainDef.lattice = 'square'; terrainDef.scale = 5000; terrainDef.height = 2600
    historyReady = false; nodes = []; edges = []; uid = 1; selected = null
    selectedEdge = null; undoStack = []; redoStack = []
    const mountain = makeNode('mountain', 80, 140)
    Object.assign(mountain.params, { form: 'peak', shape: 'broad', style: 'basic',
      seed: 23, detail: .4, character: .25, reduce: 1, weather: 0 })
    const fracture = makeNode('fracture', 350, 140)
    Object.assign(fracture.params, { scaleM: 680, octaves: 3, widthM: 22, depthM: 80,
      warp: .34, warpScaleM: 950, breakdownM: 30, breakdown: .35, roughness: .25, seed: 37 })
    const output = makeNode('output', 620, 140)
    edges.push({ from: mountain.id, to: fracture.id, slot: 0 },
      { from: fracture.id, to: output.id, slot: 0 })
    historyReady = true; previewMode = 'output'; select(fracture); evalGraph()
    shadeMode = 1; syncDisplayState(); frameHero()
    const inspect = () => ({
      toolbox: !!document.querySelector('.node-tool-item[data-type="fracture"]'),
      nodeName: TYPES.fracture.name,
      sections: [...document.querySelectorAll('#pBody .param-section')].map(section => ({
        id: section.dataset.section,
        open: !section.querySelector('.param-section-body').hidden,
        enabled: section.querySelector('[role=switch]').getAttribute('aria-checked'),
        badge: section.querySelector('.param-section-badge').textContent.trim(),
        keys: [...section.querySelectorAll('.field[data-param-key]')].map(field => field.dataset.paramKey)
      })),
      params: { ...fracture.params }
    })
    const initial = inspect()
    const beforeCollapse = JSON.stringify(fracture.params)
    document.querySelector('.param-section[data-section=network] .param-section-collapse').click()
    const collapsed = inspect()
    return { initial, collapsed, collapsePure: beforeCollapse === JSON.stringify(fracture.params) }
  })
  await page.waitForTimeout(900)
  await page.locator('#props').screenshot({
    path: path.resolve(__dirname, '_shot_fracture_props.png')
  })
  await page.locator('#viewport').screenshot({
    path: path.resolve(__dirname, '_shot_fracture_terrain.png')
  })
  await browser.close()

  const failures = []
  const s = result.schema
  if (!s.present || s.category !== 'ero' || s.inputs.join(',') !== 'In,Mask'
    || s.sections.length !== 2 || s.sections.some(section => section.device !== 'gpu')) {
    failures.push(`registration/schema failed: ${JSON.stringify(s)}`)
  }
  const b = result.base
  if (!b.field.finite || b.field.max > .7500001 || b.delta.max <= .002
    || b.delta.max > b.maxAllowedDrop || b.delta.changedFraction < .05
    || b.delta.changedFraction > .95 || b.strongFraction < .08 || b.strongFraction > .8) {
    failures.push(`base fracture dose/range failed: ${JSON.stringify(b)}`)
  }
  if (result.deterministic.max !== 0) {
    failures.push(`same-seed CPU repeat changed: ${JSON.stringify(result.deterministic)}`)
  }
  if (result.seedVariation.rms < 5e-4 || result.seedVariation.changedFraction < .2) {
    failures.push(`seed did not alter network: ${JSON.stringify(result.seedVariation)}`)
  }
  if (result.bypass.max !== 0) failures.push(`disabled network was not identity`)
  const w = result.weathering
  if (w.hardToWeathered.max <= 1e-4 || w.weatheredDrop.mean <= w.hardDrop.mean * 1.05) {
    failures.push(`edge weathering did not widen/recess joints: ${JSON.stringify(w)}`)
  }
  for (const r of result.ranges) {
    if (!r.field.finite || r.delta.max <= .002 || r.field.max > r.value + 1e-7
      || (r.value < 0 && r.field.max >= 0) || (r.value > 1 && r.field.min <= 1)) {
      failures.push(`unbounded range ${r.value} failed: ${JSON.stringify(r)}`)
    }
  }
  if (!result.mask.finite || result.mask.outsideMax !== 0 || result.mask.insideMax <= 1e-4) {
    failures.push(`mask contract failed: ${JSON.stringify(result.mask)}`)
  }
  if (!result.edges.finite || result.edges.edge <= 0 || result.edges.inner <= 0
    || result.edges.ratio < .3 || result.edges.ratio > 3.2) {
    failures.push(`edge continuation contract failed: ${JSON.stringify(result.edges)}`)
  }
  if (result.resolution.max > .008 || result.resolution.rms > .0015) {
    failures.push(`world-scale resolution stability failed: ${JSON.stringify(result.resolution)}`)
  }
  const p = result.parity
  if (!p.ready || !p.cpu.finite || !p.gpu.finite || p.max > 2e-4 || p.rms > 2e-5) {
    failures.push(`CPU/GPU parity failed: ${JSON.stringify(p)}`)
  }
  if (result.hex.length !== result.hex.expected || !result.hex.field.finite
    || result.hex.delta.max <= 1e-4) {
    failures.push(`hex compatibility path failed: ${JSON.stringify(result.hex)}`)
  }
  if (!result.rejects.input || !result.rejects.maskRange || !result.rejects.maskFinite) {
    failures.push(`invalid-field rejection failed: ${JSON.stringify(result.rejects)}`)
  }
  const ui = result.ui
  const network = ui.initial.sections.find(section => section.id === 'network')
  const weather = ui.initial.sections.find(section => section.id === 'weather')
  const collapsedNetwork = ui.collapsed.sections.find(section => section.id === 'network')
  if (!ui.initial.toolbox || ui.initial.nodeName !== 'Rock Fracture' || !network || !weather
    || network.enabled !== 'true' || weather.enabled !== 'true'
    || network.badge !== 'GPU' || weather.badge !== 'GPU'
    || !network.keys.includes('scaleM') || !network.keys.includes('depthM')
    || !weather.keys.includes('breakdownM') || !weather.keys.includes('roughness')
    || !collapsedNetwork || collapsedNetwork.open || !ui.collapsePure) {
    failures.push(`toolbox/inspector contract failed: ${JSON.stringify(ui)}`)
  }
  if (errors.length) failures.push(`page errors: ${JSON.stringify(errors)}`)

  console.log(JSON.stringify(result, null, 2))
  if (failures.length) {
    console.error('GATES FAILED:', failures.join(' | '))
    process.exit(1)
  }
  console.log('PASS Rock Fracture registration, range, mask, edge, scale, hex, and CPU/GPU contract')
})().catch(e => { console.error('FATAL', e); process.exit(2) })
