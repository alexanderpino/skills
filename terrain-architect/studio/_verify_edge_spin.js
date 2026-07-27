// Adaptive terrain topology regression: ridge/valley-aware normal fitting, deterministic
// planar ties, bounded staging memory, and the actual uploaded element buffer.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(1400);

  const report = await page.evaluate(() => {
    const choose = (delta,x,y) => Math.abs(delta) <= 1e-6 ? !!((x+y)&1) : delta < 0;
    const mainRidgeDelta = terrainQuadFitDelta(0,-1,-1,0, 0,0,-1,1,1,-1,0,0);
    const antiRidgeDelta = terrainQuadFitDelta(-1,0,0,-1, 1,1,0,0,0,0,-1,-1);
    const mainValleyDelta = terrainQuadFitDelta(0,1,1,0, 0,0,1,-1,-1,1,0,0);
    const antiValleyDelta = terrainQuadFitDelta(1,0,0,1, -1,-1,0,0,0,0,1,1);
    const planarDelta = terrainQuadFitDelta(0,1,2,3, 1,2,1,2,1,2,1,2);
    const choice = {
      mainRidge:choose(mainRidgeDelta,0,0),antiRidge:choose(antiRidgeDelta,0,0),
      mainValley:choose(mainValleyDelta,0,0),antiValley:choose(antiValleyDelta,0,0),
      planarDelta,tieEven:choose(planarDelta,0,0),tieOdd:choose(planarDelta,1,0)
    };
    const stats = { ...buffers.edgeSpin };
    const rows = Math.min(8, RES - 1), count = rows * (RES - 1) * 6;
    const actual = buffers.u32 ? new Uint32Array(count) : new Uint16Array(count);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buffers.idx);
    gl.getBufferSubData(gl.ELEMENT_ARRAY_BUFFER, 0, actual);
    const snow = scene.snow && scene.snow.layer && scene.snow.layer.depthM;
    const snowScale = snow && snow.length === RES * RES ? 1 / terrainDef.height : 0;
    const sample = i => curHgt[i] + (snowScale ? snow[i] * snowScale : 0);
    const gradient = (x,y) => [Math.fround((sample(y*RES+Math.min(RES-1,x+1))-sample(y*RES+Math.max(0,x-1)))*.5),
      Math.fround((sample(Math.min(RES-1,y+1)*RES+x)-sample(Math.max(0,y-1)*RES+x))*.5)];
    let checked = 0, mismatches = 0, windingErrors = 0;
    for (let y = 0; y < rows; y++) for (let x = 0; x < RES - 1; x++) {
      const i = y * RES + x, q = (y * (RES - 1) + x) * 6;
      const h00=sample(i),h10=sample(i+1),h01=sample(i+RES),h11=sample(i+RES+1);
      const g00=gradient(x,y),g10=gradient(x+1,y),g01=gradient(x,y+1),g11=gradient(x+1,y+1);
      const delta=terrainQuadFitDelta(h00,h10,h01,h11,
        g00[0],g00[1],g10[0],g10[1],g01[0],g01[1],g11[0],g11[1]);
      const main=choose(delta,x,y);
      const uploadedMain = actual[q + 2] === i + RES + 1;
      if (main !== uploadedMain) mismatches++;
      const expected = main
        ? [i,i+1,i+RES+1, i,i+RES+1,i+RES]
        : [i,i+1,i+RES, i+1,i+RES+1,i+RES];
      for (let k = 0; k < 6; k++) if (actual[q + k] !== expected[k]) windingErrors++;
      checked++;
    }
    const revision = stats.revision;
    updateViewport(curField, activePreviewNode(), { color:false });
    return { choice, stats, checked, mismatches, windingErrors,
      noOpPreservedTopology:buffers.edgeSpin.revision === revision,
      indexedDraw:buffers.count === (RES - 1) * (RES - 1) * 6 };
  });

  const ok = report.choice.mainRidge && !report.choice.antiRidge
    && report.choice.mainValley && !report.choice.antiValley
    && Math.abs(report.choice.planarDelta) < 1e-12
    && !report.choice.tieEven && report.choice.tieOdd
    && report.stats.adaptive
    && report.stats.quadCount === (512 - 1) * (512 - 1)
    && report.stats.mainCount > 0 && report.stats.antiCount > 0
    && report.stats.mainCount + report.stats.antiCount === report.stats.quadCount
    && report.stats.flipsFromCheckerboard > 0
    && report.stats.fitGain > 0 && report.stats.fitStrength > report.stats.fitGain
    && report.stats.stagingBytes <= 3 * 1024 * 1024
    && report.stats.durationMs < 500
    && report.checked > 4000 && report.mismatches === 0 && report.windingErrors === 0
    && report.noOpPreservedTopology && report.indexedDraw && !errors.length;
  console.log(JSON.stringify({ ...report, errors, ok }, null, 2));
  await browser.close();
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
