// Is stream power's HILLSLOPE DIFFUSION isotropic on each lattice?
//
// The full detachment-limited landscape equation is dh/dt = U - K*A^m*S^n + D*grad^2(h). The last
// term is what gives hillslopes a length and valleys a width: without it ridges sharpen without
// bound. It is also the only part of streamPowerErode that is a STENCIL rather than a graph walk,
// which is exactly the kind of code that carries a lattice assumption silently.
//
// grad^2 has no preferred direction. A diffusion operator that spreads faster along x than along y
// is not a discretisation detail - it is a different equation, and it prints the array's axes onto
// every ridge the node relaxes. `26` calls a visible lattice direction always a defect.
//
// THE MEASUREMENT. Diffuse an impulse and take the SECOND-MOMENT TENSOR of the result. For a
// diffusion tensor D, variance grows as sigma^2 = 2*D*t along each principal axis, so the aspect
// ratio sqrt(lmax/lmin) is exactly sqrt(Dmax/Dmin) - it reads the operator's anisotropy directly
// and is independent of how long it ran. Positions are in WORLD units: on hex a row step is
// sqrt(3)/2 of a column step, and measuring in array space would manufacture the anisotropy this
// file exists to detect. Same instrument as _verify_blur_isotropy, for the same reason.
//
// Driven through streamPowerErode with Kdt=0 and Udt=0 so diffusion is the only term that acts.
// The incision loop still runs, and with Kdt=0 its C is 0, so h[i]=(h[i]+0)/(1+0) is identity and
// the never-incise-below-your-receiver clamp cannot fire on a monotone bump. The mass gate below
// is what confirms that claim rather than assuming it.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

