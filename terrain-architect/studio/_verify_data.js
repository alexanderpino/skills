// Verify the Data Map nodes (Gaea "Derive" channels) evaluate, and that a SatMap can bind to each.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');

(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = [];
  p.on('console', m => { if (m.type()==='error') errors.push('C:'+m.text()); });
  p.on('pageerror', e => errors.push('P:'+e.message));
  await p.goto(URL, { waitUntil: 'load' });
  await p.waitForTimeout(1600);

  // Evaluate every data node off the current terrain and report its stats.
  const stats = await p.evaluate(() => {
    const out = outputNode(); const src = edges.find(e=>e.to===out.id&&e.slot===0).from;
    const h = nodeById(src)._field;
    const types = Object.keys(TYPES).filter(k=>TYPES[k].cat==='data');
    const res = {};
    for (const t of types) {
      const def = TYPES[t]; const prm = {}; def.params.forEach(x=>prm[x.key]=x.def);
      const t0 = performance.now();
      const f = def.eval(prm, [h], {});
      const ms = performance.now()-t0;
      let mn=Infinity,mx=-Infinity,sum=0;
      for (let i=0;i<f.length;i++){ const v=f[i]; if(v<mn)mn=v; if(v>mx)mx=v; sum+=v; }
      res[t] = { name: def.name, min:+mn.toFixed(3), max:+mx.toFixed(3), mean:+(sum/f.length).toFixed(3),
                 varied: (mx-mn)>0.05, finite: Number.isFinite(sum), ms: Math.round(ms) };
    }
    return res;
  });
  for (const [k,v] of Object.entries(stats))
    console.log(`${v.name.padEnd(11)} min=${v.min} max=${v.max} mean=${v.mean} varied=${v.varied} finite=${v.finite} ${v.ms}ms`);

  // Bind a SatMap to the Flow data map (Driver port) and render.
  const bound = await p.evaluate(() => {
    const out = outputNode(); const ie = edges.find(e=>e.to===out.id&&e.slot===0); const src = ie.from;
    const F  = makeNode('d_flow', 120, 540);
    const SM = makeNode('satmap', 380, 560); SM.params.source='auto'; SM.params.gradient='Frost';
    edges = edges.filter(e=>!(e.to===out.id&&e.slot===0));
    edges.push({from:src,to:F.id,slot:0});
    edges.push({from:src,to:SM.id,slot:0});     // In  = height (passthrough)
    edges.push({from:F.id,to:SM.id,slot:1});    // Driver = FLOW  -> colour follows the rivers
    edges.push({from:SM.id,to:out.id,slot:0});
    cam.az=0.85; cam.el=0.55; cam.dist=2.4; sun.az=0.9; sun.el=0.6;
    nodes.forEach(n=>n._dirty=true); evalGraph();
    return { satComposite, driverBound: !!scene.satmap, source: scene.satmap && scene.satmap.source };
  });
  await p.waitForTimeout(700);
  await p.screenshot({ path: path.resolve(__dirname, '_shot_flowdriven.png') });
  console.log('SatMap bound to Flow:', JSON.stringify(bound));

  console.log('ERRORS', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
