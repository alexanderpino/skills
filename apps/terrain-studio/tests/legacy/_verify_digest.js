// =====================================================================
// BEHAVIOUR-PRESERVATION ORACLE  (Phase 0 of the index.html -> ESM/Vite/TS migration)
// =====================================================================
// index.html is about to be split into ES modules, bundled, and typed, over many commits.
// After every such commit the computed terrain must be provably bit-identical to today's.
// This script is the proof. It builds a minimal valid graph for EVERY node type in TYPES,
// evaluates it on the CPU path at a fixed resolution, and folds the resulting Float32Array
// into an order-sensitive integer digest. Bit-exact: no tolerance, no epsilon.
//
//   node _verify_digest.js --write            record the baseline from index.html
//   node _verify_digest.js                    GATE: compare index.html against the baseline
//   node _verify_digest.js dist/index.html    GATE: compare a Vite-built artifact instead
//   node _verify_digest.js --res=512 --write   re-baseline at another resolution
//   node _verify_digest.js --repeat=2 --write  run the sweep twice (fresh page load each
//                                              time) and fail if any type is non-deterministic
//   node _verify_digest.js --verbose          per-node timing / range / non-finite diagnostics
//
// stdout is ALWAYS the JSON document and nothing else, so CI can pipe it.
// Verdicts, drift lists and diagnostics go to stderr.
//
// WHAT IS DIGESTED
//   The field the node's own `eval` RETURNS (its output field), plus every auxiliary field the
//   node computes and hangs off the node object, because for several types that is where the
//   real work lands:
//     d_sunshadow   -> _solarExposure
//     d_temperature -> _temperatureC, _solarShadow, _solarExposure
//     d_heat        -> _temperatureC
//     snow          -> _snowLayer            (the metres-of-snow simulation)
//     satmap        -> _driver               (the enhanced colour driver)
//   and for the five colour nodes the resolved per-vertex RGB field from resolveColor(), which
//   is where SatMap gradients, colour erosion transport, weathering and colour blending actually
//   execute. Without that, `passthrough:true` nodes would digest nothing but their own input.
//   A composite digest is rendered as "<primary>|<aux>=<digest>|..." — still one opaque string.
//
// DIGEST
//   Identical fold to _verify_canyon_identity.js: quantise to 1e-7 and carry two 32-bit
//   accumulators, one summing, one xor-folding position in. Order-sensitive; a single changed
//   sample moves it. The only addition is that non-finite samples fold a distinct sentinel
//   instead of collapsing to 0, so a field that degrades to NaN cannot masquerade as unchanged.
//   For any all-finite field the value is byte-identical to _verify_canyon_identity's digest.
//
// DETERMINISM CONTRACT (requirement: two runs on one build must match)
//   USE_GPU=false so nothing depends on the GPU/SwiftShader path; RES/TARGET_RES/SCALE_RES/
//   BUILD_QUALITY/XF pinned; terrainDef reset to the shipped defaults (nodes read scale, height,
//   latitude, north, solarElevation); CANYON_EVOLUTION_CACHE cleared between node types; the
//   graph is torn down and rebuilt per node type; and node params come from the TYPE DEFAULTS
//   rather than makeNode(), which deliberately re-rolls every `seed` at creation time.
//   Any type discovered to be non-deterministic goes in NONDETERMINISTIC below WITH A REASON and
//   is excluded from the gate, so the gate is never merely flaky.
//
// CONSTRUCTED, NOT DEFAULT, INPUTS — the three documented deviations from "default parameters":
//   drawmask  default params.strokes is [] and rasterises to an all-zero field, so a fixed
//             three-point stroke is injected; otherwise the stroke rasteriser is untested.
//   import    has no DEM without a file, so a deterministic synthetic DEM is installed on the
//             node; otherwise only the radialField() fallback would be covered.
//   sources   every declared input slot is wired to a DISTINCT deterministic perlin seed (or the
//             right typed source: a real Temperature chain for Temperature ports, a real SatMap
//             branch for colour ports), so slot-swap bugs are visible in the digest.
//
// MIGRATION PREREQUISITE — read this before the first ESM commit.
//   This oracle drives the app through the globals the inline classic <script> currently creates:
//     TYPES  nodes  edges  uid  selected  selectedEdge  buildRun  evalFrame  RES  TARGET_RES
//     USE_GPU  SCALE_RES  BUILD_QUALITY  XF  H_SCALE  terrainDef  CANYON_EVOLUTION_CACHE
//     cloneParams  nodeById  inputEdge  nodeInputs  propagateFieldMetadata  resolveColor
//     priorityFloodFill  d8Accumulation
//   ES modules do not create globals. The moment index.html becomes a module bundle, every one of
//   these disappears from the page scope and this script stops working — not because behaviour
//   changed, but because the oracle went blind, which is the worst possible failure mode for the
//   thing that is supposed to be measuring the migration. The bundle MUST therefore keep an
//   explicit test surface (e.g. `globalThis.__terrain = { TYPES, nodes, edges, ... }`), and the
//   one commit that introduces it is the one commit where this file's page-side accessors change.
// =====================================================================
const nodeRequire = typeof require === 'function'
  ? require
  : process.getBuiltinModule('node:module').createRequire(process.argv[1]);
