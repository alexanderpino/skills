// Cliff-and-talus oracle. A bimodal slope distribution is only legitimate if it is traceable to two
// entries in the MATERIAL table; a bimodal histogram produced by a height threshold is a known defect
// that looks identical in a screenshot. So the decisive assertion is not "is it bimodal" but "do the
// modes MOVE when the bed table's repose angles move". A height-threshold artefact does not move.
// Linear diffusion previously gave one mode at 13.5-14.5 degrees in all five styles - the diffusion
// equilibrium slope, not a repose angle.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));

(async()=>{
  const browser=await chromium.launch({executablePath:EXE,args:['--use-gl=angle','--use-angle=swiftshader',
    '--enable-unsafe-swiftshader','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1280,height:800}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1400);
  const out=await page.evaluate(()=>{
    RES=512;TARGET_RES=512;USE_GPU=false;CANYON_EVOLUTION_CACHE.clear();
    const defaults=Object.fromEntries(TYPES.canyon.params.map(p=>[p.key,cloneParams(p.def)]));
    const cellM=terrainDef.scale/(RES-1),H=terrainDef.height;
    // Steep-only. Including the plateau puts a huge spike at 0 degrees that dominates any modality
    // statistic and reports "bimodal" for a surface with one slope population.
    const modes=f=>{
      const bins=new Float64Array(90);let tot=0;
      for(let y=1;y<RES-1;y++)for(let x=1;x<RES-1;x++){
        const i=y*RES+x;
        const gx=(f[i+1]-f[i-1])*H/(2*cellM),gy=(f[i+RES]-f[i-RES])*H/(2*cellM);
        const deg=Math.atan(Math.hypot(gx,gy))*180/Math.PI;
        if(deg<8)continue;
        bins[Math.min(89,Math.floor(deg))]++;tot++;
      }
      for(let k=0;k<90;k++)bins[k]=100*bins[k]/Math.max(tot,1);
      const peaks=[];
      for(let k=1;k<89;k++)if(bins[k]>=bins[k-1]&&bins[k]>=bins[k+1]&&bins[k]>.05)peaks.push([k+.5,bins[k]]);
      peaks.sort((a,b)=>b[1]-a[1]);
      let repose=0;for(let k=30;k<38;k++)repose+=bins[k];
      return{peaks:peaks.slice(0,3).map(p=>[+p[0].toFixed(1),+p[1].toFixed(3)]),
        reposeBandPct:+repose.toFixed(2),
        prominenceRatio:peaks.length>1?+(peaks[1][1]/Math.max(peaks[0][1],1e-9)).toFixed(3):0};
    };
    const p={...defaults,style:"classic",scale:.35,slot:.36,valley:.58,surrounding:.60,depth:1,
      structural:.50,tributaries:4,seed:8,detailWarp:.50,alternate:"off"};
    const baseM=modes(canyonFieldCPU(p));
    // Also measure the RAW process grid. If the solver is enforcing repose but the output is not, the
    // defect is downstream of the solve (resample or output-resolution detail), not in the mechanism.
    const st=canyonEvolutionState(p);
    const modesAt=(f,m,cell)=>{
      const bins=new Float64Array(90);let tot=0;
      for(let y=1;y<m-1;y++)for(let x=1;x<m-1;x++){
        const i=y*m+x;
        const gx=(f[i+1]-f[i-1])*H/(2*cell),gy=(f[i+m]-f[i-m])*H/(2*cell);
        const deg=Math.atan(Math.hypot(gx,gy))*180/Math.PI;
        if(deg<8)continue;bins[Math.min(89,Math.floor(deg))]++;tot++;
      }
      for(let k=0;k<90;k++)bins[k]=100*bins[k]/Math.max(tot,1);
      const pk=[];for(let k=1;k<89;k++)if(bins[k]>=bins[k-1]&&bins[k]>=bins[k+1]&&bins[k]>.05)pk.push([k+.5,bins[k]]);
      pk.sort((a,b)=>b[1]-a[1]);
      let rep=0;for(let k=30;k<38;k++)rep+=bins[k];
      let over70=0;for(let k=70;k<90;k++)over70+=bins[k];
      return{peaks:pk.slice(0,3).map(q=>[+q[0].toFixed(1),+q[1].toFixed(3)]),
        reposeBandPct:+rep.toFixed(2),over70Pct:+over70.toFixed(2)};
    };
    const procM=modesAt(st.h,st.n,terrainDef.scale/(st.n-1));
    // Predict the bed table's OWN angles, so the assertion is self-calibrating rather than a fixed
    // band someone chose. A landscape whose debris mode sits between the softest bed's repose angle
    // and the soft/stiff midpoint is resting on material; one that ignores those numbers is not.
    const pr=CANYON_PROCESS[CANYON_STYLE_ID[p.style]||0];
    const rs=pr.repose*(1.32+(.76-1.32)*p.valley)*(.74+(1.34-.74)*p.slot);
    const predSoft=Math.min(46,Math.max(30,(43-11*pr.lith)*rs)),predStiff=Math.min(84,Math.max(47,(54+22*pr.lith)*rs));
    // Perturb the bed table's angles via the style whose lithologic contrast is maximal, and via the
    // repose scale. If the modes are a material property they must follow; if they are a height
    // threshold they will not.
    CANYON_EVOLUTION_CACHE.clear();
    const saved=CANYON_PROCESS[0].repose;
    CANYON_PROCESS[0].repose=saved*0.72;
    const shallow=modes(canyonFieldCPU(p));
    CANYON_EVOLUTION_CACHE.clear();
    CANYON_PROCESS[0].repose=saved*1.28;
    const steep=modes(canyonFieldCPU(p));
    CANYON_PROCESS[0].repose=saved;CANYON_EVOLUTION_CACHE.clear();
    const shift=Math.abs(steep.peaks[0][0]-shallow.peaks[0][0]);
    const lowMode=Math.min(baseM.peaks[0][0],baseM.peaks[1][0]);
    const highMode=Math.max(baseM.peaks[0][0],baseM.peaks[1][0]);
    return{base:baseM,proc:procM,shallow,steep,lowMode,highMode,
      predSoft:+predSoft.toFixed(1),predStiff:+predStiff.toFixed(1),
      debrisBracket:[+(predSoft-3).toFixed(1),+((predSoft+predStiff)/2+3).toFixed(1)],primaryModeShiftDeg:+shift.toFixed(2)};
  });
  // The bare 30-38 band was inherited from an earlier probe and is NOT the right test: the corpus puts
  // scree/talus at 35-40 and soil at 30-45, and the aggregate debris population sits above the softest
  // bed's angle because hardness varies through the stack. It is reported, not asserted. What IS
  // asserted is stronger: the two modes must exist, must be comparably prominent, must MOVE when the
  // bed table moves, and the debris mode must land inside the bracket the bed table itself predicts.
  const inBracket=out.lowMode>=out.debrisBracket[0]&&out.lowMode<=out.debrisBracket[1];
  const ok=out.primaryModeShiftDeg>=5&&out.base.prominenceRatio>=0.5
    &&inBracket&&out.highMode>=out.lowMode+18&&!errors.length;
  console.log(JSON.stringify({...out,errors,
    gate:{primaryModeShiftDeg:[out.primaryModeShiftDeg,">=5"],
      prominenceRatio:[out.base.prominenceRatio,">=0.5"],
      debrisModeInBracket:[out.lowMode,out.debrisBracket,inBracket],
      modeSeparation:[+(out.highMode-out.lowMode).toFixed(1),">=18"],
      reposeBandPct_reported_only:out.base.reposeBandPct},ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error("FATAL",e);process.exit(2);});
