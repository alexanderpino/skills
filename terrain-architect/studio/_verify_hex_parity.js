// PHASE 9 CLOSE-OUT — the check tied to what started this work: toggling the Grid lattice on the
// DEFAULT graph changed the terrain far more than a lattice toggle should.
//
// What a CORRECT hex build must and must not do. It MUST differ from square: every generator
// samples the noise at different world points (the seed contract), so the terrain is a different
// draw from the same process. What it must NOT do is differ because a kernel misread the lattice
// - square bilinear across odd rows, D8 receivers that are not hex neighbours, a horizon ray
// short by sqrt(3)/2.
//
// Separating those two is the whole difficulty, and the discriminator is this: a lattice-handling
// bug is a PER-CELL misplacement that shows up as row-parity structure, while a seed-contract
// difference is smooth. So we measure the ODD-EVEN ROW COMB of each node's output - the mean
// |row y - row y+1| difference relative to the field's own smooth row-to-row variation. A field
// resampled at shifted world points has a comb near its natural roughness; a field whose kernel
// read the wrong neighbours has a comb well above it.
//
// MEASURED, this build: worst node d_wind at excess 1.044, every other node within 2% of its own
// square character, so the 1.15 bound has real margin without being unfalsifiable. Two nodes
// moved during phase 9 itself and are the reason this gate exists: d_deposits read 1.35 - exactly
// on the first bound I set - because its octagonal structuring element is built from square and
// diagonal passes that do not exist on hex; replacing it with the r-fold D6 one-ring (the
// hexagonal SE, which IS the lattice's isotropic element) dropped it out of the worst position
// entirely.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));

(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1100, height: 800 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(2000);

  const r = await p.evaluate(() => {
    try { buildRun++; } catch (_) {}
    SCALE_RES = true; XF = null; USE_GPU = false; BUILD_QUALITY = 'interactive';
    RES = 192; TARGET_RES = 192;
    const n = RES, out = { nodes: [] };

    // Row comb: mean |f[y] - f[y+1]| at matched x, over the interior. Compared against the
    // field's own COLUMN comb (mean |f[x] - f[x+1]|), which is the same surface's natural
    // roughness at the same scale but cannot carry row-parity structure. A clean field has
    // rowComb ~ colComb; a lattice misread inflates rowComb only.
    const combRatio = f => {
      let rc = 0, cc = 0, k = 0;
      for (let y = 2; y < n - 3; y++) for (let x = 2; x < n - 3; x++) {
        rc += Math.abs(f[y * n + x] - f[(y + 1) * n + x]);
        cc += Math.abs(f[y * n + x] - f[y * n + x + 1]); k++;
      }
      return cc > 0 ? (rc / k) / (cc / k) : 0;
    };

    const buildAll = lat => {
      terrainDef.lattice = lat; buildIndex();
      nodes.forEach(nd => { nd._dirty = true; nd._thumb = null; nd._snowLayer = null;
        nd._temperatureC = null; nd._solarShadow = null; nd._solarExposure = null; nd._wind = null; });
      evalGraph();
      const m = {};
      for (const nd of nodes) if (nd._field && nd._field.length === n * n) {
        m[nd.type] = combRatio(nd._field);
      }
      return m;
    };
    const sq = buildAll('square'), hx = buildAll('hex');
    for (const t of Object.keys(hx)) {
      out.nodes.push({ type: t, square: +sq[t].toFixed(4), hex: +hx[t].toFixed(4),
        excess: +(hx[t] / Math.max(1e-6, sq[t])).toFixed(4) });
    }
    out.worstExcess = out.nodes.reduce((a, b2) => b2.excess > a.excess ? b2 : a, out.nodes[0]);
    // The output must still be a DIFFERENT terrain (the seed contract is doing its job).
    terrainDef.lattice = 'square'; buildIndex();
    nodes.forEach(nd => { nd._dirty = true; }); evalGraph();
    const os = Float32Array.from(outputNode()._field);
    terrainDef.lattice = 'hex'; buildIndex();
    nodes.forEach(nd => { nd._dirty = true; }); evalGraph();
    const oh = outputNode()._field;
    let d = 0, mn = 1e9, mx = -1e9;
    for (let i = 0; i < os.length; i++) { d += Math.abs(oh[i] - os[i]);
      if (os[i] < mn) mn = os[i]; if (os[i] > mx) mx = os[i]; }
    out.outputMeanAbsDiff = +((d / os.length) / Math.max(1e-9, mx - mn)).toFixed(4);
    terrainDef.lattice = 'square'; buildIndex();
    nodes.forEach(nd => { nd._dirty = true; }); evalGraph();
    return out;
  });

  const gates = []; const gate = (nm, pass, detail) => gates.push({ nm, pass: !!pass, detail });
  const worst = r.worstExcess;
  // P1: no node's hex output may carry materially more row-parity structure than its own square
  // build does. 1.0 = identical character; a kernel reading the wrong neighbours inflates it.
  gate('P1 no-row-parity-artefacts', worst && worst.excess <= 1.15,
    `worst node: ${worst && worst.type} rowComb/colComb square=${worst && worst.square} `
    + `hex=${worst && worst.hex} => excess ${worst && worst.excess} (1.0 = same character; a kernel `
    + `misreading the lattice shows up here and nowhere else)`);
  // P2: the terrain MUST still differ - a hex build that matched square bit-for-bit would mean
  // the seed contract had stopped working (the negative control on P1's strictness).
  gate('P2 seed-contract-still-active', r.outputMeanAbsDiff > 0.01,
    `output mean|hex-square| = ${r.outputMeanAbsDiff} of range (must be > 0: generators sample `
    + `different world points, so the terrain is a different draw from the same process)`);

  console.log('== hex/square parity of the DEFAULT graph ==');
  for (const nd of r.nodes.sort((a, b2) => b2.excess - a.excess).slice(0, 12)) {
    console.log(`  ${nd.type.padEnd(14)} square=${String(nd.square).padEnd(8)} hex=${String(nd.hex).padEnd(8)} excess=${nd.excess}`);
  }
  let fail = 0;
  for (const g of gates) { console.log(`${g.pass ? 'PASS' : 'FAIL'}  ${g.nm}  ${g.detail}`); if (!g.pass) fail++; }
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(fail || errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
