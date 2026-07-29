// Step 0 hygiene oracle. Two assertions, each failing on the exact corruption it guards:
//  1. Hoisting the duplicated uplift literal must be EXACTLY behaviour-neutral. If the loop's uplift
//     and the processDelta reference ever disagree, processDelta -> residualCut -> incision is
//     silently poisoned. Proven by digesting all five styles against a pre-change build.
//  2. terrainDef.scale/height are solver inputs, so changing them must change the cache key.
// The cache-key assertion is a standing regression test. The per-style digests are a differential
// tool: point this at two builds and compare, to prove a refactor was exactly behaviour-neutral.
// Usage: node _verify_canyon_identity.js [page.html]   (default index.html)
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const PAGE = process.argv[2] || 'index.html';
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../', PAGE));

(async()=>{
  const browser=await chromium.launch({executablePath:EXE,args:['--use-gl=angle','--use-angle=swiftshader',
    '--enable-unsafe-swiftshader','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1280,height:800}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1400);
  const result=await page.evaluate(()=>{
    RES=512;TARGET_RES=512;USE_GPU=false;CANYON_EVOLUTION_CACHE.clear();
    const defaults=Object.fromEntries(TYPES.canyon.params.map(p=>[p.key,cloneParams(p.def)]));
    // Order-sensitive digest: any single changed sample moves it.
    const digest=f=>{let a=0,b=0;for(let i=0;i<f.length;i++){a=(a+Math.round(f[i]*1e7))>>>0;b=(b^(a+i))>>>0;}
      return a.toString(16)+":"+b.toString(16);};
    const styles=["classic","eroded","eroded2","strata","both"],digests={};
    for(const style of styles){
      const p={...defaults,style,scale:.35,slot:.36,valley:.58,surrounding:.60,depth:1,
        structural:.50,tributaries:4,seed:8,detailWarp:.50,alternate:"off"};
      digests[style]=digest(canyonFieldCPU(p));
    }
    let keyChanges=null,keyRestores=null;
    try{
      const probe={...defaults,style:"classic",tributaries:4,seed:8};
      const before=canyonCacheKey(probe,192),saved=terrainDef.height;
      terrainDef.height=1800;const after=canyonCacheKey(probe,192);terrainDef.height=saved;
      keyChanges=before!==after;keyRestores=before===canyonCacheKey(probe,192);
    }catch(e){keyChanges="ERR:"+e.message;}
    return{digests,keyChanges,keyRestores};
  });
  const ok=result.keyChanges===true&&result.keyRestores===true&&!errors.length;
  // Report the URL actually loaded, not the page argument: STUDIO_URL overrides PAGE, so printing
  // PAGE would label the output with a file this run never opened.
  console.log(JSON.stringify({page:URL,...result,errors,ok},null,2));
  await browser.close();
  process.exit(ok?0:1);
})().catch(e=>{console.error("FATAL",e);process.exit(2);});
