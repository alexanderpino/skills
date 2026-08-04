// The GPGPU fast path: WebGL2 render-to-texture kernels for noise, thermal, warp, rock fracture,
// and the pipe + particle hydraulic solvers, plus their capability gates.
//
// Extracted first of the four core concerns because it is the cheapest cut: 21 inbound references
// of which 19 are its own wrappers, exactly two external callers (both toolbar handlers), no DOM,
// and no dependence on the graph or the node registry - the arrow points the other way
// (TYPES.perlin.eval -> gpuFbm -> GPU).
//
// TWO HAZARDS CARRIED OVER UNCHANGED, documented rather than silently inherited:
//   * GPU.rt() never frees. Render targets are cached by key+"_"+n, so every distinct RES leaves
//     its allocations resident and applyWorkingResolution() does not invalidate them.
//   * GPU.prog() caches by key while IGNORING the source, so two call sites sharing a key get a
//     stale program. Both predate this extraction and neither is worsened by it.
//
// gl is injected via setGL (see gl-util.js for why, and for the do-not-cache-methods rule).
// GPU.init() is still reached through the setTimeout(...,0) in legacy.js so that it runs AFTER
// boot() has assigned gl; called earlier it sees undefined, returns false, and disables the GPU
// path with no error at all - a silent capability downgrade the digest cannot catch, because the
// CPU path produces valid output.
import { makeProg, u } from './gl-util.js';
import { fieldW, fieldH, normalize, terrainDef, XF, USE_GPU, clamp } from '../legacy.js';

let gl = null;
export const setGL = (ctx) => { gl = ctx; };

export const GPU={
  ok:null,floatBlend:false,vs:null,progs:{},rts:{},fbo:null,
  init(){
    if(this.ok!==null)return this.ok;
    this.ok=false;
    if(!gl||typeof WebGL2RenderingContext==="undefined"||!(gl instanceof WebGL2RenderingContext))return false;
    if(!gl.getExtension("EXT_color_buffer_float"))return false;   // required to render into float textures
    this.floatBlend=!!gl.getExtension("EXT_float_blend");          // droplet brush deltas use additive float blending
    this.vs=`#version 300 es
      void main(){vec2 p=vec2((gl_VertexID==1)?3.:-1.,(gl_VertexID==2)?3.:-1.);gl_Position=vec4(p,0.,1.);}`;
    this.fbo=gl.createFramebuffer();
    this.ok=true;return true;
  },
  prog(key,fs){if(!this.progs[key])this.progs[key]=makeProg(this.vs,fs);return this.progs[key];},
  customProg(key,vs,fs){if(!this.progs[key])this.progs[key]=makeProg(vs,fs);return this.progs[key];},
  rt(key,n){const k=key+"_"+n;let t=this.rts[k];
    if(!t){t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA32F,n,n,0,gl.RGBA,gl.FLOAT,null);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
      this.rts[k]=t;}
    return t;},
  bind(target,n){gl.bindFramebuffer(gl.FRAMEBUFFER,this.fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,target,0);
    // Particle updates use three MRT attachments of a different size. Leaving attachment 1/2
    // attached makes later terrain-sized single-target framebuffers incomplete on WebGL2, even
    // when drawBuffers selects only attachment 0; the draw then silently writes nothing.
    gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT1,gl.TEXTURE_2D,null,0);
    gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT2,gl.TEXTURE_2D,null,0);
    gl.drawBuffers([gl.COLOR_ATTACHMENT0]);gl.viewport(0,0,n,n);},
  bindMRT(targets,n){gl.bindFramebuffer(gl.FRAMEBUFFER,this.fbo);
    targets.forEach((target,i)=>gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0+i,gl.TEXTURE_2D,target,0));
    gl.drawBuffers(targets.map((_,i)=>gl.COLOR_ATTACHMENT0+i));gl.viewport(0,0,n,n);},
  run(prog,n,target,setup){
    this.bind(target,n);gl.disable(gl.DEPTH_TEST);gl.disable(gl.BLEND);
    gl.useProgram(prog);if(setup)setup(prog);
    gl.drawArrays(gl.TRIANGLES,0,3);gl.bindFramebuffer(gl.FRAMEBUFFER,null);},
  runMRT(prog,n,targets,setup){
    this.bindMRT(targets,n);gl.disable(gl.DEPTH_TEST);gl.disable(gl.BLEND);
    gl.useProgram(prog);if(setup)setup(prog);
    gl.drawArrays(gl.TRIANGLES,0,3);gl.bindFramebuffer(gl.FRAMEBUFFER,null);},
  clear(target,n){this.bind(target,n);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.bindFramebuffer(gl.FRAMEBUFFER,null);},
  upload(key,n,data){const t=this.rt(key,n),rgba=new Float32Array(n*n*4);   // shape-ok: staging buffer for the square texture above, not a field
    for(let i=0;i<n*n;i++)rgba[i*4]=data[i];   // shape-ok: fills that square texture
    gl.bindTexture(gl.TEXTURE_2D,t);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA32F,n,n,0,gl.RGBA,gl.FLOAT,rgba);return t;},
  uploadState(key,n,bed){const t=this.rt(key,n),rgba=new Float32Array(n*n*4);   // shape-ok: staging buffer for the square texture above, not a field
    for(let i=0;i<n*n;i++){rgba[i*4]=bed[i];rgba[i*4+3]=1;}   // shape-ok: fills that square texture
    gl.bindTexture(gl.TEXTURE_2D,t);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA32F,n,n,0,gl.RGBA,gl.FLOAT,rgba);return t;},
  uploadRGBA(key,n,rgba){const t=this.rt(key,n);
    gl.bindTexture(gl.TEXTURE_2D,t);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA32F,n,n,0,gl.RGBA,gl.FLOAT,rgba);return t;},
  readRGBA(target,n){this.bind(target,n);
    const rgba=new Float32Array(n*n*4);gl.readPixels(0,0,n,n,gl.RGBA,gl.FLOAT,rgba);   // shape-ok: readback must match the square texture it reads
    gl.bindFramebuffer(gl.FRAMEBUFFER,null);return rgba;},
  // shape-ok: reads back a GPU TEXTURE and the textures allocated above are square, so the readback must keep matching what was uploaded - it stays n*n, NOT n*nh.
  // Making hex textures n x latticeRows(n) belongs with the GPU hex kernels, not here - the readback
  // must keep matching whatever was actually uploaded.
  read(target,n){const rgba=this.readRGBA(target,n);
    const o=new Float32Array(n*n);for(let i=0;i<n*n;i++)o[i]=rgba[i*4];return o;},   // shape-ok: square texture readback
};
// GLSL twins of hash2/gnoise/snoise above — identical uint32 hash, so the same seed gives the same field.
const GLSL_NOISE=`
  float hashf(int x,int y,int s){
    uint h=uint(x)*374761393u+uint(y)*668265263u+uint(s)*1442695041u;
    h=(h^(h>>13u))*1274126177u;
    return float(h^(h>>16u))/4294967295.0;}
  float sm(float t){return t*t*t*(t*(t*6.0-15.0)+10.0);}
  float gnoise(float x,float y,int s){
    float fx=floor(x),fy=floor(y);int x0=int(fx),y0=int(fy);
    float xf=x-fx,yf=y-fy;const float TAU=6.2831853;
    float a00=hashf(x0,y0,s)*TAU,a10=hashf(x0+1,y0,s)*TAU,a01=hashf(x0,y0+1,s)*TAU,a11=hashf(x0+1,y0+1,s)*TAU;
    float n00=cos(a00)*xf+sin(a00)*yf;
    float n10=cos(a10)*(xf-1.0)+sin(a10)*yf;
    float n01=cos(a01)*xf+sin(a01)*(yf-1.0);
    float n11=cos(a11)*(xf-1.0)+sin(a11)*(yf-1.0);
    float u=sm(xf),v=sm(yf);
    return 0.5+0.5*mix(mix(n00,n10,u),mix(n01,n11,u),v)*1.35;}
  float simplexCorner(int ix,int iy,float dx,float dy,int s){
    float t=0.5-dx*dx-dy*dy;if(t<=0.0)return 0.0;
    float a=hashf(ix,iy,s)*6.28318530718;t*=t;
    return t*t*(cos(a)*dx+sin(a)*dy);}
  float snoise(float x,float y,int s){
    const float F2=0.3660254037844386,G2=0.21132486540518713;
    float skew=(x+y)*F2,fi=floor(x+skew),fj=floor(y+skew),unskew=(fi+fj)*G2;
    int i=int(fi),j=int(fj);float x0=x-(fi-unskew),y0=y-(fj-unskew);
    int i1=x0>y0?1:0,j1=x0>y0?0:1;
    float x1=x0-float(i1)+G2,y1=y0-float(j1)+G2;
    float x2=x0-1.0+2.0*G2,y2=y0-1.0+2.0*G2;
    float n=simplexCorner(i,j,x0,y0,s)+simplexCorner(i+i1,j+j1,x1,y1,s)+simplexCorner(i+1,j+1,x2,y2,s);
    return clamp(0.5+35.0*n,0.0,1.0);}`;
