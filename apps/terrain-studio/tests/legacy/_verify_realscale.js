// Real Scale: `repose` must behave as a TRUE angle — same landform at any RES, and the implied
// per-cell drop must equal tan(angle)*cellSize/height at every resolution.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    // BUILD THE DOCUMENT THIS FILE MEASURES. D7 demoted the 18-node showcase and made the opening
    // document L0 bedrock (perlin, ridged, blend, d_height, heightmask, levels, output). L0 has no
    // thermal node, so `nodes.find(n=>n.type==='thermal')` returned undefined and the evaluate died
    // on `.params` (measured: FATAL, exit 2).
    //
    // evalGraph() is sufficient; a full #buildBtn build is NOT needed. Nothing here reads curHgt /
    // curFilled / curAccum, renders a frame, or asserts on a pixel — the screenshot below is a
    // diagnostic of the properties panel, not a measurement. evalGraph() is still called rather
    // than showcaseGraph() alone so the app's derived state (scene, viewport, thumbnails, node
    // stats) belongs to the document the panel is photographed over; a full build would add the
    // hydraulic and snow simulations for no assertion.
    nodes.length = 0; edges.length = 0; uid = 1; selected = null; selectedEdge = null;
    showcaseGraph(); evalGraph();

    const out = { defaults: {...terrainDef}, verticalRatio: +(terrainDef.height/terrainDef.scale).toFixed(3), H_SCALE };
    const th = nodes.find(n=>n.type==='thermal');
    if (!th) throw new Error('SETUP FAILURE: no thermal node after showcaseGraph()');

    // THE PARAM SCHEMA IS A REAL GATE and this one has failed before: thermal.js records that when
    // cell units shipped as the default, the Repose slider did not exist on a fresh node, so
    // repose 25 and repose 45 measured IDENTICAL slope percentiles — the node's only physical
    // control was unreachable out of the box. Read the shipped schema and hold that shape.
    const ps = {}; TYPES.thermal.params.forEach(q => { ps[q.key] = q; });
    for (const k of ['realScale','repose','talus'])
      if (!ps[k]) throw new Error(`SETUP FAILURE: thermal has no '${k}' param`);
    out.schema = {
      realScaleDefault: ps.realScale.def,
      reposeDefault: ps.repose.def, reposeMin: ps.repose.min, reposeMax: ps.repose.max,
      reposeShownWhen: ps.repose.when && `${ps.repose.when.key}=${(ps.repose.when.values||[]).join(',')}`,
      talusShownWhen:  ps.talus.when  && `${ps.talus.when.key}=${(ps.talus.when.values||[]).join(',')}`,
    };

    const RES0 = RES;               // measured 512 — the app default. The old code restored a
                                    // hardcoded 192 (REF_RES), leaving the app at a resolution its
                                    // GPU buffers were not built for, under the screenshot below.
    th.params.realScale='on'; th.params.repose=35;
    // The effective per-cell drop the node computes, and the angle it implies, at several
    // resolutions. NOTE WHAT THIS IS AND IS NOT: `angleDeg` re-derives the node's own expression
    // and then inverts it, so atan(tan(t)*c/H * H/c) === t identically — it is DOCUMENTATION of the
    // formula at thermal.js:27, and it CANNOT FAIL. It is printed, deliberately not asserted on.
    // What IS asserted is cellSizeM() itself: cellM*RES must equal terrainDef.scale at every
    // resolution, which is what makes `repose` resolution independent in the first place. If
    // cellSizeM() ever stopped tracking RES (a constant, or REF_RES) three of these four rows break.
    out.byRes = {};
    for (const n of [128, 192, 256, 512]) {
      RES = n;
      const cell = cellSizeM();
      const drop = Math.tan(35*Math.PI/180)*cell/terrainDef.height;  // same expression the node uses
      const angle = Math.atan(drop*terrainDef.height/cell)*180/Math.PI;
      out.byRes[n] = { cellM:+cell.toFixed(2), cellTimesRes:+(cell*n).toFixed(6),
                       dropNorm:+drop.toExponential(3), angleDeg:+angle.toFixed(2) };
    }
    RES = RES0;
    // Leave the node as showcaseGraph() shipped it (cell units), so nothing downstream inherits a
    // document this oracle mutated.
    th.params.realScale='off';
    out.resRestored = RES === RES0;
    out.hScaleSynced = H_SCALE === terrainDef.height/terrainDef.scale;
    return out;
  });
  console.log('terrain default:', JSON.stringify(r.defaults), 'vertical ratio', r.verticalRatio, 'H_SCALE', r.H_SCALE);
  for (const [n,v] of Object.entries(r.byRes))
    console.log(`  RES ${String(n).padStart(4)}  cell=${String(v.cellM).padStart(7)}m  cell*RES=${v.cellTimesRes}  perCellDrop=${v.dropNorm}  -> angle ${v.angleDeg}° (identity, not a gate)`);
  console.log('schema:', JSON.stringify(r.schema));

  // screenshot the terrain-definition panel (shown when nothing is selected)
  await p.evaluate(() => { select(null); buildProps(); });
  await p.waitForTimeout(300);
  await p.screenshot({ path: path.resolve(__dirname, '_shot_terraindef.png') });
  console.log('errors', errors.length?JSON.stringify(errors):'none');

  // This file printed all of the above and then exited on `errors.length` alone. Every bound below
  // reads a value the APP owns, never one this oracle computed. Measured: scale 5000 m, height
  // 2600 m, H_SCALE 0.52, cell*RES = 5000 at 128/192/256/512, RES default 512.
  const scale = r.defaults.scale;
  // cellSizeM() = terrainDef.scale/RES. This is the single fact `repose` depends on for resolution
  // independence, and it is measured at four resolutions, not asserted at one.
  const cellOk = Object.values(r.byRes).length === 4
    && Object.values(r.byRes).every(v => Math.abs(v.cellTimesRes - scale) < 1e-6 && v.cellM > 0);
  // H_SCALE is a SEPARATE global re-synced by hand at four sites in legacy.js; it drifting from
  // terrainDef is a real failure mode, not an identity.
  const s = r.schema;
  const schemaOk = s.realScaleDefault === 'on'          // cell units as default hid the Repose slider
    && s.reposeDefault === 35 && s.reposeMin === 15 && s.reposeMax === 60
    && s.reposeShownWhen === 'realScale=on' && s.talusShownWhen === 'realScale=off';
  const ok = cellOk && schemaOk && r.hScaleSynced && r.resRestored && !errors.length;
  console.log(JSON.stringify({ cellOk, schemaOk, hScaleSynced: r.hScaleSynced, resRestored: r.resRestored, ok }));
  await b.close();
  process.exit(ok?0:1);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
