// Runs the Canyon verification suite and prints a one-line-per-test summary with the headline
// numbers, so a full status check is one command. Each child is a normal standalone script; run any
// of them directly to see its full JSON. Exit code is non-zero if any test fails.
//   node _verify_all_canyon.js            all canyon + shared tests
//   node _verify_all_canyon.js --quick    canyon only, skips render/realtime/build_progress
const { execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const CANYON = [
  ['_verify_canyon_relief.js',   'relief budget: depth is cut by the solve, not stamped on'],
  ['_verify_canyon_slopes.js',   'cliff/talus: modes must track the bed table, not geometry'],
  ['_verify_canyon_gridscale.js','grid invariance: landform must survive a resolution change'],
  ['_verify_canyon_evolution.js','network: connectivity, hierarchy, junctions, taper, cache'],
  ['_verify_canyon.js',          'controls, five styles, determinism, grouped UI'],
  ['_verify_canyon_classic.js',  'Classic amphitheatre, wall detail, slider stepping'],
  ['_verify_canyon_process.js',  'Canyon -> Erosion 2 -> HydroFix production chain'],
  ['_verify_canyon_identity.js', 'cache-key correctness + build-to-build digest'],
];
const SHARED = [
  ['_verify_render.js',         'renderer'],
  ['_verify_realtime.js',       'realtime path'],
  ['_verify_build_progress.js', 'build progress UI'],
];

const quick = process.argv.includes('--quick');
const tests = quick ? CANYON : CANYON.concat(SHARED);

// Pull a few headline numbers out of whatever JSON the child printed, without knowing its schema.
const PICK = ['buildMs','depthMs','composeCorr','cutP99','medianRowRelief','bedsAbove5pct','plateauPct',
  'connectivity','activeChainFraction','gapMaxAreaFrac','maxStrahler','trunkLength','amphGain',
  'altRoughness','deterministic'];
const harvest=(node,out={},depth=0)=>{
  if(!node||typeof node!=='object'||depth>3)return out;
  for(const [k,v] of Object.entries(node)){
    if(PICK.includes(k)&&(typeof v==='number'||typeof v==='boolean')&&!(k in out))out[k]=v;
    else if(v&&typeof v==='object')harvest(v,out,depth+1);
  }
  return out;
};

let failed=0;
console.log(`\nCanyon verification suite  (${tests.length} tests)\n`);
for(const [file,what] of tests){
  const started=process.hrtime.bigint();
  let code=0,stdout='';
  try{
    stdout=execFileSync(process.execPath,[path.resolve(__dirname,file)],
      {cwd:__dirname,encoding:'utf8',stdio:['ignore','pipe','pipe'],maxBuffer:64*1024*1024});
  }catch(e){code=e.status==null?1:e.status;stdout=(e.stdout||'')+(e.stderr||'');}
  const secs=Number(process.hrtime.bigint()-started)/1e9;
  if(code!==0)failed++;
  let nums='';
  try{
    const brace=stdout.indexOf('{');
    if(brace>=0){
      const got=harvest(JSON.parse(stdout.slice(brace)));
      nums=Object.entries(got).map(([k,v])=>
        `${k}=${typeof v==='number'&&!Number.isInteger(v)?Number(v.toFixed(4)):v}`).join('  ');
    }
  }catch{ /* a crashed child has no JSON to report; the FAIL line is the signal */ }
  console.log(`${code===0?' PASS':' FAIL'}  ${file.padEnd(30)} ${secs.toFixed(1)}s  ${what}`);
  if(nums)console.log(`        ${nums}`);
  if(code!==0&&stdout.trim())console.log(`        ${stdout.trim().split('\n').slice(-4).join('\n        ')}`);
}
// STATE THE COVERAGE, ALWAYS. This file runs a hand-written list, and for a long time it printed
// "all passed" while covering 12 of the 70 oracles on disk - including neither _verify_digest.js,
// the byte-identity gate of record, nor any hex oracle. Promoting the opening document to L0 broke
// 17 oracles; this list caught 2, and four subsequent commits each read as a green suite.
//
// A suite that does not say what it skipped cannot be audited by watching it pass, so the count is
// printed next to the verdict and the number on disk is COUNTED rather than hardcoded - a hardcoded
// total would drift back into a lie the moment someone adds an oracle.
const onDisk = fs.readdirSync(__dirname).filter(f => /^_verify_.*\.js$/.test(f) && f !== path.basename(__filename));
const skipped = onDisk.length - tests.length;
console.log(`\n${failed?`${failed} FAILED`:'all passed'}  —  ran ${tests.length} of ${onDisk.length} oracles`
  + `${skipped>0?`, ${skipped} NOT RUN (this is the Canyon suite; use \`npm run verify:all\` for every oracle)`:''}\n`);
process.exit(failed?1:0);
