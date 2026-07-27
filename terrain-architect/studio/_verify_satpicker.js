// Visual SatMap-library regression: actual LUT strips, graph-bound selection, property reuse, keyboard-safe model.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));

(async()=>{
  const browser=await chromium.launch({executablePath:EXE,
    args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:900}});
  const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1200);

  await page.evaluate(()=>select(nearestUpstreamNode('satmap')));
  await page.locator('.prop-sat-picker').click();await page.waitForTimeout(120);
  const open=await page.evaluate(()=>{
    const items=[...document.querySelectorAll('#satPickerList .sat-option')],menu=document.querySelector('#satPickerMenu');
    const r=menu.getBoundingClientRect(),selected=items.find(x=>x.classList.contains('selected'));
    return{count:items.length,expected:Object.keys(SATMAPS).length,visible:!menu.hidden,
      gradients:items.every(x=>getComputedStyle(x.querySelector('.sat-option-strip')).backgroundImage.includes('linear-gradient')),
      selected:selected&&selected.dataset.name,property:document.querySelector('.prop-sat-picker .sat-picker-name').textContent,
      viewportHasPicker:!!document.querySelector('#viewport #satPickerMenu, #viewport #satSel, .vp-tools #satPickerBtn'),
      inWindow:r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight};
  });
  await page.screenshot({path:path.resolve(__dirname,'_shot_satpicker.png')});

  await page.locator('.sat-option[data-name="Canyon"]').click();await page.waitForTimeout(180);
  const chosen=await page.evaluate(()=>{
    const sat=nearestUpstreamNode('satmap');
    return{satName,property:document.querySelector('.prop-sat-picker .sat-picker-name').textContent,
      graphGradient:sat&&sat.params.gradient,closed:document.querySelector('#satPickerMenu').hidden};
  });

  const property=await page.evaluate(()=>{
    const sat=nearestUpstreamNode('satmap');select(sat);
    const keys=TYPES.satmap.params.map(x=>x.key);
    return{hasVisual:!!document.querySelector('.prop-sat-picker'),hasStudio:[...document.querySelectorAll('#pBody button')].some(b=>b.textContent.includes('SatMap Studio')),keys};
  });
  await page.locator('.prop-sat-picker').click();await page.waitForTimeout(100);
  const propertyOpen=await page.evaluate(()=>!document.querySelector('#satPickerMenu').hidden
    &&document.querySelector('#satPickerList .selected')?.dataset.name==='Canyon');

  const ok=open.visible&&open.count===open.expected&&open.count>10&&open.gradients&&open.selected==='Temperate'
    &&open.property==='Temperate'&&!open.viewportHasPicker&&open.inWindow&&chosen.satName==='Canyon'
    &&chosen.property==='Canyon'&&chosen.graphGradient==='Canyon'&&chosen.closed&&property.hasVisual&&property.hasStudio
    &&property.keys.includes('gradient')&&!property.keys.includes('gradientB')&&!property.keys.includes('mode')
    &&propertyOpen&&!errors.length;
  console.log(JSON.stringify({open,chosen,property,propertyOpen,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
