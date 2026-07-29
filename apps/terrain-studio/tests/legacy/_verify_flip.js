// FLIP-SMOKE — the only MC-1 gate that exercises nh != n, and therefore the only one that can
// tell "conversion complete" from "nothing done".
//
// Every other gate in that item runs with HEX_SQUARE_WORLD false, where latticeRows(w) === w and
// each edit is numerically a no-op; a plan review found the original acceptance set passed on the
// UNMODIFIED file for exactly that reason. So this runs against a scratch copy of index.html with
// the gate forced true, builds the default graph on hex, and measures what only a taller field can
// show: non-finite values, short buffers, and rows n..nh-1 that no kernel ever wrote.
//
//   --baseline   record the RED endpoint. FAILS if it finds nothing wrong, because an empty
//                baseline is not evidence of a healthy build - it is evidence of a dead probe.
//   (default)    assert the fix. Requires zero failing nodes AND a healthy probe.
//
// Named as _verify_* deliberately: .gitignore excludes _*.js and negates only !_verify*.js, and a
// red baseline that cannot be committed is not reproducible from the commit it justifies - the
// same evidence gap this check exists to close.
//
// Usage: STUDIO_URL=file:///.../index_flipped.html node _verify_flip.js [--baseline]
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));
const BASELINE = process.argv.includes('--baseline');
// Pinned from the recorded red baseline (evidence/MC-1/red-baseline.md): 18 node fields plus 11
// side channels. --baseline mode does not pin it, because that run is what establishes the number.
const EXPECT_RECORDS = BASELINE ? 0 : +(process.env.FLIP_EXPECT_RECORDS || 29);

