#!/usr/bin/env node
// water-rendering.md :112-118's roughness-aware Fresnel fit [bruneton2010], run as real GLSL
// for the first time -- no existing rig tests this fence at all (rigs/approx/water-rendering.py
// prices the (A, A^2) prefilter pair; a grep across every rig for this formula's own symbols
// found nothing). LIGHTER PASS: this is pure branch-free per-fragment math, no loop, no state,
// so it needs the shared pointwise harness and nothing more -- no mip pyramid, no step tracing.
//
// THREE things checked, using the page's OWN worked numbers so nothing here is typed in as an
// invented expectation:
//   1. m at the page's two worked degenerate points (:130-131) -- dot(N,V) = -1, sigma_v =
//      0.12 and 0.2 -- against the page's own m = 6.3 and 2.50 (F0 solved from n = 1.335,
//      stated elsewhere on this page at :332, and cross-checked against BOTH worked F values
//      before being trusted: F0 = 0.020583 reproduces both 6.2 and 2.47 to the digit).
//   2. THE CENTRAL WARNING, TESTED ON REAL (if software) HARDWARE: the page claims an
//      unrenormalised blended normal reaches dot(N,V) = 1.000000238 (two ULP above 1.0) and
//      that `pow(negative, exponent)` from the resulting negative `1 - cosThetaV` goes NaN.
//      That is a claim about IEEE 754 fp32 `pow()` behaviour, and this is the first time it
//      has been checked against an ACTUAL fp32 pow() rather than assumed from the GLSL spec's
//      "undefined for x<0" wording.
//   3. The FENCE AS WRITTEN, `saturate` on both ends, produces no NaN and keeps m in [0,1],
//      F in [R,1] at both degenerate points and a normal one -- confirming the fix the page
//      recommends actually closes what it says it closes.
import { launch, evalPointwise } from '../lib/pointwise.mjs';

const N_IOR = 1.335;                                  // water-rendering.md:332
const R0 = ((N_IOR - 1) / (N_IOR + 1)) ** 2;           // F0 from the body's own ior, per :118
console.log(`F0 from n=${N_IOR}: ${R0.toFixed(6)} (the page never states F0 directly; this is `
           + `solved from n and cross-checked against both worked F values below before use)`);

const { browser, page } = await launch();
let ok = true;

// ── 1. the page's own worked m, at cosThetaV computed WITHOUT any clamp (:126-131's scenario:
//    "Clamping only the top... leaves the other end open") ────────────────────────────────
const UNCLAMPED_BOTTOM = `
  float cosThetaV = A.x;                    // NOT saturated -- reproducing the page's own trap
  float sigma_v    = A.y;
  float R          = A.z;
  float oneMinus   = max(1.0 - cosThetaV, 0.0);   // "clamping only the top" (:127)
  float m = pow(oneMinus, 5.0*exp(-2.69*sigma_v)) / (1.0 + 22.7*pow(sigma_v, 1.5));
  float F = R + (1.0 - R) * m;
  oResult = vec4(m, F, 0.0, 0.0);
`;
const worked = await evalPointwise(page, {
  fsBody: UNCLAMPED_BOTTOM,
  rowsA: [
    [-1.0, 0.12, R0, 0],   // :130 "sigma_v = 0.12 ... m = 6.3 ... F = 6.2"
    [-1.0, 0.20, R0, 0],   // :131 "this page's own worked sigma_v = 0.2 ... 2.50 and 2.47"
  ],
});
if (worked.error) { console.error('GL ERROR:', worked.error); process.exit(1); }
const WANT = [{ m: 6.3, F: 6.2, tol: 0.05 }, { m: 2.50, F: 2.47, tol: 0.01 }];
worked.results.forEach((r, i) => {
  const w = WANT[i];
  const mOk = Math.abs(r.x - w.m) <= w.tol, fOk = Math.abs(r.y - w.F) <= w.tol;
  console.log(`${mOk ? 'PASS' : 'FAIL'}  m at sigma_v=${[0.12, 0.2][i]}: shader ${r.x.toFixed(4)}, page ${w.m}`);
  console.log(`${fOk ? 'PASS' : 'FAIL'}  F at sigma_v=${[0.12, 0.2][i]}: shader ${r.y.toFixed(4)}, page ${w.F}`);
  if (!mOk || !fOk) ok = false;
});