const { chromium } = nodeRequire('playwright-core');
const path = nodeRequire('node:path');
const fs = nodeRequire('node:fs');
const scriptDir = path.dirname(path.resolve(process.argv[1]));

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');

const argv = process.argv.slice(2);
const flag = name => argv.some(a => a === '--' + name || a.startsWith('--' + name + '='));
const flagVal = (name, dflt) => {
  const hit = argv.find(a => a.startsWith('--' + name + '='));
  return hit ? hit.slice(name.length + 3) : dflt;
};
const PAGE = argv.find(a => !a.startsWith('--')) || 'index.html';
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(scriptDir, '../../', PAGE));
const WRITE = flag('write');
const VERBOSE = flag('verbose');
const RES = parseInt(flagVal('res', '256'), 10);
const REPEAT = flag('repeat') ? Math.max(1, parseInt(flagVal('repeat', '2'), 10)) : 1;
const BASELINE = path.resolve(scriptDir, '_digest_baseline.json');
const REQUIRED_NODE_COUNT = 92;   // 89 + S3.4's three explicit cover-state selectors

// Node types proven non-deterministic and therefore EXCLUDED FROM THE GATE.
// Populate ONLY from evidence (a --repeat run that disagreed), always with the reason.
// Empty means: every node type in this app digests identically on repeat runs.
const NONDETERMINISTIC = {
  // "<nodeType>": "reason it cannot be gated",
};

