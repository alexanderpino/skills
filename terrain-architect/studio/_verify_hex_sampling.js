// Hex-awareness of the SHARED bilinear resampler, and of its CALLERS
// (references/26-hexagonal-lattice.md).
//
// THE CONTRACT. A resampler answers exactly one question: "what is this field's value at world
// point P?" Chapter 26 states it in those words - verification item 7 compares nodes "sampled at
// identical world (x,y)" - and its GPU note states the failure mode verbatim: "never
// hardware-bilinear - the taps live in a sheared basis (systematic error + half-texel row shear).
// Sample barycentrically in the containing triangle." So: sampleBilinear(f, X, Y) returns f at the
// WORLD point (X, Y) in cell units. On the square lattice grid index space IS world cell space,
// which is why the plain 4-corner form is correct there. On hex the two diverge - odd rows sit
// half a cell right, all rows sit sqrt(3)/2 apart - and BOTH halves have to know it: the sampler
// must place its taps on the lattice, and every caller must hand it world units, not grid indices.
//
// WHY A LINEAR RAMP IS THE UNAMBIGUOUS PROBE. Toggling the lattice legitimately changes a NOISE
// field (generators evaluate at different world points - the seed contract, gated by _verify_hex.js
// H4 at corr 0.9999 vs 0.5681), so noise cannot separate "expected" from "broken". A ramp can:
// build h(X,Y) = a*X + b*Y sampled AT EACH CELL'S TRUE WORLD POINT, and correct interpolation of a
// linear field is EXACT at every world point, on every lattice, forever. Any error is a tap in the
// wrong place. This file carries its own reference hex sampler (axial parallelogram 4-tap, S3) so
// the bound is proved achievable rather than asserted.
//
// ---- MEASURED, RES=192, errors as a fraction of the probed ramp's own range -------------------
// FIRST RUN, against the build as it stood at the start of this session (sampleBilinear was plain
// square 4-corner - f[i], f[i+1], f[i+n], f[i+n+1] - with no hex branch at all, and warpField
// passed raw grid indices):
//   S1 shipped sampler, diagonal ramp, HEX    max 6.072e-02  rms 3.502e-02   <-- RED, the defect
//        X-only ramp (odd-row half-cell shift ignored)  max 2.593e-03 = 0.497 cells
//        Y-only ramp (sqrt(3)/2 row pitch ignored)      max 1.312e-01 (asymptote 1-sqrt(3)/2)
//   S2 shipped sampler, diagonal ramp, SQUARE max 7.44e-17   <-- already exact
//   S3 reference axial 4-tap, HEX             max 4.061e-08  <-- achievable == float32 epsilon
//   warpField end-to-end vs the reference warp: max 11.8% / rms 1.9% of relief.
// SECOND RUN, minutes later, same probes: index.html had been edited concurrently - sampleBilinear
// grew a hex branch (undo each row's OWN parity shift, then blend between rows) and warpField was
// switched to world coordinates. S1 collapsed onto S3 at 4.061e-08. The defect was real, was
// measured red, and was fixed under this oracle mid-session. S1/S2/S3 are kept as the regression
// lock with the red numbers recorded above.
//
// THRESHOLD ARMED AT 1.0e-03 of range: 60.7x below the measured broken value and 2.5e+04x above
// both the fixed sampler and the square control. It also still rejects a half-fix: correcting the
// row pitch but forgetting the odd-row parity leaves ~0.5 cells over the diagonal ramp's 356.9
// range = 1.4e-03, above the bound. Do not raise TOL past 1.4e-03 or that half-fix walks through.
//
// GATES
//   S1 sampler-exact-on-ramp-hex   sampler, hex ramp, world queries      <= 1e-3   PASSES (fixed)
//   S2 square-unaffected           NEGATIVE CONTROL, same probe, square  <= 1e-3   PASSES
//   S3 reference-achievable        POSITIVE CONTROL, axial 4-tap         <= 1e-3   PASSES
//   S4 warp-exact-on-ramp-hex      caller+sampler end to end on the ramp <= 1e-3   PASSES (fixed)
//   S5 callers-pass-world-units    the OTHER half of the same defect, still live: bakeThumb feeds
//                                  grid indices to the now-world-space sampler, so the bottom of
//                                  every hex thumbnail clamps onto the last lattice row. Measured
//                                  5 adjacent-row duplicates = 6 of 48 rows identical = 12.5% of
//                                  the image (predicted: sy > (RES-1.001)*sqrt(3)/2 = 165.4 starts
//                                  at thumbnail row 42, so rows 42..47, exactly 6), against 0 on
//                                  square - the built-in negative control. CURRENTLY FAILS.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));
const TOL = 1e-3;                       // max |error| as a fraction of the probed ramp's range