const GPU_FBM_FS=`#version 300 es
  precision highp float;precision highp int;out vec4 frag;
  uniform float uN,uFreq,uLac,uGain,uRidge,uSimplex;uniform int uOct,uSeed;
  uniform vec3 uXFa,uXFb;                    // dest-uv -> source-uv affine rows (identity by default)
  `+GLSL_NOISE+`
  void main(){
    float x=floor(gl_FragCoord.x),y=floor(gl_FragCoord.y);
    vec3 uv=vec3(x/uN,y/uN,1.0);
    float gu=dot(uXFa,uv),gv=dot(uXFb,uv);
    float amps=0.0,a=1.0;
    for(int k=0;k<32;k++){if(k>=uOct)break;amps+=a;a*=uGain;}
    float sum=0.0,amp=1.0,f=uFreq;
    for(int k=0;k<32;k++){if(k>=uOct)break;
      float v=uSimplex>0.5?snoise(gu*f,gv*f,uSeed+k*7):gnoise(gu*f,gv*f,uSeed+k*7);
      if(uRidge>0.5){v=1.0-abs(v*2.0-1.0);v=v*v;}
      sum+=v*amp;amp*=uGain;f*=uLac;}
    frag=vec4(sum/amps,0.0,0.0,1.0);}`;
// Thermal erosion, gather form: a cell LOSES rate*maxDrop and GAINS each neighbour's share.
// Same arithmetic as thermalErode() above, restructured so every cell can be solved independently.
// Split into TWO passes: pass 1 memoises each cell's (move, sum); pass 2 only reads it back. The
// single-pass version recomputed every neighbour's moveSum (72 fetches/cell); this is ~27.
const GPU_THERMAL_NB=`
  const ivec2 NB[8]=ivec2[8](ivec2(-1,0),ivec2(1,0),ivec2(0,-1),ivec2(0,1),ivec2(-1,-1),ivec2(1,1),ivec2(-1,1),ivec2(1,-1));
  const float ND[8]=float[8](1.,1.,1.,1.,1.41421356,1.41421356,1.41421356,1.41421356);  // diagonal distance correction
  bool inb(ivec2 p,int n){return p.x>=0&&p.y>=0&&p.x<n&&p.y<n;}`;   // shape-ok: GLSL bound over those same square textures
const GPU_THERMAL_MS_FS=`#version 300 es
  precision highp float;precision highp int;out vec4 frag;
  uniform sampler2D uH;uniform float uTalus,uRate;uniform int uN;`+GPU_THERMAL_NB+`
  float H(ivec2 p){return texelFetch(uH,p,0).r;}
  void main(){                                  // -> (stable move budget, sumOfExcess)
    ivec2 p=ivec2(gl_FragCoord.xy);float c=H(p),maxd=0.0,sum=0.0;
    for(int k=0;k<8;k++){ivec2 q=p+NB[k];if(!inb(q,uN))continue;
      float e=c-H(q)-uTalus*ND[k];if(e>0.0){sum+=e;maxd=max(maxd,e);}}
    frag=vec4(0.5*uRate*maxd,sum,0.0,1.0);}`;
const GPU_THERMAL_APPLY_FS=`#version 300 es
  precision highp float;precision highp int;out vec4 frag;
  uniform sampler2D uH,uMS;uniform float uTalus;uniform int uN;`+GPU_THERMAL_NB+`
  float H(ivec2 p){return texelFetch(uH,p,0).r;}
  vec2 MS(ivec2 p){return texelFetch(uMS,p,0).rg;}
  void main(){
    ivec2 p=ivec2(gl_FragCoord.xy);float h=H(p);
    vec2 me=MS(p);float lose=0.0,gain=0.0;
    for(int k=0;k<8;k++){ivec2 q=p+NB[k];if(!inb(q,uN))continue;
      float own=h-H(q)-uTalus*ND[k];
      if(own>0.0&&me.y>0.0)lose+=min(me.x*own/me.y,0.5*own);
      vec2 mn=MS(q);if(mn.y<=0.0)continue;
      float e=H(q)-h-uTalus*ND[k];if(e>0.0)gain+=min(mn.x*e/mn.y,0.5*e);}
    frag=vec4(h+gain-lose,0.0,0.0,1.0);}`;
