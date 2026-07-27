// The artist draws the skirt; the engine reads a LUT. Data flow: control points -> monotone cubic
// -> 256-entry LUT -> one lerped lookup per cell driving the crest-face cross section.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    const out = {};

    // ---- 1. the bake reproduces the analytic curve it replaces ----
    const lut = bakeCurve(curveFromExponent(1.4));
    let maxErr = 0;
    for (let k=0;k<256;k++){ const x=k/255; maxErr = Math.max(maxErr, Math.abs(lut[k]-Math.pow(1-x,1.4))); }
    out.matchesAnalytic = { maxAbsErrVsPow: +maxErr.toExponential(2), endpointsExact:
      lut[0]===1 && lut[255]===0 };

    // ---- 2. MONOTONE CUBIC CANNOT OVERSHOOT. A plain spline through these points would.
    // An overshoot means terrain above the summit or below the plane, so this is a hard invariant.
    const nasty = [[0,1],[0.08,0.99],[0.12,0.15],[0.5,0.12],[0.55,0.11],[1,0]];
    const nl = bakeCurve(nasty);
    let inRange = true, monotone = true;
    for (let k=0;k<256;k++){ if (nl[k]<0 || nl[k]>1) inRange=false;
                             if (k && nl[k] > nl[k-1] + 1e-6) monotone=false; }
    out.noOvershoot = { stayedInRange: inRange, stayedMonotone: monotone,
                        min:+Math.min(...nl).toFixed(4), max:+Math.max(...nl).toFixed(4) };

    // ---- 3. the LUT actually drives the envelope: different curves, different mountains ----
    const M = (skirt) => TYPES.mountain.eval({form:"peak", style:"eroded", seed:7, x:0.5, y:0.5,
      size:0.35, angle:25, ridges:2, detail:2.6, aspect:1, relief:0.8, skirt});
    const n = RES;
    // mean height in an annulus at 70% of the radius -- the apron is what the curve controls
    const apron = (f) => { let s=0,c=0;
      for (let y=0;y<n;y++) for (let x=0;x<n;x++){
        const d=Math.hypot((x+0.5)/n-0.5,(y+0.5)/n-0.5)/0.35;
        if (d>0.62 && d<0.78){ s+=f[y*n+x]; c++; } }
      return s/Math.max(c,1); };
    const byPreset = SKIRT_PRESETS.map(([name,e]) => ({ name, exponent:e,
      apronHeight:+apron(M(curveFromExponent(e))).toFixed(4) }));
    out.curveDrivesTheApron = { byPreset,
      // a sweeping (high-exponent) curve leaves LESS material out at 70% than a plateau curve
      plateauHighestApron: byPreset[3].apronHeight === Math.max(...byPreset.map(v=>v.apronHeight)),
      sweepingLowestApron: byPreset[2].apronHeight === Math.min(...byPreset.map(v=>v.apronHeight)),
      allDistinct: new Set(byPreset.map(v=>v.apronHeight)).size === byPreset.length };

    // ---- 4. a hand-drawn curve that is not any exponent still works ----
    const drawn = M([[0,1],[0.2,0.55],[0.45,0.42],[0.8,0.10],[1,0]]);
    let lo=1e9,hi=-1e9,bad=0;
    for (const v of drawn){ if(!isFinite(v))bad++; if(v<lo)lo=v; if(v>hi)hi=v; }
    out.handDrawnCurve = { relief:+(hi-lo).toFixed(3), nonFinite:bad, works: bad===0 && hi-lo>0.3 };

    // ---- 5. the LUT is the contract: 256 entries, [0,1], starts at the summit ends at the rim ----
    out.lutContract = { length: lut.length, isFloat32: lut instanceof Float32Array,
                        startsAtSummit: lut[0]===1, endsAtRim: lut[255]===0 };
    return out;
  });

  // ---- 6. the WIDGET: dragging a real control point must change the terrain ----
  const drag = await p.evaluate(() => {
    nodes.length=0; edges.length=0; uid=1;
    const m=makeNode("mountain",100,100), o=makeNode("output",400,100);
    Object.assign(m.params,{form:"peak",style:"eroded",seed:7,size:0.35,relief:0.8});
    edges.push({from:m.id,to:o.id,slot:0});
    selected=m; buildProps(); evalGraph();
    return { hasCanvas: !!document.querySelector('#props canvas'), points: m.params.skirt.length };
  });
  const canvas = p.locator('#props canvas').first();
  await canvas.scrollIntoViewIfNeeded();                 // the widget sits below a long param list
  const box = await canvas.boundingBox();
  // ask the page where a given control point actually is on screen, rather than guessing
  const ptScreen = await p.evaluate((i) => {
    const cv=document.querySelector('#props canvas'), r=cv.getBoundingClientRect();
    const W=272,H=132,PAD=10, q=nodes.find(n=>n.type==='mountain').params.skirt[i];
    const px=PAD+q[0]*(W-2*PAD), py=PAD+(1-q[1])*(H-2*PAD);
    return { x:r.left+px*r.width/W, y:r.top+py*r.height/H, value:q };
  }, 2);
  // compare the WHOLE field: the first rows of the tile lie outside the footprint and are
  // zero either way, so slicing them was measuring nothing.
  const before = await p.evaluate(() => Array.from(nodes.find(n=>n.type==='mountain')._field));
  await p.mouse.move(ptScreen.x, ptScreen.y);
  await p.mouse.down();
  await p.mouse.move(ptScreen.x, ptScreen.y - box.height*0.28, { steps: 10 });   // lift the apron
  await p.mouse.up();
  await p.waitForTimeout(2200);
  const after = await p.evaluate(() => { const m=nodes.find(n=>n.type==='mountain');
    return { field: Array.from(m._field), points: m.params.skirt.length,
             ends: [m.params.skirt[0][0], m.params.skirt[m.params.skirt.length-1][0]],
             moved: m.params.skirt[2] }; });
  let diff=0; for (let i=0;i<before.length;i++) diff += Math.abs(before[i]-after.field[i]);

  // clicking empty space adds a point; double-clicking it removes it again
  const mid = { x: box.x + box.width*0.5, y: box.y + box.height*0.30 };
  await p.mouse.click(mid.x, mid.y); await p.waitForTimeout(900);
  const added = await p.evaluate(() => nodes.find(n=>n.type==='mountain').params.skirt.length);
  await p.mouse.dblclick(mid.x, mid.y); await p.waitForTimeout(900);
  const removed = await p.evaluate(() => nodes.find(n=>n.type==='mountain').params.skirt.length);

  console.log(JSON.stringify({ ...r, widget: { ...drag,
    grabbedPointWas: ptScreen.value.map(v=>+v.toFixed(3)),
    grabbedPointNow: after.moved.map(v=>+v.toFixed(3)),
    endpointsStayPinnedInX: after.ends[0] === 0 && after.ends[1] === 1,
    pointMovedInY: after.moved[1] > ptScreen.value[1] + 0.05,
    pointCountUnchangedByDrag: after.points === drag.points,
    terrainChanged: diff > 1, meanAbsChange: +(diff/before.length).toFixed(4),
    clickAddsPoint: added === drag.points + 1,
    dblClickRemovesPoint: removed === drag.points } }, null, 2));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
