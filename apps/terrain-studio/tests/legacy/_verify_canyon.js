// Canyon primitive regression: process-based control response, deterministic output, node UI, and
// rendered style evidence. Network topology is tested in _verify_canyon_evolution.js.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

(async()=>{
  const browser=await chromium.launch({executablePath:EXE,args:['--use-gl=angle','--use-angle=swiftshader',
    '--enable-unsafe-swiftshader','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:900}});
  const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1200);
  const result=await page.evaluate(()=>{
    RES=128;TARGET_RES=128;USE_GPU=true;CANYON_EVOLUTION_CACHE.clear();
    const defaults=Object.fromEntries(TYPES.canyon.params.map(p=>[p.key,cloneParams(p.def)]));
    const stats=f=>{const a=Array.from(f).sort((x,y)=>x-y),mn=a[0],mx=a[a.length-1],d=mx-mn||1;
      return{min:mn,max:mx,median:a[(a.length*.5)|0],
        deep:a.filter(v=>v<mn+d*.22).length/a.length,incised:a.filter(v=>v<mn+d*.72).length/a.length};};
    const mad=(a,b)=>{let s=0;for(let i=0;i<a.length;i++)s+=Math.abs(a[i]-b[i]);return s/a.length;};
    const cpu=canyonFieldCPU(defaults),cpu2=canyonFieldCPU(defaults);
    const lowDepth=canyonFieldCPU({...defaults,depth:.2}),highDepth=canyonFieldCPU({...defaults,depth:1.2});
    const lowSlot=canyonFieldCPU({...defaults,slot:0}),highSlot=canyonFieldCPU({...defaults,slot:1});
    const lowValley=canyonFieldCPU({...defaults,valley:0}),highValley=canyonFieldCPU({...defaults,valley:1});
    const styleFields=["classic","eroded","eroded2","strata","both"].map(style=>canyonFieldCPU({...defaults,style}));
    const stylePair=[];for(let a=0;a<styleFields.length;a++)for(let b=a+1;b<styleFields.length;b++)
      stylePair.push(mad(styleFields[a],styleFields[b]));
    const straight=canyonFieldCPU({...defaults,structural:0}),warped=canyonFieldCPU({...defaults,structural:1});
    const sparse=canyonEvolutionState({...defaults,tributaries:0}),dense=canyonEvolutionState({...defaults,tributaries:7});
    const active=s=>Array.from(s.channelHeadIndex).filter(v=>v>=.68).length;
    const branched=canyonFieldCPU({...defaults,tributaries:4}),beds=canyonBeds(defaults);
    const thickness=beds.map((b,i)=>b[0]-(i?beds[i-1][0]:0)),tm=thickness.reduce((s,v)=>s+v,0)/thickness.length;
    const thicknessCV=Math.sqrt(thickness.reduce((s,v)=>s+(v-tm)**2,0)/thickness.length)/tm;
    const control={
      depthRelief:(stats(highDepth).max-stats(highDepth).min)-(stats(lowDepth).max-stats(lowDepth).min),
      slotResponse:Math.abs(stats(highSlot).deep-stats(lowSlot).deep),
      valleyResponse:Math.abs(stats(highValley).incised-stats(lowValley).incised),
      defaultStyle:defaults.style,stylePairMin:Math.min(...stylePair),stylePairMax:Math.max(...stylePair),
      warpMAD:mad(straight,warped),branchMAD:mad(cpu,branched),sparseActive:active(sparse),denseActive:active(dense),
      bedThicknessCV:thicknessCV,bedHardnessRange:Math.max(...beds.map(b=>b[1]))-Math.min(...beds.map(b=>b[1])),
      deterministic:mad(cpu,cpu2),exactTransform:EXACT_TYPES.has("canyon")};
    historyReady=false;nodes=[];edges=[];uid=1;selected=null;selectedEdge=null;undoStack=[];redoStack=[];
    const canyon=makeNode("canyon",80,100),out=makeNode("output",300,100);canyon.params=defaults;
    edges.push({from:canyon.id,to:out.id,slot:0});historyReady=true;previewMode="output";select(canyon);
    evalGraph();shadeMode=1;syncDisplayState();frameHero();
    return{cpuStats:stats(cpu),control,nodeCount:nodes.length,nodeType:canyon.type,
      toolbox:!!document.querySelector('.node-tool-item[data-type="canyon"]'),
      groups:[...document.querySelectorAll(".param-group-title")].map(x=>x.textContent),
      labels:[...document.querySelectorAll("#pBody .field label")].map(x=>x.textContent.trim())};
  });
  await page.waitForTimeout(250);await page.screenshot({path:path.resolve(__dirname,'_shot_canyon.png')});
  await page.evaluate(()=>{if(!planView)togglePlanView();});
  await page.waitForTimeout(180);await page.screenshot({path:path.resolve(__dirname,'_shot_canyon_plan.png')});
  await page.evaluate(()=>{const c=nodes.find(n=>n.type==="canyon");c.params.tributaries=4;
    markDirtyFrom(c.id);select(c);buildProps();evalGraph();});
  await page.waitForTimeout(180);await page.screenshot({path:path.resolve(__dirname,'_shot_canyon_branches.png')});
  await page.evaluate(()=>{if(planView)togglePlanView();frameHero();});
  for(const style of ["classic","eroded","eroded2","strata","both"]){
    await page.evaluate(style=>{const c=nodes.find(n=>n.type==="canyon");c.params.style=style;
      c.params.tributaries=0;c.params.alternate="on";markDirtyFrom(c.id);select(c);buildProps();evalGraph();},style);
    await page.waitForTimeout(100);await page.screenshot({path:path.resolve(__dirname,`_shot_canyon_${style}.png`)});
  }
  const s=result.cpuStats,c=result.control;
  const ok=s.max-s.min>.55&&s.median>s.min+(s.max-s.min)*.62&&s.deep>.002&&s.deep<.25
    &&c.depthRelief>.45&&c.slotResponse>.0005&&c.valleyResponse>.03&&c.defaultStyle==="classic"
    &&c.stylePairMin>.002&&c.stylePairMax>.01&&c.warpMAD>.015&&c.branchMAD>.004
    &&c.denseActive>c.sparseActive&&c.bedThicknessCV>.15&&c.bedHardnessRange>.35
    &&c.deterministic===0&&!c.exactTransform&&result.nodeCount===2&&result.nodeType==="canyon"
    &&result.toolbox&&JSON.stringify(result.groups)===JSON.stringify(["Structure","Formation"])
    &&["Style","Scale","Slot","Valley","Surrounding","Depth","Structural warp","Tributary density",
      "Seed","Detail warp","Alternate style"].every(x=>result.labels.includes(x))&&!errors.length;
  console.log(JSON.stringify({result,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error("FATAL",e);process.exit(2);});
