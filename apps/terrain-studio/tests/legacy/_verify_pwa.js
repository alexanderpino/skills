// PWA shell: manifest, icons, service-worker registration, and OFFLINE.
//
// Must be run against a BUILT app over http. `npm run verify -- --preview _verify_pwa.js` does
// that. Two reasons it cannot work any other way:
//   * the service worker is registered behind `import.meta.env.PROD`, so it does not exist in dev;
//   * a worker only registers on a SECURE ORIGIN - https, or http on localhost - and never from
//     file://, which is also why the whole suite moved to http.
//
// The offline check is the point of the file. Everything else here (manifest parses, icons are
// PNGs, registration resolves) can pass on an app that is useless without a network, and
// "installable" is not the same claim as "works offline". So the last gate takes the context
// offline and reloads.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || 'http://127.0.0.1:4173/index.html';

let failures = 0;
const gate = (name, ok, detail) => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}  ${detail}`);
  if (!ok) failures++;
};

(async () => {
  if (URL.startsWith('file://')) {
    console.log('FAIL  pwa-origin  file:// cannot register a service worker. Run with --preview.');
    process.exit(1);
  }
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] });
  const ctx = await b.newContext();
  const p = await ctx.newPage();
  const errors = [];
  p.on('pageerror', (e) => errors.push(String(e.message).slice(0, 200)));

  await p.goto(URL, { waitUntil: 'load' });

  // ---- manifest ---------------------------------------------------------------------------------
  const href = await p.getAttribute('link[rel="manifest"]', 'href');
  gate('pwa-manifest-linked', !!href, `href=${href}`);

  const manifest = href ? await p.evaluate(async (h) => {
    try { const r = await fetch(h); return r.ok ? await r.json() : { __status: r.status }; }
    catch (e) { return { __error: String(e) }; }
  }, href) : null;

  const required = ['name', 'start_url', 'display', 'icons'];
  const missing = manifest ? required.filter((k) => !(k in manifest)) : required;
  gate('pwa-manifest-valid', !!manifest && !manifest.__status && !manifest.__error && !missing.length,
    manifest && manifest.name ? `name="${manifest.name}" display=${manifest.display} icons=${(manifest.icons || []).length}`
      : `missing=${missing.join(',')} ${JSON.stringify(manifest).slice(0, 120)}`);

  // Installability needs a 192 and a 512; a manifest listing icons that 404 is the common way this
  // silently fails, so fetch each one rather than trusting the list.
  const iconResults = manifest && manifest.icons ? await p.evaluate(async (icons) => {
    const out = [];
    for (const i of icons) {
      try {
        const r = await fetch(i.src);
        const buf = r.ok ? new Uint8Array(await r.arrayBuffer()) : null;
        const sig = buf && buf.length > 8
          ? [...buf.slice(0, 8)].map((x) => x.toString(16).padStart(2, '0')).join('') : '';
        out.push({ src: i.src, sizes: i.sizes, status: r.status, png: sig === '89504e470d0a1a0a', bytes: buf ? buf.length : 0 });
      } catch (e) { out.push({ src: i.src, error: String(e) }); }
    }
    return out;
  }, manifest.icons) : [];
  const sizes = new Set(iconResults.filter((i) => i.png).flatMap((i) => String(i.sizes).split(' ')));
  gate('pwa-icons', iconResults.length > 0 && iconResults.every((i) => i.png)
    && sizes.has('192x192') && sizes.has('512x512'),
    iconResults.map((i) => `${i.src}:${i.status}${i.png ? 'png' : 'NOT-PNG'}`).join(' '));

  // ---- service worker ---------------------------------------------------------------------------
  // navigator.serviceWorker.ready NEVER REJECTS - it is a promise that simply does not settle when
  // nothing registers. Awaiting it bare turns "this build has no worker" into a hang, which is the
  // worst failure mode available: no message, no exit code, and a leaked preview server. That is
  // not theoretical - it happened the moment the registration was gated to MODE === "production",
  // because --preview builds --mode test. So: race it against a timeout and report the absence.
  const reg = await p.evaluate(async () => {
    if (!('serviceWorker' in navigator)) return { supported: false };
    const timeout = new Promise((res) => setTimeout(() => res({ timedOut: true }), 8000));
    try {
      const r = await Promise.race([navigator.serviceWorker.ready, timeout]);
      if (r && r.timedOut) {
        return { supported: true, timedOut: true,
          registrations: (await navigator.serviceWorker.getRegistrations()).length };
      }
      return { supported: true, scope: r.scope, active: !!r.active, state: r.active && r.active.state };
    } catch (e) { return { supported: true, error: String(e).slice(0, 160) }; }
  });
  if (reg.timedOut) {
    console.log('FAIL  pwa-sw-registered  no service worker registered within 8s '
      + `(registrations=${reg.registrations}). This gate needs a PRODUCTION build: the registration `
      + 'is gated on import.meta.env.MODE === "production", and --preview builds --mode test so the '
      + 'oracle suite stays worker-free. Use: npm run verify -- --preview-prod _verify_pwa.js');
    await b.close();
    process.exit(1);
  }
  gate('pwa-sw-registered', !!(reg.supported && reg.active && reg.state === 'activated'),
    JSON.stringify(reg));

  // ---- OFFLINE: the claim that actually matters -------------------------------------------------
  let offline = { ok: false, note: 'not attempted' };
  if (reg.active) {
    await ctx.setOffline(true);
    try {
      const resp = await p.reload({ waitUntil: 'load', timeout: 20000 });
      const title = await p.title();
      const hasCanvas = await p.evaluate(() => !!document.querySelector('canvas'));
      offline = { ok: !!title && hasCanvas, status: resp ? resp.status() : null, title, hasCanvas };
    } catch (e) {
      offline = { ok: false, note: String(e).slice(0, 160) };
    }
    await ctx.setOffline(false);
  }
  gate('pwa-offline', offline.ok,
    `${JSON.stringify(offline)} — the shell must load and mount its canvas with the network cut`);

  gate('pwa-no-page-errors', errors.length === 0, errors.length ? JSON.stringify(errors) : 'none');

  await b.close();
  console.log(failures ? `\n${failures} PWA gate(s) failed.` : '\nPWA shell OK.');
  process.exit(failures ? 1 : 0);
})().catch((e) => { console.error('FATAL ' + String(e).slice(0, 300)); process.exit(2); });
