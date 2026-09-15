import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { VS_FULLSCREEN, FS_MARCH } from './shaders.mjs';

const scene = JSON.parse(readFileSync(process.argv[2], 'utf-8'));
const { S0, NG, NLevels, field } = scene;
const idx = parseInt(process.argv[3] || '0', 10);
const ray = scene.rays.filter(r => r.kind === 'primary')[idx];
console.log('testing ray:', JSON.stringify(ray));

function dilate3(a) {
  const n = a.length, out = [];
  for (let j = 0; j < n; j++) { const row = new Float32Array(n);
    for (let i = 0; i < n; i++) { let m = -Infinity;
      for (const dj of [-1,0,1]) for (const di of [-1,0,1]) {
        const v = a[((j+dj)%n+n)%n][((i+di)%n+n)%n]; if (v > m) m = v; }
      row[i] = m; } out.push(row); } return out; }
function reduce2(a) { const n = a.length/2, out = [];
  for (let j=0;j<n;j++){ const row=new Float32Array(n);
    for (let i=0;i<n;i++) row[i]=Math.max(a[2*j][2*i],a[2*j][2*i+1],a[2*j+1][2*i],a[2*j+1][2*i+1]);
    out.push(row);} return out; }
const pyramid = [dilate3(field)];
for (let l=1;l<NLevels;l++) pyramid.push(reduce2(pyramid[l-1]));
function flatten(level){ const n=level.length, out=new Float32Array(n*n);
  for(let j=0;j<n;j++)for(let i=0;i<n;i++)out[j*n+i]=level[j][i]; return out; }

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist'] });
const page = await browser.newPage();
page.on('console', m => console.log('[page]', m.text()));

const result = await page.evaluate(({vs,fs,S0,NG,NLevels,pyramidFlat,baseFlat,rayBuf,bisections,stepCap,debugStep})=>{
  const canvas=document.createElement('canvas'); canvas.width=1; canvas.height=1;
  const gl=canvas.getContext('webgl2'); gl.getExtension('EXT_color_buffer_float');
  function compile(type,src){ const s=gl.createShader(type); gl.shaderSource(s,src); gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; }
  const prog=gl.createProgram();
  gl.attachShader(prog,compile(gl.VERTEX_SHADER,vs)); gl.attachShader(prog,compile(gl.FRAGMENT_SHADER,fs));
  gl.linkProgram(prog); gl.useProgram(prog);
  const quad=gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,quad);
  gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
  const loc=gl.getAttribLocation(prog,'aPos'); gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
  function mkTex(unit,n,data){ gl.activeTexture(gl.TEXTURE0+unit); const t=gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D,t);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.R32F,n,n,0,gl.RED,gl.FLOAT,data); return t; }
  for(let l=0;l<NLevels;l++){ mkTex(l, NG>>l, pyramidFlat[l]); gl.uniform1i(gl.getUniformLocation(prog,`uPyramid[${l}]`),l); }
  mkTex(8,NG,baseFlat); gl.uniform1i(gl.getUniformLocation(prog,'uBase'),8);
  gl.activeTexture(gl.TEXTURE0+9); const rayTex=gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D,rayTex);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
  gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA32F,2,1,0,gl.RGBA,gl.FLOAT,rayBuf);
  gl.uniform1i(gl.getUniformLocation(prog,'uRays'),9);
  gl.uniform1i(gl.getUniformLocation(prog,'uNLevels'),NLevels);
  gl.uniform1f(gl.getUniformLocation(prog,'uS0'),S0);
  gl.uniform1i(gl.getUniformLocation(prog,'uNG'),NG);
  gl.uniform1i(gl.getUniformLocation(prog,'uBisections'),bisections);
  gl.uniform1i(gl.getUniformLocation(prog,'uStepCap'),stepCap);
  gl.uniform1i(gl.getUniformLocation(prog,'uDebugStep'), debugStep);
  const outTex=gl.createTexture(); gl.activeTexture(gl.TEXTURE0+15); gl.bindTexture(gl.TEXTURE_2D,outTex);
  gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA32F,1,1,0,gl.RGBA,gl.FLOAT,null);
  const fbo=gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER,fbo);
  gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,outTex,0);
  gl.viewport(0,0,1,1); gl.drawArrays(gl.TRIANGLES,0,3);
  const px=new Float32Array(4); gl.readPixels(0,0,1,1,gl.RGBA,gl.FLOAT,px);
  return { t: px[0], steps: px[1], exitLevel: px[2], glErr: gl.getError() };
}, {
  vs: VS_FULLSCREEN, fs: FS_MARCH, S0, NG, NLevels,
  pyramidFlat: pyramid.map(flatten), baseFlat: flatten(field),
  rayBuf: new Float32Array([ray.o[0],ray.o[1],ray.o[2],ray.t0, ray.d[0],ray.d[1],ray.d[2],ray.t1]),
  bisections: 6, stepCap: 20000, debugStep: parseInt(process.argv[4] ?? '-1', 10),
});
console.log('GPU result:', result);
console.log('python ref:', ray.ref);
await browser.close();
