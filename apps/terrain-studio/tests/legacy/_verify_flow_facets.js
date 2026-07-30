// Does flow routing snap drainage onto the lattice's own directions?
//
// THE DEFECT D6 DOES NOT FIX, AND MAKES WORSE. Going hex buys isotropy nearly everywhere, but not
// here: single-receiver routing sends ALL of a cell's water to ONE neighbour, so the realisable flow
// directions are exactly the lattice's own. D8 offers 8 at 45 degrees (max aspect error 22.5); D6
// offers 6 at 60 (max error 30). On this one measure hex is COARSER than square, which is why `26`
// records MFD as the thing that actually delivers "smoother and more natural" - D6 alone does not.
//
// THE TEST SURFACE is a cone: radially symmetric, so the true drainage is radial and every azimuth
// must carry the SAME area. There is no parameter to tune and no reference image to eyeball - the
// correct answer is dictated by the surface's symmetry. Any azimuthal structure in the result was
// put there by the router.
//
// THE MEASUREMENT. Take an annulus, bin its cells by azimuth, and average drainage area per cell in
// each bin. A perfect router gives a flat histogram (concentration 1.0). A single-receiver router
// gives spokes along the lattice axes, and max/mean reports how tall they are. Cells are binned by
// WORLD azimuth - on hex a row step is sqrt(3)/2 of a column step, and array-space angles would
// invent a six-fold pattern of their own.
//
// `26` records prior art at hex facet concentration 1.413 vs corrected-D8 1.17, measured by a
// different harness. The endpoints this file arms against are its own, measured below.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

