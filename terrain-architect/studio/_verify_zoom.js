// Deep viewport navigation: cursor-focused dolly, movable pivot, surface lock, adaptive near plane,
// right-drag pan, and deterministic frame reset.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');

(async () => {
  const browser = await chromium.launch({executablePath:EXE,
    args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox']});
  const page = await browser.newPage({viewport:{width:1440,height:900}});
  const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1200);
  await page.locator('#layoutBtn').click();await page.waitForTimeout(120);
  await page.evaluate(()=>{RES=512;buildIndex();nodes.forEach(n=>{n._dirty=true;n._thumb=null;});evalGraph();});
  await page.waitForTimeout(250);
  const r=await page.locator('#viewport').boundingBox();

  // Right-drag pans the inspection pivot before zooming.
  await page.mouse.move(r.x+r.width*.5,r.y+r.height*.5);
  await page.mouse.down({button:'right'});
  await page.mouse.move(r.x+r.width*.58,r.y+r.height*.46,{steps:5});
  await page.mouse.up({button:'right'});
  const afterPan=await page.evaluate(()=>({dist:cam.dist,target:[...cam.target]}));

  // Dolly repeatedly toward an off-centre cursor. The target should move under that cursor and
  // settle onto the sampled terrain surface while distance reaches the deep-inspection clamp.
  await page.mouse.move(r.x+r.width*.72,r.y+r.height*.43);
  for(let i=0;i<24;i++)await page.mouse.wheel(0,-240);
  await page.waitForTimeout(180);
  const deep=await page.evaluate(()=>{
    const eye=cameraEye(),d=Math.hypot(eye[0]-cam.target[0],eye[1]-cam.target[1],eye[2]-cam.target[2]);
    return{dist:cam.dist,near:cameraNear(),target:[...cam.target],eyeDistance:d,
      surface:surfaceHeight(cam.target[0],cam.target[2]),glError:gl.getError()};
  });
  await page.screenshot({path:path.resolve(__dirname,'_shot_zoom_deep.png')});

  await page.locator('#frameBtn').click();await page.waitForTimeout(80);
  const framed=await page.evaluate(()=>({dist:cam.dist,target:[...cam.target],az:cam.az,el:cam.el,planView}));
  const panMoved=Math.hypot(afterPan.target[0],afterPan.target[1]-.05,afterPan.target[2])>.01;
  const focusMoved=Math.hypot(deep.target[0]-afterPan.target[0],deep.target[2]-afterPan.target[2])>.01;
  const ok=panMoved&&focusMoved&&deep.dist<=.01201&&deep.near<.0003
    && Math.abs(deep.eyeDistance-deep.dist)<1e-6&&Math.abs(deep.target[1]-deep.surface)<1e-5&&deep.glError===0
    && framed.dist===2.6&&framed.target.every((v,i)=>Math.abs(v-[0,.05,0][i])<1e-9)&&!framed.planView&&!errors.length;
  console.log(JSON.stringify({afterPan,deep,framed,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
