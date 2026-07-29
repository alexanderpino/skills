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
    const o = outputNode(); const src = edges.find(e=>e.to===o.id&&e.slot===0).from;
    const base = nodeById(src)._field;
    const mask = TYPES.shape.eval({kind:'circle',x:0.3,y:0.3,size:0.35,aspect:1,angle:0,falloff:0.08,invert:'off'});
    const th = nodes.find(n=>n.type==='thermal');
    const everywhere = TYPES.thermal.eval(th.params, [base, null], th);
    const confined   = TYPES.thermal.eval(th.params, [base, mask], th);
    let changedIn=0, changedOut=0, nIn=0, nOut=0;
    for (let i=0;i<base.length;i++){
      const d = Math.abs(confined[i]-base[i]);
      if (mask[i] > 0.95) { changedIn += d; nIn++; }
      else if (mask[i] < 1e-6) { changedOut += d; nOut++; }
    }
    out.masking = {
      meanChangeInsideMask: +(changedIn/Math.max(nIn,1)).toExponential(2),
      meanChangeOutsideMask: +(changedOut/Math.max(nOut,1)).toExponential(2),
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
  await b.close();
  process.exit(errors.length?1:0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
