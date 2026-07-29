// Wireframe overlay: does it draw REAL MESH EDGES, or a triangle LIST reinterpreted as a strip?
//
// THE DEFECT. drawTerrain() drew the overlay with
//     gl.drawElements(wire?gl.LINE_STRIP:gl.TRIANGLES, buffers.count, ...)
// buffers.idx is a triangle LIST (3 consecutive indices = 1 triangle). A LINE_STRIP joins EVERY
// consecutive pair in buffer order, so at each triangle boundary (k%3===2) it draws a segment from
// one triangle's last vertex to the next triangle's FIRST vertex. Those "stitches" are not edges of
// the mesh. Some land on a real edge by accident - the two triangles of one quad share their
// diagonal, so the intra-quad stitch falls on it - and the rest are pure fiction, including one
// full-width jump at every row wrap. Symmetrically, the strip never draws each triangle's third
// edge unless a stitch happens to cover it, so it also OMITS real edges. The overlay therefore drew
// a lattice that does not exist, which is why hex mode was unreadable on screen. Broken on BOTH
// lattices: the hex triangulation is a triangle list too.
//
// MEASURED RED, LIVE, ON THE BROKEN BUILD (index.html at git 214ccc3; RES=512, buffers.count
// 1,566,726, 522,242 triangles, 784,385 unique mesh edges - the analytic count, confirmed):
//                                     square (adaptive fit)     hex (static equilateral)
//   drawn segments                            1,566,725                  1,566,725
//   FAKE segments                               130,967 (8.36%)            130,560 (8.33%)
//   triangle-boundary stitches                  522,241                    522,241
//     ... of which fake                         130,967                    130,560
//     ... coinciding with a real edge           391,274                    391,681
//   fake segments INSIDE a triangle                   0                          0   (as predicted)
//   real edges drawn more than once             651,884                    652,291
//   real edges never drawn                          511                        511
//   buffers.lineIdx / buffers.lineCount          absent / null              absent / null
// and on the same broken build after the W5 height edit (an fbm field whose fit picks mostly
// anti-diagonals, so far more stitches land on a real edge by luck):
//   1,566,725 segments, 2,653 fake (0.17%), 780,198 duplicated, 511 missing.
// MEASURED GREEN, same oracle, on the fixed build (deduplicated edge buffer, gl.LINES):
//   784,385 segments, fake 0, duplicates 0, missing 0, lineCount 1,568,770 == 2*784,385, on both
//   lattices and after the height edit.
//
// THRESHOLD ARMING, and why a band would be VACUOUS here. The obvious scale-free form of W1 would
// be "fakeFraction <= 0.005", nicely between the measured broken 0.0836 and the fixed 0.0000. That
// arming is falsified by this oracle's own data: whether a stitch is fake depends on which diagonal
// the adaptive fit chose for that quad (on an anti quad the stitch lands on the anti diagonal and
// IS a real edge), so the fake fraction is a function of the TERRAIN, and it was measured swinging
// from 0.0836 to 0.0017 on the identical broken code just by changing the height field. 0.0017
// slips under a 0.005 band - the band would have passed the broken build. So every gate here is
// armed at exact zero / exact equality instead. That is the honest arming for a combinatorial
// invariant: the metric counts segments that are not edges of the triangulation actually uploaded,
// the broken build sits at 2,653-130,967 and a correct edge buffer sits at 0 with no continuum in
// between, and the whole gap IS the margin. Nothing content-dependent is thresholded at all - the
// ground truth is rebuilt from the index buffer on the GPU on this run, so adaptive diagonal
// spinning cannot make it stale.
//
// GATES
//   W0 metric-discriminates  identity/negative control, and it must PASS on the broken build too or
//                            the counts below mean nothing. The classifier must accept all
//                            1,566,726 triangle-list edges; must reject the OTHER diagonal of quad
//                            (0,0) (exactly one of the two is in the mesh - the single
//                            discrimination a wireframe exists to make); must reject a row-wrapping
//                            pair whose index delta is 1 and therefore *looks* horizontal; and the
//                            edge set it recovers must equal the analytic 3*(n-1)^2 + 2*(n-1).
//   W1 no-fake-segments      every segment the wireframe draw ACTUALLY issues - observed by hooking
//                            gl.drawElements and reading back whichever buffer it bound - is an
//                            edge of the uploaded triangulation, and no edge is drawn twice.
//   W2 edge-count            buffers.lineCount === 2*(3*(n-1)^2 + 2*(n-1)).
//   W3 both-lattices         W1+W2 hold for square AND hex, the wire draw is gl.LINES from
//                            buffers.lineIdx, and with the wireframe OFF nothing draws lines at all
//                            while the terrain still draws TRIANGLES from buffers.idx.
//   W4 edge-coverage         the overlay covers every unique mesh edge exactly once (the strip
//                            missed 511 - the left-column verticals no stitch ever reaches).
//   W5 no-stale-edges        after a height edit spins the adaptive diagonals, the overlay follows.
//                            Self-arming: the gate also asserts the edit actually spun diagonals,
//                            so it cannot pass by the topology having stood still.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  const errors = []; p.on('pageerror', e => errors.push(e.message));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600);

  const r = await p.evaluate(() => {
    const out = { lattices: {} };
    const MODE = { 0:'POINTS', 1:'LINES', 2:'LINE_LOOP', 3:'LINE_STRIP',
      4:'TRIANGLES', 5:'TRIANGLE_STRIP', 6:'TRIANGLE_FAN' };
    const isLine = m => m === gl.LINES || m === gl.LINE_STRIP || m === gl.LINE_LOOP;

    // Observe the REAL draw calls instead of trusting a helper: "what does the wireframe draw" is
    // answered by the primitive mode and the element buffer bound at draw time, whatever function
    // produced them. This is what makes the gate survive the fix being written differently.
    const origDrawElements = gl.drawElements;
    let log = null;
    gl.drawElements = function (mode, count, type, offset) {
      if (log) log.push({ mode, count, ebo: gl.getParameter(gl.ELEMENT_ARRAY_BUFFER_BINDING) });
      return origDrawElements.call(gl, mode, count, type, offset);
    };
    const readIdx = (buf, count) => {
      const arr = buffers.u32 ? new Uint32Array(count) : new Uint16Array(count);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf);
      gl.getBufferSubData(gl.ELEMENT_ARRAY_BUFFER, 0, arr);
      return arr;
    };
    const popcount = a => { let c = 0;
      for (let i = 0; i < a.length; i++) { let m = a[i]; while (m) { c += m & 1; m >>= 1; } } return c; };

    // ---- ground truth: the edge set of the triangulation that is ACTUALLY on the GPU right now ----
    // Every edge of this lattice joins two indices differing by 1 (horizontal), n (vertical), n+1
    // (main diagonal) or n-1 (anti diagonal), so one nibble per vertex stores the whole set exactly
    // - no hashing, no collisions, no per-quad case analysis. A pair whose delta falls outside that
    // family, or whose bit was never set (a quad's OTHER diagonal, a row-wrapping "delta 1" jump, a
    // leap across the mesh), is not an edge of this mesh.
    const groundTruth = () => {
      const n = RES, tri = readIdx(buffers.idx, buffers.count);
      const slot = d => d === 1 ? 1 : d === n - 1 ? 2 : d === n ? 4 : d === n + 1 ? 8 : 0;
      const mask = new Uint8Array(n * n);
      let offLattice = 0;
      for (let t = 0; t + 2 < tri.length; t += 3) for (let e = 0; e < 3; e++) {
        const u = tri[t + e], v = tri[t + (e + 1) % 3];
        const a = u < v ? u : v, s = slot(u < v ? v - u : u - v);
        if (!s) { offLattice++; continue; }
        mask[a] |= s;
      }
      const uniqueRealEdges = popcount(mask);
      const isReal = (u, v) => { if (u === v) return false;
        const a = u < v ? u : v, s = slot(u < v ? v - u : u - v);
        return !!s && !!(mask[a] & s); };
      const classify = seg => {
        const seen = new Uint8Array(n * n);
        let real = 0, fake = 0, dup = 0; const ex = [];
        for (let k = 0; k < seg.length; k++) {
          const u = seg.u(k), v = seg.v(k);
          if (isReal(u, v)) {
            real++;
            const a = u < v ? u : v, s = slot(u < v ? v - u : u - v);
            if (seen[a] & s) dup++; else seen[a] |= s;
          } else { fake++; if (ex.length < 4) ex.push(u + '->' + v + '(d=' + (v - u) + ')'); }
        }
        const covered = popcount(seen);
        return { segments: seg.length, realSegments: real, fakeSegments: fake,
          fakeFraction: +(fake / Math.max(1, seg.length)).toFixed(4), duplicatedRealEdges: dup,
          coveredRealEdges: covered, missingRealEdges: uniqueRealEdges - covered, fakeExamples: ex };
      };
      // The diagonal each quad chose, so a later build can be compared against this one.
      const diagSig = () => { const q = (n - 1) * (n - 1), d = new Uint8Array(q);
        for (let k = 0; k < q; k++) { const i = ((k / (n - 1)) | 0) * n + (k % (n - 1));
          d[k] = tri[k * 6 + 2] === i + n + 1 ? 1 : 0; } return d; };
      return { n, tri, uniqueRealEdges, offLatticeTriangleEdges: offLattice, isReal, classify, diagSig };
    };

    // Render once with the wireframe off and once with it on, capturing every element draw.
    const renderBoth = () => {
      wire = false; log = []; renderGL(); const off = log;
      wire = true;  log = []; renderGL(); const on = log; log = null; wire = false;
      return { off, on };
    };
    const nameDraw = d => ({ mode: MODE[d.mode] || d.mode, count: d.count,
      src: d.ebo === buffers.idx ? 'buffers.idx'
        : (buffers.lineIdx && d.ebo === buffers.lineIdx) ? 'buffers.lineIdx' : 'other' });

    // Classify whatever the wireframe draw bound, as the primitive it was drawn with.
    const inspectWireDraw = (draws, G, M) => {
      M.lineDrawsWithWireOff = draws.off.filter(d => isLine(d.mode)).length;      // negative control: 0
      M.trianglesWithWireOff = draws.off.filter(d => d.mode === gl.TRIANGLES && d.ebo === buffers.idx).length;
      M.drawsWireOn = draws.on.map(nameDraw);
      M.hasLineIdx = !!buffers.lineIdx;
      M.lineCount = buffers.lineCount === undefined ? null : buffers.lineCount;
      const wd = draws.on.find(d => isLine(d.mode));
      if (!wd) { M.wireDraw = null; M.source = null; return M; }
      M.wireDraw = nameDraw(wd);
      const arr = readIdx(wd.ebo, wd.count);
      if (wd.mode === gl.LINES) {
        M.source = G.classify({ length: arr.length >> 1, u: k => arr[2 * k], v: k => arr[2 * k + 1] });
        M.source.kind = 'LINES';
      } else {
        // LINE_STRIP / LINE_LOOP: segment k joins arr[k] and arr[k+1], for EVERY k.
        M.source = G.classify({ length: Math.max(0, arr.length - 1), u: k => arr[k], v: k => arr[k + 1] });
        M.source.kind = MODE[wd.mode];
        // Anatomy of the failure. k%3===2 spans a triangle boundary (a stitch); k%3 in {0,1} lies
        // inside one triangle and so is always a genuine edge of it. Stitches that land on a real
        // edge by accident (a quad's two triangles share their diagonal) are NOT counted as fake -
        // the conservative reading of the defect.
        let stitches = 0, stitchFake = 0, insideFake = 0;
        for (let k = 0; k + 1 < arr.length; k++) {
          const ok = G.isReal(arr[k], arr[k + 1]);
          if (k % 3 === 2) { stitches++; if (!ok) stitchFake++; } else if (!ok) insideFake++;
        }
        M.stitch = { triangleBoundarySegments: stitches, stitchesThatAreFake: stitchFake,
          stitchesCoincidingWithARealEdge: stitches - stitchFake, fakeInsideATriangle: insideFake };
      }
      return M;
    };

    const measure = lattice => {
      terrainDef.lattice = lattice;
      updateViewport(curField || newField(), activePreviewNode(), { color: false });
      const G = groundTruth(), n = G.n;
      const M = { lattice, n, pattern: buffers.indexPattern, triIndexCount: buffers.count,
        uniqueRealEdges: G.uniqueRealEdges, offLatticeTriangleEdges: G.offLatticeTriangleEdges,
        analyticEdges: (rows => 3 * (n - 1) * (rows - 1) + (n - 1) + (rows - 1))(fieldH()) };
      M.analyticLineCount = 2 * M.analyticEdges;
      // ---- W0 controls: prove the metric can tell a real edge from a plausible fake ----
      let triEdgeFake = 0;
      for (let t = 0; t + 2 < G.tri.length; t += 3) for (let e = 0; e < 3; e++)
        if (!G.isReal(G.tri[t + e], G.tri[t + (e + 1) % 3])) triEdgeFake++;
      const mainD = G.isReal(0, n + 1), antiD = G.isReal(1, n);
      M.control = { triangleListEdgesRejected: triEdgeFake,
        quad0MainDiagonalReal: mainD, quad0AntiDiagonalReal: antiD,
        quad0DiagonalsExclusive: mainD !== antiD,       // exactly one exists => the other is rejected
        rowWrapPairRejected: !G.isReal(n - 1, n),       // delta 1, but it wraps a row
        farLeapRejected: !G.isReal(0, n * n - 1), skipPairRejected: !G.isReal(0, 2) };
      return inspectWireDraw(renderBoth(), G, M);
    };

    out.lattices.square = measure('square');
    out.lattices.hex = measure('hex');

    // ---- W5: the overlay must follow the adaptive diagonals when the height changes ----
    // Square only: hex topology is static by construction. The edge buffer is built once and cached,
    // so a height edit that re-streams the triangle indices must invalidate it. Ground truth is
    // re-derived from the NEW triangle buffer, so a stale overlay reads as fake segments.
    terrainDef.lattice = 'square';
    const fA = fbmField(gnoise, { seed: 7, freq: 3, octaves: 6, lac: 2, gain: 0.5 });
    updateViewport(fA, null, { color: false });
    renderBoth();                                        // force the edge buffer to be built for fA
    const diagA = groundTruth().diagSig();
    const fB = Float32Array.from(fA, (v, i) => v + 0.25 * Math.sin(i * 0.0173));
    updateViewport(fB, null, { color: false });
    const GB = groundTruth(), diagB = GB.diagSig();
    let spun = 0; for (let k = 0; k < diagA.length; k++) if (diagA[k] !== diagB[k]) spun++;
    out.stale = inspectWireDraw(renderBoth(), GB, { lattice: 'square-after-height-edit',
      n: GB.n, pattern: buffers.indexPattern, uniqueRealEdges: GB.uniqueRealEdges,
      analyticEdges: (rows => 3 * (GB.n - 1) * (rows - 1) + (GB.n - 1) + (rows - 1))(fieldH()), diagonalsSpunByTheEdit: spun });
    out.stale.analyticLineCount = 2 * out.stale.analyticEdges;

    terrainDef.lattice = 'square';
    updateViewport(fA, null, { color: false });
    gl.drawElements = origDrawElements; try { delete gl.drawElements; } catch (_) {}
    return out;
  });

  const gates = [];
  const gate = (name, pass, detail) => gates.push({ name, pass: !!pass, detail });
  const sq = r.lattices.square, hx = r.lattices.hex, st = r.stale;
  const src = m => (m && m.source) || {};
  const ctl = m => (m && m.control) || {};
  const one = m => !m ? 'missing' : `n=${m.n} pattern=${m.pattern} kind=${src(m).kind || 'NO-LINE-DRAW'} `
    + `drawnFrom=${m.wireDraw ? m.wireDraw.src : 'none'} segments=${src(m).segments} `
    + `fake=${src(m).fakeSegments} (${(src(m).fakeFraction * 100).toFixed(2)}%) `
    + `dupEdges=${src(m).duplicatedRealEdges} missingEdges=${src(m).missingRealEdges}`
    + (m.stitch ? ` stitches=${m.stitch.triangleBoundarySegments} ofWhichFake=${m.stitch.stitchesThatAreFake}`
      + ` accidentallyReal=${m.stitch.stitchesCoincidingWithARealEdge} fakeInsideTri=${m.stitch.fakeInsideATriangle}` : '')
    + (src(m).fakeExamples && src(m).fakeExamples.length ? ` e.g. ${src(m).fakeExamples.join(' ')}` : '');
  const controlsOk = m => ctl(m).triangleListEdgesRejected === 0 && ctl(m).quad0DiagonalsExclusive
    && ctl(m).rowWrapPairRejected && ctl(m).farLeapRejected && ctl(m).skipPairRejected
    && m && m.offLatticeTriangleEdges === 0 && m.uniqueRealEdges === m.analyticEdges;
  const cleanSrc = m => m && m.source && m.source.fakeSegments === 0 && m.source.duplicatedRealEdges === 0;
  const countOk = m => m && m.hasLineIdx && m.lineCount === m.analyticLineCount;
  const drawOk = m => m && m.wireDraw && m.wireDraw.mode === 'LINES'
    && m.wireDraw.src === 'buffers.lineIdx' && m.lineDrawsWithWireOff === 0 && m.trianglesWithWireOff > 0;
  const coverOk = m => m && m.source && m.source.missingRealEdges === 0
    && m.source.coveredRealEdges === m.analyticEdges;

  gate('W0 metric-discriminates', controlsOk(sq) && controlsOk(hx),
    `square: all ${sq && sq.triIndexCount} triangle-list edges accepted (rejected=${ctl(sq).triangleListEdgesRejected}), `
    + `quad(0,0) diagonals main=${ctl(sq).quad0MainDiagonalReal}/anti=${ctl(sq).quad0AntiDiagonalReal} `
    + `exclusive=${ctl(sq).quad0DiagonalsExclusive} (=> the wrong diagonal IS rejected), `
    + `rowWrapDelta1Rejected=${ctl(sq).rowWrapPairRejected}, recoveredEdges=${sq && sq.uniqueRealEdges} `
    + `vs analytic 3*(n-1)^2+2*(n-1)=${sq && sq.analyticEdges} | hex: rejected=${ctl(hx).triangleListEdgesRejected} `
    + `exclusive=${ctl(hx).quad0DiagonalsExclusive} rowWrapDelta1Rejected=${ctl(hx).rowWrapPairRejected} `
    + `recoveredEdges=${hx && hx.uniqueRealEdges} vs analytic ${hx && hx.analyticEdges} `
    + `-- this gate must PASS on the broken build too, or the counts below mean nothing`);

  gate('W1 no-fake-segments', cleanSrc(sq) && cleanSrc(hx),
    `THRESHOLD fakeSegments===0 && duplicatedRealEdges===0 (measured broken LINE_STRIP: 130,967 fake `
    + `/ 651,884 dup on square, 130,560 / 652,291 on hex; a real edge buffer measures exactly 0 -- `
    + `no continuum between, the gap IS the margin). SQUARE ${one(sq)} || HEX ${one(hx)}`);

  gate('W2 edge-count', countOk(sq) && countOk(hx),
    `buffers.lineIdx present square=${sq && sq.hasLineIdx} hex=${hx && hx.hasLineIdx}; `
    + `buffers.lineCount square=${sq && sq.lineCount} expected ${sq && sq.analyticLineCount} `
    + `(= 2*(3*(n-1)^2+2*(n-1)) at n=${sq && sq.n}); hex=${hx && hx.lineCount} expected ${hx && hx.analyticLineCount}`);

  gate('W3 both-lattices', cleanSrc(sq) && cleanSrc(hx) && countOk(sq) && countOk(hx)
    && drawOk(sq) && drawOk(hx),
    `square W1=${cleanSrc(sq)} W2=${countOk(sq)} wireDraw=${sq && sq.wireDraw ? sq.wireDraw.mode + ' from ' + sq.wireDraw.src : 'none'} `
    + `linesWhenWireOff=${sq && sq.lineDrawsWithWireOff} trianglesWhenWireOff=${sq && sq.trianglesWithWireOff} | `
    + `hex W1=${cleanSrc(hx)} W2=${countOk(hx)} wireDraw=${hx && hx.wireDraw ? hx.wireDraw.mode + ' from ' + hx.wireDraw.src : 'none'} `
    + `linesWhenWireOff=${hx && hx.lineDrawsWithWireOff} trianglesWhenWireOff=${hx && hx.trianglesWithWireOff}`);

  gate('W4 edge-coverage', coverOk(sq) && coverOk(hx),
    `square covered=${src(sq).coveredRealEdges}/${sq && sq.analyticEdges} missing=${src(sq).missingRealEdges} | `
    + `hex covered=${src(hx).coveredRealEdges}/${hx && hx.analyticEdges} missing=${src(hx).missingRealEdges} `
    + `-- a strip OMITS edges too: a triangle's third edge is drawn only if a stitch lands on it, and `
    + `nothing ever reaches the left-column verticals (broken build missed 511 on both lattices)`);

  gate('W5 no-stale-edges', st && st.diagonalsSpunByTheEdit > 0 && cleanSrc(st) && coverOk(st),
    `height edit spun ${st && st.diagonalsSpunByTheEdit} adaptive diagonals (must be >0 or this gate `
    + `would be vacuous); overlay afterwards: ${one(st)}`);

  console.log('== wireframe overlay draws real mesh edges ==');
  let fail = 0;
  for (const g of gates) { console.log(`${g.pass ? 'PASS' : 'FAIL'}  ${g.name}  ${g.detail}`); if (!g.pass) fail++; }
  console.log('REPORT square element draws, wireframe ON: ' + JSON.stringify(sq && sq.drawsWireOn));
  console.log('REPORT hex    element draws, wireframe ON: ' + JSON.stringify(hx && hx.drawsWireOn));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(fail || errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
