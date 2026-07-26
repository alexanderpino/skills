// Renderer regression: scene-linear output, PBR/data views, look controls, SatMap breakup,
// animated water-ripple controls, shader health, and an image-level guard against the former chalk-white viewport.
const { chromium } = require('playwright-core');
const path = require('path');
const zlib = require('zlib');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');

function decodePng(buf) {
  if (buf.toString('ascii', 1, 4) !== 'PNG') throw new Error('not a PNG');
  let p = 8, w, h, type, depth, idat = [];
  while (p < buf.length) {
    const n = buf.readUInt32BE(p), tag = buf.toString('ascii', p + 4, p + 8), d = buf.subarray(p + 8, p + 8 + n);
    if (tag === 'IHDR') { w = d.readUInt32BE(0); h = d.readUInt32BE(4); depth = d[8]; type = d[9]; }
    if (tag === 'IDAT') idat.push(d);
    p += n + 12;
    if (tag === 'IEND') break;
  }
  if (depth !== 8 || (type !== 2 && type !== 6)) throw new Error(`expected RGB/RGBA8 PNG, got depth=${depth} type=${type}`);
  const channels = type === 6 ? 4 : 3;
  const src = zlib.inflateSync(Buffer.concat(idat)), stride = w * channels, out = Buffer.alloc(stride * h);
  let si = 0;
  const paeth = (a, b, c) => {
    const q = a + b - c, pa = Math.abs(q - a), pb = Math.abs(q - b), pc = Math.abs(q - c);
    return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
  };
  for (let y = 0; y < h; y++) {
    const filter = src[si++];
    for (let x = 0; x < stride; x++) {
      const raw = src[si++], a = x >= channels ? out[y * stride + x - channels] : 0;
      const b = y ? out[(y - 1) * stride + x] : 0;
      const c = y && x >= channels ? out[(y - 1) * stride + x - channels] : 0;
      out[y * stride + x] = (raw + (filter === 1 ? a : filter === 2 ? b : filter === 3 ? ((a + b) >> 1) : filter === 4 ? paeth(a, b, c) : 0)) & 255;
    }
  }
  return { w, h, channels, data: out };
}

