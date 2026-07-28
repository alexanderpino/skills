// Resolution invariance for the erosion family: the same node on the same world-space input must
// produce the SAME LANDFORM at any working resolution — just with more detail (SKILL.md world-units
// invariant; the canyon primitive earned this via CANYON_REF_GRID and _verify_canyon_gridscale.js;
// this suite extends the contract to streampower / hydraulic / erosion2 / hydrofix).
//
// Method: evaluate each node's pure eval() on a world-coherent fbm source at 192² and 384²
// (SCALE_RES on — the shipped Res Lock default), then compare:
//   depthRatio  rms(out−in)@384 / rms(out−in)@192  — how much the node's modification depth
//               drifts when the grid doubles. 1.0 = resolution-invariant depth.
//   corr        Pearson of out@192 vs box-downsampled out@384 — does the LANDFORM survive.
//
// RED-RUN NUMBERS (recorded on the pre-fix build — kernels carried their length scales in cells)
// against the fixed build, same input, same params:
//   streampower (m=.5)  depthRatio 0.7185 -> 1.0279   (first fix attempt read 1.1076 and grew
//                       to 1.30 by k=4 — a single-point fit caught in cross-model review; the
//                       shipped K exponent is a CALIBRATION swept over m x k, see index.html)
//   streampower m=.2/.8 -> 0.9851 / 1.0592;  k=3 -> 1.0570 (was 1.201 under the first attempt)
//   hydraulic-droplets  depthRatio 0.8091 -> 1.0214
//   hydraulic-pipes     depthRatio 0.3827 -> 1.0199
//   erosion2-gpu        depthRatio 0.4986 -> 1.0770   (delta corr 0.8742 -> 0.9836)
//   hydrofix-corridor   depthRatio ~0.70  -> 0.9335   (corridor-dominated composite; the pure
//                       corridor deconvolves to ~0.97, and the rawcells REPORT case re-measures
//                       the legacy path live on every run: 0.6803 depth, 0.7786 delta corr)
// The [0.80, 1.25] band sits between every broken and fixed value with margin on both sides.
// The landform gate is DELTA correlation (out-in across the grid change): absolute output
// correlation is vacuous — an untouched fbm field already reads 0.9991 across this downsample.
// Armed at 0.85: every gated case measures >= 0.9075 fixed, while the legacy rawcells path
// reads 0.7786 and the lattice-thin breach 0.6235 (both below — the metric discriminates).
//
// The compensation contract under test: kernels take gridK (default 1 → byte-identical legacy
// behaviour for mountain/peak callers); node evals pass gridK = resScale() measured at NODE level
// (outside atFeatureScale), so at the 192 reference gridK=1 and the shipped look is preserved by
// construction. SCALE_RES=false remains the escape hatch to raw cell-unit behaviour.
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
    try { buildRun++; } catch (_) {}
    try { if (evalFrame) { cancelAnimationFrame(evalFrame); evalFrame = 0; } } catch (_) {}
    SCALE_RES = true; BUILD_QUALITY = 'interactive'; XF = null;
    Object.assign(terrainDef, { scale: 5000, height: 2600, baseElevation: 0, latitude: 46,
      north: 0, seaTemp: 6, lapseRate: 6.5, solarElevation: 45 });
    H_SCALE = terrainDef.height / terrainDef.scale;

    const A = {seed:7,freq:3,octaves:6,lac:2,gain:0.5};
    const mkParams = (type, over) => { const p = {};
      TYPES[type].params.forEach(pr => { p[pr.key] = cloneParams(pr.def); });
      return Object.assign(p, over || {}); };

    const down = (f, from, to) => { const o = new Float32Array(to * to), s = from / to;
      for (let y = 0; y < to; y++) for (let x = 0; x < to; x++) { let acc = 0, c = 0;
        for (let j = 0; j < s; j++) for (let i = 0; i < s; i++) { acc += f[((y*s+j)|0)*from + ((x*s+i)|0)]; c++; }
        o[y*to+x] = acc / c; } return o; };
    const rmsDelta = (a, b2) => { let se = 0;
      for (let i = 0; i < a.length; i++) { const d = b2[i] - a[i]; se += d * d; }
      return Math.sqrt(se / a.length); };
    const pearson = (a, b2) => { let sa=0,sb=0; const n2=a.length;
      for (let i=0;i<n2;i++){sa+=a[i];sb+=b2[i];} const ma=sa/n2,mb=sb/n2;
      let num=0,da=0,db=0;
      for (let i=0;i<n2;i++){const x=a[i]-ma,y=b2[i]-mb;num+=x*y;da+=x*x;db+=y*y;}
      return num/Math.max(1e-12,Math.sqrt(da*db)); };

    // Each case: node type, param overrides, GPU on/off, input slots builder, optional kHi
    // (high-side grid ratio; default 2 -> 384). Stream power gets the m AXIS and a k=3 point:
    // its K exponent is a CALIBRATION fitted over m x k (review found the first mapping was a
    // single-point fit at the default m, where the celerity term was exactly 1 in every gate).
    const CASES = [
      { key: 'streampower',        type: 'streampower', gpu: false, ins: s => [s, null, null] },
      { key: 'streampower-m02',    type: 'streampower', gpu: false, over: { m: 0.2 }, ins: s => [s, null, null] },
      { key: 'streampower-m08',    type: 'streampower', gpu: false, over: { m: 0.8 }, ins: s => [s, null, null] },
      // k=3 certifies the UNCAPPED mapping, so it runs Final (Interactive caps the diffusion
      // dose at k=2, which is a different — capped — contract).
      { key: 'streampower-k3',     type: 'streampower', gpu: false, kHi: 3, quality: 'final', ins: s => [s, null, null] },
      { key: 'hydraulic-droplets', type: 'hydraulic',   gpu: false, over: { engine: 'droplets' }, ins: s => [s, null] },
      { key: 'hydraulic-pipes',    type: 'hydraulic',   gpu: true,  ins: s => [s, null] },
      { key: 'erosion2-gpu',       type: 'erosion2',    gpu: true,  ins: s => [s, null] },
      // hydrofix is two mechanisms with different lattice contracts. The soft accumulation
      // CORRIDOR is a landform (world width, world depth) — gated at downcut=1 where it
      // dominates. The descent ENFORCEMENT is a 1-cell-wide breach, a lattice operation like
      // depression breaching itself: its rms contribution shrinks ~1/sqrt(k) BY DESIGN, so the
      // breach-dominated case is corr-gated but its depth is REPORTED, not banded — a wide band
      // that passes the broken build would be vacuous (fix=1 because the shipped default .52 is
      // near-inert, a separate queued defect).
      // corridor case: PRE-FILLED input makes the measurement corridor-DOMINATED, not pure —
      // measured ~85% of delta energy is the soft cut; the eps-descent enforcement across the
      // flats the fill leaves contributes ~15% and carries its 1/sqrt(k) signature, so the
      // pure-corridor ratio deconvolves to ~0.97 and the reported composite (~0.93) slightly
      // UNDER-reports the fix.
      { key: 'hydrofix-corridor',  type: 'hydrofix',    gpu: false, over: { fix: 1, downcut: 1 },
        prep: f => priorityFloodFill(f), ins: s => [s, null] },
      { key: 'hydrofix-breach',    type: 'hydrofix',    gpu: false, over: { fix: 1 }, depthReportOnly: true, ins: s => [s, null] },
      // Live record of the legacy path: SCALE_RES=false disables every compensation (the user
      // escape hatch to raw cell units), which is bit-exactly the pre-fix node. Its drift is
      // REPORTED each run so the armed-against broken value stays a measurement, not a memory.
      { key: 'hydrofix-corridor-rawcells', type: 'hydrofix', gpu: false, over: { fix: 1, downcut: 1 },
        prep: f => priorityFloodFill(f), scaleRes: false, depthReportOnly: true, ins: s => [s, null] },
      // The app's DEFAULT working resolution is 512 (k=2.667), where the Interactive tier cap
      // grants pipes only 2/2.667 of the grid ratio. Report how far the default tier actually
      // sits from the certified band — the cap is a documented trade, not a secret.
      { key: 'hydraulic-pipes-512-interactive', type: 'hydraulic', gpu: true, kHi: 512 / 192,
        depthReportOnly: true, ins: s => [s, null] },
    ];

    const out = { gpuAvailable: GPU.init(), cases: {} };
    for (const c of CASES) {
      if (c.gpu && !out.gpuAvailable) { out.cases[c.key] = { skipped: 'GPU unavailable' }; continue; }
      USE_GPU = c.gpu; SCALE_RES = c.scaleRes !== false;
      BUILD_QUALITY = c.quality || 'interactive';
      const params = mkParams(c.type, c.over);
      const t0 = performance.now();
      const HI = Math.round(192 * (c.kHi || 2));
      RES = 192;
      const in192 = c.prep ? c.prep(fbmField(gnoise, A)) : fbmField(gnoise, A);
      const out192 = TYPES[c.type].eval(params, c.ins(in192));
      RES = HI;
      const inHi = c.prep ? c.prep(fbmField(gnoise, A)) : fbmField(gnoise, A);
      const outHi = TYPES[c.type].eval(params, c.ins(inHi));
      RES = 192;
      const d192 = rmsDelta(in192, out192), dHi = rmsDelta(inHi, outHi);
      // deltaCorr correlates the MODIFICATIONS (out - in), not the outputs: the absolute-output
      // correlation of an untouched fbm field across this downsample is already 0.9991, so an
      // identity node would pass an absolute gate — the modification is what must survive.
      const del192 = new Float32Array(out192.length), delHi = new Float32Array(outHi.length);
      for (let i = 0; i < del192.length; i++) del192[i] = out192[i] - in192[i];
      for (let i = 0; i < delHi.length; i++) delHi[i] = outHi[i] - inHi[i];
      out.cases[c.key] = {
        reportOnly: !!c.depthReportOnly,
        depth192: +d192.toFixed(5), depthHi: +dHi.toFixed(5),
        depthRatio: +(dHi / Math.max(1e-9, d192)).toFixed(4),
        corr: +pearson(out192, down(outHi, HI, 192)).toFixed(4),
        deltaCorr: +pearson(del192, down(delHi, HI, 192)).toFixed(4),
        ms: Math.round(performance.now() - t0),
      };
    }
    USE_GPU = true; SCALE_RES = true;
    return out;
  });

  const gates = [];
  const gate = (name, pass, detail) => gates.push({ name, pass: !!pass, detail });
  console.log('== erosion grid-scale invariance (192 vs 384, SCALE_RES on) ==');
  for (const [k, v] of Object.entries(r.cases)) {
    console.log(k.padEnd(19), JSON.stringify(v));
    if (v.skipped) { gate(k, false, v.skipped); continue; }
    if (v.reportOnly) {
      console.log(`REPORT ${k}  depthRatio=${v.depthRatio} deltaCorr=${v.deltaCorr} — NOT gated: `
        + (k.endsWith('rawcells')
          ? `legacy raw-cell path (SCALE_RES off), the live measurement of the drift the gates are armed against`
          : k.includes('512')
            ? `the app-default 512 working resolution under the Interactive travel cap (gk = 2 of 2.667) — the documented tier trade, measured live; Final restores the band`
            : `the 1-cell breach shrinks ~1/sqrt(k) by design (expected ~0.70 at k=2); a band wide enough to pass it would be vacuous`));
      gate(`${k} modified`, v.depth192 >= 2e-5,
        `depth192=${v.depth192} (identity guard: a node that modifies nothing proves nothing)`);
      // The two legacy/lattice cases are the EVIDENCE that the 0.85 delta bar discriminates;
      // if either drifts above it, the landform metric has silently stopped meaning anything.
      if (k === 'hydrofix-corridor-rawcells' || k === 'hydrofix-breach')
        gate(`${k} discriminates`, v.deltaCorr < 0.85,
          `deltaCorr=${v.deltaCorr} — must stay BELOW the 0.85 bar the real gates are armed at`);
    } else {
      gate(`${k} depth`, v.depthRatio >= 0.80 && v.depthRatio <= 1.25,
        `depthRatio=${v.depthRatio} (target 1.0 — modification depth must survive a grid change)`);
      gate(`${k} modified`, v.depth192 >= 2e-5,
        `depth192=${v.depth192} (identity guard: a node that modifies nothing proves nothing)`);
      gate(`${k} landform`, v.deltaCorr >= 0.85,
        `deltaCorr=${v.deltaCorr} (the MODIFICATION must survive the grid change; abs corr `
        + `${v.corr} is not evidence — an untouched field already reads 0.9991)`);
    }
  }
  let fail = 0;
  for (const g of gates) { console.log(`${g.pass ? 'PASS' : 'FAIL'}  ${g.name}  ${g.detail}`); if (!g.pass) fail++; }
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(fail || errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
