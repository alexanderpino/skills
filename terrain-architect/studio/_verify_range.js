// Place three mountains and combine them into ONE range -- the workflow reference-impl/landforms.py
// prescribes: "place it, combine several (np.maximum / ops_filters.smax), then run a real pass".
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    const n = RES, out = {};
    // ---- 1. smax is the union, smin is the intersection. State it as a number. ----
    out.operators = { smax_1_0:+smax(1,0,0.15).toFixed(3), smin_1_0:+smin(1,0,0.15).toFixed(3),
                      unionIsMax: smax(1,0,0.15) > 0.9 && smin(1,0,0.15) < 0.1 };

    // ---- 2. three placed mountains ----
    const M = (o) => TYPES.mountain.eval({style:"eroded", seed:7, x:0.5, y:0.5, size:0.35,
                                          angle:25, ridges:2, relief:0.66, ...o});
    const A = M({x:0.26, y:0.64, size:0.26, seed:3,  angle:20});
    const B = M({x:0.50, y:0.50, size:0.30, seed:11, angle:25});
    const C = M({x:0.74, y:0.38, size:0.24, seed:29, angle:30});
    const centroid = f => { let sx=0,sy=0,w=0;
      for (let y=0;y<n;y++) for (let x=0;x<n;x++){ const v=f[y*n+x]; sx+=v*(x+0.5)/n; sy+=v*(y+0.5)/n; w+=v; }
      return [+(sx/w).toFixed(3), +(sy/w).toFixed(3)]; };
    out.placedWhereAsked = { A:centroid(A), B:centroid(B), C:centroid(C),
                             distinct: centroid(A)[0] < centroid(B)[0] && centroid(B)[0] < centroid(C)[0] };
    const relief = f => { let lo=1e9,hi=-1e9; for (const v of f){if(v<lo)lo=v;if(v>hi)hi=v;} return +(hi-lo).toFixed(3); };
    out.eachIsALandform = { reliefA:relief(A), reliefB:relief(B), reliefC:relief(C),
                            allNonTrivial: [A,B,C].every(f=>relief(f) > 0.05) };

    // ---- 3. union: hard max vs smooth max, scored at the SEAM ----
    const hard = combine(combine(A,B,Math.max), C, Math.max);
    const soft = TYPES.smax.eval({k:0.12}, [TYPES.smax.eval({k:0.12},[A,B]), C]);
    const seamCurv = (f) => { let sum=0,cnt=0;
      for (let y=1;y<n-1;y++) for (let x=1;x<n-1;x++){
        const i=y*n+x, v=[A[i],B[i],C[i]].sort((a,bb)=>bb-a);
        if (v[0] > 0.05 && Math.abs(v[0]-v[1]) < 0.01*v[0]) {
          sum += Math.abs(4*f[i]-f[i-1]-f[i+1]-f[i-n]-f[i+n]); cnt++; } }
      return { cells:cnt, mean:sum/Math.max(cnt,1) }; };
    const sh = seamCurv(hard), ss = seamCurv(soft);
    out.seam = { hardMax:+sh.mean.toExponential(3), smoothMax:+ss.mean.toExponential(3),
                 seamCells: sh.cells,
                 smoothReducesCreaseBy:+(100*(1-ss.mean/sh.mean)).toFixed(1)+"%",
                 smoothIsSmoother: ss.mean < sh.mean };

    // ---- 4. is it ONE range? connected components of the high ground ----
    const components = (f, frac) => {
      let hi=0; for (const v of f) if (v>hi) hi=v;
      const thr=hi*frac, seen=new Uint8Array(n*n); let comps=0, biggest=0;
      for (let i=0;i<n*n;i++){ if (seen[i]||f[i]<=thr) continue;
        comps++; let size=0; const st=[i]; seen[i]=1;
        while (st.length){ const c=st.pop(); size++; const x=c%n, y=(c/n)|0;
          if(x>0&&!seen[c-1]&&f[c-1]>thr){seen[c-1]=1;st.push(c-1);}
          if(x<n-1&&!seen[c+1]&&f[c+1]>thr){seen[c+1]=1;st.push(c+1);}
          if(y>0&&!seen[c-n]&&f[c-n]>thr){seen[c-n]=1;st.push(c-n);}
          if(y<n-1&&!seen[c+n]&&f[c+n]>thr){seen[c+n]=1;st.push(c+n);} }
        if (size>biggest) biggest=size; }
      return { components:comps, largestCells:biggest }; };
    const eroded = thermalErode(soft, {talus:0.010, iters:40, rate:0.5});
    out.oneRange = { unionedOnly: components(soft, 0.35), afterErosion: components(eroded, 0.35),
                     erosionKnitsThemTogether:
                       components(eroded,0.35).components < components(soft,0.35).components };
    return out;
  });

  console.log(JSON.stringify(r, null, 2));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