/* ------------------------------------------------------------------ page */
// Everything below runs INSIDE the page. It must only use globals index.html already defines.
function installHarness(cfg) {
  // Stop the app fighting us: kill any queued/in-flight progressive build before repinning RES.
  try { buildRun++; } catch (_) {}
  try { if (evalFrame) { cancelAnimationFrame(evalFrame); evalFrame = 0; } } catch (_) {}

  RES = cfg.res; TARGET_RES = cfg.res;
  USE_GPU = false;            // never take the GPU path: the digest must not depend on the driver
  SCALE_RES = true;           // shipped default (resScale() = RES/REF_RES)
  BUILD_QUALITY = 'interactive';
  XF = null;                  // no ambient transform leaking into generators
  Object.assign(terrainDef, { scale: 5000, height: 2600, baseElevation: 0, latitude: 46,
    north: 0, seaTemp: 6, lapseRate: 6.5, solarElevation: 45 });
  H_SCALE = terrainDef.height / terrainDef.scale;

  const digest = f => {
    // Never digest something that is not a numeric field: an all-zero fold ("0:0") would look like
    // a perfectly stable digest while actually meaning "I read nothing".
    if (!f || !ArrayBuffer.isView(f) || typeof f.length !== 'number' || !f.length) return null;
    let a = 0, b = 0;
    for (let i = 0; i < f.length; i++) {
      const v = f[i];
      // Finite -> the reference quantisation. Non-finite -> a distinct sentinel, so a field that
      // rots to NaN cannot fold to the same accumulator as a field of zeros.
      const q = Number.isFinite(v) ? Math.round(v * 1e7)
        : (Number.isNaN(v) ? 0x7fc00000 : (v > 0 ? 0x7f800000 : 0xff800000));
      a = (a + q) >>> 0;
      b = (b ^ (a + i)) >>> 0;
    }
    return a.toString(16) + ':' + b.toString(16);
  };
  const stats = f => {
    if (!f || !ArrayBuffer.isView(f) || !f.length) return null;
    let mn = Infinity, mx = -Infinity, bad = 0, first = f[0], flat = true;
    for (let i = 0; i < f.length; i++) {
      const v = f[i];
      if (!Number.isFinite(v)) { bad++; continue; }
      if (v < mn) mn = v; if (v > mx) mx = v;
      if (v !== first) flat = false;
    }
    return { len: f.length, min: mn, max: mx, nonFinite: bad, constant: flat };
  };

  /* -------- graph construction (mirrors makeNode, minus the random seed re-roll) -------- */
  function reset() {
    nodes.length = 0; edges.length = 0; uid = 1; selected = null; selectedEdge = null;
    CANYON_EVOLUTION_CACHE.clear();     // canyon caches its landscape-evolution solve by key
    XF = null;
  }
  function mk(type, over) {
    const def = TYPES[type], p = {};
    def.params.forEach(pr => { p[pr.key] = cloneParams(pr.def); });
    const nd = { id: uid++, type, x: 0, y: 0, w: type === 'colormixer' ? 190 : 150, params: p,
      _field: null, _thumb: null, _dirty: true, _dem: null,
      _snowLayer: null, _temperatureC: null, _solarShadow: null, _solarExposure: null, _wind: null };
    if (type === 'colormixer') {
      nd._inputs = ['Layer 1', 'Layer 2', 'Layer 3'];
      nd.params.layers = [{ opacity: 1, blend: 'normal', edgeBlend: 0 },
        { opacity: 1, blend: 'normal', edgeBlend: 0 },
        { opacity: 1, blend: 'normal', edgeBlend: 0 }];
    }
    if (type === 'drawmask') nd.params.strokes = [];
    if (over) Object.assign(nd.params, over);
    nodes.push(nd);
    return nd;
  }
  const wire = (from, to, slot) => { edges.push({ from: from.id, to: to.id, slot }); };

  // Byte-for-byte the evaluator from evalGraph()'s inner ev(), except errors propagate instead of
  // being swallowed into newField() — a node that throws must be reported, never silently digested
  // as a field of zeros.
  function ev(id, guard) {
    if (!id) return null;
    if (guard.has(id)) return null;
    guard.add(id);
    const nd = nodeById(id);
    if (!nd) { guard.delete(id); return null; }
    if (!nd._dirty && nd._field) { guard.delete(id); return nd._field; }
    const def = TYPES[nd.type];
    const refs = def.referenceOnly || [];
    const ins = nodeInputs(nd).map((_, s) => {
      const e = inputEdge(id, s);
      const v = e ? ev(e.from, guard) : null;
      if (refs.includes(s)) nd._reference = v;
      return v;
    });
    // S2.1/S2.6: a typed evaluator returns { values: Map<portId, value> }. The primary scalar
    // raster is what this digest folds as "the field"; every OTHER declared output is folded too,
    // under its port id, so a multi-output node cannot half-exist in the gate — a vector output
    // that silently stopped being produced would otherwise leave the primary bit-identical and the
    // digest green. Legacy evaluators return a bare Float32Array and are untouched.
    let raw = def.eval(nd.params, ins, nd);
    let f = raw, extraPorts = null;
    if (raw && raw.values instanceof Map) {
      const outs = def.outputs || [];
      const primaryPort = (outs.find(p => p.primary) || outs[0] || {}).id;
      f = raw.values.get(primaryPort);
      extraPorts = [];
      for (const port of outs) {
        if (!port || port.id === primaryPort) continue;
        extraPorts.push([port.id, raw.values.get(port.id)]);
      }
    }
    f = propagateFieldMetadata(f, ins, def);
    nd._field = f; nd._dirty = false;
    if (extraPorts) nd._digestPorts = extraPorts;
    guard.delete(id);
    return f;
  }

  /* -------- deterministic sources, one per semantic port kind -------- */
  // Distinct seeds per slot so a refactor that swaps two input slots changes the digest.
  const SEEDS = { A: 101, B: 202, C: 303, M: 404, D: 505 };
  function makeSources() {
    const memo = {};
    const perlin = key => mk('perlin', { seed: SEEDS[key] });   // all other perlin params default
    const get = key => {
      if (key in memo) return memo[key];
      let nd = null;
      if (key === 'A' || key === 'B' || key === 'C' || key === 'M' || key === 'D') nd = perlin(key);
      else if (key === 'H') { nd = mk('d_height'); wire(get('A'), nd, 0); }
      else if (key === 'S') { nd = mk('d_sunshadow'); wire(get('A'), nd, 0); }
      else if (key === 'T') {                       // a REAL physical Temperature field
        nd = mk('d_temperature'); wire(get('H'), nd, 0); wire(get('S'), nd, 1);
      } else if (key === 'W') {                     // a REAL physical Wind vector field
        nd = mk('d_wind'); wire(get('A'), nd, 0);
      } else if (key === 'SAT' || key === 'SAT2' || key === 'SAT3') {
        // a real colour branch, so resolveColor() has something authored to work on
        const h = { SAT: 'A', SAT2: 'B', SAT3: 'C' }[key];
        const drv = { SAT: 'D', SAT2: 'C', SAT3: 'M' }[key];
        nd = mk('satmap'); wire(get(h), nd, 0); wire(get(drv), nd, 1);
      }
      memo[key] = nd;
      return nd;
    };
    return get;
  }

  // Slot -> source recipe for every key in TYPES. Order matches each type's `ins:[...]`.
  const WIRING = {
    // --- generators: no inputs ---
    perlin: [], simplex: [], ridged: [], worley: [], gradient: [], shape: [],
    mountain: [], canyon: [], tectonic: [], crater: [], craterfield: [], island: [], volcano: [],
    mountainside: [], rugged: [], constant: [], import: [],
    drawmask: ['A'],                       // Reference (referenceOnly slot 0)
    layout: ['A', 'M'],                    // Base, Mask
    // --- combine ---
    blend: ['A', 'B', 'M'], add: ['A', 'B'], maxmin: ['A', 'B'],
    stampn: ['A', 'B', 'M'], smax: ['A', 'B'], smin: ['A', 'B'],
    // --- filters ---
    warp: ['A', 'M'], terrace: ['A', 'M'], normalizen: ['A', 'M'], levels: ['A'], curve: ['A'], histeq: ['A'],
    blur: ['A', 'M'], sculpt: ['A', 'M'], clampn: ['A'], transform: ['A', 'M'], invert: ['A'],
    sharpen: ['A', 'M'], threshold: ['A'], dilate: ['A', 'M'], deflate: ['A', 'M'],
    match: ['A', 'B'], softclip: ['A', 'M'], flip: ['A', 'M'], transpose: ['A', 'M'],
    fold: ['A', 'M'], directionalwarp: ['A', 'D', 'M'],
    // --- erosion ---
    thermal: ['A', 'M'], fracture: ['A', 'M'], streampower: ['A', 'B', 'M'],
    hydraulic: ['A', 'M'],
    erosion2: ['A', 'M'], hydrofix: ['A', 'M'],
    surface: ['A', 'M'],
    // --- surface / geology ---
    // Regolith takes carried soil depth (metres) and an optional dimensionless climate multiplier.
    // A perlin in each slot is a fixture, not a legal graph edge — the Soil port is strictly typed
    // `soilDepth`/m and canConnect would refuse this pairing in the UI. The digest wires by slot and
    // never consults canConnect, and what it needs from a source is determinism, which perlin has.
    regolith: ['A', 'M'],
    // S3.4's explicit cover-state selectors. Each returns its connected port's exact bytes, so the
    // digest of a wired selector IS the digest of its source — it appears in the LOW-SENSITIVITY
    // report below and belongs there, because identity is the whole of what these nodes promise.
    // The claims that carry real weight (a typed missing-input refusal on a disconnected port, a
    // WIRED zero field evaluating clean, a rewire moving the result) are not digest-shaped and are
    // gated by _verify_cover_reader.js. What this recipe pins is that all three still evaluate, at
    // the declared arity, returning a full-length field.
    s_soilDepth: ['A'], s_sedimentDepth: ['A'], s_sandDepth: ['A'],
    // --- masks ---
    slopemask: ['A'], heightmask: ['A'], tempmask: ['T'],
    // --- data maps ---
    d_slope: ['A'], d_height: ['A'], d_sunshadow: ['A'],
    normals: ['A'],
    route: ['A'], chokepoint: ['A'], edge: ['M'],
    switch: ['A','B','C'], gate: ['A'],
    mathnode: ['A','B','C'],
    variable: [],
    subgraph: ['A'],
    d_temperature: ['H', 'S'], d_heat: ['T', 'D', 'M'],
    d_wind: ['A'], d_windmodify: ['W', 'D', 'M'],
    d_curvature: ['A'], d_flow: ['A'], d_occlusion: ['A'], d_deposits: ['A', null],
    d_wear: ['A'], d_peaks: ['A'], d_texture: ['A'], aspect: ['A'],
    // --- effects (passthrough) ---
    water: ['A', 'T'], snow: ['A', 'T', 'W'], satmap: ['A', 'D', 'M'],
    colorerosion: ['SAT', 'D', 'M'], weathering: ['SAT', 'M'],
    satmapblend: ['SAT', 'SAT2', 'M'], colormixer: ['SAT', 'SAT2', 'SAT3'],
    // --- output ---
    output: ['A'],
  };

  // A recipe entry of `null` means DECLARED BUT DELIBERATELY UNWIRED. It still occupies its slot,
  // so the arity check below is unchanged and a new input cannot be hidden by shortening a recipe —
  // but nothing is attached to it, and the reason has to be stated here or build() refuses.
  //
  // This exists because for one slot in the app, wiring it DESTROYS coverage rather than adding it.
  // Everything else in this table gains from a source; that one loses everything it had.
  const UNWIRED_REASON = {
    'd_deposits:1': 'S3.4 made this the OPTIONAL explicit Sediment state override, and a connected '
      + 'state makes d_deposits return that input byte-for-byte. Wiring a perlin here would replace '
      + "the morphological closing in this digest with an identity passthrough of the source — "
      + 'deleting the only coverage depositsField() has anywhere in the gate, on the very node whose '
      + 'radius control was once found dead. The prediction branch is what this recipe pins; the '
      + 'override branch is gated by _verify_cover_reader.js:depositsReturnsConnectedStateIdentity.',
  };

  // Auxiliary FIELDS each node hangs off itself (dotted paths allowed). These carry the actual
  // computation for the climate / snow / colour-driver nodes, whose returned field is only a
  // passthrough. `snow` stores a whole simulation result object, so reach into its depth grid.
  const AUX = {
    d_sunshadow: ['_solarExposure'],
    d_temperature: ['_temperatureC', '_solarShadow', '_solarExposure'],
    d_heat: ['_temperatureC'],
    d_wind: ['_wind.u', '_wind.v', '_wind.speed'],
    d_windmodify: ['_wind.u', '_wind.v', '_wind.speed'],
    snow: ['_snowLayer.depthM'],
    satmap: ['_driver'],
  };
  // Auxiliary SCALARS: float64 accumulations over the whole grid, in a fixed traversal order.
  // They pin the mass-conservation bookkeeping of the snow model, which no single-field digest
  // of the final depth grid fully constrains.
  const SCALARS = {
    snow: ['_snowLayer.volumeM3', '_snowLayer.depositedM3', '_snowLayer.meltedM3',
      '_snowLayer.movedM3', '_snowLayer.maxDepthM', '_snowLayer.coverage',
      '_snowLayer.iterationsRun'],
  };
  const reach = (obj, dotted) => dotted.split('.').reduce((o, k) => (o == null ? o : o[k]), obj);
  // Nodes whose real output is colour, resolved by walking the colour graph.
  const COLOUR = new Set(['satmap', 'colorerosion', 'weathering', 'satmapblend', 'colormixer']);

  // Nodes that are EXACTLY the identity at their default parameters (Levels 0..1 / gamma 1,
  // Curve at 0.5/0.5, Clamp 0..1, Transform with a unit matrix taking the exact re-evaluation
  // path, Temperature Modify offsetting by 0 degrees). A default-parameter digest for these is an
  // identity digest: it would still read "unchanged" if the implementation were gutted. So each
  // also gets ONE documented non-default evaluation folded in as `ex=`, chosen to enter the code
  // path defaults skip — including Transform's raster resample, which the exact path never runs.
  const EXERCISE = {
    normalizen: { amount: 0.35 },
    levels: { inLo: 0.18, inHi: 0.82, gamma: 1.7, outLo: 0.05, outHi: 0.95 },
    curve: { bias: 0.3, gain: 0.72 },
    clampn: { lo: 0.35, hi: 0.62 },
    transform: { mode: 'raster', scale: 1.3, aspect: 0.8, angle: 37, offX: 0.11, offY: -0.07,
      pivX: 0.4, pivY: 0.6, edge: 'mirror' },
    d_heat: { mode: 'set', targetC: 900, amount: 0.6 },
    d_windmodify: { direction: 45, speed: 26, amount: 0.65 },
    // Not identity-shaped, but the default form:"peak" never reaches the massif branch — and
    // with it the second hydraulicErode call, which must stay settle-free (opt-out contract).
    mountain: { form: 'massif' },
    surface: [
      { name: 'roughen', overrides: { style: 'roughen', amountM: 120 } },
      { name: 'distress', overrides: { style: 'distress', amountM: 120 } },
      { name: 'groundtexture', overrides: { style: 'groundtexture', amountM: 120 } },
      { name: 'rocknoise', overrides: { style: 'rocknoise', amountM: 120 } },
      { name: 'bulbous', overrides: { style: 'bulbous', amountM: 120 } },
      { name: 'pockmarks', overrides: { style: 'pockmarks', amountM: 120 } },
      { name: 'contours', overrides: { style: 'contours', amountM: 120 } },
      { name: 'grid', overrides: { style: 'grid', amountM: 120, angleDeg: 37 } },
    ],
  };

  // A fixed stroke: drawmask ships with strokes:[] and would otherwise digest an all-zero field.
  const DRAW_STROKES = () => ([{
    points: [[0.12, 0.22], [0.38, 0.55], [0.62, 0.41], [0.88, 0.74]],
    width: 0.09, hardness: 0.6, opacity: 1, mode: 'draw',
  }]);
  // A deterministic synthetic DEM: Import has no file here, and would otherwise only ever cover
  // its radialField() fallback instead of the _dem sampling path.
  const SYNTH_DEM = () => {
    const n = RES, a = new Float32Array(n * n);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      const u = x / n, v = y / n;
      a[y * n + x] = 0.5 + 0.35 * Math.sin(u * 6.2831853 * 1.5) * Math.cos(v * 6.2831853 * 2.5)
        + 0.1 * u - 0.1 * v;
    }
    return a;
  };

  // Build a fresh single-node graph of `type`, wire every declared input, evaluate.
  function build(type, over) {
    reset();
    const src = makeSources();
    const nd = mk(type, over);
    const recipe = WIRING[type];
    recipe.forEach((key, slot) => {
      if (key === null) {
        // Absence of evidence is a failure, not a pass: an unexplained hole in a recipe is
        // indistinguishable from a slot somebody forgot, so it throws and the type is SKIPPED,
        // which `complete` already refuses.
        if (!UNWIRED_REASON[type + ':' + slot]) {
          throw new Error('wiring recipe leaves slot ' + slot + ' unwired with no stated reason — '
            + 'add "' + type + ':' + slot + '" to UNWIRED_REASON or wire it');
        }
        return;
      }
      const source = src(key);
      if (!source) throw new Error('wiring recipe slot ' + slot + ' uses unsupported source ' + key);
      wire(source, nd, slot);
    });
    if (type === 'drawmask') nd.params.strokes = DRAW_STROKES();
    if (type === 'import') nd._dem = SYNTH_DEM();
    // Regolith's Duration is REQUIRED AUTHORED DATA with no production default (S3.2), so a
    // default-parameter Regolith node refuses to evaluate — by design, and gated by
    // _verify_soildepth.js:durationHasNoProductionDefault. The digest therefore has to author one,
    // exactly as it authors a stroke for drawmask and a DEM for import: a node type whose defaults
    // cannot produce a field is otherwise SKIPPED, which is the digest's own failure mode. 1000 yr
    // is the acceptance oracle's fixture. Guarded on == null so an EXERCISE override still wins.
    if (type === 'regolith' && nd.params.durationYears == null) nd.params.durationYears = 1000;
    const t0 = performance.now();
    const field = ev(nd.id, new Set());
    return { nd, field, ms: performance.now() - t0,
      slot0: recipe.length ? (src(recipe[0]) || {})._field || null : null,
      declared: nodeInputs(nd) };
  }

  function run(type) {
    const def = TYPES[type];
    if (!def) return { type, skipped: 'not present in TYPES' };
    if (!WIRING[type]) {
      return { type, skipped: 'no wiring recipe defined in _verify_digest.js — add one so this '
        + 'node type is covered instead of silently omitted' };
    }
    let r;
    try { r = build(type); }
    catch (err) { return { type, skipped: 'eval threw: ' + ((err && err.message) || String(err)) }; }

    const { nd, field: primary } = r;
    // colormixer declares its slots on the node, everything else on the TYPE
    const slotWarn = r.declared.length !== WIRING[type].length
      ? 'recipe covers ' + WIRING[type].length + ' slot(s) but the node declares '
        + r.declared.length + ' (' + r.declared.join(', ') + ')'
      : null;
    if (!primary || !ArrayBuffer.isView(primary)) {
      return { type, slotWarn, skipped: 'eval returned no field ('
        + Object.prototype.toString.call(primary) + ')' };
    }
    if (primary.length !== RES * RES) {
      return { type, slotWarn, skipped: 'eval returned a field of length ' + primary.length
        + ', expected ' + (RES * RES) };
    }

    const head = digest(primary);
    const parts = [head];
    const diag = { ms: Math.round(r.ms), primary: stats(primary), aux: {},
      identity: !!(r.slot0 && digest(r.slot0) === head) };

    // Non-primary declared outputs, folded under their port id. A vectorRaster is 3 interleaved
    // components per sample, so its length is 3*RES*RES and the fold covers every component.
    for (const [portId, value] of (nd._digestPorts || [])) {
      const d = digest(value);
      if (d === null) {
        parts.push('port_' + portId + '=INVALID(' + (value == null ? String(value)
          : (value.constructor && value.constructor.name) || typeof value) + ')');
      } else {
        parts.push('port_' + portId + '=' + d);
        diag.aux['port_' + portId] = stats(value);
      }
    }

    for (const p of (AUX[type] || [])) {
      const name = p.replace(/^_/, '').replace(/\./g, '_');
      const f = reach(nd, p);
      const d = digest(f);
      if (d === null) {
        parts.push(name + '=INVALID(' + (f == null ? String(f)
          : (f.constructor && f.constructor.name) || typeof f) + ')');
        diag.aux[name] = null;
      } else { parts.push(name + '=' + d); diag.aux[name] = stats(f); }
    }
    for (const p of (SCALARS[type] || [])) {
      const name = p.replace(/^_/, '').replace(/\./g, '_'), v = reach(nd, p);
      parts.push(name + '=' + (typeof v === 'number' ? String(v) : 'INVALID(' + typeof v + ')'));
    }
    if (COLOUR.has(type)) {
      let col = null, cerr = null;
      try { col = resolveColor(nd.id, RES, {}, new Set()); }
      catch (err) { cerr = (err && err.message) || String(err); }
      if (cerr) parts.push('color=ERR:' + cerr);
      else if (digest(col) === null) parts.push('color=absent');
      else { parts.push('color=' + digest(col)); diag.aux.color = stats(col); }
    }
    if (type === 'water') {
      // The Water node's own eval is `ins[0] || newField()` — a pure passthrough. Every lake and
      // river it describes is produced downstream by refreshWater(), which needs a live WebGL
      // context and the renderer's cached surface, so it is out of reach of a CPU-only oracle.
      // What IS reachable, and is pure CPU terrain computation that exists only to serve this
      // node, is the depression fill and the D8 accumulation that place the lake levels and the
      // river network. Digest those against the node's own output so Water is not a blind spot.
      try {
        const filled = priorityFloodFill(primary);
        parts.push('filled=' + digest(filled));
        parts.push('accum=' + digest(d8Accumulation(filled)));
      } catch (err) { parts.push('hydrology=ERR:' + ((err && err.message) || String(err))); }
    }
    if (EXERCISE[type]) {
      const exercises = Array.isArray(EXERCISE[type]) ? EXERCISE[type]
        : [{ name: '', overrides: EXERCISE[type] }];
      diag.exercise = {};
      for (const exercise of exercises) try {
        const x = build(type, exercise.overrides), xd = digest(x.field);
        const suffix = exercise.name ? '_' + exercise.name : '';
        parts.push('ex' + suffix + '=' + (xd === null ? 'INVALID' : xd));
        diag.exercise[exercise.name || 'default'] = stats(x.field);
        if (AUX[type]) for (const p of AUX[type]) {
          const d = digest(reach(x.nd, p));
          parts.push('ex' + suffix + '_' + p.replace(/^_/, '').replace(/\./g, '_') + '=' + (d === null ? 'INVALID' : d));
        }
      } catch (err) { parts.push('ex' + (exercise.name ? '_' + exercise.name : '')
        + '=ERR:' + ((err && err.message) || String(err))); }
    }
    return { type, digest: parts.join('|'), diag, slotWarn };
  }

  window.__D = { run, types: Object.keys(TYPES) };
  return { types: Object.keys(TYPES), res: RES };
}

