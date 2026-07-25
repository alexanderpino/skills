// Stream power is verified by the slope-area relation, not by eye: at steady state
// U = K*A^m*S^n gives S ~ A^(-m/n), a straight line of slope -m/n on log-log.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
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
    return out;
  });

  console.log(JSON.stringify(r, null, 2));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
