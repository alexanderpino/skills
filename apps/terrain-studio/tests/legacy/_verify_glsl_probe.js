// Why does the deferred probe disagree with the CPU sampler on BOTH lattices after the compositor
// X/Y split? Prints the actual uniform values, the shader compile log, and a handful of probe
// points against their CPU reference, so the failure is located instead of guessed at.
const { chromium } = require('playwright-core');
const path = require('path');
const { liftOrDie, ENV_VAR } = require('./lift-glsl-source');
const EXE = process.env.STUDIO_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
// STUDIO_URL first, file:// only as the fallback — see the note in _verify_colorknobs.js.
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

// The lift used to be a private fs.readFileSync('../../index.html') + brace match that returned
// null on a miss, and the null went straight into the shader template below. That is the quiet
// failure this file's header used to admit to, and it is not hypothetical: run the old code
// against an ES-module-split copy (script body in src/legacy.js) and you get
//   fsOk:false  fsLog:"ERROR: 0:5: 'null' : syntax error"   "samples": []   exit 0
// — a probe that compared nothing and reported success. lift-glsl-source.js searches index.html
// AND src/**/*.js, so it keeps finding these before and after the split, and liftOrDie() exits 2
// naming the signature it could not find and every file it looked in. FN_WORLD/FN_TAP below are
// therefore guaranteed non-null by construction: there is no path from here into the template
// that carries a missing function.
const SIG_WORLD = 'vec2 worldUV(', SIG_TAP = 'float latTap(';
const LIFT = liftOrDie([SIG_WORLD, SIG_TAP], { label: 'the compositor helpers worldUV/latTap' });
const FN_WORLD = LIFT.code[SIG_WORLD], FN_TAP = LIFT.code[SIG_TAP];

