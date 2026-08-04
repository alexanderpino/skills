const { chromium } = require('playwright-core');
const path = require('node:path');
const { mkdirSync, writeFileSync } = require('node:fs');

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));
const STYLES = ['roughen', 'distress', 'groundtexture', 'rocknoise', 'bulbous', 'pockmarks', 'contours', 'grid'];
// A visual mutation FORCES the capture on. flat-render and unfrozen-framebuffer are checked only
// inside the --visual block; without it they rendered nothing and still exited 1, reporting a
// violation never observed. The sweep never passes --visual, so both were dead in every automated
// run. Same defect, same fix, as _verify_landforms.
const VISUAL_MUTATIONS = ['flat-render', 'unfrozen-framebuffer'];
const VISUAL = process.argv.includes('--visual')
  || VISUAL_MUTATIONS.includes((process.argv.find(a => a.startsWith('--mutate=')) || '').slice(9));
const SUMMARY = process.argv.includes('--summary');
const flagValue = name => process.argv.find(argument => argument.startsWith(`--${name}=`))?.split('=')[1];
const VISUAL_STYLE = flagValue('visual-style');
const VISUAL_LATTICE = flagValue('visual-lattice');
const VISUAL_VIEW = flagValue('visual-view');
const mutationArg = process.argv.find(argument => argument.startsWith('--mutate='));
const MUTATION = mutationArg ? mutationArg.slice(9) : null;
const MUTATIONS = ['roughen-drop-slope', 'distress-invert-convex', 'groundtexture-drop-wear',
  'rocknoise-use-fbm', 'bulbous-invert-cell', 'pockmarks-positive', 'contours-cell-height',
  'grid-unrotated', 'pre-mask', 'cell-space', 'nyquist-force-one', 'hex-row-normalized',
  'root-seed-zero', 'spectral-cell-space', 'width-double', 'slope-endpoint',
  'copycam-drop-fov', 'unfrozen-framebuffer', 'flat-render'];
if (MUTATION && !MUTATIONS.includes(MUTATION)) { console.error(`Unknown mutation ${MUTATION}`); process.exit(2); }

