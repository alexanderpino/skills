// Visual confirmation that the numbers mean what they claim: render the DEFAULT graph on each
// lattice and write both PNGs. Numbers say corr 0.992; eyes say whether anything is visibly wrong
// (row-parity tearing, a re-rolled landscape, a broken mesh). Driven through the REAL UI toggle
// and the app's own frame loop - calling drawTerrain() directly bypasses the projection setup.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const URL = 'file://' + path.resolve(__dirname, 'index.html');
const OUT = process.env.SHOT_DIR || __dirname;
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1000, height: 720 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(3000);
  // Force CPU on BOTH. GPU compute is disabled on hex, so an unforced pair differs by compute
  // path as well as lattice - which would confound exactly the thing this is meant to isolate.
  await p.evaluate(() => { USE_GPU = false; cam.dist = 2.15; cam.el = .58; cam.az = .72; });
  // The Terrain-definition panel builds its buttons lazily, so drive the exact code path the
  // button's onclick runs instead of depending on that panel being open.
  for (const [i, lat] of [[0, 'square'], [1, 'hex']]) {
    await p.evaluate(l => {
      // Rebuild UNCONDITIONALLY, including for square. Returning early when the lattice already
      // matches would leave square showing the GPU build made at page load, and the whole point
      // is that both sides run the same compute path.
      USE_GPU = false;
      terrainDef.lattice = l;
      buildIndex(); nodes.forEach(nd => { nd._dirty = true; nd._thumb = null; nd._snowLayer = null;
        nd._temperatureC = null; nd._solarShadow = null; nd._solarExposure = null; nd._wind = null; });
      requestEval(); tdInfo();
    }, lat);
    await p.waitForTimeout(30000);
    // Force CPU on BOTH. GPU compute is disabled on hex, so an unforced pair differs by compute
  // path as well as lattice - which would confound exactly the thing this is meant to isolate.
  await p.evaluate(() => { USE_GPU = false; cam.dist = 2.15; cam.el = .58; cam.az = .72; });
    await p.waitForTimeout(1500);
    await p.screenshot({ path: path.join(OUT, `_shot_${lat}.png`) });
    const lt = await p.evaluate(() => terrainDef.lattice);
    console.log(`wrote _shot_${lat}.png (live lattice = ${lt})`);
  }
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
})().catch(e => { console.error('FATAL', e); process.exit(2); });
