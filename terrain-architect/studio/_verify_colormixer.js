// Color Mixer regression: ordered 2–15 color layers, per-layer blend/opacity, dynamic ports, height passthrough.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');

(async()=>{
  const browser=await chromium.launch({executablePath:EXE,
    args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:900}});
  const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1100);

  const report=await page.evaluate(()=>{
    const out=outputNode(),src=edges.find(e=>e.to===out.id&&e.slot===0).from;
    const A=makeNode('satmap',360,520);A.params.gradient='Verdant';A.params.source='height';A.params.rough='none';
    const B=makeNode('satmap',360,630);B.params.gradient='Canyon';B.params.source='slope';B.params.rough='none';
    const C=makeNode('satmap',360,740);C.params.gradient='Frost';C.params.source='height';C.params.rough='none';
    const M=makeNode('colormixer',650,590);
    M.params.layers[1]={opacity:.42,blend:'screen'};M.params.layers[2]={opacity:.31,blend:'multiply'};
    edges=edges.filter(e=>!(e.to===out.id&&e.slot===0));
    edges.push({from:src,to:A.id,slot:0},{from:src,to:B.id,slot:0},{from:src,to:C.id,slot:0},
      {from:A.id,to:M.id,slot:0},{from:B.id,to:M.id,slot:1},{from:C.id,to:M.id,slot:2},{from:M.id,to:out.id,slot:0});
    nodes.forEach(n=>n._dirty=true);evalGraph();
    const a=resolveColor(A.id,RES),b=resolveColor(B.id,RES),c=resolveColor(C.id,RES),mixed=resolveColor(M.id,RES);
    const ab=blendFields(a,b,{_mask:null,params:{opacity:.42,blend:'screen'}},RES);
    const expected=blendFields(ab,c,{_mask:null,params:{opacity:.31,blend:'multiply'}},RES);
    let err=0;for(let i=0;i<mixed.length;i++)err=Math.max(err,Math.abs(mixed[i]-expected[i]));
    select(M);return{mixer:M.id,heightPass:M._field===A._field,maxError:err,finite:mixed.every(Number.isFinite),
      inputs:[...nodeInputs(M)],modes:M.params.layers.map(x=>x.blend)};
  });

  // Exercise the real dynamic-input UI up to Gaea's documented 15-layer ceiling.
  for(let i=3;i<15;i++)await page.locator('#pBody > button').click();
  const dynamic=await page.evaluate(()=>{
    const m=selected,add=document.querySelector('#pBody > button');
    return{count:nodeInputs(m).length,configs:m.params.layers.length,disabled:add.disabled,nodeHeight:nodeH(m),
      ports:nodeInputs(m).map((_,i)=>portPos(m,'in',i).y)};
  });
  await page.locator('#pBody').evaluate(el=>el.scrollTop=0);await page.screenshot({path:path.resolve(__dirname,'_shot_colormixer.png')});

  const ok=report.heightPass&&report.maxError<1e-7&&report.finite&&report.inputs.length===3
    &&report.modes.join('|')==='normal|screen|multiply'&&dynamic.count===15&&dynamic.configs===15
    &&dynamic.disabled&&dynamic.nodeHeight>200&&new Set(dynamic.ports.map(v=>v.toFixed(3))).size===15&&!errors.length;
  console.log(JSON.stringify({report,dynamic,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
