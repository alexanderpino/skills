// Surface/Geology palette family: classification, styling, toolbox, search, and quick-create.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

// The armed control. The story's negative control is "a fixture category table with Rock Fracture
// left under Erosion, which must fail". It used to be spelled
//   mutationRejected: ({ ...TYPES.fracture, cat: 'ero' }).cat !== 'surface'
// which spreads into a fresh object, overwrites cat with the literal 'ero', and compares 'ero' to
// 'surface' — constant true on every possible build, including a broken one. It never touched the
// registry and never re-ran the toolbox or quick-create probes, so it could not go red. Replaced
// with a mutation that actually reclassifies the live registry and then re-measures.
const mutation = (process.argv.find(value => value.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null;
const MUTATIONS = ['fracture-under-erosion'];
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2); }

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(1400);

  // Reclassify the live registry BEFORE anything is measured, so every probe below sees it.
  const mutationApplied = await page.evaluate(name => {
    if (name !== 'fracture-under-erosion') return false;
    if (!TYPES.fracture) return false;
    TYPES.fracture.cat = 'ero';
    return TYPES.fracture.cat === 'ero';
  }, mutation);
  if (mutation && !mutationApplied) { console.error(`FATAL mutation ${mutation} did not take effect`); process.exit(2); }

  const registry = await page.evaluate(() => ({
    surface: CAT.surface,
    fractureCategory: TYPES.fracture?.cat,
    thermalCategory: TYPES.thermal?.cat,
    surfaceColor: getComputedStyle(document.documentElement).getPropertyValue('--cat-surface').trim()
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

  const report = { registry, toolbox, quickCreate, mutation, errors };
  let ok = registry.surface?.name === 'Surface / Geology'
    && registry.surface?.c === '--cat-surface'
    && registry.fractureCategory === 'surface'
    && registry.thermalCategory === 'ero'
    && /^#[0-9a-f]{6}$/i.test(registry.surfaceColor)
    && toolbox.found && toolbox.category === 'Surface / Geology' && toolbox.count === 1
    && quickCreate.found && quickCreate.count === 1
    && !errors.length;
  // A mutated run that still reports ok means the probes above are not measuring classification.
  if (mutation && ok) { console.error(`FAIL mutation ${mutation} was not detected — the control is vacuous`); ok = false; }
  else if (mutation) { report.mutationDetected = true; ok = false; }
  console.log(`${ok ? 'PASS' : 'FAIL'}  surface family registry=${registry.fractureCategory} toolbox=${toolbox.category} quick=${quickCreate.found} mutation=${mutation || 'none'}`);
  console.log(JSON.stringify({ ...report, ok }, null, 2));
  await browser.close();
  process.exit(ok ? 0 : 1);
})().catch(error => { console.error('FATAL', error); process.exit(2); });