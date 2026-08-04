const { chromium } = require('playwright-core');
const path = require('node:path');
const EXE=process.env.STUDIO_CHROME||(process.platform==='win32'?'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe':'/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL=process.env.STUDIO_URL||('file://'+path.resolve(__dirname,'../../index.html'));
const mutation=(process.argv.find(value=>value.startsWith('--mutate='))||'').slice(9)||process.env.MC_MUTATION||null;
const VISUAL=process.argv.includes('--visual');
const MUTATIONS=['aspect-uphill','aspect-normalized-turns','aspect-linear-mean','aspect-preview-raw'];
if(mutation&&!MUTATIONS.includes(mutation)){console.error(`Unknown mutation ${mutation}`);process.exit(2);}

(async()=>{const browser=await chromium.launch({executablePath:EXE,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:900}});const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(800);
  const report=await page.evaluate(mutation=>{const assert=(ok,message)=>{if(!ok)throw new Error(message);},gamma=n=>n*2**-24/(1-n*2**-24);
    assert(TYPES.aspect&&TYPES.aspect.unit==='rad','Aspect registration/unit violated');assert(!EXACT_TYPES.has('aspect'),'Aspect exact eligibility violated');
    const pairs=[[.7,.2],[-.4,.9],[1.1,-.6],[-.8,-.3],[.25,-1.2]],offsets=[-.7,.15,2.3];let compared=0,flat=0,maxError=0,maxBound=0;
    const circular=(a,b)=>Math.abs(Math.atan2(Math.sin(a-b),Math.cos(a-b))),EX=[-1,1,-.5,.5,-.5,.5],EY=[0,0,-Math.sqrt(3)/2,-Math.sqrt(3)/2,Math.sqrt(3)/2,Math.sqrt(3)/2];
    for(const lattice of ['square','hex'])for(const resolution of [128,256]){RES=resolution;TARGET_RES=resolution;terrainDef.scale=5000;terrainDef.height=2600;terrainDef.lattice=lattice;terrainDef.north=0;
      const n=fieldW(),nh=fieldH(),d=terrainDef.scale/n;
      for(const [a,b] of pairs)for(const c of offsets){const input=newField();for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const wx=(x+.5+(lattice==='hex'?.5*(y&1):0))*d,wy=(y+.5)*d*(lattice==='hex'?Math.sqrt(3)/2:1);input[y*n+x]=a*wx/5000+b*wy/5000+c;}
        const rawActual=TYPES.aspect.eval({},[input]),actual=mutation==='aspect-normalized-turns'?TYPES.aspect.previewAdapter(rawActual,terrainDef):rawActual;for(let y=2;y<nh-2;y+=17)for(let x=2;x<n-2;x+=17){const i=y*n+x;let gx,gy,bx,by;
          if(lattice==='square'){const l=input[i-1],r=input[i+1],u=input[i-n],down=input[i+n];gx=(r-l)/(2*d);gy=(down-u)/(2*d);bx=gamma(4)*(Math.abs(r)+Math.abs(l))/(2*d);by=gamma(4)*(Math.abs(down)+Math.abs(u))/(2*d);}
          else{const odd=y&1,nb=odd?[[-1,0],[1,0],[0,-1],[1,-1],[0,1],[1,1]]:[[-1,0],[1,0],[-1,-1],[0,-1],[-1,1],[0,1]];let sx=0,sy=0,ax=0,ay=0;
            for(let k=0;k<6;k++){const h=input[(y+nb[k][1])*n+x+nb[k][0]];sx+=h*EX[k];sy+=h*EY[k];ax+=Math.abs(h*EX[k]);ay+=Math.abs(h*EY[k]);}gx=sx/(3*d);gy=sy/(3*d);bx=gamma(16)*ax/(3*d);by=gamma(16)*ay/(3*d);}
          const expected=Math.atan2(mutation==='aspect-uphill'?gy:-gy,mutation==='aspect-uphill'?gx:-gx),G=Math.hypot(gx,gy),E=Math.hypot(bx,by);assert(E<G,'Aspect oracle bound not finite-positive');
          const bound=Math.asin(Math.min(1,E/G))+gamma(3)*Math.PI,error=circular(actual[i],expected);assert(error<=bound,`${lattice} Aspect circular bound violated error=${error} bound=${bound}`);
          const dx=Math.abs(Math.cos(actual[i])-(-gx/G)),dy=Math.abs(Math.sin(actual[i])-(-gy/G));assert(Math.hypot(dx,dy)<=2*Math.sin(bound/2)+gamma(3),`${lattice} Aspect downslope vector violated`);
          assert(Number.isFinite(actual[i])&&actual[i]>=-Math.PI&&actual[i]<=Math.PI,`${lattice} Aspect finite range violated`);compared++;maxError=Math.max(maxError,error);maxBound=Math.max(maxBound,bound);}
      }
      const level=newField(.25),levelOut=TYPES.aspect.eval({},[level]);for(const value of levelOut){assert(value===0,'Aspect flat sentinel violated');flat++;}
    }
    assert(compared>0&&flat>0&&maxBound>0&&Number.isFinite(maxBound),'Aspect positive sample/bound counts violated');
    terrainDef.north=37;const angles=Float32Array.from([-Math.PI/2+37*Math.PI/180,0+37*Math.PI/180,Math.PI/2+37*Math.PI/180,Math.PI+37*Math.PI/180]);
    const preview=mutation==='aspect-preview-raw'?angles:TYPES.aspect.previewAdapter(angles,terrainDef),expectedTurns=[0,.25,.5,.75];for(let i=0;i<4;i++)assert(Math.abs(preview[i]-expectedTurns[i])<2e-7,`Aspect preview compass adapter violated index=${i} actual=${preview[i]} expected=${expectedTurns[i]}`);
    assert(TYPES.aspect.previewRange[0]===0&&TYPES.aspect.previewRange[1]===1,'Aspect fixed preview range violated');
    // S1.5's circular-statistics control, computed from PRODUCTION. It previously built a two-element
    // literal array [359deg, 1deg] and took its circular mean — arithmetic entirely inside the test,
    // identical on a broken build, and the only named negative control the story has. Same shape as
    // the shipped ({...TYPES.fracture, cat:'ero'}).cat !== 'surface'.
    //
    // The story's actual claim: "aspect is periodic — a naive mean would fail on a north-facing
    // slope straddling 0/360, which is the negative control". So build a north-facing slope, run it
    // through TYPES.aspect.eval, and take both means of the REAL aspect field. The circular mean
    // must land on north; the linear mean must NOT, which is what makes circular statistics
    // necessary rather than merely preferred.
    RES=64;TARGET_RES=64;terrainDef.lattice='square';terrainDef.north=0;
    {
      const n=fieldW(),nh=fieldH(),d=terrainDef.scale/n,slope=newField();
      // The slope must STRADDLE the seam, which is the whole point. A pure +y ramp gives a constant
      // aspect field, and a constant field has identical linear and circular means — so it cannot
      // demonstrate why circular statistics are needed. atan2 returns (-pi, pi], so the seam is at
      // +/-pi: a ramp in +x puts steepest descent at +/-pi, and a small sinusoidal wobble in y
      // pushes samples onto BOTH sides of it. That is the "north-facing slope straddling 0/360" the
      // story names, and it is where a naive mean collapses to ~0 instead of ~pi.
      for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
        const wx=(x+.5)*d,wy=(y+.5)*d;
        slope[y*n+x]=wx/5000+0.004*Math.sin(wy*2*Math.PI/1200);
      }
      const field=TYPES.aspect.eval({},[slope]);
      const interior=[];
      for(let y=2;y<nh-2;y++)for(let x=2;x<n-2;x++)interior.push(field[y*n+x]);
      assert(interior.length>0,'Aspect north-slope probe compared nothing');
      const circMean=Math.atan2(interior.reduce((t,v)=>t+Math.sin(v),0)/interior.length,
                                interior.reduce((t,v)=>t+Math.cos(v),0)/interior.length);
      const linMean=interior.reduce((t,v)=>t+v,0)/interior.length;
      // The expected azimuth is DERIVED from the same analytic formula the main loop validates
      // against — atan2(-gy, -gx), the direction of steepest descent — not assumed from a mental
      // model of the compass convention. Height here is wy/5000, so gx = 0 and gy = 1/5000.
      // Steepest descent for a +x ramp is -x, i.e. the seam at +/-pi. Derived, not assumed.
      const expectedNorth=Math.atan2(-0,-(1/5000));
      const chosen=mutation==='aspect-linear-mean'?linMean:circMean;
      assert(circular(chosen,expectedNorth)<.02,`Aspect circular mean violated circ=${circMean} lin=${linMean} expected=${expectedNorth}`);
      // The control only means something if the linear mean genuinely disagrees. Assert the gap,
      // so "circular statistics are required" is measured rather than assumed.
      assert(circular(linMean,circMean)>.5,`Aspect linear/circular means did not diverge circ=${circMean} lin=${linMean}`);
    }
    const raw=TYPES.aspect.eval({},[Float32Array.from(newField(),(_,i)=>i%fieldW())]);assert(raw.some(value=>value<0),'Aspect graph field was normalized for preview');
    return{compared,flat,maxError,maxBound,preview:Array.from(preview),mutation};
  },mutation);
  await page.locator('#nodeToolBtn').click();const ui=await page.evaluate(()=>{const toolbox=!!document.querySelector('.node-tool-item[data-type="aspect"]');RES=64;TARGET_RES=64;terrainDef.lattice='hex';terrainDef.north=37;const input=newField(),n=fieldW();for(let y=0;y<fieldH();y++)for(let x=0;x<n;x++)input[y*n+x]=Math.sin(x*.21)+Math.cos(y*.17);const field=TYPES.aspect.eval({},[input]),node=makeNode('aspect',50,50);node._field=field;selected=node;buildProps();const canvas=bakeThumb(node),pixels=canvas.getContext('2d').getImageData(0,0,48,48).data;let minimum=255,maximum=0;for(let i=0;i<pixels.length;i+=4){minimum=Math.min(minimum,pixels[i]);maximum=Math.max(maximum,pixels[i]);}previewMode='selected';refreshPreview();return{toolbox,title:document.querySelector('#pTitle')?.textContent||'',thumb:[canvas.width,canvas.height],variance:maximum-minimum,rawNegative:field.some(value=>value<0),range:TYPES.aspect.previewRange};});
  if(!ui.toolbox||!ui.title.includes('Aspect')||ui.thumb[0]!==48||ui.thumb[1]!==48||ui.variance<=0||!ui.rawNegative||ui.range[0]!==0||ui.range[1]!==1)throw new Error(`Aspect UI gate violated ${JSON.stringify(ui)}`);
  await page.locator('#nodeToolBtn').click();await page.locator('#graph').dblclick({position:{x:820,y:350}});const quick=await page.evaluate(()=>!!document.querySelector('#menu .menu-item[data-type="aspect"]'));if(!quick)throw new Error('Aspect quick-create discovery violated');if(VISUAL)for(const lattice of ['square','hex']){await page.evaluate(value=>{terrainDef.lattice=value;nodes.forEach(node=>{node._dirty=true;node._thumb=null;});evalGraph();if(typeof frameHero==='function')frameHero();},lattice);await page.waitForTimeout(250);await page.screenshot({path:path.resolve(__dirname,`_shot_aspect_${lattice}_close.png`)});await page.evaluate(()=>togglePlanView());await page.waitForTimeout(150);await page.screenshot({path:path.resolve(__dirname,`_shot_aspect_${lattice}_plan.png`)});await page.evaluate(()=>togglePlanView());}
  console.log(JSON.stringify({...report,ui,quick}));if(errors.length)throw new Error(errors.join('\n'));await browser.close();
})().catch(error=>{console.error(error.stack||error);process.exit(1);});