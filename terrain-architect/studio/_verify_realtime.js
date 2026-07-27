// Live-update regression: property drags coalesce to one frame, SatMap recolours
// without rebuilding terrain geometry, and height edits still rebuild geometry.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(URL, { waitUntil: 'load' });
  await page.waitForTimeout(1400);

  const result = await page.evaluate(async () => {
    const uploads = [];
    let boundBuffer = null;
    const originalBindBuffer = gl.bindBuffer.bind(gl);
    const originalBufferData = gl.bufferData.bind(gl);
    gl.bindBuffer = function(target, buffer) {
      if (target === gl.ARRAY_BUFFER) boundBuffer = buffer;
      return originalBindBuffer(target, buffer);
    };
    gl.bufferData = function(target, data, usage) {
      const entry = Object.entries(buffers).find(([, value]) => value === boundBuffer);
      uploads.push({ buffer: entry ? entry[0] : 'unknown',
        bytes: data && typeof data.byteLength === 'number' ? data.byteLength : 0 });
      return originalBufferData(target, data, usage);
    };
    const waitFrames = n => new Promise(resolve => {
      const next = () => n-- > 0 ? requestAnimationFrame(next) : resolve();
      requestAnimationFrame(next);
    });
    const waitBuild = async () => {
      // Progressive evaluation starts on the next frame and may span several more.
      // Wait for that run to begin, then for its aria-busy contract to clear.
      await waitFrames(2);
      const deadline = performance.now() + 12000;
      while ((evalFrame || document.querySelector('#buildBtn').hasAttribute('aria-busy')) && performance.now() < deadline)
        await waitFrames(1);
    };
    const edit = async (nd, key, values) => {
      selected = nd; buildProps(); uploads.length = 0;
      const fields = [...document.querySelectorAll('#pBody .field')];
      const field = fields.find(f => f.querySelector('label')?.textContent ===
        TYPES[nd.type].params.find(p => p.key === key).label);
      const slider = field && field.querySelector('input[type=range]');
      if (!slider) throw new Error(`missing slider ${nd.type}.${key}`);
      const beforeField = activePreviewNode()._field;
      const t0 = performance.now();
      for (const value of values) {
        slider.value = value;
        slider.dispatchEvent(new Event('input', { bubbles: true }));
      }
      const dispatchMs = performance.now() - t0;
      await waitBuild();
      return {
        dispatchMs,
        settleMs: performance.now() - t0,
        statTime: document.querySelector('#statTime').textContent,
        uploads: uploads.slice(),
        fieldStable: beforeField === activePreviewNode()._field,
        finalValue: nd.params[key]
      };
    };
    const editGlobalWater = async values => {
      uploads.length=0;const slider=document.querySelector('#waterStrength'),beforeField=activePreviewNode()._field;
      const t0=performance.now();for(const value of values){slider.value=value;slider.dispatchEvent(new Event('input',{bubbles:true}));}
      await waitFrames(3);return{dispatchMs:performance.now()-t0,uploads:uploads.slice(),
        fieldStable:beforeField===activePreviewNode()._field,finalValue:waterLook.strength};
    };
    const sat = nodes.find(n => n.type === 'satmap');
    const erosion = nodes.find(n => n.type === 'colorerosion');
    const weather = nodes.find(n => n.type === 'weathering');
    const base = nodes.find(n => n.type === 'perlin');
    return {
      sat: await edit(sat, 'hue', ['.1','.2','.3','.4','.5']),
      erosion: await edit(erosion, 'density', ['.3','.4','.5']),
      weather: await edit(weather, 'amount', ['.35','.45']),
      water: await editGlobalWater(['.4','.7']),
      height: await edit(base, 'freq', ['3.2','3.4'])
    };
  });

  console.log('live update:', JSON.stringify(result));
  console.log('ERRORS', errors.length ? JSON.stringify(errors) : 'none');
  await browser.close();

  const materialStable = ['sat','erosion','weather','water'].every(k => result[k].fieldStable);
  const valid = result.sat.dispatchMs < 20
    && materialStable
    && result.sat.uploads.length === 1
    && result.sat.uploads[0].buffer === 'col'
    && result.sat.finalValue === .5
    && !result.height.fieldStable
    && ['pos','nrm','hgt','drive','col'].every(name => result.height.uploads.some(u => u.buffer === name));
  process.exit(errors.length || !valid ? 1 : 0);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
