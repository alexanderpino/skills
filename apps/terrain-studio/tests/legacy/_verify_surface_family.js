// Surface/Geology palette family: classification, styling, toolbox, search, and quick-create.
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
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(1400);

  const registry = await page.evaluate(() => ({
    surface: CAT.surface,
    fractureCategory: TYPES.fracture?.cat,
    thermalCategory: TYPES.thermal?.cat,
    surfaceColor: getComputedStyle(document.documentElement).getPropertyValue('--cat-surface').trim(),
    mutationRejected: ({ ...TYPES.fracture, cat: 'ero' }).cat !== 'surface'
  }));

  await page.locator('#nodeToolBtn').click();
  await page.locator('#nodeToolSearch').fill('Rock Fracture');
  const toolbox = await page.evaluate(() => {
    const item = document.querySelector('.node-tool-item[data-type="fracture"]');
    const category = item?.closest('.node-tool-cat')?.querySelector('.node-tool-cat-title')?.textContent || '';
    return { found: !!item, category, count: document.querySelectorAll('.node-tool-item').length };
  });

  await page.keyboard.press('Escape');
  await page.locator('#graph').dblclick({ position: { x: 820, y: 350 } });
  await page.locator('#menu .menu-search').fill('Rock Fracture');
  const quickCreate = await page.evaluate(() => ({
    found: !!document.querySelector('#menu .menu-item[data-type="fracture"]'),
    count: document.querySelectorAll('#menu .menu-item').length
  }));

  const report = { registry, toolbox, quickCreate, errors };
  const ok = registry.surface?.name === 'Surface / Geology'
    && registry.surface?.c === '--cat-surface'
    && registry.fractureCategory === 'surface'
    && registry.thermalCategory === 'ero'
    && registry.mutationRejected
    && /^#[0-9a-f]{6}$/i.test(registry.surfaceColor)
    && toolbox.found && toolbox.category === 'Surface / Geology' && toolbox.count === 1
    && quickCreate.found && quickCreate.count === 1
    && !errors.length;
  console.log(`PASS  surface family registry=${registry.fractureCategory} toolbox=${toolbox.category} quick=${quickCreate.found}`);
  console.log(JSON.stringify({ ...report, ok }, null, 2));
  await browser.close();
  process.exit(ok ? 0 : 1);
})().catch(error => { console.error('FATAL', error); process.exit(2); });