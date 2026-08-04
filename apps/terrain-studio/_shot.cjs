const { chromium } = require('playwright-core')
const path = require('path')
const EXE = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const URL = 'file://' + path.resolve(__dirname, 'index.html')
;(async () => {
  const b = await chromium.launch({ executablePath: EXE, args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] })
  const p = await b.newPage({ viewport: { width: 900, height: 560 } })
  await p.goto(URL, { waitUntil: 'load' }); await p.waitForTimeout(1600)
  await p.evaluate(() => {
    USE_GPU = true
    nodes.length=0; edges.length=0; uid=1; selected=null
    const gen=makeNode('perlin',60,60), wat=makeNode('water',380,60), out=makeNode('output',700,60)
    edges.push({from:gen.id,to:wat.id,slot:0},{from:wat.id,to:out.id,slot:0})
    wat.params.mode='sea'; wat.params.level=0.62
    select(out); previewMode='output'; nodes.forEach(n=>{n._dirty=true}); evalGraph()
    cam.target=[0.5,0.32,0.5]; cam.dist=0.85; cam.pitch=0.12; cam.yaw=0.4
    if (typeof AUTO!=='undefined'&&AUTO) AUTO=false
    uTime=3.5; waterLook.strength=0.85; waterLook.scale=1
  })
  await p.waitForTimeout(1400)
  await p.evaluate(()=>{ uTime=3.5; if(typeof renderGL==='function') renderGL() })
  await p.locator('#gl').screenshot({ path: '.sweep-logs/banding-fixture.png' })
  await b.close()
})()
