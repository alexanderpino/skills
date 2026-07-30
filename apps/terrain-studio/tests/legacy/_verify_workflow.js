// Authoring workflow: side/stacked layouts, intermediate preview, undo/redo, plan/fullscreen,
// GPU hydraulic stability, and a high-resolution interactive performance smoke test.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));
(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});
  await page.evaluate(()=>localStorage.removeItem('terrainStudioLayout'));
  await page.reload({waitUntil:'load'});await page.waitForTimeout(1200);

  const rects=()=>page.evaluate(()=>Object.fromEntries(['graphwrap','viewport','props'].map(id=>{
    const r=document.querySelector('#'+id).getBoundingClientRect();return[id,{x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}];
  })));
  const stacked=await rects();
  await page.screenshot({path:path.resolve(__dirname,'_shot_workflow_stacked.png')});
  await page.locator('#layoutBtn').click();await page.waitForTimeout(150);
  const side=await rects();
  await page.screenshot({path:path.resolve(__dirname,'_shot_workflow_side.png')});
  await page.reload({waitUntil:'load'});await page.waitForTimeout(1200);
  const savedSide=await rects();

  // BUILD THE DOCUMENT THIS FILE MEASURES. 31f5688 demoted the 18-node showcase to L0 - a 7-node
  // bedrock document (perlin, ridged, blend, d_height, heightmask, levels, output) - and this
  // oracle needs the erosion stack: the intermediate-preview gate previews a `hydraulic` node, and
  // the interactive perf smoke test times `hydraulic` and `thermal` specifically. Inherited, the
  // run died at `curField===hyd._field` with "Cannot read properties of undefined (reading
  // '_field')" - exit 2, measured.
  //
  // Placed AFTER the last reload deliberately: the layout gates above (stacked/side/savedSide) are
  // pure geometry and must see the app's own persisted-layout boot path, unperturbed.
  //
  // evalGraph() is sufficient here; the app's own #buildBtn is NOT needed. The one renderer cache
  // this file reads is curField, and it is written by the refreshPreview() call two statements
  // before the assertion that reads it - so it cannot be inherited from L0. evalGraph() also ends
  // in finishGraphEvaluation() -> updateViewport(), which rebuilds the viewport caches against the
  // new document anyway. Nothing here samples pixels, water, or the wireframe: the two screenshots
  // are layout artefacts, and every term of `ok` is geometry, node count, camera state, button
  // state, or field finiteness. Going through evalGraphProgressive would only add wall clock.
  await page.evaluate(()=>{
    nodes.length=0;edges.length=0;uid=1;selected=null;selectedEdge=null;
    showcaseGraph();evalGraph();
    // Absence of evidence is failure: name the missing node instead of handing the gates an
    // undefined that reads as a silent pass two indirections later.
    for(const t of ['hydraulic','thermal','output'])
      if(!nodes.find(n=>n.type===t))throw new Error('SETUP FAILURE: no '+t+' node after showcaseGraph()');
  });

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
  const plan=await page.evaluate(()=>({planView,el:+cam.el.toFixed(2),
    state:document.querySelector('#viewBtn').dataset.state,
    label:document.querySelector('#viewBtn').getAttribute('aria-label')}));
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
  const ok=stacked.viewport.y<stacked.graphwrap.y
    && stacked.viewport.x===stacked.graphwrap.x
    && side.graphwrap.h>side.viewport.h
    && savedSide.graphwrap.h===side.graphwrap.h
    && savedSide.viewport.x===side.viewport.x
    && interaction.afterAdd===interaction.before+1
    && interaction.afterUndo===interaction.before
    && interaction.afterRedo===interaction.before+1
    && interaction.selectedPreview&&interaction.finite&&perf.finite
    && plan.planView&&plan.state==='plan'&&plan.label==='Return to hero camera'
    && fullscreen==='viewport'
    && !errors.length;
  console.log(JSON.stringify({stackedDefault:stacked,side,savedSide,interaction,plan,fullscreen,perf,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