let failures = 0;
const gate = (name, ok, detail) => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}  ${detail}`); if (!ok) failures++; };

(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  const errors = []; p.on('pageerror', (e) => errors.push(String(e.message).slice(0, 200)));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    const HEXR = Math.sqrt(3) / 2, BINS = 36;
    SCALE_RES = true; XF = null; USE_GPU = false; BUILD_QUALITY = 'interactive';
    Object.assign(terrainDef, { scale: 5000, height: 2600, baseElevation: 0, lattice: 'square' });
    RES = 192;

    const measure = (lattice) => {
      terrainDef.lattice = lattice;
      const n = fieldW(), nh = fieldH(), hex = lattice === 'hex';
      const wx = (x, y) => x + (hex ? 0.5 * (y & 1) : 0);
      const wy = (y) => y * (hex ? HEXR : 1);

      // A cone in WORLD space, so both lattices sample the identical continuous surface. Height
      // falls off linearly with world radius; the apex sits at the field's world centre.
      const ox = wx(n >> 1, nh >> 1), oy = wy(nh >> 1);
      const R = Math.min(ox, oy) * 0.92;
      const f = newField();
      for (let y = 0; y < nh; y++) for (let x = 0; x < n; x++) {
        const dx = wx(x, y) - ox, dy = wy(y) - oy;
        f[y * n + x] = Math.max(0, 1 - Math.hypot(dx, dy) / R);
      }

      const A = d8Accumulation(priorityFloodFill(f));

      // Annulus well inside the cone: far enough from the apex that azimuth is well resolved, far
      // enough from the base that the flat outside the cone plays no part.
      const rIn = 0.30 * R, rOut = 0.60 * R;
      const sum = new Float64Array(BINS), cnt = new Float64Array(BINS);
      for (let y = 0; y < nh; y++) for (let x = 0; x < n; x++) {
        const dx = wx(x, y) - ox, dy = wy(y) - oy, rr = Math.hypot(dx, dy);
        if (rr < rIn || rr > rOut) continue;
        let a = Math.atan2(dy, dx); if (a < 0) a += 2 * Math.PI;
        const bin = Math.min(BINS - 1, Math.floor(a / (2 * Math.PI) * BINS));
        sum[bin] += A[y * n + x]; cnt[bin] += 1;
      }
      let mn = Infinity, mx = -Infinity, tot = 0, used = 0, empty = 0;
      const prof = [];
      for (let k = 0; k < BINS; k++) {
        if (cnt[k] < 4) { empty++; prof.push(0); continue; }
        const v = sum[k] / cnt[k];
        prof.push(+v.toFixed(2));
        if (v < mn) mn = v; if (v > mx) mx = v; tot += v; used++;
      }
      const mean = tot / Math.max(1, used);
      return {
        lattice, n, nh, bins: BINS, usedBins: used, emptyBins: empty,
        concentration: +(mx / Math.max(mean, 1e-12)).toFixed(4),
        minOverMean: +(mn / Math.max(mean, 1e-12)).toFixed(4),
        meanArea: +mean.toFixed(2),
        profile: prof,
      };
    };

    const out = { square: measure('square'), hex: measure('hex') };
    terrainDef.lattice = 'square';
    return out;
  });

  for (const lat of ['square', 'hex'])
    console.log(`${lat}  concentration=${r[lat].concentration}  min/mean=${r[lat].minOverMean}  `
      + `bins=${r[lat].usedBins}/${r[lat].bins} (empty ${r[lat].emptyBins})  meanArea=${r[lat].meanArea}`);
  console.log('square profile', JSON.stringify(r.square.profile));
  console.log('hex    profile', JSON.stringify(r.hex.profile));

  for (const lat of ['square', 'hex']) {
    const m = r[lat];
    // CONTROLS ON THE MEASUREMENT. Empty azimuth bins would make max/mean read off a handful of
    // cells; a collapsed mean area would mean the cone never drained at all and every bin is 1.
    gate(`flow-bins-populated-${lat}`, m.emptyBins === 0,
      `${m.usedBins}/${m.bins} bins had >=4 cells — an empty bin would make the ratio noise`);
    gate(`flow-drained-${lat}`, m.meanArea > 3,
      `mean drainage area in the annulus = ${m.meanArea} cells — a surface that did not route would `
      + `sit at 1 everywhere and report a perfect concentration of 1.0 for the wrong reason`);
  }

  // ALL EIGHT D8 DIRECTIONS MUST CARRY DRAINAGE. On a cone the steepest-descent receiver is the
  // neighbour whose direction is closest to radial, so a correct D8 router lays down EIGHT spokes -
  // four on the axes, four on the diagonals. d8Accumulation used to pick the LOWEST neighbour over
  // a table with no distances, and on a smooth slope the diagonal is sqrt(2) further and therefore
  // always lower, so it always won: four spokes, and the axial directions were never chosen at all.
  //
  // This is the assertion that actually pins the fix. Concentration does NOT - see the report line
  // below - because a single-receiver router snaps every cell to some lattice direction whatever
  // rule picks it, so the spokes merely MOVED. Measured, axis-bin mean over diagonal-bin mean:
  //     lowest-neighbour (before)   0.1382    axes starved: 3.91 against 28.25
  //     steepest-descent (after)    1.2547    both families present: 33.21 against 26.47
  // Armed at 0.5: an order of magnitude above the broken value and clear of the correct one. Square
  // only - hex has no axis/diagonal distinction, all six neighbours being one cell away, which is
  // also why hex is bit-identical across this change.
  const prof = r.square.profile;
  const at = (ix) => ix.reduce((s2, k) => s2 + prof[k], 0) / ix.length;
  const axisMean = at([0, 9, 18, 27]), diagMean = at([4, 13, 22, 31]);
  const axisOverDiag = +(axisMean / Math.max(diagMean, 1e-12)).toFixed(4);
  gate('flow-square-all-eight-directions', axisOverDiag > 0.5,
    `axis/diagonal drainage = ${axisOverDiag} (axes ${axisMean.toFixed(2)}, diagonals ${diagMean.toFixed(2)}) `
    + `— picking the lowest neighbour instead of the steepest reads 0.1382 here, because the sqrt(2) `
    + `diagonal is always lower on a smooth slope and no cell ever drains along an axis`);

  // REPORTED, NOT GATED, and deliberately so. Single-receiver routing sends all of a cell's water to
  // one neighbour, so the realisable directions ARE the lattice's own and concentration cannot reach
  // 1.0 by fixing the selection rule - the distance correction above moved the spokes from the
  // diagonals to the axes and left the number where it was (1.8132 -> 1.8161). Only distributing
  // flow across several receivers moves it, which is precisely why `26` records MFD, and not D6, as
  // what delivers "smoother and more natural". Gating this now would be gating a number no change in
  // this commit can move; it becomes a gate when MFD lands.
  console.log(`\nREPORT  flow-facet-concentration  square=${r.square.concentration}  hex=${r.hex.concentration}`
    + `  (single-receiver floor; MFD is what lowers this)`);

  gate('flow-no-page-errors', errors.length === 0, errors.length ? JSON.stringify(errors) : 'none');

  await b.close();
  console.log(failures ? `\n${failures} gate(s) failed.` : '\nmeasurement complete.');
  process.exit(failures ? 1 : 0);
})().catch((e) => { console.error('FATAL ' + String(e).slice(0, 300)); process.exit(2); });
