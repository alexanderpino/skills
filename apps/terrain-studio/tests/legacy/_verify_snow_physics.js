// Snow PHYSICS oracle. Landed red on the unmodified build, by design — each gate encodes a defect
// measured and adjudicated before any fix was written:
//
//  G0  frame        The climate stack must simulate the SAME terrain the renderer draws. Today
//                   metricHeightField renormalises any field to the full [datum, datum+height] span,
//                   so a default terrain (span 0.26-0.73) is simulated 2.12x steeper and taller than
//                   it is rendered, and the snowline sits at the wrong elevation.
//  G1a/b ridges     Convex ground must hold snow. Today the settling loop computes instability
//                   against the TOTAL surface, and the bedrock drop cannot be reduced by removing
//                   snow, so on over-steep ground the whole column leaves every iteration; at a
//                   divergence there is no upslope resupply, so ridges strip bare. Bare band width
//                   is iterations x cell size — a pure artefact with no physical quantity in it.
//  G3  convergence  The same scene must not change snow cover with build quality. Today iterations
//                   scale with quality and the loop has no fixed point, so coverage moves ~15 pp
//                   between interactive and final.
//  G4  roof         A synthetic roof ridge steeper than repose must retain at least the render
//                   threshold at its crest, independent of iteration count. Today the crest strips
//                   to 0.000 and the bare band grows with every added iteration.
//  G5  wind         Corpus snowStep step 5: windward scour, lee deposition (cornices). Absent today;
//                   gravity settling produces symmetric bare stripes, a pattern real ridges never
//                   show. Gate feature-detects the wind parameters and fails while they are missing.
//
// Reported, NOT gated: maxDepth vs iterations (deposition is unbounded — 6 m of snowfall piles
// >100 m drifts; bounding it needs its own design and a gate here would stay red after this fix).
// ACCEPTED LIMITATIONS, documented rather than gated: G3 varies iteration count at a fixed grid,
// so the interactive-512-preview vs final-full-res RESOLUTION axis (cell size, lapMean, exposure
// estimates) is not covered; G4's retained>=0.10 magnitude is satisfied by any adhesion >= 0.0625
// (its non-vacuous content is the iteration-stability and flank-thinning pair); diagonal wind
// bearings stretch the ~30 m walk cap to ~42 m.
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
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1600);

  // BUILD THE DOCUMENT THIS FILE MEASURES. D7 (31f5688) demoted the 18-node showcase to the
  // page-global showcaseGraph() and made the opening document L0 - perlin, ridged, blend, d_height,
  // heightmask, levels, output. Inherited, this oracle read
  //   "no snow node/_field in default graph"  -> exit 2
  // because L0 has no snow node at all.
  //
  // FULL BUILD via #buildBtn, not evalGraph(). G0 is what forces the question: it compares
  // metricHeightField(outputField) against datum + curHgt*height, and curHgt is the RENDERER's own
  // normalised height buffer (legacy.js:5161), written ONLY by updateViewport.
  //
  // Measured, all three paths, same swapped showcase document, n=512:
  //   swap with no viewport refresh at all  ->  frameErrM = 2213.537   (gate bound <= 0.001)
  //   swap + evalGraph()                    ->  frameErrM = 0
  //   swap + #buildBtn (this file)          ->  frameErrM = 0
  // So evalGraph() IS sufficient today - it reaches updateViewport through
  // finishGraphEvaluation (legacy.js:3155) - and the honest reading is that the build is not
  // strictly required for G0 to be correct right now.
  //
  // It is used anyway, for a reason the first number shows: stale curHgt is 262144 floats of the
  // PREVIOUS document, exactly the same length as the new one, so the oracle's `curHgt.length ===
  // outF.length` guard does not catch it - only the value comparison does, at 2.2 km of error.
  // G0's whole contract is "the sim runs on the terrain the SCREEN draws", so it is pinned to the
  // path the screen actually takes: #buildBtn applies TARGET_RES, re-dirties every node and syncs
  // the build profile (legacy.js:6050) before evaluating. If curHgt population ever moves off
  // finishGraphEvaluation onto the render path, this oracle follows the app instead of routing
  // around it.
  //
  // (The reset leaves previewMode at its default "output" - legacy.js:3685 - so activePreviewNode()
  // is the output node and curHgt is normalised FROM the output field, the same field G0 feeds to
  // metricHeightField. showcaseGraph() ends with select(sat), inert while previewMode is "output".)
  await page.evaluate(()=>{
    nodes.length=0; edges.length=0; uid=1; selected=null; selectedEdge=null;
    showcaseGraph();
  });
  await page.locator('#buildBtn').click();
  await page.waitForFunction(
    () => !evalFrame && !document.querySelector('#buildBtn').hasAttribute('aria-busy'),
    null, { timeout: 60000 });
  await page.waitForTimeout(500);

  const out=await page.evaluate(()=>{
    USE_GPU=false;
    // Assert the subjects EXIST. A missing node must be a named SETUP FAILURE (exit 2), never a
    // silent undefined that reads as a physics verdict.
    const sn=nodes.find(n=>n.type==="snow");
    if(!sn)return{fatal:"SETUP FAILURE: no snow node after showcaseGraph()"};
    const inp=sn._field;
    if(!inp)return{fatal:"SETUP FAILURE: snow node has no _field after the build"};
    const outNd=outputNode();
    if(!outNd||!outNd._field)return{fatal:"SETUP FAILURE: no output node/_field after the build"};
    const n=Math.sqrt(inp.length)|0,N=n*n;
    const defaults=Object.fromEntries(TYPES.snow.params.map(p=>[p.key,cloneParams(p.def)]));
    const REFK=n/192;
    const cold=new Float32Array(N).fill(-25);           // snowFraction=1, melt=0: deposit==snowfall
    const run=(p,quality,field,def)=>simulateSnowLayer(field||inp,p,{res:n,terrainDef:def||terrainDef,
      quality,resScale:REFK,temperatureC:cold});
    const stats=(layer,which)=>{
      const b=layer.baseM,d=layer.depthM,lap=new Float32Array(N);
      for(let y=1;y<n-1;y++)for(let x=1;x<n-1;x++){const i=y*n+x;
        lap[i]=b[i-1]+b[i+1]+b[i-n]+b[i+n]-4*b[i];}
      const order=Array.from({length:N},(_,i)=>i).sort((a,c)=>lap[a]-lap[c]);
      const convex=order.slice(0,N/10|0);                // most negative Laplacian = most convex
      const bare=(idx,t)=>100*idx.reduce((s,i)=>s+(d[i]<t?1:0),0)/idx.length;
      const all=Array.from({length:N},(_,i)=>i);
      return{convexBare015:+bare(convex,.015).toFixed(2),convexBare100:+bare(convex,.10).toFixed(2),
        allBare015:+bare(all,.015).toFixed(2),maxDepthM:+layer.maxDepthM.toFixed(2),
        volumeM3:layer.volumeM3,depositedM3:layer.depositedM3,meltedM3:layer.meltedM3};
    };
    // ---- G0: metric frame agrees with the VIEWPORT. The viewport autolevels every displayed
    // field ((field-mn)/(mx-mn), see updateViewport's hgt fill) and derives its climate readout and
    // fallback temperature from that normalised height; the sim must live in the same frame. This
    // expression mirrors the renderer's composition independently rather than calling the function
    // under test. Recorded here because the opposite "physical" contract (datum + f*height, no
    // renormalisation) was briefly shipped on a mis-reading of the renderer and inverted the frame.
    // Pinned to the LIVE renderer: curHgt is the viewport's own normalised height buffer for the
    // displayed output field. metricHeightField(outputField) must land exactly on
    // datum + curHgt*height, or the sim and the screen have diverged - whichever side moved.
    // (A transcription of metricHeightField's formula would stay green if the VIEWPORT changed,
    // which is precisely the failure this gate exists to catch.)
    const outF=outNd._field;
    const mh=metricHeightField(outF,Math.sqrt(outF.length)|0,terrainDef);
    let frameErr=0;
    if(curHgt&&curHgt.length===outF.length){
      for(let i=0;i<outF.length;i+=97){
        const want=(terrainDef.baseElevation||0)+curHgt[i]*(terrainDef.height||2600);
        frameErr=Math.max(frameErr,Math.abs(mh[i]-want));}
    }else frameErr=9999;
    // ---- G1/G3: production-shaped params, uniform cold ----
    const interactive=stats(run(defaults,"interactive"));
    const finalQ=stats(run(defaults,"final"));
    // ---- G4: synthetic roof at A degrees; field spans exactly [0,1] so it is frame-invariant ----
    const roof=A=>{
      const m=129,mid=(m-1)/2,f=new Float32Array(m*m),cell=5000/m;
      for(let y=0;y<m;y++)for(let x=0;x<m;x++)f[y*m+x]=1-Math.abs(x-mid)/mid;
      const def={...terrainDef,scale:5000,height:mid*cell*Math.tan(A*Math.PI/180),baseElevation:0};
      const coldM=new Float32Array(m*m).fill(-25);
      const go=iter=>{
        const l=simulateSnowLayer(f,{...defaults,windStrength:0,iterations:iter},   // settling only: wind would mask flank thinning by conserving the two-flank average
          {res:m,terrainDef:def,quality:"interactive",resScale:1,temperatureC:coldM});
        let c=0,fl=0,fn=0;
        // Flank sampled 8 cells off the crest: the drain front travels ONE cell per iteration, so a
        // quarter-width sample (32 cells out) reads pristine deposit at 18 iterations and calls the
        // mechanism dead when it is merely en route.
        for(let y=0;y<m;y++){c+=l.depthM[y*m+(mid|0)];
          for(const q of [(mid|0)-8,(mid|0)+8]){fl+=l.depthM[y*m+q];fn++;}}
        return{crest:c/m,flank:fl/fn};
      };
      const g18=go(18),g72=go(72);
      // flankThinned: transport must actually RUN above repose - otherwise a large enough
      // adhesion constant satisfies crest retention with the avalanche mechanism dead.
      return{A,crest18:+g18.crest.toFixed(3),crest72:+g72.crest.toFixed(3),
        flank18:+g18.flank.toFixed(3),
        stable:Math.abs(g18.crest-g72.crest)<=.02,retained:g18.crest>=.10,
        flankThinned:A>defaults.repose?g18.flank<defaults.snowfall*.9:true};
    };
    const roof45=roof(45),roof75=roof(75);
    // ---- G5: wind (feature-detected) ----
    const hasWind=TYPES.snow.params.some(p=>p.key==="windStrength");
    let wind=null;
    if(hasWind){
      const p={...defaults,windStrength:.7,windDirection:270}; // from map-west: wind blows +x
      const layer=run(p,"interactive");
      const calm=run({...defaults,windStrength:0},"interactive");
      const d=layer.depthM,b=layer.baseM;
      // Measure the cornice AT THE CREST LINE, not as a face-wide mean. On a uniform windward face
      // saltation is a conveyor - every cell receives what its upwind neighbour loses - so means
      // over whole faces cancel to ~1.0 no matter how strong the wind is. The signature of the
      // process is local: at a crest along the wind axis, the first LEE cell is loaded and the
      // windward brow is stripped. Wind blows +x here (from map-west), so crests are x-local-maxima.
      // FACE-INTEGRATED gates, classified on the BEDROCK (fixed sets, immune to where any single
      // drift crest lands). Two earlier metrics both failed for instructive reasons: crest-line
      // cells detected on the windy surface select exactly what the wind carved (leeLoading read
      // 0.751); crest-line cells on the bedrock read the drift-shoulder planing as lee LOSS,
      // because settling parks drift crests downwind of bedrock crests and the saltation model -
      // which has no flow separation - erodes the drift's windward shoulder there. The corpus
      // claim "strips crests, builds lee cornices" is a statement about FACES: windward bedrock
      // faces must net-lose and lee faces net-gain, versus the calm run.
      let crestN=0,leeSum=0,browSum=0,calmLeeSum=0;
      let wwCalm=0,wwWind=0,leeCalm=0,leeWind=0;
      const cellW=layer.cellSizeM;
      for(let y=1;y<n-1;y++)for(let x=2;x<n-2;x++){const i=y*n+x;
        if(b[i]>b[i-1]&&b[i]>b[i+1]){crestN++;browSum+=d[i-1];leeSum+=d[i+1];calmLeeSum+=calm.depthM[i+1];}
        const gxB=(b[i+1]-b[i-1])/(2*cellW);
        if(gxB>.25){wwCalm+=calm.depthM[i];wwWind+=d[i];}
        else if(gxB<-.25){leeCalm+=calm.depthM[i];leeWind+=d[i];}}
      const windwardLossPct=100*(wwCalm-wwWind)/Math.max(wwCalm,1e-6);
      const leeGainPct=100*(leeWind-leeCalm)/Math.max(leeCalm,1e-6);
      const massErr=Math.abs(layer.depositedM3-layer.meltedM3-layer.volumeM3)/Math.max(layer.depositedM3,1);
      // leeLoading compares the SAME cells with wind on vs off: brow stripping alone cannot
      // satisfy it, so it proves deposition, not just scour. crests>=50 guards the degenerate
      // flat-terrain case where zero crests would make every ratio vacuous.
      wind={crests:crestN,
        windwardLossPct:+windwardLossPct.toFixed(2),leeGainPct:+leeGainPct.toFixed(2),
        crestLine:{browMean:+(browSum/Math.max(crestN,1)).toFixed(3),   // diagnostics, unasserted
          leeMean:+(leeSum/Math.max(crestN,1)).toFixed(3),
          calmLeeMean:+(calmLeeSum/Math.max(crestN,1)).toFixed(3)},
        massErr:+massErr.toExponential(2)};
    }
    const massErr=Math.abs(interactive.depositedM3-interactive.meltedM3-interactive.volumeM3)
      /Math.max(interactive.depositedM3,1);
    return{n,frameErrM:+frameErr.toFixed(3),interactive,finalQ,
      qualityDeltaPp:+Math.abs(interactive.allBare015-finalQ.allBare015).toFixed(2),
      maxDepthTrend:{i18:interactive.maxDepthM,i32:finalQ.maxDepthM,
        note:"REPORT ONLY - deposition bound is separate work; target <= 1.10 ratio"},
      roof45,roof75,hasWind,wind,massErr:+massErr.toExponential(2)};
  });
  if(out.fatal){console.error(out.fatal);process.exit(2);}
  const gates={
    G0_frameErrM:[out.frameErrM,"<=0.001",out.frameErrM<=.001],
    G1a_convexBare015:[out.interactive.convexBare015,"<=5",out.interactive.convexBare015<=5],
    G1b_convexBare100:[out.interactive.convexBare100,"<=10",out.interactive.convexBare100<=10],
    G3_qualityDeltaPp:[out.qualityDeltaPp,"<=3",out.qualityDeltaPp<=3],
    G4_roof45:[[out.roof45.crest18,out.roof45.crest72,out.roof45.flank18],"retained & stable & flank thinned",out.roof45.retained&&out.roof45.stable&&out.roof45.flankThinned],
    G4_roof75:[[out.roof75.crest18,out.roof75.crest72,out.roof75.flank18],"retained & stable & flank thinned",out.roof75.retained&&out.roof75.stable&&out.roof75.flankThinned],
    G5_windPresent:[out.hasWind,"wind params implemented",out.hasWind],
    G5_windwardLoss:[out.wind?out.wind.windwardLossPct:null,">=2% of calm windward volume",!!out.wind&&out.wind.windwardLossPct>=2&&out.wind.crests>=50],
    G5_leeGain:[out.wind?out.wind.leeGainPct:null,">=2% of calm lee volume",!!out.wind&&out.wind.leeGainPct>=2],
    G5_windMass:[out.wind?out.wind.massErr:null,"<=1e-6",!!out.wind&&out.wind.massErr<=1e-6],
    mass:[out.massErr,"<=1e-6",out.massErr<=1e-6],
  };
  const ok=Object.values(gates).every(g=>g[2])&&!errors.length;
  console.log(JSON.stringify({...out,gates,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error("FATAL",e);process.exit(2);});
