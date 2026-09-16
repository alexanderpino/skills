#!/usr/bin/env node
// Run heightfield-raymarching.md's :61-82 fence as an ACTUAL GLSL ES 3.00 fragment shader,
// in headless Chromium, against the EXACT scene rigs/approx/heightfield-raymarching.py runs
// (see export_scene.py) -- then compare hit distances against that scene's own closed-form
// reference, the same way the Python rig's gate 9 does.
//
// WHAT THIS IS.  A second, independent execution of the page's algorithm, in the language the
// page is actually written for (a shader), instead of a third CPython transcription of it.
// Every rig in this corpus transcribes a fence into Python; none has run it as a shader before
// today, and a shader-specific defect -- an ANGLE/SwiftShader precision quirk, a sampler-array
// indexing restriction, a branch-divergence assumption the fence's prose does not state -- is
// a failure mode nothing here has tested.
//
// WHAT THIS IS NOT, AND WHY.  This container has NO hardware GPU. WebGL2 here runs on
// SwiftShader, a software rasterizer (`ANGLE ... SwiftShader Device`), confirmed by
// caps.mjs/smoke.mjs before this script was written. THE WALL-CLOCK NUMBERS BELOW ARE NOT A
// FRAME COST ON ANY GPU A PLAYER OWNS. They are printed anyway, loudly labelled, because
// silently omitting them would look like nothing was measured; what is safe to trust from
// them is comparisons WITHIN this run (gate-on vs gate-off), never the absolute figure --
// exactly the caveat rigs/README.md states for the Python rigs' own CPython wall-clock, one
// level further down the stack.
//
// WHAT IS HARDWARE-INDEPENDENT, AND THEREFORE TRUSTWORTHY REGARDLESS OF THIS CONTAINER: the
// STEP COUNT per ray (how many loop iterations the fence's own while-loop takes) and the EXIT
// LEVEL. Both are outputs of the algorithm's control flow, not of how fast this machine
// executes it, and they reproduce on any conformant GLSL ES 3.00 implementation.
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { VS_FULLSCREEN, FS_MARCH } from './shaders.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const scenePath = process.argv[2] || path.join(HERE, 'scene.json');
const scene = JSON.parse(readFileSync(scenePath, 'utf-8'));

const { S0, NG, NLevels, field, rays } = scene;
const NUM_RAYS = rays.length;

// ── build the pyramid EXACTLY as _pyramid(h, "level0") does: level 0 is the base samples
// dilated 3x3 (periodic wrap -- ":146-147... Periodic, so floor wraps exactly"), each further
// level a 2x2 max-reduce of the one below. Ported line-for-line from _dilate3/_reduce2.
function dilate3(a) {
  const n = a.length, out = [];
  for (let j = 0; j < n; j++) {
    const row = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      let m = -Infinity;
      for (const dj of [-1, 0, 1]) for (const di of [-1, 0, 1]) {
        const v = a[((j + dj) % n + n) % n][((i + di) % n + n) % n];
        if (v > m) m = v;
      }
      row[i] = m;
    }
    out.push(row);
  }
  return out;
}
function reduce2(a) {
  const n = a.length / 2, out = [];
  for (let j = 0; j < n; j++) {
    const row = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      row[i] = Math.max(a[2 * j][2 * i], a[2 * j][2 * i + 1], a[2 * j + 1][2 * i], a[2 * j + 1][2 * i + 1]);
    }
    out.push(row);
  }
  return out;
}
const pyramid = [dilate3(field)];
for (let l = 1; l < NLevels; l++) pyramid.push(reduce2(pyramid[l - 1]));
if (pyramid.length !== NLevels) throw new Error(`pyramid has ${pyramid.length} levels, scene says ${NLevels}`);

function flatten(level) {
  const n = level.length, out = new Float32Array(n * n);
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) out[j * n + i] = level[j][i];
  return out;
}

const browser = await chromium.launch({
  executablePath: CHROME,
  args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'],
});
const page = await browser.newPage();
page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });

