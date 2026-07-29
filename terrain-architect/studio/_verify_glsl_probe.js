// Why does the deferred probe disagree with the CPU sampler on BOTH lattices after the compositor
// X/Y split? Prints the actual uniform values, the shader compile log, and a handful of probe
// points against their CPU reference, so the failure is located instead of guessed at.
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');
const EXE = process.env.STUDIO_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'file://' + path.resolve(__dirname, 'index.html');
const SRC = fs.readFileSync(path.resolve(__dirname, 'index.html'), 'utf8');
function grabFn(sig) {
  const i = SRC.indexOf(sig); if (i < 0) return null;
  let d = 0, j = SRC.indexOf('{', i); if (j < 0) return null;
  for (let k = j; k < SRC.length; k++) {
    if (SRC[k] === '{') d++; else if (SRC[k] === '}') { d--; if (!d) return SRC.slice(i, k + 1); }
  } return null;
}
const FN_WORLD = grabFn('vec2 worldUV('), FN_TAP = grabFn('float latTap(');

(async () => {
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
})().catch(e => { console.error('FATAL ' + String(e).slice(0, 300)); process.exit(2); });
