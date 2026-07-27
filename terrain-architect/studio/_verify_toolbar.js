// Scalable toolbar regression: profile popover, queued high-res target, command search,
// graph locator, keyboard access, and compact-width overflow.
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
  const initial=await page.evaluate(()=>({res:RES,target:TARGET_RES,profile:profileRes.textContent,overflow:topbar.scrollWidth-topbar.clientWidth,
    resolutions:[...resSel.options].map(o=>+o.value)}));
  await page.locator('#buildProfileBtn').click();
  const profileOpen=await page.evaluate(()=>({open:!buildSettings.hidden,controls:['resSel','qualitySel','gpuBtn','scaleBtn'].every(id=>!!document.getElementById(id))}));
  await page.locator('#resSel').selectOption('2048');
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
  const ok=initial.res===512&&initial.target===512&&initial.profile==='512²'&&initial.overflow<=1
    &&[512,1024,2048,4096].every(n=>initial.resolutions.includes(n))
    &&profileOpen.open&&profileOpen.controls&&queued.active===512&&queued.target===2048&&!queued.auto&&queued.detail.includes('Queued')
    &&filtered.profileClosed&&filtered.menu&&filtered.visible.length===1&&filtered.visible[0]==='find-water'
    &&located.selected==='water'&&located.menuClosed&&keyboardOpen
    &&compact.overflow<=1&&compact.commandRight&&compact.ioDisplay==='none'&&!errors.length;
  console.log(JSON.stringify({initial,profileOpen,queued,filtered,located,keyboardOpen,compact,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
