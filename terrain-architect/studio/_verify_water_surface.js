// Water rendering regression: topology stays on the node; global controls own motion/refraction;
// the deferred renderer uses a rasterized fluid-surface depth layer.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL='file://'+path.resolve(__dirname,'index.html');

(async()=>{
  const browser=await chromium.launch({executablePath:EXE,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1280,height:820}});
  const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1900);
  await page.locator('#waterLookBtn').click();await page.waitForTimeout(80);
  await page.screenshot({path:path.resolve(__dirname,'_shot_water_surface_settings.png')});
  const result=await page.evaluate(()=>{
    const waterDef=TYPES.water,keys=waterDef.params.map(x=>x.key),linked=p=>!!p&&gl.getProgramParameter(p,gl.LINK_STATUS);
    // Rendering controls are tested on known liquid water so the independent climate/ice phase does
    // not reduce the refraction sample area.
    const warmEncoded=new Float32Array(RES*RES).fill(encodeTemperatureC(12));
    scene.water.temperatureField=tagTemperatureField(warmEncoded,new Float32Array(RES*RES).fill(12),{lapseRate:6.5});
    refreshWater();
    const frame=(time,strength,refraction)=>{uTime=time;waterLook.strength=strength;waterLook.refraction=refraction;renderGL();gl.finish();
      const p=new Uint8Array(glc.width*glc.height*4);gl.readPixels(0,0,glc.width,glc.height,gl.RGBA,gl.UNSIGNED_BYTE,p);return p;};
    const delta=(a,b)=>{let sum=0,changed=0,n=0;for(let i=0;i<a.length;i+=16){const d=Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2]);sum+=d;changed+=d>2;n++;}return{mean:sum/n,changed};};
    const moving=delta(frame(0,.55,.55),frame(1.5,.55,.55)),still=delta(frame(0,0,.55),frame(1.5,0,.55));
    const refracted=delta(frame(.7,.55,0),frame(.7,.55,1));
    gl.bindFramebuffer(gl.FRAMEBUFFER,gbuf.waterFbo);const mask=new Uint8Array(glc.width*glc.height*4);
    gl.readPixels(0,0,glc.width,glc.height,gl.RGBA,gl.UNSIGNED_BYTE,mask);gl.bindFramebuffer(gl.FRAMEBUFFER,null);
    let surfacePixels=0;for(let i=0;i<mask.length;i+=4)surfacePixels+=mask[i]>127;
    return{nodeKeys:keys,global:{...waterLook},panel:!waterLookPanel.hidden,linked:{waterMask:linked(waterMaskProg),composite:linked(compProg)},
      moving,still,refracted,surfacePixels};
  });
  const forbidden=['pattern','ripple','rippleScale','rippleSpeed'];
  const ok=forbidden.every(k=>!result.nodeKeys.includes(k))&&result.panel&&result.linked.waterMask&&result.linked.composite
    &&result.surfacePixels>100&&result.moving.mean>result.still.mean+.01&&result.still.mean<.01
    &&result.refracted.mean>.01&&result.refracted.changed>20&&!errors.length;
  console.log(JSON.stringify({result,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
