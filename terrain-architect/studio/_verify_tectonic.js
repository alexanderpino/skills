// Voronoi plates as the structural skeleton: warped boundaries, classified uplift diffused inland,
// then handed to stream power so the rivers make the topography.
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
    const T = (o) => TYPES.tectonic.eval({seed:3, plates:10, warp:0.5, orogen:0.35,
                                          ocean:0.45, output:"orogen", ...o});

    // ---- 1. it produces a structured field, not a blur of nothing ----
    const base = T({});
    let lo=1e9, hi=-1e9; for (const v of base){ if(v<lo)lo=v; if(v>hi)hi=v; }
    const sorted = Array.from(base).sort((a,b)=>a-b);
    const q = (t) => +sorted[Math.floor(sorted.length*t)].toFixed(3);
    out.produces = { min:+lo.toFixed(3), max:+hi.toFixed(3), finite: base.every(v=>isFinite(v)),
                     hasRelief: hi-lo > 0.5,
                     quartiles:[q(0.25), q(0.5), q(0.75)],
                     // zero must mean zero: most of the tile is away from any belt and must get no
                     // uplift at all. Normalising a field with negative rift values broke this.
                     backgroundIsZero: q(0.25) === 0,
                     mostOfTileUnuplifted: sorted.filter(v=>v<0.05).length/sorted.length > 0.4 };

    // ---- 2. STRAIGHT VORONOI EDGES ARE THE TELL, so warping must move the boundaries ----
    // An earlier metric tried to score "straightness" by direction coherence along the belt crest
    // and could not discriminate at all (0.183 / 0.189 / 0.188 across the whole warp range). It was
    // measuring the wrong thing. What is defensible without a curvature model is DISPLACEMENT: warp
    // must relocate the belts, not merely perturb their amplitude.
    const beltMask = (f) => { let m=0; for (const v of f) if (v>m) m=v;
      const th=m*0.35, u=new Uint8Array(n*n);
      for (let i=0;i<n*n;i++) u[i] = f[i]>th ? 1 : 0; return u; };
    const b0 = beltMask(T({warp:0})), b1 = beltMask(T({warp:1}));
    let differ=0, either=0;
    for (let i=0;i<n*n;i++){ if (b0[i]||b1[i]) either++; if (b0[i]!==b1[i]) differ++; }
    out.warpMovesBoundaries = { beltCellsEither:either, cellsDiffering:differ,
      jaccardDistance:+(differ/Math.max(either,1)).toFixed(3),
      // Threshold set FROM the measurement, not before it: 0.167 at the original warp frequency and
      // 0.209 after matching the reference's, so 0.12 has real headroom without being invented. The
      // effect is genuine but modest -- warping displaces belts by roughly one belt width.
      warpRelocatesBelts: differ/Math.max(either,1) > 0.12,
      note:"displacement, not curvature -- the straightness metric it replaced had no signal at all" };

    // ---- 3. orogen width diffuses the belt inland: a mountain belt is a welt, not a line ----
    const spread = (f) => { let m=0; for (const v of f) if (v>m) m=v;
      let c=0; for (const v of f) if (v > m*0.25) c++; return +(c/(n*n)).toFixed(4); };
    const byOrogen = [0.1, 0.35, 0.8].map(o => ({ orogen:o, fracAboveQuarterPeak: spread(T({orogen:o})) }));
    out.orogenWidens = { byOrogen,
      monotonic: byOrogen.every((v,i)=> i===0 || v.fracAboveQuarterPeak > byOrogen[i-1].fracAboveQuarterPeak) };

    // ---- 4. more plates -> more boundary -> more belt ----
    const byPlates = [4, 10, 20].map(k => ({ plates:k, belt: spread(T({plates:k})) }));
    out.morePlatesMoreBoundary = { byPlates,
      increases: byPlates[2].belt > byPlates[0].belt };

    // ---- 5. THE POINT: hand it to stream power and get a landscape with a drainage network ----
    const flat = newField(0);
    const carved = streamPowerErode(flat, {Kdt:0.6, Udt:0.004, m:0.5, iters:180,
                                           uplift:T({orogen:0.30}), Ddt:0.08});
    const hf = priorityFloodFill(carved); const { rec } = spReceivers(hf,1);
    const A = new Float32Array(n*n).fill(1);
    const ord = Array.from({length:n*n},(_,i)=>i).sort((a,b)=>hf[b]-hf[a]);
    for (const i of ord) if (rec[i]>=0) A[rec[i]] += A[i];
    let maxA=0; for (const v of A) if (v>maxA) maxA=v;
    const lapOf = (f) => { let s2=0,c=0,m2=0; for (const v of f) if (v>m2) m2=v;
      for (let y=1;y<n-1;y++) for (let x=1;x<n-1;x++){ const i=y*n+x;
        s2 += Math.abs(4*f[i]-f[i-1]-f[i+1]-f[i-n]-f[i+n]); c++; }
      return +((s2/c)/(m2||1)).toFixed(4); };
    // compare texture only WHERE THERE IS TERRAIN: most of the tile now gets no uplift at all, and
    // averaging the smooth zero background into both sides understates the contrast
    const up = T({orogen:0.30});
    const lapWhere = (f, sel) => { let s2=0,c=0,m2=0; for (const v of f) if (v>m2) m2=v;
      for (let y=1;y<n-1;y++) for (let x=1;x<n-1;x++){ const i=y*n+x; if (!sel[i]) continue;
        s2 += Math.abs(4*f[i]-f[i-1]-f[i+1]-f[i-n]-f[i+n]); c++; }
      return +((s2/Math.max(c,1))/(m2||1)).toFixed(4); };
    const inBelt = new Uint8Array(n*n);
    { let m=0; for (const v of up) if (v>m) m=v;
      for (let i=0;i<n*n;i++) inBelt[i] = up[i] > m*0.15 ? 1 : 0; }
    out.drivesStreamPower = { upliftTextureInBelt: lapWhere(up, inBelt),
      carvedTextureInBelt: lapWhere(carved, inBelt),
      ratio: +(lapWhere(carved,inBelt)/Math.max(lapWhere(up,inBelt),1e-9)).toFixed(1),
      maxDrainageArea: Math.round(maxA),
      // measured between 4.8x and 6.5x across warp settings, so 3x is the honest floor; a tighter
      // bound was tracking one realisation rather than the effect
      structureIsEmergent: lapWhere(carved,inBelt) > 3 * lapWhere(up,inBelt),
      hasRealDrainageNetwork: maxA > 500 };
    return out;
  });

  console.log(JSON.stringify(r, null, 2));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