export function gpuFbm({seed=1,freq=3,octaves=5,lac=2.0,gain=0.5,ridge=false,simplex=false}){
  const n=fieldW(),nh=fieldH(),prog=GPU.prog("fbm",GPU_FBM_FS),out=GPU.rt("gen",n);
  GPU.run(prog,n,out,p=>{
    gl.uniform1f(u(p,"uN"),n);gl.uniform1f(u(p,"uFreq"),freq);gl.uniform1f(u(p,"uLac"),lac);
    gl.uniform1f(u(p,"uGain"),gain);gl.uniform1f(u(p,"uRidge"),ridge?1:0);gl.uniform1f(u(p,"uSimplex"),simplex?1:0);
    gl.uniform1i(u(p,"uOct"),octaves|0);gl.uniform1i(u(p,"uSeed"),seed|0);
    const M=XF||[1,0,0,0,1,0];                 // same placement matrix the CPU path uses
    gl.uniform3f(u(p,"uXFa"),M[0],M[1],M[2]);gl.uniform3f(u(p,"uXFb"),M[3],M[4],M[5]);});
  const f=GPU.read(out,n);
  return ridge?normalize(f):f;                 // ridged normalises on the CPU (a reduction), as before
}
export function gpuThermal(inp,{talus=0.012,iters=30,rate=0.5}){
  const n=fieldW(),nh=fieldH(),pMS=GPU.prog("thermalMS",GPU_THERMAL_MS_FS),pAp=GPU.prog("thermalApply",GPU_THERMAL_APPLY_FS);
  let src=GPU.upload("thA",n,inp),dst=GPU.rt("thB",n);const ms=GPU.rt("thMS",n);
  for(let i=0;i<iters;i++){
    GPU.run(pMS,n,ms,p=>{                      // pass 1: per-cell (move, sum)
      gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,src);gl.uniform1i(u(p,"uH"),0);
      gl.uniform1f(u(p,"uTalus"),talus);gl.uniform1f(u(p,"uRate"),rate);gl.uniform1i(u(p,"uN"),n);});
    GPU.run(pAp,n,dst,p=>{                     // pass 2: redistribute
      gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,src);gl.uniform1i(u(p,"uH"),0);
      gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,ms);gl.uniform1i(u(p,"uMS"),1);
      gl.uniform1f(u(p,"uTalus"),talus);gl.uniform1i(u(p,"uN"),n);});
    const t=src;src=dst;dst=t;                 // ping-pong
  }
  return GPU.read(src,n);
}
const GPU_WARP_FS=`#version 300 es
  precision highp float;precision highp int;out vec4 frag;
  uniform sampler2D uH;uniform float uN,uStrength,uFreq;uniform int uSeed;
  `+GLSL_NOISE+`
  float H(ivec2 p){int n=int(uN);return texelFetch(uH,clamp(p,ivec2(0),ivec2(n-1)),0).r;}
  float bilinear(vec2 p){
    ivec2 a=ivec2(floor(p));vec2 f=p-vec2(a);
    return mix(mix(H(a),H(a+ivec2(1,0)),f.x),mix(H(a+ivec2(0,1)),H(a+ivec2(1,1)),f.x),f.y);}
  void main(){
    vec2 p=floor(gl_FragCoord.xy);float s=uStrength*uN;
    float ox=(gnoise(p.x/uN*uFreq,p.y/uN*uFreq,uSeed)-0.5)*2.0*s;
    float oy=(gnoise(p.x/uN*uFreq,p.y/uN*uFreq,uSeed+53)-0.5)*2.0*s;
    frag=vec4(bilinear(p+vec2(ox,oy)),0.0,0.0,1.0);}`;
export function gpuWarp(inp,{strength=0.12,freq=3,seed=7}){
  const n=fieldW(),nh=fieldH(),src=GPU.upload("warpIn",n,inp),dst=GPU.rt("warpOut",n),p=GPU.prog("warp",GPU_WARP_FS);
  GPU.run(p,n,dst,q=>{
    gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,src);gl.uniform1i(u(q,"uH"),0);
    gl.uniform1f(u(q,"uN"),n);gl.uniform1f(u(q,"uStrength"),strength);gl.uniform1f(u(q,"uFreq"),freq);
    gl.uniform1i(u(q,"uSeed"),seed|0);});
  return GPU.read(dst,n);
}

// Multi-scale rock fractures are a T0 gather kernel: the input height is read once and a warped
// Worley F2-F1 distance field is evaluated directly in world metres. No neighbour is sampled, so
// the authored domain edge is not a simulation boundary and cannot grow a clamped frame.
const GPU_ROCK_FRACTURE_FS=`#version 300 es
  precision highp float;precision highp int;out vec4 frag;
  uniform sampler2D uH;
  uniform int uN,uSeed,uOctaves;
  uniform float uWorldScale,uScaleM,uLacunarity,uJitter,uWarp,uWarpScaleM;
  uniform float uWidthM,uDepth,uDepthFalloff,uBreakdownM,uBreakdown,uRoughness,uWeather;
  `+GLSL_NOISE+`
  float smooth01(float t){t=clamp(t,0.0,1.0);return t*t*(3.0-2.0*t);}
  float lineCoverage(float edge,float widthM,float cellM,float spacing){
    float threshold=widthM/spacing,aa=max(1e-5,cellM/spacing);
    return 1.0-smooth01((edge-(threshold-aa))/(2.0*aa));}
  vec2 featurePoint(ivec2 c,int seed){
    vec2 random=vec2(hashf(c.x,c.y,seed),hashf(c.x,c.y,seed+91));
    return vec2(c)+mix(vec2(0.5),random,uJitter);}
  vec2 fractureMasks(vec2 world,float cellM){
    float core=0.0,weathered=0.0,spacing=uScaleM,amp=1.0;
    for(int octave=0;octave<5;octave++){
      if(octave>=uOctaves)break;
      int octaveSeed=uSeed+octave*1013;
      vec2 warpUV=world/uWarpScaleM;
      vec2 warp=vec2(gnoise(warpUV.x,warpUV.y,octaveSeed+37),
                     gnoise(warpUV.x,warpUV.y,octaveSeed+109));
      vec2 p=(world+(warp-0.5)*2.0*uWarp*spacing)/spacing;
      ivec2 c=ivec2(floor(p));float f1=1e9,f2=1e9;
      for(int oy=-1;oy<=1;oy++)for(int ox=-1;ox<=1;ox++){
        ivec2 q=c+ivec2(ox,oy);float d=length(p-featurePoint(q,octaveSeed));
        if(d<f1){f2=f1;f1=d;}else if(d<f2)f2=d;}
      float edge=max(0.0,f2-f1);
      float crackWidth=uWidthM*amp;
      float weatherWidth=crackWidth+2.0*uBreakdownM*amp;
      float crack=lineCoverage(edge,crackWidth,cellM,spacing);
      float broken=lineCoverage(edge,weatherWidth,cellM,spacing);
      core=1.0-(1.0-core)*(1.0-crack*amp);
      weathered=1.0-(1.0-weathered)*(1.0-broken*amp);
      spacing/=uLacunarity;amp*=uDepthFalloff;
    }
    return vec2(core,max(0.0,weathered-core));}
  void main(){
    ivec2 pixel=ivec2(gl_FragCoord.xy);
    float cellM=uWorldScale/float(uN);
    vec2 world=(vec2(pixel)+0.5)*cellM;
    vec2 masks=fractureMasks(world,cellM);
    float shoulder=uWeather>0.5?masks.y*uBreakdown:0.0;
    float rough=gnoise(world.x/max(1.0,uScaleM*0.37),
      world.y/max(1.0,uScaleM*0.37),uSeed+2081);
    float variation=1.0+uRoughness*(rough*1.4-0.7);
    float height=texelFetch(uH,pixel,0).r;
    frag=vec4(height-uDepth*(masks.x+shoulder)*variation,0.0,0.0,1.0);
  }`;
