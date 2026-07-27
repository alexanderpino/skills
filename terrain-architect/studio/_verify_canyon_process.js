// Canyon process regression: internal Style hierarchy, conservative Erosion 2, subtle HydroFix,
// starter graph wiring, toolbox/menu exposure, and rendered hero/plan evidence.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));

(async()=>{
  const browser=await chromium.launch({executablePath:EXE,args:['--use-gl=angle','--use-angle=swiftshader',
    '--enable-unsafe-swiftshader','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:900}});
  const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1400);
  const result=await page.evaluate(()=>{
    RES=192;TARGET_RES=192;USE_GPU=true;
    const params=type=>Object.fromEntries(TYPES[type].params.map(p=>[p.key,cloneParams(p.def)]));
    const cp={...params("canyon"),style:"eroded",surrounding:.72,detailWarp:.56,tributaries:0};
    const ep={...params("erosion2"),duration:.28,downcut:.38,erosionScale:.50,shape:.20,
      shapeSharp:.34,shapeDetail:.68};
    const hp={...params("hydrofix"),fix:.48,downcut:.22};
    const finite=f=>f.length===RES*RES&&Array.from(f).every(Number.isFinite);
    const mad=(a,b)=>{let s=0;for(let i=0;i<a.length;i++)s+=Math.abs(a[i]-b[i]);return s/a.length;};
    const corr=(a,b)=>{
      let aa=0,bb=0;for(let i=0;i<a.length;i++){aa+=a[i];bb+=b[i];}aa/=a.length;bb/=b.length;
      let ab=0,a2=0,b2=0;for(let i=0;i<a.length;i++){const x=a[i]-aa,y=b[i]-bb;ab+=x*y;a2+=x*x;b2+=y*y;}
      return ab/Math.sqrt(Math.max(a2*b2,1e-20));
    };
    const relief=f=>{const [mn,mx]=fieldRange(f);return mx-mn;};
    const pits=f=>{
      let count=0;for(let y=1;y<RES-1;y++)for(let x=1;x<RES-1;x++){
        const i=y*RES+x,v=f[i];let lower=false;
        for(let yy=-1;yy<=1;yy++)for(let xx=-1;xx<=1;xx++)if((xx||yy)&&f[i+yy*RES+xx]<v-1e-7)lower=true;
        if(!lower)count++;
      }return count;
    };
    const raw=canyonField(cp),eroded=erosion2Field(raw,ep),repeat=erosion2Field(raw,ep);
    const low=erosion2Field(raw,{...ep,duration:.04,downcut:.08});
    const scaled=erosion2Field(raw,{...ep,erosionScale:.92});
    const otherSeed=erosion2Field(raw,{...ep,seed:29});
    const fixed=hydroFixField(eroded,hp);
    const rr=relief(raw),metrics={
      rawFinite:finite(raw),erodedFinite:finite(eroded),fixedFinite:finite(fixed),
      rawRelief:rr,erodedRelief:relief(eroded),fixedRelief:relief(fixed),
      erosionMAD:mad(raw,eroded)/rr,lowMAD:mad(raw,low)/rr,scaleMAD:mad(eroded,scaled)/rr,
      seedMAD:mad(eroded,otherSeed)/rr,deterministic:mad(eroded,repeat),
      macroCorrelation:corr(raw,eroded),fixMAD:mad(eroded,fixed)/rr,
      pitsBefore:pits(eroded),pitsAfter:pits(fixed)};
    historyReady=false;newTerrainDocument(false,"canyon");historyReady=true;
    const chain=nodes.map(n=>n.type),wiring=edges.map(e=>[nodeById(e.from).type,nodeById(e.to).type,e.slot]);
    const ui={
      chain,wiring,selected:selected&&selected.type,
      erosionTool:!!document.querySelector('.node-tool-item[data-type="erosion2"]'),
      hydroTool:!!document.querySelector('.node-tool-item[data-type="hydrofix"]'),
      desktopTemplate:!!document.querySelector('#fileMenu [data-editor-command="new-canyon"]'),
      compactTemplate:!!document.querySelector('#compactFile [data-editor-command="new-canyon"]'),
      commandTemplate:!!document.querySelector('#commandList [data-action="new-canyon"]'),
      groups:[...document.querySelectorAll(".param-group-title")].map(x=>x.textContent.trim())};
    shadeMode=1;syncDisplayState();frameHero();
    return{metrics,ui};
  });
  await page.waitForTimeout(1000);await page.screenshot({path:path.resolve(__dirname,'_shot_canyon_process.png')});
  await page.evaluate(()=>{if(!planView)togglePlanView();});
  await page.waitForTimeout(250);await page.screenshot({path:path.resolve(__dirname,'_shot_canyon_process_plan.png')});
  const m=result.metrics,u=result.ui;
  const ok=m.rawFinite&&m.erodedFinite&&m.fixedFinite&&m.rawRelief>.5&&m.erodedRelief>.4
    &&m.erosionMAD>.0002&&m.erosionMAD<.20&&m.erosionMAD>m.lowMAD
    &&m.scaleMAD>.00005&&m.seedMAD>.000001&&m.deterministic===0&&m.macroCorrelation>.78
    &&m.fixMAD>0&&m.fixMAD<.025&&m.pitsAfter<=m.pitsBefore
    &&JSON.stringify(u.chain)===JSON.stringify(["canyon","erosion2","hydrofix","output"])
    &&JSON.stringify(u.wiring)===JSON.stringify([
      ["canyon","erosion2",0],["erosion2","hydrofix",0],["hydrofix","output",0]])
    &&u.selected==="erosion2"&&u.erosionTool&&u.hydroTool&&u.desktopTemplate&&u.compactTemplate
    &&u.commandTemplate&&JSON.stringify(u.groups)===JSON.stringify(["General","Sediment discharge","Shape"])
    &&!errors.length;
  console.log(JSON.stringify({result,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error("FATAL",e);process.exit(2);});
