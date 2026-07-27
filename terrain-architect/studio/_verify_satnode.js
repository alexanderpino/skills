// Headless test: default SatMap chain, explicit biome branch+Color Blend, chain stacking, fallback.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = [];
  page.on('console', m => { if (m.type()==='error') errors.push('CONSOLE:'+m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR:'+e.message));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(1500);

  console.log('default colour graph:', JSON.stringify(await page.evaluate(() => ({ satComposite }))));

  // EXPLICIT BIOME BRANCH + BLEND: src -> SatMapA(height,Temperate) and src -> SatMapB(slope,Canyon);
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
    window.__satTest={A:A.id,B:B.id,BL:BL.id};
    nodes.forEach(n=>n._dirty=true); evalGraph();
    // confirm the blend really merges A and B (differs from A-only)
    const cBL=resolveColor(BL.id,RES), cA=resolveColor(A.id,RES);
    let diff=0; for(let i=0;i<cA.length;i+=997){ if(Math.abs(cA[i]-cBL[i])>0.02) diff++; }
    return { satComposite, blendLen:cBL.length, differsFromA: diff };
  });
  console.log('biome branch+blend:', JSON.stringify(branch));
  await page.screenshot({ path: path.resolve(__dirname, '_shot_satblend.png') });

  // CHAIN STACK still works for a simple masked overlay: src -> SatMapA -> SatMapB(masked) -> Output.
  const chain = await page.evaluate(() => {
    const out=outputNode();
    const A=nodeById(window.__satTest.A),B=nodeById(window.__satTest.B),BL=nodeById(window.__satTest.BL);
    const src=edges.find(e=>e.to===A.id&&e.slot===0).from;
    edges=edges.filter(e=>e.from!==BL.id&&e.to!==BL.id); nodes=nodes.filter(n=>n.id!==BL.id);
    edges=edges.filter(e=>e.to!==out.id&&!(e.to===B.id));
    edges.push({from:A.id,to:B.id,slot:0});
    edges.push({from:src,to:B.id,slot:2});         // mask the top layer by height
    edges.push({from:B.id,to:out.id,slot:0});
    nodes.forEach(n=>n._dirty=true); evalGraph();
    return { satComposite };
  });
  console.log('chain stack:', JSON.stringify(chain));

  const model = await page.evaluate(() => ({
    satmapParams:TYPES.satmap.params.map(p=>p.key),
    blendModes:TYPES.satmapblend.params.find(p=>p.key==='blend').opts.map(x=>x[0])
  }));
  console.log('single-gradient model:', JSON.stringify(model));

  // remove all colour nodes -> fallback.
  const removed = await page.evaluate(() => {
    const out=outputNode();
    const colorTypes=new Set(['satmap','colorerosion','weathering','satmapblend']);
    nodes.filter(n=>colorTypes.has(n.type)).forEach(sm=>{ edges=edges.filter(e=>e.from!==sm.id&&e.to!==sm.id); });
    nodes=nodes.filter(n=>!colorTypes.has(n.type));
    if(!edges.some(e=>e.to===out.id)) edges.push({from:nodes.find(n=>n.type==='thermal').id,to:out.id,slot:0});
    nodes.forEach(n=>n._dirty=true); evalGraph();
    return { satComposite };
  });
  console.log('after remove:', JSON.stringify(removed));

  console.log('ERRORS', errors.length ? JSON.stringify(errors) : 'none');
  await browser.close();
  const valid=branch.satComposite===1&&branch.differsFromA>0&&chain.satComposite===1&&removed.satComposite===0
    &&model.satmapParams.includes('gradient')&&!model.satmapParams.includes('gradientB')&&!model.satmapParams.includes('mode')
    &&model.satmapParams.includes('enhance')&&model.satmapParams.includes('hue')&&!model.satmapParams.includes('blend')
    &&model.blendModes.includes('normal')&&model.blendModes.includes('multiply')&&model.blendModes.includes('difference')
    &&model.blendModes.includes('hypotenuse');
  process.exit(errors.length||!valid ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