(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1000, height: 720 } });
  const errors = []; p.on('pageerror', e => errors.push(String(e.message).slice(0, 200)));
  let booted = true, bootErr = null;
  try { await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(2500); }
  catch (e) { booted = false; bootErr = String(e).slice(0, 300); }

  const r = booted ? await p.evaluate(() => {
    const out = { gateTrue: null, n: null, nh: null, nodes: [], sideChannels: [], buffers: null,
      evalError: null, fatal: null, featForced: null };
    try {
      out.gateTrue = (typeof HEX_SQUARE_WORLD !== 'undefined') ? !!HEX_SQUARE_WORLD : 'undefined';
      SCALE_RES = true; XF = null; USE_GPU = false; BUILD_QUALITY = 'interactive';
      RES = 192; TARGET_RES = 192;
      terrainDef.lattice = 'hex';
      buildIndex();
      const n = fieldW(), nh = fieldH(), want = n * nh;
      out.n = n; out.nh = nh; out.expectLen = want;

      // atFeatureScale short-circuits at k <= 1.02 (index.html:2593), and the default hydraulic
      // node ships feat:1 - so the item's self-declared highest-severity defect could not fire on
      // the stock graph. Force it above the threshold so the NaN routes are actually in scope.
      for (const nd of nodes) if (nd.params && nd.params.feat != null && nd.params.feat <= 1.02) {
        nd.params.feat = 1.6; out.featForced = (out.featForced || 0) + 1;
      }

      nodes.forEach(nd => { nd._dirty = true; nd._thumb = null; nd._snowLayer = null;
        nd._temperatureC = null; nd._solarShadow = null; nd._solarExposure = null; nd._wind = null; });
      try { evalGraph(); } catch (e) { out.evalError = String(e.message).slice(0, 300); }

      const band = (f, y0, y1) => { let s = 0, k = 0;
        for (let y = y0; y < y1 - 1; y++) for (let x = 1; x < n - 1; x++) {
          const d = f[(y + 1) * n + x] - f[y * n + x];
          if (Number.isFinite(d)) { s += Math.abs(d); k++; } }
        return k ? s / k : 0; };
      const inspect = (label, f) => {
        if (!f || !f.length) return { label, fail: 'missing' };
        const rec = { label, len: f.length };
        let bad = 0; for (let i = 0; i < f.length; i++) if (!Number.isFinite(f[i])) bad++;
        rec.nonFinite = bad;
        const fails = [];
        if (bad > 0) fails.push('nonFinite=' + bad);
        if (f.length % n === 0) {
          const rows = f.length / n;
          if (rows !== nh) fails.push('rows=' + rows + ' want ' + nh);
          else if (nh > n) {
            const h = nh - n, m0 = Math.max(1, (n - h) >> 1);
            const bot = band(f, n, nh), mid = band(f, m0, m0 + h);
            rec.ratio = mid > 1e-12 ? +(bot / mid).toFixed(4) : null;
            if (mid > 1e-12 && bot / mid < 0.1) fails.push('deadBottom ratio=' + rec.ratio);
            // A band average hides a PARTLY dead band: half the extra rows frozen still averages
            // above the threshold. Check the worst individual row too.
            if (mid > 1e-12) { let worst = Infinity, worstRow = -1;
              for (let y = n; y < nh - 1; y++) { const e = band(f, y, y + 2);
                if (e < worst) { worst = e; worstRow = y; } }
              rec.worstRow = worstRow; rec.worstRatio = +(worst / mid).toFixed(4);
              if (worst / mid < 0.02) fails.push('deadRow ' + worstRow + ' ratio=' + rec.worstRatio);
            }
          }
        } else fails.push('len=' + f.length + ' not a multiple of n=' + n);
        if (fails.length) rec.fail = fails.join(' | ');
        return rec;
      };

      for (const nd of nodes) {
        const rec = inspect(nd.type, nd._field); rec.type = nd.type; out.nodes.push(rec);
        // SIDE CHANNELS. The review found the first version nulled these to force recompute and
        // then never read them - so jacobi/evaluateTerrainWind, climateSolarExposure and the snow
        // layer were all outside the probe while being named as covered by it.
        const sc = [];
        if (nd._wind && nd._wind.u) { sc.push(['wind.u', nd._wind.u], ['wind.v', nd._wind.v]); }
        if (nd._temperatureC) sc.push(['temperatureC', nd._temperatureC]);
        if (nd._solarExposure) sc.push(['solarExposure', nd._solarExposure]);
        if (nd._solarShadow) sc.push(['solarShadow', nd._solarShadow]);
        if (nd._snowLayer && nd._snowLayer.depthM) sc.push(['snow.depthM', nd._snowLayer.depthM]);
        for (const [nm, arr] of sc) {
          const s = inspect(nd.type + ':' + nm, arr); s.type = nd.type + ':' + nm;
          out.sideChannels.push(s);
        }
      }

      // Render-path buffers: the mesh/wire counts, which no node _field reaches. Guarded - a throw
      // here is reported, never swallowed.
      //
      // buildWireIndex() must be called EXPLICITLY. Its only caller is the `if(wire)` branch of the
      // draw path, and `wire` is false until the overlay button is pressed, so updateViewport()
      // alone never builds the edge buffer: buffers.lineCount would read undefined at baseline AND
      // after a perfect conversion, making this sub-gate impossible to satisfy. A gate that cannot
      // go green gets waived, and a waived gate is how vacuity gets back in.
      try {
        updateViewport();
        buildWireIndex();
        const wantVerts = n * nh;
        out.buffers = {
          count: buffers.count, wantCount: (n - 1) * (nh - 1) * 6,
          lineCount: buffers.lineCount,
          wantLineCount: 2 * (3 * (n - 1) * (nh - 1) + (n - 1) + (nh - 1)),
          builtLattice: buffers.builtLattice, wantVerts
        };
        out.buffers.ok = out.buffers.count === out.buffers.wantCount
          && out.buffers.lineCount === out.buffers.wantLineCount;
      } catch (e) { out.buffers = { error: String(e.message).slice(0, 200) }; }
    } catch (e) { out.fatal = String(e.message).slice(0, 300); }
    return out;
  }) : {};

  const allRecs = [...(r.nodes || []), ...(r.sideChannels || [])];
  const failed = allRecs.filter(x => x.fail);
  const bufFail = r.buffers && (r.buffers.error || r.buffers.ok === false);

  console.log('== FLIP-SMOKE ' + (BASELINE ? '(RED BASELINE)' : '(ASSERT)') + ' ==');
  console.log('gate HEX_SQUARE_WORLD =', r.gateTrue, ' n =', r.n, ' nh =', r.nh,
    ' expectLen =', r.expectLen, ' featForced =', r.featForced);
  if (!booted) console.log('BOOT FAILED:', bootErr);
  if (r.fatal) console.log('FATAL(in-page):', r.fatal);
  if (r.evalError) console.log('evalGraph threw:', r.evalError);
  if (r.buffers) console.log('buffers:', JSON.stringify(r.buffers));
  console.log('records inspected: ' + allRecs.length + '  failing: ' + failed.length);
  for (const f of failed) console.log('  ' + String(f.type || f.label).padEnd(26) + f.fail);
  console.log('pageerrors', errors.length ? JSON.stringify(errors.slice(0, 6)) : 'none');
  console.log('NAMED_RED=' + failed.map(f => f.type || f.label).sort().join(','));
  console.log('RECORD_COUNT=' + allRecs.length);

  // PROBE HEALTH is scored, not printed and ignored. The first version exited 0 unconditionally,
  // so an in-page throw produced an empty failure list that read as a clean pass.
  const unhealthy = [];
  if (!booted) unhealthy.push('did not boot');
  if (r.fatal) unhealthy.push('in-page fatal');
  if (r.evalError) unhealthy.push('evalGraph threw');
  if (errors.length) unhealthy.push(errors.length + ' pageerror(s)');
  if (!allRecs.length) unhealthy.push('inspected nothing');
  if (r.gateTrue !== true) unhealthy.push('gate is not true - wrong file under test');
  // The gate being true is not the same as the gate DOING anything. If latticeRows() ever regresses
  // to returning w, nh===n and every shape check below is trivially satisfied while the feature is
  // absent. Require the field to actually be taller.
  if (!(r.nh > r.n)) unhealthy.push('nh (' + r.nh + ') is not greater than n (' + r.n + ') - the square-world row count is not in effect');
  // Vacuity by ABSENCE: side-channel records are only collected when the channel EXISTS, so a build
  // that silently stops computing wind, snow or temperature loses those records and the remaining
  // ones still pass. Pin the count. This is the same class d2f6769 closed for lineCount.
  if (EXPECT_RECORDS && allRecs.length !== EXPECT_RECORDS)
    unhealthy.push('record count ' + allRecs.length + ' != expected ' + EXPECT_RECORDS + ' - a node or side channel stopped being produced');
  if (r.buffers && r.buffers.error) unhealthy.push('buffer probe threw');

  let bad = 0;
  if (unhealthy.length) { console.log('FAIL  probe-health  ' + unhealthy.join('; ')); bad++; }
  else console.log('PASS  probe-health  booted, gate true, ' + allRecs.length + ' records, no page errors');

  if (BASELINE) {
    // An empty red baseline means the probe is blind, not that the build is well.
    if (!failed.length && !bufFail) { console.log('FAIL  baseline-non-empty  found NOTHING wrong with the gate forced true; a probe that cannot see the defect cannot arm a gate against it'); bad++; }
    else console.log('PASS  baseline-non-empty  ' + (failed.length + (bufFail ? 1 : 0)) + ' named failure(s) recorded as the red endpoint');
  } else {
    if (failed.length) { console.log('FAIL  zero-failures  ' + failed.length + ' record(s) still failing at nh != n'); bad++; }
    else console.log('PASS  zero-failures  every field and side channel finite, full height, live to the bottom row');
    if (bufFail) { console.log('FAIL  buffers  ' + JSON.stringify(r.buffers)); bad++; }
    else if (r.buffers) console.log('PASS  buffers  count and lineCount match the hex analytic forms');
  }
  await b.close();
  process.exit(bad ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
