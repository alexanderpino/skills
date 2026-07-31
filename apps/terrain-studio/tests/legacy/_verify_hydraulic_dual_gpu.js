// Hydraulic node contract:
//   * Pipe and Droplet are independent switches with collapsible property sections.
//   * Both enabled means a fixed Pipe -> Droplet GPU chain.
//   * The combined chain stays texture-resident and performs one final readback.
//   * The GPU droplet kernel is finite, seeded, and produces both erosion and deposition.
//   * A lifetime cap never becomes a synchronized terminal sediment dump ("hedgehog" peaks).
//   * Real resolution-scaled particle density cannot run away through stale-read scatter overlap.
//   * Long pipe runs use a cropped continuation apron and preserve edge continuity.
//   * Downward pits, high-density combined runs, and low camera positions are explicitly gated.
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
    const spikeStats=(field,n)=>{
      let maxLocalProminence=0,peaksOver02=0,maxPitDepth=0,pitsOver02=0,maxSlope=0;
      for(let y=1;y<n-1;y++)for(let x=1;x<n-1;x++){
        const i=y*n+x,v=field[i];let highestNeighbour=-Infinity,lowestNeighbour=Infinity;
        for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
          if(dx===0&&dy===0)continue;
          const nv=field[(y+dy)*n+x+dx],dist=dx&&dy?Math.SQRT2:1;
          highestNeighbour=Math.max(highestNeighbour,nv);
          lowestNeighbour=Math.min(lowestNeighbour,nv);
          maxSlope=Math.max(maxSlope,Math.abs(v-nv)/dist);
        }
        const prominence=Math.max(0,v-highestNeighbour);
        const pitDepth=Math.max(0,lowestNeighbour-v);
        maxLocalProminence=Math.max(maxLocalProminence,prominence);
        maxPitDepth=Math.max(maxPitDepth,pitDepth);
        if(prominence>.02)peaksOver02++;
        if(pitDepth>.02)pitsOver02++;
      }
      return{maxLocalProminence,peaksOver02,maxPitDepth,pitsOver02,maxSlope};
    };
    const edgeStats=(base,out,n)=>{
      const cliffs=[];let maxEdgeChange=0;
      for(let t=0;t<n;t++){
        const samples=[[t,n+t],[(n-1)*n+t,(n-2)*n+t],[t*n,t*n+1],
          [t*n+n-1,t*n+n-2]];
        for(const[i,j]of samples){
          cliffs.push(Math.abs(out[i]-out[j]));
          maxEdgeChange=Math.max(maxEdgeChange,Math.abs(out[i]-base[i]));
        }
      }
      cliffs.sort((a,b)=>a-b);
      return{mean:cliffs.reduce((a,b)=>a+b,0)/cliffs.length,
        p99:cliffs[Math.floor(cliffs.length*.99)],max:cliffs[cliffs.length-1],maxEdgeChange};
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
    const spikeControl=base.slice();
    spikeControl[48*RES+48]+=.2;
    const pitDetectorControl=base.slice();
    pitDetectorControl[48*RES+48]-=.2;

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

    // Persistent visual diagnostic: fixed-path hillshade beside local-prominence heat.
    // The numeric gate below is authoritative; this image makes the failure readable by eye.
    const diagnostic=document.createElement('canvas');
    diagnostic.id='hydraulic-shape-preview';diagnostic.width=RES*2;diagnostic.height=RES;
    diagnostic.style.cssText='position:fixed;left:8px;top:8px;width:768px;height:384px;z-index:99999;image-rendering:pixelated';
    const dc=diagnostic.getContext('2d'),image=dc.createImageData(RES*2,RES);
    for(let y=0;y<RES;y++)for(let x=0;x<RES;x++){
      const xm=Math.max(0,x-1),xp=Math.min(RES-1,x+1);
      const ym=Math.max(0,y-1),yp=Math.min(RES-1,y+1),i=y*RES+x;
      const gx=(dropA[y*RES+xp]-dropA[y*RES+xm])*18;
      const gy=(dropA[yp*RES+x]-dropA[ym*RES+x])*18;
      const il=1/Math.hypot(gx,gy,1),shade=Math.max(0,(-gx*.45-gy*.55+1*.7)*il);
      const grey=Math.round(32+shade*210),p0=(y*(RES*2)+x)*4;
      image.data[p0]=grey;image.data[p0+1]=grey;image.data[p0+2]=grey+Math.min(18,255-grey);image.data[p0+3]=255;
      let neighbour=-Infinity;
      for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
        if(!dx&&!dy)continue;
        const qx=Math.max(0,Math.min(RES-1,x+dx)),qy=Math.max(0,Math.min(RES-1,y+dy));
        neighbour=Math.max(neighbour,dropA[qy*RES+qx]);
      }
      const heat=Math.min(1,Math.max(0,dropA[i]-neighbour)/.02),p1=(y*(RES*2)+RES+x)*4;
      image.data[p1]=Math.round(255*heat);image.data[p1+1]=Math.round(90*(1-heat));
      image.data[p1+2]=Math.round(125*(1-heat));image.data[p1+3]=255;
    }
    dc.putImageData(image,0,0);document.body.appendChild(diagnostic);

    // Production-density shape check at the node's defaults. The smaller fixture above keeps
    // deterministic comparisons cheap; this one covers the workload that produced the screenshot.
    RES=192;buildIndex();
    const defaultBase=fbmField(gnoise,{seed:17,freq:3.2,octaves:5,lac:2,gain:.52});
    const defaultOut=gpuHydraulicDroplets(defaultBase,{droplets:18000,lifetime:48,inertia:.05,
      capacity:6,erode:.35,deposit:.28,evap:.02,gravity:4,radius:2,minSlope:.01,seed:31,gridK:1});
    const defaultCase={effect:stats(defaultBase,defaultOut),base:spikeStats(defaultBase,RES),
      droplets:spikeStats(defaultOut,RES)};

    // Exercise the reported 14,389 × 71 failure and the authored slider maximum through the
    // real 512² Interactive scaling. The UI counts become 57,556/120k/240k GPU particles at
    // a 384² sim grid.
    RES=512;buildIndex();
    const loadBase=fbmField(gnoise,{seed:17,freq:3.2,octaves:5,lac:2,gain:.52});
    const params=()=>{const p={};TYPES.hydraulic.params.forEach(pr=>p[pr.key]=cloneParams(pr.def));return p;};
    const dropletSweep=[];let highDensityOut=null;
    for(const {particles,lifetime} of [
      {particles:14389,lifetime:71},{particles:30000,lifetime:48},{particles:60000,lifetime:48}
    ]){
      const p=params();Object.assign(p,{pipeEnabled:false,dropletEnabled:true,droplets:particles,
        lifetime,dropletInertia:.05,dropletCapacity:6,dropletErode:.35,
        dropletDeposit:.28,evap:.02,gravity:4,radius:2,seed:31,feat:1});
      const t=performance.now(),out=TYPES.hydraulic.eval(p,[loadBase,null]);
      const diag=JSON.parse(JSON.stringify(hydroMassDiag));
      dropletSweep.push({particles,lifetime,ms:performance.now()-t,effect:stats(loadBase,out),
        shape:spikeStats(out,RES),diag});
      highDensityOut=out;
    }
    const reportedSeedSweep=[dropletSweep[0]];
    for(const seed of [12345,98765]){
      const p=params();Object.assign(p,{pipeEnabled:false,dropletEnabled:true,droplets:14389,
        lifetime:71,dropletInertia:.05,dropletCapacity:6,dropletErode:.35,
        dropletDeposit:.28,evap:.02,gravity:4,radius:2,seed,feat:1});
      const t=performance.now(),out=TYPES.hydraulic.eval(p,[loadBase,null]);
      reportedSeedSweep.push({seed,ms:performance.now()-t,effect:stats(loadBase,out),
        shape:spikeStats(out,RES),diag:JSON.parse(JSON.stringify(hydroMassDiag))});
    }
    const pipeLoadParams=params();Object.assign(pipeLoadParams,{pipeEnabled:true,dropletEnabled:false,
      pipeIters:279,pipeInertia:.05,pipeCapacity:6,pipeErode:.35,pipeDeposit:.48,feat:1});
    const pipeLoadOut=TYPES.hydraulic.eval(pipeLoadParams,[loadBase,null]);
    const pipeLoad={effect:stats(loadBase,pipeLoadOut),shape:spikeStats(pipeLoadOut,RES),
      edge:edgeStats(loadBase,pipeLoadOut,RES),diag:JSON.parse(JSON.stringify(hydroMassDiag))};
    const combinedLoadParams={...pipeLoadParams,pipeEnabled:true,dropletEnabled:true,
      droplets:57670,lifetime:48,dropletInertia:.05,dropletCapacity:6,dropletErode:.35,
      dropletDeposit:.28,evap:.02,gravity:4,radius:2,seed:31,feat:1};
    const combinedStart=performance.now();
    const combinedLoadOut=TYPES.hydraulic.eval(combinedLoadParams,[loadBase,null]);
    const combinedLoad={ms:performance.now()-combinedStart,effect:stats(loadBase,combinedLoadOut),
      shape:spikeStats(combinedLoadOut,RES),edge:edgeStats(loadBase,combinedLoadOut,RES),
      diag:JSON.parse(JSON.stringify(hydroMassDiag))};
    const pitBase=new Float32Array(RES*RES);pitBase.fill(.5);
    const pitIndex=(RES>>1)*RES+(RES>>1);pitBase[pitIndex]=.49;
    const pitOut=TYPES.hydraulic.eval(pipeLoadParams,[pitBase,null]);
    const pitControl={effect:stats(pitBase,pitOut),shape:spikeStats(pitOut,RES),
      centerAdditionalDrop:pitBase[pitIndex]-pitOut[pitIndex]};
    const loadCase={baseShape:spikeStats(loadBase,RES),baseEdge:edgeStats(loadBase,loadBase,RES),
      dropletSweep,reportedSeedSweep,pipe:pipeLoad,combined:combinedLoad,pitControl};

    // High-density visual diagnostic: output hillshade beside a 0.005-prominence heat map.
    const loadDiagnostic=document.createElement('canvas'),loadN=RES;
    loadDiagnostic.id='hydraulic-load-preview';loadDiagnostic.width=loadN*2;loadDiagnostic.height=loadN;
    loadDiagnostic.style.cssText='position:fixed;left:8px;top:8px;width:768px;height:384px;z-index:99998;image-rendering:pixelated';
    const lc=loadDiagnostic.getContext('2d'),li=lc.createImageData(loadN*2,loadN);
    for(let y=0;y<loadN;y++)for(let x=0;x<loadN;x++){
      const xm=Math.max(0,x-1),xp=Math.min(loadN-1,x+1),ym=Math.max(0,y-1),yp=Math.min(loadN-1,y+1);
      const i=y*loadN+x,gx=(highDensityOut[y*loadN+xp]-highDensityOut[y*loadN+xm])*18;
      const gy=(highDensityOut[yp*loadN+x]-highDensityOut[ym*loadN+x])*18;
      const il=1/Math.hypot(gx,gy,1),shade=Math.max(0,(-gx*.45-gy*.55+.7)*il);
      const grey=Math.round(32+shade*210),p0=(y*(loadN*2)+x)*4;
      li.data[p0]=grey;li.data[p0+1]=grey;li.data[p0+2]=grey+Math.min(18,255-grey);li.data[p0+3]=255;
      let neighbour=-Infinity;
      for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++)if(dx||dy){
        const qx=Math.max(0,Math.min(loadN-1,x+dx)),qy=Math.max(0,Math.min(loadN-1,y+dy));
        neighbour=Math.max(neighbour,highDensityOut[qy*loadN+qx]);
      }
      const heat=Math.min(1,Math.max(0,highDensityOut[i]-neighbour)/.005),p1=(y*(loadN*2)+loadN+x)*4;
      li.data[p1]=Math.round(255*heat);li.data[p1+1]=Math.round(90*(1-heat));
      li.data[p1+2]=Math.round(125*(1-heat));li.data[p1+3]=255;
    }
    lc.putImageData(li,0,0);document.body.appendChild(loadDiagnostic);
    updateViewport(combinedLoadOut,null);
    cam={az:-.65,el:.055,dist:1.85,target:[0,-.18,0]};
    const cameraBefore=cameraEye();renderGL();
    const cameraAfter=cameraEye();let surfaceMax=-Infinity;
    for(let i=0;i<curSolidSurfaceY.length;i++)surfaceMax=Math.max(surfaceMax,curSolidSurfaceY[i]);
    const cameraGuard={beforeY:cameraBefore[1],afterY:cameraAfter[1],surfaceMax};

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
      shape:{base:spikeStats(base,96),injected:spikeStats(spikeControl,96),
        injectedPit:spikeStats(pitDetectorControl,96),
        droplets:spikeStats(dropA,96),combined:spikeStats(combined,96)},
      defaultCase,loadCase,diagA,combined:stats(base,combined),combinedDiag,readbacks,
      cameraGuard,migrated,ui:{initial,collapsed,both,collapsePure}
    };
  });

  const pipe0=report.ui.initial.sections.find(s=>s.id==='pipe');
  const drop0=report.ui.initial.sections.find(s=>s.id==='droplet');
  const pipeCollapsed=report.ui.collapsed.sections.find(s=>s.id==='pipe');
  const pipeBoth=report.ui.both.sections.find(s=>s.id==='pipe');
  const dropBoth=report.ui.both.sections.find(s=>s.id==='droplet');
  // Measured endpoints for this exact 96²/seed fixture:
  //   rejected terminal dump: prominence .100287, 53 peaks > .02, max slope .152989
  //   stable fixed path: prominence .018229, 0 peaks > .02, max slope .071470
  // At production density (192², 18k × 48), rejected/fixed are 154/0 peaks > .02 and
  // .098667/.006561 maximum prominence respectively. The 512² load gate below additionally
  // covers the reported 14,389 × 71 case and the 60k UI / 240k actual-particle maximum.
  // The injected control proves the detector is armed; the base bounds its natural-noise floor.
  const sharpRise=report.shape.droplets.maxLocalProminence-report.shape.base.maxLocalProminence;
  const slopeGrowth=report.shape.droplets.maxSlope-report.shape.base.maxSlope;
  await page.locator('#props').screenshot({
    path:path.resolve(__dirname,'_shot_hydraulic_dual_gpu_props.png')
  });
  await page.locator('#hydraulic-shape-preview').screenshot({
    path:path.resolve(__dirname,'_shot_hydraulic_dual_gpu_shape.png')
  });
  await page.locator('#hydraulic-load-preview').screenshot({
    path:path.resolve(__dirname,'_shot_hydraulic_load_shape.png')
  });
  await page.evaluate(()=>{
    document.querySelector('#hydraulic-shape-preview').hidden=true;
    document.querySelector('#hydraulic-load-preview').hidden=true;
  });
  await page.locator('#gl').screenshot({
    path:path.resolve(__dirname,'_shot_hydraulic_pipe_edge.png')
  });
  const expectedGpuCounts=[57556,120000,240000];
  const loadSweepOk=report.loadCase.dropletSweep.every((r,i)=>r.ms>0&&r.ms<30000
    &&r.effect.finite&&r.effect.eroded>500&&r.effect.deposited>500
    &&r.effect.maxDrop<.25&&r.effect.maxRise<.25
    &&r.shape.peaksOver02===0&&r.shape.pitsOver02===0
    &&r.shape.maxLocalProminence<.01&&r.shape.maxPitDepth<.01&&r.shape.maxSlope<.04
    &&r.diag.requestedDroplets===expectedGpuCounts[i]&&r.diag.cohorts>=4
    &&r.diag.cohortLimit>0&&r.diag.particleWeight>0&&r.diag.particleWeight<=1);
  const reportedSeedSweepOk=report.loadCase.reportedSeedSweep.every(r=>r.ms>0&&r.ms<30000
    &&r.effect.finite&&r.effect.maxDrop<.25&&r.effect.maxRise<.25
    &&r.shape.peaksOver02===0&&r.shape.pitsOver02===0
    &&r.shape.maxLocalProminence<.01&&r.shape.maxPitDepth<.01&&r.shape.maxSlope<.04
    &&r.diag.requestedDroplets===57556&&r.diag.cohorts===4&&r.diag.particleWeight===1);
  const pipeEdge=report.loadCase.pipe.edge,baseEdge=report.loadCase.baseEdge;
  const combinedLoad=report.loadCase.combined,pitControl=report.loadCase.pitControl;
  const ok=report.capability.dropletsReady
    &&report.dropMs>0&&report.dropMs<10000
    &&report.drop.finite&&report.drop.eroded>50&&report.drop.deposited>50
    &&report.drop.maxDrop>1e-5&&report.drop.maxRise>1e-5&&report.drop.rms>1e-5
    &&report.repeat.max<=1e-6&&report.reroll.rms>1e-6
    &&report.shape.injected.maxLocalProminence>.15&&report.shape.injected.peaksOver02>=1
    &&report.shape.injectedPit.maxPitDepth>.15&&report.shape.injectedPit.pitsOver02>=1
    &&report.shape.base.peaksOver02===0
    &&report.shape.droplets.peaksOver02===0&&report.shape.droplets.pitsOver02===0
    &&sharpRise<.008&&slopeGrowth<.015
    &&report.shape.combined.peaksOver02===0&&report.shape.combined.pitsOver02===0
    &&report.shape.combined.maxLocalProminence<.02&&report.shape.combined.maxPitDepth<.02
    &&report.defaultCase.effect.finite&&report.defaultCase.effect.eroded>500
    &&report.defaultCase.effect.deposited>500
    &&report.defaultCase.base.peaksOver02===0&&report.defaultCase.droplets.peaksOver02<=2
    &&report.defaultCase.droplets.maxLocalProminence<.03
    &&report.defaultCase.droplets.maxSlope-report.defaultCase.base.maxSlope<.025
    &&loadSweepOk&&reportedSeedSweepOk
    &&report.loadCase.dropletSweep[2].diag.particleWeight<.35
    &&report.loadCase.dropletSweep[2].diag.cohorts>=16
    &&report.loadCase.pipe.effect.finite&&report.loadCase.pipe.effect.eroded>500
    &&report.loadCase.pipe.effect.deposited>500
    &&report.loadCase.pipe.effect.maxDrop<.25&&report.loadCase.pipe.effect.maxRise<.25
    &&report.loadCase.pipe.shape.peaksOver02===0&&report.loadCase.pipe.shape.pitsOver02===0
    &&report.loadCase.pipe.shape.maxPitDepth<.01&&report.loadCase.pipe.shape.maxSlope<.04
    &&pipeEdge.maxEdgeChange<.08&&pipeEdge.p99<=baseEdge.p99*1.1
    &&pipeEdge.max<=baseEdge.max*1.1
    &&report.loadCase.pipe.diag.boundaryPolicy==='continuation-apron-closed-wall'
    &&report.loadCase.pipe.diag.boundaryApronCells>=32
    &&Math.abs(report.loadCase.pipe.diag.lost)<.01
    &&combinedLoad.ms>0&&combinedLoad.ms<30000&&combinedLoad.effect.finite
    &&combinedLoad.effect.eroded>500&&combinedLoad.effect.deposited>500
    &&combinedLoad.effect.maxDrop<.25&&combinedLoad.effect.maxRise<.25
    &&combinedLoad.shape.peaksOver02===0&&combinedLoad.shape.pitsOver02===0
    &&combinedLoad.shape.maxLocalProminence<.01&&combinedLoad.shape.maxPitDepth<.01
    &&combinedLoad.shape.maxSlope<.04&&combinedLoad.edge.p99<=baseEdge.p99*1.1
    &&combinedLoad.edge.max<=baseEdge.max*1.1
    &&combinedLoad.diag.requestedDroplets===230680&&combinedLoad.diag.cohorts>=16
    &&combinedLoad.diag.pipeBoundaryPolicy==='continuation-apron-closed-wall'
    &&pitControl.effect.finite&&pitControl.effect.maxDrop<.005
    &&pitControl.centerAdditionalDrop<.002&&pitControl.shape.maxPitDepth<.011
    &&report.cameraGuard.beforeY<report.cameraGuard.surfaceMax
    &&report.cameraGuard.afterY>report.cameraGuard.surfaceMax
    &&report.diagA.engine==='gpu-droplets'&&report.diagA.settle===false
    &&report.diagA.terminalDeposit===false&&report.diagA.unresolvedIncluded===true
    &&report.diagA.terminalPolicy==='suspend-at-lifetime'
    &&report.diagA.exportedDerived===true&&report.diagA.exportedOrSuspended>0
    &&report.combined.finite&&report.combined.eroded>50&&report.combined.deposited>50
    &&report.combinedDiag.engine==='gpu-combined'
    &&report.combinedDiag.terminalDeposit===false&&report.combinedDiag.unresolvedIncluded===true
    &&report.combinedDiag.terminalPolicy==='suspend-at-lifetime'
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
  console.log(JSON.stringify({...report,sharpRise,slopeGrowth,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error('FATAL',e);process.exit(2);});
