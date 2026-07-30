// D7: the opening document must be the highest layer VERIFIED CORRECT ON BOTH LATTICES.
//
// The rule only means anything if something enforces it, so this file is the enforcement. It builds
// the opening document on square and on hex and requires, on each:
//
//   * every node evaluates — no throw, no empty field;
//   * the output carries real relief, not a flat or NaN plate;
//   * the two lattices agree in STATISTICS, not in bytes. They cannot agree byte-for-byte: hex has
//     15.5% more cells and a different sample grid. What must hold is that the same graph makes the
//     same KIND of terrain — comparable relief and comparable roughness — because if hex produced a
//     visibly different landscape from identical parameters, "correct on both lattices" would be
//     an empty phrase.
//
// This is deliberately NOT a byte-identity gate. _verify_digest owns byte identity, and only for
// square; asking for it across lattices would be asking for the wrong thing and would fail forever.
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
    SCALE_RES = true; XF = null; USE_GPU = false; BUILD_QUALITY = 'interactive';
    Object.assign(terrainDef, { scale: 5000, height: 2600, baseElevation: 0 });
    RES = 192;

    const run = (lattice) => {
      terrainDef.lattice = lattice;
      nodes.length = 0; edges.length = 0; uid = 1; selected = null; selectedEdge = null;
      layer0Graph();
      evalGraph();

      const out = outputNode();
      const f = out && out._field;
      const stats = { lattice, nodeCount: nodes.length, edgeCount: edges.length };
      if (!f) return { ...stats, ok: false, why: 'no output field' };

      let mn = Infinity, mx = -Infinity, sum = 0, nan = 0, len = f.length;
      for (let i = 0; i < len; i++) {
        const v = f[i];
        if (!Number.isFinite(v)) { nan++; continue; }
        if (v < mn) mn = v; if (v > mx) mx = v; sum += v;
      }
      const mean = sum / Math.max(1, len - nan);
      // roughness: mean absolute first difference along a row, in world units. Scale-free enough to
      // compare across two lattices with different cell counts.
      const n = fieldW(), nh = fieldH();
      let d = 0, dc = 0;
      for (let y = 1; y < nh - 1; y++) for (let x = 1; x < n - 1; x++) {
        d += Math.abs(f[y * n + x] - f[y * n + x - 1]); dc++;
      }
      // how many nodes actually produced a field
      const evaluated = nodes.filter((nd) => nd._field && nd._field.length).length;
      return {
        ...stats, ok: true, len, nan,
        min: +mn.toFixed(5), max: +mx.toFixed(5), mean: +mean.toFixed(5),
        relief: +(mx - mn).toFixed(5),
        roughness: +(d / Math.max(1, dc)).toFixed(6),
        evaluated,
      };
    };

    const sq = run('square'), hx = run('hex');
    terrainDef.lattice = 'square';
    return { square: sq, hex: hx };
  });

  console.log(JSON.stringify(r, null, 1));
  const { square: sq, hex: hx } = r;

  for (const m of [sq, hx]) {
    gate(`L0-evaluates-${m.lattice}`, m.ok && m.evaluated === m.nodeCount,
      `${m.evaluated}/${m.nodeCount} nodes produced a field${m.why ? ' — ' + m.why : ''}`);
    gate(`L0-finite-${m.lattice}`, m.ok && m.nan === 0, `NaN cells = ${m.nan}`);
    // A flat plate passes "no NaN" and is useless — this is the control that stops the gate
    // certifying an empty document.
    gate(`L0-has-relief-${m.lattice}`, m.ok && m.relief > 0.25,
      `relief = ${m.relief} (min ${m.min}, max ${m.max}) — a flat plate would satisfy every other check here`);
  }

  // STRUCTURE, pinned. Without this the file measures lattice AGREEMENT and nothing else, and a
  // document broken identically on both lattices sails through — which is not hypothetical: cutting
  // the detail generator out of the blend halved roughness on both lattices (0.029 -> 0.012) and
  // every ratio check still passed, because both sides fell together. A gate that only compares two
  // things to each other cannot notice them both being wrong.
  const L0_NODES = 7, L0_EDGES = 6;
  for (const m of [sq, hx]) {
    gate(`L0-topology-${m.lattice}`, m.nodeCount === L0_NODES && m.edgeCount === L0_EDGES,
      `${m.nodeCount} nodes / ${m.edgeCount} edges (expected ${L0_NODES}/${L0_EDGES}) — pins the `
      + `document itself, so a missing connection cannot hide behind a healthy-looking ratio`);
  }

  // ABSOLUTE roughness, armed between measured endpoints:
  //     correct L0                       square 0.0290   hex 0.0286
  //     detail generator disconnected    square 0.0124   hex 0.0124
  // The band sits at 0.020-0.040: clear of the broken value by a factor of ~1.7 and wide enough to
  // survive ordinary parameter tuning of the default document.
  for (const m of [sq, hx]) {
    gate(`L0-roughness-absolute-${m.lattice}`, m.roughness > 0.020 && m.roughness < 0.040,
      `roughness = ${m.roughness} (correct ~0.029; with the detail generator cut, 0.0124)`);
  }

  // The cross-lattice comparison. Bounds are wide on purpose: the point is "same kind of terrain",
  // and a tight bound would be asserting a false equivalence between two different sample grids.
  const reliefRatio = +(hx.relief / Math.max(1e-9, sq.relief)).toFixed(4);
  const roughRatio = +(hx.roughness / Math.max(1e-9, sq.roughness)).toFixed(4);
  gate('L0-lattices-agree-relief', reliefRatio > 0.85 && reliefRatio < 1.18,
    `hex/square relief = ${reliefRatio} (${hx.relief} vs ${sq.relief})`);
  gate('L0-lattices-agree-roughness', roughRatio > 0.75 && roughRatio < 1.35,
    `hex/square roughness = ${roughRatio} (${hx.roughness} vs ${sq.roughness}) — hex samples ~15.5% more `
    + `cells at the same cellSize, so an exact match is not expected and would be suspicious`);

  gate('L0-no-page-errors', errors.length === 0, errors.length ? JSON.stringify(errors) : 'none');

  await b.close();
  console.log(failures ? `\n${failures} L0 gate(s) failed.` : '\nL0 is correct on both lattices.');
  process.exit(failures ? 1 : 0);
})().catch((e) => { console.error('FATAL ' + String(e).slice(0, 300)); process.exit(2); });
