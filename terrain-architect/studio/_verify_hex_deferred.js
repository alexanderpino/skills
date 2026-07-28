// The debt phase 8 left owed: the deferred compositor's GLSL sampler is verified NUMERICALLY
// against the CPU sampler, not just structurally.
//
// Why it needs its own oracle. The compositor reads the height/water textures with its own
// hand-written bilinear (latTap) and its own world->uv mapping (worldUV), neither of which the
// CPU path touches. On hex both had to change: the mesh puts rows at sqrt(3)/2 device spacing
// (so reading device z as v walks ~6.7% of the map off) and odd rows sit half a cell right. A
// shader that samples the wrong texel produces wrong per-pixel normals, shadows, AO and water
// depth while every CPU-side gate stays green - which is exactly the kind of gap this suite
// exists to close.
//
// METHOD. Rather than trying to read the compositor's internal values (they are consumed inside
// one fragment shader and never written out), compile a small PROBE program that #includes the
// same two functions verbatim - lifted out of the live shader source at runtime, so the probe
// cannot drift from what actually ships - renders them into an RGBA32F target at a set of world
// points, reads that back, and compares against the CPU sampleBilinear at the same world points.
//
// MEASURED (see gate detail strings). The pre-fix shader, driven with uRowScale forced to 1.0,
// is the built-in negative control: it is the old square-only code path exactly.
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));

// Lift worldUV + latTap out of the SHIPPED file (the same one the page loads), by brace
// matching. Reading the source rather than hand-copying it is the point: a hand-copied shader
// keeps passing after someone edits the real one.
const SRC = fs.readFileSync(path.resolve(__dirname, 'index.html'), 'utf8');
function grabFn(sig) {
  const i = SRC.indexOf(sig);
  if (i < 0) return null;
  let d = 0, j = SRC.indexOf('{', i);
  if (j < 0) return null;
  for (let k = j; k < SRC.length; k++) {
    if (SRC[k] === '{') d++;
    else if (SRC[k] === '}') { d--; if (!d) return SRC.slice(i, k + 1); }
  }
  return null;
}
const FN_WORLD = grabFn('vec2 worldUV('), FN_TAP = grabFn('float latTap(');

