const { chromium } = require('playwright-core');
const path = require('node:path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32' ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe' : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));
const mutation = (process.argv.find(value=>value.startsWith('--mutate='))||'').slice(9)||process.env.MC_MUTATION||null;
const VISUAL=process.argv.includes('--visual');
const MUTATIONS=['raw-odd-r-transpose','directionalwarp-constant-translation','directionalwarp-abs-driver','directionalwarp-cell-space'];
if(mutation&&!MUTATIONS.includes(mutation)){console.error(`Unknown mutation ${mutation}`);process.exit(2);}

(async()=>{const browser=await chromium.launch({executablePath:EXE,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:900}});const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(URL,{waitUntil:'load'});await page.waitForTimeout(800);
  const report=await page.evaluate(mutation=>{const assert=(ok,message)=>{if(!ok)throw new Error(message);};
    const types=['flip','transpose','fold','directionalwarp'];for(const type of types){assert(TYPES[type],`missing ${type}`);assert(!EXACT_TYPES.has(type),`${type} exact eligibility violated`);}
    let assertions=8,samples=0;const maxError=(a,b)=>{let m=0;for(let i=0;i<a.length;i++)m=Math.max(m,Math.abs(a[i]-b[i]));return m;};
    for(const lattice of ['square','hex'])for(const resolution of [128,256]){RES=resolution;TARGET_RES=resolution;terrainDef.scale=5000;terrainDef.height=2600;terrainDef.north=0;terrainDef.lattice=lattice;
      const n=fieldW(),nh=fieldH(),d=terrainDef.scale/n,input=newField(),xRamp=newField(),yRamp=newField(),zero=newField(),plus=newField(1),minus=newField(-1),varying=newField();
      for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const wx=(x+.5+(lattice==='hex'?.5*(y&1):0))*d,wy=(y+.5)*d*(lattice==='hex'?Math.sqrt(3)/2:1),i=y*n+x;
        xRamp[i]=wx/5000;yRamp[i]=wy/5000;input[i]=.2+wx/10000+wy/20000;varying[i]=(x/(n-1))*2-1;}
      const flip=TYPES.flip.eval({axis:'horizontal'},[input,null]);if(lattice==='square'){const twice=TYPES.flip.eval({axis:'horizontal'},[flip,null]);assert(maxError(twice,input)===0,'Square Flip twice identity violated');assertions++;}
      // THE STORY'S NAMED FAILING FIXTURE, spelled the way the story names it: "A raw odd-r array
      // transpose is the armed failing fixture." This previously fed production a REVERSED array
      // (Float32Array.from(input).reverse()), which is not a transpose of anything — it turned the
      // gate red, but for garbage input rather than for the defect the story describes, so the
      // named failure mode had never actually been executed.
      //
      // A raw odd-r transpose swaps array indices directly, out[x*nh+y] = in[y*n+x]. On square that
      // IS the world transpose. On hex it is wrong, because odd rows sit half a cell right and rows
      // are sqrt(3)/2 apart — so index space is not world space, and the affine assertion below is
      // exactly what catches it. Substituting it for production's output is the fixture.
      let trans=TYPES.transpose.eval({},[input,null]);
      if(mutation==='raw-odd-r-transpose'){
        const raw=newField();
        for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const ty=x,tx=y;if(ty<nh&&tx<n)raw[ty*n+tx]=input[y*n+x];}
        trans=raw;
      }
      const margin=Math.ceil(300/d)+2;for(let y=margin;y<nh-margin;y++)for(let x=margin;x<n-margin;x++){const i=y*n+x,wx=(x+.5+(lattice==='hex'?.5*(y&1):0))*d,wy=(y+.5)*d*(lattice==='hex'?Math.sqrt(3)/2:1);
        assert(Math.abs(trans[i]-(.2+wy/10000+wx/20000))<3e-6,`${lattice} Transpose affine violated`);samples++;}
      assertions++;
      const folded=TYPES.fold.eval({bearing:0,offsetM:0},[xRamp,null]);assert(folded.every(Number.isFinite),`${lattice} Fold finite violated`);assertions++;
      const identity=TYPES.directionalwarp.eval({bearing:90,amplitudeM:300},[input,zero,null]);assert(maxError(identity,input)===0,`${lattice} DirectionalWarp zero-driver identity violated`);assertions++;
      const positive=TYPES.directionalwarp.eval({bearing:90,amplitudeM:300},[xRamp,plus,null]);const negative=TYPES.directionalwarp.eval({bearing:90,amplitudeM:300},[xRamp,minus,null]);
      const varyingDriver=mutation==='directionalwarp-constant-translation'?plus:mutation==='directionalwarp-abs-driver'?Float32Array.from(varying,Math.abs):varying;
      const amplitude=mutation==='directionalwarp-cell-space'?300*d:300,warped=TYPES.directionalwarp.eval({bearing:90,amplitudeM:amplitude},[xRamp,varyingDriver,null]);
      let distinct=false,opposite=false;for(let y=margin;y<nh-margin;y++)for(let x=margin;x<n-margin;x++){const i=y*n+x,base=xRamp[i],expected=base+300*varying[i]/5000;
        assert(Math.abs(warped[i]-expected)<3e-6,`${lattice} DirectionalWarp varying Driver violated index=${i} actual=${warped[i]} expected=${expected}`);distinct ||= Math.abs(warped[i]-base)>1e-4&&Math.abs(warped[i]-base)<.05;opposite ||= positive[i]>base&&negative[i]<base;samples++;}
      assert(distinct,`${lattice} DirectionalWarp displacement diversity violated`);assert(opposite,`${lattice} DirectionalWarp signed Driver violated`);assertions+=2;
    }
    return{types,assertions,samples,mutation};
  },mutation);
  await page.locator('#nodeToolBtn').click();const ui=await page.evaluate(types=>{const toolbox=[...document.querySelectorAll('.node-tool-item')].filter(item=>types.includes(item.dataset.type)).map(item=>item.dataset.type);
    RES=32;TARGET_RES=32;terrainDef.lattice='hex';const source=newField(),driver=newField();for(let i=0;i<source.length;i++){source[i]=Math.sin(i*.11)+i/source.length;driver[i]=Math.sin(i*.07);}
    const nodesReport=types.map(type=>{const def=TYPES[type],params=Object.fromEntries(def.params.map(param=>[param.key,cloneParams(param.def)])),inputs=def.ins.map(name=>name==='Mask'?null:name==='Driver'?driver:source),field=def.eval(params,inputs),node=makeNode(type,50,50);node._field=field;selected=node;buildProps();const canvas=bakeThumb(node),pixels=canvas.getContext('2d').getImageData(0,0,48,48).data;let minimum=255,maximum=0;for(let i=0;i<pixels.length;i+=4){minimum=Math.min(minimum,pixels[i]);maximum=Math.max(maximum,pixels[i]);}return{type,title:document.querySelector('#pTitle')?.textContent||'',controls:document.querySelectorAll('#pBody input,#pBody select,#pBody button').length,params:def.params.length,thumb:[canvas.width,canvas.height],variance:maximum-minimum};});return{toolbox,nodes:nodesReport};},report.types);
  if(ui.toolbox.length!==report.types.length||ui.nodes.some(node=>node.controls<node.params||node.thumb[0]!==48||node.thumb[1]!==48||node.variance<=0))throw new Error(`Coordinate UI gate violated ${JSON.stringify(ui)}`);
  await page.locator('#nodeToolBtn').click();await page.locator('#graph').dblclick({position:{x:820,y:350}});const quick=await page.evaluate(types=>types.every(type=>document.querySelector(`#menu .menu-item[data-type="${type}"]`)),report.types);if(!quick)throw new Error('Coordinate quick-create discovery violated');if(VISUAL)await page.screenshot({path:path.resolve(__dirname,'_shot_coordinate_filters.png')});
  console.log(JSON.stringify({...report,ui:{toolbox:ui.toolbox.length,nodes:ui.nodes},quick}));if(errors.length)throw new Error(errors.join('\n'));await browser.close();
})().catch(error=>{console.error(error.stack||error);process.exit(1);});