/* ------------------------------------------------------------------ node */
const log = (...a) => console.error(...a);

async function sweep(page, label) {
  const info = await page.evaluate(installHarness, { res: RES });
  const digests = {}, skipped = [], diags = {}, warns = [];
  for (const type of info.types) {
    const r = await page.evaluate(t => window.__D.run(t), type);
    if (r.slotWarn) warns.push(r.type + ': ' + r.slotWarn);
    if (r.skipped) {
      skipped.push({ type: r.type, reason: r.skipped });
      log('  ' + label + ' ' + r.type.padEnd(16) + ' SKIPPED  ' + r.skipped);
      continue;
    }
    digests[r.type] = r.digest;
    diags[r.type] = r.diag;
    if (/INVALID|=ERR:/.test(r.digest)) warns.push(r.type + ': ' + r.digest);
    if (VERBOSE) {
      const s = r.diag.primary;
      log('  ' + label + ' ' + r.type.padEnd(16) + ' ' + String(r.diag.ms).padStart(6) + ' ms  '
        + r.digest
        + '  [' + s.min.toFixed(4) + ' .. ' + s.max.toFixed(4) + ']'
        + (s.nonFinite ? '  NON-FINITE=' + s.nonFinite : '')
        + (s.constant ? '  CONSTANT' : ''));
    }
  }
  return { digests, skipped, diags, warns, types: info.types };
}

