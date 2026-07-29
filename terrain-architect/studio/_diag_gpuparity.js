// WHICH kernel makes GPU and CPU disagree, and WHERE on the field?
// End-to-end the default graph correlates only 0.910 GPU-vs-CPU while two same-engine rebuilds are
// bit-identical. That is a real divergence, so isolate it: run each GPU-backed node ALONE on the
// same input and compare against its CPU counterpart. Also split the error into a border ring vs
// the interior, because the render shows a suspicious sharp edge near the boundary.
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
    RES = 192; TARGET_RES = 192; terrainDef.lattice = 'square'; buildIndex();
    const n = RES, out = { gpuAvailable: null, kernels: [] };
    { const held = USE_GPU; USE_GPU = true;
      try { out.gpuAvailable = !!gpuReady(); } catch (e) { out.gpuAvailable = 'throw:' + e.message; }
      USE_GPU = held; }

    // A deterministic, non-trivial input every kernel sees identically.
    USE_GPU = false;
    const base = fbmField(gnoise, { seed: 11, freq: 3, octaves: 6, lac: 2, gain: 0.5 });

    const stats = (A, B) => {
      let mn = 1e9, mx = -1e9; for (const v of A) { if (v < mn) mn = v; if (v > mx) mx = v; }
      const range = (mx - mn) || 1;
      let sd = 0, wd = 0, sa = 0, sb = 0;
      for (let i = 0; i < A.length; i++) { const d = Math.abs(B[i] - A[i]); sd += d; if (d > wd) wd = d; sa += A[i]; sb += B[i]; }
      const ma = sa / A.length, mb = sb / A.length; let nu = 0, da = 0, db = 0;
      for (let i = 0; i < A.length; i++) { const u = A[i] - ma, v = B[i] - mb; nu += u * v; da += u * u; db += v * v; }
      // Border ring (outer 4 cells) vs interior: a kernel with a boundary-condition bug puts its
      // error on the ring; a genuinely different algorithm spreads it everywhere.
      let rs = 0, rc = 0, is = 0, ic = 0;
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const d = Math.abs(B[y * n + x] - A[y * n + x]);
        if (x < 4 || y < 4 || x >= n - 4 || y >= n - 4) { rs += d; rc++; } else { is += d; ic++; }
      }
      return { meanPct: +(100 * (sd / A.length) / range).toFixed(2),
        maxPct: +(100 * wd / range).toFixed(2),
        corr: +(nu / Math.sqrt(da * db || 1e-30)).toFixed(5),
        borderMeanPct: +(100 * (rs / rc) / range).toFixed(2),
        interiorMeanPct: +(100 * (is / ic) / range).toFixed(2) };
    };


    // SAME algorithm both sides - any divergence here is a genuine GPU kernel defect.
    const cmp = (name, cpu, gpu) => {
      USE_GPU = false; const C = Float32Array.from(cpu());
      USE_GPU = true;  const G = Float32Array.from(gpu());
      USE_GPU = false;
      out.kernels.push(Object.assign({ kernel: name }, stats(C, G)));
    };
    const A = { seed: 11, freq: 3, octaves: 6, lac: 2, gain: 0.5 };
    cmp('fbm  [same algo]', () => fbmField(gnoise, A), () => gpuFbm(A));
    cmp('thermal [same algo]',
      () => thermalOn(base, { talus: 0.012, iters: 30, rate: 0.5 }),
      () => gpuThermal(base, { talus: 0.012, iters: 30, rate: 0.5 }));
    cmp('warp [same algo]',
      () => warpField(base, { strength: 0.12, freq: 3, seed: 7 }),
      () => gpuWarp(base, { strength: 0.12, freq: 3, seed: 7 }));
    // DIFFERENT algorithms by construction: the engine picks pipes on GPU and droplets on CPU.
    // Reported to size the swap, NOT as a kernel defect.
    cmp('hydraulic [DIFFERENT MODELS]',
      () => hydraulicErode(base, { droplets: 40000, capacity: 6, erode: 0.35, deposit: 0.28,
        inertia: 0.05, radius: 2, seed: 3, settle: true, gridK: 1 }),
      () => gpuHydraulicPipes(base, { iters: 48, capacity: 6, erode: 0.35, deposit: 0.28,
        inertia: 0.05, gridK: 1 }));
    return out;
  });
  console.log(JSON.stringify(r, null, 1));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
})().catch(e => { console.error('FATAL', e); process.exit(2); });
