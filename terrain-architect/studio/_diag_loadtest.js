// Does the page load at all, and what does it throw on the way? A hang is indistinguishable from
// a slow build unless something isolates it, so this does the navigation and nothing else.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage();
  const errs = [];
  p.on('pageerror', e => errs.push(String(e.message).slice(0, 200)));
  const target = process.argv[2] || 'index.html';
  const url = target.startsWith('file:') ? target : 'file://' + path.resolve(target);
  try { await p.goto(url, { waitUntil: 'load', timeout: 60000 }); console.log('LOADED ok'); }
  catch (e) { console.log('LOAD FAILED: ' + String(e.message).slice(0, 160)); }
  console.log('pageerrors(' + errs.length + '): ' + JSON.stringify(errs.slice(0, 6)));
  await b.close();
})().catch(e => { console.error('FATAL ' + String(e).slice(0, 200)); process.exit(2); });