export function gpuRockFracture(inp,o={}){
  const n=fieldW(),src=GPU.upload("fractureIn",n,inp),dst=GPU.rt("fractureOut",n);
  const prog=GPU.prog("rockFracture",GPU_ROCK_FRACTURE_FS);
  GPU.run(prog,n,dst,d=>{
    gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,src);gl.uniform1i(u(d,"uH"),0);
    gl.uniform1i(u(d,"uN"),n);gl.uniform1i(u(d,"uSeed"),o.seed|0);
    gl.uniform1i(u(d,"uOctaves"),o.octaves|0);
    gl.uniform1f(u(d,"uWorldScale"),terrainDef.scale);
    gl.uniform1f(u(d,"uScaleM"),o.scaleM);gl.uniform1f(u(d,"uLacunarity"),o.lacunarity);
    gl.uniform1f(u(d,"uJitter"),o.jitter);gl.uniform1f(u(d,"uWarp"),o.warp);
    gl.uniform1f(u(d,"uWarpScaleM"),o.warpScaleM);gl.uniform1f(u(d,"uWidthM"),o.widthM);
    gl.uniform1f(u(d,"uDepth"),o.depthM/terrainDef.height);
    gl.uniform1f(u(d,"uDepthFalloff"),o.depthFalloff);
    gl.uniform1f(u(d,"uBreakdownM"),o.breakdownM);gl.uniform1f(u(d,"uBreakdown"),o.breakdown);
    gl.uniform1f(u(d,"uRoughness"),o.roughness);gl.uniform1f(u(d,"uWeather"),o.weatherEnabled?1:0);
  });
  return GPU.read(dst,n);
}

// Mei-style virtual-pipe hydraulic erosion in gather form. Unlike the CPU droplet solver, every
// pixel only reads its four neighbours, so the whole simulation remains in float textures until one
// final readback. RGBA state = bed, water, sediment, 1; RGBA flux = left, right, top, bottom.
const GPU_PIPE_FLUX_FS=`#version 300 es
  precision highp float;precision highp int;out vec4 frag;
  uniform sampler2D uS,uPrevF;uniform int uN;uniform float uRain,uMomentum,uFlow;
  bool inside(ivec2 p){return p.x>=0&&p.y>=0&&p.x<uN&&p.y<uN;}
  vec3 S(ivec2 p){return texelFetch(uS,clamp(p,ivec2(0),ivec2(uN-1)),0).rgb;}
  float head(ivec2 p,float wallHead){return inside(p)?S(p).r+S(p).g:wallHead;}
  void main(){
    ivec2 p=ivec2(gl_FragCoord.xy);vec3 s=S(p);float water=s.g+uRain,h=s.r+water;
    vec4 prev=texelFetch(uPrevF,p,0);
    // Explicit no-flux wall: an outside neighbour has the current cell's hydraulic head. This
    // is the finite-heightfield boundary contract; it neither invents an exterior terrain step
    // nor silently exports water through an unmodelled apron.
    vec4 dh=vec4(h-head(p+ivec2(-1,0),h),h-head(p+ivec2(1,0),h),
                 h-head(p+ivec2(0,-1),h),h-head(p+ivec2(0,1),h));
    vec4 f=max(vec4(0.0),prev*uMomentum+max(dh,vec4(0.0))*uFlow);
    float total=f.x+f.y+f.z+f.w;
    if(total>water&&total>0.0)f*=water/total;
    frag=f;}`;
const GPU_PIPE_STATE_FS=`#version 300 es
  precision highp float;precision highp int;out vec4 frag;
  uniform sampler2D uS,uF;uniform int uN;
  uniform float uRain,uEvap,uCapacity,uErode,uDeposit,uKS,uErCap;
  bool inside(ivec2 p){return p.x>=0&&p.y>=0&&p.x<uN&&p.y<uN;}
  vec3 S(ivec2 p){return texelFetch(uS,clamp(p,ivec2(0),ivec2(uN-1)),0).rgb;}
  vec4 F(ivec2 p){return inside(p)?texelFetch(uF,p,0):vec4(0.0);}
  void main(){
    ivec2 p=ivec2(gl_FragCoord.xy);vec3 s=S(p);vec4 own=F(p);
    float inL=F(p+ivec2(-1,0)).y,inR=F(p+ivec2(1,0)).x;
    float inT=F(p+ivec2(0,-1)).w,inB=F(p+ivec2(0,1)).z;
    float inflow=inL+inR+inT+inB,outflow=own.x+own.y+own.z+own.w;
    float water0=s.g+uRain,water=max(0.0,water0+inflow-outflow)*uEvap;
    float c=s.b/max(water0,0.0001);
    float sedIn=S(p+ivec2(-1,0)).b/max(S(p+ivec2(-1,0)).g+uRain,0.0001)*inL
               +S(p+ivec2(1,0)).b/max(S(p+ivec2(1,0)).g+uRain,0.0001)*inR
               +S(p+ivec2(0,-1)).b/max(S(p+ivec2(0,-1)).g+uRain,0.0001)*inT
               +S(p+ivec2(0,1)).b/max(S(p+ivec2(0,1)).g+uRain,0.0001)*inB;
    float sediment=max(0.0,s.b+sedIn-c*outflow);
    float b=s.r;
    float lowest=min(min(S(p+ivec2(-1,0)).r,S(p+ivec2(1,0)).r),
                     min(S(p+ivec2(0,-1)).r,S(p+ivec2(0,1)).r));
    // Capacity needs a SIGNED downhill outlet. abs(b-neighbour) made a local minimum look
    // maximally steep, so the minimum eroded itself deeper on every iteration.
    float slope=uKS*max(0.0,b-lowest);
    vec2 transport=0.5*vec2(own.y-own.x+inL-inR,own.w-own.z+inT-inB);
    float depth=max(0.001,0.5*(water0+water));
    float speed=min(8.0,length(transport)/depth);
    // A soft depth ramp prevents a one-step rain film from carrying river-scale sediment.
    float wet=smoothstep(0.0002,0.003,0.5*(water0+water));
    float cap=uCapacity*slope*speed*wet;
    float er=cap>sediment?min(uErode*(cap-sediment),uErCap):0.0;
    float dep=cap<=sediment?min(uDeposit*(sediment-cap),sediment):0.0;
    frag=vec4(b+dep-er,water,sediment+er-dep,1.0);}`;
