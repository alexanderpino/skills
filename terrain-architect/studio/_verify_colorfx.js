// Color graph regression: SatMap -> Color Erosion -> Weathering are independent, composable nodes.
// Checks height passthrough, deterministic pigment transport, sediment/mask control, weathering,
// neutral settings, post grading, blend modes/opacity, branch blending, and finite [0,1] color output.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));

(async()=>{
  const browser=await chromium.launch({executablePath:EXE,
    args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:900}});
  const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1200);

  const report=await page.evaluate(()=>{
    const out=outputNode(),defaultChain=[];let walk=out.id;
    for(let k=0;k<20;k++){const e=edges.find(x=>x.to===walk&&x.slot===0);if(!e)break;
      const n=nodeById(e.from);if(!n)break;defaultChain.push(n.type);walk=n.id;}
    const defaultCE=nodes.find(n=>n.type==='colorerosion'),defaultSed=defaultCE&&inputEdge(defaultCE.id,1);
    const defaultSetup={chain:defaultChain,sedimentType:defaultSed&&TYPES[nodeById(defaultSed.from).type].name,
      water:({...nodes.find(n=>n.type==='water').params}),surface:({...waterLook})};
    const old=edges.find(e=>e.to===out.id&&e.slot===0),src=old.from;
    const sat=makeNode('satmap',430,520);sat.params.gradient='Terracotta';sat.params.source='height';sat.params.rough='med';
    const dep=makeNode('d_deposits',430,680);dep.params.radius=4;
    const ce=makeNode('colorerosion',670,520);
    const we=makeNode('weathering',900,520);
    const cb=makeNode('satmapblend',1110,650);cb.params.opacity=.5;
    edges=edges.filter(e=>!(e.to===out.id&&e.slot===0));
    edges.push({from:src,to:sat.id,slot:0},{from:src,to:dep.id,slot:0},{from:sat.id,to:ce.id,slot:0},
      {from:dep.id,to:ce.id,slot:1},{from:ce.id,to:we.id,slot:0},
      {from:sat.id,to:cb.id,slot:0},{from:we.id,to:cb.id,slot:1},{from:cb.id,to:out.id,slot:0});
    nodes.forEach(n=>n._dirty=true);evalGraph();
    const A=resolveColor(sat.id,RES),C=resolveColor(ce.id,RES),W=resolveColor(we.id,RES);
    const mae=(a,b)=>{let s=0;for(let i=0;i<a.length;i++)s+=Math.abs(a[i]-b[i]);return s/a.length;};
    const finite=a=>a.every(v=>Number.isFinite(v)&&v>=0&&v<=1);
    const deterministic=mae(C,resolveColor(ce.id,RES))===0;
    const heightPass=ce._field===sat._field&&we._field===ce._field;
    ce.params.blendMode='multiply';const Cmultiply=resolveColor(ce.id,RES);ce.params.blendMode='normal';
    const opacity=we.params.opacity;we.params.opacity=0;const Wzero=resolveColor(we.id,RES);we.params.opacity=opacity;
    we.params.blendMode='screen';const Wscreen=resolveColor(we.id,RES);we.params.blendMode='normal';
    const B=resolveColor(cb.id,RES);

    const density=ce.params.density;ce.params.density=0;
    const neutralErode=colorErodeField(A,ce._height,{...ce.params,_sediment:ce._sediment},ce._mask,RES);ce.params.density=density;
    const zeroMask=new Float32Array(RES*RES);
    const maskedErode=colorErodeField(A,ce._height,{...ce.params,_sediment:ce._sediment},zeroMask,RES);

    const neutralWeather=weatherColorField(C,we._height,{...we.params,amount:0,dirt:0,hue:0,saturation:0,lightness:0},we._mask,RES);
    const inverse=weatherColorField(C,we._height,{...we.params,amount:.7,dirt:.25,inverse:'on'},we._mask,RES);
    const normal=weatherColorField(C,we._height,{...we.params,amount:.7,dirt:.25,inverse:'off'},we._mask,RES);
    const graded=weatherColorField(C,we._height,{...we.params,hue:.2,saturation:.25,lightness:.12},we._mask,RES);

    // Explicit sediment input should concentrate more change where that field is strong.
    let hi=0,lo=0,hn=0,ln=0;const sm=normalize(ce._sediment);
    for(let i=0;i<RES*RES;i++){const d=(Math.abs(A[i*3]-C[i*3])+Math.abs(A[i*3+1]-C[i*3+1])+Math.abs(A[i*3+2]-C[i*3+2]))/3;
      if(sm[i]>.65){hi+=d;hn++;}else if(sm[i]<.25){lo+=d;ln++;}}
    return{defaultSetup,types:[sat.type,ce.type,we.type],blendName:TYPES[cb.type].name,heightPass,deterministic,finite:finite(C)&&finite(W)&&finite(B),
      erosionDelta:mae(A,C),weatherDelta:mae(C,W),neutralErode:mae(A,neutralErode),
      maskedErode:mae(A,maskedErode),neutralWeather:mae(C,neutralWeather),
      inverseDelta:mae(normal,inverse),gradeDelta:mae(W,graded),
      compositing:{erosionModeDelta:mae(C,Cmultiply),weatherZeroOpacity:mae(C,Wzero),
        weatherModeDelta:mae(W,Wscreen),branchFromA:mae(A,B),branchFromB:mae(W,B)},
      sedimentChange:{high:hi/Math.max(1,hn),low:lo/Math.max(1,ln),highN:hn,lowN:ln}};
  });
  await page.locator('#layoutBtn').click();await page.locator('#shadeSel').evaluate(el=>{
    el.value='2';el.dispatchEvent(new Event('change',{bubbles:true}));});
  await page.evaluate(()=>{view={x:-250,y:-380,z:.85};selected=nodes.find(n=>n.type==='weathering');buildProps();drawGraph();});
  await page.waitForTimeout(180);
  await page.screenshot({path:path.resolve(__dirname,'_shot_colorfx_albedo.png')});
  const ok=report.defaultSetup.chain.slice(0,7).join('|')==='snow|water|weathering|colorerosion|satmap|thermal|hydraulic'
    &&report.defaultSetup.sedimentType==='Deposits'&&report.defaultSetup.surface.strength>.01
    &&report.defaultSetup.surface.scale>0&&report.defaultSetup.surface.speed>0
    &&report.types.join('|')==='satmap|colorerosion|weathering'&&report.blendName==='Color Blend'
    &&report.heightPass&&report.deterministic&&report.finite
    &&report.erosionDelta>.0005&&report.weatherDelta>.0001&&report.neutralErode<1e-8&&report.maskedErode<1e-8
    &&report.neutralWeather<1e-8&&report.inverseDelta>.0001&&report.gradeDelta>.005
    &&report.compositing.erosionModeDelta>.0001&&report.compositing.weatherZeroOpacity<1e-8
    &&report.compositing.weatherModeDelta>.0001&&report.compositing.branchFromA>.0001&&report.compositing.branchFromB>.0001
    &&report.sedimentChange.high>report.sedimentChange.low&&!errors.length;
  console.log(JSON.stringify({report,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
