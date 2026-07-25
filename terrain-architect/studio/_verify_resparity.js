// Resolution independence: the same graph at 192² and 1024² should give the SAME landform
// (the 1024 one just carrying more detail). Compare by downsampling 1024 -> 192.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');

(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    // strip water/snow so we compare pure terrain
    const o = outputNode();
    nodes.filter(n=>n.type==='water'||n.type==='snow').forEach(sm=>{
      const inc=edges.find(e=>e.to===sm.id&&e.slot===0), outs=edges.filter(e=>e.from===sm.id);
      edges=edges.filter(e=>e.from!==sm.id&&e.to!==sm.id);
      if(inc) outs.forEach(x=>edges.push({from:inc.from,to:x.to,slot:x.slot}));
    });
    nodes=nodes.filter(n=>n.type!=='water'&&n.type!=='snow');

    const build = n => { RES=n; buildIndex(); nodes.forEach(x=>{x._dirty=true;x._thumb=null;});
      evalGraph(); return Float32Array.from(outputNode()._field); };
    const norm = f => { let mn=Infinity,mx=-Infinity; for(const v of f){if(v<mn)mn=v;if(v>mx)mx=v;}
      const d=mx-mn||1; return Float32Array.from(f,v=>(v-mn)/d); };
    const down = (f,from,to) => { const o=new Float32Array(to*to),s=from/to;
      for(let y=0;y<to;y++)for(let x=0;x<to;x++){ let acc=0,c=0;
        for(let j=0;j<s;j++)for(let i=0;i<s;i++){acc+=f[((y*s+j)|0)*from+((x*s+i)|0)];c++;}
        o[y*to+x]=acc/c; } return o; };
    // roughness = mean |h - mean(4-neighbours)| : the "spikiness" metric
    const rough = (f,n) => { let sum=0,c=0;
      for(let y=1;y<n-1;y++)for(let x=1;x<n-1;x++){const i=y*n+x;
        sum+=Math.abs(f[i]-(f[i-1]+f[i+1]+f[i-n]+f[i+n])/4);c++;} return sum/c; };
    const compare = (a,bb) => { let se=0,mx=0; for(let i=0;i<a.length;i++){const d=a[i]-bb[i];se+=d*d;if(Math.abs(d)>mx)mx=Math.abs(d);}
      return { rms:+Math.sqrt(se/a.length).toFixed(4), maxAbs:+mx.toFixed(4) }; };

    const out = {};
    for (const scaled of [false, true]) {
      SCALE_RES = scaled;
      const lo = norm(build(192));
      const hi = norm(build(1024));
      const hiDown = norm(down(hi,1024,192));
      // roughness in SLOPE units (x RES) is the resolution-comparable form: per-cell drops shrink
      // as cells get closer, so only slope tells you whether the surface is genuinely spikier.
      out[scaled?'scaled':'unscaled'] = {
        ...compare(lo, hiDown),
        slope192: +(rough(lo,192)*192).toFixed(3),
        slope1024: +(rough(hi,1024)*1024).toFixed(3),
        spikier: +((rough(hi,1024)*1024)/(rough(lo,192)*192)).toFixed(2),
      };
    }
    SCALE_RES = true; RES=192; buildIndex();
    return out;
  });

  for (const [k,v] of Object.entries(r))
    console.log(`${k.padEnd(9)} rms=${v.rms} maxAbs=${v.maxAbs}   slope@192=${v.slope192} slope@1024=${v.slope1024}  -> ${v.spikier}x spikier`);
  console.log('errors', errors.length?JSON.stringify(errors):'none');
  await b.close();
  process.exit(errors.length?1:0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