const result = await page.evaluate(({ vs, fs, S0, NG, NLevels, pyramidFlat, baseFlat, rayData, numRays, bisections, stepCap }) => {
  const canvas = document.createElement('canvas');
  canvas.width = numRays; canvas.height = 1;
  const gl = canvas.getContext('webgl2');
  if (!gl) return { error: 'no webgl2 context' };
  gl.getExtension('EXT_color_buffer_float');

  function compile(type, src) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }
  const prog = gl.createProgram();
  gl.attachShader(prog, compile(gl.VERTEX_SHADER, vs));
  gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return { error: gl.getProgramInfoLog(prog) };
  gl.useProgram(prog);

  const quad = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, quad);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, 'aPos');
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

  function makeFloatTex(unit, sizeN, data) {
    gl.activeTexture(gl.TEXTURE0 + unit);
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R32F, sizeN, sizeN, 0, gl.RED, gl.FLOAT, data);
    return t;
  }
  for (let l = 0; l < NLevels; l++) {
    const n = NG >> l;
    makeFloatTex(l, n, pyramidFlat[l]);
    gl.uniform1i(gl.getUniformLocation(prog, `uPyramid[${l}]`), l);
  }
  makeFloatTex(8, NG, baseFlat);
  gl.uniform1i(gl.getUniformLocation(prog, 'uBase'), 8);

  // ray texture: 2 texels wide (o+t0, d+t1), numRays tall, RGBA32F
  gl.activeTexture(gl.TEXTURE0 + 9);
  const rayTex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, rayTex);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, 2, numRays, 0, gl.RGBA, gl.FLOAT, rayData);
  gl.uniform1i(gl.getUniformLocation(prog, 'uRays'), 9);

  gl.uniform1i(gl.getUniformLocation(prog, 'uNLevels'), NLevels);
  gl.uniform1f(gl.getUniformLocation(prog, 'uS0'), S0);
  gl.uniform1i(gl.getUniformLocation(prog, 'uNG'), NG);
  gl.uniform1i(gl.getUniformLocation(prog, 'uBisections'), bisections);
  gl.uniform1i(gl.getUniformLocation(prog, 'uStepCap'), stepCap);

  const outTex = gl.createTexture();
  gl.activeTexture(gl.TEXTURE0 + 15);  // an unused unit -- TEXTURE0 is claimed by uPyramid[0], and rebinding it here silently clobbered that sampler's texture. This was the actual bug: not a shader-language finding, a texture-unit collision in this driver.
  gl.bindTexture(gl.TEXTURE_2D, outTex);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, numRays, 1, 0, gl.RGBA, gl.FLOAT, null);
  const fbo = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, outTex, 0);
  if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) {
    return { error: 'incomplete FBO: ' + gl.checkFramebufferStatus(gl.FRAMEBUFFER) };
  }
  gl.viewport(0, 0, numRays, 1);

  const N_TIMING_RUNS = 200;   // repeated to get a stable SwiftShader wall-clock reading
  const t0 = performance.now();
  for (let i = 0; i < N_TIMING_RUNS; i++) {
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  gl.finish();
  const t1 = performance.now();

  const pixels = new Float32Array(numRays * 4);
  gl.readPixels(0, 0, numRays, 1, gl.RGBA, gl.FLOAT, pixels);

  return {
    hits: Array.from({ length: numRays }, (_, i) => ({
      t: pixels[i * 4 + 0], steps: pixels[i * 4 + 1], exitLevel: pixels[i * 4 + 2],
    })),
    msPerDraw: (t1 - t0) / N_TIMING_RUNS,
    nDraws: N_TIMING_RUNS,
    glVersion: gl.getParameter(gl.VERSION),
    renderer: (() => { const d = gl.getExtension('WEBGL_debug_renderer_info');
      return d ? gl.getParameter(d.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER); })(),
  };
}, {
  vs: VS_FULLSCREEN, fs: FS_MARCH, S0, NG, NLevels,
  pyramidFlat: pyramid.map(flatten),
  baseFlat: flatten(field),
  rayData: (() => {
    const buf = new Float32Array(NUM_RAYS * 2 * 4);
    rays.forEach((r, i) => {
      buf[i * 8 + 0] = r.o[0]; buf[i * 8 + 1] = r.o[1]; buf[i * 8 + 2] = r.o[2]; buf[i * 8 + 3] = r.t0;
      buf[i * 8 + 4] = r.d[0]; buf[i * 8 + 5] = r.d[1]; buf[i * 8 + 6] = r.d[2]; buf[i * 8 + 7] = r.t1;
    });
    return buf;
  })(),
  numRays: NUM_RAYS,
  bisections: 6,     // the page's own mid-range figure at :50, "at 6 bisections"
  stepCap: 20000,    // matches the Python rig's _STATE_CAP -- a belt, not the argument, per :80
});

await browser.close();

if (result.error) {
  console.error('SHADER/GL ERROR:', result.error);
  process.exit(1);
}

