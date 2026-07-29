// The "sharp edge" on the rendered plate. Two candidate causes, and they are distinguishable:
//  (a) a SCARP in the height field near the boundary - erosion treating the border as base level,
//      leaving a cliff a few cells in. Shows as a step in the ring-mean profile.
//  (b) CLIPPING - autolevel/normalize saturating, giving a flat top with sharp sides. Shows as a
//      large mass of cells pinned at exactly the field max.
// Measured per engine, because the CPU (droplet) and GPU (pipe) models are different algorithms.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const URL = 'file://' + path.resolve(__dirname, 'index.html');
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1000, height: 720 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(2500);
  const r = await p.evaluate(() => {
    SCALE_RES = true; XF = null; BUILD_QUALITY = 'interactive';
    RES = 192; TARGET_RES = 192;
    const n = RES, out = {};
    const probe = (lat, gpu) => {
      terrainDef.lattice = lat; buildIndex(); USE_GPU = gpu;
      nodes.forEach(nd => { nd._dirty = true; nd._thumb = null; nd._snowLayer = null;
        nd._temperatureC = null; nd._solarShadow = null; nd._solarExposure = null; nd._wind = null; });
      evalGraph();
      const f = outputNode()._field;
      let mn = 1e9, mx = -1e9; for (const v of f) { if (v < mn) mn = v; if (v > mx) mx = v; }
      const range = (mx - mn) || 1;
      // Ring-mean profile: ring k = cells at Chebyshev distance k from the border.
      const rings = [];
      for (let k = 0; k < 12; k++) { let s = 0, c = 0;
        for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
          const d = Math.min(x, y, n - 1 - x, n - 1 - y);
          if (d === k) { s += f[y * n + x]; c++; } }
        rings.push(+((s / c - mn) / range).toFixed(4)); }
      // Biggest step between consecutive rings = the scarp signature.
      let step = 0, stepAt = -1;
      for (let k = 1; k < rings.length; k++) { const d = Math.abs(rings[k] - rings[k - 1]);
        if (d > step) { step = d; stepAt = k; } }
      // Clipping: fraction of cells within 0.1% of the extremes.
      let atMax = 0, atMin = 0;
      for (const v of f) { if (v >= mx - 0.001 * range) atMax++; if (v <= mn + 0.001 * range) atMin++; }
      return { ringProfile: rings, maxRingStep: +step.toFixed(4), atRing: stepAt,
        pctPinnedHigh: +(100 * atMax / f.length).toFixed(2),
        pctPinnedLow: +(100 * atMin / f.length).toFixed(2) };
    };
    out.square_GPU = probe('square', true);
    out.square_CPU = probe('square', false);
    out.hex_CPU = probe('hex', false);
    terrainDef.lattice = 'square'; buildIndex(); USE_GPU = true;
    return out;
  });
  console.log(JSON.stringify(r, null, 1));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
})().catch(e => { console.error('FATAL', e); process.exit(2); });