// One mass ledger per KERNEL run (raw engine, last-run-wins), top-level so verification can read
// it from page.evaluate (_verify_erosion_mass.js). The budget it must close: sumIn - sumOut =
// exported (+ lost, only when a caller opts out of settling). It is NOT a node ledger: erosion2
// runs the kernel twice on an atFeatureScale-coarsened grid and post-shapes the result, and
// maskApply rescales any kernel's output after the fact - read it only immediately after a
// direct kernel call. Erosion and deposition are one budget, not two nodes.
export let hydroMassDiag=null;
export const setHydroMassDiag=(v)=>{hydroMassDiag=v;};
function continuationApron(inp,n,apron){
  const simN=n+apron*2,out=new Float32Array(simN*simN);
  for(let y=0;y<simN;y++)for(let x=0;x<simN;x++)
    out[y*simN+x]=inp[clamp(y-apron,0,n-1)*n+clamp(x-apron,0,n-1)]; // shape-ok: GPU hydraulic input is square
  return{field:out,n:simN};
}
function runHydraulicPipeState(inp,{iters=48,capacity=6,erode=0.35,deposit=0.28,inertia=0.05,gridK=1},key="pipe"){
  const n=fieldW(),nh=fieldH();
  // Res Lock (gridK = node-level RES/REF_RES; 1 = legacy behaviour, bit-exact). Water crosses one
  // cell per iteration, so the same world transport takes k x the iterations; everything the
  // solver does PER ITERATION is a per-cell rate and rescales accordingly: rain/erosion-cap by
  // 1/k (same totals over k x iterations), fractional relaxation rates by 1-(1-r)^(1/k),
  // survival factors (evap, momentum) by ^(1/k), and the head-difference terms (slope in the
  // capacity law, flux gain) back UP to reference-cell magnitude by k, because a per-cell head
  // drop halves when cells halve. All identities at k=1. Regime note: steady-state flux grows
  // ~k under these scalings, so at large k the water-limited clamp in the flux shader engages
  // more often and Inertia's influence flattens - bounded (the clamp is a hard limiter, not an
  // instability; cross-model review measured depth ratio 1.025 at k=3 Final), but a different
  // regime than k=1.
  const gk=gridK>0?gridK:1,itersEff=Math.max(1,Math.round(iters*gk));
  // Simulate a border-replicated continuation and crop it, instead of crossfading the output. The bounded
  // interactive apron moves the closed outer wall away from every authored sample; a tiled/export
  // pipeline can request a wider source apron according to its own transport-distance contract.
  const apron=Math.min(48,Math.max(8,Math.ceil(8*gk*Math.sqrt(Math.max(1,iters/48)))));
  const padded=continuationApron(inp,n,apron),simN=padded.n;
  const pF=GPU.prog("pipeFlux",GPU_PIPE_FLUX_FS),pS=GPU.prog("pipeState",GPU_PIPE_STATE_FS);
  let state=GPU.uploadState(key+"StateA",simN,padded.field),next=GPU.rt(key+"StateB",simN);
  let flux=GPU.rt(key+"FluxA",simN),nextFlux=GPU.rt(key+"FluxB",simN);GPU.clear(flux,simN);
  const rain=0.0012/gk,evap=gk===1?0.985:Math.pow(0.985,1/gk);
  const momentum0=clamp(0.35+inertia,0.2,0.82),momentum=gk===1?momentum0:Math.pow(momentum0,1/gk);
  const flow=0.42*gk;
  const er0=erode*0.16,erRate=gk===1?er0:1-Math.pow(1-er0,1/gk);
  const dp0=deposit*0.22,dpRate=gk===1?dp0:1-Math.pow(1-dp0,1/gk);
  for(let i=0;i<itersEff;i++){
    GPU.run(pF,simN,nextFlux,p=>{
      gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,state);gl.uniform1i(u(p,"uS"),0);
      gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,flux);gl.uniform1i(u(p,"uPrevF"),1);
      gl.uniform1i(u(p,"uN"),simN);gl.uniform1f(u(p,"uRain"),rain);gl.uniform1f(u(p,"uMomentum"),momentum);
      gl.uniform1f(u(p,"uFlow"),flow);});
    GPU.run(pS,simN,next,p=>{
      gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,state);gl.uniform1i(u(p,"uS"),0);
      gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,nextFlux);gl.uniform1i(u(p,"uF"),1);
      gl.uniform1i(u(p,"uN"),simN);gl.uniform1f(u(p,"uRain"),rain);gl.uniform1f(u(p,"uEvap"),evap);
      // Calibrated after replacing abs-slope/total-flux speed: keeps the default pipe dose in the
      // documented cross-engine band without restoring either self-deepening feedback.
      gl.uniform1f(u(p,"uCapacity"),capacity*0.23);gl.uniform1f(u(p,"uErode"),erRate);
      gl.uniform1f(u(p,"uDeposit"),dpRate);
      gl.uniform1f(u(p,"uKS"),gk);gl.uniform1f(u(p,"uErCap"),0.0025/gk);});
    let t=state;state=next;next=t;t=flux;flux=nextFlux;nextFlux=t;
  }
  return{state,n,nh,simN,apron,padded:padded.field};
}
export function gpuHydraulicPipes(inp,opts={}){
  const{state,n,nh,simN,apron,padded}=runHydraulicPipeState(inp,opts);
  // Terminal settle. The state texture's blue channel is sediment still suspended when the
  // iterations end, in the SAME normalized-height units as bed (the state shader exchanges the
  // two strictly 1:1). GPU.read keeps only red, so this load used to vanish at readback - 92% of
  // net-eroded volume at reference settings - which is why the production hydraulic path could
  // never finish a fan or a delta. Green (water) is never added - it is rain.
  const rgba=GPU.readRGBA(state,simN);
  const o=new Float32Array(n*nh);let sumIn=0,sumOut=0,settled=0,sumSimOut=0;
  for(let i=0;i<simN*simN;i++)sumSimOut+=rgba[i*4]+rgba[i*4+2];
  // THE APRON RING, ACCUMULATED IN ITS OWN RIGHT. Every loss term here used to be a difference of
  // sums over NESTED cell sets — `cropExchange: sumIn-sumOut` and `lost: sumSimIn-sumSimOut` — so
  // any closure identity computed from them held by construction, for any implementation, including
  // one that deleted the terrain. A Sprint 3 audit found the guard meant to catch that
  // (`exportedDerived:false`) was itself a hardcoded literal on this very object: the ledger
  // declared itself itemized while its only loss term was a subtraction.
  //
  // Core and apron are DISJOINT, so accumulating the apron separately gives a genuinely independent
  // reading of the same physical quantity. If the kernel conserves mass, what leaves the core
  // arrives in the apron: (sumIn - sumOut) == (apronOut - apronIn) to within float error. If it
  // does not, the two disagree — which no subtraction of nested sums could ever show.
  let apronIn=0,apronOut=0,apronCells=0;
  for(let y=0;y<simN;y++)for(let x=0;x<simN;x++){
    const inCore=(y>=apron&&y<apron+nh&&x>=apron&&x<apron+n);
    if(inCore)continue;
    const si=(y*simN+x)*4;
    apronIn+=padded[y*simN+x];apronOut+=rgba[si]+rgba[si+2];apronCells++;
  }
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const i=y*n+x,si=((y+apron)*simN+x+apron)*4;
    o[i]=rgba[si]+rgba[si+2];
    settled+=rgba[si+2];sumIn+=inp[i];sumOut+=o[i];
  }
  const sumSimIn=fieldSum(padded);
  hydroMassDiag={engine:"pipes",settle:true,boundaryPolicy:"continuation-apron-closed-wall",
    boundaryApronCells:apron,sumIn,sumOut,settled,cropExchange:sumIn-sumOut,
    sumSimIn,sumSimOut,
    // Itemized: accumulated over the apron ring, a disjoint cell set from the core. `exportedDerived`
    // now reports the truth about THIS field rather than being a constant.
    apronCells,apronIn,apronOut,exportedToApron:apronOut-apronIn,exported:apronOut-apronIn,
    exportedDerived:false,
    // Total non-conservation across the WHOLE simulated domain, apron included. This is what the
    // field named `lost` always was, and it is NOT export: material leaving the core is still inside
    // the padded domain. It should be ~0, and calling it "lost" hid that.
    nonConservation:sumSimIn-sumSimOut,lost:sumSimIn-sumSimOut};
  return o;
}

