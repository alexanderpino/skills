// GRID INVARIANCE. Solve the same world at different process resolutions and require that the
// large-scale landform is the same landform - only the detail may differ. This is the cheapest
// detector of the most pervasive defect in terrain graphs: a length or an area written in CELLS
// rather than in metres. If the mountains move when only the resolution changed, a parameter is
// denominated in the grid.
// Contributing area here accumulates in cells, so a fixed cell-count channel threshold means a
// different physical area at every resolution; raising the process grid without correcting it
// channelises the whole map. The correction is asserted, not assumed.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

(async()=>{
  const browser=await chromium.launch({executablePath:EXE,args:['--use-gl=angle','--use-angle=swiftshader',
    '--enable-unsafe-swiftshader','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1280,height:800}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1400);
  const out=await page.evaluate(()=>{
    RES=512;TARGET_RES=512;USE_GPU=false;CANYON_EVOLUTION_CACHE.clear();
    const defaults=Object.fromEntries(TYPES.canyon.params.map(p=>[p.key,cloneParams(p.def)]));
    const p={...defaults,style:"classic",scale:.35,slot:.36,valley:.58,surrounding:.60,depth:1,
      structural:.50,tributaries:4,seed:8,detailWarp:.50,alternate:"off"};
    const H=terrainDef.height;
    const box=(f,m,K)=>{ // average onto a KxK grid: the landform, with detail deliberately removed
      const o=new Float64Array(K*K);
      for(let y=0;y<m;y++)for(let x=0;x<m;x++){
        const gy=Math.min(K-1,(y*K/m)|0),gx=Math.min(K-1,(x*K/m)|0);
        o[gy*K+gx]+=f[y*m+x];
      }
      const per=(m/K)*(m/K);for(let i=0;i<K*K;i++)o[i]/=per;return o;
    };
    const corr=(a,b)=>{const m=a.length;let sx=0,sy=0,sxx=0,syy=0,sxy=0;
      for(let i=0;i<m;i++){sx+=a[i];sy+=b[i];sxx+=a[i]*a[i];syy+=b[i]*b[i];sxy+=a[i]*b[i];}
      const cov=sxy/m-(sx/m)*(sy/m);
      return cov/Math.sqrt(Math.max(sxx/m-(sx/m)**2,1e-20)*Math.max(syy/m-(sy/m)**2,1e-20));};
    const sample=nProc=>{
      CANYON_EVOLUTION_CACHE.clear();
      const s=canyonEvolutionState(p,nProc),N=s.n*s.n;
      let mn=Infinity,mx=-Infinity,act=0;
      for(let i=0;i<N;i++){if(s.h[i]<mn)mn=s.h[i];if(s.h[i]>mx)mx=s.h[i];
        if(s.channelHeadIndex[i]>=.68)act++;}
      const cellM=terrainDef.scale/(s.n-1);
      // Drainage density in 1/m: channel length over area. Reported in units that do NOT contain the
      // grid, because a count of "channel cells" is meaningless across two different grids.
      const densityPerM=(act*cellM)/(terrainDef.scale*terrainDef.scale);
      let flat=0;for(let i=0;i<N;i++)if(s.h[i]>mx-.12*.82)flat++;
      return{n:s.n,reliefM:+((mx-mn)*H).toFixed(1),activeCells:act,
        drainageDensityPerM:+densityPerM.toExponential(3),
        plateauPct:+(100*flat/N).toFixed(1),coarse:box(s.h,s.n,24)};
    };
    const a=sample(160),b=sample(192),c=sample(256);
    return{a:{...a,coarse:undefined},b:{...b,coarse:undefined},c:{...c,coarse:undefined},
      corrAB:+corr(a.coarse,b.coarse).toFixed(4),corrBC:+corr(b.coarse,c.coarse).toFixed(4),
      densitySpreadPct:+(100*(Math.max(a.drainageDensityPerM,b.drainageDensityPerM,c.drainageDensityPerM)/
        Math.min(a.drainageDensityPerM,b.drainageDensityPerM,c.drainageDensityPerM)-1)).toFixed(1),
      reliefSpreadPct:+(100*(Math.max(a.reliefM,b.reliefM,c.reliefM)/
        Math.min(a.reliefM,b.reliefM,c.reliefM)-1)).toFixed(1)};
  });
  const ok=out.corrAB>=.90&&out.corrBC>=.90&&out.densitySpreadPct<=60
    &&out.reliefSpreadPct<=12&&!errors.length;
  console.log(JSON.stringify({...out,errors,
    gate:{corrAB:[out.corrAB,">=.90"],corrBC:[out.corrBC,">=.90"],
      densitySpreadPct:[out.densitySpreadPct,"<=60"],
      reliefSpreadPct:[out.reliefSpreadPct,"<=12"]},ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error("FATAL",e);process.exit(2);});
