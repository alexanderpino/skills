// Would DOMAIN-normalised noise (v = y/n) give the "same seed, same terrain" the user expects,
// while keeping true-hex isotropy? Compare three samplings of the SAME noise, same seed:
//   A square                      : u=x/n,               v=y/n
//   B hex, world-normalised (ships): u=(x+.5(y&1))/n,     v=y*sqrt(3)/2/n   <- crops in v
//   C hex, domain-normalised       : u=(x+.5(y&1))/n,     v=y/n             <- same v span
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const URL = 'file://' + path.resolve(__dirname, 'index.html');
(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1500);
  const r = await p.evaluate(() => {
    const HR = Math.sqrt(3) / 2, n = 192;
    RES = n; USE_GPU = false;
    const seed = 7, freq = 3, oct = 6, lac = 2, gain = 0.5;
    // replicate fbmField's accumulation exactly, with a pluggable (u,v)
    const build = (uv) => {
      const o = new Float32Array(n * n);
      let amps = 0, a = 1; for (let k = 0; k < oct; k++) { amps += a; a *= gain; }
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const [gu, gv] = uv(x, y);
        let sum = 0, amp = 1, f = freq;
        for (let k = 0; k < oct; k++) { sum += gnoise(gu * f, gv * f, seed + k * 7) * amp; amp *= gain; f *= lac; }
        o[y * n + x] = sum / amps;
      }
      return o;
    };
    const A = build((x, y) => [x / n, y / n]);
    const B = build((x, y) => [(x + 0.5 * (y & 1)) / n, y * HR / n]);
    const C = build((x, y) => [(x + 0.5 * (y & 1)) / n, y / n]);
    const rng = f => { let a = 1e9, b2 = -1e9; for (const v of f) { if (v < a) a = v; if (v > b2) b2 = v; } return b2 - a; };
    const span = rng(A);
    const cmp = (P, Q) => { let s = 0, w = 0; for (let i = 0; i < P.length; i++) { const d = Math.abs(P[i] - Q[i]); s += d; if (d > w) w = d; } return { mean: +((s / P.length) / span).toFixed(4), max: +(w / span).toFixed(4) }; };
    const pear = (P, Q) => { let sa = 0, sb = 0, m = P.length; for (let i = 0; i < m; i++) { sa += P[i]; sb += Q[i]; }
      const ma = sa / m, mb = sb / m; let nu = 0, da = 0, db = 0;
      for (let i = 0; i < m; i++) { const u2 = P[i] - ma, v2 = Q[i] - mb; nu += u2 * v2; da += u2 * u2; db += v2 * v2; }
      return +(nu / Math.sqrt(da * db)).toFixed(5); };
    RES = 512; buildIndex();
    return {
      worldNormalised_vs_square: { ...cmp(A, B), corr: pear(A, B) },
      domainNormalised_vs_square: { ...cmp(A, C), corr: pear(A, C) },
      spanA: +span.toFixed(4), spanB: +rng(B).toFixed(4), spanC: +rng(C).toFixed(4),
    };
  });
  console.log(JSON.stringify(r, null, 1));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
})().catch(e => { console.error('FATAL', e); process.exit(2); });
