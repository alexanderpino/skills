// Is the GPU compute path and the CPU path the same terrain? Noticed while screenshotting the
// lattice work: the app's natural (GPU) build looked very different from a forced-CPU rebuild.
// That comparison was NOT controlled - one was the page's own load path, the other my harness -
// so this measures it properly: identical graph, identical RES, identical dirty-set, ONLY
// USE_GPU differing. Hex forces CPU, so any real divergence here is what hex users inherit.
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
    const build = gpu => { USE_GPU = gpu;
      nodes.forEach(nd => { nd._dirty = true; nd._thumb = null; nd._snowLayer = null;
        nd._temperatureC = null; nd._solarShadow = null; nd._solarExposure = null; nd._wind = null; });
      evalGraph(); return Float32Array.from(outputNode()._field); };
    // NULL HYPOTHESIS FIRST. If two builds with the SAME setting already differ, the GPU/CPU
    // comparison below is measuring rebuild non-determinism or state carryover, not the engine.
    const A1 = build(false), A2 = build(false);
    let sdn = 0; for (let i = 0; i < A1.length; i++) sdn += Math.abs(A2[i] - A1[i]);
    let mn0 = 1e9, mx0 = -1e9; for (const v of A1) { if (v < mn0) mn0 = v; if (v > mx0) mx0 = v; }
    const selfDiff = +(100 * (sdn / A1.length) / (mx0 - mn0)).toFixed(3);
    const G = build(true), C = build(false);
    // Probe gpuReady() WITH USE_GPU set true - it almost certainly ANDs the flag, so probing it
    // after a CPU build reports false no matter what the hardware can do, which is uninformative.
    const gpuActuallyUsed = (() => { const held = USE_GPU; USE_GPU = true;
      let v; try { v = !!gpuReady(); } catch (e) { v = 'unknown'; } USE_GPU = held; return v; })();
    let mn = 1e9, mx = -1e9; for (const v of G) { if (v < mn) mn = v; if (v > mx) mx = v; }
    const range = mx - mn;
    let sd = 0, wd = 0;
    for (let i = 0; i < G.length; i++) { const d = Math.abs(C[i] - G[i]); sd += d; if (d > wd) wd = d; }
    let sa = 0, sb = 0; for (let i = 0; i < G.length; i++) { sa += G[i]; sb += C[i]; }
    const ma = sa / G.length, mb = sb / G.length; let nu = 0, da = 0, db = 0;
    for (let i = 0; i < G.length; i++) { const u = G[i] - ma, v = C[i] - mb; nu += u * v; da += u * u; db += v * v; }
    return { gpuAvailable: gpuActuallyUsed, selfDiffPctOfRange_sameSettingTwice: selfDiff,
      meanDiffPctOfRange: +(100 * (sd / G.length) / range).toFixed(2),
      maxDiffPctOfRange: +(100 * wd / range).toFixed(2),
      correlation: +(nu / Math.sqrt(da * db)).toFixed(5) };
  });
  console.log(JSON.stringify(r, null, 1));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
})().catch(e => { console.error('FATAL', e); process.exit(2); });
