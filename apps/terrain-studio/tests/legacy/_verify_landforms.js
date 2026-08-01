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
const VISUAL_STYLE = flagValue('visual-style');
const VISUAL_LATTICE = flagValue('visual-lattice');
const VISUAL_VIEW = flagValue('visual-view');
const mutationArg = process.argv.find(argument => argument.startsWith('--mutate='));
const MUTATION = mutationArg ? mutationArg.slice(9) : null;
const MUTATIONS = ['crater-ejecta-r2', 'craterfield-grid-jitter', 'island-circular-envelope',
  'volcano-alias-styles', 'volcano-straight-cone', 'volcano-gaussian-cone', 'volcano-drop-summit',
  'volcano-swap-style-defaults', 'mountainside-invert-halfplane', 'rugged-sum-blocks', 'silent-underfill',
  'nyquist-force-one', 'hex-row-normalized', 'root-seed-zero', 'volcano-no-barrancos',
  'unfrozen-framebuffer', 'flat-render'];
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

  const lifecycle = await page.evaluate(() => {
    const types = ['craterfield', 'island', 'volcano', 'mountainside', 'rugged'];
    const readSeed = value => ({ has: Object.prototype.hasOwnProperty.call(value, 'seed'),
      value: value.seed === undefined ? null : value.seed });
    const defaults = type => Object.fromEntries(TYPES[type].params.map(param => [param.key, cloneParams(param.def)]));
    const mix32 = value => { let hash = value >>> 0; hash = Math.imul(hash ^ (hash >>> 16), 0x7feb352d) >>> 0;
      hash = Math.imul(hash ^ (hash >>> 15), 0x846ca68b) >>> 0; return (hash ^ (hash >>> 16)) >>> 0; };
    const hashText = text => { let hash = 2166136261 >>> 0;
      for (let index = 0; index < text.length; index++) { hash ^= text.charCodeAt(index); hash = Math.imul(hash, 16777619) >>> 0; }
      return hash; };
    const effectiveSeed = (type, seed, nodeId, rootSeed) => mix32((seed + hashText(type)
      + Math.imul(nodeId, 0x9e3779b1) + rootSeed) >>> 0);
    const compare = (actual, expected) => { let changed = 0;
      for (let index = 0; index < actual.length; index++) if (actual[index] !== expected[index]) changed++;
      return changed; };
    const signature = field => { let hash = 2166136261 >>> 0; const view = new DataView(new ArrayBuffer(4));
      for (const value of field) { view.setFloat32(0, value, true); hash ^= view.getUint32(0, true); hash = Math.imul(hash, 16777619) >>> 0; }
      return hash.toString(16).padStart(8, '0'); };
    RES = 64; TARGET_RES = 64; terrainDef.scale = 5000; terrainDef.height = 2600; terrainDef.lattice = 'square'; XF = null;
    const fixtures = Object.fromEntries(types.map(type => [type, { params: defaults(type), node: { id: 23 } }]));
    const phases = [];
    const measure = (name, expectedRoot) => {
      const root = readSeed(terrainDef), snapshot = readSeed(graphSnapshot().terrainDef), outputs = {};
      for (const type of types) {
        const { params, node } = fixtures[type], actual = TYPES[type].eval(params, [], node);
        const expected = TYPES[type].field(params, node.id, expectedRoot);
        outputs[type] = { effectiveSeed: effectiveSeed(type, TYPES[type].options(params).seed, node.id, expectedRoot),
          signature: signature(actual), expectedSignature: signature(expected), oracleDiff: compare(actual, expected) };
      }
      phases.push({ name, expectedRoot, root, snapshot, outputs });
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
    const oracleOk = phases.every(phase => types.every(type => phase.outputs[type].oracleDiff === 0
      && phase.outputs[type].signature === phase.outputs[type].expectedSignature));
    const stableSeven = types.every(type => byName.boot.outputs[type].signature === byName.new.outputs[type].signature
      && byName.boot.outputs[type].signature === byName['legacy-seedless'].outputs[type].signature);
    const distinctRoots = types.every(type => ['explicit-0', 'explicit-123', 'explicit-456']
      .every(name => byName[name].outputs[type].signature !== byName.boot.outputs[type].signature));
    const volcano = makeNode('volcano', 0, 0); nodes = [volcano]; edges = []; selected = volcano; historyReady = true;
    undoStack = []; redoStack = []; buildProps();
    const setStyle = style => { const input = document.querySelector('.field[data-param-key="style"] select');
      input.value = style; input.onchange(); };
    setStyle('shield');
    const shieldSnapshot = graphSnapshot(), shieldJson = JSON.stringify(shieldSnapshot);
    const bundleKeys = Object.keys(volcano.params).filter(key => key.startsWith('shield') || key.startsWith('strato')).sort();
    setStyle('stratovolcano'); const stratoSnapshot = graphSnapshot();
    undoGraph(); const undoStyle = nodes[0].params.style; redoGraph(); const redoStyle = nodes[0].params.style;
    undoStack = [JSON.parse(shieldJson)]; redoStack = []; undoGraph(); const loaded = graphSnapshot(), loadedKeys = Object.keys(nodes[0].params)
      .filter(key => key.startsWith('shield') || key.startsWith('strato')).sort();
    const legacy = TYPES.volcano.options({ style: 'stratovolcano', radiusM: 1777, heightM: 888, craterRadiusM: 99,
      craterDepthM: 77, rimHeightM: 22, rimWidthM: 33, barrancoCount: 9, barrancoDepth: .27,
      barrancoWavelengthM: 444, octaves: 3, lacunarity: 1.8, gain: .4 });
    const stylePersistence = { shieldSerialized: shieldJson.includes('"style":"shield"'), bundles: bundleKeys.length === 18,
      stratoSerialized: stratoSnapshot.nodes[0].params.style === 'stratovolcano', undoStyle, redoStyle,
      loadStyle: nodes[0].params.style, loadEquivalent: JSON.stringify(loaded.nodes[0].params) === JSON.stringify(shieldSnapshot.nodes[0].params),
      bundlesEquivalent: JSON.stringify(loadedKeys) === JSON.stringify(bundleKeys),
      legacy: legacy.radiusM === 1777 && legacy.heightM === 888 && legacy.craterRadiusM === 99 && legacy.craterDepthM === 77
        && legacy.rimHeightM === 22 && legacy.rimWidthM === 33 && legacy.barrancoCount === 9 && legacy.barrancoDepth === .27
        && legacy.barrancoWavelengthM === 444 && legacy.octaves === 3 && legacy.lacunarity === 1.8 && legacy.gain === .4 };
    stylePersistence.ok = stylePersistence.shieldSerialized && stylePersistence.bundles && stylePersistence.stratoSerialized
      && undoStyle === 'shield' && redoStyle === 'stratovolcano' && stylePersistence.loadStyle === 'shield'
      && stylePersistence.loadEquivalent && stylePersistence.bundlesEquivalent && stylePersistence.legacy;
    return { types, phases, stateOk, oracleOk, stableSeven, distinctRoots, stylePersistence,
      ok: phases.length === 6 && stateOk && oracleOk && stableSeven && distinctRoots && stylePersistence.ok };
  });

  const report = await page.evaluate(async mutation => {
    const TYPES_ = ['crater', 'craterfield', 'island', 'volcano', 'mountainside', 'rugged'];
    const defaults = type => Object.fromEntries(TYPES[type].params.map(param => [param.key, cloneParams(param.def)]));
    const gamma = n => (n * 2 ** -24) / (1 - n * 2 ** -24);
    const mix32 = value => { let h = value >>> 0; h = Math.imul(h ^ (h >>> 16), 0x7feb352d) >>> 0;
      h = Math.imul(h ^ (h >>> 15), 0x846ca68b) >>> 0; return (h ^ (h >>> 16)) >>> 0; };
    const hashText = text => { let h = 2166136261 >>> 0; for (let i = 0; i < text.length; i++) {
      h ^= text.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return h; };
    const seedFor = (type, seed, nodeId = 0, rootSeed = 7) => mix32((seed + hashText(type)
      + Math.imul(nodeId, 0x9e3779b1) + (mutation === 'root-seed-zero' ? 0 : rootSeed)) >>> 0);
    const randomStream = seed => { let state = mix32(seed); return () => {
      state = (Math.imul(state ^ (state >>> 15), 2246822519) + 374761393) >>> 0;
      return state / 4294967296; }; };
    const smoothstep = (a, b, value) => { const t = clamp((value - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
    const fbm = (x, y, wavelength, seed, options, cellM) => {
      let count = 0;
      for (let k = 0; k < options.octaves; k++) {
        if (wavelength / options.lacunarity ** k < 2 * cellM) break; count++;
      }
      if (mutation === 'nyquist-force-one') count = Math.max(1, count);
      if (count === 0) return 0;
      let sum = 0, total = 0, weight = 1;
      for (let k = 0; k < count; k++) { const frequency = options.lacunarity ** k / wavelength;
        sum += weight * gnoise(x * frequency, y * frequency, (seed + 7 * k) >>> 0);
        total += weight; weight *= options.gain; }
      return 2 * sum / total - 1;
    };
    const world = (x, y, n, nh, lattice) => [(x + .5 + (lattice === 'hex' ? .5 * (y & 1) : 0)) / n * terrainDef.scale,
      mutation === 'hex-row-normalized' && lattice === 'hex' ? (y + .5) / nh * terrainDef.scale
        : (y + .5) / n * terrainDef.scale * (lattice === 'hex' ? Math.sqrt(3) / 2 : 1)];
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
    try { TYPES.volcano.options({ ...defaults('volcano'), style: 'caldera' }); } catch (error) { unknownEnum = /unknown/i.test(error.message); }
    try { TYPES.mountainside.options({ ...defaults('mountainside'), skirt: [[0, 1], [.5, NaN], [1, 0]] }); }
    catch (error) { badCurve = /finite, monotone/i.test(error.message); }
    const shieldDefaults = TYPES.volcano.options({ ...defaults('volcano'), style: 'shield' });
    const stratoDefaults = TYPES.volcano.options({ ...defaults('volcano'), style: 'stratovolcano' });
    invalid.enums = unknownEnum && ['shield', 'stratovolcano'].every(style => TYPES.volcano.options({ ...defaults('volcano'), style }).style === style);
    invalid.volcanoSchema = !TYPES.volcano.params.some(param => param.key === 'profileExponent')
      && shieldDefaults.radiusM === 3500 && shieldDefaults.heightM === 300 && shieldDefaults.craterRadiusM === 180
      && shieldDefaults.craterDepthM === 20 && shieldDefaults.rimHeightM === 8 && shieldDefaults.rimWidthM === 45 && shieldDefaults.barrancoDepth === 0
      && stratoDefaults.radiusM === 2500 && stratoDefaults.heightM === 1000 && stratoDefaults.craterRadiusM === 100
      && stratoDefaults.craterDepthM === 120 && stratoDefaults.rimHeightM === 30 && stratoDefaults.rimWidthM === 35
      && stratoDefaults.barrancoCount === 12 && stratoDefaults.barrancoDepth === .18 && stratoDefaults.barrancoWavelengthM === 700;
    invalid.curve = badCurve; invalid.ok = Object.values(invalid).every(Boolean);

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

    const craterVolumes = [];
    for (const lattice of ['square', 'hex']) {
      RES = 256; TARGET_RES = 256; terrainDef.lattice = lattice; terrainDef.scale = 5000; terrainDef.height = 2600; terrainDef.seed = 7; XF = null;
      const bowlParams = { ...craterParams, depositFraction: 0 }, fullParams = { ...craterParams };
      const bowlField = TYPES.crater.eval(bowlParams, [], { id: 0 }), fullField = TYPES.crater.eval(fullParams, [], { id: 0 });
      const n = fieldW(), nh = fieldH(), cellM = terrainDef.scale / n, cellArea = cellM * cellM * (lattice === 'hex' ? Math.sqrt(3) / 2 : 1);
      const radius = craterParams.diameterM / 2, depth = .2 * craterParams.diameterM;
      let actualBowl = 0, actualEjecta = 0, expectedBowl = 0, expectedEjecta = 0;
      for (let y = 0; y < nh; y++) for (let x = 0; x < n; x++) { const index = y * n + x, point = world(x, y, n, nh, lattice);
        const u = Math.hypot(point[0] - 2500, point[1] - 2500) / radius;
        const bowl = u < 1 ? -depth * (1 - u * u) : 0, power = mutation === 'crater-ejecta-r2' ? -2 : -3;
        const ejecta = u >= 1 && u <= 3 ? 3 * craterParams.depositFraction * depth / 8 * u ** power : 0;
        actualBowl += -bowlField[index] * terrainDef.height * cellArea;
        actualEjecta += (fullField[index] - bowlField[index]) * terrainDef.height * cellArea;
        expectedBowl += -bowl * cellArea; expectedEjecta += ejecta * cellArea;
      }
      const exactExcavated = Math.PI * depth * radius * radius / 2;
      const reductionBound = gamma(2 * n * nh) * Math.max(expectedBowl, expectedEjecta, 1);
      craterVolumes.push({ lattice, samples: n * nh, actualBowl, expectedBowl, actualEjecta, expectedEjecta,
        bowlError: Math.abs(actualBowl - expectedBowl), ejectaError: Math.abs(actualEjecta - expectedEjecta), reductionBound,
        bowlDiscretization: Math.abs(actualBowl / exactExcavated - 1),
        massRatio: actualEjecta / (craterParams.depositFraction * actualBowl) });
    }
    const craterMass = { runs: craterVolumes, ok: craterVolumes.every(item => item.samples > 0
      && item.bowlError <= item.reductionBound && item.ejectaError <= item.reductionBound
      && item.bowlDiscretization <= .06 && Math.abs(item.massRatio - 1) <= .08) };

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
      RES = resolution; TARGET_RES = resolution; terrainDef.lattice = lattice; terrainDef.scale = 5000; terrainDef.height = 2600; terrainDef.seed = 7; XF = null;
      const nh = fieldH(), cellM = terrainDef.scale / resolution, indices = [];
      for (let iy = 1; iy <= 8; iy++) for (let ix = 1; ix <= 8; ix++) indices.push([
        Math.floor(ix * resolution / 10), Math.floor(iy * nh / 10)]);

      const islandParams = { ...defaults('island'), radiusXM: 1200, radiusYM: 650, angleDeg: 27, warpM: 0, roughnessM: 220, detailWavelengthM: 10 };
      const islandField = TYPES.island.eval(islandParams, [], { id: 0 }), islandOptions = TYPES.island.options(islandParams), islandSeed = seedFor('island', 7);
      const islandExpected = [], islandActual = [];
      for (const index of indices) { const point = world(index[0], index[1], resolution, nh, lattice), dx = point[0] - 2500, dy = point[1] - 2500;
        const a = islandOptions.angleDeg * Math.PI / 180, qx = (dx * Math.cos(a) - dy * Math.sin(a)) / islandOptions.radiusXM;
        const divisorY = mutation === 'island-circular-envelope' ? islandOptions.radiusXM : islandOptions.radiusYM;
        const qy = (dx * Math.sin(a) + dy * Math.cos(a)) / divisorY, minimum = Math.min(islandOptions.radiusXM, islandOptions.radiusYM);
        const envelope = 1 - smoothstep(1 - islandOptions.coastWidthM / minimum, 1, Math.hypot(qx, qy));
        const relief = islandOptions.elevationM + islandOptions.roughnessM * fbm(point[0], point[1], islandOptions.detailWavelengthM, islandSeed, islandOptions, cellM);
        islandExpected.push(Math.fround(Math.max(0, envelope * relief) / terrainDef.height));
        islandActual.push(islandField[index[1] * resolution + index[0]]); }

      const volcanoComparisons = {}, volcanoFields = {};
      for (const style of ['shield', 'stratovolcano']) {
        const volcanoParams = { ...defaults('volcano'), style, stratoBarrancoDepth: .35, stratoBarrancoWavelengthM: 5000, stratoOctaves: 1 };
        const volcanoOptions = TYPES.volcano.options(volcanoParams), volcanoSeed = seedFor('volcano', volcanoOptions.seed);
        const volcanoField = TYPES.volcano.eval(volcanoParams, [], { id: 0 }), volcanoExpected = [], volcanoActual = [];
        for (const index of indices) { const point = world(index[0], index[1], resolution, nh, lattice), dx = point[0] - 2500, dy = point[1] - 2500;
          const radius = Math.hypot(dx, dy), rn = radius / volcanoOptions.radiusM;
          let base = rn <= 1 ? Math.max(0, style === 'shield' ? 1 - rn ** 1.7 : (1 - rn) ** 2.2) : 0;
          if (mutation === 'volcano-alias-styles' && style === 'shield') base = rn <= 1 ? (1 - rn) ** 2.2 : 0;
          if (mutation === 'volcano-straight-cone') base = rn <= 1 ? 1 - rn : 0;
          if (mutation === 'volcano-gaussian-cone') base = rn <= 1 ? Math.exp(-4 * rn * rn) : 0;
          const noise = style === 'shield' ? 0 : fbm(point[0], point[1], volcanoOptions.barrancoWavelengthM, volcanoSeed, volcanoOptions, cellM);
          const grooves = style === 'shield' ? 0 : .5 * (1 + Math.cos(volcanoOptions.barrancoCount * Math.atan2(dy, dx) + 2 * Math.PI * noise));
          const depth = mutation === 'volcano-no-barrancos' ? 0 : volcanoOptions.barrancoDepth;
          const edifice = volcanoOptions.heightM * base * (1 - depth * grooves * rn), craterRho = radius / volcanoOptions.craterRadiusM;
          const summit = mutation === 'volcano-drop-summit' ? 0 : (craterRho < 1 ? -volcanoOptions.craterDepthM * (1 - craterRho ** 2) ** 1.5 : 0);
          const rim = volcanoOptions.rimHeightM * Math.exp(-.5 * ((radius - volcanoOptions.craterRadiusM) / volcanoOptions.rimWidthM) ** 2);
          volcanoExpected.push(Math.fround(Math.max(0, edifice + summit + rim) / terrainDef.height));
          volcanoActual.push(volcanoField[index[1] * resolution + index[0]]); }
        volcanoComparisons[style] = maxError(volcanoActual, volcanoExpected); volcanoFields[style] = volcanoField;
      }

      const sideParams = { ...defaults('mountainside'), weather: 0 }, sideOptions = TYPES.mountainside.options(sideParams);
      sideOptions.seed = seedFor('mountainside', sideOptions.seed, 0, 7);
      const sideField = TYPES.mountainside.eval(sideParams, [], { id: 0 }), mountain = TYPES.mountain.eval(sideOptions, [], { id: 0 }), sideExpected = [], sideActual = [];
      const bearing = sideOptions.bearingDeg * Math.PI / 180;
      for (const index of indices) { const point = world(index[0], index[1], resolution, nh, lattice);
        const t = (point[0] - 2500) * Math.cos(bearing) + (point[1] - 2500) * Math.sin(bearing);
        let gate = smoothstep(-sideOptions.featherM, sideOptions.featherM, t); if (mutation === 'mountainside-invert-halfplane') gate = 1 - gate;
        sideExpected.push(Math.fround(mountain[index[1] * resolution + index[0]] * gate)); sideActual.push(sideField[index[1] * resolution + index[0]]); }

      const ruggedParams = { ...defaults('rugged'), blockCount: 8, minSpacingM: 100, blockRadiusM: 500, blockVariation: 0, macroReliefM: 0, baseElevationM: 120 };
      const ruggedOptions = TYPES.rugged.options(ruggedParams), ruggedSeed = seedFor('rugged', 7), ruggedPlan = TYPES.rugged.planPlacement(ruggedParams, 0, 7);
      const ruggedField = TYPES.rugged.eval(ruggedParams, [], { id: 0 }), ruggedExpected = [], ruggedActual = [];
      for (const index of indices) { const point = world(index[0], index[1], resolution, nh, lattice), contributions = [];
        for (let blockIndex = 0; blockIndex < ruggedPlan.points.length; blockIndex++) { const block = ruggedPlan.points[blockIndex], distance = Math.hypot(point[0] - block.x, point[1] - block.y) / ruggedOptions.blockRadiusM;
          if (distance < 1) contributions.push(ruggedOptions.blockHeightM * (1 - distance) ** ruggedOptions.blockExponent
            * (1 + ruggedOptions.blockNoise * fbm(point[0], point[1], ruggedOptions.blockWavelengthM, ruggedSeed + 4099 * blockIndex, ruggedOptions, cellM))); }
        const blocks = mutation === 'rugged-sum-blocks' ? contributions.reduce((sum, value) => sum + value, 0) : Math.max(0, ...contributions);
        ruggedExpected.push(Math.fround((ruggedOptions.baseElevationM + blocks) / terrainDef.height)); ruggedActual.push(ruggedField[index[1] * resolution + index[0]]); }

      const comparisons = { island: maxError(islandActual, islandExpected), volcanoShield: volcanoComparisons.shield, volcanoStrato: volcanoComparisons.stratovolcano,
        mountainside: maxError(sideActual, sideExpected), rugged: maxError(ruggedActual, ruggedExpected) };
      const tolerance = gamma(64) * 2;
      lattices.push({ lattice, resolution, seed: 7, samples: indices.length, comparisons,
        positive: { island: islandField.some(value => value > 0), volcanoShield: volcanoFields.shield.some(value => value > 0), volcanoStrato: volcanoFields.stratovolcano.some(value => value > 0),
          mountainside: sideField.some(value => value > 0), rugged: ruggedField.some(value => value > 0) },
        zero: { island: islandField.some(value => value === 0), volcanoShield: volcanoFields.shield.some(value => value === 0), volcanoStrato: volcanoFields.stratovolcano.some(value => value === 0),
          mountainside: sideField.some(value => value === 0), rugged: ruggedField.every(value => value >= 0) },
        ok: Object.values(comparisons).every(value => value.error <= tolerance) });
    }

    terrainDef.scale = 5000; terrainDef.height = 2600; terrainDef.seed = 7; RES = 128; TARGET_RES = 128; XF = null;
    const rootSeedIntegration = {};
    for (const type of ['craterfield', 'island', 'volcano', 'mountainside', 'rugged']) {
      const params = defaults(type), node = { id: 23 };
      terrainDef.seed = 7; const first = TYPES[type].eval(params, [], node);
      terrainDef.seed = 8; const changed = TYPES[type].eval(params, [], node);
      rootSeedIntegration[type] = { changed: maxError(first, changed).changed > 0 };
    }
    terrainDef.seed = 7;

    const transformMatrix = xfFromParams({ scale: 1.17, aspect: .83, angle: 23, offX: .071, offY: -.043, pivX: .41, pivY: .63 });
    const worldMapping = [], transformed = {};
    for (const lattice of ['square', 'hex']) {
      terrainDef.lattice = lattice; const nh = fieldH(), baseActual = [], baseExpected = [], transformedActual = [], transformedExpected = [];
      for (let iy = 1; iy <= 8; iy++) for (let ix = 1; ix <= 8; ix++) { const x = Math.floor(ix * RES / 10), y = Math.floor(iy * nh / 10);
        XF = null; baseActual.push(TYPES.crater.worldSampleAt(x, y)); baseExpected.push(world(x, y, RES, nh, lattice));
        XF = transformMatrix; transformedActual.push(TYPES.crater.worldSampleAt(x, y));
        const point = world(x, y, RES, nh, lattice), u = point[0] / terrainDef.scale, v = point[1] / terrainDef.scale;
        transformedExpected.push([(transformMatrix[0] * u + transformMatrix[1] * v + transformMatrix[2]) * terrainDef.scale,
          (transformMatrix[3] * u + transformMatrix[4] * v + transformMatrix[5]) * terrainDef.scale]);
      }
      XF = null;
      const coordinateError = (actual, expected) => actual.reduce((error, point, index) => Math.max(error,
        Math.abs(point[0] - expected[index][0]), Math.abs(point[1] - expected[index][1])), 0);
      worldMapping.push({ lattice, samples: baseActual.length, baseError: coordinateError(baseActual, baseExpected),
        transformError: coordinateError(transformedActual, transformedExpected) });
      for (const entry of ['crater', 'island', 'volcano:shield', 'volcano:stratovolcano']) {
        const [type, style] = entry.split(':'), params = { ...defaults(type), ...(style ? { style } : {}) }, options = TYPES[type].options(params), node = { id: 0 }, previous = XF; XF = transformMatrix;
        const field = TYPES[type].eval(params, [], node); XF = previous; const actual = [], expected = [], seed = seedFor(type, params.seed || 0);
        for (let iy = 1; iy <= 8; iy++) for (let ix = 1; ix <= 8; ix++) { const x = Math.floor(ix * RES / 10), y = Math.floor(iy * nh / 10);
          const point = world(x, y, RES, nh, lattice), u = point[0] / terrainDef.scale, v = point[1] / terrainDef.scale;
          const worldX = (transformMatrix[0] * u + transformMatrix[1] * v + transformMatrix[2]) * terrainDef.scale;
          const worldY = (transformMatrix[3] * u + transformMatrix[4] * v + transformMatrix[5]) * terrainDef.scale;
          const metres = type === 'crater' ? TYPES.crater.profile(Math.hypot(worldX - options.x * terrainDef.scale, worldY - options.y * terrainDef.scale), options)
            : TYPES[type].profile(worldX, worldY, options, seed, terrainDef.scale / RES);
          actual.push(field[y * RES + x]); expected.push(Math.fround(metres / terrainDef.height)); }
        const comparison = maxError(actual, expected); transformed[`${lattice}:${entry}`] = { samples: actual.length, maxError: comparison.error, ok: comparison.error === 0 };
      }
    }
    worldMapping.ok = worldMapping.every(item => item.samples === 64 && item.baseError <= 1e-10 && item.transformError <= 1e-10);
    transformed.rasterExcluded = ['craterfield', 'mountainside', 'rugged'].every(type => !EXACT_TYPES.has(type));
    transformed.ok = Object.entries(transformed).filter(([key]) => key.includes(':')).every(([, value]) => value.ok) && transformed.rasterExcluded;

    terrainDef.lattice = 'square'; RES = 256; TARGET_RES = 256; XF = null;
    const radialExpected = {
      shield: [.9052677146, .6922138967, .3867971739],
      stratovolcano: [.5310492251, .2176376408, .0473661427] };
    const radial = {}, radialValues = [], radialRhos = [.25, .5, .75];
    for (const style of ['shield', 'stratovolcano']) {
      const prefix = style === 'shield' ? 'shield' : 'strato';
      const params = { ...defaults('volcano'), style, [`${prefix}RadiusM`]: 1000, [`${prefix}HeightM`]: 500,
        [`${prefix}CraterDepthM`]: 0, [`${prefix}RimHeightM`]: 0, stratoBarrancoDepth: 0 };
      const options = TYPES.volcano.options(params), values = radialRhos.map(rho =>
        TYPES.volcano.profile(2500 + rho * options.radiusM, 2500, options, seedFor('volcano', options.seed), terrainDef.scale / RES) / options.heightM);
      radial[style] = { values, expected: radialExpected[style], maxError: Math.max(...values.map((value, index) => Math.abs(value - radialExpected[style][index]))) };
      radialValues.push(...values);
    }
    const secant = (style, height, radius, a, b) => { const B = rho => style === 'shield' ? 1 - rho ** 1.7 : (1 - rho) ** 2.2;
      return Math.atan(Math.abs(height / radius * (B(b) - B(a)) / (b - a))) * 180 / Math.PI; };
    let slopeShield = shieldDefaults, slopeStrato = stratoDefaults;
    if (mutation === 'volcano-swap-style-defaults') [slopeShield, slopeStrato] = [slopeStrato, slopeShield];
    const slopes = { shield: secant('shield', slopeShield.heightM, slopeShield.radiusM, .25, .75),
      stratoUpper: secant('stratovolcano', slopeStrato.heightM, slopeStrato.radiusM, .2, .4),
      stratoLower: secant('stratovolcano', slopeStrato.heightM, slopeStrato.radiusM, .6, .8) };
    const summit = {};
    for (const style of ['shield', 'stratovolcano']) {
      const prefix = style === 'shield' ? 'shield' : 'strato', base = defaults('volcano');
      if (mutation === 'volcano-drop-summit') base[`${prefix}CraterDepthM`] = 0;
      const options = TYPES.volcano.options({ ...base, style }), seed = seedFor('volcano', options.seed), centre = TYPES.volcano.profile(2500, 2500, options, seed, terrainDef.scale / RES);
      const annulus = Array.from({ length: 65 }, (_, index) => { const radius = options.craterRadiusM * (.8 + .4 * index / 64);
        return TYPES.volcano.profile(2500 + radius, 2500, options, seed, terrainDef.scale / RES); });
      const noDepression = TYPES.volcano.options({ ...base, style, [`${prefix}CraterDepthM`]: 0 });
      summit[style] = { centre, annulusMax: Math.max(...annulus), depression: TYPES.volcano.profile(2500, 2500, noDepression, seed, terrainDef.scale / RES) - centre };
    }
    const shieldSymmetryOptions = TYPES.volcano.options({ ...defaults('volcano'), style: 'shield', shieldCraterDepthM: 0, shieldRimHeightM: 0 });
    const shieldCircle = Array.from({ length: 64 }, (_, index) => { const angle = 2 * Math.PI * index / 64, radius = .55 * shieldSymmetryOptions.radiusM;
      return TYPES.volcano.profile(2500 + radius * Math.cos(angle), 2500 + radius * Math.sin(angle), shieldSymmetryOptions, seedFor('volcano', shieldSymmetryOptions.seed), terrainDef.scale / RES); });
    const volcanoMorphology = { radial, slopes, summit, shieldSpread: Math.max(...shieldCircle) - Math.min(...shieldCircle) };
    volcanoMorphology.ok = Object.values(radial).every(item => item.values.length === 3 && item.maxError <= 1e-9)
      && radialExpected.shield.every((value, index) => value !== radialExpected.stratovolcano[index])
      && Math.abs(slopes.shield - 5.079140) < 1e-6 && slopes.shield >= 2 && slopes.shield <= 10
      && Math.abs(slopes.stratoUpper - 29.858292) < 1e-6 && slopes.stratoUpper >= 20 && slopes.stratoUpper <= 35
      && Math.abs(slopes.stratoLower - 11.773853) < 1e-6 && slopes.stratoUpper > slopes.stratoLower
      && Object.values(summit).every(item => item.centre > 0 && item.centre < item.annulusMax && item.depression > 0)
      && shieldCircle.length === 64 && volcanoMorphology.shieldSpread <= gamma(16) * Math.max(...shieldCircle);
    const barrancoParams = { ...defaults('volcano'), style: 'stratovolcano', stratoCraterDepthM: 0, stratoRimHeightM: 0,
      stratoBarrancoDepth: mutation === 'volcano-no-barrancos' ? 0 : .65, stratoBarrancoWavelengthM: 5000, stratoOctaves: 1 };
    const barrancoOptions = TYPES.volcano.options(barrancoParams);
    const barrancoSeed = seedFor('volcano', barrancoOptions.seed), barrancoSamples = 16 * barrancoOptions.barrancoCount, circular = [];
    for (let index = 0; index < barrancoSamples; index++) { const angle = 2 * Math.PI * index / barrancoSamples, radius = barrancoOptions.radiusM * .55;
      circular.push(TYPES.volcano.profile(2500 + radius * Math.cos(angle), 2500 + radius * Math.sin(angle), barrancoOptions, barrancoSeed, terrainDef.scale / RES)); }
    let minima = 0; for (let index = 0; index < circular.length; index++) {
      const previous = circular[(index + circular.length - 1) % circular.length], current = circular[index], next = circular[(index + 1) % circular.length];
      if (current < previous && current <= next) minima++;
    }
    const barrancos = { samples: circular.length, minima, expected: barrancoOptions.barrancoCount,
      ok: circular.length === 16 * barrancoOptions.barrancoCount && minima === barrancoOptions.barrancoCount };
    terrainDef.lattice = 'square'; RES = 512; TARGET_RES = 512;
    const mutationReached = mutation ? ({
      'crater-ejecta-r2': !crater.ok, 'craterfield-grid-jitter': !placement.craterfield.spacing,
      'island-circular-envelope': lattices.some(item => !item.ok), 'volcano-alias-styles': lattices.some(item => !item.ok),
      'volcano-straight-cone': lattices.some(item => !item.ok), 'volcano-gaussian-cone': lattices.some(item => !item.ok),
      'volcano-drop-summit': !volcanoMorphology.ok, 'volcano-swap-style-defaults': !volcanoMorphology.ok,
      'mountainside-invert-halfplane': lattices.some(item => !item.ok), 'rugged-sum-blocks': lattices.some(item => !item.ok),
      'silent-underfill': !placement.craterfield.saturation, 'nyquist-force-one': lattices.some(item => !item.ok),
      'hex-row-normalized': !worldMapping.ok || lattices.some(item => !item.ok), 'root-seed-zero': lattices.some(item => !item.ok),
      'volcano-no-barrancos': !barrancos.ok }[mutation]) : false;
    const normalOk = registration.ok && invalid.ok && crater.ok && craterMass.ok && placement.ok && worldMapping.ok && transformed.ok && volcanoMorphology.ok && barrancos.ok
      && Object.values(rootSeedIntegration).every(item => item.changed) && lattices.every(item => item.ok)
      && lattices.every(item => Object.values(item.positive).every(Boolean) && Object.values(item.zero).every(Boolean));
    return { registration, invalid, crater, craterMass, placement, worldMapping, transformed, rootSeedIntegration, volcanoMorphology, barrancos, lattices, mutation, mutationReached,
      violatedFormula: mutation ? ({ 'crater-ejecta-r2': 'Crater ejecta u^-3', 'craterfield-grid-jitter': 'Bridson pairwise spacing',
        'island-circular-envelope': 'Island elliptical envelope', 'volcano-alias-styles': 'Volcano distinct fixed radial signatures',
        'volcano-straight-cone': 'Volcano shield 1-r^1.7 and strato (1-r)^2.2 profiles',
        'volcano-gaussian-cone': 'Volcano non-Gaussian fixed radial signatures', 'volcano-drop-summit': 'Volcano style summit depressions',
        'volcano-swap-style-defaults': 'Volcano style default slope bands',
        'mountainside-invert-halfplane': 'MountainSide M*G half-plane', 'rugged-sum-blocks': 'Rugged base+max(block)',
        'silent-underfill': 'Poisson saturation status', 'nyquist-force-one': 'zero-safe Nyquist octave truncation',
        'hex-row-normalized': 'physical hex world/transform row pitch', 'root-seed-zero': 'canonical root seed integration',
        'volcano-no-barrancos': 'Volcano barrancoCount circular minima', 'unfrozen-framebuffer': 'frozen 960x540 framebuffer' })[mutation] : null,
      ok: mutation ? false : normalOk };
  }, MUTATION);

  const inspectUi = async viewport => {
    await page.setViewportSize(viewport); await page.waitForTimeout(120);
    const result = await page.evaluate(types => {
      buildIndex(); nodes.length = 0; edges.length = 0; uid = 1; selected = null; selectedEdge = null;
      const measured = {};
      for (const type of types) { const node = makeNode(type, 0, 0), keys = new Set(), styles = {}; let geometry = true;
        const variants = type === 'mountainside' ? [{ form: 'peak' }, { form: 'massif' }]
          : type === 'volcano' ? [{ style: 'shield' }, { style: 'stratovolcano' }] : [{}];
        for (const variant of variants) { Object.assign(node.params, variant); selected = node; buildProps();
          const panel = document.querySelector('#props').getBoundingClientRect(), fields = [...document.querySelectorAll('#pBody .field[data-param-key]')];
          for (const field of fields) { keys.add(field.dataset.paramKey); const rect = field.getBoundingClientRect();
            geometry &&= rect.width > 0 && rect.left >= panel.left - 1 && rect.right <= panel.right + 1 && field.scrollWidth <= field.clientWidth + 2; }
          if (type === 'volcano') styles[variant.style] = { keys: fields.map(field => field.dataset.paramKey), info: TYPES.volcano.info(node) };
        }
        measured[type] = { name: TYPES[type].name, toolbox: !!document.querySelector(`.node-tool-item[data-type="${type}"]`), keys: [...keys],
          expected: TYPES[type].params.map(param => param.key), geometry, styles };
      }
      return measured;
    }, ['crater', 'craterfield', 'island', 'volcano', 'mountainside', 'rugged']);
    await page.evaluate(() => { nodes.length = 0; edges.length = 0; selected = null; selectedEdge = null; drawGraph(); });
    const graphBox = await page.locator('#graph').boundingBox();
    for (const type of Object.keys(result)) {
      await page.locator('#graph').dispatchEvent('dblclick', {
        clientX: graphBox.x + Math.max(8, graphBox.width * .75), clientY: graphBox.y + Math.max(8, graphBox.height * .75) });
      await page.locator('#menu .menu-search').fill(result[type].name);
      result[type].quickCreate = await page.locator(`#menu .menu-item[data-type="${type}"]`).count() === 1;
      await page.keyboard.press('Escape');
    }
    return result;
  };
  report.ui = { desktop: await inspectUi({ width: 1440, height: 900 }), mobile: await inspectUi({ width: 390, height: 844 }) };
  report.ui.ok = Object.values(report.ui).filter(value => typeof value === 'object').every(view => Object.values(view).every(result => {
    const stylesOk = !result.styles.shield || (result.styles.shield.keys.some(key => key.startsWith('shield'))
      && !result.styles.shield.keys.some(key => key.startsWith('strato')) && /5\.079.*2-10.*depression.*disabled/i.test(result.styles.shield.info)
      && result.styles.stratovolcano.keys.some(key => key.startsWith('strato'))
      && !result.styles.stratovolcano.keys.some(key => key.startsWith('shield')) && /29\.858.*20-35.*11\.774.*crater.*12.*barranco/i.test(result.styles.stratovolcano.info));
    return result.toolbox && result.quickCreate && result.geometry && result.expected.every(key => result.keys.includes(key)) && stylesOk;
  }));
  report.lifecycle = lifecycle;
  report.ok = report.ok && report.ui.ok && lifecycle.ok;

  report.visual = { runs: [], ok: true };
  if (VISUAL) {
    if (VISUAL_STYLE && !['shield', 'stratovolcano'].includes(VISUAL_STYLE)) throw new Error(`Unknown visual style ${VISUAL_STYLE}`);
    if (VISUAL_STYLE && VISUAL_TYPE !== 'volcano') throw new Error('--visual-style requires --visual-type=volcano');
    const endpoint = (() => { try { const parsed = new globalThis.URL(URL); return parsed.port || parsed.protocol.replace(':', ''); } catch (_) { return 'source'; } })();
    const evidenceDir = path.resolve(__dirname, `../../.sweep-logs/MC-S32/${endpoint}`); mkdirSync(evidenceDir, { recursive: true });
    await page.setViewportSize({ width: 1440, height: 900 });
    const visualLattices = VISUAL_LATTICE ? [VISUAL_LATTICE] : ['square', 'hex'];
    const visualTypes = VISUAL_TYPE ? [VISUAL_TYPE] : ['crater', 'craterfield', 'island', 'volcano', 'mountainside', 'rugged'];
    const visualViews = VISUAL_VIEW ? [[VISUAL_VIEW, VISUAL_VIEW === 'traversal' ? 2.88 : 1.04]] : [['traversal', 2.88], ['close', 1.04]];
    for (const lattice of visualLattices) for (const type of visualTypes) {
      const visualStyles = type === 'volcano' ? (VISUAL_STYLE ? [VISUAL_STYLE] : ['shield', 'stratovolcano']) : [null];
      for (const style of visualStyles) for (const view of visualViews) {
        const result = await page.evaluate(({ lattice, type, style, distance, flat }) => {
          RES = 256; TARGET_RES = 256; terrainDef.lattice = lattice; terrainDef.scale = 5000; terrainDef.height = 2600; buildIndex();
          const params = Object.fromEntries(TYPES[type].params.map(param => [param.key, cloneParams(param.def)])), node = { id: 23, type, params };
          if (style) params.style = style;
          if ('amount' in params) params.amount = 1.7;
          const baseline = newField(.12), generated = TYPES[type].eval(params, [], node), treatment = flat ? baseline : new Float32Array(generated.length);
          if (!flat) for (let i = 0; i < generated.length; i++) treatment[i] = Math.fround(baseline[i] + generated[i]);
          const capture = field => { const root = { id: 24, type: 'output', params: { norm: 'off' }, _field: field };
            updateViewport(field, root); cam = { az: -35 * Math.PI / 180, el: 42 * Math.PI / 180, dist: distance, target: [0, 0, 0], fov: 45 * Math.PI / 180 };
            shadeMode = 1; syncDisplayState(); const canvas = document.querySelector('#gl');
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
          return { lattice, type, style, distance, terrainPixels: count, changedPixels: changed, changedFraction: count ? changed / count : 0,
            channelsValid: after.every(value => Number.isInteger(value) && value >= 0 && value <= 255), fovDeg: treatmentCapture.fovDeg,
            framebuffer: [treatmentCapture.canvasWidth, treatmentCapture.canvasHeight, treatmentCapture.drawingWidth, treatmentCapture.drawingHeight],
            deviceScale: treatmentCapture.deviceScale, png: treatmentCapture.png };
          }, { lattice, type, style, distance: view[1], flat: MUTATION === 'flat-render' ? true : MUTATION === 'unfrozen-framebuffer' ? 'unfrozen-framebuffer' : false });
        result.endpoint = endpoint; result.view = view[0]; result.ok = result.terrainPixels >= 10000 && result.changedFraction >= .01 && result.channelsValid && Math.abs(result.fovDeg - 45) < 1e-9;
          result.ok &&= result.deviceScale === 1 && result.framebuffer.every((value, index) => value === (index % 2 ? 540 : 960));
        report.visual.runs.push(result); report.visual.ok &&= result.ok;
        const styleName = style ? `-${style}` : '';
        if (MUTATION !== 'flat-render') writeFileSync(path.join(evidenceDir, `landform-${type}${styleName}-${lattice}-${view[0]}.png`), Buffer.from(result.png.split(',')[1], 'base64'));
        delete result.png;
      }
    }
    if (VISUAL_TYPE === 'volcano' && VISUAL_STYLE) report.visual.ok &&= report.visual.runs.length === 4
      && report.visual.runs.every(run => run.type === 'volcano' && run.style === VISUAL_STYLE)
      && new Set(report.visual.runs.map(run => `${run.style}:${run.lattice}:${run.view}`)).size === 4;
  }
  if (MUTATION === 'flat-render' || MUTATION === 'unfrozen-framebuffer') { report.mutationReached = VISUAL && !report.visual.ok;
    report.violatedFormula = MUTATION === 'flat-render' ? 'visual treatment pixel threshold' : 'frozen 960x540 framebuffer'; report.ok = false; }
  else report.ok = report.ok && report.visual.ok;

  console.log(`landforms lifecycle ${JSON.stringify(lifecycle)}`);
  console.log(`landforms latticeRuns=${report.lattices.length} samples=${report.lattices.reduce((sum, item) => sum + item.samples, 0)} seed=7 mutationReached=${report.mutationReached}`);
  console.log(`landforms gates=${JSON.stringify({ registration: report.registration.ok, invalid: report.invalid.ok, crater: report.crater.ok,
    craterMass: report.craterMass.ok, placement: report.placement.ok, worldMapping: report.worldMapping.ok, transformed: report.transformed.ok,
    barrancos: report.barrancos.ok, roots: Object.values(report.rootSeedIntegration).every(item => item.changed),
    lattices: report.lattices.every(item => item.ok), ui: report.ui.ok, lifecycle: report.lifecycle.ok })}`);
  console.log(`landforms volcanoUi=${JSON.stringify({ ok: report.ui.ok, desktop: report.ui.desktop.volcano.styles, mobile: report.ui.mobile.volcano.styles })}`);
  if (report.mutation) console.log(`MUTATION ${report.mutation} violated ${report.violatedFormula}`);
  if (!SUMMARY) console.log(JSON.stringify({ ...report, errors }, null, 2));
  else if (VISUAL) console.log(`visual runs=${report.visual.runs.length} minTerrain=${Math.min(...report.visual.runs.map(run => run.terrainPixels))} minChanged=${Math.min(...report.visual.runs.map(run => run.changedFraction))} fov=${Math.min(...report.visual.runs.map(run => run.fovDeg))}`);
  const cleanupBudget = new Promise(resolve => setTimeout(resolve, 2000));
  await Promise.race([page.close({ runBeforeUnload: false }).catch(() => {}), cleanupBudget]);
  await Promise.race([browser.close().catch(() => {}), cleanupBudget]);
  process.exit(report.ok && !errors.length ? 0 : 1);
})().catch(error => { console.error('FATAL', error); process.exit(2); });