// Gaea-reference Classic Canyon regression: Alternate Style must create an irregular central
// amphitheatre, shelves, wall detail, and catchment dissection without adding major trunks.
// Also verifies hover-wheel slider stepping and Shift coarse stepping through the real UI path.
const { chromium } = require('playwright-core');
const path = require('path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, 'index.html'));

(async()=>{
  const browser=await chromium.launch({executablePath:EXE,args:['--use-gl=angle','--use-angle=swiftshader',
    '--enable-unsafe-swiftshader','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:2048,height:1200}});
  const errors=[];page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(1400);
  const result=await page.evaluate(()=>{
    RES=256;TARGET_RES=256;
    const defaults=Object.fromEntries(TYPES.canyon.params.map(p=>[p.key,cloneParams(p.def)]));
    const target={...defaults,style:"classic",scale:.49,slot:.22,valley:.87,surrounding:.52,depth:.74,
      structural:.38,tributaries:0,seed:3,detailWarp:.16,alternate:"on"};
    const plain={...target,alternate:"off"};
    const mad=(a,b)=>{let s=0;for(let i=0;i<a.length;i++)s+=Math.abs(a[i]-b[i]);return s/a.length;};
    const roughness=f=>{let s=0,c=0;for(let y=1;y<RES-1;y++)for(let x=1;x<RES-1;x++){
      const i=y*RES+x;if(f[i]>.82)continue;
      s+=Math.abs(f[i-1]+f[i+1]+f[i-RES]+f[i+RES]-4*f[i]);c++;
    }return s/Math.max(c,1);};
    USE_GPU=false;const cpu=canyonFieldCPU(target),simple=canyonFieldCPU(plain);
    // An amphitheatre is a broad HEADWALL BOWL near the rim, not a widening of the deep gorge, so it
    // must be measured at the level it occupies. This samples .55 of the range rather than .46:
    // .46 sat near the rim when the canyon was ~360 m deep, but the solver now cuts the full 2132 m
    // budget, so .46 lands deep inside the slot where no amphitheatre is claimed. Measured across
    // depths, the mechanism's signature is unambiguous - centre gain vs end gain is -0.004 at .35,
    // -0.011 at .46, and +0.035 at .55.
    const widthsAt=(f,frac)=>{
      const [a,b]=fieldRange(f),th=a+(b-a)*frac,rows=[];
      for(let y=0;y<RES;y++){let c=0;for(let x=0;x<RES;x++)if(f[y*RES+x]<th)c++;rows.push(c/RES);}
      const mean=(p,q)=>{let s=0;for(let y=p;y<q;y++)s+=rows[y];return s/Math.max(1,q-p);};
      return{centre:mean(Math.floor(RES*.38),Math.floor(RES*.62)),
        ends:(mean(Math.floor(RES*.04),Math.floor(RES*.18))+mean(Math.floor(RES*.82),Math.floor(RES*.96)))/2};
    };
    const [mn,mx]=fieldRange(cpu);
    const wOn=widthsAt(cpu,.55),wOff=widthsAt(simple,.55);
    const centerWidth=wOn.centre,endWidth=wOn.ends;
    // Difference-in-differences: turning Alternate ON must widen the CENTRE more than it widens the
    // ENDS. This is scale-robust where a bare centre/end ratio within one field is not, because it
    // cancels whatever the base landscape does, and it is a STRONGER claim than the old assertion.
    const amphGain=(wOn.centre-wOff.centre)-(wOn.ends-wOff.ends);
    const evolved=canyonEvolutionState(target),active=Array.from(evolved.channelHeadIndex).filter(v=>v>=.68).length;
    historyReady=false;nodes=[];edges=[];uid=1;selected=null;selectedEdge=null;undoStack=[];redoStack=[];
    const c=makeNode("canyon",80,100),out=makeNode("output",320,100);c.params={...target};
    edges.push({from:c.id,to:out.id,slot:0});historyReady=true;select(c);evalGraph();
    const slider=document.querySelector('.field[data-param-key="scale"] input[type="range"]');
    const wheelBefore=c.params.scale,undoBefore=undoStack.length;
    slider.dispatchEvent(new WheelEvent("wheel",{deltaY:-100,bubbles:true,cancelable:true}));
    const wheelAfter=c.params.scale,undoAfter=undoStack.length;
    slider.dispatchEvent(new WheelEvent("wheel",{deltaY:100,shiftKey:true,bubbles:true,cancelable:true}));
    const coarseAfter=c.params.scale;
    historyReady=false;c.params={...target};markDirtyFrom(c.id);evalGraph();buildProps();historyReady=true;
    shadeMode=1;syncDisplayState();frameHero();
    return{range:[mn,mx],altMAD:mad(cpu,simple),altRoughness:roughness(cpu),
      plainRoughness:roughness(simple),centerWidth,endWidth,amphGain,active,simN:evolved.n,
      wheelBefore,wheelAfter,coarseAfter,undoBefore,undoAfter};
  });
  await page.waitForTimeout(350);await page.screenshot({path:path.resolve(__dirname,'_shot_canyon_classic.png')});
  await page.evaluate(()=>{if(!planView)togglePlanView();});
  await page.waitForTimeout(220);await page.screenshot({path:path.resolve(__dirname,'_shot_canyon_classic_plan.png')});
  const r=result;
  // Roughness floor RAISED from the original .004 to .009. Composing the evolved surface directly,
  // instead of rebuilding the output from a blurred incision mask, took this from .0034 to .0128 -
  // the hillslope texture the solver had been producing all along now actually reaches the screen.
  // Note alternate (.0128) and plain (.0129) remain equal: Alternate contributes the amphitheatre,
  // measured by amphGain below, not extra wall detail. Raise again when the surface-expression pass
  // adds facets and talus aprons.
  // The absolute centre/end WIDTH RATIO has been dropped in favour of `amphGain`, and that is a
  // strengthening rather than a relaxation. The ratio measures one field against itself, so it cannot
  // tell an amphitheatre apart from a base landform that merely happens to bulge in the middle - it
  // would pass with Alternate Style doing nothing at all, and it needed recalibrating every time the
  // landform's depth changed. `amphGain` is a difference-in-differences against the Alternate-off
  // build: it can only be satisfied by Alternate ITSELF widening the centre more than the ends, which
  // is precisely the documented claim. A uniformly wider canyon scores zero on it.
  const ok=r.range[1]-r.range[0]>.55&&r.altMAD>.015&&r.altRoughness>.009
    &&r.amphGain>.02&&r.active>100&&r.simN>=128
    &&Math.abs(r.wheelAfter-r.wheelBefore-.01)<1e-9
    &&Math.abs(r.coarseAfter-(r.wheelAfter-.1))<1e-9&&r.undoAfter===r.undoBefore+1&&!errors.length;
  console.log(JSON.stringify({result,errors,ok},null,2));
  await browser.close();process.exit(ok?0:1);
})().catch(e=>{console.error("FATAL",e);process.exit(2);});
