// "Place before you sample": a Transform over a procedural chain must be EXACT (re-evaluated at
// transformed coordinates), and measurably sharper than resampling the finished raster.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    const out = {};
    const GEN = {seed:7, freq:3, octaves:6, lac:2, gain:0.5};
    // mean |laplacian| — the fine-detail energy a low-pass filter removes
    const detail = f => { const n=RES; let s=0,c=0;
      for(let y=1;y<n-1;y++)for(let x=1;x<n-1;x++){
        s+=Math.abs(4*f[y*n+x]-f[y*n+x-1]-f[y*n+x+1]-f[(y-1)*n+x]-f[(y+1)*n+x]);c++;}
      return s/c; };
    const rms = (a,bb) => { let s=0;for(let i=0;i<a.length;i++)s+=(a[i]-bb[i])**2;return Math.sqrt(s/a.length); };
    const maxDiff = (a,bb) => { let m=0;for(let i=0;i<a.length;i++)m=Math.max(m,Math.abs(a[i]-bb[i]));return m; };
    const withXF = (m, fn) => { const prev=XF; XF=m; try{ return fn(); } finally{ XF=prev; } };

    // ---- 1. identity must be bit-for-bit the untransformed field (no silent behaviour change) ----
    const base = fbmField(gnoise, GEN);
    const ident = withXF(xfFromParams({scale:1,aspect:1,angle:0,offX:0,offY:0}), () => fbmField(gnoise, GEN));
    out.identity = { maxAbsDiff: +maxDiff(base,ident).toExponential(2) };

    // ---- 2. exact vs raster at 2x magnification ----
    const P2 = {scale:2, aspect:1, angle:0, offX:0, offY:0, edge:"clamp"};
    const exact  = withXF(xfFromParams(P2), () => fbmField(gnoise, GEN));
    const raster = transformField(base, P2);
    const dE = detail(exact), dR = detail(raster);
    out.magnify2x = { detailExact:+dE.toFixed(5), detailRaster:+dR.toFixed(5),
                      rasterDetailLostPct:+((1-dR/dE)*100).toFixed(1),
                      agreementRms:+rms(exact,raster).toFixed(4) };

    // ---- 3. exact 2x is the SAME SURFACE, just magnified: it must equal the generator evaluated at
    //         half frequency over the centre. Analytic oracle, not a heuristic. ----
    const half = withXF(null, () => fbmField(gnoise, {...GEN, freq: GEN.freq/2}));
    // exact 2x samples uv/2+0.25; freq/2 over the full tile samples the same band but from uv/1 --
    // instead compare against an independent direct evaluation of the transformed coordinates:
    const direct = (()=>{ const n=RES,o=newField(),M=xfFromParams(P2);
      let amps=0,a=1;for(let k=0;k<GEN.octaves;k++){amps+=a;a*=GEN.gain;}
      for(let y=0;y<n;y++)for(let x=0;x<n;x++){
        const u=M[0]*(x/n)+M[1]*(y/n)+M[2], v=M[3]*(x/n)+M[4]*(y/n)+M[5];
        let s=0,amp=1,f=GEN.freq;
        for(let k=0;k<GEN.octaves;k++){s+=gnoise(u*f,v*f,GEN.seed+k*7)*amp;amp*=GEN.gain;f*=GEN.lac;}
        o[y*n+x]=s/amps;}
      return o; })();
    out.oracle = { maxAbsDiffVsDirectEval: +maxDiff(exact,direct).toExponential(2),
                   sanityHalfFreqDiffers: rms(exact,half) > 1e-3 };

    // ---- 4. transforms COMPOSE: 2x then 2x == one 4x, in one evaluation ----
    const twice = xfMul(xfFromParams({scale:2}), xfFromParams({scale:2}));
    const once  = xfFromParams({scale:4});
    const fTwice = withXF(twice, () => fbmField(gnoise, GEN));
    const fOnce  = withXF(once,  () => fbmField(gnoise, GEN));
    out.compose = { maxAbsDiff:+maxDiff(fTwice,fOnce).toExponential(2),
                    matrixMaxDiff:+Math.max(...twice.map((v,i)=>Math.abs(v-once[i]))).toExponential(2) };

    // ---- 5. chained NON-INTEGER moves: each raster hop is another low-pass, exact never degrades ----
    const step = {scale:1, aspect:1, angle:0, offX:0.037, offY:0.023, edge:"clamp"};
    out.translate = {};
    let rr = base, mm = null;
    for (let i=1;i<=4;i++){
      rr = transformField(rr, step); mm = xfMul(xfFromParams(step), mm);
      const ee = withXF(mm, () => fbmField(gnoise, GEN));
      out.translate["move"+i] = { detailExact:+detail(ee).toFixed(5), detailRaster:+detail(rr).toFixed(5),
                                  rasterDetailLostPct:+((1-detail(rr)/detail(ee))*100).toFixed(1) };
    }

    // ---- 6. the graph picks the right mode ----
    const gen = makeNode("perlin", 0, 0), ero = makeNode("thermal", 0, 0);
    const t1 = makeNode("transform", 0, 0), t2 = makeNode("transform", 0, 0);
    const wire = (from,to,slot)=>edges.push({from, to, slot});
    wire(gen.id, t1.id, 0);                                // procedural chain  -> exact
    wire(gen.id, ero.id, 0); wire(ero.id, t2.id, 0);       // erosion upstream  -> raster
    t1.params.scale = t2.params.scale = 2;
    evalGraph();
    out.modeSelection = { proceduralChain: t1._xfMode, afterErosion: t2._xfMode };
    out.exactChainSays = { gen: exactChain(gen.id), erosion: exactChain(ero.id) };
    const detailAuto = detail(t1._field);

    // ---- 7. forcing Raster is the escape hatch -- and an A/B on the SAME chain ----
    t1.params.mode = "raster"; markDirtyFrom(t1.id); evalGraph();
    out.forcedRaster = { mode: t1._xfMode, detailExact:+detailAuto.toFixed(5),
                         detailRaster:+detail(t1._field).toFixed(5),
                         exactIsSharper: detailAuto > detail(t1._field) };

    // ---- 8. CPU/GPU parity must survive the transform ----
    if (GPU.init()) {
      const M = xfFromParams({scale:2, angle:30, offX:0.1});
      const c = withXF(M, () => fbmField(gnoise, GEN));
      const g = withXF(M, () => gpuFbm(GEN));
    out.gpuParity = { maxAbsDiff:+maxDiff(c,g).toExponential(2) };
    } else out.gpuParity = "no gpu";
    return out;
  });

  console.log(JSON.stringify(r, null, 2));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