console.log(`renderer: ${result.renderer}`);
console.log(`GL version: ${result.glVersion}`);
console.log(`${NUM_RAYS} rays, ${NLevels}-level pyramid over a ${NG}x${NG} field\n`);

// ── correctness: hit/miss/spurious against the Python rig's own closed-form reference ────
// Split by ray kind from the start: ascending/grazing are the GATED classes (span/2^6 below);
// primary and picking are NOT GATED, for the reasons the report below states in full, so a
// miss or a spurious hit on THOSE kinds must not flip the overall exit code -- doing so would
// contradict the very outcomes this file documents and reports.
const GATED_KINDS = new Set(['ascending', 'grazing']);
let ok = true;
let missed = 0, spurious = 0, agreeing = 0;
let gatedMissed = 0, gatedSpurious = 0;
const errsByKind = {};
const stepsByKind = {};
for (let i = 0; i < NUM_RAYS; i++) {
  const ray = rays[i];
  const got = result.hits[i];
  const ref = ray.ref;
  const gotHit = got.t >= 0.0;
  const refHit = ref !== null;
  const gated = GATED_KINDS.has(ray.kind);
  if (refHit && !gotHit) { missed++; if (gated) gatedMissed++; continue; }
  if (!refHit && gotHit) { spurious++; if (gated) gatedSpurious++; continue; }
  if (refHit && gotHit) {
    const err = Math.abs(got.t - ref);
    agreeing++;
    (errsByKind[ray.kind] ??= []).push(err);
  }
  (stepsByKind[ray.kind] ??= []).push(got.steps);
}

console.log(`hit/miss agreement: ${agreeing} agree, ${missed} missed (ref hit, shader missed), `
           + `${spurious} spurious (ref miss, shader hit)`);
console.log(`  of which, on the GATED classes (ascending/grazing): ${gatedMissed} missed, `
           + `${gatedSpurious} spurious`);
if (gatedMissed > 0 || gatedSpurious > 0) ok = false;

console.log('\nerror vs the Python rig\'s closed-form reference, by ray class, at 6 bisections:');
for (const [kind, errs] of Object.entries(errsByKind)) {
  const max = Math.max(...errs), mean = errs.reduce((a, b) => a + b, 0) / errs.length;
  console.log(`  ${kind.padEnd(10)} n=${errs.length.toString().padStart(3)}  `
             + `max=${(max * 1000).toFixed(3).padStart(9)} mm  mean=${(mean * 1000).toFixed(3).padStart(8)} mm  `
             + `avg steps=${(stepsByKind[kind].reduce((a, b) => a + b, 0) / stepsByKind[kind].length).toFixed(1)}`);
}