(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    try { buildRun++; } catch (_) {}
    SCALE_RES = true; XF = null; USE_GPU = false; BUILD_QUALITY = 'interactive';
    Object.assign(terrainDef, { scale: 5000, height: 2600, baseElevation: 0, lattice: 'square' });
    H_SCALE = terrainDef.height / terrainDef.scale;
    RES = 192; const n = RES, H = Math.sqrt(3) / 2, out = {};

    // The seed contract, restated once: cell (x,y) of odd-r offset storage sits at this world
    // point, in CELL units. Every generator applies it; the sampler and its callers must too.
    const cw = (x, y, hex) => hex ? [x + 0.5 * (y & 1), y * H] : [x, y];
    const mkRamp = (a, b2, hex) => { const f = new Float32Array(n * n);
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const w = cw(x, y, hex); f[y * n + x] = a * w[0] + b2 * w[1]; }
      return f; };
    const rng = f => { let mn = Infinity, mx = -Infinity;
      for (let i = 0; i < f.length; i++) { const v = f[i]; if (v < mn) mn = v; if (v > mx) mx = v; }
      return mx - mn; };

    // ---- reference hex sampler: what "hex-aware" means, independently derived -----------------
    // The hex lattice is a Bravais lattice: in AXIAL coordinates (q,r) the map to world is the one
    // linear shear X = q + r/2, Y = r*sqrt(3)/2 - no per-row parity anywhere. Storage relates to
    // axial by q = x - floor(y/2), r = y. The four axial neighbours of a query form a PARALLELOGRAM
    // in world space, and bilinear on a parallelogram is affine, hence exact for a linear field.
    // (26 prefers the 3-tap barycentric form; the 4-tap axial form has the same exactness with one
    // extra fetch, and exactness is what this file measures.) This is deliberately NOT the shape of
    // the shipped fix - it is a second, independent construction that must agree with it.
    const ci = v => v < 0 ? 0 : (v > n - 1 ? n - 1 : v);
    const hexRef = (f, X, Y) => {
      const rr = Y / H, qq = X - 0.5 * rr;
      const r0 = Math.floor(rr), q0 = Math.floor(qq), fr = rr - r0, fq = qq - q0;
      const at = (qi, ri) => f[ci(ri) * n + ci(qi + Math.floor(ri / 2))];
      const t = at(q0, r0) + (at(q0 + 1, r0) - at(q0, r0)) * fq;
      const b3 = at(q0, r0 + 1) + (at(q0 + 1, r0 + 1) - at(q0, r0 + 1)) * fq;
      return t + (b3 - t) * fr;
    };

    // Sub-cell offsets in WORLD cell units. (0,0) is the identity case - a query at a cell's own
    // world point must return that cell's stored value exactly, on either lattice.
    const OFF = [[0,0],[0.5,0],[0,0.5],[0.5,0.5],[0.25,0.75],[0.37,0.61],[0.13,0.87],[0.87,0.13]];
    // Interior stride: the largest world query is ~189.4 in X and ~163.7 in Y, both < n-1, so
    // NOTHING in this probe reaches sampleBilinear's clamp - the error measured is interpolation.
    const probe = (f, a, b2, hex, sampler) => {
      let mx = 0, s2 = 0, m = 0, worst = null;
      for (let y = 4; y < n - 5; y += 7) for (let x = 4; x < n - 5; x += 7) {
        const W = cw(x, y, hex);
        for (const [dx, dy] of OFF) {
          const X = W[0] + dx, Y = W[1] + dy;
          const truth = a * X + b2 * Y, got = sampler(f, X, Y), e = Math.abs(got - truth);
          if (e > mx) { mx = e; worst = { cell: [x, y], world: [+X.toFixed(3), +Y.toFixed(3)],
            got: +got.toFixed(4), truth: +truth.toFixed(4) }; }
          s2 += e * e; m++;
        }
      }
      return { max: mx, rms: Math.sqrt(s2 / m), n: m, worst };
    };
    const fmt = (q, range) => ({ maxAbs: +q.max.toFixed(5), rmsAbs: +q.rms.toFixed(5),
      relMax: +(q.max / range).toExponential(3), relRms: +(q.rms / range).toExponential(3),
      samples: q.n, worst: q.worst });

    // ---- S1 : the shipped sampler on the hex lattice -------------------------------------------
    terrainDef.lattice = 'hex';
    const hXY = mkRamp(1, 1, true), hX = mkRamp(1, 0, true), hY = mkRamp(0, 1, true);
    const rXY = rng(hXY), rX = rng(hX), rY = rng(hY);
    out.hexDiag = fmt(probe(hXY, 1, 1, true, sampleBilinear), rXY);
    out.hexDiag.range = +rXY.toFixed(3);
    out.hexXonly = fmt(probe(hX, 1, 0, true, sampleBilinear), rX);   // odd-row half-cell shift
    out.hexYonly = fmt(probe(hY, 0, 1, true, sampleBilinear), rY);   // sqrt(3)/2 row pitch
    // ---- S3 : positive control, same probe, independent hex-aware sampler ----------------------
    out.hexRef = fmt(probe(hXY, 1, 1, true, hexRef), rXY);

    // ---- S2 : negative control, identical probe on the square lattice --------------------------
    terrainDef.lattice = 'square';
    const sXY = mkRamp(1, 1, false); const rS = rng(sXY);
    out.square = fmt(probe(sXY, 1, 1, false, sampleBilinear), rS);
    out.square.range = +rS.toFixed(3);

    // ---- REPORT : what a STALE caller gets ------------------------------------------------------
    // The caller-side half of the same defect, on the same analytic ramp: hand the sampler GRID
    // INDICES while meaning the cell's world point. This is the number every un-migrated call site
    // is currently paying, and the size of the defect the sampler fix just removed.
    terrainDef.lattice = 'hex';
    { let mx = 0, s2 = 0, m = 0;
      for (let y = 4; y < n - 5; y += 7) for (let x = 4; x < n - 5; x += 7)
        for (const [dx, dy] of OFF) {
          const W = cw(x, y, true), truth = (W[0] + dx) + (W[1] + dy);
          const e = Math.abs(sampleBilinear(hXY, x + dx, y + dy) - truth);
          if (e > mx) mx = e; s2 += e * e; m++;
        }
      out.staleCaller = { maxAbs: +mx.toFixed(4), rmsAbs: +Math.sqrt(s2 / m).toFixed(4),
        relMax: +(mx / rXY).toExponential(3), relRms: +(Math.sqrt(s2 / m) / rXY).toExponential(3) };
    }

    // ---- S4 : warpField end to end on the analytic ramp -----------------------------------------
    // warpField sits at perlin -> blend -> WARP -> hydraulic -> thermal in the DEFAULT graph and is
    // height-critical. Displacing a LINEAR field by a known offset has a closed form, so caller and
    // sampler are gated together with no reference implementation in the loop at all. Cells whose
    // displaced target leaves the footprint are skipped - the sampler legitimately clamps there.
    //
    // Warp is the one node that straddles the authoring domain and the world metric, so its closed
    // form has to be written carefully. The driving noise and the displacement are AUTHORED, so
    // both live in the domain: offsets are domain cell units applied to the domain point. Only the
    // final lookup is a world position, so only there does the row pitch enter. Truth at cell
    // (x,y) is therefore ramp( du+ox , (dv+oy)*sqrt(3)/2 ), NOT ramp(worldPoint + offset) - the
    // latter is what this gate asserted while generators still sampled world v, and it is a real
    // contract change rather than a retuned tolerance. Square is untouched: H=1, du=x, dv=y.
    const WS = { strength: 0.12, freq: 3, seed: 7 };
    const warpRampErr = (hex, dropConversion) => {
      terrainDef.lattice = hex ? 'hex' : 'square';
      const RS = hex ? H : 1;
      const f = mkRamp(1, 1, hex), range = rng(f), o = warpField(f, WS), s = WS.strength * n;
      const yMax = hex ? (n - 1) * H : n - 1;
      let mx = 0, s2 = 0, m = 0, worst = null;
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const du = x + (hex ? 0.5 * (y & 1) : 0), dv = y;           // authoring domain
        const ox = (gnoise(du / n * WS.freq, dv / n * WS.freq, WS.seed) - .5) * 2 * s;
        const oy = (gnoise(du / n * WS.freq, dv / n * WS.freq, WS.seed + 53) - .5) * 2 * s;
        // dropConversion models the specific slip this straddle invites: displacing in the domain
        // and then handing the domain row straight to a world-space sampler.
        const X = du + ox, Y = (dv + oy) * (dropConversion ? 1 : RS);
        if (X < 1 || X > n - 2 || Y < 1 || Y > yMax - 1) continue;    // clamp zone, not a defect
        const e = Math.abs(o[y * n + x] - (X + Y));
        if (e > mx) { mx = e; worst = { cell: [x, y], world: [+X.toFixed(2), +Y.toFixed(2)],
          got: +o[y * n + x].toFixed(3), truth: +(X + Y).toFixed(3) }; }
        s2 += e * e; m++;
      }
      return { maxAbs: +mx.toFixed(5), rmsAbs: +Math.sqrt(s2 / m).toFixed(5),
        relMax: +(mx / range).toExponential(3), relRms: +(Math.sqrt(s2 / m) / range).toExponential(3),
        cells: m, range: +range.toFixed(2), worst };
    };
    out.warpHex = warpRampErr(true, false);
    out.warpSquare = warpRampErr(false, false);
    out.warpNoConvert = warpRampErr(true, true);

    // ---- S5 : the caller contract, measured through a real call site ----------------------------
    // bakeThumb walks sx,sy over 0..RES-1 in GRID INDEX space and hands them straight to the
    // world-space sampler. On hex the field's world height is only (RES-1)*sqrt(3)/2, so every
    // sy above that clamps onto the LAST lattice row: the bottom 1-sqrt(3)/2 = 13.4% of the
    // thumbnail is a smear of one row. Probed with a pure-Y ramp, where a correct thumbnail has
    // every row different from the one above it. Square is the built-in negative control: grid
    // index space IS world cell space there, so the count must be 0.
    const thumbDup = hex => {
      terrainDef.lattice = hex ? 'hex' : 'square';
      const c = bakeThumb({ _field: mkRamp(0, 1, hex) });
      if (!c) return { dup: -1, rows: 0 };
      const w = c.width, h2 = c.height;
      const g = c.getContext('2d').getImageData(0, 0, w, h2).data;
      const rowEq = (r1, r2) => { for (let k = 0; k < w * 4; k++)
        if (g[r1 * w * 4 + k] !== g[r2 * w * 4 + k]) return false; return true; };
      let dup = 0;
      for (let rr = h2 - 1; rr > 0; rr--) { if (rowEq(rr, rr - 1)) dup++; else break; }
      // dup adjacent duplicates == dup+1 identical rows (only when dup>0). Predicted independently
      // from bakeThumb's own sy = y/TH*(RES-1) against the sampler's clamp at world row RES-1.001.
      let pred = 0;
      for (let y = 0; y < h2; y++) if (hex && y / h2 * (n - 1) > (n - 1.001) * H) pred++;
      return { dup, same: dup ? dup + 1 : 0, rows: h2, predicted: pred,
        frac: +((dup ? dup + 1 : 0) / h2).toFixed(4) };
    };
    try { out.thumbHex = thumbDup(true); out.thumbSquare = thumbDup(false); }
    catch (e) { out.thumbErr = String(e && e.message || e); }

    // ---- REPORT : lattice sensitivity of the warp stage ------------------------------------------
    // Before the fix the whole warp stage was byte-identical across the square/hex toggle while
    // every generator feeding it moved - lattice blindness, stated as a hash. It must not be.
    const digest = f => { let a = 0, b2 = 0;
      for (let i = 0; i < f.length; i++) { const q = Math.round(f[i] * 1e7);
        a = (a + q) >>> 0; b2 = (b2 ^ (a + i)) >>> 0; } return a.toString(16) + ':' + b2.toString(16); };
    const A = { seed: 7, freq: 3, octaves: 6, lac: 2, gain: 0.5 };
    terrainDef.lattice = 'square';
    const inp = fbmField(gnoise, A), inR = rng(inp);
    const wSq = warpField(inp, WS);
    terrainDef.lattice = 'hex';
    const wHx = warpField(inp, WS);
    { let s2 = 0, m = 0, mx = 0;
      for (let y = 8; y < n - 8; y++) for (let x = 8; x < n - 8; x++) {
        const e = Math.abs(wHx[y * n + x] - wSq[y * n + x]);
        if (e > mx) mx = e; s2 += e * e; m++; }
      out.toggle = { latticeBlind: digest(wSq) === digest(wHx), inputRange: +inR.toFixed(4),
        relMax: +(mx / inR).toFixed(4), relRms: +(Math.sqrt(s2 / m) / inR).toFixed(4) }; }
    terrainDef.lattice = 'square';
    return out;
  });

  const gates = [];
  const gate = (name, pass, detail) => gates.push({ name, pass: !!pass, detail });

  gate('S1 sampler-exact-on-ramp-hex', r.hexDiag && r.hexDiag.relMax <= TOL,
    `hex lattice, world-linear ramp a*X+b*Y (correct interpolation is EXACT everywhere): `
    + `maxErr=${r.hexDiag.maxAbs} rmsErr=${r.hexDiag.rmsAbs} over range ${r.hexDiag.range} `
    + `=> relMax=${r.hexDiag.relMax} relRms=${r.hexDiag.relRms} (tol ${TOL}, ${r.hexDiag.samples} probes). `
    + `Split by axis: X-only ramp relMax=${r.hexXonly.relMax} (odd-row half-cell shift) `
    + `Y-only ramp relMax=${r.hexYonly.relMax} (sqrt(3)/2 row pitch). `
    + `RED REFERENCE - this same probe read 6.072e-2 / rms 3.502e-2 earlier in this session, on the `
    + `build where sampleBilinear had no hex branch; the bound is armed 60.7x below that.`);

  gate('S2 square-unaffected', r.square && r.square.relMax <= TOL,
    `NEGATIVE CONTROL - identical probe, lattice='square' where grid index space IS world cell `
    + `space: maxErr=${r.square.maxAbs} rmsErr=${r.square.rmsAbs} over range ${r.square.range} `
    + `=> relMax=${r.square.relMax} relRms=${r.square.relRms} (tol ${TOL}), exact to double `
    + `rounding. It read the same on the broken build, so S1's failure there was hex-awareness, `
    + `not the probe.`);

  gate('S3 reference-achievable', r.hexRef && r.hexRef.relMax <= TOL,
    `POSITIVE CONTROL - same hex ramp, same probes, sampled with this file's INDEPENDENT axial `
    + `4-tap (parallelogram basis of the Bravais lattice, not the shape of the shipped fix): `
    + `maxErr=${r.hexRef.maxAbs} => relMax=${r.hexRef.relMax} relRms=${r.hexRef.relRms}. Two `
    + `independent constructions agreeing to float32 epsilon is what makes ${TOL} achievable `
    + `rather than aspirational.`);

  gate('S4 warp-exact-on-ramp-hex', r.warpHex && r.warpHex.relMax <= TOL,
    `warpField (perlin->blend->WARP->hydraulic->thermal, the DEFAULT graph) displacing a `
    + `world-linear ramp has a CLOSED FORM, so caller and sampler are gated together with no `
    + `reference implementation in the loop: hex maxErr=${r.warpHex.maxAbs} rmsErr=${r.warpHex.rmsAbs} `
    + `over range ${r.warpHex.range} => relMax=${r.warpHex.relMax} relRms=${r.warpHex.relRms} `
    + `on ${r.warpHex.cells} unclamped cells (tol ${TOL}). Square control relMax=${r.warpSquare.relMax}. `
    + `TWO live negative controls, both on this same ramp: a stale caller handing grid indices to `
    + `the world-space sampler reads relMax=${r.staleCaller.relMax}, and warp displacing in the `
    + `domain but skipping the world conversion at the lookup reads relMax=${r.warpNoConvert.relMax} `
    + `- that is the size of what S4 holds shut.`);

  gate('S5 callers-pass-world-units', r.thumbHex && r.thumbHex.dup === 0,
    `bakeThumb walks sx,sy over grid indices 0..RES-1 and hands them to the world-space sampler. `
    + `The hex field is only (RES-1)*sqrt(3)/2 = 165.4 cells tall in world units, so every sy above `
    + `that clamps onto the LAST lattice row. Probed with a pure-Y ramp, where a correct thumbnail `
    + `has every row different from the one above: `
    + `${r.thumbHex && r.thumbHex.same}/${r.thumbHex && r.thumbHex.rows} bottom rows come back `
    + `BYTE-IDENTICAL (${r.thumbHex && (r.thumbHex.frac * 100).toFixed(1)}% of the image; predicted `
    + `${r.thumbHex && r.thumbHex.predicted} rows from the 1-sqrt(3)/2 = 13.4% overrun). `
    + `NEGATIVE CONTROL, same probe on square: `
    + `${r.thumbSquare && r.thumbSquare.same}/${r.thumbSquare && r.thumbSquare.rows} - zero, so `
    + `this measures hex caller units, not thumbnail quantisation. Fix: sy must be `
    + `y/TH*(RES-1)*(isHex()?HEX_ROW:1).${r.thumbErr ? ' ERR=' + r.thumbErr : ''}`);

  console.log(`REPORT stale-caller cost  handing GRID INDICES to the world-space sampler on hex costs `
    + `maxErr=${r.staleCaller.maxAbs} rms=${r.staleCaller.rmsAbs} cells of misplacement on the `
    + `diagonal ramp (relMax=${r.staleCaller.relMax}, relRms=${r.staleCaller.relRms}) - `
    + `${(r.staleCaller.relMax / TOL).toFixed(0)}x the gate bound. Call sites still on grid indices `
    + `at the time of writing: bakeThumb / bakeColorThumb (gated by S5), windAtViewFocus and the `
    + `temperature readout (both sample cam.target device coords without the sqrt(3)/2 row recovery `
    + `that surfaceHeight now does - about 0.067*RES = 12.8 cells of offset on hex).`);
  console.log(`REPORT warp lattice-sensitivity  same fBm input, warpField under square vs hex: `
    + `latticeBlind=${r.toggle.latticeBlind} relMax=${r.toggle.relMax} relRms=${r.toggle.relRms} of `
    + `an input range ${r.toggle.inputRange}. On the broken build this read latticeBlind=true - the `
    + `entire warp stage was byte-identical across the toggle while every generator feeding it had `
    + `moved. A lattice-aware warp MUST differ here; it is the S4 ramp, not this number, that says `
    + `whether it differs correctly.`);

  console.log('== hex-aware sampling: the shared resampler and its callers ==');
  let fail = 0;
  for (const g of gates) { console.log(`${g.pass ? 'PASS' : 'FAIL'}  ${g.name}  ${g.detail}`); if (!g.pass) fail++; }
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(fail || errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
