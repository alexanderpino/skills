// The user-facing question, measured end to end on the DEFAULT graph rather than on one fbm node:
// toggle Grid -> Hex with the same seed and everything else unchanged. How different is the terrain?
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const URL = 'file://' + path.resolve(__dirname, 'index.html');
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1100, height: 800 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(2000);
  const r = await p.evaluate(() => {
    SCALE_RES = true; XF = null; USE_GPU = false; BUILD_QUALITY = 'interactive';
    RES = 192; TARGET_RES = 192;
    const build = lat => { terrainDef.lattice = lat; buildIndex();
      nodes.forEach(nd => { nd._dirty = true; nd._thumb = null; nd._snowLayer = null;
        nd._temperatureC = null; nd._solarShadow = null; nd._solarExposure = null; nd._wind = null; });
      evalGraph(); return Float32Array.from(outputNode()._field); };
    const S = build('square'), Hx = build('hex');
    terrainDef.lattice = 'square'; buildIndex();
    nodes.forEach(nd => { nd._dirty = true; }); evalGraph();
    let mn = 1e9, mx = -1e9; for (const v of S) { if (v < mn) mn = v; if (v > mx) mx = v; }
    const range = mx - mn;
    let sd = 0, wd = 0;
    for (let i = 0; i < S.length; i++) { const d = Math.abs(Hx[i] - S[i]); sd += d; if (d > wd) wd = d; }
    let sa = 0, sb = 0; for (let i = 0; i < S.length; i++) { sa += S[i]; sb += Hx[i]; }
    const ma = sa / S.length, mb = sb / S.length; let nu = 0, da = 0, db = 0;
    for (let i = 0; i < S.length; i++) { const u = S[i] - ma, v = Hx[i] - mb; nu += u * v; da += u * u; db += v * v; }
    return { meanDiffPctOfRange: +(100 * (sd / S.length) / range).toFixed(2),
      maxDiffPctOfRange: +(100 * wd / range).toFixed(2),
      correlation: +(nu / Math.sqrt(da * db)).toFixed(5),
      squareMeanM: +ma.toFixed(1), hexMeanM: +mb.toFixed(1), rangeM: +range.toFixed(1) };
  });
  console.log(JSON.stringify(r, null, 1));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
})().catch(e => { console.error('FATAL', e); process.exit(2); });
