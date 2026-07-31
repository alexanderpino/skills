const { chromium } = await import('playwright-core');
const path = (await import('node:path')).default;
const { mkdirSync, writeFileSync } = await import('node:fs');
const __dirname = path.dirname(path.resolve(process.argv[1]));

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));
const STYLES = ['roughen', 'distress', 'groundtexture', 'rocknoise', 'bulbous', 'pockmarks', 'contours', 'grid'];
const VISUAL = process.argv.includes('--visual');
const SUMMARY = process.argv.includes('--summary');
const flagValue = name => process.argv.find(argument => argument.startsWith(`--${name}=`))?.split('=')[1];
const VISUAL_STYLE = flagValue('visual-style');
const VISUAL_LATTICE = flagValue('visual-lattice');
const VISUAL_VIEW = flagValue('visual-view');
const mutationArg = process.argv.find(argument => argument.startsWith('--mutate='));
const MUTATION = mutationArg ? mutationArg.slice(9) : null;
const MUTATIONS = ['roughen-drop-slope', 'distress-invert-convex', 'groundtexture-drop-wear',
  'rocknoise-use-fbm', 'bulbous-invert-cell', 'pockmarks-positive', 'contours-cell-height',
  'grid-unrotated', 'pre-mask', 'cell-space', 'flat-render'];
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
    const effectiveSeed = (style, seed, nodeId) => mix32((seed + Math.imul(nodeId, 0x9e3779b1) + hashText(style)) >>> 0);
    const normalized = field => { let minimum = Infinity, maximum = -Infinity;
      for (const value of field) { minimum = Math.min(minimum, value); maximum = Math.max(maximum, value); }
      const range = maximum - minimum || 1, output = new Float32Array(field.length);
      for (let i = 0; i < field.length; i++) output[i] = (field[i] - minimum) / range; return output; };
    const fbm = (worldX, worldY, wavelength, seed, options, cellM) => {
      let count = 0; for (let k = 0; k < options.octaves; k++) {
        if (wavelength / options.lacunarity ** k < 2 * cellM) break; count++; }
      count = Math.max(1, count); let sum = 0, total = 0, weight = 1;
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
    const malformed = TYPES.surface.options({ slopeLowDeg: 88, slopeHighDeg: -Infinity, cellSpacingM: 100,
      bulbRadiusM: Infinity, pitRadiusM: Infinity, edgeFeatherM: Infinity, style: 'pockmarks', spacingM: 20, lineWidthM: 1000, angleDeg: 360 });
    invalid.finite = Object.values(malformed).filter(value => typeof value === 'number').every(Number.isFinite);
    invalid.relational = malformed.slopeHighDeg >= malformed.slopeLowDeg + 1 && malformed.pitRadiusM <= 50
      && malformed.edgeFeatherM <= 50 - malformed.pitRadiusM && malformed.lineWidthM < malformed.spacingM / 2 && malformed.angleDeg === 0;
    invalid.ok = invalid.unknown && invalid.finite && invalid.relational;

    const runs = [];
    for (const lattice of ['square', 'hex']) for (const resolution of [128, 256]) {
      RES = resolution; TARGET_RES = resolution; terrainDef.lattice = lattice; terrainDef.scale = 5000; terrainDef.height = 2600; XF = null;
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
        const expected = [], sampled = [], seed = effectiveSeed(style, options.seed, node.id), low = Math.tan(options.slopeLowDeg * Math.PI / 180), high = Math.tan(options.slopeHighDeg * Math.PI / 180);
        let driverNonzero = 0, changed = 0, maskExchange = true;
        for (const index of indices) { const x = index[0], y = index[1], i = y * n + x, worldX = (x + .5 + (lattice === 'hex' ? .5 * (y & 1) : 0)) * cellM;
          const worldY = (y + .5) * cellM * (lattice === 'hex' ? Math.sqrt(3) / 2 : 1), slopeMask = smoothstep(low, high, slope[i] * terrainDef.height / terrainDef.scale);
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
        let seedDiff = false; for (let i = 0; i < actual.length; i++) if (actual[i] !== changedSeed[i]) { seedDiff = true; break; }
        stylesReport[style] = { maxError: maxError(sampled, expected), samples: sampled.length, driverNonzero, changed,
          amountIdentity: zeroAmount === input, zeroMaskIdentity: zeroMask === input, maskExchange,
          deterministic: maxError(actual, repeat) === 0, seedDifference: ['contours', 'grid'].includes(style) ? true : seedDiff,
          octaves: TYPES.surface.fbmAt(1000, 1000, options.wavelengthM, seed, options, cellM).octaves };
        stylesReport[style].ok = stylesReport[style].maxError <= gamma(64) * 2 && driverNonzero >= 32 && changed > 0
          && stylesReport[style].amountIdentity && stylesReport[style].zeroMaskIdentity && maskExchange
          && stylesReport[style].deterministic && stylesReport[style].seedDifference;
      }
      runs.push({ lattice, resolution, seed: 7, samples: indices.length * styles.length, styles: stylesReport,
        ok: Object.values(stylesReport).every(style => style.ok) });
    }
    terrainDef.lattice = 'square'; RES = 512; TARGET_RES = 512;
    const mutationReached = mutation ? runs.some(run => !run.ok) : false;
    return { invalid, runs, mutation, mutationReached, ok: mutation ? false : invalid.ok && runs.every(run => run.ok),
      violatedFormula: mutation ? ({ 'roughen-drop-slope': 'Roughen slope driver', 'distress-invert-convex': 'Distress convex driver',
        'groundtexture-drop-wear': 'Ground Texture wear driver', 'rocknoise-use-fbm': 'Rock Noise ridge pattern',
        'bulbous-invert-cell': 'Bulbous cellular radius', 'pockmarks-positive': 'Pockmarks negative relief',
        'contours-cell-height': 'Contours metre elevation', 'grid-unrotated': 'Grid world rotation',
        'pre-mask': 'post-effect mask application', 'cell-space': 'world-metre pattern coordinates',
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
    await page.locator('#graph').dblclick({ position: { x: Math.max(8, graphBox.width * .75), y: Math.max(8, graphBox.height * .75) } });
    await page.locator('#menu .menu-search').fill('Surface Detail');
    result.quickCreate = await page.locator('#menu .menu-item[data-type="surface"]').count() === 1;
    await page.keyboard.press('Escape');
    return result;
  };
  const ui = { desktop: await inspectUi({ width: 1440, height: 900 }), mobile: await inspectUi({ width: 390, height: 844 }) };
  ui.ok = Object.values(ui).filter(value => typeof value === 'object').every(result => result.toolbox
    && result.category === 'Surface / Geology' && result.geometry && result.quickCreate
    && result.expected.every(key => result.keys.includes(key)));

  const visual = { runs: [], ok: true };
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
          dist: distance, target: [0, 0, 0] }; shadeMode = 1; syncDisplayState(); const canvas = document.querySelector('#gl'); canvas.width = 960; canvas.height = 540;
          gl.viewport(0, 0, 960, 540); renderGL(); gl.finish(); const pixels = new Uint8Array(960 * 540 * 4);
          gl.readPixels(0, 0, 960, 540, gl.RGBA, gl.UNSIGNED_BYTE, pixels); return { pixels, png: canvas.toDataURL('image/png') }; };
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
          channelsValid: after.every(value => Number.isInteger(value) && value >= 0 && value <= 255), png: treatmentCapture.png };
      }, { lattice, style, distance: view[1], flat: MUTATION === 'flat-render' });
      result.view = view[0]; result.ok = result.terrainPixels >= 10000 && result.changedFraction >= .01 && result.channelsValid;
      visual.runs.push(result); visual.ok &&= result.ok;
      if (MUTATION !== 'flat-render') {
        writeFileSync(path.join(evidenceDir, `surface-${style}-${lattice}-${view[0]}.png`), Buffer.from(result.png.split(',')[1], 'base64'));
      }
      delete result.png;
    }
  }
  if (MUTATION === 'flat-render') analytic.mutationReached = VISUAL && !visual.ok;

  const manifestOk = measured.manifest && Object.values(measured.manifest).every(Boolean);
  const ok = measured.registered && measured.category === 'surface'
    && JSON.stringify(measured.inputs) === JSON.stringify(['In', 'Mask'])
    && JSON.stringify(measured.styles) === JSON.stringify(STYLES)
    && measured.styleDefault === 'roughen' && manifestOk && measured.copyHonest && analytic.ok && ui.ok && visual.ok && !errors.length;
  console.log(`surface registration registered=${measured.registered} styles=${measured.styles?.length || 0} manifest=${manifestOk ? 'pass' : 'fail'} latticeRuns=${analytic.runs.length} samples=${analytic.runs.reduce((sum, run) => sum + run.samples, 0)} mutationReached=${analytic.mutationReached}`);
  if (analytic.mutation) console.log(`MUTATION ${analytic.mutation} violated ${analytic.violatedFormula}`);
  if (!SUMMARY) console.log(JSON.stringify({ measured, analytic, ui, visual, errors, ok }, null, 2));
  else if (VISUAL) console.log(`visual runs=${visual.runs.length} minTerrain=${Math.min(...visual.runs.map(run => run.terrainPixels))} minChanged=${Math.min(...visual.runs.map(run => run.changedFraction))}`);
  await browser.close();
  process.exit(ok ? 0 : 1);
})().catch(error => { console.error('FATAL', error); process.exit(2); });