function imageStats(png, r) {
  const rw=r.width??r.w,rh=r.height??r.h;
  const im = decodePng(png), x0 = Math.max(0, Math.round(r.x + 4)), x1 = Math.min(im.w, Math.round(r.x + rw - 4));
  const y0 = Math.max(0, Math.round(r.y + 42)), y1 = Math.min(im.h, Math.round(r.y + rh - 4));
  let n = 0, sum = 0, sum2 = 0, dark = 0, white = 0, sat = 0;
  for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
    const i = (y * im.w + x) * im.channels, R = im.data[i], G = im.data[i + 1], B = im.data[i + 2];
    const l = .2126 * R + .7152 * G + .0722 * B;
    n++; sum += l; sum2 += l * l; dark += l < 42; white += l > 238; sat += Math.max(R, G, B) - Math.min(R, G, B);
  }
  const mean = sum / n;
  return { mean:+mean.toFixed(2), std:+Math.sqrt(sum2 / n - mean * mean).toFixed(2),
    dark:+(dark / n).toFixed(4), nearWhite:+(white / n).toFixed(4), chroma:+(sat / n).toFixed(2) };
}

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(URL, { waitUntil:'load' }); await page.waitForTimeout(1400);
  await page.locator('#layoutBtn').click(); await page.waitForTimeout(200);
  await page.evaluate(() => { cam.dist = 2.15; cam.el = .58; cam.az = .72; });
  const rect = await page.locator('#viewport').boundingBox();

  const capture = async (value, name) => {
    await page.locator('#shadeSel').evaluate((el,v) => {
      el.value = v; el.dispatchEvent(new Event('change', { bubbles: true }));
    }, value); await page.waitForTimeout(180);
    const png = await page.screenshot({ path:path.resolve(__dirname, `_shot_render_${name}.png`) });
    return imageStats(png, rect);
  };
  const realistic = await capture('0', 'realistic');
  const clay = await capture('1', 'clay');
  const albedo = await capture('2', 'albedo');
  const normals = await capture('4', 'normals');
  const temperature = await capture('5', 'temperature');
  const sunShadow = await capture('6', 'sun_shadow');

  await page.locator('#shadeSel').evaluate(el => {
    el.value = '0'; el.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await page.locator('#exposure').evaluate((el) => { el.value = '-1'; el.dispatchEvent(new Event('input',{bubbles:true})); });
  await page.waitForTimeout(120); const lowExposure = imageStats(await page.screenshot(), rect);
  await page.locator('#exposure').evaluate((el) => { el.value = '1'; el.dispatchEvent(new Event('input',{bubbles:true})); });
  await page.waitForTimeout(120); const highExposure = imageStats(await page.screenshot(), rect);

  const diag = await page.evaluate(() => {
    const linked = p => !!p && gl.getProgramParameter(p, gl.LINK_STATUS);
    const roundtrip = c => {
      const l = c <= .04045 ? c / 12.92 : Math.pow((c + .055) / 1.055, 2.4);
      return l <= .0031308 ? l * 12.92 : 1.055 * Math.pow(l, 1 / 2.4) - .055;
    };
    const L = {driver:new Float32Array(RES*RES).fill(.5),reverse:'off',rangeLo:0,rangeHi:1,shift:0,
      gradient:'Temperate',mode:'1d',rough:'none'};
    let delta = 0;
    for (let i=0;i<RES*RES;i+=17) {
      const a=satLayerColor(L,i);L.rough='high';const b=satLayerColor(L,i);L.rough='none';
      delta += Math.abs(a[0]-b[0])+Math.abs(a[1]-b[1])+Math.abs(a[2]-b[2]);
    }
    const oldTime=uTime,oldRipple=waterLook.strength,oldSeaTemp=terrainDef.seaTemp;
    terrainDef.seaTemp=35;refreshWater(); // motion contract is liquid water; frozen standing water correctly has none
    const frame=(time,ripple)=>{
      waterLook.strength=ripple;uTime=time;renderGL();gl.finish();
      const px=new Uint8Array(glc.width*glc.height*4);gl.readPixels(0,0,glc.width,glc.height,gl.RGBA,gl.UNSIGNED_BYTE,px);return px;
    };
    const motionA=frame(0,.55),motionB=frame(1.5,.55),stillA=frame(0,0),stillB=frame(1.5,0);
    let motionSum=0,stillSum=0,changed=0,samples=0;
    for(let i=0;i<motionA.length;i+=16){const dm=Math.abs(motionA[i]-motionB[i])+Math.abs(motionA[i+1]-motionB[i+1])+Math.abs(motionA[i+2]-motionB[i+2]);
      motionSum+=dm;stillSum+=Math.abs(stillA[i]-stillB[i])+Math.abs(stillA[i+1]-stillB[i+1])+Math.abs(stillA[i+2]-stillB[i+2]);changed+=dm>2;samples++;}
    waterLook.strength=oldRipple;uTime=oldTime;terrainDef.seaTemp=oldSeaTemp;refreshWater();
    return {webgl2:gl instanceof WebGL2RenderingContext,deferred:USE_DEFERRED,
      linked:{terrain:linked(terrainProg),composite:linked(compProg),water:linked(waterProg)},
      styles:Array.from(document.querySelector('#shadeSel').options).map(o=>o.text),
      look:{exposure:renderLook.exposure,haze:renderLook.haze},
      srgbRoundtripError:Math.max(...[.02,.18,.5,.9].map(v=>Math.abs(v-roundtrip(v)))),
      satRoughnessDelta:delta,rippleMotion:{mean:motionSum/samples,stillMean:stillSum/samples,changed}};
  });
  const ok = diag.webgl2 && diag.deferred && Object.values(diag.linked).every(Boolean)
    && diag.styles.join('|') === 'Realistic|Clay|Albedo|Slope|Normals|Temperature|Sun shadow'
    && diag.srgbRoundtripError < 1e-6 && diag.satRoughnessDelta > 1
    && diag.rippleMotion.mean > diag.rippleMotion.stillMean + .01 && diag.rippleMotion.stillMean < .01 && diag.rippleMotion.changed > 20
    && realistic.std > 28 && realistic.nearWhite < .55 && realistic.chroma > 7
    && Math.abs(realistic.mean-clay.mean) > 2 && Math.abs(albedo.chroma-normals.chroma) > 4
    && temperature.std > 8 && temperature.chroma > 20 && sunShadow.std > 8
    && highExposure.mean > lowExposure.mean + 12 && !errors.length;
  console.log(JSON.stringify({diag,realistic,clay,albedo,normals,temperature,sunShadow,lowExposure,highExposure,errors,ok},null,2));
  await browser.close(); process.exit(ok?0:1);
})().catch(e => { console.error('FATAL',e); process.exit(2); });
