// Water topology is node-authored; global rendering owns its patterned fluid surface and refraction.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox'] });
  const page = await browser.newPage({ viewport:{ width:1440, height:900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(URL, { waitUntil:'load' });
  await page.waitForTimeout(1200);
  await page.locator('#layoutBtn').click();

  const report = await page.evaluate(() => {
    const water = nodes.find(n => n.type === 'water');
    Object.assign(water.params, { mode:'sea', level:.46, shoreSmooth:1.35, foam:.18 });
    Object.assign(waterLook, {pattern:'wind',strength:.72,scale:.8,speed:.75,refraction:.55});
    selected = water;
    nodes.forEach(n => n._dirty = true);
    evalGraph();
    cam = { target:[0,.24,0], dist:1.48, az:.62, el:.38 };
    buildProps();

    const frame = (pattern, smooth) => {
      waterLook.pattern = pattern;
      scene.water.shoreSmooth = smooth;
      uTime = .7;
      renderGL();
      gl.finish();
      const px = new Uint8Array(glc.width * glc.height * 4);
      gl.readPixels(0, 0, glc.width, glc.height, gl.RGBA, gl.UNSIGNED_BYTE, px);
      return px;
    };
    const none = frame('none', 1.35), patterned = frame('wind', 1.35), hard = frame('wind', 0);
    let patternDelta = 0, smoothingDelta = 0, patternPixels = 0, smoothingPixels = 0, samples = 0;
    for (let i = 0; i < none.length; i += 16) {
      const dp = Math.abs(none[i]-patterned[i])+Math.abs(none[i+1]-patterned[i+1])+Math.abs(none[i+2]-patterned[i+2]);
      const ds = Math.abs(hard[i]-patterned[i])+Math.abs(hard[i+1]-patterned[i+1])+Math.abs(hard[i+2]-patterned[i+2]);
      patternDelta += dp; smoothingDelta += ds; patternPixels += dp > 2; smoothingPixels += ds > 2; samples++;
    }
    // Regression: zero water depth is dry, not 50% coverage. Time may change, pixels may not.
    Object.assign(scene.water, { mode:'sea', level:0, shoreSmooth:1.35 });
    Object.assign(waterLook,{pattern:'wind',strength:1});
    refreshWater();
    const dryA = frame('wind', 1.35);
    uTime = 2.1; renderGL(); gl.finish();
    const dryB = new Uint8Array(glc.width * glc.height * 4);
    gl.readPixels(0, 0, glc.width, glc.height, gl.RGBA, gl.UNSIGNED_BYTE, dryB);
    let dryMotion = 0, dryChanged = 0;
    for (let i = 0; i < dryA.length; i += 16) {
      const d = Math.abs(dryA[i]-dryB[i])+Math.abs(dryA[i+1]-dryB[i+1])+Math.abs(dryA[i+2]-dryB[i+2]);
      dryMotion += d; dryChanged += d > 2;
    }
    dryMotion /= samples;
    Object.assign(scene.water, { mode:'sea', level:.46, shoreSmooth:1.35, foam:.18 });
    Object.assign(waterLook,{pattern:'wind',strength:.72,scale:.8,speed:.75});
    refreshWater();
    let shoreGuardMax=0,shorePairs=0,partialIce=0;
    for(let y=0;y<RES;y++)for(let x=0;x<RES;x++){
      const i=y*RES+x,wet=curWater[i]>curHgt[i]+1e-7;
      if(curWaterIce[i]>.02&&curWaterIce[i]<.98)partialIce++;
      if(!wet)continue;
      for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){
        const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=RES||yy>=RES)continue;
        const j=yy*RES+xx;if(curWater[j]>curHgt[j]+1e-7)continue;
        shorePairs++;shoreGuardMax=Math.max(shoreGuardMax,Math.abs(curWater[i]-curWater[j]));
      }
    }
    const waterNode=nodes.find(n=>n.type==='water'),temperatureEdge=waterNode&&inputEdge(waterNode.id,1);
    return {
      params:TYPES.water.params.map(p => p.key),
      inputs:TYPES.water.ins,
      temperatureConnected:!!temperatureEdge,
      patterns:[...document.querySelector('#waterPattern').options].map(o => o.value),
      globalControls:['waterPattern','waterStrength','waterScale','waterSpeed','waterRefraction'].every(id=>!!document.getElementById(id)),
      linked:!!waterProg && !!waterMaskProg && !!compProg && gl.getProgramParameter(waterProg,gl.LINK_STATUS)
        && gl.getProgramParameter(waterMaskProg,gl.LINK_STATUS) && gl.getProgramParameter(compProg,gl.LINK_STATUS),
      pattern:{ mean:patternDelta/samples, changed:patternPixels },
      smoothing:{ mean:smoothingDelta/samples, changed:smoothingPixels },
      dryField:{ motion:dryMotion, changed:dryChanged },
      shoreline:{pairs:shorePairs,maxSurfaceJump:shoreGuardMax},
      partialIce
    };
  });
  await page.waitForTimeout(250);
  await page.locator('#viewport').screenshot({ path:path.resolve(__dirname, '_shot_water_close.png') });

  const ok = report.linked
    && ['shoreSmooth','foam'].every(k => report.params.includes(k))
    && ['pattern','ripple','rippleScale','rippleSpeed'].every(k => !report.params.includes(k))
    && report.inputs.includes('Temperature')&&report.temperatureConnected
    && report.globalControls
    && report.patterns.join('|') === 'cross|wind|rings|none'
    && report.pattern.mean > .01 && report.pattern.changed > 64
    && report.smoothing.mean > .001 && report.smoothing.changed > 10
    && report.dryField.motion < .01 && report.dryField.changed <= 8
    && report.shoreline.pairs>0&&report.shoreline.maxSurfaceJump<1e-5
    && report.partialIce>0
    && !errors.length;
  console.log(JSON.stringify({ report, errors, ok }, null, 2));
  await browser.close();
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error('FATAL', e); process.exit(2); });
