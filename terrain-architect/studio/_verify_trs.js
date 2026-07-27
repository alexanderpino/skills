// A proper transform is translate + rotate (about the UP axis) + scale, about a PIVOT, confinable by
// a mask -- and Stamp is the other half: it drops the placed feature onto a base.
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

  const r = await p.evaluate(() => {
    const out = {}, n = RES;
    const D = {mode:"auto", scale:1, aspect:1, angle:0, offX:0, offY:0, pivX:0.5, pivY:0.5, edge:"clamp"};
    // a small off-centre disc: its centroid is an unambiguous witness of where the feature went
    const disc = (cx, cy) => TYPES.shape.eval({kind:"circle", x:cx, y:cy, size:0.18, aspect:1,
                                               angle:0, falloff:0.02, invert:"off"});
    const centroid = f => { let sx=0, sy=0, w=0;
      for (let y=0;y<n;y++) for (let x=0;x<n;x++){ const v=f[y*n+x]; sx+=v*(x+0.5)/n; sy+=v*(y+0.5)/n; w+=v; }
      return w > 1e-9 ? [sx/w, sy/w] : [NaN, NaN]; };
    const near = (a, e, tol) => Math.abs(a-e) < tol;

    // ---- 1. TRANSLATE: the centroid must land exactly where asked ----
    const src = disc(0.5, 0.5);
    const moved = transformField(src, {...D, offX:0.2, offY:-0.1});
    const [mx, my] = centroid(moved);
    out.translate = { centroid:[+mx.toFixed(3), +my.toFixed(3)], expected:[0.7, 0.4],
                      ok: near(mx,0.7,0.01) && near(my,0.4,0.01) };

    // ---- 2. ROTATE about the up axis, around the PIVOT ----
    // A disc at (0.75,0.5) turned 90 deg about the tile centre must swing to (0.5,0.75) or (0.5,0.25).
    const off = disc(0.75, 0.5);
    const spun = transformField(off, {...D, angle:90});
    const [rx, ry] = centroid(spun);
    out.rotateAboutCentre = { centroid:[+rx.toFixed(3), +ry.toFixed(3)],
                              movedOffAxis: near(rx,0.5,0.02) && (near(ry,0.75,0.02)||near(ry,0.25,0.02)),
                              radiusPreserved: near(Math.hypot(rx-0.5, ry-0.5), 0.25, 0.02) };
    // ...and with the PIVOT on the disc itself, rotation must leave it where it is.
    const spunInPlace = transformField(off, {...D, angle:90, pivX:0.75, pivY:0.5});
    const [px2, py2] = centroid(spunInPlace);
    out.rotateAboutPivot = { centroid:[+px2.toFixed(3), +py2.toFixed(3)],
                             staysPut: near(px2,0.75,0.01) && near(py2,0.5,0.01) };

    // ---- 3. SCALE about the pivot. Documented semantics: >1 magnifies, <1 shrinks. Area is the
    //         square of the linear factor, so 2x -> 4x area and 0.5x -> 0.25x. ----
    const area = f => { let a=0; for (let i=0;i<f.length;i++) a += f[i]; return a/f.length; };
    const a0 = area(src);
    const up = area(transformField(src, {...D, scale:2}));
    const dn = area(transformField(src, {...D, scale:0.5}));
    out.scale = { areaBase:+a0.toFixed(4),
                  magnify2x:{ ratio:+(up/a0).toFixed(2), expected:4.0, ok: Math.abs(up/a0-4) < 0.25 },
                  shrink2x:{ ratio:+(dn/a0).toFixed(2), expected:0.25, ok: Math.abs(dn/a0-0.25) < 0.03 } };

    // ---- 4. exact and raster must describe the SAME placement, pivot included ----
    const gen = makeNode("perlin",0,0), t = makeNode("transform",0,0);
    edges.push({from:gen.id, to:t.id, slot:0});
    Object.assign(t.params, {scale:2, angle:35, offX:0.15, offY:-0.08, pivX:0.3, pivY:0.7});
    markDirtyFrom(gen.id); evalGraph();
    const exact = t._field.slice(); const modeA = t._xfMode;
    t.params.mode = "raster"; markDirtyFrom(t.id); evalGraph();
    const raster = t._field.slice();
    // They cannot be identical: exact re-evaluates the generator (so it has real terrain past the old
    // tile edge and no filtering) while raster clamps and low-passes. What must hold is that they put
    // the SAME features in the SAME places. Scored in the INTERIOR, away from the clamped border, so
    // the metric measures placement agreement rather than the two modes' differing edge policy.
    const corrOver = (keep) => { const A=[],B=[];
      for (let y=0;y<n;y++) for (let x=0;x<n;x++) if (keep(x,y)) { A.push(exact[y*n+x]); B.push(raster[y*n+x]); }
      const ma=A.reduce((s,v)=>s+v,0)/A.length, mb=B.reduce((s,v)=>s+v,0)/B.length;
      let num=0,da=0,db=0;
      for (let i=0;i<A.length;i++){ const p=A[i]-ma,q=B[i]-mb; num+=p*q; da+=p*p; db+=q*q; }
      return +(num/Math.sqrt(da*db)).toFixed(4); };
    let se=0; for (let i=0;i<exact.length;i++) se += (exact[i]-raster[i])**2;
    const m = Math.round(n*0.25);
    out.exactVsRasterSamePlacement = { modeA, modeB:t._xfMode,
      rms:+Math.sqrt(se/exact.length).toFixed(4),
      corrWholeTile: corrOver(()=>true),
      corrInterior:  corrOver((x,y)=>x>=m&&y>=m&&x<n-m&&y<n-m) };

    // ---- 5. the Transform's Mask input confines the move ----
    const base = disc(0.5, 0.5);
    const mask = TYPES.shape.eval({kind:"circle", x:0.5, y:0.5, size:0.9, aspect:1, angle:0,
                                   falloff:0.02, invert:"off"});
    const confined = TYPES.transform.eval({...D, offX:0.35}, [base, mask],
                                          {id:-1, params:{}, _xfMode:null});
    let outsideChanged = 0, insideChanged = 0;
    for (let i=0;i<base.length;i++){
      const d = Math.abs(confined[i]-base[i]);
      if (mask[i] < 1e-6) outsideChanged += d; else if (mask[i] > 0.99) insideChanged += d;
    }
    out.transformMask = { changeOutsideMask:+outsideChanged.toExponential(2),
                          changeInsideMask:+insideChanged.toFixed(2),
                          confinedProperly: outsideChanged === 0 && insideChanged > 0 };

    // ---- 6. STAMP: place a patch onto a base through a mask ----
    const bed  = newField(0.3);
    const peak = disc(0.25, 0.25);                       // the "landform" to place
    const spot = TYPES.shape.eval({kind:"circle", x:0.25, y:0.25, size:0.3, aspect:1, angle:0,
                                   falloff:0.05, invert:"off"});
    const st = (op, amount, m) => TYPES.stampn.eval({op, amount}, [bed, peak, m]);
    const maxed = st("max", 1, spot);
    let untouched = 0, raised = 0;
    for (let i=0;i<bed.length;i++){
      if (spot[i] < 1e-6) untouched += Math.abs(maxed[i]-bed[i]);
      if (spot[i] > 0.99 && peak[i] > 0.5) raised += (maxed[i]-bed[i]);
    }
    out.stamp = {
      maxLeavesOutsideAlone: +untouched.toExponential(2),
      maxRaisesInside: raised > 0,
      neverBelowBase: maxed.every((v,i)=>v >= bed[i]-1e-6),
      addAccumulates: (()=>{ const a=st("add",1,spot); return a.some((v,i)=>v > bed[i]+1e-6); })(),
      replaceOverwrites: (()=>{ const rp=st("replace",1,null);
        return rp.every((v,i)=>Math.abs(v-peak[i])<1e-6); })(),
      amountZeroIsIdentity: st("max",0,spot).every((v,i)=>Math.abs(v-bed[i])<1e-6),
      noPatchIsIdentity: TYPES.stampn.eval({op:"max",amount:1},[bed,null,spot])
                          .every((v,i)=>Math.abs(v-bed[i])<1e-6),
    };
    return out;
  });

  console.log(JSON.stringify(r, null, 2));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
