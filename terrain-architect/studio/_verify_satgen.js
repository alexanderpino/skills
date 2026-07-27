// Headless test of the docked SatMap Studio gradient editor.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));
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

  const handleCount = () => page.evaluate(() => document.querySelectorAll('#sgTrack .sg-handle').length);
  const lutMid = () => page.evaluate(() => { const c=document.querySelector('#sgLut'); const g=c.getContext('2d');
    return Array.from(g.getImageData((c.width/2)|0,18,1,1).data).slice(0,3); });
  const histoHasBars = () => page.evaluate(() => { const c=document.querySelector('#sgHisto'); const g=c.getContext('2d');
    const d=g.getImageData(0,0,c.width,c.height).data; let n=0; for(let i=3;i<d.length;i+=4) if(d[i]>0) n++; return n; });

  // open
  await page.getByRole('button',{name:'Open SatMap Studio…'}).click(); await page.waitForTimeout(200);
  log('drawer open:', await page.evaluate(()=>({open:document.querySelector('#satgen').classList.contains('open'),
    nodeGradient:nearestUpstreamNode('satmap').params.gradient})));
  log('handles (Temperate=7):', await handleCount(), '| histo bars:', await histoHasBars(), '| lut mid:', JSON.stringify(await lutMid()));

  // preset -> Dune (12 stops)
  await page.selectOption('#sgPreset', 'Dune'); await page.waitForTimeout(150);
  log('handles after Dune preset (12):', await handleCount());

  // click the bar to add a stop
  const barBox = await page.evaluate(()=>{const r=document.querySelector('#sgLut').getBoundingClientRect();return{x:r.left,y:r.top,w:r.width,h:r.height};});
  await page.mouse.click(barBox.x + barBox.w*0.5, barBox.y + barBox.h*0.5); await page.waitForTimeout(120);
  log('handles after click-add:', await handleCount());

  // drag the first handle to the right
  const h0 = await page.evaluate(()=>{const h=document.querySelector('#sgTrack .sg-handle');const r=h.getBoundingClientRect();return{x:r.left+r.width/2,y:r.top+r.height/2};});
  const before = await page.evaluate(()=>document.querySelector('#sgTrack .sg-handle').style.left);
  await page.mouse.move(h0.x, h0.y); await page.mouse.down();
  await page.mouse.move(h0.x + barBox.w*0.25, h0.y, {steps:6}); await page.mouse.up(); await page.waitForTimeout(120);
  const after = await page.evaluate(()=>document.querySelectorAll('#sgTrack .sg-handle')[0].style.left);
  log('drag stop: firstHandle left before/after =', before, '->', 'moved:', before!==after);

  // hue slider changes the LUT colours
  const beforeHue = await lutMid();
  await page.evaluate(()=>{const s=document.querySelector('#sgHue');s.value=120;s.dispatchEvent(new Event('input'));});
  await page.waitForTimeout(120);
  const afterHue = await lutMid();
  log('hue shift changed LUT:', JSON.stringify(beforeHue)!==JSON.stringify(afterHue));
  await page.evaluate(()=>document.querySelector('#sgResetAdj').click());

  // bands + reverse (just exercise; no crash)
  await page.click('#sgInterp button[data-v="bands"]'); await page.waitForTimeout(80);
  await page.click('#sgReverse'); await page.waitForTimeout(80);
  await page.click('#sgInterp button[data-v="smooth"]'); await page.waitForTimeout(80);
  log('after bands/reverse handles:', await handleCount());

  // del stop
  const preDel = await handleCount();
  await page.click('#sgDelStop'); await page.waitForTimeout(100);
  log('del stop:', preDel, '->', await handleCount());

  // from image -> auto-extract
  await page.click('#sgFromImg'); await page.waitForTimeout(120);
  log('image panel visible:', await page.evaluate(()=>!document.querySelector('#sgImgPanel').hidden));
  const fixture=Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="96" height="48">
    <defs><linearGradient id="g"><stop stop-color="#20364c"/><stop offset=".35" stop-color="#70865c"/>
      <stop offset=".7" stop-color="#b47b4d"/><stop offset="1" stop-color="#e4d8c4"/></linearGradient></defs>
    <rect width="96" height="48" fill="url(#g)"/></svg>`);
  await page.setInputFiles('#satImg',{name:'satmap-fixture.svg',mimeType:'image/svg+xml',buffer:fixture}); await page.waitForTimeout(400);
  await page.evaluate(()=>{const s=document.querySelector('#sgN');s.value=10;s.dispatchEvent(new Event('input'));});
  await page.click('#sgAuto'); await page.waitForTimeout(200);
  log('handles after Auto-extract (10):', await handleCount());

  await page.screenshot({ path: path.resolve(__dirname, '_shot_drawer.png') });

  // apply
  await page.fill('#sgName', 'DrawerMap'); await page.click('#sgApply'); await page.waitForTimeout(400);
  const applied = await page.evaluate(()=>({ open:document.querySelector('#satgen').classList.contains('open'),
    inSat: !!SATMAPS['DrawerMap'], satName,
    nodeGradient:nearestUpstreamNode('satmap').params.gradient }));
  log('after apply:', JSON.stringify(applied));
  await page.screenshot({ path: path.resolve(__dirname, '_shot_drawer_applied.png') });

  log('ERRORS', errors.length ? JSON.stringify(errors) : 'none');
  await browser.close();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
