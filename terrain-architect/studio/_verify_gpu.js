// GPU-vs-CPU parity: the CPU kernels are the reference; the GPU fast path must match them.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');

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

  if (!r.gpuAvailable) { console.log('GPU NOT AVAILABLE'); }
  else {
    for (const k of ['perlin','ridged','thermal'])
      console.log(`${k.padEnd(8)} maxAbs=${r[k].maxAbs} meanAbs=${r[k].meanAbs}   cpu=${r[k].cpuMs}ms gpu=${r[k].gpuMs}ms`);
    for (const [n,v] of Object.entries(r.scale))
      console.log(`fbm@${n}^2  gpu=${v.gpuMs}ms cpu=${v.cpuMs===null?'(skipped)':v.cpuMs+'ms'}`);
  }
  console.log('errors', errors.length?JSON.stringify(errors):'none');
  await b.close();
  process.exit(errors.length?1:0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
