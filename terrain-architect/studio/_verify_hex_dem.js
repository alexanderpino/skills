// DEM interchange on the hexagonal lattice (references/26, "Interchange"): hex is a grid you
// SIMULATE on and RESAMPLE OUT of. Every engine, DCC and DEM consumer expects a square raster,
// so import must place a square source onto the hex lattice at each cell's true world point, and
// export must resample the odd-r array back to square. Shipping the raw array either way ships a
// SHEARED terrain — alternate rows displaced half a cell — which 26 calls out as the likely first
// bug of a hex implementation.
//
// The normalisation that makes this tractable: the hex world is scale x scale*sqrt(3)/2, so a
// cell's normalised world position is ( (x + 0.5*(y&1))/(n-1), y/(n-1) ) — the row compression
// CANCELS against the world's own extent and only the odd-row half-cell shift in x survives.
//
// MEASURED, this build (n=192, ramp/chirp probes; see gate detail strings for the live numbers):
//   pre-fix import  : odd rows landed half a cell off along x — on an x-ramp that is a fixed
//                     0.5-cell error on every other row, a comb the eye reads as a shear.
//   pre-fix export  : same defect mirrored — the PNG carried the odd-r offset as real geometry.
// Gates are armed against a WORLD-SPACE ramp, where the correct answer is analytic, plus a
// square-lattice negative control proving the metric measures hex handling and not resampling.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));

