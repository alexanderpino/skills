// Stream power is verified by the slope-area relation, not by eye: at steady state
// U = K*A^m*S^n gives S ~ A^(-m/n), a straight line of slope -m/n on log-log.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(async () => {
    const savedWorkingRes=RES;RES=128; // fixed numerical oracle; do not scale with the editor's 512² default
    const n = RES, out = {};
    const noisy = fbmField(gnoise, {seed:5, freq:2, octaves:4, lac:2, gain:0.5});

    // ---- THE ORACLE: at steady state U = K*A^m*S^n gives S ~ A^(-m/n) ----
    // Driven in the regime the reference-impl's own test uses, and for the same reason: from small
    // uniform noise (so the network self-organises rather than inheriting a structure) and with
    // U*dt = K*dt (so it actually reaches steady state). Driving it from structured fBm with an
    // unbalanced uplift instead made the fitted exponent wander between -0.28 and +0.02 -- a broken
    // HARNESS reporting a broken solver, which nearly got working code "fixed".
    const h0 = newField(); let st = 12345;
    const rnd = () => { st=(Math.imul(st^(st>>>15),2246822519)+374761393)>>>0; return st/4294967296; };
    for (let i=0;i<h0.length;i++) h0[i] = rnd()*0.05;
    const fitSlopeArea = (h, mExp) => {
      const hf = priorityFloodFill(h); const { rec, dist } = spReceivers(hf, 1);
      const A = new Float32Array(n*n).fill(1);
      const order = Array.from({length:n*n},(_,i)=>i).sort((a,b)=>hf[b]-hf[a]);
      for (const i of order) if (rec[i]>=0) A[rec[i]] += A[i];
      const X=[], Y=[];
      for (let y=2;y<n-2;y++) for (let x=2;x<n-2;x++){
        const i=y*n+x; if (rec[i]<0) continue;
        const S=(hf[i]-hf[rec[i]])/dist[i];
        if (A[i] <= 30 || S <= 1e-6) continue;          // channel cells only, as in the reference
        X.push(Math.log(A[i])); Y.push(Math.log(S)); }
      if (X.length < 50) return { tooFewChannelCells: X.length };
      const mx=X.reduce((a,v)=>a+v,0)/X.length, my=Y.reduce((a,v)=>a+v,0)/Y.length;
      let num=0, den=0, sy=0;
      for (let i=0;i<X.length;i++){ num+=(X[i]-mx)*(Y[i]-my); den+=(X[i]-mx)**2; sy+=(Y[i]-my)**2; }
      const slope=num/den;
      return { slope:+slope.toFixed(3), expected:-mExp, err:+Math.abs(slope+mExp).toFixed(3),
               r2:+((num*num)/(den*sy)).toFixed(3), channelCells:X.length,
               withinReferenceTolerance: Math.abs(slope+mExp) < 0.1 };
    };
    for (const mExp of [0.4, 0.5, 0.6])
      out["slopeArea_m"+mExp] = fitSlopeArea(streamPowerErode(h0,{Kdt:2,Udt:2,m:mExp,iters:400}), mExp);
    // and it must be CONVERGED, not passing by luck at one iteration count
    out.steadyState = [100,200,400,800].map(iters =>
      ({ iters, slope: fitSlopeArea(streamPowerErode(h0,{Kdt:2,Udt:2,m:0.5,iters}), 0.5).slope }));

    // ---- structural invariants ----
    const eroded = streamPowerErode(noisy, {Kdt:0.5, Udt:0.004, m:0.5, iters:30});
    const flowOf = (h) => { const hf=priorityFloodFill(h); const {rec}=spReceivers(hf,1);
      const A=new Float32Array(n*n).fill(1);
      const o=Array.from({length:n*n},(_,i)=>i).sort((a,b)=>hf[b]-hf[a]);
      for (const i of o) if (rec[i]>=0) A[rec[i]]+=A[i];
      return A; };
    // a drainage network is a TREE: a few cells carry very large area, most carry almost none.
    // Uniform texture would not concentrate like this.
    const conc = (A) => { const s=Array.from(A).sort((a,b)=>b-a);
      const tot=s.reduce((a,v)=>a+v,0);
      let acc=0,k=0; while (acc < tot*0.5 && k<s.length){ acc+=s[k++]; }
      return +(k/s.length).toFixed(4); };
    out.drainageConcentrates = { rawFracCarryingHalfTheFlow: conc(flowOf(noisy)),
                                 erodedFracCarryingHalfTheFlow: conc(flowOf(eroded)),
                                 moreConcentratedAfterIncision: conc(flowOf(eroded)) < conc(flowOf(noisy)) };
    // no pits left below their receiver, and edges held at base level
    let belowReceiver=0; { const hf=priorityFloodFill(eroded); const {rec}=spReceivers(hf,1);
      for (let i=0;i<n*n;i++) if (rec[i]>=0 && eroded[i] < eroded[rec[i]]-1e-6) belowReceiver++; }
    let edgeMax=0; for (let x=0;x<n;x++){ edgeMax=Math.max(edgeMax,eroded[x],eroded[(n-1)*n+x]); }
    out.invariants = { cellsBelowTheirReceiver:belowReceiver, maxEdgeHeight:+edgeMax.toFixed(6),
                       finite: eroded.every(v=>isFinite(v)) };

    // ---- it must carve, not flatten: relief survives with uplift on ----
    const relief=(f)=>{let lo=1e9,hi=-1e9;for(const v of f){if(v<lo)lo=v;if(v>hi)hi=v;}return +(hi-lo).toFixed(3);};
    out.carvesWithoutFlattening = { before:relief(noisy), after:relief(eroded),
      keptRelief: relief(eroded) > relief(noisy)*0.4 };
    // ---- with no uplift it BASE-LEVELS, and that is correct physics, not a bug ----
    // Rivers reduce a landmass that has stopped rising. Recorded as expected behaviour so nobody
    // "fixes" it later, and because the node's defaults have to sit well clear of it.
    const DEF=Object.fromEntries(TYPES.mountain.params.map(q=>[q.key,q.def]));
    const mt=TYPES.mountain.eval({...DEF,style:"alpine",x:0.5,y:0.5,size:0.40,seed:77777,variation:0.8},[],{});
    const peak=(f)=>{let hi=0;for(const v of f)if(v>hi)hi=v;return +hi.toFixed(4);};
    out.noUpliftBaseLevels = {
      input: peak(mt),
      byIncision: [[0.30,14],[0.70,26],[1.20,40]].map(([Kdt,iters]) =>
        ({ Kdt, iters, peak: peak(streamPowerErode(mt,{Kdt,Udt:0,m:0.5,iters})) })),
      erodesToNothing: peak(streamPowerErode(mt,{Kdt:1.2,Udt:0,m:0.5,iters:40})) < 0.01 };
    // the shipped defaults must carve without destroying
    const dp = TYPES.streampower.params.reduce((a,q)=>(a[q.key]=q.def,a),{});
    const atDefaults = TYPES.streampower.eval(dp, [mt, null], {});
    out.defaultsAreSafe = { peakBefore:peak(mt), peakAfter:peak(atDefaults),
      keepsMostRelief: peak(atDefaults) > peak(mt)*0.6,
      actuallyCarves: (()=>{ let d=0; for(let i=0;i<mt.length;i++) d+=Math.abs(mt[i]-atDefaults[i]);
        return d/mt.length > 1e-4; })() };
    out.noNegatives = { mountainMin:+Math.min(...mt).toFixed(6), clean: Math.min(...mt) >= 0 };
    // ---- HILLSLOPE DIFFUSION: the other half of the equation ----
    // dh/dt = U - K*A^m*S^n + D*grad^2(h). Stream power sharpens interfluves without limit; run it
    // alone from a smooth uplift field and the result is a field of razor blades. Diffusion is what
    // gives hillslopes a length and valleys a width. It must run INSIDE the loop -- one relaxation
    // afterwards cannot undo ridges that sharpened for 200 iterations.
    const blob = TYPES.shape.eval({kind:"circle", x:0.5, y:0.5, size:0.62, aspect:1.25,
                                   angle:20, falloff:0.55, invert:"off"});
    const flat = newField(0);
    const sharpness = (f) => { let lo=1e9,hi=-1e9,lap=0,c=0;
      for (const v of f){ if(v<lo)lo=v; if(v>hi)hi=v; }
      for (let y=1;y<n-1;y++) for (let x=1;x<n-1;x++){ const i=y*n+x;
        lap += Math.abs(4*f[i]-f[i-1]-f[i+1]-f[i-n]-f[i+n]); c++; }
      return { relief:+(hi-lo).toFixed(4), ridge:+((lap/c)/((hi-lo)||1)).toFixed(4) }; };
    const byD = [0, 0.05, 0.10, 0.18].map(Ddt =>
      ({ Ddt, ...sharpness(streamPowerErode(flat,{Kdt:0.6,Udt:0.004,m:0.5,iters:140,uplift:blob,Ddt})) }));
    out.hillslopeDiffusion = { byD,
      ridgesRelaxMonotonically: byD.every((v,i)=> i===0 || v.ridge < byD[i-1].ridge),
      sharpnessRange: +(byD[0].ridge/byD[byD.length-1].ridge).toFixed(2),
      // relaxing ridges must not flatten the landscape -- those are different things
      reliefPreserved: byD.every(v => v.relief > byD[0].relief*0.85) };

    // ---- terrain built ENTIRELY by uplift + incision, with no authored summit ----
    // The uplift field is a smooth featureless blob; every ridge and valley in the result is residue
    // between channels. This is the workflow the whole node exists for.
    const residue = streamPowerErode(flat,{Kdt:0.6,Udt:0.004,m:0.5,iters:140,uplift:blob,Ddt:0.10});
    const lapOf = (f) => { let s2=0,c=0,hi=0;
      for (const v of f) if (v>hi) hi=v;
      for (let y=1;y<n-1;y++) for (let x=1;x<n-1;x++){ const i=y*n+x;
        s2 += Math.abs(4*f[i]-f[i-1]-f[i+1]-f[i-n]-f[i+n]); c++; }
      return +((s2/c)/(hi||1)).toFixed(4); };
    out.terrainFromUpliftAlone = {
      upliftFieldTexture: lapOf(blob), carvedTexture: lapOf(residue),
      // the input carries essentially no structure; the output is all structure
      structureIsEmergent: lapOf(residue) > 20 * lapOf(blob),
      hasRelief: (()=>{ let hi=0; for(const v of residue) if(v>hi) hi=v; return hi > 0.02; })() };

    // ---- D/K sets DRAINAGE DENSITY, and past a point there is no fluvial domain left ----
    // Modest diffusion leaves the fluvial scaling intact; heavy diffusion does not "contaminate the
    // fit", it erases the channel network outright. Raising the area threshold to escape it makes
    // the fit worse, not better, which is how the distinction was settled: at Ddt 0.08 the largest
    // drainage area is 707 cells against 3969 with no diffusion, and above A=1000 there are zero
    // channel cells to fit. Higher D means fewer, longer hillslopes and a sparser network -- the
    // textbook D/K competition, not a bug.
    const dk = [0, 0.01, 0.08, 0.25]  /* heavy rung raised: 0.08 only thins heads 11%, which is not the 'erases the network' regime the gate names; ridge relaxation needs ~0.18+ to even triple (see hillslopeDiffusion) */.map(Ddt => {
      const h = streamPowerErode(h0,{Kdt:2,Udt:2,m:0.5,iters:400,Ddt});
      const hf = priorityFloodFill(h); const { rec } = spReceivers(hf,1);
      const A = new Float32Array(n*n).fill(1);
      const o = Array.from({length:n*n},(_,i)=>i).sort((a,b)=>hf[b]-hf[a]);
      for (const i of o) if (rec[i]>=0) A[rec[i]] += A[i];
      let maxA=0; for (const v of A) if (v>maxA) maxA=v;
      // CHANNEL HEADS, not channel cells: on a spanning tree the count of cells above a fixed A is
      // close to a topological invariant (measured flat at 1509-1565 across a 8x range of D), so it
      // cannot express drainage density. Valley-initiation count can: a head is a channel cell with
      // no channelised donor, and diffusion widens valley spacing - fewer, wider valleys (Perron's
      // spacing result). Heads are what D controls.
      const CH=8; const isCh=new Uint8Array(A.length); for(let i2=0;i2<A.length;i2++) isCh[i2]=A[i2]>=CH?1:0;
      const hasChDonor=new Uint8Array(A.length);
      for(let i2=0;i2<A.length;i2++){ const r2=rec[i2]; if(r2>=0&&isCh[i2]) hasChDonor[r2]=1; }
      let headCount=0; for(let i2=0;i2<A.length;i2++) if(isCh[i2]&&!hasChDonor[i2]) headCount++;
      return { Ddt, maxDrainageArea:Math.round(maxA), headCount, fit:fitSlopeArea(h,0.5) }; });
    // Drainage DENSITY is channel length per area - proxied by the count of cells above a fixed
    // accumulation threshold. The previous proxy, the LARGEST catchment area, moves the wrong way:
    // diffusion merges basins, so max catchment can GROW (measured 1365 -> 1613) while the network
    // genuinely thins. Two gates sat false for the lifetime of the script because of that proxy
    // (and because the script never gated at all).
    out.diffusionSetsDrainageDensity = {
      byD: dk.map(q=>({Ddt:q.Ddt, headCount:q.headCount, maxDrainageArea:q.maxDrainageArea,
                       slope:q.fit.slope, r2:q.fit.r2})),
      // Two regimes, two statistics - measured, not assumed. Head count expresses valley SPACING
      // while a network exists (554 -> 491 across the organized rungs), but INVERTS once the
      // network shatters: every isolated A>=8 fragment becomes its own 'head' (measured 637 at
      // Ddt=0.25, above the D=0 count). So the monotone gate covers the organized rungs only, and
      // 'erased' is gated on what erasure actually means: the slope-area scaling itself collapses
      // (r2 0.60 organized -> below 0.25 when no coherent fluvial network remains).
      networkShrinksWithDiffusion: dk.slice(0,3).every((q,i)=> i===0 || q.headCount <= dk[i-1].headCount*1.05),
      modestDiffusionKeepsTheScaling: dk[1].fit.withinReferenceTolerance,
      heavyDiffusionErasesTheNetwork: dk[3].fit.r2 < 0.25 };
    // ---- THE SLOPE DISTRIBUTION MUST LOOK LIKE REAL TERRAIN ----
    // The strongest grounded check available: compare against the embedded real SRTM tile rather
    // than against judgement. It caught what "spiky and erratic" actually was -- a landscape that
    // was 90% dead flat with razor blades in the top 1%, slope median 0 and p90 0.47 against the
    // real tile's 2.45 and 9.26, with a maximum twice anything real.
    const nd = makeNode("import",0,0);
    await new Promise(res => { loadImageAsDEM(nd, REAL_DEM_SAMPLE, "");
      const t = setInterval(()=>{ if (nd._dem){ clearInterval(t); res(); } }, 200); });
    const realDem = TYPES.import.eval({scale:1},[],nd);
    // normalise each field to relief 1 first, so this compares SHAPE not amplitude
    const slopeQuantiles = (f) => { let lo=1e9,hi=-1e9; for (const v of f){ if(v<lo)lo=v; if(v>hi)hi=v; }
      const d=(hi-lo)||1, arr=[];
      for (let y=1;y<n-1;y++) for (let x=1;x<n-1;x++){ const i=y*n+x;
        arr.push(Math.hypot(((f[i+1]-f[i-1])/d)*n/2, ((f[i+n]-f[i-n])/d)*n/2)); }
      arr.sort((a,b2)=>a-b2);
      const q=(t)=>+arr[Math.floor(arr.length*t)].toFixed(2);
      return { median:q(0.5), p90:q(0.9), p99:q(0.99), max:+arr[arr.length-1].toFixed(1) }; };
    const up = TYPES.tectonic.eval({seed:3, plates:10, warp:0.5, orogen:0.30,
                                    ocean:0.4, land:0.45, output:"orogen"});
    const sp = TYPES.streampower.params.reduce((a,q)=>(a[q.key]=q.def,a),{});
    const built = streamPowerErode(newField(0), {Kdt:sp.strength*2.0, Udt:0.004, m:sp.m,
                                                 iters:180, uplift:up, Ddt:sp.hillslope*0.24});
    const R = slopeQuantiles(realDem), M = slopeQuantiles(built);
    out.slopeDistributionVsRealDEM = { realSRTM:R, atShippedDefaults:M,
      // within ~2 units at every percentile, on a scale where the failure mode read 0 vs 2.45
      p90Close: Math.abs(M.p90-R.p90) < 2.5,
      p99Close: Math.abs(M.p99-R.p99) < 2.5,
      maxNotRazor: M.max < R.max * 1.35,
      notFlat: M.median > R.median * 0.5 };
    RES=savedWorkingRes;return out;
  });

  console.log(JSON.stringify(r, null, 2));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  // The verdicts below existed for a long time while the script exited solely on page errors -
  // a vacuous oracle that stayed green through a measured slope-area regression (exponent -0.310,
  // r2 0.05, caused by the routing epsilon reaching the implicit solve). Every verdict now gates.
  const ss=r.steadyState.map(q=>q.slope);
  const gates={
    slopeArea_m04: r['slopeArea_m0.4'].withinReferenceTolerance,
    slopeArea_m05: r['slopeArea_m0.5'].withinReferenceTolerance,
    slopeArea_m06: r['slopeArea_m0.6'].withinReferenceTolerance,
    steadyStateStable: Math.max(...ss)-Math.min(...ss) <= 0.05,
    keptRelief: r.carvesWithoutFlattening.keptRelief,
    defaultsKeepMostRelief: r.defaultsAreSafe.keepsMostRelief,
    defaultsActuallyCarve: r.defaultsAreSafe.actuallyCarves,
    noNegatives: r.noNegatives.clean,
    finite: r.invariants.finite && r.invariants.maxEdgeHeight===0,
    ridgesRelaxMonotonically: r.hillslopeDiffusion.ridgesRelaxMonotonically,
    reliefPreservedUnderDiffusion: r.hillslopeDiffusion.reliefPreserved,
    structureIsEmergent: r.terrainFromUpliftAlone.structureIsEmergent && r.terrainFromUpliftAlone.hasRelief,
    networkShrinksWithDiffusion: r.diffusionSetsDrainageDensity.networkShrinksWithDiffusion,
    modestDiffusionKeepsTheScaling: r.diffusionSetsDrainageDensity.modestDiffusionKeepsTheScaling,
    heavyDiffusionErasesTheNetwork: r.diffusionSetsDrainageDensity.heavyDiffusionErasesTheNetwork,
    p90Close: r.slopeDistributionVsRealDEM.p90Close,
    p99Close: r.slopeDistributionVsRealDEM.p99Close,
    maxNotRazor: r.slopeDistributionVsRealDEM.maxNotRazor,
    notFlat: r.slopeDistributionVsRealDEM.notFlat,
    // Reported, not gated: drainageConcentrates (its half-flow-fraction proxy moves the wrong way
    // on raw noise, whose few deep pits concentrate flow artificially); invariants.cellsBelowTheirReceiver
    // (corpus: count clamp events and watch for growth, not a fixed bound).
  };
  const failed=Object.entries(gates).filter(([,v])=>!v).map(([k])=>k);
  if(failed.length)console.error('GATES FAILED:',failed.join(', '));
  process.exit(errors.length||failed.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
