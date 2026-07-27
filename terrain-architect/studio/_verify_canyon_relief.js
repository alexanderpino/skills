// Relief-budget oracle. The canyon's depth must be CUT by the solve, not stamped on at compose time.
// Before this was enforced the evolution loop cut 99% of the map by under 21 m into a 185 m plateau,
// a hand-set outlet notch supplied 46% of the entire range, and canyonComposeField invented the rest
// with a 5.86x vertical stretch. Every downstream mechanism was inert as a result: bed thicknesses of
// 32-87 m against a 21 m cut meant no bed was ever exposed, so lithology could not express.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');
const H = 2600; // terrainDef.height; h and the composed field share this normalised unit

(async()=>{
  const browser=await chromium.launch({executablePath:EXE,args:['--use-gl=angle','--use-angle=swiftshader',
    '--enable-unsafe-swiftshader','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1280,height:800}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1400);
  const result=await page.evaluate(({H})=>{
    RES=512;TARGET_RES=512;USE_GPU=false;CANYON_EVOLUTION_CACHE.clear();
    const defaults=Object.fromEntries(TYPES.canyon.params.map(p=>[p.key,cloneParams(p.def)]));
    const q=(arr,f)=>{const s=Float64Array.from(arr).sort();return s[Math.min(s.length-1,Math.floor(s.length*f))];};
    const run=style=>{
      const p={...defaults,style,scale:.35,slot:.36,valley:.58,surrounding:.60,depth:1,
        structural:.50,tributaries:4,seed:8,detailWarp:.50,alternate:"off"};
      const s=canyonEvolutionState(p),n=s.n,N=n*n,h=s.h;
      let mn=Infinity,mx=-Infinity;
      for(let i=0;i<N;i++){if(h[i]<mn)mn=h[i];if(h[i]>mx)mx=h[i];}
      // Net fluvial cut = how far below the uplifted initial surface the solve actually took each cell.
      const cut=new Float64Array(N);
      for(let i=0;i<N;i++)cut[i]=Math.max(0,(s.initial[i]-h[i]))*H;
      // Row-wise cross-section relief: what actually reads as canyon depth when you look across it.
      const rowRelief=[];
      for(let y=0;y<n;y++){let a=Infinity,b=-Infinity;
        for(let x=0;x<n;x++){const v=h[y*n+x];if(v<a)a=v;if(v>b)b=v;}rowRelief.push((b-a)*H);}
      // Bed exposure: a bed that underlies almost none of the map can never show a shelf.
      const beds=canyonBeds(p),base=mx-.82;
      const exposure=beds.map(bd=>{const e=base+bd[0]*.82;let c=0;
        for(let i=0;i<N;i++)if(h[i]<e)c++;return +(100*c/N).toFixed(2);});
      // The plateau must SURVIVE. Too much celerity grades everything to base level and the tableland
      // (the thing a canyon is cut INTO) disappears, which would pass a depth gate while destroying
      // the landform. Also track the trunk's long profile: a canyon graded only near its outlet is a
      // knickpoint that never finished travelling.
      let high=0;for(let i=0;i<N;i++)if(h[i]>mx-.12*.82)high++;
      const rowMax=[];for(let y=0;y<n;y++){let b=-Infinity;
        for(let x=0;x<n;x++){const v=h[y*n+x];if(v>b)b=v;}rowMax.push(b);}
      const upstreamRow=Math.floor(n*.25),downstreamRow=Math.floor(n*.85);
      const rowRel=y=>{let a=Infinity,b=-Infinity;
        for(let x=0;x<n;x++){const v=h[y*n+x];if(v<a)a=v;if(v>b)b=v;}return (b-a)*H;};
      // Compose must be an AFFINE VIEW of the solve, nothing more. Correlation below 1 means compose
      // has started inventing terrain again; it read 0.4786 when the output was rebuilt from the
      // pre-erosion surface minus a blurred incision mask.
      // Measured on the COMPOSED field itself, not on canyonFieldCPU's output. The surface-expression
      // pass legitimately alters the output afterwards - it is a mass-conserving, material-gated
      // weathering operator at render resolution - so running the correlation through it would test
      // two things at once and stop isolating the property this oracle exists to protect.
      const composed=s.field,m=composed.length;
      const hs=h;
      let sx=0,sy=0,sxx=0,syy=0,sxy=0;
      for(let i=0;i<m;i++){const x=hs[i],y=composed[i];sx+=x;sy+=y;sxx+=x*x;syy+=y*y;sxy+=x*y;}
      const cov=sxy/m-(sx/m)*(sy/m);
      const corr=cov/Math.sqrt(Math.max(sxx/m-(sx/m)**2,1e-20)*Math.max(syy/m-(sy/m)**2,1e-20));
      // Mass budget for the weathering pass: everything a face loses must land at its foot or be
      // accounted as leaving the tile. The published form of this recipe ADDS material; that is the
      // exact defect the budget catches, so the sink is reported rather than silently dropped.
      canyonFieldCPU(p);
      const sf=s.surface||{sourced:0,exported:0,deposited:0};
      const massErr=Math.abs(sf.sourced-(sf.deposited+sf.exported))/Math.max(sf.sourced,1e-12);
      return{n,reliefM:+((mx-mn)*H).toFixed(1),composeCorr:+corr.toFixed(5),
        weatheringMassErr:+massErr.toExponential(2),
        weatheredSourced:+sf.sourced.toFixed(4),weatheredExportedPct:+(100*sf.exported/Math.max(sf.sourced,1e-12)).toFixed(2),
        plateauPct:+(100*high/N).toFixed(1),
        reliefUpstream:+rowRel(upstreamRow).toFixed(0),reliefDownstream:+rowRel(downstreamRow).toFixed(0),
        cutMean:+(cut.reduce((a,b)=>a+b,0)/N).toFixed(1),cutP99:+q(cut,.99).toFixed(1),
        medianRowRelief:+q(rowRelief,.5).toFixed(1),
        bedExposurePct:exposure,bedsAbove5pct:exposure.filter(v=>v>5).length,bedCount:beds.length};
    };
    const out={};for(const st of["classic","eroded","eroded2","strata","both"])out[st]=run(st);
    return out;
  },{H});
  const c=result.classic;
  const ok=c.cutP99>=600&&c.medianRowRelief>=1490&&c.bedsAbove5pct>=4
    &&c.composeCorr>=.999&&c.plateauPct>=25
    &&c.weatheringMassErr<1e-6&&c.weatheredSourced>0&&!errors.length;
  console.log(JSON.stringify({result,errors,
    gate:{cutP99:[c.cutP99,">=600"],medianRowRelief:[c.medianRowRelief,">=1490"],
      bedsAbove5pct:[c.bedsAbove5pct,">=4 of "+c.bedCount],
      composeCorr:[c.composeCorr,">=.999"],plateauPct:[c.plateauPct,">=25"],
      weatheringMassErr:[c.weatheringMassErr,"<1e-6"],
      weatheredExportedPct:c.weatheredExportedPct},ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error("FATAL",e);process.exit(2);});
