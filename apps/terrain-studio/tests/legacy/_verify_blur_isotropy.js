// Is blurField isotropic on each lattice?
//
// A Gaussian blur is defined by being direction-free: blur an impulse and the response must be a
// round spot, whatever azimuth you measure along. Anything else is the discretisation printing
// through, which `26` calls out as always a defect — the preferred direction is a property of the
// array and nothing in the world put it there.
//
// WHY THIS MATTERS BEYOND BLUR. Masks are built from blur: slope masks, height masks and every
// soft-edged selection run through blurField, and D7 puts blur in L0 for exactly that reason. An
// anisotropic blur biases every mask that consumes it, and a biased mask biases everything the mask
// gates. It is the lowest thing in the stack that can quietly tilt the whole image.
//
// THE MEASUREMENT. Blur an impulse and take the SECOND-MOMENT TENSOR of the response: its
// eigenvalues are the squared widths along the principal axes, so sqrt(lmax/lmin) is the aspect
// ratio of the blur ellipse - 1.0 for a round spot. Positions are computed in WORLD units, because
// on hex a row step is sqrt(3)/2 of a column step and an array-space measure would manufacture the
// anisotropy it is meant to detect.
//
// A ring sample was tried first and is fragile: the kernel is truncated to a SQUARE support, so a
// ring outside it along the axes but inside along the diagonals reads ~0 in one bin and the max/min
// ratio explodes. That first version reported 2.4e9 for a blur that was fine.
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

    const measure = (lattice, radius) => {
      terrainDef.lattice = lattice;
      const n = fieldW(), nh = fieldH(), hex = lattice === 'hex';
      // impulse at the field centre
      const f = newField();
      const cx = n >> 1, cy = nh >> 1;
      f[cy * n + cx] = 1;
      const o = blurField(f, { radius });

      // world position of a cell, and of the impulse
      const wx = (x, y) => x + (hex ? 0.5 * (y & 1) : 0);
      const wy = (y) => y * (hex ? HEXR : 1);
      const ox = wx(cx, cy), oy = wy(cy);

      // THE SECOND-MOMENT TENSOR, not a ring. A ring sample was the obvious choice and it is
      // fragile: the kernel is truncated to a SQUARE support of side 2r+1, so a ring at radius
      // 1.15r crosses outside the support along the axes while staying inside along the diagonals.
      // One bin reads ~0, the max/min ratio explodes, and the first run of this file duly reported
      // an anisotropy of 2.4e9 for a blur that is fine. The square control is what exposed it.
      //
      // The covariance of the response uses every cell instead of a thin annulus:
      //     M = Σ v·[[dx², dx·dy], [dx·dy, dy²]] / Σ v
      // Its eigenvalues are the squared widths along the principal axes, so √(λmax/λmin) is the
      // aspect ratio of the blur ellipse — exactly 1 for a round spot, and undefined-free because
      // λmin cannot be zero for any kernel with support in two dimensions.
      let total = 0, peak = 0, mxx = 0, myy = 0, mxy = 0;
      for (let y = 0; y < nh; y++) for (let x = 0; x < n; x++) {
        const v = o[y * n + x];
        if (v <= 0) continue;
        const dx = wx(x, y) - ox, dy = wy(y) - oy;
        total += v; if (v > peak) peak = v;
        mxx += v * dx * dx; myy += v * dy * dy; mxy += v * dx * dy;
      }
      mxx /= total; myy /= total; mxy /= total;
      const tr = mxx + myy, det = mxx * myy - mxy * mxy;
      const disc = Math.sqrt(Math.max(0, tr * tr / 4 - det));
      const l1 = tr / 2 + disc, l2 = tr / 2 - disc;
      return {
        lattice, radius, n, nh,
        anisotropy: +Math.sqrt(l1 / Math.max(l2, 1e-12)).toFixed(4),
        sigmaMajor: +Math.sqrt(l1).toFixed(3),
        sigmaMinor: +Math.sqrt(l2).toFixed(3),
        mass: +total.toFixed(6),          // a blur must conserve mass
        peak: +peak.toFixed(6),
      };
    };

    const out = { square: [], hex: [] };
    for (const rad of [3, 6]) { out.square.push(measure('square', rad)); out.hex.push(measure('hex', rad)); }
    terrainDef.lattice = 'square';
    return out;
  });

  console.log(JSON.stringify(r, null, 1));

  for (const lat of ['square', 'hex']) {
    for (const m of r[lat]) {
      // Mass conservation is a control on the measurement itself: a blur that loses mass at the
      // border would flatten the ring and make anything look isotropic.
      gate(`blur-mass-${lat}-r${m.radius}`, Math.abs(m.mass - 1) < 0.02,
        `mass=${m.mass} (impulse of 1; clamped edges keep it, so ~1)`);
      gate(`blur-width-${lat}-r${m.radius}`, m.sigmaMinor > 0.5,
        `sigma major/minor = ${m.sigmaMajor}/${m.sigmaMinor} — a degenerate minor axis would make the ratio meaningless`);
    }
  }

  // ARMED BETWEEN MEASURED ENDPOINTS. blurField used to be one separable X-then-Y Gaussian for
  // both lattices, and on hex the vertical pass walked straight down the ARRAY - not a lattice
  // direction, and with a row spacing of 1 where the truth is sqrt(3)/2. Measured on an impulse:
  //
  //     before (separable, both lattices)   square 1.0000 / 1.0000   hex 1.1847 / 1.1625
  //     after  (3-axis lattice-line on hex) square 1.0000 / 1.0000   hex 1.0000 / 1.0000
  //
  // The bound sits at 1.05: comfortably above float noise at exact isotropy, and well below the
  // 1.16-1.18 the off-lattice blur produced. Reverting blurField to the single separable path fails
  // this gate on hex and leaves square passing, which is what makes it a lattice gate rather than a
  // blur gate.
  const sq = r.square.map((m) => m.anisotropy), hx = r.hex.map((m) => m.anisotropy);
  console.log(`
REPORT  blur-anisotropy  square=[${sq}]  hex=[${hx}]`);

  gate('blur-square-isotropic', sq.every((a) => a < 1.05),
    `square=[${sq}] - the control: the separable blur was written for this lattice, so a failure
     here means the MEASUREMENT is wrong, not the blur`);
  gate('blur-hex-isotropic', hx.every((a) => a < 1.05),
    `hex=[${hx}] (before the 3-axis blur: 1.1847, 1.1625) - three 1-D Gaussians at 60 degrees
     compose to a round spot; two along the array axes do not`);

  gate('blur-no-page-errors', errors.length === 0, errors.length ? JSON.stringify(errors) : 'none');

  await b.close();
  console.log(failures ? `\n${failures} gate(s) failed.` : '\nblur isotropy OK.');
  process.exit(failures ? 1 : 0);
})().catch((e) => { console.error('FATAL ' + String(e).slice(0, 300)); process.exit(2); });
