// Feature Scale + Transform must change the LATERAL size of features, measured — not just "it ran".
// Metric: mean feature width from zero-crossing spacing of (h - blur(h)) along rows, in cells.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    // mean spacing between sign changes of the high-pass signal = characteristic feature width (cells)
    const featureWidth = f => {
      const n=RES, lo=blurField(f,{radius:2}); let cross=0, samples=0;
      for(let y=2;y<n-2;y+=3){ let prev=0;
        for(let x=0;x<n;x++){ const d=f[y*n+x]-lo[y*n+x]; if(x&&Math.sign(d)!==Math.sign(prev)&&prev!==0)cross++; prev=d; samples++; }}
      return cross? samples/cross : 0;
    };
    const out = { transform:{}, featureScale:{} };

    // --- Transform: exact test on an analytic sine. Magnifying by k must multiply the PERIOD by k. ---
    const n0=RES, CYC=8;
    const sine=new Float32Array(n0*n0);
    for(let y=0;y<n0;y++)for(let x=0;x<n0;x++)sine[y*n0+x]=Math.sin(2*Math.PI*CYC*(x+0.5)/n0);
    const period = f => { const y=(n0/2)|0; let cross=0,prev=f[y*n0];
      for(let x=1;x<n0;x++){const v=f[y*n0+x];if(Math.sign(v)!==Math.sign(prev)&&prev!==0)cross++;prev=v;}
      return cross? (2*n0)/cross : 0; };                 // two zero-crossings per period
    out.base = +period(sine).toFixed(2);
    for (const k of [1,2,4]) {
      const t = transformField(sine,{scale:k,aspect:1,angle:0,offX:0,offY:0,edge:'wrap'});
      // ORACLE: magnifying by k must reproduce sin() evaluated at the inverse-mapped coordinate
      let maxErr=0;
      for(let y=1;y<n0-1;y+=7)for(let x=1;x<n0-1;x++){
        const u=(x+0.5)/n0-0.5, ru=u/k+0.5;
        const want=Math.sin(2*Math.PI*CYC*ru);
        maxErr=Math.max(maxErr,Math.abs(t[y*n0+x]-want));
      }
      out.transform[k+'x'] = { period:+period(t).toFixed(1), maxErrVsOracle:+maxErr.toFixed(4) };
    }

    // --- Feature Scale on erosion: larger k should widen the eroded valleys ---
    const th = nodes.find(n=>n.type==='thermal');
    const base = fbmField(gnoise,{seed:7,freq:4,octaves:6,lac:2,gain:0.5});
    for (const k of [1,3,6]) {
      const t0=performance.now();
      const eroded = atFeatureScale(base,k,f=>thermalErode(f,{talus:0.012,iters:30,rate:0.5}));
      const ms=Math.round(performance.now()-t0);
      // measure the CHANGE the erosion made (that's what has the feature scale)
      const delta=new Float32Array(eroded.length);
      for(let i=0;i<delta.length;i++)delta[i]=eroded[i]-base[i];
      out.featureScale[k+'x'] = { deltaWidth:+featureWidth(delta).toFixed(2), ms };
    }
    return out;
  });

  console.log(`base feature width = ${r.base} cells`);
  console.log('Transform (magnify):');
  for (const [k,v] of Object.entries(r.transform)) console.log(`  scale ${k.padEnd(3)} period=${v.period} cells   max err vs oracle = ${v.maxErrVsOracle}`);
  console.log('Erosion Feature Scale (width of the erosion delta):');
  for (const [k,v] of Object.entries(r.featureScale)) console.log(`  feat ${k.padEnd(3)} width=${v.deltaWidth} cells  ${v.ms}ms`);
  console.log('errors', errors.length?JSON.stringify(errors):'none');
  await b.close();
  process.exit(errors.length?1:0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
