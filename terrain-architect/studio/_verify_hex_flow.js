// Hex lattice x FLOW ROUTING / SLOPE ANALYSIS (references/26-hexagonal-lattice.md).
// thermalErodeHex got a D6 kernel; slopeOf, spReceivers, priorityFloodFill, d8Accumulation and
// hydroFixField did NOT. Grep them for `lattice` / `isHex()`: nothing. They run square 4-neighbour
// stencils and sqrt(2)-weighted D8 offsets straight over odd-r hex storage, where those same index
// offsets denote DIFFERENT spatial relationships.
//
// Odd-r geometry (the convention thermalErodeHex's nbEven/nbOdd already encodes, and the one this
// script re-derives and self-checks): world point of cell (x,y) is (x + 0.5*(y&1), y*sqrt(3)/2).
// The six true neighbours are (x+-1,y) and, with off=(y&1)?0:-1, (x+off,y+-1),(x+off+1,y+-1) — all
// at world distance exactly 1. What the square stencils see instead:
//   * slopeOf's vertical central difference spans rows y-1..y+1 = sqrt(3) world units, but divides
//     by 2. dh/dy comes out sqrt(3)/2 = 0.866x too small while dh/dx is exact -> a cone reads
//     ELLIPTICAL. Predicted ring anisotropy 2/sqrt(3) = 1.1547.
//   * the D8 offset set is NOT the hex one-ring: on even rows (+1,-1) and (+1,+1) land 1.5 cells
//     east, sqrt(3) away (two rings out, with an untouched cell in between); on odd rows (-1,-1)
//     and (-1,+1) do. spReceivers labels all four "sqrt(2)", which is a distance no pair of hex
//     cells has. Steepest descent therefore prefers the far cell over the true neighbour across
//     roughly half of all azimuths, and flow TELEPORTS over cells it never drains.
//
// MEASURED on the current build, 192^2 world-space cone (2026-07-28; full set in the gate details):
//                                            hex cone     square cone (control)   correct
//   F1/F2 ring slope anisotropy (24 bins)      1.1472           1.0001             ~1.00
//         E-W vs N-S axis slope ratio          1.1499           1.0000              1.00   (2/sqrt(3)=1.1547 predicted)
//         mean |slope| / analytic truth        0.9343           1.0000              1.00
//   F3    interior pits after the fill              0                0                 0
//         accumulation reaching the border     1.0000           1.0000              1.00
//         sum(A over terminals)/N              1.0000           1.0000              1.00   (accounting identity)
//   F4/F5 receivers that are NOT lattice
//         neighbours (spReceivers)             0.4040           0.0000             0.0000
//         receivers whose reported `dist`
//         is not the true world distance       0.5413           0.0000             0.0000
//         longest receiver hop (world cells)   1.7321           1.4142             1.0000
//
// THRESHOLDS, armed between the measured-broken and the correct value, margin on both sides:
//   F1 hex ring anisotropy <= 1.06    — broken 1.1472 (0.087 above), correct ~1.00, square control
//                                       1.0001 (0.060 below). RED NOW, by design.
//   F2 square ring anisotropy <= 1.03 — measures 1.0001. The discriminator: identical cone,
//                                       identical operator, identical annulus. Must PASS NOW.
//   F3 interior pits == 0 AND border reach >= 0.999 — measures 0 / 1.0000 on BOTH lattices, i.e.
//                                       this one is GREEN on the broken build and says so in its
//                                       detail line. Not weakened, not inflated: the square D8
//                                       offset set is a superset of the hex one-ring, so it cannot
//                                       strand flow on a monotone cone. Kept as the regression
//                                       floor; F4 is where the routing defect actually lives.
//   F4 hex non-neighbour receiver fraction <= 0.02 — broken 0.4040, correct EXACTLY 0. RED NOW.
//   F5 square non-neighbour receiver fraction <= 0.02 — measures 0.0000. Must PASS NOW.
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
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    try { buildRun++; } catch (_) {}
    SCALE_RES = true; XF = null; USE_GPU = false; BUILD_QUALITY = 'interactive';
    Object.assign(terrainDef, { scale: 5000, height: 2600, baseElevation: 0, lattice: 'square' });
    H_SCALE = terrainDef.height / terrainDef.scale;
    RES = 192; const n = RES, N = n * n, HEXR = Math.sqrt(3) / 2;
    const out = {};

    // ---- odd-r geometry + the six-neighbour table, copied from thermalErodeHex (index.html) ----
    const nbEven = [[-1,0],[1,0],[-1,-1],[0,-1],[-1,1],[0,1]];
    const nbOdd  = [[-1,0],[1,0],[0,-1],[1,-1],[0,1],[1,1]];
    const nbSq8  = [[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[1,1],[-1,1],[1,-1]];
    const nbOf = (hex, y) => hex ? ((y & 1) ? nbOdd : nbEven) : nbSq8;
    const wx = (hex, x, y) => x + (hex ? 0.5 * (y & 1) : 0);
    const wy = (hex, y) => y * (hex ? HEXR : 1);

    // Identity control on MY OWN geometry before it is used to judge anything: every entry of the
    // odd-r table must sit at world distance exactly 1, on both row parities. If this is not 1 the
    // rest of the script is measuring my bug, not the studio's.
    { let mn = Infinity, mx = 0;
      for (const y of [40, 41]) for (const d of nbOf(true, y)) {
        const L = Math.hypot(wx(true, 60 + d[0], y + d[1]) - wx(true, 60, y), wy(true, y + d[1]) - wy(true, y));
        if (L < mn) mn = L; if (L > mx) mx = L; }
      out.latticeSelfCheck = { minNbDist: +mn.toFixed(6), maxNbDist: +mx.toFixed(6) }; }

    // ---- world-space cone: h = 1 - dist(worldPoint, worldCentre)/R, R past the far corner so the
    // surface is STRICTLY descending everywhere (no clamped flat rim to manufacture fake pits). A
    // cone has one slope magnitude at every azimuth and one flow direction (radially out), which is
    // what makes both measurements below unambiguous. ----
    const mkCone = hex => {
      const px = new Float64Array(N), py = new Float64Array(N), d = new Float64Array(N);
      const cx = (n - 1) / 2 + (hex ? 0.25 : 0), cy = ((n - 1) / 2) * (hex ? HEXR : 1);
      let rmax = 0;
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) { const i = y * n + x;
        px[i] = wx(hex, x, y); py[i] = wy(hex, y);
        d[i] = Math.hypot(px[i] - cx, py[i] - cy); if (d[i] > rmax) rmax = d[i]; }
      const R = rmax * 1.25, f = newField();
      for (let i = 0; i < N; i++) f[i] = 1 - d[i] / R;
      return { f, px, py, d, cx, cy, R, hex };
    };
    // One annulus in WORLD units for both lattices, so hex and square are asked the same question.
    const rIn = 0.22 * n, rOut = 0.38 * n, B = 24;

    // ---- (1) SLOPE ISOTROPY ----------------------------------------------------------------
    const slopeStats = c => {
      terrainDef.lattice = c.hex ? 'hex' : 'square';
      const sl = slopeOf(c.f);
      const sum = new Float64Array(B), cnt = new Float64Array(B);
      let tot = 0, cells = 0, axE = 0, axEn = 0, axN = 0, axNn = 0;
      for (let y = 2; y < n - 2; y++) for (let x = 2; x < n - 2; x++) {
        const i = y * n + x, rr = c.d[i]; if (rr < rIn || rr > rOut) continue;
        const th = Math.atan2(c.py[i] - c.cy, c.px[i] - c.cx);
        let bb = Math.floor((th + Math.PI) / (2 * Math.PI) * B);
        bb = bb < 0 ? 0 : bb >= B ? B - 1 : bb;
        sum[bb] += sl[i]; cnt[bb]++; tot += sl[i]; cells++;
        const a = Math.abs(((th * 180 / Math.PI) + 360) % 180 - 90);   // 90 = due E/W, 0 = due N/S
        if (a > 78) { axE += sl[i]; axEn++; } else if (a < 12) { axN += sl[i]; axNn++; }
      }
      let mx = 0, mn = Infinity, empty = 0;
      for (let k = 0; k < B; k++) { if (!cnt[k]) { empty++; continue; }
        const v = sum[k] / cnt[k]; if (v > mx) mx = v; if (v < mn) mn = v; }
      return { ratio: +(mx / mn).toFixed(4), emptyBins: empty, ringCells: cells,
        // analytic truth: |grad h| = 1/R per world cell, and slopeOf scales by n
        meanOverTruth: +(tot / cells / (n / c.R)).toFixed(4),
        ewOverNs: +((axE / axEn) / (axN / axNn)).toFixed(4) };
    };

    // ---- (2) ROUTING ------------------------------------------------------------------------
    const routeStats = c => {
      terrainDef.lattice = c.hex ? 'hex' : 'square';
      const filled = priorityFloodFill(c.f);        // routing caller -> default flat epsilon
      const A = d8Accumulation(filled);             // the river network under test
      const { rec, dist } = spReceivers(filled, 1); // same 8-offset family, and it RETURNS its
      // receivers + the distance it believes it used, so the legality check below reads the
      // product's own output rather than a re-implementation that a fix would invalidate.
      let over = 0; for (let i = 0; i < N; i++) over = Math.max(over, filled[i] - c.f[i]);

      // Legal Order: after the fill nothing interior may be a pit under the lattice's OWN one-ring.
      let pits = 0;
      for (let y = 1; y < n - 1; y++) for (let x = 1; x < n - 1; x++) {
        const i = y * n + x; let lower = false;
        for (const dd of nbOf(c.hex, y)) { const xx = x + dd[0], yy = y + dd[1];
          if (xx < 0 || yy < 0 || xx >= n || yy >= n) continue;
          if (filled[yy * n + xx] < filled[i]) { lower = true; break; } }
        if (!lower) pits++;
      }
      // Terminals: rec === -1 means "no strictly lower cell in the stencil" — the SAME predicate
      // d8Accumulation stops on, so the basins A counts are exactly these cells' basins and
      // sum(A over terminals) must be N. That identity is the control on this accounting.
      let termA = 0, interiorTermA = 0, interiorTerms = 0, borderTerms = 0;
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) { const i = y * n + x;
        if (rec[i] >= 0) continue;
        termA += A[i];
        if (x === 0 || y === 0 || x === n - 1 || y === n - 1) borderTerms++;
        else { interiorTerms++; interiorTermA += A[i]; } }

      // Receiver legality: a receiver must BE a lattice neighbour (world distance 1 on hex,
      // <= sqrt(2) on square) and the distance the router used must be the real one.
      const maxLegal = c.hex ? 1.0001 : Math.SQRT2 + 1e-4;
      let far = 0, wrongD = 0, seen = 0, maxStep = 0;
      for (let y = 1; y < n - 1; y++) for (let x = 1; x < n - 1; x++) {
        const i = y * n + x, j = rec[i]; if (j < 0) continue;
        const L = Math.hypot(c.px[j] - c.px[i], c.py[j] - c.py[i]);
        seen++; if (L > maxStep) maxStep = L;
        if (L > maxLegal) far++;
        if (Math.abs(dist[i] - L) > 1e-3) wrongD++;
      }
      // Reported, not gated (26 "Limits": single-receiver parallel-line artefacts survive on BOTH
      // lattices, so a channelisation statistic cannot discriminate lattice handling).
      let orphan = 0, ring = 0;
      for (let y = 2; y < n - 2; y++) for (let x = 2; x < n - 2; x++) { const i = y * n + x;
        if (c.d[i] < rIn || c.d[i] > rOut) continue; ring++; if (A[i] <= 1.000001) orphan++; }
      return { overFill: +over.toExponential(2), interiorPits: pits,
        borderReach: +(1 - interiorTermA / N).toFixed(6),
        terminalMassOverN: +(termA / N).toFixed(6), interiorTerms, borderTerms,
        farRecFrac: +(far / seen).toFixed(4), wrongDistFrac: +(wrongD / seen).toFixed(4),
        maxStep: +maxStep.toFixed(4), orphanFrac: +(orphan / ring).toFixed(4) };
    };

    const hexC = mkCone(true), sqC = mkCone(false);
    out.slope = { hex: slopeStats(hexC), square: slopeStats(sqC) };
    out.route = { hex: routeStats(hexC), square: routeStats(sqC) };
    terrainDef.lattice = 'square';
    return out;
  });

  const gates = [];
  const gate = (name, pass, detail) => gates.push({ name, pass: !!pass, detail });
  const S = r.slope, R = r.route;

  gate('F0 lattice-self-check',
    r.latticeSelfCheck && Math.abs(r.latticeSelfCheck.minNbDist - 1) < 1e-4
      && Math.abs(r.latticeSelfCheck.maxNbDist - 1) < 1e-4,
    `odd-r one-ring world distances min=${r.latticeSelfCheck.minNbDist} max=${r.latticeSelfCheck.maxNbDist} `
    + `(both parities; this is the control on the geometry the gates below judge with)`);

  gate('F1 slope-ring-isotropy-hex', S.hex.ratio <= 1.06,
    `hex world cone, slopeOf around a mid-radius annulus, ${24} azimuth bins: max/min=${S.hex.ratio} `
    + `(square control ${S.square.ratio}; a cone has ONE slope at every azimuth, so correct ~1.00). `
    + `E-W/N-S axis ratio=${S.hex.ewOverNs} vs the predicted 2/sqrt(3)=1.1547 — slopeOf spans `
    + `sqrt(3) world units between rows y-1..y+1 and divides by 2. mean|slope|/analytic=`
    + `${S.hex.meanOverTruth} (square ${S.square.meanOverTruth}); ringCells=${S.hex.ringCells} emptyBins=${S.hex.emptyBins}`);

  gate('F2 square-control', S.square.ratio <= 1.03,
    `square world cone through the SAME slopeOf, same annulus, same bins: max/min=${S.square.ratio} `
    + `mean|slope|/analytic=${S.square.meanOverTruth} ewOverNs=${S.square.ewOverNs} — near-isotropic, so `
    + `F1 is reading lattice handling, not "cones are hard"`);

  gate('F3 routing-reaches-edge',
    R.hex.interiorPits === 0 && R.hex.borderReach >= 0.999,
    `hex cone: interiorPits(after priorityFloodFill, judged on the D6 one-ring)=${R.hex.interiorPits} `
    + `borderReach=${R.hex.borderReach} overFill=${R.hex.overFill} interiorTerminals=${R.hex.interiorTerms} `
    + `borderTerminals=${R.hex.borderTerms} sum(A over terminals)/N=${R.hex.terminalMassOverN} `
    + `[square: pits=${R.square.interiorPits} borderReach=${R.square.borderReach} terminalMass=${R.square.terminalMassOverN}] `
    + `— MEASURED FINDING: the square-D8 offset set is a SUPERSET of the hex one-ring (all six true `
    + `neighbours plus two extras), so it cannot strand flow on a monotone cone. Pure connectivity `
    + `is NOT where this defect shows; it shows in WHICH cell flow moves to — see F4.`);

  gate('F4 routing-receiver-adjacency', R.hex.farRecFrac <= 0.02,
    `hex cone, spReceivers' own rec/dist output: ${(R.hex.farRecFrac*100).toFixed(2)}% of interior `
    + `receivers are NOT lattice neighbours (max step=${R.hex.maxStep} world cells — sqrt(3), two rings `
    + `out, with an undrained cell in between); ${(R.hex.wrongDistFrac*100).toFixed(2)}% carry a `
    + `reported dist that is not the true world distance (it says sqrt(2), a distance no pair of hex `
    + `cells has). Correct D6 = exactly 0 for both. [square control ${R.square.farRecFrac} / `
    + `${R.square.wrongDistFrac}, maxStep=${R.square.maxStep}]`);

  gate('F5 square-routing-control',
    R.square.farRecFrac <= 0.02 && R.square.wrongDistFrac <= 0.02 && R.square.interiorPits === 0,
    `square cone through the SAME priorityFloodFill/d8Accumulation/spReceivers: farRec=`
    + `${R.square.farRecFrac} wrongDist=${R.square.wrongDistFrac} pits=${R.square.interiorPits} — the `
    + `router is correct on the lattice it was written for, so F4 is a lattice failure, not a router failure`);

  console.log(`REPORT flow-confetti  orphan cells (A==1) in the ring: hex=${R.hex.orphanFrac} `
    + `square=${R.square.orphanFrac} — reported, NOT gated: references/26 "Limits" says single-receiver `
    + `parallel-line artefacts survive on both lattices, so channelisation statistics cannot `
    + `discriminate lattice handling. The discriminating routing statistic is F4's adjacency.`);
  console.log(`REPORT fill-stencil  priorityFloodFill walks 4 offsets ((+-1,0),(0,+-1)). On odd-r `
    + `those are 4 of the 6 true neighbours — the (x-1,y+-1) pair on even rows and (x+1,y+-1) on odd `
    + `rows are unreachable to the fill, so a basin whose only spill runs through them floods `
    + `spuriously. Not gated here: the fill is D4 while accumulation is D8 on the SQUARE lattice too, `
    + `so that mismatch is not lattice-specific and a gate on it would not discriminate.`);

  console.log('== hex lattice: flow routing + slope analysis ==');
  let fail = 0;
  for (const g of gates) { console.log(`${g.pass ? 'PASS' : 'FAIL'}  ${g.name}  ${g.detail}`); if (!g.pass) fail++; }
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(fail || errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
