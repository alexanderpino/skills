// Terrain-aware Wind regression: physical vector contract, ridge acceleration / lee shelter,
// valley channeling, mass-consistency, regional overrides, visualization, and Snow consumption.
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));
const HEIGHTMAP = process.env.STUDIO_HEIGHTMAP || '';
const HEIGHTMAP_SIZE = Number(process.env.STUDIO_HEIGHTMAP_SIZE || 0);

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(900);

  const report = await page.evaluate(() => {
    const n = 96, N = n * n;
    const def = { ...terrainDef, scale: 5000, height: 1200, baseElevation: 0,
      windDirection: 270, windSpeed: 12, lattice: 'square' };
    const defaults = type => {
      const out = {};
      TYPES[type].params.forEach(p => { out[p.key] = p.def; });
      return out;
    };
    const mean = (a, predicate) => {
      let sum = 0, count = 0;
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        if (!predicate(x, y)) continue;
        sum += a[y * n + x]; count++;
      }
      return sum / Math.max(1, count);
    };

    const flat = new Float32Array(N);
    const baseParams = { ...defaults('d_wind'), speedUp: 0, shelter: 0, channeling: 0,
      consistency: 'off' };
    const flatWind = simulateTerrainWind(flat, baseParams, { res: n, terrainDef: def });

    // A north-south ridge crossed by a west wind: accelerate on the west face, shelter the east.
    const ridge = new Float32Array(N);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      const q = (x / (n - 1) - .5) / .075;
      ridge[y * n + x] = Math.exp(-q * q);
    }
    const ridgeParams = { ...defaults('d_wind'), speedUp: .85, shelter: .8, channeling: 0,
      consistency: 'off', reach: 1400 };
    const ridgeWind = simulateTerrainWind(ridge, ridgeParams, { res: n, terrainDef: def });
    const upstream = mean(ridgeWind.speed, x => x > 8 && x < 23);
    const windward = mean(ridgeWind.speed, x => x > 34 && x < 45);
    const lee = mean(ridgeWind.speed, x => x > 52 && x < 68);

    // A north-south valley should turn an oblique regional wind toward its long axis.
    const valley = new Float32Array(N);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      const q = Math.abs(x / (n - 1) - .5) / .5;
      valley[y * n + x] = q * q;
    }
    const valleyDef = { ...def, windDirection: 315 };
    const valleyWind = simulateTerrainWind(valley, { ...defaults('d_wind'), speedUp: 0,
      shelter: 0, channeling: 1, consistency: 'off' }, { res: n, terrainDef: valleyDef });
    const centreU = mean(valleyWind.u, x => x > 43 && x < 53);
    const centreV = mean(valleyWind.v, x => x > 43 && x < 53);

    const projected = simulateTerrainWind(ridge, { ...ridgeParams, consistency: 'on' },
      { res: n, terrainDef: def });

    // One reusable biome/region mask overrides the physical direction and speed without touching
    // the cells outside it.
    const baseField = tagWindField(flatWind.encoded, flatWind.u, flatWind.v, flatWind.speed,
      { heightField: flat });
    const mask = new Float32Array(N);
    for (let y = 0; y < n; y++) for (let x = n >> 1; x < n; x++) mask[y * n + x] = 1;
    const modifiedNode = {};
    // Preserve-exactly mode: the authored override must hold to 1e-3 on both sides of the mask
    // (and the divergence the seam introduces is knowingly kept - that is this mode's contract).
    const modifiedField = TYPES.d_windmodify.eval({ direction: 0, speed: 20, amount: 1, consistency: 'off' },
      [baseField, null, mask], modifiedNode);
    const modified = windVectorFromField(modifiedField);
    const leftU = mean(modified.u, x => x < n / 2 - 2);
    const leftV = mean(modified.v, x => x < n / 2 - 2);
    const rightU = mean(modified.u, x => x > n / 2 + 2);
    const rightV = mean(modified.v, x => x > n / 2 + 2);
    // Project mode (the default): the same hard seam must LOWER divergence, not raise it — the
    // pre-fix node measured +39% at this exact seam and stamped before/after INVERTED. The
    // authored target holds approximately in the region interior (conservation bleeds flow
    // across the seam; that is the mode's documented price).
    const modifiedOnNode = {};
    const modifiedOnField = TYPES.d_windmodify.eval({ direction: 0, speed: 20, amount: 1 },
      [baseField, null, mask], modifiedOnNode);
    const modifiedOnMeta = fieldMetadata(modifiedOnField);
    const modifiedOnVec = windVectorFromField(modifiedOnField);
    const regionalProjected = {
      before: modifiedOnMeta.divergenceRmsBefore, after: modifiedOnMeta.divergenceRmsAfter,
      insideV: mean(modifiedOnVec.v, x => x > n / 2 + 6),
    };

    // Snow must consume the vector field, not merely acknowledge the new socket.
    const cold = new Float32Array(N).fill(-12), shadow = new Float32Array(N).fill(1);
    const exposure = new Float32Array(N);
    const east = simulateTerrainWind(ridge, { ...ridgeParams, consistency: 'off' },
      { res: n, terrainDef: { ...def, windSpeed: 28, windDirection: 270 } });
    const west = simulateTerrainWind(ridge, { ...ridgeParams, consistency: 'off' },
      { res: n, terrainDef: { ...def, windSpeed: 28, windDirection: 90 } });
    const snowParams = { snowfall: 1, meltDays: 0, meltRate: 0, repose: 38, adhesion: 0,
      iterations: 0, settle: .5, windStrength: 0, windDirection: 0 };
    const snowEast = simulateSnowLayer(ridge, snowParams, { res: n, terrainDef: def,
      temperatureC: cold, solarShadow: shadow, solarExposure: exposure, wind: east });
    const snowWest = simulateSnowLayer(ridge, snowParams, { res: n, terrainDef: def,
      temperatureC: cold, solarShadow: shadow, solarExposure: exposure, wind: west });
    let snowDifference = 0;
    for (let i = 0; i < N; i++) snowDifference += Math.abs(snowEast.depthM[i] - snowWest.depthM[i]);

    const windDef = TYPES.d_wind, modifyDef = TYPES.d_windmodify, snowDef = TYPES.snow;
    const defaultWindNode = nodes.find(n => n.type === 'd_wind');
    const defaultSnowNode = nodes.find(n => n.type === 'snow');
    const defaultWindEdge = defaultWindNode && defaultSnowNode
      && edges.find(e => e.from === defaultWindNode.id && e.to === defaultSnowNode.id && e.slot === 2);
    previewMode = 'selected'; select(defaultWindNode); shadeMode = 7; refreshPreview();
    const ui = { exists: false, hasSync: typeof syncWindReadout === 'function' };
    if (ui.hasSync) {
      const saved = {
        scene, previewMode, selected, az: cam.az, target: [...cam.target],
        direction: terrainDef.windDirection, speed: terrainDef.windSpeed,
      };
      const count = RES * RES, u = new Float32Array(count).fill(18);
      const v = new Float32Array(count), speed = new Float32Array(count).fill(18);
      const encoded = new Float32Array(count).fill(18 / WIND_MAX_MPS);
      const field = tagWindField(encoded, u, v, speed, { baseDirection: 270, baseSpeed: 18 });
      previewMode = 'output'; scene = { snow: { windField: field } };
      cam.target = [0, 0, 0]; cam.az = .2; syncWindReadout();
      const root = document.querySelector('#windReadout');
      const arrow = document.querySelector('#windIndicatorArrow');
      ui.exists = !!root && !!arrow;
      ui.fieldSource = root && root.dataset.source;
      ui.fieldSpeed = document.querySelector('#windSpeed')?.textContent || '';
      ui.fieldBearing = document.querySelector('#windBearing')?.textContent || '';
      ui.fieldAria = root?.getAttribute('aria-label') || '';
      ui.firstTransform = arrow?.style.transform || '';
      cam.az = 1.1; syncWindReadout();
      ui.orbitTransform = arrow?.style.transform || '';
      scene = {}; terrainDef.windDirection = 300; terrainDef.windSpeed = 10; syncWindReadout();
      ui.fallbackSource = root && root.dataset.source;
      ui.fallbackSpeed = document.querySelector('#windSpeed')?.textContent || '';
      ui.fallbackBearing = document.querySelector('#windBearing')?.textContent || '';
      scene = saved.scene; previewMode = saved.previewMode; selected = saved.selected;
      cam.az = saved.az; cam.target = saved.target;
      terrainDef.windDirection = saved.direction; terrainDef.windSpeed = saved.speed;
      syncWindReadout();
    }
    return {
      contract: {
        terrainDirection: terrainDef.windDirection,
        terrainSpeed: terrainDef.windSpeed,
        windInputs: windDef.ins,
        modifyInputs: modifyDef.ins,
        snowInputs: snowDef.ins,
        kind: fieldMetadata(modifiedField).kind,
        unit: fieldMetadata(modifiedField).unit,
      },
      flat: {
        meanU: mean(flatWind.u, () => true), meanV: mean(flatWind.v, () => true),
        meanSpeed: mean(flatWind.speed, () => true),
      },
      ridge: { upstream, windward, lee },
      valley: { centreU, centreV, alignment: Math.abs(centreV) / Math.max(.001, Math.abs(centreU)) },
      consistency: {
        before: projected.divergenceRmsBefore,
        after: projected.divergenceRmsAfter,
      },
      regional: { leftU, leftV, rightU, rightV },
      regionalProjected,
      snow: {
        eastSource: snowEast.windSource,
        westSource: snowWest.windSource,
        difference: snowDifference,
        volumeRatio: snowEast.volumeM3 / Math.max(1e-9, snowWest.volumeM3),
      },
      visualization: {
        shade: SHADE.includes('Wind'),
        option: !!document.querySelector('#shadeSel option[value="7"]'),
        composite: satComposite,
      },
      defaultGraph: {
        connected: !!defaultWindEdge,
        windKind: defaultWindNode && fieldMetadata(defaultWindNode._field).kind,
        snowSource: defaultSnowNode && defaultSnowNode._snowLayer.windSource,
        serializedDirection: graphSnapshot().terrainDef.windDirection,
        serializedSpeed: graphSnapshot().terrainDef.windSpeed,
      },
      ui,
    };
  });

  const hudLayout = await page.evaluate(() => {
    const box = id => {
      const el = document.querySelector(id), r = el && el.getBoundingClientRect();
      return r && { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
    };
    const wind = box('#windReadout'), compass = box('#viewportCompass'), climate = box('#climateReadout');
    const overlaps = (a, b) => !!a && !!b && a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
    return {
      wind, compass, climate,
      visible: !!wind && wind.width > 0 && wind.height > 0,
      overlapsCompass: overlaps(wind, compass),
      overlapsClimate: overlaps(wind, climate),
    };
  });
  await page.screenshot({ path: path.resolve(__dirname, '_shot_wind_hud.png') });
  await page.setViewportSize({ width: 680, height: 720 });
  await page.waitForTimeout(150);
  const compactHud = await page.evaluate(() => {
    const root = document.querySelector('#windReadout'), speed = document.querySelector('#windSpeed');
    const bearing = document.querySelector('#windBearing'), r = root && root.getBoundingClientRect();
    return {
      visible: !!r && r.width > 0 && r.height > 0 && getComputedStyle(root).display !== 'none',
      speedVisible: !!speed && getComputedStyle(speed).display !== 'none',
      bearingCollapsed: !!bearing && getComputedStyle(bearing).display === 'none',
      viewportWidth: innerWidth,
    };
  });
  await page.setViewportSize({ width: 1280, height: 820 });

  let heightmap = null;
  if (HEIGHTMAP) {
    if (!fs.existsSync(HEIGHTMAP)) throw new Error(`STUDIO_HEIGHTMAP does not exist: ${HEIGHTMAP}`);
    await page.evaluate(() => {
      importTarget = makeNode('import', 80, 80);
      select(importTarget);
    });
    await page.locator('#fileInput').setInputFiles(HEIGHTMAP);
    await page.waitForFunction(() => importTarget && importTarget._dem && importTarget._demImg);
    heightmap = await page.evaluate(() => {
      const dem = importTarget._dem, n = Math.round(Math.sqrt(dem.length)), N = dem.length;
      terrainDef.scale = 8000;
      terrainDef.height = 2500;
      terrainDef.windDirection = 300;
      terrainDef.windSpeed = 10;
      const params = {};
      TYPES.d_wind.params.forEach(p => { params[p.key] = p.def; });
      const windNode = {}, field = TYPES.d_wind.eval(params, [dem], windNode);
      const wind = windVectorFromField(field), meta = fieldMetadata(field);
      const mask = new Float32Array(N);
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++)
        mask[y * n + x] = smooth(clamp((x / (n - 1) - .45) / .2, 0, 1));
      const modifyNode = {};
      const modifiedField = TYPES.d_windmodify.eval({ direction: 0, speed: 20, amount: 1 },
        [field, null, mask], modifyNode);
      const modified = windVectorFromField(modifiedField);
      let min = Infinity, max = -Infinity, sum = 0, sum2 = 0, finite = 0;
      let outsideDelta = 0, insideU = 0, insideV = 0, insideCount = 0;
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        const i = y * n + x, s = wind.speed[i];
        if (Number.isFinite(s) && Number.isFinite(wind.u[i]) && Number.isFinite(wind.v[i])) finite++;
        min = Math.min(min, s); max = Math.max(max, s); sum += s; sum2 += s * s;
        if (mask[i] === 0) outsideDelta = Math.max(outsideDelta,
          Math.hypot(modified.u[i] - wind.u[i], modified.v[i] - wind.v[i]));
        if (mask[i] === 1) { insideU += modified.u[i]; insideV += modified.v[i]; insideCount++; }
      }
      const mean = sum / N;
      return {
        file: importTarget._demImg.currentSrc || importTarget._demImg.src,
        nativeWidth: importTarget._demImg.naturalWidth,
        nativeHeight: importTarget._demImg.naturalHeight,
        workingResolution: n,
        samples: N,
        physicalKind: meta.kind,
        finite,
        speed: { min, mean, max, stddev: Math.sqrt(Math.max(0, sum2 / N - mean * mean)) },
        divergence: { before: meta.divergenceRmsBefore, after: meta.divergenceRmsAfter },
        regional: {
          outsideMaxDelta: outsideDelta,
          insideMeanU: insideU / Math.max(1, insideCount),
          insideMeanV: insideV / Math.max(1, insideCount),
        },
      };
    });
  }

  const c = report.contract;
  const heightmapOk = !heightmap || ((!HEIGHTMAP_SIZE
      || (heightmap.nativeWidth === HEIGHTMAP_SIZE && heightmap.nativeHeight === HEIGHTMAP_SIZE))
    && heightmap.samples === heightmap.workingResolution ** 2
    && heightmap.physicalKind === 'wind' && heightmap.finite === heightmap.samples
    && heightmap.speed.stddev > .05 && heightmap.speed.max > heightmap.speed.min
    && heightmap.divergence.after < heightmap.divergence.before
    && heightmap.regional.outsideMaxDelta < 1e-5
    && Math.abs(heightmap.regional.insideMeanU) < 1e-3
    && Math.abs(heightmap.regional.insideMeanV - 20) < 1e-3);
  const ok = c.terrainDirection === 300 && c.terrainSpeed === 10
    && c.windInputs.join('|') === 'Height'
    && c.modifyInputs.join('|') === 'Wind|Driver|Mask'
    && c.snowInputs.join('|') === 'In|Temperature|Wind'
    && c.kind === 'wind' && c.unit === 'm/s'
    && Math.abs(report.flat.meanU - 12) < 1e-4
    && Math.abs(report.flat.meanV) < 1e-4
    && Math.abs(report.flat.meanSpeed - 12) < 1e-4
    && report.ridge.windward > report.ridge.upstream * 1.05
    && report.ridge.lee < report.ridge.upstream * .85
    && report.valley.alignment > 1.2
    && report.consistency.before > 1e-5
    && report.consistency.after < report.consistency.before * .35 /* exact-adjoint + 2 V-cycles:
        measured 0.236; the old central/compact stencil pair CONVERGED at ~0.5 (Nyquist-blind) */
    && Math.abs(report.regional.leftU - 12) < 1e-3
    && Math.abs(report.regional.leftV) < 1e-3
    && Math.abs(report.regional.rightU) < 1e-3
    && Math.abs(report.regional.rightV - 20) < 1e-3
    && report.regionalProjected.after < report.regionalProjected.before
    && Math.abs(report.regionalProjected.insideV - 20) < 20 * .3
    && report.snow.eastSource === 'field' && report.snow.westSource === 'field'
    && report.snow.difference > 1 && Math.abs(report.snow.volumeRatio - 1) < 1e-4
    && report.visualization.shade && report.visualization.option && report.visualization.composite === 1
    && report.defaultGraph.connected && report.defaultGraph.windKind === 'wind'
    && report.defaultGraph.snowSource === 'field'
    && report.defaultGraph.serializedDirection === 300 && report.defaultGraph.serializedSpeed === 10
    && report.ui.exists && report.ui.hasSync
    && report.ui.fieldSource === 'field'
    && report.ui.fieldSpeed.includes('18.0 m/s') && report.ui.fieldBearing.includes('270° from')
    && report.ui.fieldAria.includes('blowing toward 90 degrees')
    && report.ui.firstTransform !== report.ui.orbitTransform
    && report.ui.fallbackSource === 'fallback'
    && report.ui.fallbackSpeed.includes('10.0 m/s') && report.ui.fallbackBearing.includes('300° from')
    && hudLayout.visible && !hudLayout.overlapsCompass && !hudLayout.overlapsClimate
    && compactHud.visible && compactHud.speedVisible && compactHud.bearingCollapsed
    && heightmapOk && !errors.length;
  if (!heightmap) console.log('SKIPPED real-DEM block (vacuous-green otherwise): set '
    + 'STUDIO_HEIGHTMAP to arm the divergence + regional-seam gates on real terrain');
  console.log(JSON.stringify({ report, hudLayout, compactHud, heightmap, errors, ok }, null, 2));
  await browser.close();
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
