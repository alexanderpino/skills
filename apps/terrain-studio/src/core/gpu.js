// The GPGPU fast path: WebGL2 render-to-texture kernels for noise, thermal, warp and the
// pipe-model hydraulic solver, plus the gpuReady() capability gate.
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
import { fieldW, fieldH, normalize, terrainDef, XF, USE_GPU } from '../legacy.js';

let gl = null;
export const setGL = (ctx) => { gl = ctx; };

export const GPU={
  ok:null,vs:null,progs:{},rts:{},fbo:null,
  init(){
    if(this.ok!==null)return this.ok;
    this.ok=false;
    if(!gl||typeof WebGL2RenderingContext==="undefined"||!(gl instanceof WebGL2RenderingContext))return false;
    if(!gl.getExtension("EXT_color_buffer_float"))return false;   // required to render into float textures
    this.vs=`#version 300 es
      void main(){vec2 p=vec2((gl_VertexID==1)?3.:-1.,(gl_VertexID==2)?3.:-1.);gl_Position=vec4(p,0.,1.);}`;
    this.fbo=gl.createFramebuffer();
    this.ok=true;return true;
  },
  prog(key,fs){if(!this.progs[key])this.progs[key]=makeProg(this.vs,fs);return this.progs[key];},
  rt(key,n){const k=key+"_"+n;let t=this.rts[k];
    if(!t){t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA32F,n,n,0,gl.RGBA,gl.FLOAT,null);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
      this.rts[k]=t;}
    return t;},
  bind(target,n){gl.bindFramebuffer(gl.FRAMEBUFFER,this.fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,target,0);gl.viewport(0,0,n,n);},
  run(prog,n,target,setup){
    this.bind(target,n);gl.disable(gl.DEPTH_TEST);gl.disable(gl.BLEND);
    gl.useProgram(prog);if(setup)setup(prog);
    gl.drawArrays(gl.TRIANGLES,0,3);gl.bindFramebuffer(gl.FRAMEBUFFER,null);},
  clear(target,n){this.bind(target,n);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.bindFramebuffer(gl.FRAMEBUFFER,null);},
  upload(key,n,data){const t=this.rt(key,n),rgba=new Float32Array(n*n*4);   // shape-ok: staging buffer for the square texture above, not a field
    for(let i=0;i<n*n;i++)rgba[i*4]=data[i];   // shape-ok: fills that square texture
    gl.bindTexture(gl.TEXTURE_2D,t);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA32F,n,n,0,gl.RGBA,gl.FLOAT,rgba);return t;},
  uploadState(key,n,bed){const t=this.rt(key,n),rgba=new Float32Array(n*n*4);   // shape-ok: staging buffer for the square texture above, not a field
    for(let i=0;i<n*n;i++){rgba[i*4]=bed[i];rgba[i*4+3]=1;}   // shape-ok: fills that square texture
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

// Mei-style virtual-pipe hydraulic erosion in gather form. Unlike the CPU droplet solver, every
// pixel only reads its four neighbours, so the whole simulation remains in float textures until one
// final readback. RGBA state = bed, water, sediment, 1; RGBA flux = left, right, top, bottom.
const GPU_PIPE_FLUX_FS=`#version 300 es
  precision highp float;precision highp int;out vec4 frag;
  uniform sampler2D uS,uPrevF;uniform int uN;uniform float uRain,uMomentum,uFlow;
  bool inside(ivec2 p){return p.x>=0&&p.y>=0&&p.x<uN&&p.y<uN;}
  vec3 S(ivec2 p){return texelFetch(uS,clamp(p,ivec2(0),ivec2(uN-1)),0).rgb;}
  float head(ivec2 p,float edge){return inside(p)?S(p).r+S(p).g:edge;}
  void main(){
    ivec2 p=ivec2(gl_FragCoord.xy);vec3 s=S(p);float water=s.g+uRain,h=s.r+water;
    vec4 prev=texelFetch(uPrevF,p,0);
    vec4 dh=vec4(h-head(p+ivec2(-1,0),s.r-0.03),h-head(p+ivec2(1,0),s.r-0.03),
                 h-head(p+ivec2(0,-1),s.r-0.03),h-head(p+ivec2(0,1),s.r-0.03));
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
    float slope=uKS*max(max(abs(b-S(p+ivec2(-1,0)).r),abs(b-S(p+ivec2(1,0)).r)),
                        max(abs(b-S(p+ivec2(0,-1)).r),abs(b-S(p+ivec2(0,1)).r)));
    float speed=min(8.0,(inflow+outflow)/max(0.001,0.5*(water0+water)));
    float cap=uCapacity*max(slope,0.0005)*speed*(water0>0.0002?1.0:0.0);
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
export function gpuHydraulicPipes(inp,{iters=48,capacity=6,erode=0.35,deposit=0.28,inertia=0.05,gridK=1}){
  const n=fieldW(),nh=fieldH(),pF=GPU.prog("pipeFlux",GPU_PIPE_FLUX_FS),pS=GPU.prog("pipeState",GPU_PIPE_STATE_FS);
  let state=GPU.uploadState("pipeStateA",n,inp),next=GPU.rt("pipeStateB",n);
  let flux=GPU.rt("pipeFluxA",n),nextFlux=GPU.rt("pipeFluxB",n);GPU.clear(flux,n);
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
  const rain=0.0012/gk,evap=gk===1?0.985:Math.pow(0.985,1/gk);
  const momentum0=clamp(0.35+inertia,0.2,0.82),momentum=gk===1?momentum0:Math.pow(momentum0,1/gk);
  const flow=0.42*gk;
  const er0=erode*0.16,erRate=gk===1?er0:1-Math.pow(1-er0,1/gk);
  const dp0=deposit*0.22,dpRate=gk===1?dp0:1-Math.pow(1-dp0,1/gk);
  for(let i=0;i<itersEff;i++){
    GPU.run(pF,n,nextFlux,p=>{
      gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,state);gl.uniform1i(u(p,"uS"),0);
      gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,flux);gl.uniform1i(u(p,"uPrevF"),1);
      gl.uniform1i(u(p,"uN"),n);gl.uniform1f(u(p,"uRain"),rain);gl.uniform1f(u(p,"uMomentum"),momentum);
      gl.uniform1f(u(p,"uFlow"),flow);});
    GPU.run(pS,n,next,p=>{
      gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,state);gl.uniform1i(u(p,"uS"),0);
      gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,nextFlux);gl.uniform1i(u(p,"uF"),1);
      gl.uniform1i(u(p,"uN"),n);gl.uniform1f(u(p,"uRain"),rain);gl.uniform1f(u(p,"uEvap"),evap);
      gl.uniform1f(u(p,"uCapacity"),capacity*0.075);gl.uniform1f(u(p,"uErode"),erRate);
      gl.uniform1f(u(p,"uDeposit"),dpRate);
      gl.uniform1f(u(p,"uKS"),gk);gl.uniform1f(u(p,"uErCap"),0.0025/gk);});
    let t=state;state=next;next=t;t=flux;flux=nextFlux;nextFlux=t;
  }
  // Terminal settle. The state texture's blue channel is sediment still suspended when the
  // iterations end, in the SAME normalized-height units as bed (the state shader exchanges the
  // two strictly 1:1). GPU.read keeps only red, so this load used to vanish at readback - 92% of
  // net-eroded volume at reference settings - which is why the production hydraulic path could
  // never finish a fan or a delta. Settle it where it stands, rim included: a rim exclusion was
  // tried and REJECTED by measurement - the -0.03 edge head FLUSHES suspension off-grid, so the
  // rim carries the LEAST of any ring (mean 0.0025 vs 0.0064 interior) and its max suspension is
  // half its mean net erosion, making a deposit lip geometrically impossible; excluding it only
  // deepened the existing one-cell border trench ~15%. Green (water) is never added - it is rain.
  const rgba=GPU.readRGBA(state,n);
  const o=new Float32Array(n*nh);let sumIn=0,sumOut=0,settled=0;
  for(let i=0;i<n*nh;i++){o[i]=rgba[i*4]+rgba[i*4+2];settled+=rgba[i*4+2];sumIn+=inp[i];sumOut+=o[i];}
  // With everything settled, the only bed-mass sink left is in-sim outflow through the edge
  // pipes, so `exported` is exact by elimination - but DERIVED, not independently itemized.
  // exportedDerived tells a closure gate not to accept it as evidence (the CPU ledger's is).
  hydroMassDiag={engine:"pipes",settle:true,sumIn,sumOut,settled,exported:sumIn-sumOut,exportedDerived:true,lost:0};
  return o;
}
// GPU compute is square-texture end to end: every kernel taps ivec2 +-(1,0) neighbours and the
// noise shaders sample grid-uv x/uN, so on the hex lattice they would print the half-cell
// zig-zag and square-stencil anisotropy silently (26's seed-contract trap). Hex forces the CPU
// path wholesale; the GPU button stays honest on the square lattice.
export const gpuReady=()=>USE_GPU&&terrainDef.lattice!=="hex"&&GPU.init();
