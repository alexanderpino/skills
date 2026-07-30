// Art direction: a Shape mask must confine an effect to where it is bright, and leave the rest alone.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    const out = {};
    // BUILD THE DOCUMENT THIS FILE MEASURES. D7 demoted the 18-node showcase and made the opening
    // document L0 bedrock (perlin, ridged, blend, d_height, heightmask, levels, output). The mask
    // rule below is demonstrated ON THERMAL EROSION, and L0 has no thermal node: inherited, the
    // lookup returned undefined and the evaluate died on `.params` (measured: FATAL, exit 2).
    //
    // evalGraph() is sufficient and a full #buildBtn build is NOT needed. Every number in this file
    // comes from TYPES.*.eval() and from nodeById(src)._field — pure CPU heightfields. Nothing here
    // reads curHgt / curFilled / curAccum, renders a frame or screenshots the viewport, so there is
    // no renderer cache that could quietly hold the previous document's terrain behind the result.
    nodes.length = 0; edges.length = 0; uid = 1; selected = null; selectedEdge = null;
    showcaseGraph(); evalGraph();

    // --- the Shape primitive itself ---
    const kinds = {};
    for (const kind of ['circle','box','line']) {
      const f = TYPES.shape.eval({kind, x:0.5, y:0.5, size:0.4, aspect:1, angle:0, falloff:0.25, invert:'off'});
      let inside=0, edge=0, outside=0;
      for (let i=0;i<f.length;i++){ if(f[i]>0.99)inside++; else if(f[i]<0.01)outside++; else edge++; }
      const c = f[(RES/2|0)*RES + (RES/2|0)];          // centre
      kinds[kind] = { centre:+c.toFixed(3), inside, edge, outside, bounded: f.every(v=>v>=0&&v<=1) };
    }
    out.kinds = kinds;

    // position actually moves it
    const left  = TYPES.shape.eval({kind:'circle',x:0.25,y:0.5,size:0.3,aspect:1,angle:0,falloff:0.1,invert:'off'});
    const right = TYPES.shape.eval({kind:'circle',x:0.75,y:0.5,size:0.3,aspect:1,angle:0,falloff:0.1,invert:'off'});
    const row = (RES/2|0)*RES;
    out.moves = { leftAtQuarter:+left[row+(RES*0.25|0)].toFixed(2), leftAtThreeQuarter:+left[row+(RES*0.75|0)].toFixed(2),
                  rightAtThreeQuarter:+right[row+(RES*0.75|0)].toFixed(2) };

    // --- the universal mask rule: erode only inside the shape ---
    // Every lookup is named, so a document that stops containing the subject is a SETUP FAILURE
    // rather than a silent undefined that lets the gate measure nothing and report success.
    const o = outputNode();
    if (!o) throw new Error('SETUP FAILURE: no output node after showcaseGraph()');
    const oe = edges.find(e=>e.to===o.id&&e.slot===0);
    if (!oe) throw new Error('SETUP FAILURE: nothing wired into the output node');
    const srcNode = nodeById(oe.from);
    if (!srcNode || !srcNode._field) throw new Error('SETUP FAILURE: output source has no _field after evalGraph()');
    const base = srcNode._field;
    const mask = TYPES.shape.eval({kind:'circle',x:0.3,y:0.3,size:0.35,aspect:1,angle:0,falloff:0.08,invert:'off'});
    const th = nodes.find(n=>n.type==='thermal');
    if (!th) throw new Error('SETUP FAILURE: no thermal node after showcaseGraph()');
    const everywhere = TYPES.thermal.eval(th.params, [base, null], th);
    const confined   = TYPES.thermal.eval(th.params, [base, mask], th);
    let changedIn=0, changedOut=0, loose=0, nIn=0, nOut=0;
    for (let i=0;i<base.length;i++){
      const d = Math.abs(confined[i]-base[i]);
      if (mask[i] > 0.95) { changedIn += d; nIn++; }
      else if (mask[i] < 1e-6) { changedOut += d; loose += Math.abs(everywhere[i]-base[i]); nOut++; }
    }
    out.masking = {
      meanChangeInsideMask: +(changedIn/Math.max(nIn,1)).toExponential(2),
      meanChangeOutsideMask: +(changedOut/Math.max(nOut,1)).toExponential(2),
      // The SAME statistic for the UNMASKED run over the SAME cells. This is the armed endpoint:
      // without it, "outside change is zero" is indistinguishable from a thermal node that did
      // nothing at all, or from a mask region the erosion could never have reached anyway.
      meanChangeOutsideUnmasked: +(loose/Math.max(nOut,1)).toExponential(2),
      unmaskedDiffers: !confined.every((v,i)=>v===everywhere[i]),
      maskHasBothRegions: nIn>0 && nOut>0,
    };
    return out;
  });

  console.log('Shape primitive:');
  for (const [k,v] of Object.entries(r.kinds))
    console.log(`  ${k.padEnd(7)} centre=${v.centre} inside=${v.inside} edge=${v.edge} outside=${v.outside} bounded=${v.bounded}`);
  console.log('Position:', JSON.stringify(r.moves));
  console.log('Mask rule:', JSON.stringify(r.masking));
  console.log('errors', errors.length?JSON.stringify(errors):'none');

  // This file printed all of the above and then exited on `errors.length` alone — it would have
  // reported success on a shape node returning a constant field. Bounds below are anchored on
  // measured values (RES=512, 262144 cells, showcase document):
  //   circle inside=17280 edge=36328 outside=208536 · box 21904/45968/194272 · line 47592/59684/154868
  //   moves 1 / 0 / 1        masking in=2.64e-4  out=0  outUnmasked=1.5e-4
  const shapeOk = ['circle','box','line'].every(k => {
    const v = r.kinds[k];
    // edge>0 is what separates a real falloff from a hard binary stamp; outside>0 and inside>0
    // together are what separate a shape from a constant field, which is how this could pass blind.
    return v && v.bounded && v.centre === 1 && v.inside > 0 && v.edge > 0 && v.outside > 0;
  });
  // A shape that ignored `x` would put the same value at both sample columns; the left/right pair
  // is the armed contrast — 1 vs 0 at the SAME column for two different centres.
  const movesOk = r.moves.leftAtQuarter === 1 && r.moves.leftAtThreeQuarter === 0
    && r.moves.rightAtThreeQuarter === 1;
  const m = r.masking;
  // meanChangeOutsideUnmasked is the broken-path endpoint measured in the same run over the same
  // cells: thermal DOES move those cells (1.5e-4) when unmasked, so "outside change is exactly 0"
  // is confinement, not an erosion that did nothing or a region it could never have reached.
  const maskOk = m.maskHasBothRegions && m.unmaskedDiffers
    && m.meanChangeInsideMask > 1e-5      // measured 2.64e-4
    && m.meanChangeOutsideUnmasked > 1e-5 // measured 1.50e-4 — arms the line below
    && m.meanChangeOutsideMask === 0;     // measured exactly 0; a mask multiply is exact
  const ok = shapeOk && movesOk && maskOk && !errors.length;
  console.log(JSON.stringify({ shapeOk, movesOk, maskOk, ok }));
  await b.close();
  process.exit(ok?0:1);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
