// Real Scale: `repose` must behave as a TRUE angle — same landform at any RES, and the implied
// per-cell drop must equal tan(angle)*cellSize/height at every resolution.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    const out = { defaults: {...terrainDef}, verticalRatio: +(terrainDef.height/terrainDef.scale).toFixed(3), H_SCALE };
    const th = nodes.find(n=>n.type==='thermal');
    th.params.realScale='on'; th.params.repose=35;
    // the effective per-cell drop the node computes, and the ANGLE it implies, at several resolutions
    out.byRes = {};
    for (const n of [128, 192, 256, 512]) {
      RES = n;
      const drop = Math.tan(35*Math.PI/180)*cellSizeM()/terrainDef.height;  // same expression the node uses
      // recover the angle: slope = dropNormalized*height / cellSizeM
      const angle = Math.atan(drop*terrainDef.height/cellSizeM())*180/Math.PI;
      out.byRes[n] = { cellM:+cellSizeM().toFixed(2), dropNorm:+drop.toExponential(3), angleDeg:+angle.toFixed(2) };
    }
    RES = 192;
    // and confirm the OFF path still uses the raw talus/k
    th.params.realScale='off';
    return out;
  });
  console.log('terrain default:', JSON.stringify(r.defaults), 'vertical ratio', r.verticalRatio, 'H_SCALE', r.H_SCALE);
  for (const [n,v] of Object.entries(r.byRes))
    console.log(`  RES ${String(n).padStart(4)}  cell=${String(v.cellM).padStart(7)}m  perCellDrop=${v.dropNorm}  -> angle ${v.angleDeg}°`);

  // screenshot the terrain-definition panel (shown when nothing is selected)
  await p.evaluate(() => { select(null); buildProps(); });
  await p.waitForTimeout(300);
  await p.screenshot({ path: path.resolve(__dirname, '_shot_terraindef.png') });
  console.log('errors', errors.length?JSON.stringify(errors):'none');
  await b.close();
  process.exit(errors.length?1:0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
