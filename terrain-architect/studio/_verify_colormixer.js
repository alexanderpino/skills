// Color Mixer regression: ordered 2–15 color layers, biome masks + edge blend, dynamic ports, height passthrough.
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
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1100);

  const report=await page.evaluate(()=>{
    const out=outputNode(),H=makeNode('perlin',120,620);H.params.seed=818;H.params.freq=3;
    const A=makeNode('satmap',360,520);A.params.gradient='Verdant';A.params.source='height';A.params.rough='none';
    const B=makeNode('satmap',360,630);B.params.gradient='Canyon';B.params.source='slope';B.params.rough='none';
    const C=makeNode('satmap',360,740);C.params.gradient='Frost';C.params.source='height';C.params.rough='none';
    const M=makeNode('colormixer',650,590);
    M.params.layers[1]={opacity:.42,blend:'screen'};M.params.layers[2]={opacity:.31,blend:'multiply'};
    edges=edges.filter(e=>!(e.to===out.id&&e.slot===0));
    edges.push({from:H.id,to:A.id,slot:0},{from:H.id,to:B.id,slot:0},{from:H.id,to:C.id,slot:0},
      {from:A.id,to:M.id,slot:0},{from:B.id,to:M.id,slot:1},{from:C.id,to:M.id,slot:2},{from:M.id,to:out.id,slot:0});
    nodes.forEach(n=>n._dirty=true);evalGraph();
    const a=resolveColor(A.id,RES),b=resolveColor(B.id,RES),c=resolveColor(C.id,RES),mixed=resolveColor(M.id,RES);
    const ab=blendFields(a,b,{_mask:null,params:{opacity:.42,blend:'screen'}},RES);
    const expected=blendFields(ab,c,{_mask:null,params:{opacity:.31,blend:'multiply'}},RES);
    let err=0;for(let i=0;i<mixed.length;i++)err=Math.max(err,Math.abs(mixed[i]-expected[i]));

    // A standalone masked SatMap is a biome layer: black must preserve Layer 1, white must apply
    // Layer 2, and an optional world-space edge blend may affect only the boundary band.
    const BM=makeNode('colormixer',900,590);
    BM.params.layers[1]={opacity:1,blend:'normal',edgeBlend:0};
    edges.push({from:A.id,to:BM.id,slot:0},{from:B.id,to:BM.id,slot:1});
    const hardMask=new Float32Array(RES*RES),mid=RES>>1;
    for(let y=0;y<RES;y++)for(let x=mid;x<RES;x++)hardMask[y*RES+x]=1;
    B._mask=hardMask;
    const hard=resolveColor(BM.id,RES);
    const maeRegion=(actual,want,x0,x1)=>{let sum=0,count=0;
      for(let y=0;y<RES;y++)for(let x=x0;x<x1;x++){const i=(y*RES+x)*3;
        sum+=Math.abs(actual[i]-want[i])+Math.abs(actual[i+1]-want[i+1])+Math.abs(actual[i+2]-want[i+2]);count+=3;}
      return sum/Math.max(1,count);};
    const hardOutside=maeRegion(hard,a,0,mid),hardInside=maeRegion(hard,b,mid,RES);
    BM.params.layers[1].edgeBlend=cellSizeM()*4;
    const soft=resolveColor(BM.id,RES),farOutside=maeRegion(soft,a,0,mid-10),farInside=maeRegion(soft,b,mid+10,RES);
    let transition=0;
    for(let y=0;y<RES;y++)for(let x=mid-8;x<mid+8;x++){const i=(y*RES+x)*3;
      const da=Math.abs(soft[i]-a[i])+Math.abs(soft[i+1]-a[i+1])+Math.abs(soft[i+2]-a[i+2]);
      const db=Math.abs(soft[i]-b[i])+Math.abs(soft[i+1]-b[i+1])+Math.abs(soft[i+2]-b[i+2]);
      if(da>1e-5&&db>1e-5)transition++;}
    select(M);return{mixer:M.id,resolution:RES,heightPass:M._field===A._field,maxError:err,finite:mixed.every(Number.isFinite),
      inputs:[...nodeInputs(M)],modes:M.params.layers.map(x=>x.blend),
      biome:{hardOutside,hardInside,farOutside,farInside,transition}};
  });

  // Exercise the real dynamic-input UI up to Gaea's documented 15-layer ceiling.
  for(let i=3;i<15;i++)await page.locator('#pBody > button').click();
  const dynamic=await page.evaluate(()=>{
    const m=selected,add=document.querySelector('#pBody > button');
    const oldZoom=view.z;view.z=.35;
    const portHits=nodeInputs(m).map((_,i)=>{
      const p=portPos(m,'in',i),hit=portAt(p.x,p.y);return hit&&hit.node===m.id?hit.slot:null;});
    view.z=oldZoom;
    return{count:nodeInputs(m).length,configs:m.params.layers.length,disabled:add.disabled,nodeHeight:nodeH(m),
      ports:nodeInputs(m).map((_,i)=>portPos(m,'in',i).y),portHits};
  });
  await page.locator('#pBody').evaluate(el=>el.scrollTop=0);await page.screenshot({path:path.resolve(__dirname,'_shot_colormixer.png')});

  const ok=report.heightPass&&report.maxError<1e-7&&report.finite&&report.inputs.length===3
    &&report.modes.join('|')==='normal|screen|multiply'&&dynamic.count===15&&dynamic.configs===15
    &&report.biome.hardOutside<1e-8&&report.biome.hardInside<1e-8
    &&report.biome.farOutside<1e-8&&report.biome.farInside<1e-8&&report.biome.transition>report.resolution
    &&dynamic.disabled&&dynamic.nodeHeight>200&&new Set(dynamic.ports.map(v=>v.toFixed(3))).size===15
    &&dynamic.portHits.every((slot,i)=>slot===i)&&!errors.length;
  console.log(JSON.stringify({report,dynamic,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
