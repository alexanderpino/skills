// Simplex regression: first-class node/toolbox integration, deterministic CPU field,
// distinct spectrum from Perlin, exact placement support, and GPU parity.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(URL, { waitUntil: 'load' }); await page.waitForTimeout(1800);
  const result = await page.evaluate(() => {
    const oldRes=RES,oldTarget=TARGET_RES,oldGpu=USE_GPU;RES=128;TARGET_RES=128;buildIndex();USE_GPU=false;
    const p={seed:2468,freq:3.2,octaves:6,lac:2.05,gain:.51};
    const a=fbmField(snoise,p),b=fbmField(snoise,p),seeded=fbmField(snoise,{...p,seed:p.seed+1});
    const perlin=fbmField(gnoise,p);
    const diff=(x,y)=>{let max=0,mean=0;for(let i=0;i<x.length;i++){const d=Math.abs(x[i]-y[i]);max=Math.max(max,d);mean+=d;}return{max,mean:mean/x.length};};
    const corr=(x,y)=>{let ax=0,ay=0;for(let i=0;i<x.length;i++){ax+=x[i];ay+=y[i];}ax/=x.length;ay/=y.length;
      let xy=0,xx=0,yy=0;for(let i=0;i<x.length;i++){const dx=x[i]-ax,dy=y[i]-ay;xy+=dx*dy;xx+=dx*dx;yy+=dy*dy;}return xy/Math.sqrt(xx*yy);};
    const range=fieldRange(a),gpuAvailable=GPU.init();let gpu=null;
    if(gpuAvailable){USE_GPU=true;gpu=diff(a,gpuFbm({...p,simplex:true}));}
    const nd=makeNode("simplex",20,20),exact=EXACT_TYPES.has("simplex")&&exactChain(nd.id,new Set());
    nodes.splice(nodes.indexOf(nd),1);
    RES=oldRes;TARGET_RES=oldTarget;USE_GPU=oldGpu;buildIndex();
    return {nodeName:TYPES.simplex&&TYPES.simplex.name,toolbox:!!document.querySelector('.node-tool-item[data-type="simplex"]'),
      deterministic:diff(a,b),seedDelta:diff(a,seeded),perlinCorrelation:corr(a,perlin),range,gpuAvailable,gpu,exact};
  });
  await page.locator('#nodeToolBtn').click();
  await page.locator('#nodeToolSearch').fill('Simplex');
  await page.screenshot({ path:path.resolve(__dirname,'_shot_simplex_toolbox.png') });
  const ok=result.nodeName==='Simplex fBm'&&result.toolbox&&result.exact
    &&result.deterministic.max===0&&result.seedDelta.mean>.03
    &&result.perlinCorrelation<.96&&result.range[0]>=0&&result.range[1]<=1
    &&(!result.gpuAvailable||(result.gpu.max<.002&&result.gpu.mean<.0002))
    &&!errors.length;
  console.log(JSON.stringify({result,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
