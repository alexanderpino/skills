// Calibration evidence for the stream-power Res Lock exponent. The node ships
//   Kdt *= k^(1.198 - 1.018m)   (i.e. phi*(m) = 1.018m - 1.198, beta=0 family:
//   iterations unchanged, Udt unchanged, Ddt * k^2)
// History: the first fit (0.683m - 1.11) was measured against the 0.24-bounded diffusion
// substep; tightening the bound to 1/6 (ringing fix) moved the m=0.8 root by 0.17 and THIS
// HARNESS went red - exactly its job. The line was re-fitted on the re-derived roots
// (residuals <= 0.02 at all three m points).
// fitted by sweeping the kernel over m x k on the reference input. This script IS the sweep:
// it re-derives the per-m root phi* (the exponent that makes depthRatio(k)=1) by measuring a
// phi grid that BRACKETS the roots at k in {2,3}, linearly root-finding on the average, and
// gating that the shipped line stays within +/-0.15 of the measured roots. If the kernel's
// dynamics change (e.g. the diffusion substep bound), this goes red instead of the calibration
// silently rotting. Calibration, not derivation — the transient regime of a Braun-Willett
// implicit cascade at shipped iteration counts has no clean closed form; the steady-state
// exponent (1-2m) under-erodes it, which is why the fitted line sits below it.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1500);

  const r = await p.evaluate(() => {
    try { buildRun++; } catch (_) {}
    SCALE_RES = true; BUILD_QUALITY = 'interactive'; XF = null; USE_GPU = false;
    const A = {seed:7,freq:3,octaves:6,lac:2,gain:0.5};
    const rmsDelta = (a, b2) => { let se = 0;
      for (let i = 0; i < a.length; i++) { const d = b2[i] - a[i]; se += d * d; }
      return Math.sqrt(se / a.length); };
    // Node defaults mapped to physical quantities (strength .08 -> Kdt .16, uplift .35 ->
    // Udt .0014, iters 14, hillslope .9 -> Ddt .216) — the same regime the node gates run.
    const KDT = 0.16, UDT = 0.35 * 0.004, ITERS = 14, DDT = 0.9 * 0.24;
    const run = (k, m, phi) => {
      RES = 192 * k;
      const src = fbmField(gnoise, A);
      const out = streamPowerErode(src, {
        Kdt: KDT * Math.pow(k, -phi), Udt: UDT, m, iters: ITERS,
        uplift: null, Ddt: DDT * k * k,
      });
      RES = 192;
      return rmsDelta(src, out);
    };
    const res = {};
    for (const m of [0.2, 0.5, 0.8]) {
      const base = run(1, m, 0);
      const rows = [];
      // dphi grid around the steady-state centre 2m-1, chosen to BRACKET the transient roots
      // (which sit 0.35-0.55 below the centre).
      for (const dphi of [-1.3, -1.0, -0.7, -0.4, -0.1]) {
        const phi = 2 * m - 1 + dphi;
        const r2 = run(2, m, phi) / base, r3 = run(3, m, phi) / base;
        rows.push({ phi: +phi.toFixed(3), k2: +r2.toFixed(4), k3: +r3.toFixed(4),
          avg: +((r2 + r3) / 2).toFixed(4) });
      }
      // Linear root-find on avg(k2,k3) crossing 1 (ratio decreases as phi increases).
      let root = null;
      for (let i = 1; i < rows.length; i++) {
        const a = rows[i - 1], b2 = rows[i];
        if ((a.avg - 1) * (b2.avg - 1) <= 0) {
          root = a.phi + (b2.phi - a.phi) * (a.avg - 1) / (a.avg - b2.avg);
          break;
        }
      }
      res['m' + m] = { base: +base.toFixed(5), rows, root: root === null ? null : +root.toFixed(4),
        shipped: +(1.018 * m - 1.198).toFixed(4) };
    }
    return res;
  });

  const gates = [];
  console.log('== stream-power calibration (phi roots vs shipped 0.683m - 1.11) ==');
  for (const [mk, v] of Object.entries(r)) {
    console.log(mk, JSON.stringify(v.rows));
    const pass = v.root !== null && Math.abs(v.root - v.shipped) <= 0.12;
    gates.push(pass);
    console.log(`${pass ? 'PASS' : 'FAIL'}  ${mk}  root=${v.root} shipped=${v.shipped} |diff|=${
      v.root === null ? 'no bracket' : Math.abs(v.root - v.shipped).toFixed(4)}`);
  }
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(gates.every(Boolean) && !errors.length ? 0 : 1);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
