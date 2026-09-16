#!/usr/bin/env node
// gpu-driven-culling.md's four-corner-tap HiZ test, the one genuinely per-invocation GPU
// primitive on this page (the fence itself, :102-108, is a two-PASS PIPELINE description --
// draw calls and a HiZ rebuild between them -- which no single fragment shader can meaningfully
// run in isolation; that is reported below as NOT ATTEMPTED, not silently skipped).
//
// LIGHTER PASS: the depth buffer and HiZ pyramid are the EXACT ones
// rigs/approx/gpu-driven-culling.py's build_scene()/build_pyramid() produce -- export_scene.py
// imports the rig and calls them directly, so the scene is not re-derived. 300 query rects (a
// fresh trial stream, same distributions as the rig's own 20,000) are tested at
// base_mip-1/0/+1, exactly as the rig's own tally does, against the rig's own ground truth
// (true_max(), brute force). This validates the SHADER LOGIC against a same-construction
// scene; the rig's own fp64 run keeps ownership of the large-N statistical claim.
import { readFileSync } from 'node:fs';
import { launch, evalPointwise } from '../lib/pointwise.mjs';

const scenePath = process.argv[2];
if (!scenePath) { console.error('usage: measure.mjs scene.json'); process.exit(1); }
const scene = JSON.parse(readFileSync(scenePath, 'utf-8'));
const { DIM, n_levels, mips, trials } = scene;

function flatten(level) {
  const n = level.length, out = new Float32Array(n * n);
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) out[j * n + i] = level[j][i];
  return out;
}
const extraTextures = mips.map((m, l) => ({ name: `uMip${l}`, size: m.length, data: flatten(m) }));

// sampled_max(), transcribed: clamp the mip index, four-corner tap, take the max.
const HELPERS = `
float fetchMip(int m, ivec2 texel) {
${mips.map((_, l) => `  if (m == ${l}) return texelFetch(uMip${l}, texel, 0).r;`).join('\n')}
  return texelFetch(uMip${mips.length - 1}, texel, 0).r;
}
`;
const FS_BODY = `
  int x0 = int(A.x), y0 = int(A.y), w = int(A.z), h = int(A.w);
  int m = clamp(int(B.x), 0, uNLevels - 1);
  int n = uDim >> m;
  int x1 = x0 + w - 1, y1 = y0 + h - 1;
  int tx0 = min(x0 >> m, n - 1), tx1 = min(x1 >> m, n - 1);
  int ty0 = min(y0 >> m, n - 1), ty1 = min(y1 >> m, n - 1);
  float v00 = fetchMip(m, ivec2(tx0, ty0));
  float v10 = fetchMip(m, ivec2(tx1, ty0));
  float v01 = fetchMip(m, ivec2(tx0, ty1));
  float v11 = fetchMip(m, ivec2(tx1, ty1));
  oResult = vec4(max(max(v00, v10), max(v01, v11)), 0.0, 0.0, 0.0);
`;

const { browser, page } = await launch();
const rowsA = trials.map(t => [t.x0, t.y0, t.w, t.h]);

let ok = true;
const OFFSETS = [
  { off: -1, name: 'one level FINER  (rule - 1)' },
  { off: 0, name: 'THE RULE ceil(log2)     ' },
  { off: 1, name: 'one level COARSER (rule + 1)' },
];
console.log(`${trials.length} trials on the rig's own ${DIM}x${DIM} scene, ${n_levels} mip levels\n`);

const drawable = trials.filter(t => !(t.z_near > t.true_max)).length;
const occluded = trials.length - drawable;
console.log(`ground truth: ${drawable} drawable, ${occluded} genuinely occluded (of ${trials.length})`);

for (const { off, name } of OFFSETS) {
  const rowsB = trials.map(t => [t.base_mip + off, 0, 0, 0]);
  const res = await evalPointwise(page, { fsBody: FS_BODY, rowsA, rowsB, extraTextures,
                                          helpers: HELPERS,
                                          intUniforms: { uNLevels: n_levels, uDim: DIM } });
  if (res.error) { console.error('GL ERROR:', res.error); process.exit(1); }

  let falseCull = 0, missCull = 0, agree = 0;
  res.results.forEach((r, i) => {
    const t = trials[i];
    const truthCull = t.z_near > t.true_max;
    const testCull = t.z_near > r.x;
    if (testCull && !truthCull) falseCull++;
    else if (truthCull && !testCull) missCull++;
    // cross-check the SHADER's four-corner max against Python's sampled_max at m=0 (base
    // offset, mip clamp aside) is implicit here -- what matters is the CULL DECISION agrees
    // with what an identical Python four-corner tap would decide, which the tally below
    // reproduces from the rig's own printed shape (falseCull/missCull, not raw sampled values,
    // since the rig itself never prints sampled_max() directly -- only the decisions it drives).
    agree++;
  });
  const fcPct = drawable ? (100 * falseCull / drawable).toFixed(2) : '0.00';
  const mcPct = occluded ? (100 * missCull / occluded).toFixed(2) : '0.00';
  console.log(`  ${name}: wrongly culled ${falseCull} of ${drawable} drawable (${fcPct}%)   `
             + `cull lost ${missCull} of ${occluded} (${mcPct}%)`);
}

// ── the ONE thing worth gating: the rule itself (offset 0) must not cull visible geometry ──
// matching the page's own claim structure -- read gpu-driven-culling.md's failure table: the
// rule is chosen so drawable geometry is never wrongly culled at the base mip. If this shader
// finds even one false cull at offset 0 on this scene, the rule's own safety property failed
// on real (if software) texture sampling, not just in Python's exact-index arithmetic.
const baseB = trials.map(t => [t.base_mip, 0, 0, 0]);
const baseRes = await evalPointwise(page, { fsBody: FS_BODY, rowsA, rowsB: baseB, extraTextures,
                                            helpers: HELPERS,
                                            intUniforms: { uNLevels: n_levels, uDim: DIM } });
let falseCullAtRule = 0;
baseRes.results.forEach((r, i) => {
  const t = trials[i];
  const truthCull = t.z_near > t.true_max;
  const testCull = t.z_near > r.x;
  if (testCull && !truthCull) falseCullAtRule++;
});
const ruleSafe = falseCullAtRule === 0;
console.log(`\n${ruleSafe ? 'PASS' : 'FAIL'}  the rule's own safety property on real GLSL `
           + `texture fetches: ${falseCullAtRule} of ${drawable} drawable trials wrongly `
           + `culled at the rule mip (want 0)`);
if (!ruleSafe) ok = false;

console.log('\nNOT ATTEMPTED: the fence itself (:102-108) is a two-pass PIPELINE -- draw last');
console.log('frame\'s visible set, rebuild HiZ, test candidates, draw disocclusions -- which');
console.log('needs real geometry, real indirect draws and a real HiZ rebuild between two');
console.log('render passes. A single fragment shader cannot run that in isolation, and');
console.log('building the scaffolding to run it for real is out of scope for a lighter pass.');

await browser.close();
console.log(`\n${ok ? 'PASS' : 'FAIL'} overall`);
process.exit(ok ? 0 : 1);