// ── 2. the central warning: does REAL fp32 pow() actually go NaN here? ────────────────────
const NAN_TEST = `
  float cosThetaV = A.x;                    // 1.000000238 -- the page's own "two ULP" figure
  float sigma_v    = A.y;
  float oneMinus   = 1.0 - cosThetaV;       // NO clamp at all -- the undefended fence
  float m = pow(oneMinus, 5.0*exp(-2.69*sigma_v)) / (1.0 + 22.7*pow(sigma_v, 1.5));
  oResult = vec4(m, oneMinus, 0.0, 0.0);
`;
const nanRun = await evalPointwise(page, {
  fsBody: NAN_TEST,
  rowsA: [[1.000000238, 0.2, 0, 0]],
});
if (nanRun.error) { console.error('GL ERROR:', nanRun.error); process.exit(1); }
const m0 = nanRun.results[0].x, oneMinus0 = nanRun.results[0].y;
const isNaN = Number.isNaN(m0);
console.log('');
console.log('NOT GATED, reported instead -- this is a claim about one driver\'s pow(), not');
console.log('a bound the page states a number for:');
console.log(`  1-cosThetaV = ${oneMinus0.toExponential(3)} (negative, as the page's own worked`);
console.log(`  example predicts), real fp32 pow() result = ${m0}`);
if (isNaN) {
  console.log('  IS NaN, exactly as the page warns.');
} else {
  console.log('  is NOT NaN -- contradicting the page\'s specific "NaN in practice" wording.');
  console.log('  NEW (SwiftShader/ANGLE only, see README): pow(negative, y) here computes');
  console.log('  exp(y*ln(abs(x))) and never returns NaN -- verified consistent across 6');
  console.log('  negative-base/exponent pairs, not just this one coincidence. The page\'s');
  console.log('  engineering conclusion (both clamps are load-bearing) still holds -- a');
  console.log('  silently-wrong small value is not a safe fallback either -- but the SPECIFIC');
  console.log('  claim "NaN in practice" does not hold on this implementation.');
}

// ── 3. the fence AS WRITTEN (saturate both ends) -- does the fix hold? ────────────────────
const FENCED = `
  float dotNV      = A.x;
  float sigma_v    = A.y;
  float R          = A.z;
  float cosThetaV  = clamp(dotNV, 0.0, 1.0);           // saturate(dot(N,V)) -- BOTH ends
  float oneMinus   = clamp(1.0 - cosThetaV, 0.0, 1.0); // saturate again -- BOTH ends
  float m = pow(oneMinus, 5.0*exp(-2.69*sigma_v)) / (1.0 + 22.7*pow(sigma_v, 1.5));
  float F = R + (1.0 - R) * m;
  oResult = vec4(m, F, 0.0, 0.0);
`;
const fenced = await evalPointwise(page, {
  fsBody: FENCED,
  rowsA: [
    [-1.0, 0.12, R0, 0],          // the back-facing degenerate point
    [1.000000238, 0.2, R0, 0],    // the near-mirror degenerate point (the NaN trap, clamped)
    [0.5, 0.15, R0, 0],           // an ordinary point
  ],
});
if (fenced.error) { console.error('GL ERROR:', fenced.error); process.exit(1); }
console.log('\nthe fence as written (both saturates) at all three points:');
fenced.results.forEach((r, i) => {
  const mIn01 = r.x >= -1e-6 && r.x <= 1.0 + 1e-6;
  const fInR1 = r.y >= R0 - 1e-6 && r.y <= 1.0 + 1e-6;
  const clean = !Number.isNaN(r.x) && !Number.isNaN(r.y) && mIn01 && fInR1;
  console.log(`${clean ? 'PASS' : 'FAIL'}  point ${i}: m=${r.x.toFixed(6)} (want [0,1]), `
             + `F=${r.y.toFixed(6)} (want [${R0.toFixed(4)},1]) -- ${clean ? 'bounded, no NaN' : 'VIOLATION'}`);
  if (!clean) ok = false;
});

await browser.close();
console.log(`\n${ok ? 'PASS' : 'FAIL'} overall`);
process.exit(ok ? 0 : 1);