(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1500);

  const r = await p.evaluate(() => {
    const HR = Math.sqrt(3) / 2, out = {};
    const n = 192;

    // A square SOURCE raster carrying a pure x-ramp. Under a correct import every hex cell must
    // read the ramp value at ITS OWN world x, so odd rows read half a cell further along. An
    // importer that ignores the shift returns the same value for both parities: the tell is a
    // row-to-row comb whose size is exactly the half-cell ramp step.
    const src = new Float32Array(n * n);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) src[y * n + x] = x / (n - 1);
    const u16 = new Uint16Array(n * n);
    for (let i = 0; i < n * n; i++) u16[i] = Math.round(src[i] * 65535);

    const importUnder = (lat) => {
      terrainDef.lattice = lat; RES = n;
      // resampleTo is the RAW/.r16 import path; it normalises, so compare shape not absolute level
      const f = resampleTo(u16, n, v => v / 65535);
      const hex = lat === 'hex';
      // Analytic expectation: normalised ramp at this cell's own world x.
      let maxErr = 0, se = 0, cnt = 0;
      for (let y = 2; y < n - 2; y++) for (let x = 2; x < n - 3; x++) {
        const wx = x + (hex ? 0.5 * (y & 1) : 0);
        const want = wx / (n - 1);
        // f is normalised to [0,1] over its own range; the ramp stays a ramp, so compare directly
        const e = Math.abs(f[y * n + x] - want);
        if (e > maxErr) maxErr = e; se += e * e; cnt++;
      }
      // The parity comb. It must be measured as |row y - row y+1|, NOT signed: consecutive rows
      // alternate parity, so the signed step flips sign every row and averages to ~0 on a
      // CORRECT import as well as a broken one. (First form of this gate did exactly that and
      // read 0 against a correct import.) Absolute: a correct import reads the half-cell ramp
      // step 0.5/(n-1); a shift-blind one reads ~0 because both parities sample the same column.
      let comb = 0, cc = 0;
      for (let y = 2; y < n - 3; y++) for (let x = 2; x < n - 3; x++) {
        comb += Math.abs(f[y * n + x] - f[(y + 1) * n + x]); cc++;
      }
      return { maxErr: +maxErr.toExponential(3), rms: +Math.sqrt(se / cnt).toExponential(3),
        meanAbsRowStep: +(comb / cc).toExponential(3), cells: cnt };
    };
    out.importHex = importUnder('hex');
    out.importSquare = importUnder('square');

    // EXPORT: build a field on the hex lattice whose WORLD content is a pure x-ramp, resample it
    // to square the way exportHeightmap does, and check the square raster is a clean ramp again.
    terrainDef.lattice = 'hex'; RES = n;
    const hexField = new Float32Array(n * n);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      hexField[y * n + x] = (x + 0.5 * (y & 1)) / (n - 1);
    }
    const sq = new Float32Array(n * n);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) sq[y * n + x] = sampleBilinear(hexField, x, y * HR);
    let eMax = 0, eSe = 0, eCnt = 0, combSq = 0, combCnt = 0;
    for (let y = 2; y < n - 3; y++) for (let x = 2; x < n - 3; x++) {
      const e = Math.abs(sq[y * n + x] - x / (n - 1));
      if (e > eMax) eMax = e; eSe += e * e; eCnt++;
      combSq += Math.abs(sq[y * n + x] - sq[(y + 1) * n + x]); combCnt++;
    }
    out.exportHex = { maxErr: +eMax.toExponential(3), rms: +Math.sqrt(eSe / eCnt).toExponential(3),
      residualRowComb: +(combSq / combCnt).toExponential(3), cells: eCnt };

    // Raw (unresampled) export of the same field, i.e. what shipping the odd-r array directly
    // would have produced — the discriminator the gates are armed against.
    let rawMax = 0, rawComb = 0, rawCnt = 0;
    for (let y = 2; y < n - 3; y++) for (let x = 2; x < n - 3; x++) {
      rawMax = Math.max(rawMax, Math.abs(hexField[y * n + x] - x / (n - 1)));
      rawComb += Math.abs(hexField[y * n + x] - hexField[(y + 1) * n + x]); rawCnt++;
    }
    out.exportRawUnresampled = { maxErr: +rawMax.toExponential(3),
      rowComb: +(rawComb / rawCnt).toExponential(3) };

    terrainDef.lattice = 'square'; RES = 512; buildIndex();
    return out;
  });

  const gates = []; const gate = (nm, pass, detail) => gates.push({ nm, pass: !!pass, detail });
  const halfStep = 0.5 / 191;
  // D1: a hex import must place each cell at ITS OWN world x — the parity comb must appear and
  // equal the half-cell ramp step. A shift-blind import reads ~0 comb.
  gate('D1 import-honours-parity-shift',
    Math.abs(r.importHex.meanAbsRowStep - halfStep) < halfStep * 0.4
    && r.importHex.maxErr < 1e-4,
    `hex meanAbsRowStep=${r.importHex.meanAbsRowStep} vs the analytic half-cell ramp step `
    + `${halfStep.toExponential(3)} (a shift-blind import reads ~0 comb and a 0.5-cell maxErr; `
    + `nearest-neighbour resampling truncates the shift straight back out, which is how this gate `
    + `caught the first version of the fix); maxErr=${r.importHex.maxErr} rms=${r.importHex.rms}`);
  // D2: square control — the same import path on the square lattice has NO parity comb at all,
  // proving D1 measures hex handling rather than resampling error.
  gate('D2 import-square-control',
    r.importSquare.meanAbsRowStep < halfStep * 0.05 && r.importSquare.maxErr < 1e-4,
    `square meanAbsRowStep=${r.importSquare.meanAbsRowStep} (must be ~0, vs hex `
    + `${r.importHex.meanAbsRowStep}) maxErr=${r.importSquare.maxErr}`);
  // D3: export must UNDO the lattice — the square raster is a clean ramp again, and the residual
  // row-to-row comb collapses versus shipping the odd-r array raw.
  gate('D3 export-resamples-to-square',
    r.exportHex.maxErr < 5e-3 && r.exportHex.residualRowComb < r.exportRawUnresampled.rowComb * 0.25,
    `resampled maxErr=${r.exportHex.maxErr} rowComb=${r.exportHex.residualRowComb} vs RAW odd-r array `
    + `maxErr=${r.exportRawUnresampled.maxErr} rowComb=${r.exportRawUnresampled.rowComb} (the sheared PNG)`);

  console.log('== hex DEM interchange ==');
  console.log(JSON.stringify(r, null, 1));
  let fail = 0;
  for (const g of gates) { console.log(`${g.pass ? 'PASS' : 'FAIL'}  ${g.nm}  ${g.detail}`); if (!g.pass) fail++; }
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(fail || errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
