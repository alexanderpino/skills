// Viewport UX regression: quiet default state, compact icon rail, exclusive
// contextual flyouts, live control state, and responsive containment.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(1400);

  const quiet = await page.evaluate(() => ({
    chips: document.querySelectorAll('#vpInfo .vp-chip').length,
    railButtons: document.querySelectorAll('.vp-rail .vp-tool').length,
    openPanels: [...document.querySelectorAll('.vp-flyout')].filter(x => !x.hidden).length,
    oldTools: !!document.querySelector('.vp-tools'),
    oldRender: !!document.querySelector('.vp-render'),
    previewState: document.querySelector('#previewBtn').dataset.state,
    cameraState: document.querySelector('#viewBtn').dataset.state
  }));
  await page.screenshot({ path: path.resolve(__dirname, '_shot_viewport_clean.png') });

  await page.locator('#lookBtn').click();
  const lighting = await page.evaluate(() => ({
    visible: !document.querySelector('#lookPanel').hidden,
    expanded: document.querySelector('#lookBtn').getAttribute('aria-expanded'),
    displayHidden: document.querySelector('#displayPanel').hidden,
    values: ['sunAzVal','sunElVal','exposureVal','hazeVal'].map(id => document.querySelector('#' + id).textContent)
  }));
  await page.screenshot({ path: path.resolve(__dirname, '_shot_viewport_look.png') });

  await page.locator('#displayBtn').click();
  await page.locator('#shadeSel').selectOption('3');
  await page.locator('#wireBtn').click();
  const display = await page.evaluate(() => ({
    visible: !document.querySelector('#displayPanel').hidden,
    lookHidden: document.querySelector('#lookPanel').hidden,
    shadeMode,
    wire,
    wireLabel: document.querySelector('#wireState').textContent,
    active: document.querySelector('#displayBtn').classList.contains('on')
  }));

  await page.locator('#previewBtn').click();
  await page.locator('#viewBtn').click();
  const direct = await page.evaluate(() => ({
    previewMode,
    previewState: document.querySelector('#previewBtn').dataset.state,
    previewLabel: document.querySelector('#previewBtn').getAttribute('aria-label'),
    planView,
    cameraState: document.querySelector('#viewBtn').dataset.state,
    cameraLabel: document.querySelector('#viewBtn').getAttribute('aria-label')
  }));

  await page.locator('#helpBtn').click();
  const help = await page.evaluate(() => ({
    visible: !document.querySelector('#helpPanel').hidden,
    rows: document.querySelectorAll('#helpPanel .vp-help li').length,
    othersHidden: document.querySelector('#displayPanel').hidden && document.querySelector('#lookPanel').hidden
      && document.querySelector('#waterLookPanel').hidden
  }));
  await page.keyboard.press('Escape');
  const escaped = await page.evaluate(() => [...document.querySelectorAll('.vp-flyout')].every(x => x.hidden));

  await page.locator('#layoutBtn').click();
  await page.locator('#lookBtn').click();
  const responsive = await page.evaluate(() => {
    const v = document.querySelector('#viewport').getBoundingClientRect();
    const r = document.querySelector('.vp-rail').getBoundingClientRect();
    const p = document.querySelector('#lookPanel').getBoundingClientRect();
    return {
      railInside: r.left >= v.left && r.right <= v.right && r.top >= v.top && r.bottom <= v.bottom,
      panelInside: p.left >= v.left && p.right <= v.right && p.top >= v.top && p.bottom <= v.bottom,
      viewport: { w: Math.round(v.width), h: Math.round(v.height) },
      panel: { w: Math.round(p.width), h: Math.round(p.height) }
    };
  });

  const report = { quiet, lighting, display, direct, help, escaped, responsive, errors };
  const ok = quiet.chips === 1 && quiet.railButtons === 7 && quiet.openPanels === 0
    && !quiet.oldTools && !quiet.oldRender
    && quiet.previewState === 'output' && quiet.cameraState === 'hero'
    && lighting.visible && lighting.expanded === 'true' && lighting.displayHidden
    && lighting.values.every(Boolean)
    && display.visible && display.lookHidden && display.shadeMode === 3
    && display.wire && display.wireLabel === 'On' && display.active
    && direct.previewMode === 'selected' && direct.previewState === 'selected'
    && direct.previewLabel === 'Preview final Output'
    && direct.planView && direct.cameraState === 'plan'
    && direct.cameraLabel === 'Return to hero camera'
    && help.visible && help.rows === 5 && help.othersHidden && escaped
    && responsive.railInside && responsive.panelInside
    && !errors.length;
  console.log(JSON.stringify({ ...report, ok }, null, 2));
  await browser.close();
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
