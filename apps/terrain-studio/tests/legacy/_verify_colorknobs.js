// Colour knobs on a MINIMAL graph, because the 18-node default is a bad instrument: if the colour
// arriving at Color Erosion is already near-uniform, every slider reads dead regardless of the code.
//
// Graph: perlin -> satmap(height-driven, high contrast) -> colorerosion -> weathering.
// A height-driven SatMap over real relief guarantees the input colour actually VARIES, so a
// transport effect has something to move and a dead slider means the slider is dead.
//
// Also reports the diagnostic that decides the mechanism:
//   baseSpread   - how much the INPUT colour varies (if this is ~0 the test is meaningless)
//   pigmentDelta - mean |deposited pigment - destination colour|, which is what the effect can
//                  possibly change. `hold` blends the pigment toward the SOURCE cell's own colour,
//                  so if source and destination look alike this is ~0 and the node is identity by
//                  construction, whatever the sliders say.
//   fmMean       - mean saturation factor 1-exp(-m*(4+flow*7)); the other half of the strength.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'file://' + path.resolve(__dirname, '../../index.html');

(async () => {
  const b = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 1100, height: 800 } });
  const errors = []; p.on('pageerror', e => errors.push(String(e.message).slice(0, 160)));
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(2500);

  const r = await p.evaluate(lat => {
    SCALE_RES = true; XF = null; USE_GPU = false; BUILD_QUALITY = 'interactive';
    RES = 160; TARGET_RES = 160; terrainDef.lattice = lat; buildIndex();

    // Minimal graph: relief -> height SatMap -> colour erosion -> weathering.
    const src = nodes.find(n => n.type === 'perlin') || nodes[0];
    const out = nodes.find(n => n.type === 'output');
    const sat = makeNode('satmap', 430, 520);
    sat.params.gradient = 'Terracotta'; sat.params.source = 'height'; sat.params.rough = 'med';
    const ce = makeNode('colorerosion', 670, 520);
    const we = makeNode('weathering', 900, 520);
    edges = edges.filter(e => e.to === src.id);
    edges.push({ from: src.id, to: sat.id, slot: 0 }, { from: sat.id, to: ce.id, slot: 0 },
      { from: ce.id, to: we.id, slot: 0 }, { from: we.id, to: out.id, slot: 0 });
    nodes.forEach(nd => { nd._dirty = true; }); evalGraph();

    const n = fieldW(), nh = fieldH(), N = n * nh;
    const baseCol = resolveColor(sat.id, RES);
    const res = { lattice: lat, n, nh, nodes: [] };

    // Does the INPUT colour actually vary? If not, nothing downstream can be judged.
    let mn = [1,1,1], mx = [0,0,0], sd = 0;
    for (let i = 0; i < N; i++) for (let c = 0; c < 3; c++) {
      const v = baseCol[i*3+c]; if (v < mn[c]) mn[c] = v; if (v > mx[c]) mx[c] = v;
    }
    for (let i = 1; i < N; i++) sd += Math.abs(baseCol[i*3] - baseCol[(i-1)*3]);
    res.baseSpread = { rangeR: +(255*(mx[0]-mn[0])).toFixed(1), rangeG: +(255*(mx[1]-mn[1])).toFixed(1),
      rangeB: +(255*(mx[2]-mn[2])).toFixed(1), neighbourVar: +(255*sd/N).toFixed(3) };

    // Color Erosion deposits along FLOW PATHS, so its change is concentrated in channels - a
    // whole-image mean divides a real localised change by ~100x the area it acts on and reports
    // 'dead' for an effect that is working. Report the distribution instead.
    const stat = (a, b2) => { const d = [];
      for (let i = 0; i < a.length; i += 3) {
        d.push(255 * (Math.abs(a[i]-b2[i]) + Math.abs(a[i+1]-b2[i+1]) + Math.abs(a[i+2]-b2[i+2])) / 3);
      }
      d.sort((x, y) => x - y);
      const q = f => d[Math.min(d.length - 1, Math.floor(f * d.length))];
      const hit = d.filter(v => v > 2).length / d.length;
      return { mean: +(d.reduce((x,y)=>x+y,0)/d.length).toFixed(3), p99: +q(0.99).toFixed(2),
               max: +d[d.length-1].toFixed(2), pctMoved: +(100*hit).toFixed(2) };
    };

    for (const nd of [ce, we]) {
      const def = TYPES[nd.type];
      const rec = { type: nd.type, params: [] };
      const base = Float32Array.from(resolveColor(nd.id, RES));
      for (const spec of def.params) {
        const k = spec.k || spec.key || spec.name;
        if (!k || !(k in nd.params)) continue;
        if (typeof spec.min !== 'number' || typeof spec.max !== 'number') continue;
        const held = nd.params[k];
        const d = [0, .25, .5, .75, 1].map(t => {
          nd.params[k] = spec.min + t * (spec.max - spec.min);
          return stat(base, resolveColor(nd.id, RES));
        });
        nd.params[k] = held;
        const span = Math.max(...d.map(x=>x.p99)) - Math.min(...d.map(x=>x.p99));
        rec.params.push({ key: k, spanP99: +span.toFixed(2),
          endMean: d[4].mean, endP99: d[4].p99, endMax: d[4].max, endPct: d[4].pctMoved,
          curveP99: d.map(x => x.p99) });
      }
      res.nodes.push(rec);
    }
    return res;
  }, process.argv[2] || 'square');

  console.log('== MINIMAL GRAPH: perlin -> satmap(height) -> colorerosion -> weathering ==');
  console.log('lattice=' + r.lattice + '  field=' + r.n + 'x' + r.nh);
  console.log('input colour spread (0-255): ' + JSON.stringify(r.baseSpread));
  if (r.baseSpread.neighbourVar < 0.05) console.log('  !! input colour is nearly flat - knob results below are meaningless');
  for (const nd of r.nodes) {
    console.log('\n--- ' + nd.type + ' ---');
    for (const q of nd.params) {
      const flag = q.spanP99 < 1 ? '   <<< DEAD' : q.spanP99 < 4 ? '   <- weak' : '';
      console.log('  ' + q.key.padEnd(12) + 'p99span=' + String(q.spanP99).padStart(8)
        + ' | at max: mean=' + String(q.endMean).padStart(7) + ' p99=' + String(q.endP99).padStart(7)
        + ' max=' + String(q.endMax).padStart(7) + ' cellsMoved=' + String(q.endPct).padStart(6) + '%'
        + '  ' + JSON.stringify(q.curveP99) + flag);
    }
  }
  console.log('\nerrors', errors.length ? JSON.stringify(errors) : 'none');
  await b.close();
})().catch(e => { console.error('FATAL ' + String(e).slice(0, 300)); process.exit(2); });
