// Wireframe overlay: does it draw REAL MESH EDGES, or a triangle LIST reinterpreted as a strip?
//
// THE DEFECT. drawTerrain() drew the overlay with
//     gl.drawElements(wire?gl.LINE_STRIP:gl.TRIANGLES, buffers.count, ...)
// buffers.idx is a triangle LIST (3 consecutive indices = 1 triangle). A LINE_STRIP joins EVERY
// consecutive pair in buffer order, so at each triangle boundary (k%3===2) it draws a segment from
// one triangle's last vertex to the next triangle's first vertex. Those "stitches" are not edges of
// the mesh. Some of them coincide with a real edge by accident (the two triangles of one quad share
// their diagonal, so the intra-quad stitch lands on it); the rest are pure fiction, including one
// full-width jump per row wrap. The overlay therefore showed a lattice that does not exist - which
// is why hex mode looked unreadable on screen.
//
// MEASURED, LIVE, ON THE BROKEN BUILD (git HEAD 214ccc3 index.html, RES=512, 1,566,726 indices):
//                            square (adaptive fit)      hex (static equilateral)
//   drawn segments                    1,566,725                    1,566,725
//   FAKE segments                       131,053  ( 8.37%)            131,073  ( 8.37%)
//   duplicated real edges               522,241                      522,241
//   real edges never drawn                  511                          511
//   unique real mesh edges              784,385                      784,385   (analytic, matches)
// EXPECTED ON THE FIXED BUILD (dedicated deduplicated edge buffer, gl.LINES over buffers.lineIdx):
//   fake 0, duplicates 0, missing 0, lineCount 1,568,770 == 2*(3*(n-1)^2+2*(n-1)).
//
// THRESHOLDS ARE ARMED AT EXACT ZERO / EXACT EQUALITY, and that is the honest arming for a
// combinatorial invariant: the metric is a count of segments that are not edges of the uploaded
// triangulation, so the broken build sits at 131,053 and the fixed build sits at 0 with no
// continuum in between - every unit of margin the gate could give away would be a licence to draw
// a line that is not there. The 131,053-to-0 gap IS the margin. The gates that could drift with
// content (fitted diagonals move as the height changes) are not thresholded at all: the ground
// truth is rebuilt from the index buffer that was actually uploaded on this run.
//
// GATES
//   W0 metric-discriminates  identity/negative control. The classifier must accept all 1,566,726
//                            triangle-list edges, must reject the OTHER diagonal of quad (0,0)
//                            (exactly one of the two is in the mesh - the single discrimination a
//                            wireframe exists to make), and must reject a row-wrapping "delta 1"
//                            pair that looks horizontal but is not an edge. Passes on BOTH builds:
//                            it proves the numbers below mean what they say.
//   W1 no-fake-segments      every segment the wireframe draw ACTUALLY issues (observed by hooking
//                            gl.drawElements and reading back the buffer it bound) is an edge of
//                            the uploaded triangulation, and no edge is drawn twice.
//   W2 edge-count            buffers.lineCount === 2*(3*(n-1)^2+2*(n-1)).
//   W3 both-lattices         W1+W2 hold for square AND hex, the wire draw is gl.LINES from
//                            buffers.lineIdx, and with the wireframe OFF nothing draws lines at all
//                            (the negative control on the observation itself).
//   W4 edge-coverage         the overlay covers every unique mesh edge exactly once - a strip also
//                            MISSES edges (each triangle's 3rd edge is only drawn if a stitch
//                            happens to land on it; the left-column verticals never are).
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
    const out = { lattices: {} };
    const MODE = { 0:'POINTS', 1:'LINES', 2:'LINE_LOOP', 3:'LINE_STRIP',
      4:'TRIANGLES', 5:'TRIANGLE_STRIP', 6:'TRIANGLE_FAN' };
    const isLine = m => m === gl.LINES || m === gl.LINE_STRIP || m === gl.LINE_LOOP;

    // Observe the REAL draw calls rather than trusting a helper: the question "what does the
    // wireframe draw" is answered by the primitive mode and the element buffer that was bound at
    // draw time, whatever function produced them.
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

    const measure = lattice => {
      const M = { lattice };
      terrainDef.lattice = lattice;
      updateViewport(curField || newField(), activePreviewNode(), { color: false });
      const n = RES;
      M.n = n; M.pattern = buffers.indexPattern; M.triIndexCount = buffers.count;
      // Unique edges of an n x n vertex grid cut into (n-1)^2 quads, one diagonal each:
      //   horizontals n(n-1) + verticals n(n-1) + diagonals (n-1)^2 = 3(n-1)^2 + 2(n-1).
      M.analyticEdges = 3 * (n - 1) * (n - 1) + 2 * (n - 1);
      M.analyticLineCount = 2 * M.analyticEdges;

      // ---- ground truth: the edge set of the triangulation that is ACTUALLY on the GPU ----
      // Every edge of this lattice joins two indices differing by 1 (horizontal), n (vertical),
      // n+1 (main diagonal) or n-1 (anti diagonal), so one nibble per vertex stores the whole set
      // exactly - no hashing, no collisions, no per-quad case analysis. A pair whose delta is
      // outside that family, or whose bit was never set (the quad's OTHER diagonal, a row-wrapping
      // "delta 1" jump, a leap across the mesh) is not an edge. Built from the uploaded buffer, so
      // adaptive diagonal spinning cannot make the truth stale.
      const tri = readIdx(buffers.idx, buffers.count);
      const slot = d => d === 1 ? 1 : d === n - 1 ? 2 : d === n ? 4 : d === n + 1 ? 8 : 0;
      const mask = new Uint8Array(n * n);
      let offLattice = 0;
      for (let t = 0; t + 2 < tri.length; t += 3) for (let e = 0; e < 3; e++) {
        const u = tri[t + e], v = tri[t + (e + 1) % 3];
        const a = u < v ? u : v, s = slot(u < v ? v - u : u - v);
        if (!s) { offLattice++; continue; }
        mask[a] |= s;
      }
      M.offLatticeTriangleEdges = offLattice;
      M.uniqueRealEdges = popcount(mask);
      const isReal = (u, v) => { if (u === v) return false;
        const a = u < v ? u : v, s = slot(u < v ? v - u : u - v);
        return !!s && !!(mask[a] & s); };

      // ---- W0 controls: prove the metric can tell a real edge from a plausible fake ----
      let triEdgeFake = 0;
      for (let t = 0; t + 2 < tri.length; t += 3) for (let e = 0; e < 3; e++)
        if (!isReal(tri[t + e], tri[t + (e + 1) % 3])) triEdgeFake++;
      const mainD = isReal(0, n + 1), antiD = isReal(1, n);
      M.control = {
        triangleListEdgesRejected: triEdgeFake,                       // must be 0
        quad0MainDiagonalReal: mainD, quad0AntiDiagonalReal: antiD,
        quad0DiagonalsExclusive: mainD !== antiD,                     // exactly one exists
        wrongDiagonalRejected: mainD !== antiD,                       // => the other is rejected
        rowWrapPairRejected: !isReal(n - 1, n),                       // delta 1, but wraps a row
        farLeapRejected: !isReal(0, n * n - 1),
        skipPairRejected: !isReal(0, 2)
      };

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
          coveredRealEdges: covered, missingRealEdges: M.uniqueRealEdges - covered,
          fakeExamples: ex };
      };

      // ---- what the wireframe actually draws ----
      wire = false; log = []; renderGL(); const off = log;
      wire = true;  log = []; renderGL(); const on = log; log = null; wire = false;
      const name = d => ({ mode: MODE[d.mode] || d.mode, count: d.count,
        src: d.ebo === buffers.idx ? 'buffers.idx'
          : (buffers.lineIdx && d.ebo === buffers.lineIdx) ? 'buffers.lineIdx' : 'other' });
      M.lineDrawsWithWireOff = off.filter(d => isLine(d.mode)).length;   // negative control: 0
      M.trianglesWithWireOff = off.filter(d => d.mode === gl.TRIANGLES && d.ebo === buffers.idx).length;
      M.drawsWireOn = on.map(name);
      M.hasLineIdx = !!buffers.lineIdx;
      M.lineCount = buffers.lineCount === undefined ? null : buffers.lineCount;

      const wd = on.find(d => isLine(d.mode));
      if (!wd) { M.wireDraw = null; M.source = null; return M; }
      M.wireDraw = name(wd);
      const arr = readIdx(wd.ebo, wd.count);
      if (wd.mode === gl.LINES) {
        M.source = classify({ length: arr.length >> 1, u: k => arr[2 * k], v: k => arr[2 * k + 1] });
        M.source.kind = 'LINES';
      } else {
        // LINE_STRIP: segment k joins arr[k] and arr[k+1] for every k.
        M.source = classify({ length: Math.max(0, arr.length - 1), u: k => arr[k], v: k => arr[k + 1] });
        M.source.kind = MODE[wd.mode];
        // Anatomy of the failure: k%3===2 spans a triangle boundary (a stitch), k%3 in {0,1} lies
        // inside one triangle and is therefore always a genuine edge of it. Some stitches land on
        // a real edge by accident - the two triangles of a quad share their diagonal - so only the
        // rest are counted as fake, which is the conservative reading of the defect.
        let stitches = 0, stitchFake = 0, insideFake = 0;
        for (let k = 0; k + 1 < arr.length; k++) {
          const ok = isReal(arr[k], arr[k + 1]);
          if (k % 3 === 2) { stitches++; if (!ok) stitchFake++; } else if (!ok) insideFake++;
        }
        M.stitch = { triangleBoundarySegments: stitches, stitchesThatAreFake: stitchFake,
          stitchesCoincidingWithARealEdge: stitches - stitchFake, fakeInsideATriangle: insideFake };
      }
      return M;
    };

    out.lattices.square = measure('square');
    out.lattices.hex = measure('hex');
    terrainDef.lattice = 'square';
    updateViewport(curField || newField(), activePreviewNode(), { color: false });
    gl.drawElements = origDrawElements; try { delete gl.drawElements; } catch (_) {}
    return out;
  });

  const gates = [];
  const gate = (name, pass, detail) => gates.push({ name, pass: !!pass, detail });
  const sq = r.lattices.square, hx = r.lattices.hex;
  const src = m => (m && m.source) || {};
  const ctl = m => (m && m.control) || {};
  const one = m => !m ? 'missing' : `n=${m.n} pattern=${m.pattern} kind=${src(m).kind || 'NO-LINE-DRAW'} `
    + `drawnFrom=${m.wireDraw ? m.wireDraw.src + '/' + m.wireDraw.mode : 'none'} `
    + `segments=${src(m).segments} fake=${src(m).fakeSegments} (${(src(m).fakeFraction * 100).toFixed(2)}%) `
    + `dupEdges=${src(m).duplicatedRealEdges} missingEdges=${src(m).missingRealEdges}`
    + (m.stitch ? ` stitches=${m.stitch.triangleBoundarySegments} ofWhichFake=${m.stitch.stitchesThatAreFake}`
      + ` accidentallyReal=${m.stitch.stitchesCoincidingWithARealEdge} fakeInsideTri=${m.stitch.fakeInsideATriangle}` : '')
    + (src(m).fakeExamples && src(m).fakeExamples.length ? ` e.g. ${src(m).fakeExamples.join(' ')}` : '');
  const controlsOk = m => ctl(m).triangleListEdgesRejected === 0 && ctl(m).quad0DiagonalsExclusive
    && ctl(m).wrongDiagonalRejected && ctl(m).rowWrapPairRejected && ctl(m).farLeapRejected
    && ctl(m).skipPairRejected;
  const cleanSrc = m => m && m.source && m.source.fakeSegments === 0 && m.source.duplicatedRealEdges === 0;
  const countOk = m => m && m.hasLineIdx && m.lineCount === m.analyticLineCount;
  const drawOk = m => m && m.wireDraw && m.wireDraw.mode === 'LINES'
    && m.wireDraw.src === 'buffers.lineIdx' && m.lineDrawsWithWireOff === 0 && m.trianglesWithWireOff > 0;
  const coverOk = m => m && m.source && m.source.missingRealEdges === 0
    && m.source.coveredRealEdges === m.analyticEdges;

  gate('W0 metric-discriminates', controlsOk(sq) && controlsOk(hx)
    && sq && hx && sq.uniqueRealEdges === sq.analyticEdges && hx.uniqueRealEdges === hx.analyticEdges,
    `square: acceptsAll ${sq && sq.triIndexCount} triangle-list edges (rejected=${ctl(sq).triangleListEdgesRejected}), `
    + `quad0 diagonals main=${ctl(sq).quad0MainDiagonalReal}/anti=${ctl(sq).quad0AntiDiagonalReal} exclusive=${ctl(sq).quad0DiagonalsExclusive}, `
    + `rowWrapRejected=${ctl(sq).rowWrapPairRejected}, uniqueRealEdges=${sq && sq.uniqueRealEdges} vs analytic ${sq && sq.analyticEdges} | `
    + `hex: rejected=${ctl(hx).triangleListEdgesRejected} exclusive=${ctl(hx).quad0DiagonalsExclusive} `
    + `rowWrapRejected=${ctl(hx).rowWrapPairRejected} uniqueRealEdges=${hx && hx.uniqueRealEdges} vs analytic ${hx && hx.analyticEdges} `
    + `-- must PASS on the broken build too, or the counts below mean nothing`);

  gate('W1 no-fake-segments', cleanSrc(sq) && cleanSrc(hx),
    `THRESHOLD fakeSegments===0 and duplicatedRealEdges===0 (broken LINE_STRIP measures ~131k fakes `
    + `and 522k duplicates per lattice; a correct edge buffer measures exactly 0 - no continuum between). `
    + `SQUARE ${one(sq)} || HEX ${one(hx)}`);

  gate('W2 edge-count', countOk(sq) && countOk(hx),
    `buffers.lineIdx present square=${sq && sq.hasLineIdx} hex=${hx && hx.hasLineIdx}; `
    + `lineCount square=${sq && sq.lineCount} expected ${sq && sq.analyticLineCount} `
    + `(= 2*(3*(n-1)^2+2*(n-1)), n=${sq && sq.n}); `
    + `lineCount hex=${hx && hx.lineCount} expected ${hx && hx.analyticLineCount}`);

  gate('W3 both-lattices', cleanSrc(sq) && cleanSrc(hx) && countOk(sq) && countOk(hx)
    && drawOk(sq) && drawOk(hx),
    `square W1=${cleanSrc(sq)} W2=${countOk(sq)} wireDraw=${sq && sq.wireDraw ? sq.wireDraw.mode + ' from ' + sq.wireDraw.src : 'none'} `
    + `linesWhenWireOff=${sq && sq.lineDrawsWithWireOff} trianglesWhenWireOff=${sq && sq.trianglesWithWireOff} | `
    + `hex W1=${cleanSrc(hx)} W2=${countOk(hx)} wireDraw=${hx && hx.wireDraw ? hx.wireDraw.mode + ' from ' + hx.wireDraw.src : 'none'} `
    + `linesWhenWireOff=${hx && hx.lineDrawsWithWireOff} trianglesWhenWireOff=${hx && hx.trianglesWithWireOff}`);

  gate('W4 edge-coverage', coverOk(sq) && coverOk(hx),
    `square covered=${src(sq).coveredRealEdges}/${sq && sq.analyticEdges} missing=${src(sq).missingRealEdges} | `
    + `hex covered=${src(hx).coveredRealEdges}/${hx && hx.analyticEdges} missing=${src(hx).missingRealEdges} `
    + `-- a strip also OMITS edges: each triangle's third edge is drawn only when a stitch lands on it`);

  console.log('== wireframe overlay draws real mesh edges ==');
  let fail = 0;
  for (const g of gates) { console.log(`${g.pass ? 'PASS' : 'FAIL'}  ${g.name}  ${g.detail}`); if (!g.pass) fail++; }
  console.log('REPORT square draws with wireframe ON: ' + JSON.stringify(sq && sq.drawsWireOn));
  console.log('REPORT hex    draws with wireframe ON: ' + JSON.stringify(hx && hx.drawsWireOn));
  console.log('errors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
  process.exit(fail || errors.length ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
