// Mass conservation for the hydraulic-erosion family: what erodes must deposit somewhere or be
// counted as export — erosion and deposition are one budget (09: "the single most under-used
// terrain assertion"). This oracle was written RED-FIRST against the pre-fix build, then
// cross-model reviewed; G5's first form was found to pass on the broken build AND move the
// wrong way under improvement (it scored the slope-preference of TOTAL deposition, which the
// near-uniform settled component dilutes toward 0.5) — replaced with the D/E discriminator.
//
//   RED-RUN NUMBERS (pre-fix build, RES=192, fbm seed 7, reference params):
//     - GPU pipes: deficit 0.9193 (E=316.1, D=25.5, D/E=0.081) — the readback kept only the red
//       (bed) channel; ALL still-suspended sediment (blue) was discarded. Post-fix: deficit
//       ~0.35 with ~231 units settled. The final boundary fix runs a replicated-continuation
//       apron behind a closed wall, then crops; the full padded simulation closes to numerical
//       precision while `cropExchange` honestly names transport across the authored crop.
//     - CPU droplets: deficit 0.4291 — the ledger shows most of that is LEGITIMATE boundary
//       export (droplets leaving with their load: 157.3 of E=382.0, 41.2%); the true interior
//       loss (dry-out/life-cap exits) was 7.9 (~2% of E on open terrain; closed basins should
//       raise the settled share BY MECHANISM — not measured here, this oracle runs open fbm).
//       The first closure form tolerated 5% — which turned out to be absorbing a real unnamed
//       mass SOURCE: border-clipped brush cells remove nothing while the droplet credits itself
//       in full (+1.25 units at radius 2, growing with the radius slider). The ledger now names
//       it (brushClipGain) and the identity closes exactly:
//         sumIn - sumOut = exported + lost - brushClipGain.
//
// GATES:
//   G1  gpu-mass-closes   GPU crop deficit (E-D)/E <= 0.15 — armed between broken 0.9193 and
//                         current ~0.04 with margin both sides.
//   G2  cpu-mass-closes   CPU budget closes through the ITEMIZED ledger: E-D ~ exported.
//   G3  diag gates        both engines write hydroMassDiag. GPU closure is measured over the
//                         padded closed simulation; CPU export is itemized.
//   G4  settle-is-opt-in  ledger-based: with settle nothing is lost and something settles;
//                         without it the same mass is lost and nothing settles. (The byte gate
//                         for the opt-out callers is _verify_digest.js — NOTE: that digest pins
//                         USE_GPU=false, so it guards exactly the CPU droplet path; flipping the
//                         digest to GPU would silently unguard the two settle:true sites.)
//   G5a fans-can-form     D/E >= 0.30 — the broken build scores 0.081, the fixed ~0.65; this is
//                         the "deposition exists as a phenomenon" gate that makes fans possible.
//   G5b no-beading (GPU)  max single-cell rise <= 0.06 (measured 0.033 fixed; erosion maxDrop
//                         0.0454 per _verify_gpu.js for scale). GPU-only by design: the CPU
//                         droplet engine's ordinary deposition peaks at ~0.096, so an absolute
//                         bound is unusable there — hence G5c.
//   G5c cpu-no-beading    DELTA gate: settle must not raise the CPU maxRise vs the no-settle
//                         run (a change that dumps the residual into one cell instead of the
//                         bilinear deposit1 fails here and nowhere else).
//   G6  border-no-trench  the ring0-vs-ring1 mean-delta gap is gated so a boundary regression
//                         goes red instead of surviving on prose.
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
    const out = {};
    RES = 192; buildIndex();
    const A = {seed:7,freq:3,octaves:6,lac:2,gain:0.5};
    const base = fbmField(gnoise, A);

    // E = net-eroded volume, D = net-deposited volume (per-cell net deltas; gross transport is
    // larger but unobservable from outside). deficit = fraction of eroded volume that vanished.
    const stats = (inp, res) => {
      let E = 0, D = 0, maxRise = 0, finite = true;
      for (let i = 0; i < inp.length; i++) {
        if (!Number.isFinite(res[i])) finite = false;
        const d = res[i] - inp[i];
        if (d < 0) E -= d; else { D += d; if (d > maxRise) maxRise = d; }
      }
      return { E: +E.toFixed(4), D: +D.toFixed(4), deficit: E > 0 ? +((E - D) / E).toFixed(4) : 0,
        depositShare: E > 0 ? +(D / E).toFixed(4) : 0, maxRise: +maxRise.toFixed(5), finite };
    };
    const grabDiag = () => (typeof hydroMassDiag !== 'undefined' && hydroMassDiag)
      ? JSON.parse(JSON.stringify(hydroMassDiag)) : null;

    // --- CPU droplets, production-style call (settle:true is what the hydraulic node passes).
    const cp = {droplets:15000,capacity:4,erode:.3,deposit:.3,inertia:.05,radius:2,seed:1};
    const cSettle = hydraulicErode(base, {...cp, settle:true});
    out.cpu = { ...stats(base, cSettle), diag: grabDiag() };

    // --- CPU droplets WITHOUT settle: the mountain/peak/canyon contract — must stay lossy.
    const cRaw = hydraulicErode(base, cp);
    out.cpuNoSettle = { ...stats(base, cRaw), diag: grabDiag() };

    // --- GPU pipes (settle is unconditional there: both production callers want it).
    out.gpuAvailable = GPU.init();
    if (out.gpuAvailable) {
      const g = gpuHydraulicPipes(base, {iters:48,capacity:6,erode:.35,deposit:.28,inertia:.05});
      out.gpu = { ...stats(base, g), diag: grabDiag() };
      let r0 = 0, c0 = 0, r1 = 0, c1 = 0;
      for (let y = 0; y < RES; y++) for (let x = 0; x < RES; x++) {
        const i = y * RES + x, d = g[i] - base[i];
        const ring = Math.min(x, y, RES - 1 - x, RES - 1 - y);
        if (ring === 0) { r0 += d; c0++; } else if (ring === 1) { r1 += d; c1++; }
      }
      out.gpu.ring0Mean = +(r0 / c0).toFixed(5);
      out.gpu.ring1Mean = +(r1 / c1).toFixed(5);
    }
    return out;
  });

  // ---- gates ----
  const gates = [];
  const gate = (name, pass, detail) => gates.push({ name, pass: !!pass, detail });

  // Closure is only meaningful against an ITEMIZED export ledger. A derived export
  // (exportedDerived:true) closes by construction and must never count as evidence. The full
  // identity is sumIn - sumOut = exported + lost - brushClipGain: `lost` so an unaccounted-loss
  // ledger cannot sneak under the tolerance, `brushClipGain` because border-clipped brush cells
  // are a genuine mass source the first closure form silently absorbed.
  const closure = d => (d && d.sumIn != null && d.exportedDerived === false)
    ? Math.abs((d.sumIn - d.sumOut) - ((d.exported || 0) + (d.lost || 0) - (d.brushClipGain || 0)))
      / Math.max(1e-6, d.sumIn - d.sumOut + (d.settled || 0))
    : null;

  if (r.gpuAvailable) {
    gate('G1 gpu-mass-closes', r.gpu.finite && r.gpu.deficit <= 0.15,
      `deficit=${r.gpu.deficit} (broken 0.9193; cropped continuation apron is ~0.04)`);
    // `exported === 0` used to be asserted here, and it was correct at the time: the field was a
    // placeholder the pipe ledger never filled in. It now carries a real figure accumulated over
    // the APRON RING — a cell set disjoint from the core — so the assertion measures the stronger
    // property instead of the placeholder.
    //
    // Why this matters: every other loss term on this object is a difference of sums over NESTED
    // cell sets (cropExchange = sumIn-sumOut, lost = sumSimIn-sumSimOut), so a closure identity
    // built from them holds by construction for ANY implementation, including one that deletes the
    // terrain. Core loss and apron gain are measured over disjoint cells, so if the kernel destroys
    // or creates mass the two disagree, and no subtraction of nested sums could ever show it.
    //
    // Measured on the shipped kernel: cropExchange 3.632687, exportedToApron 3.632644 over 6400
    // apron cells — 1.2e-5 relative. The 1e-3 bound is ~80x that float noise and ~800x below the
    // ~100% discrepancy a genuinely broken boundary would produce.
    const dg = r.gpu.diag || {};
    const exportAgreement = Math.abs(dg.exportedToApron - dg.cropExchange)
      / Math.max(1e-9, Math.abs(dg.cropExchange));
    gate('G3g gpu-diag', r.gpu.diag && dg.engine === 'pipes'
      && dg.boundaryPolicy === 'continuation-apron-closed-wall'
      && dg.boundaryApronCells >= 8
      && dg.exportedDerived === false
      && dg.apronCells > 0 && Number.isFinite(dg.exportedToApron)
      && exportAgreement <= 1e-3
      && Math.abs(dg.nonConservation) < 0.01
      && Math.abs(dg.lost) < 0.01
      && Number.isFinite(dg.cropExchange) && dg.settled > 0,
      `agreement=${exportAgreement.toExponential(2)} ` + JSON.stringify(r.gpu.diag));
    gate('G5a fans-can-form', r.gpu.depositShare >= 0.30,
      `D/E=${r.gpu.depositShare} (broken 0.081 — deposition must exist as a phenomenon)`);
    gate('G5b no-beading', r.gpu.maxRise <= 0.06,
      `maxRise=${r.gpu.maxRise} (terminal settle must not print spikes; maxDrop ~0.0454 for scale)`);
    const trenchGap = +(r.gpu.ring1Mean - r.gpu.ring0Mean).toFixed(5);
    gate('G6 border-no-trench', trenchGap <= 0.0045,
      `ring0=${r.gpu.ring0Mean} ring1=${r.gpu.ring1Mean} gap=${trenchGap}`);
  } else {
    gate('G1 gpu-mass-closes', false, 'GPU unavailable — cannot verify the production pipe path');
  }
  gate('G2 cpu-mass-closes', r.cpu.diag && closure(r.cpu.diag) != null && closure(r.cpu.diag) <= 0.01,
    `closure=${r.cpu.diag ? closure(r.cpu.diag) : 'n/a'} deficit=${r.cpu.deficit} diag=${JSON.stringify(r.cpu.diag)}`);
  gate('G5c cpu-no-beading', r.cpu.maxRise <= r.cpuNoSettle.maxRise + 0.005,
    `settle maxRise=${r.cpu.maxRise} vs noSettle ${r.cpuNoSettle.maxRise} (residual must splat via deposit1, never one cell)`);
  gate('G3c cpu-diag', r.cpu.diag && r.cpu.diag.engine === 'droplets'
    && r.cpu.diag.exportedDerived === false
    && r.cpu.diag.settled >= 0 && r.cpu.diag.exported >= 0, JSON.stringify(r.cpu.diag));
  // Gate the flag on the LEDGER, not on deficit magnitude: on open terrain most of the CPU
  // budget is legitimate boundary export (droplets leave with their load), so the settled share
  // is small (~2% of E here) and a magnitude gate would be noise.
  const dS = r.cpu.diag, dN = r.cpuNoSettle.diag;
  gate('G4 settle-is-opt-in', dS && dN
    && dS.lost === 0 && dS.settled > 0
    && dN.settled === 0 && dN.lost > 0
    && r.cpuNoSettle.deficit >= r.cpu.deficit,
    `settle:{settled:${dS && +dS.settled.toFixed(3)},lost:${dS && dS.lost}} noSettle:{settled:${dN && dN.settled},lost:${dN && +(+dN.lost).toFixed(3)}}`);

  console.log('== erosion mass conservation ==');
  console.log('cpu       ', JSON.stringify(r.cpu));
  console.log('cpuNoSettle', JSON.stringify(r.cpuNoSettle));
  console.log('gpu       ', r.gpuAvailable ? JSON.stringify(r.gpu) : 'GPU NOT AVAILABLE');
  let fail = 0;
  for (const g of gates) { console.log(`${g.pass ? 'PASS' : 'FAIL'}  ${g.name}  ${g.detail}`); if (!g.pass) fail++; }
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(fail || errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