// ── THE FINDING APPLIES TO EVERY RAY CLASS, NOT ONLY "primary" ──────────────────────────
//
// An earlier version of this file reported ascending/grazing as a clean PASS and confined
// the fp32 finding to primary rays. That was wrong, and the wrongness was caught the same
// way everything else in this corpus is: by tracing a specific failure rather than trusting
// a class-level summary. 7 of 105 rays -- some ascending, some grazing -- MISS entirely.
// Traced one by hand (idx 71, ascending): the ray's z-coordinate crosses a mip-level cell
// boundary at a point where the true value is a few times 1e-7 away from exactly zero. In
// real GLSL fp32 it lands on the NEGATIVE side (z = -7.15e-7), and `floor`/`mod` correctly
// wrap that to the LAST row of the level's texture rather than the first -- exactly the
// periodic wrap this rig relies on, working as designed. The trajectory that follows from
// the wrapped cell diverges from the one a slightly different fp32 rounding would take.
//
// So the finding is broader than first reported: ANY ray whose trajectory crosses a
// mip-level boundary within about 1e-6 of exactly on it is subject to this sensitivity,
// REGARDLESS OF KIND. Primary and picking rays hit it often because they march far and
// cross many boundaries; ascending/grazing rays hit it rarely because they converge in a
// few dozen steps and rarely land on one. "Rarely" is not "never" -- 7 of 105 here -- and
// reporting the class as immune because a first pass did not sample the exception would
// have been exactly the kind of overclaim this corpus's registers exist to catch.
//
// The page's own :154-155 already documents fp32 sensitivity, but ONLY for the UNFIXED
// registration. This shader implements the CORRECT, fixed registration (the 3x3-dilated
// apron, matching _pyramid(h, "level0")) and still shows this sensitivity -- a genuinely
// new finding, now stated for what it actually is: a property of the ALGORITHM under fp32,
// triggered by trajectory, not a property of one ray class.
const GENERAL_BOUND_MM = (S0 / 64) * 1000; // span/2^6 for a one-texel span
const missedByKind = {};
for (let i = 0; i < NUM_RAYS; i++) {
  const ray = rays[i], got = result.hits[i];
  if (ray.ref !== null && got.t < 0) missedByKind[ray.kind] = (missedByKind[ray.kind] || 0) + 1;
}
for (const kind of ['ascending', 'grazing']) {
  const errs = errsByKind[kind] || [];
  const max = errs.length ? Math.max(...errs) * 1000 : 0;
  const miss = missedByKind[kind] || 0;
  const errBad = max > GENERAL_BOUND_MM * 1.05; // 5% slack for fp32 vs the Python rig's fp64
  const bad = errBad || miss > 0;
  const total = errs.length + miss;
  if (bad) {
    console.log(`FAIL  ${kind}: ${miss} of ${total} missed entirely (fp32 boundary `
               + `sensitivity, see above)${errBad ? `; worst error among the rest ${max.toFixed(3)} mm exceeds ${GENERAL_BOUND_MM.toFixed(3)} mm` : `; the ${errs.length} that hit are within ${GENERAL_BOUND_MM.toFixed(3)} mm`}`);
  } else {
    console.log(`PASS  ${kind}: all ${total} hit, worst error ${max.toFixed(3)} mm is within `
               + `span/2^6 = ${GENERAL_BOUND_MM.toFixed(3)} mm (+5% fp32 slack)`);
  }
  if (bad) ok = false;
}
console.log('\nNOT GATED, reported instead, and why:');
const pickErrs = errsByKind['picking'] || [];
if (pickErrs.length) {
  console.log(`  picking: max ${(Math.max(...pickErrs) * 1000).toFixed(1)} mm -- matches the Python rig's own`);
  console.log('           documented limit (its level-0 span is the rest of the ray; the fixed 8-step');
  console.log('           scan is not fine enough to bracket reliably over tens of metres). KNOWN, not new.');
}
const primErrs = errsByKind['primary'] || [];
if (primErrs.length) {
  const primSteps = stepsByKind['primary'] || [];
  console.log(`  primary: max ${(Math.max(...primErrs) * 1000 / 1000).toFixed(1)} m, mean `
             + `${(primErrs.reduce((a, b) => a + b, 0) / primErrs.length).toFixed(1)} m, `
             + `up to ${Math.max(...primSteps)} loop iterations on one ray.`);
  console.log('           NEW: fp32 execution of the CORRECTLY-registered fence livelocks near a');
  console.log('           mip-level cell boundary. The page documents fp32 sensitivity only for the');
  console.log('           UNFIXED registration (:154-155); this is the fixed one, still sensitive, on');
  console.log('           real (if software) fp32 hardware. See gaia/gpu/heightfield-raymarching/README.md.');
}

console.log('\n-- hardware-independent cost (portable to any conformant GL ES 3.00 device) --');
const allSteps = result.hits.map(h => h.steps);
console.log(`  steps per ray: min=${Math.min(...allSteps)} max=${Math.max(...allSteps)} `
           + `mean=${(allSteps.reduce((a, b) => a + b, 0) / allSteps.length).toFixed(2)}`);

console.log('\n-- SwiftShader software-raster wall-clock -- NOT a GPU frame cost, see this file\'s docstring --');
console.log(`  ${result.msPerDraw.toFixed(4)} ms/draw for ${NUM_RAYS} rays on ${result.renderer}`);
console.log(`  (${(result.msPerDraw / NUM_RAYS * 1000).toFixed(2)} µs/ray on SOFTWARE rasterisation; `
           + `meaningless as a frame-time prediction for any real GPU -- rigs/README.md `
           + `records the Python rigs' own CPython wall-clock varying 38.1-46.9x across three `
           + `containers, and software vs hardware rasterisation is a far larger gap than that)`);

writeFileSync(path.join(HERE, 'last-run.json'), JSON.stringify({
  ok, agreeing, missed, spurious,
  errsByKind: Object.fromEntries(Object.entries(errsByKind).map(([k, v]) => [k,
    { n: v.length, maxMm: Math.max(...v) * 1000, meanMm: v.reduce((a, b) => a + b, 0) / v.length * 1000 }])),
  stepsMean: allSteps.reduce((a, b) => a + b, 0) / allSteps.length,
  msPerDraw: result.msPerDraw, renderer: result.renderer, glVersion: result.glVersion,
}, null, 1));

console.log(`\n${ok ? 'PASS' : 'FAIL'} overall`);
process.exit(ok ? 0 : 1);
