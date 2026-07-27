// Progressive build HUD regression: real dirty-node counts, intermediate progress,
// active-node naming, elapsed clock, completion, and automatic dismissal.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');

(async()=>{
  const browser=await chromium.launch({executablePath:EXE,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:900}});
  const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1200);
  const initial=await page.evaluate(()=>{
    AUTO=false;RES=192;TARGET_RES=192;historyReady=false;nodes=[];edges=[];uid=1;selected=null;selectedEdge=null;
    const src=makeNode('perlin',40,80);let prev=src;
    for(let i=0;i<6;i++){const nd=makeNode('blur',220+i*150,80);edges.push({from:prev.id,to:nd.id,slot:0});prev=nd;}
    const out=makeNode('output',1160,80);edges.push({from:prev.id,to:out.id,slot:0});historyReady=true;
    const realBlur=TYPES.blur.eval;
    TYPES.blur.eval=(...args)=>{const start=performance.now();while(performance.now()-start<42){}return realBlur(...args);};
    nodes.forEach(n=>n._dirty=true);document.querySelector('#buildBtn').click();
    return{
      hidden:document.querySelector('#buildHud').hidden,
      busy:document.querySelector('#buildBtn').getAttribute('aria-busy'),
      now:+document.querySelector('#buildTicks').getAttribute('aria-valuenow'),
      tickCount:document.querySelector('#buildTicks').children.length,
      clock:document.querySelector('#buildElapsed').textContent
    };
  });
  await page.waitForFunction(()=>{
    const value=+document.querySelector('#buildTicks').getAttribute('aria-valuenow');
    return value>0&&value<100;
  },{timeout:5000});
  const intermediate=await page.evaluate(()=>({
    hidden:document.querySelector('#buildHud').hidden,
    busy:document.querySelector('#buildBtn').getAttribute('aria-busy'),
    now:+document.querySelector('#buildTicks').getAttribute('aria-valuenow'),
    active:document.querySelector('#buildNode').textContent,
    done:document.querySelectorAll('#buildTicks i.done').length,
    clock:document.querySelector('#buildElapsed').textContent,
    status:document.querySelector('#statMsg').textContent
  }));
  await page.screenshot({path:path.resolve(__dirname,'_shot_build_progress.png')});
  await page.waitForFunction(()=>document.querySelector('#buildTicks').getAttribute('aria-valuenow')==='100',{timeout:5000});
  const complete=await page.evaluate(()=>({
    now:+document.querySelector('#buildTicks').getAttribute('aria-valuenow'),
    active:document.querySelector('#buildNode').textContent,
    busy:document.querySelector('#buildBtn').hasAttribute('aria-busy'),
    eval:document.querySelector('#statTime').textContent,
    status:document.querySelector('#statMsg').textContent
  }));
  await page.waitForTimeout(800);
  const dismissed=await page.$eval('#buildHud',el=>el.hidden);
  const ok=!initial.hidden&&initial.busy==='true'&&initial.now===0&&initial.tickCount===20&&/^\d\d:\d\d$/.test(initial.clock)
    &&!intermediate.hidden&&intermediate.busy==='true'&&intermediate.now>0&&intermediate.now<100
    &&intermediate.done>0&&intermediate.active.length>0&&/^\d\d:\d\d$/.test(intermediate.clock)
    &&complete.now===100&&complete.active==='Complete'&&!complete.busy&&/ms$/.test(complete.eval)
    &&/Graph evaluated/.test(complete.status)&&dismissed&&!errors.length;
  console.log(JSON.stringify({initial,intermediate,complete,dismissed,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