const EXPECTED = {
  amountM: ['slider', 0, 500, 10],
  wavelengthM: ['slider', 10, 5000, 80],
  octaves: ['slider', 1, 10, 4],
  lacunarity: ['slider', 1.25, 4, 2],
  gain: ['slider', 0.1, 0.9, 0.5],
  seed: ['seed', undefined, undefined, 7],
  slopeLowDeg: ['slider', 0, 89, 5],
  slopeHighDeg: ['slider', 1, 89, 35],
  curvatureStrength: ['slider', 0, 4, 1],
  curvatureWidth: ['slider', 0.001, 1, 0.25],
  wearStrength: ['slider', 0, 4, 1],
  occlusionRadiusM: ['slider', 1, 5000, 300],
  occlusionDirections: ['slider', 4, 32, 8],
  cellSpacingM: ['slider', 10, 5000, 100],
  bulbRadiusM: ['slider', 1, 2500, 40],
  pitRadiusM: ['slider', 1, 2500, 25],
  edgeFeatherM: ['slider', 0, 1000, 8],
  intervalM: ['slider', 2, 5000, 100],
  spacingM: ['slider', 2, 5000, 250],
  lineWidthM: ['slider', 0.25, 1000, 10],
  angleDeg: ['slider', 0, 360, 0],
};

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(800);

  const lifecycle = await page.evaluate(mutation => {
    const readSeed = value => ({ has: Object.prototype.hasOwnProperty.call(value, 'seed'),
      value: value.seed === undefined ? null : value.seed });
    const defaults = () => Object.fromEntries(TYPES.surface.params.map(param => [param.key, cloneParams(param.def)]));
    const compare = (actual, expected) => { let changed = 0;
      for (let index = 0; index < actual.length; index++) if (actual[index] !== expected[index]) changed++;
      return changed;
    };
    const signature = field => { let hash = 2166136261 >>> 0; const view = new DataView(new ArrayBuffer(4));
      for (const value of field) { view.setFloat32(0, value, true); hash ^= view.getUint32(0, true); hash = Math.imul(hash, 16777619) >>> 0; }
      return hash.toString(16).padStart(8, '0'); };
    RES = 64; TARGET_RES = 64; terrainDef.scale = 5000; terrainDef.height = 2600; terrainDef.lattice = 'square'; XF = null;
    const input = newField(), size = fieldW();
    for (let y = 0; y < fieldH(); y++) for (let x = 0; x < size; x++) {
      const dx = (x + .5) / size - .5, dy = (y + .5) / fieldH() - .5;
      input[y * size + x] = .18 + .55 * Math.max(0, 1 - 2.2 * Math.hypot(dx, dy) ** 2);
    }
    const params = { ...defaults(), style: 'roughen', amountM: 180, wavelengthM: 700, octaves: 4, seed: 19 };
    const node = { id: 23 }, phases = [];
    const measure = (name, expectedRoot) => {
      const root = readSeed(terrainDef), snapshot = readSeed(graphSnapshot().terrainDef);
      const actual = TYPES.surface.eval(params, [input, null], node);
      const expected = TYPES.surface.field(input, params, null, node.id, expectedRoot);
      phases.push({ name, expectedRoot, root, snapshot,
        effectiveSeed: TYPES.surface.effectiveSeed(TYPES.surface.options(params), node.id, expectedRoot),
        signature: signature(actual), expectedSignature: signature(expected), oracleDiff: compare(actual, expected) });
    };
    const restore = seed => {
      const snapshot = graphSnapshot();
      if (seed === undefined) delete snapshot.terrainDef.seed; else snapshot.terrainDef.seed = seed;
      undoStack = [snapshot]; redoStack = []; undoGraph();
    };
    measure('boot', 7);
    const originalConfirm = globalThis.confirm; globalThis.confirm = () => true;
    newTerrainDocument(false); globalThis.confirm = originalConfirm;
    measure('new', 7);
    restore(undefined); measure('legacy-seedless', 7);
    restore(0); measure('explicit-0', 0);
    restore(123); measure('explicit-123', 123);
    restore(456); measure('explicit-456', 456);
    const byName = Object.fromEntries(phases.map(phase => [phase.name, phase]));
    const stateOk = phases.every(phase => phase.root.has && phase.snapshot.has
      && phase.root.value === phase.expectedRoot && phase.snapshot.value === phase.expectedRoot);
    const oracleOk = phases.every(phase => phase.oracleDiff === 0 && phase.signature === phase.expectedSignature);
    const stableSeven = byName.boot.signature === byName.new.signature
      && byName.boot.signature === byName['legacy-seedless'].signature;
    const distinctRoots = ['explicit-0', 'explicit-123', 'explicit-456']
      .every(name => byName[name].signature !== byName.boot.signature);
    const authoredFov = .73, rounds = [];
    frameHero(); cam = { ...cam, target: [...cam.target], fov: authoredFov };
    for (let round = 0; round < 2; round++) {
      togglePlanView();
      const planFov = cam.fov; togglePlanView();
      if (mutation === 'copycam-drop-fov') delete cam.fov;
      rounds.push({ round: round + 1, planFov, restoredFov: cam.fov });
    }
    frameHero(); const resetFov = cam.fov;
    const camera = { authoredFov, defaultFov: 1.05, rounds, resetFov,
      ok: rounds.length === 2 && rounds.every(round => round.planFov === authoredFov && round.restoredFov === authoredFov)
        && resetFov === 1.05 };
    return { phases, stateOk, oracleOk, stableSeven, distinctRoots, camera,
      ok: phases.length === 6 && stateOk && oracleOk && stableSeven && distinctRoots && camera.ok };
  }, MUTATION);

  const measured = await page.evaluate(({ styles, expected }) => {
    const def = TYPES.surface;
    if (!def) return { registered: false };
    const byKey = Object.fromEntries(def.params.map(param => [param.key, param]));
    const manifest = Object.fromEntries(Object.entries(expected).map(([key, spec]) => {
      const param = byKey[key];
      return [key, !!param && param.type === spec[0] && param.min === spec[1]
        && param.max === spec[2] && param.def === spec[3]];
    }));
    const style = byKey.style;
    return {
      registered: true,
      category: def.cat,
      inputs: def.ins,
      styles: style?.opts?.map(option => option[0]),
      styleDefault: style?.def,
      manifest,
      copyHonest: !/(gaea.{0,24}(same|exact|internal|parity)|proprietary)/i.test(`${def.desc || ''} ${def.note || ''}`),
    };
  }, { styles: STYLES, expected: EXPECTED });

  const analytic = await page.evaluate(({ styles, mutation }) => {
    const gamma = n => (n * 2 ** -24) / (1 - n * 2 ** -24);
    const smoothstep = (a, b, value) => { if (a === b) return value < a ? 0 : 1;
      const t = clamp((value - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
    const mix32 = value => { let h = value >>> 0; h = Math.imul(h ^ (h >>> 16), 0x7feb352d) >>> 0;
      h = Math.imul(h ^ (h >>> 15), 0x846ca68b) >>> 0; return (h ^ (h >>> 16)) >>> 0; };
    const hashText = text => { let h = 2166136261 >>> 0; for (let i = 0; i < text.length; i++) {
      h ^= text.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return h; };
    const hash01 = (x, y, seed) => mix32((Math.imul(x, 374761393) + Math.imul(y, 668265263) + seed) >>> 0) / 4294967296;
    const effectiveSeed = (style, seed, nodeId, rootSeed) => mix32((seed + Math.imul(nodeId, 0x9e3779b1)
      + hashText(style) + (mutation === 'root-seed-zero' ? 0 : rootSeed)) >>> 0);
    const normalized = field => { let minimum = Infinity, maximum = -Infinity;
      for (const value of field) { minimum = Math.min(minimum, value); maximum = Math.max(maximum, value); }
      const range = maximum - minimum || 1, output = new Float32Array(field.length);
      for (let i = 0; i < field.length; i++) output[i] = (field[i] - minimum) / range; return output; };
    const fbm = (worldX, worldY, wavelength, seed, options, cellM) => {
      let count = 0; for (let k = 0; k < options.octaves; k++) {
        if (wavelength / options.lacunarity ** k < 2 * cellM) break; count++; }
      if (mutation === 'nyquist-force-one') count = Math.max(1, count);
      if (count === 0) return { value: 0, octaves: 0 };
      let sum = 0, total = 0, weight = 1;
      for (let k = 0; k < count; k++) { const frequency = options.lacunarity ** k / wavelength;
        sum += weight * gnoise(worldX * frequency, worldY * frequency, (seed + 7 * k) >>> 0);
        total += weight; weight *= options.gain; }
      return { value: 2 * sum / total - 1, octaves: count };
    };
    const nearest = (worldX, worldY, spacing, seed) => { const px = worldX / spacing, py = worldY / spacing;
      const cx = Math.floor(px), cy = Math.floor(py); let distance = Infinity;
      for (let oy = -1; oy <= 1; oy++) for (let ox = -1; ox <= 1; ox++) { const gx = cx + ox, gy = cy + oy;
        const fx = (gx + hash01(gx, gy, seed)) * spacing, fy = (gy + hash01(gx, gy, seed + 91)) * spacing;
        distance = Math.min(distance, Math.hypot(worldX - fx, worldY - fy)); } return distance; };
    const pattern = (style, worldX, worldY, heightM, options, seed, cellM) => {
      const useCellSpace = mutation === 'cell-space';
      const px = useCellSpace ? worldX / cellM : worldX, py = useCellSpace ? worldY / cellM : worldY;
      if (['roughen', 'distress', 'groundtexture', 'rocknoise'].includes(style)) { const value = fbm(px, py, options.wavelengthM, seed, options, cellM).value;
        return style === 'rocknoise' && mutation !== 'rocknoise-use-fbm' ? 1 - Math.abs(value) : value; }
      if (style === 'bulbous') { const d = nearest(px, py, options.cellSpacingM, seed), coverage = smoothstep(0, options.bulbRadiusM, d);
        return mutation === 'bulbous-invert-cell' ? coverage : 1 - coverage; }
      if (style === 'pockmarks') { const d = nearest(px, py, options.cellSpacingM, seed), pit = 1 - smoothstep(options.pitRadiusM, options.pitRadiusM + options.edgeFeatherM, d);
        return mutation === 'pockmarks-positive' ? pit : -pit; }
      if (style === 'contours') { const z = mutation === 'contours-cell-height' ? heightM / terrainDef.height : heightM;
        const d = Math.abs(((z + options.intervalM / 2) % options.intervalM + options.intervalM) % options.intervalM - options.intervalM / 2);
        return 1 - smoothstep(options.lineWidthM / 2, options.lineWidthM, d); }
      const angle = (mutation === 'grid-unrotated' ? 0 : options.angleDeg) * Math.PI / 180;
      const rx = px * Math.cos(angle) - py * Math.sin(angle), ry = px * Math.sin(angle) + py * Math.cos(angle);
      const dx = Math.abs(((rx + options.spacingM / 2) % options.spacingM + options.spacingM) % options.spacingM - options.spacingM / 2);
      const dy = Math.abs(((ry + options.spacingM / 2) % options.spacingM + options.spacingM) % options.spacingM - options.spacingM / 2);
      return 1 - smoothstep(options.lineWidthM / 2, options.lineWidthM, Math.min(dx, dy));
    };
    const maxError = (actual, expected) => { let error = 0; for (let i = 0; i < actual.length; i++) error = Math.max(error, Math.abs(actual[i] - expected[i])); return error; };

    const invalid = { unknown: false, finite: true, relational: true };
    try { TYPES.surface.options({ style: 'unknown' }); } catch (error) { invalid.unknown = /unknown style/i.test(error.message); }
    const malformed = TYPES.surface.options({ slopeLowDeg: 89, slopeHighDeg: -Infinity, cellSpacingM: 100,
      bulbRadiusM: Infinity, pitRadiusM: Infinity, edgeFeatherM: Infinity, style: 'pockmarks', spacingM: 20, lineWidthM: 1000, angleDeg: 360 });
    invalid.finite = Object.values(malformed).filter(value => typeof value === 'number').every(Number.isFinite);
    const measuredSlopeLow = mutation === 'slope-endpoint' ? 89 : malformed.slopeLowDeg;
    invalid.relational = measuredSlopeLow === 88 && malformed.slopeHighDeg === 89 && malformed.slopeHighDeg >= measuredSlopeLow + 1 && malformed.pitRadiusM <= 50
      && malformed.edgeFeatherM <= 50 - malformed.pitRadiusM && malformed.lineWidthM < malformed.spacingM / 2 && malformed.angleDeg === 0;
    invalid.ok = invalid.unknown && invalid.finite && invalid.relational;

    const runs = [];
    for (const lattice of ['square', 'hex']) for (const resolution of [128, 256]) {
      RES = resolution; TARGET_RES = resolution; terrainDef.lattice = lattice; terrainDef.scale = 5000; terrainDef.height = 2600; terrainDef.seed = 7; XF = null;
      const n = fieldW(), nh = fieldH(), cellM = terrainDef.scale / n, input = newField(), mask = newField(), inverse = newField();
      for (let y = 0; y < nh; y++) for (let x = 0; x < n; x++) { const worldX = (x + .5 + (lattice === 'hex' ? .5 * (y & 1) : 0)) * cellM;
        const worldY = (y + .5) * cellM * (lattice === 'hex' ? Math.sqrt(3) / 2 : 1), radius = Math.hypot(worldX - 2500, worldY - 2500) / 2500;
        input[y * n + x] = .18 + .55 * Math.max(0, 1 - radius * radius); mask[y * n + x] = x < n / 2 ? 1 : 0; inverse[y * n + x] = 1 - mask[y * n + x]; }
      const slope = slopeOf(input), profile = curvatureField(input, { kind: 'profile', strength: 1 }), mean = curvatureField(input, { kind: 'mean', strength: 1 });
      const slopeNormalized = normalized(slope), wearRaw = new Float32Array(input.length);
      for (let i = 0; i < input.length; i++) wearRaw[i] = Math.max(.5 - mean[i], 0) * 2 * slopeNormalized[i];
      const wear = normalized(wearRaw), occlusion = occlusionField(input, { radius: 300 / terrainDef.scale, dirs: 8 });
      const indices = []; for (let iy = 1; iy <= 8; iy++) for (let ix = 1; ix <= 8; ix++) indices.push([Math.floor(ix * n / 10), Math.floor(iy * nh / 10)]);
      const stylesReport = {};
      for (const style of styles) { const params = Object.fromEntries(TYPES.surface.params.map(param => [param.key, cloneParams(param.def)]));
        Object.assign(params, { style, angleDeg: 37, intervalM: 137, spacingM: 263, lineWidthM: 20 });
        const options = TYPES.surface.options(params), node = { id: 23 }, actual = TYPES.surface.eval(params, [input, null], node);
        const zeroAmount = TYPES.surface.eval({ ...params, amountM: 0 }, [input, null], node), zeroMask = TYPES.surface.eval(params, [input, newField()], node);
        const masked = TYPES.surface.eval(params, [input, mask], node), inverted = TYPES.surface.eval(params, [input, inverse], node);
        const repeat = TYPES.surface.eval(params, [input, null], node), changedSeed = TYPES.surface.eval({ ...params, seed: params.seed + 1 }, [input, null], node);
        terrainDef.seed = 8; const changedRoot = TYPES.surface.eval(params, [input, null], node); terrainDef.seed = 7;
        const expected = [], sampled = [], seed = effectiveSeed(style, options.seed, node.id, 7), low = Math.tan(options.slopeLowDeg * Math.PI / 180), high = Math.tan(options.slopeHighDeg * Math.PI / 180);
        let driverNonzero = 0, changed = 0, maskExchange = true;
        for (const index of indices) { const x = index[0], y = index[1], i = y * n + x, worldX = (x + .5 + (lattice === 'hex' ? .5 * (y & 1) : 0)) * cellM;
          const worldY = mutation === 'hex-row-normalized' && lattice === 'hex'
            ? (y + .5) / nh * terrainDef.scale
            : (y + .5) * cellM * (lattice === 'hex' ? Math.sqrt(3) / 2 : 1);
          const slopeMask = smoothstep(low, high, slope[i] * terrainDef.height / terrainDef.scale);
          const convex = smoothstep(0, options.curvatureWidth, Math.max(0, .5 - profile[i]) * 2); let driver = 1;
          if (style === 'roughen') driver = mutation === 'roughen-drop-slope' ? 1 : slopeMask;
          else if (style === 'distress') driver = mutation === 'distress-invert-convex' ? 1 - convex : convex;
          else if (style === 'groundtexture') driver = (1 - slopeMask) * (mutation === 'groundtexture-drop-wear' ? 1 : 1 - wear[i]);
          else if (style === 'rocknoise') driver = slopeMask * convex;
          else if (style === 'bulbous') driver = wear[i]; else if (style === 'pockmarks') driver = 1 - occlusion[i];
          if (driver !== 0) driverNonzero++;
          const proposed = Math.fround((input[i] * terrainDef.height + options.amountM * driver
            * pattern(style, worldX, worldY, input[i] * terrainDef.height, options, seed, cellM)) / terrainDef.height);
          const expectedValue = mutation === 'pre-mask' && mask[i] ? input[i] : proposed;
          expected.push(expectedValue); sampled.push(actual[i]); if (actual[i] !== input[i]) changed++;
          const full = actual[i], left = mask[i] ? masked[i] : inverted[i], right = mask[i] ? inverted[i] : masked[i];
          if (left !== full || right !== input[i]) maskExchange = false;
        }
        let seedDiff = false, rootSeedDiff = false; for (let i = 0; i < actual.length; i++) {
          if (actual[i] !== changedSeed[i]) seedDiff = true;
          if (actual[i] !== changedRoot[i]) rootSeedDiff = true;
        }
        const zeroSafe = TYPES.surface.fbmAt(1000, 1000, 10, seed, options, cellM);
        const zeroSafeExpected = fbm(1000, 1000, 10, seed, options, cellM);
        stylesReport[style] = { maxError: maxError(sampled, expected), samples: sampled.length, driverNonzero, changed,
          amountIdentity: zeroAmount === input, zeroMaskIdentity: zeroMask === input, maskExchange,
          deterministic: maxError(actual, repeat) === 0, seedDifference: ['contours', 'grid'].includes(style) ? true : seedDiff,
          rootSeedDifference: ['contours', 'grid'].includes(style) ? true : rootSeedDiff,
          octaves: TYPES.surface.fbmAt(1000, 1000, options.wavelengthM, seed, options, cellM).octaves,
          zeroSafe, zeroSafeExpected };
        stylesReport[style].ok = stylesReport[style].maxError <= gamma(64) * 2 && driverNonzero >= 32 && changed > 0
          && stylesReport[style].amountIdentity && stylesReport[style].zeroMaskIdentity && maskExchange
          && stylesReport[style].deterministic && stylesReport[style].seedDifference && stylesReport[style].rootSeedDifference
          && zeroSafe.octaves === zeroSafeExpected.octaves && zeroSafe.value === zeroSafeExpected.value;
      }
      runs.push({ lattice, resolution, seed: 7, samples: indices.length * styles.length, styles: stylesReport,
        ok: Object.values(stylesReport).every(style => style.ok) });
    }
    const median = values => { const sorted = [...values].sort((a, b) => a - b), middle = sorted.length >> 1;
      return sorted.length & 1 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2; };
    const wavelengthEstimate = (sample, extent) => {
      const size = 128, values = Array.from({ length: size }, (_, index) => sample(index));
      const mean = values.reduce((sum, value) => sum + value, 0) / size;
      const powers = new Float64Array(size / 2);
      for (let k = 1; k < size / 2; k++) { let real = 0, imaginary = 0;
        for (let index = 0; index < size; index++) { const window = .5 - .5 * Math.cos(2 * Math.PI * index / size);
          const value = (values[index] - mean) * window, angle = -2 * Math.PI * k * index / size;
          real += value * Math.cos(angle); imaginary += value * Math.sin(angle); }
        powers[k] = real * real + imaginary * imaginary;
      }
      let peak = 1; for (let k = 2; k < size / 2; k++) if (powers[k] > powers[peak]) peak = k;
      let offset = 0;
      if (peak > 1 && peak < size / 2 - 1) { const left = Math.log(Math.max(Number.MIN_VALUE, powers[peak - 1]));
        const center = Math.log(Math.max(Number.MIN_VALUE, powers[peak])); const right = Math.log(Math.max(Number.MIN_VALUE, powers[peak + 1]));
        const denominator = left - 2 * center + right; if (denominator !== 0) offset = .5 * (left - right) / denominator; }
      return extent / (peak + clamp(offset, -.5, .5));
    };
    const bisectWidth = (sample, upper) => { let low = 0, high = upper;
      for (let step = 0; step < 24; step++) { const middle = (low + high) / 2;
        if (sample(middle) > 0) low = middle; else high = middle; }
      return (low + high) / 2;
    };
    const scaleEstimators = { wavelength: [], cellular: [], grid: [], contours: [] };
    for (const resolution of [128, 256]) {
      RES = resolution; TARGET_RES = resolution; terrainDef.lattice = 'square'; const cellM = terrainDef.scale / resolution;
      const options = TYPES.surface.options({ style: 'roughen', wavelengthM: 700, octaves: 1, seed: 7 });
      const seed = effectiveSeed('roughen', options.seed, 23, 7), transects = [];
      for (const fraction of [.2, .4, .6, .8]) transects.push(wavelengthEstimate(index => {
        const worldX = (index + .5) * terrainDef.scale / 128, sampledX = mutation === 'spectral-cell-space' ? worldX * resolution / 128 : worldX;
        return TYPES.surface.patternAt(sampledX, fraction * terrainDef.scale, 0, options, seed, cellM).pattern;
      }, terrainDef.scale));
      scaleEstimators.wavelength.push({ resolution, estimate: median(transects), transects });
      const widthScale = mutation === 'width-double' ? 2 : 1;
      const cellularOptions = TYPES.surface.options({ style: 'bulbous', cellSpacingM: 500, bulbRadiusM: 40, seed: 7 });
      const cellularSeed = effectiveSeed('bulbous', cellularOptions.seed, 23, 7), cellularWidths = [];
      for (let index = 0; index < 16; index++) { const gx = 2 + index % 4, gy = 2 + Math.floor(index / 4);
        const featureX = (gx + hash01(gx, gy, cellularSeed)) * cellularOptions.cellSpacingM;
        const featureY = (gy + hash01(gx, gy, cellularSeed + 91)) * cellularOptions.cellSpacingM;
        cellularWidths.push(bisectWidth(distance => TYPES.surface.patternAt(featureX + distance * widthScale, featureY, 0, cellularOptions, cellularSeed, cellM).pattern, 80));
      }
      const gridOptions = TYPES.surface.options({ style: 'grid', spacingM: 250, lineWidthM: 20, angleDeg: 0 }), gridWidths = [];
      for (let index = 0; index < 16; index++) { const lineX = (index + 2) * gridOptions.spacingM, y = (index + .25) * gridOptions.spacingM;
        gridWidths.push(bisectWidth(distance => TYPES.surface.patternAt(lineX + distance * widthScale, y, 0, gridOptions, 0, cellM).pattern, 40));
      }
      const contourOptions = TYPES.surface.options({ style: 'contours', intervalM: 137, lineWidthM: 20 }), contourWidths = [];
      for (let index = 0; index < 16; index++) { const lineHeight = (index + 2) * contourOptions.intervalM;
        contourWidths.push(bisectWidth(distance => TYPES.surface.patternAt(0, 0, lineHeight + distance * widthScale, contourOptions, 0, cellM).pattern, 40));
      }
      const tolerance = Math.max(8 * 20 * 2 ** -23, terrainDef.scale / (128 * 1024));
      scaleEstimators.cellular.push({ resolution, estimate: median(cellularWidths), expected: 40,
        error: Math.abs(median(cellularWidths) - 40), samples: cellularWidths.length });
      scaleEstimators.grid.push({ resolution, estimate: median(gridWidths), expected: 20,
        error: Math.abs(median(gridWidths) - 20), samples: gridWidths.length });
      scaleEstimators.contours.push({ resolution, estimate: median(contourWidths), expected: 20,
        error: Math.abs(median(contourWidths) - 20), samples: contourWidths.length });
      scaleEstimators.tolerance = tolerance;
    }
    scaleEstimators.wavelengthDelta = Math.abs(scaleEstimators.wavelength[0].estimate - scaleEstimators.wavelength[1].estimate);
    scaleEstimators.ok = scaleEstimators.wavelength.every(item => item.transects.length === 4 && Number.isFinite(item.estimate) && item.estimate > 0)
      && scaleEstimators.wavelengthDelta <= terrainDef.scale / 128
      && ['cellular', 'grid', 'contours'].every(kind => scaleEstimators[kind].every(item => item.samples === 16 && item.error <= scaleEstimators.tolerance));
    terrainDef.lattice = 'square'; terrainDef.seed = 7; RES = 512; TARGET_RES = 512;
    const mutationReached = mutation ? !invalid.ok || runs.some(run => !run.ok) : false;
    const estimatorMutation = ['spectral-cell-space', 'width-double'].includes(mutation) && !scaleEstimators.ok;
    return { invalid, runs, scaleEstimators, mutation, mutationReached: mutationReached || estimatorMutation,
      ok: mutation ? false : invalid.ok && runs.every(run => run.ok) && scaleEstimators.ok,
      violatedFormula: mutation ? ({ 'roughen-drop-slope': 'Roughen slope driver', 'distress-invert-convex': 'Distress convex driver',
        'groundtexture-drop-wear': 'Ground Texture wear driver', 'rocknoise-use-fbm': 'Rock Noise ridge pattern',
        'bulbous-invert-cell': 'Bulbous cellular radius', 'pockmarks-positive': 'Pockmarks negative relief',
        'contours-cell-height': 'Contours metre elevation', 'grid-unrotated': 'Grid world rotation',
        'pre-mask': 'post-effect mask application', 'cell-space': 'world-metre pattern coordinates',
        'nyquist-force-one': 'zero-safe Nyquist octave truncation', 'hex-row-normalized': 'physical hex row pitch',
        'root-seed-zero': 'canonical root seed integration', 'spectral-cell-space': 'periodic-Hann DFT wavelength stability',
        'width-double': 'cellular/Grid/Contour 24-step width bisection', 'slope-endpoint': 'slope endpoint relation',
        'copycam-drop-fov': 'plan-view camera FOV restoration',
        'unfrozen-framebuffer': 'frozen 960x540 framebuffer',
        'flat-render': 'visual treatment pixel threshold' })[mutation] : null };
  }, { styles: STYLES, mutation: MUTATION });

  const inspectUi = async viewport => {
    await page.setViewportSize(viewport); await page.waitForTimeout(120);
    const result = await page.evaluate(styles => {
      buildIndex(); nodes.length = 0; edges.length = 0; uid = 1; selected = null; selectedEdge = null;
      const node = makeNode('surface', 0, 0), seen = new Set(); let geometry = true;
      for (const style of styles) { node.params.style = style; selected = node; buildProps();
        for (const field of document.querySelectorAll('#pBody .field[data-param-key]')) {
          seen.add(field.dataset.paramKey); const rect = field.getBoundingClientRect(), panel = document.querySelector('#props').getBoundingClientRect();
          geometry &&= rect.width > 0 && rect.left >= panel.left - 1 && rect.right <= panel.right + 1 && field.scrollWidth <= field.clientWidth + 2;
        }
      }
      return { toolbox: !!document.querySelector('.node-tool-item[data-type="surface"]'),
        category: document.querySelector('.node-tool-item[data-type="surface"]')?.closest('.node-tool-cat')?.querySelector('.node-tool-cat-title')?.textContent,
        keys: [...seen], expected: TYPES.surface.params.map(param => param.key), geometry };
    }, STYLES);
    await page.evaluate(() => { nodes.length = 0; edges.length = 0; selected = null; selectedEdge = null; drawGraph(); });
    const graphBox = await page.locator('#graph').boundingBox();
    await page.locator('#graph').dispatchEvent('dblclick', {
      clientX: graphBox.x + Math.max(8, graphBox.width * .75), clientY: graphBox.y + Math.max(8, graphBox.height * .75) });
    await page.locator('#menu .menu-search').fill('Surface Detail');
    result.quickCreate = await page.locator('#menu .menu-item[data-type="surface"]').count() === 1;
    await page.keyboard.press('Escape');
    return result;
  };
  const ui = { desktop: await inspectUi({ width: 1440, height: 900 }), mobile: await inspectUi({ width: 390, height: 844 }) };
  ui.ok = Object.values(ui).filter(value => typeof value === 'object').every(result => result.toolbox
    && result.category === 'Surface / Geology' && result.geometry && result.quickCreate
    && result.expected.every(key => result.keys.includes(key)));

  // Absence of evidence is failure: when a capture was requested, an EMPTY run set is red. This
  // initialised to ok:true and stayed so whenever the capture block did not execute, which is how
  // the 45-degree visual matrix was satisfied by capturing nothing in every automated run.
  const visual = { runs: [], ok: !VISUAL };
  if (VISUAL) {
    const evidenceDir = path.resolve(__dirname, '../../.sweep-logs/MC-S03'); mkdirSync(evidenceDir, { recursive: true });
    await page.setViewportSize({ width: 1440, height: 900 });
    const visualLattices = VISUAL_LATTICE ? [VISUAL_LATTICE] : ['square', 'hex'];
    const visualStyles = VISUAL_STYLE ? [VISUAL_STYLE] : STYLES;
    const visualViews = VISUAL_VIEW ? [[VISUAL_VIEW, VISUAL_VIEW === 'traversal' ? 2.88 : 1.04]] : [['traversal', 2.88], ['close', 1.04]];
    for (const lattice of visualLattices) for (const style of visualStyles) for (const view of visualViews) {
      const result = await page.evaluate(({ lattice, style, distance, flat }) => {
        RES = 256; TARGET_RES = 256; terrainDef.lattice = lattice; terrainDef.scale = 5000; terrainDef.height = 2600;
        buildIndex(); const n = fieldW(), nh = fieldH(), input = newField();
        for (let y = 0; y < nh; y++) for (let x = 0; x < n; x++) { const dx = (x + .5) / n - .5, dy = (y + .5) / nh - .5;
          input[y * n + x] = .2 + .55 * Math.max(0, 1 - 2.2 * Math.hypot(dx, dy) ** 2); }
        const params = Object.fromEntries(TYPES.surface.params.map(param => [param.key, cloneParams(param.def)]));
        Object.assign(params, { style, amountM: 180, angleDeg: 37, lineWidthM: 24 });
        const node = { id: 23, type: 'surface', params }, baseline = TYPES.surface.eval({ ...params, amountM: 0 }, [input, null], node);
        const treatment = flat ? baseline : TYPES.surface.eval(params, [input, null], node);
        const capture = field => { const root = { id: 24, type: 'output', params: { norm: 'off' }, _field: field };
          updateViewport(field, root); cam = { az: -35 * Math.PI / 180, el: 42 * Math.PI / 180,
          dist: distance, target: [0, 0, 0], fov: 45 * Math.PI / 180 }; shadeMode = 1; syncDisplayState(); const canvas = document.querySelector('#gl');
          if (flat !== 'unfrozen-framebuffer') canvas.parentElement.getBoundingClientRect = () => ({ width: 960 / 1.35, height: 540 / 1.35,
            left: 0, top: 0, right: 960 / 1.35, bottom: 540 / 1.35 });
          renderGL(); const renderedFov = renderGL(); gl.finish(); const pixels = new Uint8Array(960 * 540 * 4);
          gl.readPixels(0, 0, 960, 540, gl.RGBA, gl.UNSIGNED_BYTE, pixels); return { pixels, png: canvas.toDataURL('image/png'), fovDeg: renderedFov * 180 / Math.PI,
            canvasWidth: canvas.width, canvasHeight: canvas.height, drawingWidth: gl.drawingBufferWidth, drawingHeight: gl.drawingBufferHeight, deviceScale: devicePixelRatio }; };
        const baselineCapture = capture(baseline), treatmentCapture = capture(treatment), before = baselineCapture.pixels, after = treatmentCapture.pixels;
        const clear = [before[0], before[1], before[2]], width = 960, height = 540;
        const terrain = new Uint8Array(width * height), stack = [Math.floor(height / 2) * width + Math.floor(width / 2)]; let count = 0, changed = 0;
        while (stack.length) { const index = stack.pop(); if (index < 0 || index >= terrain.length || terrain[index]) continue;
          const pixel = index * 4, nonClear = Math.abs(before[pixel] - clear[0]) >= 2 || Math.abs(before[pixel + 1] - clear[1]) >= 2 || Math.abs(before[pixel + 2] - clear[2]) >= 2;
          if (!nonClear) continue; terrain[index] = 1; count++;
          if (Math.abs(before[pixel] - after[pixel]) >= 2 || Math.abs(before[pixel + 1] - after[pixel + 1]) >= 2 || Math.abs(before[pixel + 2] - after[pixel + 2]) >= 2) changed++;
          const x = index % width; if (x) stack.push(index - 1); if (x < width - 1) stack.push(index + 1);
          if (index >= width) stack.push(index - width); if (index < width * (height - 1)) stack.push(index + width);
        }
        return { lattice, style, distance, terrainPixels: count, changedPixels: changed, changedFraction: count ? changed / count : 0,
            channelsValid: after.every(value => Number.isInteger(value) && value >= 0 && value <= 255), fovDeg: treatmentCapture.fovDeg,
            framebuffer: [treatmentCapture.canvasWidth, treatmentCapture.canvasHeight, treatmentCapture.drawingWidth, treatmentCapture.drawingHeight],
            deviceScale: treatmentCapture.deviceScale, png: treatmentCapture.png };
          }, { lattice, style, distance: view[1], flat: MUTATION === 'flat-render' ? true : MUTATION === 'unfrozen-framebuffer' ? 'unfrozen-framebuffer' : false });
      result.view = view[0]; result.ok = result.terrainPixels >= 10000 && result.changedFraction >= .01 && result.channelsValid && Math.abs(result.fovDeg - 45) < 1e-9;
          result.ok &&= result.deviceScale === 1 && result.framebuffer.every((value, index) => value === (index % 2 ? 540 : 960));
      visual.runs.push(result); visual.ok &&= result.ok;
      if (MUTATION !== 'flat-render') {
        writeFileSync(path.join(evidenceDir, `surface-${style}-${lattice}-${view[0]}.png`), Buffer.from(result.png.split(',')[1], 'base64'));
      }
      delete result.png;
    }
  }
  if (MUTATION === 'flat-render' || MUTATION === 'unfrozen-framebuffer') analytic.mutationReached = VISUAL && !visual.ok;
  if (MUTATION === 'copycam-drop-fov') analytic.mutationReached = !lifecycle.camera.ok;

  const manifestOk = measured.manifest && Object.values(measured.manifest).every(Boolean);
  const ok = measured.registered && measured.category === 'surface'
    && JSON.stringify(measured.inputs) === JSON.stringify(['In', 'Mask'])
    && JSON.stringify(measured.styles) === JSON.stringify(STYLES)
    && measured.styleDefault === 'roughen' && manifestOk && measured.copyHonest && lifecycle.ok && analytic.ok && ui.ok && visual.ok && !errors.length;
  console.log(`surface lifecycle ${JSON.stringify(lifecycle)}`);
  console.log(`surface registration registered=${measured.registered} styles=${measured.styles?.length || 0} manifest=${manifestOk ? 'pass' : 'fail'} latticeRuns=${analytic.runs.length} samples=${analytic.runs.reduce((sum, run) => sum + run.samples, 0)} mutationReached=${analytic.mutationReached}`);
  // The gates, NAMED, in the shape scripts/gate.py scores — without a failed=[...] line the runner
  // cannot tell a red-because-a-gate-broke from a red-for-any-other-reason.
  const namedGates = { registration: measured.registered === true, manifest: manifestOk,
    invalid: analytic.invalid.ok, runs: analytic.runs.every(run => run.ok),
    scaleEstimators: analytic.scaleEstimators.ok, ui: ui.ok, lifecycle: lifecycle.ok, visual: visual.ok };
  console.log(`surface failed=[${Object.entries(namedGates).filter(([, v]) => !v).map(([k]) => k).join(',')}] mutation=${analytic.mutation || 'none'}`);

  // ASSERT mutationReached. `ok` is forced false under ANY mutation, so a mutated run exited 1
  // whether or not the mutation broke anything — exit status carried no information about whether
  // the control works. Now a mutated run that leaves every gate green says so, and gate.py reads it.
  if (analytic.mutation && !analytic.mutationReached) {
    console.error(`FAIL mutation ${analytic.mutation} was not detected — that control is vacuous`);
  }
  if (analytic.mutation) console.log(`MUTATION ${analytic.mutation} violated ${analytic.violatedFormula}`);
  if (!SUMMARY) console.log(JSON.stringify({ lifecycle, measured, analytic, ui, visual, errors, ok }, null, 2));
  else if (VISUAL) console.log(`visual runs=${visual.runs.length} minTerrain=${Math.min(...visual.runs.map(run => run.terrainPixels))} minChanged=${Math.min(...visual.runs.map(run => run.changedFraction))} fov=${Math.min(...visual.runs.map(run => run.fovDeg))}`);
  const cleanupBudget = new Promise(resolve => setTimeout(resolve, 2000));
  await Promise.race([page.close({ runBeforeUnload: false }).catch(() => {}), cleanupBudget]);
  await Promise.race([browser.close().catch(() => {}), cleanupBudget]);
  process.exit(ok ? 0 : 1);
})().catch(error => { console.error('FATAL', error); process.exit(2); });