(async () => {
  // Provenance, so a reader of the log can tell WHICH file the compiled GLSL came from instead of
  // assuming index.html forever.
  console.log('lifted ' + JSON.stringify({
    from: LIFT.sources.mode === 'file' ? LIFT.sources.searched[0] : LIFT.sources.root,
    override: LIFT.sources.override ? `${ENV_VAR}=${LIFT.sources.override}` : null,
    searched: LIFT.sources.searched,
    worldUV: `${LIFT.found[SIG_WORLD].file}:${LIFT.found[SIG_WORLD].line}`,
    latTap: `${LIFT.found[SIG_TAP].file}:${LIFT.found[SIG_TAP].line}`,
    chars: { worldUV: FN_WORLD.length, latTap: FN_TAP.length },
  }));
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  const errors = []; p.on('pageerror', e => errors.push(String(e.message).slice(0, 200)));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(2000);

  const r = await p.evaluate(({ fnWorld, fnTap }) => {
    const HR = Math.sqrt(3) / 2, N = 16;
    const out = { compile: null, uniforms: {}, samples: [] };
    const probeFS = `#version 300 es
      precision highp float; precision highp int;
      out vec4 frag;
      uniform sampler2D tx; uniform float uRES,uWpx,uRowScale,uROWS,uHpx,uZScale; uniform int uN;
      ${fnWorld}
      ${fnTap}
      void main(){
        ivec2 q=ivec2(gl_FragCoord.xy);
        float fx=(float(q.x)+0.5)/float(uN), fz=(float(q.y)+0.5)/float(uN);
        float zExt=1.0/(2.0*uZScale);
        vec2 pxz=vec2(fx*2.0-1.0,(fz*2.0-1.0)*zExt);
        frag=vec4(latTap(tx,worldUV(pxz)),0.0,0.0,1.0);
      }`;

    // compile by hand so the log is visible rather than swallowed
    const vsSrc = `#version 300 es
      void main(){vec2 p=vec2((gl_VertexID==1)?3.:-1.,(gl_VertexID==2)?3.:-1.);gl_Position=vec4(p,0.,1.);}`;
    const mk = (t, src) => { const s = gl.createShader(t); gl.shaderSource(s, src); gl.compileShader(s);
      return { s, ok: gl.getShaderParameter(s, gl.COMPILE_STATUS), log: gl.getShaderInfoLog(s) }; };
    const vs = mk(gl.VERTEX_SHADER, vsSrc), fsh = mk(gl.FRAGMENT_SHADER, probeFS);
    out.compile = { vsOk: vs.ok, fsOk: fsh.ok, fsLog: (fsh.log || '').slice(0, 400) };
    if (!fsh.ok) return out;
    const pr = gl.createProgram(); gl.attachShader(pr, vs.s); gl.attachShader(pr, fsh.s); gl.linkProgram(pr);
    out.compile.linkOk = gl.getProgramParameter(pr, gl.LINK_STATUS);
    out.compile.linkLog = (gl.getProgramInfoLog(pr) || '').slice(0, 300);

    terrainDef.lattice = 'square'; RES = 192; buildIndex();
    const n = fieldW(), nh = fieldH(), rz = 1;
    const xHalf = (n - 1) / 2, zHalf = (nh - 1) * rz / 2, zScale = xHalf / (2 * zHalf);
    out.uniforms = { n, nh, xHalf, zHalf, zScale, uWpx: 1 / n, uHpx: 1 / nh };

    const A = 0.0131, B = -0.0087;
    const f = new Float32Array(n * nh);
    for (let y = 0; y < nh; y++) for (let x = 0; x < n; x++) f[y * n + x] = A * x + B * (y * rz);

    const rgba = new Float32Array(n * nh * 4);
    for (let i = 0; i < n * nh; i++) rgba[i * 4] = f[i];
    const tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, n, nh, 0, gl.RGBA, gl.FLOAT, rgba);

    const target = GPU.rt('glslDiagOut', N);
    GPU.bind(target, N);
    gl.useProgram(pr);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
    const U = nm => gl.getUniformLocation(pr, nm);
    out.locs = { tx: !!U('tx'), uRES: !!U('uRES'), uROWS: !!U('uROWS'), uHpx: !!U('uHpx'),
      uZScale: !!U('uZScale'), uWpx: !!U('uWpx'), uRowScale: !!U('uRowScale'), uN: !!U('uN') };
    gl.uniform1i(U('tx'), 0);
    gl.uniform1f(U('uRES'), n); gl.uniform1f(U('uWpx'), 1 / n);
    gl.uniform1f(U('uROWS'), nh); gl.uniform1f(U('uHpx'), 1 / nh);
    gl.uniform1f(U('uZScale'), zScale); gl.uniform1f(U('uRowScale'), rz);
    gl.uniform1i(U('uN'), N);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    const got = new Float32Array(N * N * 4);
    gl.readPixels(0, 0, N, N, gl.RGBA, gl.FLOAT, got);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);

    for (const [qx, qy] of [[4,4],[8,8],[12,6],[6,11]]) {
      const fx = (qx + 0.5) / N, fz = (qy + 0.5) / N;
      const wx = fx * n - 0.5, rowF = fz * nh - 0.5;
      out.samples.push({ qx, qy, gpu: +got[(qy * N + qx) * 4].toFixed(6),
        cpu: +sampleBilinear(f, wx, rowF * rz).toFixed(6), wx: +wx.toFixed(2), row: +rowF.toFixed(2) });
    }
    return out;
  }, { fnWorld: FN_WORLD, fnTap: FN_TAP });

  console.log(JSON.stringify(r, null, 1));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();

  // ---- GATE. Everything above is a report; without this the report IS the result. --------------
  // Lifting the right source only guarantees the probe found something to compile. It does not
  // guarantee the compile SUCCEEDED, and a failed compile leaves `samples: []` and falls off the
  // end of the script at exit 0 — which run-legacy-verify.mjs reports as a pass. That is not
  // hypothetical: adding a single call to a nonexistent GLSL function inside latTap yields
  //   fsOk:false  samples:[]  EXIT=0
  // i.e. a probe that compared nothing and announced success. Four assertions close it, and each
  // one is a distinct way of comparing nothing:
  //   compile   — the shader never built
  //   link      — it built but the program did not link
  //   coverage  — it linked but produced no sample rows
  //   agreement — rows exist but GPU and CPU disagree (the defect the probe is FOR)
  const fail = [];
  const c = r.compile || {};
  if (!c.fsOk) fail.push(`fragment shader did not compile: ${c.fsLog || '(no log)'}`);
  if (c.fsOk && !c.linkOk) fail.push(`program did not link: ${c.linkLog || '(no log)'}`);
  if (!r.samples || r.samples.length !== 4)
    fail.push(`expected 4 probe samples, got ${r.samples ? r.samples.length : 0} — nothing was compared`);
  if (errors.length) fail.push(`page errors: ${JSON.stringify(errors)}`);

  let maxDiff = 0;
  for (const s of r.samples || []) maxDiff = Math.max(maxDiff, Math.abs(s.gpu - s.cpu));
  // Bound armed between two MEASURED endpoints, not chosen from theory:
  //   correct build                                        maxDiff = 0.000e+0   PASS
  //   half-texel offset perturbed 0.5 -> 0.46 in latTap    maxDiff = 1.760e-4   FAIL
  // so 1e-5 sits an order below a 4%-of-a-texel error and above exact agreement. Reproduce the
  // negative control with GLSL_SRC pointed at a copy carrying that edit — the override exists
  // precisely so this can be re-armed without touching the app.
  //
  // NOTE for whoever re-arms it: this probe runs `terrainDef.lattice='square'` with uRowScale=1
  // (see below), so it exercises ONLY latTap's `if(uRowScale==1.0)` fast path. Perturbing the hex
  // branch — anything guarded by uHpx/uRowScale != 1 — changes nothing here and the control will
  // pass while proving nothing. Hex coverage of the same helper is _verify_hex_deferred.js G1.
  const TOL = 1e-5;
  if ((r.samples || []).length && maxDiff > TOL)
    fail.push(`GPU/CPU disagree: maxDiff=${maxDiff.toExponential(3)} > ${TOL}`);

  if (fail.length) {
    console.log(`FAIL  glsl-probe  ${fail.join(' | ')}`);
    process.exit(1);
  }
  console.log(`PASS  glsl-probe  lifted worldUV+latTap from ${LIFT.found[SIG_WORLD].file}, compiled, `
    + `linked, 4/4 samples, maxDiff=${maxDiff.toExponential(3)} (tol ${TOL})`);
})().catch(e => { console.error('FATAL ' + String(e).slice(0, 300)); process.exit(2); });
