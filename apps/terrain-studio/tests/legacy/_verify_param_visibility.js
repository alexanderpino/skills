// Mode-aware property regression: inactive settings must be hidden without losing their values.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox'] });
  const page = await browser.newPage({ viewport:{ width:1440, height:900 } });
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1400);
  const report=await page.evaluate(()=>{
    // BUILD THE DOCUMENT THIS FILE MEASURES. 31f5688 demoted the 18-node showcase to L0 - the
    // 7-node bedrock document (perlin, ridged, blend, d_height, heightmask, levels, output) - which
    // carries no water, hydraulic or thermal node. Inherited, this file died on
    // nodes.find(n=>n.type==='water').params.level: measured TypeError "Cannot read properties of
    // undefined (reading 'params')", exit 2.
    //
    // showcaseGraph() ONLY - no evalGraph(), no #buildBtn. This oracle measures the PROPERTY PANEL:
    // buildProps() renders #pBody rows straight out of nd.params (it touches _dem, and only for
    // import nodes) and the screenshot is of #props, not #viewport. Nothing here reads a
    // heightfield, a colour field, or curHgt/curFilled/curAccum, so there is no stale-cache hazard
    // to close - and evaluating the showcase (hydraulic + thermal + snow) would cost seconds to
    // prove nothing. Measured after the change: 0 console/page errors, so the unevaluated
    // _field:null nodes do not upset the panel.
    nodes.length=0;edges.length=0;uid=1;selected=null;selectedEdge=null;
    showcaseGraph();
    const keys=()=>[...document.querySelectorAll('#pBody .field[data-param-key]')].map(e=>e.dataset.paramKey);
    // gradient/mountain/transform/sculpt have never been in the opening document - makeNode is the
    // intended path for those. water/hydraulic/thermal DO come from the document, so their absence
    // is a named SETUP FAILURE rather than a freshly-defaulted stand-in that would quietly pass.
    const need=t=>{const n=nodes.find(x=>x.type===t);
      if(!n)throw new Error('SETUP FAILURE: no '+t+' node after showcaseGraph()');return n;};
    const show=(type,changes={})=>{const nd=nodes.find(n=>n.type===type)||makeNode(type,0,0);Object.assign(nd.params,changes);selected=nd;buildProps();return keys();};
    need('hydraulic');need('thermal');
    const water=need('water'),savedLevel=water.params.level;
    if(!Number.isFinite(savedLevel))throw new Error('SETUP FAILURE: water node has no numeric level param to preserve');
    const hydro=show('water',{mode:'hydro'}),sea=show('water',{mode:'sea'});
    const gpu=show('hydraulic',{engine:'auto'}),cpu=show('hydraulic',{engine:'droplets'});
    const cell=show('thermal',{realScale:'off'}),real=show('thermal',{realScale:'on'});
    const linear=show('gradient',{kind:'lin'}),radial=show('gradient',{kind:'rad'});
    const peak=show('mountain',{form:'peak'}),massif=show('mountain',{form:'massif'});
    const exact=show('transform',{mode:'auto'}),raster=show('transform',{mode:'raster'});
    const smooth=show('sculpt',{mode:'smooth'}),raise=show('sculpt',{mode:'raise'}),flatten=show('sculpt',{mode:'flatten'});
    show('water',{mode:'hydro'});
    return {hydro,sea,gpu,cpu,cell,real,linear,radial,peak,massif,exact,raster,smooth,raise,flatten,
      levelPreserved:water.params.level===savedLevel,
      tabs:[...document.querySelectorAll('#pBody .seg.tabs')].length};
  });
  await page.evaluate(()=>{const w=nodes.find(n=>n.type==='water');w.params.mode='hydro';selected=w;buildProps();});
  await page.locator('#props').screenshot({path:path.resolve(__dirname,'_shot_water_hydrology_props.png')});
  const has=(a,...v)=>v.every(k=>a.includes(k)),lacks=(a,...v)=>v.every(k=>!a.includes(k));
  const ok=has(report.hydro,'mode','lakes','lakeMin','flow','riverDepth','shoreSmooth','foam')
    && lacks(report.hydro,'level')
    && has(report.sea,'mode','level','shoreSmooth','foam')&&lacks(report.sea,'lakes','lakeMin','flow','riverDepth')
    && has(report.gpu,'pipeIters')&&lacks(report.gpu,'droplets','seed')
    && has(report.cpu,'droplets','seed')&&lacks(report.cpu,'pipeIters')
    && has(report.cell,'talus')&&lacks(report.cell,'repose')&&has(report.real,'repose')&&lacks(report.real,'talus')
    && has(report.linear,'angle')&&lacks(report.radial,'angle')
    && has(report.peak,'shape')&&lacks(report.peak,'ridges')&&has(report.massif,'ridges')&&lacks(report.massif,'shape')
    && lacks(report.exact,'edge')&&has(report.raster,'edge')
    && has(report.smooth,'radius')&&lacks(report.smooth,'amount','target')
    && has(report.raise,'amount')&&lacks(report.raise,'radius','target')
    && has(report.flatten,'target')&&lacks(report.flatten,'radius','amount')
    && report.levelPreserved&&report.tabs>0&&!errors.length;
  console.log(JSON.stringify({report,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