let failures = 0;
const gate = (name, ok, detail) => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}  ${detail}`); if (!ok) failures++; };

(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  const errors = []; p.on('pageerror', (e) => errors.push(String(e.message).slice(0, 200)));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    const HEXR = Math.sqrt(3) / 2;
    SCALE_RES = true; XF = null; USE_GPU = false; BUILD_QUALITY = 'interactive';
    Object.assign(terrainDef, { scale: 5000, height: 2600, baseElevation: 0, lattice: 'square' });
    RES = 128;

    // Ddt = 0.125 keeps the scheme at ONE substep (the <= 0.24 branch) so this measures the
    // stencil and not the substepping, and sits at the square scheme's zero-amplification point
    // for the Nyquist mode (1 - 8c = 0). A larger dose rings, and ringing puts negative values in
    // the tail that would bias a second-moment sum.
    const DDT = 0.125, ITERS = 60;

    const measure = (lattice) => {
      terrainDef.lattice = lattice;
      const n = fieldW(), nh = fieldH(), hex = lattice === 'hex';
      const f = newField();
      const cx = n >> 1, cy = nh >> 1;
      f[cy * n + cx] = 1;

      const o = streamPowerErode(f, { Kdt: 0, Udt: 0, m: 0.5, iters: ITERS, Ddt: DDT });

      const wx = (x, y) => x + (hex ? 0.5 * (y & 1) : 0);
      const wy = (y) => y * (hex ? HEXR : 1);
      const ox = wx(cx, cy), oy = wy(cy);

      let total = 0, peak = 0, mxx = 0, myy = 0, mxy = 0, neg = 0;
      for (let y = 0; y < nh; y++) for (let x = 0; x < n; x++) {
        const v = o[y * n + x];
        if (v < 0) { neg += -v; continue; }
        if (v <= 1e-7) continue;
        const dx = wx(x, y) - ox, dy = wy(y) - oy;
        total += v; if (v > peak) peak = v;
        mxx += v * dx * dx; myy += v * dy * dy; mxy += v * dx * dy;
      }
      mxx /= total; myy /= total; mxy /= total;
      const tr = mxx + myy, det = mxx * myy - mxy * mxy;
      const disc = Math.sqrt(Math.max(0, tr * tr / 4 - det));
      const l1 = tr / 2 + disc, l2 = tr / 2 - disc;
      return {
        lattice, n, nh,
        anisotropy: +Math.sqrt(l1 / Math.max(l2, 1e-12)).toFixed(4),
        sigmaMajor: +Math.sqrt(l1).toFixed(3),
        sigmaMinor: +Math.sqrt(l2).toFixed(3),
        mass: +total.toFixed(6),
        negMass: +neg.toFixed(6),
        peak: +peak.toFixed(6),
      };
    };

    const out = { square: measure('square'), hex: measure('hex'), DDT, ITERS };
    terrainDef.lattice = 'square';
    return out;
  });

  console.log(JSON.stringify(r, null, 1));

  for (const lat of ['square', 'hex']) {
    const m = r[lat];
    // CONTROLS ON THE MEASUREMENT ITSELF, not on the operator.
    //
    // Mass: diffusion conserves it. If streamPowerErode's incision loop or its edge clamp were
    // touching the bump - the assumption this whole setup rests on - mass would not come back at
    // ~1, and the anisotropy number would be measuring something other than the stencil.
    gate(`hillslope-mass-${lat}`, Math.abs(m.mass - 1) < 0.02,
      `mass=${m.mass} (impulse of 1; Kdt=0 so diffusion is the only term that may act on it)`);
    // A tail that has gone negative biases a second-moment sum toward whichever axis rang hardest.
    gate(`hillslope-no-ringing-${lat}`, m.negMass < 0.01,
      `negative mass = ${m.negMass} — at Ddt=${r.DDT} the scheme should not ring`);
    // A degenerate minor axis makes the ratio meaningless, and a bump that never spread would
    // report a perfect 1.0 while proving nothing.
    gate(`hillslope-spread-${lat}`, m.sigmaMinor > 1.5,
      `sigma major/minor = ${m.sigmaMajor}/${m.sigmaMinor} after ${r.ITERS} iters — an impulse that `
      + `barely moved would read as isotropic for the wrong reason`);
  }

  // ARMED BETWEEN MEASURED ENDPOINTS. The diffusion stencil was a square 5-point Laplacian,
  //     h[i] += c*(t[i-1]+t[i+1]+t[i-n]+t[i+n]-4*t[i])
  // applied on BOTH lattices. On odd-r hex those four array offsets ARE lattice neighbours - but
  // four of six, and WHICH two are missing depends on row parity. In world directions:
  //     even rows  0, 180,  60, 300      offsets sum to (+1, 0)
  //     odd rows   0, 180, 120, 240      offsets sum to (-1, 0)
  // A Laplacian's offsets sum to zero. This subset's do not, so it carries a first-derivative term:
  // it ADVECTS material +x on even rows and -x on odd rows, a per-row zig-zag under the smoothing.
  //
  //     before (square stencil on both)   square 1.0000   hex 1.1595
  //     after  (D6 stencil on hex)        square 1.0000   hex 1.0000
  //
  // A leading-order tensor argument for the four-offset subset predicts sqrt(2.5/1.5) = 1.291 and
  // the measurement is 1.1595. The gap is that broken first-order term interacting with the parity
  // flip, which the tensor argument does not model. The bound is armed on the MEASUREMENT, 1.06:
  // well above the residual on either lattice and well below 1.16.
  console.log(`\nREPORT  hillslope-anisotropy  square=${r.square.anisotropy}  hex=${r.hex.anisotropy}`);

  gate('hillslope-square-isotropic', r.square.anisotropy < 1.06,
    `square=${r.square.anisotropy} — the control: the 5-point Laplacian was written for this lattice, `
    + `so a failure here means the MEASUREMENT is wrong, not the stencil`);
  gate('hillslope-hex-isotropic', r.hex.anisotropy < 1.06,
    `hex=${r.hex.anisotropy} (square stencil on hex: 1.1595) — six neighbours, not four of them`);

  // THE CONSTANT, which the isotropy gates above CANNOT SEE. This was very nearly the vacuous
  // pattern again: six neighbours with the wrong coefficient produce a perfectly ROUND response of
  // the wrong WIDTH, and every check above passes on it. That is not hypothetical - it is the exact
  // shape of the defect MC-3 is named for. Summing six equidistant neighbours gives
  // (3s^2/2)*grad^2(h), not s^2*grad^2(h), so the isotropic operator is (2/(3s^2))*sum; keeping the
  // square 1/s^2 makes diffusivity 1.5x too high, and sigma sqrt(1.5) = 1.22x too wide.
  //
  // Diffusion is a physical rate, so the same Ddt must produce the same WIDTH on both lattices -
  // hillslope length is set by D, and a lattice that quietly diffuses 1.5x harder gives shorter
  // hillslopes and wider valleys from identical parameters. Measured, at Ddt=0.125 x 60 iters:
  //     square           sigma 3.873
  //     hex, 2/3         sigma 3.873   (ratio 1.0000)
  //     hex, constant 1  sigma 4.743   (ratio 1.2246 = sqrt(1.5))
  // The band is 0.97-1.10: clear of 1.2246 by a wide margin, and loose enough not to fail on the
  // border treatment differing between two lattices with different row counts.
  const widthRatio = +(r.hex.sigmaMajor / Math.max(1e-9, r.square.sigmaMajor)).toFixed(4);
  gate('hillslope-diffusivity-matches', widthRatio > 0.97 && widthRatio < 1.10,
    `hex/square sigma = ${widthRatio} (${r.hex.sigmaMajor} vs ${r.square.sigmaMajor}) — with the `
    + `constant left at 1/s^2 instead of 2/(3s^2) this reads 1.2246 while every isotropy gate above `
    + `still passes, because the response stays round and only gets wider`);

  gate('hillslope-no-page-errors', errors.length === 0, errors.length ? JSON.stringify(errors) : 'none');

  await b.close();
  console.log(failures ? `\n${failures} gate(s) failed.` : '\nhillslope diffusion is isotropic on both lattices.');
  process.exit(failures ? 1 : 0);
})().catch((e) => { console.error('FATAL ' + String(e).slice(0, 300)); process.exit(2); });
