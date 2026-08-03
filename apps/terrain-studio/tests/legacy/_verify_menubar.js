// Application-menu regression: responsive desktop/hamburger states, shared commands,
// safe new-document reset, default starter restoration, and topbar overflow.
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

  const bootSeed=await page.evaluate(()=>{
    const read=def=>({has:Object.prototype.hasOwnProperty.call(def,'seed'),value:def.seed===undefined?null:def.seed});
    return {root:read(terrainDef),snapshot:read(graphSnapshot().terrainDef)};
  });

  const desktop=await page.evaluate(()=>({
    desktopDisplay:getComputedStyle(document.querySelector('.desktop-menu')).display,
    compactDisplay:getComputedStyle(document.querySelector('.compact-menu-wrap')).display,
    topbarOverflow:topbar.scrollWidth-topbar.clientWidth,
    headings:[...document.querySelectorAll('.editor-menu-trigger')].map(b=>b.textContent.trim())
  }));
  await page.locator('#fileMenuBtn').click();
  const fileOpen=await page.evaluate(()=>({
    open:!fileMenu.hidden,
    commands:[...fileMenu.querySelectorAll('[data-editor-command]')].map(b=>b.dataset.editorCommand)
  }));
  await page.screenshot({path:path.resolve(__dirname,'_shot_menubar_desktop.png')});

  // `new` opens the New Terrain dialog now, not a native confirm(), so no dialog handler here:
  // an unconsumed page.once('dialog') collides with the next one that IS needed.
  await page.locator('#fileMenu [data-editor-command="new"]').click();
  // S9.2: `new` now opens the New Terrain dialog rather than creating immediately — creation
  // runs a feasibility preflight before anything is allocated. The dialog is modal and
  // intercepts pointer events, so confirm it opened, then dismiss it with Escape.
  const newDialogOpened = await page.evaluate(() => document.querySelector("#newTerrainDialog").hidden === false);
  if (!newDialogOpened) throw new Error("File > New did not open the New Terrain dialog");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(80);
  await page.waitForTimeout(120);
  const blank=await page.evaluate(()=>({
    types:nodes.map(n=>n.type),edges:edges.length,undo:undoStack.length,redo:redoStack.length,
    selected:selected&&selected.type,outputReady:!!(outputNode()&&outputNode()._field),
    seed:{root:{has:Object.prototype.hasOwnProperty.call(terrainDef,'seed'),value:terrainDef.seed===undefined?null:terrainDef.seed},
      snapshot:{has:Object.prototype.hasOwnProperty.call(graphSnapshot().terrainDef,'seed'),value:graphSnapshot().terrainDef.seed===undefined?null:graphSnapshot().terrainDef.seed}}
  }));

  // "new-default" restores THE DEFAULT DOCUMENT, so this oracle deliberately does NOT construct
  // showcaseGraph() the way the renderer/water oracles do - the default is precisely the subject
  // under test, and seeding another graph first would measure nothing (newTerrainDocument() clears
  // nodes/edges before building). D7 moved that default: newTerrainDocument(true) -> defaultGraph()
  // -> layer0Graph() (legacy.js:6512), the L0 bedrock layer, where it used to be the 18-node
  // showcase. The expectation below is re-pointed at L0 and tightened from the old
  // count>=16 / edges>=18 / three membership tests to EXACT equality on the whole node list and
  // edge count, so a silent change to the opening document is red in one line instead of
  // surviving under a >= bound.
  await page.locator('#fileMenuBtn').click();
  page.once('dialog',d=>d.accept());
  await page.locator('#fileMenu [data-editor-command="new-default"]').click();
  await page.waitForTimeout(300);
  const starter=await page.evaluate(()=>{
    if(!nodes.length)throw new Error('SETUP FAILURE: new-default produced an empty graph');
    return {count:nodes.length,types:nodes.map(n=>n.type),edges:edges.length,
      selected:selected&&selected.type,undo:undoStack.length,
      // newTerrainDocument() ends in evalGraph(), so a restored default must arrive EVALUATED.
      // Without this the type list alone would pass on a default that renders nothing.
      outputReady:!!(outputNode()&&outputNode()._field),
      seed:{root:{has:Object.prototype.hasOwnProperty.call(terrainDef,'seed'),value:terrainDef.seed===undefined?null:terrainDef.seed},
        snapshot:{has:Object.prototype.hasOwnProperty.call(graphSnapshot().terrainDef,'seed'),value:graphSnapshot().terrainDef.seed===undefined?null:graphSnapshot().terrainDef.seed}}};
  });

  await page.locator('#fileMenuBtn').click();
  page.once('dialog',d=>d.accept());
  await page.locator('#fileMenu [data-editor-command="new-canyon"]').click();
  await page.waitForTimeout(300);
  const canyonSeed=await page.evaluate(()=>{
    const read=def=>({has:Object.prototype.hasOwnProperty.call(def,'seed'),value:def.seed===undefined?null:def.seed});
    return {root:read(terrainDef),snapshot:read(graphSnapshot().terrainDef)};
  });

  await page.locator('#fileMenuBtn').click();
  // `new` opens the New Terrain dialog now, not a native confirm(), so no dialog handler here:
  // an unconsumed page.once('dialog') collides with the next one that IS needed.
  await page.locator('#fileMenu [data-editor-command="new"]').click();
  // S9.2: `new` now opens the New Terrain dialog rather than creating immediately — creation
  // runs a feasibility preflight before anything is allocated. The dialog is modal and
  // intercepts pointer events, so confirm it opened, then dismiss it with Escape.
  const newDialogOpened2 = await page.evaluate(() => document.querySelector("#newTerrainDialog").hidden === false);
  if (!newDialogOpened2) throw new Error("File > New did not open the New Terrain dialog");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(80);
  await page.waitForTimeout(120);
  const showcaseSeed=await page.evaluate(()=>{
    showcaseGraph();
    const read=def=>({has:Object.prototype.hasOwnProperty.call(def,'seed'),value:def.seed===undefined?null:def.seed});
    return {root:read(terrainDef),snapshot:read(graphSnapshot().terrainDef)};
  });

  const absentZero=await page.evaluate(()=>{
    const read=def=>({has:Object.prototype.hasOwnProperty.call(def,'seed'),value:def.seed===undefined?null:def.seed});
    undoStack=[];redoStack=[];
    terrainDef.seed=0;
    const legacy=graphSnapshot();delete legacy.terrainDef.seed;undoStack=[legacy];
    undoGraph();
    const undo={root:read(terrainDef),snapshot:read(graphSnapshot().terrainDef)};
    redoGraph();
    const redo={root:read(terrainDef),snapshot:read(graphSnapshot().terrainDef)};
    return {undo,redo};
  });

  const explicitSeeds=await page.evaluate(()=>{
    const read=def=>({has:Object.prototype.hasOwnProperty.call(def,'seed'),value:def.seed===undefined?null:def.seed});
    undoStack=[];redoStack=[];
    terrainDef.seed=456;
    const prior=graphSnapshot();prior.terrainDef.seed=123;undoStack=[prior];
    undoGraph();
    const undo={root:read(terrainDef),snapshot:read(graphSnapshot().terrainDef)};
    redoGraph();
    const redo={root:read(terrainDef),snapshot:read(graphSnapshot().terrainDef)};
    return {undo,redo};
  });

  await page.setViewportSize({width:760,height:720});await page.waitForTimeout(150);
  const compact=await page.evaluate(()=>({
    desktopDisplay:getComputedStyle(document.querySelector('.desktop-menu')).display,
    compactDisplay:getComputedStyle(document.querySelector('.compact-menu-wrap')).display,
    overflow:topbar.scrollWidth-topbar.clientWidth
  }));
  await page.locator('#mainMenuBtn').click();
  const compactOpen=await page.evaluate(()=>({
    open:!mainMenu.hidden,
    sections:[...document.querySelectorAll('.compact-menu-section')].map(b=>b.textContent.trim().replace('›','').trim())
  }));
  await page.locator('[data-compact-section="compactFile"]').click();
  const compactFile=await page.evaluate(()=>({
    open:!compactFile.hidden,
    commands:[...compactFile.querySelectorAll('[data-editor-command]')].map(b=>b.dataset.editorCommand)
  }));
  await page.screenshot({path:path.resolve(__dirname,'_shot_menubar_compact.png')});
  await page.keyboard.press('Escape');
  const escapeClosed=await page.evaluate(()=>mainMenu.hidden);

  // Both File menus are driven off the same command table (legacy.js:5942/6029), so they are held
  // to the same EXACT list rather than a membership test - a dropped or renamed command has to be
  // red, and `.every(includes)` cannot see a removal. Measured: identical in desktop and compact.
  // S0.1 added `open` and `save` between the New group and the heightmap group, in both menus.
  // Updating this list is a deliberate contract change, not a repair: the EXACT match is what makes
  // an accidental addition or a silent removal red, and it caught this one.
  const FILE_COMMANDS=JSON.stringify(['new','new-default','new-canyon','open','save','import','export']);
  // The L0 opening document, read off layer0Graph() (legacy.js:6512) and confirmed by measurement:
  // 7 nodes, 6 edges, selection parked on the base generator.
  const STARTER_TYPES=JSON.stringify(['perlin','ridged','blend','d_height','heightmask','levels','output']);
  const seedIs=(reading,value)=>reading&&reading.root.has&&reading.root.value===value
    &&reading.snapshot.has&&reading.snapshot.value===value;
  const ok=desktop.desktopDisplay==='flex'&&desktop.compactDisplay==='none'&&desktop.topbarOverflow<=1
    &&JSON.stringify(desktop.headings)===JSON.stringify(['File','Edit','View','Help'])
    &&fileOpen.open&&JSON.stringify(fileOpen.commands)===FILE_COMMANDS
    // S9.2: `new` opens the New Terrain dialog instead of wiping immediately, and this oracle
    // presses Escape. Cancelling must leave the open document UNTOUCHED — a stronger property than
    // the old expectation, which described the immediate wipe ('output' alone, zero edges) and
    // would now pass only if cancelling still destroyed the user's graph.
    &&JSON.stringify(blank.types)===JSON.stringify(['perlin','ridged','blend','d_height','heightmask','levels','output'])
    &&blank.edges===6&&!blank.undo&&!blank.redo
    &&blank.outputReady&&seedIs(bootSeed,7)&&seedIs(blank.seed,7)
    &&starter.count===7&&starter.edges===6&&JSON.stringify(starter.types)===STARTER_TYPES
    &&starter.selected==='perlin'&&!starter.undo&&starter.outputReady&&seedIs(starter.seed,7)
    &&seedIs(canyonSeed,7)&&seedIs(showcaseSeed,7)
    &&seedIs(absentZero.undo,7)&&seedIs(absentZero.redo,0)
    &&seedIs(explicitSeeds.undo,123)&&seedIs(explicitSeeds.redo,456)
    &&compact.desktopDisplay==='none'&&compact.compactDisplay==='block'&&compact.overflow<=1
    &&compactOpen.open&&JSON.stringify(compactOpen.sections)===JSON.stringify(['▱File','✎Edit','▣View','?Help'])
    &&compactFile.open&&JSON.stringify(compactFile.commands)===FILE_COMMANDS
    &&escapeClosed&&!errors.length;
  console.log(JSON.stringify({bootSeed,desktop,fileOpen,blank,starter,canyonSeed,showcaseSeed,absentZero,explicitSeeds,
    compact,compactOpen,compactFile,escapeClosed,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