// GPU droplet erosion on WebGL2. Particle state is ping-ponged through float textures; every
// particle emits one signed bed action per step. Those actions are rasterised as point sprites
// into a float delta target with additive blending, then applied to the height texture in a
// separate pass. This is the rasterisation-style solution to overlapping droplet brush writes:
// particles never write the terrain directly, and the terrain is read only after the complete
// action batch has landed.
const GPU_PIPE_SETTLE_FS=`#version 300 es
  precision highp float;out vec4 frag;uniform sampler2D uS;uniform int uOffset;
  void main(){ivec2 p=ivec2(gl_FragCoord.xy)+ivec2(uOffset);vec3 s=texelFetch(uS,p,0).rgb;
    frag=vec4(s.r+s.b,0.0,0.0,1.0);}`;
const GPU_DROPLET_UPDATE_FS=`#version 300 es
  precision highp float;precision highp int;
  layout(location=0) out vec4 outPos;
  layout(location=1) out vec4 outDyn;
  layout(location=2) out vec4 outAction;
  uniform sampler2D uPos,uDyn,uHeight;
  uniform int uPS,uCount,uN,uStep,uSeed,uMargin;
  uniform float uInertia,uCapacity,uErode,uDeposit,uEvap,uGravity,uMinSlope,uGridK,uMinWater;
  float H(ivec2 p){return texelFetch(uHeight,clamp(p,ivec2(0),ivec2(uN-1)),0).r;}
  vec3 HG(vec2 p){
    ivec2 a=ivec2(floor(p));vec2 f=p-vec2(a);
    float h00=H(a),h10=H(a+ivec2(1,0)),h01=H(a+ivec2(0,1)),h11=H(a+ivec2(1,1));
    float h=mix(mix(h00,h10,f.x),mix(h01,h11,f.x),f.y);
    float gx=mix(h10-h00,h11-h01,f.y),gy=mix(h01-h00,h11-h10,f.x);
    return vec3(gx,gy,h);}
  float rand01(int i){
    uint h=uint(i)*374761393u+uint(uStep)*668265263u+uint(uSeed)*1442695041u+2246822519u;
    h=(h^(h>>13u))*1274126177u;return float(h^(h>>16u))/4294967295.0;}
  void main(){
    ivec2 tc=ivec2(gl_FragCoord.xy);int idx=tc.y*uPS+tc.x;
    if(idx>=uCount){outPos=vec4(0.0);outDyn=vec4(0.0);outAction=vec4(0.0);return;}
    vec4 ps=texelFetch(uPos,tc,0),ds=texelFetch(uDyn,tc,0);
    if(ds.w!=1.0){outPos=ps;outDyn=ds;outAction=vec4(0.0);return;}
    vec2 pos=ps.xy,dir=ps.zw;float speed=ds.x,water=ds.y,sed=ds.z;
    vec3 old=HG(pos);dir=dir*uInertia-old.xy*(1.0-uInertia);
    float dl=length(dir);
    if(dl<0.00001){float a=rand01(idx)*6.28318530718;dir=vec2(cos(a),sin(a));}
    else dir/=dl;
    vec2 nextPos=pos+dir;
    float margin=float(uMargin);
    if(nextPos.x<margin||nextPos.y<margin||
       nextPos.x>=float(uN-1)-margin||nextPos.y>=float(uN-1)-margin){
      outPos=vec4(pos,dir);outDyn=vec4(speed,water,sed,0.0);outAction=vec4(0.0);return;}
    float dH=HG(nextPos).z-old.z;
    float cap=max(-dH*uGridK,uMinSlope)*speed*water*uCapacity;
    float amount=0.0;
    if(sed>cap||dH>0.0){
      float dep=dH>0.0?min(dH,sed):max(0.0,(sed-cap)*uDeposit);
      sed-=dep;amount=dep;
    }else{
      float er=min(max(0.0,(cap-sed)*uErode),max(0.0,-dH));
      sed+=er;amount=-er;
    }
    // Bound the velocity/CFL feedback: a stale overlapping scatter may deepen a channel, but it
    // cannot turn that local error into unbounded capacity on the following step.
    speed=min(8.0,sqrt(max(0.0,speed*speed-dH*uGravity)));water*=1.0-uEvap;
    float alive=water<uMinWater?2.0:1.0; // 2 = dry on-grid; remaining load stays suspended
    outPos=vec4(nextPos,dir);outDyn=vec4(speed,water,sed,alive);
    outAction=abs(amount)>1e-12?vec4(pos,amount,1.0):vec4(0.0);
  }`;
