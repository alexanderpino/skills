// End-to-end: build + render the default graph at 1024^2 on the GPU fast path.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');

(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1600, height: 900 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  // full-width viewport, neutral inspection framing
  await p.evaluate(() => {
    document.querySelector('#graphwrap').style.display='none';
    document.querySelector('#props').style.display='none';
    document.querySelector('#main').style.gridTemplate='1fr / 1fr';
    document.querySelector('#viewport').style.gridArea='1 / 1';
    document.querySelector('#status').style.display='none';
  });

  const r = await p.evaluate(() => {
    const out = {}; out.gpu = GPU.init();
    // drop water (its priority-flood is the CPU-only stage) for a clean high-res terrain build
    const o = outputNode();
    nodes.filter(n=>n.type==='water'||n.type==='snow').forEach(sm=>{
      const inc=edges.find(e=>e.to===sm.id&&e.slot===0), outs=edges.filter(e=>e.from===sm.id);
      edges=edges.filter(e=>e.from!==sm.id&&e.to!==sm.id);
      if(inc) outs.forEach(x=>edges.push({from:inc.from,to:x.to,slot:x.slot}));
    });
    nodes=nodes.filter(n=>n.type!=='water'&&n.type!=='snow');
    const th=nodes.find(n=>n.type==='thermal'); if(th){th.params.iters=40;}

    for (const n of [256, 1024]) {
      RES=n; buildIndex(); nodes.forEach(x=>{x._dirty=true;x._thumb=null;});
      const t=performance.now(); evalGraph(); out['build'+n]=Math.round(performance.now()-t);
    }
    out.cells = RES*RES; out.tris = buffers.count/3;
    satName='Terracotta'; buildSatLUT('Terracotta');
    cam.az=0.9; cam.el=0.34; cam.dist=2.0; sun.az=1.1; sun.el=0.36;
    return out;
  });
  await p.waitForTimeout(3000);
  await p.screenshot({ path: path.resolve(__dirname, '_shot_1024.png') });
  console.log(JSON.stringify(r), 'errors', errors.length?JSON.stringify(errors):'none');
  await b.close();
  process.exit(errors.length?1:0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
