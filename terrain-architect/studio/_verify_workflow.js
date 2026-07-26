// Authoring workflow: side/stacked layouts, intermediate preview, undo/redo, plan/fullscreen,
// GPU hydraulic stability, and a high-resolution interactive performance smoke test.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const URL = 'file://' + path.resolve(__dirname, 'index.html');
(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1200);

  const rects=()=>page.evaluate(()=>Object.fromEntries(['graphwrap','viewport','props'].map(id=>{
    const r=document.querySelector('#'+id).getBoundingClientRect();return[id,{x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}];
  })));
  const side=await rects();
  await page.screenshot({path:path.resolve(__dirname,'_shot_workflow_side.png')});
  await page.locator('#layoutBtn').click();await page.waitForTimeout(150);
  const stacked=await rects();
  await page.screenshot({path:path.resolve(__dirname,'_shot_workflow_stacked.png')});

  const interaction=await page.evaluate(()=>{
    const before=nodes.length;
    const added=makeNode('perlin',120,120);select(added);evalGraph();
    const afterAdd=nodes.length;undoGraph();const afterUndo=nodes.length;redoGraph();const afterRedo=nodes.length;
    const hyd=nodes.find(n=>n.type==='hydraulic');select(hyd);previewMode='selected';refreshPreview();
    const selectedPreview=activePreviewNode()===hyd&&curField===hyd._field;
    const finite=hyd._field&&hyd._field.every(Number.isFinite);
    previewMode='output';refreshPreview();
    return{before,afterAdd,afterUndo,afterRedo,selectedPreview,finite,gpu:GPU.init()};
  });
  await page.locator('#viewBtn').click();
  const plan=await page.evaluate(()=>({planView,el:+cam.el.toFixed(2),label:document.querySelector('#viewBtn').textContent}));
  await page.locator('#fullscreenBtn').click();await page.waitForTimeout(100);
  const fullscreen=await page.evaluate(()=>document.fullscreenElement&&document.fullscreenElement.id);
  if(fullscreen)await page.locator('#fullscreenBtn').click();

  const perf=await page.evaluate(()=>{
    BUILD_QUALITY='interactive';RES=1024;buildIndex();nodes.forEach(n=>{n._dirty=true;n._thumb=null;});
    const t=performance.now();evalGraph();const total=Math.round(performance.now()-t);
    return{total,hydraulic:Math.round(nodes.find(n=>n.type==='hydraulic')._lastMs),
      thermal:Math.round(nodes.find(n=>n.type==='thermal')._lastMs),
      finite:outputNode()._field.every(Number.isFinite)};
  });
  const ok=side.graphwrap.h>side.viewport.h
    && stacked.viewport.y<stacked.graphwrap.y
    && stacked.viewport.x===stacked.graphwrap.x
    && interaction.afterAdd===interaction.before+1
    && interaction.afterUndo===interaction.before
    && interaction.afterRedo===interaction.before+1
    && interaction.selectedPreview&&interaction.finite&&perf.finite
    && plan.planView&&plan.label==='Hero'
    && fullscreen==='viewport'
    && !errors.length;
  console.log(JSON.stringify({side,stacked,interaction,plan,fullscreen,perf,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
