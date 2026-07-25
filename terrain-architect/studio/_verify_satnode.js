// Headless test: SatMap colour graph — explicit branch+Blend, chain stacking, 2D biome, fallback.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = [];
  page.on('console', m => { if (m.type()==='error') errors.push('CONSOLE:'+m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR:'+e.message));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(1500);

  console.log('fallback:', JSON.stringify(await page.evaluate(() => ({ satComposite }))));

  // EXPLICIT BRANCH + BLEND: src -> SatMapA(height,Temperate) and src -> SatMapB(slope,Canyon);
  //   A -> Blend.A, B -> Blend.B, src -> Blend.Mask; Blend -> Output.
  const branch = await page.evaluate(() => {
    const out=outputNode(); const ie=edges.find(e=>e.to===out.id&&e.slot===0); const src=ie?ie.from:null;
    const A=makeNode('satmap',120,520); A.params.source='height'; A.params.gradient='Temperate';
    const B=makeNode('satmap',120,640); B.params.source='slope';  B.params.gradient='Canyon';
    const BL=makeNode('satmapblend',380,560); BL.params.blend='normal'; BL.params.opacity=1;
    edges=edges.filter(e=>!(e.to===out.id&&e.slot===0));
    if(src!=null){ edges.push({from:src,to:A.id,slot:0}); edges.push({from:src,to:B.id,slot:0}); edges.push({from:src,to:BL.id,slot:2}); }
    edges.push({from:A.id,to:BL.id,slot:0});
    edges.push({from:B.id,to:BL.id,slot:1});
    edges.push({from:BL.id,to:out.id,slot:0});
    nodes.forEach(n=>n._dirty=true); evalGraph();
    // confirm the blend really merges A and B (differs from A-only)
    const cBL=resolveColor(BL.id,RES), cA=resolveColor(A.id,RES);
    let diff=0; for(let i=0;i<cA.length;i+=997){ if(Math.abs(cA[i]-cBL[i])>0.02) diff++; }
    return { satComposite, blendLen:cBL.length, differsFromA: diff };
  });
  console.log('branch+blend:', JSON.stringify(branch));
  await page.screenshot({ path: path.resolve(__dirname, '_shot_satblend.png') });

  // CHAIN STACK still works: reduce to src -> SatMapA -> SatMapB -> Output (multiply, masked).
  const chain = await page.evaluate(() => {
    const out=outputNode();
    const A=nodes.find(n=>n.type==='satmap'&&n.params.gradient==='Temperate');
    const B=nodes.find(n=>n.type==='satmap'&&n.params.gradient==='Canyon');
    const BL=nodes.find(n=>n.type==='satmapblend');
    const src=edges.find(e=>e.to===A.id&&e.slot===0).from;
    edges=edges.filter(e=>e.from!==BL.id&&e.to!==BL.id); nodes=nodes.filter(n=>n.id!==BL.id);
    edges=edges.filter(e=>e.to!==out.id&&!(e.to===B.id));
    B.params.blend='multiply'; B.params.opacity=0.8;
    edges.push({from:A.id,to:B.id,slot:0});
    edges.push({from:src,to:B.id,slot:2});         // mask the top layer by height
    edges.push({from:B.id,to:out.id,slot:0});
    nodes.forEach(n=>n._dirty=true); evalGraph();
    return { satComposite };
  });
  console.log('chain stack:', JSON.stringify(chain));

  // 2D biome on the base.
  const biome = await page.evaluate(() => {
    const A=nodes.find(n=>n.type==='satmap'&&n.params.gradient==='Temperate');
    A.params.mode='2d'; A.params.gradient='Verdant'; A.params.gradientB='Canyon';
    nodes.forEach(n=>n._dirty=true); evalGraph();
    return { satComposite, mode:A.params.mode };
  });
  console.log('2D biome:', JSON.stringify(biome));

  // remove all colour nodes -> fallback.
  const removed = await page.evaluate(() => {
    const out=outputNode();
    nodes.filter(n=>n.type==='satmap'||n.type==='satmapblend').forEach(sm=>{ edges=edges.filter(e=>e.from!==sm.id&&e.to!==sm.id); });
    nodes=nodes.filter(n=>n.type!=='satmap'&&n.type!=='satmapblend');
    if(!edges.some(e=>e.to===out.id)) edges.push({from:nodes.find(n=>n.type!=='output').id,to:out.id,slot:0});
    nodes.forEach(n=>n._dirty=true); evalGraph();
    return { satComposite };
  });
  console.log('after remove:', JSON.stringify(removed));

  console.log('ERRORS', errors.length ? JSON.stringify(errors) : 'none');
  await browser.close();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