(async () => {
  if (!FN_WORLD || !FN_TAP) {
    console.log('SETUP FAILURE: could not lift the compositor helpers from index.html '
      + `(worldUV=${!!FN_WORLD} latTap=${!!FN_TAP})`);
    process.exit(1);
  }
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1800);

  const r = await p.evaluate(({ fnWorld, fnTap }) => {
    const out = { liftedFromLiveShader: true }, HR = Math.sqrt(3) / 2;
    if (!gl) return { noGL: true };
    const N = 64;                      // probe grid: N*N world points rendered in one pass

    const probeFS = `#version 300 es
      precision highp float; precision highp int;
      out vec4 frag;
      uniform sampler2D tx; uniform float uRES,uWpx,uRowScale; uniform int uN;
      ${fnWorld}
      ${fnTap}
      void main(){
        ivec2 q=ivec2(gl_FragCoord.xy);
        // walk the probe grid across the terrain's DEVICE extent, exactly as the compositor sees
        // it: x in [-1,1], z in [-uRowScale,uRowScale]
        float fx=(float(q.x)+0.5)/float(uN), fz=(float(q.y)+0.5)/float(uN);
        vec2 pxz=vec2(fx*2.0-1.0,(fz*2.0-1.0)*uRowScale);
        frag=vec4(latTap(tx,worldUV(pxz)),0.0,0.0,1.0);
      }`;

    const run = (lat) => {
      terrainDef.lattice = lat; RES = 192; const n = RES, hex = lat === 'hex';
      // A world-linear ramp: correct interpolation is EXACT, so any error is the sampler's.
      const A = 0.0131, B = -0.0087;
      const f = new Float32Array(n * n);
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const wx = x + (hex ? 0.5 * (y & 1) : 0), wy = y * (hex ? HR : 1);
        f[y * n + x] = A * wx + B * wy;
      }
      const tex = GPU.upload('hexDeferredProbe', n, f);
      const prog = GPU.prog('hexDeferredProbe', probeFS);
      const target = GPU.rt('hexDeferredProbeOut', N);
      GPU.run(prog, N, target, pr => {
        gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
        gl.uniform1i(u(pr, 'tx'), 0);
        gl.uniform1f(u(pr, 'uRES'), n); gl.uniform1f(u(pr, 'uWpx'), 1 / n);
        gl.uniform1f(u(pr, 'uRowScale'), hex ? HR : 1);
        gl.uniform1i(u(pr, 'uN'), N);
      });
      const got = GPU.read(target, N);
      // CPU reference at the SAME world points
      let maxErr = 0, se = 0, cnt = 0;
      for (let qy = 0; qy < N; qy++) for (let qx = 0; qx < N; qx++) {
        const fx = (qx + 0.5) / N, fz = (qy + 0.5) / N;
        // Device -> world cell units in the SHADER's own convention. The texture treats the
        // field as n texels spanning uv [0,1] (cell i at uv=(i+0.5)/n), so uv*n-0.5 IS the cell
        // coordinate. Using the MESH's convention here instead (cell i at uv=i/(n-1)) offsets
        // the reference by up to half a cell and shows up as a flat ~0.0026 error on BOTH
        // lattices - see the REPORT below, which is a real finding but not this gate's subject.
        const wx = fx * n - 0.5;
        const rowF = fz * n - 0.5;
        const wy = hex ? rowF * HR : rowF;
        // skip the outer ring: the shader clamps at texel edges, the CPU clamps at cell edges,
        // and disagreeing about the boundary is not what this gate is about
        if (wx < 2 || wx > n - 3 || rowF < 2 || rowF > n - 3) continue;
        const want = sampleBilinear(f, wx, wy);
        const e = Math.abs(got[qy * N + qx] - want);
        if (e > maxErr) maxErr = e; se += e * e; cnt++;
      }
      const range = Math.abs(A) * n + Math.abs(B) * n * (hex ? HR : 1);
      return { maxErr: +maxErr.toExponential(3), rms: +Math.sqrt(se / cnt).toExponential(3),
        relMax: +(maxErr / range).toExponential(3), probes: cnt };
    };

    out.hex = run('hex');
    out.square = run('square');

    // NEGATIVE CONTROL: drive the hex field through the shader with uRowScale forced to 1.0 -
    // that is bit-for-bit the pre-fix square-only path, on hex data.
    {
      terrainDef.lattice = 'hex'; RES = 192; const n = RES;
      const A = 0.0131, B = -0.0087;
      const f = new Float32Array(n * n);
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++)
        f[y * n + x] = A * (x + 0.5 * (y & 1)) + B * (y * HR);
      const tex = GPU.upload('hexDeferredProbe', n, f);
      const prog = GPU.prog('hexDeferredProbe', probeFS);
      const target = GPU.rt('hexDeferredProbeOut', N);
      GPU.run(prog, N, target, pr => {
        gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
        gl.uniform1i(u(pr, 'tx'), 0);
        gl.uniform1f(u(pr, 'uRES'), n); gl.uniform1f(u(pr, 'uWpx'), 1 / n);
        gl.uniform1f(u(pr, 'uRowScale'), 1);          // <- the pre-fix behaviour
        gl.uniform1i(u(pr, 'uN'), N);
      });
      const got = GPU.read(target, N);
      let maxErr = 0, cnt = 0;
      for (let qy = 0; qy < N; qy++) for (let qx = 0; qx < N; qx++) {
        const fx = (qx + 0.5) / N, fz = (qy + 0.5) / N;
        const wx = fx * n - 0.5, rowF = fz * n - 0.5;
        if (wx < 2 || wx > n - 3 || rowF < 2 || rowF > n - 3) continue;
        const want = sampleBilinear(f, wx, rowF * HR);
        maxErr = Math.max(maxErr, Math.abs(got[qy * N + qx] - want)); cnt++;
      }
      const range = Math.abs(A) * n + Math.abs(B) * n * HR;
      out.hexUncorrected = { maxErr: +maxErr.toExponential(3), relMax: +(maxErr / range).toExponential(3), probes: cnt };
    }

    terrainDef.lattice = 'square'; RES = 512; buildIndex();
    return out;
  }, { fnWorld: FN_WORLD, fnTap: FN_TAP });

  const gates = []; const gate = (nm, pass, detail) => gates.push({ nm, pass: !!pass, detail });
  if (r.noGL) {
    console.log('SETUP FAILURE', JSON.stringify(r));
    console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
    await b.close(); process.exit(1);
  }
  // ARMING. Corrected reads 3.0e-8 (float32 epsilon); the uncorrected control reads 1.65e-3.
  // The FIRST tolerance I set here was 2e-3 - ABOVE the uncorrected value, so a pre-fix shader
  // would have passed G1. That is the vacuous-gate failure this suite exists to prevent, caught
  // only because G3 measures the broken path instead of assuming it would fail. 1e-5 sits ~330x
  // above the corrected value and ~165x below the broken one.
  const TOL = 1e-5;
  gate('G1 shader-matches-cpu-hex', r.hex.relMax < TOL,
    `GLSL latTap vs CPU sampleBilinear at matched world points, hex lattice, world-linear ramp: `
    + `relMax=${r.hex.relMax} rms=${r.hex.rms} over ${r.hex.probes} probes (tol ${TOL})`);
  gate('G2 shader-matches-cpu-square', r.square.relMax < TOL,
    `NEGATIVE CONTROL on the lattice the shader was written for: relMax=${r.square.relMax} `
    + `- passes on the pre-fix build too, so G1 measures hex handling and not the probe harness`);
  gate('G3 metric-discriminates', r.hexUncorrected.relMax > TOL * 10,
    `SECOND CONTROL - the same hex field through the shader with uRowScale forced to 1.0, which is `
    + `bit-for-bit the pre-fix square-only path: relMax=${r.hexUncorrected.relMax}, `
    + `${(r.hexUncorrected.relMax / Math.max(1e-12, r.hex.relMax)).toFixed(0)}x the corrected value. `
    + `Without this the tolerance could be unfalsifiable.`);
  gate('G4 lifted-from-live-shader', r.liftedFromLiveShader === true,
    `worldUV/latTap were extracted from the live compositor source at runtime, so the probe cannot `
    + `drift from what ships (a hand-copied shader would silently keep passing after an edit)`);

  console.log('== deferred compositor sampling, GLSL vs CPU ==');
  console.log('REPORT mesh-vs-texture convention  The compositor addresses the height texture by '
    + 'TEXEL CENTRE (cell i at uv=(i+0.5)/n) while the terrain MESH places cell i at uv=i/(n-1). '
    + 'Those differ by up to half a cell (zero at the centre, +-0.5 at the edges), on BOTH '
    + 'lattices - a pre-existing inconsistency this oracle surfaced while being written, not a hex '
    + 'defect and not introduced by the hex work. Reported, not gated: it is a shared-convention '
    + 'question about which mapping is canonical, and changing either side moves every deferred '
    + 'pixel on square too.');
  console.log(JSON.stringify({ hex: r.hex, square: r.square, hexUncorrected: r.hexUncorrected }, null, 1));
  let fail = 0;
  for (const g of gates) { console.log(`${g.pass ? 'PASS' : 'FAIL'}  ${g.nm}  ${g.detail}`); if (!g.pass) fail++; }
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(fail || errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
