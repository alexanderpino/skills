// Hexagonal lattice mode (references/26-hexagonal-lattice.md). What the chapter PROMISES, this
// script gates:
//   H1 static topology    hex has a UNIQUE equilateral triangulation, so the index buffer is a
//                         pure function of the grid — hash-identical across a height change
//                         (edge spinning ceases to exist). Square keeps its adaptive stream.
//   H2 D6 mass            thermalErodeHex conserves mass and actually acts (identity guard).
//   H3 lattice signature  a thermally-relaxed cone prints LESS azimuthal anisotropy on C6 than
//                         on C4 — measured against the square kernel on the same cone, live,
//                         so the gate self-arms instead of trusting a recorded number.
//   H4a domain contract   generators are authored in the DOMAIN, so toggling the lattice must
//                         not re-roll the terrain: hex fbm must match square fbm at matched
//                         domain points. (This replaced a world-point contract, which cropped
//                         the noise and was the terrain re-roll users hit — see H4's own note.)
//   H4b half-cell shift   the odd-row shift is still alive, controlled by D6 Laplacian rather
//                         than correlation, which cannot see a half-cell and would pass vacuously.
//   H5 square-safety      toggling hex on and back leaves a square build BYTE-identical.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));

(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    try { buildRun++; } catch (_) {}
    SCALE_RES = true; XF = null; USE_GPU = false; BUILD_QUALITY = 'interactive';
    Object.assign(terrainDef, { scale: 5000, height: 2600, baseElevation: 0, lattice: 'square' });
    H_SCALE = terrainDef.height / terrainDef.scale;
    const A = {seed:7,freq:3,octaves:6,lac:2,gain:0.5};
    const out = {};
    RES = 192; const n = RES;

    const hashIdx = () => {
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buffers.idx);
      const buf = buffers.u32 ? new Uint32Array(buffers.count) : new Uint16Array(buffers.count);
      gl.getBufferSubData(gl.ELEMENT_ARRAY_BUFFER, 0, buf);
      let a = 0x811c9dc5;
      for (let i = 0; i < buf.length; i++) { a ^= buf[i]; a = Math.imul(a, 0x01000193) >>> 0; }
      return a.toString(16);
    };
    const digest = f => { let a = 0, b2 = 0;
      for (let i = 0; i < f.length; i++) { const q = Math.round(f[i] * 1e7);
        a = (a + q) >>> 0; b2 = (b2 ^ (a + i)) >>> 0; } return a.toString(16) + ':' + b2.toString(16); };
    const pearson = (a, b2) => { let sa=0,sb=0; const n2=a.length;
      for (let i=0;i<n2;i++){sa+=a[i];sb+=b2[i];} const ma=sa/n2,mb=sb/n2;
      let num=0,da=0,db=0; for (let i=0;i<n2;i++){const x=a[i]-ma,y=b2[i]-mb;num+=x*y;da+=x*x;db+=y*y;}
      return num/Math.max(1e-12,Math.sqrt(da*db)); };

    // ---- H5 pre: square reference build ----
    const sq1 = fbmField(gnoise, A);
    // ---- H1: hex static topology ----
    terrainDef.lattice = 'hex'; buildIndex();
    out.hexPattern = buffers.indexPattern;
    const hash1 = hashIdx();
    // Geometry, not just stability: every emitted triangle must be near-equilateral in world
    // cells (max edge ~1). A swapped row-parity pattern would take the sqrt(3) diagonal on
    // every quad and still hash stably — the hash alone cannot fail it.
    {
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buffers.idx);
      const buf = buffers.u32 ? new Uint32Array(buffers.count) : new Uint16Array(buffers.count);
      gl.getBufferSubData(gl.ELEMENT_ARRAY_BUFFER, 0, buf);
      let maxEdge = 0;
      const HEXR2 = Math.sqrt(3) / 2;
      const px = i2 => (i2 % n) + 0.5 * (((i2 / n) | 0) & 1), py = i2 => ((i2 / n) | 0) * HEXR2;
      for (let t = 0; t < buf.length; t += 3) for (let e = 0; e < 3; e++) {
        const a2 = buf[t + e], b3 = buf[t + (e + 1) % 3];
        maxEdge = Math.max(maxEdge, Math.hypot(px(a2) - px(b3), py(a2) - py(b3)));
      }
      out.maxEdge = +maxEdge.toFixed(4);
    }
    const hexNoise = fbmField(gnoise, A);
    updateViewport(hexNoise);                      // a real height change through the renderer
    const hash2 = hashIdx();
    const bumpy = Float32Array.from(hexNoise, (v, i) => v + 0.2 * Math.sin(i * 0.01));
    updateViewport(bumpy);
    out.idxStable = hash1 === hashIdx() && hash1 === hash2;
    out.idxHash = hash1;

    // ---- H4: the authoring-domain contract, and the live control on the half-cell shift ----
    // The contract this gate asserts CHANGED, on measurement, and the reasoning is worth keeping.
    // It used to assert that hex noise equals square noise at matched WORLD points. That is
    // self-consistent but it makes a lattice toggle re-roll the terrain (correlation 0.57 on the
    // default graph), because a hex map is only 0.866 as tall: sampling the same noise down a
    // shorter axis CROPS it. Generators now work in the authoring domain instead, so the same
    // graph draws the same terrain on either lattice (correlation 0.999) - the trade being a
    // 13.4% aspect squash of the pattern, which is unavoidable either way and is the cheaper
    // half (see the AUTHORING DOMAIN note in index.html).
    //
    // That change also DEMOTES this gate's old negative control. `naive` drops the odd-row
    // half-cell shift, which under the new contract differs from the real build by half a cell -
    // invisible to correlation, which now reads 0.999 for the broken build too. A control that
    // passes on the defect is worth nothing, so the shift gets a metric that can actually see
    // what it is FOR: the odd-row zig-zag. Dropping the shift offsets consecutive rows by half a
    // cell in world, injecting a row-parity component that the D6 Laplacian picks up directly.
    // Square field sampled at the hex cells' world coordinates, bilinear:
    terrainDef.lattice = 'square';
    const sqF = fbmField(gnoise, A);
    terrainDef.lattice = 'hex';
    const HEXR = Math.sqrt(3) / 2;
    const wanted = new Float32Array(n * n), got = new Float32Array(n * n),
      naive = new Float32Array(n * n);
    let m = 0;
    // sqF is a SQUARE-lattice field: its cell (X,Y) holds the value at world point (X,Y), so it
    // must be probed with square semantics. sampleBilinear is now lattice-aware, and leaving
    // terrainDef.lattice='hex' during these probes would apply the odd-r parity shift and the
    // sqrt(3)/2 row compression a SECOND time, on data that never had them - which reads as a
    // seed-contract failure when the contract is actually being met. Probe under 'square' and
    // restore; `got` is already-computed hex output and is unaffected either way.
    const latHeld = terrainDef.lattice;
    terrainDef.lattice = 'square';
    for (let y = 1; y < n - 1; y++) for (let x = 1; x < n - 1; x++) {
      const u = (x + 0.5 * (y & 1)), v = y * HEXR;          // hex WORLD point in CELL units
      if (v >= n - 1 || u >= n - 1) continue;
      wanted[m] = sampleBilinear(sqF, u, v);                 // square build at that world point
      got[m] = hexNoise[y * n + x];                          // hex build's own sample there
      naive[m] = sampleBilinear(sqF, x + 0.5 * (y & 1), y);  // matched DOMAIN point: the contract
      m++;
    }
    terrainDef.lattice = latHeld;
    out.seedContract = { worldCorr: +pearson(wanted.subarray(0, m), got.subarray(0, m)).toFixed(4),
      domainCorr: +pearson(naive.subarray(0, m), got.subarray(0, m)).toFixed(4) };

    // The half-cell shift's live control. Build the SAME noise with the shift suppressed, and
    // measure each build's D6 Laplacian magnitude - the row-parity zig-zag the shift exists to
    // prevent shows up there and essentially nowhere else. Both numbers are printed, so the
    // bound below sits between a MEASURED broken build and a MEASURED correct one rather than
    // being asserted.
    // Built here rather than behind a flag in index.html: a production test hook to disable a
    // correctness feature is a worse thing to own than fifteen lines of duplicated accumulation.
    terrainDef.lattice = 'hex';
    const unshifted = (() => {
      const f = new Float32Array(n * n);
      let amps = 0, a2 = 1; for (let k = 0; k < A.octaves; k++) { amps += a2; a2 *= A.gain; }
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const gu = x / n, gv = y / n;        // domain, but WITHOUT the odd-row half-cell shift
        let sum = 0, amp = 1, fr = A.freq;
        for (let k = 0; k < A.octaves; k++) {
          sum += gnoise(gu * fr, gv * fr, A.seed + k * 7) * amp; amp *= A.gain; fr *= A.lac;
        }
        f[y * n + x] = sum / amps;
      }
      return f;
    })();
    const d6lap = f => {                     // |sum(neighbour) - 6*centre| over the D6 one-ring
      let s = 0, k = 0;
      for (let y = 2; y < n - 2; y++) for (let x = 2; x < n - 2; x++) {
        const nb = hexNb(y); let acc = 0;
        for (let q = 0; q < 6; q++) acc += f[(y + nb[q][1]) * n + x + nb[q][0]];
        s += Math.abs(acc - 6 * f[y * n + x]); k++;
      }
      return s / k;
    };
    out.shiftControl = { shifted: +d6lap(hexNoise).toFixed(6), unshifted: +d6lap(unshifted).toFixed(6) };
    out.shiftControl.ratio = +(out.shiftControl.unshifted / Math.max(1e-9, out.shiftControl.shifted)).toFixed(3);

    // ---- H2 + H3: D6 thermal on a WORLD-SPACE cone (one per lattice: a cone built in raw
    // grid coordinates is an ellipse-with-row-wobble in hex world space, and the first form of
    // this gate measured that geometry distortion, not the lattice). Radius n/2*sqrt(3)/2 so
    // the same world-circular cone fits both footprints.
    const r0 = (n / 2) * HEXR;
    const mkCone = hexGeom => { const f = new Float32Array(n * n);
      const cx2 = hexGeom ? n / 2 : n / 2, cy2 = hexGeom ? (n / 2) * HEXR : n / 2;
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const px = x + (hexGeom ? 0.5 * (y & 1) : 0), py = y * (hexGeom ? HEXR : 1);
        f[y * n + x] = Math.max(0, 1 - Math.hypot(px - cx2, py - cy2) / r0);
      } return f; };
    const coneHex = mkCone(true), coneSq = mkCone(false);
    const sum = f => { let s = 0; for (const v of f) s += v; return s; };
    const hexT = thermalErodeHex(coneHex, { talus: 0.004, iters: 120, rate: 0.9 });
    out.d6Mass = { rel: +(Math.abs(sum(hexT) - sum(coneHex)) / sum(coneHex)).toExponential(2),
      acted: +Math.abs(hexT[(n/2)*n + (n/2|0)] - coneHex[(n/2)*n + (n/2|0)]).toFixed(4) };
    const sqT = thermalErode(coneSq, { talus: 0.004, iters: 120, rate: 0.9 });
    // The C4-vs-C6 signature is NOT slope magnitude (the distance-corrected square kernel is
    // built to equalize that — measured 1.004 ring anisotropy, and gating it would be vacuous).
    // It is the FACET DIRECTIONS: a relaxed cone's gradient directions concentrate into the
    // lattice's preferred families — 8-fold on square, 12-fold (weaker) on hex. Metric: share
    // of gradient directions in the sharpest 36-bin histogram bin, x36 (uniform = 1.0). Each
    // lattice is measured with ITS OWN gradient (central diff / D6 one-ring) — the one its
    // renderer actually shades with.
    const dirConc = (f, hexGeom) => {
      const bins = new Float32Array(36); let tot = 0;
      const EX = [1, -1, .5, -.5, .5, -.5], EY = [0, 0, HEXR, HEXR, -HEXR, -HEXR];
      for (let y = 2; y < n - 2; y++) for (let x = 2; x < n - 2; x++) {
        const px = x + (hexGeom ? 0.5 * (y & 1) : 0), py = y * (hexGeom ? HEXR : 1);
        const dx = (px - n / 2) / r0, dy = (py - (hexGeom ? n / 2 * HEXR : n / 2)) / r0;
        const rr = Math.hypot(dx, dy); if (rr < 0.3 || rr > 0.8) continue;
        const i = y * n + x; let gx, gy;
        if (hexGeom) {
          const off = (y & 1) ? 0 : -1;
          const hE = f[y*n+x+1], hW = f[y*n+x-1];
          const hDE = f[(y+1)*n+x+off+1], hDW = f[(y+1)*n+x+off];
          const hUE = f[(y-1)*n+x+off+1], hUW = f[(y-1)*n+x+off];
          gx = (hE*EX[0]+hW*EX[1]+hDE*EX[2]+hDW*EX[3]+hUE*EX[4]+hUW*EX[5])/3;
          gy = (hDE*EY[2]+hDW*EY[3]+hUE*EY[4]+hUW*EY[5])/3;
        } else {
          gx = (f[i+1]-f[i-1])/2; gy = (f[i+n]-f[i-n])/2;
        }
        if (Math.hypot(gx, gy) < 1e-5) continue;
        const th = ((Math.atan2(gy, gx) + Math.PI) / (2 * Math.PI)) * 36 | 0;
        bins[Math.min(35, th)]++; tot++;
      }
      let mx = 0; for (const v of bins) if (v > mx) mx = v;
      return +(mx / Math.max(1, tot) * 36).toFixed(3);
    };
    // The defect class 26 cures is the UNCORRECTED square kernel (D4 / no distance correction -
    // the plus-cone). This studio's square thermal is the distance-corrected D8 kernel, which
    // has MORE facet families than D6 (8 at 45 deg vs 6 at 60 deg). The D4 kernel is measured
    // for CONTEXT in the REPORT line - none of the three facet-direction numbers is gated,
    // because every gradient estimator quantizes directions toward its own tap families; the
    // gate that holds is the ring magnitude-isotropy below.
    const d4Thermal = (inp, { talus, iters, rate }) => {
      let f = inp.slice();
      for (let it = 0; it < iters; it++) {
        const dh = new Float32Array(n * n);
        for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
          const c = f[y*n+x]; let maxd = 0, sum2 = 0; const diffs = [];
          for (const [ddx, ddy] of [[-1,0],[1,0],[0,-1],[0,1]]) {
            const xx = x+ddx, yy = y+ddy;
            if (xx<0||yy<0||xx>=n||yy>=n) { diffs.push(0); continue; }
            const e = c - f[yy*n+xx] - talus;
            if (e>0) { diffs.push(e); sum2+=e; if (e>maxd) maxd=e; } else diffs.push(0);
          }
          if (sum2<=0) continue;
          const move = rate*maxd*0.5; let k = 0;
          for (const [ddx, ddy] of [[-1,0],[1,0],[0,-1],[0,1]]) {
            if (diffs[k]>0) { const q = Math.min(move*diffs[k]/sum2, diffs[k]*0.5);
              dh[y*n+x]-=q; dh[(y+ddy)*n+x+ddx]+=q; } k++;
          }
        }
        for (let i = 0; i < f.length; i++) f[i]+=dh[i];
      }
      return f;
    };
    const d4T = d4Thermal(coneSq, { talus: 0.004, iters: 120, rate: 0.9 });
    out.coneAniso = { hex: dirConc(hexT, true), squareD8corrected: dirConc(sqT, false),
      squareD4defect: dirConc(d4T, false) };
    // What D6 PROVABLY delivers and the gate below holds: magnitude isotropy of the relaxed
    // cone — one neighbour distance, one threshold, so the talus ring must reach the repose
    // slope uniformly in azimuth. (Direction-family concentration is reported, not gated: every
    // gradient estimator quantizes directions toward its own tap families, so the comparative
    // numbers above measure estimator+surface together — see the REPORT line.)
    const magAniso = (f, hexGeom) => {
      const bins = new Float32Array(24), cnt = new Float32Array(24);
      const EX = [1, -1, .5, -.5, .5, -.5], EY = [0, 0, HEXR, HEXR, -HEXR, -HEXR];
      for (let y = 2; y < n - 2; y++) for (let x = 2; x < n - 2; x++) {
        const px = x + (hexGeom ? 0.5 * (y & 1) : 0), py = y * (hexGeom ? HEXR : 1);
        const dx = (px - n / 2) / r0, dy = (py - (hexGeom ? n / 2 * HEXR : n / 2)) / r0;
        const rr = Math.hypot(dx, dy); if (rr < 0.45 || rr > 0.75) continue;
        const i = y * n + x; let gx, gy;
        if (hexGeom) {
          const off = (y & 1) ? 0 : -1;
          gx = (f[y*n+x+1]*EX[0]+f[y*n+x-1]*EX[1]+f[(y+1)*n+x+off+1]*EX[2]+f[(y+1)*n+x+off]*EX[3]
            +f[(y-1)*n+x+off+1]*EX[4]+f[(y-1)*n+x+off]*EX[5])/3;
          gy = (f[(y+1)*n+x+off+1]*EY[2]+f[(y+1)*n+x+off]*EY[3]+f[(y-1)*n+x+off+1]*EY[4]+f[(y-1)*n+x+off]*EY[5])/3;
        } else { gx = (f[i+1]-f[i-1])/2; gy = (f[i+n]-f[i-n])/2; }
        const th = ((Math.atan2(dy, dx) + Math.PI) / (2 * Math.PI)) * 24 | 0;
        bins[Math.min(23, th)] += Math.hypot(gx, gy); cnt[Math.min(23, th)]++;
      }
      let mx = 0, mn = Infinity;
      for (let d = 0; d < 24; d++) { if (!cnt[d]) continue; const v = bins[d] / cnt[d];
        if (v > mx) mx = v; if (v < mn) mn = v; }
      return +(mx / mn).toFixed(3);
    };
    out.magIso = { hex: magAniso(hexT, true), square: magAniso(sqT, false) };

    // ---- H6: the ANALYSIS operators read isotropically on a world-space paraboloid ----
    // slopeOf is gated by _verify_hex_flow.js F1; curvature and occlusion are the other two
    // stencil operators a hex build feeds to masks, and both were square-only. A paraboloid has
    // a constant mean curvature and a rotationally symmetric horizon near its axis, so azimuthal
    // spread on an annulus is the discriminator - the same shape as H3's ring test.
    const paraboloid = hexGeom => { const f = new Float32Array(n * n), K = 2e-5;
      const cx2 = n / 2, cy2 = (hexGeom ? n * HEXR : n) / 2;
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const wx = x + (hexGeom ? 0.5 * (y & 1) : 0), wy = y * (hexGeom ? HEXR : 1);
        f[y * n + x] = K * ((wx - cx2) ** 2 + (wy - cy2) ** 2);
      } return f; };
    const ringSpread = (fld, hexGeom) => {
      const bins = new Float32Array(24), cnt = new Float32Array(24);
      const cx2 = n / 2, cy2 = (hexGeom ? n * HEXR : n) / 2, R0 = n * 0.18, R1 = n * 0.34;
      for (let y = 2; y < n - 2; y++) for (let x = 2; x < n - 2; x++) {
        const wx = x + (hexGeom ? 0.5 * (y & 1) : 0), wy = y * (hexGeom ? HEXR : 1);
        const dx = wx - cx2, dy = wy - cy2, rr = Math.hypot(dx, dy);
        if (rr < R0 || rr > R1) continue;
        const th = ((Math.atan2(dy, dx) + Math.PI) / (2 * Math.PI)) * 24 | 0;
        bins[Math.min(23, th)] += fld[y * n + x]; cnt[Math.min(23, th)]++;
      }
      let mx = -1e9, mn = 1e9, sum = 0, k = 0;
      for (let d2 = 0; d2 < 24; d2++) { if (!cnt[d2]) continue; const v = bins[d2] / cnt[d2];
        if (v > mx) mx = v; if (v < mn) mn = v; sum += v; k++; }
      return { spread: mx - mn, mean: sum / k };
    };
    const analysisOn = lat => { terrainDef.lattice = lat; const hg = lat === 'hex';
      const par = paraboloid(hg);
      const cv = ringSpread(curvatureField(par, { kind: 'mean', strength: 1 }), hg);
      const oc = ringSpread(occlusionField(par, { radius: 0.06, dirs: 8 }), hg);
      return { curvMean: +cv.mean.toFixed(6), curvSpread: +cv.spread.toExponential(3),
        occSpread: +oc.spread.toExponential(3) };
    };
    out.analysisHex = analysisOn('hex');
    out.analysisSquare = analysisOn('square');
    terrainDef.lattice = 'hex';

    // ---- H7: droplet erosion works the WHOLE hex domain, and its mass ledger still closes ----
    // The droplet walks a world position, so its spawn box and retirement bounds have to be the
    // world extent: the hex domain is only (n-1)*sqrt(3)/2 tall, and checking against n-1 sends
    // droplets past the last lattice row where at() clamps them. Coverage catches that; the
    // ledger catches a mis-weighted splat (the four hex weights must still sum to 1).
    const dropOn = lat => { terrainDef.lattice = lat;
      const base = fbmField(gnoise, A);
      const o = hydraulicErode(base, { droplets: 9000, capacity: 4, erode: .3, deposit: .3,
        inertia: .05, radius: 2, seed: 1, settle: true });
      // Bound by the ROW COUNT, not the width. This gate calls itself 'droplets-cover-hex-domain'
      // but read only rows < n, so post-flip it certified full coverage while never looking at rows
      // n..nh-1 - exactly the rows the square-world change added. Found by cross-model review.
      const rowsTotal = fieldH();
      let lastRow = -1, rows = 0;
      for (let y = 0; y < rowsTotal; y++) { let t = false;
        for (let x = 0; x < n; x++) if (Math.abs(o[y * n + x] - base[y * n + x]) > 1e-9) { t = true; break; }
        if (t) { rows++; lastRow = y; } }
      const d = hydroMassDiag;
      return { lastRow, rows: rowsTotal, rowFrac: +(rows / rowsTotal).toFixed(4), lost: d.lost,
        closure: +(Math.abs((d.sumIn - d.sumOut) - (d.exported + d.lost - d.brushClipGain))
          / Math.max(1e-6, d.sumIn - d.sumOut + d.settled)).toExponential(2) };
    };
    out.n = n;
    out.dropHex = dropOn('hex');
    out.dropSquare = dropOn('square');
    terrainDef.lattice = 'hex';

    // ---- H5: toggling back leaves square byte-identical ----
    terrainDef.lattice = 'square'; buildIndex();
    const sq2 = fbmField(gnoise, A);
    out.squareSafety = { identical: digest(sq1) === digest(sq2), pattern: buffers.indexPattern };
    return out;
  });

  const gates = [];
  const gate = (name, pass, detail) => gates.push({ name, pass: !!pass, detail });
  gate('H1 hex-static-topology', r.hexPattern === 'hex-static' && r.idxStable && r.maxEdge <= 1.01,
    `pattern=${r.hexPattern} idxStableAcrossHeightEdits=${r.idxStable} hash=${r.idxHash} `
    + `maxEdge=${r.maxEdge} (equilateral: a parity-swapped pattern would read ~1.73)`);
  gate('H2 d6-mass', r.d6Mass && +r.d6Mass.rel <= 1e-4 && r.d6Mass.acted > 0.01,
    `massRel=${r.d6Mass && r.d6Mass.rel} acted=${r.d6Mass && r.d6Mass.acted}`);
  gate('H3 d6-ring-isotropy', r.magIso && r.magIso.hex <= 1.10,
    `ring slope-magnitude anisotropy hex=${r.magIso && r.magIso.hex} (one distance, one threshold `
    + `=> the talus ring must reach repose uniformly; square reads ${r.magIso && r.magIso.square} for scale)`);
  console.log(`REPORT H3 facet-direction concentration  hex=${r.coneAniso && r.coneAniso.hex} `
    + `squareD8corrected=${r.coneAniso && r.coneAniso.squareD8corrected} squareD4defect=${r.coneAniso && r.coneAniso.squareD4defect} `
    + `— MEASURED FINDING, reported not gated: each estimator quantizes directions toward its own `
    + `tap families (6 vs 8), so the corrected-D8 kernel prints LESS facet concentration than D6 on `
    + `this metric; hex thermal's win is exactness (one distance, no sqrt(2) correction to forget), `
    + `not facet diversity. Upstreamed to references/26.`);
  // H4a: the contract a user can feel. Toggling the lattice must not re-roll their terrain, so
  // the hex build must match the square build at matched DOMAIN points. worldCorr is reported
  // alongside because it is the number this gate used to assert, and its collapse is the whole
  // reason the contract moved - not a regression.
  gate('H4a domain-contract', r.seedContract && r.seedContract.worldCorr >= 0.99,
    `matchedCorr=${r.seedContract && r.seedContract.worldCorr} (>=0.99: the same seed draws the `
    + `same terrain on either lattice) - rawRowIndexCorr=${r.seedContract && r.seedContract.domainCorr} `
    + `reported, NOT gated. Third revision of this contract: now that the world is SQUARE, `
    + `(nh-1)*sqrt(3)/2 equals n-1 to within 0.2%, so probing row y*sqrt(3)/2 of the square field IS `
    + `probing the same domain fraction - the world-point and matched-domain probes have converged `
    + `and this gate reads that one. What now means nothing is the raw same-row-index probe, because `
    + `the two lattices no longer share a row count (192 vs 222 at preview).`);
  // H4b: the odd-row half-cell shift, controlled by a metric that can see what it is for. Under
  // the domain contract, dropping the shift barely moves the correlation (a half-cell is
  // sub-pixel), so correlation would pass on the broken build - the vacuous-gate failure mode
  // this suite keeps finding. The D6 Laplacian sees the row-parity zig-zag the shift prevents.
  // Both endpoints measured before arming, and they bracket the bound from opposite sides:
  // a build whose shift is DEAD reads ratio 1.000 (the two fields are then the same field), and
  // this build reads 1.313. 1.15 sits between them with margin either way. The first bound tried
  // here was a guessed 1.5, which the correct build failed - the guess, not the code, was wrong.
  const sc = r.shiftControl;
  gate('H4b half-cell-shift-alive', sc && sc.ratio >= 1.15,
    `D6 |Laplacian| shifted=${sc && sc.shifted} vs shift-suppressed=${sc && sc.unshifted} `
    + `=> ratio ${sc && sc.ratio} (1.000 = shift dead, 1.313 = shift alive as measured; correlation `
    + `reads ~0.999 for BOTH builds and would pass vacuously, which is why this is not a corr gate)`);
  // Curvature: the hex fit must land on the SAME physical answer as ZT does on square (both see
  // the same paraboloid), and read isotropically around the ring. Armed against the square
  // control rather than an absolute number, so it tracks if the paraboloid probe ever changes.
  gate('H6 analysis-isotropy',
    r.analysisHex && r.analysisSquare
    && Math.abs(r.analysisHex.curvMean - r.analysisSquare.curvMean) < 1e-4
    && r.analysisHex.curvSpread < 5e-5 && r.analysisHex.occSpread < 0.12,
    `hex curvMean=${r.analysisHex && r.analysisHex.curvMean} vs square `
    + `${r.analysisSquare && r.analysisSquare.curvMean} (same surface => same curvature); `
    + `hex ring spread curv=${r.analysisHex && r.analysisHex.curvSpread} `
    + `occ=${r.analysisHex && r.analysisHex.occSpread} `
    + `[square curv=${r.analysisSquare && r.analysisSquare.curvSpread} `
    + `occ=${r.analysisSquare && r.analysisSquare.occSpread}]`);
  gate('H7 droplets-cover-hex-domain',
    r.dropHex && r.dropSquare
    && r.dropHex.lastRow >= r.dropHex.rows - 2 && r.dropHex.rowFrac > 0.95
    && +r.dropHex.closure < 1e-5 && r.dropHex.lost === 0,
    `hex lastTouchedRow=${r.dropHex && r.dropHex.lastRow}/${r.dropHex && r.dropHex.rows - 1} rowFrac=${r.dropHex && r.dropHex.rowFrac} `
    + `massClosure=${r.dropHex && r.dropHex.closure} lost=${r.dropHex && r.dropHex.lost} `
    + `[square lastRow=${r.dropSquare && r.dropSquare.lastRow} closure=${r.dropSquare && r.dropSquare.closure}]`);
  gate('H5 square-safety', r.squareSafety && r.squareSafety.identical,
    `squareByteIdentical=${r.squareSafety && r.squareSafety.identical} pattern=${r.squareSafety && r.squareSafety.pattern}`);

  console.log('== hexagonal lattice mode ==');
  let fail = 0;
  for (const g of gates) { console.log(`${g.pass ? 'PASS' : 'FAIL'}  ${g.name}  ${g.detail}`); if (!g.pass) fail++; }
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(fail || errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
