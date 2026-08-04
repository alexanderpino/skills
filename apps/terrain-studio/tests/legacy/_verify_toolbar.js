// Scalable toolbar regression: profile popover, queued high-res target, command search,
// graph locator, keyboard access, and compact-width overflow.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

(async () => {
  const browser=await chromium.launch({executablePath:EXE,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:900}});
  const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1800);

  // BUILD THE DOCUMENT THIS FILE MEASURES. D7 made the opening document L0 (perlin, ridged, blend,
  // d_height, heightmask, levels, output) and this oracle's graph-locator gate drives the "Locate
  // Water node" command. locateNode() (legacy.js:6015) exits with a toast when the type is absent,
  // so inherited the click was a silent no-op: `located.selected` read 'perlin' - the L0 default
  // selection, untouched - against an expected 'water'. showcaseGraph() is the 18-node graph that
  // used to open, and it still carries water/satmap.
  //
  // evalGraph() is enough here; the app's own #buildBtn path is NOT needed. This oracle asserts
  // only chip text, selection type and topbar geometry - it never reads pixels, water surface or
  // curHgt/curFilled/curAccum. Its one renderer touch is updateViewport(curField) in the lattice
  // probe below, and evalGraph() ends in finishGraphEvaluation() which itself calls updateViewport
  // (legacy.js:3155), so curField is rebuilt from the new document rather than left holding L0's.
  // This is byte-for-byte the app's own boot path: defaultGraph(); evalGraph(); (legacy.js:6538).
  // It also has to happen HERE, before #resSel is moved to full detail on a 2048-sample document:
  // that queues a resolution without
  // rebuilding (legacy.js:6051) and the "· Queued" it leaves in the chip is load-bearing for the
  // lattice assertions, so no build may run after it.
  const setup=await page.evaluate(()=>{
    nodes.length=0;edges.length=0;uid=1;selected=null;selectedEdge=null;
    showcaseGraph();evalGraph();
    const w=nodes.find(n=>n.type==='water');
    if(!w)throw new Error('SETUP FAILURE: no water node after showcaseGraph()');
    // Absence of evidence is failure: if the render caches did not follow the swap, every later
    // updateViewport(curField) would be replaying the previous document.
    if(!curField)throw new Error('SETUP FAILURE: curField null after evalGraph() - render caches did not follow the new document');
    return {count:nodes.length,edges:edges.length,selected:selected&&selected.type,curFieldLen:curField.length};
  });

  const initial=await page.evaluate(()=>({res:RES,target:TARGET_RES,profile:profileRes.textContent,overflow:topbar.scrollWidth-topbar.clientWidth,
    resolutions:[...resSel.options].map(o=>+o.value)}));
  await page.locator('#buildProfileBtn').click();
  const profileOpen=await page.evaluate(()=>({open:!buildSettings.hidden,controls:['resSel','qualitySel','gpuBtn','scaleBtn'].every(id=>!!document.getElementById(id))}));
  // #resSel now carries FRACTIONS of the document's own grid, not absolute sample counts — the old
  // absolute list let a 1024 selection halve the sample spacing of a 512-sample world, which is a
  // different simulation presented as a preview setting. The queue-on-large behaviour is unchanged
  // and still worth gating, so the document is set large and full detail is selected to reach it.
  await page.evaluate(() => { setDocumentSamples(2048); });
  await page.locator('#resSel').selectOption('1');
  const queued=await page.evaluate(()=>({active:RES,target:TARGET_RES,auto:AUTO,detail:profileDetail.textContent}));
  await page.screenshot({path:path.resolve(__dirname,'_shot_toolbar_profile.png')});
  await page.locator('#commandBtn').click();
  await page.locator('#commandSearch').fill('water');
  const filtered=await page.evaluate(()=>({profileClosed:buildSettings.hidden,menu:!commandMenu.hidden,
    visible:[...document.querySelectorAll('.command-item:not(.hidden)')].map(x=>x.dataset.action||x.id)}));
  await page.locator('.command-item[data-action="find-water"]').click();await page.waitForTimeout(80);
  const located=await page.evaluate(()=>({selected:selected&&selected.type,menuClosed:commandMenu.hidden}));
  await page.keyboard.press('Control+K');await page.waitForTimeout(50);
  const keyboardOpen=await page.evaluate(()=>!commandMenu.hidden);
  await page.keyboard.press('Escape');
  await page.setViewportSize({width:760,height:720});await page.waitForTimeout(120);
  const compact=await page.evaluate(()=>{const r=topbar.getBoundingClientRect();return{overflow:topbar.scrollWidth-topbar.clientWidth,
    commandRight:commandBtn.getBoundingClientRect().right<=r.right+1,ioDisplay:getComputedStyle(document.querySelector('.top-io')).display};});
  await page.screenshot({path:path.resolve(__dirname,'_shot_toolbar_compact.png')});
  // The build-profile chip is the ONLY always-visible readout of the active lattice (the Grid
  // lattice toggle lives inside the Terrain-definition panel), so it has to track every path
  // that can change it - not just the toggle button. It reads buffers.builtLattice, which
  // buildIndex() owns, so undo/redo/New/restoreGraph are covered by construction. The device
  // segment must also tell the truth: gpuReady() forces the CPU path on hex.
  const lattice=await page.evaluate(()=>{
    const chip=()=>profileDetail.textContent,out={square:chip()};
    const before=graphSnapshot();
    terrainDef.lattice='hex';pushUndo(before);buildIndex();out.hex=chip();
    undoGraph();updateViewport(curField);out.undone=chip();
    redoGraph();updateViewport(curField);out.redone=chip();
    if((terrainDef.lattice||'square')!=='square'){terrainDef.lattice='square';buildIndex();updateViewport(curField);}
    out.restored=chip();
    return out;
  });
  // Guard the guard: the locator gate is only meaningful if the selection was something ELSE
  // beforehand. showcaseGraph() ends on select(sat), so 'satmap' -> 'water' is a real transition;
  // were the pre-state already 'water', `located.selected==='water'` would pass on a dead command.
  const ok=setup.count===18&&setup.edges===22&&setup.selected==='satmap'&&setup.curFieldLen>0
    &&initial.res===512&&initial.target===512&&initial.profile==='512²'&&initial.overflow<=1
    &&!lattice.square.includes('Hex')&&lattice.hex.includes('Hex')
    &&!lattice.undone.includes('Hex')&&lattice.redone.includes('Hex')&&!lattice.restored.includes('Hex')
    &&lattice.hex.includes('CPU')&&lattice.redone.includes('CPU')   /* hex forces the CPU path */
    &&[0.25,0.5,0.75,1].every(n=>initial.resolutions.includes(n))
    &&profileOpen.open&&profileOpen.controls&&queued.active===512&&queued.target===2048&&!queued.auto&&queued.detail.includes('Queued')
    &&filtered.profileClosed&&filtered.menu&&filtered.visible.length===1&&filtered.visible[0]==='find-water'
    &&located.selected==='water'&&located.menuClosed&&keyboardOpen
    &&compact.overflow<=1&&compact.commandRight&&compact.ioDisplay==='none'&&!errors.length;
  console.log(JSON.stringify({setup,initial,profileOpen,queued,filtered,located,keyboardOpen,compact,lattice,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