const GPU_DROPLET_SPLAT_VS=`#version 300 es
  precision highp float;precision highp int;
  uniform sampler2D uAction;uniform int uPS,uCount,uN,uRadius;
  flat out vec4 vAction;flat out float vNorm;
  void main(){int idx=gl_VertexID;ivec2 tc=ivec2(idx%uPS,idx/uPS);
    vec4 a=idx<uCount?texelFetch(uAction,tc,0):vec4(0.0);vAction=a;vNorm=1.0;
    if(a.w<0.5||abs(a.z)<1e-12){gl_Position=vec4(2.0,2.0,0.0,1.0);gl_PointSize=1.0;return;}
    ivec2 base=ivec2(floor(a.xy));
    if(a.z<0.0){
      float norm=0.0;
      for(int dy=-5;dy<=5;dy++)for(int dx=-5;dx<=5;dx++){
        if(abs(dx)>uRadius||abs(dy)>uRadius)continue;
        ivec2 q=base+ivec2(dx,dy);float d=length(vec2(dx,dy));
        if(q.x>=0&&q.y>=0&&q.x<uN&&q.y<uN&&d<=float(uRadius))
          norm+=1.0-d/float(uRadius+1);}
      vNorm=max(norm,1e-6);gl_PointSize=float(2*uRadius+3);
    }else gl_PointSize=3.0;
    vec2 ndc=(vec2(base)+0.5)/float(uN)*2.0-1.0;gl_Position=vec4(ndc,0.0,1.0);
  }`;
const GPU_DROPLET_SPLAT_FS=`#version 300 es
  precision highp float;precision highp int;out vec4 frag;
  uniform int uRadius;flat in vec4 vAction;flat in float vNorm;
  void main(){ivec2 cell=ivec2(floor(gl_FragCoord.xy)),base=ivec2(floor(vAction.xy));
    ivec2 di=cell-base;float weight=0.0;
    if(vAction.z<0.0){
      float d=length(vec2(di));if(abs(di.x)>uRadius||abs(di.y)>uRadius||d>float(uRadius))discard;
      weight=(1.0-d/float(uRadius+1))/vNorm;
    }else{
      if(di.x<0||di.y<0||di.x>1||di.y>1)discard;
      vec2 f=vAction.xy-vec2(base);
      weight=(di.x==0?1.0-f.x:f.x)*(di.y==0?1.0-f.y:f.y);
    }
    frag=vec4(vAction.z*weight,0.0,0.0,0.0);
  }`;
const GPU_DROPLET_APPLY_FS=`#version 300 es
  precision highp float;out vec4 frag;uniform sampler2D uHeight,uDelta;
  void main(){ivec2 p=ivec2(gl_FragCoord.xy);
    frag=vec4(texelFetch(uHeight,p,0).r+texelFetch(uDelta,p,0).r,0.0,0.0,1.0);}`;