function document_(res, sweepResult) {
  const digests = {};
  Object.keys(sweepResult.digests).sort().forEach(k => { digests[k] = sweepResult.digests[k]; });
  const skipped = sweepResult.skipped.slice().sort((a, b) => a.type.localeCompare(b.type));
  return {
    res,
    nodeCount: Object.keys(digests).length,
    skipped,
    digests,
    generatedAt: null,      // deliberately null: the baseline must be byte-stable across re-runs
  };
}

(async () => {
  const browser = await chromium.launch({
    executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  page.setDefaultTimeout(0);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  const runs = [];
  for (let i = 0; i < REPEAT; i++) {
    if (i === 0) await page.goto(URL, { waitUntil: 'load' });
    else await page.reload({ waitUntil: 'load' });
    await page.waitForTimeout(1400);
    log((REPEAT > 1 ? 'sweep ' + (i + 1) + '/' + REPEAT + ' ' : '') + 'digesting ' + PAGE
      + ' at ' + RES + '\u00b2 ...');
    runs.push(await sweep(page, REPEAT > 1 ? '[' + (i + 1) + ']' : ' '));
  }
  await browser.close();

  const first = runs[0];
  const doc = document_(RES, first);

  // ---- determinism check across repeated sweeps -------------------------------------------
  const nondet = [];
  for (let i = 1; i < runs.length; i++) {
    for (const t of Object.keys(first.digests)) {
      if (runs[i].digests[t] !== first.digests[t]) {
        nondet.push({ type: t, run1: first.digests[t], ['run' + (i + 1)]: runs[i].digests[t] });
      }
    }
  }

  process.stdout.write(JSON.stringify(doc, null, 2) + '\n');

  first.warns.forEach(w => log('WARN  ' + w));

  // Standing sensitivity report: a node whose output equals its slot-0 input carries no evidence
  // of its own implementation unless something else in its digest does.
  const weak = Object.keys(first.diags).filter(t => first.diags[t].identity
    && !/\|[A-Za-z_]+=[0-9a-f]+:[0-9a-f]+/.test(first.digests[t]));
  if (weak.length) {
    log('');
    log('LOW-SENSITIVITY (output is bit-identical to the slot-0 input, and the node computes no '
      + 'other field, so the digest cannot detect a broken implementation):');
    weak.forEach(t => log('  ' + t));
  }
  if (errors.length) {
    log('');
    log('page errors observed (' + errors.length + '):');
    errors.slice(0, 10).forEach(e => log('  ' + e));
  }
  log('');
  log('covered ' + doc.nodeCount + '/' + first.types.length + ' registered node types, skipped '
    + doc.skipped.length);
  doc.skipped.forEach(s => log('  SKIPPED ' + s.type + ': ' + s.reason));

  if (REPEAT > 1) {
    if (nondet.length) {
      log('');
      log('NON-DETERMINISTIC across ' + REPEAT + ' sweeps of the SAME build — these cannot be '
        + 'gated until fixed or documented in NONDETERMINISTIC:');
      nondet.forEach(n => log('  ' + JSON.stringify(n)));
    } else {
      log(REPEAT + ' sweeps of the same build produced identical digests for all '
        + doc.nodeCount + ' node types.');
    }
  }

  const gated = t => !(t in NONDETERMINISTIC);
  Object.keys(NONDETERMINISTIC).forEach(t =>
    log('UNGATED ' + t + ': ' + NONDETERMINISTIC[t]));

  const complete = first.types.length === REQUIRED_NODE_COUNT
    && doc.nodeCount === REQUIRED_NODE_COUNT && !doc.skipped.length && !first.warns.length;
  if (!complete) {
    log('INCOMPLETE digest sweep: required ' + REQUIRED_NODE_COUNT + '/' + REQUIRED_NODE_COUNT
      + ' registered node types with zero skips and zero wiring warnings.');
  }

  if (WRITE) {
    if (nondet.length || !complete) {
      log('baseline not written: the repeated digest sweep is not complete and deterministic.');
      process.exit(1);
    }
    fs.writeFileSync(BASELINE, JSON.stringify(doc, null, 2) + '\n');
    log('baseline written: ' + BASELINE);
    process.exit(0);
  }

  // ---- GATE ---------------------------------------------------------------------------------
  if (!fs.existsSync(BASELINE)) {
    log('FATAL no baseline at ' + BASELINE + ' — run `node _verify_digest.js --write` first.');
    process.exit(2);
  }
  let base;
  try { base = JSON.parse(fs.readFileSync(BASELINE, 'utf8')); }
  catch (e) { log('FATAL baseline is not valid JSON: ' + e.message); process.exit(2); }

  if (base.res !== doc.res) {
    log('FATAL baseline was recorded at ' + base.res + '\u00b2 but this run is '
      + doc.res + '\u00b2 — digests are resolution dependent. Re-run with --res=' + base.res + '.');
    process.exit(2);
  }

  const drifted = [], missing = [], added = [];
  for (const t of Object.keys(base.digests)) {
    if (!gated(t)) continue;
    if (!(t in doc.digests)) missing.push(t);
    else if (doc.digests[t] !== base.digests[t]) drifted.push(t);
  }
  for (const t of Object.keys(doc.digests)) {
    if (!gated(t)) continue;
    if (!(t in base.digests)) added.push(t);
  }

  log('');
  if (drifted.length) {
    log('BEHAVIOUR CHANGED in ' + drifted.length + ' node type(s):');
    drifted.forEach(t => {
      log('  ' + t);
      log('      baseline ' + base.digests[t]);
      log('      current  ' + doc.digests[t]);
    });
  }
  if (missing.length) {
    log('MISSING from this build (in the baseline, not digested now) — '
      + missing.length + ' node type(s):');
    missing.forEach(t => {
      const s = doc.skipped.find(x => x.type === t);
      log('  ' + t + (s ? '  (skipped: ' + s.reason + ')' : '  (absent from TYPES)'));
    });
  }
  if (added.length) {
    log('NEW node type(s) with no baseline entry — ' + added.length + ':');
    added.forEach(t => log('  ' + t));
    log('  Re-baseline deliberately with --write once the new behaviour is reviewed.');
  }

  const ok = !drifted.length && !missing.length && !added.length && !nondet.length && complete;
  log(ok
    ? 'PASS  ' + doc.nodeCount + ' node types bit-identical to the baseline at ' + doc.res + '\u00b2.'
    : 'FAIL  the computed terrain is not identical to the baseline.');
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
