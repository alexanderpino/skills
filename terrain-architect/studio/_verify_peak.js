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
    const M = (o) => TYPES.mountain.eval({form:"peak", style:"eroded", seed:7, x:0.5, y:0.5,
                     size:0.35, angle:25, ridges:2, spurs:7, relief:0.66, ...o});

    // --- the two reference extremes, so the numbers below have a scale ---
    out.reference = { cone: score(cone),
                      ridgedNoise: score(fbmField(gnoise,{seed:7,freq:5,octaves:6,lac:2.1,gain:0.55,ridge:true})) };

    // --- a PEAK has ONE summit. Topographic prominence is the measure that says so. ---
    const peaks = {};
    for (const style of ["basic","eroded","alpine","old","strata"]) peaks[style] = score(M({style}));
    for (const seed of [3,11,29]) peaks["seed"+seed] = score(M({seed}));
    out.peakIsOneSummit = {
      summitCounts: Object.fromEntries(Object.entries(peaks).map(([k,v])=>[k, v.summitsAbove10pct])),
      worstSecondOverFirst: +Math.max(...Object.values(peaks).map(v=>v.secondOverFirst)).toFixed(3),
      allSingleSummit: Object.values(peaks).every(v=>v.summitsAbove10pct === 1),
      allDescendMonotonically: Object.values(peaks).every(v=>v.radial.monotonicDescent),
      // and it must not read as noise: noise scores 100+ summits and a ~0.55 ratio
      farFromNoise: Object.values(peaks).every(v=>v.secondOverFirst < 0.10) };

    // --- a MASSIF is deliberately several summits: the contrast is the point ---
    const massif = score(M({form:"massif"}));
    out.massifIsSeveralSummits = { summits: massif.summitsAbove10pct,
      secondOverFirst: massif.secondOverFirst,
      moreSummitsThanPeak: massif.summitsAbove10pct > peaks.eroded.summitsAbove10pct };

    // --- SPURS: the parameter must actually control the spur count ---
    const azimuth = (f,rad) => { const K=360, prof=[];
      for (let k=0;k<K;k++){ const th=k/K*2*Math.PI;
        const x=Math.round((0.5+Math.cos(th)*rad)*n), y=Math.round((0.5+Math.sin(th)*rad)*n);
        prof.push(f[Math.min(n-1,Math.max(0,y))*n+Math.min(n-1,Math.max(0,x))]); }
      const m=prof.reduce((a,v)=>a+v,0)/K, sd=Math.sqrt(prof.reduce((a,v)=>a+(v-m)**2,0)/K);
      const lo=Math.min(...prof), hi=Math.max(...prof), thr=(hi-lo)*0.15; let maxima=0;
      for (let k=0;k<K;k++){ const c=prof[k]; if (c<=m) continue;
        let isMax=true, drop=0;
        for (let d=1;d<=12;d++){ const a=prof[(k-d+K)%K], b2=prof[(k+d)%K];
          if (a>c||b2>c){isMax=false;break;} drop=Math.max(drop,Math.max(c-a,c-b2)); }
        if (isMax&&drop>thr) maxima++; }
      return { relSD:+(sd/(m||1)).toFixed(3), spurs:maxima }; };
    const counts = [4,7,10,12].map(sp => ({ asked:sp, ...azimuth(M({spurs:sp}), 0.21) }));
    out.spurParameterWorks = { counts,
      monotonic: counts.every((c,i)=> i===0 || c.spurs >= counts[i-1].spurs),
      tracksAsked: counts.every(c => c.spurs >= c.asked),
      // and the spurs must be real relief, not texture -- a smooth cone scores ~0.01
      azimuthalReliefVsCone: { peak: azimuth(M({}), 0.21).relSD, cone: azimuth(cone, 0.21).relSD },
      spursAreRealRelief: azimuth(M({}), 0.21).relSD > 10 * azimuth(cone, 0.21).relSD };
    return out;
  });

  console.log(JSON.stringify(r, null, 2));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
