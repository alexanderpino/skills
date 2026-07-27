// Application-menu regression: responsive desktop/hamburger states, shared commands,
// safe new-document reset, default starter restoration, and topbar overflow.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));

(async () => {
  const browser=await chromium.launch({executablePath:EXE,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:900}});
  const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1800);

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

  page.once('dialog',d=>d.accept());
  await page.locator('#fileMenu [data-editor-command="new"]').click();
  await page.waitForTimeout(120);
  const blank=await page.evaluate(()=>({
    types:nodes.map(n=>n.type),edges:edges.length,undo:undoStack.length,redo:redoStack.length,
    selected:selected&&selected.type,outputReady:!!(outputNode()&&outputNode()._field)
  }));

  await page.locator('#fileMenuBtn').click();
  page.once('dialog',d=>d.accept());
  await page.locator('#fileMenu [data-editor-command="new-default"]').click();
  await page.waitForTimeout(300);
  const starter=await page.evaluate(()=>({
    count:nodes.length,types:nodes.map(n=>n.type),edges:edges.length,
    selected:selected&&selected.type,undo:undoStack.length
  }));

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

  const ok=desktop.desktopDisplay==='flex'&&desktop.compactDisplay==='none'&&desktop.topbarOverflow<=1
    &&JSON.stringify(desktop.headings)===JSON.stringify(['File','Edit','View','Help'])
    &&fileOpen.open&&['new','new-default','import','export'].every(x=>fileOpen.commands.includes(x))
    &&JSON.stringify(blank.types)===JSON.stringify(['output'])&&blank.edges===0&&!blank.undo&&!blank.redo
    &&blank.selected==='output'&&blank.outputReady
    &&starter.count>=16&&starter.edges>=18&&starter.types.includes('water')&&starter.types.includes('snow')
    &&starter.types.includes('d_temperature')&&starter.selected==='satmap'&&!starter.undo
    &&compact.desktopDisplay==='none'&&compact.compactDisplay==='block'&&compact.overflow<=1
    &&compactOpen.open&&JSON.stringify(compactOpen.sections)===JSON.stringify(['▱File','✎Edit','▣View','?Help'])
    &&compactFile.open&&['new','new-default','import','export'].every(x=>compactFile.commands.includes(x))
    &&escapeClosed&&!errors.length;
  console.log(JSON.stringify({desktop,fileOpen,blank,starter,compact,compactOpen,compactFile,escapeClosed,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
