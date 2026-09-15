#!/usr/bin/env node
// caustics.md's two scalar formulas -- exact unpolarised Fresnel (:103-104) and the
// Henyey-Greenstein backscatter fraction B(phase_g) (:99-101) -- run as real GLSL. Both are
// already exhaustively checked in fp64 by rigs/optics/caustics.py; the value this adds is
// confirming the SAME closed forms survive real fp32 shader arithmetic at the page's own
// stated points, which no rig here has done before. LIGHTER PASS: two formulas, no loop, no
// state, no branch worth stress-testing (unlike water-rendering, this page raises no
// NaN/undefined-behaviour warning about either one) -- so this is the shared pointwise
// harness and nothing more.
import { launch, evalPointwise } from '../lib/pointwise.mjs';

const { browser, page } = await launch();
let ok = true;

// ── 1. exact unpolarised Fresnel, at the page's own four angles and n (:104) ──────────────
const FRESNEL = `
  float theta = A.x, n = A.y;
  float c1 = cos(theta);
  float s  = sin(theta) / n;
  float c2 = sqrt(max(1.0 - s*s, 0.0));   // s < 1 always at these angles; guarded anyway
  float rs = (c1 - n*c2) / (c1 + n*c2);
  float rp = (n*c1 - c2) / (n*c1 + c2);
  float r  = (rs*rs + rp*rp) / 2.0;
  oResult = vec4(r, 0.0, 0.0, 0.0);
`;
const N_IOR = 1.335;                                        // caustics.md:104
const ANGLES_DEG = [0, 30, 45, 60];
const WANT_PCT   = [2.06, 2.17, 2.82, 6.01];                 // caustics.md:104, verbatim
const fres = await evalPointwise(page, {
  fsBody: FRESNEL,
  rowsA: ANGLES_DEG.map(d => [d * Math.PI / 180, N_IOR, 0, 0]),
});
if (fres.error) { console.error('GL ERROR:', fres.error); process.exit(1); }
fres.results.forEach((r, i) => {
  const pct = r.x * 100;
  const good = Math.abs(pct - WANT_PCT[i]) <= 0.01;
  console.log(`${good ? 'PASS' : 'FAIL'}  R_ext at ${ANGLES_DEG[i]} deg, n=${N_IOR}: `
             + `shader ${pct.toFixed(4)}%, page ${WANT_PCT[i]}%`);
  if (!good) ok = false;
});

// ── 2. Henyey-Greenstein backscatter fraction, at the page's own phase_g (:101) ───────────
const HG_B = `
  float g = A.x;
  float b = (1.0 - g*g) / (2.0*g) * (1.0/sqrt(1.0 + g*g) - 1.0/(1.0 + g));
  oResult = vec4(1.0 / b, 0.0, 0.0, 0.0);   // 1/B is what the page prints (:101, "58.9*b_b")
`;
const PHASE_G = 0.924;                                       // caustics.md:101
const WANT_RECIP_B = 58.9;                                   // caustics.md:101, verbatim
const hg = await evalPointwise(page, { fsBody: HG_B, rowsA: [[PHASE_G, 0, 0, 0]] });
if (hg.error) { console.error('GL ERROR:', hg.error); process.exit(1); }
const recipB = hg.results[0].x;
const hgOk = Math.abs(recipB - WANT_RECIP_B) <= 0.05;
console.log(`${hgOk ? 'PASS' : 'FAIL'}  1/B(phase_g) at phase_g=${PHASE_G}: shader `
           + `${recipB.toFixed(3)}, page ${WANT_RECIP_B}`);
if (!hgOk) ok = false;

console.log('\n-- hardware-independent: neither formula branches or loops, so no step or');
console.log('   fetch count to report -- fixed-cost per-fragment arithmetic on any GL ES 3.00 device.');

await browser.close();
console.log(`\n${ok ? 'PASS' : 'FAIL'} overall`);
process.exit(ok ? 0 : 1);
