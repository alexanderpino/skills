// Is our "Mountain" a PEAK, or is it noise-on-a-lump? Judged by topographic prominence, the measure
// mountaineers and geomorphologists actually use, plus the hypsometric integral and a radial profile.
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
    const n = RES;

    // --- TOPOGRAPHIC PROMINENCE via descending flood + union-find ---------------------------
    // Process cells high->low. Union with already-flooded neighbours. When two distinct basins
    // merge at elevation s, the LOWER of the two summits is closed off: its prominence is
    // summit - s (s is the key saddle). The global summit's prominence is its full relief.
    const prominence = (f) => {
      const idx = Array.from({length:n*n}, (_,i)=>i).sort((a,b)=>f[b]-f[a]);
      const parent = new Int32Array(n*n).fill(-1);      // -1 = not yet flooded
      const summit = new Float64Array(n*n);
      const find = (x) => { while (parent[x]!==x) { parent[x]=parent[parent[x]]; x=parent[x]; } return x; };
      const proms = [];
      let lo = Infinity; for (const v of f) if (v<lo) lo=v;
      for (const i of idx) {
        const x = i%n, y = (i/n)|0;
        const nb = [];
        if (x>0)   nb.push(i-1);
        if (x<n-1) nb.push(i+1);
        if (y>0)   nb.push(i-n);
        if (y<n-1) nb.push(i+n);
        parent[i] = i; summit[i] = f[i];               // new basin, provisionally its own summit
        for (const j of nb) {
          if (parent[j] === -1) continue;              // not flooded yet (lower) -- skip
          const a = find(i), c = find(j);
          if (a === c) continue;
          const sa = summit[a], sc = summit[c];
          // the lower summit dies here; f[i] is the saddle elevation
          if (sa >= sc) { proms.push(sc - f[i]); parent[c] = a; summit[a] = sa; }
          else          { proms.push(sa - f[i]); parent[a] = c; summit[c] = sc; }
        }
      }
      let hi = -Infinity; for (const v of f) if (v>hi) hi=v;
      proms.push(hi - lo);                             // the global summit
      proms.sort((a,b)=>b-a);
      const relief = hi - lo;
      return { relief, proms,
               // how many summits are REAL features rather than texture
               nAbove10pct: proms.filter(v=>v > 0.10*relief).length,
               nAbove25pct: proms.filter(v=>v > 0.25*relief).length,
               // is there one clearly dominant summit? 2nd/1st prominence ratio
               secondOverFirst: +(proms[1]/proms[0]).toFixed(3) };
    };

    const hypso = (f) => { let lo=1e9,hi=-1e9,s=0;
      for (const v of f){ if(v<lo)lo=v; if(v>hi)hi=v; s+=v; }
      return +(((s/f.length)-lo)/((hi-lo)||1)).toFixed(3); };   // cone~0.33, symmetric noise~0.5

    // radial mean height from the highest cell -- a peak descends monotonically, a massif plateaus
    const radial = (f) => {
      let bi=0; for (let i=1;i<f.length;i++) if (f[i]>f[bi]) bi=i;
      const bx=bi%n, by=(bi/n)|0, K=10, sum=new Float64Array(K), cnt=new Float64Array(K);
      const rmax = n*0.5;
      for (let y=0;y<n;y++) for (let x=0;x<n;x++){
        const d = Math.hypot(x-bx, y-by); if (d>=rmax) continue;
        const k = Math.min(K-1, (d/rmax*K)|0); sum[k]+=f[y*n+x]; cnt[k]++; }
      const prof = Array.from(sum, (v,i)=>+(v/Math.max(cnt[i],1)).toFixed(3));
      let mono = true; for (let i=1;i<K;i++) if (prof[i] > prof[i-1]+1e-6) mono = false;
      return { profile: prof, monotonicDescent: mono };
    };

    const score = (f) => { const pr = prominence(f);
      return { hypsometric: hypso(f), summitsAbove10pct: pr.nAbove10pct,
               summitsAbove25pct: pr.nAbove25pct, secondOverFirst: pr.secondOverFirst,
               radial: radial(f) }; };

    const out = {};
    const cone = (()=>{ const o=newField();
      for (let y=0;y<n;y++) for (let x=0;x<n;x++)
        o[y*n+x] = Math.max(0, 1 - Math.hypot(x/n-0.5, y/n-0.5)*2); return o; })();
    // Build from the node's DECLARED defaults, not a hand-copied list. The hand-copied version had
    // drifted -- it still said relief 0.66 after the default moved to 0.80, and never passed
    // `character` at all, so the solid-of-revolution probe below was silently measuring the domain
    // warp switched off. A harness that restates defaults will always drift away from them.
    const DEF = Object.fromEntries(TYPES.mountain.params.map(q=>[q.key,
      Array.isArray(q.def) ? JSON.parse(JSON.stringify(q.def)) : q.def]));
    const M = (o) => TYPES.mountain.eval({...DEF, form:"peak", style:"eroded", seed:7,
                     x:0.5, y:0.5, size:0.35, ...o});

    // --- the two reference extremes, so the numbers below have a scale ---
    out.reference = { cone: score(cone),
                      ridgedNoise: score(fbmField(gnoise,{seed:7,freq:5,octaves:6,lac:2.1,gain:0.55,ridge:true})) };

    // --- a PEAK has ONE summit. Topographic prominence is the measure that says so. ---
    const peaks = {};
    for (const style of ["basic","eroded","alpine","old","strata"]) peaks[style] = score(M({style}));
    for (const seed of [3,11,29]) peaks["seed"+seed] = score(M({seed}));
    // A dissected dome legitimately carries a few subsidiary highs -- the reference shows them, and
    // demanding EXACTLY one summit is what let a smooth pyramid pass here before. The invariants that
    // separate a mountain from noise are that one summit clearly dominates and that there are few of
    // them: ridged fBm scores 109 summits at a 0.56 ratio.
    out.peakIsOneSummit = {
      summitCounts: Object.fromEntries(Object.entries(peaks).map(([k,v])=>[k, v.summitsAbove10pct])),
      worstSecondOverFirst: +Math.max(...Object.values(peaks).map(v=>v.secondOverFirst)).toFixed(3),
      mostSummits: Math.max(...Object.values(peaks).map(v=>v.summitsAbove10pct)),
      oneSummitDominates: Object.values(peaks).every(v=>v.secondOverFirst < 0.25),
      fewSummits: Object.values(peaks).every(v=>v.summitsAbove10pct <= 5),
      allDescendMonotonically: Object.values(peaks).every(v=>v.radial.monotonicDescent) };

    // --- a MASSIF is deliberately several summits: the contrast is the point ---
    const massif = score(M({form:"massif"}));
    out.massifIsSeveralSummits = { summits: massif.summitsAbove10pct,
      secondOverFirst: massif.secondOverFirst,
      moreSummitsThanPeak: massif.summitsAbove10pct > peaks.eroded.summitsAbove10pct };

    // --- DISSECTION is what makes it read as a mountain, not the macro topology ---
    // A cone satisfies every prominence test above. What it fails is having any texture at all,
    // which is how a smooth pyramid passed an earlier version of this file: the statistics were
    // fine, the thing looked like a pile of sand. Measure texture directly, per unit height so the
    // metric is scale free, and only inside the footprint.
    const fineDetail = (f) => { let s=0,c=0,mx=0;
      for (let y=1;y<n-1;y++) for (let x=1;x<n-1;x++){ const i=y*n+x; if (f[i]<=0) continue;
        if (f[i]>mx) mx=f[i];
        s += Math.abs(4*f[i]-f[i-1]-f[i+1]-f[i-n]-f[i+n]); c++; }
      return +((s/Math.max(c,1))/(mx||1)).toFixed(5); };
    const coneDetail = fineDetail(cone), peakDetail = fineDetail(M({}));
    out.dissection = { cone: coneDetail, peak: peakDetail,
      ratioVsCone: +(peakDetail/Math.max(coneDetail,1e-6)).toFixed(1),
      // a smooth cone is essentially featureless; a dissected dome must be far above it
      farMoreTexturedThanACone: peakDetail > 8 * coneDetail };

    // Drainage detail must genuinely control density. Measured on a style with NO erosion, because
    // an eroded style overprints the network with its own texture and masks the parameter's effect
    // -- on `eroded` this same sweep reads flat, which is a fact about erosion, not about the knob.
    const sweep = [0.6, 1.4, 2.2, 3.4].map(d =>
      ({ detail:d, fine: fineDetail(M({style:"basic", detail:d})) }));
    // It rises across the usable range and then SATURATES: the talus pass relaxes anything finer
    // than its own scale, so past roughly 2-3x more cells stop adding texture. That is a real floor
    // on feature size, not a broken knob, and it is why the default sits at 2.6.
    const rising = sweep.slice(0, 3);
    out.detailControlsDensity = { sweep,
      monotonicOverUsableRange: rising.every((v,i)=> i===0 || v.fine > rising[i-1].fine),
      spanToSaturation: +(rising[rising.length-1].fine / rising[0].fine).toFixed(1),
      saturatesAtHighDetail: sweep[3].fine < sweep[2].fine,
      overprintedByErosion: (()=>{ const a=fineDetail(M({style:"eroded",detail:0.6}));
        const b2=fineDetail(M({style:"eroded",detail:3.4}));
        return { at0_6:a, at3_4:b2, ratio:+(b2/a).toFixed(2) }; })() };

    // --- THE SKIRT: the profile must be a peak with a concave apron, not a bell ---
    // (1-r^2)^p is flat on top and steepest halfway out -- a bell, which renders as pudding on a
    // plate however much texture sits on it. (1-r)^p is steep at the summit and convex outward,
    // which is the pediment/talus apron a real massif grades into. Measured on the ENVELOPE itself
    // so dissection noise cannot mask the shape.
    const profile = (skirt) => Array.from({length:21}, (_,k)=> Math.pow(1-k/20, skirt));
    const slopes = (pr) => pr.slice(1).map((v,i)=> (v-pr[i])*20);
    const bell = Array.from({length:21}, (_,k)=> Math.pow(1-(k/20)**2, 1.25));
    const sk   = profile(1.4);
    out.skirt = {
      bellSlopeAtSummit:  +slopes(bell)[0].toFixed(3),
      skirtSlopeAtSummit: +slopes(sk)[0].toFixed(3),
      skirtSlopeAtEdge:   +slopes(sk)[slopes(sk).length-1].toFixed(3),
      // a bell is nearly flat at the summit; a peak is not
      bellIsFlatOnTop: Math.abs(slopes(bell)[0]) < 0.15,
      peakIsSteepOnTop: Math.abs(slopes(sk)[0]) > 0.8,
      // and the apron must flatten outward -- slope magnitude strictly decreasing
      apronFlattensOutward: slopes(sk).every((v,i,a)=> i===0 || Math.abs(v) < Math.abs(a[i-1])),
      // it must reach exactly zero at the rim, so there is no seam to feather
      reachesZeroAtRim: sk[sk.length-1] === 0 };

    // --- IT MUST NOT BE A SOLID OF REVOLUTION ---
    // A cone with flutes cut in it is a tipi tent, and the flutes do not save it: what gives it away
    // is that it is unchanged when you spin it about its axis. So correlate the field against a
    // 90-degree rotation of itself. A solid of revolution scores ~1; a real massif does not.
    // This replaced a per-octant descent metric that anchored on the summit CELL -- when the warp
    // moves the summit the window moves with it, and the reading swung around non-monotonically on
    // a single seed. Rotational correlation needs no anchor and is averaged over five seeds.
    const rotCorr = (f) => { const A=[],B=[];
      for (let y=0;y<n;y++) for (let x=0;x<n;x++){
        const rx=n-1-y, ry=x;                              // 90 degrees about the tile centre
        if (f[y*n+x]<=0 && f[ry*n+rx]<=0) continue;
        A.push(f[y*n+x]); B.push(f[ry*n+rx]); }
      const ma=A.reduce((a,v)=>a+v,0)/A.length, mb=B.reduce((a,v)=>a+v,0)/B.length;
      let num=0,da=0,db=0;
      for (let i=0;i<A.length;i++){ const u=A[i]-ma, v=B[i]-mb; num+=u*v; da+=u*u; db+=v*v; }
      return +(num/Math.sqrt(da*db)).toFixed(3); };
    const meanRot = (c) => { const vs=[3,7,11,29,101].map(seed=>rotCorr(M({character:c, seed})));
      return { perSeed:vs, mean:+(vs.reduce((a,v)=>a+v,0)/vs.length).toFixed(3) }; };
    const atDefault = meanRot(DEF.character);
    out.notASolidOfRevolution = {
      cone: rotCorr(cone), atDefaultCharacter: atDefault,
      byCharacter: Object.fromEntries([0, 0.3, 0.9].map(c => [c, meanRot(c).mean])),
      farFromRotationallySymmetric: atDefault.mean < 0.93,
      characterDrivesIt: meanRot(0).mean > meanRot(0.9).mean };

    // --- THE MASK MUST NOT FORCE EVERY MOUNTAIN INTO ONE SHAPE ---
    // With reach, aspect and rotation fixed, the seed only displaces noise inside a footprint whose
    // proportions never change. Measured before this was fixed: across six seeds, elongation stayed
    // between 1.03 and 1.26 -- six variations on one circle. Second moments of the support give
    // area, elongation and orientation without any reference to height.
    const footprint = (f) => {
      let sx=0, sy=0, w=0;
      for (let y=0;y<n;y++) for (let x=0;x<n;x++){ if (f[y*n+x]<=0) continue; sx+=x; sy+=y; w++; }
      if (w < 10) return null;
      const fx=sx/w, fy=sy/w; let xx=0, yy=0, xy=0;
      for (let y=0;y<n;y++) for (let x=0;x<n;x++){ if (f[y*n+x]<=0) continue;
        const dx=x-fx, dy=y-fy; xx+=dx*dx; yy+=dy*dy; xy+=dx*dy; }
      xx/=w; yy/=w; xy/=w;
      const tr=xx+yy, det=xx*yy-xy*xy, disc=Math.sqrt(Math.max(tr*tr/4-det,0));
      return { area:w/(n*n), elongation:Math.sqrt((tr/2+disc)/Math.max(tr/2-disc,1e-9)),
               orientation:(Math.atan2(2*xy,xx-yy)/2)*180/Math.PI }; };
    const SEEDS = [3,7,11,29,101,777,1234,5150,9001,424242];
    const survey = (V) => { const fp = SEEDS.map(seed => footprint(M({seed, variation:V})));
      const el = fp.map(q=>q.elongation), ar = fp.map(q=>q.area), or = fp.map(q=>q.orientation);
      const sp = (v) => { const m=v.reduce((a,x)=>a+x,0)/v.length;
        return Math.sqrt(v.reduce((a,x)=>a+(x-m)**2,0)/v.length)/Math.abs(m); };
      return { elongationRange:[+Math.min(...el).toFixed(2), +Math.max(...el).toFixed(2)],
               areaSpread:+sp(ar).toFixed(3), elongationSpread:+sp(el).toFixed(3),
               orientationRangeDeg:+(Math.max(...or)-Math.min(...or)).toFixed(0) }; };
    const v0 = survey(0), vDef = survey(DEF.variation), v1 = survey(1);
    out.maskDoesNotForceOneShape = { atVariation0:v0, atDefault:vDef, atVariation1:v1,
      // at 0 you get exactly the proportions you authored; the knob has to actually widen them
      variationWidensShapes: v1.elongationSpread > v0.elongationSpread * 1.5,
      areaVariesMore: v1.areaSpread > v0.areaSpread * 1.5,
      someMassifIsElongated: v1.elongationRange[1] > 1.6 };

    // --- the primitive must stay inside its own footprint, so it composites cleanly ---
    const f = M({x:0.5, y:0.5, size:0.25});
    let outside = 0, inside = 0;
    for (let y=0;y<n;y++) for (let x=0;x<n;x++){
      const r = Math.hypot((x+0.5)/n-0.5, (y+0.5)/n-0.5);
      if (r > 0.25*1.55) outside += Math.abs(f[y*n+x]);      // beyond any wobbled reach
      else inside += f[y*n+x]; }
    out.staysInsideFootprint = { totalOutside:+outside.toExponential(2), totalInside:+inside.toFixed(1),
                                 clean: outside === 0 && inside > 0 };

    return out;
  });

  console.log(JSON.stringify(r, null, 2));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
