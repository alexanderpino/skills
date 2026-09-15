// Shared harness for "evaluate this fence at N test points" checks -- the LIGHTER pass this
// corpus's second attempt at GPU validation deliberately uses. heightfield-raymarching's rig
// (gaia/gpu/heightfield-raymarching/) built one bespoke, deeply-traced harness for a branchy,
// stateful raymarch and it cost most of a session, including two real bugs in the harness
// itself found only by a step-by-step trace. Most fenced formulas are NOT that: they are pure,
// branch-free per-fragment math with no loop, and evaluating one at N independent test points
// needs no state, no mip pyramid, and no forensic tracing -- only a correct read-back.
//
// This module is that: launch Chromium (SwiftShader; see gaia/gpu/README.md for what that
// does and does not mean), compile ONE fragment shader, feed it N rows of up to two vec4
// inputs via a texture, run it once, and read back N vec4 outputs. Callers supply the GLSL
// body; this file supplies everything around it.
import { chromium } from 'playwright';

const CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const VS = `#version 300 es
in vec2 aPos;
void main() { gl_Position = vec4(aPos, 0.0, 1.0); }
`;

export async function launch() {
  const browser = await chromium.launch({
    executablePath: CHROME,
    args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'],
  });
  const page = await browser.newPage();
  page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });
  return { browser, page };
}

// fsBody: GLSL ES 3.00 fragment-shader BODY (no #version/precision/main -- those are supplied).
// It receives per-point inputs as `vec4 A` and `vec4 B` (B optional -- pass rowsB=null to skip)
// and must write `vec4 oResult`.
// rowsA / rowsB: arrays of 4-element [x,y,z,w] arrays, one per test point.
// Returns: array of {x,y,z,w} result objects, one per input row.
// extraTextures: array of {name, size, data (Float32Array, size*size R32F), intUniform} for
// lookups beyond the per-point A/B inputs -- a mip pyramid, a lookup table. `helpers` is raw
// GLSL (functions, extra uniform declarations) inserted before main().
export async function evalPointwise(page, { fsBody, rowsA, rowsB = null, uniforms = {},
                                            extraTextures = [], helpers = '', intUniforms = {} }) {
  const n = rowsA.length;
  if (rowsB && rowsB.length !== n) throw new Error('rowsA/rowsB length mismatch');

  const fs = `#version 300 es
precision highp float;
precision highp int;
uniform sampler2D uA;
${rowsB ? 'uniform sampler2D uB;' : ''}
${extraTextures.map(t => `uniform sampler2D ${t.name};`).join('\n')}
${Object.keys(uniforms).map(k => `uniform float ${k};`).join('\n')}
${Object.keys(intUniforms).map(k => `uniform int ${k};`).join('\n')}
out vec4 oResult;
${helpers}
void main() {
  vec4 A = texelFetch(uA, ivec2(gl_FragCoord.x, 0), 0);
  ${rowsB ? 'vec4 B = texelFetch(uB, ivec2(gl_FragCoord.x, 0), 0);' : ''}
${fsBody}
}
`;

  return page.evaluate(({ vs, fs, n, rowsA, rowsB, uniforms, intUniforms, extraTextures }) => {
    const canvas = document.createElement('canvas');
    canvas.width = n; canvas.height = 1;
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

    function mkInputTex(unit, rows) {
      const buf = new Float32Array(n * 4);
      rows.forEach((r, i) => { for (let k = 0; k < 4; k++) buf[i * 4 + k] = r[k] ?? 0; });
      gl.activeTexture(gl.TEXTURE0 + unit);
      const t = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, n, 1, 0, gl.RGBA, gl.FLOAT, buf);
    }
    mkInputTex(0, rowsA);
    gl.uniform1i(gl.getUniformLocation(prog, 'uA'), 0);
    if (rowsB) { mkInputTex(1, rowsB); gl.uniform1i(gl.getUniformLocation(prog, 'uB'), 1); }
    for (const [k, v] of Object.entries(uniforms)) {
      gl.uniform1f(gl.getUniformLocation(prog, k), v);
    }
    for (const [k, v] of Object.entries(intUniforms)) {
      gl.uniform1i(gl.getUniformLocation(prog, k), v);
    }
    // extra textures start at unit 2 -- 0/1 are uA/uB, 15 is the output (below).
    extraTextures.forEach((t, i) => {
      const unit = 2 + i;
      gl.activeTexture(gl.TEXTURE0 + unit);
      const tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.R32F, t.size, t.size, 0, gl.RED, gl.FLOAT, t.data);
      gl.uniform1i(gl.getUniformLocation(prog, t.name), unit);
    });

    // output texture on an unused unit -- gaia/gpu/heightfield-raymarching found this the
    // hard way: binding it to TEXTURE0 after an input already claimed that unit silently
    // zeroed every read from it. Unit 15 here for the same reason that fix used unit 15.
    gl.activeTexture(gl.TEXTURE0 + 15);
    const outTex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, outTex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, n, 1, 0, gl.RGBA, gl.FLOAT, null);
    const fbo = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, outTex, 0);
    if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) {
      return { error: 'incomplete FBO: ' + gl.checkFramebufferStatus(gl.FRAMEBUFFER) };
    }
    gl.viewport(0, 0, n, 1);
    gl.drawArrays(gl.TRIANGLES, 0, 3);

    const px = new Float32Array(n * 4);
    gl.readPixels(0, 0, n, 1, gl.RGBA, gl.FLOAT, px);
    const results = [];
    for (let i = 0; i < n; i++) {
      results.push({ x: px[i * 4], y: px[i * 4 + 1], z: px[i * 4 + 2], w: px[i * 4 + 3] });
    }
    return { results, glErr: gl.getError() };
  }, { vs: VS, fs, n, rowsA, rowsB, uniforms, intUniforms, extraTextures });
}
