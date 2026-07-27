// Artist mask workflow: vector strokes remain stable across resolution and Sculpt merges only through the mask.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox'] });
  const page = await browser.newPage({ viewport:{ width:1440, height:900 } });
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1400);
  const report=await page.evaluate(()=>{
    const oldRes=RES,oldTarget=TARGET_RES;XF=null;
    const strokes=[
      {mode:'add',width:.08,hardness:.65,opacity:1,points:[[.08,.5],[.28,.45],[.5,.53],[.72,.42],[.92,.5]]},
      {mode:'erase',width:.025,hardness:.8,opacity:.65,points:[[.47,.48],[.55,.49]]}
    ];
    const stats=res=>{RES=res;TARGET_RES=res;buildIndex();const m=drawMaskField({strokes});let sum=0,count=0,cx=0,cy=0;
      for(let y=0;y<res;y++)for(let x=0;x<res;x++){const v=m[y*res+x];sum+=v;if(v>.5){count++;cx+=x*v;cy+=y*v;}}
      return{coverage:sum/(res*res),binary:count/(res*res),cx:cx/(sum||1)/(res-1),cy:cy/(sum||1)/(res-1)};};
    const low=stats(64),high=stats(192);
    RES=128;TARGET_RES=128;buildIndex();
    const mask=drawMaskField({strokes:[strokes[0]]}),base=new Float32Array(RES*RES);
    for(let y=0;y<RES;y++)for(let x=0;x<RES;x++)base[y*RES+x]=.25+.45*x/(RES-1)+.025*((x+y)%2);
    const lowered=maskApply(base,sculptField(base,{mode:'lower',amount:.06,strength:.8}),mask);
    const smoothed=maskApply(base,sculptField(base,{mode:'smooth',radius:4,strength:1}),mask);
    let insideDelta=0,insideN=0,outsideDelta=0,outsideN=0,roughBase=0,roughSmooth=0;
    for(let y=1;y<RES-1;y++)for(let x=1;x<RES-1;x++){const i=y*RES+x;
      if(mask[i]>.8){insideDelta+=base[i]-lowered[i];insideN++;
        roughBase+=Math.abs(base[i]-base[i-1]);roughSmooth+=Math.abs(smoothed[i]-smoothed[i-1]);}
      if(mask[i]===0){outsideDelta=Math.max(outsideDelta,Math.abs(base[i]-lowered[i]),Math.abs(base[i]-smoothed[i]));outsideN++;}
    }
    RES=oldRes;TARGET_RES=oldTarget;buildIndex();
    const nd=makeNode('drawmask',120,120);nd.params.strokes=strokes;nd._reference=curField;
    const nonExactReference=makeNode('blur',0,0);edges.push({from:nonExactReference.id,to:nd.id,slot:0});
    const referenceIndependent=exactChain(nd.id,new Set());
    edges=edges.filter(e=>e.to!==nd.id||e.slot!==0);nodes.splice(nodes.indexOf(nonExactReference),1);
    selected=nd;buildProps();openDrawEditor(nd);
    return{low,high,insideLower:insideDelta/(insideN||1),outsideDelta,outsideN,
      roughnessRatio:roughSmooth/(roughBase||1),exact:EXACT_TYPES.has('drawmask'),
      toolbox:!!document.querySelector('.node-tool-item[data-type="drawmask"]')&&!!document.querySelector('.node-tool-item[data-type="sculpt"]'),
      referenceIndependent,
      editor:!document.querySelector('#drawEditor').hidden,strokes:nd.params.strokes.length};
  });
  await page.waitForTimeout(250);
  await page.locator('#drawEditor').screenshot({path:path.resolve(__dirname,'_shot_draw_mask_editor.png')});
  const box=await page.locator('#drawCanvas').boundingBox();
  await page.mouse.move(box.x+box.width*.22,box.y+box.height*.24);
  await page.mouse.down();await page.mouse.move(box.x+box.width*.38,box.y+box.height*.30,{steps:8});await page.mouse.up();
  const afterPaint=await page.evaluate(()=>drawTarget.params.strokes.length);
  await page.locator('#drawUndoStroke').click();
  const afterUndo=await page.evaluate(()=>drawTarget.params.strokes.length);
  const ok=Math.abs(report.low.coverage-report.high.coverage)<.004
    && Math.abs(report.low.cx-report.high.cx)<.01&&Math.abs(report.low.cy-report.high.cy)<.01
    && report.insideLower>.035&&report.outsideDelta<1e-7&&report.outsideN>100
    && report.roughnessRatio<.75&&report.exact&&report.referenceIndependent&&report.toolbox&&report.editor&&report.strokes===2
    && afterPaint===3&&afterUndo===2&&!errors.length;
  console.log(JSON.stringify({report,interaction:{afterPaint,afterUndo},errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
