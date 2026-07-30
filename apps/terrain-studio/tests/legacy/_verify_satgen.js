// Headless test of the docked SatMap Studio gradient editor.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));
const log = (...a) => console.log(...a);

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 860 } });
  const errors = [];
  page.on('console', m => { if (m.type()==='error') errors.push('CONSOLE:'+m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR:'+e.message));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(1600);

  // BUILD THE DOCUMENT THIS FILE MEASURES. 31f5688 demoted the 18-node showcase to the page-global
  // showcaseGraph() and made the opening document L0 - perlin, ridged, blend, d_height, heightmask,
  // levels, output. L0 has NO satmap node, so buildProps() never emits the "Open SatMap Studio…"
  // button and this oracle died at exit 2 on a 30 s locator timeout at its very first click.
  //
  // evalGraph() is enough here; the app's own #buildBtn is not needed. The only cur* cache this
  // file reaches is curHgt, read by the drawer's computeHist() for the #sgHisto bars, and evalGraph
  // -> finishGraphEvaluation -> updateViewport repopulates it synchronously. Measured on this
  // machine: curHgt strided sum was 18591.5237 for L0, 19256.9096 after showcaseGraph()+evalGraph(),
  // and clicking #buildBtn afterwards left it at exactly 19256.9096 - identical, for 18.3 s instead
  // of 3.7 s. Nothing here reads curFilled/curAccum (refreshWater) or asserts on viewport pixels.
  await page.evaluate(() => {
    nodes.length=0; edges.length=0; uid=1; selected=null; selectedEdge=null;
    showcaseGraph(); evalGraph();
    const sat = nodes.find(n => n.type === 'satmap');
    if (!sat) throw new Error('SETUP FAILURE: no satmap node after showcaseGraph()');
    if (sat.params.gradient !== 'Temperate')
      throw new Error('SETUP FAILURE: satmap gradient is ' + sat.params.gradient + ', expected Temperate');
    select(sat); // the Studio button lives in the satmap node's property panel
  });
  await page.waitForTimeout(200);

  const handleCount = () => page.evaluate(() => document.querySelectorAll('#sgTrack .sg-handle').length);
  const lutMid = () => page.evaluate(() => { const c=document.querySelector('#sgLut'); const g=c.getContext('2d');
    return Array.from(g.getImageData((c.width/2)|0,18,1,1).data).slice(0,3); });
  const histoHasBars = () => page.evaluate(() => { const c=document.querySelector('#sgHisto'); const g=c.getContext('2d');
    const d=g.getImageData(0,0,c.width,c.height).data; let n=0; for(let i=3;i<d.length;i+=4) if(d[i]>0) n++; return n; });

  // stop counts are asserted against the library, not against numbers typed into a comment:
  // Temperate has 7 stops and Dune 12 on this build, and the gate reads them from SATMAPS.
  const stopsIn = name => page.evaluate(n => (SATMAPS[n]||[]).length, name);
  const temperateStops = await stopsIn('Temperate'), duneStops = await stopsIn('Dune');

  // open
  await page.getByRole('button',{name:'Open SatMap Studio…'}).click(); await page.waitForTimeout(200);
  const opened = await page.evaluate(()=>({open:document.querySelector('#satgen').classList.contains('open'),
    nodeGradient:nearestUpstreamNode('satmap').params.gradient}));
  log('drawer open:', opened);
  const openHandles = await handleCount(), openBars = await histoHasBars(), openLut = await lutMid();
  log(`handles (Temperate=${temperateStops}):`, openHandles, '| histo bars:', openBars, '| lut mid:', JSON.stringify(openLut));

  // preset -> Dune (12 stops)
  await page.selectOption('#sgPreset', 'Dune'); await page.waitForTimeout(150);
  const duneHandles = await handleCount();
  log(`handles after Dune preset (${duneStops}):`, duneHandles);

  // click the bar to add a stop
  const barBox = await page.evaluate(()=>{const r=document.querySelector('#sgLut').getBoundingClientRect();return{x:r.left,y:r.top,w:r.width,h:r.height};});
  await page.mouse.click(barBox.x + barBox.w*0.5, barBox.y + barBox.h*0.5); await page.waitForTimeout(120);
  const addedHandles = await handleCount();
  log('handles after click-add:', addedHandles);

  // drag the first handle to the right
  const h0 = await page.evaluate(()=>{const h=document.querySelector('#sgTrack .sg-handle');const r=h.getBoundingClientRect();return{x:r.left+r.width/2,y:r.top+r.height/2};});
  const before = await page.evaluate(()=>document.querySelector('#sgTrack .sg-handle').style.left);
  await page.mouse.move(h0.x, h0.y); await page.mouse.down();
  await page.mouse.move(h0.x + barBox.w*0.25, h0.y, {steps:6}); await page.mouse.up(); await page.waitForTimeout(120);
  const after = await page.evaluate(()=>document.querySelectorAll('#sgTrack .sg-handle')[0].style.left);
  const dragMoved = before!==after;
  log('drag stop: firstHandle left before/after =', before, '->', after, 'moved:', dragMoved);

  // hue slider changes the LUT colours
  const beforeHue = await lutMid();
  await page.evaluate(()=>{const s=document.querySelector('#sgHue');s.value=120;s.dispatchEvent(new Event('input'));});
  await page.waitForTimeout(120);
  const afterHue = await lutMid();
  const hueChanged = JSON.stringify(beforeHue)!==JSON.stringify(afterHue);
  log('hue shift changed LUT:', hueChanged, JSON.stringify(beforeHue), '->', JSON.stringify(afterHue));
  await page.evaluate(()=>document.querySelector('#sgResetAdj').click());

  // bands + reverse (just exercise; no crash)
  await page.click('#sgInterp button[data-v="bands"]'); await page.waitForTimeout(80);
  await page.click('#sgReverse'); await page.waitForTimeout(80);
  await page.click('#sgInterp button[data-v="smooth"]'); await page.waitForTimeout(80);
  const bandsHandles = await handleCount();
  log('after bands/reverse handles:', bandsHandles);

  // del stop
  const preDel = await handleCount();
  await page.click('#sgDelStop'); await page.waitForTimeout(100);
  const postDel = await handleCount();
  log('del stop:', preDel, '->', postDel);

  // from image -> auto-extract
  await page.click('#sgFromImg'); await page.waitForTimeout(120);
  const imgPanelVisible = await page.evaluate(()=>!document.querySelector('#sgImgPanel').hidden);
  log('image panel visible:', imgPanelVisible);
  const fixture=Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="96" height="48">
    <defs><linearGradient id="g"><stop stop-color="#20364c"/><stop offset=".35" stop-color="#70865c"/>
      <stop offset=".7" stop-color="#b47b4d"/><stop offset="1" stop-color="#e4d8c4"/></linearGradient></defs>
    <rect width="96" height="48" fill="url(#g)"/></svg>`);
  await page.setInputFiles('#satImg',{name:'satmap-fixture.svg',mimeType:'image/svg+xml',buffer:fixture}); await page.waitForTimeout(400);
  await page.evaluate(()=>{const s=document.querySelector('#sgN');s.value=10;s.dispatchEvent(new Event('input'));});
  await page.click('#sgAuto'); await page.waitForTimeout(200);
  const autoHandles = await handleCount();
  log('handles after Auto-extract (10):', autoHandles);

  await page.screenshot({ path: path.resolve(__dirname, '_shot_drawer.png') });

  // apply
  await page.fill('#sgName', 'DrawerMap'); await page.click('#sgApply'); await page.waitForTimeout(400);
  const applied = await page.evaluate(()=>({ open:document.querySelector('#satgen').classList.contains('open'),
    inSat: !!SATMAPS['DrawerMap'], satName,
    nodeGradient:nearestUpstreamNode('satmap').params.gradient }));
  log('after apply:', JSON.stringify(applied));
  await page.screenshot({ path: path.resolve(__dirname, '_shot_drawer_applied.png') });

  log('ERRORS', errors.length ? JSON.stringify(errors) : 'none');

  // This file used to print thirteen measurements and exit on errors.length alone - a gate that
  // could not fail on a drawer that did nothing, which is the vacuous shape this project keeps
  // finding. Every printed quantity is now a bound. Measured on the repaired path:
  //   opened.open=true  nodeGradient='__SatMap Studio Preview'  openHandles=7  openBars=8872
  //   duneHandles=12  addedHandles=13  dragMoved=true  hueChanged=true  bandsHandles=13
  //   preDel=13 -> postDel=12  imgPanelVisible=true  autoHandles=10
  //   applied={open:false, inSat:true, satName:'DrawerMap', nodeGradient:'DrawerMap'}
  //
  // nodeGradient is the load-bearing one, and it is armed between two MEASURED endpoints.
  // render() writes the live preview key onto the TARGET NODE, so '__SatMap Studio Preview' is
  // proof the drawer bound to the graph's satmap node. Broken endpoint, measured by driving the
  // drawer open on the L0 opening document (perlin,ridged,blend,d_height,heightmask,levels,output):
  // nearestUpstreamNode('satmap')=null, target=null, drawer opens looking perfectly healthy with
  // the same 7 Temperate handles - and nodes carrying the preview key = 0. Every stop count, the
  // histogram and the LUT read identical on that path; only nodeGradient tells the two apart.
  // (That path is unreachable by a user: #satGenBtn is a hidden proxy and the only real entry is
  // the property-panel button, which L0 never renders. The probe called the handler directly.)
  const PREVIEW_KEY = '__SatMap Studio Preview';
  const ok = opened.open && opened.nodeGradient === PREVIEW_KEY
    && temperateStops === 7 && duneStops === 12
    && openHandles === temperateStops && duneHandles === duneStops && addedHandles === duneStops + 1
    && openBars > 0 && openLut.length === 3 && openLut.some(c => c > 0)
    && dragMoved && hueChanged
    && bandsHandles === addedHandles && postDel === preDel - 1
    && imgPanelVisible && autoHandles === 10
    && applied.open === false && applied.inSat && applied.satName === 'DrawerMap'
    && applied.nodeGradient === 'DrawerMap'
    && !errors.length;
  log('ok:', ok);
  await browser.close();
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
