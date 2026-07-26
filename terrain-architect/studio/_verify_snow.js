// Snow regression: Amount is coverage, not merely an altitude tint. At 1.0 the rendered
// terrain becomes a snowy world while 0.0 remains unchanged.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');

(async()=>{
  const browser=await chromium.launch({executablePath:EXE,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1280,height:820}});
  const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1900);
  await page.evaluate(()=>{const n=nodes.find(x=>x.type==='snow');select(n);previewMode='selected';refreshPreview();shadeMode=2;});
  const setSnow=async amount=>{
    await page.evaluate(v=>{const n=nodes.find(x=>x.type==='snow');n.params.amount=v;markParamDirty(n);evalGraph();},amount);
    await page.waitForTimeout(180);
    return page.evaluate(()=>{renderGL();gl.finish();const p=new Uint8Array(glc.width*glc.height*4);gl.readPixels(0,0,glc.width,glc.height,gl.RGBA,gl.UNSIGNED_BYTE,p);
      let snowy=0,bright=0;for(let i=0;i<p.length;i+=4){if(p[i]>195&&p[i+1]>200&&p[i+2]>205)snowy++;if((p[i]+p[i+1]+p[i+2])/3>185)bright++;}
      return{snowy,bright,pixels:p.length/4};});
  };
  const none=await setSnow(0),full=await setSnow(1);
  await page.locator('#viewport').screenshot({path:path.resolve(__dirname,'_shot_snow_world.png')});
  const contract=await page.evaluate(()=>({description:TYPES.snow.desc,amount:nodes.find(x=>x.type==='snow').params.amount}));
  const ok=full.snowy>none.snowy+full.pixels*.08&&full.bright>none.bright+full.pixels*.08
    &&contract.description.includes('snowy world')&&contract.amount===1&&!errors.length;
  console.log(JSON.stringify({none,full,contract,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
