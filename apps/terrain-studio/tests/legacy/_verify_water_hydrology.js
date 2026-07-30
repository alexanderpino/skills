// Hydrology controls must visibly affect the generated water surface, independently of sea level.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox'] });
  const page = await browser.newPage({ viewport:{width:1280,height:800} });
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1700);

  // BUILD THE DOCUMENT THIS FILE MEASURES. 31f5688 demoted the opening document to L0 - seven
  // bedrock nodes with NO water node. Two things then broke at once:
  //   1. curFilled/curAccum are only computed by updateViewport when scene.water.mode !== 'sea',
  //      and with no water node scene.water is null, so they stayed null. refreshWater() then
  //      threw "Cannot read properties of null (reading '0')" at src/legacy.js:5447 (filled[i]).
  //   2. even had it run, curHgt would be L0's un-eroded blend, not the hydraulic+thermal surface
  //      whose basins and channels these thresholds (lakes.wet>20, deep.mean>shallow.mean*1.8,
  //      seaWet>5% of the field) were calibrated against.
  // showcaseGraph() restores the 18-node graph, and its water node ships mode:'hydro', which is
  // exactly what makes updateViewport run priorityFloodFill/d8Accumulation.
  //
  // evalGraph() suffices; no #buildBtn build is needed. This oracle never renders - it reads
  // curWater/curHgt only - and evalGraph() calls finishGraphEvaluation -> updateViewport
  // synchronously. Measured against the progressive build on this document: sum(curHgt[0..63]) =
  // 46.13122934103012 and 86580 wet vertices of 262144 by BOTH routes (7.9 s vs 15.8 s wall).
  await page.evaluate(()=>{
    nodes.length=0;edges.length=0;uid=1;selected=null;selectedEdge=null;
    showcaseGraph();evalGraph();
  });

  const report=await page.evaluate(()=>{
    const wn=nodes.find(n=>n.type==='water');
    if(!wn)throw new Error('SETUP FAILURE: no water node after showcaseGraph()');
    if(!scene.water)throw new Error('SETUP FAILURE: scene.water null after evalGraph() - water node not on the Output chain');
    if(scene.water.mode==='sea')throw new Error('SETUP FAILURE: showcase water is in sea mode, so updateViewport never built curFilled/curAccum');
    if(!curHgt||!curWater)throw new Error('SETUP FAILURE: curHgt/curWater not populated by evalGraph()');
    const measure=p=>{scene.water={mode:'hydro',lakes:'off',lakeMin:.001,flow:.5,riverDepth:.7,level:.58,shoreSmooth:1,foam:.2,...p};
      refreshWater();let wet=0,sum=0,max=0;for(let i=0;i<curWater.length;i++){const d=curWater[i]-curHgt[i];if(d>1e-7){wet++;sum+=d;max=Math.max(max,d);}}
      return{wet,mean:wet?sum/wet:0,max};};
    const dry=measure({lakes:'off',riverDepth:0,flow:1});
    const lakes=measure({lakes:'on',lakeMin:.0001,riverDepth:0});
    const filteredLakes=measure({lakes:'on',lakeMin:.02,riverDepth:0});
    const sparse=measure({lakes:'off',riverDepth:1,flow:.1});
    const dense=measure({lakes:'off',riverDepth:1,flow:.9});
    const shallow=measure({lakes:'off',riverDepth:.2,flow:.65});
    const deep=measure({lakes:'off',riverDepth:1,flow:.65});
    scene.water={mode:'sea',level:.58,shoreSmooth:1,foam:.2};refreshWater();
    let seaWet=0;for(let i=0;i<curWater.length;i++)seaWet+=curWater[i]-curHgt[i]>1e-7;
    return{dry,lakes,filteredLakes,sparse,dense,shallow,deep,seaWet,total:curWater.length};
  });
  const ok=report.dry.wet===0
    && report.lakes.wet>report.filteredLakes.wet&&report.lakes.wet>20
    && report.dense.wet>report.sparse.wet*1.15
    && report.deep.mean>report.shallow.mean*1.8
    && report.seaWet>report.total*.05&&!errors.length;
  console.log(JSON.stringify({report,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
