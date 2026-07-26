// The art-direction layer: vector shapes carrying PER-VERTEX elevation, which is what turns a drawn
// line into a ridgeline. Plus the peak-as-ridge-junction rebuild it shares an evaluator with.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    const n = RES, out = {};
    const at = (f,u,v) => f[Math.min(n-1,Math.round(v*n))*n + Math.min(n-1,Math.round(u*n))];
    const L = (spec, base) => TYPES.layout.eval({spec, height:1}, [base||null, null], {});

    // ---- 1. the parser ----
    const sh = parseLayout(`path width=0.02 falloff=0.3 profile=squared op=add breakup=0.5 seed=9
      0.1,0.2,0.3  0.4,0.5,0.6`);
    out.parser = { count: sh.length, kind: sh[0].kind, width: sh[0].width, falloff: sh[0].falloff,
                   profile: sh[0].profile, op: sh[0].op, breakup: sh[0].breakup,
                   verts: sh[0].pts.length, firstVert: sh[0].pts[0],
                   ok: sh.length===1 && sh[0].profile==="squared" && sh[0].op==="add" &&
                       sh[0].pts.length===2 && sh[0].pts[0][2]===0.3 };

    // ---- 2. PER-VERTEX ELEVATION: the height at each vertex must be what was authored ----
    const spine = L(`path width=0.01 falloff=0.18 profile=linear op=max
      0.15,0.5,0.30   0.35,0.5,0.90   0.55,0.5,0.45   0.75,0.5,1.00`);
    out.perVertexElevation = {
      atV1:+at(spine,0.15,0.5).toFixed(2), atV2:+at(spine,0.35,0.5).toFixed(2),
      atV3:+at(spine,0.55,0.5).toFixed(2), atV4:+at(spine,0.75,0.5).toFixed(2),
      asked:[0.30,0.90,0.45,1.00],
      matches: [[0.15,0.30],[0.35,0.90],[0.55,0.45],[0.75,1.00]]
        .every(([u,e]) => Math.abs(at(spine,u,0.5)-e) < 0.05),
      // and BETWEEN vertices it interpolates -- a ribbon at constant height would fail this
      midpointIsBetween: (()=>{ const m=at(spine,0.45,0.5); return m>0.45 && m<0.90; })() };

    // ---- 3. that spine must read as a RIDGE: summits at high vertices, saddles at low ones ----
    const along = []; for (let k=0;k<=100;k++) along.push(at(spine, 0.10+0.70*k/100, 0.5));
    let localMax=0, localMin=0;
    for (let k=2;k<along.length-2;k++){
      if (along[k]>along[k-2] && along[k]>=along[k+2]) localMax++;
      if (along[k]<along[k-2] && along[k]<=along[k+2]) localMin++; }
    out.readsAsARidge = { summitsAlongCrest:localMax, saddlesAlongCrest:localMin,
                          // height must FALL AWAY perpendicular to the crest
                          onCrest:+at(spine,0.75,0.5).toFixed(2),
                          offCrest:+at(spine,0.75,0.72).toFixed(2),
                          fallsAwayPerpendicular: at(spine,0.75,0.5) > at(spine,0.75,0.72) };

    // ---- 4. falloff profiles must actually differ ----
    const halfway = (prof) => at(L(`path width=0 falloff=0.30 profile=${prof} op=max
      0.5,0.2,1.0   0.5,0.8,1.0`), 0.65, 0.5);            // exactly halfway out the falloff
    out.falloffProfiles = Object.fromEntries(
      ["linear","squared","sqrt","scurve"].map(k=>[k, +halfway(k).toFixed(3)]));
    out.falloffProfiles.allDistinct =
      new Set(["linear","squared","sqrt","scurve"].map(k=>halfway(k).toFixed(3))).size === 4;
    out.falloffProfiles.orderedSqrtAboveSquared = halfway("sqrt") > halfway("squared");

    // ---- 5. ops, overlap rule, and Source vs Modifier ----
    const two = `path width=0.02 falloff=0.15 op=OP
      0.3,0.5,0.4   0.7,0.5,0.4
path width=0.02 falloff=0.15 op=OP
      0.5,0.3,0.9   0.5,0.7,0.9`;
    const crossMax = L(two.replace(/OP/g,"max"));
    out.overlapGreatestHeightWins = { atCrossing:+at(crossMax,0.5,0.5).toFixed(2),
                                      expectedAbout:0.9, ok: Math.abs(at(crossMax,0.5,0.5)-0.9)<0.06 };
    const bed = newField(0.25);
    const modifier = L(`path width=0.02 falloff=0.12 op=max\n  0.2,0.5,0.8  0.8,0.5,0.8`, bed);
    out.sourceVsModifier = {
      modifierKeepsBaseAwayFromShape:+at(modifier,0.5,0.95).toFixed(2),
      modifierRaisesOnShape:+at(modifier,0.5,0.5).toFixed(2),
      embedsRatherThanReplaces: Math.abs(at(modifier,0.5,0.95)-0.25)<0.01 && at(modifier,0.5,0.5)>0.7 };
    const subbed = L(`path width=0.03 falloff=0.10 op=sub\n  0.2,0.5,0.5  0.8,0.5,0.5`, bed);
    out.sourceVsModifier.subCarves = at(subbed,0.5,0.5) < 0.25;

    // ---- 6. polygons fill; breakup makes the outline non-geometric ----
    const sq = L(`poly falloff=0.02 op=max\n  0.3,0.3,0.7  0.7,0.3,0.7  0.7,0.7,0.7  0.3,0.7,0.7`);
    out.polygon = { inside:+at(sq,0.5,0.5).toFixed(2), outside:+at(sq,0.1,0.1).toFixed(2),
                    fills: at(sq,0.5,0.5)>0.65 && at(sq,0.1,0.1)<0.01 };
    const plain  = L(`path width=0.02 falloff=0.2 op=max breakup=0\n  0.2,0.5,1  0.8,0.5,1`);
    const broken = L(`path width=0.02 falloff=0.2 op=max breakup=0.8 seed=5\n  0.2,0.5,1  0.8,0.5,1`);
    let diff=0; for (let i=0;i<plain.length;i++) diff += Math.abs(plain[i]-broken[i]);
    out.breakupDistortsOutline = { meanAbsDiff:+(diff/plain.length).toFixed(4), differs: diff>0 };

    // ---- 7. the node in the graph, both wirings ----
    const nd = makeNode("layout",0,0); evalGraph();
    out.node = { shapesParsedFromDefault: nd._shapeCount, producesRelief:
      (()=>{ let lo=1e9,hi=-1e9; for(const v of nd._field){if(v<lo)lo=v;if(v>hi)hi=v;} return +(hi-lo).toFixed(2); })() };
    return out;
  });

  console.log(JSON.stringify(r, null, 2));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
