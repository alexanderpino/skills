// Headless WebGL2 verification of the Studio AAA render pipeline (swiftshader).
const { chromium } = require('playwright-core');
const path = require('path');

const EXE = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');

(async () => {
  const browser = await chromium.launch({
    executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
           '--ignore-gpu-blocklist', '--no-sandbox', '--enable-webgl', '--enable-webgl2'],
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push('CONSOLE:' + m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR:' + e.message));

  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(2500);   // let the default graph eval + a few render frames run

  // Report WebGL context + shader-link status pulled from the page.
  const diag = await page.evaluate(() => ({
    ctx: (typeof gl !== 'undefined' && gl) ? (gl instanceof WebGL2RenderingContext ? 'webgl2' : 'webgl1') : 'none',
    deferred: (typeof USE_DEFERRED !== 'undefined') ? USE_DEFERRED : null,
    hasTerrainProg: (typeof terrainProg !== 'undefined') && !!terrainProg,
    hasCompProg: (typeof compProg !== 'undefined') && !!compProg,
    res: (typeof RES !== 'undefined') ? RES : null,
    sats: (typeof SATMAPS !== 'undefined') ? Object.keys(SATMAPS) : [],
  }));
  console.log('DIAG', JSON.stringify(diag));

  const shots = [
    ['Verdant',  0.85, 0.45, 2.4],    // derived (Amazon) — very dark canopy floor
    ['Volcanic', 0.9,  0.4,  2.4],    // derived (Icelandic lava) — basalt greys
    ['Tundra',   0.85, 0.5,  2.4],    // derived (Iceland) — soil -> brown -> snow
    ['Lunar',    0.8,  0.55, 2.4],    // derived (LROC) — neutral greys
    ['Alpine',   0.9,  0.35, 2.6],    // derived (Ligurian Alps)
    ['CloseUp',  0.85, 0.45, 1.6],    // zoomed in -> judge per-pixel surface relief
  ];
  for (const [name, az, el, dist] of shots) {
    await page.evaluate(([n, a, e, d]) => {
      const sn = (n === 'CloseUp') ? 'Tundra' : n;
      if (typeof buildSatLUT === 'function') { satName = sn; buildSatLUT(sn); }
      if (typeof sun !== 'undefined') { sun.az = a; sun.el = e; }
      if (typeof cam !== 'undefined') { cam.dist = d; }
    }, [name, az, el, dist]);
    await page.waitForTimeout(700);
    // sample a pixel near the centre of the GL canvas to confirm non-empty render
    const px = await page.evaluate(() => {
      const c = document.querySelector('#gl');
      const g = c.getContext('webgl2') || c.getContext('webgl');
      const p = new Uint8Array(4);
      g.readPixels((c.width/2)|0, (c.height/2)|0, 1, 1, g.RGBA, g.UNSIGNED_BYTE, p);
      return Array.from(p);
    });
    await page.screenshot({ path: path.resolve(__dirname, `_shot_${name}.png`) });
    console.log('SHOT', name, 'centerPixel', JSON.stringify(px));
  }

  console.log('ERRORS', errors.length ? JSON.stringify(errors, null, 2) : 'none');
  await browser.close();
  process.exit(errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
