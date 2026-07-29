// Graph toolbox regression: graph-owned toggle, complete categorized catalog,
// search, click-to-place, keyboard close, and retained double-click quick menu.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(1400);

  const initial = await page.evaluate(() => ({
    topbarAdd: !!document.querySelector('#topbar #addBtn'),
    graphToggle: document.querySelector('#nodeToolBtn')?.parentElement?.id,
    typeCount: Object.keys(TYPES).length,
    categoryCount: Object.keys(CAT).filter(c => Object.values(TYPES).some(t => t.cat === c)).length,
    nodeCount: nodes.length
  }));
  await page.locator('#nodeToolBtn').click();
  await page.waitForTimeout(120);
  const catalog = await page.evaluate(() => ({
    open: document.querySelector('#nodeToolbox').classList.contains('open'),
    expanded: document.querySelector('#nodeToolBtn').getAttribute('aria-expanded'),
    items: document.querySelectorAll('.node-tool-item').length,
    categories: document.querySelectorAll('.node-tool-cat').length
  }));
  await page.screenshot({ path: path.resolve(__dirname, '_shot_toolbox.png') });

  await page.locator('#nodeToolSearch').fill('Mountain');
  const filtered = await page.locator('.node-tool-item').count();
  const mountain = page.locator('.node-tool-item[data-type="mountain"]');
  await mountain.click();
  await page.waitForTimeout(120);
  const added = await page.evaluate(() => ({
    nodeCount: nodes.length,
    selectedType: selected && selected.type,
    open: document.querySelector('#nodeToolbox').classList.contains('open'),
    screenX: selected ? Math.round(selected.x * view.z + view.x) : -1
  }));

  await page.locator('#nodeToolSearch').press('Escape');
  const closed = await page.evaluate(() => ({
    open: document.querySelector('#nodeToolbox').classList.contains('open'),
    expanded: document.querySelector('#nodeToolBtn').getAttribute('aria-expanded')
  }));
  await page.locator('#graph').dblclick({ position: { x: 820, y: 350 } });
  const quickMenu = await page.evaluate(() => ({
    open: document.querySelector('#menu').classList.contains('open'),
    items: document.querySelectorAll('#menu .menu-item').length
  }));

  const report = { initial, catalog, filtered, added, closed, quickMenu, errors };
  const ok = !initial.topbarAdd
    && initial.graphToggle === 'graphwrap'
    && catalog.open && catalog.expanded === 'true'
    && catalog.items === initial.typeCount && catalog.categories === initial.categoryCount
    && filtered >= 1
    && added.nodeCount === initial.nodeCount + 1
    && added.selectedType === 'mountain' && added.open && added.screenX > 248
    && !closed.open && closed.expanded === 'false'
    && quickMenu.open && quickMenu.items === initial.typeCount
    && !errors.length;
  console.log(JSON.stringify({ ...report, ok }, null, 2));
  await browser.close();
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
