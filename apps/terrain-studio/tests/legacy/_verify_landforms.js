const { chromium } = await import('playwright-core');
const path = (await import('node:path')).default;
const { mkdirSync, writeFileSync } = await import('node:fs');
const __dirname = path.dirname(path.resolve(process.argv[1]));
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));
const VISUAL = process.argv.includes('--visual');
const SUMMARY = process.argv.includes('--summary');
const flagValue = name => process.argv.find(argument => argument.startsWith(`--${name}=`))?.split('=')[1];
const VISUAL_TYPE = flagValue('visual-type');
const VISUAL_LATTICE = flagValue('visual-lattice');
const VISUAL_VIEW = flagValue('visual-view');
const mutationArg = process.argv.find(argument => argument.startsWith('--mutate='));
const MUTATION = mutationArg ? mutationArg.slice(9) : null;
const MUTATIONS = ['crater-ejecta-r2', 'craterfield-grid-jitter', 'island-circular-envelope',
  'volcano-drop-summit', 'mountainside-invert-halfplane', 'rugged-sum-blocks', 'silent-underfill', 'flat-render'];
if (MUTATION && !MUTATIONS.includes(MUTATION)) {
  console.error(`Unknown mutation ${MUTATION}`); process.exit(2);
}

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(900);

  const report = await page.evaluate(async mutation => {
    const TYPES_ = ['crater', 'craterfield', 'island', 'volcano', 'mountainside', 'rugged'];
    const defaults = type => Object.fromEntries(TYPES[type].params.map(param => [param.key, cloneParams(param.def)]));
    const gamma = n => (n * 2 ** -24) / (1 - n * 2 ** -24);
    const mix32 = value => { let h = value >>> 0; h = Math.imul(h ^ (h >>> 16), 0x7feb352d) >>> 0;
      h = Math.imul(h ^ (h >>> 15), 0x846ca68b) >>> 0; return (h ^ (h >>> 16)) >>> 0; };
    const hashText = text => { let h = 2166136261 >>> 0; for (let i = 0; i < text.length; i++) {
      h ^= text.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return h; };
    const seedFor = (type, seed, nodeId = 0) => mix32((seed + hashText(type)
      + Math.imul(nodeId, 0x9e3779b1)) >>> 0);
    const randomStream = seed => { let state = mix32(seed); return () => {
      state = (Math.imul(state ^ (state >>> 15), 2246822519) + 374761393) >>> 0;
      return state / 4294967296; }; };
    const smoothstep = (a, b, value) => { const t = clamp((value - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
    const fbm = (x, y, wavelength, seed, options, cellM) => {
      let count = 0;
      for (let k = 0; k < options.octaves; k++) {
        if (wavelength / options.lacunarity ** k < 2 * cellM) break; count++;
      }
      count = Math.max(1, count); let sum = 0, total = 0, weight = 1;
      for (let k = 0; k < count; k++) { const frequency = options.lacunarity ** k / wavelength;
        sum += weight * gnoise(x * frequency, y * frequency, (seed + 7 * k) >>> 0);
        total += weight; weight *= options.gain; }
      return 2 * sum / total - 1;
    };
    const world = (x, y, n, nh, lattice) => [(x + .5 + (lattice === 'hex' ? .5 * (y & 1) : 0)) / n * terrainDef.scale,
      (y + .5) / nh * terrainDef.scale];
    const maxError = (actual, expected) => { let error = 0, changed = 0;
      for (let i = 0; i < actual.length; i++) { error = Math.max(error, Math.abs(actual[i] - expected[i]));
        if (actual[i] !== expected[i]) changed++; } return { error, changed }; };

    const registration = { count: TYPES_.filter(type => !!TYPES[type]).length,
      categories: Object.fromEntries(TYPES_.map(type => [type, TYPES[type]?.cat])),
      exact: Object.fromEntries(TYPES_.map(type => [type, EXACT_TYPES.has(type)])),
      copyHonest: TYPES_.every(type => !/(gaea.{0,24}(same|exact|internal|parity)|proprietary)/i
        .test(`${TYPES[type]?.desc || ''} ${TYPES[type]?.note || ''}`)) };
    registration.ok = registration.count === 6 && Object.values(registration.categories).every(category => category === 'gen')
      && registration.exact.crater && registration.exact.island && registration.exact.volcano
      && !registration.exact.craterfield && !registration.exact.mountainside && !registration.exact.rugged
      && registration.copyHonest;

    const invalid = {};
    for (const type of TYPES_) {
      const def = TYPES[type], base = defaults(type), checks = [];
      for (const param of def.params) {
        if (!Number.isFinite(param.min) || !Number.isFinite(param.max)) continue;
        for (const value of [param.min - Math.max(1, Math.abs(param.min)), param.max + Math.max(1, Math.abs(param.max)), NaN, Infinity, -Infinity]) {
          try { const result = def.options({ ...base, [param.key]: value }); checks.push(Object.values(result).every(item => {
            if (typeof item === 'number') return Number.isFinite(item); return true; })); }
          catch (_) { checks.push(false); }
        }
      }
      invalid[type] = checks.length > 0 && checks.every(Boolean);
    }
    let unknownEnum = false, badCurve = false;
    try { TYPES.volcano.options({ ...defaults('volcano'), style: 'shield' }); } catch (error) { unknownEnum = /unknown/i.test(error.message); }
    try { TYPES.mountainside.options({ ...defaults('mountainside'), skirt: [[0, 1], [.5, NaN], [1, 0]] }); }
    catch (error) { badCurve = /finite, monotone/i.test(error.message); }
    invalid.enums = unknownEnum; invalid.curve = badCurve; invalid.ok = Object.values(invalid).every(Boolean);

    const craterParams = defaults('crater'), craterOracle = radius => {
      const D = craterParams.diameterM, R = D / 2, u = radius / R, Dc = 3200 * (9.81 / craterParams.gravity);
      const depth = D < Dc ? .2 * D : .2 * Dc * (D / Dc) ** .3;
      const bowl = u < 1 ? -depth * (1 - u * u) : 0, amplitude = 3 * craterParams.depositFraction * depth / 8;
      const power = mutation === 'crater-ejecta-r2' ? -2 : -3;
      const ejecta = u >= 1 && u <= 3 ? amplitude * u ** power : 0;
      const uplift = D >= Dc ? .5 * depth * Math.exp(-((u / .18) ** 2)) : 0;
      return craterParams.amount * (bowl + ejecta + uplift);
    };
    const craterRadii = Array.from({ length: 64 }, (_, index) => index / 63 * craterParams.diameterM * 1.75);
    const craterActual = craterRadii.map(radius => TYPES.crater.profile(radius, TYPES.crater.options(craterParams)));
    const craterExpected = craterRadii.map(craterOracle), craterCompare = maxError(craterActual, craterExpected);
    const R = craterParams.diameterM / 2;
    const crater = { maxError: craterCompare.error, samples: craterRadii.length, floor: craterOracle(0) < 0,
      rim: craterOracle(R) > 0, outside: craterOracle(3 * R + 1) === 0,
      ejectaSlope: Math.abs((Math.log(craterOracle(2 * R)) - Math.log(craterOracle(1.25 * R)))
        / (Math.log(2) - Math.log(1.25)) + 3) < 1e-10,
      amountZero: TYPES.crater.profile(0, TYPES.crater.options({ ...craterParams, amount: 0 })) === 0 };
    crater.ok = crater.maxError <= gamma(32) * Math.max(...craterExpected.map(Math.abs), 1)
      && crater.floor && crater.rim && crater.outside && crater.ejectaSlope && crater.amountZero;

    const placementCheck = (def, feasible, impossible) => {
      let first = def.planPlacement(feasible, 17, 0), again = def.planPlacement(feasible, 17, 0);
      const changed = def.planPlacement({ ...feasible, seed: feasible.seed + 1 }, 17, 0);
      if (mutation === 'craterfield-grid-jitter' && def === TYPES.craterfield) {
        first = { ...first, points: first.points.map((point, index) => index === 1
          ? { x: first.points[0].x + feasible.minSpacingM / 2, y: first.points[0].y }
          : point) };
      }
      const epsilon = gamma(6), pairs = [];
      for (let i = 0; i < first.points.length; i++) for (let j = i + 1; j < first.points.length; j++) {
        const dx = first.points[i].x - first.points[j].x, dy = first.points[i].y - first.points[j].y;
        pairs.push(Math.hypot(dx, dy) + epsilon * (Math.abs(dx) + Math.abs(dy) + first.minSpacingM) >= first.minSpacingM);
      }
      let saturated = def.planPlacement(impossible, 17, 0);
      if (mutation === 'silent-underfill' && def === TYPES.craterfield) saturated = { ...saturated, saturated: false };
      return { requested: first.placed === first.requested && !first.saturated,
        spacing: pairs.length > 0 && pairs.every(Boolean), pairCount: pairs.length,
        identity: JSON.stringify(first.points) === JSON.stringify(again.points),
        seedDifference: JSON.stringify(first.points) !== JSON.stringify(changed.points),
        saturation: saturated.saturated && saturated.placed < saturated.requested && saturated.points.length === saturated.placed };
    };
    const placement = {
      craterfield: placementCheck(TYPES.craterfield, { ...defaults('craterfield'), count: 24, minSpacingM: 400 },
        { ...defaults('craterfield'), count: 512, minSpacingM: 5000 }),
      rugged: placementCheck(TYPES.rugged, { ...defaults('rugged'), blockCount: 24, minSpacingM: 400 },
        { ...defaults('rugged'), blockCount: 512, minSpacingM: 5000 }) };
    placement.ok = Object.values(placement.craterfield).every(Boolean) && Object.values(placement.rugged).every(Boolean);

    const lattices = [];
    for (const lattice of ['square', 'hex']) for (const resolution of [128, 256]) {
      RES = resolution; TARGET_RES = resolution; terrainDef.lattice = lattice; terrainDef.scale = 5000; terrainDef.height = 2600; XF = null;
      const nh = fieldH(), cellM = terrainDef.scale / resolution, indices = [];
      for (let iy = 1; iy <= 8; iy++) for (let ix = 1; ix <= 8; ix++) indices.push([
        Math.floor(ix * resolution / 10), Math.floor(iy * nh / 10)]);

      const islandParams = { ...defaults('island'), radiusXM: 1200, radiusYM: 650, angleDeg: 27, warpM: 0, roughnessM: 0 };
      const islandField = TYPES.island.eval(islandParams, [], { id: 0 }), islandOptions = TYPES.island.options(islandParams), islandSeed = seedFor('island', 7);
      const islandExpected = [], islandActual = [];
      for (const index of indices) { const point = world(index[0], index[1], resolution, nh, lattice), dx = point[0] - 2500, dy = point[1] - 2500;
        const a = islandOptions.angleDeg * Math.PI / 180, qx = (dx * Math.cos(a) - dy * Math.sin(a)) / islandOptions.radiusXM;
        const divisorY = mutation === 'island-circular-envelope' ? islandOptions.radiusXM : islandOptions.radiusYM;
        const qy = (dx * Math.sin(a) + dy * Math.cos(a)) / divisorY, minimum = Math.min(islandOptions.radiusXM, islandOptions.radiusYM);
        const envelope = 1 - smoothstep(1 - islandOptions.coastWidthM / minimum, 1, Math.hypot(qx, qy));
        islandExpected.push(Math.fround(Math.max(0, envelope * islandOptions.elevationM) / terrainDef.height));
        islandActual.push(islandField[index[1] * resolution + index[0]]); }

      const volcanoParams = { ...defaults('volcano'), barrancoDepth: 0 }, volcanoOptions = TYPES.volcano.options(volcanoParams);
      const volcanoField = TYPES.volcano.eval(volcanoParams, [], { id: 0 }), volcanoExpected = [], volcanoActual = [];
      for (const index of indices) { const point = world(index[0], index[1], resolution, nh, lattice), dx = point[0] - 2500, dy = point[1] - 2500;
        const radius = Math.hypot(dx, dy), rn = radius / volcanoOptions.radiusM;
        const base = rn <= 1 ? Math.max(0, (1 - rn) ** volcanoOptions.profileExponent) : 0;
        const edifice = volcanoOptions.heightM * base, craterRho = radius / volcanoOptions.craterRadiusM;
        const summit = mutation === 'volcano-drop-summit' ? 0 : (craterRho < 1 ? -volcanoOptions.craterDepthM * (1 - craterRho ** 2) ** 1.5 : 0);
        const rim = volcanoOptions.rimHeightM * Math.exp(-.5 * ((radius - volcanoOptions.craterRadiusM) / volcanoOptions.rimWidthM) ** 2);
        volcanoExpected.push(Math.fround(Math.max(0, edifice + summit + rim) / terrainDef.height));
        volcanoActual.push(volcanoField[index[1] * resolution + index[0]]); }

      const sideParams = { ...defaults('mountainside'), weather: 0 }, sideOptions = TYPES.mountainside.options(sideParams);
      sideOptions.seed = seedFor('mountainside', sideOptions.seed);
      const sideField = TYPES.mountainside.eval(sideParams, [], { id: 0 }), mountain = TYPES.mountain.eval(sideOptions, [], { id: 0 }), sideExpected = [], sideActual = [];
      const bearing = sideOptions.bearingDeg * Math.PI / 180;
      for (const index of indices) { const point = world(index[0], index[1], resolution, nh, lattice);
        const t = (point[0] - 2500) * Math.cos(bearing) + (point[1] - 2500) * Math.sin(bearing);
        let gate = smoothstep(-sideOptions.featherM, sideOptions.featherM, t); if (mutation === 'mountainside-invert-halfplane') gate = 1 - gate;
        sideExpected.push(Math.fround(mountain[index[1] * resolution + index[0]] * gate)); sideActual.push(sideField[index[1] * resolution + index[0]]); }

      const ruggedParams = { ...defaults('rugged'), blockCount: 8, minSpacingM: 100, blockRadiusM: 500, blockVariation: 0, macroReliefM: 0, baseElevationM: 120 };
      const ruggedOptions = TYPES.rugged.options(ruggedParams), ruggedSeed = seedFor('rugged', 7), ruggedPlan = TYPES.rugged.planPlacement(ruggedParams, 0, 0);
      const ruggedField = TYPES.rugged.eval(ruggedParams, [], { id: 0 }), ruggedExpected = [], ruggedActual = [];
      for (const index of indices) { const point = world(index[0], index[1], resolution, nh, lattice), contributions = [];
        for (let blockIndex = 0; blockIndex < ruggedPlan.points.length; blockIndex++) { const block = ruggedPlan.points[blockIndex], distance = Math.hypot(point[0] - block.x, point[1] - block.y) / ruggedOptions.blockRadiusM;
          if (distance < 1) contributions.push(ruggedOptions.blockHeightM * (1 - distance) ** ruggedOptions.blockExponent
            * (1 + ruggedOptions.blockNoise * fbm(point[0], point[1], ruggedOptions.blockWavelengthM, ruggedSeed + 4099 * blockIndex, ruggedOptions, cellM))); }
        const blocks = mutation === 'rugged-sum-blocks' ? contributions.reduce((sum, value) => sum + value, 0) : Math.max(0, ...contributions);
        ruggedExpected.push(Math.fround((ruggedOptions.baseElevationM + blocks) / terrainDef.height)); ruggedActual.push(ruggedField[index[1] * resolution + index[0]]); }

      const comparisons = { island: maxError(islandActual, islandExpected), volcano: maxError(volcanoActual, volcanoExpected),
        mountainside: maxError(sideActual, sideExpected), rugged: maxError(ruggedActual, ruggedExpected) };
      const tolerance = gamma(64) * 2;
      lattices.push({ lattice, resolution, seed: 7, samples: indices.length, comparisons,
        positive: { island: islandField.some(value => value > 0), volcano: volcanoField.some(value => value > 0),
          mountainside: sideField.some(value => value > 0), rugged: ruggedField.some(value => value > 0) },
        zero: { island: islandField.some(value => value === 0), volcano: volcanoField.some(value => value === 0),
          mountainside: sideField.some(value => value === 0), rugged: ruggedField.every(value => value >= 0) },
        ok: Object.values(comparisons).every(value => value.error <= tolerance) });
    }
    terrainDef.lattice = 'square'; RES = 128; TARGET_RES = 128;
    const transformMatrix = xfFromParams({ scale: 1.17, aspect: .83, angle: 23, offX: .071, offY: -.043, pivX: .41, pivY: .63 });
    const transformed = {};
    for (const type of ['crater', 'island', 'volcano']) {
      const params = defaults(type), options = TYPES[type].options(params), node = { id: 0 }, previous = XF; XF = transformMatrix;
      const field = TYPES[type].eval(params, [], node); XF = previous; const actual = [], expected = [], seed = seedFor(type, params.seed || 0);
      for (let iy = 1; iy <= 8; iy++) for (let ix = 1; ix <= 8; ix++) { const x = Math.floor(ix * RES / 10), y = Math.floor(iy * RES / 10);
        const u = (x + .5) / RES, v = (y + .5) / RES, worldX = (transformMatrix[0] * u + transformMatrix[1] * v + transformMatrix[2]) * terrainDef.scale;
        const worldY = (transformMatrix[3] * u + transformMatrix[4] * v + transformMatrix[5]) * terrainDef.scale;
        let metres = type === 'crater' ? TYPES.crater.profile(Math.hypot(worldX - options.x * terrainDef.scale, worldY - options.y * terrainDef.scale), options)
          : TYPES[type].profile(worldX, worldY, options, seed, terrainDef.scale / RES);
        actual.push(field[y * RES + x]); expected.push(Math.fround(metres / terrainDef.height)); }
      const comparison = maxError(actual, expected); transformed[type] = { samples: actual.length, maxError: comparison.error, ok: comparison.error === 0 };
    }
    transformed.rasterExcluded = ['craterfield', 'mountainside', 'rugged'].every(type => !EXACT_TYPES.has(type));
    transformed.ok = transformed.crater.ok && transformed.island.ok && transformed.volcano.ok && transformed.rasterExcluded;
    terrainDef.lattice = 'square'; RES = 512; TARGET_RES = 512;
    const mutationReached = mutation ? ({
      'crater-ejecta-r2': !crater.ok, 'craterfield-grid-jitter': !placement.craterfield.spacing,
      'island-circular-envelope': lattices.some(item => !item.ok), 'volcano-drop-summit': lattices.some(item => !item.ok),
      'mountainside-invert-halfplane': lattices.some(item => !item.ok), 'rugged-sum-blocks': lattices.some(item => !item.ok),
      'silent-underfill': !placement.craterfield.saturation }[mutation]) : false;
    const normalOk = registration.ok && invalid.ok && crater.ok && placement.ok && transformed.ok && lattices.every(item => item.ok)
      && lattices.every(item => Object.values(item.positive).every(Boolean) && Object.values(item.zero).every(Boolean));
    return { registration, invalid, crater, placement, transformed, lattices, mutation, mutationReached,
      violatedFormula: mutation ? ({ 'crater-ejecta-r2': 'Crater ejecta u^-3', 'craterfield-grid-jitter': 'Bridson pairwise spacing',
        'island-circular-envelope': 'Island elliptical envelope', 'volcano-drop-summit': 'Volcano summit depression',
        'mountainside-invert-halfplane': 'MountainSide M*G half-plane', 'rugged-sum-blocks': 'Rugged base+max(block)',
        'silent-underfill': 'Poisson saturation status' })[mutation] : null,
      ok: mutation ? false : normalOk };
  }, MUTATION);

  const inspectUi = async viewport => {
    await page.setViewportSize(viewport); await page.waitForTimeout(120);
    const result = await page.evaluate(types => {
      buildIndex(); nodes.length = 0; edges.length = 0; uid = 1; selected = null; selectedEdge = null;
      const measured = {};
      for (const type of types) { const node = makeNode(type, 0, 0), keys = new Set(); let geometry = true;
        const variants = type === 'mountainside' ? [{ form: 'peak' }, { form: 'massif' }] : [{}];
        for (const variant of variants) { Object.assign(node.params, variant); selected = node; buildProps();
          const panel = document.querySelector('#props').getBoundingClientRect(), fields = [...document.querySelectorAll('#pBody .field[data-param-key]')];
          for (const field of fields) { keys.add(field.dataset.paramKey); const rect = field.getBoundingClientRect();
            geometry &&= rect.width > 0 && rect.left >= panel.left - 1 && rect.right <= panel.right + 1 && field.scrollWidth <= field.clientWidth + 2; }
        }
        measured[type] = { name: TYPES[type].name, toolbox: !!document.querySelector(`.node-tool-item[data-type="${type}"]`), keys: [...keys],
          expected: TYPES[type].params.map(param => param.key), geometry };
      }
      return measured;
    }, ['crater', 'craterfield', 'island', 'volcano', 'mountainside', 'rugged']);
    await page.evaluate(() => { nodes.length = 0; edges.length = 0; selected = null; selectedEdge = null; drawGraph(); });
    const graphBox = await page.locator('#graph').boundingBox();
    for (const type of Object.keys(result)) {
      await page.locator('#graph').dblclick({ position: { x: Math.max(8, graphBox.width * .75), y: Math.max(8, graphBox.height * .75) } });
      await page.locator('#menu .menu-search').fill(result[type].name);
      result[type].quickCreate = await page.locator(`#menu .menu-item[data-type="${type}"]`).count() === 1;
      await page.keyboard.press('Escape');
    }
    return result;
  };
  report.ui = { desktop: await inspectUi({ width: 1440, height: 900 }), mobile: await inspectUi({ width: 390, height: 844 }) };
  report.ui.ok = Object.values(report.ui).filter(value => typeof value === 'object').every(view => Object.values(view).every(result => result.toolbox && result.quickCreate
    && result.geometry && result.expected.every(key => result.keys.includes(key))));
  report.ok = report.ok && report.ui.ok;

  report.visual = { runs: [], ok: true };
  if (VISUAL) {
    const evidenceDir = path.resolve(__dirname, '../../.sweep-logs/MC-S03'); mkdirSync(evidenceDir, { recursive: true });
    await page.setViewportSize({ width: 1440, height: 900 });
    const visualLattices = VISUAL_LATTICE ? [VISUAL_LATTICE] : ['square', 'hex'];
    const visualTypes = VISUAL_TYPE ? [VISUAL_TYPE] : ['crater', 'craterfield', 'island', 'volcano', 'mountainside', 'rugged'];
    const visualViews = VISUAL_VIEW ? [[VISUAL_VIEW, VISUAL_VIEW === 'traversal' ? 2.88 : 1.04]] : [['traversal', 2.88], ['close', 1.04]];
    for (const lattice of visualLattices) for (const type of visualTypes) for (const view of visualViews) {
        const result = await page.evaluate(({ lattice, type, distance, flat }) => {
          RES = 256; TARGET_RES = 256; terrainDef.lattice = lattice; terrainDef.scale = 5000; terrainDef.height = 2600; buildIndex();
          const params = Object.fromEntries(TYPES[type].params.map(param => [param.key, cloneParams(param.def)])), node = { id: 23, type, params };
          if ('amount' in params) params.amount = 1.7;
          const baseline = newField(.12), generated = TYPES[type].eval(params, [], node), treatment = flat ? baseline : new Float32Array(generated.length);
          if (!flat) for (let i = 0; i < generated.length; i++) treatment[i] = Math.fround(baseline[i] + generated[i]);
          const capture = field => { const root = { id: 24, type: 'output', params: { norm: 'off' }, _field: field };
            updateViewport(field, root); cam = { az: -35 * Math.PI / 180, el: 42 * Math.PI / 180, dist: distance, target: [0, 0, 0], fov: 45 * Math.PI / 180 };
            shadeMode = 1; syncDisplayState(); const canvas = document.querySelector('#gl'); canvas.width = 960; canvas.height = 540;
            gl.viewport(0, 0, 960, 540); const renderedFov = renderGL(); gl.finish(); const pixels = new Uint8Array(960 * 540 * 4);
            gl.readPixels(0, 0, 960, 540, gl.RGBA, gl.UNSIGNED_BYTE, pixels); return { pixels, png: canvas.toDataURL('image/png'), fovDeg: renderedFov * 180 / Math.PI }; };
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
          return { lattice, type, distance, terrainPixels: count, changedPixels: changed, changedFraction: count ? changed / count : 0,
            channelsValid: after.every(value => Number.isInteger(value) && value >= 0 && value <= 255), fovDeg: treatmentCapture.fovDeg, png: treatmentCapture.png };
        }, { lattice, type, distance: view[1], flat: MUTATION === 'flat-render' });
        result.view = view[0]; result.ok = result.terrainPixels >= 10000 && result.changedFraction >= .01 && result.channelsValid && Math.abs(result.fovDeg - 45) < 1e-9;
        report.visual.runs.push(result); report.visual.ok &&= result.ok;
        if (MUTATION !== 'flat-render') writeFileSync(path.join(evidenceDir, `landform-${type}-${lattice}-${view[0]}.png`), Buffer.from(result.png.split(',')[1], 'base64'));
        delete result.png;
      }
  }
  if (MUTATION === 'flat-render') { report.mutationReached = VISUAL && !report.visual.ok;
    report.violatedFormula = 'visual treatment pixel threshold'; report.ok = false; }
  else report.ok = report.ok && report.visual.ok;

  console.log(`landforms latticeRuns=${report.lattices.length} samples=${report.lattices.reduce((sum, item) => sum + item.samples, 0)} seed=7 mutationReached=${report.mutationReached}`);
  if (report.mutation) console.log(`MUTATION ${report.mutation} violated ${report.violatedFormula}`);
  if (!SUMMARY) console.log(JSON.stringify({ ...report, errors }, null, 2));
  else if (VISUAL) console.log(`visual runs=${report.visual.runs.length} minTerrain=${Math.min(...report.visual.runs.map(run => run.terrainPixels))} minChanged=${Math.min(...report.visual.runs.map(run => run.changedFraction))} fov=${Math.min(...report.visual.runs.map(run => run.fovDeg))}`);
  await browser.close();
  process.exit(report.ok && !errors.length ? 0 : 1);
})().catch(error => { console.error('FATAL', error); process.exit(2); });