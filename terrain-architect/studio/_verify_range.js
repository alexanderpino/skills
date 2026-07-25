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
    // ---- 5. placing N Mountains must give N DIFFERENT mountains ----
    // Taking the type default gave every node the same seed, so three placed Mountains were three
    // identical ones and the whole place-and-combine workflow was pointless.
    nodes.length=0; edges.length=0; uid=1;
    const m1=makeNode("mountain",0,0), m2=makeNode("mountain",0,0), m3=makeNode("mountain",0,0);
    const f1=TYPES.mountain.eval(m1.params,[],m1), f2=TYPES.mountain.eval(m2.params,[],m2);
    // compare INSIDE the footprint: most of the tile is zero in both, and averaging over it dilutes
    // the difference into nothing (0.0067 whole-tile vs 0.30 relative, for the same two fields)
    let d12=0, sum=0, c12=0;
    for (let i=0;i<f1.length;i++){ if (f1[i]<=0 && f2[i]<=0) continue;
      d12 += Math.abs(f1[i]-f2[i]); sum += Math.max(f1[i],f2[i]); c12++; }
    const rel = d12/Math.max(sum,1e-9);
    // the control that gives the number meaning: SAME seed must reproduce bit-for-bit, so any
    // non-zero relative difference is attributable to the seed and nothing else
    const same = TYPES.mountain.eval({...m1.params, seed:m2.params.seed},[],m2);
    let dSame=0; for (let i=0;i<f2.length;i++) dSame += Math.abs(f2[i]-same[i]);
    // ...and rebuilding the SAME graph must reproduce the SAME seeds, so it is derived not random
    const firstRun=[m1.params.seed,m2.params.seed,m3.params.seed];
    nodes.length=0; edges.length=0; uid=1;
    const r1=makeNode("mountain",0,0), r2=makeNode("mountain",0,0), r3=makeNode("mountain",0,0);
    out.seedPerPlacedNode = {
      seeds: firstRun, rebuilt: [r1.params.seed,r2.params.seed,r3.params.seed],
      allDistinct: new Set(firstRun).size === 3,
      sameSeedIsIdentical: dSame === 0,
      differentTerrain: rel > 0.05 && dSame === 0,
      relativeDiffInFootprint: +rel.toFixed(3),
      footprintCells: c12,
      deterministicAcrossRebuilds: firstRun.every((v,i)=>v===[r1,r2,r3][i].params.seed),
      notTheTypeDefault: firstRun.every(v=>v!==TYPES.mountain.params.find(q=>q.key==="seed").def) };

    // ...and the seed must remain EDITABLE -- a derived seed that cannot be overridden is just a
    // different hardcoded one. Setting it by hand must reproduce that exact terrain.
    const hand = {...r1.params, seed: 123};
    const a1 = TYPES.mountain.eval(hand,[],r1), a2 = TYPES.mountain.eval({...r2.params, seed:123},[],r2);
    let dHand=0; for (let i=0;i<a1.length;i++) dHand += Math.abs(a1[i]-a2[i]);
    out.seedIsEditable = { twoNodesForcedToSameSeedMatch: dHand === 0,
      differsFromItsDerivedSeed: (()=>{ const d0=TYPES.mountain.eval(r1.params,[],r1);
        let z=0; for (let i=0;i<a1.length;i++) z += Math.abs(a1[i]-d0[i]); return z > 0; })() };

    // duplicating gives a NEW feature, not a clone -- "every node gets a new seed"
    nodes.length=0; edges.length=0; uid=1;
    const orig = makeNode("mountain",0,0);
    selected = orig; duplicateSel();
    const dup = nodes[nodes.length-1];
    out.duplicateReseeds = { original: orig.params.seed, duplicate: dup.params.seed,
      differs: dup.params.seed !== orig.params.seed,
      otherParamsCopied: dup.params.size === orig.params.size && dup.params.style === orig.params.style };
    return out;
  });

  console.log(JSON.stringify(r, null, 2));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
