// Is our Mountain a coherent landform, or merely noise on a cone? Judge primary topology,
// multi-scale dissection, asymmetry, independent generator families, controls and scale behaviour.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    const savedWorkingRes=RES;RES=192; // fixed analysis oracle; independent of the studio's default working resolution
    const n = RES;

    // --- TOPOGRAPHIC PROMINENCE via descending flood + union-find ---------------------------
    // Process cells high->low. Union with already-flooded neighbours. When two distinct basins
    // merge at elevation s, the LOWER of the two summits is closed off: its prominence is
    // summit - s (s is the key saddle). The global summit's prominence is its full relief.
    const prominence = (f) => {
      const idx = Array.from({length:n*n}, (_,i)=>i).sort((a,b)=>f[b]-f[a]);
      const parent = new Int32Array(n*n).fill(-1);      // -1 = not yet flooded
      const summit = new Float64Array(n*n);
      const find = (x) => { while (parent[x]!==x) { parent[x]=parent[parent[x]]; x=parent[x]; } return x; };
      const proms = [];
      let lo = Infinity; for (const v of f) if (v<lo) lo=v;
      for (const i of idx) {
        const x = i%n, y = (i/n)|0;
        const nb = [];
        if (x>0)   nb.push(i-1);
        if (x<n-1) nb.push(i+1);
        if (y>0)   nb.push(i-n);
        if (y<n-1) nb.push(i+n);
        parent[i] = i; summit[i] = f[i];               // new basin, provisionally its own summit
        for (const j of nb) {
          if (parent[j] === -1) continue;              // not flooded yet (lower) -- skip
          const a = find(i), c = find(j);
          if (a === c) continue;
          const sa = summit[a], sc = summit[c];
          // the lower summit dies here; f[i] is the saddle elevation
          if (sa >= sc) { proms.push(sc - f[i]); parent[c] = a; summit[a] = sa; }
          else          { proms.push(sa - f[i]); parent[a] = c; summit[c] = sc; }
        }
      }
      let hi = -Infinity; for (const v of f) if (v>hi) hi=v;
      proms.push(hi - lo);                             // the global summit
      proms.sort((a,b)=>b-a);
      const relief = hi - lo;
      return { relief, proms,
               // how many summits are REAL features rather than texture
               nAbove10pct: proms.filter(v=>v > 0.10*relief).length,
               nAbove25pct: proms.filter(v=>v > 0.25*relief).length,
               // is there one clearly dominant summit? 2nd/1st prominence ratio
               secondOverFirst: +(proms[1]/proms[0]).toFixed(3) };
    };

    const hypso = (f) => { let lo=1e9,hi=-1e9,s=0;
      for (const v of f){ if(v<lo)lo=v; if(v>hi)hi=v; s+=v; }
      return +(((s/f.length)-lo)/((hi-lo)||1)).toFixed(3); };   // cone~0.33, symmetric noise~0.5

    // radial mean height from the highest cell -- a peak descends monotonically, a massif plateaus
    const radial = (f) => {
      let bi=0; for (let i=1;i<f.length;i++) if (f[i]>f[bi]) bi=i;
      const bx=bi%n, by=(bi/n)|0, K=10, sum=new Float64Array(K), cnt=new Float64Array(K);
      const rmax = n*0.5;
      for (let y=0;y<n;y++) for (let x=0;x<n;x++){
        const d = Math.hypot(x-bx, y-by); if (d>=rmax) continue;
        const k = Math.min(K-1, (d/rmax*K)|0); sum[k]+=f[y*n+x]; cnt[k]++; }
      const prof = Array.from(sum, (v,i)=>+(v/Math.max(cnt[i],1)).toFixed(3));
      let mono = true; for (let i=1;i<K;i++) if (prof[i] > prof[i-1]+1e-6) mono = false;
      return { profile: prof, monotonicDescent: mono };
    };

    const score = (f) => { const pr = prominence(f);
      return { hypsometric: hypso(f), summitsAbove10pct: pr.nAbove10pct,
               summitsAbove25pct: pr.nAbove25pct, secondOverFirst: pr.secondOverFirst,
               radial: radial(f) }; };

    const out = {};
    const cone = (()=>{ const o=newField();
      for (let y=0;y<n;y++) for (let x=0;x<n;x++)
        o[y*n+x] = Math.max(0, 1 - Math.hypot(x/n-0.5, y/n-0.5)*2); return o; })();
    // Build from the node's DECLARED defaults, not a hand-copied list. The hand-copied version had
    // drifted -- it still said relief 0.66 after the default moved to 0.80, and never passed
    // `character` at all, so the solid-of-revolution probe below was silently measuring the domain
    // warp switched off. A harness that restates defaults will always drift away from them.
    const DEF = Object.fromEntries(TYPES.mountain.params.map(q=>[q.key,
      Array.isArray(q.def) ? JSON.parse(JSON.stringify(q.def)) : q.def]));
    const M = (o) => TYPES.mountain.eval({...DEF, form:"peak", style:"eroded", seed:7,
                     x:0.5, y:0.5, size:0.35, ...o});

    // --- the two reference extremes, so the numbers below have a scale ---
    out.reference = { cone: score(cone),
                      ridgedNoise: score(fbmField(gnoise,{seed:7,freq:5,octaves:6,lac:2.1,gain:0.55,ridge:true})) };

    // --- SUMMIT TOPOLOGY depends on the selected generator family. ---------------------------
    const peaks = {};
    for (const style of ["basic","eroded","alpine","old","strata"]) peaks[style] = score(M({style}));
    for (const seed of [3,11,29]) peaks["seed"+seed] = score(M({seed}));
    const dominant=score(M({shape:"dominant"})),compound=score(M({shape:"compound"}));
    // Dominant Peak should retain one clear hero summit. Compound Peaks deliberately admits several
    // nearby highs and saddles, but must remain far below the topology of unbounded ridged noise.
    out.peakTopology = {
      summitCounts: Object.fromEntries(Object.entries(peaks).map(([k,v])=>[k, v.summitsAbove10pct])),
      worstSecondOverFirst: +Math.max(...Object.values(peaks).map(v=>v.secondOverFirst)).toFixed(3),
      mostSummits: Math.max(...Object.values(peaks).map(v=>v.summitsAbove10pct)),
      dominantPeak:{summits:dominant.summitsAbove10pct,secondOverFirst:dominant.secondOverFirst},
      compoundPeaks:{summits:compound.summitsAbove10pct,secondOverFirst:compound.secondOverFirst},
      dominantHasClearHero:dominant.secondOverFirst < .25,
      compoundAllowsShoulders:compound.summitsAbove10pct >= dominant.summitsAbove10pct,
      coherentNotNoise:Object.values(peaks).every(v=>v.secondOverFirst < .40&&v.summitsAbove10pct <= 10),
      allDescendMonotonically: Object.values(peaks).every(v=>v.radial.monotonicDescent) };

    // --- a MASSIF is deliberately several summits: the contrast is the point ---
    const massif = score(M({form:"massif"}));
    out.massifIsSeveralSummits = { summits: massif.summitsAbove10pct,
      secondOverFirst: massif.secondOverFirst,
      moreSummitsThanPeak: massif.summitsAbove10pct > peaks.eroded.summitsAbove10pct };

    // --- DISSECTION is what makes it read as a mountain, not the macro topology ---
    // A cone satisfies every prominence test above. What it fails is having any texture at all,
    // which is how a smooth pyramid passed an earlier version of this file: the statistics were
    // fine, the thing looked like a pile of sand. Measure texture directly, per unit height so the
    // metric is scale free, and only inside the footprint.
    const fineDetail = (f) => { let s=0,c=0,mx=0;
      for (let y=1;y<n-1;y++) for (let x=1;x<n-1;x++){ const i=y*n+x; if (f[i]<=0) continue;
        if (f[i]>mx) mx=f[i];
        s += Math.abs(4*f[i]-f[i-1]-f[i+1]-f[i-n]-f[i+n]); c++; }
      return +((s/Math.max(c,1))/(mx||1)).toFixed(5); };
    const coneDetail = fineDetail(cone), peakDetail = fineDetail(M({}));
    const upperDetail = (f) => { let mx=0;for(const v of f)if(v>mx)mx=v;let s=0,c=0;
      for(let y=1;y<n-1;y++)for(let x=1;x<n-1;x++){const i=y*n+x;if(f[i]<mx*.55)continue;
        s+=Math.abs(4*f[i]-f[i-1]-f[i+1]-f[i-n]-f[i+n]);c++;}
      return +((s/Math.max(c,1))/(mx||1)).toFixed(5); };
    const fieldDifference = (a,b) => { let s=0,c=0,mx=0;
      for(let i=0;i<a.length;i++){mx=Math.max(mx,a[i],b[i]);if(a[i]>0||b[i]>0){s+=Math.abs(a[i]-b[i]);c++;}}
      return +(s/Math.max(c*mx,1e-9)).toFixed(4); };
    out.dissection = { cone: coneDetail, peak: peakDetail,
      ratioVsCone: +(peakDetail/Math.max(coneDetail,1e-6)).toFixed(1),
      upperCrag:upperDetail(M({})),coneUpper:upperDetail(cone),
      // a smooth cone is essentially featureless; a dissected dome must be far above it
      farMoreTexturedThanACone: peakDetail > 8 * coneDetail };

    // Shape family and Mountain type must change generating geometry, not just labels or materials.
    // Weather is disabled here so a pass-specific overprint cannot manufacture the distinction.
    const shapeFields=Object.fromEntries(["dominant","compound","ridge","broad"].map(shape=>
      [shape,M({shape,style:"basic",weather:0})]));
    const typeFields=Object.fromEntries(["basic","eroded","old","alpine","strata"].map(style=>
      [style,M({shape:"compound",style,weather:0})]));
    const pairwise=(fields)=>{
      const names=Object.keys(fields),d={};let least=Infinity;
      for(let i=0;i<names.length;i++)for(let j=i+1;j<names.length;j++){
        const k=names[i]+" / "+names[j],v=fieldDifference(fields[names[i]],fields[names[j]]);
        d[k]=v;least=Math.min(least,v);}
      return{differences:d,leastDifference:+least.toFixed(4)};};
    const shapePairs=pairwise(shapeFields),typePairs=pairwise(typeFields);
    out.generatorFamilies={
      shapes:shapePairs,
      types:typePairs,
      typeFineEnergy:Object.fromEntries(Object.entries(typeFields).map(([k,v])=>[k,fineDetail(v)])),
      allShapesDistinct:shapePairs.leastDifference>.025,
      allTypesDistinct:typePairs.leastDifference>.018,
      alpineSharperThanBasic:fineDetail(typeFields.alpine)>fineDetail(typeFields.basic)*1.25,
      oldRounderThanAlpine:fineDetail(typeFields.old)<fineDetail(typeFields.alpine)*.75
    };

    // Drainage detail must genuinely control density. Measured on a style with NO erosion, because
    // an eroded style overprints the network with its own texture and masks the parameter's effect
    // -- on `eroded` this same sweep reads flat, which is a fact about erosion, not about the knob.
    const sweep = [0.6, 1.4, 2.2, 3.4].map(d =>
      ({ detail:d, fine: fineDetail(M({style:"basic", detail:d})) }));
    // Density must rise across the full authored range. Separate meso-cell and fracture bands keep
    // the control from saturating when its finest structures approach the talus scale.
    out.detailControlsDensity = { sweep,
      monotonicAcrossRange: sweep.every((v,i)=> i===0 || v.fine > sweep[i-1].fine),
      fullRangeSpan: +(sweep[sweep.length-1].fine / sweep[0].fine).toFixed(1),
      overprintedByErosion: (()=>{ const a=fineDetail(M({style:"eroded",detail:0.6}));
        const b2=fineDetail(M({style:"eroded",detail:3.4}));
        return { at0_6:a, at3_4:b2, ratio:+(b2/a).toFixed(2) }; })() };

    // --- THE SKIRT: a mountain profile has distinct upper-crag, shoulder, face and apron bands. ---
    // A constant-slope radial ramp is literally a tent. Measure the declared default curve itself
    // so cellular detail cannot hide a regressed cone.
    const profile = (skirt) => Array.from({length:41}, (_,k)=> Math.pow(1-k/40, skirt));
    const slopes = (pr) => pr.slice(1).map((v,i)=> (v-pr[i])*40);
    const cv = (a) => {const q=a.map(Math.abs),m=q.reduce((s,v)=>s+v,0)/q.length;
      return Math.sqrt(q.reduce((s,v)=>s+(v-m)**2,0)/q.length)/(m||1);};
    const bell = Array.from({length:41}, (_,k)=> Math.pow(1-(k/40)**2, 1.25));
    const tent=profile(1),sk=Array.from({length:41},(_,k)=>curveAt(bakeCurve(DEF.skirt),k/40));
    out.skirt = {
      bellSlopeAtSummit:  +slopes(bell)[0].toFixed(3),
      skirtSlopeAtSummit: +slopes(sk)[0].toFixed(3),
      skirtSlopeAtEdge:   +slopes(sk)[slopes(sk).length-1].toFixed(3),
      tentSlopeVariation:+cv(slopes(tent)).toFixed(3),
      mountainSlopeVariation:+cv(slopes(sk)).toFixed(3),
      hasBrokenSlopeBands:cv(slopes(sk))>.40,
      reachesZeroAtRim: sk[sk.length-1] === 0 };

    // --- IT MUST NOT BE A SOLID OF REVOLUTION ---
    // Raw correlation was a bad measurement: the radial bulk dominates it even when the shoulders
    // are strongly asymmetric. Score the mid-elevation contour and normalised L1 difference against
    // a 90-degree rotation instead. A cone has IoU≈1 and L1≈0; Character must lower the contour
    // overlap and raise the difference without needing noisy high-frequency texture.
    const rotShape = (f) => { let hi=0;for(const v of f)if(v>hi)hi=v;
      let inter=0,uni=0,diff=0,sum=0;
      for(let y=0;y<n;y++)for(let x=0;x<n;x++){
        const a=f[y*n+x],b2=f[x*n+(n-1-y)],aa=a>hi*.42,bb=b2>hi*.42;
        if(aa||bb)uni++;if(aa&&bb)inter++;diff+=Math.abs(a-b2);sum+=Math.max(a,b2);}
      return {contourIoU:+(inter/Math.max(uni,1)).toFixed(3),relativeL1:+(diff/Math.max(sum,1e-9)).toFixed(3)}; };
    const byCharacter=Object.fromEntries([0,.3,DEF.character,.9].map(c=>
      [c,rotShape(M({character:c,variation:0,weather:0}))]));
    out.notASolidOfRevolution = { cone:rotShape(cone), byCharacter,
      asymmetricAtDefault:byCharacter[DEF.character].relativeL1>.18,
      characterDrivesIt:byCharacter[.9].relativeL1>byCharacter[0].relativeL1*1.45 };

    // --- THE MASK MUST NOT FORCE EVERY MOUNTAIN INTO ONE SHAPE ---
    // With reach, aspect and rotation fixed, the seed only displaces noise inside a footprint whose
    // proportions never change. Measured before this was fixed: across six seeds, elongation stayed
    // between 1.03 and 1.26 -- six variations on one circle. Second moments of the support give
    // area, elongation and orientation without any reference to height.
    const footprint = (f) => {
      let sx=0, sy=0, w=0;
      for (let y=0;y<n;y++) for (let x=0;x<n;x++){ if (f[y*n+x]<=0) continue; sx+=x; sy+=y; w++; }
      if (w < 10) return null;
      const fx=sx/w, fy=sy/w; let xx=0, yy=0, xy=0;
      for (let y=0;y<n;y++) for (let x=0;x<n;x++){ if (f[y*n+x]<=0) continue;
        const dx=x-fx, dy=y-fy; xx+=dx*dx; yy+=dy*dy; xy+=dx*dy; }
      xx/=w; yy/=w; xy/=w;
      const tr=xx+yy, det=xx*yy-xy*xy, disc=Math.sqrt(Math.max(tr*tr/4-det,0));
      return { area:w/(n*n), elongation:Math.sqrt((tr/2+disc)/Math.max(tr/2-disc,1e-9)),
               orientation:(Math.atan2(2*xy,xx-yy)/2)*180/Math.PI }; };
    const SEEDS = [3,7,11,29,101,777,1234,5150,9001,424242];
    const survey = (V) => { const fp = SEEDS.map(seed => footprint(M({seed, variation:V})));
      const el = fp.map(q=>q.elongation), ar = fp.map(q=>q.area), or = fp.map(q=>q.orientation);
      const sp = (v) => { const m=v.reduce((a,x)=>a+x,0)/v.length;
        return Math.sqrt(v.reduce((a,x)=>a+(x-m)**2,0)/v.length)/Math.abs(m); };
      return { elongationRange:[+Math.min(...el).toFixed(2), +Math.max(...el).toFixed(2)],
               areaSpread:+sp(ar).toFixed(3), elongationSpread:+sp(el).toFixed(3),
               orientationRangeDeg:+(Math.max(...or)-Math.min(...or)).toFixed(0) }; };
    const v0 = survey(0), vDef = survey(DEF.variation), v1 = survey(1);
    out.maskDoesNotForceOneShape = { atVariation0:v0, atDefault:vDef, atVariation1:v1,
      // at 0 you get exactly the proportions you authored; the knob has to actually widen them
      variationWidensShapes: v1.elongationSpread > v0.elongationSpread * 1.5,
      areaVariesMore: v1.areaSpread > v0.areaSpread * 1.5,
      someMassifIsElongated: v1.elongationRange[1] > 1.6 };

    // --- the primitive must stay inside its own footprint, so it composites cleanly ---
    const f = M({x:0.5, y:0.5, size:0.25});
    let outside = 0, inside = 0;
    for (let y=0;y<n;y++) for (let x=0;x<n;x++){
      const r = Math.hypot((x+0.5)/n-0.5, (y+0.5)/n-0.5);
      if (r > 0.25*1.55) outside += Math.abs(f[y*n+x]);      // beyond any wobbled reach
      else inside += f[y*n+x]; }
    out.staysInsideFootprint = { totalOutside:+outside.toExponential(2), totalInside:+inside.toFixed(1),
                                 clean: outside === 0 && inside > 0 };

    // --- COMMERCIAL-GRADE CONTROL SURFACE: every exposed control must own one independent axis ---
    const sumField=f=>{let s=0;for(const v of f)s+=v;return s;};
    const peakOf=f=>{let m=-Infinity;for(const v of f)if(v>m)m=v;return m;};
    const h05=M({height:.5,weather:0}),h10=M({height:1,weather:0});
    const bulkLow=M({bulk:"low",weather:0}),bulkHigh=M({bulk:"high",weather:0});
    const detailFull=M({reduce:0,style:"alpine",weather:0}),detailReduced=M({reduce:1,style:"alpine",weather:0});
    out.productionControls = {
      heightIsLinear:+(peakOf(h05)/peakOf(h10)).toFixed(3),
      highBulkHasMoreMass:sumField(bulkHigh)>sumField(bulkLow)*1.25,
      reduceDetailsLowersFineEnergy:fineDetail(detailReduced)<fineDetail(detailFull)*.82,
      weatheringChangesSurface:(()=>{const a=M({weather:0}),b2=M({weather:2});let d=0;
        for(let i=0;i<a.length;i++)d+=Math.abs(a[i]-b2[i]);return d>1;})()
    };

    // Same world, twice the build resolution: macro structure must stay put. Weathering remains on,
    // so this covers the resolution-scaled droplet brush and per-cell talus threshold as well as the
    // analytic generator. Box-downsample 384² back to the 192² preview for the comparison.
    const lowRes=M({}),oldRes=RES;RES=384;
    const highRes=TYPES.mountain.eval({...DEF,form:"peak",style:"eroded",seed:7,x:.5,y:.5,size:.35});
    RES=oldRes;let se=0,maxAbs=0;
    for(let y=0;y<n;y++)for(let x=0;x<n;x++){let v=0;
      for(let j=0;j<2;j++)for(let i=0;i<2;i++)v+=highRes[(y*2+j)*384+x*2+i];
      const d=lowRes[y*n+x]-v*.25;se+=d*d;maxAbs=Math.max(maxAbs,Math.abs(d));}
    const rawRms=Math.sqrt(se/(n*n)),rawMaxAbs=maxAbs,coarse=n/4;se=0;maxAbs=0;
    for(let y=0;y<coarse;y++)for(let x=0;x<coarse;x++){let a=0,b2=0;
      for(let j=0;j<4;j++)for(let i=0;i<4;i++)a+=lowRes[(y*4+j)*n+x*4+i];
      for(let j=0;j<8;j++)for(let i=0;i<8;i++)b2+=highRes[(y*8+j)*384+x*8+i];
      const d=a/16-b2/64;se+=d*d;maxAbs=Math.max(maxAbs,Math.abs(d));}
    out.resolutionConsistency={rms:+Math.sqrt(se/(coarse*coarse)).toFixed(5),
      maxAbs:+maxAbs.toFixed(5),rawRms:+rawRms.toFixed(5),rawMaxAbs:+rawMaxAbs.toFixed(5)};

    RES=savedWorkingRes;return out;
  });

  console.log(JSON.stringify(r, null, 2));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  const failed = [
    ["coherent summit topology",r.peakTopology.dominantHasClearHero&&
      r.peakTopology.compoundAllowsShoulders&&r.peakTopology.coherentNotNoise],
    ["monotonic macro descent",r.peakTopology.allDescendMonotonically],
    ["four shape generators",r.generatorFamilies.allShapesDistinct],
    ["five mountain types",r.generatorFamilies.allTypesDistinct&&
      r.generatorFamilies.alpineSharperThanBasic&&r.generatorFamilies.oldRounderThanAlpine],
    ["connected detail control",r.detailControlsDensity.monotonicAcrossRange&&r.detailControlsDensity.fullRangeSpan>1.25],
    ["not a tipi",r.skirt.hasBrokenSlopeBands&&r.dissection.upperCrag>r.dissection.coneUpper*8],
    ["asymmetric character",r.notASolidOfRevolution.asymmetricAtDefault&&r.notASolidOfRevolution.characterDrivesIt],
    ["shape variation",r.maskDoesNotForceOneShape.variationWidensShapes&&r.maskDoesNotForceOneShape.areaVariesMore],
    ["bounded footprint",r.staysInsideFootprint.clean],
    ["height control",Math.abs(r.productionControls.heightIsLinear-.5)<.01],
    ["bulk control",r.productionControls.highBulkHasMoreMass],
    ["detail reduction",r.productionControls.reduceDetailsLowersFineEnergy],
    ["weathering control",r.productionControls.weatheringChangesSurface],
    ["resolution consistency",r.resolutionConsistency.rms<.009&&r.resolutionConsistency.maxAbs<.055],
  ].filter(([,ok])=>!ok).map(([name])=>name);
  if(failed.length)console.error("FAILED CONTRACTS:",failed.join(", "));
  await b.close();
  process.exit(errors.length||failed.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
