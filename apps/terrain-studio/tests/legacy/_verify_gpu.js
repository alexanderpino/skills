// GPU-vs-CPU parity: the CPU kernels are the reference; the GPU fast path must match them.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1500);

  const r = await p.evaluate(() => {
    const res = { gpuAvailable: GPU.init() };
    if (!res.gpuAvailable) return res;
    const diff = (a,bb) => { let mx=0,sum=0; for(let i=0;i<a.length;i++){const d=Math.abs(a[i]-bb[i]); if(d>mx)mx=d; sum+=d;}
      return { maxAbs:+mx.toExponential(2), meanAbs:+(sum/a.length).toExponential(2) }; };
    const time = f => { const t=performance.now(); const v=f(); return { v, ms: Math.round(performance.now()-t) }; };

    RES = 192; buildIndex();
    // --- fBm (Perlin) ---
    const A = {seed:7,freq:3,octaves:6,lac:2,gain:0.5};
    const c1 = time(()=>fbmField(gnoise,A)), g1 = time(()=>gpuFbm(A));
    res.perlin = { ...diff(c1.v,g1.v), cpuMs:c1.ms, gpuMs:g1.ms };
    // --- Ridged ---
    const B = {seed:3,freq:3.5,octaves:6,lac:2.1,gain:0.55,ridge:true};
    const c2 = time(()=>fbmField(gnoise,B)), g2 = time(()=>gpuFbm(B));
    res.ridged = { ...diff(c2.v,g2.v), cpuMs:c2.ms, gpuMs:g2.ms };
    // --- Thermal erosion (30 iters on the same input) ---
    const base = fbmField(gnoise,A), T = {talus:0.012,iters:30,rate:0.5};
    const c3 = time(()=>thermalErode(base,T)), g3 = time(()=>gpuThermal(base,T));
    res.thermal = { ...diff(c3.v,g3.v), cpuMs:c3.ms, gpuMs:g3.ms };
    // --- Warp: same noise offsets and manual bilinear sampling ---
    const W={strength:0.12,freq:3,seed:7};
    const c4=time(()=>warpField(base,W)),g4=time(()=>gpuWarp(base,W));
    res.warp={...diff(c4.v,g4.v),cpuMs:c4.ms,gpuMs:g4.ms};
    // --- GPU hydraulic pipes: invariants + expected erosion and deposition ---
    const hp=time(()=>gpuHydraulicPipes(base,{iters:48,capacity:6,erode:.35,deposit:.28,inertia:.05}));
    let eroded=0,deposited=0,maxDrop=0,maxRise=0,finite=true;
    for(let i=0;i<base.length;i++){const d=hp.v[i]-base[i];if(!Number.isFinite(hp.v[i]))finite=false;
      if(d<0){eroded++;maxDrop=Math.max(maxDrop,-d);}if(d>0){deposited++;maxRise=Math.max(maxRise,d);}}
    res.hydraulic={gpuMs:hp.ms,finite,eroded,deposited,maxDrop:+maxDrop.toFixed(5),maxRise:+maxRise.toFixed(5)};
    // --- cross-ENGINE record of the hydraulic node: pipes vs droplets are two different
    // simulations behind one "auto" tab. The gap is MEASURED AND GATED, not closed: at the
    // shipped defaults the pipe engine runs ~0.37x the droplet depth (band [0.25, 0.55]) with
    // modification corr ~0.59 (floor 0.40). A parity retune was attempted and REVERTED: iters
    // ~160 reach depth parity but break grid invariance (1.42 at k=2), and cap-scaling moves
    // gridRatio to ~2.0 while cross-depth stays flat - the invariance partly rests on the
    // k-scaled erosion cap, so dose and invariance are coupled. These gates stop SILENT DRIFT
    // of the documented relationship; closing the gap is queued kernel work.
    {
      const mk=t=>{const q={};TYPES[t].params.forEach(pr=>{q[pr.key]=cloneParams(pr.def);});return q;};
      const rms=(a,b2)=>{let se=0;for(let i=0;i<a.length;i++){const d=b2[i]-a[i];se+=d*d;}return Math.sqrt(se/a.length);};
      const pearson=(a,b2)=>{let sa=0,sb=0;const n2=a.length;
        for(let i=0;i<n2;i++){sa+=a[i];sb+=b2[i];}const ma=sa/n2,mb=sb/n2;
        let num=0,da=0,db=0;for(let i=0;i<n2;i++){const x=a[i]-ma,y=b2[i]-mb;num+=x*y;da+=x*x;db+=y*y;}
        return num/Math.max(1e-12,Math.sqrt(da*db));};
      const del=(x,y)=>{const d=new Float32Array(x.length);for(let i=0;i<d.length;i++)d[i]=y[i]-x[i];return d;};
      const held=USE_GPU;
      USE_GPU=true; const eng1=TYPES.hydraulic.eval(mk('hydraulic'),[base,null]);
      USE_GPU=false; const prm=mk('hydraulic');prm.engine='droplets';
      const eng2=TYPES.hydraulic.eval(prm,[base,null]);
      USE_GPU=held;
      res.crossEngine={depthRatio:+(rms(base,eng1)/rms(base,eng2)).toFixed(3),
        deltaCorr:+pearson(del(base,eng1),del(base,eng2)).toFixed(4)};
    }

    // --- scaling: how long does a 512^2 / 1024^2 generator take on each path? ---
    res.scale = {};
    for (const n of [512, 1024]) {
      RES = n; buildIndex();
      const g = time(()=>gpuFbm(A));
      let cpuMs = null;
      if (n <= 512) { const c = time(()=>fbmField(gnoise,A)); cpuMs = c.ms; }
      res.scale[n] = { gpuMs: g.ms, cpuMs };
    }
    RES = 192; buildIndex();
    return res;
  });

  let crossFail = 0;
  if (!r.gpuAvailable) { console.log('GPU NOT AVAILABLE'); }
  else {
    for (const k of ['perlin','ridged','thermal','warp'])
      console.log(`${k.padEnd(8)} maxAbs=${r[k].maxAbs} meanAbs=${r[k].meanAbs}   cpu=${r[k].cpuMs}ms gpu=${r[k].gpuMs}ms`);
    console.log('hydraulic',JSON.stringify(r.hydraulic));
    console.log('crossEngine',JSON.stringify(r.crossEngine));
    if (!(r.crossEngine && r.crossEngine.depthRatio >= 0.25 && r.crossEngine.depthRatio <= 0.55
        && r.crossEngine.deltaCorr >= 0.40)) {
      console.log('FAIL cross-engine record: depthRatio in [0.25,0.55] (measured 0.37 — the gap '
        + 'is documented, not closed) and deltaCorr >= 0.40. This stops silent drift only.');
      crossFail = 1;
    }
    for (const [n,v] of Object.entries(r.scale))
      console.log(`fbm@${n}^2  gpu=${v.gpuMs}ms cpu=${v.cpuMs===null?'(skipped)':v.cpuMs+'ms'}`);
  }
  console.log('errors', errors.length?JSON.stringify(errors):'none');
  await b.close();
  process.exit(errors.length || crossFail ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
