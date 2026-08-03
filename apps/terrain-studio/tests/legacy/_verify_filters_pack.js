const { chromium } = require('playwright-core');
const path = require('node:path');
const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome');
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'));
const mutation = (process.argv.find(value => value.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null;
const VISUAL = process.argv.includes('--visual');
const MUTATIONS = ['threshold-noop','morph-square-on-hex','match-cdf'];
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2); }

(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto(URL, { waitUntil: 'load' }); await page.waitForTimeout(800);
  const report = await page.evaluate(mutation => {
    const assert = (condition, message) => { if (!condition) throw new Error(message); };
    const equal = (actual, expected, message) => { assert(actual.length === expected.length, `${message}: length`);
      for (let index = 0; index < actual.length; index++) assert(Object.is(actual[index], expected[index]), `${message}: sample ${index}`); };
    const types = ['sharpen','threshold','dilate','deflate','match','softclip'];
    for (const type of types) assert(TYPES[type], `missing ${type}`);
    let assertions = types.length, samples = 0;
    RES = 16; TARGET_RES = 16; terrainDef.scale = 1600; terrainDef.height = 1000; terrainDef.lattice = 'square';
    const ramp = newField(); for (let index = 0; index < ramp.length; index++) ramp[index] = index;
    const threshold = mutation === 'threshold-noop' ? ramp.slice() : TYPES.threshold.eval({ cut: 100 }, [ramp]);
    assert(threshold[99] === 0 && threshold[100] === 1, 'Threshold equality/boundary violated'); assertions += 2;
    assert(TYPES.threshold.eval({ cut: -1 }, [ramp]).every(value => value === 1), 'Threshold below-min violated');
    assert(TYPES.threshold.eval({ cut: 256 }, [ramp]).every(value => value === 0), 'Threshold above-max violated'); assertions += 2;
    const moved = TYPES.threshold.eval({ cut: 116 }, [ramp]);
    assert(threshold.reduce((sum,value,index)=>sum+(value!==moved[index]),0) === 16, 'Threshold predicted moved count violated'); assertions++;

    const constant = new Float32Array(ramp.length).fill(.375);
    equal(TYPES.sharpen.eval({ amount: 0, radiusM: 200 }, [ramp,null]), ramp, 'Sharpen amount-zero identity');
    equal(TYPES.sharpen.eval({ amount: 2, radiusM: 200 }, [constant,null]), constant, 'Sharpen constant identity'); assertions += 2;
    const edge = newField(); for (let y=0;y<16;y++) for (let x=8;x<16;x++) edge[y*16+x]=1;
    const sharp = TYPES.sharpen.eval({ amount: 1, radiusM: 100 }, [edge,null]);
    assert(sharp[8*16+8]-sharp[8*16+7] > 1, 'Sharpen edge contrast violated'); assertions++;
    const sharp2=TYPES.sharpen.eval({amount:2,radiusM:100},[edge,null]);for(let i=0;i<edge.length;i++)assert(Math.abs(sharp2[i]-(edge[i]+2*(sharp[i]-edge[i])))<3e-7,`Sharpen direct formula violated sample=${i}`);assertions++;samples+=edge.length;

    const morphologyOracle = (input,k,dilate,hex) => { const out = new Float32Array(input.length), n=RES, nh=input.length/n;
      for (let y=0;y<nh;y++) for (let x=0;x<n;x++) { let value=dilate?-Infinity:Infinity;
        if (hex) { const q=x-((y-(y&1))>>1); for(let dr=-k;dr<=k;dr++)for(let dq=Math.max(-k,-dr-k);dq<=Math.min(k,-dr+k);dq++){
          const yy=y+dr,xx=q+dq+((yy-(yy&1))>>1); if(xx<0||yy<0||xx>=n||yy>=nh)continue;
          value=dilate?Math.max(value,input[yy*n+xx]):Math.min(value,input[yy*n+xx]); }
        } else for(let dy=-k;dy<=k;dy++)for(let dx=-k;dx<=k;dx++){if(dx*dx+dy*dy>k*k)continue;
          const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=n||yy>=nh)continue;value=dilate?Math.max(value,input[yy*n+xx]):Math.min(value,input[yy*n+xx]);}
        out[y*n+x]=value; } return out; };
    for (const lattice of ['square','hex']) { terrainDef.lattice=lattice; const input=newField();
      for(let i=0;i<input.length;i++)input[i]=Math.sin(i*.31)+i*.001;
      for (const [type,dilate] of [['dilate',true],['deflate',false]]) { const actual=TYPES[type].eval({radiusM:200},[input,null]);
        const oracleHex = mutation === 'morph-square-on-hex' && lattice === 'hex' ? false : lattice === 'hex';
        const expected=morphologyOracle(input,2,dilate,oracleHex); equal(actual,expected,`${type} ${lattice} disc`); samples += actual.length; assertions++; }
    }
    for(const lattice of ['square','hex'])for(const resolution of [128,256]){RES=resolution;TARGET_RES=resolution;terrainDef.lattice=lattice;terrainDef.scale=5000;const n=fieldW(),nh=fieldH(),d=terrainDef.scale/n,disc=newField(),cx=2500,cy=2500,baseRadius=600,radiusM=220,k=Math.round(radiusM/d),effective=k*d;
      for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const wx=(x+.5+(lattice==='hex'?.5*(y&1):0))*d,wy=(y+.5)*d*(lattice==='hex'?Math.sqrt(3)/2:1);disc[y*n+x]=Math.hypot(wx-cx,wy-cy)<=baseRadius?1:0;}
      for(const [type,expectedRadius] of [['dilate',baseRadius+effective],['deflate',baseRadius-effective]]){const out=TYPES[type].eval({radiusM},[disc,null]);let measured=0,count=0;for(let y=0;y<nh;y++)for(let x=0;x<n;x++)if(out[y*n+x]>.5){const wx=(x+.5+(lattice==='hex'?.5*(y&1):0))*d,wy=(y+.5)*d*(lattice==='hex'?Math.sqrt(3)/2:1);measured=Math.max(measured,Math.hypot(wx-cx,wy-cy));count++;}assert(count>0,`${type} ${lattice} ${resolution} empty physical disc`);assert(Math.abs(measured-expectedRadius)<=d,`${type} ${lattice} ${resolution} physical radius violated measured=${measured} expected=${expectedRadius} cell=${d}`);assertions+=2;samples+=count;}}

    terrainDef.lattice='square'; const source=Float32Array.from([4,1,4,2,3,2,1,3]);
    const target=Float32Array.from([40,10,30,20,20,30,10,40]);
    const rank=(field)=>Array.from(field,(value,index)=>({value,index})).sort((a,b)=>a.value-b.value||a.index-b.index);
    const s=rank(source),t=rank(target),rankExpected=new Float32Array(source.length);for(let k=0;k<s.length;k++)rankExpected[s[k].index]=t[k].value;
    const matched=mutation==='match-cdf'?Float32Array.from(source,value=>value/4):TYPES.match.eval({},[source,target]);
    equal(matched,rankExpected,'Match stable rank violated'); equal(TYPES.match.eval({},[source,source]),source,'Match self identity'); assertions+=2;samples+=source.length;
    const bins=new Float32Array(1024);for(let i=0;i<bins.length;i++)bins[i]=i%256;
    const binsOut=TYPES.match.eval({},[Float32Array.from(bins,(v,i)=>((i*313)%1024)),bins]);
    const counts=new Uint32Array(256);for(const value of binsOut)counts[value]++;assert(counts.every(count=>count===4),'Match target multiplicities violated');assertions++;

    const values=Float32Array.from([-1,0,.25,.5,.75,1,2]);
    for(const softness of [0,.4,1]){const actual=TYPES.softclip.eval({lo:0,hi:1,softness},[values,null]);
      for(let i=0;i<values.length;i++){const x=values[i],u=Math.max(0,Math.min(1,x)),expected=u+softness*(u*u*(3-2*u)-u);
        assert(actual[i]===Math.fround(expected),`SoftClip formula violated softness=${softness} sample=${i}`);samples++;}assertions++;}
    return { types, assertions, samples, mutation };
  }, mutation);
  await page.locator('#nodeToolBtn').click();
  const ui = await page.evaluate(types => {
    const toolbox=[...document.querySelectorAll('.node-tool-item')].filter(item=>types.includes(item.dataset.type)).map(item=>item.dataset.type);
    RES=32;TARGET_RES=32;terrainDef.lattice='square';const source=newField(),target=newField(),driver=newField();
    for(let i=0;i<source.length;i++){source[i]=Math.sin(i*.13)+i/source.length;target[i]=(i*17)%251;driver[i]=Math.sin(i*.07);}
    const nodesReport=types.map(type=>{const def=TYPES[type],params=Object.fromEntries(def.params.map(param=>[param.key,cloneParams(param.def)]));
      const inputs=def.ins.map(name=>name==='Mask'?null:name==='Target'?target:source),field=def.eval(params,inputs),node=makeNode(type,50,50);node._field=field;selected=node;buildProps();
      const canvas=bakeThumb(node),pixels=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;let minimum=255,maximum=0;for(let i=0;i<pixels.length;i+=4){minimum=Math.min(minimum,pixels[i]);maximum=Math.max(maximum,pixels[i]);}
      return{type,title:document.querySelector('#pTitle')?.textContent||'',controls:document.querySelectorAll('#pBody input,#pBody select,#pBody button').length,params:def.params.length,thumb:[canvas.width,canvas.height],variance:maximum-minimum};});
    return{toolbox,nodes:nodesReport};
  },report.types);
  if(ui.toolbox.length!==report.types.length||ui.nodes.some(node=>!node.title||node.controls<node.params||node.thumb[0]!==48||node.thumb[1]!==48||node.variance<=0))throw new Error(`Filter UI gate violated ${JSON.stringify(ui)}`);
  await page.locator('#nodeToolBtn').click();await page.locator('#graph').dblclick({position:{x:820,y:350}});
  const quick=await page.evaluate(types=>types.every(type=>document.querySelector(`#menu .menu-item[data-type="${type}"]`)),report.types);if(!quick)throw new Error('Filter quick-create discovery violated');
  if(VISUAL)await page.screenshot({path:path.resolve(__dirname,'_shot_filters_pack.png')});
  console.log(JSON.stringify({...report,ui:{toolbox:ui.toolbox.length,nodes:ui.nodes},quick})); if (errors.length) throw new Error(errors.join('\n'));
  await browser.close();
})().catch(error => { console.error(error.stack || error); process.exit(1); });