function bindTex(prog,name,unit,tex){
  gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,tex);gl.uniform1i(u(prog,name),unit);
}
function fieldSum(f){let s=0;for(let i=0;i<f.length;i++)s+=f[i];return s;}
function initGpuDroplets(n,count,seed,key,margin,particleWeight){
  const side=Math.max(1,Math.ceil(Math.sqrt(count))),pos=new Float32Array(side*side*4);
  const dyn=new Float32Array(side*side*4);let rng=Math.imul(seed|0,2654435761)>>>0;
  const rnd=()=>((rng=(Math.imul(rng,1664525)+1013904223)>>>0)/4294967295);
  const span=Math.max(0.001,n-1-margin*2);
  for(let i=0;i<count;i++){
    // Spawn far enough inside the domain that the full erosion brush is in-bounds. A departing
    // droplet is exported before it reaches this guard, so the rim never receives a renormalized
    // partial brush (the previous source of concentrated edge cuts).
    pos[i*4]=margin+rnd()*span;pos[i*4+1]=margin+rnd()*span;
    dyn[i*4]=1;dyn[i*4+1]=particleWeight;dyn[i*4+3]=1;
  }
  return{side,pos:GPU.uploadRGBA(key+"PosA",side,pos),dyn:GPU.uploadRGBA(key+"DynA",side,dyn)};
}
function splatDropletActions(action,side,count,delta,n,radius,key){
  const prog=GPU.customProg("dropletSplat",GPU_DROPLET_SPLAT_VS,GPU_DROPLET_SPLAT_FS);
  GPU.bind(delta,n);gl.disable(gl.DEPTH_TEST);gl.enable(gl.BLEND);gl.blendEquation(gl.FUNC_ADD);
  gl.blendFunc(gl.ONE,gl.ONE);gl.useProgram(prog);bindTex(prog,"uAction",0,action);
  gl.uniform1i(u(prog,"uPS"),side);gl.uniform1i(u(prog,"uCount"),count);
  gl.uniform1i(u(prog,"uN"),n);gl.uniform1i(u(prog,"uRadius"),radius);
  gl.drawArrays(gl.POINTS,0,side*side);gl.disable(gl.BLEND);gl.bindFramebuffer(gl.FRAMEBUFFER,null);
}
let lastDropletRunMeta=null;
function runHydraulicDropletCohort(heightTex,opts,key,count,cohortSeed,particleWeight){
  const n=fieldW();
  const lifetime=Math.max(1,Math.round(opts.lifetime==null?48:opts.lifetime));
  const inertia=opts.inertia==null ? .05 : opts.inertia,capacity=opts.capacity==null ? 4 : opts.capacity;
  const erode=opts.erode==null ? .3 : opts.erode,deposit=opts.deposit==null ? .3 : opts.deposit;
  const evap=opts.evap==null ? .02 : opts.evap,gravity=opts.gravity==null ? 4 : opts.gravity;
  const minSlope=opts.minSlope==null ? .01 : opts.minSlope,gk=opts.gridK>0?opts.gridK:1;
  const radius=Math.max(1,Math.min(5,Math.round(opts.radius==null?2:opts.radius)));
  const margin=radius+1;
  const evapK=gk===1?evap:1-Math.pow(1-evap,1/gk);
  const erodeK=gk===1?erode:1-Math.pow(1-erode,1/gk);
  const depositK=gk===1?deposit:1-Math.pow(1-deposit,1/gk);
  const steps=Math.max(1,Math.round(lifetime*gk));
  const initial=initGpuDroplets(n,count,cohortSeed,key,margin,particleWeight);
  const side=initial.side,pUpdate=GPU.prog("dropletUpdate",GPU_DROPLET_UPDATE_FS);
  const pApply=GPU.prog("dropletApply",GPU_DROPLET_APPLY_FS);
  let pos=initial.pos,dyn=initial.dyn,nextPos=GPU.rt(key+"PosB",side),nextDyn=GPU.rt(key+"DynB",side);
  const workA=GPU.rt(key+"HeightWorkA",n),workB=GPU.rt(key+"HeightWorkB",n);
  let height=heightTex,nextHeight=heightTex===workA?workB:workA;
  const action=GPU.rt(key+"Action",side),delta=GPU.rt(key+"Delta",n);
  for(let step=0;step<steps;step++){
    GPU.runMRT(pUpdate,side,[nextPos,nextDyn,action],p=>{
      bindTex(p,"uPos",0,pos);bindTex(p,"uDyn",1,dyn);bindTex(p,"uHeight",2,height);
      gl.uniform1i(u(p,"uPS"),side);gl.uniform1i(u(p,"uCount"),count);gl.uniform1i(u(p,"uN"),n);
      gl.uniform1i(u(p,"uStep"),step);gl.uniform1i(u(p,"uSeed"),cohortSeed);
      gl.uniform1i(u(p,"uMargin"),margin);
      gl.uniform1f(u(p,"uInertia"),inertia);
      gl.uniform1f(u(p,"uCapacity"),capacity);gl.uniform1f(u(p,"uErode"),erodeK);
      gl.uniform1f(u(p,"uDeposit"),depositK);gl.uniform1f(u(p,"uEvap"),evapK);
      gl.uniform1f(u(p,"uGravity"),gravity);gl.uniform1f(u(p,"uMinSlope"),minSlope);
      gl.uniform1f(u(p,"uGridK"),gk);gl.uniform1f(u(p,"uMinWater"),.008*particleWeight);});
    GPU.clear(delta,n);splatDropletActions(action,side,count,delta,n,radius,key);
    GPU.run(pApply,n,nextHeight,p=>{bindTex(p,"uHeight",0,height);bindTex(p,"uDelta",1,delta);});
    let t=pos;pos=nextPos;nextPos=t;t=dyn;dyn=nextDyn;nextDyn=t;t=height;height=nextHeight;nextHeight=t;
  }
  // ARCH-REF: ADR-001 (docs/adr-001-gpu-hydraulic-composition.md)
  // Lifetime is a numerical work cap, not a physical deposition event. Depositing every
  // particle's remaining load here synchronises thousands of point deposits and turns the
  // terrain into a field of cones. Keep only capacity-driven deposition from the integration
  // loop; boundary export and suspended load at truncation are named together in the ledger.
  return height;
}
function runHydraulicDropletTexture(heightTex,opts={},key="droplet"){
  const n=fieldW(),count=Math.max(1,Math.round(opts.droplets==null?15000:opts.droplets));
  // A particle step is a scatter batch: every action in it sampled the same pre-step terrain.
  // At high particles/cell, overlapping deposits/brushes can collectively overshoot the
  // height difference each particle bounded independently, invert the slope, and feed an
  // exponential speed/capacity spike on the next step. Cohorts cap that stale-read density;
  // each cohort finishes against terrain containing every prior cohort's actions.
  const cohortLimit=Math.max(1024,Math.floor(n*n*.10)); // shape-ok: GPU terrain texture is square
  // Particle count is sampling density, not an unbounded erosion-strength multiplier. Up to
  // half a particle per cell, each path has unit weight. Beyond that, each particle represents
  // a smaller water parcel. Capacity, carried sediment, and the terrain write therefore use the
  // same weight instead of scaling only the write and breaking the particle/terrain ledger.
  const particleWeight=Math.min(1,n*n*.5/count); // shape-ok: GPU terrain texture is square
  const cohorts=Math.ceil(count/cohortLimit),baseSeed=opts.seed==null?1:opts.seed|0;
  let height=heightTex,offset=0;
  for(let cohort=0;cohort<cohorts;cohort++){
    const cohortCount=Math.min(cohortLimit,count-offset);
    const cohortSeed=(baseSeed+Math.imul(cohort,0x9e3779b9))|0;
    height=runHydraulicDropletCohort(height,opts,key,cohortCount,cohortSeed,particleWeight);
    offset+=cohortCount;
  }
  lastDropletRunMeta={requestedDroplets:count,cohortLimit,cohorts,particleWeight};
  return height;
}
export function gpuHydraulicDroplets(inp,opts={}){
  if(!gpuDropletsReady())throw new Error("GPU droplet erosion requires WebGL2 float render targets and EXT_float_blend");
  const n=fieldW(),sumIn=fieldSum(inp),height=GPU.upload("dropletHeightA",n,inp);
  const result=GPU.read(runHydraulicDropletTexture(height,opts,"droplet"),n),sumOut=fieldSum(result);
  const exportedOrSuspended=sumIn-sumOut;
  hydroMassDiag={engine:"gpu-droplets",settle:false,terminalDeposit:false,
    terminalPolicy:"suspend-at-lifetime",sumIn,sumOut,settled:0,
    exported:exportedOrSuspended,exportedOrSuspended,exportedDerived:true,
    unresolvedIncluded:true,lost:0,...lastDropletRunMeta,stages:["droplets"],readbacks:1};
  return result;
}
export function gpuHydraulicCombined(inp,{pipes={},droplets={}}={}){
  if(!gpuDropletsReady())throw new Error("Combined hydraulic GPU path requires WebGL2 float blending");
  const sumIn=fieldSum(inp),pipe=runHydraulicPipeState(inp,pipes,"combinedPipe");
  const settleProg=GPU.prog("pipeSettle",GPU_PIPE_SETTLE_FS),pipeHeight=GPU.rt("combinedPipeHeight",pipe.n);
  GPU.run(settleProg,pipe.n,pipeHeight,p=>{bindTex(p,"uS",0,pipe.state);
    gl.uniform1i(u(p,"uOffset"),pipe.apron);});
  const result=GPU.read(runHydraulicDropletTexture(pipeHeight,droplets,"combinedDroplet"),pipe.n);
  const sumOut=fieldSum(result);
  const exportedOrSuspended=sumIn-sumOut;
  hydroMassDiag={engine:"gpu-combined",settle:false,pipeSettled:true,terminalDeposit:false,
    terminalPolicy:"suspend-at-lifetime",
    pipeBoundaryPolicy:"continuation-apron-closed-wall",pipeBoundaryApronCells:pipe.apron,
    sumIn,sumOut,settled:0,exported:exportedOrSuspended,exportedOrSuspended,
    exportedDerived:true,unresolvedIncluded:true,lost:0,
    ...lastDropletRunMeta,stages:["pipes","droplets"],readbacks:1};
  return result;
}
// GPU compute is square-texture end to end: every kernel taps ivec2 +-(1,0) neighbours and the
// noise shaders sample grid-uv x/uN, so on the hex lattice they would print the half-cell
// zig-zag and square-stencil anisotropy silently (26's seed-contract trap). Hex forces the CPU
// path wholesale; the GPU button stays honest on the square lattice.
export const gpuReady=()=>USE_GPU&&terrainDef.lattice!=="hex"&&GPU.init();
export const gpuDropletsReady=()=>gpuReady()&&GPU.floatBlend;
