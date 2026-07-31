// Thermal erosion contract:
//   * Feature Scale derives repose on the simulation grid, not the output grid.
//   * square CPU/GPU implementations agree and converge without non-finite values;
//   * omitted off-grid neighbours are a closed/no-flux boundary;
//   * HeightField values are finite but unbounded (negative and >1 are not colour-clamped).
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
    const out = { subRepose: [], flats: [], edges: [], parity: null, convergence: null, rejects: {} }
    const params = overrides => {
      const p = {}
      for (const d of TYPES.thermal.params) p[d.key] = structuredClone(d.def)
      return Object.assign(p, overrides)
    }
    const runNode = (field, overrides, gpu, mask = null) => {
      USE_GPU = gpu
      return TYPES.thermal.eval(params(overrides), [field, mask])
    }
    const stats = f => {
      let min = Infinity, max = -Infinity, sum = 0, sumAbs = 0, finite = true
      for (let i = 0; i < f.length; i++) {
        const v = f[i]
        finite = finite && Number.isFinite(v)
        min = Math.min(min, v); max = Math.max(max, v)
        sum += v; sumAbs += Math.abs(v)
      }
      return { min, max, sum, sumAbs, finite }
    }
    const diff = (a, b) => {
      let max = 0, ss = 0
      for (let i = 0; i < a.length; i++) {
        const d = Math.abs(a[i] - b[i])
        max = Math.max(max, d); ss += d * d
      }
      return { max, rms: Math.sqrt(ss / a.length) }
    }
    const massRel = (before, after) => {
      const a = stats(before), b = stats(after)
      return Math.abs(b.sum - a.sum) / Math.max(1, a.sumAbs)
    }
    const maxExcess = (field, talus) => {
      const n = RES
      let excess = 0
      const nb = [[1, 0, 1], [0, 1, 1], [1, 1, Math.SQRT2], [-1, 1, Math.SQRT2]]
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const h = field[y * n + x]
        for (const [dx, dy, dist] of nb) {
          const xx = x + dx, yy = y + dy
          if (xx < 0 || yy < 0 || xx >= n || yy >= n) continue
          excess = Math.max(excess, Math.abs(h - field[yy * n + xx]) - talus * dist)
        }
      }
      return Math.max(0, excess)
    }

    try {
      terrainDef.lattice = 'square'
      terrainDef.scale = 5000
      terrainDef.height = 2600
      BUILD_QUALITY = 'final'
      SCALE_RES = true

      // A manufactured linear slope at 80% of repose must be an exact fixed point at both
      // Feature Scale 1 and 4. Before the wrapper fix, feat=4 changed 34,470/36,864 samples:
      // the coarse solver received the fine-cell threshold and 35 degrees behaved like ~9.9.
      RES = 192
      const repose = 35
      const realTalus = Math.tan(repose * Math.PI / 180) * (terrainDef.scale / RES) / terrainDef.height
      for (const units of ['real', 'cell']) {
        const threshold = units === 'real' ? realTalus : 0.012
        const ramp = new Float32Array(RES * RES)
        for (let y = 0; y < RES; y++) for (let x = 0; x < RES; x++) {
          ramp[y * RES + x] = -0.75 + x * threshold * 0.8
        }
        const base = units === 'real'
          ? { realScale: 'on', repose, iters: 40, rate: 0.5 }
          : { realScale: 'off', talus: 0.012, iters: 40, rate: 0.5 }
        for (const gpu of [false, true]) for (const feat of [1, 4]) {
          const eroded = runNode(ramp, { ...base, feat }, gpu)
          out.subRepose.push({ units, gpu, feat, ...diff(ramp, eroded), finite: stats(eroded).finite })
        }
        // A slope above repose proves the same path is active rather than returning its input.
        const steep = new Float32Array(RES * RES)
        for (let y = 0; y < RES; y++) for (let x = 0; x < RES; x++) {
          steep[y * RES + x] = -0.75 + x * threshold * 1.25
        }
        const acted = runNode(steep, { ...base, feat: 4 }, false)
        out.subRepose.push({ units, gpu: false, feat: '4-active', ...diff(steep, acted),
          finite: stats(acted).finite })
      }

      // Uniform values on either side of [0,1] exercise every outer cell. A ghost-height or
      // cosmetic clamp would move these edges or collapse their legitimate elevation range.
      RES = 64
      for (const value of [-2.5, 2.5]) for (const gpu of [false, true]) {
        const flat = new Float32Array(RES * RES).fill(value)
        const eroded = runNode(flat, { realScale: 'off', talus: 0.012, feat: 1,
          iters: 60, rate: 0.5 }, gpu)
        out.flats.push({ value, gpu, delta: diff(flat, eroded), field: stats(eroded) })
      }

      // A corner impulse plus a -2.25/+2.25 step makes transfers touch the outer boundary.
      // With a closed boundary, all material stays on-grid and no new extrema are invented.
      const edgeField = new Float32Array(RES * RES)
      for (let y = 0; y < RES; y++) for (let x = 0; x < RES; x++) {
        edgeField[y * RES + x] = (x < RES / 2 ? -2.25 : 2.25) + y * 0.0005
      }
      edgeField[0] = 4.5
      const edgeIn = stats(edgeField)
      for (const gpu of [false, true]) {
        const eroded = runNode(edgeField, { realScale: 'off', talus: 0.012, feat: 1,
          iters: 80, rate: 0.5 }, gpu)
        const s = stats(eroded)
        out.edges.push({ gpu, inputCorner: edgeField[0], outputCorner: eroded[0],
          min: s.min, max: s.max, finite: s.finite, massRel: massRel(edgeField, eroded),
          minBoundError: Math.max(0, edgeIn.min - s.min),
          maxBoundError: Math.max(0, s.max - edgeIn.max) })
      }

      // Direct-kernel parity and a long-run cone give the numerical core an independent gate.
      RES = 48
      let seed = 0x1234abcd
      const random = new Float32Array(RES * RES)
      for (let i = 0; i < random.length; i++) {
        seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5
        random[i] = -1.5 + ((seed >>> 0) / 4294967296) * 4
      }
      const kernelOpt = { talus: 0.018, iters: 320, rate: 0.5 }
      const cpuRandom = thermalErode(random, kernelOpt)
      USE_GPU = true
      const gpuRandom = gpuThermal(random, kernelOpt)
      out.parity = { ...diff(cpuRandom, gpuRandom), cpuFinite: stats(cpuRandom).finite,
        gpuFinite: stats(gpuRandom).finite, cpuMass: massRel(random, cpuRandom),
        gpuMass: massRel(random, gpuRandom) }

      const cone = new Float32Array(RES * RES)
      const center = (RES - 1) / 2
      for (let y = 0; y < RES; y++) for (let x = 0; x < RES; x++) {
        cone[y * RES + x] = -1 + Math.max(0, 4 * (1 - Math.hypot(x - center, y - center) / 20))
      }
      const talus = 0.02
      const beforeExcess = maxExcess(cone, talus)
      const mid = thermalErode(cone, { talus, iters: 600, rate: 0.5 })
      const long = thermalErode(cone, { talus, iters: 1400, rate: 0.5 })
      out.convergence = { beforeExcess, afterExcess: maxExcess(long, talus),
        continuation: diff(mid, long), finite: stats(long).finite,
        massRel: massRel(cone, long), min: stats(long).min, max: stats(long).max }

      // Invalid values must fail at the node boundary. They must never be repaired by a [0,1]
      // clamp, because that would also destroy valid bathymetry and absolute DEM elevations.
      const valid = new Float32Array(RES * RES).fill(2)
      const badInput = valid.slice(); badInput[17] = NaN
      try { runNode(badInput, { realScale: 'on', repose: 35, feat: 1 }, false) }
      catch (e) { out.rejects.input = /non-finite height/.test(String(e.message)) }
      const badMask = new Float32Array(RES * RES).fill(1); badMask[29] = Infinity
      try { runNode(valid, { realScale: 'on', repose: 35, feat: 1 }, false, badMask) }
      catch (e) { out.rejects.mask = /non-finite height/.test(String(e.message)) }
    } finally {
      RES = saved.RES; USE_GPU = saved.USE_GPU; BUILD_QUALITY = saved.BUILD_QUALITY
      SCALE_RES = saved.SCALE_RES
      terrainDef.lattice = saved.lattice; terrainDef.scale = saved.scale; terrainDef.height = saved.height
    }
    return out
  })

  await browser.close()

  const failures = []
  for (const r of result.subRepose) {
    if (r.feat === '4-active') {
      if (!r.finite || r.max < 1e-4) failures.push(`above-repose ${r.units} slope did not erode`)
    } else if (!r.finite || r.max > 2e-6) {
      failures.push(`sub-repose ${r.units} gpu=${r.gpu} feat=${r.feat} drifted max=${r.max}`)
    }
  }
  for (const r of result.flats) {
    if (!r.field.finite || r.delta.max > 1e-7 || Math.abs(r.field.min - r.value) > 1e-7
      || Math.abs(r.field.max - r.value) > 1e-7) {
      failures.push(`flat ${r.value} gpu=${r.gpu} changed or was clamped`)
    }
  }
  for (const r of result.edges) {
    if (!r.finite || !(r.outputCorner < r.inputCorner) || r.min >= -1 || r.max <= 1
      || r.massRel > 2e-6 || r.minBoundError > 2e-5 || r.maxBoundError > 2e-5) {
      failures.push(`edge contract gpu=${r.gpu} failed: ${JSON.stringify(r)}`)
    }
  }
  const p = result.parity
  if (!p.cpuFinite || !p.gpuFinite || p.max > 8e-5 || p.rms > 1e-5
    || p.cpuMass > 2e-6 || p.gpuMass > 2e-6) {
    failures.push(`CPU/GPU parity or mass failed: ${JSON.stringify(p)}`)
  }
  const c = result.convergence
  // Convergence is defined by the physical residual (maximum slope above repose), not by
  // byte-identical successive fields: material can keep diffusing while that residual tends to
  // zero. The 1400-step cone must remove at least 99.8% of its initial excess without range growth.
  if (!c.finite || c.afterExcess > Math.max(3e-4, c.beforeExcess * 0.002)
    || c.massRel > 2e-6 || c.min < -1.00002 || c.max > 3.00002) {
    failures.push(`long-run convergence failed: ${JSON.stringify(c)}`)
  }
  if (!result.rejects.input || !result.rejects.mask) {
    failures.push(`non-finite rejection failed: ${JSON.stringify(result.rejects)}`)
  }
  if (errors.length) failures.push(`page errors: ${JSON.stringify(errors)}`)

  console.log(JSON.stringify(result, null, 2))
  if (failures.length) {
    console.error('GATES FAILED:', failures.join(' | '))
    process.exit(1)
  }
  console.log('PASS thermal Feature Scale, edge, range, convergence, and CPU/GPU contract')
})().catch(e => { console.error('FATAL', e); process.exit(2) })
