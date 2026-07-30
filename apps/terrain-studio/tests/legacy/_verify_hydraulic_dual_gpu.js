// Hydraulic node contract:
//   * Pipe and Droplet are independent switches with collapsible property sections.
//   * Both enabled means a fixed Pipe -> Droplet GPU chain.
//   * The combined chain stays texture-resident and performs one final readback.
//   * The GPU droplet kernel is finite, seeded, and produces both erosion and deposition.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader',
      '--ignore-gpu-blocklist','--no-sandbox'] });
  const page = await browser.newPage({ viewport:{ width:1440, height:900 } });
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1300);

  const report=await page.evaluate(()=>{
    const stats=(base,out)=>{
      let eroded=0,deposited=0,maxDrop=0,maxRise=0,finite=true,sumSq=0;
      for(let i=0;i<base.length;i++){
        const v=out[i],d=v-base[i];finite=finite&&Number.isFinite(v);sumSq+=d*d;
        if(d<0){eroded++;maxDrop=Math.max(maxDrop,-d);}
        if(d>0){deposited++;maxRise=Math.max(maxRise,d);}
      }
      return{finite,eroded,deposited,maxDrop,maxRise,rms:Math.sqrt(sumSq/base.length)};
    };
    const diff=(a,b)=>{
      let max=0,sumSq=0;for(let i=0;i<a.length;i++){const d=a[i]-b[i];max=Math.max(max,Math.abs(d));sumSq+=d*d;}
      return{max,rms:Math.sqrt(sumSq/a.length)};
    };
    const capability={
      gpu:GPU.init(),
      floatBlend:!!gl.getExtension('EXT_float_blend'),
      dropletsReady:typeof gpuDropletsReady==='function'&&gpuDropletsReady()
    };
    if(!capability.gpu||!capability.floatBlend)throw new Error('SETUP FAILURE: GPU droplet capability unavailable');
    if(typeof gpuHydraulicDroplets!=='function')throw new Error('gpuHydraulicDroplets is not exported');
    if(typeof gpuHydraulicCombined!=='function')throw new Error('gpuHydraulicCombined is not exported');

    RES=96;terrainDef.lattice='square';buildIndex();
    const base=fbmField(gnoise,{seed:17,freq:3.2,octaves:5,lac:2,gain:.52});
    const dropletParams={droplets:1800,lifetime:28,inertia:.08,capacity:6,erode:.35,
      deposit:.28,evap:.02,gravity:4,radius:2,minSlope:.01,seed:31,gridK:1};
    const t0=performance.now(),dropA=gpuHydraulicDroplets(base,dropletParams),dropMs=performance.now()-t0;
    const diagA=JSON.parse(JSON.stringify(hydroMassDiag));
    const dropB=gpuHydraulicDroplets(base,dropletParams);
    const dropC=gpuHydraulicDroplets(base,{...dropletParams,seed:32});

    const pipeParams={iters:12,capacity:6,erode:.35,deposit:.28,inertia:.05,gridK:1};
    const nodeParams={};TYPES.hydraulic.params.forEach(pr=>nodeParams[pr.key]=cloneParams(pr.def));
    Object.assign(nodeParams,{pipeEnabled:true,dropletEnabled:true,pipeIters:pipeParams.iters,
      droplets:dropletParams.droplets,lifetime:dropletParams.lifetime,seed:dropletParams.seed,feat:1});
    const heldScale=SCALE_RES;SCALE_RES=false;
    let readbacks=0;const oldRead=gl.readPixels;
    gl.readPixels=function(...args){readbacks++;return oldRead.apply(this,args);};
    const combined=TYPES.hydraulic.eval(nodeParams,[base,null]);
    gl.readPixels=oldRead;
    SCALE_RES=heldScale;
    const combinedDiag=JSON.parse(JSON.stringify(hydroMassDiag));

    // Inspector-only setup: no input edge means toggle changes do not launch a heavy simulation.
    nodes.length=0;edges.length=0;uid=1;selected=null;selectedEdge=null;
    const legacyNode=makeNode('hydraulic',0,0);
    legacyNode.params={engine:'droplets',pipeIters:33,droplets:4321,erode:.41,deposit:.22,
      capacity:7,inertia:.12,radius:3,seed:99,feat:1};
    selected=legacyNode;buildProps();
    const migrated={...legacyNode.params};
    nodes.length=0;edges.length=0;uid=1;selected=null;
    const node=makeNode('hydraulic',100,100);selected=node;buildProps();
    const inspect=()=>({
      sections:[...document.querySelectorAll('#pBody .param-section')].map(s=>({
        id:s.dataset.section,open:!s.querySelector('.param-section-body').hidden,
        enabled:s.querySelector('[role=switch]').getAttribute('aria-checked'),
        badge:s.querySelector('.param-section-badge').textContent.trim(),
        keys:[...s.querySelectorAll('.field[data-param-key]')].map(f=>f.dataset.paramKey)
      })),
      values:{...node.params}
    });
    const initial=inspect();
    const pipeCollapse=document.querySelector('.param-section[data-section=pipe] .param-section-collapse');
    const beforeCollapse=JSON.stringify(node.params);pipeCollapse.click();
    const collapsed=inspect(),collapsePure=beforeCollapse===JSON.stringify(node.params);
    const dropletSwitch=document.querySelector('.param-section[data-section=droplet] [role=switch]');
    dropletSwitch.click();
    const both=inspect();

    return{
      capability,dropMs,drop:stats(base,dropA),repeat:diff(dropA,dropB),reroll:diff(dropA,dropC),
      diagA,combined:stats(base,combined),combinedDiag,readbacks,
      migrated,ui:{initial,collapsed,both,collapsePure}
    };
  });

  const pipe0=report.ui.initial.sections.find(s=>s.id==='pipe');
  const drop0=report.ui.initial.sections.find(s=>s.id==='droplet');
  const pipeCollapsed=report.ui.collapsed.sections.find(s=>s.id==='pipe');
  const pipeBoth=report.ui.both.sections.find(s=>s.id==='pipe');
  const dropBoth=report.ui.both.sections.find(s=>s.id==='droplet');
  const massResidual=Math.abs((report.diagA.sumIn-report.diagA.sumOut)-report.diagA.exported);
  await page.locator('#props').screenshot({
    path:path.resolve(__dirname,'_shot_hydraulic_dual_gpu_props.png')
  });
  const ok=report.capability.dropletsReady
    &&report.drop.finite&&report.drop.eroded>50&&report.drop.deposited>50
    &&report.drop.maxDrop>1e-5&&report.drop.maxRise>1e-5&&report.drop.rms>1e-5
    &&report.repeat.max<=1e-6&&report.reroll.rms>1e-6
    &&report.diagA.engine==='gpu-droplets'&&massResidual<1e-5
    &&report.combined.finite&&report.combined.eroded>50&&report.combined.deposited>50
    &&report.combinedDiag.engine==='gpu-combined'
    &&JSON.stringify(report.combinedDiag.stages)===JSON.stringify(['pipes','droplets'])
    &&report.readbacks===1
    &&report.migrated.engine===null&&report.migrated.pipeEnabled===false&&report.migrated.dropletEnabled===true
    &&report.migrated.dropletCapacity===7&&report.migrated.dropletErode===.41
    &&pipe0&&drop0&&pipe0.enabled==='true'&&drop0.enabled==='false'
    &&pipe0.open&&!drop0.open&&pipe0.badge.includes('GPU')&&drop0.badge.includes('GPU')
    &&pipe0.keys.includes('pipeIters')&&pipe0.keys.includes('pipeCapacity')
    &&drop0.keys.includes('droplets')&&drop0.keys.includes('lifetime')&&drop0.keys.includes('seed')
    &&pipeCollapsed&&!pipeCollapsed.open&&report.ui.collapsePure
    &&pipeBoth.enabled==='true'&&dropBoth.enabled==='true'
    &&!errors.length;
  console.log(JSON.stringify({...report,massResidual,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
