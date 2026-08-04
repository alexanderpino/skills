import { GPU, gpuFbm, gpuThermal, gpuWarp, gpuHydraulicPipes, gpuHydraulicDroplets,
  gpuHydraulicCombined, gpuReady, gpuDropletsReady, hydroMassDiag, setHydroMassDiag,
  setGL as setGpuGL } from './core/gpu.js';
import { mergePlugins, attachLegacyPorts } from './core/registry.js';
import './plugins/out/index.js';
import './plugins/data/index.js';
import './plugins/effect/index.js';
import './plugins/ero/index.js';
import './plugins/gen/index.js';
import './plugins/surface/index.js';
import './plugins/filt/index.js';
import './plugins/mask/index.js';
import './plugins/comb/index.js';
import { P, WHEN, GROUP, CAT } from './core/params.js';
import { mountainSkirtDefault } from './core/defaults.js';
import { makeProg, u, setGL as setGlUtilGL } from './core/gl-util.js';
// Acyclic core import, safe at module-evaluation time: project.js imports nothing from here.
import { canConnect, validatePortList, GENERICS, SEMANTICS, UNITS, RANGE } from './core/ports.js';
import { AUX_MAPS, AUX_LENSES, SIDE_CHANNEL_LEDGER, semanticDebt, debtByOwner, validateAuxDeclaration } from './core/aux-maps.js';
import { validateLegalOrder, validateLens, DOCTRINE_STAGES, DERIVED_PRODUCERS, HEIGHT_WRITERS } from './core/doctrine.js';
import { parseExpr, evalExpr, EXPR_FUNCTIONS, EXPR_MAX_NODES, EXPR_MAX_DEPTH } from './core/expr.js';
import { makeScope, validateVariables, requireVariable, VARIABLE_UNITS } from './core/variables.js';
import { expandPreset as expandWavePreset, glslGerstner, glslWaterDetail, glslShoal, presetBounds } from './core/water-waves.js';
import { BIOMES, BIOME_KEYS, DEFAULT_BIOME, biomeTerrainOverrides, biomeSeaLevel, biomePrecipMmYr } from './core/biomes.js';
import { domainFromLegacy, deriveResolution, validateDomain, spacingWasRounded, WORLD_DOMAIN_VERSION, AUTHORING_UNITS } from './core/world-domain.js';
import { assessCreation, decomposePages, formatBytes } from './core/feasibility.js';
import { registerDefinition, definitionHash, findRecursion, validateDefinition, instanceCacheKey, referencedDefinitions, closureHashes, fieldKey, SUBGRAPH_VERSION } from './core/subgraph.js';
import { LEGACY_PORTS, LEGACY_ROSTER, LEGACY_INS_LABELS } from './core/legacy-ports.js';
import { serializeProject, parseProject, migrateProject, migrateV1toV2, migrateV2toV3, validateProject,
  PROJECT_SCHEMA_VERSION, PROJECT_FILE_EXTENSION, ProjectError } from './core/project.js';

"use strict";
/* =====================================================================
   TERRAIN STUDIO — a node-based WebGL terrain generator.
   Compute runs on the CPU (Float32Array heightfields, deterministic,
   mirrors the pure-numpy reference-impl atoms); the 3D viewport is WebGL2.
   ===================================================================== */
const $=s=>document.querySelector(s);
export const clamp=(x,a,b)=>x<a?a:x>b?b:x;
export const lerp=(a,b,t)=>a+(b-a)*t;
export const smooth=t=>t*t*(3-2*t);
const fade5=t=>t*t*t*(t*(t*6-15)+10);          // improved Perlin: C2 at lattice boundaries
const fract=x=>x-Math.floor(x);
// Wheel-adjust every range control while hovered. Small precision-trackpad deltas accumulate into
// one step; a normal mouse notch changes one step, Shift changes ten. Dispatching input + change
// deliberately reuses each control's normal preview, invalidation, formatting, and undo path.
const rangeWheelCarry=new WeakMap();
document.addEventListener("wheel",e=>{
  const inp=e.target&&e.target.closest?e.target.closest('input[type="range"]'):null;
  if(!inp||inp.disabled)return;
  e.preventDefault();e.stopPropagation();
  const raw=e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?120:1);
  let carry=rangeWheelCarry.get(inp)||0;
  if(carry&&Math.sign(carry)!==Math.sign(raw))carry=0;
  carry+=raw;
  if(Math.abs(carry)<8){rangeWheelCarry.set(inp,carry);return;}
  const notches=Math.max(1,Math.min(12,Math.round(Math.abs(carry)/100)));
  rangeWheelCarry.set(inp,0);
  const min=Number.isFinite(inp.minAsNumber)?inp.minAsNumber:parseFloat(inp.min);
  const max=Number.isFinite(inp.maxAsNumber)?inp.maxAsNumber:parseFloat(inp.max);
  const lo=Number.isFinite(min)?min:-Infinity,hi=Number.isFinite(max)?max:Infinity;
  const declared=parseFloat(inp.step),step=Number.isFinite(declared)&&declared>0?declared:
    Number.isFinite(lo)&&Number.isFinite(hi)?(hi-lo)/100:1;
  const current=Number.isFinite(inp.valueAsNumber)?inp.valueAsNumber:parseFloat(inp.value)||0;
  const direction=carry<0?1:-1,mult=e.shiftKey?10:1;
  const precision=Math.min(10,Math.max(0,(String(step).split(".")[1]||"").length));
  const next=clamp(current+direction*step*mult*notches,lo,hi);
  const rounded=Number(next.toFixed(precision));
  if(rounded===current)return;
  inp.value=String(rounded);
  inp.dispatchEvent(new Event("input",{bubbles:true}));
  inp.dispatchEvent(new Event("change",{bubbles:true}));
},{passive:false,capture:true});

export let RES=512;                                   // active working grid resolution (square)
let TARGET_RES=RES;                            // profile target; 2K/4K wait for an explicit Build
let AUTO=true;
// SatMap colour LUTs — curated elevation gradients (Gaea's "SatMap" idea). "Dune" is EXTRACTED from a
// real NASA Terra/ASTER top-down image (reference-impl render.extract_satmap); the rest are authored to
// real terrain palettes. Applied as a 1-D lookup by normalized height, blended to rock on slopes.
// SatMap colour LUTs — elevation gradients (low -> high), stops [pos,[r,g,b]].
// Most are GENUINELY DERIVED from real public-domain top-down satellite/aerial imagery, not hand-picked:
// each source image (see satmaps/derived.json + satmaps/extract_satmaps.py) is ordered by luminance into
// an elevation ramp with the skill's reference-impl `extract_satmap` (Rec.709). Derived: Alpine (Ligurian
// Alps), Dune (Rub' al Khali / Terra), Verdant (Amazon / Landsat), Volcanic (Icelandic lava / ESA),
// Arctic (Greenland), Tundra (Iceland / ESA), Lunar (LROC). Authored to real palettes where no on-biome
// true-colour source was available: Temperate, Canyon, Arid, Mars. (NASA/USGS = public domain; ESA = CC BY.)
const SATMAPS={
 Temperate:[[0,[46,78,54]],[.12,[72,104,66]],[.34,[120,138,86]],[.54,[150,140,104]],[.74,[126,116,102]],[.9,[182,178,174]],[1,[236,240,246]]],
 Alpine:[[0,[37,36,23]],[.125,[49,45,27]],[.208,[66,58,33]],[.292,[80,69,39]],[.375,[91,78,46]],[.458,[99,87,54]],[.542,[107,95,63]],[.625,[120,110,83]],[.708,[148,140,122]],[.792,[187,182,172]],[.875,[225,223,216]],[1,[247,245,239]]],
 Verdant:[[0,[3,32,2]],[.125,[4,35,2]],[.208,[5,38,3]],[.292,[7,42,4]],[.375,[11,46,6]],[.458,[16,52,8]],[.542,[23,60,12]],[.625,[33,70,18]],[.708,[51,83,28]],[.792,[80,102,38]],[.875,[123,136,71]],[1,[157,164,98]]],
 Canyon:[[0,[92,44,32]],[.18,[140,66,42]],[.36,[176,92,58]],[.54,[196,124,84]],[.72,[176,150,120]],[.88,[150,122,98]],[1,[214,196,176]]],
 Arid:[[0,[96,54,40]],[.2,[150,80,52]],[.44,[178,120,78]],[.68,[200,168,120]],[.86,[214,196,166]],[1,[232,222,200]]],
 Dune:[[0,[62,31,15]],[.125,[77,46,26]],[.208,[97,67,44]],[.292,[112,85,61]],[.375,[124,101,80]],[.458,[132,116,99]],[.542,[139,128,115]],[.625,[145,138,128]],[.708,[154,148,138]],[.792,[169,160,147]],[.875,[196,183,159]],[1,[219,203,170]]],
 Volcanic:[[0,[55,54,56]],[.125,[63,62,62]],[.208,[73,71,70]],[.292,[81,78,75]],[.375,[88,84,81]],[.458,[95,91,88]],[.542,[104,100,98]],[.625,[114,111,109]],[.708,[126,123,123]],[.792,[139,137,138]],[.875,[159,156,158]],[1,[175,170,172]]],
 Mars:[[0,[92,50,40]],[.3,[140,72,50]],[.58,[180,104,66]],[.8,[200,140,96]],[1,[214,182,152]]],
 Lunar:[[0,[40,40,40]],[.125,[47,47,47]],[.208,[56,56,56]],[.292,[64,64,64]],[.375,[70,70,70]],[.458,[77,77,77]],[.542,[83,83,83]],[.625,[90,90,90]],[.708,[99,99,99]],[.792,[111,111,111]],[.875,[141,141,141]],[1,[168,168,168]]],
 Arctic:[[0,[51,52,52]],[.125,[73,72,73]],[.208,[101,103,110]],[.292,[121,128,142]],[.375,[134,146,168]],[.458,[144,156,179]],[.542,[154,164,187]],[.625,[164,172,194]],[.708,[178,181,200]],[.792,[193,191,207]],[.875,[213,207,217]],[1,[227,220,225]]],
 Tundra:[[0,[19,26,30]],[.125,[33,33,32]],[.208,[60,43,37]],[.292,[89,54,43]],[.375,[113,65,51]],[.458,[130,76,62]],[.542,[141,91,77]],[.625,[145,110,99]],[.708,[151,135,128]],[.792,[167,167,162]],[.875,[196,204,200]],[1,[220,231,228]]],
 // Traced from Gaea SatMap-editor screenshots (per-column median of the gradient bar). Dusk = the selected in-range window.
 Estuary:[[0,[94,82,52]],[.077,[109,104,76]],[.154,[142,138,119]],[.231,[114,124,114]],[.308,[99,116,113]],[.385,[85,107,111]],[.462,[65,100,109]],[.538,[62,96,108]],[.615,[60,97,110]],[.692,[59,95,110]],[.769,[59,97,112]],[.846,[60,98,113]],[.923,[58,99,115]],[1,[61,98,113]]],
 Dusk:[[0,[128,119,125]],[.077,[190,179,190]],[.154,[185,173,186]],[.231,[157,145,145]],[.308,[181,165,164]],[.385,[232,207,193]],[.462,[133,102,99]],[.538,[119,88,81]],[.615,[145,96,85]],[.692,[157,87,64]],[.769,[160,94,68]],[.846,[179,99,65]],[.923,[179,104,75]],[1,[181,114,82]]],
 // Traced from a Gaea SatMap-library screenshot (13 stacked gradient strips; per-column median of each strip). Names are descriptive.
 Steel:[[0,[42,50,58]],[0.091,[85,107,128]],[0.182,[107,131,153]],[0.273,[96,119,139]],[0.364,[72,85,96]],[0.455,[130,139,149]],[0.545,[157,156,160]],[0.636,[155,137,127]],[0.727,[113,101,99]],[0.818,[142,108,88]],[0.909,[190,138,104]],[1,[250,253,251]]],
 Moss:[[0,[163,145,83]],[0.091,[137,123,79]],[0.182,[117,116,95]],[0.273,[121,130,129]],[0.364,[96,106,107]],[0.455,[117,127,129]],[0.545,[118,116,95]],[0.636,[106,101,77]],[0.727,[100,95,75]],[0.818,[90,88,75]],[0.909,[75,81,79]],[1,[79,94,102]]],
 Pewter:[[0,[42,41,42]],[0.091,[170,168,169]],[0.182,[126,125,126]],[0.273,[163,163,163]],[0.364,[130,137,138]],[0.455,[106,119,135]],[0.545,[106,120,133]],[0.636,[98,114,128]],[0.727,[113,138,159]],[0.818,[134,164,189]],[0.909,[130,147,165]],[1,[93,100,111]]],
 Copper:[[0,[152,142,140]],[0.091,[123,114,110]],[0.182,[106,96,94]],[0.273,[84,73,71]],[0.364,[74,65,64]],[0.455,[66,55,54]],[0.545,[64,53,50]],[0.636,[120,81,63]],[0.727,[142,95,77]],[0.818,[102,69,59]],[0.909,[96,68,58]],[1,[120,86,74]]],
 Chrome:[[0,[103,117,142]],[0.091,[92,109,133]],[0.182,[102,102,110]],[0.273,[90,81,82]],[0.364,[88,74,73]],[0.455,[88,79,74]],[0.545,[120,121,123]],[0.636,[182,183,185]],[0.727,[165,165,165]],[0.818,[128,118,113]],[0.909,[61,54,51]],[1,[90,65,58]]],
 Ash:[[0,[93,90,104]],[0.091,[77,77,87]],[0.182,[66,69,84]],[0.273,[63,65,77]],[0.364,[85,80,87]],[0.455,[104,90,94]],[0.545,[69,67,72]],[0.636,[88,79,80]],[0.727,[114,96,96]],[0.818,[116,93,74]],[0.909,[46,41,39]],[1,[82,71,67]]],
 Terracotta:[[0,[139,89,59]],[0.091,[140,90,57]],[0.182,[134,84,52]],[0.273,[131,86,60]],[0.364,[85,69,57]],[0.455,[94,81,66]],[0.545,[100,84,68]],[0.636,[123,92,70]],[0.727,[144,96,64]],[0.818,[180,106,67]],[0.909,[185,107,68]],[1,[174,115,84]]],
 Savanna:[[0,[66,67,55]],[0.091,[72,73,65]],[0.182,[83,81,69]],[0.273,[141,132,112]],[0.364,[153,149,135]],[0.455,[181,174,157]],[0.545,[129,126,111]],[0.636,[67,68,60]],[0.727,[76,74,64]],[0.818,[82,82,74]],[0.909,[182,171,155]],[1,[208,202,192]]],
 Frost:[[0,[93,117,155]],[0.091,[71,82,99]],[0.182,[61,74,90]],[0.273,[74,82,101]],[0.364,[123,138,166]],[0.455,[171,180,194]],[0.545,[193,196,204]],[0.636,[211,211,217]],[0.727,[226,216,208]],[0.818,[164,161,166]],[0.909,[125,128,141]],[1,[253,245,235]]],
 Fjord:[[0,[115,119,130]],[0.091,[109,115,127]],[0.182,[98,102,116]],[0.273,[62,61,66]],[0.364,[70,66,64]],[0.455,[85,79,67]],[0.545,[99,92,74]],[0.636,[103,97,77]],[0.727,[96,90,74]],[0.818,[101,97,83]],[0.909,[92,92,84]],[1,[90,88,89]]],
 Amber:[[0,[52,37,30]],[0.091,[146,116,49]],[0.182,[131,109,60]],[0.273,[65,49,34]],[0.364,[108,84,44]],[0.455,[101,82,40]],[0.545,[92,74,39]],[0.636,[97,78,39]],[0.727,[90,75,41]],[0.818,[102,86,43]],[0.909,[53,38,33]],[1,[57,41,33]]],
 Brass:[[0,[88,73,40]],[0.091,[98,80,42]],[0.182,[113,93,47]],[0.273,[120,97,47]],[0.364,[73,54,35]],[0.455,[73,57,37]],[0.545,[161,138,68]],[0.636,[131,113,54]],[0.727,[135,116,52]],[0.818,[113,94,47]],[0.909,[162,142,59]],[1,[87,72,41]]],
 Harvest:[[0,[64,55,46]],[0.091,[154,93,56]],[0.182,[176,123,94]],[0.273,[108,95,85]],[0.364,[141,133,122]],[0.455,[158,155,142]],[0.545,[99,102,77]],[0.636,[77,72,53]],[0.727,[73,67,62]],[0.818,[60,59,54]],[0.909,[67,55,53]],[1,[68,57,48]]]
};
let satName="Temperate";
let satUniform={lo:0,hi:1,shift:0,reverse:0};   // SatMap-node Range/Shift/Reverse applied to the driver in the terrain shader
let satComposite=0;                             // 1 when a SatMap layer stack is compositing per-vertex colour (else global LUT)
function satDrawerOpen(){const d=document.getElementById("satgen");return !!(d&&d.classList.contains("open"));}
let sun={az:0.55,el:0.85};                     // sun direction (radians); drives shading + cast shadows
let renderLook={exposure:-0.15,haze:0.28};     // scene-linear look development; exposure is in stops
let waterLook={style:"realistic",bandSteps:5,pattern:"wind",strength:.55,scale:1,speed:1,refraction:.55,waveDisplacement:1,amplitudeM:12,seaState:.55,bodyKind:"ocean"};
// waveDisplacement is SEPARATE from `strength` on purpose. `strength` drives the legacy ripple
// SHADING (uRipple), so wiring the geometric displacement to it too made the two impossible to
// tell apart: a gate that varied `strength` and saw 99% of pixels change was reading the ripple,
// not the mesh. One control, two effects, and no way to attribute a difference to either. // global renderer, independent of Water nodes
function sunDir(){const ce=Math.cos(sun.el);return[ce*Math.cos(sun.az),Math.sin(sun.el),ce*Math.sin(sun.az)];}
// A real, public-domain USGS/SRTM heightmap (Colorado Plateau, 128²) embedded so a real-world area
// is one click — an in-browser fetch of the AWS SRTM bucket is impossible (the bucket sends no CORS
// headers, and the reference-impl heightfield_io.py is the tool that pulls arbitrary real tiles).
const REAL_DEM_SAMPLE="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAAAAADmVT4XAAAkNklEQVR42lW7yZIsSa4deA4AVTMfI+JOmVkDH1ukRZrbXlCEO677Z/ivXJHd/V51VVZlZeXNe29MPpipKoBeeGSRdF/4xsVUDYACBwdH+V8ejh+eT+PuE2QKkAQJACQhRMJ/+dfHyzV9XEdalq4lRbXMm4eHu3/ZgQBypAhAkiMBIYUkSQFAEYKkMAFyRJEMp9EtpVCit19eX9SmGgNvH+J/fDL5UPR42FtlDl+F3UGriXbhoAgpFKZHJpAiZCYiM5mAmuntaR4BkCw6aFYkUKCAWKyvwZ1tNacYRoL/8w4yE9Dynv1Cil8ym1hl9KjdOS3PZSugAAkkgiSTyFAh8mYIDBKgMkORIpoDKklPVR+09Wp1c5iOoGok/xcjZCZwGdO7O/v2/OK6TDGC0aVCBNn+bHc7s+9mkADBBAhJIuGqFMmuCFQCGW5KAW6vKAJN0DKszXV3PN4bCKi7MIkE33aAwHbu8f38h//WPEcOR0gyMYRrYHqdNkfu7wnit10IiER4kgRCVZAZFHhYCEKpSKQIASZN7Xjc3+2BJKDJ/B82SDAFKfZdQFv6yOFEJkeAY5bsi20WRF8/KTOTTAApAkACINJEFO6mymQGnNBbbCRAJmBjnPYRAWESJCT/GQNEEgnARvYWnj17gjKYUqr6K0Qlnkas49+R6YAghUhQGAFhRIiDBbf3BZOZSUN0iAgBsXGNf/xhPsqb0Qkikf9LJFKVaKP1dAfF55ot0TtLKUvvaMf91/egJRIIIZGuwoTcjA2/HckgRZhQJBmMhAgsUmaRtxD65ybeXPrmGBc0D4y1USo922TeUDV7l8TLBs/jNH8nb5uPIOkkDUIAkgkMRQjzZh2+eRhEWrJ8+jitWhBvJxa8fQkgmRAkBUhSk9mrqco8An2IqkSkXX/cfpiaUSUBAZmKRA4GSAZJQcZtXfL2K3l7ZcuMz0Ndth8pJJK/rQ8gAZBI4fivax+gBnOYiFg1rpLUwhFLZC1FVUhPIRWg+C2eb1nwllNAQQKBgIoEKJnd6NfxVHcfPs4c8tvCv61+y0qB/PN16d4dQSKuqmpZymaozUsZOVpnvGyKyjCOFBVCI2+2FkoCkQLPABQSpkgXIkc2Sy7YbN4pAM2EIhNg3tz1Wyz++vfLdWmQEv4WKhww39cSwu4O/+mJ025/2EqOiex6O1UgSGY4IZkMCoYEAxAm6W1J89Ry/PR+y1BJMCUzBBmQ3xwB+fNfr0vz3sMzpQYBFdVayt0P3xz9Mvzq16qv95f9xyEXoSZ9EILMoRohzJCSt4QsGsGQlLG2Efofgirb67oHICQT6wW8ugnk7f2//PX1fFmvzWPonOlC0VJms+Pu3bv744cuWUy3u30xf1n3RmMgkioJJyJVYbyFv2gIRUDhuCx9mMnwBde733/5AUgicvSX+7aPW20BiGzrdWnriPAiZdMjVOhp9WiTfLRx+ZfTlzHdb7i7fr9xJdTVBhiOQYCkiBAjkkTAMihC9KV1NzXJjDUvf/kBvwcBXr/6ps6CvBVwAKgkWDhdR8jaOSmsTFY2+9+NMuu8X37Vix2/s3QNqiRLwAQeQaEyE+kqCkUKgnLzcu/DacXAoLc4Lts2EUuL8/7DW0p5y03ttSVg1s0GGTaySDWddgd+fGjVdPPH5Vv/HgLEEFczalLIIZZvx14QN4TDJG6+NckwNQtkl2B7uVureH89BZY93hIhCebPP63r2lcbo+ha6ekZfbO3afdwzOo5iuymJjGkOpIIB265gLeMTEXcUszbI4mkdx8wiJX0LjKu+JEKf1we34/2Fn0JgnyJy6W1kS+ZCSR0YqS66TTfTWMURodRqeSwZCYGRZIBIUAnBQkhhIlMghCR7K1n9noxUeueCUwvksvfl3fcH1z5W0bO8+e/9BjRR440RaiqKmJX5b1tqNGrACk2VFKSigjRjIwbOHKSiFQC6UhJJTMT3kak4xlWYzAcA8/L1zwNvMjmqL+hUuD51z+dL9fmIkMU4KS+1tiarduhCYq9YZyMVEkFhIQiM2/lnWSkIEAELZGEMBkx3OEU6wHJ8Bh9LBxuJ/9wane/1ePx9Lfzc1vWyNyeHVY8TdO86PHd5gEh0Jut0oLQfPMyeAMSECKdDCYjyaRkJoDLeu2ehBZLA4OBoRIJeNqfylyFxRDA2pujrc0ZqRgmGqBKUYvzeJ0k5J+16wY5MkNTIg1EgC5kCgEGBAwFicx2vbYARaA2tYBAPLpmQBn99KcPXvcQUPj45/Pa0iKvCoj1CEVm9IrpnpvyW9W+SmGGMNFFfdjguGEukXQJoYMCkkgSce2X7kVEZXQTRVBTMpcypsAa80kftlqTov3io619hMMsNeEAkFFSpJZpFXOjsD2H7V+njTTfjGaRFQ7JpMYAE4kQIPOGhvpo1+FCI82aDacYI8JjxbL1WjCWb93KcVP1aTA9M4bYMBNQhVA1ymKnw7fvvBnI/twX62fW/TI1mXJWJyhMH7dwdlHwhskz19aGd1ULqRu9GMmqNbquNla/bPtQvfyoOf1w/0McHmHFIuAciUFRQkAwtLR1kwURTG+XX3E8vKMUbPW2dslIs0gSCCKF6RDocmk+eN5XlZyKVTd63Vj1y2XqOS25Fs31arR8emiGIg61ZNrASEVSVJHI7CHRZjH1y8/jp/4v23c7TxsBVEgSgxEmmSTJRKaQom259Oi+F886zzbJbF6n7f3hc8ja4TLITMcwJVD90lrvvUckpZkgU+DUiOjL+cfDMv9OHh8vv177MY574WDtiSGuQk0JCIIJQJMCUaKt7utWspdwmYrI1rTuf7c9lL9/dWBavIuLSkpk5Pqy/NvVgfARPp9QgByKDMmeyOX68rvBL49Li2pTxaCllgRTCEG8YSp5Q9hCchmOXuBVrUgsYZJmm++Px3L+8Kx1uszlMpgAYyxlff3L02sfzdOzDa+tAkiXSHhErrUtHbaM5pPUat+2pUgIwADl1oT4LRXeigp9Pfe2YhJFJqrmxSFW76Y9dXPaDa4yXJd9EUpm5Fd5PV1Xj3CylYrNuUJSMsxDbCk+fFGOAGo+7jvKnONcsLEMkaTkbeHfMD14fu3uTzb2EuyjMeGW9v1+VsS75TJyEEiJBlWDED+vbb2ERAQ2Ldg3CIeFuc+4Cktcbk2OrbH+v7s7f6lTqc0jJSQhGnnLxePGVvh1/dr4vsQarTBLJsti9uEeDpF3l/rT6C6SKSVoRbK15i4LB0l6CFMtAoxmCwpi9FSISKVa2d7/cXpYp0rGqMxgIoVBggJAAOkRrR5Vy9yPt6DUrhsbi5rA5N2pljIG6VxVchm+RA8klyRE6/UgJC2Dapk5Mh0GMVGqlnn78XiUkqLaxCTEJUgIUgQMIeHNfRwToiJZcxbjdNKD5XJQsVC9DI8EGc4MsVjXYIvwbopFxyaDWSlElaWQESIAxVTqYft+k7VXipAlKOoCCdycTwpT4trS6uN859RJsbGqyDKr3ZERPsnT36/L6swUF6FnghHpsBg+72/Mg1IIitpuDCM01ZCiOTDN+fzOLTvUVEgOZgKSoCSE6Nd1jYAfJq3zZFGsaF73k9iUGUaiSICjiwyFwEcHIzMEx9bP+xBFmpJanBbrvGlMWN1C00zXz4f3dxEdYhDxW9dNApLpROZ6XfuISzOy7raTRChzaEUaJZgZvmZmEGsQ8CASEbcWcbLTdSM3lJghxSbpPtcVzuzzwTmVjR3mqg5JesgbShImkwQ5rn0d6/Wpl20l4L2qgMIC0KCQDE9QmJHe53RKMiJChIlQSpKUW48bzCwUt92I0KJ6J/KhbOSjqFHWikhvpkm4EEIi1/XaPc7feK8V0V/9GO6KFCZhKir9Rh2kqIs7wUTGo2WQZeaI0Mt9UoQiKsxW57DDioR4Lb+fVB8mQc+inFIte0YIaQkgW/ex9v40rnF4MEnDJJda1AgmApajUERQEQiA0zACKTIv3EnrHZCN8lwtBBRRFbCUTSnhLqW0z98Hzqf5bkI0VUGyOEJEhJk5XoZ7vn5bY9p9FNt31bS9pggyUwJmAM25rOvaMyI8Q4lR5bB5Pd/tJNBrUm24hmSKqonqvPnD49JjHObjneweRuSqoRMyEaRCIgjkGJe2Ij5fej28q1XrtFfpVQxYQTBETBEp/afXP12WdfRk22kG3SVpnqRSQ4WkpsM4RK3O0913hzlf11Y/fqqn5fPDbqS7XNUk5K3/Y5zczj7657Xn7nBHm+t2KqlF0Ig0JgE3CtOfLn86Xfpo7qsFgomgZ8AnTZACUjUltVSRaLK7mx+mb8fokgfWa1k25lJGigdkgALVGHI5e4zPr307PxxEJGqtBBAxBEpNEDAOwvUfY/XRgZhObXDbhu1fHJsJt4QqIFNgXNOCdVN2D/tphnd1Vd+W6ze7E2o6EF3FJPOSl2g9np/XUeffFZtRrS+cmKFMUcSNSbY1mC/TD8sawwaNOyCfEfFN5+0FIM0FpBBkoWZY5Dqfr/t5CgmTIYX80FcKCR24Rbd6f80e4+dlwXx8LyybSQtSUxxrYjg1k0Lal6fnPu4+mLGEa8KAdveEulfHQYOECgkaKVlHMqLX6y+HiGkKYwHFAOvRRcRqZhKJdHBZr8/n1bYfHsgM15kk4JcsvhGkpAgJ/eO3l/N6eW6re9ywS9KkySxyGzuoVaEVM6tSC4pagFxm36BAyBFKUQTDmOmiSoT0dYkvX5brtN9/0DJZCFSEce5QMRVTURKAPfdIlmu21t0TmQz11zzqjVJUFndRKZPPMoCSVVNHu/5sq/ahogVOogIxCmApwkR6b/84Lb3uP+7IOhUftZL9BTmz2lvnmcm0FwTYhWN4RGQ6crnmrtxoUwFTQNFN1SIuw7EJiLCvX3YW1RipN7IeIQ7zKiSR4/rtfF3n/eEoOnFv0jT03CJqKb+x0Q6F28UC5oRnRGZ6nHrwsFG57VIMmmqVdjfLGhKxyTBRvSqqSXigWyEJlOGF7FQKr9dYhgftPW27tVJZkutpqfNeoQjXDBpz0JqnjJoBByIQo9WdEr3cAp9ZVIUpJu/vGhafunDrdXtG+3qvrVZBNrMgaUiVkoKEeGvDM2I1ILUI/Mx2ESmmhPeCVpkjJc1dXTsjE4gAztyICDQ0ISSVqmYThKn/+xd2qg3uZLPO4U1rrLPSRtNUUoe7iJCoh7VI5hiPE859PW4peenjcKjiQEZEriBN1ZomdQCZBBDfsJnyxmMBSTAAwsph3u1LvA8LNRGXPhtG0Sw9XbRkCAEpqQ4A6Bf3ERmtjaLTcQZYYmSu7FepPq+uChUVWK5GV0EAQn7DYeNv4ffPPYAh5d37w50xIAxTcQlKuopLE6qqeYoAg1O4SCyRPTyEtHqYqpDYcqzn64O8bvtukZomyHTov5cxkpE3Pr9HWxfYLfPeGDUCZhHXNsVUqEJKmBdTUaaKmlqGU29EiVKEuJ7PPy3LSFPZzCVZSeDann8JU33WFDWFKgnTP6qJLq33rpJZN8G4hGm+ze0AIsMz2U8X9q2J6HqS204oFBERN4u4cQAkKfmP008vi3eqTvMct6lpLq8/nxqfM2W3My+M2zb+vcAwTYWIgv68REE0ExDoCIToACQQ3taznW3yPF3dmTm8IzNVJRgm6ZAbD5OX6z9Oa2shIkUOETm65vL07WmJl8G51K2E3EYWF6udNKT0Mbufp/l6UcjpVEN3JXpqDgWy0HvPGLtlfv8afinvJU2FCMvMGweOcCGzPZ+1X9Y1PKlzvZNqnKri68vPF8d29+HeJgtNqPLxRJOSifSuvGZOW9zdf46DYq9uwpoiQ0emIIns7fq0Wb7K/XFvxQsDGp4JJk2Qgsz28+iP53713lJEoDvbbclJfnn5+zIStp3Kkbdpzeup//Jk06APd+EBAhD52Td1hrK+DbhqbgbWGjG8j1bWZ93vlqyzhhjSIkGBM5TE+XN//tJi9Lh6ipA0TnOtgI/LJQeif+U6Dqp6Pl/7L2dfjdpB6tuIMPKb7+YKpQjCUDKBqC5kAJHa+qaU3afdEqZgUhgUB0WQefn759exLh4enVq0zNvvjVYofPUXrJ4Nzvoyjcty+eaxrNdh8Iwbjxx0ytieL7a59dMWmhRxUQFFWVRhJmUzpGSPqj6opjdWG8xfX3+8XL2FR3hMhaJS6gN6hfSvp7GOAR8pm+3Xy9d1faneRzYrOjoSPTLzqWu5u9z8jVtyF2JKlRSBFNMiKPP2sIuski1VIt/ox+VXnH88tT462AMmU9Gyu5f4kCnj8/Wn88DQ1Zb1+vNzjNbH2jNHWqbZOoKZpxex1i5y2DKTFORNT0HFJowosTHdZkzE5BipqsZEkhqJn79eTpd+HXDHoAmhm/1xO099Ipb24zL6yG6rvPz36Bh90DmQw3Ik3eGZIbLLMN8pSYaL3KqRGotVCcVmW8rer8eP66glMklKihBEH7/6a+tjIDIgKdFMHu43dp3A9vjUrysjB7Tl2hGe3ZqGpxs4PDJBRJRaACjeJtu3nhwqZbqrCpvmPTezvdx71jFbDHjRYIL5pwG+tN5HRABmUzXUrmrTfuL159PP55GrI7zFikwkYs3RqJNlAoGMPPWsgLj9pj9hAgnSleHQ76tspt0ew7Cj9BSxYasQSfy0/nVcRl9yeFKlTlJ2LJvZ0T00pbfRPKMHR/AGiNJH39UQGz3c/cKxDrYmd4WkkJoiiURoCiLbdTpP9fcNGyt361JpARMJAoMZ/etyWdbhDoepWt1O+91dPZQoGvL05fPZ0yOJzIxMqOtlTMdShDZGH8Xun3Pbrj3y+kdQpCQ0U1MUmS09Blopkx+7fJQiCzuNQZUUhmj48LZ4j2yqZrNo2B8PGyksahKG1ZcRI+Fj8gxojJf5YCJJsWpgcbmPyDhd100myMxIwlFsJenwphTJ9AiHQIxICKAOMvyzZkKbe7rIvJlY59nq3qQK0J27UjxaBOm9MDIuclQAHik2WlRKIjNOy1IPsm6yL0P3uU7ZmpbiJCBap/nTw96XXUJdhUglFNTxb/p/n3t6ZiBKUcXm+HCoyz2yQddsCehtho3IlZd+zE0IM5OSlixSe3hCfClHW1/WsrOqoQa7TTxkg5RaNvfzwwHRb8Cb+SYv4Jn/32VZ+/DMNoviWnR9/FX37Xh4WXcvz8desrWggN35Wg9qW49FoUqYsSZHeFIHU55s926CgUIWvqUidS21luN3DwehtgGIvGE1ycDlpXvr3bsnBY7ii5co/fT7Z/154YXO1qP3JM7z66EKE2qTcNaetDmdMcTBl4U47qrAUoVC2A0TEYAmtu/nd4ok3CSHym/zovX6dO6aGcAoyQAFY4l9r50DC8MRnkhGx/QSkTegSYpPdYht+0hqi0w4tve9V6QAQqiIBmhFZxQ1DoYlOY3bJCzfxruvy4jomUiUZRvwkCE+XaSvOSAD6dYlEC0XGe+LvK1PZMhWbSPSsC1LjPnM8dW5295m1wwIikJknk3mWpiy0sAS0Miw278wSu8uyCSzRxdxB+oI6bWVlQi4haRTPNpt3zewqUabdjYhcjRk+sXjlMDr72NWDLIwAC+Yps3xYc+5fgpjuqolbq3rrRG/mEbPdMTIngaEmCOHDL0MybDeRRiJeK13jtt4M4qoGW1jd09jirUR5g8c0i7+qqPUCkGmU0VGK6OU6eGwigjSQYJxm0Eisb+g5pWtJgXP2401mTIjUqQhnDmyl0y4fuNB3yQByqAzJbqJZCjI0b5H8LJ4ik3VIAglkcMK1m8+34/Xj8VThJFUSrpmJJivz97W7ls0BB8ec4qSkQEMurrQJeCefOngo5jfo2SkSISjX69Gnd1Lik6RGXnmcVNNUW5jFyfHVXR6GWP9XRdjJo03aWLeBJhdpqWXEosDjt1XfsomxnCqBy9NWqnn3dpl3gt1qKyDKgiMkOZix+hmo3CEOOOcUsqUbiEJdDXmcAuCs3HKUAFIvelwEkDgO15dWls0RtQo8eXxXZor8Tj12L8031w0m01lTwXmwJbqi2CbmV3M3l03fbA3ZI7HFwenfvXy8XGv0ovQE5PUMpXYzyKekDcSPElJJLGbPoxL9AhKCWbl8ngPjPXLSsUp7PAuv+7243IQGgM1IdCcsBZbitBqpoln+Gjl4/xz+vNcN0c8NFw3XGelpSdYN7W42E1kdpuC3U4h+bDWKYPskenUD09fy53jc75zef/SpyP1w1Ot90xxrZEioJLcDPUB2ureIhxiGiwEc1csVCZMyImslvQYrf/tcjre33q2N7RERgKo5ePj6J5gZkScz+qP8awPD0DcR1JYt1UogGpopkmGQUWlOFz/r96HewLQSUSv3i8Pqm+yXkBwe7K0drk8ra+xIwL8TWFBEC/nf+srRkSkZzyfr3G6XMv7d5VCMUkptGFCpVCKiFSwmKjIlEY7nKdlFQlo9MQev/bxpkUJhir8pnl45WZd59Ndjg86hCJym4sS4/GXvqxXH4gAMM7yhwxu5/SSSmPAgnAVIYlQiqhXVx2sYNgnvKAkJB2MuJ4HCvIm96TAoRkhWK2M2tadzBXDRP4ptrw8X9u5XQGPxgjHY99uVYWoN2khbeqAONpEERoJaimBMg+ZMOyvP3Z4856Aez+/5PweSE8NIkUkXDM6oxWXKhMo+mZ6Enj6/OWp9XPvjqG+gj8v9TsBkvpmIHBQkVQdk0JAKUTZRNWMXLXY/7O05gFKIv30knIs5m50yG366EvMRQSsE7reFwZW36omgL+//PX1ymW04cHMsvz6hDlDQb1hCZAJSZBUiaEABSzzvlTtvtRIe2oNgUQAUEoCayuT4KoVimB7/jQnhVY0tseD+I/Oy2r3sR21X/7yulzmNnrEim4erdf9ThFwvXVsfNPTvEU0CVBUpx/m0vIfPWjXduMnEUDu/XP/Ut8VW/qshlR8nt7nakYlICLyr71r0vk3UTf0dl3jRTzDu7jL6ZS7e0nmm4zq5qj47diKglJFw6//+Pjp/ak8OW0dHgTcEeGXsrv0aPPLslUJLT5OH03HUBlF4AvP155hSIioT+EuzWNl+DogeXlatw+FQchNwvWbMhTJJJAoolWkaq7nZXPcVx22MByJiEj/9eJQ+OXSu9Xf7ZrF3zaJQDYX5AQMLm5NFYM6XwrDkjliMMhTll9f5X7f11XrMSX4VrQIIigJMqVua6VO2+2Ur3PdHWitpiedjvY3j8xMnINc8vN7Pl35qbdJFMnEQAjGuG68l0UlvJOeSMKH8vq5SRv6/A3bbvct533x8EooOTQR0ARSOH0wPx7n7XTd8nxR8wYOd3l9bZyn0wogp8pr4zVDjy9jVjEhiPCAdc8lcwxg9VBJwOHK9vfXtkKKRHl4+a6ujOdFJts1sSFgRoilUhIyyTud77a9aFZms7X0vJ7dC+4nYX1Zh9R3qr/EUsukudF5mAuEIZFwzx43ORyGhPpNSw1snqNO1eeDzZut3dUevac/0qKWUANN6WIc7dv6qscvD9+hImumYbwKH05112MLbI4nN+O4KnX6ZFQrnCgqScmIYCAGvc0DaFJDASQyYypN7Hclp241lFHCNiA0Xcg1JmY3wQCy9nNddr3fbY+GpB19tujtPQ2pTLtn9vPjmgnhVo0Kv1GKyIyRKcuMtatIDmdxDGUExogUSUoYKJEUAZmpEEI1I3KDkPQYzjLFWM4v96fy0aj/wYvFZS5BnVKFhXL6dumddbsFIKlV9JZCEhhNXhX+xM1YHydhRO9r5mjPy2mz21GFIkomSqooKElVEWPpGdRMJGA+ItplsO9U/w+V0UopagKBlGS2axtVOV4ue0kIhG8UbLrwqzPXX646/q77bIrmnnH9er3slDIRBFxEACZECSHEREy5oTuETEQiPRCFs+n/idFNC6vF7fYHbCCVsbSmS7VKAnqToiHHkC+v2l79cmqxnF9HiX+cL8vzOpgxrsuONw3hWzWlkCK4VWIWNQIy35gPlPlhd2zGLvtFjUxBAkmJh8OuX5doa9dTdRAZQmZkGmXJ0zBeRII9uT5nd+ViRSJ7j7/9joFtBoNv+A1J3hRVCFVrQorS5jl6n0K2liyoUjlCmOKJDOamLd2z7+xoFHEZCmiQPkIjL9pnRVwm8Yslp7PpdFeGL8s6/iw/lNUFs70pCHlrX0iFqOnkZrNj3h0Bf/4IWE5ltWlsl7Xc7qUgWv32uKzEBr6o1xomcbt6I0QvesbONpvVQekjyt1DnGSzQV6+6bjgL9N2OmxUIG8q3n9ewEFyg2UupULL/kMZL7ouNg2zXutgDWbqSM/812sfxehn5Kno8YHZ0zCg1OR8nlRsv5PsLOvjZXoPXlRQYOrreaxePs0CSry9/O0AEWS2nOeyn6VbBr8b07UfbO4GU+vRY2SORFx+vZxna2nL9jLOmI/dUnokwt1clQoCrhs0nb3vWcVrCgsq3F9/WdPWWW/rZ76JiRDUTEPofv8xryoW63SQF7e7XtgDkeZJiGfB+XrYxNKuO8Fpr0UYdE2mo83DqH6pwx/Cd7Xqde59YrUSiqQwTMzWyceUkp4Mu105GklQb8lse9d9nuMkO7Rm73PSn8+xhEICmT1+avvth+W1ptbSX1F+2dZ9UYePXH6K+dra1qouxfpOcVx1k1I1NwNECDz9eXzY83VLZ1i6t8KIVYUGqKnk6+Y77PLK3ue92//m/+16iaFrh2cHLj+2w8Ne5rkH5pfT/rS2/imje45Vvq4vR3z+xPIJLk1CRfYxSRTSlQmkbH94vrwu+G7zstUGTBY2QmHVQlRvbQb6g8bWo8c0mf60Lqunx2Ak4sen+bu6NdeNvlxPkdyfdrFumP31uiLbAcunMVnM4XNeY9JtG7VAQGgkZbbN/Pxl2j5fyitYpLta2r6IpJoW06oKzArJAZkk7fFESl89O5H48fxR7pVSEr09X0emoxjR/PHaLvX5UymbDD0oN0Id4jaVVWCpSBEHYcEJ1IeyffGP09qqDdYqRilzNYqJIm7iZIhC7dfzuQeYA61+ftl8v2cWgTCf10u7bqzsbHfI9euC1zuZtd4Tpc2TWEVU0aRMUNqNdkRytFjleBzSdyUvc1Xh8LWiKkd2KyDUShCEUZN2vo41Ih14avJ+3msgBdTen0erKqq7rcfriLi3WmYhim41w0IsCUmaOTE1MFOyEzrzujkMSLJkSnIOjczxdueLmKsgpUbP1LS1de8cuax2mHyO24ROQE7BdsIdXhZpkb/+oJsjIWWk2dQzMSYhqGlhVVGSjgyJyfLd8x41lC4QAmnKSFWoqlrmOuiEUOB9shY+enqs9oAsKGQwhc6HWKVGfTrUNdt1lae9vaJs12oQVIOGK6kaNEFSXRGZFhnZt/qqRfXWjaiqiCZDBCS1pncTIQvg3aZO2hC5c0qqWnZCMhFXO7SxkW2z8Xq4I35da/vyab130gMbzYJIQiTVZIqUVA3r4uEjLnMt4kIqTVRFKKCAKXWa3r2vAndSxYYN0JLM8y5RqHPLocik7tordxhrNH3QKdf2zr+uY7ncoXWVqCUUQkRRKUpFAOJLimT57gVrZRpv62olRXSwTiFtzGXnHoVEQIpBJmbPyyQSVHNKBTAi+ZJ3uy/92LCZHjaPI77uP/2Y6Kc2tGynPtU6Ccn0JCYVduWFpG1wGfNWrAAUBSNTJ5o6qHOdC3w1LarBSBdrqwcwdhnFgQwFEik+ftWP+3G/DJX6cZ+H5d/l5We4ny8xdvOmyFRUQGQXI7rWzbUtKRIZm0toKVVvkEyUKbmbNSFlLrvp7veqmkihAmlANHfj3MWaQIUJj5RJdndQbmKZN3XKr339ho/5c+3frTuoxUjKpZRkIgbrVEbWWABSHSxbBhSZZFCBWvYfWu53lTrdFzJvAk0h9T9nYEyoaqmGaRKix3Bvxz0rpumubqc5X0/LqX0POezn83UneT5fo/f6+ITJrKoY17X3yBHpiDUpl27Cm6hdKCka4NpmSR+z4C1mQNplQETMyqgigTBCqb1NyoRCYu8WVoTT67KRKUs9Z1whclETfX8oIBxDWwiSNiLHWtf+OL9L/03WmaP6aTFFedZS5uX7crvwRgT0P7lnUdVJikxSN3MlFV4xCShmSsLCR2P5+V71vtrEoT6uCp3205xGjsgxQhDRli6YYhzm6zxRbkJAQsXXvl6XWC/efBvHm5QPY4T+x0AxKaYz61S25Y8h8KyULQglEAGyxOv6jz8Ipm3d7wI0sEx37+ZZLLX5NRMKZIQpRBebt37aGyNxu+3tI6KPaN176H4uKQQy2+ui/8mqllrKvOFhN+3efZfwYnNmZoDIHOHM7Es/nv66brkt0wHTJnDV9ZqgxFhfJwUEYFKK+Gob5dzOkUKIIhLhEZ4ZDJaad5xMxjpwPbf/Hwb388QFLG0hAAAAAElFTkSuQmCC";

/* ------------------------------------------------------------ Field --- */
// A heightfield is a Float32Array of fieldW()*fieldH(), values nominally in [0,1].
//
// ---- FIELD DIMENSIONS: why a hex field is TALLER than it is wide ------------------------------
// RES is the authoring resolution and it means the field's WIDTH in cells, not "the field is
// RES x RES". A square field is RES x RES and nothing below changes for it - fieldH() === RES, so
// every square expression is numerically identical and the 60/60 digest still holds.
//
// A hex field is RES x round(RES * 2/sqrt(3)). The reason is that the lattice's rows sit sqrt(3)/2
// apart, so a hex array with as many rows as columns covers a world only 0.866 as TALL as it is
// wide. Storing hex in a square array was the original retrofit, and it forced a choice between
// squashing the terrain into a short map or cropping it - the "squash or crop" dilemma that looked
// fundamental but was really just an artefact of reusing the square array shape. Give the field its
// own row count and the dilemma dissolves: a SQUARE WORLD IN METRES, covered by equilateral cells,
// with no squash and no crop.
//
//   RES = 512, terrainDef.scale = 5000 m
//   square : 512 x 512 cells, s = 9.766 m, world 5000 x 5000 m, cell area s^2        = 95.4 m^2
//   hex    : 512 x 591 cells, s = 9.766 m, world 5000 x 5000 m, cell area (v3/2)s^2  = 82.6 m^2
//
// The price is 15.5% more cells on hex, which is inherent to covering a square world at equal
// spacing (26 states it: "equal spacing => 15.47% more samples"), not an implementation artefact.
//
// The map's EDGE is genuinely ragged on hex and that is correct, not a defect to sand off: odd rows
// sit half a cell right, so the left and right boundaries are serrated by s/2. A hex heightfield
// does not have a straight edge. Do not "fix" it.
// MIGRATION GATE. Flipping the hex row count is the LAST step of the conversion, not the first:
// until every kernel reads fieldH() instead of assuming RES rows, a taller hex field would leave
// its bottom rows untouched. So this stays false while the call sites are converted, and every
// intermediate state remains shippable. Square is unaffected either way - fieldH() === RES there,
// so every square expression is numerically identical and the digest holds throughout.
const HEX_SQUARE_WORLD=true;
const HEX_ROWS_FOR=w=>Math.round(w*2/Math.sqrt(3));   // rows that make the world square
// Row count for a grid of a GIVEN width. Helpers that take n as a parameter (the canyon working
// grid, blurScalarField, climateSolarExposure, the wind projector) run on their own grid, not
// necessarily the full field, so they must derive rows from THEIR n rather than from RES.
const latticeRows=w=>(HEX_SQUARE_WORLD&&terrainDef.lattice==="hex")?HEX_ROWS_FOR(w):w;
export const fieldW=()=>RES;                                  // field WIDTH in cells - always RES
export const fieldH=()=>latticeRows(RES);                     // field HEIGHT in ROWS
export const fieldLen=()=>fieldW()*fieldH();

// RECOVER A FIELD'S WIDTH FROM ITS LENGTH, honestly, for the current lattice.
//
// A bare Float32Array carries no shape, so a node handed one has to work out how wide it is. The
// obvious `Math.round(Math.sqrt(N))` is exact on square and WRONG on hex, where the field is
// RES x round(RES*2/sqrt(3)) and the cell count is never a perfect square: at RES 512 that guess
// returns 550 against a real width of 512. Measured in d_windmodify, where it made the divergence
// sum and the mass-consistency projection read across row boundaries. Every sample stayed finite,
// which is why nothing caught it — the wind was simply wrong, quietly, on hex.
//
// fieldW() is NOT the answer either, and that mistake was made first: a node may legitimately be
// evaluated on a field that is not the working grid — atFeatureScale coarsens, and oracles pass
// fixtures of their own size. The width has to come from the field itself.
//
// Inverting rows(w) has no closed form on hex, so estimate and then VERIFY the factorisation
// exactly. If no width reproduces the length, this is not a field of this lattice's shape and the
// caller is told so by falling back to the working grid rather than being handed a plausible lie.
export function widthForLength(N){
  if(!(N>0))return 0;
  const hex=terrainDef.lattice==="hex";
  const est=Math.round(hex?Math.sqrt(N*Math.sqrt(3)/2):Math.sqrt(N));
  for(let d=0;d<=4;d++)for(const w of (d===0?[est]:[est-d,est+d])){
    if(w>1&&w*latticeRows(w)===N)return w;
  }
  return fieldW();
}
export function newField(v=0){const a=new Float32Array(fieldLen());if(v)a.fill(v);return a;}
function sampleBilinear(f,x,y){            // x,y in grid coords (= world position in cell units)
  const n=fieldW(),nh=fieldH();
  if(terrainDef.lattice==="hex"){
    // Odd-r storage (26): cell (c,r) sits at world ( c + 0.5*(r&1), r*sqrt(3)/2 ) in cell units,
    // and every caller means a WORLD position by (x,y) - warpField displaces by noise offsets in
    // cells, pickers convert from world. Square bilinear on that data reads i+n as "directly
    // below" when it is half a cell across and sqrt(3)/2 down, so it blends the wrong points:
    // this is what made the DEFAULT graph's terrain change on a lattice toggle far beyond the
    // expected seed-contract resample. Undo each row's OWN parity shift before interpolating
    // along it, then blend between rows - exact for a linear field, still four taps. (Using one
    // row's parity for both rows, the cheap shear correction, leaves up to half a cell of error
    // on alternating rows.)
    const r=clamp(y/HEX_ROW,0,nh-1.001),r0=r|0,fr=r-r0;
    const rowAt=rr=>{const cx=clamp(x-0.5*(rr&1),0,n-1.001),c0=cx|0,i=rr*n+c0;
      return lerp(f[i],f[i+1],cx-c0);};
    return lerp(rowAt(r0),rowAt(r0+1),fr);
  }
  x=clamp(x,0,n-1.001);y=clamp(y,0,nh-1.001);
  const x0=x|0,y0=y|0,fx=x-x0,fy=y-y0,i=y0*n+x0;
  const a=f[i],b=f[i+1],c=f[i+n],d=f[i+n+1];
  return lerp(lerp(a,b,fx),lerp(c,d,fx),fy);
}
export function fieldRange(f){let mn=1e9,mx=-1e9;for(let i=0;i<f.length;i++){const v=f[i];if(v<mn)mn=v;if(v>mx)mx=v;}return[mn,mx];}
export function normalize(f){const[mn,mx]=fieldRange(f);const d=mx-mn||1;const o=newField();for(let i=0;i<f.length;i++)o[i]=(f[i]-mn)/d;return o;}

/* --------------------------------------------------- hash & gradients -- */
// Exact 32-bit integer hash (Math.imul, not float multiply): the second multiply exceeds 2^53 as a
// double, so plain `*` would round. Being exact also makes it reproducible bit-for-bit in GLSL `uint`,
// which is what lets the GPU fast path generate the *same* noise as this CPU reference.
/* ---- COORDINATE-SPACE PLACEMENT — "place before you sample".
   A procedural generator is a function of position, so evaluating it at TRANSFORMED coordinates
   moves/rotates/scales the feature EXACTLY: same function, sampled somewhere else. Transforming the
   finished RASTER instead costs a bilinear resample, and bilinear is a low-pass filter. Measured here
   on fBm as mean |laplacian| (_verify_exact_transform.js): one non-integer move loses 24.7% of the
   fine detail, four chained moves 53.8%, a 2x magnify 27.2% — exact placement loses none of it, at
   any depth. Gaea's and World Machine's Transform are raster nodes; Houdini transforms the noise's
   input P, which is this.
   XF maps DESTINATION uv -> SOURCE uv as a 2x3 affine [a,b,c, d,e,f]; null means identity. Nested
   transforms COMPOSE into one matrix (xfMul), so N moves still cost exactly one evaluation. This is
   reference-impl/placement.py's `affine`/`compose`/`sample_coords` in normalised tile units. ---- */
export let XF=null;
// XF is swapped by the transform node during evaluation, and the transform node is now a plugin
// module - so it can no longer assign the binding directly. An imported binding is immutable in the
// importing module ("TypeError: Assignment to constant variable"), which is the same rule that
// governs the test bridge: a WRITTEN symbol cannot live outside the module that declares it unless
// its owner exports a setter. This is that setter.
export function setXF(v){ XF=v; }
const xfU=(u,v)=>XF?XF[0]*u+XF[1]*v+XF[2]:u;
const xfV=(u,v)=>XF?XF[3]*u+XF[4]*v+XF[5]:v;
export function worldSampleAt(x,y){
  const n=fieldW(),hex=terrainDef.lattice==="hex",hxs=hex?0.5:0;
  const u=(x+0.5+hxs*(y&1))/n,v=(y+0.5)/n*(hex?Math.sqrt(3)/2:1);
  return[xfU(u,v)*terrainDef.scale,xfV(u,v)*terrainDef.scale];
}
// The SAME inverse map transformField() uses, so exact and raster modes describe one placement.
export function xfFromParams({scale=1,aspect=1,angle=0,offX=0,offY=0,pivX=0.5,pivY=0.5}){
  const a=-angle*Math.PI/180,ca=Math.cos(a),sa=Math.sin(a);
  const sX=Math.max(0.05,scale),sY=Math.max(0.05,scale*aspect);
  // M = T(offset) . T(pivot) . R(yaw) . S(scale) . T(-pivot), inverted for sampling. Rotation and
  // scale happen about PIVOT, not about the tile centre \u2014 the difference between turning a ridge
  // in place and swinging it across the map.
  return [ca/sX,-sa/sX,(-ca*pivX+sa*pivY)/sX+pivX-offX,
          sa/sY, ca/sY,(-sa*pivX-ca*pivY)/sY+pivY-offY];
}
export function xfMul(inner,outer){        // result(u,v) = inner(outer(u,v)) — outer applied first
  if(!inner)return outer;if(!outer)return inner;
  const[a,b,c,d,e,f]=inner,[A,B,C,D,E,F]=outer;
  return [a*A+b*D,a*B+b*E,a*C+b*F+c,
          d*A+e*D,d*B+e*E,d*C+e*F+f];
}
function hash2(x,y,s){let h=(Math.imul(x,374761393)+Math.imul(y,668265263)+Math.imul(s,1442695041))|0;
  h=Math.imul(h^(h>>>13),1274126177);return((h^(h>>>16))>>>0)/4294967295;}
function vnoise(x,y,s){ // value noise, C1 smooth
  const x0=Math.floor(x),y0=Math.floor(y),fx=smooth(x-x0),fy=smooth(y-y0);
  const a=hash2(x0,y0,s),b=hash2(x0+1,y0,s),c=hash2(x0,y0+1,s),d=hash2(x0+1,y0+1,s);
  return lerp(lerp(a,b,fx),lerp(c,d,fx),fy);
}
export function gnoise(x,y,s){ // gradient (perlin-ish) noise in ~[-1,1] -> [0,1]
  const x0=Math.floor(x),y0=Math.floor(y),xf=x-x0,yf=y-y0;
  function grad(ix,iy,dx,dy){const a=hash2(ix,iy,s)*6.2831853;return Math.cos(a)*dx+Math.sin(a)*dy;}
  const u=fade5(xf),v=fade5(yf);
  const n00=grad(x0,y0,xf,yf),n10=grad(x0+1,y0,xf-1,yf),n01=grad(x0,y0+1,xf,yf-1),n11=grad(x0+1,y0+1,xf-1,yf-1);
  return 0.5+0.5*lerp(lerp(n00,n10,u),lerp(n01,n11,u),v)*1.35;
}
export function snoise(x,y,s){ // 2D simplex gradient noise on a triangular lattice, normalised to [0,1]
  const F2=0.3660254037844386,G2=0.21132486540518713;
  const skew=(x+y)*F2,i=Math.floor(x+skew),j=Math.floor(y+skew),unskew=(i+j)*G2;
  const x0=x-(i-unskew),y0=y-(j-unskew),i1=x0>y0?1:0,j1=x0>y0?0:1;
  const x1=x0-i1+G2,y1=y0-j1+G2,x2=x0-1+2*G2,y2=y0-1+2*G2;
  function corner(ix,iy,dx,dy){
    let t=0.5-dx*dx-dy*dy;if(t<=0)return 0;
    const a=hash2(ix,iy,s)*6.28318530718;t*=t;
    return t*t*(Math.cos(a)*dx+Math.sin(a)*dy);
  }
  return clamp(0.5+35*(corner(i,j,x0,y0)+corner(i+i1,j+j1,x1,y1)+corner(i+1,j+1,x2,y2)),0,1);
}
// fractal sum over a base function
export function fbmField(base,{seed=1,freq=3,octaves=5,lac=2.0,gain=0.5,ridge=false}){
  const o=newField();const n=fieldW(),nh=fieldH();let amps=0,a=1;for(let k=0;k<octaves;k++){amps+=a;a*=gain;}
  // Authoring DOMAIN, not world metres (the AUTHORING DOMAIN note at isHex()). hxs=0 on square.
  const hxs=terrainDef.lattice==="hex"?0.5:0;
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const gu=xfU((x+hxs*(y&1))/n,y/nh),gv=xfV((x+hxs*(y&1))/n,y/nh);   // placement folded into the coordinates, not the raster
    let sum=0,amp=1,f=freq;
    for(let k=0;k<octaves;k++){
      let v=base(gu*f,gv*f,seed+k*7);
      if(ridge){v=1-Math.abs(v*2-1);v=v*v;}
      sum+=v*amp;amp*=gain;f*=lac;
    }
    o[y*n+x]=sum/amps;
  }
  return ridge?normalize(o):o;
}
export function worleyField({seed=1,freq=5,mode="f2f1"}){
  const o=newField();const n=fieldW(),nh=fieldH(),cells=Math.max(2,Math.round(freq));
  const hxs=terrainDef.lattice==="hex"?0.5:0;
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const px=xfU((x+hxs*(y&1))/n,y/nh)*cells,py=xfV((x+hxs*(y&1))/n,y/nh)*cells,cx=Math.floor(px),cy=Math.floor(py);
    let f1=9,f2=9;
    for(let j=-1;j<=1;j++)for(let i=-1;i<=1;i++){
      const gx=cx+i,gy=cy+j;
      const fx=gx+hash2(gx,gy,seed),fy=gy+hash2(gx,gy,seed+91);
      const d=Math.hypot(px-fx,py-fy);
      if(d<f1){f2=f1;f1=d;}else if(d<f2){f2=d;}
    }
    let v=mode==="f1"?f1:mode==="invf1"?1-f1:f2-f1;
    o[y*n+x]=v;
  }
  return normalize(o);
}
export function gradientField(angleDeg){
  const o=newField();const n=fieldW(),nh=fieldH(),a=angleDeg*Math.PI/180,cx=Math.cos(a),cy=Math.sin(a);
  const hxs=terrainDef.lattice==="hex"?0.5:0;
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){o[y*n+x]=(xfU((x+hxs*(y&1))/n,y/nh)*cx+xfV((x+hxs*(y&1))/n,y/nh)*cy);}
  return normalize(o);
}
export function radialField(){
  const o=newField();const n=fieldW(),nh=fieldH();
  const hxs=terrainDef.lattice==="hex"?0.5:0;
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const dx=xfU((x+hxs*(y&1))/n,y/nh)-.5,dy=xfV((x+hxs*(y&1))/n,y/nh)-.5;o[y*n+x]=1-clamp(Math.hypot(dx,dy)*2,0,1);}
  return o;
}

/* =====================================================================
   GPU COMPUTE — optional WebGL2 GPGPU fast path for the heavy kernels.
   Each kernel is a fragment shader run over a fullscreen triangle into an
   RGBA32F render target (the same technique as the deferred composite).
   The CPU kernels above stay the REFERENCE implementation; `_verify_gpu.js`
   checks the GPU output against them. Only the parallel-friendly kernels
   live here — sequential ones (priority flood, D8) remain CPU.
   ===================================================================== */
/* --------------------------------------------------------------------
   RESOLUTION INDEPENDENCE. Several node params are expressed in CELLS, so
   raising RES silently changes what they mean — e.g. thermal `talus` is a
   height drop per cell, and cell spacing is 1/RES, so the repose ANGLE it
   encodes is atan(talus*RES): 66° at 192² but 85° at 1024², which is why a
   high-res build came out spiky. Scaling converts those to resolution-
   independent quantities against a reference grid, so the same graph gives
   the same landform at any resolution (just with more detail) — the parity
   Gaea documents between a 512² preview and a 4K/8K build.
   -------------------------------------------------------------------- */
let SCALE_RES=true;
const REF_RES=192;
export const resScale=()=>SCALE_RES?RES/REF_RES:1;          // >1 when finer than the reference grid
export let BUILD_QUALITY="interactive";
export let USE_GPU=true;
// GPU compute, makeProg and u now live in src/core/. See the import at the top of this file.

/* ---- PLACEMENT (art direction): SDF shape masks positioned in METRES, mirroring
   reference-impl/placement.py. A Shape is both a mask (wire it into any node's Mask input to
   confine an effect) and a heightfield (erode it into a landform) — Gaea's Mask-as-Primitive. ---- */
export function shapeField(p){
  const n=fieldW(),nh=fieldH(),o=newField(),cs=cellSizeM();
  const cx=p.x*terrainDef.scale,cy=p.y*terrainDef.scale;          // 0..1 of the terrain -> metres
  const rad=p.size*terrainDef.scale*0.5,fall=Math.max(p.falloff*terrainDef.scale*0.5,cs);
  const a=-p.angle*Math.PI/180,ca=Math.cos(a),sa=Math.sin(a);
  const half=Math.max(rad*p.aspect,cs);
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const U=(x+0.5+(terrainDef.lattice==="hex"?0.5*(y&1):0))/n,V=(y+0.5)/nh; // authoring domain (note at isHex())
    let dx=xfU(U,V)*terrainDef.scale-cx,dy=xfV(U,V)*terrainDef.scale-cy;
    const rx=dx*ca-dy*sa,ry=dx*sa+dy*ca;                          // rotate into object space
    let d;
    if(p.kind==="box"){const qx=Math.abs(rx)-rad,qy=Math.abs(ry)-half;
      d=Math.hypot(Math.max(qx,0),Math.max(qy,0))+Math.min(Math.max(qx,qy),0);}
    else if(p.kind==="line"){const L=rad;const t=clamp(rx/(2*L)+0.5,0,1);
      const px=rx-(t*2*L-L),py=ry;d=Math.hypot(px,py)-half;}
    else d=Math.hypot(rx,ry/Math.max(p.aspect,1e-3))-rad;          // circle / ellipse
    o[y*n+x]=smooth(clamp((fall*0.5-d)/(fall||1e-6),0,1));         // SDF -> soft coverage
  }
  return p.invert==="on"?invertField(o):o;
}
// pointSegmentDistance lives at the stroke-rasteriser below (search: `function
// pointSegmentDistance`). A SECOND, textually different definition used to sit here and was dead
// code: in a classic script both declarations hoist and the LATER one wins, so this one had never
// executed. Under `sourceType: "module"` the same pair is a hard SyntaxError -- "Identifier
// 'pointSegmentDistance' has already been declared" -- which blocked the ES-module split outright.
// Removing the unreachable one is behaviour-preserving by construction. (The two differed in their
// degenerate-segment guard: this one tested `den > 1e-12`, the live one uses `d = dx*dx+dy*dy || 1`,
// which only catches exact zero. Both clamp t to [0,1] so a sub-micron segment collapses to its
// start point either way -- but if that guard is ever revisited, the epsilon form was the more
// careful of the two.)
// Vector brush strokes stay in normalised terrain coordinates, so an artist-authored road mask
// survives every working/build resolution. Strokes alpha-composite in order; Erase is destructive
// only inside this node and remains fully undoable/serialisable with the graph.
export function drawMaskField(p){
  const n=fieldW(),nh=fieldH(),N=n*nh,out=new Float32Array(N),strokes=Array.isArray(p.strokes)?p.strokes:[];
  for(const stroke of strokes){
    const pts=stroke.points||[];if(!pts.length)continue;
    const radius=Math.max(.0005,(stroke.width||.04)*.5),hard=clamp(stroke.hardness==null?.7:stroke.hardness,0,1);
    const inner=radius*hard,opacity=clamp(stroke.opacity==null?1:stroke.opacity,0,1),erase=stroke.mode==="erase";
    const coverage=d=>d>=radius?0:hard>=.999?1:1-smooth(clamp((d-inner)/Math.max(radius-inner,1e-6),0,1));
    const composite=(i,c)=>{const a=c*opacity;if(a>0)out[i]=erase?out[i]*(1-a):out[i]+(1-out[i])*a;};
    // Strokes are authored in the DOMAIN (note at isHex()) - the brush writes uv straight from the
    // pick, and a Shape at the same uv must land in the same place. Review caught the default
    // (non-Transform) branch unconverted once already: a stroke at v=0.8 landed 15.5% of the map
    // away from a Shape at the same coordinate, and inserting an identity Transform silently
    // moved every stroke. BOTH branches convert, and both convert the same way.
    const hxs=terrainDef.lattice==="hex"?0.5:0;
    if(XF){
      // An exact Transform can move any painted segment across the tile. Scan output cells once
      // per stroke and find the nearest segment; this avoids a 64 MB Float32 coverage raster at 4K.
      for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
        const su=(x+.5+hxs*(y&1))/n,sv=(y+.5)/nh;
        const u=xfU(su,sv),v=xfV(su,sv);let d=Infinity;
        if(pts.length===1)d=Math.hypot(u-pts[0][0],v-pts[0][1]);
        else for(let q=1;q<pts.length;q++)d=Math.min(d,pointSegmentDistance(u,v,pts[q-1][0],pts[q-1][1],pts[q][0],pts[q][1]));
        composite(y*n+x,coverage(d));
      }
      continue;
    }
    let minU=pts[0][0],maxU=minU,minV=pts[0][1],maxV=minV;
    for(const q of pts){minU=Math.min(minU,q[0]);maxU=Math.max(maxU,q[0]);minV=Math.min(minV,q[1]);maxV=Math.max(maxV,q[1]);}
    // Bounding boxes pad x by the odd-row shift; v is already a row fraction in the domain.
    const bx0=clamp(Math.floor((minU-radius)*n-hxs),0,n-1),bx1=clamp(Math.ceil((maxU+radius)*n),0,n-1);
    const by0=clamp(Math.floor((minV-radius)*nh),0,nh-1),by1=clamp(Math.ceil((maxV+radius)*nh),0,nh-1);
    const bw=bx1-bx0+1,bh=by1-by0+1,cov=new Uint8Array(bw*bh);
    const segment=(a,b)=>{
      const x0=clamp(Math.floor((Math.min(a[0],b[0])-radius)*n-hxs),bx0,bx1),x1=clamp(Math.ceil((Math.max(a[0],b[0])+radius)*n),bx0,bx1);
      const y0=clamp(Math.floor((Math.min(a[1],b[1])-radius)*nh),by0,by1),y1=clamp(Math.ceil((Math.max(a[1],b[1])+radius)*nh),by0,by1);
      for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){
        const c=Math.round(coverage(pointSegmentDistance((x+.5+hxs*(y&1))/n,(y+.5)/nh,a[0],a[1],b[0],b[1]))*255),i=(y-by0)*bw+x-bx0;
        if(c>cov[i])cov[i]=c;}
    };
    if(pts.length===1)segment(pts[0],pts[0]);else for(let i=1;i<pts.length;i++)segment(pts[i-1],pts[i]);
    for(let y=by0;y<=by1;y++)for(let x=bx0;x<=bx1;x++)composite(y*n+x,cov[(y-by0)*bw+x-bx0]/255);
  }
  return out;
}
export function sculptField(inp,p){
  const o=new Float32Array(inp.length),strength=clamp(p.strength==null?1:p.strength,0,1);
  let smoothed=null;if(p.mode==="smooth")smoothed=blurField(inp,{radius:Math.max(1,Math.round(p.radius*resScale()))});
  for(let i=0;i<o.length;i++){
    let target=inp[i];
    if(p.mode==="raise")target=inp[i]+p.amount;
    else if(p.mode==="lower")target=inp[i]-p.amount;
    else if(p.mode==="flatten")target=p.target;
    else if(smoothed)target=smoothed[i];
    o[i]=lerp(inp[i],target,strength);
  }
  return o;
}
// Universal MASK rule (Gaea: "connect a mask to a node and it is applied only within the masked
// area"). Applied as a POST-PROCESS lerp, so changing the mask never re-runs the effect.
export function maskApply(base,modified,mask){
  if(!mask)return modified;
  const o=newField();for(let i=0;i<o.length;i++){const m=clamp(mask[i],0,1);o[i]=base[i]+(modified[i]-base[i])*m;}
  return o;
}

/* ---- FALLOFF CURVE — the artist draws the transition, the engine reads a LUT.
   X is distance from the feature centre (0 at the summit, 1 at the radius); Y is the elevation
   multiplier (1 down to 0). A deep concave curve gives a wide sweeping talus apron; a straight line
   gives a cone; a convex one gives a plateau with an abrupt rim.

   Interpolation is monotone cubic Hermite (Fritsch-Carlson), NOT a plain Catmull-Rom or bezier,
   because an overshooting spline between control points would push the multiplier above 1 (terrain
   above the summit) or below 0 (terrain below the plane). Monotone cubic cannot overshoot by
   construction, so every curve an artist can draw is a valid envelope.

   The curve bakes once to a 256-entry LUT and the generator does a single lerped lookup per cell --
   cheaper than the pow() it replaces, and it means an arbitrary drawn shape costs the same as the
   analytic one. ---- */
const CURVE_N=256;
function bakeCurve(pts){
  const P=(pts||[]).slice().sort((a,b)=>a[0]-b[0]),out=new Float32Array(CURVE_N),m=P.length;
  if(m===0){out.fill(0);return out;}
  if(m===1){out.fill(clamp(P[0][1],0,1));return out;}
  const xs=P.map(q=>q[0]),ys=P.map(q=>q[1]),d=[],tg=[];
  for(let i=0;i<m-1;i++)d.push((ys[i+1]-ys[i])/Math.max(xs[i+1]-xs[i],1e-6));
  tg.push(d[0]);
  for(let i=1;i<m-1;i++){
    if(d[i-1]*d[i]<=0)tg.push(0);                       // local extremum -> flat, no overshoot
    else{const h1=Math.max(xs[i]-xs[i-1],1e-6),h2=Math.max(xs[i+1]-xs[i],1e-6);
      tg.push(3*(h1+h2)/((2*h2+h1)/d[i-1]+(h2+2*h1)/d[i]));}}
  tg.push(d[m-2]);
  for(let k=0;k<CURVE_N;k++){
    const x=k/(CURVE_N-1);
    if(x<=xs[0]){out[k]=clamp(ys[0],0,1);continue;}
    if(x>=xs[m-1]){out[k]=clamp(ys[m-1],0,1);continue;}
    let i=0;while(i<m-2&&x>xs[i+1])i++;
    const h=Math.max(xs[i+1]-xs[i],1e-6),t=(x-xs[i])/h,t2=t*t,t3=t2*t;
    out[k]=clamp((2*t3-3*t2+1)*ys[i]+(t3-2*t2+t)*h*tg[i]
                +(-2*t3+3*t2)*ys[i+1]+(t3-t2)*h*tg[i+1],0,1);}
  return out;
}
function curveAt(lut,x){                                // lerped lookup, so 256 entries read smooth
  const t=clamp(x,0,1)*(CURVE_N-1),i=Math.floor(t),f=t-i;
  return i>=CURVE_N-1?lut[CURVE_N-1]:lut[i]+(lut[i+1]-lut[i])*f;
}
function curveFromExponent(e,k=6){                      // the analytic (1-x)^e as control points
  const o=[];for(let i=0;i<k;i++){const x=i/(k-1);o.push([+x.toFixed(3),+Math.pow(1-x,e).toFixed(4)]);}
  return o;
}
const SKIRT_PRESETS=[["Cone",1.0],["Apron",1.4],["Sweeping",2.2],["Plateau",0.65]];
// The Mountain default is intentionally not a one-exponent radial ramp. Its upper crag, shoulder,
// main face and pediment occupy separate slope bands, which prevents the profile reading as canvas
// stretched between one pole and a circular rim.
// mountainSkirtDefault moved to src/core/defaults.js. The Mountain plugin reads it while building
// its params array — i.e. at module-evaluation time — and in the legacy<->plugin cycle the plugin
// evaluates first, so a value declared here is still in its temporal dead zone and throws
// "Cannot access mountainSkirtDefault before initialization", blanking the page. Anything a params
// array reads directly has to live outside the cycle.

/* ---- LAYOUT — the art-direction layer every terrain tool converges on. World Machine's Layout
   Generator, Houdini's HeightField Project from curves, Gaea's vector drawing, and academically
   Hnaidi et al. 2010 "Feature based terrain generation using diffusion equation" all do the same
   thing: you author a SKELETON in vector form with ELEVATION attached, and the procedural system
   fills in between. That is different from a mask, which only gates an effect that already exists.

   The decisive detail, taken from World Machine: elevation is PER VERTEX. A path is not a constant
   height ribbon, it carries a height profile along its length. That single property is what turns a
   drawn line into a ridgeline -- summits at the high vertices, saddles at the low ones, faces
   falling away either side -- and it is why the same node that art-directs a range is also the
   right way to build one mountain. ---- */
const FALLOFF={                                   // World Machine's falloff function list
  linear:  t=>t,
  squared: t=>t*t,
  sqrt:    t=>Math.sqrt(t),
  scurve:  t=>t*t*(3-2*t),
};
// Nearest point on a polyline, and the elevation INTERPOLATED along it at that point.
function polylineNearest(px,py,pts){
  if(pts.length===1)return {d:Math.hypot(px-pts[0][0],py-pts[0][1]),e:pts[0][2]};
  let bd=Infinity,be=0;
  for(let i=0;i<pts.length-1;i++){
    const ax=pts[i][0],ay=pts[i][1],ae=pts[i][2];
    const bx=pts[i+1][0],by=pts[i+1][1],be2=pts[i+1][2];
    const vx=bx-ax,vy=by-ay,wx=px-ax,wy=py-ay;
    const t=clamp((wx*vx+wy*vy)/(vx*vx+vy*vy||1e-9),0,1);
    const d=Math.hypot(px-(ax+t*vx),py-(ay+t*vy));
    if(d<bd){bd=d;be=ae+(be2-ae)*t;}}
  return {d:bd,e:be};
}
function pointInPoly(px,py,pts){
  let inside=false;
  for(let i=0,j=pts.length-1;i<pts.length;j=i++){
    const xi=pts[i][0],yi=pts[i][1],xj=pts[j][0],yj=pts[j][1];
    if((yi>py)!==(yj>py)&&px<(xj-xi)*(py-yi)/((yj-yi)||1e-9)+xi)inside=!inside;}
  return inside;
}
// Author the canyon trunk's centerline directly instead of only accepting the procedural sinusoid.
// Lines of "x,y" (normalized 0-1), sorted by y so callers can list them in any order; interpolated
// piecewise-linearly and held constant past the first/last row so v outside the authored span is
// still defined. Two points is a valid path (a straight cut); fewer is not enough to define one.
function parseCanyonWaypoints(text){
  const pts=[];
  for(const raw of String(text||"").split("\n")){
    const line=raw.trim();
    if(!line||line[0]==="#")continue;
    const a=line.split(",").map(Number);
    if(a.length>=2&&a.every(isFinite))pts.push([clamp(a[0],0,1),clamp(a[1],0,1)]);
  }
  if(pts.length<2)return null;
  pts.sort((p,q)=>p[1]-q[1]);
  return pts;
}
function canyonWaypointX(pts,v){
  if(v<=pts[0][1])return pts[0][0];
  if(v>=pts[pts.length-1][1])return pts[pts.length-1][0];
  for(let i=0;i<pts.length-1;i++){
    const [ax,ay]=pts[i],[bx,by]=pts[i+1];
    if(v>=ay&&v<=by){const t=by>ay?(v-ay)/(by-ay):0;return ax+(bx-ax)*t;}
  }
  return pts[pts.length-1][0];
}
/* Text format, one shape per header line, vertices `x,y,elevation` on the lines under it:
     path width=0.04 falloff=0.22 profile=scurve op=max breakup=0.4
       0.12,0.66,0.30   0.34,0.58,0.90   0.74,0.46,1.00 */
export function parseLayout(text){
  const shapes=[];let cur=null;
  for(const raw of String(text||"").split("\n")){
    const line=raw.trim();
    if(!line||line[0]==="#")continue;
    const m=line.match(/^(path|point|poly)\b(.*)$/i);
    if(m){
      cur={kind:m[1].toLowerCase(),pts:[],width:0,falloff:0.15,profile:"scurve",op:"max",breakup:0,seed:1};
      const kv=m[2].matchAll(/([A-Za-z]+)\s*=\s*([\w.\-]+)/g);
      for(const g of kv){const k=g[1],v=g[2];
        if(k==="profile"||k==="op")cur[k]=v;else if(k in cur)cur[k]=parseFloat(v);}
      shapes.push(cur);continue;}
    if(!cur)continue;
    for(const tok of line.split(/\s+/)){
      const a=tok.split(",").map(Number);
      if(a.length>=2&&a.every(v=>isFinite(v)))cur.pts.push([a[0],a[1],a.length>2?a[2]:1]);}
  }
  return shapes.filter(sh=>sh.pts.length>0);
}
export function layoutField(shapes,base){
  const n=fieldW(),nh=fieldH(),o=base?base.slice():newField(0);
  for(const sh of shapes){
    const prof=FALLOFF[sh.profile]||FALLOFF.scurve;
    const fall=Math.max(sh.falloff,1e-4),half=(sh.width||0)*0.5;
    for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
      const u=(x+0.5+(terrainDef.lattice==="hex"?0.5*(y&1):0))/n,v=(y+0.5)/nh;
      let {d,e}=polylineNearest(u,v,sh.pts);
      // inside a closed polygon the distance is zero, so the interior sits at the shape's elevation
      if(sh.kind==="poly"&&sh.pts.length>2&&pointInPoly(u,v,sh.pts))d=0;
      // "breakup" (World Machine's term): let a fractal distort the outline so it is not geometric
      if(sh.breakup)d+=fbm2(u*7,v*7,(sh.seed|0)+13,4)*sh.breakup*fall*0.5;
      d=Math.max(0,d-half);
      if(d>=fall)continue;
      const w=prof(clamp(1-d/fall,0,1)),val=e*w,i=y*n+x;
      o[i]=sh.op==="add"?o[i]+val
          :sh.op==="sub"?o[i]-val
          :sh.op==="replace"?(w>0.5?e:o[i])
          :Math.max(o[i],val);                    // max: greatest height governs (World Machine)
    }
  }
  return o;
}

/* ---- MOUNTAIN — a placeable FEATURE PRIMITIVE in the Gaea/World Machine/Houdini family,
   grounded in Genevaux et al. 2015 "Terrain Modelling from Feature Primitives" and Guerin et al.
   2016. It is not thresholded isotropic noise:
     PEAK   = an asymmetric uplift MASS composed from overlapping rock volumes, a short broken
              summit divide, broad face basins, modulated cellular structure and style weathering.
     MASSIF = the earlier multi-crest envelope + modulated Voronoi + style weathering.
   Placement is evaluated directly in the generator's world-space coordinates, so Position, Reach,
   Aspect and Trend are exact before the non-commuting erosion passes run.

   The order is deliberate. Starting with a cone and cutting radial grooves into it leaves a tent
   no matter how good the grooves are. Here the large rock masses, saddles and asymmetric faces exist
   BEFORE drainage and fine fracture. The cellular bands redistribute surface mass without replacing
   that silhouette, and the hydraulic/thermal passes weather the result rather than inventing it. ---- */
const MOUNTAIN_STYLES={
  // Legacy massif controls                       Peak controls
  //            cells warp relief spur crest erode talus repose terr  incise width rough cell branches profile macro meso divide basin
  basic: {cells:4.0,warp:.30,relief:.55,spur:.28,crest:1.15,erode:.00,talus:0, repose:.95,terr:0, incise:.46,width:1.16,rough:.032,cell:.070,branches:.55,profile:.92,macro:.12,meso:.020,divide:.94,basin:.50},
  eroded:{cells:5.0,warp:.55,relief:.66,spur:.40,crest:1.35,erode:.15,talus:0, repose:.72,terr:0, incise:.82,width:1.00,rough:.082,cell:.175,branches:1.00,profile:1.00,macro:.32,meso:.090,divide:.84,basin:1.00},
  old:   {cells:5.6,warp:.62,relief:.44,spur:.30,crest:1.05,erode:.18,talus:2, repose:.42,terr:0, incise:.54,width:1.42,rough:.040,cell:.080,branches:1.12,profile:.70,macro:.14,meso:.030,divide:.72,basin:.62},
  alpine:{cells:3.6,warp:.42,relief:.74,spur:.44,crest:1.70,erode:.10,talus:0, repose:1.15,terr:0, incise:.94,width:.78,rough:.125,cell:.230,branches:.82,profile:1.18,macro:.44,meso:.135,divide:.98,basin:1.08},
  strata:{cells:4.4,warp:.34,relief:.52,spur:.30,crest:1.20,erode:.08,talus:1, repose:.72,terr:9, incise:.68,width:1.06,rough:.048,cell:.115,branches:.78,profile:.86,macro:.22,meso:.055,divide:.86,basin:.82},
};
/* Gaea's public 1.3 documentation says its old Type control selected four different generative
   algorithms, but does not disclose those algorithms. These are clean-room behavioural families
   built from the documented geo-cellular vocabulary: they change the uplift topology before the
   five modern Mountain types add their own geomorphic expression. */
const MOUNTAIN_SHAPES={
  dominant:{spread:.82,central:1.00,alongA:.82,alongB:.64,sideA:.42,sideB:.36,tail:.30,
            broad:1.00,lobe:.76,face:.56,crest:.80,cellEdge:.78,cellCore:.22,basins:.78},
  compound:{spread:1.16,central:.96,alongA:1.00,alongB:.88,sideA:.72,sideB:.64,tail:.58,
            broad:1.08,lobe:.72,face:.60,crest:1.08,cellEdge:.62,cellCore:.38,basins:1.00},
  ridge:{spread:1.32,central:.93,alongA:.98,alongB:.91,sideA:.43,sideB:.38,tail:.67,
         broad:.88,lobe:.66,face:.50,crest:1.28,cellEdge:.90,cellCore:.10,basins:.86},
  broad:{spread:.92,central:1.00,alongA:.87,alongB:.78,sideA:.62,sideB:.56,tail:.48,
         broad:1.30,lobe:.70,face:.74,crest:.68,cellEdge:.42,cellCore:.58,basins:.66},
};
/* The clean-room peak model follows the visible/public contract of a modulated, distorted cellular
   primitive without attempting to reproduce proprietary internals. It builds an irregular cluster
   of overlapping uplift volumes around a short crest. Those volumes are intentionally broad:
   cellular detail may split a face, but it cannot turn a thin polyline into a mountain after the
   fact. Seed variation moves and reshapes the volumes; Position remains the dominant high point. */
function peakMasses(seed,character,variation,shape){
  const sh=MOUNTAIN_SHAPES[shape]||MOUNTAIN_SHAPES.compound;
  const hs=k=>hash2(seed|0,k,24733),axis=(hs(3)-.5)*(.22+.58*variation);
  const ca=Math.cos(axis),sa=Math.sin(axis),px=-sa,py=ca;
  const spread=(.46+.78*character)*sh.spread;
  const broad=sh.broad;
  const at=(t,side,amp,rx,ry,key)=>({
    x:ca*t*spread+px*side*spread,y:sa*t*spread+py*side*spread,
    amp:amp*(.72+.28*character),
    rx:rx*(1+(hs(key)-.5)*.42*variation),
    ry:ry*(1+(hs(key+1)-.5)*.48*variation),
    angle:axis+(hs(key+2)-.5)*(.18+.38*variation)
  });
  const lobes=[
    {...at(-.035,.018,sh.central,(.59+.10*character)*broad,(.54-.04*character)*broad,20),
      amp:sh.central*sh.lobe},
    at(.30+.08*(hs(31)-.5)*variation,.045,sh.alongA+.035*hs(32),.54*broad,.37*broad,34),
    at(-.33-.08*hs(40)*variation,-.055,sh.alongB+.05*hs(41),.52*broad,.35*broad,43),
    at(.06,.34+.08*(hs(50)-.5)*variation,sh.sideA+.06*hs(51),.46*broad,.30*broad,53),
    at(.10,-.38-.07*hs(60)*variation,sh.sideB+.06*hs(61),.44*broad,.28*broad,63),
    at(.57+.08*hs(70)*variation,.18*(hs(71)>.5?1:-1),sh.tail+.06*hs(72),.41*broad,.26*broad,74)
  ];
  for(let i=1;i<lobes.length;i++)lobes[i].amp*=sh.lobe;
  // A variable-height crest is the primary uplift skeleton. Each family gets a different summit /
  // saddle arrangement before any cellular modulation or erosion is applied.
  const crestSpec=shape==="dominant"
    ?[[-.47,-.04,.48],[-.23,.025,.73],[-.04,.01,1],[.19,.055,.74],[.43,-.02,.46]]
    :shape==="ridge"
    ?[[-.73,-.04,.42],[-.48,.035,.66],[-.19,.01,.94],[.08,.06,.98],[.37,-.015,.79],[.68,.025,.48]]
    :shape==="broad"
    ?[[-.50,-.04,.64],[-.27,.025,.91],[-.04,.01,.98],[.22,.055,.92],[.48,-.02,.64]]
    :[[-.61,-.045,.45],[-.35,.03,.79],[-.09,.012,.98],[.17,.06,.93],[.44,-.02,.67],[.65,.025,.43]];
  const crest=crestSpec
    .map((q,k)=>{
      const t=q[0]*spread,side=(q[1]+(hs(100+k)-.5)*.10*variation)*spread;
      return[ca*t+px*side,sa*t+py*side,q[2]-(k&&k<4?.025*hs(120+k):0)];
    });
  return{axis,lobes,crest,width:(.145+.065*character)*sh.crest,
    faceWidth:sh.face*(.90+.16*character),shape:sh};
}
// Only the largest face basins are authored. They start on different shoulders of the crest and
// wander toward unequal outlets; the hydraulic pass supplies the smaller connected hierarchy.
// This avoids the radial spoke field that made the old primitive read as stitched canvas panels.
function peakBasins(seed,axis,variation,detail){
  const hs=k=>hash2(seed|0,k,17749),basins=[];
  const angles=[axis+1.42,axis-1.18,axis+2.72,axis-.38];
  const count=detail<1?3:4;
  for(let j=0;j<count;j++){
    const a=angles[j]+(hs(30+j)-.5)*(.34+.38*variation);
    const headR=.16+.13*hs(45+j),endR=.82+.17*hs(55+j),pts=[];let aa=a;
    for(let k=0;k<=6;k++){
      const t=k/6,tt=smooth(t),r=lerp(headR,endR,tt);
      const target=a+(hs(80+j*11+k)-.5)*(.20+.26*variation)
        +Math.sin(t*Math.PI*1.4+hs(120+j)*6.283)*(.06+.08*variation);
      aa=lerp(aa,target,.46);
      pts.push([r*Math.cos(aa),r*Math.sin(aa),.34+.66*tt]);
    }
    basins.push({pts,width:(j===0?.17+.035*hs(150+j):.082+.040*hs(150+j))*(.94+detail*.035),
      strength:j===0?.84+.12*hs(170+j):.56+.28*hs(170+j)});
  }
  return basins;
}
function smoothMaxHeight(a,b,k){
  if(a<=0)return Math.max(0,b);
  if(b<=0)return Math.max(0,a);
  if(!(k>0))return Math.max(a,b);
  const t=clamp(.5+.5*(a-b)/k,0,1);
  return lerp(b,a,t)+k*t*(1-t);
}
function peakField(p){
  const n=fieldW(),nh=fieldH(),st=MOUNTAIN_STYLES[p.style]||MOUNTAIN_STYLES.eroded;
  const variation=Math.max(p.variation||0,0),hs=k=>hash2(p.seed|0,k,9137);
  const vr=(k,amt)=>1+(hs(k)*2-1)*amt*variation;
  const reach=Math.max(p.size,0.02)*vr(1,.22);
  const aspectS=Math.max(p.aspect||1,.15)*Math.exp((hs(2)-.5)*1.05*variation);
  const rot=p.angle*Math.PI/180+(hs(3)-.5)*.90*variation;
  const ca=Math.cos(rot),sa=Math.sin(rot),sx=reach*Math.sqrt(aspectS),sy=reach/Math.sqrt(aspectS);
  const relief=clamp(p.relief,0,1),char=Math.max(p.character||0,0);
  const weather=Math.max(p.weather==null?1:p.weather,0),height=Math.max(p.height==null?1:p.height,0);
  const reduce=clamp(p.reduce==null?0:p.reduce,0,1);
  const bulkExp=p.bulk==="low"?1.28:p.bulk==="high"?.72:1;
  const skirtLUT=bakeCurve(p.skirt&&p.skirt.length?p.skirt:mountainSkirtDefault());
  const detail=Math.max(p.detail||1,.2);
  const masses=peakMasses(p.seed,char,variation,p.shape);
  const basins=peakBasins(p.seed,masses.axis,variation,detail);
  const warpAmp=(.035+.075*char)*(.72+.28*variation);
  const w0x=fbm2(4.2,1.7,p.seed+31,4),w0y=fbm2(8.3,5.1,p.seed+32,4);
  let h=newField(0);const cover=newField(0);
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const u=(x+0.5+(terrainDef.lattice==="hex"?0.5*(y&1):0))/n,v=(y+0.5)/nh,dx=u-p.x,dy=v-p.y;
    let qx=( dx*ca+dy*sa)/sx,qy=(-dx*sa+dy*ca)/sy;
    // Subtract the warp at the origin: Character can move shoulders and contours without moving
    // the authored summit away from Position X/Y.
    const wx=fbm2(qx*1.65+4.2,qy*1.65+1.7,p.seed+31,4)-w0x;
    const wy=fbm2(qx*1.65+8.3,qy*1.65+5.1,p.seed+32,4)-w0y;
    qx+=wx*warpAmp;qy+=wy*warpAmp;
    // The broad, variable-height crest ribbon is the load-bearing envelope. Unequal widths on its
    // two sides create a steep wall and a longer face without requiring a radial cone.
    const cq=polylineNearest(qx,qy,masses.crest);
    const side=qx*(-Math.sin(masses.axis))+qy*Math.cos(masses.axis);
    const faceWarp=1+(fbm2(qx*1.25+2.7,qy*1.25+6.1,p.seed+46,3)-.5)*.22*char;
    const faceWidth=masses.faceWidth*(side>=0?1.10:.82)*faceWarp;
    let uplift=0;
    if(cq.d<faceWidth){
      const r=cq.d/Math.max(faceWidth,1e-5);
      uplift=cq.e*Math.pow(curveAt(skirtLUT,r),bulkExp*st.profile);
    }
    // Cellular uplift volumes now form shoulders and buttresses around that crest. Smooth max
    // removes Boolean seams but they no longer define the entire mountain as nested radial domes.
    for(const lobe of masses.lobes){
      const la=Math.cos(lobe.angle),ls=Math.sin(lobe.angle),lx=qx-lobe.x,ly=qy-lobe.y;
      const ex=(lx*la+ly*ls)/Math.max(lobe.rx,1e-4);
      const ey=(-lx*ls+ly*la)/Math.max(lobe.ry,1e-4),r=Math.hypot(ex,ey);
      if(r>=1)continue;
      const candidate=lobe.amp*Math.pow(curveAt(skirtLUT,r),bulkExp*st.profile);
      uplift=smoothMaxHeight(uplift,candidate,.025+.030*char);
    }
    if(cq.d<masses.width){
      const cross=Math.pow(1-cq.d/masses.width,.72);
      uplift=smoothMaxHeight(uplift,Math.pow(cq.e*cross,bulkExp*st.profile),.025+.018*char);
    }
    if(uplift<=.00005)continue;
    const i=y*n+x;cover[i]=1;

    // Two distorted cellular bands create connected large faces and subordinate rock blocks. The
    // frequencies are far enough apart to read as a hierarchy, not the same pattern at two scales.
    const mvx=fbm2(qx*1.28+7.2,qy*1.28+2.4,p.seed+55,4);
    const mvy=fbm2(qx*1.28+1.6,qy*1.28+8.7,p.seed+56,4);
    const macroU=qx*(2.45+detail*.10)+(.46+.28*char)*mvx;
    const macroV=qy*(2.45+detail*.10)+(.46+.28*char)*mvy;
    const macroEdge=worleyAt(macroU,macroV,p.seed+57,"f2f1");
    const macroF1=worleyAt(macroU,macroV,p.seed+57,"f1");
    const mesoEdge=worleyAt(qx*(5.05+detail*.30)+st.warp*mvy+3.1,
      qy*(5.05+detail*.30)-st.warp*mvx+6.7,p.seed+59,"f2f1");
    const macroBoundary=1-smooth(clamp(macroEdge/.42,0,1));
    const macroCore=1-smooth(clamp(macroF1/.72,0,1));
    const macroRidge=macroBoundary*masses.shape.cellEdge+macroCore*masses.shape.cellCore;
    const mesoRidge=1-smooth(clamp(mesoEdge/.34,0,1));
    const pointKeep=1-smooth(clamp((Math.hypot(qx,qy)-.012)/.055,0,1));
    const divideKeep=Math.pow(1-clamp(cq.d/(masses.width*.86),0,1),1.35)
      *smooth(clamp((cq.e-.43)/.48,0,1));
    const summitKeep=Math.max(pointKeep,divideKeep*st.divide);
    const macroDepth=st.macro*relief*(1-.55*reduce);
    let env=uplift*(1-macroDepth*(1-macroRidge));
    env*=1-st.meso*relief*(1-mesoRidge)*(1-reduce);
    env=lerp(env,uplift,summitKeep);

    // Four unequal, broad basins interrupt the faces. They do not share an apex and they do not
    // divide the footprint into radial sectors; smaller gullies are left to the process pass.
    let survive=1;
    for(const basin of basins){
      const q=polylineNearest(qx,qy,basin.pts),w=basin.width*st.width*(1+.30*q.e);
      const z=q.d/Math.max(w,1e-5);
      const cut=Math.exp(-1.65*z*z)*(.42+.58*q.e)*basin.strength;
      survive*=1-clamp(cut,0,.88);
    }
    env*=1-clamp((1-survive)*relief*st.incise*.66*st.basin*masses.shape.basins,0,.72);

    // Surface expression is subordinate to the uplift mass. A signed, slope-scale rock band breaks
    // planar faces; fine cellular boundaries cut fractures. Reduce Details removes these bands but
    // leaves the macro masses and basins intact.
    const rf=smooth(clamp((uplift-.025)/.28,0,1))*(1-summitKeep*.25);
    const rock=.68*fbm2(qx*(3.7+detail*.30)+5.7,qy*(3.7+detail*.30)+1.4,p.seed+69,5)
      +.32*(mesoRidge*2-1);
    const micro=Math.max(0,-fbm2(qx*(7+detail*1.8),qy*(7+detail*1.8),p.seed+73,4));
    const cellFreq=7.2+detail*2.05;
    const cwx=fbm2(qx*1.7+3.4,qy*1.7+8.1,p.seed+81,3);
    const cwy=fbm2(qx*1.7+7.8,qy*1.7+2.2,p.seed+82,3);
    const cellEdge=worleyAt(qx*cellFreq+st.warp*cwx,qy*cellFreq+st.warp*cwy,p.seed+83,"f2f1");
    const cellEdge2=worleyAt(qx*cellFreq*1.92+st.warp*cwy+4.1,
      qy*cellFreq*1.92-st.warp*cwx+7.3,p.seed+89,"f2f1");
    const fracture=.72*(1-smooth(clamp(cellEdge/.145,0,1)))
      +.28*(1-smooth(clamp(cellEdge2/.105,0,1)));
    const detailGain=.25+1.45*clamp((detail-.4)/3.1,0,1);
    const faceGain=(.045+st.rough*(.55+.45*weather))*char*(1-reduce)*rf;
    const fineCut=(st.cell*fracture+st.rough*.45*weather*micro)
      *detailGain*(1-reduce)*rf;
    h[i]=Math.max(0,env*(1+rock*faceGain)*(1-clamp(fineCut,0,.52)));
  }
  if(st.erode>0&&weather>0)h=hydraulicErode(h,{droplets:Math.round(st.erode*weather*n*nh),   // NOTE (converted, not an exemption): droplet COUNT (a cell-count proxy), not a field shape
    seed:p.seed+11,radius:Math.max(2,Math.round(resScale()*2)),spawn:cover});
  if(st.talus&&weather>0)h=thermalOn(h,{talus:st.repose*0.012/resScale(),
    iters:Math.max(1,Math.round(st.talus*weather)),rate:0.5});
  for(let i=0;i<h.length;i++)if(cover[i]<=0||h[i]<0)h[i]=0;   // open base-level footprint
  if(st.terr){const[,mx]=fieldRange(h);
    if(mx>0){const t=terraceField(scaleField(h,1/mx),{steps:st.terr,sharp:0.7});h=scaleField(t,mx);}}
  // Height is the final maximum elevation, matching the node contract after style weathering.
  const[,mx]=fieldRange(h);
  if(mx>0)for(let i=0;i<h.length;i++)h[i]=h[i]/mx*height;
  return h;
}
export function mountainField(p){
  if(p.form==="peak")return peakField(p);
  const n=fieldW(),nh=fieldH(),st=MOUNTAIN_STYLES[p.style]||MOUNTAIN_STYLES.eroded;
  const relief=p.relief,ncell=st.cells,warpamt=st.warp;
  const weather=Math.max(p.weather==null?1:p.weather,0),height=Math.max(p.height==null?1:p.height,0);
  const reduce=clamp(p.reduce==null?0:p.reduce,0,1),bulkExp=p.bulk==="low"?1.28:p.bulk==="high"?.72:1;
  // deterministic per-seed stream, so the same seed always builds the same massif
  let rs=Math.imul(p.seed|0,2654435761)>>>0;
  const rnd=()=>{rs=(Math.imul(rs^(rs>>>15),2246822519)+374761393)>>>0;return rs/4294967296;};
  // The SAME domain cell-units for both skeleton steps (review caught them disagreeing once:
  // Position Y meant two different places in the envelope and the ridge network). Domain, not
  // world - cy0 = p.y*nh is a row index, so Position Y=1 must reach the last row, which it does
  // not if the field is measured down a world axis only 0.866n tall. hxs is 0 on square.
  const hxs=terrainDef.lattice==="hex"?0.5:0;
  const cx0=p.x*n,cy0=p.y*nh,reach=Math.max(p.size,0.02)*n;
  const rot=p.angle*Math.PI/180;

  // 1) crest-skeleton envelope
  const env=newField();
  for(let r=0;r<Math.max(1,p.ridges|0);r++){
    const ang=rot+rnd()*Math.PI*(p.ridges>1?1:0),k=6,cxp=[],cyp=[];
    const px=-Math.sin(ang),py=Math.cos(ang);
    const wob=[];let acc=0;for(let a=0;a<k;a++){acc+=(rnd()-0.5)*0.1;wob.push(acc);}
    const wm=wob.reduce((s2,v)=>s2+v,0)/k;
    for(let a=0;a<k;a++){const t=-1+2*a/(k-1);
      cxp.push(cx0+0.9*reach*Math.cos(ang)*t+px*(wob[a]-wm)*n);
      cyp.push(cy0+0.9*reach*Math.sin(ang)*t+py*(wob[a]-wm)*n);}
    const amp=0.7+0.6*rnd();
    for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
      const xw=x+hxs*(y&1),yw=y;
      let d=Infinity;
      for(let a=0;a<k-1;a++)d=Math.min(d,sdSegment(xw,yw,cxp[a],cyp[a],cxp[a+1],cyp[a+1]));
      const e=amp*Math.pow(clamp(1-d/reach,0,1),1.6);
      const i=y*n+x;if(e>env[i])env[i]=e;}
  }

  // 2) modulated-Voronoi ridge network
  const netA=new Float32Array(n*nh),netB=new Float32Array(n*nh);
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const u=(x+hxs*(y&1))/n*ncell,v=y/nh*ncell;
    const wx=fbm2(u*0.35,v*0.35,p.seed+3,4)+0.5*fbm2(u*0.9,v*0.9,p.seed+13,4);
    const wy=fbm2(u*0.35+4.7,v*0.35+2.3,p.seed+4,4)+0.5*fbm2(u*0.9+1.9,v*0.9+6.1,p.seed+14,4);
    const u2=u+warpamt*wx,v2=v+warpamt*wy,i=y*n+x;
    netA[i]=worleyAt(u2,v2,p.seed+1,"f2f1");
    netB[i]=worleyAt(u2*2,v2*2,p.seed+8,"f2f1");}
  const pA=percentileOf(netA,0.98)+1e-9,pB=percentileOf(netB,0.98)+1e-9;

  // 3) incise: crest sits at the envelope, valleys drop `relief` below it
  let h=newField();
  for(let i=0;i<h.length;i++){
    const a=1-netA[i]/pA,b2=1-netB[i]/pB;
    const ridges=Math.pow(clamp((1-st.spur)*a+st.spur*b2,0,1),st.crest);
    h[i]=Math.pow(lerp(env[i]*((1-relief)+relief*ridges),env[i],reduce),bulkExp);}

  // 4) bake in the weathering the style implies
  if(st.erode>0&&weather>0)h=hydraulicErode(h,{droplets:Math.round(st.erode*weather*n*nh),   // NOTE (converted, not an exemption): droplet COUNT (a cell-count proxy), not a field shape
    seed:p.seed+11,radius:Math.max(2,Math.round(resScale()*2)),spawn:env});
  if(st.talus&&weather>0)h=thermalOn(h,{talus:st.repose*0.012/resScale(),
    iters:Math.max(1,Math.round(st.talus*weather)),rate:0.5});
  for(let i=0;i<h.length;i++)h[i]=env[i]>0?Math.max(0,h[i])*height:0;
  if(st.terr){const[,mx]=fieldRange(h);
    if(mx>0){const t=terraceField(scaleField(h,1/mx),{steps:st.terr,sharp:0.7});h=scaleField(t,mx);}}
  return h;
}

/* ---- CANYON — a fast LANDSCAPE primitive, not a hidden erosion composite.
   The public Gaea contract says Canyon is drainage-based and exposes Slot, Valley, Surrounding,
   Depth, Structural Warp and Detail Warp. The internals are proprietary, so this clean-room model
   constructs the process claim directly:
     * a high plateau is the mass;
     * a routed, accumulated catchment supplies the trunk and convergent tributaries;
     * downstream hydraulic geometry grows channel width and depth with drainage area;
     * non-uniform hard/soft beds, wall retreat, and colluvial aprons form the landform;
     * styles select different balances of those processes, never a cosmetic noise preset.
   Downstream Erosion remains the physically evolving process. This node is the art-directable,
   deterministic starting landform Gaea describes, evaluated in coordinate space before resampling. */
const CANYON_STYLE_ID={classic:0,eroded:1,eroded2:2,strata:3,both:4};
const CANYON_FORMATION=[
  // sideDepth, basinDepth, bench, layers, talus, breakup
  {sideDepth:.56,basinDepth:.16,bench:.36,layers:7,talus:.30,breakup:.14}, // Classic
  {sideDepth:.66,basinDepth:.24,bench:.16,layers:6,talus:.62,breakup:.27}, // Eroded
  {sideDepth:.82,basinDepth:.31,bench:.06,layers:6,talus:.54,breakup:.39}, // Eroded 2
  {sideDepth:.54,basinDepth:.13,bench:.92,layers:10,talus:.24,breakup:.09},// Strata
  {sideDepth:.75,basinDepth:.27,bench:.66,layers:8,talus:.46,breakup:.31}  // Both
];
// A layered erodibility field, following the representation of Beneš & Forsbach (2001).
// Thickness is deliberately non-uniform: uniform modulo bands are a terrace effect, not geology.
function canyonBeds(p){
  const style=CANYON_STYLE_ID[p.style]||0,count=CANYON_FORMATION[style].layers;
  let rs=(Math.imul((p.seed|0)^0x7f4a7c15,1597334677)+3812015801)>>>0;
  const rnd=()=>{rs=(Math.imul(rs^(rs>>>16),2246822519)+3266489917)>>>0;return rs/4294967296;};
  const raw=[];let total=0;
  for(let i=0;i<count;i++){const v=Math.exp((rnd()-.5)*1.15);raw.push(v);total+=v;}
  const beds=[];let top=0;
  for(let i=0;i<count;i++){
    top+=raw[i]/total;
    // Alternating cliff-formers and slope-formers, but never a perfect two-value barcode.
    const hard=clamp((i&1?(.68+.23*rnd()):(.16+.27*rnd()))+(rnd()-.5)*.08,.08,.94);
    beds.push([i===count-1?1:top,hard]);
  }
  return beds;
}
/* An earlier clean-room Canyon routed a drainage network and then used it as an SDF skeleton. That
   graph was better than hand-authored spokes, but the final geometry was still a union of rounded
   segment stamps: uniform cross-sections, capsule heads, and tributaries that looked applied to the
   plateau rather than cut into it. That path, its GPU shader and its segment constants have been
   deleted rather than left dormant, so there is exactly one Canyon implementation to reason about.

   The production primitive below instead evolves a small, process-resolution bedrock landscape:

     1. regional uplift, tilt, lithologic weakness and tiny initial relief establish POTENTIAL paths;
     2. an outlet-seeded Priority-Flood gives every cell a depression-safe route to one base level;
     3. contributing area and slope activate channel heads (Montgomery & Dietrich, 1988);
     4. Braun & Willett's implicit n=1 stream-power step magnifies convergent drainage;
     5. lithology-dependent hillslope diffusion and mass wasting widen the incised valleys.

   No tributary polyline is ever constructed or stamped. `tributaries` changes the channel-initiation
   threshold—the amount of runoff/weakness required for a head to persist—so branches emerge from the
   environment and meet downstream channels through the shared receiver graph. The broad trunk bias
   is only a shallow structural sag in the INITIAL plateau; it is deliberately much smaller than the
   final relief and cannot appear unless drainage captures and amplifies it. */
const CANYON_EVOLUTION_CACHE=new Map();
// K is a knickpoint CELERITY, not a free-floating strength. In the implicit n=1 solve a cell moves
// C/(1+C) of the way to its receiver per iteration, so an upstream-travelling signal decays by that
// factor PER CELL. The old K gave C ~= 0.18 at the trunk, i.e. 0.15 per cell: base-level fall died
// within five cells of the outlet and the interior was never told the canyon existed. Crossing a
// 191-cell grid needs C*iters on the order of the grid, which is what these values buy.
// `repose` replaces the old `D`/`talus` pair. Those were a linear-diffusion rate plus a per-cell
// normalised drop guard of .021-.034, which at a 26 m process cell implies 64-73 degrees - a
// grid-blade cutoff, never a repose angle. `repose` scales the bed table's angles per style, so a
// style now changes how the hillslope FAILS rather than how hard it is blurred.
const CANYON_PROCESS=[
  // iterations, Kdt, head area, area exponent, lithology contrast, repose scale
  {iters:90,K:.075,head:78,m:.46,lith:.52,repose:1.00}, // Classic
  {iters:105,K:.088,head:58,m:.47,lith:.42,repose:.86},// Eroded
  {iters:121,K:.102,head:42,m:.48,lith:.50,repose:.92},// Eroded 2
  {iters:96,K:.075,head:82,m:.45,lith:1.00,repose:1.06},// Strata
  {iters:115,K:.095,head:48,m:.47,lith:.92,repose:.95} // Both
];
// A canyon's depth has to be EARNED by the solve, not stamped on afterwards. The budget is the Depth
// slider's own label at Depth 1 (.82 * 2600 m = 2132 m), so the relief the solver carves and the relief
// the UI advertises are finally the same number. Previously the solver cut a ~360 m column, of which a
// hand-set outlet notch supplied 46%, and compose stretched the result 5.86x to fake the rest.
// CANYON_RELIEF_SCALE exists only to re-parameterise the two dimensionless thresholds that were tuned
// against that shallow column, so deepening the budget does not silently change what counts as a channel.
const CANYON_RELIEF_BUDGET=.82,CANYON_LEGACY_RELIEF=.1349;
// The process grid the cell-denominated parameters were tuned against. Everything expressed in
// cells is rescaled relative to this, so changing the grid changes DETAIL and not the landform.
const CANYON_REF_GRID=191;
const CANYON_RELIEF_SCALE=CANYON_RELIEF_BUDGET/CANYON_LEGACY_RELIEF;
function canyonSimulationSize(outputN){
  // Global flow topology needs coherent cells, not render pixels. Keeping that scale bounded makes
  // 2K/4K builds practical; the final heightfield is resampled and receives only subordinate detail.
  if(outputN<128)return Math.max(48,outputN);
  if(outputN<384)return 160;
  // The grid is now safely RAISABLE - every cell-denominated parameter is expressed relative to
  // CANYON_REF_GRID, and _verify_canyon_gridscale.js holds the landform invariant across 160/192/256.
  // It is kept at 192 for cost, not correctness: 224 measured 2.5 s against a 3 s budget, and since
  // every parameter except Depth triggers a rebuild, that is felt on each slider drag. Fine detail is
  // cheaper to buy from the output-resolution weathering pass, which does not pay the O(n^2) solve.
  if(outputN<1024)return 192;
  return 256;
}
function canyonCacheKey(p,n){
  // World extent and height are solver inputs, not just display units, so a terrainDef change has to
  // invalidate the cached process. Without this a resized world silently reuses a stale solve.
  return[n,p.style,p.scale,p.slot,p.valley,p.surrounding,p.structural,
    p.tributaries??0,p.seed,p.detailWarp,p.alternate,p.waypoints??'',
    terrainDef.scale,terrainDef.height].join("|");
}
function canyonPriorityFlood(h,n,outlet){const nh=latticeRows(n);
  const N=n*nh,filled=new Float32Array(N),done=new Uint8Array(N),rank=new Int32Array(N);
  const order=[],heap=[],flatEpsilon=7.5e-7;
  const push=(e,i)=>{heap.push([e,i]);let c=heap.length-1;while(c>0){const p=(c-1)>>1;
    if(heap[p][0]<=heap[c][0])break;[heap[p],heap[c]]=[heap[c],heap[p]];c=p;}};
  const pop=()=>{const top=heap[0],last=heap.pop();if(heap.length){heap[0]=last;let c=0;
    for(;;){const l=c*2+1,r=l+1;let s=c;
      if(l<heap.length&&heap[l][0]<heap[s][0])s=l;
      if(r<heap.length&&heap[r][0]<heap[s][0])s=r;
      if(s===c)break;[heap[s],heap[c]]=[heap[c],heap[s]];c=s;}}return top;};
  done[outlet]=1;filled[outlet]=h[outlet];push(h[outlet],outlet);
  const nb=[[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[1,-1],[-1,1],[1,1]];
  while(heap.length){
    const [e,i]=pop(),y=(i/n)|0,x=i-y*n;rank[i]=order.length;order.push(i);
    for(const[dx,dy]of nb){const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=n||yy>=nh)continue;
      const j=yy*n+xx;if(done[j])continue;done[j]=1;
      const z=h[j]<=e?e+flatEpsilon:h[j];filled[j]=z;push(z,j);}
  }
  return{filled,rank,order};
}
function canyonDrainage(h,n,outlet,inlet=-1,externalArea=0){const nh=latticeRows(n);
  const flood=canyonPriorityFlood(h,n,outlet),N=n*nh,rec=new Int32Array(N).fill(-1);
  const dist=new Float32Array(N).fill(1),A=new Float32Array(N).fill(1);
  const nb=[[-1,0,1],[1,0,1],[0,-1,1],[0,1,1],
    [-1,-1,Math.SQRT2],[1,-1,Math.SQRT2],[-1,1,Math.SQRT2],[1,1,Math.SQRT2]];
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const i=y*n+x;if(i===outlet)continue;let best=-Infinity,br=-1,bd=1;
    for(const[dx,dy,d]of nb){const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=n||yy>=nh)continue;
      const j=yy*n+xx;if(flood.rank[j]>=flood.rank[i])continue;
      // Prefer the steepest filled-surface descent. Rank resolves the epsilon flats created by
      // Priority-Flood without imposing a radial or shortest-path tributary layout.
      const slope=(flood.filled[i]-flood.filled[j])/d;
      const score=slope+(flood.rank[i]-flood.rank[j])*1e-10;
      if(score>best){best=score;br=j;bd=d;}}
    rec[i]=br;dist[i]=bd;
  }
  // Flood visitation is low -> high, so reversing it is a topological donor -> receiver pass.
  for(let k=flood.order.length-1;k>=0;k--){const i=flood.order[k],r=rec[i];if(r>=0)A[r]+=A[i];}
  // An antecedent river may carry discharge from beyond this tile. Add that contributing area at
  // the upstream boundary and let the current receiver graph—not an authored curve—carry it to the
  // outlet. This guarantees one through-going trunk without specifying any interior channel cell.
  if(inlet>=0&&externalArea>0){
    let i=inlet,guard=0;while(i>=0&&guard++<N){A[i]+=externalArea;if(i===outlet)break;i=rec[i];}
  }
  return{...flood,rec,dist,A};
}
function canyonBedHardness(z,beds){
  z=clamp(z,0,1);for(const b of beds)if(z<=b[0])return b[1];return beds[beds.length-1][1];
}
// Thermal erosion (Musgrave, Kolb & Mace, 1989) REPLACES linear hillslope diffusion rather than
// supplementing it. Linear D*grad^2(h) has no threshold in it, so it cannot express a repose angle: it
// drives every hillslope toward one equilibrium gradient, which is exactly why the old surface showed
// a single ~14.5 degree slope mode in ALL FIVE styles. Thermal is slope-limited diffusion, so it
// stands in for the diffusion term AND supplies repose behaviour - one operator instead of two, and
// running both would be worse than either, because the linear term rounds off the very cliff lip the
// hard bed just produced.
// The angle comes from the SAME bed table that sets erodibility. That pairing is load-bearing: bedded
// K with a uniform talus angle lets thermal shave off the cliffs differential erosion just built,
// while bedded talus with uniform K puts cliffs where nothing pins them and the next pass relaxes
// them away. Competent beds hold a near-cliff face, soft beds stand at scree repose, and that
// contrast is what makes a cliff band over a talus apron instead of a uniformly faceted wall.
// `wash` is the fraction of colluvium delivered onto a cell that the river carries away instead of
// leaving as fill. Without it a deep canyon buries itself under its own walls: hillslope retreat
// delivers debris to the floor every iteration and nothing removes it, so the canyon shallows as fast
// as it is cut. Stream power as solved here is detachment-limited - it is already a no-deposition
// model - and the tile is an open system that exports sediment through the outlet, so the material is
// genuinely leaving rather than vanishing. It is returned as `exported` so the mass budget can be
// audited, because a silent sink is indistinguishable from a bug.
function canyonThermalStep(h,n,tanLut,wash,base,relief,cellM,heightM,c,budget){const nh=latticeRows(n);
  const N=n*nh,next=new Float32Array(N),delta=new Float32Array(N),LUTM=tanLut.length-1;
  const invRelief=1/Math.max(relief,1e-6);
  // Per-neighbour distance correction. Holding all eight neighbours to one drop means diagonals are
  // limited to a slope SQRT2 times too steep, so material collapses preferentially along the
  // cardinals and every cone grows a plus-shaped artefact.
  const card=cellM/heightM,diag=card*Math.SQRT2;
  const nbx=[-1,1,0,0,-1,1,-1,1],nby=[0,0,-1,1,-1,-1,1,1];
  const nbd=[card,card,card,card,diag,diag,diag,diag];
  // Hoisted scratch: allocating per cell here would cost more in GC than the whole pass.
  const sj=new Int32Array(8),sd=new Float64Array(8),sl=new Float64Array(8);
  for(let y=1;y<nh-1;y++)for(let x=1;x<n-1;x++){
    const i=y*n+x,hi=h[i];
    const k=clamp(Math.round((hi-base)*invRelief*LUTM),0,LUTM),tanPhi=tanLut[k];
    let cnt=0,dTotal=0,maxExcess=0;
    for(let q=0;q<8;q++){
      const j=(y+nby[q])*n+x+nbx[q],d=hi-h[j];
      if(d<=0)continue;
      const lim=tanPhi*nbd[q];
      if(d<=lim)continue;
      sj[cnt]=j;sd[cnt]=d;sl[cnt]=lim;cnt++;
      dTotal+=d;const e=d-lim;if(e>maxExcess)maxExcess=e;
    }
    if(!cnt)continue;
    // c*maxExcess/2: the halving is a stability factor. Moving the full excess overshoots and the
    // surface oscillates. Clamping each transfer to half of THAT pair's own excess makes every pair
    // individually non-inverting, so the step is stable no matter how many neighbours are steep.
    const moved=c*maxExcess/2;
    for(let q=0;q<cnt;q++){
      const give=Math.min(moved*sd[q]/dTotal,(sd[q]-sl[q])/2),j=sj[q],w=wash[j];
      delta[i]-=give;delta[j]+=give*(1-w);
      if(w>0&&budget)budget.exported+=give*w;
    }
  }
  // Double-buffered: accumulate into delta, then apply. In-place neighbour updates make the result
  // order-dependent, which is the classic "my thermal erosion changes when I enable threading" bug.
  for(let i=0;i<N;i++)next[i]=h[i]+delta[i];
  return next;
}
// Compose is an AFFINE VIEW of the evolved surface, and nothing more. It used to rebuild the output
// from the PRE-EROSION surface minus a triple-blurred `incision` mask, which discarded the solve
// entirely - correlation between the evolved surface and what reached the screen was 0.478. Every
// lithologic contrast, every hillslope response and every caprock was computed, cached, and thrown
// away; what looked like bedding was a compose-side bed-snapping remap, i.e. a terrace filter applied
// to a finished heightfield, which the literature is explicit destroys drainage geometry because the
// rivers end up running through the steps rather than down them.
// Depth stays a composition-only control: it is a pure vertical gain on the cached solve, so a depth
// edit is two flops per cell and never re-runs the process.
function canyonComposeField(result,p){
  const {n,h,hDatum,surrounding}=result,nh=latticeRows(n),N=n*nh;
  const depth=.10+.72*clamp(p.depth,0,1.25),rim=.88+.035*surrounding;
  const gain=depth/CANYON_RELIEF_BUDGET,field=new Float32Array(N);
  for(let i=0;i<N;i++)field[i]=rim-gain*(hDatum-h[i]);
  result.field=field;result.renderDepth=p.depth;return result;
}
function canyonEvolutionState(p,requestedN){
  const n=requestedN||canyonSimulationSize(RES),nh=latticeRows(n),key=canyonCacheKey(p,n);
  if(CANYON_EVOLUTION_CACHE.has(key))return canyonComposeField(CANYON_EVOLUTION_CACHE.get(key),p);
  const N=n*nh,style=CANYON_STYLE_ID[p.style]||0,proc=CANYON_PROCESS[style],beds=canyonBeds(p);
  const seed=p.seed|0,structural=clamp(p.structural,0,1),detail=clamp(p.detailWarp,0,1);
  const scale=clamp(p.scale,0,1),valley=clamp(p.valley,0,1),slot=clamp(p.slot,0,1);
  const surrounding=clamp(p.surrounding,0,1),density=clamp((p.tributaries??0)/8,0,1);
  const alternate=p.alternate==="on",initial=new Float32Array(N);let h=new Float32Array(N);
  const uplift=new Float32Array(N),weakness=new Float32Array(N),fluvialCut=new Float32Array(N);
  const phase=(hash2(seed,17,seed+199)-.5)*Math.PI*2;
  // A waypoint path (if the user drew one) supplies the macro trunk shape; the same fine fbm wiggle
  // still rides on top either way, so an authored two-point line still incises as an organic river
  // and not a ruler-straight cut. No waypoints -> byte-identical to the procedural sinusoid.
  const waypoints=parseCanyonWaypoints(p.waypoints);
  const centerAt=waypoints
    ?v=>clamp(canyonWaypointX(waypoints,v)+fbm2(.37,v*1.65+3.4,seed+201,4)*.035,.16,.84)
    :y=>clamp(.5+(.018+.105*structural)*Math.sin(y*Math.PI*(1.18+.72*structural)+phase)
    +fbm2(.37,y*1.65+3.4,seed+201,4)*.052*structural,.16,.84);
  const inletX=clamp(Math.round(centerAt(0)*(n-1)),2,n-3),inlet=inletX;
  const outletX=clamp(Math.round(centerAt(1)*(n-1)),2,n-3),outlet=(nh-1)*n+outletX;
  const externalArea=N*lerp(.22,.48,scale);
  let initialMin=Infinity,initialMax=-Infinity;
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const i=y*n+x,u=x/(n-1),v=y/(nh-1),cx=centerAt(v),dx=Math.abs(u-cx);
    // A broad synclinal/weak structural corridor and regional downstream tilt only seed drainage.
    // Their relief is < 8% of the requested final canyon depth; incision must amplify them.
    const macro=fbm2(u*(1.55+scale*.75)+4.3,v*(1.55+scale*.75)+8.1,seed+211,5);
    const grain=fbm2(u*(5.4+detail*3.2)+10.7,v*(5.4+detail*3.2)+1.9,seed+223,4);
    const syncline=Math.exp(-Math.pow(dx/lerp(.085,.22,scale),2));
    const chamber=alternate*Math.exp(-((u-.46)*(u-.46)/.055+(v-.53)*(v-.53)/.085));
    const regional=.855+.052*(1-v)+(.010+.035*surrounding)*macro+.010*detail*grain
      -(.006+.018*structural)*syncline-.032*chamber;
    h[i]=initial[i]=regional;initialMin=Math.min(initialMin,regional);initialMax=Math.max(initialMax,regional);
    const margin=Math.min(u,1-u,v,1-v);
    uplift[i]=smooth(clamp(margin*n/5,0,1))*(.55+.45*(1-syncline));
    const joints=.5+.5*fbm2(u*3.2+6.4,v*3.2+2.7,seed+229,5);
    // The amphitheatre is a WEAKNESS, not a dent. A real headwall bowl is fractured or spring-sapped
    // rock that retreats faster, so it belongs in erodibility exactly like the syncline corridor above.
    // Carving it into the initial surface alone would be authored relief that erosion never earns.
    weakness[i]=lerp(.76,1.28,joints)*lerp(1,1.18,syncline*structural)*lerp(1,1.55,chamber);
  }
  // Closed/no-flow borders are kept as plateau. Only this small bottom breach is base level, and it is
  // NOT pre-notched: a hand-set drop is authored relief, and the old one supplied 46% of the entire
  // landscape range before a single grain moved. Instead base level FALLS on a schedule through the run,
  // so every metre of canyon depth has to be transmitted upstream by the incision solve.
  // `base` is the FINAL datum from iteration 0, which keeps the stratigraphic column fixed in space -
  // beds must not drift downward with the outlet, or they stop being horizontal.
  const hDatum=initialMax,baseFinal=hDatum-CANYON_RELIEF_BUDGET,baseStart=initialMin-.004;
  h[outlet]=baseStart;
  const base=baseFinal,initialRelief=CANYON_RELIEF_BUDGET;
  let state=null,channelHeadIndex=new Float32Array(N);
  // A nonlinear response reserves the low end for a genuinely isolated antecedent trunk, while the
  // upper half progressively exposes the drainage hierarchy already latent in the environment.
  const densityThreshold=.38+3.20*Math.pow(1-density,2);
  // Valley now acts on the PROCESS, not on a compose-time remap of a finished field. A broad-valley
  // landscape is one where channels start higher on the hillslope, so it lowers the area-slope
  // initiation threshold; the wall-retreat half of the same control lives in the hillslope step below.
  // GRID INVARIANCE. Contributing area is accumulated in CELLS, so the same physical catchment counts
  // (n-1)^2 times more cells on a finer grid. A threshold written as a bare cell count therefore means
  // a different physical area at every resolution, and simply raising the process grid would quietly
  // channelise the whole map. Scaling by the squared grid ratio expresses it as a fixed AREA instead.
  // `proc.head` stays the value tuned at the reference grid, so this is exactly 1.0 there.
  const gridRatio=(n-1)/CANYON_REF_GRID;
  const headBase=proc.head*gridRatio*gridRatio
    *densityThreshold*lerp(1.12,.82,detail)*lerp(1.22,.80,valley);
  // Likewise the incision coefficient: C is proportional to A^m/dist with A in cells and dist in
  // cells, so it drifts as (n-1)^(2m-1) unless corrected. Left uncorrected, a finer grid erodes at a
  // different rate and the landform changes when only the resolution did.
  const kScale=Math.pow(1/gridRatio,2*proc.m-1);
  const totalIters=Math.round(proc.iters*lerp(.90,1.12,surrounding));
  // One definition, two consumers: the iteration loop below and the processDelta reference after it.
  // These were separate copies of the same literal. Changing one and not the other would silently
  // desynchronise the uplift reference, poisoning processDelta -> residualCut -> incision, and would
  // take the gap, taper and junction diagnostics down with it without any test naming the cause.
  const upliftStep=.00011*lerp(.65,1.35,surrounding);
  // ONE bed table, resolved once into a lookup indexed by normalised elevation, feeding BOTH
  // erodibility and repose angle. These two must never decouple - see canyonThermalStep. Resolving it
  // up front also keeps Math.tan and the 6-10 element stack walk out of a loop that runs ~3M times.
  // Repose bands follow the material tables: scree/talus 35-40, fractured bedrock 45-55, competent
  // rock approaching vertical. Higher lithologic contrast widens the gap between soft and stiff beds,
  // which is precisely what turns a smooth wall into alternating cliff bands and slopes.
  const LUT=1024,hardLut=new Float32Array(LUT),tanLut=new Float32Array(LUT);
  // Slot and Valley are the two ends of one physical control: how steeply the walls stand. A slot
  // canyon is defined by near-vertical walls confining a narrow floor; a broad valley by walls that
  // lie back. Both therefore act on the repose angle rather than on a compose-time cross-section.
  const reposeScale=proc.repose*lerp(1.32,.76,valley)*lerp(.74,1.34,slot);
  // Soft beds stand at scree/talus repose; competent beds run from fractured bedrock toward a
  // near-vertical rock face. CLAMPED into those material bands: Valley and Slot shift the angles
  // WITHIN what the rock can do, and must not push them outside it. Unclamped, Valley 0.87 drove soft
  // beds to 27 degrees - below any real scree angle - and the walls read as melted rather than as
  // debris slopes.
  const softDeg=clamp((43-11*proc.lith)*reposeScale,30,46);
  const stiffDeg=clamp((54+22*proc.lith)*reposeScale,47,84);
  for(let k=0;k<LUT;k++){
    const hard=canyonBedHardness(k/(LUT-1),beds);
    hardLut[k]=hard;
    tanLut[k]=Math.tan(lerp(softDeg,stiffDeg,smooth(hard))*Math.PI/180);
  }
  const lutIndex=v=>clamp(Math.round((v-base)/CANYON_RELIEF_BUDGET*(LUT-1)),0,LUT-1);
  const cellM=terrainDef.scale/(n-1),heightM=terrainDef.height;
  // Reference slope for the channel-head test, re-expressed for the deeper column. .012/.075 is exactly
  // .16, so this reduces to the original formula at the legacy relief: the threshold keeps meaning the
  // same thing about drainage, instead of quietly loosening because every gradient just got 6x steeper.
  const sRef=.075*CANYON_RELIEF_SCALE,sOff=sRef*.16;
  const wash=new Float32Array(N),logN=Math.log2(Math.max(N,2)),budget={exported:0};
  // A cell is "channel" by discharge, so the transport capacity that removes talus is derived from
  // contributing area rather than from a drawn mask.
  // Capped below 1: a river removes talus at CAPACITY, not completely. Exporting every grain leaves no
  // debris population at all, the walls stand at whatever the depth-to-width ratio forces, and the
  // slope modes stop tracking the bed table - which is the difference between a repose mechanism and
  // a geometric artefact that merely looks like one.
  // Confined to the true channel CORE, not the whole valley. Washing broadly starves the slopes of
  // debris entirely: the walls then stand whereever the depth-to-width ratio forces them rather than
  // at repose, and the slope modes stop responding to the bed table. Narrow and strong reproduces the
  // real arrangement - a gorge whose river keeps its own bed clear while talus aprons accumulate on
  // the valley floor either side of it.
  const refreshWash=()=>{for(let i=0;i<N;i++)
    wash[i]=.88*smooth(clamp((Math.log2(Math.max(1,state.A[i]))/logN-.66)/.16,0,1));};
  for(let it=0;it<totalIters;it++){
    // Base level falls on a smoothstep schedule. The canyon is cut by transmitting that fall upstream
    // through the receiver graph, which is what makes depth a product of drainage rather than of a hole.
    const baseNow=baseStart+(baseFinal-baseStart)*smooth((it+1)/totalIters);
    for(let i=0;i<N;i++)if(i!==outlet)h[i]+=upliftStep*uplift[i];
    h[outlet]=baseNow;
    for(let x=Math.max(0,outletX-1);x<=Math.min(n-1,outletX+1);x++)
      h[(nh-1)*n+x]=Math.min(h[(nh-1)*n+x],baseNow+Math.abs(x-outletX)*.002);
    if(!state||it%3===0){state=canyonDrainage(h,n,outlet,inlet,externalArea);refreshWash();}
    // Receiver-first is the implicit O(N) Braun-Willett solve for n=1. Unlike an SDF trench,
    // incision grows only after flow area and local gradient cross the channel-head condition.
    for(const i of state.order){
      const r=state.rec[i];if(r<0)continue;
      const S=Math.max((state.filled[i]-state.filled[r])*(n-1)/state.dist[i],1e-5);
      const A=state.A[i],critical=headBase*Math.pow(sRef/(S+sOff),1.12);
      const activation=smooth(clamp((A/Math.max(critical,1)-.72)/.72,0,1));
      channelHeadIndex[i]=A/Math.max(critical,1);
      if(activation<=0)continue;
      const hard=hardLut[lutIndex(h[i])];
      const erodibility=weakness[i]*lerp(1.38,.34,hard*proc.lith);
      const C=proc.K*kScale*lerp(.78,1.28,scale)*erodibility*activation*Math.pow(A,proc.m)/state.dist[i];
      const before=h[i];h[i]=(h[i]+C*h[r])/(1+C);
      if(h[i]<h[r])h[i]=h[r];
      fluvialCut[i]+=Math.max(0,before-h[i]);
    }
    // Legal Order: thermal runs AFTER the fluvial sweep, every iteration. Reversed, incision simply
    // re-steepens what thermal just relaxed and the hillslope pass is wasted work.
    // Thermal converges - once every slope is at or under repose, further passes do nothing - so the
    // control is the ANGLE, not the count. Two passes per iteration is what it takes for relaxation to
    // keep pace with an incision solve this strong; with one, walls stay over-steepened above repose
    // and the slope modes report the depth-to-width geometry instead of the material.
    h=canyonThermalStep(h,n,tanLut,wash,base,initialRelief,cellM,heightM,.5,budget);
    h=canyonThermalStep(h,n,tanLut,wash,base,initialRelief,cellM,heightM,.5,budget);
    h[outlet]=baseNow;
  }
  // HILLSLOPE RELAXATION TAIL. While base level is still falling, incision cuts a channel cell far
  // below its neighbours in a single step and thermal can only remove part of that excess per pass, so
  // walls stay over-steepened for as long as the driver runs - the solver was leaving ~39% of the grid
  // above 70 degrees, i.e. pinned by the depth-to-width geometry rather than resting at a material
  // angle. Once the schedule ends the driver stops but the hillslopes have not finished responding,
  // which is a real ordering in landscape evolution, not a numerical trick: relief is created faster
  // than slopes can adjust, and they keep adjusting afterwards. Thermal converges, so this terminates.
  // How long the hillslopes get to respond is itself a landform control. A slot canyon is a YOUNG,
  // barely-relaxed form whose walls have not had time to lie back; a broad valley is the same canyon
  // after its hillslopes have caught up. So Slot shortens the tail and Valley lengthens it, which is a
  // statement about relative rates rather than a shape parameter.
  const tailPasses=Math.round(lerp(20,6,slot)*lerp(.85,1.25,valley));
  for(let k=0;k<tailPasses;k++){
    h=canyonThermalStep(h,n,tanLut,wash,base,initialRelief,cellM,heightM,.6,budget);
    h[outlet]=baseFinal;
  }
  state=canyonDrainage(h,n,outlet,inlet,externalArea);
  // Render the CHANGE made by the process, not the regional tilt that drove it. Cumulative incision
  // records capture and headward growth; the final area/slope field supplies a connected hydraulic
  // backbone after channels have migrated. Diffusing those process fields gives valley width without
  // measuring distance to a line, stamping a capsule, or inventing an independent cross-section.
  const cutRadius=Math.max(1,Math.round(1+valley*1.8-slot*.55));
  const cumulative=blurScalarField(fluvialCut,n,cutRadius,2),sortedCumulative=Array.from(cumulative).sort((a,b)=>a-b);
  const cumulativeScale=Math.max(sortedCumulative[Math.min(N-1,Math.floor(N*.992))],1e-6);
  const channelSeed=new Float32Array(N),activeChannel=new Uint8Array(N),outletArea=Math.max(state.A[outlet],1);
  for(let i=0;i<N;i++){
    const r=state.rec[i];if(r<0)continue;
    const S=Math.max((state.filled[i]-state.filled[r])*(n-1)/state.dist[i],1e-5);
    const critical=headBase*Math.pow(.075/(S+.012),1.12),ratio=state.A[i]/Math.max(critical,1);
    channelHeadIndex[i]=ratio;
    const active=smooth(clamp((ratio-.68)/.88,0,1));
    activeChannel[i]=ratio>=.68?1:0;
    channelSeed[i]=active*Math.pow(clamp(state.A[i]/outletArea,0,1),.24);
  }
  // A threshold defines where a channel BEGINS, not whether it randomly disappears downstream on a
  // low-gradient reach. Propagate every initiated channel through its receivers before composing the
  // valley field. This removes the disconnected dark capsules caused by evaluating the head test as
  // an independent per-cell mask.
  for(let k=state.order.length-1;k>=0;k--){
    const i=state.order[k],r=state.rec[i];if(!activeChannel[i]||r<0)continue;
    activeChannel[r]=1;
    // Carry MEMBERSHIP, derive STRENGTH locally. Inheriting the head's amplitude would make every
    // reach the same size and erase the discharge hierarchy; downstream hydraulic geometry sizes a
    // reach by its OWN discharge, which the contributing area already measures. A reach that is
    // carried rather than self-initiating sits on a low-gradient, more depositional stretch, so it
    // stays subordinate to one that crosses the area-slope threshold on its own.
    const carried=Math.pow(clamp(state.A[r]/outletArea,0,1),.24)
      *lerp(.42,1,smooth(clamp(channelHeadIndex[r]/.68,0,1)));
    channelSeed[r]=Math.max(channelSeed[r],carried);
    channelHeadIndex[r]=Math.max(channelHeadIndex[r],.68);
  }
  // Channel heads do not terminate in hemispherical caps: a colluvial hollow continues upslope and
  // tapers into the divide. Follow the largest environmental donor above each area/slope threshold
  // crossing, decaying the signal headward. This uses the drainage graph and never invents a spline.
  const bestDonor=new Int32Array(N).fill(-1),hasActiveDonor=new Uint8Array(N);
  for(let i=0;i<N;i++){const r=state.rec[i];if(r<0)continue;
    if(bestDonor[r]<0||state.A[i]>state.A[bestDonor[r]])bestDonor[r]=i;
    if(activeChannel[i])hasActiveDonor[r]=1;}
  const extension=Math.max(2,Math.round(lerp(5,12,detail)*lerp(.82,1.18,scale)
    *(n-1)/CANYON_REF_GRID));   // a hollow is a LENGTH in metres, not a fixed number of cells
  for(let i=0;i<N;i++)if(activeChannel[i]&&!hasActiveDonor[i]){
    let cur=bestDonor[i],strength=channelSeed[i]*.52;
    for(let k=0;k<extension&&cur>=0;k++){
      channelSeed[cur]=Math.max(channelSeed[cur],strength);
      strength*=.72;cur=bestDonor[cur];
    }
  }
  let connected=blurScalarField(channelSeed,n,cutRadius,3),connectedScale=1e-6;
  for(let i=0;i<N;i++)connectedScale=Math.max(connectedScale,connected[i]);
  const processDelta=new Float32Array(N);
  for(let i=0;i<N;i++){
    const reference=initial[i]+(i===outlet?0:upliftStep*totalIters*uplift[i]);
    processDelta[i]=h[i]-reference;
  }
  const relaxedDelta=blurScalarField(processDelta,n,Math.max(1,cutRadius-1),2);
  const residualCut=new Float32Array(N),sortedResidual=new Array(N);
  for(let i=0;i<N;i++)sortedResidual[i]=residualCut[i]=Math.max(0,-relaxedDelta[i]);
  sortedResidual.sort((a,b)=>a-b);
  const residualScale=Math.max(sortedResidual[Math.min(N-1,Math.floor(N*.992))],1e-6);
  const incision=new Float32Array(N);
  for(let i=0;i<N;i++){
    const connectedN=clamp(connected[i]/connectedScale,0,1),support=Math.pow(connectedN,.34);
    incision[i]=Math.max(connectedN,.52*clamp(cumulative[i]/cumulativeScale,0,1)*support,
      .58*clamp(residualCut[i]/residualScale,0,1)*support);
  }
  // CONTRACT: `incision`, `channelHeadIndex` and the routing fields are PROCESS DIAGNOSTICS, consumed
  // by the verification suite to measure the network. They are never masks on the output height - the
  // output is the evolved surface. Re-introducing one into compose would restore the defect above.
  const result={n,initial,initialMin,initialMax,h,hDatum,filled:state.filled,rec:state.rec,A:state.A,
    incision,beds,style,surrounding,channelHeadIndex,inlet,outlet,headBase,iterations:totalIters};
  canyonComposeField(result,p);
  CANYON_EVOLUTION_CACHE.set(key,result);
  if(CANYON_EVOLUTION_CACHE.size>10)CANYON_EVOLUTION_CACHE.delete(CANYON_EVOLUTION_CACHE.keys().next().value);
  return result;
}
// SURFACE EXPRESSION at output resolution: weather -> deposit -> relax.
// This replaces a term that subtracted fbm straight from height wherever the surface was steep - noise
// with no rate, no material, and no mass budget, which is decoration by any honest reading. Here the
// cliff face RETREATS at a rate set by its own material and exposure, the liberated mass is DEPOSITED
// at the foot of the face it came from, and the debris then stands at its own repose angle. What comes
// out is benches, facets, chutes and talus aprons.
// It is legal at output resolution because thermal and weathering are scale-free; a second stream-power
// pass here would not be, which is why this adds no channels. It cannot: it produces no drainage.
// NOTE THE ORDER MATTERS AND THE SOURCE IS LOad-BEARING. A thermal pass alone on a bilinearly upsampled
// field does exactly nothing, because bilinear interpolation's gradient is a convex combination of the
// coarse edge gradients and is therefore bounded by the coarse maximum: a surface at repose on the
// process grid is still at repose on the finer grid. Do not delete the weathering source and keep the
// relaxation - that would silently turn this whole pass into a no-op.
function canyonSurfaceExpression(state,p,o,n){const nh=latticeRows(n);
  const N=n*nh,detail=clamp(p.detailWarp,0,1);
  const cellM=terrainDef.scale/(n-1),H=terrainDef.height;
  // Compose is affine, and an affine map preserves NORMALISED position, so taking `rel` from the
  // field's own range makes the bed lookup identical at every Depth. The stratigraphy a face exposes
  // must not slide up and down the column when the Depth slider moves.
  let oMin=Infinity,oMax=-Infinity;
  for(let i=0;i<N;i++){if(o[i]<oMin)oMin=o[i];if(o[i]>oMax)oMax=o[i];}
  const inv=1/Math.max(oMax-oMin,1e-6);
  const src=new Float32Array(N),dep=new Float32Array(N);
  const tan28=Math.tan(28*Math.PI/180),tan62=Math.tan(62*Math.PI/180);
  let sourced=0,exported=0;
  // Full field, border included: one-sided differences at the edge (replicate boundary) rather than
  // skipping the outermost ring outright. The prior y=1..nh-2/x=1..n-2 loop left every border pixel
  // permanently unweathered - a visible, untouched seam exactly at the domain edge, worst at higher
  // output resolutions where that seam is a full render pixel wide. `(xp-xm)`/`(yp-ym)` is 2 in the
  // interior (central difference, unchanged) and 1 at the edge (one-sided), so no fictitious neighbour
  // across the boundary is invented.
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const i=y*n+x;
    const xm=x>0?x-1:x,xp=x<n-1?x+1:x,ym=y>0?y-1:y,yp=y<nh-1?y+1:y;
    const gx=(o[y*n+xp]-o[y*n+xm])*H/(cellM*Math.max(xp-xm,1)),gy=(o[yp*n+x]-o[ym*n+x])*H/(cellM*Math.max(yp-ym,1)),S=Math.hypot(gx,gy);
    // Hard-gated to zero below 28 degrees: this is FACE retreat, so it does not touch gentle ground.
    if(S<=tan28)continue;
    const exposure=smooth(clamp((S-tan28)/(tan62-tan28),0,1));
    const rel=clamp((o[i]-oMin)*inv,0,1);
    const hard=canyonBedHardness(rel,state.beds);
    const soften=lerp(1.45,.28,hard);
    // Fracture density is a MATERIAL property that multiplies a rate; it is scaled by the bed hardness
    // from the same table and cannot act where exposure is zero. It is not added to height.
    const joint=lerp(.66,1.34,.5+.5*fbm2(x/n*17.5,y/nh*17.5,p.seed+241,5));
    const retreatM=(7.5+38.0*detail)*exposure*soften*joint;
    const lower=retreatM*S/H;
    src[i]=lower;sourced+=lower;
  }
  // Deposit at the foot of the face: one steepest-descent hop. Mass is moved, never conjured.
  // Full field again; clamped neighbour coordinates that fall back onto the source cell itself are
  // skipped (`j===i`), so a border/corner cell with no true off-domain neighbour on some side simply
  // has fewer candidates rather than inventing one - it can still deposit toward any real interior
  // neighbour it has.
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const i=y*n+x,q=src[i];if(q<=0)continue;
    let bj=-1,best=0;
    for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
      if(!dx&&!dy)continue;
      const nx=clamp(x+dx,0,n-1),ny=clamp(y+dy,0,nh-1),j=ny*n+nx;if(j===i)continue;
      const d=o[i]-o[j];
      if(d>best){best=d;bj=j;}
    }
    if(bj<0){exported+=q;continue;}
    dep[bj]+=q;
  }
  for(let i=0;i<N;i++)o[i]+=dep[i]-src[i];
  return{sourced,exported,deposited:sourced-exported};
}
// A rill pass at render resolution was built, measured, and REMOVED - recording it so it is not
// rediscovered as a good idea. Droplet erosion seeded on the hillslopes made the surface SMOOTHER
// at every scale (29 m band 25.0 -> 17.4 m RMS, and worse with a tighter brush). It roughens a
// smooth base, which is what the Mountain primitive feeds it, but this surface already sits at
// repose with sharp thermal facets, so droplets simply plane the highs into the lows. The fine
// scale is carried instead by the weathering pass above: the 29 m band measures 25.0 m RMS here
// against 2.28 m before this work, comfortably past the fractal-consistent expectation of ~13 m.
function canyonFieldCPU(p){
  const state=canyonEvolutionState(p),o=state.n===RES?state.field.slice():resampleRect(state.field,state.n,latticeRows(state.n),RES,fieldH());
  if(RES>state.n){
    state.surface=canyonSurfaceExpression(state,p,o,RES);
  }
  return o;
}
export function canyonField(p){return canyonFieldCPU(p);}
export function fbm2(x,y,seed,oct){                      // small fbm helper for the domain distortion
  let s=0,amp=1,f=1,tot=0;
  for(let k=0;k<oct;k++){s+=(gnoise(x*f,y*f,seed+k*7)-0.5)*2*amp;tot+=amp;amp*=0.5;f*=2;}
  return s/(tot||1);
}
function scaleField(f,k){const o=newField();for(let i=0;i<o.length;i++)o[i]=f[i]*k;return o;}

/* ---- SPATIAL SCALE: run an effect over a larger/smaller area (Gaea's Feature Scale + Transform) ---- */
function resampleField(f,fromN,toN){            // bilinear resample between two square grids
  const o=new Float32Array(toN*toN);
  const g=(xx,yy)=>f[clamp(yy,0,fromN-1)*fromN+clamp(xx,0,fromN-1)];
  for(let y=0;y<toN;y++)for(let x=0;x<toN;x++){
    const sx=(x+0.5)*fromN/toN-0.5,sy=(y+0.5)*fromN/toN-0.5;
    const x0=Math.floor(sx),y0=Math.floor(sy),fx=sx-x0,fy=sy-y0;
    o[y*toN+x]=lerp(lerp(g(x0,y0),g(x0+1,y0),fx),lerp(g(x0,y0+1),g(x0+1,y0+1),fx),fy);}
  return o;
}
// Rectangular twin of resampleField, for grids whose ROW COUNT is not their width. Each axis
// rescales independently and the row clamp uses the SOURCE row count, so a W x H field resamples
// without cropping its bottom band. resampleField keeps its square-in-square-out contract for the
// callers that genuinely mean a square grid; this is line-for-line identical to it whenever
// fromH===fromW and toH===toW, which is every call while latticeRows(w)===w.
function resampleRect(f,fromW,fromH,toW,toH){
  const o=new Float32Array(toW*toH);
  const g=(xx,yy)=>f[clamp(yy,0,fromH-1)*fromW+clamp(xx,0,fromW-1)];
  for(let y=0;y<toH;y++)for(let x=0;x<toW;x++){
    const sx=(x+0.5)*fromW/toW-0.5,sy=(y+0.5)*fromH/toH-0.5;
    const x0=Math.floor(sx),y0=Math.floor(sy),fx=sx-x0,fy=sy-y0;
    o[y*toW+x]=lerp(lerp(g(x0,y0),g(x0+1,y0),fx),lerp(g(x0,y0+1),g(x0+1,y0+1),fx),fy);}
  return o;
}
// FEATURE SCALE — run `fn` on a grid k times coarser so its features come out k times WIDER, then add
// the change back at full resolution (fine detail is preserved; only the erosion's footprint grows).
// Coarse cell size is k * cellSizeM() metres, which is the lateral size the simulation actually sees.
export function atFeatureScale(inp,k,fn){
  if(!(k>1.02))return fn(inp);
  const full=RES,fullH=latticeRows(full),w=Math.max(16,Math.round(RES/k)),wH=latticeRows(w);
  const small=resampleRect(inp,full,fullH,w,wH);
  const prev=RES;let out;
  RES=w;try{out=fn(small);}finally{RES=prev;}   // the kernels read the global RES
  const d=new Float32Array(w*wH);for(let i=0;i<w*wH;i++)d[i]=out[i]-small[i];
  const up=resampleRect(d,w,wH,full,fullH),o=newField();
  for(let i=0;i<o.length;i++)o[i]=inp[i]+up[i];
  return o;
}
// TRANSFORM — move / rotate / scale the terrain itself (Gaea's Transform node). scale>1 magnifies.
export function transformField(inp,{scale=1,aspect=1,angle=0,offX=0,offY=0,pivX=0.5,pivY=0.5,edge="clamp"}){
  const n=fieldW(),nh=fieldH(),o=newField(),a=-angle*Math.PI/180,ca=Math.cos(a),sa=Math.sin(a);
  const sX=Math.max(0.05,scale),sY=Math.max(0.05,scale*aspect);
  // Edge handling is per AXIS: columns wrap/mirror/clamp over the WIDTH, rows over the ROW COUNT.
  const wrapAt=(t,m)=>edge==="wrap"?((t%m)+m)%m
    :edge==="mirror"?(()=>{const p=((t%(2*m))+2*m)%(2*m);return p<m?p:2*m-1-p;})()
    :clamp(t,0,m-1);
  const samp=(fx,fy)=>{const x0=Math.floor(fx),y0=Math.floor(fy),tx=fx-x0,ty=fy-y0;
    const g=(xx,yy)=>inp[wrapAt(yy,nh)*n+wrapAt(xx,n)];
    return lerp(lerp(g(x0,y0),g(x0+1,y0),tx),lerp(g(x0,y0+1),g(x0+1,y0+1),tx),ty);};
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const u=(x+0.5)/n-pivX,v=(y+0.5)/nh-pivY;
    let ru=(u*ca-v*sa)/sX,rv=(u*sa+v*ca)/sY;    // inverse map: sample a smaller region to magnify
    ru+=pivX-offX;rv+=pivY-offY;
    o[y*n+x]=samp(ru*n-0.5,rv*nh-0.5);}
  return o;
}

/* ------------------------------------------------------- modifiers ---- */
export function warpField(inp,{strength=0.12,freq=3,seed=7}){
  const o=newField();const n=fieldW(),nh=fieldH(),s=strength*n;
  // Seed contract AND world-space displacement (26). Two separate hex defects lived here, and
  // together they were the largest single reason the DEFAULT graph's terrain changed on a
  // lattice toggle (warp sits early in perlin -> blend -> warp -> hydraulic -> thermal, and is
  // height-critical): the driving noise was sampled at raw grid indices, and the displaced
  // lookup handed raw indices to a sampler that reads world positions.
  //
  // Warp is the one node that straddles both coordinate systems (the note at isHex()), so it is worth
  // being explicit. The driving noise and the displacement are AUTHORED, so they live in the
  // domain: du,dv are domain cell units and the offsets displace a domain point. sampleBilinear
  // reads WORLD positions, so the displaced point converts on the way in - and only there.
  // hxs=0, rzs=1 on square: byte-identical there.
  const hxs=terrainDef.lattice==="hex"?0.5:0,rzs=terrainDef.lattice==="hex"?HEX_ROW:1;
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const du=x+hxs*(y&1),dv=y;
    // du is a COLUMN (divide by the width) and dv a ROW (divide by the row count). This line had
    // both transposed - inert on square where nh===n, ~15% anisotropic distortion of the x
    // displacement on hex, and invisible to every gate. Found by cross-model review.
    const ox=(gnoise(du/n*freq,dv/nh*freq,seed)-.5)*2*s;
    const oy=(gnoise(du/n*freq,dv/nh*freq,seed+53)-.5)*2*s;
    o[y*n+x]=sampleBilinear(inp,du+ox,(dv+oy)*rzs);
  }
  return o;
}
export function terraceField(inp,{steps=8,sharp=0.6}){
  const o=newField();
  for(let i=0;i<inp.length;i++){
    const v=inp[i]*steps;const f=Math.floor(v),frac=v-f;
    const s=frac<0.5?0.5*Math.pow(frac*2,1+sharp*4):1-0.5*Math.pow((1-frac)*2,1+sharp*4);
    o[i]=(f+s)/steps;
  }
  return o;
}
export function curveField(inp,{bias=0.5,gain=0.5}){
  // Schlick bias/gain tone curve; 0.5 = identity for each.
  const b=clamp(bias,.01,.99),g=clamp(gain,.01,.99);
  const biasF=(x,k)=>x/(((1/k-2)*(1-x))+1);
  const gainF=(x,k)=>x<0.5?biasF(2*x,k)/2:1-biasF(2-2*x,k)/2;
  const o=newField();
  for(let i=0;i<inp.length;i++){let x=clamp(inp[i],0,1);x=biasF(x,b);x=gainF(x,g);o[i]=clamp(x,0,1);}
  return o;
}
export function levelsField(inp,{inLo=0,inHi=1,gamma=1,outLo=0,outHi=1}){
  const o=newField();const d=(inHi-inLo)||1e-6;const ig=1/Math.max(1e-3,gamma);
  for(let i=0;i<inp.length;i++){let v=clamp((inp[i]-inLo)/d,0,1);v=Math.pow(v,ig);o[i]=outLo+v*(outHi-outLo);}
  return o;
}
export function clampField(inp,{lo=0,hi=1}){const o=newField();for(let i=0;i<inp.length;i++)o[i]=clamp(inp[i],lo,hi);return o;}
export function invertField(inp){const o=newField();for(let i=0;i<inp.length;i++)o[i]=1-inp[i];return o;}
// A 1-D Gaussian tap set of half-width r, normalised. sigma is expressed in LATTICE STEPS, and
// on both lattices a step along a lattice line is one world unit, so the same weights serve every
// axis. Separated out because the hex path needs the identical kernel three times.
function gaussTaps(r,sigma){
  const w=[];let ws=0;
  for(let k=-r;k<=r;k++){const g=Math.exp(-(k*k)/(2*sigma*sigma));w.push(g);ws+=g;}
  for(let i=0;i<w.length;i++)w[i]/=ws;
  return w;
}

// THE SQUARE PATH, unchanged. Two separable passes along the array axes, which on a square lattice
// ARE the lattice lines. Kept byte-identical: the digest is a byte-identity gate and this is the
// path it measures.
function blurFieldSquare(inp,r){
  const n=fieldW(),nh=fieldH();const tmp=newField(),o=newField();
  const w=gaussTaps(r,r*0.6);
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){let s=0;for(let k=-r;k<=r;k++)s+=inp[y*n+clamp(x+k,0,n-1)]*w[k+r];tmp[y*n+x]=s;}
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){let s=0;for(let k=-r;k<=r;k++)s+=tmp[clamp(y+k,0,nh-1)*n+x]*w[k+r];o[y*n+x]=s;}
  return o;
}

// THE HEX PATH — three passes along the three lattice lines, not two along the array.
//
// Why the square code is wrong here, concretely: its second pass walks straight down the ARRAY,
// (x, y+1). On an odd-r offset lattice that is not a neighbour at all — the two cells below are at
// x and x±1 depending on row parity — and the row spacing is √3/2, not 1. So the vertical pass
// blurs along a direction the lattice does not have, with the wrong metric. Measured on an impulse,
// the result is an ellipse: anisotropy 1.185 at r=3 and 1.163 at r=6, against 1.0000 on square.
//
// A hex lattice has THREE axes at 60°, and three 1-D Gaussians at 60° compose to an isotropic 2-D
// Gaussian — the same fact that makes a 6-fold lattice isotropic at 4th order where a 4-fold one is
// not (FHP; `26`). The variance adds per axis: three passes of variance v give 3v/2 in every
// direction, so to land on target variance σ² each pass uses
//
//     σ' = σ·√(2/3)
//
// which is where the factor in this function comes from. It is not a tuning constant and must not
// be adjusted to taste — a different value produces a round blur of the wrong WIDTH, which is
// harder to notice than an elliptical one of the right width.
//
// Axis walking uses the same odd-r neighbour tables as thermalErodeHex. Stepping along axes B and C
// changes column by a row-parity-dependent amount, so the walk is done one row at a time rather
// than by an index stride.
function blurFieldHex(inp,r){
  const n=fieldW(),nh=fieldH();
  const w=gaussTaps(r,r*0.6*Math.sqrt(2/3));
  const at=(f,x,y)=>f[clamp(y,0,nh-1)*n+clamp(x,0,n-1)];

  // axis A: the row itself, (±1, 0) — a real lattice line on hex as on square
  const a=newField();
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    let s=0;for(let k=-r;k<=r;k++)s+=at(inp,x+k,y)*w[k+r];
    a[y*n+x]=s;
  }

  // axes B and C: one row per step, column shifted by parity.
  //   B (NW/SE): from an EVEN row, SE is (x, y+1) and NW is (x-1, y-1)
  //              from an ODD  row, SE is (x+1, y+1) and NW is (x, y-1)
  //   C (NE/SW): from an EVEN row, NE is (x, y-1) and SW is (x-1, y+1)
  //              from an ODD  row, NE is (x+1, y-1) and SW is (x, y+1)
  const walk=(src,dst,downDX)=>{
    for(let y0=0;y0<nh;y0++)for(let x0=0;x0<n;x0++){
      let s=src[y0*n+x0]*w[r];
      // downhill in y
      let x=x0,y=y0;
      for(let k=1;k<=r;k++){
        x+=downDX(y);y+=1;
        s+=at(src,x,y)*w[k+r];
      }
      // uphill in y — the inverse step, so the parity consulted is that of the row being LEFT
      x=x0;y=y0;
      for(let k=1;k<=r;k++){
        y-=1;x-=downDX(y);
        s+=at(src,x,y)*w[r-k];
      }
      dst[y0*n+x0]=s;
    }
  };
  const b=newField(),o=newField();
  walk(a,b,(y)=>(y&1)?1:0);    // B: SE steps +1 in x from an odd row, +0 from an even one
  walk(b,o,(y)=>(y&1)?0:-1);   // C: SW steps  0 in x from an odd row, -1 from an even one
  return o;
}

export function blurField(inp,{radius=2}){
  const r=Math.max(1,Math.round(radius));
  return isHex()?blurFieldHex(inp,r):blurFieldSquare(inp,r);
}
export function histEqualizeField(inp,{bins=256,amount=1}){
  const[mn,mx]=fieldRange(inp);const d=mx-mn||1;const hist=new Float64Array(bins);
  for(let i=0;i<inp.length;i++){const b=clamp(((inp[i]-mn)/d*(bins-1))|0,0,bins-1);hist[b]++;}
  const cdf=new Float64Array(bins);let acc=0;for(let b=0;b<bins;b++){acc+=hist[b];cdf[b]=acc;}
  const tot=cdf[bins-1]||1;const o=newField();
  for(let i=0;i<inp.length;i++){const b=clamp(((inp[i]-mn)/d*(bins-1))|0,0,bins-1);const eq=cdf[b]/tot;o[i]=lerp((inp[i]-mn)/d,eq,amount);}
  return o;
}

export function sharpenField(inp,{amount=1,radiusM=100}){
  const strength=Number.isFinite(amount)?Math.max(0,amount):1;
  if(strength===0)return inp.slice();
  const authoredRadius=Number.isFinite(radiusM)&&radiusM>0?radiusM:100;
  const blurred=blurField(inp,{radius:Math.max(1,authoredRadius/cellSizeM())}),o=newField();
  for(let i=0;i<inp.length;i++)o[i]=inp[i]+strength*(inp[i]-blurred[i]);
  return o;
}
export function thresholdField(inp,{cut=.5}){
  const threshold=Number.isFinite(cut)?cut:.5,o=newField();
  for(let i=0;i<inp.length;i++)o[i]=inp[i]>=threshold?1:0;
  return o;
}
function morphologyField(inp,radiusM,dilate){
  const radius=Number.isFinite(radiusM)?Math.max(0,radiusM):100;
  const k=Math.max(0,Math.round(radius/cellSizeM())),n=fieldW(),nh=fieldH();
  if(k===0)return inp.slice();
  const o=newField(),hex=isHex();
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    let value=dilate?-Infinity:Infinity;
    if(hex){
      const q=x-((y-(y&1))>>1);
      for(let dr=-k;dr<=k;dr++)for(let dq=Math.max(-k,-dr-k);dq<=Math.min(k,-dr+k);dq++){
        const yy=y+dr,qq=q+dq,xx=qq+((yy-(yy&1))>>1);
        if(xx<0||yy<0||xx>=n||yy>=nh)continue;
        value=dilate?Math.max(value,inp[yy*n+xx]):Math.min(value,inp[yy*n+xx]);
      }
    }else for(let dy=-k;dy<=k;dy++)for(let dx=-k;dx<=k;dx++){
      if(dx*dx+dy*dy>k*k)continue;
      const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=n||yy>=nh)continue;
      value=dilate?Math.max(value,inp[yy*n+xx]):Math.min(value,inp[yy*n+xx]);
    }
    o[y*n+x]=value;
  }
  return o;
}
export function dilateField(inp,{radiusM=100}){return morphologyField(inp,radiusM,true);}
export function deflateField(inp,{radiusM=100}){return morphologyField(inp,radiusM,false);}
export function matchField(source,target){
  if(!source||!target||source.length===0||source.length!==target.length)throw new Error("Match requires equal-length non-empty fields");
  const ranked=f=>Array.from(f,(value,index)=>{if(!Number.isFinite(value))throw new Error("Match requires finite fields");return{value,index};})
    .sort((a,b)=>a.value-b.value||a.index-b.index);
  const sourceRank=ranked(source),targetRank=ranked(target),o=new Float32Array(source.length);
  for(let k=0;k<sourceRank.length;k++)o[sourceRank[k].index]=targetRank[k].value;
  return o;
}
export function softClipField(inp,{lo=0,hi=1,softness=.5}){
  const lower=Number.isFinite(lo)?lo:0,upper=Number.isFinite(hi)&&hi>lower?hi:lower+1;
  const blend=Number.isFinite(softness)?clamp(softness,0,1):.5,o=newField(),range=upper-lower;
  for(let i=0;i<inp.length;i++){
    const t=clamp((inp[i]-lower)/range,0,1),hard=lower+range*t,soft=lower+range*t*t*(3-2*t);
    o[i]=hard+blend*(soft-hard);
  }
  return o;
}

function sampleLatticeWorld(inp,worldX,worldY){
  const n=fieldW(),nh=fieldH(),d=cellSizeM();
  const atOffset=(x,y)=>inp[clamp(y,0,nh-1)*n+clamp(x,0,n-1)];
  if(!isHex()){
    const fx=worldX/d-.5,fy=worldY/d-.5,x0=Math.floor(fx),y0=Math.floor(fy),tx=fx-x0,ty=fy-y0;
    return lerp(lerp(atOffset(x0,y0),atOffset(x0+1,y0),tx),lerp(atOffset(x0,y0+1),atOffset(x0+1,y0+1),tx),ty);
  }
  const r=worldY/(d*HEX_ROW)-.5,q=worldX/d-.5-r*.5;
  const qi=Math.floor(q),ri=Math.floor(r),fq=q-qi,fr=r-ri;
  const axial=(aq,ar)=>atOffset(aq+((ar-(ar&1))>>1),ar);
  if(fq+fr<=1)return(1-fq-fr)*axial(qi,ri)+fq*axial(qi+1,ri)+fr*axial(qi,ri+1);
  return(1-fr)*axial(qi+1,ri)+(1-fq)*axial(qi,ri+1)+(fq+fr-1)*axial(qi+1,ri+1);
}
function coordinateFilterField(inp,map){
  const o=newField(),n=fieldW(),nh=fieldH();
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const p=worldSampleAt(x,y),q=map(p[0],p[1],y*n+x);
    o[y*n+x]=sampleLatticeWorld(inp,q[0],q[1]);
  }
  return o;
}
export function flipField(inp,{axis="horizontal"}){
  const extent=terrainDef.scale;
  return coordinateFilterField(inp,(x,y)=>axis==="vertical"?[x,extent-y]:[extent-x,y]);
}
export function transposeWorldField(inp){return coordinateFilterField(inp,(x,y)=>[y,x]);}
function bearingDirection(bearing){
  const authored=Number.isFinite(bearing)?bearing:0;
  const theta=authored*Math.PI/180+(terrainDef.north||0)*Math.PI/180-Math.PI/2;
  return[Math.cos(theta),Math.sin(theta)];
}
export function foldField(inp,{bearing=0,offsetM=0}){
  const dir=bearingDirection(bearing),normal=[-dir[1],dir[0]],offset=Number.isFinite(offsetM)?offsetM:0;
  const ax=terrainDef.scale*.5+offset*normal[0],ay=terrainDef.scale*.5+offset*normal[1];
  return coordinateFilterField(inp,(x,y)=>{const side=(x-ax)*normal[0]+(y-ay)*normal[1];
    return side>=0?[x,y]:[x-2*side*normal[0],y-2*side*normal[1]];});
}
export function directionalWarpField(inp,driver,{bearing=0,amplitudeM=100}){
  if(!driver||driver.length!==inp.length)throw new Error("DirectionalWarp requires an equal-length Driver field");
  const amplitude=Number.isFinite(amplitudeM)?amplitudeM:100,dir=bearingDirection(bearing);
  if(amplitude===0)return inp.slice();
  return coordinateFilterField(inp,(x,y,index)=>{const value=driver[index];if(!Number.isFinite(value))throw new Error("DirectionalWarp Driver must be finite");
    const displacement=amplitude*value;return[x+dir[0]*displacement,y+dir[1]*displacement];});
}
export function aspectField(inp){
  const n=fieldW(),nh=fieldH(),d=cellSizeM(),o=newField();
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    let gx=0,gy=0;
    if(isHex()){
      const nb=hexNb(y);for(let k=0;k<6;k++){const h=inp[clamp(y+nb[k][1],0,nh-1)*n+clamp(x+nb[k][0],0,n-1)];gx+=h*HEX_EX[k];gy+=h*HEX_EY[k];}
      gx/=3*d;gy/=3*d;
    }else{
      gx=(inp[y*n+clamp(x+1,0,n-1)]-inp[y*n+clamp(x-1,0,n-1)])/(2*d);
      gy=(inp[clamp(y+1,0,nh-1)*n+x]-inp[clamp(y-1,0,nh-1)*n+x])/(2*d);
    }
    o[y*n+x]=gx===0&&gy===0?0:Math.atan2(-gy,-gx);
  }
  return o;
}
export function aspectPreviewField(inp,def=terrainDef){
  const o=new Float32Array(inp.length),north=(def.north||0)*Math.PI/180,tau=2*Math.PI;
  for(let i=0;i<inp.length;i++){const turn=(((inp[i]+Math.PI/2-north)/tau)%1+1)%1;o[i]=turn>1-2**-20?0:turn;}
  return o;
}

/* ------------------------------------------------------- combiners ---- */
export function combine(a,b,fn){const o=newField();for(let i=0;i<o.length;i++)o[i]=fn(a?a[i]:0,b?b[i]:0);return o;}
export function blendField(a,b,mask,factor){
  const o=newField();for(let i=0;i<o.length;i++){const t=mask?mask[i]:factor;o[i]=lerp(a?a[i]:0,b?b[i]:0,t);}return o;
}
export function smin(a,b,k){const h=clamp(0.5+0.5*(b-a)/k,0,1);return lerp(b,a,h)-k*h*(1-h);}
// Quilez smooth MAX. For a heightfield this is the crease-free UNION: merging two peaks means taking
// the higher surface, so it is max, not min. smin would take the lower one and delete both summits.
export function smax(a,b,k){return -smin(-a,-b,k);}
// --- pointwise primitives for feature generators (evaluate at ARBITRARY coordinates, not a grid) ---
function sdSegment(px,py,ax,ay,bx,by){
  const vx=bx-ax,vy=by-ay,wx=px-ax,wy=py-ay;
  const t=clamp((wx*vx+wy*vy)/(vx*vx+vy*vy||1e-9),0,1);
  return Math.hypot(wx-t*vx,wy-t*vy);
}
function worleyAt(u,v,seed,mode,period){         // F2-F1 at a point; no whole-field normalisation
  const cx=Math.floor(u),cy=Math.floor(v);let f1=9,f2=9;
  for(let j=-1;j<=1;j++)for(let i=-1;i<=1;i++){
    const gx=cx+i,gy=cy+j;
    // `period` wraps the u axis, so a network sampled in ANGLE joins seamlessly at +-pi
    const hx=period?((gx%period)+period)%period:gx;
    const fx=gx+hash2(hx,gy,seed),fy=gy+hash2(hx,gy,seed+91);
    const d=Math.hypot(u-fx,v-fy);
    if(d<f1){f2=f1;f1=d;}else if(d<f2){f2=d;}}
  return mode==="f1"?f1:f2-f1;
}
function percentileOf(f,q){                       // q in [0,1]
  const s=Float32Array.from(f);s.sort();
  return s[clamp(Math.floor(s.length*q),0,s.length-1)];
}

/* ----------------------------------------------------- selectors ------ */
export function slopeOf(inp){
  const n=fieldW(),nh=fieldH(),o=newField();
  if(isHex()){
    // D6 least-squares gradient. Square central differences on hex data span sqrt(3) world units
    // between rows y-1 and y+1 but still divide by 2, so a world-space CONE - which has one slope
    // at every azimuth - reads 2/sqrt(3) = 1.1547x steeper N-S than E-W. Measured on that cone:
    // ring anisotropy 1.147 before (square control 1.000), and the E-W/N-S ratio came out 1.1499
    // against the 1.1547 the mechanism predicts.
    for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
      const nb=hexNb(y);let gx=0,gy=0;
      for(let k=0;k<6;k++){
        const h=inp[clamp(y+nb[k][1],0,nh-1)*n+clamp(x+nb[k][0],0,n-1)];
        gx+=h*HEX_EX[k];gy+=h*HEX_EY[k];
      }
      o[y*n+x]=Math.hypot(gx,gy)/3*n;
    }
    return o;
  }
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const l=inp[y*n+clamp(x-1,0,n-1)],r=inp[y*n+clamp(x+1,0,n-1)];
    const u=inp[clamp(y-1,0,nh-1)*n+x],d=inp[clamp(y+1,0,nh-1)*n+x];
    o[y*n+x]=Math.hypot((r-l)*0.5,(d-u)*0.5)*n;
  }
  return o;
}
/* ---------------------------------------------------------------------
   DATA MAPS (Gaea's "Derive" channels) — grayscale fields you can bind a
   SatMap (or any mask input) to. Mirrors reference-impl/analysis.py.
   --------------------------------------------------------------------- */
const gAt=(f,x,y)=>f[clamp(y,0,fieldH()-1)*RES+clamp(x,0,RES-1)];
// Zevenbergen-Thorne curvature on the 3x3 window (analysis.curvature). profile: +ve concave valley floor.
export function curvatureField(inp,{kind="profile",strength=1}){
  const n=fieldW(),nh=fieldH(),o=newField(),L=1/n,eps=1e-12,hex=isHex();
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    let D,E,F,G,H;
    if(hex){
      // The 3x3 Zevenbergen-Thorne window is square machinery; the exactly analogous hex fit is a
      // quadratic least-squares over the D6 one-ring plus the centre (7 points, 6 coefficients).
      // With dz = z_k - z_centre and the six unit vectors e_k (y measured UP, as ZT's surface
      // does), the odd moments vanish and the normal equations collapse to a closed form:
      //   sum(e_x^4)=9/4, sum(e_x^2 e_y^2)=3/4, sum(e_x^3 e_y)=0
      //   P=sum(dz e_x^2), Q=sum(dz e_y^2), R=sum(dz e_x e_y)
      //   d=(3P-Q)/6, e=(3Q-P)/6, f=4R/3     [coefficients of x^2, y^2, xy in CELL units]
      // Consistency check that anchors the whole derivation: sum(dz)/3 = d+e, i.e. the Laplacian
      // is 2*sum(dz)/(3s^2) - exactly the 2/(3s^2) constant 26 warns is NOT 1/s^2.
      const nb=hexNb(y),z5=inp[y*n+x];
      let P=0,Q=0,R=0,gx=0,gy=0;
      for(let k=0;k<6;k++){
        const zk=gAt(inp,x+nb[k][0],y+nb[k][1]),dz=zk-z5;
        const ex=HEX_EX[k],ey=-HEX_EY[k];          // ey flipped: ZT measures y upward
        P+=dz*ex*ex;Q+=dz*ey*ey;R+=dz*ex*ey;gx+=zk*ex;gy+=zk*ey;
      }
      D=(3*P-Q)/6/(L*L);E=(3*Q-P)/6/(L*L);F=4*R/3/(L*L);
      G=gx/3/L;H=gy/3/L;
    }else{
      const z1=gAt(inp,x-1,y-1),z2=gAt(inp,x,y-1),z3=gAt(inp,x+1,y-1);
      const z4=gAt(inp,x-1,y),z5=gAt(inp,x,y),z6=gAt(inp,x+1,y);
      const z7=gAt(inp,x-1,y+1),z8=gAt(inp,x,y+1),z9=gAt(inp,x+1,y+1);
      D=((z4+z6)/2-z5)/(L*L);E=((z2+z8)/2-z5)/(L*L);F=(-z1+z3+z7-z9)/(4*L*L);
      G=(-z4+z6)/(2*L);H=(z2-z8)/(2*L);
    }
    const q=G*G+H*H;
    let c;
    if(kind==="mean")c=((1+G*G)*E*2-2*G*H*F+(1+H*H)*D*2)/(2*Math.pow(1+G*G+H*H,1.5));
    else if(q<eps)c=0;
    else if(kind==="plan")c=2*(D*H*H+E*G*G-F*G*H)/q;
    else c=2*(D*G*G+E*H*H+F*G*H)/q;
    o[y*n+x]=0.5+0.5*Math.tanh(c*strength*0.02);      // 0.5 = flat, >0.5 concave, <0.5 convex
  }
  return o;
}
// Flow accumulation: priority-flood fill then D8 drainage area, log-compressed (analysis/flow).
export function flowField(inp,{gain=1}){
  const acc=d8Accumulation(priorityFloodFill(inp)),o=newField();
  for(let i=0;i<o.length;i++)o[i]=Math.log1p(acc[i]*gain);
  return normalize(o);
}
// Horizon-based ambient occlusion: occl = 1 - mean(cos^2 theta) over n dirs (analysis.horizon_ao).
export function occlusionField(inp,{radius=0.06,dirs=8}){
  const n=fieldW(),nh=fieldH(),o=newField(),maxD=Math.max(2,radius*n),hex=isHex();
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const h0=inp[y*n+x];let occ=0;
    // March in WORLD space. Stepping the grid indices instead walks sqrt(3)/2 world units per
    // row step while dividing by the index distance, so the horizon is scanned along a sheared
    // set of rays and the N-S ones come out short - the same 2/sqrt(3) family of error slopeOf
    // had. Convert the world sample point back to a row/column to read the field.
    const wx0=x+(hex?0.5*(y&1):0),wy0=y*(hex?HEX_ROW:1);
    for(let k=0;k<dirs;k++){
      const a=2*Math.PI*k/dirs,dx=Math.cos(a),dy=Math.sin(a);let mt=0,d=1;
      while(d<maxD){
        let sx,sy;
        if(hex){const row=Math.round((wy0+dy*d)/HEX_ROW);sy=row;sx=Math.round(wx0+dx*d-0.5*(row&1));}
        else{sx=Math.round(x+dx*d);sy=Math.round(y+dy*d);}
        const s=gAt(inp,sx,sy);
        mt=Math.max(mt,(s-h0)*n/d);d*=1.35;}
      const c=Math.cos(Math.atan(mt));occ+=c*c;
    }
    o[y*n+x]=1-occ/dirs;                                // 0 = open sky, 1 = fully enclosed
  }
  return normalize(o);
}
// Separable grayscale dilate/erode (square SE) -> morphological closing, for deposits.
function morph1D(inp,r,mx){
  const n=fieldW(),nh=fieldH(),t=newField(),o=newField();
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){let v=inp[y*n+x];
    for(let k=-r;k<=r;k++){const s=gAt(inp,x+k,y);v=mx?Math.max(v,s):Math.min(v,s);}t[y*n+x]=v;}
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){let v=t[y*n+x];
    for(let k=-r;k<=r;k++){const s=gAt(t,x,y+k);v=mx?Math.max(v,s):Math.min(v,s);}o[y*n+x]=v;}
  return o;
}
// Diagonal companion to morph1D. Composing the two builds an OCTAGONAL structuring element:
// with square radius r1 = sqrt(2)*rd the axis reach (r1+2rd) equals the diagonal reach
// (sqrt(2)*(r1+rd)), removing the square SE's C4 print-through (fills read wider along the
// diagonals than along the axes - the plus-shaped bias family of 09).
function morphDiag1D(inp,r,mx){
  const n=fieldW(),nh=fieldH(),t=newField(),o=newField();
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){let v=inp[y*n+x];
    for(let k=-r;k<=r;k++){const s=gAt(inp,x+k,y+k);v=mx?Math.max(v,s):Math.min(v,s);}t[y*n+x]=v;}
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){let v=t[y*n+x];
    for(let k=-r;k<=r;k++){const s=gAt(t,x+k,y-k);v=mx?Math.max(v,s):Math.min(v,s);}o[y*n+x]=v;}
  return o;
}
// Deposits / soil: closing(h) - h, the depth loose material piles into hollows (analysis.deposit_fill).
// The closing runs an octagonal SE (see morphDiag1D), and the fill depth is kept PHYSICAL:
// normalize() made a half-amplitude terrain produce the IDENTICAL deposit mask (measured ratio
// 1.000) - a HeightField laundered into a MaskField, 10's normalize defect verbatim. The mask is
// now depth-in-metres against refDepth (the fill depth that saturates the mask), so "how much
// soil" survives as information and two terrains stop reading identically.
export function depositsField(inp,{radius=3,refDepth=25}){
  const r=Math.max(1,Math.round(radius));
  // rd from the isotropy optimum r*(1-1/sqrt2), r1 as the RESIDUAL r-2rd - so the axis reach is
  // exactly r for every r and the slider stays monotone (a double round() of both radii made
  // r=1..5 bit-identical: three distinct outputs across a 1..10 slider, the same dead-control
  // defect class this tranche exists to remove). At r=1 this degenerates to the old square
  // closing exactly; small radii cannot be isotropic on a lattice and do not pretend to be.
  const rd=Math.round(r*(1-1/Math.SQRT2)),r1=Math.max(0,r-2*rd);
  // On hex the octagon is built from square and diagonal passes that do not exist as such: the
  // isotropic structuring element the lattice actually offers is the HEXAGON, r iterations of
  // the D6 one-ring. Iterating the ring is exact - a radius-r hexagonal SE is the r-fold
  // Minkowski sum of the one-ring - so dilate r times then erode r times is the closing.
  const oct=isHex()?(f,mx)=>{
    const nn=RES,nnh=fieldH();let a=f;
    for(let it=0;it<r;it++){const o2=newField();
      for(let y=0;y<nnh;y++)for(let x=0;x<nn;x++){
        const nb=hexNb(y);let v=a[y*nn+x];
        for(let k=0;k<6;k++){const xx=x+nb[k][0],yy=y+nb[k][1];
          if(xx<0||yy<0||xx>=nn||yy>=nnh)continue;
          const s=a[yy*nn+xx];v=mx?Math.max(v,s):Math.min(v,s);}
        o2[y*nn+x]=v;}
      a=o2;}
    return a;
  }:(f,mx)=>{const t=r1>0?morph1D(f,r1,mx):f;return rd>0?morphDiag1D(t,rd,mx):t;};
  const closed=oct(oct(inp,true),false);
  const o=newField(),toM=terrainDef.height/Math.max(1e-6,refDepth);
  for(let i=0;i<o.length;i++)o[i]=Math.min(Math.max(closed[i]-inp[i],0)*toM,1);
  return o;
}
// Peaks: prominence above the local mean (h - blur(h), positive part).
export function peaksField(inp,{radius=4}){
  const b=blurField(inp,{radius:Math.max(1,Math.round(radius))}),o=newField();
  for(let i=0;i<o.length;i++)o[i]=Math.max(inp[i]-b[i],0);
  return normalize(o);
}
// Wear: convex, steep ground — the exposed edges erosion strips first (convexity x slope).
export function wearField(inp,{strength=1}){
  const cur=curvatureField(inp,{kind:"mean",strength:1}),sl=normalize(slopeOf(inp)),o=newField();
  for(let i=0;i<o.length;i++)o[i]=Math.max(0.5-cur[i],0)*2*sl[i]*strength;
  return normalize(o);
}
// Texture: Gaea's composite colour driver — slope + soil(deposits) + flow mixed into one mask.
export function textureField(inp,{slopeW=0.5,soilW=0.3,flowW=0.2}){
  const sl=normalize(slopeOf(inp)),so=depositsField(inp,{radius:3}),fl=flowField(inp,{gain:1});
  const o=newField(),tot=(slopeW+soilW+flowW)||1;
  for(let i=0;i<o.length;i++)o[i]=(sl[i]*slopeW+so[i]*soilW+fl[i]*flowW)/tot;
  return normalize(o);
}
export function slopeSelect(inp,{lo=0.1,hi=0.6,falloff=0.1}){
  const sl=normalize(slopeOf(inp));const o=newField();
  for(let i=0;i<o.length;i++){const v=sl[i];
    const a=smooth(clamp((v-(lo-falloff))/(falloff+1e-4),0,1));
    const b=smooth(clamp(((hi+falloff)-v)/(falloff+1e-4),0,1));o[i]=a*b;}
  return o;
}
export function heightSelect(inp,{lo=0.3,hi=0.7,falloff=0.12}){
  const o=newField();
  for(let i=0;i<o.length;i++){const v=inp[i];
    const a=smooth(clamp((v-(lo-falloff))/(falloff+1e-4),0,1));
    const b=smooth(clamp(((hi+falloff)-v)/(falloff+1e-4),0,1));o[i]=a*b;}
  return o;
}

/* ------------------------------------------------------- erosion ------ */
// Thermal (talus) erosion — material above the repose angle slides to lower neighbours.
/* PLATE TECTONICS -- Voronoi plates as the structural skeleton of a range.
   Ported from reference-impl/tectonics.py `plate_uplift` (chapter 02). Voronoi cells are the classic
   model for plate/block structure, but raw Voronoi edges are dead straight and that is the tell, so
   the coordinates are DOMAIN-WARPED before assignment and the sites are Lloyd-relaxed so plates come
   out evenly sized rather than slivered.

   Each boundary is classified from the relative velocity of the two plates: continent-continent
   collision, subduction (one oceanic), island arc (both oceanic), rift (diverging, so subsidence),
   or transform (shear-dominated, ~no uplift). The boundary uplift is then diffused INLAND over the
   orogen width, because a mountain belt is a broad welt, not a line.

   Its purpose is to drive Stream power's Uplift input: this gives the structure, the rivers give the
   topography. F-tier -- a plausible planar plate sketch, not plate physics. */
export function plateUplift(p){
  const n=fieldW(),nh=fieldH(),N=n*nh,P=Math.max(3,Math.round(p.plates));
  let rs=((p.seed|0)*2654435761)>>>0;
  const rnd=()=>{rs=(Math.imul(rs^(rs>>>15),2246822519)+374761393)>>>0;return rs/4294967296;};
  const gauss=()=>{let u=0,v=0;while(u<=1e-9)u=rnd();v=rnd();
    return Math.sqrt(-2*Math.log(u))*Math.cos(6.28318530718*v);};
  const cx=[],cy=[];for(let k=0;k<P;k++){cx.push(rnd()*n);cy.push(rnd()*n);}
  const nearest=(x,y)=>{let bd=Infinity,bi=0;
    for(let k=0;k<P;k++){const d=(x-cx[k])**2+(y-cy[k])**2;if(d<bd){bd=d;bi=k;}}return bi;};
  for(let it=0;it<2;it++){                          // Lloyd relaxation -> evenly sized plates
    const sx=new Float64Array(P),sy=new Float64Array(P),c=new Float64Array(P);
    for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const k=nearest(x,y);sx[k]+=x;sy[k]+=y;c[k]++;}
    for(let k=0;k<P;k++)if(c[k]>0){cx[k]=sx[k]/c[k];cy[k]=sy[k]/c[k];}
  }
  const warp=p.warp*n*0.06;
  const pid=new Int32Array(N);
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){        // assign on WARPED coordinates
    // Warp FREQUENCY matters more than amplitude here. The reference uses warp_freq 0.045, i.e. ~8.6
    // cycles across a 192 tile; at 3.2 cycles the noise is so smooth it translates whole boundaries
    // rigidly instead of bending them, and they stay recognisably straight. Measured, the low
    // frequency relocated only 17% of belt cells across the entire warp range.
    const wf=8.6;
    const wx=x+warp*fbm2(x/n*wf,y/n*wf,p.seed,4);
    const wy=y+warp*fbm2(x/n*wf+5.3,y/n*wf+1.7,p.seed+7,4);
    pid[y*n+x]=nearest(wx,wy);
  }
  const vx=[],vy=[],isOcean=[];
  for(let k=0;k<P;k++){vx.push(gauss());vy.push(gauss());isOcean.push(rnd()<p.ocean);}
  const boundary=newField(0);
  const NB=[[-1,0],[1,0],[0,-1],[0,1]];
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const i=y*n+x,a=pid[i];
    for(const d of NB){
      const xx=Math.min(n-1,Math.max(0,x+d[0])),yy=Math.min(n-1,Math.max(0,y+d[1]));
      const b=pid[yy*n+xx];if(b===a)continue;
      let nx=cx[b]-cx[a],ny=cy[b]-cy[a];const nl=Math.hypot(nx,ny)+1e-9;nx/=nl;ny/=nl;
      const rvx=vx[a]-vx[b],rvy=vy[a]-vy[b];
      const conv=rvx*nx+rvy*ny, shear=Math.abs(rvx*ny-rvy*nx);
      if(Math.abs(conv)<shear)continue;             // transform boundary: shear, ~no uplift
      const oa=isOcean[a],ob=isOcean[b];
      let val=0;
      if(conv>0) val=(!oa&&!ob)?1.0*conv                       // continent-continent collision
                 :(oa!==ob)?0.7*conv                            // subduction, one oceanic
                 :0.45*conv;                                    // island arc, both oceanic
      else       val=0.6*conv;                                  // rift: conv<0 -> subsidence
      boundary[i]+=val;
    }
  }
  for(let i=0;i<N;i++)boundary[i]*=0.5;             // each boundary counted from both sides
  const orogen=blurField(boundary,{radius:Math.max(2,Math.round(p.orogen*n*0.16))});
  if(p.output==="orogen"){
    // ZERO MUST MEAN ZERO in an uplift field. Rifts are divergent, so they contribute NEGATIVE
    // boundary values; normalising the result maps that negative floor to 0 and pushes "no uplift"
    // up to the middle of the range. Measured, that put the 25th, 50th and 75th percentiles all at
    // 0.377 -- a constant uplift over most of the tile, which is why everything came out mountainous
    // rather than just the belts. Clamp subsidence away and scale by the peak instead.
    const o=newField();let mx=0;
    for(let i=0;i<N;i++)if(orogen[i]>mx)mx=orogen[i];
    // A CONTINENT RISES AS A WHOLE. Uplift only along boundary belts leaves the rest of the tile at
    // base level, so the carved result was 90% dead flat with blades where the belts were -- slope
    // median 0 and p90 0.47 against a real SRTM tile's 2.45 and 9.26. The reference returns
    // base[pid] + amplitude*orogen with a continental base for exactly this reason; `land` restores
    // it, so continental plates rise broadly and orogens rise faster on top.
    // The continental base is a per-plate constant, so used raw it steps vertically at every margin
    // and the carved result grows cliff walls along the coastlines. Real margins are shelves; blur
    // the land mask over the same scale as the orogen so the transition is a slope.
    const land=newField(0);
    for(let i=0;i<N;i++)land[i]=isOcean[pid[i]]?0:1;
    const shelf=blurField(land,{radius:Math.max(2,Math.round(p.orogen*n*0.10))});
    if(mx>0)for(let i=0;i<N;i++){
      const base=p.land*shelf[i];
      o[i]=clamp(base+(1-base)*Math.max(orogen[i],0)/mx,0,1);
    }
    return o;
  }
  const o=newField();                               // full tectonic elevation: plate base + orogen
  for(let i=0;i<N;i++)o[i]=(isOcean[pid[i]]?0.0:0.55)+2.2*orogen[i];
  return normalize(o);
}

/* STREAM-POWER FLUVIAL INCISION --  dh/dt = U - K*A^m*S^n,  n = 1.
   Braun & Willett 2013 O(N) implicit solver, ported from reference-impl/erosion_streampower.py
   (P-tier there, cross-validated against Landlab).

   This is the process that ORGANISES a landscape rather than decorating one. Drainage area A is what
   makes valleys join into a tree and deepen downstream, so the ridges emerge as what is LEFT between
   them. Droplet erosion cuts local gullies; this builds topography. A mountain is not an object you
   add, it is the residue after a river network incises high ground -- which is why every attempt to
   author the summit directly produced a children's-drawing triangle.

   Nodes are solved receiver-before-donor so the implicit update is one linear solve per node, which
   is why n=1 is unconditionally stable. Domain edges are held at base level: without a fixed outlet
   there is nothing to incise toward. At steady state S ~ A^(-m/n) -- a straight line of slope -m on
   a log-log slope/area plot, which is the decisive verification (see _verify_streampower.js). */
function spReceivers(g,cellsize){
  const n=fieldW(),nh=fieldH(),N=n*nh,rec=new Int32Array(N).fill(-1),dist=new Float32Array(N).fill(cellsize);
  if(isHex()){
    // D6 steepest descent: six candidates, ONE distance, no sqrt(2) case. Run with the square D8
    // table this measured 40.4% of interior receivers landing on cells that are not lattice
    // neighbours at all (max step sqrt(3) - two rings out, with an undrained cell in between)
    // and 54.1% reporting dist=sqrt(2)*cellsize, a distance no pair of hex cells has. Note the
    // square table is a SUPERSET of the hex one-ring, so pure connectivity never showed this:
    // flow still reached the edge, it just took steps the lattice does not have.
    for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
      const i=y*n+x,nb=hexNb(y);let best=0,bi=-1;
      for(let k=0;k<6;k++){const xx=x+nb[k][0],yy=y+nb[k][1];
        if(xx<0||yy<0||xx>=n||yy>=nh)continue;
        const ni=yy*n+xx,sl=(g[i]-g[ni])/cellsize;
        if(sl>best){best=sl;bi=ni;}}
      rec[i]=bi;dist[i]=cellsize;}
    return {rec,dist};
  }
  const nb=[[-1,0,1],[1,0,1],[0,-1,1],[0,1,1],
            [-1,-1,Math.SQRT2],[1,1,Math.SQRT2],[-1,1,Math.SQRT2],[1,-1,Math.SQRT2]];
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const i=y*n+x;let best=0,bi=-1,bd=cellsize;
    for(const d of nb){const xx=x+d[0],yy=y+d[1];if(xx<0||yy<0||xx>=n||yy>=nh)continue;
      const ni=yy*n+xx,sl=(g[i]-g[ni])/(d[2]*cellsize);
      if(sl>best){best=sl;bi=ni;bd=d[2]*cellsize;}}
    rec[i]=bi;dist[i]=bd;}
  return {rec,dist};
}
// Takes the PHYSICAL quantities K*dt and U*dt rather than UI sliders, so the solver can be tested as
// the equation it claims to implement -- the node maps its 0..1 controls onto these. Conflating the
// two hid a real failure: driven by slider-scaled values the slope-area exponent wandered between
// -0.28 and +0.02 instead of settling at -m, because that regime never reaches steady state.
// `Udt` may be a scalar OR a FIELD, as in the reference. A spatially varying uplift is the whole
// point of the node: feed a broad high region in and the rivers carve it into topography, so summits
// and ridges come out as RESIDUE between the valleys rather than being authored. That is the
// difference between a mountain and a drawing of one.
// Ddt is HILLSLOPE DIFFUSION, and it is not optional decoration. The full detachment-limited
// landscape equation is dh/dt = U - K*A^m*S^n + D*grad^2(h): stream power incises channels, and
// diffusion relaxes the interfluves between them. Run without it, ridges sharpen without bound and
// the result is a field of razor blades -- which is exactly what the first uplift-driven render
// produced. Diffusion is what gives hillslopes a length and valleys a width.
// It has to run INSIDE the loop; a single relaxation pass afterwards cannot undo ridges that
// sharpened for 200 iterations. reference-impl has hillslope_diffuse but never couples the two,
// which is a gap there as well.
export function streamPowerErode(inp,{Kdt=0.5,Udt=0,m=0.5,iters=25,uplift=null,Ddt=0}){
  const n=fieldW(),nh=fieldH(),N=n*nh;
  let h=inp.slice();
  const isEdge=new Uint8Array(N);
  for(let x=0;x<n;x++){isEdge[x]=1;isEdge[(nh-1)*n+x]=1;}
  for(let y=0;y<nh;y++){isEdge[y*n]=1;isEdge[y*n+n-1]=1;}
  for(let i=0;i<N;i++)if(isEdge[i])h[i]=0;
  const A=new Float32Array(N);
  for(let it=0;it<iters;it++){
    if(uplift){for(let i=0;i<N;i++)if(!isEdge[i])h[i]+=Udt*uplift[i];}
    else if(Udt){for(let i=0;i<N;i++)if(!isEdge[i])h[i]+=Udt;}
    const hf=priorityFloodFill(h,0);   // pure max-fill: see priorityFloodFill - epsilon breaks the implicit solve's steady state
    const {rec,dist}=spReceivers(hf,1);
    const order=Array.from({length:N},(_,i)=>i).sort((a,b)=>hf[b]-hf[a]);   // high -> low
    A.fill(1);
    for(const i of order)if(rec[i]>=0)A[rec[i]]+=A[i];
    for(let k=N-1;k>=0;k--){                              // low -> high: receiver solved first
      const i=order[k];
      if(isEdge[i]||rec[i]<0)continue;
      const C=Kdt*Math.pow(A[i],m)/dist[i];
      h[i]=(h[i]+C*h[rec[i]])/(1+C);
      if(h[i]<h[rec[i]])h[i]=h[rec[i]];                   // never incise below your own receiver
    }
    if(Ddt>0){
      // THE LAPLACIAN CONSTANT IS NOT 1/s^2 ON HEX. Summing the six equidistant neighbours and
      // Taylor-expanding gives sum(h_k - h_i) = (3s^2/2)*grad^2(h), because sum(cos^2) over six
      // directions 60 degrees apart is 3, not 2 as it is over four at 90. So the isotropic operator
      // is (2/(3s^2))*sum over SIX - carry the square 1/s^2 across and diffusivity comes out 1.5x
      // too high, with nothing to see: relaxed hillslopes look like relaxed hillslopes.
      //
      // What was actually here was worse than the 1.5x, and the arithmetic that shows it is short.
      // The four square offsets (x+-1,y) and (x,y+-1) ARE lattice neighbours under odd-r - but four
      // of six, and the missing pair is chosen by row parity. Their world directions are
      //     even rows  0, 180,  60, 300      offsets sum to (+1, 0)
      //     odd rows   0, 180, 120, 240      offsets sum to (-1, 0)
      // A Laplacian's offsets must sum to ZERO; a subset whose offsets do not is a first-derivative
      // operator wearing a Laplacian's shape. This one ADVECTS - material pushed +x on even rows and
      // -x on odd rows, a per-row zig-zag shear riding on top of the smoothing.
      //
      // Measured on an impulse (_verify_hillslope_isotropy, second-moment tensor, world units):
      //     square stencil on both   square 1.0000   hex 1.1595
      //     D6 stencil on hex        square 1.0000   hex 1.0000
      // Note the leading-order tensor argument alone predicts 1.291 for the four-offset subset, and
      // the measurement says 1.1595. The gap is the broken first-order term interacting with the
      // parity flip, which that argument does not model. The MEASUREMENT is the endpoint the gate is
      // armed against; the derivation explains the direction, not the magnitude.
      // Explicit 5-point Laplacian, SUBSTEPPED: dt <= ~0.25*cell^2/D or it blows up, so a dose
      // above the stability bound splits into stable substeps instead of being silently clamped
      // (the clamp under-diffused exactly when Res Lock scales the dose with the grid). The
      // substep bound is 1/6, NOT 0.24: c in (0.125, 0.25) is the RINGING corner of the
      // stability region - Nyquist amplification |1-8c| approaches 1 with a sign flip each pass,
      // and a 0.24 bound made grid-scale damping a sawtooth in the dose (measured: channel-head
      // count 627 -> 335 crossing Ddt 0.24 -> 0.25). At c <= 1/6 the amplification is <= 1/3.
      // Ddt <= 0.24 stays ONE substep with c = Ddt - byte-identical to the old clamp, the k=1
      // pin; the single discontinuity at the legacy boundary is the price of that pin. Scratch
      // buffer hoisted: a per-substep slice() was ~385 GB of allocation churn at 4096 square.
      const sub=Ddt<=0.24?1:Math.ceil(Ddt*6),c=Ddt/sub;
      const t=new Float32Array(h.length);
      // THE STENCIL IS LATTICE-DEPENDENT, and the square one was running on hex. See hexLap below
      // for what that cost. The substep bound is shared: on hex the amplification factor is
      // 1+c*(2/3)*(S(k)-6) with S(k) >= -3 at the K point, so the worst mode damps by 1-6c - the
      // same |1-8c|-style bound the square path uses, and strictly gentler, so reusing the square
      // substep rule is conservative on hex rather than merely convenient.
      const hex=isHex(),oE=[-1,1,-1-n,-n,-1+n,n],oO=[-1,1,-n,1-n,n,1+n];
      for(let s2=0;s2<sub;s2++){
        t.set(h);
        if(hex){
          for(let y=1;y<nh-1;y++){const o=(y&1)?oO:oE;
            for(let x=1;x<n-1;x++){const i=y*n+x;
              let a=0;for(let k=0;k<6;k++)a+=t[i+o[k]]-t[i];
              h[i]=t[i]+c*(2/3)*a;}}
        }else{
          for(let y=1;y<nh-1;y++)for(let x=1;x<n-1;x++){const i=y*n+x;
            h[i]=t[i]+c*(-4*t[i]+t[i-1]+t[i+1]+t[i-n]+t[i+n]);}
        }
      }
    }
    for(let i=0;i<N;i++)if(isEdge[i])h[i]=0;
  }
  return h;
}
// D6 thermal for the hex lattice (26): six equidistant edge-neighbours, ONE distance, ONE
// threshold - the sqrt(2) diagonal split that thermalErode below must distance-correct simply
// does not exist here, which is the point. Offsets depend on row parity (odd-r); the excess
// scan, stable-pair budget and proportional distribution are thermalErode's own, unchanged.
function thermalErodeHex(inp,{talus=0.012,iters=30,rate=0.5}){
  const n=fieldW(),nh=fieldH();let h=inp.slice();
  const nbEven=[[-1,0],[1,0],[-1,-1],[0,-1],[-1,1],[0,1]];
  const nbOdd =[[-1,0],[1,0],[0,-1],[1,-1],[0,1],[1,1]];
  for(let it=0;it<iters;it++){
    const dh=new Float32Array(n*nh);
    for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
      const nb=(y&1)?nbOdd:nbEven,c=h[y*n+x];let maxd=0,sum=0;const diffs=[];
      for(const[dx,dy]of nb){const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=n||yy>=nh){diffs.push(0);continue;}
        const d=c-h[yy*n+xx];const e=d-talus;if(e>0){diffs.push(e);sum+=e;if(e>maxd)maxd=e;}else diffs.push(0);}
      if(sum<=0)continue;
      const move=rate*maxd*0.5;let k=0;
      for(const[dx,dy]of nb){const xx=x+dx,yy=y+dy;if(diffs[k]>0){
        const q=Math.min(move*diffs[k]/sum,diffs[k]*0.5);
        dh[y*n+x]-=q;dh[yy*n+xx]+=q;}k++;}
    }
    for(let i=0;i<h.length;i++)h[i]+=dh[i];
  }
  return h;
}
// One dispatcher so no caller can silently keep the square kernel on a hex build. On square this
// is exactly thermalErode, so the digest-pinned mountain/peak weathering is byte-identical.
export const thermalOn=(inp,opt)=>(isHex()?thermalErodeHex:thermalErode)(inp,opt);
function thermalErode(inp,{talus=0.012,iters=30,rate=0.5}){
  const n=fieldW(),nh=fieldH();let h=inp.slice();
  // 8-neighbour offsets with their DISTANCE (diagonals are sqrt(2) away). The repose threshold must
  // scale with distance or diagonals relax at a shallower true angle — the plus-shaped grid artefact.
  // Mirrors reference-impl/erosion_thermal.py's `distance_correct`.
  const nb=[[-1,0,1],[1,0,1],[0,-1,1],[0,1,1],[-1,-1,Math.SQRT2],[1,1,Math.SQRT2],[-1,1,Math.SQRT2],[1,-1,Math.SQRT2]];
  for(let it=0;it<iters;it++){
    const dh=new Float32Array(n*nh);
    for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
      const c=h[y*n+x];let maxd=0,sum=0;const diffs=[];
      for(const[dx,dy,dist]of nb){const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=n||yy>=nh){diffs.push(0);continue;}
        const d=c-h[yy*n+xx];const e=d-talus*dist;if(e>0){diffs.push(e);sum+=e;if(e>maxd)maxd=e;}else diffs.push(0);}
      if(sum<=0)continue;
      const move=rate*maxd*0.5;let k=0;                 // /2 keeps the steepest pair stable
      for(const[dx,dy]of nb){const xx=x+dx,yy=y+dy;if(diffs[k]>0){
        const q=Math.min(move*diffs[k]/sum,diffs[k]*0.5); // never invert an individual pair
        dh[y*n+x]-=q;dh[yy*n+xx]+=q;}k++;}
    }
    for(let i=0;i<h.length;i++)h[i]+=dh[i];
  }
  return h;
}
// Terrain georeferencing used by climate nodes and the viewport compass.
// `north` is clockwise from the top edge of the heightfield; the equator lies south of a
// northern-hemisphere map and north of a southern-hemisphere map.
function terrainOrientation(def=terrainDef){
  const a=(def.north==null?0:def.north)*Math.PI/180;
  const lat=def.latitude==null?46:def.latitude,north=[Math.sin(a),-Math.cos(a)],hemi=lat<0?-1:lat>0?1:0;
  return{north,equator:hemi>0?[-north[0],-north[1]]:hemi<0?[north[0],north[1]]:[0,0],hemisphere:hemi};
}
function blurScalarField(src,n,radius,passes=2){const nh=latticeRows(n);
  radius=Math.max(0,radius|0);if(!radius)return src.slice();
  let a=src.slice(),b=new Float32Array(n*nh),span=radius*2+1;
  for(let pass=0;pass<passes;pass++){
    for(let y=0;y<nh;y++){let sum=0;for(let k=-radius;k<=radius;k++)sum+=a[y*n+clamp(k,0,n-1)];
      for(let x=0;x<n;x++){b[y*n+x]=sum/span;sum+=a[y*n+clamp(x+radius+1,0,n-1)]-a[y*n+clamp(x-radius,0,n-1)];}}
    [a,b]=[b,a];
    for(let x=0;x<n;x++){let sum=0;for(let k=-radius;k<=radius;k++)sum+=a[clamp(k,0,nh-1)*n+x];
      for(let y=0;y<nh;y++){b[y*n+x]=sum/span;sum+=a[clamp(y+radius+1,0,nh-1)*n+x]-a[clamp(y-radius,0,nh-1)*n+x];}}
    [a,b]=[b,a];
  }
  return a;
}
// Spatial solar exposure for climate—not the viewport's cosmetic shadow. A representative
// equator-side sun supplies incidence; a logarithmic horizon march detects distant blockers, and a
// short separable diffusion produces penumbra + diffuse sky exposure without temporal accumulation.
// Scalar buffers stay graph-friendly [0,1], while their physical meaning travels beside the
// Float32Array. The wider interval includes magma/lava temperatures without sacrificing useful
// precision around freezing (Float32 still resolves far below 0.01 °C here).
export const TEMP_MIN_C=-100,TEMP_MAX_C=1400,FIELD_META=new WeakMap();
export const encodeTemperatureC=c=>clamp((c-TEMP_MIN_C)/(TEMP_MAX_C-TEMP_MIN_C),0,1);
const decodeTemperatureField=f=>{
  if(!f)return null;const out=new Float32Array(f.length),span=TEMP_MAX_C-TEMP_MIN_C;
  for(let i=0;i<f.length;i++)out[i]=TEMP_MIN_C+clamp(f[i],0,1)*span;
  return out;
};
export function tagTemperatureField(field,temperatureC=null,extras={}){
  if(!field)return field;
  FIELD_META.set(field,{kind:"temperature",unit:"°C",minC:TEMP_MIN_C,maxC:TEMP_MAX_C,
    temperatureC,solarShadow:extras.solarShadow||null,solarExposure:extras.solarExposure||null,
    lapseRate:extras.lapseRate==null?null:extras.lapseRate,heightField:extras.heightField||null});
  return field;
}
export const fieldMetadata=field=>field&&FIELD_META.get(field)||null;
export function temperatureCFromField(field){
  const meta=fieldMetadata(field);if(!meta||meta.kind!=="temperature")return null;
  if(!meta.temperatureC)meta.temperatureC=decodeTemperatureField(field);
  return meta.temperatureC;
}
// Physical field kinds survive only operations whose maths preserves their units. This is an
// explicit node contract: a Levels/Invert/Add applied to encoded Celsius is not temperature merely
// because Temperature happened to be input A.
function propagateFieldMetadata(field,inputs,def){
  if(!field||fieldMetadata(field)||!inputs||!inputs[0])return field;
  const source=fieldMetadata(inputs[0]);
  if(!source||source.kind!=="temperature")return field;
  let preserves=def.fieldSemantics==="preserve-primary";
  if(def.fieldSemantics==="temperature-pair")
    preserves=!!(inputs[1]&&fieldMetadata(inputs[1])&&fieldMetadata(inputs[1]).kind==="temperature");
  if(preserves)tagTemperatureField(field,null,{solarShadow:source.solarShadow,solarExposure:source.solarExposure,
    lapseRate:source.lapseRate,heightField:source.heightField});
  return field;
}
function metricHeightField(inp,n,def){const nh=latticeRows(n);
  // EXACTLY the viewport's frame: autolevel to the full [datum, datum+height] span. The viewport
  // unconditionally renormalises whatever field it displays (see the `(field[i]-mn)/d` fill in
  // updateViewport), so "Relief height" is the vertical span OF WHAT IS DRAWN, the climate readout
  // and fallback temperature use that normalised height, and the climate stack must live in the
  // same frame or the snowline sits at elevations the user cannot see.
  // A CORRECTION RECORDED SO IT IS NOT RE-DISCOVERED: this function was briefly changed to the
  // "physical" contract (datum + f*height, no renormalisation) on the theory that the renderer
  // used that transform. It does not - two separate investigations mis-read the renderer by
  // looking at `hgt*height` consumers downstream of an ALREADY-normalised hgt and missing the
  // normalisation at fill time. That change made the solver simulate a world 2.12x FLATTER than
  // drawn - the exact inversion of the defect it claimed to fix. If a field-value-is-absolute
  // elevation contract is ever wanted, the viewport autolevel must change in the same commit,
  // with the display consequences for non-normalised graphs accepted deliberately.
  const N=n*nh,[mn,mx]=fieldRange(inp),range=mx-mn||1,out=new Float32Array(N),heightM=def.height||2600;
  const datum=def.baseElevation||0;
  for(let i=0;i<N;i++)out[i]=datum+(inp[i]-mn)/range*heightM;
  return out;
}
function climateSolarExposure(baseM,n,def,options={}){const nh=latticeRows(n);
  const N=n*nh,orient=terrainOrientation(def),eq=orient.equator;
  const elevation=clamp(def.solarElevation==null?45:def.solarElevation,3,90)*Math.PI/180;
  const sinEl=Math.sin(elevation),cosEl=Math.cos(elevation),tanEl=Math.tan(elevation);
  const cell=(def.scale||5000)/n,direct=new Float32Array(N),visibility=new Float32Array(N);
  const suppliedVisibility=options.visibility&&options.visibility.length===N?options.visibility:null;
  const distances=[];if(!suppliedVisibility&&!options.skipHorizon&&orient.hemisphere!==0&&cosEl>.01){
    const reachM=options.reachM==null?(def.scale||5000)*.55:options.reachM;
    const maxD=Math.max(2,Math.min(n*.95,reachM/cell)),steps=Math.min(32,Math.max(12,Math.round(Math.sqrt(n)*1.35)));
    let prev=0;for(let k=1;k<=steps;k++){const d=Math.max(1,Math.round(Math.exp(Math.log(maxD+1)*k/steps)-1));
      if(d!==prev){distances.push(d);prev=d;}}
  }
  const sample=(x,y)=>{
    x=clamp(x,0,n-1.001);y=clamp(y,0,nh-1.001);
    const x0=x|0,y0=y|0,fx=x-x0,fy=y-y0,i=y0*n+x0;
    return lerp(lerp(baseM[i],baseM[i+1],fx),lerp(baseM[i+n],baseM[i+n+1],fx),fy);
  };
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const i=y*n+x,x0=Math.max(0,x-1),x1=Math.min(n-1,x+1),y0=Math.max(0,y-1),y1=Math.min(nh-1,y+1);
    const dzdx=(baseM[y*n+x1]-baseM[y*n+x0])/Math.max((x1-x0)*cell,1e-6);
    const dzdy=(baseM[y1*n+x]-baseM[y0*n+x])/Math.max((y1-y0)*cell,1e-6);
    const inv=1/Math.hypot(dzdx,1,dzdy);
    const incidence=Math.max(0,(-dzdx*eq[0]*cosEl+sinEl-dzdy*eq[1]*cosEl)*inv);
    direct[i]=clamp(incidence/Math.max(sinEl,.12),0,1);
    if(suppliedVisibility)visibility[i]=clamp(suppliedVisibility[i],0,1);
    else{
      let visible=1;
      for(const dc of distances){
        const sx=x+eq[0]*dc,sy=y+eq[1]*dc;
        if(sx<0||sy<0||sx>n-1||sy>nh-1)break;
        if(sample(sx,sy)>baseM[i]+dc*cell*tanEl+.25){visible=0;break;}
      }
      visibility[i]=visible;
    }
  }
  const softness=options.softness==null?1:options.softness;
  const softShadow=suppliedVisibility?visibility:
    blurScalarField(visibility,n,Math.min(12,Math.max(0,Math.round(n/192*2*softness))),2);
  const exposure=new Float32Array(N);
  for(let i=0;i<N;i++)exposure[i]=clamp(.12+.88*direct[i]*(.08+.92*softShadow[i]),0,1);
  return{exposure,direct,shadow:softShadow,sunElevationDeg:elevation*180/Math.PI};
}
export function evaluateSunShadowMap(inp,p={}){
  const full=RES,preview=BUILD_QUALITY==="interactive"?Math.min(full,512):full;
  const h=preview===full?inp:resampleField(inp,full,preview);
  const baseM=metricHeightField(h,preview,terrainDef);
  const solar=climateSolarExposure(baseM,preview,terrainDef,{reachM:p.reach,softness:p.softness});
  if(preview===full)return{heightM:baseM,solarExposure:solar.exposure,solarShadow:solar.shadow};
  return{heightM:resampleField(baseM,preview,full),solarExposure:resampleField(solar.exposure,preview,full),
    solarShadow:resampleField(solar.shadow,preview,full)};
}
export function evaluateTemperatureMap(inp,p={},shadowInput=null){
  const full=RES,preview=BUILD_QUALITY==="interactive"?Math.min(full,512):full;
  const h=preview===full?inp:resampleField(inp,full,preview);
  const supplied=shadowInput?(preview===full?shadowInput:resampleField(shadowInput,full,preview)):null;
  const baseM=metricHeightField(h,preview,terrainDef);
  // No visibility edge means open sky. Terrain occlusion is an explicit Sun Shadow graph input;
  // slope/aspect incidence remains part of the base temperature model.
  const solar=climateSolarExposure(baseM,preview,terrainDef,{visibility:supplied,skipHorizon:!supplied});
  const rawC=new Float32Array(preview*latticeRows(preview)),encoded=new Float32Array(preview*latticeRows(preview));
  const warming=p.warming==null?5:p.warming;
  const seaTemp=p.seaTemp==null?(terrainDef.seaTemp==null?6:terrainDef.seaTemp):p.seaTemp;
  const lapse=p.lapseRate==null?(terrainDef.lapseRate==null?6.5:terrainDef.lapseRate):p.lapseRate;
  for(let i=0;i<rawC.length;i++){
    rawC[i]=seaTemp-lapse*(baseM[i]/1000)+warming*solar.exposure[i];
    encoded[i]=encodeTemperatureC(rawC[i]);
  }
  if(preview===full)return{heightM:baseM,temperatureC:rawC,encoded,solarExposure:solar.exposure,solarShadow:solar.shadow};
  return{
    heightM:resampleField(baseM,preview,full),
    temperatureC:resampleField(rawC,preview,full),
    encoded:resampleField(encoded,preview,full),
    solarExposure:resampleField(solar.exposure,preview,full),
    solarShadow:resampleField(solar.shadow,preview,full)
  };
}
// A Wind field is physically two horizontal velocity components in m/s. The scalar carrier is
// only a graph thumbnail / generic-mask view of speed; the vector contract travels in FIELD_META,
// exactly as physical Celsius travels beside Temperature's encoded scalar field. "Wind from"
// bearings are map-relative: 0° arrives from map-top and therefore blows toward +row.
export const WIND_MAX_MPS=80;
export function windBearingVector(direction){
  const r=((direction||0)%360+360)%360*Math.PI/180;
  return[-Math.sin(r),Math.cos(r)];
}
export function tagWindField(field,u,v,speed,extras={}){
  if(!field)return field;
  FIELD_META.set(field,{kind:"wind",unit:"m/s",u,v,speed,heightField:extras.heightField||null,
    baseDirection:extras.baseDirection==null?null:extras.baseDirection,
    baseSpeed:extras.baseSpeed==null?null:extras.baseSpeed,
    divergenceRmsBefore:extras.divergenceRmsBefore==null?null:extras.divergenceRmsBefore,
    divergenceRmsAfter:extras.divergenceRmsAfter==null?null:extras.divergenceRmsAfter});
  return field;
}
export function windVectorFromField(field){
  const m=fieldMetadata(field);
  return m&&m.kind==="wind"&&m.u&&m.v&&m.speed?m:null;
}
export function windDivergenceRms(u,v,n,cell){const nh=latticeRows(n);
  if(!u||!v||n<3)return 0;
  let sum=0,count=0;
  for(let y=1;y<nh-1;y++)for(let x=1;x<n-1;x++){
    const i=y*n+x,d=(u[i+1]-u[i-1]+v[i+n]-v[i-n])/(2*cell);
    sum+=d*d;count++;
  }
  return Math.sqrt(sum/Math.max(1,count));
}
// Bounded-domain Helmholtz-Hodge projection (Sherman 1978 / MATHEW family): solve
// laplacian(lambda)=div(u0) with lambda=0 at the open tile edge, then subtract grad(lambda) -
// on an EXACT-ADJOINT stencil pair: FORWARD-difference divergence, compact 5-point Laplacian,
// BACKWARD-difference gradient, whose composition IS that Laplacian, so the projection cancels
// exactly up to solver residual. The first version paired central div/grad with the compact
// Laplacian: that pair's symbol is cos^2(theta/2) - ZERO at Nyquist - so grid-scale divergence
// was invisible to the solve, which CONVERGED at a ~2x reduction while the comment blamed the
// iteration budget (cross-model review, measured at 200x iterations: under 2% change; the
// reference-impl uses one spectral operator for div/Laplacian/grad for exactly this reason and
// gates after < 0.05*before). A coarse-grid pre-solve (4x block-mean restriction, solved deep,
// prolonged as the initial guess) carries the long-wavelength part a bounded fine sweep cannot.
export function projectWindMassConsistent(u0,v0,n,cell,iterations=56){const nh=latticeRows(n);
  const N=n*nh,rhs=new Float32Array(N);
  for(let y=0;y<nh-1;y++)for(let x=0;x<n-1;x++){
    const i=y*n+x;rhs[i]=(u0[i+1]-u0[i]+v0[i+n]-v0[i])/cell;
  }
  const jacobi=(lam0,rhs2,m,cellM,iters,mh)=>{
    const rows=mh||latticeRows(m);
    let src=lam0,dst=new Float32Array(m*rows);const c2=cellM*cellM;
    for(let it=0;it<iters;it++){
      for(let y=1;y<rows-1;y++)for(let x=1;x<m-1;x++){
        const i=y*m+x;dst[i]=(src[i-1]+src[i+1]+src[i-m]+src[i+m]-rhs2[i]*c2)*.25;
      }
      const q=src;src=dst;dst=q;
    }
    return src;
  };
  // Two V-cycles: coarse-solve the RESIDUAL (4x block-mean restriction, deep cheap Jacobi),
  // prolong the correction, then a fine sweep for the high frequencies the coarse grid cannot
  // represent. One cycle measured 0.245 of the incoming divergence; two reach the mid-band.
  const f=4,m=Math.floor(n/f),cell2=cell*cell;
  let lam=new Float32Array(N);
  const cycles=m>=8?2:1;
  for(let cyc=0;cyc<cycles;cyc++){
    if(m>=8){
      const mh=Math.max(1,Math.ceil(nh/f));
      const rc=new Float32Array(m*mh);
      for(let Y=0;Y<mh;Y++)for(let X=0;X<m;X++){
        let s2=0,c3=0;
        for(let dy=0;dy<f;dy++)for(let dx=0;dx<f;dx++){
          const yy=Y*f+dy,xx=X*f+dx;if(yy>=nh||xx>=n)continue;
          const i=yy*n+xx;
          // residual of the compact 5-point operator against the accumulated lambda
          const L=(yy>0&&yy<nh-1&&xx>0&&xx<n-1)
            ?(lam[i-1]+lam[i+1]+lam[i-n]+lam[i+n]-4*lam[i])/cell2:0;
          s2+=rhs[i]-L;c3++;}
        rc[Y*m+X]=c3?s2/c3:0;
      }
      const lamC=jacobi(new Float32Array(m*mh),rc,m,cell*f,Math.min(600,m*mh),mh);
      for(let y=1;y<nh-1;y++)for(let x=1;x<n-1;x++)
        lam[y*n+x]+=sampleGridBilinear(lamC,m,x/f,y/f,mh);
    }
    lam=jacobi(lam,rhs,n,cell,iterations,nh);
  }
  const src=lam;
  const u=u0.slice(),v=v0.slice();
  for(let y=0;y<nh;y++)for(let x=1;x<n;x++){const i=y*n+x;u[i]-=(src[i]-src[i-1])/cell;}
  for(let y=1;y<nh;y++)for(let x=0;x<n;x++){const i=y*n+x;v[i]-=(src[i]-src[i-n])/cell;}
  return{u,v};
}
function sampleGridBilinear(field,n,x,y,rows){const nh=rows||latticeRows(n);
  // Takes an explicit n because the wind model runs on a preview grid, so it cannot use the
  // global sampleBilinear. Same lattice contract though: (x,y) is a WORLD position in cell
  // units, and on hex each row's own parity shift is undone before interpolating along it.
  if(terrainDef.lattice==="hex"){
    const r=clamp(y/HEX_ROW,0,nh-1.001),r0=r|0,fr=r-r0;
    const rowAt=rr=>{const cx=clamp(x-0.5*(rr&1),0,n-1.001),c0=cx|0,i=rr*n+c0;
      return lerp(field[i],field[i+1],cx-c0);};
    return lerp(rowAt(r0),rowAt(r0+1),fr);
  }
  x=clamp(x,0,n-1.001);y=clamp(y,0,nh-1.001);
  const x0=x|0,y0=y|0,fx=x-x0,fy=y-y0,i=y0*n+x0;
  return lerp(lerp(field[i],field[i+1],fx),lerp(field[i+n],field[i+n+1],fx),fy);
}
// Terrain-adjusted middle-ground wind model (real boundary-layer CFD is intentionally out of
// scope): Jackson-Hunt-family crest speed-up, directional lee shelter, Hessian valley channeling,
// followed by an optional mass-consistency projection. All distances are derived from world metres.
// AUTHORED CONSTANTS, flagged per 09 (no corpus row backs the specific numbers): the tanh(2.5*lift)
// speed-up shaping; the 3-15 deg shelter band (13 sanctions ~15 deg); the 0.75 maximum shelter
// depth (ABOVE 13's 0.2-0.5 range - a deliberate look deviation); channelRadius = min(400 m, 7%
// of scale); the confinement denominator height*0.005; and the /30 m/s saturation used for the
// display value and snow coupling (winds above 30 read as full strength; the vector cap is 80).
function simulateTerrainWind(inp,p={},context={}){
  const n=context.res||RES,nh=latticeRows(n),N=n*nh,def=context.terrainDef||terrainDef;
  const direction=def.windDirection==null?300:def.windDirection;
  const baseSpeed=clamp(def.windSpeed==null?10:def.windSpeed,0,WIND_MAX_MPS);
  const[baseU,baseV]=windBearingVector(direction),cell=(def.scale||5000)/n;
  const baseM=metricHeightField(inp&&inp.length===N?inp:new Float32Array(N),n,def);
  const speedUp=clamp(p.speedUp==null?.65:p.speedUp,0,1.5);
  const shelterAmount=clamp(p.shelter==null?.7:p.shelter,0,1);
  const channeling=clamp(p.channeling==null?.55:p.channeling,0,1);
  const reachM=clamp(p.reach==null?1500:p.reach,Math.max(cell,50),Math.max(cell,def.scale||5000));
  const maxD=Math.max(1,Math.min(n*.75,reachM/cell)),steps=Math.min(26,Math.max(8,Math.round(Math.sqrt(n))));
  const distances=[];let last=0;
  for(let k=1;k<=steps;k++){
    const d=Math.max(1,Math.round(Math.exp(Math.log(maxD+1)*k/steps)-1));
    if(d!==last){distances.push(d);last=d;}
  }
  // Fetch length for the speed-up secant, in CELLS (world metres / cell), so the same terrain
  // gives the same speed-up at any working resolution. Floor of 2 cells keeps the secant a
  // secant on coarse previews; the reference requires fetch*cell to span the upwind hill.
  const fetchCells=Math.max(2,Math.min(n*.75,reachM/cell));
  // World extent in cell units, for the fetch/horizon walks below.
  const hexW=terrainDef.lattice==="hex",wWid=n-1,wHgt=hexW?(n-1)*HEX_ROW:n-1;
  const channelRadius=Math.max(1,Math.min(n>>3,Math.round(Math.min(400,(def.scale||5000)*.07)/cell)));
  const structure=channeling>0?blurScalarField(baseM,n,channelRadius,2):baseM;
  const u0=new Float32Array(N),v0=new Float32Array(N),speed0=new Float32Array(N);
  const tanLow=Math.tan(3*Math.PI/180),tanHigh=Math.tan(15*Math.PI/180);
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const i=y*n+x;
    // FETCH SECANT, per references/13 and reference-impl/winds.py:upwind_slope - the hill's
    // aspect ratio H/L seen looking UPWIND: (h[p] - h[p - fetch*dir]) / (fetch*cell). NOT the
    // local along-wind gradient, and the difference is the whole point: a local gradient is
    // maximal at the windward INFLECTION and exactly zero at the crest, so it puts the fastest
    // wind halfway up the hill. This shipped with a crest-carry max over an upwind sample, which
    // the corpus rules out explicitly (such a max is >= the local gradient everywhere, so the
    // inflection still wins) - measured on a Gaussian ridge: peak at column 54 of a crest at 64,
    // with the crest itself SLOWER (21.57) than the flank plateau (22.20). The secant peaks at
    // the crest, which is where anemometers, snow scour and flattened dune crests put it.
    // Reusing reachM as the fetch length matches the reference's own equal defaults (fetch=reach)
    // and keeps one "how far upwind do we look" world-scale slider. sampleGridBilinear clamps at
    // the border, which shortens the effective rise and UNDER-states the speed-up - the graceful
    // direction per the reference, not an artefact.
    // Both walks start from this cell's WORLD position and step in world cell units, so a fetch
    // or a horizon ray covers the same ground in every direction on either lattice. Walking the
    // grid indices instead shortens every N-S ray by sqrt(3)/2 on hex.
    const wx0=x+(hexW?0.5*(y&1):0),wy0=y*(hexW?HEX_ROW:1);
    const upH=sampleGridBilinear(baseM,n,wx0-baseU*fetchCells,wy0-baseV*fetchCells);
    const lift=(baseM[i]-upH)/(fetchCells*cell);
    let localSpeed=baseSpeed*(1+speedUp*Math.tanh(2.5*Math.max(0,lift)));
    if(shelterAmount>0&&baseSpeed>0){
      let horizon=-Infinity;
      for(const d of distances){
        const sx=wx0-baseU*d,sy=wy0-baseV*d;
        if(sx<0||sy<0||sx>=wWid||sy>=wHgt)break;
        horizon=Math.max(horizon,(sampleGridBilinear(baseM,n,sx,sy)-baseM[i])/(d*cell));
      }
      const shadow=smooth(clamp((horizon-tanLow)/Math.max(1e-6,tanHigh-tanLow),0,1));
      localSpeed*=1-.75*shelterAmount*shadow;
    }
    let dirU=baseU,dirV=baseV;
    if(channeling>0&&x>0&&x<n-1&&y>0&&y<nh-1){
      const a=structure[i-1]-2*structure[i]+structure[i+1];
      const c=structure[i-n]-2*structure[i]+structure[i+n];
      const b=(structure[i+n+1]-structure[i+n-1]-structure[i-n+1]+structure[i-n-1])*.25;
      const disc=Math.hypot(a-c,2*b),hi=(a+c+disc)*.5,lo=(a+c-disc)*.5;
      if(hi>0){
        let ax=b,ay=lo-a,norm=Math.hypot(ax,ay);
        if(norm<1e-7){if(Math.abs(a)>Math.abs(c)){ax=0;ay=1;}else{ax=1;ay=0;}norm=1;}
        ax/=norm;ay/=norm;if(ax*baseU+ay*baseV<0){ax=-ax;ay=-ay;}
        const crossRelief=hi*channelRadius*channelRadius;
        const confinement=smooth(clamp(crossRelief/Math.max(1,(def.height||2600)*.005),0,1));
        const w=channeling*confinement;
        dirU=lerp(baseU,ax,w);dirV=lerp(baseV,ay,w);
        const q=Math.hypot(dirU,dirV)||1;dirU/=q;dirV/=q;
      }
    }
    speed0[i]=localSpeed;u0[i]=dirU*localSpeed;v0[i]=dirV*localSpeed;
  }
  const divergenceRmsBefore=windDivergenceRms(u0,v0,n,cell);
  const projected=p.consistency==="off"?{u:u0,v:v0}
    :projectWindMassConsistent(u0,v0,n,cell,Math.min(96,Math.max(36,Math.round(Math.sqrt(n)*6))));
  const u=projected.u,v=projected.v,speed=new Float32Array(N),encoded=new Float32Array(N);
  // The cap is part of the VECTOR contract: clamp u,v together with speed, or every consumer
  // deriving a unit direction as (u/speed, v/speed) gets a "unit" vector up to 1.875 long
  // (review: snow's saltation walk stepped 2 cells per step - the documented ~30 m reach
  // silently became ~60 - and the HUD read 150 m/s against a display field saying 80).
  for(let i=0;i<N;i++){let sp=Math.hypot(u[i],v[i]);
    if(sp>WIND_MAX_MPS){const f2=WIND_MAX_MPS/sp;u[i]*=f2;v[i]*=f2;sp=WIND_MAX_MPS;}
    speed[i]=sp;encoded[i]=sp/WIND_MAX_MPS;}
  const divergenceRmsAfter=windDivergenceRms(u,v,n,cell);
  return{u,v,speed,encoded,heightM:baseM,baseDirection:direction,baseSpeed,
    divergenceRmsBefore,divergenceRmsAfter,simulationResolution:n};
}
export function evaluateTerrainWind(inp,p={}){
  const full=RES,preview=BUILD_QUALITY==="interactive"?Math.min(full,512):full;
  if(preview===full)return simulateTerrainWind(inp,p,{res:full,terrainDef});
  const result=simulateTerrainWind(resampleField(inp,full,preview),p,{res:preview,terrainDef});
  const u=resampleField(result.u,preview,full),v=resampleField(result.v,preview,full);
  const speed=new Float32Array(full*full),encoded=new Float32Array(full*full);
  for(let i=0;i<speed.length;i++){speed[i]=Math.min(WIND_MAX_MPS,Math.hypot(u[i],v[i]));encoded[i]=speed[i]/WIND_MAX_MPS;}
  return{...result,u,v,speed,encoded,simulationResolution:preview,fullResolution:full};
}
function windColorField(wind,n){const nh=latticeRows(n);
  if(!wind||!wind.u||wind.u.length!==n*nh)return null;
  const out=new Float32Array(n*nh*3);
  for(let i=0;i<n*nh;i++){
    const angle=(Math.atan2(wind.v[i],wind.u[i])/(Math.PI*2)+1)%1;
    const h=angle*6,k=~~h,f=h-k,q=1-f;
    const rgb=[[1,f,0],[q,1,0],[0,1,f],[0,q,1],[f,0,1],[1,0,q]][k%6];
    const value=.28+.72*clamp(wind.speed[i]/30,0,1),j=i*3;
    out[j]=rgb[0]*value;out[j+1]=rgb[1]*value;out[j+2]=rgb[2]*value;
  }
  return out;
}
// A transient SnowField in WORLD METRES. Fearing 2000 separates placement from stability;
// Cordonnier et al. 2018 add temperature/sun-driven melt and relax snow over the combined
// terrain + snow surface. The grid relaxation below is the heightfield form of those small,
// simultaneous avalanches: only snow moves, every transfer is distance-correct, and mass is
// conserved. The bedrock/soil height input remains unchanged.
function simulateSnowLayer(inp,p={},context={}){
  const n=context.res||RES,nh=latticeRows(n),N=n*nh,def=context.terrainDef||terrainDef;
  if(!inp||inp.length!==N)return{depthM:new Float32Array(N),volumeM3:0,maxDepthM:0,coverage:0};
  const scale=def.scale||5000,heightM=def.height||2600,cell=scale/n,cellArea=cell*cell;
  const baseM=metricHeightField(inp,n,def),depthM=new Float32Array(N);
  const snowfall=p.snowfall==null?6*(p.amount==null?.5:p.amount):p.snowfall;
  const seaTemp=def.seaTemp==null?6:def.seaTemp,lapse=def.lapseRate==null?6.5:def.lapseRate;
  const meltDays=p.meltDays==null?45:p.meltDays,meltRate=(p.meltRate==null?10:p.meltRate)/1000;
  const solarHeat=p.solarMelt==null?5:p.solarMelt,orient=terrainOrientation(def),eq=orient.equator;
  const solar=context.solarShadow&&context.solarExposure
    ?{shadow:context.solarShadow,exposure:context.solarExposure,direct:new Float32Array(N),sunElevationDeg:def.solarElevation}
    :climateSolarExposure(baseM,n,def);
  const temperatureC=context.temperatureC||new Float32Array(N);
  let depositedM3=0,meltedM3=0,preAvalancheM3=0;
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const i=y*n+x,airTemperature=seaTemp-lapse*(baseM[i]/1000);
    const temperature=context.temperatureC?temperatureC[i]:airTemperature+solarHeat*solar.exposure[i];
    if(!context.temperatureC)temperatureC[i]=temperature;
    // Mixed precipitation transition: all rain above +2 C, all snow below -3 C.
    const snowFraction=clamp((2-(context.temperatureC?temperature:airTemperature))/5,0,1);
    const deposited=snowfall*snowFraction;
    const melted=Math.min(deposited,Math.max(0,temperature)*meltRate*meltDays);
    depthM[i]=deposited-melted;
    depositedM3+=deposited*cellArea;meltedM3+=melted*cellArea;preAvalancheM3+=depthM[i]*cellArea;
  }
  const repose=(p.repose==null?38:p.repose)*Math.PI/180,talus=Math.tan(repose);
  // HOLDING DEPTH: the snow that adheres to the ground and is not available to avalanche. Without
  // it, the only equilibrium on ground steeper than repose is ZERO depth - the instability term
  // contains the bedrock drop, which removing snow cannot reduce - and the approach to it is a
  // drain front: on a planar over-steep face transport is a conveyor (each cell receives what its
  // upslope neighbour loses), so only the topmost divergent cell net-drains, then its neighbour,
  // one cell per iteration. Ridges and spurs therefore stripped bare with a bare band exactly
  // iterations x cellSize wide - no physical quantity in it - and snow COVER changed ~15 pp with
  // build quality alone, because quality scales the iteration count. The holding depth changes
  // that terminal value from zero to an adhered residual, which is what makes the covered/bare
  // classification convergent. Depths above the hold keep maturing with more iterations; that
  // remaining trend is the deferred deposition-bound work, not this mechanism.
  //   hold = H0 * min(1, tan(repose)/slope) * roughness
  // A repose-anchored taper - the law actually implemented below; see the block above the formula
  // for why the corpus's 50-60 deg shed band was measured and REJECTED as the retention law on
  // this terrain class. `roughness` is the answer to "what does snow stick TO": micro-relief
  // measured from the terrain itself (|Laplacian| against its own interior mean), so ledgy, blocky
  // ground holds more and smooth slab sheds sooner - cliffs strip in streaks, not uniformly. H0
  // and the 0.6-1.6 range are AUTHORED look controls (the corpus has no adhesion-depth row); H0=0
  // restores the strip-to-bare behaviour exactly. Slope from the TERRAIN, one-sided differences at
  // the border ring - a zeroed ring reads as flat, holds a full deposit, and rims the map.
  const holdH0=clamp(p.adhesion==null?.6:p.adhesion,0,2);   // fallback MUST equal the schema default: a node evaluated before hydration and after must produce the same terrain
  const hold=new Float32Array(N);
  if(holdH0>0){
    const tanRepose=Math.tan(repose);
    // Laplacian on the INTERIOR only, rim copied from the nearest interior cell. A clamped-index
    // stencil at the rim folds the cell's own rise back into itself, reading a planar slope as
    // curvature - the border ring then clamps to maximum roughness and the map grows a one-cell
    // frame that holds ~45% more snow than the ground beside it. The mean is interior-only for the
    // same reason.
    const lap=new Float32Array(N);let lapSum=0,lapCount=0;
    for(let y=1;y<nh-1;y++)for(let x=1;x<n-1;x++){
      const i=y*n+x;
      const l=Math.abs(baseM[i-1]+baseM[i+1]+baseM[i-n]+baseM[i+n]-4*baseM[i]);
      lap[i]=l;lapSum+=l;lapCount++;
    }
    for(let x=0;x<n;x++){lap[x]=lap[n+Math.min(Math.max(x,1),n-2)];
      lap[(nh-1)*n+x]=lap[(nh-2)*n+Math.min(Math.max(x,1),n-2)];}
    for(let y=0;y<nh;y++){lap[y*n]=lap[Math.min(Math.max(y,1),nh-2)*n+1];
      lap[y*n+n-1]=lap[Math.min(Math.max(y,1),nh-2)*n+n-2];}
    const lapMean=Math.max(lapSum/Math.max(lapCount,1),1e-6);
    for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
      const i=y*n+x,xm=Math.max(0,x-1),xp=Math.min(n-1,x+1),ym=Math.max(0,y-1),yp=Math.min(nh-1,y+1);
      const gx=(baseM[y*n+xp]-baseM[y*n+xm])/((xp-xm)*cell);
      const gy=(baseM[yp*n+x]-baseM[ym*n+x])/((yp-ym)*cell);
      const s=Math.hypot(gx,gy);
      const rough=clamp(.6+.5*lap[i]/lapMean,.6,1.6);
      // Repose-anchored retention taper: full adhesion at or below the repose angle, decaying as
      // tan(repose)/slope above it - never exactly zero, so every cell has a fixed point and the
      // covered/bare classification is convergent. The corpus's 50-60 deg shed band was evaluated
      // as the retention law first and REJECTED FOR THIS TERRAIN CLASS with numbers: in the
      // viewport's autoleveled frame ~90% of this map's cells exceed 60 deg, so a band law leaves
      // streak-only cover on most convex ground - measured 23.7% of the most-convex decile below
      // the render-opaque threshold. Real alpine ridges at 60-70 deg hold wind-packed, rime-bonded
      // snow; the taper reproduces that, thins to translucent streaks by ~80 deg, and keeps the
      // REPOSE SLIDER physical (it now moves both transport and retention). Authored law in the
      // holding-depth family - the corpus has no adhesion row; magnitude and roughness range are
      // look controls, and adhesion 0 restores the strip-to-bare behaviour exactly.
      hold[i]=holdH0*Math.min(1,tanRepose/Math.max(s,1e-6))*rough;
    }
  }
  const rate=clamp(p.settle==null?.55:p.settle,0,1),authoredIters=Math.max(0,p.iterations==null?12:p.iterations|0);
  const k=context.resScale==null?(SCALE_RES?n/REF_RES:1):context.resScale;
  const travel=(context.quality||BUILD_QUALITY)==="final"?k:Math.min(1.5,Math.sqrt(k));
  const iterations=Math.min(180,Math.round(authoredIters*travel));
  const nb=[[-1,0,1],[1,0,1],[0,-1,1],[0,1,1],[-1,-1,Math.SQRT2],[1,1,Math.SQRT2],[-1,1,Math.SQRT2],[1,-1,Math.SQRT2]];
  const delta=new Float32Array(N),excess=new Float32Array(8);
  let movedM3=0,iterationsRun=0;
  for(let it=0;it<iterations;it++){
    delta.fill(0);let moved=0;
    for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
      const i=y*n+x,available=depthM[i];if(available<=1e-7)continue;
      // Only the surplus above the holding depth is mobile. The FULL column still loads neighbours
      // (surface below is unchanged): adhered snow is not transportable, but it is not weightless.
      const mobile=available-hold[i];if(mobile<=1e-7)continue;
      const surface=baseM[i]+available;let sum=0,maxExcess=0,kb=0;
      for(const[dx,dy,dist]of nb){
        const xx=x+dx,yy=y+dy;
        if(xx<0||yy<0||xx>=n||yy>=nh){excess[kb++]=0;continue;}
        const j=yy*n+xx,e=surface-(baseM[j]+depthM[j])-talus*cell*dist;
        const q=e>0?e:0;excess[kb++]=q;sum+=q;if(q>maxExcess)maxExcess=q;
      }
      if(sum<=0)continue;
      const out=Math.min(mobile,rate*maxExcess*.5);kb=0;
      for(const[dx,dy]of nb){
        const q=excess[kb++];if(q<=0)continue;
        const j=(y+dy)*n+x+dx,transfer=Math.min(out*q/sum,q*.5);
        delta[i]-=transfer;delta[j]+=transfer;moved+=transfer;
      }
    }
    for(let i=0;i<N;i++)depthM[i]=Math.max(0,depthM[i]+delta[i]);
    movedM3+=moved*cellArea;iterationsRun=it+1;
    if(moved*cellArea<Math.max(1e-5,preAvalancheM3*1e-8))break;
  }
  // WIND REDISTRIBUTION - corpus snowStep step 5, grounded on reference-impl/snow.py
  // wind_redistribute: scour snow where the SNOW SURFACE rises into the wind; deposit it in the
  // SHADOW ZONE. This is the process gravity settling cannot imitate: windward ground strips while
  // the sheltered lee past a crest becomes the most heavily loaded ground on the mountain - a
  // cornice. Runs LAST, per the corpus ordering, and cornices are deliberately not re-settled
  // afterwards: a cornice is an over-steepened lee deposit, and a relaxation pass to repose would
  // remove exactly the feature the wind built. Wind ignores the holding depth on purpose - wind
  // scour is precisely the process that strips adhered snow.
  // TWO DOCUMENTED DEVIATIONS FROM THE REFERENCE PORT, both found by measurement:
  //  - Deposit target: the reference drops scoured mass at a FIXED one-cell offset. On terrain
  //    whose settled drifts decouple from the bedrock (20 m drifts on 10 m cells), that lands mass
  //    on ground that is still windward - measured face-integrated result: windward faces GAINED
  //    9.3% and lee faces LOST 4.4%, the exact inversion of the process being modelled. The corpus
  //    names this logic "the dune shadow-zone logic" (05), and the dune model deposits in the
  //    SHELTERED zone: here each scoured parcel walks downwind to the first cell where the surface
  //    stops rising into the wind (just past the local drift crest), capped at ~30 m of reach.
  //  - Border: numpy's roll WRAPS, teleporting mass to the far edge; here it stays in place.
  const physicalWind=context.wind&&context.wind.u&&context.wind.v&&context.wind.speed
    &&context.wind.u.length===N?context.wind:null;
  const windStrength=clamp(p.windStrength==null?.35:p.windStrength,0,1); // fallback = schema default, same reason as adhesion
  if(physicalWind||windStrength>0){
    const fallback=windBearingVector(p.windDirection==null?300:p.windDirection);
    let eventStrength=windStrength;
    if(physicalWind){
      // p95, not max: with max, ONE gusty cell (a DEM spike, a single channeled throat) doubles
      // the event duration of the entire map (measured: injecting one 40 m/s cell into a calm
      // 6 m/s field took the pass count 4 -> 8). The /30 saturation is the documented snow
      // coupling scale - winds above 30 m/s all read as a full-strength event.
      const smp=[];for(let i=0;i<N;i+=7)smp.push(physicalWind.speed[i]);
      smp.sort((a2,b2)=>a2-b2);
      eventStrength=clamp(smp[Math.min(smp.length-1,(smp.length*0.95)|0)]/30,0,1);
    }
    // The walk cap is a DISTANCE (~30 m of saltation reach along a cardinal; ~42 m diagonal, an
    // accepted stretch), not a cell count, so cornice scale does not depend on the sim grid.
    const walkCap=clamp(Math.round(30/cell),2,24),hexSnow=terrainDef.lattice==="hex";
    // Pass count is the event-duration proxy: with the transportable layer capped per pass, a
    // fixed 3 passes moves the same volume at every strength and the slider only reshapes WHERE
    // it goes. Strength now scales both the per-pass rate and how long the event blows (3-8).
    const windPasses=Math.round(3+5*eventStrength);
    const scour=new Float32Array(N),expo=new Float32Array(N);
    for(let pass=0;pass<windPasses;pass++){
      for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
        const i=y*n+x;
        const s=physicalWind?physicalWind.speed[i]:1;
        const wx=physicalWind&&s>1e-6?physicalWind.u[i]/s:fallback[0];
        const wy=physicalWind&&s>1e-6?physicalWind.v[i]/s:fallback[1];
        const localStrength=physicalWind?clamp(s/30,0,1):windStrength,wRate=.45*localStrength;
        const xm=Math.max(0,x-1),xp=Math.min(n-1,x+1),ym=Math.max(0,y-1),yp=Math.min(nh-1,y+1);
        const sx=(baseM[y*n+xp]+depthM[y*n+xp]-baseM[y*n+xm]-depthM[y*n+xm])/((xp-xm)*cell);
        const sy=(baseM[yp*n+x]+depthM[yp*n+x]-baseM[ym*n+x]-depthM[ym*n+x])/((yp-ym)*cell);
        expo[i]=wx*sx+wy*sy;                             // >0: surface rising INTO the wind
        // Saltation moves the LOOSE SURFACE LAYER, not the consolidated pack: uncapped, a 20 m
        // drift shoulder donates ~8 m per pass and that single flux swamps every face budget
        // (measured: windward faces NET GAINED because gully-drift outflow landed on their toes).
        // 0.5 m per pass is an authored transportable-layer cap, documented as such.
        scour[i]=depthM[i]<=1e-7?0:wRate*Math.min(depthM[i],.5)*Math.tanh(5*Math.max(0,expo[i]));
      }
      for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
        const i=y*n+x,q=scour[i];if(q<=0)continue;
        const s=physicalWind?physicalWind.speed[i]:1;
        const wx=physicalWind&&s>1e-6?physicalWind.u[i]/s:fallback[0];
        const wy=physicalWind&&s>1e-6?physicalWind.v[i]/s:fallback[1];
        // Snap the local wind to a LATTICE azimuth, then walk one neighbour per step. On square
        // that is sign*round(abs) - NOT Math.round: JS rounds half UP, so Math.round(0.5)=1 but
        // Math.round(-0.5)=-0, and mirrored bearings would transport on different axes. On hex
        // the eight square directions do not exist; pick the closest of the SIX one-ring azimuths
        // by dot product and step with that row's own parity offsets, re-read each step because
        // the offsets alternate as the walk crosses rows.
        let dj=0,di=0,hexK=-1;
        if(hexSnow){
          let bestDot=-Infinity;
          for(let k=0;k<6;k++){const dot=wx*HEX_EX[k]+wy*HEX_EY[k];if(dot>bestDot){bestDot=dot;hexK=k;}}
        }else{
          dj=Math.sign(wx)*Math.round(Math.abs(wx));di=Math.sign(wy)*Math.round(Math.abs(wy));
          if(!dj&&!di){if(Math.abs(wx)>=Math.abs(wy))dj=Math.sign(wx)||1;else di=Math.sign(wy)||1;}
        }
        // Walk downwind to shelter: the first cell no longer rising into the wind, i.e. just past
        // the local drift crest. If nothing shelters within the cap, drop at the cap (suspension
        // limit). Off-grid at any step: mass stays where it is (no wrap).
        let tx=x,ty=y,sheltered=false,offGrid=false;
        for(let step2=0;step2<walkCap;step2++){
          let nx2,ny2;
          if(hexSnow){const off=hexNb(ty)[hexK];nx2=tx+off[0];ny2=ty+off[1];}
          else{nx2=tx+dj;ny2=ty+di;}
          if(nx2<0||ny2<0||nx2>=n||ny2>=nh){offGrid=true;break;}
          tx=nx2;ty=ny2;
          if(expo[ty*n+tx]<=0){sheltered=true;break;}
        }
        // Deposit when sheltered or at the suspension cap. A walk that runs OFF the grid leaves
        // the parcel where it started - otherwise every unsheltered parcel within reach of the
        // downwind edge piles onto the border cell and the map grows a snow rim (the same class
        // of artefact as the Laplacian rim above).
        if(offGrid)continue;
        depthM[i]-=q;depthM[ty*n+tx]+=q;movedM3+=q*cellArea;
      }
    }
  }
  let volumeM3=0,maxDepthM=0,covered=0;
  for(let i=0;i<N;i++){const d=depthM[i];volumeM3+=d*cellArea;if(d>maxDepthM)maxDepthM=d;if(d>.01)covered++;}
  return{depthM,baseM,temperatureC,solarExposure:context.solarExposure||solar.exposure,solarShadow:context.solarShadow||solar.shadow,
    volumeM3,depositedM3,meltedM3,preAvalancheM3,movedM3,maxDepthM,
    coverage:covered/N,iterationsRun,cellSizeM:cell,equator:[...eq],
    sunElevationDeg:solar.sunElevationDeg,simulationResolution:n,windSource:physicalWind?"field":"fallback"};
}
// Keep live 1K–4K authoring bounded without changing the physical grid scale: avalanche stability is
// solved on a 512² preview field (cell size follows that field), then only the transient depth is
// reconstructed at working resolution. Final quality intentionally removes the cap.
export function evaluateSnowLayer(inp,p,temperatureField=null,solarShadow=null,solarExposure=null,wind=null){
  const full=RES,preview=BUILD_QUALITY==="interactive"?Math.min(full,512):full;
  if(preview===full)return simulateSnowLayer(inp,p,{temperatureC:temperatureField,solarShadow,solarExposure,wind});
  const small=resampleField(inp,full,preview);
  const smallTemp=temperatureField?resampleField(temperatureField,full,preview):null;
  const smallShadow=solarShadow?resampleField(solarShadow,full,preview):null;
  const smallExposure=solarExposure?resampleField(solarExposure,full,preview):null;
  let smallWind=null;
  if(wind)smallWind={...wind,u:resampleField(wind.u,full,preview),v:resampleField(wind.v,full,preview),
    speed:resampleField(wind.speed,full,preview)};
  const layer=simulateSnowLayer(small,p,{res:preview,terrainDef,quality:BUILD_QUALITY,
    resScale:SCALE_RES?preview/REF_RES:1,temperatureC:smallTemp,solarShadow:smallShadow,
    solarExposure:smallExposure,wind:smallWind});
  layer.depthM=resampleField(layer.depthM,preview,full);
  layer.temperatureC=resampleField(layer.temperatureC,preview,full);
  layer.solarExposure=resampleField(layer.solarExposure,preview,full);
  layer.solarShadow=resampleField(layer.solarShadow,preview,full);
  layer.fullResolution=full;
  return layer;
}
// Hydraulic (droplet) erosion — Beyer 2015 / Lague-style particle sim, mass-balanced with an
// erosion brush so a droplet spreads its scour over a small radius (no single-cell pits).
export function hydraulicErode(inp,{droplets=15000,lifetime=null,inertia=0.05,capacity=4,erode=0.3,deposit=0.3,evap=0.02,gravity=4,radius=2,minSlope=0.01,seed=1,spawn=null,settle=false,gridK=1}){
  const n=fieldW(),nh=fieldH();let h=inp.slice();
  // Res Lock (gridK = node-level RES/REF_RES; default 1 = legacy cell-unit behaviour, which the
  // mountain/peak callers rely on byte-for-byte). A step is one cell, so per-step rates are
  // per-CELL rates: the same world distance takes k x the steps at k x resolution, so the
  // fractional rates become 1-(1-r)^(1/k) (identical total effect over k steps) and the
  // capacity's slope term is restored to reference-cell units (dH*k). Speed/gravity need no
  // change: energy already sums the same total drop along the same world path.
  const gk=gridK>0?gridK:1;
  const evapK=gk===1?evap:1-Math.pow(1-evap,1/gk);
  const erodeK=gk===1?erode:1-Math.pow(1-erode,1/gk);
  const depositK=gk===1?deposit:1-Math.pow(1-deposit,1/gk);
  const R=Math.max(1,radius|0);const brush=[];let bw=0;
  for(let dy=-R;dy<=R;dy++)for(let dx=-R;dx<=R;dx++){const dd=Math.hypot(dx,dy);if(dd<=R){const w=1-dd/(R+1);brush.push([dx,dy,w]);bw+=w;}}
  for(const b of brush)b[2]/=bw;
  let rng=Math.imul(seed|0,2654435761)>>>0;
  const rnd=()=>((rng=(Math.imul(rng,1664525)+1013904223)>>>0)/4294967295);
  // Droplet position (px,py) is a WORLD position in cell units on either lattice, so a unit step
  // is one cell of world distance in every direction. On hex that means resolving the two rows
  // straddling py with THEIR OWN parity shifts - the same construction as sampleBilinear - and
  // splatting back onto those four lattice cells. Reading (px,py) as raw grid indices would walk
  // the droplet along a sheared basis and splat its load onto the wrong cells.
  const hexL=isHex();
  const at=hexL?(px,py)=>{
    const r=clamp(py/HEX_ROW,0,nh-1.001),r0=r|0,fr=r-r0;
    const cx0=clamp(px-0.5*(r0&1),0,n-2),c0=cx0|0,f0=cx0-c0;
    const cx1=clamp(px-0.5*((r0+1)&1),0,n-2),c1=cx1|0,f1=cx1-c1;
    const i0=r0*n+c0,i1=(r0+1)*n+c1;
    const a=h[i0],b=h[i0+1],c=h[i1],d=h[i1+1];
    const top=a+(b-a)*f0,bot=c+(d-c)*f1;
    return{gx:(b-a)*(1-fr)+(d-c)*fr,gy:(bot-top)/HEX_ROW,hh:top+(bot-top)*fr,
      i0,f0,i1,f1,fr,x0:c0,y0:r0};
  }:(px,py)=>{ // bilinear height + gradient
    const x0=clamp(px|0,0,n-2),y0=clamp(py|0,0,n-2),fx=px-x0,fy=py-y0,i=y0*n+x0;
    const a=h[i],b=h[i+1],c=h[i+n],d=h[i+n+1];
    return{gx:(b-a)*(1-fy)+(d-c)*fy,gy:(c-a)*(1-fx)+(d-b)*fx,
      hh:a*(1-fx)*(1-fy)+b*fx*(1-fy)+c*(1-fx)*fy+d*fx*fy,x0,y0,fx,fy};
  };
  // Both splats carry weights summing to exactly 1, so the mass ledger closes on either lattice.
  const deposit1=hexL?(g,amt)=>{
    h[g.i0]+=amt*(1-g.f0)*(1-g.fr);h[g.i0+1]+=amt*g.f0*(1-g.fr);
    h[g.i1]+=amt*(1-g.f1)*g.fr;h[g.i1+1]+=amt*g.f1*g.fr;
  }:(g,amt)=>{const i=g.y0*n+g.x0;
    h[i]+=amt*(1-g.fx)*(1-g.fy);h[i+1]+=amt*g.fx*(1-g.fy);h[i+n]+=amt*(1-g.fx)*g.fy;h[i+n+1]+=amt*g.fx*g.fy;};
  // A brush cell clipped at the border removes nothing from h while the droplet still credits
  // itself the full amt - mass appears from nowhere (0.8% of the budget at radius 2; the clipped
  // band is `radius` cells wide, so a radius-5 brush grows the term several-fold). Ledger it so
  // the budget closes exactly instead of hiding the gain inside a tolerance.
  let brushClip=0;
  const erode1=(g,amt)=>{for(const[dx,dy,w]of brush){const xx=g.x0+dx,yy=g.y0+dy;
    if(xx<0||yy<0||xx>=n||yy>=nh){brushClip+=amt*w;continue;}h[yy*n+xx]-=amt*w;}};
  let settled=0,exported=0,lost=0;
  // World extent in cell units. The hex domain is (nh-1)*sqrt(3)/2 tall, so spawning and
  // bounds-checking against n-1 would seed droplets outside the terrain and retire every one
  // that crossed y=n-1 - clipping the bottom 13.4% of the map out of the simulation.
  const wH=hexL?(nh-1)*HEX_ROW:nh-1,wW=n-1;
  const spawnIdx=hexL?(px,py)=>{const r=clamp(Math.round(py/HEX_ROW),0,nh-1);
      return r*n+clamp(Math.round(px-0.5*(r&1)),0,n-1);}
    :(px,py)=>clamp(py|0,0,nh-1)*n+clamp(px|0,0,n-1);
  const maxLifetime=lifetime==null?n*0.7:Math.max(1,lifetime*gk);
  for(let d=0;d<droplets;d++){
    let px=rnd()*wW,py=rnd()*wH;
    if(spawn)for(let tries=0;tries<16&&spawn[spawnIdx(px,py)]<=0;tries++){
      px=rnd()*wW;py=rnd()*wH;}
    let dx=0,dy=0,speed=1,water=1,sed=0,leftGrid=false;
    for(let life=0;life<maxLifetime;life++){
      const g=at(px,py);const hOld=g.hh;
      dx=dx*inertia-g.gx*(1-inertia);dy=dy*inertia-g.gy*(1-inertia);
      const len=Math.hypot(dx,dy);if(len<1e-5){dx=rnd()-0.5;dy=rnd()-0.5;}else{dx/=len;dy/=len;}
      const nx=px+dx,ny=py+dy;
      if(nx<0||ny<0||nx>=wW||ny>=wH){leftGrid=true;break;}
      const dH=at(nx,ny).hh-hOld;
      const cap=Math.max(-dH*gk,minSlope)*speed*water*capacity;
      if(sed>cap||dH>0){                                   // over capacity, or going uphill -> deposit
        const amt=dH>0?Math.min(dH,sed):(sed-cap)*depositK;deposit1(g,amt);sed-=amt;
      }else{                                               // under capacity -> scour (brush-distributed)
        const amt=Math.min((cap-sed)*erodeK,-dH);erode1(g,amt);sed+=amt;
      }
      speed=Math.sqrt(Math.max(0,speed*speed-dH*gravity));water*=(1-evapK);
      px=nx;py=ny;if(water<0.008)break;
    }
    // The droplet's remaining suspended load is real eroded mass. Off-grid it is export (the
    // boundary is base level; on open terrain that is MOST of the budget - measured 41% of
    // net-eroded volume, and legitimate); on-grid (dried out or life-capped) it settles where
    // the droplet stopped - dry-out in a pan IS the pan filling, and in closed basins the
    // settled share grows accordingly. Before this, the on-grid remainder vanished and the
    // budget was unauditable: no closure between erosion, deposition and export was provable.
    // `settle` is opt-in because the mountain/peak macro-weathering callers predate the fix:
    // the digest suite pins them byte-identical - the mountain node's default "peak" form via
    // its baseline digest, the "massif" form via its ex= exercise digest.
    if(leftGrid)exported+=sed;
    else if(settle&&sed>0){deposit1(at(px,py),sed);settled+=sed;}
    else lost+=sed;
  }
  // Closure identity: sumIn - sumOut = exported + lost - brushClipGain (the last term is mass
  // the border-clipped brush created; see erode1).
  let sumIn=0,sumOut=0;for(let i=0;i<n*nh;i++){sumIn+=inp[i];sumOut+=h[i];}
  setHydroMassDiag({engine:"droplets",settle:!!settle,sumIn,sumOut,settled,exported,exportedDerived:false,lost,brushClipGain:brushClip});
  return h;
}

// EROSION 2 — a clean-room, multi-scale hydraulic composition over the owned pipe/droplet kernels.
// Gaea's implementation is proprietary; its public contract separates duration/downcutting, largest
// erosion scale, three sediment mobilities, shape relaxation, and nested detail. We preserve that
// separation rather than relabelling the older single-pass Hydraulic node.
export function erosion2Field(inp,p){
  const duration=clamp(p.duration,0,1),down=clamp(p.downcut,0,1),detail=clamp(p.shapeDetail,0,1);
  const sediment=clamp((p.suspended+p.bed+p.coarse)/3*(1+.75*p.depositBoost),.03,.95);
  const[mn,mx]=fieldRange(inp),relief=Math.max(mx-mn,1e-5),seeded=inp.slice(),n=RES,nh=latticeRows(n);
  // A tiny seeded rock-resistance perturbation gives deterministic channel choice without moving
  // the macro landform. Its amplitude is below one percent of relief and is consumed by erosion.
  const seedAmp=relief*(.0007+.0022*detail);
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++)
    seeded[y*n+x]+=fbm2(x/n*11+2.7,y/n*11+6.1,p.seed|0,3)*seedAmp;
  const coarseIters=Math.max(8,Math.round(16+duration*80));
  const featureScale=lerp(1,7,clamp(p.erosionScale,0,1));
  // Res Lock: gk is the NODE-level grid ratio, measured before atFeatureScale coarsens RES, so
  // it is exactly 1 at the 192 reference (the tuned look is preserved by construction) and it
  // matches the coarse pass's own between-build grid ratio at any working resolution.
  // The Interactive tier runs each pass as a FULL-QUALITY sim on a further-coarsened grid
  // (tier = RES/384, folded into the feature scale) with ke = k/tier - identical to the old
  // min(k,2) cap at RES <= 384, full-parity physics on the capped grid above it (same contract
  // as the hydraulic node). gw is for WIDTHS at the FULL grid (shapeSharp blur) - geometry.
  const kN=resScale(),tier=BUILD_QUALITY==="final"?1:Math.max(1,RES/384);
  const gk=kN/tier,gw=kN;
  const run=(source,scale,iters,phase)=>{
    const erode=lerp(.12,.70,down)*lerp(.72,1.12,duration);
    const deposit=lerp(.08,.62,sediment);
    const capacity=lerp(3,11,down)*lerp(.72,1.18,1-sediment);
    return atFeatureScale(source,scale*tier,field=>gpuReady()
      ?gpuHydraulicPipes(field,{iters,capacity,erode,deposit,inertia:.04+.08*phase,gridK:gk})
      :hydraulicErode(field,{droplets:Math.max(2500,Math.round(fieldLen()*(.12+.40*duration))),  // NOTE (converted, not an exemption): a droplet COUNT proportional to cell count, not a field shape
        capacity,erode,deposit,inertia:.04+.08*phase,radius:Math.max(1,Math.round((1+scale*.35)*gk)),seed:(p.seed|0)+phase*101,settle:true,gridK:gk}));
  };
  let h=run(seeded,featureScale,coarseIters,0);
  // A shorter fine pass nests gullies inside the broad ravines. Higher Erosion Scale still goes
  // first, so the fine pass cannot erase the macro drainage hierarchy. On the Interactive tier
  // above 384 the fine pass rides the 384-capped grid (fineScale*tier), so it is near-native
  // only on Final - the preview matches the landform, not the sub-tier detail.
  if(detail>.02){
    const fineScale=lerp(1,Math.max(1,featureScale*.46),1-detail);
    h=run(h,fineScale,Math.max(6,Math.round(coarseIters*(.14+.34*detail))),1);
  }
  if(p.shape>.01){
    const talus=Math.tan(lerp(43,30,p.shape)*Math.PI/180)*cellSizeM()/terrainDef.height;
    const shaped=gpuReady()?gpuThermal(h,{talus,iters:Math.max(2,Math.round(3+p.shape*14)),rate:.34})
      :thermalOn(h,{talus,iters:Math.max(2,Math.round(3+p.shape*14)),rate:.34});
    for(let i=0;i<h.length;i++)h[i]=lerp(h[i],shaped[i],p.shape*.72);
  }
  if(p.shapeSharp>.01){
    const broad=blurField(h,{radius:Math.max(1,Math.round((1+featureScale*.35)*gw))});
    for(let i=0;i<h.length;i++){
      const residual=h[i]-broad[i];
      h[i]+=residual>0?residual*p.shapeSharp*.24:residual*p.shapeSharp*.07;
    }
  }
  return h;
}

// HYDROFIX — low-amplitude drainage conditioning. Route on a priority-filled copy, carve a soft
// accumulation corridor into the original terrain, then enforce only the tiny descent needed for
// connected receivers. This changes flow topology without replacing the landscape.
export function hydroFixField(inp,p){
  const n=fieldW(),nh=fieldH(),N=n*nh,filled=priorityFloodFill(inp),rec=new Int32Array(N).fill(-1),A=new Float32Array(N).fill(1);
  // Same one-ring contract as spReceivers: D6 on hex (one distance), D8 with sqrt(2) on square.
  const nbSq=[[-1,0,1],[1,0,1],[0,-1,1],[0,1,1],[-1,-1,Math.SQRT2],[1,1,Math.SQRT2],[-1,1,Math.SQRT2],[1,-1,Math.SQRT2]];
  const hex=isHex();
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const i=y*n+x;let best=filled[i],bestSlope=0,receiver=-1;
    const nb=hex?hexNb(y):nbSq;
    for(const d of nb){const xx=x+d[0],yy=y+d[1];if(xx<0||yy<0||xx>=n||yy>=nh)continue;
      const j=yy*n+xx,s=(filled[i]-filled[j])/(hex?1:d[2]);if(s>bestSlope){bestSlope=s;best=filled[j];receiver=j;}}
    rec[i]=receiver;
  }
  const order=Array.from({length:N},(_,i)=>i).sort((a,b)=>filled[b]-filled[a]);
  for(const i of order)if(rec[i]>=0)A[rec[i]]+=A[i];
  // `fix` controls WHERE the node acts (channel extent, exponential across the slider - the
  // linear form left the shipped default .52 inert: 10 of 750 pits removed, rms 2.3e-4), never
  // HOW MUCH: the descent enforcement below is always full, because 52% of a breach is a dam.
  // fix = 0 is an exact bypass - with unconditional enforcement the trunk network would
  // otherwise still be breached at the slider's OFF position.
  const fix=clamp(p.fix,0,1);
  if(fix<=0)return inp.slice();
  const down=clamp(p.downcut,0,1),threshold=.035*Math.pow(.0025/.035,fix)*N;
  const rawMask=new Float32Array(N),den=Math.log(Math.max(N/Math.max(threshold,1),1.0001));
  for(let i=0;i<N;i++)rawMask[i]=A[i]<=threshold?0:smooth(clamp(Math.log(A[i]/threshold)/den,0,1));
  // Corridor width is a WORLD width: the blur radius follows the grid, and the amplitude is
  // restored by the box-dilution factor - a 1-cell-wide raster channel line spread over a
  // (2R+1)-cell band loses exactly that factor, which made the soft cut fade ~1/sqrt(k) as the
  // grid doubled. At the 192 reference R=R0 and the factor is exactly 1. (The descent
  // ENFORCEMENT below stays one cell wide on purpose: it is a breach, a lattice operation like
  // depression breaching itself, not a landform.)
  const R0=Math.max(1,Math.round(1+fix*2)),R=Math.max(1,Math.round((1+fix*2)*resScale()));
  const mask=blurScalarField(rawMask,n,R,1);
  if(R!==R0){const amp=(2*R+1)/(2*R0+1);for(let i=0;i<N;i++)mask[i]=Math.min(1,mask[i]*amp);}
  const[mn,mx]=fieldRange(inp),relief=Math.max(mx-mn,1e-5),cut=relief*(.0003+.0072*down)*fix;
  const out=inp.slice();for(let i=0;i<N;i++)out[i]-=mask[i]*cut;
  const eps=relief/(Math.max(n,2)*160);
  for(const i of order){const r=rec[i];if(r<0||rawMask[i]<=0)continue;
    const target=out[i]-eps;if(out[r]>target)out[r]=target;}
  return out;
}

/* =====================================================================
   NODE TYPES
   ===================================================================== */
// P / WHEN / GROUP / CAT now live in src/core/params.js.
const EXACT_TYPES=new Set(["perlin","simplex","ridged","worley","gradient","shape","crater","island","volcano","drawmask","constant",
  "levels","curve","clampn","invert","terrace","blend","add","maxmin","smin","smax","stampn"]);
// The declared output ports of a node instance. `cat:"out"` types (the Output sink) declare none,
// which is the same rule drawNode and portAt used to spell inline as `def.cat!=="out"` — it now
// lives in one place and answers with the actual descriptors rather than a boolean.
function nodeOutputs(nd){
  const def=TYPES[nd.type||nd];
  if(!def)return [];
  // A node may refine its declared ports per INSTANCE. Variable does: its unit is whatever the
  // referenced variable declares, and a static descriptor cannot know that. Without this the
  // declaration and the value disagree, which is exactly the class of defect typed ports exist to
  // prevent.
  if(typeof def.resolvePorts==="function"&&nd&&nd.type){
    try{const r=def.resolvePorts(nd);if(r&&Array.isArray(r.outputs))return r.outputs;}catch(_){}
  }
  if(def.outputs)return def.outputs;
  return def.cat==="out"?[]:[{id:"out",name:"Out"}];
}
// S2.3 — the typed result contract, shared by ALL THREE evaluation paths (evalGraph's ev,
// evalGraphProgressive, and evalExact) so recursive, progressive and exact execution cannot
// disagree about which port carries what.
//
// ADR-002: "A typed evaluation returns { values: Map<portId, value> }. The primary output is
// compatibility metadata, not an untyped bypass." A legacy evaluator returning a bare
// Float32Array is adapted to its ONE declared primary scalar raster; that adaptation is the only
// thing standing between 79 untyped plugins and a typed runtime, and it is why the digest does not
// move: the same eval is called with the same arguments and its result is simply given a name.
// The graph SINK produces a value but publishes no port. `output` (cat:"out") has no outgoing wire
// — that is why drawNode and portAt have always refused to draw one — yet its eval returns the
// final terrain the renderer, the exporter and collectScene all read through nd._field. Keying that
// value under a reserved id keeps the alias alive without inventing a connectable port.
//
// Measured the hard way: returning an empty Map for the sink left outputNode()._field undefined,
// and _verify_water, _verify_snow and _verify_workflow all went red with every reading at zero.
// The digest never noticed, because it calls def.eval directly and never goes through a sink.
const SINK_PRIMARY="__sink";
// Which outputs of `nd` anything downstream actually asks for. The primary is always in the set:
// it backs nd._field, which the thumbnail, the preview and collectScene all read. Anything else is
// demanded only if some edge names it — that is what makes an undemanded output free.
// S8.2 — INPUT-side demand, the mirror of demandedPortsFor. A plugin may declare which of its
// input slots can actually affect its result given its current params; Switch demands only the
// selected branch. Absent the hook every slot is demanded, which is what all 82 other types mean.
//
// The blanket thumbnail pass in evalGraph still visits every node in its own right — the story
// permits exactly that ("thumbnail policy may request branch previews explicitly"). What this
// removes is a Switch DRAGGING an unselected branch into evaluation through its own input edge,
// which is the case that made branch cost unavoidable.
function demandedInputSlots(nd){
  const def=TYPES[nd.type];
  const n=nodeInputs(nd).length;
  if(!def||typeof def.demandInputs!=="function"){const all=new Set();for(let i=0;i<n;i++)all.add(i);return all;}
  const want=def.demandInputs(nd.params,nd);
  const set=new Set();
  for(const i of (want||[]))if(Number.isInteger(i)&&i>=0&&i<n)set.add(i);
  return set;
}
function demandedPortsFor(nd){
  const want=new Set();
  const primary=primaryPortId(nd);
  if(primary)want.add(primary);
  for(const e of edges){if(e.disabled||e.from!==nd.id)continue;if(e.fromPort)want.add(e.fromPort);}
  return want;
}
// Typed plugins receive a fourth argument. Legacy plugins have a three-parameter eval and simply
// ignore it, so nothing about the existing 79 changes — which is why the digest cannot move.
function evaluateNodeValues(nd,ins,demanded){
  const def=TYPES[nd.type];
  const raw=def.eval(nd.params,ins,nd,{demanded:demanded||demandedPortsFor(nd)});
  if(raw&&raw.values instanceof Map)return raw.values;           // already typed
  return new Map([[primaryPortId(nd),raw]]);
}
function primaryPortId(nd){const o=nodeOutputs(nd),p=o.find(x=>x.primary)||o[0];return p?p.id:SINK_PRIMARY;}
// Read one input for `nd` at `slot`, honouring the edge's SOURCE port. For a single-output node
// this is the primary and therefore exactly the previous behaviour.
function readInputValue(e,fallback){
  if(!e||!e.fromPort)return fallback;
  const src=nodeById(e.from);
  if(src&&src._outputs&&src._outputs.has(e.fromPort))return src._outputs.get(e.fromPort);
  return fallback;
}
// Which output an existing edge leaves from. Edges written before port identity carry no fromPort,
// and every type declares exactly one output today, so 0 is the correct answer rather than a guess.
function outSlotForEdge(e){
  const from=e&&nodeById(e.from);
  if(!from||!e.fromPort)return 0;
  const i=nodeOutputs(from).findIndex(p=>p.id===e.fromPort);
  return i<0?0:i;
}
function nodeInputs(nd){return nd&&nd._inputs?nd._inputs:TYPES[nd.type].ins;}
export function exactChain(id,guard){
  guard=guard||new Set();if(!id||guard.has(id))return false;guard.add(id);
  const nd=nodeById(id);if(!nd||!EXACT_TYPES.has(nd.type))return false;
  const refs=TYPES[nd.type].referenceOnly||[];
  return nodeInputs(nd).every((_,s)=>{if(refs.includes(s))return true;const e=inputEdge(id,s);return !e||exactChain(e.from,guard);});
}
// Re-evaluate a chain under the ambient XF. Deliberately does NOT write nd._field: the cached fields
// are the untransformed ones other branches and the thumbnails still depend on.
export function evalExact(id,guard){
  if(!id||guard.has(id))return null;guard.add(id);
  const nd=nodeById(id);if(!nd){guard.delete(id);return null;}
  const def=TYPES[nd.type],refs=def.referenceOnly||[];
  const wantExact=demandedInputSlots(nd);
  const ins=nodeInputs(nd).map((_,s)=>{if(refs.includes(s))return nd._reference||null;const e=inputEdge(id,s);
    if(!e||!wantExact.has(s))return null;const up=evalExact(e.from,guard);return readInputValue(e,up);});
  // The exact path is a fold used by Transform chains: it does not populate the per-output cache,
  // because it deliberately does not own node state. It reads ports the same way, so the three
  // paths cannot disagree about which output an edge carries.
  let f;try{f=evaluateNodeValues(nd,ins).get(primaryPortId(nd));f=propagateFieldMetadata(f,ins,def);nd._evalError=null;nd._evalErrorCode=null;}catch(err){console.error("exact",nd.type,err);nd._evalError=String(err&&err.message||err);nd._evalErrorCode=(err&&err.code)||null;f=newField();}
  guard.delete(id);return f;
}

const TYPES=mergePlugins({





  // ---- DATA MAPS (Gaea's "Derive" channels): grayscale fields to bind a SatMap / mask to ----


});

/* =====================================================================
   GRAPH MODEL
   ===================================================================== */
let nodes=[],edges=[],uid=1,selected=null,selectedEdge=null;
let historyReady=false,undoStack=[],redoStack=[];
const HISTORY_LIMIT=60;
const cloneParams=p=>typeof structuredClone==="function"?structuredClone(p):JSON.parse(JSON.stringify(p));
function graphSnapshot(){
  return{
    nodes:nodes.map(n=>({id:n.id,type:n.type,x:n.x,y:n.y,w:n.w,params:cloneParams(n.params),
      // _demSrc carries WHERE an imported height came from, and it was the one _dem* field the
      // snapshot omitted — so undo/redo silently stripped an import's provenance, and because the
      // project writer reads _demSrc, a saved document after an undo lost the source entirely.
      _inputs:n._inputs?[...n._inputs]:null,_dem:n._dem,_demImg:n._demImg,_demRaw:n._demRaw,
      _demSrc:n._demSrc?{...n._demSrc}:null})),
    edges:edges.map(e=>({...e})),uid,selectedId:selected?selected.id:null,selectedEdgeKey:selectedEdge,terrainDef:{...terrainDef},
    // S8.3 says "variable edits are one undo record". They were in no undo record at all: a
    // snapshot carried nodes/edges/uid/terrainDef and nothing else, so changing a variable and
    // pressing undo left the new value in place while the graph around it reverted.
    variables:documentVariables.map(v=>({...v}))
  };
}
function updateHistoryButtons(){
  $("#undoBtn").disabled=!undoStack.length;$("#redoBtn").disabled=!redoStack.length;
  document.querySelectorAll('[data-editor-command="undo"]').forEach(b=>b.disabled=!undoStack.length);
  document.querySelectorAll('[data-editor-command="redo"]').forEach(b=>b.disabled=!redoStack.length);
}
function pushUndo(snap){
  if(!historyReady||!snap)return;
  undoStack.push(snap);if(undoStack.length>HISTORY_LIMIT)undoStack.shift();redoStack.length=0;updateHistoryButtons();
}
function recordHistory(){pushUndo(graphSnapshot());}
function snapshotIsEditorOnly(snap){
  if(snap.nodes.length!==nodes.length||snap.edges.length!==edges.length||snap.uid!==uid)return false;
  if(JSON.stringify(snap.edges)!==JSON.stringify(edges)||JSON.stringify(snap.terrainDef)!==JSON.stringify(terrainDef))return false;
  return snap.nodes.every(sn=>{const n=nodeById(sn.id);return n&&n.type===sn.type&&n.w===sn.w
    &&JSON.stringify(n.params)===JSON.stringify(sn.params)
    &&JSON.stringify(n._inputs||null)===JSON.stringify(sn._inputs)
    &&n._dem===sn._dem&&n._demImg===sn._demImg&&n._demRaw===sn._demRaw;});
}
function restoreGraph(snap){
  // Variables are DOCUMENT state and are restored on both paths. snapshotIsEditorOnly() takes an
  // early return when only positions/selection changed, and a variable edit changes neither — so
  // restoring variables inside the full branch alone meant a variables-only undo hit the editor
  // path and reverted nothing. Measured: value stayed 0.75 after undo instead of returning to 0.25.
  if(Array.isArray(snap.variables))documentVariables=snap.variables.map(v=>({...v}));
  if(snapshotIsEditorOnly(snap)){
    snap.nodes.forEach(sn=>{const n=nodeById(sn.id);n.x=sn.x;n.y=sn.y;});
    selected=snap.selectedId==null?null:nodeById(snap.selectedId);
    selectedEdge=snap.selectedEdgeKey&&edgeByKey(snap.selectedEdgeKey)?snap.selectedEdgeKey:null;
    buildProps();drawGraph();updateHistoryButtons();return;
  }
  nodes=snap.nodes.map(n=>({...n,params:cloneParams(n.params),_inputs:n._inputs?[...n._inputs]:null,_field:null,_thumb:null,_dirty:true,
    _snowLayer:null,_temperatureC:null,_solarShadow:null,_solarExposure:null,_wind:null}));
  edges=snap.edges.map(e=>({...e}));uid=snap.uid;terrainDef=createTerrainDef(snap.terrainDef);
  H_SCALE=terrainDef.height/terrainDef.scale;
  selected=snap.selectedId==null?null:nodeById(snap.selectedId);
  selectedEdge=snap.selectedEdgeKey&&edgeByKey(snap.selectedEdgeKey)?snap.selectedEdgeKey:null;
  buildProps();evalGraph();updateHistoryButtons();
}
function undoGraph(){
  if(!undoStack.length)return;const cur=graphSnapshot(),snap=undoStack.pop();redoStack.push(cur);restoreGraph(snap);toast("Undo");
}
function redoGraph(){
  if(!redoStack.length)return;const cur=graphSnapshot(),snap=redoStack.pop();undoStack.push(cur);restoreGraph(snap);toast("Redo");
}
// Every node carrying a `seed` gets a fresh RANDOM one, 0..1000000. Taking the type default gave
// every Mountain seed 7, so three placed Mountains were three identical mountains and the whole
// place-and-combine workflow was pointless.
// The trade this makes: a graph is no longer reproducible from its construction order alone, because
// reloading re-rolls every seed. Reproducibility comes from the seed VALUES, which is why the Seed
// control is a number field you can read off and type back rather than a slider -- 1e6 of range
// through a few hundred pixels cannot address a specific value.
const SEED_MAX=1000000;
const randomSeed=()=>Math.floor(Math.random()*(SEED_MAX+1));
function makeNode(type,x,y){
  if(historyReady)recordHistory();
  const def=TYPES[type];const p={};def.params.forEach(pr=>p[pr.key]=pr.def);
  const nd={id:uid++,type,x,y,w:type==="colormixer"?190:150,params:p,_field:null,_thumb:null,_dirty:true,_dem:null,
    _snowLayer:null,_temperatureC:null,_solarShadow:null,_solarExposure:null,_wind:null};
  if(type==="colormixer"){
    nd._inputs=["Layer 1","Layer 2","Layer 3"];
    nd.params.layers=[{opacity:1,blend:"normal",edgeBlend:0},{opacity:1,blend:"normal",edgeBlend:0},
      {opacity:1,blend:"normal",edgeBlend:0}];
  }
  if(type==="drawmask")nd.params.strokes=[];
  if("seed"in p)p.seed=randomSeed();
  nodes.push(nd);return nd;
}
function nodeById(id){return nodes.find(n=>n.id===id);}
function edgeKey(e){return e?e.from+">"+e.to+":"+e.slot:null;}
function edgeByKey(key){return edges.find(e=>edgeKey(e)===key);}
export function inputEdge(nodeId,slot){return edges.find(e=>!e.disabled&&e.to===nodeId&&e.slot===slot);}
function outputNode(){return nodes.find(n=>n.type==="output");}
function collectScene(root){                        // walk the PRIMARY height/effect chain only
  const s={water:null,snow:null,satmap:null};root=root||outputNode();if(!root)return s;
  let nd=root;const seen=new Set();
  while(nd&&!seen.has(nd.id)){seen.add(nd.id);
    if(nd.type==="water"&&!s.water){
      const temperatureEdge=inputEdge(nd.id,1),temperatureNode=temperatureEdge&&nodeById(temperatureEdge.from);
      const temperatureField=temperatureNode&&fieldMetadata(temperatureNode._field)&&fieldMetadata(temperatureNode._field).kind==="temperature"
        ?temperatureNode._field:null;
      nd._inputError=temperatureEdge&&!temperatureField?"Temperature input requires a physical Temperature field":null;
      s.water={...nd.params,nodeId:nd.id,temperatureField};
    }
    if(nd.type==="snow"&&!s.snow){
      const temperatureEdge=inputEdge(nd.id,1),temperatureNode=temperatureEdge&&nodeById(temperatureEdge.from);
      const windEdge=inputEdge(nd.id,2),windNode=windEdge&&nodeById(windEdge.from);
      const windField=windNode&&windVectorFromField(windNode._field)?windNode._field:null;
      const errors=[];
      if(temperatureEdge&&!(temperatureNode&&temperatureCFromField(temperatureNode._field)))
        errors.push("Temperature input requires a physical Temperature field");
      if(windEdge&&!windField)errors.push("Wind input requires a physical Wind field");
      nd._inputError=errors.length?errors.join(" · "):null;
      s.snow={...nd.params,nodeId:nd.id,layer:nd._snowLayer,
        temperatureField:temperatureNode&&temperatureNode._field||null,windField};
    }
    if(nd.type==="satmap"&&!s.satmap)s.satmap={...nd.params,nodeId:nd.id};
    const e=inputEdge(nd.id,0);nd=e?nodeById(e.from):null;}
  return s;
}
function nearestUpstreamNode(type,root){
  root=root||activePreviewNode()||outputNode();if(!root)return null;
  const q=[root.id],seen=new Set();
  while(q.length){const id=q.shift();if(seen.has(id))continue;seen.add(id);const nd=nodeById(id);if(!nd)continue;
    if(nd.type===type)return nd;edges.filter(e=>!e.disabled&&e.to===id).forEach(e=>q.push(e.from));}
  return null;
}
function markDirtyFrom(id){ // mark node and everything downstream dirty
  const stack=[id];const seen=new Set();
  while(stack.length){const cur=stack.pop();if(seen.has(cur))continue;seen.add(cur);
    const nd=nodeById(cur);if(nd)nd._dirty=true;
    edges.filter(e=>!e.disabled&&e.from===cur).forEach(e=>stack.push(e.to));}
}
// Parameter edits on passthrough/effect nodes change colour or scene state, not height.
// Keep the cached downstream heightfield alive so a SatMap drag does not normalize and
// rebuild the entire mesh, normals, height texture, and hydrology as if geology changed.
function markParamDirty(nd){
  if(!nd)return;
  if(TYPES[nd.type]&&TYPES[nd.type].passthrough){nd._dirty=true;nd._thumb=null;}
  else markDirtyFrom(nd.id);
}
let evalFrame=0,buildRun=0,buildTimer=0,buildHideTimer=0;
const nextPaint=()=>new Promise(resolve=>requestAnimationFrame(resolve));
function ensureBuildTicks(){
  const el=$("#buildTicks");if(el.children.length)return;
  for(let i=0;i<20;i++)el.appendChild(document.createElement("i"));
}
function buildClock(ms){
  const sec=Math.floor(ms/1000);return String(Math.floor(sec/60)).padStart(2,"0")+":"+String(sec%60).padStart(2,"0");
}
function updateBuildHud(done,total,nodeName,started){
  ensureBuildTicks();
  const ratio=total?clamp(done/total,0,1):1,ticks=[...$("#buildTicks").children],filled=Math.floor(ratio*ticks.length+.0001);
  ticks.forEach((tick,i)=>{tick.classList.toggle("done",i<filled);tick.classList.toggle("active",done<total&&i===filled);});
  $("#buildTicks").setAttribute("aria-valuenow",Math.round(ratio*100));
  $("#buildElapsed").textContent=buildClock(performance.now()-started);
  $("#buildNode").textContent=done>=total?"Complete":nodeName||"Preparing";
}
function beginBuildHud(run,total,label){
  clearInterval(buildTimer);clearTimeout(buildHideTimer);ensureBuildTicks();
  const started=performance.now();$("#buildHud").hidden=false;$("#buildBtn").setAttribute("aria-busy","true");
  updateBuildHud(0,total,label,started);setStat("warn",(label||"Building terrain")+" · 0 / "+total);
  buildTimer=setInterval(()=>{if(run===buildRun)$("#buildElapsed").textContent=buildClock(performance.now()-started);},200);
  return started;
}
function finishBuildHud(run,total,started,completed){
  if(run!==buildRun)return;clearInterval(buildTimer);buildTimer=0;$("#buildBtn").removeAttribute("aria-busy");
  if(!completed){$("#buildHud").hidden=true;return;}
  updateBuildHud(total,total,"Complete",started);
  buildHideTimer=setTimeout(()=>{if(run===buildRun)$("#buildHud").hidden=true;},700);
}
function stopBuildHud(){
  clearInterval(buildTimer);clearTimeout(buildHideTimer);buildTimer=0;$("#buildHud").hidden=true;$("#buildBtn").removeAttribute("aria-busy");
}
function finishGraphEvaluation(t0,evals,colorDirty){
  const out=outputNode();const outF=out?out._field:null;
  const preview=activePreviewNode();
  scene=collectScene(preview);                     // effect nodes feeding the active viewport preview
  if(scene.satmap&&SATMAPS[scene.satmap.gradient]){
    satName=scene.satmap.gradient;if(typeof syncSatPicker==="function")syncSatPicker(false);
  }
  const previewMeta=preview&&fieldMetadata(preview._field);
  updateViewport(preview?(previewMeta&&previewMeta.heightField||preview._field):null,preview,{color:colorDirty});
  updatePreviewInfo(preview);
  redrawThumbs();
  const rng=outF?fieldRange(outF):[0,0];
  $("#statTime").textContent=(performance.now()-t0).toFixed(0)+" ms";
  $("#statNodes").textContent=nodes.length;
  $("#statOut").textContent=out?TYPES[out.type].name:"—";
  $("#statRange").textContent=outF?rng[0].toFixed(2)+" – "+rng[1].toFixed(2):"—";
  setStat(out?"ok":"warn",out?"Graph evaluated · "+evals+" nodes":"Add an Output node");
  drawGraph();if(drawTarget&&!$("#drawEditor").hidden){drawBaseField=null;renderDrawEditor();}
}
function evalGraph(){
  if(evalFrame){cancelAnimationFrame(evalFrame);evalFrame=0;}
  buildRun++;stopBuildHud();
  const t0=performance.now();let evals=0,colorDirty=false;
  function ev(id,guard){
    if(!id)return null;if(guard.has(id))return null;guard.add(id);
    const nd=nodeById(id);if(!nd){guard.delete(id);return null;}
    if(!nd._dirty&&nd._field){guard.delete(id);return nd._field;}
    const def=TYPES[nd.type];const want=demandedInputSlots(nd);
    const ins=nodeInputs(nd).map((_,s)=>{const e=inputEdge(id,s);
      if(!e||!want.has(s))return null;const up=ev(e.from,guard);return readInputValue(e,up);});
    const nt0=performance.now();let f,values;
    try{values=evaluateNodeValues(nd,ins);f=values.get(primaryPortId(nd));f=propagateFieldMetadata(f,ins,def);nd._evalError=null;nd._evalErrorCode=null;}
    catch(err){
      // A THROWN EVAL IS A VISIBLE FAILURE, not a flat field. Every one of these three paths
      // caught, logged to a console nobody has open, substituted newField() and cleared _dirty —
      // so a node that REFUSES to run renders as flat terrain and says nothing. The Sprint 3
      // audit found the sharpest case: S3.2 requires a Regolith duration to be authored with no
      // default, the plugin correctly throws when it is missing, and the product swallowed it.
      // The claim "duration is required" was true of the plugin and false of the application.
      // _inputError already draws a marker on the node and prints in the inspector; this uses
      // the same surface rather than inventing a second one.
      console.error("node",nd.type,err);nd._evalError=String(err&&err.message||err);nd._evalErrorCode=(err&&err.code)||null;
      f=newField();values=new Map([[primaryPortId(nd),f]]);}
    nd._lastMs=performance.now()-nt0;
    // _field stays a read-only ALIAS of the primary scalar raster, per ADR-002. Semantic data lives
    // in the per-output cache; nothing may write through the alias to reach it.
    nd._outputs=values;nd._field=f;nd._dirty=false;nd._thumb=null;evals++;
    if(nd.type!=="water"&&nd.type!=="snow")colorDirty=true;
    guard.delete(id);return f;
  }
  nodes.forEach(n=>ev(n.id,new Set()));             // eval all for thumbnails
  finishGraphEvaluation(t0,evals,colorDirty);
}
function graphEvalOrder(){
  const order=[],done=new Set(),visiting=new Set();
  function visit(nd){
    if(!nd||done.has(nd.id))return;if(visiting.has(nd.id))return;visiting.add(nd.id);
    nodeInputs(nd).forEach((_,slot)=>{const edge=inputEdge(nd.id,slot);if(edge)visit(nodeById(edge.from));});
    visiting.delete(nd.id);done.add(nd.id);order.push(nd);
  }
  nodes.forEach(visit);return order;
}
async function evalGraphProgressive(label="Building terrain"){
  if(evalFrame){cancelAnimationFrame(evalFrame);evalFrame=0;}
  const run=++buildRun,t0=performance.now(),order=graphEvalOrder();
  const work=order.filter(nd=>nd._dirty||!nd._field);let evals=0,colorDirty=false;
  if(!work.length){stopBuildHud();finishGraphEvaluation(t0,0,false);return true;}
  const started=beginBuildHud(run,work.length,label);let lastYield=performance.now();
  for(let i=0;i<work.length;i++){
    if(run!==buildRun)return false;
    const nd=work[i],def=TYPES[nd.type];
    updateBuildHud(i,work.length,def.name,started);
    // Yield before known-heavy nodes and periodically through quick chains. This lets the browser
    // paint truthful DAG progress without adding a frame of latency for every tiny passthrough node.
    if(i===0||nd._lastMs>8||i%4===0||performance.now()-lastYield>24){
      await nextPaint();lastYield=performance.now();if(run!==buildRun)return false;
    }
    const wantSlots=demandedInputSlots(nd);
    const ins=nodeInputs(nd).map((_,slot)=>{const edge=inputEdge(nd.id,slot);
      if(!edge||!wantSlots.has(slot))return null;return readInputValue(edge,(nodeById(edge.from)||{})._field||null);});
    const nt0=performance.now();let f;
    let values;
    try{values=evaluateNodeValues(nd,ins);f=values.get(primaryPortId(nd));f=propagateFieldMetadata(f,ins,def);nd._evalError=null;nd._evalErrorCode=null;}
    catch(err){console.error("node",nd.type,err);nd._evalError=String(err&&err.message||err);nd._evalErrorCode=(err&&err.code)||null;f=newField();}
    nd._lastMs=performance.now()-nt0;nd._outputs=values||new Map([[primaryPortId(nd),f]]);
    nd._field=f;nd._dirty=false;nd._thumb=null;evals++;
    if(nd.type!=="water"&&nd.type!=="snow")colorDirty=true;
    updateBuildHud(i+1,work.length,def.name,started);
    setStat("warn",label+" · "+(i+1)+" / "+work.length);
    if(nd._lastMs>18||performance.now()-lastYield>24){
      await nextPaint();lastYield=performance.now();if(run!==buildRun)return false;
    }
  }
  finishGraphEvaluation(t0,evals,colorDirty);finishBuildHud(run,work.length,started,true);return true;
}
function requestEval(){
  if(!AUTO){drawGraph();return;}
  // Slider/pointer events can arrive much faster than a terrain frame. Coalesce the
  // burst to the newest value instead of synchronously evaluating every stale value.
  if(evalFrame)return;
  evalFrame=requestAnimationFrame(()=>{evalFrame=0;evalGraphProgressive("Updating terrain");});
}

/* =====================================================================
   THUMBNAILS (hillshaded preview baked per node)
   ===================================================================== */
const TH=48;
function bakeThumb(nd){
  // TYPES[nd.type] may be absent: a node whose plugin failed to register, and the probe fixtures
  // that drive bakeThumb directly with a synthetic node. Before the preview-adapter hook existed
  // this function never consulted TYPES at all, so an unregistered type baked a plain thumbnail
  // rather than throwing. Keep that: a missing descriptor means "no adapter", not a crash.
  const raw=nd._field;if(!raw)return null;const adapter=TYPES[nd.type]?.previewAdapter;
  const f=adapter?adapter(raw,terrainDef):raw;
  const c=document.createElement("canvas");c.width=TH;c.height=TH;const ctx=c.getContext("2d");
  const img=ctx.createImageData(TH,TH);const n=fieldW(),nh=fieldH();
  const range=TYPES[nd.type]?.previewRange,[mn,mx]=range||fieldRange(f);const d=mx-mn||1;
  // sampleBilinear reads WORLD position in cell units. The hex world is only (n-1)*sqrt(3)/2
  // cells tall, so walking sy over raw grid indices runs 13.4% past the bottom and clamps onto
  // the last lattice row - measured: 6 of 48 thumbnail rows came back byte-identical on hex,
  // 0 of 48 on square.
  const rowScale=isHex()?HEX_ROW:1;
  for(let y=0;y<TH;y++)for(let x=0;x<TH;x++){
    const sx=x/TH*(n-1),sy=y/TH*(nh-1)*rowScale;
    const h=(sampleBilinear(f,sx,sy)-mn)/d;
    const hl=(sampleBilinear(f,sx-1,sy)-mn)/d,hr=(sampleBilinear(f,sx+1,sy)-mn)/d;
    const hu=(sampleBilinear(f,sx,sy-1)-mn)/d,hd=(sampleBilinear(f,sx,sy+1)-mn)/d;
    const nx=(hl-hr),ny=(hu-hd),nz=0.12;const L=Math.hypot(nx,ny,nz)||1;
    const sh=clamp((nx*0.5+ny*0.6+nz*0.6)/L,0,1);
    const col=hyps(h);const s=0.35+0.85*sh;
    const i=(y*TH+x)*4;img.data[i]=col[0]*s;img.data[i+1]=col[1]*s;img.data[i+2]=col[2]*s;img.data[i+3]=255;
  }
  ctx.putImageData(img,0,0);return c;
}
function bakeColorThumb(nd,col){
  const f=nd._field;if(!f||!col)return null;
  const c=document.createElement("canvas");c.width=TH;c.height=TH;const ctx=c.getContext("2d");
  const img=ctx.createImageData(TH,TH),n=fieldW(),nh=fieldH(),[mn,mx]=fieldRange(f),d=mx-mn||1;
  const rgbAt=(sx,sy,ch)=>{
    sx=clamp(sx,0,n-1);sy=clamp(sy,0,nh-1);
    const x0=Math.floor(sx),y0=Math.floor(sy),x1=Math.min(x0+1,n-1),y1=Math.min(y0+1,nh-1),tx=sx-x0,ty=sy-y0;
    const a=col[(y0*n+x0)*3+ch]*(1-tx)+col[(y0*n+x1)*3+ch]*tx;
    const b=col[(y1*n+x0)*3+ch]*(1-tx)+col[(y1*n+x1)*3+ch]*tx;
    return a*(1-ty)+b*ty;
  };
  // Two coordinate spaces here, and they are NOT the same on hex: sampleBilinear takes a WORLD
  // position in cell units, while rgbAt above indexes the colour array by grid ROW. Keep them
  // apart - conflating them shifts the shading against the colour by 13.4% of the image.
  const rowScale=isHex()?HEX_ROW:1;
  for(let y=0;y<TH;y++)for(let x=0;x<TH;x++){
    const sx=x/(TH-1)*(n-1),syRow=y/(TH-1)*(nh-1),sy=syRow*rowScale;
    const hl=(sampleBilinear(f,sx-1,sy)-mn)/d,hr=(sampleBilinear(f,sx+1,sy)-mn)/d;
    const hu=(sampleBilinear(f,sx,sy-1)-mn)/d,hd=(sampleBilinear(f,sx,sy+1)-mn)/d;
    const nx=hl-hr,ny=hu-hd,nz=.16,L=Math.hypot(nx,ny,nz)||1;
    const sh=.62+.52*clamp((nx*.5+ny*.6+nz*.6)/L,0,1),i=(y*TH+x)*4;
    img.data[i]=Math.round(clamp(rgbAt(sx,syRow,0)*sh,0,1)*255);
    img.data[i+1]=Math.round(clamp(rgbAt(sx,syRow,1)*sh,0,1)*255);
    img.data[i+2]=Math.round(clamp(rgbAt(sx,syRow,2)*sh,0,1)*255);   // syRow, not sy: rgbAt indexes a GRID ROW like channels 0-1 above; passing world y sheared the blue channel 13.4% on hex
    img.data[i+3]=255;
  }
  ctx.putImageData(img,0,0);return c;
}
function hyps(h){ // hypsometric tint 0..1
  const stops=[[0.0,[38,58,84]],[0.28,[54,92,74]],[0.45,[120,132,86]],[0.62,[150,124,86]],[0.78,[128,96,72]],[0.92,[196,190,182]],[1,[245,247,250]]];
  h=clamp(h,0,1);for(let i=0;i<stops.length-1;i++){if(h<=stops[i+1][0]){const t=(h-stops[i][0])/(stops[i+1][0]-stops[i][0]||1);
    return[lerp(stops[i][1][0],stops[i+1][1][0],t),lerp(stops[i][1][1],stops[i+1][1][1],t),lerp(stops[i][1][2],stops[i+1][1][2],t)];}}
  return stops[stops.length-1][1];
}
function redrawThumbs(){nodes.forEach(n=>{if(!n._thumb)n._thumb=bakeThumb(n);});}

/* =====================================================================
   GRAPH EDITOR (canvas)
   ===================================================================== */
const gc=$("#graph"),gx=gc.getContext("2d");
let view={x:60,y:70,z:1};
let drag=null,linking=null,hoverPort=null,hoverEdge=null;
function css(v){return getComputedStyle(document.documentElement).getPropertyValue(v).trim();}
function resizeGraph(){const r=gc.parentElement.getBoundingClientRect();const dpr=Math.min(2,devicePixelRatio||1);
  gc.width=r.width*dpr;gc.height=r.height*dpr;gc.style.width=r.width+"px";gc.style.height=r.height+"px";gx.setTransform(dpr,0,0,dpr,0,0);drawGraph();}
function toWorld(mx,my){return{x:(mx-view.x)/view.z,y:(my-view.y)/view.z};}
// Height must clear BOTH port columns. With one output — every type today — the outputs term is
// inert, so this is byte-identical to the previous single-output layout.
function nodeH(nd){const n=nodeInputs(nd).length,m=nodeOutputs(nd).length;
  const base=nd.type==="colormixer"?Math.max(30+TH+8,38+n*15):30+TH+8;
  return m>1?Math.max(base,38+m*15):base;}
function portPos(nd,which,slot){
  const h=nodeH(nd);
  if(which==="out"){
    const m=nodeOutputs(nd).length;
    // One output keeps the exact previous geometry — centred on the node's right edge — so the
    // single-output layout every existing oracle measures is unchanged to the pixel.
    if(m<=1)return{x:nd.x+nd.w,y:nd.y+h/2};
    const gapY=h/(m+1);return{x:nd.x+nd.w,y:nd.y+gapY*((slot||0)+1)};
  }
  const ins=nodeInputs(nd),n=ins.length;
  if(nd.type==="colormixer")return{x:nd.x,y:nd.y+31+(slot+.5)*(h-36)/Math.max(n,1)};
  const gapY=h/(n+1);return{x:nd.x,y:nd.y+gapY*(slot+1)};
}
function drawGraph(){
  const w=gc.clientWidth,h=gc.clientHeight;gx.clearRect(0,0,w,h);
  // grid
  gx.save();const g=18*view.z,ox=view.x%g,oy=view.y%g;
  gx.strokeStyle=css("--line")+"55";gx.lineWidth=1;gx.beginPath();
  for(let x=ox;x<w;x+=g){gx.moveTo(x,0);gx.lineTo(x,h);}for(let y=oy;y<h;y+=g){gx.moveTo(0,y);gx.lineTo(w,y);}gx.stroke();
  const g2=90*view.z,ox2=view.x%g2,oy2=view.y%g2;gx.strokeStyle=css("--line")+"aa";gx.beginPath();
  for(let x=ox2;x<w;x+=g2){gx.moveTo(x,0);gx.lineTo(x,h);}for(let y=oy2;y<h;y+=g2){gx.moveTo(0,y);gx.lineTo(w,y);}gx.stroke();
  gx.restore();
  gx.save();gx.translate(view.x,view.y);gx.scale(view.z,view.z);
  // edges
  edges.forEach(e=>{const a=nodeById(e.from),b=nodeById(e.to);if(!a||!b)return;
    const p0=portPos(a,"out",outSlotForEdge(e)),p1=portPos(b,"in",e.slot),key=edgeKey(e);
    const state=selectedEdge===key?"selected":hoverEdge===key?"hover":(!selectedEdge&&selected&&(selected.id===a.id||selected.id===b.id))?"related":"normal";
    drawWire(p0,p1,state,!!e.disabled);if(selectedEdge===key)drawEdgeDeleteHandle(p0,p1);});
  if(linking){const p0=portPos(nodeById(linking.from),"out",linking.fromSlot||0);drawWire(p0,linking.cur,"selected",true);}
  // nodes
  nodes.forEach(nd=>drawNode(nd));
  gx.restore();
}
function wireCurve(p0,p1){
  const dx=Math.max(30,Math.abs(p1.x-p0.x)*0.5);
  return{p0,p1,c0:{x:p0.x+dx,y:p0.y},c1:{x:p1.x-dx,y:p1.y}};
}
function wirePoint(p0,p1,t){
  const c=wireCurve(p0,p1),u=1-t;
  return{x:u*u*u*p0.x+3*u*u*t*c.c0.x+3*u*t*t*c.c1.x+t*t*t*p1.x,
    y:u*u*u*p0.y+3*u*u*t*c.c0.y+3*u*t*t*c.c1.y+t*t*t*p1.y};
}
function drawWire(p0,p1,state,dashed){
  const c=wireCurve(p0,p1),active=state!=="normal";
  gx.save();
  if(state==="selected"){gx.shadowColor=css("--accent");gx.shadowBlur=8/view.z;}
  gx.beginPath();gx.moveTo(p0.x,p0.y);gx.bezierCurveTo(c.c0.x,c.c0.y,c.c1.x,c.c1.y,p1.x,p1.y);
  gx.lineWidth=(state==="selected"?3.6:state==="hover"?3:active?2.4:1.8)/view.z;
  gx.strokeStyle=state==="selected"?css("--accent"):state==="hover"?css("--text"):active?css("--accent"):css("--line2");
  gx.globalAlpha=dashed ? .52 : 1;
  if(dashed)gx.setLineDash([7/view.z,6/view.z]);gx.stroke();gx.restore();
}
function drawEdgeDeleteHandle(p0,p1){
  const p=wirePoint(p0,p1,.5),r=8.5/view.z;
  gx.save();gx.beginPath();gx.arc(p.x,p.y,r,0,Math.PI*2);gx.fillStyle=css("--panel");gx.fill();
  gx.lineWidth=1.5/view.z;gx.strokeStyle=css("--accent");gx.stroke();
  gx.fillStyle=css("--text");gx.font=`${12/view.z}px ${css("--sans")}`;gx.textAlign="center";gx.textBaseline="middle";
  gx.fillText("×",p.x,p.y-.5/view.z);gx.restore();
}
function pointSegmentDistance(px,py,ax,ay,bx,by){
  const dx=bx-ax,dy=by-ay,d=dx*dx+dy*dy||1,t=clamp(((px-ax)*dx+(py-ay)*dy)/d,0,1);
  return Math.hypot(px-(ax+dx*t),py-(ay+dy*t));
}
function edgeAt(wx,wy){
  const tolerance=11/view.z;
  for(let ei=edges.length-1;ei>=0;ei--){const e=edges[ei],a=nodeById(e.from),b=nodeById(e.to);if(!a||!b)continue;
    const p0=portPos(a,"out",outSlotForEdge(e)),p1=portPos(b,"in",e.slot);let prev=p0;
    for(let i=1;i<=28;i++){const p=wirePoint(p0,p1,i/28);
      if(pointSegmentDistance(wx,wy,prev.x,prev.y,p.x,p.y)<=tolerance)return e;prev=p;}}
  return null;
}
function edgeDeleteAt(wx,wy){
  const e=edgeByKey(selectedEdge);if(!e)return null;const a=nodeById(e.from),b=nodeById(e.to);if(!a||!b)return null;
  const p=wirePoint(portPos(a,"out",outSlotForEdge(e)),portPos(b,"in",e.slot),.5);
  return Math.hypot(wx-p.x,wy-p.y)<=11/view.z?e:null;
}
function roundRect(x,y,w,h,r){gx.beginPath();gx.moveTo(x+r,y);gx.arcTo(x+w,y,x+w,y+h,r);gx.arcTo(x+w,y+h,x,y+h,r);gx.arcTo(x,y+h,x,y,r);gx.arcTo(x,y,x+w,y,r);gx.closePath();}
function drawNode(nd){
  const def=TYPES[nd.type],h=nodeH(nd),sel=selected&&selected.id===nd.id;
  const shown=activePreviewNode()&&activePreviewNode().id===nd.id;
  const cc=css(CAT[def.cat].c);
  gx.save();
  gx.shadowColor="rgba(0,0,0,.5)";gx.shadowBlur=sel?18:9;gx.shadowOffsetY=4;
  roundRect(nd.x,nd.y,nd.w,h,8);gx.fillStyle=css("--panel2");gx.fill();
  gx.shadowColor="transparent";
  roundRect(nd.x,nd.y,nd.w,h,8);gx.lineWidth=sel?2:1;gx.strokeStyle=sel?css("--accent"):css("--line2");gx.stroke();
  // category stripe
  gx.save();roundRect(nd.x,nd.y,nd.w,h,8);gx.clip();gx.fillStyle=cc;gx.fillRect(nd.x,nd.y,nd.w,3);gx.restore();
  // title
  gx.fillStyle=css("--text");gx.font="600 11px "+css("--sans").split(",")[0]+",sans-serif";gx.textBaseline="middle";
  gx.fillText(def.name,nd.x+10,nd.y+16,nd.w-18);
  if(shown){gx.beginPath();gx.arc(nd.x+nd.w-11,nd.y+16,4,0,6.2832);gx.fillStyle="#62a8ff";gx.fill();}
  // thumb
  const tx=nd.type==="colormixer"?nd.x+nd.w-TH-8:nd.x+nd.w/2-TH/2,ty=nd.y+28;
  if(nd._thumb){gx.drawImage(nd._thumb,tx,ty,TH,TH);}else{gx.fillStyle=css("--panel3");gx.fillRect(tx,ty,TH,TH);}
  if(nd._lastMs!=null){gx.fillStyle=css("--faint");gx.font="9px "+css("--mono");gx.textBaseline="alphabetic";
    gx.fillText(nd._lastMs<10?nd._lastMs.toFixed(1)+" ms":Math.round(nd._lastMs)+" ms",nd.x+7,nd.y+h-7);}
  if(nd._inputError||nd._evalError){gx.beginPath();gx.arc(nd.x+nd.w-9,nd.y+h-8,4,0,7);gx.fillStyle=css("--bad");gx.fill();}
  gx.strokeStyle=css("--line");gx.lineWidth=1;gx.strokeRect(tx+.5,ty+.5,TH-1,TH-1);
  // ports
  nodeInputs(nd).forEach((nm,s)=>{const p=portPos(nd,"in",s);drawPort(p,cc,hoverPort&&hoverPort.node===nd.id&&hoverPort.which==="in"&&hoverPort.slot===s);
    gx.fillStyle=css("--muted");gx.font="9px "+css("--mono");gx.textAlign="left";gx.fillText(nm,p.x+8,p.y);gx.textAlign="left";});
  // One output port per declared output. `cat!=="out"` remains the rule for having outputs at all
  // — the Output node is the one sink — and nodeOutputs returns [] for it.
  nodeOutputs(nd).forEach((op,s)=>{const p=portPos(nd,"out",s);
    drawPort(p,css("--accent"),hoverPort&&hoverPort.node===nd.id&&hoverPort.which==="out"&&(hoverPort.slot||0)===s);
    if(nodeOutputs(nd).length>1){gx.fillStyle=css("--muted");gx.font="9px "+css("--mono");gx.textAlign="right";
      gx.fillText(op.name||op.id,p.x-8,p.y);gx.textAlign="left";}});
  gx.restore();
}
function drawPort(p,color,hot){gx.beginPath();gx.arc(p.x,p.y,hot?6:4.5,0,7);gx.fillStyle=hot?css("--accent"):css("--panel");gx.fill();
  gx.lineWidth=2;gx.strokeStyle=color;gx.stroke();}
function nodeAt(wx,wy){for(let i=nodes.length-1;i>=0;i--){const nd=nodes[i],h=nodeH(nd);
  if(wx>=nd.x&&wx<=nd.x+nd.w&&wy>=nd.y&&wy<=nd.y+h)return nd;}return null;}
function portAt(wx,wy){
  const hit=12/view.z;                                        // fixed ~12 px target at every graph zoom
  let best=null,bestDistance=hit;
  for(let i=nodes.length-1;i>=0;i--){const nd=nodes[i],def=TYPES[nd.type];
    const outs=nodeOutputs(nd);
    for(let s=0;s<outs.length;s++){const p=portPos(nd,"out",s),d=Math.hypot(wx-p.x,wy-p.y);
      if(d<bestDistance){bestDistance=d;best={node:nd.id,which:"out",slot:s};}}
    for(let s=0;s<nodeInputs(nd).length;s++){const p=portPos(nd,"in",s),d=Math.hypot(wx-p.x,wy-p.y);
      if(d<bestDistance){bestDistance=d;best={node:nd.id,which:"in",slot:s};}}}
  return best;
}

/* ---- interaction ---- */
let spaceDown=false;
gc.addEventListener("mousedown",e=>{
  const r=gc.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;const w=toWorld(mx,my);
  if(e.button===2)return;                                      // right-click belongs to the graph context menu
  if(e.button===1||spaceDown||(e.button===0&&e.altKey)){e.preventDefault();drag={pan:true,sx:mx,sy:my,vx:view.x,vy:view.y};gc.classList.add("panning");return;}
  const port=portAt(w.x,w.y);
  if(port){
    if(port.which==="out"){linking={from:port.node,fromSlot:port.slot||0,cur:w};gc.classList.add("linking");}
    else{const ex=inputEdge(port.node,port.slot);if(ex){linking={from:ex.from,fromSlot:outSlotForEdge(ex),cur:w,original:ex};gc.classList.add("linking");}}
    return;
  }
  const edgeDelete=edgeDeleteAt(w.x,w.y);
  if(edgeDelete){deleteEdge(edgeDelete);return;}
  const nd=nodeAt(w.x,w.y);
  if(nd){select(nd);drag={node:nd,dx:w.x-nd.x,dy:w.y-nd.y,moved:false,before:graphSnapshot()};}
  else{const edge=edgeAt(w.x,w.y);
    if(edge)selectEdge(edge);
    else{select(null);drag={pan:true,sx:mx,sy:my,vx:view.x,vy:view.y};gc.classList.add("panning");}}
  drawGraph();
});
const _pk=a=>a?a.node+":"+a.which+":"+(a.slot==null?"":a.slot):"";   // hover-port identity key
window.addEventListener("mousemove",e=>{
  const r=gc.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,w=toWorld(mx,my);
  if(drag&&drag.pan){view.x=drag.vx+(mx-drag.sx);view.y=drag.vy+(my-drag.sy);drawGraph();return;}
  if(drag&&drag.node){drag.node.x=w.x-drag.dx;drag.node.y=w.y-drag.dy;drag.moved=true;drawGraph();return;}
  if(linking){linking.cur=w;drawGraph();return;}
  const inside=e.clientX>=r.left&&e.clientX<=r.right&&e.clientY>=r.top&&e.clientY<=r.bottom;   // only hover over the graph
  const hp=inside?portAt(w.x,w.y):null,nd=inside?nodeAt(w.x,w.y):null;
  const he=inside&&!hp&&!nd?edgeAt(w.x,w.y):null,deleteHot=inside?edgeDeleteAt(w.x,w.y):null;
  if(inside)gc.style.cursor=hp?"crosshair":nd?"move":(he||deleteHot)?"pointer":"grab";
  if(_pk(hp)!==_pk(hoverPort)||edgeKey(he)!==hoverEdge){hoverPort=hp;hoverEdge=edgeKey(he);drawGraph();} // redraw on enter AND leave
});
window.addEventListener("mouseup",e=>{
  if(linking){
    const r=gc.getBoundingClientRect();
    const inside=e.clientX>=r.left&&e.clientX<=r.right&&e.clientY>=r.top&&e.clientY<=r.bottom;
    const w=toWorld(e.clientX-r.left,e.clientY-r.top);const port=inside?portAt(w.x,w.y):null;
    if(port&&port.which==="in"&&port.node!==linking.from){
      // Cycles, self-links and type refusals all land here now, and all of them leave the graph
      // exactly as it was — linkDrop mutates only after every check has passed.
      const verdict=linkDrop(linking.from,linking.fromSlot||0,port.node,port.slot,{replacing:linking.original});
      if(!verdict.ok)toast(verdict.reason||("Cannot connect ("+verdict.code+")"));
    }else if(inside&&!nodeAt(w.x,w.y)&&!edgeAt(w.x,w.y)){
      // Gaea-style drag-out quick create: keep the graph unchanged until the user actually
      // chooses a compatible node. Releasing on empty space is therefore cancellable, and an
      // input rewire keeps its original edge until the replacement node is committed.
      const pending={from:linking.from,original:linking.original||null};
      linking=null;gc.classList.remove("linking");drawGraph();
      openMenu(e.clientX,e.clientY,w,pending);
    }
    if(linking){linking=null;gc.classList.remove("linking");drawGraph();}
  }
  if(drag){if(drag.node&&drag.moved)pushUndo(drag.before);gc.classList.remove("panning");drag=null;}
});
function wouldCycle(from,to){ // does 'to' already feed 'from'?
  const stack=[from];const seen=new Set();
  while(stack.length){const c=stack.pop();if(c===to)return true;if(seen.has(c))continue;seen.add(c);
    edges.filter(e=>e.to===c).forEach(e=>stack.push(e.from));}
  return false;
}

/* ---- deterministic layered graph organization (editor-only; never dirties terrain fields) ---- */
function graphIdsFrom(seedId,mode){
  if(seedId==null)return new Set(nodes.map(n=>n.id));
  const found=new Set(),stack=[seedId];
  while(stack.length){const id=stack.pop();if(found.has(id))continue;found.add(id);
    if(mode==="up"||mode==="connected")edges.filter(e=>e.to===id).forEach(e=>stack.push(e.from));
    if(mode==="down"||mode==="connected")edges.filter(e=>e.from===id).forEach(e=>stack.push(e.to));}
  return found;
}
function weakComponents(ids){
  const left=new Set(ids),out=[];
  while(left.size){const seed=Math.min(...left),part=new Set(),stack=[seed];
    while(stack.length){const id=stack.pop();if(part.has(id)||!ids.has(id))continue;part.add(id);left.delete(id);
      edges.forEach(e=>{if(e.from===id&&ids.has(e.to))stack.push(e.to);if(e.to===id&&ids.has(e.from))stack.push(e.from);});}
    out.push(part);}
  return out.sort((a,b)=>Math.min(...a)-Math.min(...b));
}
function layoutComponent(ids){
  const ns=nodes.filter(n=>ids.has(n.id)),rank=new Map(ns.map(n=>[n.id,0])),deg=new Map(ns.map(n=>[n.id,0]));
  const es=edges.filter(e=>ids.has(e.from)&&ids.has(e.to));
  es.forEach(e=>deg.set(e.to,deg.get(e.to)+1));
  const queue=ns.filter(n=>deg.get(n.id)===0).sort((a,b)=>a.id-b.id),topo=[];
  while(queue.length){const nd=queue.shift();topo.push(nd);
    es.filter(e=>e.from===nd.id).sort((a,b)=>a.slot-b.slot||a.to-b.to).forEach(e=>{
      rank.set(e.to,Math.max(rank.get(e.to),rank.get(nd.id)+1));deg.set(e.to,deg.get(e.to)-1);
      if(deg.get(e.to)===0){queue.push(nodeById(e.to));queue.sort((a,b)=>a.id-b.id);}});}
  // Cycles are rejected by the editor; this fallback keeps corrupt/imported graphs arrangeable.
  ns.filter(n=>!topo.includes(n)).sort((a,b)=>a.id-b.id).forEach(n=>topo.push(n));
  const maxRank=Math.max(0,...rank.values()),layers=Array.from({length:maxRank+1},()=>[]);
  topo.forEach(n=>layers[rank.get(n.id)].push(n));
  layers.forEach(L=>L.sort((a,b)=>a.y-b.y||a.id-b.id));
  const rebuildOrder=()=>{const m=new Map();layers.forEach(L=>L.forEach((n,i)=>m.set(n.id,i)));return m;};
  const reorder=(L,neighbours,order)=>{
    const prior=new Map(L.map((n,i)=>[n.id,i]));
    L.sort((a,b)=>{const av=neighbours(a),bv=neighbours(b);
      const aa=av.length?av.reduce((s,e)=>s+(order.get(e.id)||0)+((e.slot||0)*.015),0)/av.length:prior.get(a.id);
      const bb=bv.length?bv.reduce((s,e)=>s+(order.get(e.id)||0)+((e.slot||0)*.015),0)/bv.length:prior.get(b.id);
      return aa-bb||prior.get(a.id)-prior.get(b.id)||a.id-b.id;});
  };
  for(let pass=0;pass<4;pass++){
    let order=rebuildOrder();
    for(let l=1;l<layers.length;l++){reorder(layers[l],n=>es.filter(e=>e.to===n.id).map(e=>({id:e.from,slot:e.slot})),order);order=rebuildOrder();}
    order=rebuildOrder();
    for(let l=layers.length-2;l>=0;l--){reorder(layers[l],n=>es.filter(e=>e.from===n.id).map(e=>({id:e.to,slot:e.slot})),order);order=rebuildOrder();}
  }
  const COL_GAP=82,ROW_GAP=36,widths=layers.map(L=>Math.max(150,...L.map(n=>n.w))),xs=[];let x=0;
  widths.forEach((w,i)=>{xs[i]=x;x+=w+COL_GAP;});
  const heights=layers.map(L=>L.reduce((s,n)=>s+nodeH(n),0)+Math.max(0,L.length-1)*ROW_GAP);
  const H=Math.max(1,...heights),pos=new Map();
  layers.forEach((L,l)=>{let y=(H-heights[l])*.5;L.forEach(n=>{pos.set(n.id,{x:xs[l],y});y+=nodeH(n)+ROW_GAP;});});
  return{pos,width:Math.max(1,x-COL_GAP),height:H};
}
function frameGraph(ids){
  ids=ids?new Set(ids):new Set(nodes.map(n=>n.id));const ns=nodes.filter(n=>ids.has(n.id));if(!ns.length)return;
  const minX=Math.min(...ns.map(n=>n.x)),minY=Math.min(...ns.map(n=>n.y));
  const maxX=Math.max(...ns.map(n=>n.x+n.w)),maxY=Math.max(...ns.map(n=>n.y+nodeH(n)));
  const inset=$("#graphwrap").classList.contains("toolbox-open")?248:0,pad=54;
  const aw=Math.max(80,gc.clientWidth-inset),ah=Math.max(80,gc.clientHeight);
  view.z=clamp(Math.min((aw-pad*2)/Math.max(1,maxX-minX),(ah-pad*2)/Math.max(1,maxY-minY)),.35,1.35);
  view.x=inset+(aw-(maxX-minX)*view.z)*.5-minX*view.z;
  view.y=(ah-(maxY-minY)*view.z)*.5-minY*view.z;drawGraph();
}
function organizeGraph(ids,anchorId,label){
  ids=ids?new Set(ids):new Set(nodes.map(n=>n.id));if(!ids.size)return null;
  const components=weakComponents(ids),target=new Map();let y=0,maxW=0;
  components.forEach(comp=>{const z=layoutComponent(comp);z.pos.forEach((p,id)=>target.set(id,{x:p.x,y:p.y+y}));
    y+=z.height+96;maxW=Math.max(maxW,z.width);});
  const arranged=nodes.filter(n=>ids.has(n.id)),oldMinX=Math.min(...arranged.map(n=>n.x)),oldMinY=Math.min(...arranged.map(n=>n.y));
  let dx=oldMinX,dy=oldMinY;
  if(anchorId!=null&&target.has(anchorId)){const a=nodeById(anchorId),p=target.get(anchorId);dx=a.x-p.x;dy=a.y-p.y;}
  const before=graphSnapshot();let changed=false;
  arranged.forEach(n=>{const p=target.get(n.id),nx=Math.round((p.x+dx)*2)/2,ny=Math.round((p.y+dy)*2)/2;
    if(Math.abs(nx-n.x)>.01||Math.abs(ny-n.y)>.01)changed=true;n.x=nx;n.y=ny;});
  if(changed)pushUndo(before);frameGraph(ids);toast((label||"Organized graph")+" · "+arranged.length+" nodes");
  return{changed,count:arranged.length,components:components.length,width:maxW,height:y?y-96:0};
}

/* ---- graph context menu: occasional graph/node operations without permanent toolbar clutter ---- */
const graphMenu=$("#graphMenu");let graphMenuPoint=null;
function closeGraphMenu(){graphMenu.classList.remove("open");graphMenu.innerHTML="";}
function graphMenuItem(label,icon,action,shortcut,danger){
  const b=document.createElement("button");b.type="button";b.className="graph-menu-item"+(danger?" danger":"");
  b.setAttribute("role","menuitem");b.innerHTML=`<span class="ico">${icon}</span><span>${label}</span>${shortcut?`<small>${shortcut}</small>`:""}`;
  b.onclick=()=>{closeGraphMenu();action();};graphMenu.appendChild(b);
}
function graphMenuSep(){const d=document.createElement("div");d.className="graph-menu-sep";d.setAttribute("role","separator");graphMenu.appendChild(d);}
function openGraphMenu(clientX,clientY,nd,world,edge){
  closeMenu();closeGraphMenu();graphMenuPoint={clientX,clientY,world,nodeId:nd?nd.id:null,edgeKey:edgeKey(edge)};
  const title=document.createElement("div");title.className="graph-menu-title";title.textContent=edge?"Connection":nd?TYPES[nd.type].name:"Graph";graphMenu.appendChild(title);
  if(edge){
    const from=nodeById(edge.from),to=nodeById(edge.to),input=nodeInputs(to)[edge.slot]||("Input "+(edge.slot+1));
    graphMenuItem("Connection properties","◎",()=>selectEdge(edge));
    graphMenuItem(edge.disabled?"Enable connection":"Mute connection",edge.disabled?"▶":"Ⅱ",()=>toggleEdge(edge,!!edge.disabled));
    graphMenuSep();
    graphMenuItem("Select source","←",()=>select(from));
    graphMenuItem("Select target · "+input,"→",()=>select(to));
    graphMenuSep();
    graphMenuItem("Disconnect","×",()=>deleteEdge(edge),"Del",true);
    graphMenuSep();
  }else if(nd){
    graphMenuItem("Preview this node","◉",()=>{select(nd);previewMode="selected";refreshPreview();});
    graphMenuItem("Organize connected branch","⌘",()=>organizeGraph(graphIdsFrom(nd.id,"connected"),nd.id,"Organized connected branch"));
    graphMenuItem("Organize upstream","←",()=>organizeGraph(graphIdsFrom(nd.id,"up"),nd.id,"Organized upstream"));
    graphMenuItem("Organize downstream","→",()=>organizeGraph(graphIdsFrom(nd.id,"down"),nd.id,"Organized downstream"));
    graphMenuItem("Frame connected branch","⤢",()=>frameGraph(graphIdsFrom(nd.id,"connected")));
    graphMenuSep();
    graphMenuItem("Duplicate","⧉",()=>{select(nd);duplicateSel();},"Ctrl+D");
    graphMenuItem("Delete","×",()=>{select(nd);deleteSel();},"Del",true);
    graphMenuSep();
  }else{
    graphMenuItem("Add node here…","＋",()=>openMenu(clientX,clientY,world));
    graphMenuItem("Open node toolbox","▤",()=>setNodeToolbox(true));
    graphMenuSep();
  }
  graphMenuItem("Organize all nodes","⌘",()=>organizeGraph(null,null,"Organized graph"));
  graphMenuItem("Frame all nodes","⤢",()=>frameGraph());
  graphMenu.classList.add("open");
  const mw=224,mh=graphMenu.offsetHeight;
  graphMenu.style.left=Math.max(6,Math.min(clientX,window.innerWidth-mw-6))+"px";
  graphMenu.style.top=Math.max(6,Math.min(clientY,window.innerHeight-mh-6))+"px";
}
gc.addEventListener("contextmenu",e=>{e.preventDefault();const r=gc.getBoundingClientRect();
  const w=toWorld(e.clientX-r.left,e.clientY-r.top),port=portAt(w.x,w.y);
  let edge=null;if(port&&port.which==="in")edge=edges.find(x=>x.to===port.node&&x.slot===port.slot)||null;
  else if(port&&port.which==="out"){const outgoing=edges.filter(x=>x.from===port.node);if(outgoing.length===1)edge=outgoing[0];}
  const nd=edge?null:nodeAt(w.x,w.y);if(!edge&&!nd)edge=edgeAt(w.x,w.y);
  if(nd)select(nd);else if(edge)selectEdge(edge);
  openGraphMenu(e.clientX,e.clientY,nd,w,edge);});
window.addEventListener("mousedown",e=>{if(graphMenu.classList.contains("open")&&!graphMenu.contains(e.target))closeGraphMenu();});

gc.addEventListener("wheel",e=>{e.preventDefault();const r=gc.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
  const f=e.deltaY<0?1.1:1/1.1;const nz=clamp(view.z*f,0.35,2.4);
  view.x=mx-(mx-view.x)*(nz/view.z);view.y=my-(my-view.y)*(nz/view.z);view.z=nz;drawGraph();},{passive:false});
gc.addEventListener("dblclick",e=>{const r=gc.getBoundingClientRect(),w=toWorld(e.clientX-r.left,e.clientY-r.top);
  if(portAt(w.x,w.y)||nodeAt(w.x,w.y)||edgeAt(w.x,w.y))return;openMenu(e.clientX,e.clientY,w);});

/* =====================================================================
   ADD-NODE MENU
   ===================================================================== */
const menu=$("#menu");let menuWorld=null,menuConnect=null;
function groupedNodeTypes(query,predicate){
  query=(query||"").trim().toLowerCase();const groups={};
  Object.keys(TYPES).forEach(t=>{const def=TYPES[t],cat=CAT[def.cat];
    if(predicate&&!predicate(t,def))return;
    const hay=(def.name+" "+def.desc+" "+(cat?cat.name:"")).toLowerCase();
    if(query&&!hay.includes(query))return;(groups[def.cat]=groups[def.cat]||[]).push(t);});
  return groups;
}
function primaryInputSlot(type){return TYPES[type]&&TYPES[type].ins.length?0:-1;}
function addNodeAt(type,world,connect){
  const slot=connect?primaryInputSlot(type):-1;
  if(connect&&slot<0)return null;
  const nd=makeNode(type,world.x-nd0w(type)/2,world.y-30);
  if(connect){
    // Drag-out quick create wires the new node immediately, so it is a connection time too. The
    // node is kept either way — the user asked for it — but an illegal wire is refused and said so,
    // rather than being made silently because it arrived through the menu instead of the canvas.
    // records:false — makeNode() above already opened the undo record for this whole gesture.
    const verdict=linkDrop(connect.from,connect.fromSlot||0,nd.id,slot,{replacing:connect.original,records:false});
    if(!verdict.ok)toast(verdict.reason||("Added unconnected: "+verdict.code));
  }
  select(nd);requestEval();return nd;
}
function chooseMenuNode(type){
  const world=menuWorld,connect=menuConnect;closeMenu();
  if(world)addNodeAt(type,world,connect);
}
function renderAddMenu(query){
  const list=menu.querySelector(".menu-list");if(!list)return;
  list.innerHTML="";let shown=0;
  const cats=groupedNodeTypes(query,menuConnect?(_t,def)=>def.ins.length>0:null);
  Object.keys(CAT).forEach(c=>{if(!cats[c])return;
    const h=document.createElement("div");h.className="menu-cat";h.textContent=CAT[c].name;list.appendChild(h);
    cats[c].forEach(t=>{const def=TYPES[t];const it=document.createElement("button");it.type="button";it.className="menu-item";
      it.dataset.type=t;
      it.innerHTML=`<span class="dot" style="background:${css(CAT[c].c)}"></span>${def.name}<small>${def.ins.length?def.ins.length+"in":"gen"}</small>`;
      it.onclick=()=>chooseMenuNode(t);list.appendChild(it);shown++;});
  });
  if(!shown){const empty=document.createElement("div");empty.className="menu-empty";
    empty.textContent=menuConnect?"No connectable nodes match that search.":"No nodes match that search.";list.appendChild(empty);}
  const first=list.querySelector(".menu-item");if(first)first.classList.add("active");
}
function openMenu(clientX,clientY,world,connect){
  menuWorld=world;menuConnect=connect||null;menu.innerHTML="";
  const context=document.createElement("div");context.className="menu-context";
  const source=menuConnect&&nodeById(menuConnect.from);
  context.innerHTML=source?`Connect from <b>${TYPES[source.type].name}</b>`:"Add node";
  const search=document.createElement("input");search.type="search";search.className="menu-search";
  search.autocomplete="off";search.spellcheck=false;search.placeholder=source?"Find a node to connect…":"Find a node…";
  search.setAttribute("aria-label",search.placeholder);
  const list=document.createElement("div");list.className="menu-list";
  menu.append(context,search,list);renderAddMenu("");
  search.oninput=()=>renderAddMenu(search.value);
  search.onkeydown=e=>{
    const items=[...list.querySelectorAll(".menu-item")],active=list.querySelector(".menu-item.active");
    let index=items.indexOf(active);
    if(e.key==="Escape"){e.preventDefault();closeMenu();gc.focus();return;}
    if(e.key==="Enter"&&items.length){e.preventDefault();chooseMenuNode((active||items[0]).dataset.type);return;}
    if(e.key==="ArrowDown"||e.key==="ArrowUp"){
      e.preventDefault();if(active)active.classList.remove("active");
      index=e.key==="ArrowDown"?Math.min(items.length-1,index+1):Math.max(0,index<0?0:index-1);
      if(items[index]){items[index].classList.add("active");items[index].scrollIntoView({block:"nearest"});}
    }
  };
  menu.classList.add("open");
  const mw=252,mh=Math.min(menu.scrollHeight,window.innerHeight*.7);
  menu.style.left=Math.max(6,Math.min(clientX,window.innerWidth-mw-8))+"px";
  menu.style.top=Math.max(6,Math.min(clientY,window.innerHeight-mh-8))+"px";
  search.focus({preventScroll:true});
}
function nd0w(t){return 150;}
function closeMenu(){menu.classList.remove("open");menuConnect=null;menuWorld=null;}
window.addEventListener("mousedown",e=>{if(menu.classList.contains("open")&&!menu.contains(e.target))closeMenu();});

/* =====================================================================
   GRAPH NODE TOOLBOX
   ===================================================================== */
const nodeToolbox=$("#nodeToolbox"),nodeToolList=$("#nodeToolList"),nodeToolSearch=$("#nodeToolSearch");
function toolboxSpawnPoint(){
  const open=$("#graphwrap").classList.contains("toolbox-open"),w=gc.clientWidth,h=gc.clientHeight;
  const x=(open?248:0)+(w-(open?248:0))*.5;
  return toWorld(x,h*.5);
}
function renderNodeToolbox(query){
  const groups=groupedNodeTypes(query);nodeToolList.innerHTML="";let shown=0;
  Object.keys(CAT).forEach(c=>{const types=groups[c];if(!types||!types.length)return;
    const group=document.createElement("section");group.className="node-tool-cat";
    const title=document.createElement("div");title.className="node-tool-cat-title";
    title.style.setProperty("--cat-color",css(CAT[c].c));title.textContent=CAT[c].name;group.appendChild(title);
    types.forEach(t=>{const def=TYPES[t],item=document.createElement("button");item.type="button";
      item.className="node-tool-item";item.dataset.type=t;item.title=def.desc;
      item.style.setProperty("--cat-color",css(CAT[c].c));
      const summary=(def.desc||"").split(/[.—]/)[0].trim();
      item.innerHTML=`<span class="dot"></span><span class="node-tool-copy"><b>${def.name}</b><small>${summary}</small></span><span class="node-tool-ports">${def.ins.length?def.ins.length+" in":"gen"}</span>`;
      item.onclick=()=>addNodeAt(t,toolboxSpawnPoint());group.appendChild(item);shown++;});
    nodeToolList.appendChild(group);
  });
  if(!shown){const empty=document.createElement("div");empty.className="node-tool-empty";empty.textContent="No nodes match that search.";nodeToolList.appendChild(empty);}
  $("#nodeToolCount").textContent=shown+"/"+Object.keys(TYPES).length;
}
function setNodeToolbox(open,focusSearch){
  $("#graphwrap").classList.toggle("toolbox-open",open);nodeToolbox.classList.toggle("open",open);
  nodeToolbox.setAttribute("aria-hidden",open?"false":"true");nodeToolbox.inert=!open;
  $("#nodeToolBtn").setAttribute("aria-expanded",open?"true":"false");
  $("#nodeToolBtn").textContent=open?"× Nodes":"＋ Nodes";$("#nodeToolBtn").title=open?"Close node toolbox":"Open node toolbox";
  if(open&&focusSearch!==false)requestAnimationFrame(()=>nodeToolSearch.focus());
}
$("#nodeToolBtn").onclick=()=>setNodeToolbox(!nodeToolbox.classList.contains("open"));
nodeToolSearch.oninput=()=>renderNodeToolbox(nodeToolSearch.value);
nodeToolbox.addEventListener("keydown",e=>{if(e.key==="Escape"){e.preventDefault();setNodeToolbox(false);$("#nodeToolBtn").focus();}});
renderNodeToolbox("");

/* =====================================================================
   PROPERTIES PANEL
   ===================================================================== */
let previewMode="output";
function activePreviewNode(){
  return previewMode==="selected"&&selected&&selected._field?selected:outputNode();
}
function updatePreviewInfo(root){
  const name=root?TYPES[root.type].name:"No output";
  const selectedMode=previewMode==="selected",mode=selectedMode?"Selected":"Output";
  $("#vpInfo").innerHTML=`<span class="vp-chip"><b>${mode}</b>${mode===name?"":" · "+name}</span>`;
  $("#previewBtn").dataset.state=selectedMode?"selected":"output";
  $("#previewBtn").classList.toggle("on",selectedMode);
  $("#previewBtn").setAttribute("aria-label",selectedMode?"Preview final Output":"Preview selected node");
  $("#previewBtn").title=selectedMode?"Preview final Output":"Preview selected node";
}
function refreshPreview(){
  const root=activePreviewNode(),meta=root&&fieldMetadata(root._field);scene=collectScene(root);
  const raw=root?(meta&&meta.heightField||root._field):null,adapter=root&&TYPES[root.type]?.previewAdapter;
  updateViewport(adapter?adapter(raw,terrainDef):raw,root);updatePreviewInfo(root);drawGraph();
}
function selectEdge(edge){
  selectedEdge=edge?edgeKey(edge):null;buildProps();drawGraph();syncEditorCommandState();
}
function select(nd){
  if(nd===selected&&!selectedEdge){drawGraph();return;}
  selectedEdge=null;selected=nd;buildProps();
  if(previewMode==="selected")refreshPreview();else drawGraph();syncEditorCommandState();
}
function buildEdgeProps(body,title,sub,sw,edge){
  const from=nodeById(edge.from),to=nodeById(edge.to),input=nodeInputs(to)[edge.slot]||("Input "+(edge.slot+1));
  const field=from&&from._field,temperatureC=temperatureCFromField(field),wind=windVectorFromField(field);
  const values=temperatureC||wind&&wind.speed||field;let min=Infinity,max=-Infinity,mean=0,coverage=0;
  if(values&&values.length){for(let i=0;i<values.length;i++){const v=values[i];min=Math.min(min,v);max=Math.max(max,v);mean+=v;if(!temperatureC&&!wind&&v>.5)coverage++;}
    mean/=values.length;coverage/=values.length;}else{min=max=mean=coverage=0;}
  const stat=v=>temperatureC?v.toFixed(1)+"°C":wind?v.toFixed(1)+" m/s":v.toFixed(2);
  title.firstChild.textContent="Connection";sub.textContent=(from?TYPES[from.type].name:"Missing")+" → "+(to?TYPES[to.type].name:"Missing")+"."+input;
  sw.style.background=edge.disabled?css("--faint"):css("--accent");body.innerHTML="";
  const summary=document.createElement("div");summary.className="edge-summary";
  summary.innerHTML=`<div class="edge-route">
    <div class="edge-end"><small>Source</small><b>${from?TYPES[from.type].name:"Missing node"}</b><span>Output</span></div>
    <div class="edge-arrow">→</div>
    <div class="edge-end"><small>Destination</small><b>${to?TYPES[to.type].name:"Missing node"}</b><span>${input}</span></div>
    </div><div class="edge-stats"><div class="edge-stat"><small>Min</small><b>${stat(min)}</b></div>
      <div class="edge-stat"><small>Mean</small><b>${stat(mean)}</b></div>
      <div class="edge-stat"><small>Max</small><b>${stat(max)}</b></div></div>
    ${input==="Mask"?`<div class="edge-meter" title="${Math.round(coverage*100)}% above 0.5"><span style="width:${Math.round(coverage*100)}%"></span></div>`:""}
    <div class="edge-note">${input==="Mask"
      ?"<b>Mask contract:</b> black (0) bypasses the effect, white (1) applies it fully, and grey blends between."
      :"Connections route a field without hidden processing. Use Blend, Color Blend, or Color Mixer when the connection needs compositing behavior."}</div>`;
  body.appendChild(summary);
  const status=document.createElement("div");status.className="field";
  status.innerHTML='<div class="frow"><label>Connection state</label></div>';
  const seg=document.createElement("div");seg.className="seg";
  [["enabled","Enabled"],["muted","Muted"]].forEach(([value,label])=>{const b=document.createElement("button");b.type="button";b.textContent=label;
    if((value==="enabled")!==!!edge.disabled)b.classList.add("on");
    b.onclick=()=>toggleEdge(edge,value==="enabled");seg.appendChild(b);});
  status.appendChild(seg);body.appendChild(status);
  const actions=document.createElement("div");actions.className="prop-actions";
  const source=document.createElement("button");source.className="btn";source.textContent="Select source";source.onclick=()=>select(from);
  const target=document.createElement("button");target.className="btn";target.textContent="Select target";target.onclick=()=>select(to);
  const remove=document.createElement("button");remove.className="btn";remove.textContent="Disconnect";remove.onclick=()=>deleteEdge(edge);
  actions.append(source,target,remove);body.appendChild(actions);
  const hint=document.createElement("div");hint.className="hint";hint.style.marginTop="12px";
  hint.innerHTML="Click near a curve—or right-click its connected input port—to select it. Press <kbd>Del</kbd>, use the × handle, or choose Disconnect.";
  body.appendChild(hint);
}
// Collapsed inspector state is presentation only: it is deliberately absent from graph snapshots,
// saved documents, cache keys and undo. Enabling a stage is document state and uses the normal
// command path; opening its panel is not.
const paramSectionOpen=new Map();
function appendParamFields(body,params){
  let lastGroup=null;
  params.filter(pr=>pr.type!=="hidden"&&pr.type!=="toggle"&&paramVisible(pr,selected.params)).forEach(pr=>{
    if(pr.group&&pr.group!==lastGroup){const h=document.createElement("div");h.className="param-group-title";h.textContent=pr.group;body.appendChild(h);}
    body.appendChild(buildField(pr));lastGroup=pr.group||null;
  });
}
function buildParamSections(body,def,nd){
  const consumed=new Set();
  for(const section of def.paramSections||[]){
    const toggle=def.params.find(pr=>pr.key===section.toggle);
    if(!toggle)continue;
    consumed.add(toggle.key);
    const key=nd.id+":"+section.id,enabled=!!nd.params[toggle.key];
    let open=paramSectionOpen.has(key)?paramSectionOpen.get(key):!!section.defaultOpen;
    const card=document.createElement("section");card.className="param-section"+(enabled?" enabled":" disabled");
    card.dataset.section=section.id;
    const head=document.createElement("div");head.className="param-section-head";
    const collapse=document.createElement("button");collapse.type="button";collapse.className="param-section-collapse";
    collapse.setAttribute("aria-expanded",open?"true":"false");
    const bodyId="param-section-"+nd.id+"-"+section.id;collapse.setAttribute("aria-controls",bodyId);
    const chevron=document.createElement("span");chevron.className="param-section-chevron";chevron.textContent=open?"▾":"▸";
    const label=document.createElement("span");label.className="param-section-label";label.textContent=section.label;
    collapse.append(chevron,label);
    let available=true;
    if(section.device==="gpu")available=gpuReady();
    else if(section.device==="gpu-droplets")available=gpuDropletsReady();
    const badge=document.createElement("span");badge.className="param-section-badge"+(available?"":" fallback");
    badge.textContent=available?"GPU":"CPU fallback";
    const sw=document.createElement("button");sw.type="button";sw.className="param-switch";
    sw.setAttribute("role","switch");sw.setAttribute("aria-checked",enabled?"true":"false");
    sw.setAttribute("aria-label",(enabled?"Disable ":"Enable ")+section.label);
    sw.innerHTML='<span class="param-switch-knob" aria-hidden="true"></span>';
    const sectionBody=document.createElement("div");sectionBody.className="param-section-body";sectionBody.id=bodyId;
    sectionBody.hidden=!open;
    collapse.onclick=()=>{open=!open;paramSectionOpen.set(key,open);sectionBody.hidden=!open;
      collapse.setAttribute("aria-expanded",open?"true":"false");chevron.textContent=open?"▾":"▸";};
    sw.onclick=()=>{recordHistory();nd.params[toggle.key]=!nd.params[toggle.key];
      if(nd.params[toggle.key])paramSectionOpen.set(key,true);
      markParamDirty(nd);buildProps();requestEval();};
    head.append(collapse,badge,sw);card.append(head,sectionBody);
    const params=def.params.filter(pr=>pr.section===section.id);
    params.forEach(pr=>consumed.add(pr.key));appendParamFields(sectionBody,params);
    body.appendChild(card);
  }
  return consumed;
}
function buildProps(){
  const body=$("#pBody"),title=$("#pTitle"),sub=$("#pSub"),sw=$("#pSwatch");
  const edge=edgeByKey(selectedEdge);if(edge){buildEdgeProps(body,title,sub,sw,edge);return;}
  if(selectedEdge)selectedEdge=null;
  if(!selected){ // no node selected -> scene-level TERRAIN DEFINITION (the world the heightfield represents)
    title.firstChild.textContent="Terrain definition";sub.textContent="The real-world size of this terrain";
    sw.style.background=css("--faint");body.innerHTML="";
    const mk=(key,label,min,max,step,fmt)=>{
      const f=document.createElement("div");f.className="field";
      const show=v=>fmt?fmt(v):v;
      f.innerHTML=`<div class="frow"><label>${label}</label><span class="val">${show(terrainDef[key])}</span></div>`;
      const i=document.createElement("input");i.type="range";i.min=min;i.max=max;i.step=step;i.value=terrainDef[key];
      let before=null,changed=false;
      i.oninput=()=>{if(!before)before=graphSnapshot();changed=true;terrainDef[key]=step>=1?Math.round(parseFloat(i.value)):parseFloat(i.value);
        f.querySelector(".val").textContent=show(terrainDef[key]);
        H_SCALE=terrainDef.height/terrainDef.scale;
        const climateNodes=nodes.filter(n=>n.type==="d_sunshadow"||n.type==="d_temperature"
          ||n.type==="d_wind"||n.type==="d_windmodify"||n.type==="water"||n.type==="snow");
        climateNodes.forEach(n=>{if(n.type==="snow")n._snowLayer=null;markDirtyFrom(n.id);});
        if(climateNodes.length)requestEval();else if(curField)updateViewport(curField);
        tdInfo();syncCompass();};
      i.onchange=()=>{if(changed)pushUndo(before);before=null;changed=false;
        // Every node whose output READS the terrain definition must re-evaluate when it moves:
        // thermal (Real scale repose), Rock Fracture (all dimensions are metres), and
        // deposits/texture (fill depth is metres / refDepth).
        if(key==="scale"||key==="height"){
          const affected=nodes.filter(n=>(n.type==="thermal"&&n.params.realScale==="on")
            ||n.type==="fracture"||n.type==="d_deposits"||n.type==="d_texture");
          if(affected.length){affected.forEach(n=>markDirtyFrom(n.id));requestEval();}}};
      f.appendChild(i);return f;};
    body.appendChild(mk("scale","Scale (across)",500,20000,1,v=>Math.round(v)+" m"));
    body.appendChild(mk("height","Relief height",100,8000,1,v=>Math.round(v)+" m"));
    body.appendChild(mk("baseElevation","Base elevation",-500,9000,1,v=>Math.round(v)+" m ASL"));
    body.appendChild(mk("seaTemp","Fallback sea-level temperature",-50,50,.5,v=>v.toFixed(1)+" °C"));
    body.appendChild(mk("lapseRate","Fallback temperature lapse",-10,15,.1,v=>v.toFixed(1)+" °C/km"));
    body.appendChild(mk("solarElevation","Climate sun elevation",3,90,1,v=>Math.round(v)+"°"));
    body.appendChild(mk("latitude","Latitude",-90,90,.5,v=>Math.abs(v).toFixed(1)+"° "+(v<0?"S":v>0?"N":"Equator")));
    body.appendChild(mk("north","Map north",0,359,1,v=>Math.round(v)+"° clockwise from top"));
    body.appendChild(mk("windDirection","Prevailing wind from",0,359,1,v=>Math.round(v)+"° map"));
    body.appendChild(mk("windSpeed","Prevailing wind speed",0,60,.5,v=>v.toFixed(1)+" m/s"));
    {
      // Lattice toggle (references/26): square raster or hexagonal (odd-r). Everything is
      // re-evaluated on switch - the seed contract, mesh topology and metric all change.
      // Promoted to a titled block with drawn lattice symbols: this is a structural choice about
      // the whole terrain, not a slider, so it should not read as one more row in a stack.
      const f=document.createElement("div");f.className="field lattice-field";
      f.innerHTML=`<div class="frow"><label class="lattice-title">Grid lattice</label></div>`;
      // The symbols ARE the explanation: four squares meeting at a corner (the diagonal
      // ambiguity) versus a honeycomb (six equidistant edge neighbours).
      const SYM={
        square:`<svg viewBox="0 0 40 34" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.6">
          <rect x="6" y="4" width="13" height="13"/><rect x="19" y="4" width="13" height="13"/>
          <rect x="6" y="17" width="13" height="13"/><rect x="19" y="17" width="13" height="13"/></g></svg>`,
        hex:`<svg viewBox="0 0 40 34" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.6">
          <polygon points="13,3 20,7 20,15 13,19 6,15 6,7"/><polygon points="27,3 34,7 34,15 27,19 20,15 20,7"/>
          <polygon points="20,15 27,19 27,27 20,31 13,27 13,19"/></g></svg>`};
      const seg=document.createElement("div");seg.className="seg lattice-seg";
      for(const[val,lab]of[["square","Square"],["hex","Hexagonal"]]){
        const b2=document.createElement("button");b2.type="button";b2.className="seg-btn lattice-btn";
        b2.innerHTML=SYM[val]+`<span>${lab}</span>`;
        b2.setAttribute("aria-label",lab+" grid lattice");
        if((terrainDef.lattice||"square")===val){b2.classList.add("active");b2.setAttribute("aria-pressed","true");}
        b2.onclick=()=>{if((terrainDef.lattice||"square")===val)return;
          const before=graphSnapshot();terrainDef.lattice=val;pushUndo(before);
          buildIndex();nodes.forEach(nd=>{nd._dirty=true;nd._thumb=null;});
          requestEval();buildProps();tdInfo();
          if(!AUTO)toast("Lattice changed — press Build to re-simulate on the new grid");};
        seg.appendChild(b2);
      }
      f.appendChild(seg);
      const note=document.createElement("div");note.className="hint";note.style.marginTop="6px";
      // Say the footprint consequence plainly here, because it is the thing that surprises: the
      // map really does change shape, and the reason is geometric, not a bug.
      note.innerHTML="<b>Hexagonal</b>: 6 equidistant neighbours, so there is no diagonal to weight "
        +"and no 45° drainage bias; static equilateral mesh (no edge spinning); D6 thermal, routing "
        +"and analysis.<br><b>Your terrain is kept.</b> Generators are authored in graph space, so "
        +"the same seed draws the same landscape on either lattice (correlation <b>0.99</b> on the "
        +"default graph). What changes is the <i>map</i>: a true hex lattice puts rows √3/2 apart, "
        +"so the world becomes <b>scale × scale·√3/2</b> and the terrain is fitted to a 13.4% "
        +"shorter footprint. GPU compute runs on the CPU path in hex mode.";
      f.appendChild(note);
      body.appendChild(f);
    }
    const info=document.createElement("div");info.className="hint";info.id="tdInfo";body.appendChild(info);
    tdInfo();
    const hint=document.createElement("div");hint.className="hint";hint.style.marginTop="10px";
    hint.innerHTML="Select a node in the graph to edit its parameters. Double-click empty canvas to add one.";
    body.appendChild(hint);
    return;}
  const def=TYPES[selected.type];sw.style.background=css(CAT[def.cat].c);
  title.firstChild.textContent=def.name;sub.textContent=def.desc;
  body.innerHTML="";
  // An input problem and a thrown evaluation are both failures the author has to see. The input
  // message wins when both are set, because it names the cause and the throw is usually its
  // consequence.
  const nodeProblem=selected._inputError||selected._evalError;
  if(nodeProblem){const warning=document.createElement("div");warning.className="hint";
    warning.style.cssText="border-color:var(--bad);color:var(--bad);margin-bottom:10px";
    warning.textContent=nodeProblem;body.appendChild(warning);}
  if(def.migrateParams)def.migrateParams(selected.params);
  // Graphs saved by older Studio versions (and concise hand-authored defaults) may not carry
  // parameters introduced later. Hydrate them from the schema before formatting or evaluating.
  def.params.forEach(pr=>{if(!(pr.key in selected.params))selected.params[pr.key]=cloneParams(pr.def);});
  const consumed=buildParamSections(body,def,selected);
  appendParamFields(body,def.params.filter(pr=>!consumed.has(pr.key)&&!pr.section));
  if(selected.type==="colormixer")buildColorMixerProps(body);
  if(selected.type==="satmap"){
    const tools=document.createElement("div");tools.className="prop-actions";tools.style.margin="2px 0 8px";
    const random=document.createElement("button");random.type="button";random.className="btn";random.textContent="Randomize";
    random.title="Choose another SatMap palette";random.onclick=()=>{
      const names=Object.keys(SATMAPS).filter(x=>x!==selected.params.gradient),name=names[Math.floor(Math.random()*names.length)];chooseSatMap(name,false);};
    const studio=document.createElement("button");studio.type="button";studio.className="btn";
    studio.textContent="Open SatMap Studio…";studio.title="Create or edit a SatMap LUT";studio.onclick=()=>$("#satGenBtn").click();
    tools.append(random,studio);body.appendChild(tools);
  }
  if(selected.type==="drawmask"){
    const tools=document.createElement("div");tools.className="prop-actions";tools.style.margin="2px 0 8px";
    const edit=document.createElement("button");edit.type="button";edit.className="btn primary";edit.style.flex="1";
    edit.textContent="Draw on terrain…";edit.title="Open the plan-view vector mask editor";edit.onclick=()=>openDrawEditor(selected);
    const count=document.createElement("span");count.className="hint";count.style.margin="0";count.textContent=(selected.params.strokes||[]).length+" strokes";
    tools.append(edit,count);body.appendChild(tools);
  }
  if(selected.type==="canyon"){
    const tools=document.createElement("div");tools.className="prop-actions";tools.style.margin="2px 0 8px";
    const edit=document.createElement("button");edit.type="button";edit.className="btn primary";edit.style.flex="1";
    edit.textContent="Edit waypoints on terrain…";edit.title="Click top-down to draw the trunk route";edit.onclick=()=>openPathEditor(selected);
    const pts=parsePathPoints(selected.params.waypoints);
    const count=document.createElement("span");count.className="hint";count.style.margin="0";
    count.textContent=pts.length?pts.length+" waypoints":"procedural (no waypoints)";
    tools.append(edit,count);body.appendChild(tools);
  }
  const note=def.info?def.info(selected):def.note;
  if(note){const nt=document.createElement("div");nt.className="hint";
    nt.style.margin="14px 0 10px";nt.innerHTML=note;body.appendChild(nt);}
  if(selected.type==="import"){const b=document.createElement("button");b.className="btn";b.style.width="100%";b.style.marginTop="8px";
    b.textContent=selected._dem?"Replace heightmap…":"Load heightmap file…";b.onclick=()=>{importTarget=selected;$("#fileInput").click();};
    const b2=document.createElement("button");b2.className="btn";b2.style.width="100%";b2.style.marginTop="6px";
    b2.textContent="Use real SRTM sample";b2.title="A real public-domain USGS/SRTM heightmap (Colorado Plateau)";
    b2.onclick=()=>{importTarget=selected;loadImageAsDEM(selected,REAL_DEM_SAMPLE,"Loaded real SRTM sample — Colorado Plateau");};
    const wrap=document.createElement("div");wrap.className="field";wrap.appendChild(b);wrap.appendChild(b2);
    const hint=document.createElement("div");hint.className="hint";hint.innerHTML=selected._dem?"Loaded a real DEM as this node’s base — now wire it into erosion, then Export.":"PNG (any) or square 16-bit <code>.r16</code> raw — real USGS/SRTM works (export one from <code>heightfield_io.py</code>). Or load the embedded real sample.";
    wrap.appendChild(hint);body.appendChild(wrap);}
  const act=document.createElement("div");act.className="prop-actions";
  const dup=document.createElement("button");dup.className="btn";dup.textContent="Duplicate";dup.onclick=duplicateSel;
  const del=document.createElement("button");del.className="btn";del.textContent="Delete";del.onclick=deleteSel;
  act.appendChild(dup);act.appendChild(del);body.appendChild(act);
}
function paramVisible(pr,values){
  if(!pr.when)return true;
  const clauses=Array.isArray(pr.when)?pr.when:[pr.when];
  return clauses.every(c=>c.values.includes(values[c.key]));
}
function paramControlsVisibility(type,key){
  return TYPES[type].params.some(pr=>pr.when&&(Array.isArray(pr.when)?pr.when:[pr.when]).some(c=>c.key===key));
}
function buildColorMixerProps(body){
  const nd=selected;if(!nd._inputs)nd._inputs=["Layer 1","Layer 2","Layer 3"];
  if(!Array.isArray(nd.params.layers))nd.params.layers=nd._inputs.map(()=>({opacity:1,blend:"normal",edgeBlend:0}));
  while(nd.params.layers.length<nd._inputs.length)nd.params.layers.push({opacity:1,blend:"normal",edgeBlend:0});
  nd.params.layers.forEach(cfg=>{if(cfg.edgeBlend==null)cfg.edgeBlend=0;});
  const relabel=()=>{nd._inputs=nd._inputs.map((_,i)=>"Layer "+(i+1));};
  const changed=()=>{relabel();markDirtyFrom(nd.id);buildProps();requestEval();};
  const swap=(a,b)=>{if(b<0||b>=nd._inputs.length)return;recordHistory();
    [nd.params.layers[a],nd.params.layers[b]]=[nd.params.layers[b],nd.params.layers[a]];
    edges.filter(e=>e.to===nd.id).forEach(e=>{if(e.slot===a)e.slot=b;else if(e.slot===b)e.slot=a;});changed();};
  nd._inputs.forEach((_,i)=>{
    const cfg=nd.params.layers[i],card=document.createElement("div");card.className="mix-layer";
    const head=document.createElement("div");head.className="mix-layer-head";
    const name=document.createElement("span");name.textContent=i===0?"Layer 1 · Base":"Layer "+(i+1);
    const up=document.createElement("button");up.className="btn";up.textContent="↑";up.title="Move layer up";up.disabled=i===0;up.onclick=()=>swap(i,i-1);
    const down=document.createElement("button");down.className="btn";down.textContent="↓";down.title="Move layer down";down.disabled=i===nd._inputs.length-1;down.onclick=()=>swap(i,i+1);
    const del=document.createElement("button");del.className="btn";del.textContent="×";del.title="Remove layer";del.disabled=nd._inputs.length<=2;
    del.onclick=()=>{if(nd._inputs.length<=2)return;recordHistory();edges=edges.filter(e=>!(e.to===nd.id&&e.slot===i));
      edges.filter(e=>e.to===nd.id&&e.slot>i).forEach(e=>e.slot--);nd._inputs.splice(i,1);nd.params.layers.splice(i,1);changed();};
    head.append(name,up,down,del);card.appendChild(head);
    if(i>0){
      const modeRow=document.createElement("div");modeRow.className="mix-layer-row";modeRow.innerHTML="<span>Blend</span>";
      const mode=document.createElement("select");mode.className="inp";
      TYPES.satmapblend.params.find(p=>p.key==="blend").opts.forEach(o=>{const op=document.createElement("option");op.value=o[0];op.textContent=o[1];mode.appendChild(op);});
      mode.value=cfg.blend||"normal";mode.onchange=()=>{recordHistory();cfg.blend=mode.value;markParamDirty(nd);requestEval();};modeRow.appendChild(mode);card.appendChild(modeRow);
      const opRow=document.createElement("div");opRow.className="mix-layer-row";
      const lab=document.createElement("span");lab.textContent="Opacity "+(cfg.opacity==null?1:cfg.opacity).toFixed(2);
      const slider=document.createElement("input");slider.type="range";slider.min=0;slider.max=1;slider.step=.01;slider.value=cfg.opacity==null?1:cfg.opacity;
      let before=null,dirty=false;slider.oninput=()=>{if(!before)before=graphSnapshot();dirty=true;cfg.opacity=+slider.value;lab.textContent="Opacity "+cfg.opacity.toFixed(2);markParamDirty(nd);requestEval();};
      slider.onchange=()=>{if(dirty)pushUndo(before);before=null;dirty=false;};opRow.append(lab,slider);card.appendChild(opRow);
      const edgeRow=document.createElement("div");edgeRow.className="mix-layer-row";
      const edgeLabel=document.createElement("span");
      const formatEdge=v=>v<1000?Math.round(v)+" m":(v/1000).toFixed(2)+" km";
      edgeLabel.textContent="Edge "+formatEdge(cfg.edgeBlend||0);
      const edgeSlider=document.createElement("input"),edgeMax=Math.max(terrainDef.scale*.1,cfg.edgeBlend||0,100);
      edgeSlider.type="range";edgeSlider.min=0;edgeSlider.max=edgeMax;edgeSlider.step=Math.max(1,edgeMax/200);edgeSlider.value=cfg.edgeBlend||0;
      let edgeBefore=null,edgeDirty=false;edgeSlider.oninput=()=>{if(!edgeBefore)edgeBefore=graphSnapshot();edgeDirty=true;
        cfg.edgeBlend=+edgeSlider.value;edgeLabel.textContent="Edge "+formatEdge(cfg.edgeBlend);markParamDirty(nd);requestEval();};
      edgeSlider.onchange=()=>{if(edgeDirty)pushUndo(edgeBefore);edgeBefore=null;edgeDirty=false;};
      edgeRow.append(edgeLabel,edgeSlider);card.appendChild(edgeRow);
    }
    body.appendChild(card);
  });
  const add=document.createElement("button");add.className="btn";add.style.width="100%";add.disabled=nd._inputs.length>=15;
  add.textContent=nd._inputs.length>=15?"15-layer limit reached":"＋ Add color layer ("+nd._inputs.length+"/15)";
  add.onclick=()=>{if(nd._inputs.length>=15)return;recordHistory();nd._inputs.push("Layer "+(nd._inputs.length+1));
    nd.params.layers.push({opacity:1,blend:"normal",edgeBlend:0});changed();};
  body.appendChild(add);
  const hint=document.createElement("div");hint.className="hint";hint.style.marginTop="8px";
  hint.innerHTML="Layer 1 is the base. A standalone masked <b>SatMap</b> connected to any higher layer is a biome: black preserves the layers below, white applies this layer, and <b>Edge</b> adds a world-space ecotone at the boundary. A Color Blend branch arrives already composited.";
  body.appendChild(hint);
}
function tdInfo(){const el=document.getElementById("tdInfo");if(!el)return;
  const lat=terrainDef.latitude||0,hemi=lat<0?"Southern":lat>0?"Northern":"Equatorial";
  const freeze=terrainDef.seaTemp<=0?0:terrainDef.seaTemp/(terrainDef.lapseRate||6.5)*1000;
  el.innerHTML=`${isHex()?`<b>Hexagonal lattice</b> (odd-r) · footprint <b>${Math.round(terrainDef.scale)} × ${Math.round(terrainDef.scale*HEX_ROW)} m</b> (rows sit √3/2 apart — the metric never lies) ·<br>`:""}Vertical ratio <b>${(terrainDef.height/terrainDef.scale).toFixed(2)}</b> (height ÷ scale) ·
    cell size <b>${cellSizeM().toFixed(1)} m</b> at ${RES}² ·
    elevation <b>${Math.round(terrainDef.baseElevation)}…${Math.round(terrainDef.baseElevation+terrainDef.height)} m ASL</b>.<br>
    0 °C freezing level <b>${Math.round(freeze)} m</b>${terrainDef.seaTemp<=0?" (sea level and above)":""} ·
    fallback ${terrainDef.seaTemp.toFixed(1)} °C at sea level, −${terrainDef.lapseRate.toFixed(1)} °C/km ·
    climate sun <b>${Math.round(terrainDef.solarElevation)}°</b> · prevailing wind
    <b>${Math.round(terrainDef.windDirection==null?300:terrainDef.windDirection)}° from</b> at
    <b>${(terrainDef.windSpeed==null?10:terrainDef.windSpeed).toFixed(1)} m/s</b>.<br>
    <b>${hemi} hemisphere</b> · map north ${Math.round(terrainDef.north||0)}° clockwise from the top edge.<br>
    Scale drives vertical exaggeration and real-scale nodes. Latitude + map north define the
    equator-facing aspect used by solar snowmelt and the viewport compass. Fallback climate is used
    only when Snow or Water has no valid Temperature input.`;}
function buildField(pr){
  const f=document.createElement("div");f.className="field";
  f.dataset.paramKey=pr.key;
  if(pr.type==="slider"){
    const val=selected.params[pr.key];
    f.innerHTML=`<div class="frow"><label>${pr.label}</label><span class="val">${fmtVal(pr,val)}</span></div>`;
    const inp=document.createElement("input");inp.type="range";
    const isLog=pr.scale==="log";
    // Log track: the INPUT runs in position space [0,1]; params always hold the real value. The
    // wheel handler needs no special case - a fixed position step is multiplicative in value.
    const logSpan=isLog?Math.log(pr.max/pr.floor):0;
    const toPos=v=>v<=(pr.zero?0:pr.floor)?0:clamp(Math.log(Math.max(v,pr.floor)/pr.floor)/logSpan,0,1);
    const fromPos=t=>(pr.zero&&t<=0)?0:pr.floor*Math.exp(clamp(t,0,1)*logSpan);
    if(isLog){inp.min=0;inp.max=1;inp.step=pr.step;inp.value=toPos(val);}
    else{inp.min=pr.min;inp.max=pr.max;inp.step=pr.step;inp.value=val;}
    let before=null,changed=false;
    inp.oninput=()=>{if(!before)before=graphSnapshot();changed=true;
      selected.params[pr.key]=isLog?fromPos(parseFloat(inp.value)):parseFloat(inp.value);
      f.querySelector(".val").textContent=fmtVal(pr,selected.params[pr.key]);
      markParamDirty(selected);requestEval();};
    inp.onchange=()=>{if(changed)pushUndo(before);before=null;changed=false;};
    f.appendChild(inp);
    if(isLog){
      // The indication the warped track needs: without it a knob two-thirds along reading "1.2 m"
      // on a 0-20 track is disorienting. Decade labels sit at their true track positions.
      const ticks=document.createElement("div");ticks.className="logticks";
      const marks=[];if(pr.zero)marks.push([0,"0"]);
      for(let d=Math.ceil(Math.log10(pr.floor));Math.pow(10,d)<=pr.max*1.0001;d++){
        const v=Math.pow(10,d);if(v<pr.floor)continue;
        marks.push([toPos(v),String(v)]);
      }
      // Max label only when it will not collide with the last decade label.
      if(!marks.some(m=>m[0]>.92))marks.push([1,String(pr.max)]);
      ticks.innerHTML=marks.map(([t,lab])=>
        `<span style="left:${(t*100).toFixed(1)}%">${lab}</span>`).join("");
      f.appendChild(ticks);
    }
  }else if(pr.type==="number"){
    const row=document.createElement("div");row.className="frow";const label=document.createElement("label");label.textContent=pr.label;
    const unit=document.createElement("span");unit.className="val";unit.textContent=pr.unit||"";
    row.append(label,unit);f.appendChild(row);
    const inp=document.createElement("input");inp.type="number";inp.className="inp";inp.min=pr.min;inp.max=pr.max;inp.step=pr.step;inp.value=selected.params[pr.key];
    let before=null,changed=false;
    inp.oninput=()=>{
      const value=parseFloat(inp.value);if(!Number.isFinite(value))return;
      if(!before)before=graphSnapshot();changed=true;selected.params[pr.key]=clamp(value,pr.min,pr.max);
      markParamDirty(selected);requestEval();
    };
    inp.onchange=()=>{
      const value=parseFloat(inp.value);selected.params[pr.key]=Number.isFinite(value)?clamp(value,pr.min,pr.max):pr.def;
      inp.value=selected.params[pr.key];if(changed)pushUndo(before);before=null;changed=false;markParamDirty(selected);requestEval();
    };
    f.appendChild(inp);
  }else if(pr.type==="select"){
    f.innerHTML=`<div class="frow"><label>${pr.label}</label></div>`;
    if(selected.type==="satmap"&&pr.key==="gradient"){
      const b=document.createElement("button");b.type="button";b.className="inp prop-sat-picker";
      b.setAttribute("aria-haspopup","listbox");b.title="Choose a SatMap palette";
      const strip=document.createElement("span");strip.className="sat-picker-swatch";strip.style.background=satGradientCSS(selected.params.gradient);
      const name=document.createElement("span");name.className="sat-picker-name";name.textContent=selected.params.gradient;
      const caret=document.createElement("span");caret.className="sat-picker-caret";caret.textContent="▾";
      b.append(strip,name,caret);b.onclick=()=>openSatPicker(b);f.appendChild(b);return f;
    }
    const opts=pr.opts||((pr.key==="gradient")?Object.keys(SATMAPS).map(k=>[k,k]):[]);   // null opts -> live SatMap library
    const s=document.createElement("select");s.className="inp";opts.forEach(o=>{const op=document.createElement("option");op.value=o[0]||o;op.textContent=o[1]||o;s.appendChild(op);});
    s.value=selected.params[pr.key];s.onchange=()=>{const nd=selected;recordHistory();nd.params[pr.key]=s.value;markParamDirty(nd);
      if(paramControlsVisibility(nd.type,pr.key))buildProps();requestEval();};f.appendChild(s);
  }else if(pr.type==="seed"){
    f.innerHTML=`<div class="frow"><label>${pr.label}</label></div>`;
    const wrap=document.createElement("div");wrap.style.cssText="display:flex;gap:6px";
    const inp=document.createElement("input");inp.type="number";inp.className="inp";
    inp.min=0;inp.max=SEED_MAX;inp.step=1;inp.value=selected.params[pr.key];inp.style.flex="1";
    const set=(v)=>{recordHistory();selected.params[pr.key]=clamp(Math.round(v)||0,0,SEED_MAX);
      inp.value=selected.params[pr.key];markParamDirty(selected);requestEval();};
    inp.onchange=()=>set(parseFloat(inp.value));
    const dice=document.createElement("button");dice.className="btn";dice.textContent="\u21bb";
    dice.title="New random seed";dice.style.cssText="flex:0 0 auto;min-width:34px";
    dice.onclick=()=>set(randomSeed());
    wrap.appendChild(inp);wrap.appendChild(dice);f.appendChild(wrap);
  }else if(pr.type==="curve"){
    f.innerHTML=`<div class="frow"><label>${pr.label}</label><span class="val hint" style="font-size:10px">drag \u00b7 click adds \u00b7 dbl-click removes</span></div>`;
    const nd=selected,W=272,H=132,PAD=10;
    const cv=document.createElement("canvas");cv.width=W*2;cv.height=H*2;
    cv.style.cssText=`width:100%;height:${H}px;background:#0d1117;border:1px solid var(--line);border-radius:6px;cursor:crosshair;display:block;touch-action:none`;
    const cx2=cv.getContext("2d");cx2.scale(2,2);
    const toPx=(x,y)=>[PAD+x*(W-2*PAD), PAD+(1-y)*(H-2*PAD)];
    const toVal=(px,py)=>[clamp((px-PAD)/(W-2*PAD),0,1), clamp(1-(py-PAD)/(H-2*PAD),0,1)];
    const draw=()=>{
      const pts=nd.params[pr.key],lut=bakeCurve(pts);
      cx2.clearRect(0,0,W,H);
      cx2.strokeStyle="#1c2530";cx2.lineWidth=1;
      for(let i=0;i<=4;i++){                              // grid
        const gx=PAD+i/4*(W-2*PAD),gy=PAD+i/4*(H-2*PAD);
        cx2.beginPath();cx2.moveTo(gx,PAD);cx2.lineTo(gx,H-PAD);cx2.stroke();
        cx2.beginPath();cx2.moveTo(PAD,gy);cx2.lineTo(W-PAD,gy);cx2.stroke();}
      // the profile the curve produces, mirrored, so the artist sees the mountain not the graph
      cx2.fillStyle="rgba(120,170,220,0.16)";cx2.beginPath();
      const midY=H-PAD;
      cx2.moveTo(PAD,midY);
      for(let k=0;k<CURVE_N;k++){const x=k/(CURVE_N-1);const[a,b2]=toPx(x,lut[k]);cx2.lineTo(a,b2);}
      cx2.lineTo(W-PAD,midY);cx2.closePath();cx2.fill();
      cx2.strokeStyle="#7fb4e6";cx2.lineWidth=1.6;cx2.beginPath();
      for(let k=0;k<CURVE_N;k++){const x=k/(CURVE_N-1);const[a,b2]=toPx(x,lut[k]);
        k?cx2.lineTo(a,b2):cx2.moveTo(a,b2);}
      cx2.stroke();
      pts.forEach((q,i)=>{const[a,b2]=toPx(q[0],q[1]);
        cx2.beginPath();cx2.arc(a,b2,4,0,6.2832);
        cx2.fillStyle=i===0||i===pts.length-1?"#8fa3b8":"#e8eef5";cx2.fill();
        cx2.strokeStyle="#0d1117";cx2.lineWidth=1.5;cx2.stroke();});
    };
    const hit=(px,py)=>{const pts=nd.params[pr.key];
      for(let i=0;i<pts.length;i++){const[a,b2]=toPx(pts[i][0],pts[i][1]);
        if(Math.hypot(a-px,b2-py)<8)return i;} return -1;};
    const local=(e)=>{const r=cv.getBoundingClientRect();
      return[(e.clientX-r.left)*W/r.width,(e.clientY-r.top)*H/r.height];};
    let drag=-1,before=null,changed=false;
    cv.addEventListener("pointerdown",e=>{
      before=graphSnapshot();changed=false;
      const[px,py]=local(e);let i=hit(px,py);
      if(i<0){                                            // click on empty space adds a point
        const[x,y]=toVal(px,py);const pts=nd.params[pr.key];
        pts.push([x,y]);pts.sort((a,b2)=>a[0]-b2[0]);i=pts.findIndex(q=>q[0]===x&&q[1]===y);
        changed=true;markParamDirty(nd);requestEval();}
      drag=i;cv.setPointerCapture(e.pointerId);draw();});
    cv.addEventListener("pointermove",e=>{
      if(drag<0)return;
      const[px,py]=local(e),pts=nd.params[pr.key];let[x,y]=toVal(px,py);
      // endpoints stay pinned in x: the curve must span exactly centre -> radius
      if(drag===0)x=0;else if(drag===pts.length-1)x=1;
      else x=clamp(x,pts[drag-1][0]+0.01,pts[drag+1][0]-0.01);
      pts[drag]=[x,y];changed=true;draw();markParamDirty(nd);requestEval();});
    const stop=()=>{if(changed)pushUndo(before);before=null;changed=false;drag=-1;};
    cv.addEventListener("pointerup",stop);cv.addEventListener("pointercancel",stop);
    cv.addEventListener("dblclick",e=>{
      const[px,py]=local(e),i=hit(px,py),pts=nd.params[pr.key];
      if(i>0&&i<pts.length-1&&pts.length>2){recordHistory();pts.splice(i,1);draw();markParamDirty(nd);requestEval();}});
    f.appendChild(cv);
    const seg=document.createElement("div");seg.className="seg";seg.style.marginTop="6px";
    SKIRT_PRESETS.forEach(([lab,e])=>{const b=document.createElement("button");b.textContent=lab;
      b.onclick=()=>{recordHistory();nd.params[pr.key]=curveFromExponent(e);draw();markParamDirty(nd);requestEval();};
      seg.appendChild(b);});
    f.appendChild(seg);
    draw();
  }else if(pr.type==="text"){
    f.innerHTML=`<div class="frow"><label>${pr.label}</label></div>`;
    const ta=document.createElement("textarea");ta.className="inp";ta.rows=pr.rows||9;
    ta.style.cssText="font:11px/1.45 ui-monospace,Menlo,Consolas,monospace;resize:vertical;white-space:pre;overflow-x:auto";
    ta.value=selected.params[pr.key];
    ta.onchange=()=>{recordHistory();selected.params[pr.key]=ta.value;markParamDirty(selected);requestEval();};
    f.appendChild(ta);
  }else if(pr.type==="seg"||pr.type==="tabs"){
    f.innerHTML=`<div class="frow"><label>${pr.label}</label></div>`;
    const seg=document.createElement("div");seg.className="seg"+(pr.type==="tabs"?" tabs":"");
    if(pr.type==="tabs")seg.setAttribute("role","tablist");
    pr.opts.forEach(o=>{const b=document.createElement("button");b.textContent=o[1];if(selected.params[pr.key]===o[0])b.classList.add("on");
      if(pr.type==="tabs"){b.setAttribute("role","tab");b.setAttribute("aria-selected",selected.params[pr.key]===o[0]?"true":"false");}
      b.onclick=()=>{const nd=selected;if(nd.params[pr.key]===o[0])return;recordHistory();nd.params[pr.key]=o[0];
        [...seg.children].forEach(c=>{c.classList.remove("on");if(pr.type==="tabs")c.setAttribute("aria-selected","false");});
        b.classList.add("on");if(pr.type==="tabs")b.setAttribute("aria-selected","true");markParamDirty(nd);
        if(paramControlsVisibility(nd.type,pr.key))buildProps();requestEval();};seg.appendChild(b);});
    f.appendChild(seg);
  }
  return f;
}
function fmtVal(pr,v){return pr.fmt?pr.fmt(v):(Number.isInteger(pr.step)?(v|0):(+v).toFixed(2));}
function duplicateSel(){if(!selected)return;const nd=makeNode(selected.type,selected.x+30,selected.y+30);
  nd.params=JSON.parse(JSON.stringify(selected.params));
  nd._inputs=selected._inputs?[...selected._inputs]:null;
  if("seed"in nd.params)nd.params.seed=randomSeed();   // a duplicate is a NEW feature, not a copy
  nd._dem=selected._dem;nd._demImg=selected._demImg;nd._demRaw=selected._demRaw;
  nd._demSrc=selected._demSrc?{...selected._demSrc}:null;   // cloned, so the copy cannot alias the original's source record
  select(nd);requestEval();}
function toggleEdge(edge,enabled){
  edge=edgeByKey(edgeKey(edge));if(!edge||(!edge.disabled)===enabled)return;
  recordHistory();edge.disabled=!enabled;markDirtyFrom(edge.to);buildProps();requestEval();
  toast(enabled?"Connection enabled":"Connection muted");
}
function deleteEdge(edge){
  edge=edgeByKey(typeof edge==="string"?edge:edgeKey(edge));if(!edge)return;
  recordHistory();const target=edge.to,key=edgeKey(edge);edges=edges.filter(e=>edgeKey(e)!==key);
  if(selectedEdge===key)selectedEdge=null;markDirtyFrom(target);buildProps();requestEval();toast("Connection removed");
}
function deleteSel(){if(!selected)return;const id=selected.id;
  recordHistory();
  const incoming=edges.filter(e=>!e.disabled&&e.to===id),outgoing=edges.filter(e=>!e.disabled&&e.from===id);
  const src=incoming.length===1?incoming[0].from:null;                 // auto-bridge only when the input source is unambiguous
  edges=edges.filter(e=>e.from!==id&&e.to!==id);
  if(src!=null)outgoing.forEach(o=>{if(!edges.some(e=>e.to===o.to&&e.slot===o.slot)&&!wouldCycle(src,o.to))edges.push({from:src,to:o.to,slot:o.slot});});
  nodes=nodes.filter(n=>n.id!==id);nodes.forEach(n=>n._dirty=true);
  selectedEdge=null;if(previewMode==="selected")previewMode="output";select(null);requestEval();}

/* =====================================================================
   IMPORT / EXPORT
   ===================================================================== */
// Chunked so a large raw16 cannot blow the argument limit of String.fromCharCode.
function bytesToBase64(bytes){let out="";const CH=0x8000;
  for(let i=0;i<bytes.length;i+=CH)out+=String.fromCharCode.apply(null,bytes.subarray(i,i+CH));
  return btoa(out);}
let importTarget=null;
function importHeightmap(){
  importTarget=(selected&&selected.type==="import")?selected:nodes.find(n=>n.type==="import")||null;
  if(!importTarget){importTarget=makeNode("import",toWorld(80,80).x,toWorld(80,80).y);select(importTarget);}
  $("#fileInput").click();
}
$("#importBtn").onclick=importHeightmap;
$("#fileInput").onchange=e=>{const file=e.target.files[0];if(!file||!importTarget)return;
  const nd=importTarget,name=file.name.toLowerCase();
  if(name.endsWith(".r16")||name.endsWith(".raw")||name.endsWith(".bin")){
    file.arrayBuffer().then(buf=>{const u16=new Uint16Array(buf);const side=Math.round(Math.sqrt(u16.length));
      if(side*side!==u16.length){toast("Raw must be square (got "+u16.length+" samples)");return;}
      recordHistory();
      nd._demRaw={u16,side};nd._demImg=null;
      // Capture the SOURCE bytes, not the derived field. Without them a saved project cannot
      // reproduce identical terrain on reload, and that is the whole point of the format.
      nd._demSrc={kind:"raw16",name:file.name,side,base64:bytesToBase64(new Uint8Array(buf))};
      buildDemFromSource(nd);finishDem(nd);toast("Loaded "+side+"² raw heightmap");});
  }else{
    // readAsDataURL rather than createObjectURL: the data URL is what gets persisted, and an
    // object URL would also be revoked out from under a later reload.
    const reader=new FileReader();
    reader.onload=()=>loadImageAsDEM(nd,reader.result,"Loaded heightmap file",{kind:"image",name:file.name,mime:file.type||"image/png",dataUrl:reader.result});
    reader.onerror=()=>toast("Could not read that file");
    reader.readAsDataURL(file);
  }
  e.target.value="";
};
function loadImageAsDEM(nd,src,label,source){
  const img=new Image();img.onload=()=>{recordHistory();nd._demImg=img;nd._demRaw=null;if(source)nd._demSrc=source;buildDemFromSource(nd);finishDem(nd);toast(label);};
  img.onerror=()=>toast("Could not read that image");img.src=src;
}
// (re)build a node's imported heightfield at the CURRENT resolution from its retained source, so changing
// the working resolution re-resamples cleanly instead of reading a stale, wrong-sized array.
export function buildDemFromSource(nd){const nh=fieldH();
  if(nd._demImg){const c=document.createElement("canvas");c.width=c.height=RES;const cx=c.getContext("2d");
    cx.drawImage(nd._demImg,0,0,RES,RES);const d=cx.getImageData(0,0,RES,RES).data;const f=newField();
    const lum=i=>(d[i*4]*.299+d[i*4+1]*.587+d[i*4+2]*.114)/255;
    if(terrainDef.lattice==="hex"){
      // The canvas gives a SQUARE raster; place it on the hex lattice by reading each hex cell's
      // own world x (odd rows +0.5 cell). Row compression cancels under normalisation - see
      // resampleTo - so this is a pure per-row half-cell resample along x.
      for(let y=0;y<nh;y++)for(let x=0;x<RES;x++){
        const sy=Math.min(RES-1,Math.round(y/Math.max(1,nh-1)*(RES-1)));   // dest row -> square source raster row
        const sx=x+0.5*(y&1),x0=Math.min(RES-1,sx|0),x1=Math.min(RES-1,x0+1),fx=sx-x0;
        f[y*RES+x]=lum(sy*RES+x0)*(1-fx)+lum(sy*RES+x1)*fx;}
    }else for(let i=0;i<f.length;i++)f[i]=lum(i);
    nd._dem=f;}
  else if(nd._demRaw){nd._dem=resampleTo(nd._demRaw.u16,nd._demRaw.side,v=>v/65535);}
}
// Square raster -> working lattice. On hex the destination cell (x,y) sits at world
// ( x + 0.5*(y&1), y*sqrt(3)/2 ) in cell units; normalised against the hex world's own extent
// (scale x scale*sqrt(3)/2) the row compression CANCELS - v = y*HEX_ROW/((n-1)*HEX_ROW) = y/(n-1)
// - so the only correction an import needs is the odd-row half-cell shift in x. Without it an
// imported DEM lands sheared against every generator that already honours the seed contract.
function resampleTo(src,side,map){const f=newField(),nh=fieldH();
  const hex=terrainDef.lattice==="hex";
  for(let y=0;y<nh;y++)for(let x=0;x<RES;x++){
    const sy=Math.min(side-1,(y/nh*side)|0);
    if(hex){
      // Interpolate along x, do NOT snap: the whole correction here is a HALF cell, and
      // nearest-neighbour truncation (`|0`) discards exactly that - measured, the parity comb
      // came back 0 with a 0.5-cell residual error until this became a lerp. Square keeps its
      // shipped nearest-neighbour behaviour untouched.
      const fx=(x+0.5*(y&1))/RES*side,x0=Math.min(side-1,fx|0),x1=Math.min(side-1,x0+1),t=fx-x0;
      f[y*RES+x]=map(src[sy*side+x0])*(1-t)+map(src[sy*side+x1])*t;
    }else f[y*RES+x]=map(src[sy*side+Math.min(side-1,(x/RES*side)|0)]);
  }return normalize(f);}
function finishDem(nd){markDirtyFrom(nd.id);buildProps();requestEval();}

function exportHeightmap(){const out=outputNode();if(!out||!out._field){toast("No output to export");return;}
  let f=normalize(out._field);const c=document.createElement("canvas");c.width=c.height=RES;const cx=c.getContext("2d");
  if(terrainDef.lattice==="hex"){
    // Interchange (26): hex is a grid you SIMULATE on and RESAMPLE OUT of - every engine, DCC and
    // DEM consumer expects a square raster. Writing the odd-r array straight to PNG ships a
    // sheared terrain (alternate rows displaced half a cell). Resample to square through the
    // lattice-aware sampler: output pixel (X,Y) is the hex field at world ( X, Y*sqrt(3)/2 ).
    const sq=newField(),rowSpan=(fieldH()-1)/(RES-1);
    for(let y=0;y<RES;y++)for(let x=0;x<RES;x++)sq[y*RES+x]=sampleBilinear(f,x,y*HEX_ROW*rowSpan);   // shape-ok: RESxRES square interchange raster by design; rowSpan maps the output rows onto the field's full world height
    f=sq;
  }
  const img=cx.createImageData(RES,RES);   // NOTE (converted, not an exemption): exported PNG is a square RESxRES interchange raster, not the working lattice
  /* shape-ok: the export PNG is a square RES x RES interchange raster by design; hex rows are resampled into it above */ for(let i=0;i<RES*RES;i++){const v=Math.round(f[i]*255);img.data[i*4]=img.data[i*4+1]=img.data[i*4+2]=v;img.data[i*4+3]=255;}
  // PRECISION DEBT (S6.2 owns the fix): this writer is 8-bit and cannot be otherwise. Canvas 2D
  // ImageData is Uint8ClampedArray and toDataURL re-encodes to 8-bit RGBA, so the *255 above is the
  // real ceiling, not a rounding choice. The UI advertised "16-bit PNG" for this path, which was
  // simply false. 256 levels across a 2600 m vertical range is ~10 m per step - visible terracing
  // on gentle slopes and lethal to any derivative taken downstream. The lossless R32F master plus
  // PNG16/RAW interchange arrive with the S6.2 physical format writers; until then this button is
  // a preview export and is now labelled as one.
  cx.putImageData(img,0,0);const a=document.createElement("a");a.download="terrain_height_"+RES+".png";a.href=c.toDataURL("image/png");a.click();toast("Exported "+RES+"² heightmap PNG (8-bit preview)");}
$("#exportBtn").onclick=exportHeightmap;

/* =====================================================================
   PROJECT DOCUMENT — SAVE / OPEN   (S0.1)

   The format lives in src/core/project.js, which is pure and DOM-free. This section owns the
   BINDINGS: nodes, edges, uid, terrainDef, RES, view, cam, previewMode, satName and selection are
   module-local `let`s that no other module can read or write, so the collect/apply adapters have
   to live here.

   Nothing below runs at module-evaluation time except the two DOM handler assignments at the end
   — `cam` is declared with `let` further down this file, and every function here only runs on a
   user action.
   ===================================================================== */

// --- subgraph definitions and instance evaluation (S8.5 / S8.6) -------------------------------
// Definitions are document state. Instances evaluate a definition's internal DAG in a PRIVATE node
// list, so internal nodes never enter `nodes` and therefore never reach the palette, selection, or
// the parent's serialisation. That is the difference between encapsulation and macro expansion.
let subgraphDefinitions = {};
// ADR-004: "Instances pin (definitionId, version, fullHash). Old instances never float." The table
// above holds the LATEST of each id — what the palette offers and what a new instance binds to. It
// cannot hold two versions at once, so with it alone a v2 registration silently rewrote every
// existing instance's terrain: measured, outerPack's live hash moved from 77337d1c317dcf0f to the
// v2 hash and every instance's output moved with it. The archive keeps every version ever
// registered, keyed by id@version, so a pinned instance keeps computing exactly what it computed.
let subgraphArchive = {};
const archiveKey = (id, version) => String(id) + '@' + String(version);
export function getSubgraphDefinitions(){ return subgraphDefinitions; }
export function getSubgraphArchive(){ return subgraphArchive; }
export function defineSubgraph(def){
  subgraphDefinitions = registerDefinition(subgraphDefinitions, def);
  const stored = subgraphDefinitions[def.id];
  subgraphArchive = { ...subgraphArchive, [archiveKey(def.id, def.version)]: stored };
  // Only instances OF THIS DEFINITION need re-evaluating. Marking every subgraph node dirty was
  // wasted work on every unrelated instance; pinned instances of another version are untouched
  // because their archived definition did not move.
  nodes.forEach(nd=>{ if(nd.type==='subgraph' && String(nd.params&&nd.params.definitionId||'').trim()===def.id) markDirtyFrom(nd.id); });
  return stored;
}
export function clearSubgraphDefinitions(){ subgraphDefinitions = {}; subgraphArchive = {}; }

/**
 * Resolve the definition an instance is bound to, honouring its pin.
 *
 * Returns { def, problem }. A problem is a VISIBLE failure, never a silent substitution: S8.6 says
 * "missing definitions and incompatible versions fail visibly" and ADR-004 says migrations are
 * explicit and never best-effort rewiring. An unpinned instance (one authored before pinning, or
 * one just dropped) binds to the latest and is stamped by stampInstancePin below.
 */
export function resolveInstanceDefinition(params){
  const id = String(params&&params.definitionId||'').trim();
  if(!id) return { def:null, problem:null };
  const pinnedVersion = params.version;
  const pinnedHash = params.hash;
  if(pinnedVersion==null||pinnedVersion==='') {
    const def = subgraphDefinitions[id];
    return { def: def||null, problem: def?null:{ code:'SUBGRAPH_UNKNOWN', id } };
  }
  const def = subgraphArchive[archiveKey(id, pinnedVersion)];
  if(!def) return { def:null, problem:{ code:'SUBGRAPH_VERSION_UNSUPPORTED', id, version:pinnedVersion } };
  if(pinnedHash && def.hash && String(pinnedHash)!==String(def.hash)){
    return { def:null, problem:{ code:'SUBGRAPH_HASH_CONFLICT', id, version:pinnedVersion, pinned:String(pinnedHash), actual:String(def.hash) } };
  }
  return { def, problem:null };
}
/** Stamp an unpinned instance with the version and hash it actually bound to, once. */
export function stampInstancePin(node){
  if(!node||node.type!=='subgraph'||!node.params) return null;
  if(node.params.version!=null&&node.params.version!=='') return null;
  const def = subgraphDefinitions[String(node.params.definitionId||'').trim()];
  if(!def) return null;
  node.params.version = def.version;
  node.params.hash = def.hash || definitionHash(def);
  return node.params;
}

// Immutable-result cache, keyed by the full ADR-004 identity. Two identical instances share an
// entry; two with different overrides can never collide, which is what stops one instance's state
// leaking into another.
const SUBGRAPH_CACHE = new Map();
export function subgraphCacheSize(){ return SUBGRAPH_CACHE.size; }
export function clearSubgraphCache(){ SUBGRAPH_CACHE.clear(); }

function parseOverrides(text){
  const out = {};
  for(const line of String(text||'').split(/\r?\n/)){
    const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(-?[0-9.]+)\s*$/);
    if(m) out[m[1]] = Number(m[2]);
  }
  return out;
}

export function evaluateSubgraphInstance(params, ins, node){
  const resolved = resolveInstanceDefinition(params);
  const def = resolved.def;
  // A pin that cannot be honoured is recorded on the node so the inspector can say which version
  // and hash were asked for, then renders flat. Silently evaluating against a different definition
  // is the behaviour ADR-004 forbids in the words "old instances never float".
  if(node) node._pinProblem = resolved.problem || null;
  if(!def) return null;                       // unknown definition renders flat, visibly, not fatally
  const overrides = parseOverrides(params.overrides);
  // upstreamKeys was `[String(ins[0].length)]`. Every field is RES*RES — shape-ok: prose, no alloc —
  // so that term was the same
  // string for every input in the document and never discriminated: two instances of one definition
  // with equal overrides and DIFFERENT upstream collided on a single entry, and the second returned
  // the first's Float32Array — the same object, not merely equal values. Content digests now.
  // definitionClosure covers the second half of the same defect: a parent's own content does not
  // change when a definition it contains does, so a nested edit left the key identical.
  const key = instanceCacheKey({ definition: def, overrides, seed: terrainDef.seed,
    context: { res: RES, lattice: terrainDef.lattice },
    upstreamKeys: (ins||[]).map(fieldKey),
    definitionClosure: closureHashes(subgraphDefinitions, def) });
  if(SUBGRAPH_CACHE.has(key)) return SUBGRAPH_CACHE.get(key);

  // Evaluate the internal DAG against a PRIVATE node list. `local` never touches `nodes`.
  // Overrides bind BOTH ways, and the comment in subgraph.js used to claim only the second while
  // the code did only the first. As node params they retune the definition's internals; as an inner
  // SCOPE FRAME they shadow document variables of the same id, so a Variable node inside the
  // definition reads the instance's value. Two instances therefore cannot see each other's.
  const local = new Map();
  for(const n of def.nodes) local.set(n.localId, { ...n, params:{ ...(n.params||{}), ...overrides }, _field:null });
  pushScopeFrame({ name:"instance:"+def.id,
    variables: Object.keys(overrides).map(id=>({ id, name:id, value:overrides[id], unit:"none" })) });
  const inbound = new Map();
  for(const e of (def.edges||[])) if(!e.disabled) inbound.set(e.to, e);
  const evalLocal = (localId, guard) => {
    if(guard.has(localId)) return null;
    guard.add(localId);
    const n = local.get(localId);
    if(!n){ guard.delete(localId); return null; }
    if(n._field){ guard.delete(localId); return n._field; }
    const upstream = inbound.get(localId);
    const inputField = upstream ? evalLocal(upstream.from, guard) : (ins[0]||null);
    const type = TYPES[n.type];
    let f;
    try{ f = type ? type.eval(n.params, [inputField, null, null], n) : newField(); }
    catch(err){ console.error('subgraph', n.type, err); f = newField(); }
    if(f && f.values instanceof Map) f = f.values.values().next().value;
    n._field = f;
    guard.delete(localId);
    return f;
  };
  const outPort = (def.outputs||[])[0];
  let result = null;
  try { result = outPort ? evalLocal(outPort.from, new Set()) : null; }
  finally { popScopeFrame(); }          // the frame must not leak if a node throws
  if(result) SUBGRAPH_CACHE.set(key, result);
  return result;
}

// --- New Terrain dialog and creation preflight (S9.2) -----------------------------------------
// THE RULE IS: NOTHING IS ALLOCATED UNTIL THE USER CONFIRMS. Today `newTerrainDocument` gates on a
// confirm() and then synchronously builds and evaluates, and there is no preflight anywhere — so
// asking for a raster too large simply allocates until the tab dies and the author learns the
// answer by losing their work. The preflight is pure arithmetic on counts and byte sizes; it never
// touches a Float32Array, which is what _verify_new_terrain.js spies on.
let pendingNewTerrain=null;

// AUTHORING UNITS AND RESOLUTION MODE.
//
// The dialog used to ask for metres and a column/row count and nothing else, which forced the
// author to do the division that decides the only number that matters physically: how far apart
// two samples are. Every erosion parameter in this app is denominated in cell size, so a graph
// authored at one spacing and rebuilt at another is a different simulation.
//
// Three ways to say the same thing, because different sources state it differently:
//   explicit-samples  columns x rows          — what a game engine's landscape asks for
//   spacing           distance per point      — GIS cell size / ground sample distance, the way
//                                               every DEM, GeoTIFF and SRTM tile is published
//   density           points per unit         — the reciprocal, which is how some tools phrase it
// Extents are authored in the selected unit and converted to metres HERE; the domain is stored in
// metres always, so nothing downstream has to know a unit was ever chosen. AUTHORING_UNITS is the
// same table world-domain.js validates against, not a second copy.
function ntUnitFactor(){ return AUTHORING_UNITS[($("#ntUnit")||{}).value] || 1; }
function ntResolutionFrom(widthM,heightM,posting){
  // vertex posting spans n-1 intervals across the extent; legacy-cell spans n. deriveResolution
  // owns that arithmetic and the rounding rule, so this asks it rather than repeating it.
  const mode=($("#ntResMode")||{}).value||"explicit-samples";
  const f=ntUnitFactor();
  if(mode==="explicit-samples"){
    return {mode:"explicit-samples",requestedSpacingM:null,
      sampleCount:{columns:parseInt($("#ntCols").value,10),rows:parseInt($("#ntRows").value,10)}};
  }
  let spacingM;
  if(mode==="spacing")spacingM=parseFloat($("#ntSpacing").value)*f;
  else{
    const perUnit=parseFloat($("#ntDensity").value);
    spacingM=perUnit>0?f/perUnit:NaN;              // points per unit -> metres per point
  }
  if(!Number.isFinite(spacingM)||spacingM<=0)return {mode,requestedSpacingM:spacingM,sampleCount:{columns:NaN,rows:NaN}};
  const derived=deriveResolution({extentM:{width:widthM,height:heightM},posting,
    resolution:{mode:"spacing",requestedSpacingM:{x:spacingM,y:spacingM}}});
  return {mode,requestedSpacingM:spacingM,sampleCount:derived.sampleCount,actualSpacingM:derived.actualSpacingM};
}
function ntSyncUnitLabels(){
  const u=($("#ntUnit")||{}).value||"m";
  for(const el of document.querySelectorAll("[data-unitlabel]"))el.textContent=u;
  for(const el of document.querySelectorAll("[data-unitlabel-per]"))el.textContent=u+" / point";
  for(const el of document.querySelectorAll("[data-unitlabel-inv]"))el.textContent="points / "+u;
  const mode=($("#ntResMode")||{}).value||"explicit-samples";
  for(const el of document.querySelectorAll("#newTerrainDialog [data-mode]"))el.hidden=el.dataset.mode!==mode;
}

export function previewCreation(){
  ntSyncUnitLabels();
  const f=ntUnitFactor();
  const width=parseFloat($("#ntWidth").value)*f,height=parseFloat($("#ntHeight").value)*f;
  const posting="vertex";
  const res=ntResolutionFrom(width,height,posting);
  const cols=res.sampleCount.columns,rows=res.sampleCount.rows;
  // liveFields is MEASURED from the graph that will exist, not guessed: a blank document holds one
  // field, the templates hold as many as their node count.
  const liveFields=Math.max(1,nodes.length||1);
  // FINITE, not valid. A too-small-but-finite count (1 x 4) must still reach assessCreation, which
  // rejects it with its own DIMENSIONS_INVALID code; intercepting it here produced a rejection
  // carrying no code and broke the caller that reads one. This guard exists only for the new
  // failure mode the spacing/density modes introduce: a non-finite count from a blank or zero field.
  const dims=Number.isFinite(cols)&&Number.isFinite(rows);
  // Say what was actually derived, in both directions, so the author never has to trust a division
  // they cannot see. spacingWasRounded is the honest part: a requested spacing rarely divides the
  // extent exactly, and silently shipping a different one is how a graph's parameters stop meaning
  // what they said.
  const der=$("#ntDerived");
  if(der){
    if(!dims||!Number.isFinite(width)||!Number.isFinite(height)||width<=0||height<=0){der.textContent="\u2014";}
    else{
      const sx=width/(posting==="vertex"?cols-1:cols),sy=height/(posting==="vertex"?rows-1:rows);
      const u=($("#ntUnit")||{}).value||"m",inv=AUTHORING_UNITS[u]||1;
      const rounded=res.mode!=="explicit-samples"&&res.requestedSpacingM>0
        &&(Math.abs(res.requestedSpacingM-sx)>1e-9||Math.abs(res.requestedSpacingM-sy)>1e-9);
      der.innerHTML=`${cols} \u00d7 ${rows} points \u00b7 ${(sx/inv).toPrecision(4)} \u00d7 ${(sy/inv).toPrecision(4)} ${u} per point`
        +(rounded?` <span class="nt-warn">\u00b7 rounded from ${(res.requestedSpacingM/inv).toPrecision(4)} ${u}</span>`:"");
    }
  }
  if(!dims){
    // A rejected preflight still RETURNS a verdict-shaped record. Returning null here broke every
    // caller that reads .verdict — including the oracle — and turned "this size is refused" into a
    // TypeError, which is the wrong failure for a case the dialog is supposed to handle calmly.
    const bad=$("#ntReadout");
    const reason="resolution is not a finite sample count";
    if(bad){bad.textContent="Cannot create: "+reason;bad.dataset.mode="rejected";}
    $("#ntCreate").disabled=true;
    pendingNewTerrain={cols,rows,width,height,unit:($("#ntUnit")||{}).value||"m",resMode:res.mode,
      lattice:$("#ntLattice").value,template:$("#ntTemplate").value,biome:($("#ntBiome")&&$("#ntBiome").value)||DEFAULT_BIOME,
      verdict:{mode:"rejected",code:"DIMENSIONS_INVALID",reason}};
    return pendingNewTerrain;
  }
  const verdict=assessCreation({sampleCount:{columns:cols,rows:rows},liveFields});
  const out=$("#ntReadout");
  if(verdict.mode==="rejected"){out.textContent="Cannot create: "+verdict.reason;out.dataset.mode="rejected";}
  else{
    const pages=verdict.mode==="gpu-required-paged"?decomposePages({sampleCount:{columns:cols,rows:rows}}):null;
    out.textContent=verdict.reason+(pages?` · ${pages.pagesX}x${pages.pagesY} pages, terminal core ${pages.terminalCoreCells.x}x${pages.terminalCoreCells.y}`:"");
    out.dataset.mode=verdict.mode;
  }
  $("#ntCreate").disabled=verdict.mode==="rejected"||!Number.isFinite(width)||!Number.isFinite(height)||width<=0||height<=0;
  pendingNewTerrain={cols,rows,width,height,unit:($("#ntUnit")||{}).value||"m",resMode:res.mode,
    lattice:$("#ntLattice").value,template:$("#ntTemplate").value,biome:($("#ntBiome")&&$("#ntBiome").value)||DEFAULT_BIOME,verdict};
  return pendingNewTerrain;
}
// Build the biome list FROM THE MODULE, never from markup. A hardcoded <option> list is a second
// copy of the table that drifts the moment a preset is added, and the drift is silent: the option
// still selects, it just selects a key nothing answers to.
function populateBiomes(){
  const sel=$("#ntBiome");if(!sel||sel.options.length)return;
  for(const k of BIOME_KEYS){
    const o=document.createElement("option");
    o.value=k;o.textContent=BIOMES[k].label;if(k===DEFAULT_BIOME)o.selected=true;
    sel.appendChild(o);
  }
  syncBiomeNote();
  sel.addEventListener("change",syncBiomeNote);
}
function syncBiomeNote(){
  const sel=$("#ntBiome"),note=$("#ntBiomeNote");if(!sel||!note)return;
  const b=BIOMES[sel.value]||BIOMES[DEFAULT_BIOME];
  // State the numbers, not just the mood. "Cold and damp" is a vibe; "sea 4 degC, lapse 5.8, snow
  // from 690 m" is something an author can check against what they then see on the terrain.
  const snow=b.lapseRate>0?b.seaTemp/b.lapseRate*1000:0;
  note.textContent=b.note+"  ·  sea "+b.seaTemp+" °C · lapse "+b.lapseRate+" °C/km · "
    +(snow>0?"0 °C at "+Math.round(snow)+" m":"below freezing at sea level")
    +" · "+b.precipMmYr+" mm/yr";
}
export function openNewTerrainDialog(){
  populateBiomes();
  $("#newTerrainDialog").hidden=false;previewCreation();
}
export function closeNewTerrainDialog(){$("#newTerrainDialog").hidden=true;pendingNewTerrain=null;}
// Live preflight on every edit, so the readout is never stale relative to the inputs.
for(const id of ["ntCols","ntRows","ntWidth","ntHeight","ntLattice","ntTemplate","ntUnit","ntResMode","ntSpacing","ntDensity","ntBiome"]){
  const el=$("#"+id);if(el){el.addEventListener("input",()=>previewCreation());el.addEventListener("change",()=>previewCreation());}
}
if($("#ntCancel"))$("#ntCancel").onclick=closeNewTerrainDialog;
if($("#ntClose"))$("#ntClose").onclick=closeNewTerrainDialog;
if($("#ntCreate"))$("#ntCreate").onclick=confirmNewTerrain;

export function confirmNewTerrain(){
  const p=pendingNewTerrain||previewCreation();
  if(!p||p.verdict.mode==="rejected")return false;
  const domain={
    version:WORLD_DOMAIN_VERSION,originM:{x:0,y:0},extentM:{width:p.width,height:p.height},
    authoringUnits:{horizontal:p.unit||"m",vertical:"m"},lattice:p.lattice,posting:"vertex",
    resolution:{mode:"explicit-samples",sampleCount:{columns:p.cols,rows:p.rows},actualSpacingM:{x:1,y:1}},
    vertical:{datum:{kind:"unknown",offsetM:0},rangeM:{min:0,max:terrainDef.height||2600}},
  };
  const derived=deriveResolution(domain);
  domain.resolution.actualSpacingM=derived.actualSpacingM;
  const problems=setWorldDomain(domain);
  if(problems.length){toast("Cannot create: "+problems[0].code);return false;}
  terrainDef=createTerrainDef({...terrainDef,scale:p.width,lattice:p.lattice==="hex-pointy-odd-r"?"hex":"square"});
  H_SCALE=terrainDef.height/terrainDef.scale;
  // APPLY THE COLUMN COUNT THE AUTHOR JUST CHOSE. It used to be recorded in the WorldDomain and
  // never reach the evaluator, so a document created at 493 columns still evaluated at whatever RES
  // happened to be — and the separate "working resolution" control was the only thing that set the
  // real grid. That is why picking 1024 after creating a terrain was unreadable: it silently halved
  // the sample spacing of a world whose spacing the author had just stated in metres.
  DOC_SAMPLES=p.cols;
  applyPreviewDetail(PREVIEW_DETAIL);
  closeNewTerrainDialog();
  // Only NOW does anything allocate.
  // THE BIOME IS APPLIED BEFORE THE DOCUMENT IS BUILT, not after. The opening graph is evaluated
  // once as it is created, and a climate written afterwards would leave that first frame showing
  // the previous world's temperature -- which is exactly the class of defect where the app looks
  // right on the second interaction and wrong on the first.
  pendingBiome=p.biome||DEFAULT_BIOME;
  terrainDef=createTerrainDef({...terrainDef,...biomeTerrainOverrides(pendingBiome)});
  newTerrainDocument(p.template==="default",p.template==="canyon"?"canyon":null,true);
  return true;
}

// --- world domain (S9.1) ---------------------------------------------------------------------
// The authoritative frame. Derived from the legacy terrainDef/RES on boot so nothing changes
// numerically today; S9.2 lets the author set it directly and S9.9 makes arbitrary dimensions
// evaluable.
let worldDomain=null;
export function getWorldDomain(){
  if(!worldDomain)worldDomain=domainFromLegacy(terrainDef,RES,fieldH());
  return worldDomain;
}
export function setWorldDomain(d){
  const problems=validateDomain(d);
  if(problems.length)return problems;
  worldDomain={...d};
  return [];
}

// --- document variables (S8.3) ---------------------------------------------------------------
// One number driving many nodes, changed in one place. Held here rather than in core/ because it is
// document state, like nodes and edges, and legacy.js owns the document bindings.
let documentVariables=[
  {id:"seaLevel",name:"Sea level",value:0.32,unit:"none"},
  {id:"reliefScale",name:"Relief scale",value:1,unit:"none"},
];
// The scope CHAIN, not a flat lookup. Today it is one frame deep because subgraphs do not exist
// until S8.5; building the chain now means that story adds a frame rather than a mechanism.
// The scope STACK. S8.3 built a chain and then only ever pushed one frame onto it, which made the
// shadowing path dead code with no production caller — a library function the oracle exercised
// directly. Subgraph instances now push a real inner frame, so `currentScope()` is genuinely
// multi-frame during an instance evaluation.
let scopeStack=[];
export function currentScope(){return makeScope([{name:"document",variables:documentVariables},...scopeStack]);}
export function documentScope(){return currentScope();}
export function pushScopeFrame(frame){scopeStack.push(frame);return scopeStack.length;}
export function popScopeFrame(){scopeStack.pop();return scopeStack.length;}
export function scopeDepth(){return 1+scopeStack.length;}
export function setDocumentVariables(list){
  const problems=validateVariables(list);
  if(problems.length)return problems;              // refuse the whole table rather than half-apply it
  documentVariables=list.map(v=>({...v}));
  nodes.forEach(nd=>{if(nd.type==="variable")markDirtyFrom(nd.id);});
  return [];
}
export function getDocumentVariables(){return documentVariables.map(v=>({...v}));}

// --- edge port identity (S2.2) --------------------------------------------------------------
// A v1 edge addressed its destination by ARRAY POSITION into the plugin's `ins` list and its source
// by the whole node. Both are exactly what ADR-002 forbids as identifiers: insert an input and
// every saved graph silently rewires itself. v2 edges carry {fromPort, toPort}.
//
// In memory the edge keeps `slot` as well, and `slot` remains what the three evaluators index. That
// is deliberate for this cut: port identity is a schema and authoring change, not a numerical one,
// so the evaluator is untouched and the digest cannot move. S2.3 takes evaluation itself.
function nodeOutPortId(type){
  const def=TYPES[type],outs=def&&def.outputs;
  if(!outs||!outs.length)return null;
  return (outs.find(p=>p.primary)||outs[0]).id;
}
function nodeInPorts(nd){
  const def=TYPES[nd.type],declared=(def&&def.inputs)||[],arity=nodeInputs(nd).length;
  if(arity<=declared.length)return declared.slice(0,arity);
  // ColorMixer authors its arity at runtime, so beyond the declared template the ports are
  // synthesised by the same rule that named them: "Layer 4" -> layer4.
  const out=declared.slice();
  for(let i=declared.length;i<arity;i++)out.push({id:"layer"+(i+1),name:"Layer "+(i+1),legacySlot:i,semantic:"anyScalarRaster",unit:"none"});
  return out;
}
function inPortIdForSlot(nd,slot){const p=nodeInPorts(nd);return (p[slot]&&p[slot].id)||null;}

// --- Connection-time type rejection — S8.2 and S8.5 ----------------------------------------------
//
// canConnect arrived with typed ports in S2.1 and was imported here from that first cut, but until
// now the only caller was the test bridge: `grep -n canConnect src/legacy.js` returned the import
// and the re-export and nothing else. The library refused a wire and the editor made it anyway, so
// both stories' "rejected at connection time" clauses were gated by oracles exercising the library
// rather than the application. The verdict has to live on the drop path itself, which is this.
//
// The verdict reads the LIVE descriptor tables rather than a hard-coded pair list, so changing a
// port's unit or semantic changes what the editor accepts in the same edit — which is also how the
// gate proves the check is wired in at all: mutate the table, and the editor's answer must move.
function wireVerdict(fromNode,fromSlot,toNode,toSlot){
  if(!fromNode||!toNode)return{ok:false,code:"PORT_ID_INVALID",reason:"missing endpoint"};
  const src=nodeOutputs(fromNode)[fromSlot||0],dst=nodeInPorts(toNode)[toSlot];
  // A slot with no declared descriptor predates typed ports. Refusing those would make the editor
  // unusable on every node still carrying only a legacy `ins` label, so they are permitted and
  // marked untyped — recorded as a known hole, not laundered into a silent "ok".
  if(!src||!dst)return{ok:true,untyped:true};
  return canConnect(src,dst);
}
// The single mutating entry point for "the user connected two ports". Every rejection returns
// BEFORE recordHistory, so a refused drop leaves the graph and the undo stack untouched — the old
// mouseup handler already took that care for cycles and it is preserved for type refusals.
// `opts.records:false` suppresses the undo record because the CALLER has already opened one that
// covers the whole gesture. Quick create is the case: makeNode() records, and having linkDrop record
// again split one authoring action into two undo entries — measured, the first undo removed the new
// edge and left the node stranded (nodes 8, edges 6 where 7 and 6 were expected).
function linkDrop(fromId,fromSlot,toId,toSlot,opts){
  const from=nodeById(fromId),to=nodeById(toId);
  if(!from||!to)return{ok:false,code:"PORT_ID_INVALID",reason:"that endpoint no longer exists"};
  if(fromId===toId)return{ok:false,code:"SELF_LINK",reason:"A node cannot feed itself"};
  if(wouldCycle(fromId,toId))return{ok:false,code:"CYCLE",reason:"That would create a cycle"};
  const verdict=wireVerdict(from,fromSlot,to,toSlot);
  if(!verdict.ok)return verdict;
  if(!opts||opts.records!==false)recordHistory();
  if(opts&&opts.replacing)edges=edges.filter(x=>x!==opts.replacing);
  edges=edges.filter(x=>!(x.to===toId&&x.slot===toSlot));
  edges.push({from:fromId,fromPort:(nodeOutputs(from)[fromSlot||0]||{}).id||undefined,
    to:toId,toPort:inPortIdForSlot(to,toSlot)||undefined,slot:toSlot});
  markDirtyFrom(toId);requestEval();
  return{ok:true,untyped:!!verdict.untyped};
}
function slotForInPortId(nd,portId){const p=nodeInPorts(nd);const i=p.findIndex(x=>x.id===portId);return i<0?null:i;}
// Back-fill port identity onto any edge that predates it. Called before a save and after template
// construction; an edge whose endpoints have gone is left for deleteEdge to clean up.
function ensureEdgePorts(){
  for(const e of edges){
    if(e.fromPort&&e.toPort)continue;
    const from=nodeById(e.from),to=nodeById(e.to);
    if(!from||!to)continue;
    if(!e.fromPort){const id=nodeOutPortId(from.type);if(id)e.fromPort=id;}
    if(!e.toPort){const id=inPortIdForSlot(to,e.slot);if(id)e.toPort=id;}
  }
  return edges;
}

// Frozen at module load, before SatMap Studio can add anything, so "custom" means "not shipped".
const BUILTIN_SATMAP_NAMES=Object.freeze(Object.keys(SATMAPS));

// Template graphs replace params wholesale (`out.params={norm:"on"}`), so the live app routinely
// holds nodes missing schema keys; buildProps hydrates them lazily and only for the SELECTED node.
// A document must not inherit that unevenness, so both endpoints map into a normal form. This runs
// on LOAD only, never on save: hydrating a live graph mid-session would move terrain under the
// user, and Ctrl+S must never change what is on screen.
function normalizeNodeParams(nd){
  const def=TYPES[nd.type];if(!def||!def.params)return 0;
  let added=0;
  for(const pr of def.params){if(!(pr.key in nd.params)){nd.params[pr.key]=cloneParams({v:pr.def}).v;added++;}}
  if(def.migrateParams)def.migrateParams(nd.params);
  return added;
}
function normalizeAllNodeParams(){let n=0,keys=0;for(const nd of nodes){const a=normalizeNodeParams(nd);if(a){n++;keys+=a;}}return{nodesChanged:n,keysAdded:keys};}

// Only palettes some node actually references, or the active global one, and only when they are
// not built in. An empty set is omitted entirely rather than written as {}.
function collectCustomSatmaps(){
  const used=new Set();
  if(satName&&!BUILTIN_SATMAP_NAMES.includes(satName))used.add(satName);
  for(const nd of nodes){const g=nd.params&&nd.params.gradient;if(typeof g==="string"&&!BUILTIN_SATMAP_NAMES.includes(g))used.add(g);}
  const out={};for(const name of [...used].sort())if(SATMAPS[name])out[name]=SATMAPS[name];
  return Object.keys(out).length?{satmaps:out}:null;
}

// The writer is VERBATIM and side-effect-free.
function collectProjectState(){
  const palettes=collectCustomSatmaps();
  const vars=getDocumentVariables();
  const domain=getWorldDomain();
  // Embed the LATEST of each referenced id, plus every archived version a pinned instance still
  // points at. Embedding only the latest would drop the very definitions the pins exist to protect,
  // and the document would reload with instances failing on a version it no longer carries.
  const usedDefs=referencedDefinitions(subgraphDefinitions,nodes).map(id=>subgraphDefinitions[id]);
  const embedded=new Set(usedDefs.map(d=>archiveKey(d.id,d.version)));
  for(const nd of nodes){
    if(nd.type!=='subgraph'||!nd.params)continue;
    const k=archiveKey(String(nd.params.definitionId||'').trim(),nd.params.version);
    if(nd.params.version!=null&&subgraphArchive[k]&&!embedded.has(k)){embedded.add(k);usedDefs.push(subgraphArchive[k]);}
  }
  return{
    terrain:{...terrainDef},
    build:{res:RES,quality:BUILD_QUALITY,resLock:SCALE_RES},
    nodes:nodes.map(nd=>{
      const out={id:nd.id,type:nd.type,x:nd.x,y:nd.y,w:nd.w,params:cloneParams(nd.params)};
      if(nd._inputs)out.inputs=[...nd._inputs];
      if(nd._demSrc)out.source=nd._demSrc;
      return out;
    }),
    edges:ensureEdgePorts().map(e=>{const o={from:e.from,fromPort:e.fromPort,to:e.to,toPort:e.toPort};if(e.disabled)o.disabled=true;return o;}),
    uid,
    ...(palettes?{palettes}:{}),
    domain,
    ...(vars.length?{variables:vars}:{}),
    ...(usedDefs.length?{definitions:usedDefs}:{}),
    workspace:{
      selectedId:selected?selected.id:null,
      selectedEdgeKey:selectedEdge||null,
      previewMode,satName,
      graphView:{x:view.x,y:view.y,z:view.z},
      camera:{az:cam.az,el:cam.el,dist:cam.dist,target:[...cam.target],fov:cam.fov},
    },
  };
}

export function saveProjectText(){return serializeProject(collectProjectState());}

// Declared here rather than re-exported so the generated test bridge can publish it: an imported
// binding cannot be bridged, and the oracle needs to drive the migration dispatch directly.
export const PROJECT={serializeProject,parseProject,migrateProject,validateProject,PROJECT_SCHEMA_VERSION};

// Same reason as PROJECT: an imported binding cannot be bridged, so the typed-port surface is
// republished from a legacy.js-declared const for the S2.1 oracle.
export const PORTS={canConnect,validatePortList,attachLegacyPorts,GENERICS,SEMANTICS,UNITS,RANGE,LEGACY_PORTS,LEGACY_ROSTER,LEGACY_INS_LABELS};

// The aux-map registry, republished for the S2.4 oracle for the same reason as PORTS and PROJECT:
// an imported binding cannot be bridged.
export const AUXMAPS={AUX_MAPS,AUX_LENSES,SIDE_CHANNEL_LEDGER,semanticDebt,debtByOwner,validateAuxDeclaration};

export const DOCTRINE={validateLegalOrder,validateLens,DOCTRINE_STAGES,DERIVED_PRODUCERS,HEIGHT_WRITERS};

export const PORTS_EXPR={parseExpr,evalExpr,EXPR_FUNCTIONS,EXPR_MAX_NODES,EXPR_MAX_DEPTH};

export const VARS={documentScope,currentScope,scopeDepth,setDocumentVariables,getDocumentVariables,validateVariables,requireVariable,makeScope,VARIABLE_UNITS};

export const DOMAIN={getWorldDomain,setWorldDomain,domainFromLegacy,deriveResolution,validateDomain,spacingWasRounded,WORLD_DOMAIN_VERSION};

export const FEASIBILITY_API={assessCreation,decomposePages,formatBytes};

export const SUBGRAPHS={defineSubgraph,getSubgraphDefinitions,getSubgraphArchive,resolveInstanceDefinition,stampInstancePin,clearSubgraphDefinitions,clearSubgraphCache,subgraphCacheSize,definitionHash,findRecursion,validateDefinition,instanceCacheKey,referencedDefinitions,closureHashes,fieldKey,SUBGRAPH_VERSION};

// Restoring is deliberately close to restoreGraph: same runtime-field reset, same H_SCALE recompute.
// Undo history is CLEARED, not carried — an undo across an Open would splice two unrelated
// documents together and the result would be neither.
function applyProjectDocument(doc){
  const nextNodes=doc.graph.nodes.map(n=>({
    id:n.id,type:n.type,x:n.x,y:n.y,w:n.w,params:cloneParams(n.params),
    _inputs:Array.isArray(n.inputs)?[...n.inputs]:null,
    _demSrc:n.source||null,
    _field:null,_thumb:null,_dirty:true,_dem:null,_demImg:null,_demRaw:null,
    _snowLayer:null,_temperatureC:null,_solarShadow:null,_solarExposure:null,_wind:null,
  }));
  if(doc.palettes&&doc.palettes.satmaps)for(const [name,stops] of Object.entries(doc.palettes.satmaps))SATMAPS[name]=stops;
  if(Array.isArray(doc.variables))setDocumentVariables(doc.variables);
  if(doc.domain)worldDomain={...doc.domain};
  if(Array.isArray(doc.definitions)){
    clearSubgraphDefinitions();
    for(const d of doc.definitions){
      // VERIFY THE HASH THE DOCUMENT STATES. registerDefinition recomputes and stores its own, so a
      // document claiming a hash its content does not produce used to load without a word — the
      // conflict path is unreachable on load because the table was just cleared. A corrupt or
      // tampered definition is a visible load error, not something to quietly correct.
      if(d&&d.hash){
        const actual=definitionHash(d);
        if(String(d.hash)!==String(actual))
          throw new Error('definition '+d.id+' v'+d.version+' states hash '+d.hash+' but its content hashes to '+actual);
      }
      subgraphDefinitions=registerDefinition(subgraphDefinitions,d);
      const stored=subgraphDefinitions[d.id];
      if(stored&&stored.version===d.version)subgraphArchive={...subgraphArchive,[archiveKey(d.id,d.version)]:stored};
      else subgraphArchive={...subgraphArchive,[archiveKey(d.id,d.version)]:{...d,hash:definitionHash(d)}};
    }
  }

  nodes=nextNodes;
  // Derive the legacy slot from the stable port id. That is the whole point of v2: the wire
  // remembers which INPUT it feeds, not which position that input happened to occupy.
  edges=doc.graph.edges.map(e=>{
    const to=nextNodes.find(n=>n.id===e.to);
    const slot=to?slotForInPortId(to,e.toPort):null;
    return{...e,slot:slot==null?0:slot};
  });
  uid=doc.graph.uid;
  terrainDef=createTerrainDef(doc.terrain);
  H_SCALE=terrainDef.height/terrainDef.scale;

  const ws=doc.workspace||{};
  if(ws.graphView&&Number.isFinite(ws.graphView.x))view={x:ws.graphView.x,y:ws.graphView.y,z:ws.graphView.z};
  if(ws.camera&&Number.isFinite(ws.camera.az))cam={az:ws.camera.az,el:ws.camera.el,dist:ws.camera.dist,target:[...ws.camera.target],fov:ws.camera.fov};
  if(ws.previewMode==="output"||ws.previewMode==="selected")previewMode=ws.previewMode;
  if(typeof ws.satName==="string"&&SATMAPS[ws.satName]){satName=ws.satName;buildSatLUT(satName);}

  // Normal form BEFORE anything evaluates, so a sparse document cannot produce different terrain
  // from the same document saved dense.
  normalizeAllNodeParams();
  // Rebuild every imported heightfield from its retained source at the CURRENT resolution. _dem is
  // derived, never persisted: it is a pure function of the source plus RES plus the lattice, and
  // freezing one resolution into the file would go stale the moment either changed.
  for(const nd of nodes)if(nd._demSrc)rebuildDemFromProjectSource(nd);

  undoStack.length=0;redoStack.length=0;
  selected=ws.selectedId==null?null:nodeById(ws.selectedId);
  selectedEdge=ws.selectedEdgeKey&&edgeByKey(ws.selectedEdgeKey)?ws.selectedEdgeKey:null;
  const build=doc.build||{};
  if(Number.isInteger(build.res)&&build.res>=64)applyWorkingResolution(build.res);
  buildProps();drawGraph();evalGraph();updateHistoryButtons();syncEditorCommandState();
  return true;
}

// Rebuild an import node's heightfield from the embedded source bytes.
function rebuildDemFromProjectSource(nd){
  const src=nd._demSrc;if(!src)return;
  if(src.kind==="raw16"&&typeof src.base64==="string"){
    const bin=atob(src.base64),bytes=new Uint8Array(bin.length);
    for(let i=0;i<bin.length;i++)bytes[i]=bin.charCodeAt(i);
    nd._demRaw={u16:new Uint16Array(bytes.buffer),side:src.side};nd._demImg=null;buildDemFromSource(nd);
  }else if(src.kind==="image"&&typeof src.dataUrl==="string"){
    // Asynchronous by nature; the node evaluates flat until the decode lands, then re-evaluates.
    const img=new Image();
    img.onload=()=>{nd._demImg=img;nd._demRaw=null;buildDemFromSource(nd);markDirtyFrom(nd.id);requestEval();};
    img.src=src.dataUrl;
  }
}

export function loadProjectText(text){
  const{doc,warnings}=parseProject(text);
  const upgraded=migrateProject(doc,{targetVersion:PROJECT_SCHEMA_VERSION,migrations:PROJECT_MIGRATIONS});
  validateProject(upgraded,{types:TYPES,arityOf:(type,node)=>(node&&node.inputs?node.inputs.length:(TYPES[type]&&TYPES[type].ins?TYPES[type].ins.length:0)),portsOf:(type,node)=>({inputs:nodeInPorts({type,_inputs:node&&node.inputs}),outputs:(TYPES[type]&&TYPES[type].outputs)||[]})});
  applyProjectDocument(upgraded);
  return{warnings};
}

// S2.2 adds `1: migrateV1toV2` here and changes nothing else.
// S2.2: the dispatch gains its first real step. Ports resolve from the LIVE registry, so a v1
// document written before a plugin gained an input still migrates against that plugin's current
// declaration rather than a snapshot of it.
const PROJECT_MIGRATIONS={
  // S9.1: v2 -> v3 adds the WorldDomain, built from the legacy terrain block so a document saved
  // before this story opens with numerically identical terrain.
  2:doc=>migrateV2toV3(doc,{buildDomain:(terrain,build)=>domainFromLegacy(
    terrain,
    Number.isInteger(build.res)?build.res:RES,
    null)}),
  1:doc=>migrateV1toV2(doc,{resolve:(type,node)=>({
    inputs:node&&Array.isArray(node.inputs)
      ?node.inputs.map((name,i)=>({id:(TYPES[type]&&TYPES[type].inputs&&TYPES[type].inputs[i]&&TYPES[type].inputs[i].id)||("layer"+(i+1)),legacySlot:i}))
      :((TYPES[type]&&TYPES[type].inputs)||[]),
    outputs:(TYPES[type]&&TYPES[type].outputs)||[],
  })}),
};

function saveProjectFile(){
  let text;
  try{text=saveProjectText();}
  catch(err){toast(err instanceof ProjectError?("Could not save: "+err.message):"Could not save this project");console.error(err);return false;}
  const blob=new Blob([text],{type:"application/json"});
  const url=URL.createObjectURL(blob),a=document.createElement("a");
  a.download="terrain"+PROJECT_FILE_EXTENSION;a.href=url;a.click();
  setTimeout(()=>URL.revokeObjectURL(url),0);
  toast("Saved project ("+nodes.length+" nodes)");
  return true;
}
function openProjectFile(){$("#projectFileInput").click();}
$("#projectFileInput").onchange=e=>{
  const file=e.target.files[0];e.target.value="";
  if(!file)return;
  file.text().then(text=>{
    try{const{warnings}=loadProjectText(text);
      toast("Opened project ("+nodes.length+" nodes)"+(warnings.length?" · "+warnings[0].message:""));}
    catch(err){
      // A refused load leaves the current document untouched, which is the point: this format
      // never best-effort repairs a graph, because silently rewiring one is worse than refusing.
      toast(err instanceof ProjectError?("Could not open: "+err.message):"Could not open that project");
      console.error(err);
    }
  });
};

/* =====================================================================
   WEBGL 3D VIEWPORT
   ===================================================================== */
const glc=$("#gl");let gl,terrainProg,waterProg,waterMaskProg,compProg,buffers,wTex,hTex,iTex,isTex,satTex,gbuf=null,USE_DEFERRED=false;
const DEFAULT_HERO={az:0.7,el:0.62,dist:2.6,target:[0,.05,0],fov:1.05};
const copyCam=c=>{const copy={az:c.az,el:c.el,dist:c.dist,target:[...c.target]};
  if(Number.isFinite(c.fov))copy.fov=c.fov;return copy;};
let cam=copyCam(DEFAULT_HERO),shadeMode=0,wire=false;
function buildSatLUT(name){buildSatLUTStops(SATMAPS[name]||SATMAPS.Temperate);}
function buildSatLUTStops(stops){                            // bake a 256-wide RGBA LUT texture from stops [[pos,[r,g,b]],...]
  if(!gl||!stops||!stops.length)return;const W=256,d=new Uint8Array(W*4);
  for(let i=0;i<W;i++){const t=i/(W-1);let a=stops[0],b=stops[stops.length-1];
    for(let k=0;k<stops.length-1;k++){if(t>=stops[k][0]&&t<=stops[k+1][0]){a=stops[k];b=stops[k+1];break;}}
    const f=(t-a[0])/((b[0]-a[0])||1);
    for(let c=0;c<3;c++)d[i*4+c]=Math.round(a[1][c]+(b[1][c]-a[1][c])*Math.max(0,Math.min(1,f)));d[i*4+3]=255;}
  if(!satTex){satTex=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,satTex);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);}
  gl.bindTexture(gl.TEXTURE_2D,satTex);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,W,1,0,gl.RGBA,gl.UNSIGNED_BYTE,d);
}
// ---- SatMap layer compositing (colour in the graph): each SatMap node is a colour layer; masked + blended into a per-vertex RGB ----
function sampleStops(stops,t){t=clamp(t,0,1);let a=stops[0],b=stops[stops.length-1];
  for(let k=0;k<stops.length-1;k++){if(t>=stops[k][0]&&t<=stops[k+1][0]){a=stops[k];b=stops[k+1];break;}}
  const f=clamp((t-a[0])/((b[0]-a[0])||1),0,1);
  return[(a[1][0]+(b[1][0]-a[1][0])*f)/255,(a[1][1]+(b[1][1]-a[1][1])*f)/255,(a[1][2]+(b[1][2]-a[1][2])*f)/255];}
function satLayerColor(L,i){                          // one SatMap owns exactly one gradient
  const drv=L.driver?L.driver[i]:0,dv=L.reverse==="on"?1-drv:drv;
  const rp={low:[.025,7],med:[.045,13],high:[.075,23],ultra:[.115,39]}[L.rough];
  let chaos=0;
  if(rp){const px=i%RES,py=(i/RES)|0;chaos=(vnoise(px/RES*rp[1]+3.7,py/RES*rp[1]+11.2,1709)-.5)*2*rp[0];}
  const x=clamp(L.rangeLo+(L.rangeHi-L.rangeLo)*dv+L.shift+chaos,0,1);
  const c=sampleStops(SATMAPS[L.gradient]||SATMAPS.Temperate,x);
  return gradeWeatherColor(c[0],c[1],c[2],L.hue||0,L.saturation||0,L.lightness||0);}
function satBlend(dst,src,m,mode){const o=[0,0,0];
  for(let c=0;c<3;c++){let s=src[c];
    if(mode==="add")s=clamp(dst[c]+src[c],0,1);
    else if(mode==="subtract")s=clamp(dst[c]-src[c],0,1);
    else if(mode==="difference")s=Math.abs(dst[c]-src[c]);
    else if(mode==="multiply")s=dst[c]*src[c];
    else if(mode==="screen")s=1-(1-dst[c])*(1-src[c]);
    else if(mode==="divide")s=clamp(dst[c]/Math.max(src[c],1/255),0,1);
    else if(mode==="divide2")s=clamp(src[c]/Math.max(dst[c],1/255),0,1);
    else if(mode==="max")s=Math.max(dst[c],src[c]);           // Gaea's Combine "Max" — the documented SatMap blend
    else if(mode==="min")s=Math.min(dst[c],src[c]);
    else if(mode==="hypotenuse")s=clamp(Math.hypot(dst[c],src[c]),0,1);
    else if(mode==="overlay")s=dst[c]<0.5?2*dst[c]*src[c]:1-2*(1-dst[c])*(1-src[c]);
    else if(mode==="power")s=Math.pow(clamp(dst[c],0,1),.25+clamp(src[c],0,1)*3.75);
    o[c]=clamp(dst[c]+(s-dst[c])*m,0,1);}
  return o;}
function satNodeColorField(nd,n){const nh=latticeRows(n);                     // a single SatMap node's colour as a per-vertex field
  const L={...nd.params,driver:nd._driver},col=new Float32Array(n*nh*3);
  for(let i=0;i<n*nh;i++){const c=satLayerColor(L,i);col[i*3]=c[0];col[i*3+1]=c[1];col[i*3+2]=c[2];}
  return col;}
function blendFields(base,over,nd,n){const nh=latticeRows(n);                 // composite `over` onto `base` by (nd mask × opacity) with nd blend mode
  if(!base)return over;if(!over)return base;
  const col=new Float32Array(n*nh*3),mask=nd._mask,op=(nd.params.opacity!=null?nd.params.opacity:1),mode=nd.params.blend||"normal";
  for(let i=0;i<n*nh;i++){const m=(mask?clamp(mask[i],0,1):1)*op;
    const o=satBlend([base[i*3],base[i*3+1],base[i*3+2]],[over[i*3],over[i*3+1],over[i*3+2]],m,mode);
    col[i*3]=o[0];col[i*3+1]=o[1];col[i*3+2]=o[2];}
  return col;}
function boxBlurScalar(src,n,r){const nh=latticeRows(n);                       // summed-area box filter: O(N), independent of radius
  if(r<=0)return Float32Array.from(src);
  const s=n+1,ii=new Float64Array(s*(nh+1)),out=new Float32Array(n*nh);
  for(let y=0;y<nh;y++){let row=0,ir=(y+1)*s,prev=y*s,si=y*n;
    for(let x=0;x<n;x++){row+=src[si+x];ii[ir+x+1]=ii[prev+x+1]+row;}}
  for(let y=0;y<nh;y++){const ya=Math.max(0,y-r),yb=Math.min(nh,y+r+1);
    for(let x=0;x<n;x++){const xa=Math.max(0,x-r),xb=Math.min(n,x+r+1);
      out[y*n+x]=(ii[yb*s+xb]-ii[ya*s+xb]-ii[yb*s+xa]+ii[ya*s+xa])/((xb-xa)*(yb-ya));}}
  return out;
}
function blurColorMass(rgb,mass,n,r){const nh=latticeRows(n);
  if(r<=0)return{rgb,mass};const N=n*nh,out=new Float32Array(N*3);
  for(let c=0;c<3;c++){const ch=new Float32Array(N);for(let i=0;i<N;i++)ch[i]=rgb[i*3+c];
    const b=boxBlurScalar(ch,n,r);for(let i=0;i<N;i++)out[i*3+c]=b[i];}
  return{rgb:out,mass:boxBlurScalar(mass,n,r)};
}
function colorErodeField(base,h,p,mask,n,owner){const nh=latticeRows(n);       // owned colour-advection/deposition model; height is unchanged
  const N=n*nh,laminar=p.laminar==="on",seed=p.seed|0;
  // Transport is a WORLD distance: the old min(resScale(),2.5) cap froze it in cells above 480
  // square, so reach silently shrank as resolution grew. The 96-step clamp is the cost guard -
  // note it saturates the top of the slider at high grids (above ~0.34 at 4096) rather than
  // shrinking the world reach, which is the honest direction to fail in.
  const steps=clamp(Math.round((2+p.transport*10)*resScale()),1,96);
  let route=owner&&owner._colorErosionRoute,recv,jumps;
  if(route&&route.h===h&&route.n===n&&route.steps===steps&&route.laminar===laminar&&route.seed===seed){
    recv=route.recv;jumps=route.jumps;
  }else{
    // Depression handling BEFORE flow routing - the Legal Order's first law applies to pigment
    // too. Routed on raw h, 98.8% of all deposited mass landed on the 1.2% of cells that are
    // pits (measured: an 80x concentration) and the channels got nothing. Fill for ROUTING
    // only; deposition and the visual pass still read the real surface. (priorityFloodFill
    // reads global RES - callers must pass n === RES, which resolveColor guarantees.)
    const hr=priorityFloodFill(h);
    recv=new Int32Array(N);
    const nb=[[-1,0],[1,0],[0,-1],[0,1],[-1,-1],[1,1],[-1,1],[1,-1]];
    for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const i=y*n+x,hi=hr[i];let best=i,bv=hi;
      for(let k=0;k<8;k++){const xx=x+nb[k][0],yy=y+nb[k][1];if(xx<0||yy<0||xx>=n||yy>=nh)continue;
        const j=yy*n+xx,hj=hr[j];if(hj>=hi-1e-8)continue;
        const score=hj+(laminar?0:(hash2(x+k*17,y-k*13,seed)-.5)*2e-5);
        if(score<bv){bv=score;best=j;}}
      recv[i]=best;}
    const levels=Math.ceil(Math.log2(steps+1));jumps=[recv];
    for(let l=1;l<levels;l++){const a=jumps[l-1],b=new Int32Array(N);for(let i=0;i<N;i++)b[i]=a[a[i]];jumps.push(b);}
    if(owner)owner._colorErosionRoute={h,n,steps,laminar,seed,recv,jumps};
  }
  const advance=(i,d)=>{let bit=0;while(d>0){if(d&1)i=jumps[Math.min(bit,jumps.length-1)][i];d>>=1;bit++;}return i;};
  let dep=new Float32Array(N*3),mass=new Float32Array(N);
  const density=clamp(p.density,0,1),hold=clamp(p.hold,0,1),flow=clamp(p.flow,0,1);
  if(density<=1e-5||p.blend<=1e-5)return Float32Array.from(base);
  const fr=[.34,.67,1],fw=[.28,.31,.41+flow*.65];
  for(let i=0;i<N;i++){if(recv[i]===i)continue;
    const sm=p._sediment?clamp(p._sediment[i],0,1):1,w0=density*(p._sediment?(.18+.82*sm):(.55+.45*Math.min(1,Math.abs(h[i]-h[recv[i]])*n)));
    if(w0<=1e-6)continue;
    const r=base[i*3],g=base[i*3+1],b=base[i*3+2],lum=.2126*r+.7152*g+.0722*b;
    const mr=lum*.92,mg=lum*.82,mb=lum*.70,pr=mr+(r-mr)*hold,pg=mg+(g-mg)*hold,pb=mb+(b-mb)*hold;
    for(let q=0;q<3;q++){const d=advance(i,Math.max(1,Math.round(steps*fr[q]))),w=w0*fw[q];
      dep[d*3]+=pr*w;dep[d*3+1]+=pg*w;dep[d*3+2]+=pb*w;mass[d]+=w;}}
  const br=Math.round(clamp(p.diffusion,0,1)*6*resScale());if(br>0){const z=blurColorMass(dep,mass,n,br);dep=z.rgb;mass=z.mass;}
  const out=new Float32Array(N*3);
  for(let i=0;i<N;i++){const m=mass[i],fm=m>1e-7?1-Math.exp(-m*(4+flow*7)):0,msk=mask?clamp(mask[i],0,1):1;
    const a=clamp(p.blend*fm*msk,0,1),j=i*3;
    if(m>1e-7){out[j]=base[j]+(dep[j]/m-base[j])*a;out[j+1]=base[j+1]+(dep[j+1]/m-base[j+1])*a;out[j+2]=base[j+2]+(dep[j+2]/m-base[j+2])*a;}
    else{out[j]=base[j];out[j+1]=base[j+1];out[j+2]=base[j+2];}}
  return out;
}
function gradeWeatherColor(r,g,b,hue,sat,light){
  if(Math.abs(hue)>1e-6){const Y=.299*r+.587*g+.114*b,I=.596*r-.274*g-.322*b,Q=.211*r-.523*g+.312*b,a=hue*Math.PI;
    const ii=I*Math.cos(a)-Q*Math.sin(a),qq=I*Math.sin(a)+Q*Math.cos(a);r=Y+.956*ii+.621*qq;g=Y-.272*ii-.647*qq;b=Y-1.106*ii+1.703*qq;}
  const l=.2126*r+.7152*g+.0722*b,k=Math.max(0,1+sat);r=l+(r-l)*k;g=l+(g-l)*k;b=l+(b-l)*k;
  if(light>=0){r+= (1-r)*light;g+=(1-g)*light;b+=(1-b)*light;}else{r*=1+light;g*=1+light;b*=1+light;}
  return[clamp(r,0,1),clamp(g,0,1),clamp(b,0,1)];
}
function weatherColorField(base,h,p,mask,n,owner){const nh=latticeRows(n);       // exposed relief + sheltered dirt; operates on sRGB colour data
  // Signal radius is a WIDTH (geometry): full grid ratio, same policy as Color Erosion above -
  // the old min(resScale(),2.5) cap froze it in cells above 480 square.
  const N=n*nh,r=Math.max(1,Math.round((1+Math.pow(2,p.scale*4.5))*resScale()));
  let cached=owner&&owner._weatherSignal,signal;
  if(cached&&cached.h===h&&cached.n===n&&cached.r===r&&cached.creep===p.creep)signal=cached.signal;
  else{
    const smoothH=boxBlurScalar(h,n,r);let mean=0;
    for(let i=0;i<N;i++)mean+=Math.abs(h[i]-smoothH[i]);mean/=N;
    // `scale` is a WAVELENGTH control, not a strength control, and that is deliberate: the gain
    // normalises by the mean of |h - blur(h,r)| so the effect behaves the same on flat and on
    // mountainous terrain. Strength belongs to `amount`.
    // Recorded so the next person does not re-run the experiment: partially un-normalising this
    // (gain scaled by an anchored function of p.scale) was tried and MEASURED - authority moved
    // 3.15 -> 3.24 on the p99 sweep, i.e. nothing. It was reverted.
    //
    // CORRECTION, from a second cross-model review: the first explanation given for that null was
    // wrong on two counts and is retracted here rather than left in the history.
    //   'tanh is already near saturation' is FALSE for the bulk. The normalisation makes the mean
    //   |tanh argument| about 1/3.2 = 0.31, which is nearly linear; only the distribution TAIL
    //   saturates - and the tail is exactly what a p99 metric reads, so the null was substantially
    //   a property of the instrument, not of the code. Isolating a real amplitude effect needs r
    //   held FIXED while only the multiplier sweeps, read on a mid-quantile over active cells.
    //   'amount dominates the final term' is a NON-EXPLANATION: amount is constant during a scale
    //   sweep and cannot mask a multiplicative change in ex. What amount's own 12.71 span actually
    //   shows is that POST-tanh multipliers have full authority under this metric - so if scale
    //   were ever wanted as a strength control, the intervention is to fold a p.scale factor into
    //   the ex/re terms below, not into gain above.
    // The design conclusion stands (scale is wavelength, amount is strength, and the normalisation
    // buys flat/mountain invariance); only the reasoning offered for the failed experiment was bad.
    signal=new Float32Array(N);const gain=1/(mean*3.2+1e-6);
    for(let i=0;i<N;i++)signal[i]=Math.tanh((h[i]-smoothH[i])*gain);
    const creepR=Math.round(clamp(p.creep,0,1)*r*.65);if(creepR>0)signal=boxBlurScalar(signal,n,creepR);
    if(owner)owner._weatherSignal={h,n,r,creep:p.creep,signal};
  }
  const out=new Float32Array(N*3),inv=p.inverse==="on"?-1:1,washed=p.washed==="on",dark=p.darker==="on"?1.9:1;
  for(let i=0;i<N;i++){const s=signal[i]*inv,ex=Math.max(s,0),re=Math.max(-s,0),msk=mask?clamp(mask[i],0,1):1,a=clamp(p.amount*msk,0,1),j=i*3;
    let r0=base[j],g0=base[j+1],b0=base[j+2],r1=r0,g1=g0,b1=b0;
    if(washed){const l=.2126*r1+.7152*g1+.0722*b1,pale=.16+l*.84,t=ex*a*.62;r1+= (pale-r1)*t;g1+=(pale-g1)*t;b1+=(pale-b1)*t;}
    else{const hi=1+ex*a*.32;r1*=hi;g1*=hi;b1*=hi;}
    const dirt=clamp(re*p.dirt*dark*msk,0,1);r1+=(.16-r1)*dirt;g1+=(.115-g1)*dirt;b1+=(.075-b1)*dirt;
    const q=gradeWeatherColor(r1,g1,b1,p.hue*msk,p.saturation*msk,p.lightness*msk);out[j]=q[0];out[j+1]=q[1];out[j+2]=q[2];}
  return out;
}
const inEdgeFrom=(id,slot)=>{const e=inputEdge(id,slot);return e?e.from:null;};
function primaryColorAuthor(nodeId){
  const seen=new Set();
  while(nodeId&&!seen.has(nodeId)){seen.add(nodeId);const nd=nodeById(nodeId);if(!nd)return null;
    if(nd.type==="satmap"||nd.type==="satmapblend"||nd.type==="colormixer")return nd;
    nodeId=inEdgeFrom(nodeId,0);}
  return null;
}
// A standalone masked SatMap is a material-layer packet: its RGB is the biome surface and its
// mask is the layer alpha. Effects/height passthroughs above it preserve that alpha. If a SatMap
// already has authored colour on its In chain, its mask was consumed there as an ordinary overlay.
function pendingBiomeMask(nodeId){
  const seen=new Set();
  while(nodeId&&!seen.has(nodeId)){seen.add(nodeId);const nd=nodeById(nodeId);if(!nd)return null;
    if(nd.type==="satmap")return nd._mask&&!primaryColorAuthor(inEdgeFrom(nd.id,0))?nd._mask:null;
    if(nd.type==="satmapblend"||nd.type==="colormixer")return null;
    nodeId=inEdgeFrom(nodeId,0);}
  return null;
}
function colorMixerLayerMask(mixer,slot,sourceId,n){
  const mask=pendingBiomeMask(sourceId);if(!mask)return null;
  const cfg=(mixer.params.layers||[])[slot]||{},radius=Math.min(n>>2,Math.max(0,Math.round((cfg.edgeBlend||0)/cellSizeM())));
  if(!radius)return mask;
  const cache=mixer._biomeMaskCache||(mixer._biomeMaskCache=[]),hit=cache[slot];
  if(hit&&hit.source===mask&&hit.radius===radius&&hit.n===n)return hit.field;
  const field=blurScalarField(mask,n,radius,2);cache[slot]={source:mask,radius,n,field};return field;
}
// Resolve the per-vertex terrain COLOUR by walking the graph: SatMap authors colour, Color Erosion transports it,
// Weathering ages it, SatMap Blend merges branches, and height-only nodes pass it through. Height remains a separate
// field throughout. Returns a colour field, or null if no upstream node has authored colour.
function resolveColor(nodeId,n,memo,guard){
  memo=memo||{};guard=guard||new Set();
  if(!nodeId)return null;
  if(nodeId in memo)return memo[nodeId];
  if(guard.has(nodeId))return null;guard.add(nodeId);
  const nd=nodeById(nodeId);let col=null;
  if(nd){
    if(nd.type==="satmap"){const base=resolveColor(inEdgeFrom(nodeId,0),n,memo,guard),own=satNodeColorField(nd,n);
      col=base?blendFields(base,own,nd,n):own;}
    else if(nd.type==="colorerosion"){const base=resolveColor(inEdgeFrom(nodeId,0),n,memo,guard);
      if(base){const pp={...nd.params,_sediment:nd._sediment,blend:1},raw=colorErodeField(base,nd._height||nd._field,pp,null,n,nd);
        col=blendFields(base,raw,{_mask:nd._mask,params:{opacity:nd.params.blend,blend:nd.params.blendMode||"normal"}},n);}}
    else if(nd.type==="weathering"){const base=resolveColor(inEdgeFrom(nodeId,0),n,memo,guard);
      if(base){const raw=weatherColorField(base,nd._height||nd._field,nd.params,null,n,nd);
        col=blendFields(base,raw,{_mask:nd._mask,params:{opacity:nd.params.opacity==null?1:nd.params.opacity,blend:nd.params.blendMode||"normal"}},n);}}
    else if(nd.type==="colormixer"){
      const cfg=nd.params.layers||[];
      for(let s=0;s<nodeInputs(nd).length;s++){const sourceId=inEdgeFrom(nodeId,s),layer=resolveColor(sourceId,n,memo,guard);if(!layer)continue;
        if(!col)col=layer;else{const q=cfg[s]||{opacity:1,blend:"normal"};
          col=blendFields(col,layer,{_mask:colorMixerLayerMask(nd,s,sourceId,n),
            params:{opacity:q.opacity==null?1:q.opacity,blend:q.blend||"normal"}},n);}}
    }
    else if(nd.type==="satmapblend"){const a=resolveColor(inEdgeFrom(nodeId,0),n,memo,guard),b=resolveColor(inEdgeFrom(nodeId,1),n,memo,guard);
      col=(!a&&!b)?null:!a?b:!b?a:blendFields(a,b,nd,n);}
    else col=resolveColor(inEdgeFrom(nodeId,0),n,memo,guard);       // colour flows through height/filter/erosion nodes
  }
  guard.delete(nodeId);memo[nodeId]=col;return col;
}
// TERRAIN DEFINITION — the world the heightfield represents, in metres. Gaea's defaults: 5 x 5 km
// across and 2.6 km tall, giving a vertical ratio of height/scale = 0.52. This is what makes cell
// size (scale/RES) and therefore slope ANGLES physically meaningful, which nodes with "Real Scale"
// use. (In Gaea, scale only changes processing when Real Scale is on in Erosion/Snow/Thermal.)
const createTerrainDef=(overrides={})=>({scale:5000,height:2600,baseElevation:0,latitude:46,north:0,
  seaTemp:6,lapseRate:6.5,solarElevation:45,windDirection:300,windSpeed:10,lattice:"square",seed:7,
  ...overrides});
export let terrainDef=createTerrainDef();
export const cellSizeM=()=>terrainDef.scale/RES;       // metres per cell (hex: the centre-to-centre spacing s)
// Hexagonal lattice mode (references/26-hexagonal-lattice.md). Storage stays the same W x H
// Float32Array in odd-r offset layout: odd rows are drawn (and sampled) half a cell to the
// right, rows sit sqrt(3)/2 apart. Every check is strictly === "hex" so absent/old documents
// mean square and stay byte-identical. The world footprint is TRUTHFULLY rectangular in hex
// mode - scale x scale*sqrt(3)/2 metres - because squashing rows to keep a square footprint
// would be silent metric anisotropy (the chapter's flagged first bug).
export const isHex=()=>terrainDef.lattice==="hex";
export const HEX_ROW=Math.sqrt(3)/2;
// ---- THE AUTHORING DOMAIN vs THE WORLD METRIC -------------------------------------------
// Two coordinate systems, and conflating them is what made a lattice toggle re-roll the terrain.
//
//   DOMAIN   u,v in [0,1] over the raster: u = (x + 0.5*(y&1))/n, v = y/n. Everything AUTHORED
//            lives here - generators, Position X/Y, shapes, painted strokes, warp displacement -
//            so the same graph draws the same terrain on either lattice. Measured on the default
//            graph: correlation 0.999 against square, versus 0.574 when the generators measured
//            v down the world axis. The odd-row half-cell shift stays: it is a sub-cell offset
//            WITHIN the row, and dropping it prints the zig-zag every noise field used to show.
//
//   WORLD    metres. Rows sit sqrt(3)/2 apart, so a hex map is scale x scale*sqrt(3)/2. Every
//            PHYSICAL kernel - erosion, flow routing, wind, snow, normals, AO, picking, DEM
//            interchange - reads this and must never be "corrected" to the domain.
//
// The cost, stated plainly rather than buried: mapping the unit domain onto a map 0.866 as tall
// squashes the generated PATTERN 13.4% in world y on hex. That is unavoidable - a unit square
// cannot map isotropically onto a non-square world - so the real choice is squash or crop, and
// squash is the better half. A squashed FBM is indistinguishable from a slightly different
// frequency (noise has no canonical aspect ratio), whereas a crop is a different draw, which is
// exactly the "why did my terrain change?" this replaces. The LATTICE itself stays isotropic
// under either choice, so every D6 erosion and flow kernel keeps its correctness untouched.
// warpField is the only node that straddles both; it is commented in place.
// The D6 one-ring, odd-r (26). All six neighbours sit at EXACTLY one cell spacing: the two
// lateral ones trivially, the four oblique ones at (+-0.5, +-sqrt(3)/2), whose length is
// sqrt(0.25+0.75)=1. There is no diagonal and no sqrt(2) to correct - the D4/D8 fork, and the
// whole class of bugs where a diagonal relaxes at a shallower true angle, cannot be written on
// this lattice. Offsets depend on row parity; every hex kernel shares these tables so the
// convention is defined once (thermalErodeHex established it).
const HEX_NB_EVEN=[[-1,0],[1,0],[-1,-1],[0,-1],[-1,1],[0,1]];
const HEX_NB_ODD =[[-1,0],[1,0],[0,-1],[1,-1],[0,1],[1,1]];
export const hexNb=y=>(y&1)?HEX_NB_ODD:HEX_NB_EVEN;
// Unit vectors to those six neighbours, in the SAME order the tables list them, for the
// least-squares gradient: sum(e_k)=0 and sum(e_k e_k^T)=3I, so g = sum(h_k*e_k)/3 is exact for
// a plane and isotropic to leading order. The centre height drops out entirely.
const HEX_EX=[-1,1,-.5,.5,-.5,.5],HEX_EY=[0,0,-HEX_ROW,-HEX_ROW,HEX_ROW,HEX_ROW];
let uTime=0;let H_SCALE=terrainDef.height/terrainDef.scale;
// S4.7 — the live WaterWavePreset. Cached on the six authored controls: expansion is
// deterministic, so a preset only has to be rebuilt when one of them changes, and the shader
// text is baked from it at compile time. terrainDef already owns wind, so the water does not
// re-author it — the node-responsibility audit found four copies of wind direction in the tree
// and this is deliberately not a fifth.
let _wavePreset=null,_wavePresetKey="";
// WHAT EACH WATER PROGRAM ACTUALLY RECEIVED. ADR-006 requires the forward colour pass and the
// deferred mask/depth pass to displace by the SAME function; recording the injected text makes
// that checkable instead of a claim, which is the "shader instrumentation" the story asks for.
export const waterShaderSources={mask:null,forward:null,forwardDetail:null,deferredDetail:null,forwardShoal:null,maskShoal:null};
const SKY_GLSL=`
      vec3 skyCol(vec3 d){d=normalize(d);float h=d.y;
        vec3 zen=vec3(0.10,0.24,0.55),hor=vec3(0.62,0.70,0.80);
        float t=pow(clamp(h,0.,1.),0.42);vec3 c=mix(hor,zen,t);
        c=mix(c,vec3(0.42,0.45,0.50),smoothstep(0.0,-0.12,h));
        float sd=max(dot(d,normalize(uSun)),0.);
        c+=vec3(8.0,6.4,4.2)*pow(sd,1200.);
        c+=vec3(1.2,0.72,0.38)*pow(sd,10.)*0.20;
        c+=vec3(0.8,0.42,0.20)*pow(sd,3.5)*0.10*(1.0-t);
        return c;}
`;
export function waveGlsl(name){return glslGerstner(currentWaterPreset(),name||"gerstnerDisp");}
// The detail layer is generated and recorded exactly like the geometry, and for the same reason:
// it was the one piece of water GLSL still hand-copied into two passes, and it is the piece that
// rotted into two plane sinusoids no artist could author or steer.
export function detailGlsl(name){return glslWaterDetail(currentWaterPreset(),name||"waterDetail");}
export function shoalGlsl(name){return glslShoal(name||"shoalAmp");}
export function currentWaterPreset(){
  const c={windDirectionDeg:terrainDef.windDirection==null?300:terrainDef.windDirection,
    windSpeedMps:terrainDef.windSpeed==null?10:terrainDef.windSpeed,
    seaState:waterLook&&waterLook.seaState!=null?waterLook.seaState:0.55,
    seed:terrainDef.seed==null?1:terrainDef.seed,
    // UNIT AMPLITUDE, deliberately. The twelve terms are baked into the shader as literals, so
    // anything folded into them costs a recompile to change. Expanding at 1 m and carrying the
    // authored height as a uniform makes the Wave height slider a uniform write, and leaves the
    // recompile for sea state and body kind, which genuinely reshape the spectrum.
    maxAmplitudeM:1,
    bodyKind:waterLook&&waterLook.bodyKind?waterLook.bodyKind:"ocean"};
  const key=JSON.stringify(c);
  if(key!==_wavePresetKey){_wavePreset=expandWavePreset(c);_wavePresetKey=key;}
  return _wavePreset;
}   // vertical exaggeration = the real vertical ratio
let TEMP_UNIT="C";try{TEMP_UNIT=localStorage.getItem("terrainStudioTempUnit")==="F"?"F":"C";}catch(_){}
const REDUCED=typeof matchMedia!=="undefined"&&matchMedia("(prefers-reduced-motion: reduce)").matches;
// Water extent and snow accumulation are GRAPH NODES. Water motion/refraction is a global renderer
// concern in `waterLook`; `scene` only collects graph-authored terrain/effect data.
let scene={water:null,snow:null,satmap:null};
const SHADE=["Realistic","Clay","Albedo","Slope","Normals","Temperature","Sun Shadow","Wind"];
function initGL(){
  gl=glc.getContext("webgl2",{antialias:true,alpha:false})||glc.getContext("webgl",{antialias:true,alpha:false});
  // Hand the context to the extracted modules. They cannot import it: `gl` is assigned right here,
  // and importing it would make src/core/* depend on the file they were carved out of. Injected
  // BEFORE the null check below, so a failed getContext propagates null to them too rather than
  // leaving them holding a stale context from a previous init.
  setGpuGL(gl); setGlUtilGL(gl);
  if(!gl){$("#viewport").insertAdjacentHTML("beforeend",'<div style="position:absolute;inset:0;display:grid;place-items:center;color:var(--muted);font-size:12px">WebGL unavailable</div>');return;}
  const g2=(typeof WebGL2RenderingContext!=="undefined")&&(gl instanceof WebGL2RenderingContext);
  // ---------- STAGE 1: opaque terrain (+ snow accumulation) ----------
  const tVs=(g2?`#version 300 es
    in vec3 pos;in vec3 nrm;in float hgt;in float drive;in float snow;in float temperature;in float sunvis;in vec3 col;out vec3 vN;out float vH;out float vD;out float vSnow;out float vTemp;out float vSunVis;out vec3 vW;out vec3 vCol;
    uniform mat4 uMVP;uniform mat4 uM;
    void main(){vN=nrm;vH=hgt;vD=drive;vSnow=snow;vTemp=temperature;vSunVis=sunvis;vCol=col;vW=(uM*vec4(pos,1.)).xyz;gl_Position=uMVP*vec4(pos,1.);}`
  :`attribute vec3 pos;attribute vec3 nrm;attribute float hgt;attribute float drive;attribute float snow;attribute float temperature;attribute float sunvis;attribute vec3 col;varying vec3 vN;varying float vH;varying float vD;varying float vSnow;varying float vTemp;varying float vSunVis;varying vec3 vW;varying vec3 vCol;
    uniform mat4 uMVP;uniform mat4 uM;
    void main(){vN=nrm;vH=hgt;vD=drive;vSnow=snow;vTemp=temperature;vSunVis=sunvis;vCol=col;vW=(uM*vec4(pos,1.)).xyz;gl_Position=uMVP*vec4(pos,1.);}`);
  const tFs=(g2?`#version 300 es
    precision highp float;in vec3 vN;in float vH;in float vD;in float vSnow;in float vTemp;in float vSunVis;in vec3 vW;in vec3 vCol;out vec4 frag;
    #define SAMP texture
    #define OUT frag
    uniform int uShade;uniform int uDeferred;uniform int uSatComposite;uniform vec3 uSun;uniform vec3 uCam;uniform float uExposure;uniform sampler2D uSat;uniform vec2 uRange;uniform float uShift;uniform float uReverse;`
  :`precision highp float;varying vec3 vN;varying float vH;varying float vD;varying float vSnow;varying float vTemp;varying float vSunVis;varying vec3 vW;varying vec3 vCol;
    #define SAMP texture2D
    #define OUT gl_FragColor
    uniform int uShade;uniform int uDeferred;uniform int uSatComposite;uniform vec3 uSun;uniform vec3 uCam;uniform float uExposure;uniform sampler2D uSat;uniform vec2 uRange;uniform float uShift;uniform float uReverse;`)+`
    vec3 srgbToLinear(vec3 c){return mix(c/12.92,pow((c+0.055)/1.055,vec3(2.4)),step(vec3(0.04045),c));}
    vec3 linearToSrgb(vec3 c){c=max(c,vec3(0.0));return mix(c*12.92,1.055*pow(c,vec3(1.0/2.4))-0.055,step(vec3(0.0031308),c));}
    float hash21(vec2 p){p=fract(p*vec2(123.34,345.45));p+=dot(p,p+34.345);return fract(p.x*p.y);}
    float vnoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
      return mix(mix(hash21(i),hash21(i+vec2(1,0)),f.x),mix(hash21(i+vec2(0,1)),hash21(i+vec2(1,1)),f.x),f.y);}
    float surfaceNoise(vec2 p){return vnoise(p)+0.5*vnoise(p*2.03+7.1)+0.25*vnoise(p*4.11+19.7);}
    vec3 temperatureRamp(float c){
      vec3 cold=vec3(.06,.18,.58),freeze=vec3(.74,.91,1.0),mild=vec3(.95,.82,.34),hot=vec3(.75,.10,.05);
      return c<0.0?mix(cold,freeze,smoothstep(-30.0,0.0,c)):mix(mix(freeze,mild,smoothstep(0.0,18.0,c)),hot,smoothstep(18.0,40.0,c));
    }
    vec3 acesF(vec3 x){return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.,1.);}
    void main(){
      vec3 N=normalize(vN);float slope=1.0-N.y;
      // SatMaps and authored swatches arrive as display-sRGB. Decode before lighting so the G-buffer
      // contains scene-linear albedo; otherwise midtones become chalky and energy is not conserved.
      vec3 baseSrgb;
      float dv=(uReverse>0.5)?1.0-vD:vD;                                // SatMap driver -> Reverse, then Range slice + Shift
      float sc=clamp(mix(uRange.x,uRange.y,dv)+uShift,0.001,0.999);
      if(uShade==0||uShade==2)baseSrgb=(uSatComposite==1)?vCol:SAMP(uSat,vec2(sc,0.5)).rgb;
      else if(uShade==1)baseSrgb=vec3(.46,.38,.30);                     // neutral clay: inspect form without colour
      else if(uShade==3)baseSrgb=mix(vec3(.12,.34,.70),vec3(.92,.24,.08),smoothstep(.08,.72,slope));
      else if(uShade==5)baseSrgb=temperatureRamp(vTemp);
      else if(uShade==6)baseSrgb=mix(vec3(.025,.035,.06),vec3(.98,.84,.46),clamp(vSunVis,0.0,1.0));
      else if(uShade==7)baseSrgb=vCol;
      else baseSrgb=vec3(.5);
      vec3 base=srgbToLinear(baseSrgb);
      float materialView=(uShade==0||uShade==2)?1.0:0.0;
      float rockAmt=smoothstep(.30,.76,slope)*.72*materialView;
      vec3 mineral=mix(base,srgbToLinear(vec3(.38,.34,.30)),.42);
      base=mix(base,mineral,rockAmt);                                    // exposed rock, while preserving biome palette
      // Natural breakup without baking a light direction into albedo. Two broad bands prevent the
      // elevation LUT from reading as a sterile contour ramp.
      float macro=surfaceNoise(vW.xz*8.0+vec2(3.7,11.2))/1.75;
      float grain=surfaceNoise(vW.xz*34.0+vec2(17.1,2.8))/1.75;
      base*=mix(1.0,0.88+0.18*macro+0.08*grain,materialView);
      // Snow coverage comes from the simulated WORLD-METRE thickness attribute. Geometry and normals
      // are already displaced by the same SnowField, so the material cannot masquerade as accumulation.
      // Coverage edge modulated by the same surface noise the ground albedo uses (~70 m features
      // at the default extent - sub-cell for the sim, coarse for a boot print). A pure depth
      // threshold follows the depth field's smooth contours and draws the snowline as a clean
      // painted rim; retention actually varies with micro-roughness the depth field cannot
      // resolve, so the 1-15 cm transition band is broken up. Deeper snow is unaffected: the
      // multiplier spans [0.65, 1.45), so full opacity moves at most to ~0.154 m.
      float snowCov=smoothstep(.015,.10,vSnow*(.65+.55*grain+.25*macro))*materialView;
      vec3 snowAlb=srgbToLinear(vec3(.94,.965,.985))*mix(.93,1.04,.65*macro+.35*grain);
      base=mix(base,snowAlb,snowCov);
      // Fresh snow is a rough dielectric with a broad forward-scattering sheen, not polished plastic.
      float matRough=mix(mix(.84,.62,rockAmt),.62,snowCov);
      if(uDeferred==1){OUT=vec4(clamp(base,0.,1.),matRough);return;}
      // ---- FORWARD fallback (WebGL1 / wireframe): light here with sun + hemispheric sky irradiance ----
      if(uShade==2||uShade==3||uShade==5||uShade==6||uShade==7){OUT=vec4(linearToSrgb(base),1.);return;}
      if(uShade==4){OUT=vec4(N*.5+.5,1.);return;}
      vec3 S=normalize(uSun);float d=max(dot(N,S),0.0);
      float hemi=N.y*0.5+0.5;vec3 ambIrr=mix(vec3(.12,.10,.08),vec3(.28,.38,.58),hemi);
      vec3 col=base*(ambIrr+vec3(1.0,.955,.86)*d*1.2);
      vec3 V=normalize(uCam-vW);vec3 Hh=normalize(V+S);
      col+=pow(max(dot(N,Hh),0.0),42.0)*snowCov*.12;
      OUT=vec4(linearToSrgb(acesF(col*exp2(uExposure))),1.);}`;
  terrainProg=makeProg(tVs,tFs);
  // ---------- STAGE 2: translucent water ----------
  // S4.7 — the forward pass displaces by the SAME generated source as the mask pass and carries the
  // analytic wave normal. Injecting one text into both is the only way the mask and the shaded
  // surface can agree along a crest; two hand-written copies drift on the first edit.
  // The WebGL1 fallback below is deliberately left flat: it has no deferred pass to disagree with,
  // and a second unshared implementation there is exactly what this change exists to avoid.
  const wVs=(g2?`#version 300 es
    in vec2 axz;in float ah;in float aw;in float ais;in float aice;in vec3 awn;in vec3 asnowN;out float vDepth;out float vIceSnow;out float vIce;out vec3 vW;out vec2 vXZ;out vec3 vWN;out vec3 vSnowN;out vec3 vWaveN;out float vBreak;out float vCrest;
    uniform mat4 uMVP;uniform float uH;uniform float uScale;uniform float uTime;uniform float uWaveAmp;
${(waterShaderSources.forwardShoal=shoalGlsl()).split(/\r?\n/).map(l => '' + l).join(String.fromCharCode(10))}
${(waterShaderSources.forward=waveGlsl('gerstnerDisp')).split(/\r?\n/).map(l => '    ' + l).join(String.fromCharCode(10))}
    void main(){
      vDepth=(aw-ah)*uH;vIceSnow=ais;vIce=aice;vXZ=axz;vWN=awn;vSnowN=asnowN;
      // Metres per pixel AT THIS VERTEX: distance to the eye times the angular size of one
      // pixel, converted out of grid space. uMppK carries uScale*2*tan(fov/2)/height so the
      // shader does one multiply rather than re-deriving the projection it cannot see.
      float mpp=length(uCam-vec3(axz.x, aw*uH+ais/uScale, axz.y))*uMppK;
      vec3 WN; vec3 d=gerstnerDisp(axz*uScale, uTime, mpp, WN);
      // SHOALING, which this had exactly backwards. The old fade took the waves to ZERO as water got
      // shallower, so the sea went glassy precisely where real water is at its roughest. Waves
      // entering shallow water slow down, shorten, and GROW: Green's law gives amplitude rising as
      // depth^(-1/4). They keep growing until the crest outruns the wave and it breaks, which
      // happens at a height of about 0.78 of the local depth (the McCowan limit).
      //
      // So three factors, not one:
      //   shoal  - amplitude gain from Green's law, referenced to a deep-water depth and capped so
      //            a numerically tiny depth cannot produce an infinite wave
      //   surf   - the breaking limit: a wave can never be taller than 0.78 x the water under it,
      //            which is what makes the swell rear up and then collapse as it reaches the beach
      //   dry    - a hard cutoff over the last centimetres so no wave stands on dry land
      float depthM=max((aw-ah)*uTerrainHeight,0.0);
      float amp=shoalAmp(uWaveAmp,depthM,uShoalRefM);
      float wet=min(depthM*2.0,1.0);
      // SURF. vBreak is how close this wave is to the McCowan limit; vCrest is where in the wave
      // cycle the vertex sits. Foam needs BOTH: breaking alone gives one wide band over the whole
      // shallow zone, and crest alone puts foam on open ocean. Together they give lines of foam
      // that form where the water shoals and travel with the waves, which is what surf is.
      vBreak=shoalAmpBreak(uWaveAmp,depthM,uShoalRefM);
      vCrest=d.y;
      vWaveN=normalize(mix(vec3(0.,1.,0.),WN,wet));
      vW=vec3(axz.x+d.x*amp/uScale, aw*uH+ais/uScale+d.y*amp/uScale, axz.y+d.z*amp/uScale);
      gl_Position=uMVP*vec4(vW,1.);}`
  :`attribute vec2 axz;attribute float ah;attribute float aw;attribute float ais;attribute float aice;attribute vec3 awn;attribute vec3 asnowN;varying float vDepth;varying float vIceSnow;varying float vIce;varying vec3 vW;varying vec2 vXZ;varying vec3 vWN;varying vec3 vSnowN;
    uniform mat4 uMVP;uniform float uH;uniform float uScale;
    void main(){vDepth=(aw-ah)*uH;vIceSnow=ais;vIce=aice;vW=vec3(axz.x,aw*uH+ais/uScale,axz.y);vXZ=axz;vWN=awn;vSnowN=asnowN;gl_Position=uMVP*vec4(vW,1.);}`);
  const wFs=(g2?`#version 300 es
    precision highp float;in float vDepth;in float vIceSnow;in float vIce;in vec3 vW;in vec2 vXZ;in vec3 vWN;in vec3 vSnowN;in vec3 vWaveN;in float vBreak;in float vCrest;out vec4 frag;
    uniform vec3 uSun;uniform vec3 uCam;uniform float uTime;uniform float uH;uniform float uMppK;uniform float uTerrainHeight;uniform float uShoalRefM;
    uniform float uTerrainHeight,uSeaTemp,uLapseRate,uScale;
    uniform float uRipple,uRippleScale,uRippleSpeed,uShoreSmooth,uFoam;uniform int uPattern;uniform float uToon;uniform float uBandSteps;`+SKY_GLSL+``
  :`precision highp float;varying float vDepth;varying float vIceSnow;varying float vIce;varying vec3 vW;varying vec2 vXZ;varying vec3 vWN;varying vec3 vSnowN;
    uniform vec3 uSun;uniform vec3 uCam;uniform float uTime;uniform float uH;uniform float uMppK;uniform float uTerrainHeight;uniform float uShoalRefM;
    uniform float uTerrainHeight,uSeaTemp,uLapseRate,uScale;
    uniform float uRipple,uRippleScale,uRippleSpeed,uShoreSmooth,uFoam;uniform int uPattern;uniform float uToon;uniform float uBandSteps;`)+`
    ${(waterShaderSources.forwardDetail=detailGlsl('waterDetail')).split(/\r?\n/).map(l => '    ' + l).join(String.fromCharCode(10))}
    void main(){
      float shoreAA=.0008+uShoreSmooth*.0018;
      // Dry vertices encode "no water" as exactly zero depth. Centering smoothstep around zero
      // made every dry fragment 50% water and leaked animated normals across the whole terrain.
      float coverage=vDepth>0.0?smoothstep(0.0,shoreAA,vDepth):0.0;
      if(coverage<=.005)discard;
      float ice=clamp(vIce,0.0,1.0);
      float snowCov=smoothstep(.015,.10,vIceSnow)*ice;
      // Detail is a SHADING band only, below ~1.5 m: it never reaches the silhouette and never
      // double-counts energy with the Gerstner terms above it. vXZ is grid space, the function
      // takes metres.
      float t=uTime*uRippleSpeed,waveAmt=uRipple*coverage*(1.0-ice);
      float mppF=length(uCam-vW)*uMppK;
      vec4 wd=waterDetail(vXZ*uScale,t,mppF);
      vec3 wave=vec3(wd.x,wd.y,0.5+0.5*wd.z);
      // THE GERSTNER NORMAL WAS COMPUTED AND THROWN AWAY. Both vertex shaders evaluate the analytic
      // normal and export vWaveN; this shader declared it as an input and never read a single
      // component of it. The surface was DISPLACED by twelve broadband, non-parallel, non-harmonic
      // waves and LIT as a flat plane perturbed by two plane sinusoids -- which is precisely the
      // banding, and no amount of new noise would have fixed it while the real normal stayed unused.
      //
      // Whiteout blend, not a lerp: tangents add and the up-components multiply, which composes two
      // slope fields without flattening either. A lerp toward the wave normal would wash out the
      // underlying water surface tilt that rivers and shorelines depend on.
      float liquid=coverage*(1.0-ice);
      vec3 gerN=normalize(vec3(vWN.x+vWaveN.x*liquid, vWN.y*mix(1.0,vWaveN.y,liquid), vWN.z+vWaveN.z*liquid));
      vec3 baseN=normalize(mix(gerN,vSnowN,snowCov));
      vec3 N=normalize(baseN+waveAmt*vec3(wave.x,0.,wave.y)); // snow uses its raised top normal; waves perturb liquid only
      vec3 V=normalize(uCam-vW);vec3 S=normalize(uSun);
      // Schlick with water's actual F0. n=1.333 gives F0=((1.333-1)/(1.333+1))^2=0.02037, and the
      // exponent is 5, not 3. This pass had neither: no F0 at all and an exponent of 3, while the
      // deferred pass a thousand lines down used the correct form — the same water shaded two
      // different ways depending on which path drew it.
      float fres=0.02+0.98*pow(1.0-max(dot(N,V),0.0),5.0);
      float dn=clamp(max(vDepth,0.)/(uH*0.35),0.0,1.0);      // depth attenuation: shallow teal -> deep blue
      // STYLISED GRADE. One shader path, one set of signals; the look is a transfer function on
      // them, not a second program. Quantise the DEPTH, not the colour: posterising after the mix
      // lands on the RGB lattice, off the gradient line, and spaces the bands unevenly. Quantising
      // first gives exactly uBandSteps colours, all on the gradient. Band centres (+0.5) rather
      // than floors, so the top band is not degenerate.
      //
      // This depth is GEOMETRIC vertical depth, not a screen-space depth difference, which is what
      // makes banding viable here at all: a screen-space difference is the ray's path length
      // through water, so the band boundaries would slide across the surface as the camera moved.
      float dnq=dn;
      if(uToon>0.5){
        // Antialias on the PRE-quantised depth. fwidth of the posterised value is zero inside a
        // band and a full step at the seam, which draws a bright line instead of a soft edge.
        float bw=fwidth(dn)*uBandSteps;
        float sc=dn*uBandSteps;
        dnq=(floor(sc)+smoothstep(0.5-bw,0.5+bw,fract(sc))+0.5)/uBandSteps;
      }
      vec3 wc=mix(vec3(0.28,0.58,0.62),vec3(0.03,0.12,0.30),clamp(dnq,0.0,1.0));
      // ROUGHNESS FROM THE VARIANCE THE NYQUIST FADE REMOVED. Fading sub-pixel octaves out is
      // correct, but doing it without putting their slope variance back into the roughness
      // leaves distant water perfectly smooth with a needle-sharp highlight -- a mirror-flat
      // dielectric, which is exactly the plastic look. Blinn exponent n = 2/m^2 - 2 for slope
      // variance m^2, clamped so the near field stays sharp and the far field cannot blow up.
      float lostVar=waterDetailVar(mppF);
      float m2=clamp(lostVar+1.8e-2/110.0,1.8e-2/110.0,0.16);
      float specPow=clamp(2.0/m2-2.0,8.0,110.0);
      vec3 Hh=normalize(V+S);float spec=pow(max(dot(N,Hh),0.0),specPow)*(specPow/110.0);
      // Cel specular: a threshold with a narrow AA band, lerped in by hardness so the same path
      // serves both looks. The soft lobe is what realistic water wants; the hard one is the toon
      // highlight that reads as a shape rather than a sheen.
      spec=mix(spec,smoothstep(0.005,0.011,spec),uToon);
      float pat=clamp(.5+(wave.z-.5)*waveAmt*1.6,0.,1.);
      // REFLECT THE ACTUAL SKY. This mixed toward a hardcoded vec3, which is plastic by
      // construction: a real water surface takes its colour at grazing angles from whatever is
      // above it, and a constant cannot vary with view direction, wave normal or sun position.
      // The deferred pass has always used skyCol here; the forward pass now shares the same text.
      vec3 refl=skyCol(reflect(-V,N));
      // Sub-surface: light that entered the water, scattered, and came back out. It is what
      // makes a wave glow green when you look INTO the sun through it, and its absence is a
      // large part of why flat water reads as a painted sheet.
      float sss=pow(max(dot(normalize(uSun),-V),0.0),5.0);
      vec3 scatterC=vec3(0.0885,0.497,0.456)*sss*1.7*(1.0-clamp(abs(V.y),0.0,1.0))*(1.0-dn);
      vec3 col=(mix(wc,refl,fres)+scatterC+spec*0.8)*mix(.93,1.07,pat);
      float crest=smoothstep(.68,.92,wave.z)*waveAmt;
      col+=vec3(.035,.065,.085)*crest*(.35+.65*fres);      // restrained bright wavelets make the pattern legible
      // The shoreline band: the wet edge itself, always there.
      float foam=(1.0-smoothstep(0.0,.022+uShoreSmooth*.006,max(vDepth,0.)))*uFoam*coverage;
      // SURF, which is a different thing and the one that dominates a real coastline. Foam forms
      // where the wave is at or past its breaking limit AND near its crest, so it appears as
      // lines that travel shoreward rather than as a halo around the land. Broken up by the
      // detail layer's cellular channel so the lines are ragged, not drawn with a compass.
      float breaking=smoothstep(0.55,0.98,vBreak);
      float crest=smoothstep(0.05,0.55,vCrest);
      float ragged=mix(0.55,1.0,wd.w);
      float surf=breaking*crest*ragged*coverage*(1.0-ice)*uFoam*3.2;
      // Spent foam: past the break the water stays aerated even in the troughs, which is what
      // fills the swash zone between the lines instead of leaving hard gaps.
      surf+=breaking*smoothstep(0.35,1.0,vBreak)*0.35*ragged*coverage*(1.0-ice)*uFoam;
      foam=clamp(foam+surf,0.0,1.0);
      // The shoreline edge is the load-bearing feature of the stylised look -- it is the one
      // thing BotW spends a whole extra screen-space pass on. Hardened here rather than added
      // as a second effect: same foam signal, steeper transfer.
      foam=mix(foam,smoothstep(0.35,0.5,foam),uToon);
      col=mix(col,vec3(0.9,0.95,1.0),foam*(1.0-ice));
      float frost=.5+.5*sin(vXZ.x*91.0+sin(vXZ.y*47.0)*2.0);
      vec3 iceCol=mix(vec3(.38,.55,.68),vec3(.63,.76,.84),.35+.25*frost);
      col=mix(col,iceCol,ice);
      // HUE-PRESERVING POSTERISE. Quantising the depth ramp alone did not read as cartoon and the
      // gate said so: flatness rose only 24%, because Fresnel, specular and the wave normal still
      // vary continuously WITHIN each depth band, so no region is actually flat. Cartoon water is
      // flat regions with hard edges, which means the composed shading has to be quantised too.
      //
      // Quantise the LUMINANCE and rescale, rather than each channel independently: per-channel
      // posterisation drags colours onto the RGB lattice and shifts hue band by band. This keeps
      // the hue and steps only the brightness, which is what cel shading actually is.
      if(uToon>0.5){
        float lum=max(max(col.r,col.g),col.b);
        if(lum>1e-4){
          float sc=clamp(lum,0.0,0.999)*uBandSteps;
          float bw=max(fwidth(lum)*uBandSteps,1e-5);
          float q=(floor(sc)+smoothstep(0.5-bw,0.5+bw,fract(sc))+0.5)/uBandSteps;
          col*=q/lum;
        }
      }
      col=mix(col,vec3(.91,.95,.98),snowCov);
      float alpha=mix(clamp(mix(0.45,0.9,dn)+fres*0.22+foam*0.35,0.0,1.0),.98,max(ice,snowCov))*coverage;`
    +(g2?`frag=vec4(col,alpha);}`:`gl_FragColor=vec4(col,alpha);}`);
  waterProg=makeProg(wVs,wFs);
  if(g2){
    // Rasterise the actual fluid surface into its own depth layer. The compositor can then reconstruct
    // a water-plane world position instead of pretending the visible lakebed pixel is the surface.
    // S4.7 — THE WATER MESH IS DISPLACED, not just shaded. Until now this vertex shader placed the
    // surface at a flat `aw*uH` and every wave was a colour perturbation downstream, which is why
    // the water read as a striped plane and its silhouette against the terrain was a straight line.
    //
    // The Gerstner source is GENERATED FROM THE PRESET and injected here, so the displacement the
    // depth pass rasterises is the same function the CPU oracle checks in double precision. Metres
    // convert to this space by /uScale: `axz` is grid space over `uScale` metres and the vertical is
    // the same normalised axis, so one conversion serves all three components.
    const wmVs=`#version 300 es
      in vec2 axz;in float ah;in float aw;in float ais;out float vDepth;out vec3 vWaveN;out float vBreak;out float vCrest;
      uniform mat4 uMVP;uniform float uH;uniform float uScale;uniform float uTime;uniform float uWaveAmp;uniform vec3 uCam;uniform float uMppK;uniform float uTerrainHeight;uniform float uShoalRefM;
${(waterShaderSources.maskShoal=shoalGlsl()).split(/\r?\n/).map(l => '' + l).join(String.fromCharCode(10))}
${(waterShaderSources.mask=waveGlsl('gerstnerDisp')).split(/\r?\n/).map(l => '      ' + l).join(String.fromCharCode(10))}
      void main(){
        vDepth=(aw-ah)*uH;
        float mpp=length(uCam-vec3(axz.x, aw*uH+ais/uScale, axz.y))*uMppK;
        vec3 N; vec3 d=gerstnerDisp(axz*uScale, uTime, mpp, N);
        // TWO SEPARATE FACTORS, and conflating them was a real bug. wet is a 0..1 shoreline fade
        // so a dry cell is untouched and the shore grows no fringe of waves standing on land.
        // uWaveAmp is the authored height IN METRES and can be 30+. Using one value for both made
        // the normal's mix() extrapolate far past 1 and produced nonsense shading.
        // SHOALING, which this had exactly backwards. The old fade took the waves to ZERO as water got
          // shallower, so the sea went glassy precisely where real water is at its roughest. Waves
          // entering shallow water slow down, shorten, and GROW: Green's law gives amplitude rising as
          // depth^(-1/4). They keep growing until the crest outruns the wave and it breaks, which
          // happens at a height of about 0.78 of the local depth (the McCowan limit).
          //
          // So three factors, not one:
          //   shoal  - amplitude gain from Green's law, referenced to a deep-water depth and capped so
          //            a numerically tiny depth cannot produce an infinite wave
          //   surf   - the breaking limit: a wave can never be taller than 0.78 x the water under it,
          //            which is what makes the swell rear up and then collapse as it reaches the beach
          //   dry    - a hard cutoff over the last centimetres so no wave stands on dry land
        float depthM=max((aw-ah)*uTerrainHeight,0.0);
        float amp=shoalAmp(uWaveAmp,depthM,uShoalRefM);
        float wet=min(depthM*2.0,1.0);
        vBreak=shoalAmpBreak(uWaveAmp,depthM,uShoalRefM);
        vCrest=d.y;
        vWaveN=normalize(mix(vec3(0.,1.,0.),N,wet));
        gl_Position=uMVP*vec4(axz.x+d.x*amp/uScale, aw*uH+ais/uScale+d.y*amp/uScale, axz.y+d.z*amp/uScale, 1.);
      }`;
    const wmFs=`#version 300 es
      precision highp float;in float vDepth;in vec3 vWaveN;in float vBreak;in float vCrest;out vec4 frag;
      // The analytic wave normal is carried through so the deferred pass reads the SAME normal the
      // displacement produced, rather than re-deriving one and disagreeing along every crest.
      void main(){if(vDepth<=0.00001)discard;frag=vec4(1.0,vDepth,vWaveN.y*0.5+0.5,1.0);}`;
    waterMaskProg=makeProg(wmVs,wmFs);
  }
  // ---------- DEFERRED water + analytic sky — the fullscreen-triangle technique (WebGL2) ----------
  // Terrain renders to an offscreen colour+depth G-buffer; then ONE fullscreen triangle reconstructs
  // each pixel's world position from the depth texture and composites sky + screen-space water
  // (refraction from the colour texture, Beer–Lambert absorption from view-ray thickness, Fresnel).
  if(g2){
    const cVs=`#version 300 es
      out vec2 vUv;void main(){vec2 p=vec2((gl_VertexID==1)?3.:-1.,(gl_VertexID==2)?3.:-1.);vUv=p*0.5+0.5;gl_Position=vec4(p,0.,1.);}`;
    const cFs=`#version 300 es
      precision highp float;in vec2 vUv;out vec4 frag;
      uniform sampler2D gColor;uniform highp sampler2D gDepth;uniform sampler2D gW;uniform sampler2D gH;uniform sampler2D gIce;uniform sampler2D gIceSnow;
      uniform sampler2D gWaterMask;uniform highp sampler2D gWaterDepth;
      uniform mat4 uInvMVP;uniform vec3 uCam,uSun;uniform int uStyle;uniform float uMppK;uniform float uScale;
      uniform float uH,uTime,uSeaLevel,uHasSea,uWScale,uWpx,uRES,uExposure,uHaze,uRowScale,uROWS,uHpx,uZScale;
      uniform float uTerrainHeight,uSeaTemp,uLapseRate,uSnowfall,uSnowMeltDays,uSnowMeltRate,uHasSnow;
      uniform float uRipple,uRippleScale,uRippleSpeed,uRefraction,uShoreSmooth,uFoam;uniform int uPattern;uniform vec2 uPx;uniform float uToon;uniform float uBandSteps;
      const float PI=3.14159265;
      const vec3 SUNCOL=vec3(1.0,0.92,0.78);                         // warm daylight, scene-linear
      vec3 linearToSrgb(vec3 c){c=max(c,vec3(0.0));return mix(c*12.92,1.055*pow(c,vec3(1.0/2.4))-0.055,step(vec3(0.0031308),c));}
      // analytic sky: horizon-pale -> zenith-deep gradient + sun disk, aureole and near-sun horizon scatter
      vec3 skyCol(vec3 d){d=normalize(d);float h=d.y;
        vec3 zen=vec3(0.10,0.24,0.55),hor=vec3(0.62,0.70,0.80);
        float t=pow(clamp(h,0.,1.),0.42);vec3 c=mix(hor,zen,t);
        c=mix(c,vec3(0.42,0.45,0.50),smoothstep(0.0,-0.12,h));      // below the horizon
        float sd=max(dot(d,normalize(uSun)),0.);
        c+=vec3(8.0,6.4,4.2)*pow(sd,1200.);                         // HDR sun disk
        c+=vec3(1.2,0.72,0.38)*pow(sd,10.)*0.20;                    // aureole
        c+=vec3(0.8,0.42,0.20)*pow(sd,3.5)*0.10*(1.0-t);           // warm horizon scatter toward the sun
        return c;}
      // World xz -> field uv, and it must be the exact inverse of the VERTEX mapping:
      //   x -> (wx - xHalf)/xHalf ,  z -> (wz - zHalf)/xHalf   with wz = row * rowPitch
      // so v = (pxz.y * xHalf + zHalf) / ((rows-1) * rowPitch) = pxz.y * uZScale + 0.5.
      // The old form divided device z by the row pitch, which inverted the PRE-FLIP short map.
      // After the square-world flip a cross-model review measured the endpoints landing at
      // v = -0.077 .. 1.077 on a 512x591 field - about 13.5% of the map clamped or outside the
      // shadow march, with parity-wrong normals through the middle. uZScale is 0.5 exactly on
      // square, so that path is unchanged.
      vec2 worldUV(vec2 pxz){return vec2(pxz.x*0.5+0.5,pxz.y*uZScale+0.5);}
      // Odd-r parity: row r sits half a cell right when r is odd. Interpolate along each row with
      // ITS OWN shift, then blend rows - the same construction the CPU sampler uses, exact for a
      // linear field. On square uRowScale==1.0 and this is the original bilinear, bit-for-bit.
      float latTap(sampler2D tx,vec2 uv){
        if(uRowScale==1.0){vec2 tt=uv*vec2(uRES,uROWS)-0.5,f=fract(tt),b=(floor(tt)+0.5)/vec2(uRES,uROWS);
          float a=texture(tx,b).r,c=texture(tx,b+vec2(uWpx,0.)).r,d=texture(tx,b+vec2(0.,uHpx)).r,e=texture(tx,b+vec2(uWpx,uHpx)).r;
          return mix(mix(a,c,f.x),mix(d,e,f.x),f.y);}
        // ROWS come from uROWS, COLUMNS from uRES. They are the same number on square and differ
        // by 15.5% on hex; deriving the row index from uRES read a 591-row texture as if it had
        // 512 rows, which is parity-wrong as well as displaced.
        float r=uv.y*uROWS-0.5,r0=floor(r),fr=r-r0;
        float sx=uv.x*uRES-0.5;
        float c0=sx-0.5*mod(r0,2.0),c1=sx-0.5*mod(r0+1.0,2.0);
        float f0=fract(c0),f1=fract(c1);
        vec2 b0=(vec2(floor(c0)+0.5,r0+0.5))/vec2(uRES,uROWS),b1=(vec2(floor(c1)+0.5,r0+1.5))/vec2(uRES,uROWS);
        float t0=mix(texture(tx,b0).r,texture(tx,b0+vec2(uWpx,0.)).r,f0);
        float t1=mix(texture(tx,b1).r,texture(tx,b1+vec2(uWpx,0.)).r,f1);
        return mix(t0,t1,fr);
      }
      float Wat(vec2 uv){return latTap(gW,uv);}
      float Ht(vec2 uv){return latTap(gH,uv);}
      float fieldLinear(sampler2D tx,vec2 uv){return latTap(tx,uv);}
      // per-pixel terrain normal from central differences of the height field (higher-res than the mesh vertex normals)
      vec3 terrainNormal(vec2 uv){float e=uWpx;
        float hl=Ht(uv-vec2(e,0.))*uH,hr=Ht(uv+vec2(e,0.))*uH,hd=Ht(uv-vec2(0.,e))*uH,hu=Ht(uv+vec2(0.,e))*uH;
        float s=uRES*0.25;                                          // world span across the central difference is 4/uRES
        return normalize(vec3(-(hr-hl)*s,1.0,-(hu-hd)*s));}
      // soft CAST shadow: march the height field toward the sun; occluded if terrain rises above the ray
      float shadowT(vec3 P,vec3 S){
        if(S.y<=0.03)return 1.0;
        float hstep=length(S.xz)/max(S.y,1e-3);                    // horizontal advance per unit rise
        vec2 dir=normalize(S.xz+vec2(1e-5));vec2 duv=dir*(2.6/uRES);
        float dry=length(duv)/max(hstep,1e-3);                     // ray height gain per step (world)
        vec2 uv=worldUV(P.xz)+duv; float ry=P.y+dry; float occ=0.0;
        for(int i=0;i<24;i++){ if(uv.x<0.||uv.x>1.||uv.y<0.||uv.y>1.)break;
          occ=max(occ,clamp((Ht(uv)*uH-ry)/(0.03*uH),0.,1.)); uv+=duv; ry+=dry; }
        return 1.0-occ*0.92;
      }
      // horizon ambient occlusion: how much the neighbourhood rises around this point
      float aoAt(vec2 uv,float hc){float o=0.0;const int D=6;
        for(int k=0;k<D;k++){float a=6.2831*float(k)/float(D);vec2 dr=vec2(cos(a),sin(a))/uRES;float m=0.0;
          for(int r=1;r<=3;r++){float rr=float(r)*2.5;m=max(m,(Ht(uv+dr*rr)*uH-hc)/(rr/uRES));}o+=clamp(m,0.,1.);}
        return 1.0-o/float(D)*0.7;
      }
      float aoT(vec2 uv){return aoAt(uv,Ht(uv)*uH);}
      vec3 aces(vec3 x){return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.,1.);}
      vec3 displayMap(vec3 hdr){return linearToSrgb(aces(hdr*exp2(uExposure)));}
      // aerial perspective: fade to a sky-tinted haze with distance, warming toward the sun (in-scatter)
      vec3 atmos(vec3 c,vec3 P){float dist=length(P-uCam);float f=1.0-exp(-max(dist-1.15,0.0)*(0.05+uHaze*.34));
        vec3 vd=normalize(P-uCam);
        vec3 haze=mix(vec3(0.48,0.58,0.72),vec3(0.88,0.72,0.52),pow(max(dot(vd,normalize(uSun)),0.),4.)*0.5);
        return mix(c,haze,f*uHaze*.72);}
      float hash21(vec2 p){p=fract(p*vec2(123.34,345.45));p+=dot(p,p+34.345);return fract(p.x*p.y);}
      float vnoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
        return mix(mix(hash21(i),hash21(i+vec2(1,0)),f.x),mix(hash21(i+vec2(0,1)),hash21(i+vec2(1,1)),f.x),f.y);}
      float detailNoise(vec2 p){return vnoise(p)+.5*vnoise(p*2.07+9.2);}
      ${(waterShaderSources.deferredDetail=detailGlsl('waterDetail')).split(/\r?\n/).map(l => '      ' + l).join(String.fromCharCode(10))}
      float signedWaterDepth(vec2 uv){
        float ws=Wat(uv)*uH;if(uHasSea>0.5)ws=max(ws,uSeaLevel*uH);
        return ws-Ht(uv)*uH;
      }
      float filteredShoreDepth(vec2 uv){
        float c=signedWaterDepth(uv),r=uWpx*uShoreSmooth;
        if(uShoreSmooth<=.001)return c;
        float axis=signedWaterDepth(uv+vec2(r,0.))+signedWaterDepth(uv-vec2(r,0.))
          +signedWaterDepth(uv+vec2(0.,r))+signedWaterDepth(uv-vec2(0.,r));
        float diag=signedWaterDepth(uv+vec2(r,r))+signedWaterDepth(uv+vec2(r,-r))
          +signedWaterDepth(uv+vec2(-r,r))+signedWaterDepth(uv-vec2(r,r));
        return (c*4.0+axis*2.0+diag)/16.0;
      }
      vec3 addMaterialNormal(vec3 N,vec3 P){
        float fade=1.0-smoothstep(2.6,4.5,length(P-uCam)),e=.0015;
        float n=detailNoise(P.xz*48.0),nx=detailNoise((P.xz+vec2(e,0))*48.0),nz=detailNoise((P.xz+vec2(0,e))*48.0);
        return normalize(N+vec3(-(nx-n)*.42*fade,0.,-(nz-n)*.42*fade));}
      // Cook-Torrance GGX in scene-linear radiance. The same roughness controls the sun lobe and the
      // low-cost sky reflection, while derivative variance raises roughness to suppress sparkling.
      vec3 shadeSurface(vec3 albedo,vec3 N,vec3 Pw,float rough,float sh,float ao){
        vec3 S=normalize(uSun),Vd=normalize(uCam-Pw);
        if(uStyle==0)N=addMaterialNormal(N,Pw);
        float NdL=max(dot(N,S),0.0),NdV=max(dot(N,Vd),1e-4);
        vec3 Hh=normalize(S+Vd);float NdH=max(dot(N,Hh),0.),VdH=max(dot(Vd,Hh),0.);
        float variance=max(dot(dFdx(N),dFdx(N)),dot(dFdy(N),dFdy(N)));
        rough=clamp(sqrt(rough*rough+variance*.28),.08,1.0);
        float a=rough*rough,a2=a*a;
        float den=NdH*NdH*(a2-1.)+1.;
        float D=a2/(PI*den*den+1e-5);
        float gv=NdL*sqrt(max(NdV*(NdV-NdV*a2)+a2,1e-5));
        float gl=NdV*sqrt(max(NdL*(NdL-NdL*a2)+a2,1e-5));
        float Vis=.5/max(gv+gl,1e-5);
        vec3 F0=vec3(.04),F=F0+(1.0-F0)*pow(1.0-VdH,5.0);
        vec3 spec=D*Vis*F;
        vec3 direct=((1.0-F)*albedo/PI+spec)*SUNCOL*3.15*NdL*sh;
        float hemi=N.y*0.5+0.5;
        vec3 ambIrr=mix(vec3(.15,.115,.085),vec3(.34,.46,.66),hemi);
        vec3 ambient=albedo*ambIrr*ao;
        vec3 Fenv=F0+(1.0-F0)*pow(1.0-NdV,5.0);
        vec3 envSpec=skyCol(reflect(-Vd,N))*Fenv*(.12+.24*(1.0-rough))*ao;
        return direct+ambient+envSpec;
      }
      void main(){
        float z=texture(gDepth,vUv).r;
        vec4 clip=vec4(vUv*2.-1.,z*2.-1.,1.);vec4 wp=uInvMVP*clip;vec3 Pw=wp.xyz/wp.w;
        vec3 viewDir=normalize(Pw-uCam),S=normalize(uSun);
        float waterMask=texture(gWaterMask,vUv).r;
        if(z>=0.99999&&waterMask<.5){frag=vec4(displayMap(skyCol(viewDir)),1.);return;} // background: analytic sky (skydome technique)
        vec4 g=texture(gColor,vUv);vec3 albedo=g.rgb;float rough=g.a;
        vec2 bedUv=worldUV(Pw.xz);
        vec3 Nt=terrainNormal(bedUv);
        if(uStyle==2||uStyle==3||uStyle==5||uStyle==6){frag=vec4(linearToSrgb(albedo),1.);return;}
        if(uStyle==4){frag=vec4(Nt*.5+.5,1.);return;}
        float sh=shadowT(Pw,S),ao=aoT(bedUv);                       // cast shadow + ambient occlusion from the height field
        vec3 dryCol=shadeSurface(albedo,Nt,Pw,rough,sh,ao);
        if(waterMask<.5){frag=vec4(displayMap(atmos(dryCol,Pw)),1.);return;}
        float wz=texture(gWaterDepth,vUv).r;
        vec4 wclip=vec4(vUv*2.-1.,wz*2.-1.,1.);vec4 wwp=uInvMVP*wclip;vec3 Pwater=wwp.xyz/wwp.w;
        vec2 wuv=worldUV(Pwater.xz);
        float wSurf=Pwater.y;
        float rawDepth=signedWaterDepth(wuv),thick=max(rawDepth,0.0);
        float shoreDepth=filteredShoreDepth(wuv);
        float shoreAA=max(fwidth(shoreDepth)*1.5,.00035);
        // Filtering may soften an existing shoreline but must never create fluid where the raw
        // depth says dry. Zero depth is absence, not the midpoint of an antialias transition.
        float waterCov=rawDepth>0.0?smoothstep(0.0,shoreAA,max(shoreDepth,0.0)):0.0;
        if(waterCov<=.001){frag=vec4(displayMap(atmos(dryCol,Pw)),1.);return;}
        // ---- WATER (screen-space): lit lakebed refraction + Beer–Lambert + Fresnel sky reflection ----
        float wl=Wat(wuv-vec2(uWpx,0.)),wr=Wat(wuv+vec2(uWpx,0.)),wdn=Wat(wuv-vec2(0.,uWpx)),wup=Wat(wuv+vec2(0.,uWpx));
        vec3 N=normalize(vec3((wl-wr)*uWScale,1.0,(wdn-wup)*uWScale)); // water-surface normal (flat lakes, sloped rivers)
        float ice=clamp(fieldLinear(gIce,wuv),0.0,1.0);
        float iceSnowDepth=fieldLinear(gIceSnow,wuv);
        float iceSnowCov=smoothstep(.015,.10,iceSnowDepth);
        float sl=wl*uH+fieldLinear(gIceSnow,wuv-vec2(uWpx,0.))*uH/uTerrainHeight;
        float sr=wr*uH+fieldLinear(gIceSnow,wuv+vec2(uWpx,0.))*uH/uTerrainHeight;
        float sd=wdn*uH+fieldLinear(gIceSnow,wuv-vec2(0.,uWpx))*uH/uTerrainHeight;
        float su=wup*uH+fieldLinear(gIceSnow,wuv+vec2(0.,uWpx))*uH/uTerrainHeight;
        vec3 snowN=normalize(vec3((sl-sr)*uRES*.25,1.0,(sd-su)*uRES*.25));
        N=normalize(mix(N,snowN,iceSnowCov));
        float t=uTime*uRippleSpeed;float waveAmt=uRipple*waterCov*(1.0-ice);
        float mppF=length(uCam-Pwater)*uMppK;
        vec4 wd=waterDetail(Pwater.xz*uScale,t,mppF);
        vec3 wave=vec3(wd.x,wd.y,0.5+0.5*wd.z);
        N=normalize(N+waveAmt*vec3(wave.x,0.,wave.y));
        vec3 Vd=normalize(uCam-Pwater);
        float surfaceSh=shadowT(Pwater,S),surfaceAo=aoAt(wuv,Pwater.y);
        float refrDepth=clamp(thick*8.,0.,1.);
        vec2 refrOff=N.xz*uPx*34.*refrDepth*uRefraction*(1.0-ice);
        vec2 refrUv=clamp(vUv+refrOff,vec2(0.002),vec2(0.998));
        // Three nearby taps add restrained wavelength separation and make the displaced lakebed read
        // as refraction rather than an animated colour overlay.
        vec3 bedAlb=vec3(texture(gColor,clamp(refrUv+refrOff*.025,vec2(.002),vec2(.998))).r,
                         texture(gColor,refrUv).g,
                         texture(gColor,clamp(refrUv-refrOff*.02,vec2(.002),vec2(.998))).b);
        vec3 bed=shadeSurface(bedAlb,Nt,Pw,0.82,sh,ao);            // light the rough lakebed (albedo was unlit in the g-buffer)
        // Beer-Lambert. Pure water's real absorption (Pope & Fry 1997) is 0.340 / 0.0565 / 0.0092
        // per metre -- a red:blue ratio of 37:1. The old sigma was 13 : 5.5 : 2.25, only 5.8:1, far
        // less spectrally selective than water actually is, which is why deep water read grey-blue
        // instead of blue. Scaled to keep the same overall extinction depth, with the real ratio.
        vec3 sigma=vec3(3.40,0.565,0.092);
        vec3 trans=exp(-sigma*thick*5.0);
        // The stylised grade quantises the DEPTH SIGNAL, not the composed colour, for the same
        // reason as the forward pass: posterising the colour lands off the gradient. Here the depth
        // signal is the transmittance itself, and thickness is a geometric column, not a
        // screen-space depth difference, so the bands hold still as the camera moves.
        if(uToon>0.5){
          // BAND A NORMALISED QUANTITY. Quantising the raw thickness put almost every fragment in
          // one band: thick is a world-space column, typically far below 1, so clamping it to
          // 0..1 and cutting that into five left the whole surface in the first slice. Mapping
          // through 1-exp(-k*thick) first spreads the visible range over the full 0..1 interval,
          // and inverting it afterwards keeps Beer-Lambert exact rather than approximating it.
          float tn=1.0-exp(-thick*6.0);
          float bw=max(fwidth(tn),1e-5)*uBandSteps;
          float sc=clamp(tn,0.0,0.999)*uBandSteps;
          float tnq=(floor(sc)+smoothstep(0.5-bw,0.5+bw,fract(sc))+0.5)/uBandSteps;
          float thickq=-log(max(1.0-clamp(tnq,0.0,0.999),1e-4))/6.0;
          trans=exp(-sigma*thickq*5.0);
        }
        vec3 scatter=vec3(.018,.080,.140)*(1.0-trans);
        float pat=clamp(.5+(wave.z-.5)*waveAmt*1.6,0.,1.);
        vec3 wc=(bed*trans+scatter)*mix(.93,1.07,pat);              // subtle visible pattern follows the normal motion
        float crest=smoothstep(.68,.92,wave.z)*waveAmt;
        wc+=vec3(.025,.050,.075)*crest;                             // small-scale reflected wave crests
        float fres=.02+.98*pow(1.0-max(dot(N,Vd),0.0),5.0);         // dielectric water F0 ≈ 0.02
        vec3 refl=skyCol(reflect(-Vd,N));                           // Fresnel sky reflection
        float lostVarD=waterDetailVar(mppF);
        float m2D=clamp(lostVarD+2.0/240.0*0.5,2.0/240.0*0.5,0.16);
        float specPowD=clamp(2.0/m2D-2.0,10.0,240.0);
        vec3 Hh=normalize(Vd+S);float spec=pow(max(dot(N,Hh),0.),specPowD)*(specPowD/240.0)*0.95*surfaceSh;
        spec=mix(spec,smoothstep(0.005,0.011,spec)*surfaceSh,uToon);
        float edgeW=max(shoreAA*5.0,.0015);
        float foam=(1.0-smoothstep(shoreAA,edgeW,max(shoreDepth,0.0)))*uFoam*waterCov*(1.0-ice);
        foam=mix(foam,smoothstep(0.35,0.5,foam),uToon);
        vec3 col=mix(wc,refl,fres)+spec*SUNCOL; col=mix(col,vec3(.78,.86,.92),foam);
        // HUE-PRESERVING POSTERISE. Quantising the depth ramp alone did not read as cartoon and the
          // gate said so: flatness rose only 24%, because Fresnel, specular and the wave normal still
          // vary continuously WITHIN each depth band, so no region is actually flat. Cartoon water is
          // flat regions with hard edges, which means the composed shading has to be quantised too.
          //
          // Quantise the LUMINANCE and rescale, rather than each channel independently: per-channel
          // posterisation drags colours onto the RGB lattice and shifts hue band by band. This keeps
          // the hue and steps only the brightness, which is what cel shading actually is.
          if(uToon>0.5){
          float lum=max(max(col.r,col.g),col.b);
          if(lum>1e-4){
            float sc=clamp(lum,0.0,0.999)*uBandSteps;
            float bw=max(fwidth(lum)*uBandSteps,1e-5);
            float q=(floor(sc)+smoothstep(0.5-bw,0.5+bw,fract(sc))+0.5)/uBandSteps;
            col*=q/lum;
          }
        }
        col*=mix(0.65,1.0,surfaceSh);                               // use the fluid/ice surface, not the submerged bed, for shadowing
        float frost=vnoise(wuv*83.0)+.5*vnoise(wuv*211.0+19.0);
        float cracks=1.0-smoothstep(.015,.055,abs(fract((wuv.x+wuv.y*.37)*37.0+frost*.18)-.5));
        vec3 iceAlb=mix(vec3(.34,.51,.64),vec3(.58,.70,.77),clamp(frost*.55,0.,1.));
        vec3 iceCol=shadeSurface(iceAlb,N,Pwater,.56,surfaceSh,surfaceAo)*(1.0-cracks*.18);
        col=mix(col,iceCol,ice);
        vec3 iceSnowAlb=vec3(.88,.93,.97)*mix(.94,1.04,clamp(frost*.55,0.,1.));
        vec3 iceSnowCol=shadeSurface(iceSnowAlb,N,Pwater,.66,surfaceSh,surfaceAo);
        col=mix(col,iceSnowCol,iceSnowCov);
        col=mix(dryCol,col,waterCov);                                // analytic coverage removes the binary triangle shoreline
        frag=vec4(displayMap(atmos(col,Pwater)),1.);
      }`;
    compProg=makeProg(cVs,cFs);
    const mkFloatTex=()=>{const tx=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,tx);
      gl.texImage2D(gl.TEXTURE_2D,0,gl.R32F,RES,RES,0,gl.RED,gl.FLOAT,new Float32Array(RES*RES));  // shape-ok: placeholder allocation only - every upload re-specifies the dimensions, and the compositor texture shape is owned by the deferred-rendering item
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);return tx;};
    wTex=mkFloatTex();hTex=mkFloatTex();iTex=mkFloatTex();isTex=mkFloatTex(); // water surface, terrain, ice phase, snow-on-ice
    USE_DEFERRED=true;
  }
  buildSatLUT(satName);
  buffers={pos:gl.createBuffer(),nrm:gl.createBuffer(),hgt:gl.createBuffer(),drive:gl.createBuffer(),snow:gl.createBuffer(),
           temperature:gl.createBuffer(),sunvis:gl.createBuffer(),col:gl.createBuffer(),gridXZ:gl.createBuffer(),
           wsurf:gl.createBuffer(),wnrm:gl.createBuffer(),ice:gl.createBuffer(),iceSnow:gl.createBuffer(),
           iceSnowNrm:gl.createBuffer(),idx:gl.createBuffer(),count:0};
  buildIndex();
  gl.enable(gl.DEPTH_TEST);
  glc.addEventListener("contextmenu",e=>e.preventDefault());
  glc.addEventListener("mousedown",e=>{glDrag={x:e.clientX,y:e.clientY,mode:(e.button===2||e.shiftKey)?"pan":"orbit"};});
  window.addEventListener("mousemove",e=>{
    if(!glDrag)return;
    const dx=e.clientX-glDrag.x,dy=e.clientY-glDrag.y;
    if(glDrag.mode==="pan"){
      const b=cameraBasis(),worldPerPx=2*Math.tan(1.05/2)*cam.dist/Math.max(glc.clientHeight,1);
      for(let k=0;k<3;k++)cam.target[k]+=(-b.right[k]*dx+b.up[k]*dy)*worldPerPx;
      cam.target[0]=clamp(cam.target[0],-1.25,1.25);cam.target[1]=clamp(cam.target[1],-.25,.9);cam.target[2]=clamp(cam.target[2],-1.25,1.25);
    }else{
      cam.az-=dx*.01;cam.el=clamp(cam.el-dy*.01,.035,1.535);
    }
    glDrag.x=e.clientX;glDrag.y=e.clientY;
  });
  window.addEventListener("mouseup",()=>glDrag=null);
  glc.addEventListener("wheel",e=>{
    e.preventDefault();
    const r=glc.getBoundingClientRect(),ndcX=((e.clientX-r.left)/Math.max(r.width,1))*2-1,ndcY=1-((e.clientY-r.top)/Math.max(r.height,1))*2;
    const b=cameraBasis(),halfH=Math.tan(1.05/2)*cam.dist,asp=r.width/Math.max(r.height,1);
    const focus=[b.right[0]*ndcX*halfH*asp+b.up[0]*ndcY*halfH,
                 b.right[1]*ndcX*halfH*asp+b.up[1]*ndcY*halfH,
                 b.right[2]*ndcX*halfH*asp+b.up[2]*ndcY*halfH];
    const ratio=clamp(Math.exp(e.deltaY*.00135),.72,1.38),next=clamp(cam.dist*ratio,.012,8),move=(1-next/cam.dist)*.92;
    for(let k=0;k<3;k++)cam.target[k]+=focus[k]*move;
    cam.target[0]=clamp(cam.target[0],-1.1,1.1);cam.target[2]=clamp(cam.target[2],-1.1,1.1);
    if(curHgt&&Math.abs(cam.target[0])<=1&&Math.abs(cam.target[2])<=1)cam.target[1]=surfaceHeight(cam.target[0],cam.target[2]);
    cam.dist=next;
  },{passive:false});
  requestAnimationFrame(renderGL);
}
let glDrag=null;
function terrainQuadFitDelta(h00,h10,h01,h11,g00x,g00y,g10x,g10y,g01x,g01y,g11x,g11y){
  // Fit both candidate pairs of triangle planes to the heightfield gradients estimated from
  // the surrounding 3x3 samples. Unlike "shortest diagonal", this sees whether a diagonal
  // follows a ridge/valley crease instead of merely connecting two similar elevations.
  const topX=h10-h00,bottomX=h11-h01,leftY=h01-h00,rightY=h11-h10;
  const err=(gx,gy,rx,ry)=>{const dx=gx-rx,dy=gy-ry;return dx*dx+dy*dy;};
  const main=err(topX,rightY,g00x,g00y)+err(topX,rightY,g10x,g10y)+err(topX,rightY,g11x,g11y)
    +err(bottomX,leftY,g00x,g00y)+err(bottomX,leftY,g11x,g11y)+err(bottomX,leftY,g01x,g01y);
  const anti=err(topX,leftY,g00x,g00y)+err(topX,leftY,g10x,g10y)+err(topX,leftY,g01x,g01y)
    +err(bottomX,rightY,g10x,g10y)+err(bottomX,rightY,g11x,g11y)+err(bottomX,rightY,g01x,g01y);
  return(main-anti)/(1+main+anti);                           // normalized: stable threshold across relief scales
}
/* ---- WIREFRAME EDGE BUFFER ------------------------------------------------------------------
   The overlay used to draw by reinterpreting the TRIANGLE index buffer as a LINE_STRIP, which
   connects every consecutive pair in buffer order: the 3 real edges of each triangle PLUS a
   spurious stitch from each triangle's last vertex to the next triangle's first. Those stitches
   are not mesh edges, and they are why the hex topology was unreadable on screen (the user could
   not tell hex mode was working). A triangle LIST cannot be drawn as lines without its own
   deduplicated EDGE buffer, so build one.

   Edge ownership, to emit each edge exactly once: quad (x,y) owns its TOP edge (i -> i+1), its
   LEFT edge (i -> i+n) and its diagonal; the final row's bottom edges and the final column's
   right edges are emitted separately. Total = 3*(n-1)^2 + 2*(n-1) edges, which is exactly the
   unique-edge count of the triangulation (horizontals n(n-1) + verticals n(n-1) + one diagonal
   per quad). Lazily built: at 4096 square the buffer is ~400 MB, so it is only allocated when the
   wireframe is actually switched on, and invalidated whenever the topology changes.            */
let wireDiagArr=null,wireDiagN=0;
function wireQuadDiag(n){const nh=latticeRows(n);
  if(wireDiagN!==n||!wireDiagArr){wireDiagArr=new Uint8Array((n-1)*(nh-1));wireDiagN=n;}
  return wireDiagArr;
}
function wireEdgeCount(n){const nh=latticeRows(n);return 3*(n-1)*(nh-1)+(n-1)+(nh-1);}
function buildWireIndex(){
  const n=fieldW(),nh=fieldH(),u32=buffers.u32,cnt=wireEdgeCount(n)*2;
  const idx=u32?new Uint32Array(cnt):new Uint16Array(cnt);let w=0;
  // Hex diagonals are a pure function of row parity (the unique equilateral triangulation);
  // square diagonals come from the fit recorded by streamTerrainIndices, falling back to the
  // deterministic checkerboard if the stream has not run yet.
  const hex=isHex(),diag=(wireDiagN===n&&!hex)?wireDiagArr:null;
  for(let y=0;y<nh-1;y++)for(let x=0;x<n-1;x++){
    const i=y*n+x;
    idx[w++]=i;idx[w++]=i+1;                                   // top edge of this quad
    idx[w++]=i;idx[w++]=i+n;                                   // left edge of this quad
    const useMain=hex?!!(y&1):(diag?!!diag[y*(n-1)+x]:!!((x+y)&1));
    if(useMain){idx[w++]=i;idx[w++]=i+n+1;}else{idx[w++]=i+1;idx[w++]=i+n;}
  }
  for(let x=0;x<n-1;x++){const i=(nh-1)*n+x;idx[w++]=i;idx[w++]=i+1;}   // bottom row
  for(let y=0;y<nh-1;y++){const i=y*n+n-1;idx[w++]=i;idx[w++]=i+n;}     // right column
  if(!buffers.lineIdx)buffers.lineIdx=gl.createBuffer();
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,buffers.lineIdx);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,idx,gl.STATIC_DRAW);
  buffers.lineCount=cnt;buffers.lineReady=true;buffers.lineLattice=terrainDef.lattice||"square";
}
function streamTerrainIndices(height,snowDepth){
  const n=fieldW(),nh=fieldH(),adaptive=!!(height&&height.length===n*nh),u32=buffers.u32,bytes=u32?4:2;
  const quadDiag=wireQuadDiag(n);
  // A full 4096² Uint32 index staging array is ~384 MiB. Stream row batches instead:
  // topology stays indexed on the GPU while CPU scratch memory remains below ~3 MiB.
  const batchRows=Math.max(1,Math.min(32,Math.floor(786432/Math.max(6*(n-1),1))));
  const batch=u32?new Uint32Array((n-1)*batchRows*6):new Uint16Array((n-1)*batchRows*6);
  const snowScale=snowDepth&&snowDepth.length===n*nh?1/Math.max(terrainDef.height,1e-6):0;
  const started=performance.now();let elementOffset=0,mainCount=0,antiCount=0,tieCount=0,flips=0;
  let fitGain=0,fitStrength=0;
  let grad0=adaptive?new Float32Array(n*2):null,grad1=adaptive?new Float32Array(n*2):null;
  const sample=i=>height[i]+(snowScale?snowDepth[i]*snowScale:0);
  const fillGradientRow=(y,out)=>{
    const ym=Math.max(0,y-1),yp=Math.min(nh-1,y+1);
    for(let x=0;x<n;x++){const xm=Math.max(0,x-1),xp=Math.min(n-1,x+1),j=x*2;
      out[j]=(sample(y*n+xp)-sample(y*n+xm))*.5;
      out[j+1]=(sample(yp*n+x)-sample(ym*n+x))*.5;}
  };
  if(adaptive){fillGradientRow(0,grad0);fillGradientRow(Math.min(1,n-1),grad1);}
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,buffers.idx);
  let w=0;
  for(let y=0;y<nh-1;y++){
    for(let x=0;x<n-1;x++){
      const i=y*n+x,checkerMain=!!((x+y)&1);let useMain=checkerMain;
      if(adaptive){
        const h00=sample(i),h10=sample(i+1),h01=sample(i+n),h11=sample(i+n+1),j=x*2;
        const fitDelta=terrainQuadFitDelta(h00,h10,h01,h11,
          grad0[j],grad0[j+1],grad0[j+2],grad0[j+3],
          grad1[j],grad1[j+1],grad1[j+2],grad1[j+3]);
        // Decisive-only adaptivity. On drape-smoothed snow the fit signal collapses (measured
        // median |fitDelta| 6.8e-6 against the old 1e-6 tie band), so noise picked the diagonal
        // and the wins clustered into ~100-quad same-diagonal patches - the diamond-plate
        // shading artifact on every smooth face (user screenshot; flipShare 37%). At 1e-4 the
        // flips fall to 2.4% of quads, largest patch 31 and elongated along real creases (the
        // p99 crease signal is 2e-3, 20x above the band): ridges keep their fitted diagonals,
        // smooth ground holds the deterministic checkerboard.
        if(Math.abs(fitDelta)<=1e-4){tieCount++;useMain=checkerMain;}
        else useMain=fitDelta<0;
        fitStrength+=Math.abs(fitDelta);
        fitGain+=checkerMain?Math.max(0,fitDelta):Math.max(0,-fitDelta);
        if(useMain!==checkerMain)flips++;
      }
      if(useMain){
        batch[w++]=i;batch[w++]=i+1;batch[w++]=i+n+1;
        batch[w++]=i;batch[w++]=i+n+1;batch[w++]=i+n;mainCount++;
      }else{
        batch[w++]=i;batch[w++]=i+1;batch[w++]=i+n;
        batch[w++]=i+1;batch[w++]=i+n+1;batch[w++]=i+n;antiCount++;
      }
      // Record the diagonal so the wireframe edge buffer can be rebuilt without re-deriving the
      // fit (buildWireIndex). One byte per quad, reused across rebuilds - negligible beside the
      // triangle buffer it accompanies.
      if(quadDiag)quadDiag[y*(n-1)+x]=useMain?1:0;
    }
    if(w===batch.length||y===nh-2){
      gl.bufferSubData(gl.ELEMENT_ARRAY_BUFFER,elementOffset*bytes,batch.subarray(0,w));elementOffset+=w;w=0;
    }
    if(adaptive&&y<nh-2){const old=grad0;grad0=grad1;grad1=old;fillGradientRow(y+2,grad1);}
  }
  const revision=(buffers.edgeSpin&&buffers.edgeSpin.revision||0)+1;
  buffers.lineReady=false;                       // diagonals just moved: edge buffer is stale
  buffers.indexPattern=adaptive?"adaptive-normal-fit-diagonal":"checkerboard";
  buffers.edgeSpin={adaptive,quadCount:(n-1)*(nh-1),mainCount,antiCount,tieCount,flipsFromCheckerboard:flips,
    fitGain,fitStrength,batchRows,stagingBytes:batch.byteLength+(adaptive?(grad0.byteLength+grad1.byteLength):0),
    durationMs:performance.now()-started,revision};
}
function buildIndex(){const n=fieldW(),nh=fieldH(),cnt=(n-1)*(nh-1)*6,u32=(n*nh>65000);
  buffers.count=cnt;buffers.u32=u32;buffers.lineReady=false;   // resolution/lattice changed
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,buffers.idx);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,cnt*(u32?4:2),gl.DYNAMIC_DRAW);
  if(isHex()){
    // The hex lattice has a UNIQUE equilateral triangulation (26): between an even row and the
    // shifted odd row below, the short diagonal is forced, and it alternates by ROW parity -
    // which is exactly a per-row alternation of the two quad patterns streamTerrainIndices
    // already emits. There is nothing to choose per quad, so edge spinning ceases to exist and
    // the index buffer is a pure, height-independent function of (n) - static upload once,
    // hash-assertable by _verify_hex.js, never streamed again.
    const idx=u32?new Uint32Array(cnt):new Uint16Array(cnt);let w=0;
    for(let y=0;y<nh-1;y++)for(let x=0;x<n-1;x++){const i=y*n+x;
      if(y&1){idx[w++]=i;idx[w++]=i+1;idx[w++]=i+n+1;idx[w++]=i;idx[w++]=i+n+1;idx[w++]=i+n;}
      else{idx[w++]=i;idx[w++]=i+1;idx[w++]=i+n;idx[w++]=i+1;idx[w++]=i+n+1;idx[w++]=i+n;}}
    gl.bufferSubData(gl.ELEMENT_ARRAY_BUFFER,0,idx);
    buffers.indexPattern="hex-static";buffers.edgeSpin=null;
  }else{
    // boot() and resolution changes evaluate the graph synchronously before the next frame, so do
    // not waste a second full-buffer upload on placeholder checkerboard indices.
    buffers.indexPattern="pending";buffers.edgeSpin=null;
  }
  // Water plane shares the vertex lattice with the terrain (same index buffer draws both), so
  // its XZ MUST use the same hex offsets or shorelines tear along the odd rows.
  const hx=isHex()?0.5:0,rz=isHex()?HEX_ROW:1,hexOn=isHex(),xHalf=(n-1)/2,zHalf=(nh-1)*rz/2;
  const xz=new Float32Array(n*nh*2);for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const i=y*n+x;
    if(hexOn){xz[i*2]=(x+hx*(y&1)-xHalf)/xHalf;xz[i*2+1]=(y*rz-zHalf)/xHalf;}
    else{xz[i*2]=((x/(n-1)-0.5)*2);xz[i*2+1]=((y/(n-1)-0.5)*2);}}
  gl.bindBuffer(gl.ARRAY_BUFFER,buffers.gridXZ);gl.bufferData(gl.ARRAY_BUFFER,xz,gl.STATIC_DRAW);   // water plane XZ (static)
  // Review B3: undo/redo/New/restoreGraph change terrainDef.lattice WITHOUT the toggle button;
  // updateViewport compares this tag and rebuilds, or a hex session undone to square kept the
  // hex water plane (shoreline detached) and redo drew hex vertices under the leftover square
  // adaptive index buffer (sliver strips map-wide).
  buffers.builtLattice=terrainDef.lattice||"square";
  // buildIndex is the ONE place the built lattice changes, whatever drove it (toggle, undo,
  // redo, New, restoreGraph), so refresh the always-visible toolbar chip from here.
  if(typeof syncBuildProfile==="function"&&$("#profileDetail"))syncBuildProfile();
}
let curField=null,curHeightSource=null,curHgt=null,curSnowDepthM=null,curSurfaceY=null,curSolidSurfaceY=null,curSnowLayerRef=null;
let curSurfaceMaxY=0;
let curTemperatureRef=null,curSunVisibilityRef=null;
let curFilled=null,curAccum=null,curWater=null,curWaterLiquid=null,curWaterIce=null,curIceSnow=null,curIceSnowSurfaceY=null,curGeomKey="",lastWaterSig="",lastWaterTemperatureRef=null,lastFallbackClimateSig="";
function primaryImportedHeight(rootNode){
  let node=rootNode;const seen=new Set();
  while(node&&!seen.has(node.id)){
    seen.add(node.id);
    if(node.type==="import")return node;
    const def=TYPES[node.type];
    // Masks and diagnostic/data maps convert height into a different quantity. An Import DEM on
    // their ancestry (or on an effect's side input) must not make that non-height field absolute.
    if(!def||def.cat==="mask"||def.cat==="data")return null;
    const edge=inputEdge(node.id,0);node=edge&&nodeById(edge.from);
  }
  return null;
}
function viewportHeightFrame(field,rootNode){
  let source=field,absolute=false;
  const imported=rootNode&&primaryImportedHeight(rootNode);
  const outputRaw=rootNode&&rootNode.type==="output"&&rootNode.params.norm==="off";
  if(imported||outputRaw){
    absolute=true;
    // Output normalisation is an encoding operation. For a DEM-derived graph, render the evaluated
    // input field so normalising its output samples cannot erase the Import DEM height multiplier.
    if(imported&&rootNode.type==="output"&&rootNode.params.norm==="on"){
      const edge=inputEdge(rootNode.id,0),input=edge&&nodeById(edge.from);
      if(input&&input._field&&input._field.length===field.length)source=input._field;
    }
  }
  return{source,absolute};
}
function updateViewport(f,rootNode,options){
  if(!gl){return;}
  const n=fieldW(),nh=fieldH(),field=f||newField();rootNode=rootNode||activePreviewNode();
  const heightFrame=viewportHeightFrame(field,rootNode),heightSource=heightFrame.source;
  const geomKey=n+"|"+H_SCALE+"|"+(terrainDef.lattice||"square")+"|"+(heightFrame.absolute?"absolute":"autolevel");
  if(buffers.idx&&buffers.builtLattice!==(terrainDef.lattice||"square"))buildIndex();
  const baseChanged=curField!==f||curHeightSource!==heightSource||!curHgt||curHgt.length!==n*nh||curGeomKey!==geomKey;
  const layerDepth=scene.snow&&scene.snow.layer&&scene.snow.layer.depthM&&scene.snow.layer.depthM.length===n*nh
    ?scene.snow.layer.depthM:null;
  const snowChanged=curSnowLayerRef!==layerDepth;let geometryChanged=baseChanged||snowChanged;
  let hgt=curHgt;
  if(baseChanged){
    const[mn,mx]=fieldRange(heightSource),d=mx-mn||1;hgt=new Float32Array(n*nh);
    for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const i=y*n+x,h=heightFrame.absolute?heightSource[i]:(heightSource[i]-mn)/d;
      hgt[i]=h;}
    gl.bindBuffer(gl.ARRAY_BUFFER,buffers.hgt);gl.bufferData(gl.ARRAY_BUFFER,hgt,gl.DYNAMIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER,buffers.drive);gl.bufferData(gl.ARRAY_BUFFER,hgt,gl.DYNAMIC_DRAW);
    curHgt=hgt;curFilled=null;curAccum=null;
  }
  // Edge topology depends only on the terrain's solid geometry. Water level, colour, climate,
  // and camera edits therefore never rebuild the index buffer. Accumulated snow participates
  // because it is genuine displacement rather than a material-only effect.
  // Hex topology is static (unique equilateral triangulation, uploaded by buildIndex once);
  // only the square lattice adaptively re-streams diagonals as the height changes.
  if((baseChanged||snowChanged)&&!isHex())streamTerrainIndices(hgt,layerDepth);
  const previewTemperatureField=rootNode&&fieldMetadata(rootNode._field)&&fieldMetadata(rootNode._field).kind==="temperature"
    ?rootNode._field:null;
  const activeTemperatureField=previewTemperatureField
    ||scene.snow&&scene.snow.temperatureField
    ||scene.water&&scene.water.temperatureField||null;
  const activeTemperatureMeta=fieldMetadata(activeTemperatureField)||{};
  const temperatureNode=rootNode&&(rootNode.type==="d_temperature"?rootNode:nearestUpstreamNode("d_temperature",rootNode));
  const shadowNode=rootNode&&(rootNode.type==="d_sunshadow"?rootNode:nearestUpstreamNode("d_sunshadow",rootNode));
  const temperatureMap=temperatureCFromField(activeTemperatureField)
    ||scene.snow&&scene.snow.layer&&scene.snow.layer.temperatureC
    ||temperatureNode&&temperatureNode._temperatureC||null;
  const sunVisibility=activeTemperatureMeta.solarShadow
    ||shadowNode&&shadowNode._solarShadow
    ||temperatureNode&&temperatureNode._solarShadow
    ||scene.snow&&scene.snow.layer&&scene.snow.layer.solarShadow||null;
  const fallbackClimateSig=[terrainDef.baseElevation,terrainDef.seaTemp,terrainDef.lapseRate].join("|");
  const fallbackClimateChanged=fallbackClimateSig!==lastFallbackClimateSig;
  if(baseChanged||temperatureMap!==curTemperatureRef||(!temperatureMap&&fallbackClimateChanged)){
    const temp=temperatureMap&&temperatureMap.length===n*nh?temperatureMap:new Float32Array(n*nh);
    if(!temperatureMap)for(let i=0;i<temp.length;i++)temp[i]=terrainDef.seaTemp
      -terrainDef.lapseRate*((terrainDef.baseElevation+hgt[i]*terrainDef.height)/1000);
    gl.bindBuffer(gl.ARRAY_BUFFER,buffers.temperature);gl.bufferData(gl.ARRAY_BUFFER,temp,gl.DYNAMIC_DRAW);
    curTemperatureRef=temperatureMap;
  }
  lastFallbackClimateSig=fallbackClimateSig;
  if(baseChanged||sunVisibility!==curSunVisibilityRef){
    const vis=sunVisibility&&sunVisibility.length===n*nh?sunVisibility:new Float32Array(n*nh).fill(1);
    gl.bindBuffer(gl.ARRAY_BUFFER,buffers.sunvis);gl.bufferData(gl.ARRAY_BUFFER,vis,gl.DYNAMIC_DRAW);
    curSunVisibilityRef=sunVisibility;
  }
  // Resolve water before constructing the visible solid surface. This lets snow obey the phase
  // boundary: submerged terrain receives no displayed snow, while frozen standing water gets its
  // own surface snow layer in refreshWater().
  if(scene.water&&scene.water.mode!=="sea"&&(!curFilled||!curAccum)){
    curFilled=priorityFloodFill(hgt);
    curAccum=d8Accumulation(curFilled);
  }
  const waterSig=scene.water?JSON.stringify([{...scene.water,temperatureField:undefined},terrainDef.baseElevation,
    terrainDef.seaTemp,terrainDef.lapseRate,
    scene.snow&&{snowfall:scene.snow.snowfall,meltDays:scene.snow.meltDays,meltRate:scene.snow.meltRate}]):"";
  const waterTemperatureRef=scene.water&&scene.water.temperatureField||null;
  const waterChanged=baseChanged||waterSig!==lastWaterSig||waterTemperatureRef!==lastWaterTemperatureRef;
  if(waterChanged)refreshWater();
  lastWaterSig=waterSig;lastWaterTemperatureRef=waterTemperatureRef;geometryChanged=geometryChanged||waterChanged;
  if(geometryChanged){
    const H=H_SCALE,snow=layerDepth?Float32Array.from(layerDepth):new Float32Array(n*nh);
    if(curWater)for(let i=0;i<snow.length;i++)if(curWater[i]>hgt[i]+1e-7)snow[i]=0;
    // SNOW DRAPE - display only; the physics depth field is untouched (this is already a copy).
    // Snow is a blanket: a surface deep enough to bury a feature cannot also express that feature.
    // Composing snowTop = terrain + depth verbatim keeps every crag knife-sharp under metres of
    // cover, which reads as white-painted rock - the single strongest "cartoon" tell. So the snow
    // TOP is relaxed toward a smoothed composite, weighted by local depth: thin dustings follow the
    // ground exactly, deep pack rounds it off. The top never dips below ground, and never below 35%
    // of the physical depth, so coverage classification in the shader stays honest.
    {
      let hasSnow=false;for(let i=0;i<snow.length;i++)if(snow[i]>1e-6){hasSnow=true;break;}
      if(hasSnow){
        const invH=1/Math.max(terrainDef.height,1e-6);
        const comp=new Float32Array(n*nh),tmp=new Float32Array(n*nh);
        for(let i=0;i<n*nh;i++)comp[i]=hgt[i]+snow[i]*invH;
        const blur=(src,dst)=>{ // separable 3-tap box, border-replicated
          for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const i=y*n+x;
            dst[i]=(src[y*n+Math.max(0,x-1)]+src[i]+src[y*n+Math.min(n-1,x+1)])/3;}
          for(let x=0;x<n;x++)for(let y=0;y<nh;y++){const i=y*n+x;
            tmp[i]=(dst[Math.max(0,y-1)*n+x]+dst[i]+dst[Math.min(nh-1,y+1)*n+x])/3;}
          dst.set(tmp);
        };
        // Two passes into DISTINCT buffers. blur(b,b) would alias src and dst in the horizontal
        // sweep, turning the box filter into a one-sided recursive filter with an exponential tail
        // in +x only - an east-biased drape that lifts cells from content up to five cells west.
        const b=new Float32Array(n*nh),b2=new Float32Array(n*nh);
        blur(comp,b);blur(b,b2);                         // [1,2,3,2,1]/9 per axis, ~5-cell blanket
        for(let i=0;i<n*nh;i++){
          const dM=snow[i];if(dM<=1e-6)continue;
          const w=smooth(clamp((dM-.3)/1.7,0,1));        // drape from 0.3 m, full by 2 m of pack
          // Displacement bounded SYMMETRICALLY by the local pack: a blanket redistributes within
          // its own thickness, so the top may deviate from terrain+depth by at most 0.6 x depth in
          // either direction. Unbounded lift filled couloirs with metres of displayed snow that
          // had no physical mass behind it; and on a crag whose 5-cell curvature exceeds the local
          // pack this clamp binds - correctly: a 3 m blanket CANNOT bury a 7 m spike, so sharp
          // ground is only partially rounded. That is the physical behaviour, not a compromise.
          // The symmetric clamp is also the floor: top >= comp - 0.6*dM = ground + 0.4*dM, so a
          // draped cell keeps >= 40% of its physical depth and a covered cell can never read bare.
          // (Below 0.3 m of pack w = 0 and the drape is exactly a no-op, which is what actually
          // protects the 1-15 cm coverage band.)
          const lim=.6*dM*invH,disp=clamp((b2[i]-comp[i])*w,-lim,lim);
          snow[i]=(comp[i]+disp-hgt[i])/invH;
        }
      }
    }
    const pos=new Float32Array(n*nh*3),nrm=new Float32Array(n*nh*3),surface=new Float32Array(n*nh),surfaceTex=new Float32Array(n*nh);
    const hexOn=isHex(),hx=hexOn?0.5:0,rz=hexOn?HEX_ROW:1,xHalf=(n-1)/2,zHalf=(nh-1)*rz/2;
    for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const i=y*n+x;
      surface[i]=hgt[i]*H+snow[i]/terrainDef.scale;
      surfaceTex[i]=hgt[i]+snow[i]/terrainDef.height;
      pos[i*3+1]=surface[i];
      if(hexOn){pos[i*3]=(x+hx*(y&1)-xHalf)/xHalf;pos[i*3+2]=(y*rz-zHalf)/xHalf;}
      else{pos[i*3]=((x/(n-1)-0.5)*2);pos[i*3+2]=((y/(n-1)-0.5)*2);}}
    if(hexOn){
      // Six-neighbour least-squares gradient (26): for the unit vectors to the D6 neighbours,
      // sum(e_k) = 0 and sum(e_k e_k^T) = 3I, so g = sum(h_k * e_k)/3 is exact for planes and
      // isotropic to leading order - the centre height drops out. Offsets depend on row parity
      // (odd-r); the six unit vectors are the same for both parities and all sit at distance 1,
      // because the row step is already sqrt(3)/2.
      const EX=[1,-1,.5,-.5,.5,-.5],EY=[0,0,HEX_ROW,HEX_ROW,-HEX_ROW,-HEX_ROW];
      const xc=k2=>clamp(k2,0,n-1);   // hoisted: a per-vertex closure was ~1M allocations/frame at 1024
      for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const i=y*n+x,par=y&1;
        const yu=clamp(y-1,0,nh-1),yd=clamp(y+1,0,nh-1);
        const off=par?0:-1; // even rows look left for their diagonal pair, odd rows look right
        const hE=surface[y*n+xc(x+1)],hW=surface[y*n+xc(x-1)];
        const hDE=surface[yd*n+xc(x+off+1)],hDW=surface[yd*n+xc(x+off)];
        const hUE=surface[yu*n+xc(x+off+1)],hUW=surface[yu*n+xc(x+off)];
        const gx=(hE*EX[0]+hW*EX[1]+hDE*EX[2]+hDW*EX[3]+hUE*EX[4]+hUW*EX[5])/3;
        const gy=(hDE*EY[2]+hDW*EY[3]+hUE*EY[4]+hUW*EY[5])/3;
        const sx=-gx*(n-1),sz=-gy*(n-1),L=Math.hypot(sx,1,sz)||1;
        nrm[i*3]=sx/L;nrm[i*3+1]=1/L;nrm[i*3+2]=sz/L;}
    }else{
      for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const i=y*n+x;
        const hl=surface[y*n+clamp(x-1,0,n-1)],hr=surface[y*n+clamp(x+1,0,n-1)];
        const hu=surface[clamp(y-1,0,nh-1)*n+x],hd=surface[clamp(y+1,0,nh-1)*n+x];
        const sx=(hl-hr)*(n-1)/2,sz=(hu-hd)*(n-1)/2,L=Math.hypot(sx,1,sz)||1;
        nrm[i*3]=sx/L;nrm[i*3+1]=1/L;nrm[i*3+2]=sz/L;}
    }
    gl.bindBuffer(gl.ARRAY_BUFFER,buffers.pos);gl.bufferData(gl.ARRAY_BUFFER,pos,gl.DYNAMIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER,buffers.nrm);gl.bufferData(gl.ARRAY_BUFFER,nrm,gl.DYNAMIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER,buffers.snow);gl.bufferData(gl.ARRAY_BUFFER,snow,gl.DYNAMIC_DRAW);
    // Deferred terrain normals, shadows, AO and water depth all read the visible solid surface.
    // Uploading the displaced field here keeps those passes aligned with accumulated snow.
    if(hTex){gl.bindTexture(gl.TEXTURE_2D,hTex);gl.texImage2D(gl.TEXTURE_2D,0,gl.R32F,n,nh,0,gl.RED,gl.FLOAT,surfaceTex);}
    curSnowDepthM=snow;curSurfaceY=surface;curSnowLayerRef=layerDepth;
    // The non-destructive terrain stream remains bedrock/soil, while this composed solid-surface
    // heightfield is what picking, readouts, and future "bake visible surface" export should use.
    // Frozen water is solid support; snow on that ice therefore raises the composed height.
    curSolidSurfaceY=surface.slice();
    if(curIceSnowSurfaceY&&curWaterIce)for(let i=0;i<curSolidSurfaceY.length;i++)
      if(curWaterIce[i]>.5)curSolidSurfaceY[i]=Math.max(curSolidSurfaceY[i],curIceSnowSurfaceY[i]);
    curSurfaceMaxY=-Infinity;
    for(let i=0;i<curSolidSurfaceY.length;i++)curSurfaceMaxY=Math.max(curSurfaceMaxY,curSolidSurfaceY[i]);
  }
  curField=f;curHeightSource=heightSource;curGeomKey=geomKey;
  if(baseChanged||!options||options.color!==false){
    // SatMap colouring. Resolve the colour graph (SatMap ramps composite/branch/blend) to a per-vertex RGB buffer;
    // if there is no colour node, drive the global LUT by elevation (backward-compatible fallback).
    const colorRoot=rootNode?(rootNode.type==="output"?inEdgeFrom(rootNode.id,0):rootNode.id):null;
    const colorMemo={},colField=colorRoot?resolveColor(colorRoot,n,colorMemo):null;
    const previewWind=rootNode&&windVectorFromField(rootNode._field);
    const sceneWind=scene.snow&&windVectorFromField(scene.snow.windField);
    const windCol=shadeMode===7?windColorField(previewWind||sceneWind,n):null;
    // Graph-native colour nodes must preview their actual albedo output, not a misleading duplicate height thumbnail.
    // Bake the tiny canvases now, then release the full intermediate RGB fields with colorMemo after this update.
    for(const id in colorMemo){const nd=nodeById(+id),rgb=colorMemo[id];if(nd&&rgb)nd._thumb=bakeColorThumb(nd,rgb);}
    satComposite=windCol||colField?1:0;
    const col=windCol||colField||new Float32Array(n*nh*3);
    satUniform={lo:0,hi:1,shift:0,reverse:0};               // driver attribute = elevation for the fallback shader path
    if(!satDrawerOpen()&&!satComposite)buildSatLUT("Pewter"); // no SatMap node: neutral inspection material, never a hidden palette choice
    gl.bindBuffer(gl.ARRAY_BUFFER,buffers.col);gl.bufferData(gl.ARRAY_BUFFER,col,gl.DYNAMIC_DRAW);
  }
}
// --- Priority-flood depression fill (Barnes, Lehman & Mulla 2014): every pit fills to the elevation of
//     its lowest spill point on the basin rim -> filled-h is the standing-water depth, flat per basin. ---
function priorityFloodFill(h,flatEpsilon=2e-7){
  // `flatEpsilon` exists for ROUTING: the invisible monotone gradient lets D8 accumulation cross
  // lake flats instead of terminating on them. It is NOT free for a solver that refills every
  // iteration: inside streamPowerErode the epsilon re-tilts every flat each pass, which measurably
  // destroyed the Braun-Willett steady state - slope-area exponent -0.310 (r2 0.05) against the
  // landed -0.490 (r2 0.62); restoring a pure max-fill for the solver returns -0.479 (r2 0.61).
  // Callers choose: routing/water pass the default; the implicit erosion solve passes 0.
  const n=fieldW(),nh=fieldH(),N=n*nh,filled=new Float32Array(N),done=new Uint8Array(N),heap=[];
  const push=(e,i)=>{heap.push([e,i]);let c=heap.length-1;while(c>0){const p=(c-1)>>1;if(heap[p][0]<=heap[c][0])break;const t=heap[p];heap[p]=heap[c];heap[c]=t;c=p;}};
  const pop=()=>{const top=heap[0],last=heap.pop();if(heap.length){heap[0]=last;let c=0;for(;;){let l=2*c+1,r=l+2-1,s=c;if(l<heap.length&&heap[l][0]<heap[s][0])s=l;if(r<heap.length&&heap[r][0]<heap[s][0])s=r;if(s===c)break;const t=heap[s];heap[s]=heap[c];heap[c]=t;c=s;}}return top;};
  const seed=(x,y)=>{const i=y*n+x;if(!done[i]){done[i]=1;filled[i]=h[i];push(h[i],i);}};
  for(let x=0;x<n;x++){seed(x,0);seed(x,nh-1);}
  for(let y=0;y<nh;y++){seed(0,y);seed(n-1,y);}
  // The flood must walk the lattice's OWN connectivity. On hex that is the D6 one-ring: the
  // square 4-offset set covers only 4 of the 6 true neighbours (it misses the (x-1,y±1) pair on
  // even rows and (x+1,y±1) on odd rows), so a basin whose only spill runs through one of those
  // would flood spuriously.
  const nbSq=[[-1,0],[1,0],[0,-1],[0,1]],hex=isHex();
  while(heap.length){const it=pop(),e=it[0],c=it[1],cy=(c/n)|0,cx=c-cy*n;
    const nb=hex?hexNb(cy):nbSq;
    for(const dd of nb){const xx=cx+dd[0],yy=cy+dd[1];if(xx<0||yy<0||xx>=n||yy>=nh)continue;const ni=yy*n+xx;if(done[ni])continue;
      // Epsilon filling resolves otherwise perfectly flat depressions. The invisible monotonic
      // gradient gives every flooded cell a route back to the spill point, so D8 accumulation
      // crosses lake flats instead of terminating there. Across an entire 4K tile the maximum
      // introduced rise is < 0.001 of normalized relief.
      done[ni]=1;const fv=flatEpsilon>0?(h[ni]<=e?e+flatEpsilon:h[ni]):Math.max(h[ni],e);filled[ni]=fv;push(fv,ni);}}
  return filled;
}
// --- D8 flow accumulation on the (pit-free) filled DEM: drainage area per cell -> the river network. ---
function d8Accumulation(g){
  const n=fieldW(),nh=fieldH(),N=n*nh,A=new Float32Array(N).fill(1);
  // D6 on hex (the name is kept: this is the accumulation pass, whichever one-ring it walks).
  // Six equidistant candidates mean the receiver is unambiguous with no sqrt(2) weighting to
  // forget - 26's cleanest single win over D8.
  //
  // AND THE SQUARE BRANCH FORGOT IT, exactly as the line above warns. The receiver used to be the
  // LOWEST neighbour rather than the STEEPEST, over a table that carried no distances - so on any
  // smooth slope the diagonal, being sqrt(2) further, is always lower and always won. Measured on a
  // cone, where true drainage is radial and every azimuth must carry equal area
  // (_verify_flow_facets): FOUR spokes on the diagonals, and the four axial directions never chosen
  // at all - axis-bin drainage ran at 0.14 of diagonal-bin drainage. spReceivers and hydroFixField
  // both divide by d[2]*cellsize; this was the one router of three that did not, which is why the
  // three disagreed about where water goes on identical terrain.
  //
  // WHAT THE FIX DOES NOT DO: it does not make routing isotropic. Facet concentration went 1.8132 ->
  // 1.8161, i.e. nowhere. A single-receiver router snaps every cell onto SOME lattice direction
  // whichever rule selects it; correcting the rule moved the spokes from the diagonals to the axes
  // and restored the other four, but eight spokes are still spokes. Only MFD lowers that number -
  // which is exactly why `26` credits MFD, not D6, with "smoother and more natural".
  //
  // Hex is UNAFFECTED and that is the control: all six candidates are one cell away, so dividing by
  // a common distance cannot move the argmax. Measured hex 1.6734 before and after, unchanged.
  // MULTIPLE FLOW DIRECTION (Freeman 1991, P-tier), which is the part that actually delivers
  // "smoother and more natural" - D6 on its own does not, and `26` is explicit about it. A
  // single-receiver router hands ALL of a cell's water to ONE neighbour, so the only flow directions
  // it can express are the lattice's own: D8 offers eight at 45 degrees, D6 six at 60, and hex is
  // the COARSER of the two on this one measure. Fixing which neighbour gets picked cannot help -
  // the commit before this one corrected exactly that and facet concentration did not move (1.8132
  // -> 1.8161). The spokes are the routing model, not the selection rule.
  //
  // Freeman distributes to EVERY downslope neighbour in proportion to slope^p, so the resolved
  // direction is continuous rather than snapped, and p=1.1 is his recommended value. p -> infinity
  // degenerates to single-receiver, which is the sense in which this generalises what it replaces.
  // Quinn's contour-length weighting is deliberately NOT used: it collapses on hex (`26:174`), where
  // all six neighbours share one contour length, so it would reduce to Freeman with extra steps on
  // one lattice and not the other.
  //
  // Measured on a cone (_verify_flow_facets), where drainage is radial by symmetry:
  //     single receiver   square 1.8161   hex 1.6734
  //     Freeman p=1.1     square 1.0114   hex 1.0220
  //
  // Cost, measured against the same input rather than guessed: accumulation goes 78 -> 105 ms at
  // 512 square and 270 -> 423 ms at 1024 square, so 1.3-1.6x. For scale, priorityFloodFill on the
  // same field is 70 and 260 ms - this sits beside it in the same build-time budget, not in a new
  // one. The sort is still the asymptotic term; the eight pow() calls per cell are not.
  //
  // Both call sites get this: the d_flow node AND refreshWater's curAccum. They must agree, or the
  // rendered rivers sit somewhere other than the flow map says - which is the same class of defect
  // as the three routers disagreeing, one commit ago.
  const nbSq=[[-1,0,1],[1,0,1],[0,-1,1],[0,1,1],[-1,-1,Math.SQRT2],[1,1,Math.SQRT2],[-1,1,Math.SQRT2],[1,-1,Math.SQRT2]];
  const hex=isHex(),P=1.1,w=new Float64Array(8);
  const order=Array.from({length:N},(_,i)=>i).sort((a,b)=>g[b]-g[a]);   // upstream (high) before downstream (low)
  // Descending height means a cell's own A is final before it gives any away, exactly as it was for
  // the single-receiver walk. Weights are recomputed here rather than cached from a first pass: at
  // 4096 square, eight fractions per cell would be 537 MB of Float32 that this loop reads once.
  for(const i of order){
    const y=(i/n)|0,x=i-y*n,nb=hex?hexNb(y):nbSq;
    let tot=0,k=0;
    for(const dd of nb){
      const xx=x+dd[0],yy=y+dd[1];let ww=0;
      if(xx>=0&&yy>=0&&xx<n&&yy<nh){
        const sl=(g[i]-g[yy*n+xx])/(hex?1:dd[2]);
        if(sl>0)ww=Math.pow(sl,P);
      }
      w[k++]=ww;tot+=ww;
    }
    if(tot<=0)continue;                     // filled flats and the outlet: flow stops, as before
    const share=A[i]/tot;k=0;
    for(const dd of nb){
      if(w[k]>0)A[(y+dd[1])*n+(x+dd[0])]+=share*w[k];
      k++;
    }
  }
  return A;
}
// Build the per-vertex WATER SURFACE (flat in lake basins, sloped along rivers) + its normals, from the
// cached fill/accumulation and the current sea/hydro controls. Cheap O(N) -> runs live on slider drags.
function refreshWater(){
  if(!gl||!curHgt)return;
  const n=fieldW(),nh=fieldH(),N=n*nh,h=curHgt,filled=curFilled,A=curAccum,H=H_SCALE;
  const W=new Float32Array(N),wetMask=new Uint8Array(N);
  const wn_=scene.water;                                  // params come from the Water effect node (null = no water)
  const hydroOn=wn_&&wn_.mode!=="sea",seaOn=wn_&&wn_.mode==="sea";
  const thr=(0.02-0.0194*((wn_&&wn_.flow)||0))*N;         // River flow param: high -> denser network (lower area threshold)
  const lakesOn=hydroOn&&(!wn_||wn_.lakes!=="off"),lakeMin=wn_&&wn_.lakeMin!=null?wn_.lakeMin:.001;
  const riverDepth=wn_&&wn_.riverDepth!=null?wn_.riverDepth:.7;
  const seaL=seaOn?wn_.level:-1;
  for(let i=0;i<N;i++){
    let w=h[i];
    if(hydroOn){
      const lakeDepth=filled[i]-h[i];
      if(lakesOn&&lakeDepth>lakeMin)w=filled[i];           // lake: stand water to the basin spill level
      if(riverDepth>0&&A[i]>thr){
        const film=Math.min(.002+.026*riverDepth,.001+.009*riverDepth+.005*riverDepth*Math.log(A[i]/thr));
        if(h[i]+film>w)w=h[i]+film;}                       // river film follows the routed channel downhill
    }
    if(seaL>w)w=seaL;                                     // flat ocean at a level (Sea mode)
    W[i]=w;wetMask[i]=w>h[i]+1e-7?1:0;
  }
  // Extend the adjacent wet surface one dry vertex beyond the coverage boundary. Coverage still
  // comes from signed water depth, but shoreline triangles now stay on the lake/sea plane instead
  // of climbing to a dry mountain vertex and forming the large saw-tooth fins seen at grazing angles.
  const waterSurface=W.slice();
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){
    const i=y*n+x;if(wetMask[i])continue;
    let sum=0,count=0;
    // Shoreline extension over the lattice's OWN one-ring: the 3x3 square window is 8 cells at
    // two different distances, and on hex two of them are not neighbours at all - which reads as
    // a row-parity tear along the shore.
    if(isHex()){
      const nb=hexNb(y);
      for(let k=0;k<6;k++){const xx=x+nb[k][0],yy=y+nb[k][1];
        if(xx<0||yy<0||xx>=n||yy>=nh)continue;
        const j=yy*n+xx;if(wetMask[j]){sum+=W[j];count++;}}
    }else for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
      if(!dx&&!dy)continue;const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=n||yy>=nh)continue;
      const j=yy*n+xx;if(wetMask[j]){sum+=W[j];count++;}
    }
    // Never let the guard create water on a dry sample. Normal shores remain coplanar because their
    // dry terrain is above the adjacent water; unusual disconnected low samples stay dry.
    if(count)waterSurface[i]=Math.min(sum/count,h[i]);
  }
  curWater=waterSurface;                                    // exposed to diagnostics and renderer tests
  const wn=new Float32Array(N*3);                          // normal of the WATER surface (0 gradient in lakes -> up)
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const i=y*n+x;
    const wl=waterSurface[y*n+clamp(x-1,0,n-1)],wr=waterSurface[y*n+clamp(x+1,0,n-1)];
    const wu=waterSurface[clamp(y-1,0,nh-1)*n+x],wd=waterSurface[clamp(y+1,0,nh-1)*n+x];
    const sx=(wl-wr)*H*(n-1)/2,sz=(wu-wd)*H*(n-1)/2,L=Math.hypot(sx,1,sz)||1;
    wn[i*3]=sx/L;wn[i*3+1]=1/L;wn[i*3+2]=sz/L;}
  // Snow on frozen standing water is another transient thickness layer. It shares the Snow node's
  // event/melt controls but uses the lake/sea elevation and a flatness gate, so flowing river films
  // are not silently converted into raised white ribbons.
  const iceSnow=new Float32Array(N),liquidMask=new Float32Array(N),iceMask=new Float32Array(N),snowP=scene.snow;
  const climateTemp=temperatureCFromField(wn_&&wn_.temperatureField);
  const temperatureMeta=fieldMetadata(wn_&&wn_.temperatureField),waterLapse=temperatureMeta&&temperatureMeta.lapseRate!=null
    ?temperatureMeta.lapseRate:terrainDef.lapseRate;
  const rawIce=new Float32Array(N),waterTemperatureC=new Float32Array(N);
  for(let i=0;i<N;i++){
    if(!wetMask[i])continue;
    const temp=climateTemp&&climateTemp.length===N
      ?climateTemp[i]-waterLapse*((waterSurface[i]-h[i])*terrainDef.height/1000)
      :terrainDef.seaTemp-terrainDef.lapseRate*((terrainDef.baseElevation+waterSurface[i]*terrainDef.height)/1000);
    waterTemperatureC[i]=temp;
    const ice=clamp((1-temp)/3,0,1),standing=clamp((wn[i*3+1]-.997)/.0028,0,1);
    rawIce[i]=ice*standing;
  }
  // The physical three-degree transition keeps coves locally liquid/frozen. The deferred renderer
  // bilinearly samples this field, avoiding a full-resolution CPU blur on every interactive edit.
  for(let i=0;i<N;i++){
    if(!wetMask[i])continue;
    const frozen=rawIce[i];
    iceMask[i]=frozen;liquidMask[i]=1-frozen;
    if(!snowP||frozen<=0)continue;
    const temp=waterTemperatureC[i];
    const snowFraction=clamp((2-temp)/5,0,1);
    const snowfall=snowP.snowfall==null?6*(snowP.amount==null?.5:snowP.amount):snowP.snowfall;
    const meltRate=snowP.meltRate==null?10:snowP.meltRate,meltDays=snowP.meltDays==null?45:snowP.meltDays;
    const deposited=snowfall*snowFraction;
    const melted=Math.min(deposited,Math.max(0,temp)*meltRate/1000*meltDays);
    iceSnow[i]=(deposited-melted)*frozen;
  }
  // Keep the visible transient stack explicit in world render units:
  // terrain < water/ice surface < snow-on-ice top. Its own normal prevents the raised snow
  // geometry from being lit as though it were still the flat ice sheet or submerged bed.
  const iceSnowSurfaceY=new Float32Array(N),iceSnowNrm=new Float32Array(N*3);
  for(let i=0;i<N;i++)iceSnowSurfaceY[i]=waterSurface[i]*H+iceSnow[i]/terrainDef.scale;
  for(let y=0;y<nh;y++)for(let x=0;x<n;x++){const i=y*n+x;
    const l=iceSnowSurfaceY[y*n+clamp(x-1,0,n-1)],r=iceSnowSurfaceY[y*n+clamp(x+1,0,n-1)];
    const d=iceSnowSurfaceY[clamp(y-1,0,nh-1)*n+x],u_=iceSnowSurfaceY[clamp(y+1,0,nh-1)*n+x];
    const sx=(l-r)*(n-1)/2,sz=(d-u_)*(n-1)/2,L=Math.hypot(sx,1,sz)||1;
    iceSnowNrm[i*3]=sx/L;iceSnowNrm[i*3+1]=1/L;iceSnowNrm[i*3+2]=sz/L;
  }
  curWaterLiquid=liquidMask;curWaterIce=iceMask;curIceSnow=iceSnow;curIceSnowSurfaceY=iceSnowSurfaceY;
  gl.bindBuffer(gl.ARRAY_BUFFER,buffers.wsurf);gl.bufferData(gl.ARRAY_BUFFER,waterSurface,gl.DYNAMIC_DRAW);   // forward-path geometry water
  gl.bindBuffer(gl.ARRAY_BUFFER,buffers.wnrm);gl.bufferData(gl.ARRAY_BUFFER,wn,gl.DYNAMIC_DRAW);
  gl.bindBuffer(gl.ARRAY_BUFFER,buffers.ice);gl.bufferData(gl.ARRAY_BUFFER,iceMask,gl.DYNAMIC_DRAW);
  gl.bindBuffer(gl.ARRAY_BUFFER,buffers.iceSnow);gl.bufferData(gl.ARRAY_BUFFER,iceSnow,gl.DYNAMIC_DRAW);
  gl.bindBuffer(gl.ARRAY_BUFFER,buffers.iceSnowNrm);gl.bufferData(gl.ARRAY_BUFFER,iceSnowNrm,gl.DYNAMIC_DRAW);
  if(wTex){gl.bindTexture(gl.TEXTURE_2D,wTex);gl.texImage2D(gl.TEXTURE_2D,0,gl.R32F,n,nh,0,gl.RED,gl.FLOAT,waterSurface);} // deferred-path water-height texture
  if(iTex){gl.bindTexture(gl.TEXTURE_2D,iTex);gl.texImage2D(gl.TEXTURE_2D,0,gl.R32F,n,nh,0,gl.RED,gl.FLOAT,iceMask);}
  if(isTex){gl.bindTexture(gl.TEXTURE_2D,isTex);gl.texImage2D(gl.TEXTURE_2D,0,gl.R32F,n,nh,0,gl.RED,gl.FLOAT,iceSnow);}
}
function resizeGL(){const r=glc.parentElement.getBoundingClientRect();
  const ss=Math.min(2.0,(devicePixelRatio||1)*1.35);          // supersample the whole render -> anti-aliased silhouettes
  glc.width=Math.round(r.width*ss);glc.height=Math.round(r.height*ss);}
function mat4mul(a,b){const o=new Float32Array(16);for(let i=0;i<4;i++)for(let j=0;j<4;j++){let s=0;for(let k=0;k<4;k++)s+=a[k*4+j]*b[i*4+k];o[i*4+j]=s;}return o;}
function perspective(fov,asp,n,f){const t=1/Math.tan(fov/2);return new Float32Array([t/asp,0,0,0, 0,t,0,0, 0,0,(f+n)/(n-f),-1, 0,0,2*f*n/(n-f),0]);}
function lookAt(e,c,u){const z=norm3(sub3(e,c)),x=norm3(cross3(u,z)),y=cross3(z,x);
  return new Float32Array([x[0],y[0],z[0],0, x[1],y[1],z[1],0, x[2],y[2],z[2],0, -dot3(x,e),-dot3(y,e),-dot3(z,e),1]);}
const sub3=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]],cross3=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],dot3=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const norm3=a=>{const l=Math.hypot(a[0],a[1],a[2])||1;return[a[0]/l,a[1]/l,a[2]/l];};
function cameraEye(){const ce=Math.cos(cam.el);return[cam.target[0]+Math.cos(cam.az)*ce*cam.dist,cam.target[1]+Math.sin(cam.el)*cam.dist,cam.target[2]+Math.sin(cam.az)*ce*cam.dist];}
function cameraBasis(){const eye=cameraEye(),forward=norm3(sub3(cam.target,eye)),right=norm3(cross3(forward,[0,1,0]));return{eye,forward,right,up:norm3(cross3(right,forward))};}
// Device NDC -> world position in CELL units, the exact inverse of the vertex mapping in
// updateViewport (x -> (wx-xHalf)/xHalf, z -> (wz-zHalf)/xHalf). Three call sites need it -
// surfaceHeight, the wind HUD and the climate HUD - and they drifted apart once already, so it
// lives in one place. Returns { x, wy } where wy is the WORLD y in cell units; callers wanting a
// row index divide by the row pitch.
function deviceToCell(wx,wz){
  const n=fieldW(),nh=fieldH(),rz=isHex()?HEX_ROW:1,xH=(n-1)/2,zH=(nh-1)*rz/2;
  return{x:wx*xH+xH,wy:wz*xH+zH,rz,row:(wz*xH+zH)/rz};
}
function surfaceHeight(wx,wz){
  const surface=curSolidSurfaceY||curSurfaceY||curHgt;if(!surface)return cam.target[1];
  // Device space -> world position in CELL units, which is exactly what sampleBilinear takes on
  // either lattice. On hex the mesh places rows at sqrt(3)/2 device spacing, so recover the
  // fractional row first and hand back row*sqrt(3)/2 - the sampler then applies each row's own
  // parity shift, exactly. (This used to carry its own shear approximation, up to half a cell of
  // error on the odd rows.)
  const dc=deviceToCell(wx,wz),x=dc.x,row=dc.row;
  const h=sampleBilinear(surface,x,isHex()?row*HEX_ROW:row);
  return curSolidSurfaceY||curSurfaceY?h:h*H_SCALE;
}
function keepCameraAboveSurface(){
  if(!curHgt)return;
  const eye=cameraEye();
  // The terrain is an open heightfield surface, not a closed solid. Letting the orbit eye pass
  // below it exposes back-facing triangles as long hanging wedges — visually identical to an
  // erosion spike even when the raw field is finite and smooth. Preserve the authored orbit and
  // lift eye + target together just enough to stay above the surface under the eye.
  const outside=Math.abs(eye[0])>1||Math.abs(eye[2])>1;
  const x=clamp(eye[0],-1,1),z=clamp(eye[2],-1,1);
  // When the orbit eye is outside the square, a higher ridge anywhere in the open heightfield can
  // silhouette the mesh from below. Its cached maximum is a conservative inspection-camera
  // collision plane: low grazing views remain possible, but the eye never crosses under geometry.
  const floor=(outside?curSurfaceMaxY:surfaceHeight(x,z))+Math.max(.006,cameraNear()*1.5);
  if(eye[1]<floor)cam.target[1]+=floor-eye[1];
}
// Project authored terrain directions into the current camera plane. Unlike a screen-fixed north
// badge, this needle remains useful after orbiting: it shows where map north and the equator actually
// lie across the visible terrain.
function terrainVectorScreenAngle(v,basis=cameraBasis()){
  const world=[v[0],0,v[1]],sx=dot3(world,basis.right),sy=dot3(world,basis.up);
  return Math.atan2(sx,sy)*180/Math.PI;
}
function syncCompass(){
  const root=$("#viewportCompass"),northEl=$("#compassNorth"),eqEl=$("#compassEquator");
  if(!root||!northEl||!eqEl)return;
  const orient=terrainOrientation(),basis=cameraBasis();
  const northAngle=terrainVectorScreenAngle(orient.north,basis);
  const eqAngle=terrainVectorScreenAngle(orient.equator,basis);
  northEl.style.transform=`rotate(${northAngle}deg)`;
  eqEl.style.display=orient.hemisphere===0?"none":"block";
  eqEl.style.transform=`rotate(${eqAngle}deg)`;
  northEl.querySelector(".vp-compass-n").style.transform=`rotate(${-northAngle}deg)`;
  eqEl.querySelector(".vp-compass-eq").style.transform=`rotate(${-eqAngle}deg)`;
  const lat=terrainDef.latitude||0,latLabel=lat===0?"equator":Math.abs(lat).toFixed(1)+"° "+(lat<0?"S":"N");
  const label=`Map north ${Math.round(terrainDef.north||0)}° clockwise from top; latitude ${latLabel}`;
  root.setAttribute("aria-label",label);root.title=label;
}
function windAtViewFocus(){
  const root=activePreviewNode(),preview=root&&windVectorFromField(root._field);
  const sceneField=scene.snow&&scene.snow.windField,sceneWind=windVectorFromField(sceneField);
  const wind=preview||sceneWind;
  if(wind&&wind.u.length===fieldLen()&&wind.v.length===fieldLen()){
    // Device -> world cell units, the same recovery surfaceHeight does: on hex the mesh puts
    // rows at sqrt(3)/2 device spacing, so reading device z as a row samples ~13% of the map
    // away from the point under the camera focus.
    const dc=deviceToCell(cam.target[0],cam.target[2]);
    const x=dc.x,y=dc.wy;
    const u=sampleBilinear(wind.u,x,y),v=sampleBilinear(wind.v,x,y);
    return{u,v,speed:Math.hypot(u,v),source:"field"};
  }
  const from=((terrainDef.windDirection==null?300:terrainDef.windDirection)%360+360)%360;
  const flow=windBearingVector(from);
  return{u:flow[0],v:flow[1],speed:Math.max(0,terrainDef.windSpeed==null?10:terrainDef.windSpeed),
    source:"fallback",from};
}
function syncWindReadout(){
  const root=$("#windReadout"),arrow=$("#windIndicatorArrow"),speedEl=$("#windSpeed"),bearingEl=$("#windBearing");
  if(!root||!arrow||!speedEl||!bearingEl)return;
  const local=windAtViewFocus(),calm=local.speed<1e-4;
  const from=local.from==null
    ?((Math.atan2(-local.u,local.v)*180/Math.PI)%360+360)%360
    :local.from;
  const flow=calm?windBearingVector(from):[local.u/local.speed,local.v/local.speed];
  const screenAngle=terrainVectorScreenAngle(flow),fromDeg=Math.round(from)%360,toDeg=(fromDeg+180)%360;
  arrow.style.transform=`rotate(${screenAngle}deg)`;
  speedEl.textContent=`W ${local.speed.toFixed(1)} m/s`;
  bearingEl.textContent=`${fromDeg}° from`;
  root.dataset.source=local.source;root.dataset.calm=calm?"true":"false";
  const source=local.source==="field"?"Graph wind at view focus":"Prevailing fallback wind";
  const label=`${source}: ${local.speed.toFixed(1)} metres per second from ${fromDeg} degrees, blowing toward ${toDeg} degrees.`;
  root.setAttribute("aria-label",label);root.title=label;
}
function syncClimateReadout(){
  const el=$("#climateReadout");if(!el)return;
  const elevationM=terrainDef.baseElevation+surfaceHeight(cam.target[0],cam.target[2])*terrainDef.scale;
  const root=activePreviewNode(),previewField=root&&fieldMetadata(root._field)&&fieldMetadata(root._field).kind==="temperature"?root._field:null;
  const temperatureNode=root&&(root.type==="d_temperature"?root:nearestUpstreamNode("d_temperature",root));
  const temperatureMap=temperatureCFromField(previewField
      ||scene.snow&&scene.snow.temperatureField
      ||scene.water&&scene.water.temperatureField)
    ||scene.snow&&scene.snow.layer&&scene.snow.layer.temperatureC||temperatureNode&&temperatureNode._temperatureC;
  // Device -> world cell units on either lattice (see windAtViewFocus / surfaceHeight).
  const c=temperatureMap&&temperatureMap.length===fieldLen()
    ?(dc=>sampleBilinear(temperatureMap,dc.x,dc.wy))(deviceToCell(cam.target[0],cam.target[2]))
    :terrainDef.seaTemp-terrainDef.lapseRate*elevationM/1000;
  const value=TEMP_UNIT==="F"?c*9/5+32:c,unit=TEMP_UNIT==="F"?"°F":"°C";
  el.textContent=`T ${value.toFixed(1)} ${unit} · ${Math.round(elevationM)} m`;
  el.setAttribute("aria-label",`${temperatureMap?"Graph field":"Fallback air"} temperature at view focus: ${value.toFixed(1)} degrees ${TEMP_UNIT==="F"?"Fahrenheit":"Celsius"}, elevation ${Math.round(elevationM)} metres. Click to change units.`);
}
$("#climateReadout").onclick=()=>{
  TEMP_UNIT=TEMP_UNIT==="C"?"F":"C";
  try{localStorage.setItem("terrainStudioTempUnit",TEMP_UNIT);}catch(_){}
  syncClimateReadout();
};
const cameraNear=()=>clamp(cam.dist*.018,.00018,.045);       // deep inspection without slicing the surface
function ensureGBuffer(){                                    // offscreen colour + depth textures, resized to the canvas
  const w=glc.width,h=glc.height;if(gbuf&&gbuf.w===w&&gbuf.h===h)return;
  if(gbuf){gl.deleteFramebuffer(gbuf.fbo);gl.deleteFramebuffer(gbuf.waterFbo);gl.deleteTexture(gbuf.color);gl.deleteTexture(gbuf.depth);
    gl.deleteTexture(gbuf.waterMask);gl.deleteTexture(gbuf.waterDepth);}
  const color=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,color);
  gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA8,w,h,0,gl.RGBA,gl.UNSIGNED_BYTE,null);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
  const depth=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,depth);
  gl.texImage2D(gl.TEXTURE_2D,0,gl.DEPTH_COMPONENT24,w,h,0,gl.DEPTH_COMPONENT,gl.UNSIGNED_INT,null);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
  const fbo=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,fbo);
  gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,color,0);
  gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.TEXTURE_2D,depth,0);
  if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)USE_DEFERRED=false;
  const waterMask=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,waterMask);
  gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA8,w,h,0,gl.RGBA,gl.UNSIGNED_BYTE,null);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
  const waterDepth=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,waterDepth);
  gl.texImage2D(gl.TEXTURE_2D,0,gl.DEPTH_COMPONENT24,w,h,0,gl.DEPTH_COMPONENT,gl.UNSIGNED_INT,null);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
  const waterFbo=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,waterFbo);
  gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,waterMask,0);
  gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.TEXTURE_2D,waterDepth,0);
  if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)USE_DEFERRED=false;
  gl.bindFramebuffer(gl.FRAMEBUFFER,null);gbuf={fbo,color,depth,waterFbo,waterMask,waterDepth,w,h};
}
function mat4inv(m){
  const a00=m[0],a01=m[1],a02=m[2],a03=m[3],a10=m[4],a11=m[5],a12=m[6],a13=m[7],a20=m[8],a21=m[9],a22=m[10],a23=m[11],a30=m[12],a31=m[13],a32=m[14],a33=m[15];
  const b00=a00*a11-a01*a10,b01=a00*a12-a02*a10,b02=a00*a13-a03*a10,b03=a01*a12-a02*a11,b04=a01*a13-a03*a11,b05=a02*a13-a03*a12,
        b06=a20*a31-a21*a30,b07=a20*a32-a22*a30,b08=a20*a33-a23*a30,b09=a21*a32-a22*a31,b10=a21*a33-a23*a31,b11=a22*a33-a23*a32;
  let det=b00*b11-b01*b10+b02*b09+b03*b08-b04*b07+b05*b06;if(!det)return identity();det=1/det;
  return new Float32Array([(a11*b11-a12*b10+a13*b09)*det,(a02*b10-a01*b11-a03*b09)*det,(a31*b05-a32*b04+a33*b03)*det,(a22*b04-a21*b05-a23*b03)*det,
    (a12*b08-a10*b11-a13*b07)*det,(a00*b11-a02*b08+a03*b07)*det,(a32*b02-a30*b05-a33*b01)*det,(a20*b05-a22*b02+a23*b01)*det,
    (a10*b10-a11*b08+a13*b06)*det,(a01*b08-a00*b10-a03*b06)*det,(a30*b04-a31*b02+a33*b00)*det,(a21*b02-a20*b04-a23*b00)*det,
    (a11*b07-a10*b09-a12*b06)*det,(a00*b09-a01*b07+a02*b06)*det,(a31*b01-a30*b03-a32*b00)*det,(a20*b03-a21*b01+a22*b00)*det]);
}
function drawTerrain(MVP,M,ex,ey,ez,deferred){
  gl.enable(gl.DEPTH_TEST);gl.depthMask(true);gl.disable(gl.BLEND);
  gl.useProgram(terrainProg);setM(terrainProg,"uMVP",MVP);setM(terrainProg,"uM",M);
  {const sd=sunDir();gl.uniform3f(u(terrainProg,"uSun"),sd[0],sd[1],sd[2]);}gl.uniform3f(u(terrainProg,"uCam"),ex,ey,ez);
  gl.uniform1i(u(terrainProg,"uShade"),shadeMode);
  gl.uniform1f(u(terrainProg,"uExposure"),renderLook.exposure);
  gl.uniform1i(u(terrainProg,"uDeferred"),deferred?1:0);
  gl.uniform2f(u(terrainProg,"uRange"),satUniform.lo,satUniform.hi);gl.uniform1f(u(terrainProg,"uShift"),satUniform.shift);gl.uniform1f(u(terrainProg,"uReverse"),satUniform.reverse);
  gl.uniform1i(u(terrainProg,"uSatComposite"),satComposite);
  gl.activeTexture(gl.TEXTURE3);gl.bindTexture(gl.TEXTURE_2D,satTex);gl.uniform1i(u(terrainProg,"uSat"),3);
  bindAttr(terrainProg,"pos",3,buffers.pos);bindAttr(terrainProg,"nrm",3,buffers.nrm);bindAttr(terrainProg,"hgt",1,buffers.hgt);bindAttr(terrainProg,"drive",1,buffers.drive);bindAttr(terrainProg,"snow",1,buffers.snow);
  bindAttr(terrainProg,"temperature",1,buffers.temperature);bindAttr(terrainProg,"sunvis",1,buffers.sunvis);bindAttr(terrainProg,"col",3,buffers.col);
  if(wire){
    // Real mesh edges from the deduplicated edge buffer (built lazily on first wireframe use).
    if(!buffers.lineReady||buffers.lineLattice!==(terrainDef.lattice||"square"))buildWireIndex();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,buffers.lineIdx);
    gl.drawElements(gl.LINES,buffers.lineCount,buffers.u32?gl.UNSIGNED_INT:gl.UNSIGNED_SHORT,0);
  }else{
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,buffers.idx);
    gl.drawElements(gl.TRIANGLES,buffers.count,buffers.u32?gl.UNSIGNED_INT:gl.UNSIGNED_SHORT,0);
  }
}
function drawWaterDepth(MVP,ex,ey,ez){
  if(!scene.water||!waterMaskProg)return;
  gl.enable(gl.DEPTH_TEST);gl.depthMask(true);gl.disable(gl.BLEND);gl.useProgram(waterMaskProg);
  setM(waterMaskProg,"uMVP",MVP);gl.uniform1f(u(waterMaskProg,"uH"),H_SCALE);gl.uniform1f(u(waterMaskProg,"uScale"),terrainDef.scale);
  gl.uniform1f(u(waterMaskProg,"uTime"),uTime);   // the SAME clock the forward pass uses — ADR-006 requires one time
  gl.uniform3f(u(waterMaskProg,"uCam"),ex,ey,ez);gl.uniform1f(u(waterMaskProg,"uMppK"),mppPerUnitDistance());
  gl.uniform1f(u(waterMaskProg,"uTerrainHeight"),terrainDef.height);gl.uniform1f(u(waterMaskProg,"uShoalRefM"),shoalReferenceM());
  gl.uniform1f(u(waterMaskProg,"uWaveAmp"),scene.water?((waterLook.waveDisplacement==null?1:waterLook.waveDisplacement)*(waterLook.amplitudeM==null?1.2:waterLook.amplitudeM)):0);
  bindAttr(waterMaskProg,"axz",2,buffers.gridXZ);bindAttr(waterMaskProg,"ah",1,buffers.hgt);bindAttr(waterMaskProg,"aw",1,buffers.wsurf);bindAttr(waterMaskProg,"ais",1,buffers.iceSnow);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,buffers.idx);
  gl.drawElements(gl.TRIANGLES,buffers.count,buffers.u32?gl.UNSIGNED_INT:gl.UNSIGNED_SHORT,0);
}
function shoalReferenceM(){
  // The depth at which a wave starts to feel the bottom is HALF ITS WAVELENGTH, not some multiple
  // of its height. Referencing it to amplitude was wrong and the curve showed it: with ref = 2*A the
  // breaking limit bound before the Green's-law gain could raise anything, so the wave never grew --
  // it only ever got clipped. Taking half the longest wavelength in the preset gives ~95 m for ocean
  // swell, and the swell then rears up through tens of metres of water the way it should.
  const p=currentWaterPreset();
  let longest=0;
  for(const t of (p&&p.terms)||[]) if(t.lambda>longest) longest=t.lambda;
  return Math.max(4, longest*0.5);
}
function mppPerUnitDistance(){
  // The fade needs metres per pixel, and only the JS side knows the projection. Deriving it
  // here rather than in each shader keeps one definition, and keeps the two passes fading
  // identically -- a mask that faded differently from the colour pass would reintroduce
  // exactly the crest-hairline the single-source rule exists to prevent.
  const fov=Number.isFinite(cam.fov)?cam.fov:1.05, h=(glc&&glc.height)||1;
  return terrainDef.scale*2*Math.tan(fov/2)/h;
}
function renderGL(){
  if(!gl){return;}
  resizeGL();keepCameraAboveSurface();syncCompass();syncWindReadout();syncClimateReadout();
  const asp=glc.width/glc.height||1,near=cameraNear(),fov=Number.isFinite(cam.fov)?cam.fov:1.05,P=perspective(fov,asp,near,20);
  const eye=cameraEye(),ex=eye[0],ey=eye[1],ez=eye[2];
  const waterRipple=scene.water?waterLook.strength:0;
  const waterRippleScale=waterLook.scale;
  const waterRippleSpeed=waterLook.speed;
  const waterRefraction=scene.water?waterLook.refraction:0;
  const waterShoreSmooth=scene.water?(scene.water.shoreSmooth==null?1.35:scene.water.shoreSmooth):0;
  const waterFoam=scene.water?(scene.water.foam==null?.18:scene.water.foam):0;
  const waterPattern=scene.water?({cross:0,wind:1,rings:2,none:3}[waterLook.pattern]??1):3;
  const snowEffect=scene.snow||null;
  const snowfall=snowEffect?(snowEffect.snowfall==null?6*(snowEffect.amount==null?.5:snowEffect.amount):snowEffect.snowfall):0;
  const snowMeltDays=snowEffect?(snowEffect.meltDays==null?45:snowEffect.meltDays):0;
  const snowMeltRate=snowEffect?(snowEffect.meltRate==null?10:snowEffect.meltRate):0;
  const V=lookAt(eye,cam.target,[0,1,0]);const M=identity();const MVP=mat4mul(P,mat4mul(V,M));
  if(USE_DEFERRED&&!wire){
    ensureGBuffer();
    // PASS 1: terrain -> offscreen colour + depth
    gl.bindFramebuffer(gl.FRAMEBUFFER,gbuf.fbo);gl.viewport(0,0,glc.width,glc.height);
    gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
    drawTerrain(MVP,M,ex,ey,ez,true);
    // PASS 1.5: copy terrain depth, then rasterise the nearer fluid plane into a distinct surface layer.
    gl.bindFramebuffer(gl.READ_FRAMEBUFFER,gbuf.fbo);gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER,gbuf.waterFbo);
    gl.blitFramebuffer(0,0,glc.width,glc.height,0,0,glc.width,glc.height,gl.DEPTH_BUFFER_BIT,gl.NEAREST);
    gl.bindFramebuffer(gl.FRAMEBUFFER,gbuf.waterFbo);gl.viewport(0,0,glc.width,glc.height);
    gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);drawWaterDepth(MVP,ex,ey,ez);
    // PASS 2: fullscreen triangle -> screen (sky + water-surface refraction)
    gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.viewport(0,0,glc.width,glc.height);
    gl.disable(gl.DEPTH_TEST);gl.disable(gl.BLEND);
    gl.useProgram(compProg);setM(compProg,"uInvMVP",mat4inv(MVP));
    {const sd=sunDir();gl.uniform3f(u(compProg,"uSun"),sd[0],sd[1],sd[2]);}gl.uniform3f(u(compProg,"uCam"),ex,ey,ez);gl.uniform1f(u(compProg,"uMppK"),mppPerUnitDistance());gl.uniform1f(u(compProg,"uScale"),terrainDef.scale);
    gl.uniform1i(u(compProg,"uStyle"),shadeMode);gl.uniform1f(u(compProg,"uExposure"),renderLook.exposure);gl.uniform1f(u(compProg,"uHaze"),renderLook.haze);
    gl.uniform1f(u(compProg,"uH"),H_SCALE);gl.uniform1f(u(compProg,"uTime"),uTime);
    gl.uniform1f(u(compProg,"uRipple"),waterRipple);gl.uniform1f(u(compProg,"uRippleScale"),waterRippleScale);gl.uniform1f(u(compProg,"uRippleSpeed"),waterRippleSpeed);
    gl.uniform1f(u(compProg,"uRefraction"),waterRefraction);
    gl.uniform1f(u(compProg,"uToon"),waterLook.style==="toon"?1:0);gl.uniform1f(u(compProg,"uBandSteps"),Math.max(2,waterLook.bandSteps||5));
    gl.uniform1f(u(compProg,"uShoreSmooth"),waterShoreSmooth);gl.uniform1f(u(compProg,"uFoam"),waterFoam);gl.uniform1i(u(compProg,"uPattern"),waterPattern);
    gl.uniform1f(u(compProg,"uTerrainHeight"),terrainDef.height);gl.uniform1f(u(compProg,"uSeaTemp"),terrainDef.seaTemp);gl.uniform1f(u(compProg,"uLapseRate"),terrainDef.lapseRate);
    gl.uniform1f(u(compProg,"uSnowfall"),snowfall);gl.uniform1f(u(compProg,"uSnowMeltDays"),snowMeltDays);gl.uniform1f(u(compProg,"uSnowMeltRate"),snowMeltRate);gl.uniform1f(u(compProg,"uHasSnow"),snowEffect?1:0);
    gl.uniform1f(u(compProg,"uSeaLevel"),0.0);gl.uniform1f(u(compProg,"uHasSea"),0.0);  // sea is baked into the water-height texture (W)
    gl.uniform1f(u(compProg,"uWScale"),H_SCALE*RES*0.5);gl.uniform1f(u(compProg,"uWpx"),1/RES);gl.uniform1f(u(compProg,"uRES"),RES);
    // 1.0 on square, so worldUV/latTap stay bit-for-bit the original bilinear there.
    gl.uniform1f(u(compProg,"uRowScale"),isHex()?HEX_ROW:1);
    // Texture addressing needs BOTH dimensions once a hex field is n x round(n*2/sqrt(3)).
    // uZScale converts device z to v and is exactly 0.5 on square, so that path is untouched.
    {const _n=fieldW(),_nh=fieldH(),_rz=isHex()?HEX_ROW:1,_xH=(_n-1)/2,_zH=(_nh-1)*_rz/2;
     gl.uniform1f(u(compProg,"uROWS"),_nh);
     gl.uniform1f(u(compProg,"uHpx"),1/_nh);
     gl.uniform1f(u(compProg,"uZScale"),_zH>0?_xH/(2*_zH):0.5);}
    gl.uniform2f(u(compProg,"uPx"),1/glc.width,1/glc.height);
    gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,gbuf.color);gl.uniform1i(u(compProg,"gColor"),0);
    gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,gbuf.depth);gl.uniform1i(u(compProg,"gDepth"),1);
    gl.activeTexture(gl.TEXTURE2);gl.bindTexture(gl.TEXTURE_2D,wTex);gl.uniform1i(u(compProg,"gW"),2);
    gl.activeTexture(gl.TEXTURE3);gl.bindTexture(gl.TEXTURE_2D,hTex);gl.uniform1i(u(compProg,"gH"),3);
    gl.activeTexture(gl.TEXTURE4);gl.bindTexture(gl.TEXTURE_2D,gbuf.waterMask);gl.uniform1i(u(compProg,"gWaterMask"),4);
    gl.activeTexture(gl.TEXTURE5);gl.bindTexture(gl.TEXTURE_2D,gbuf.waterDepth);gl.uniform1i(u(compProg,"gWaterDepth"),5);
    gl.activeTexture(gl.TEXTURE6);gl.bindTexture(gl.TEXTURE_2D,iTex);gl.uniform1i(u(compProg,"gIce"),6);
    gl.activeTexture(gl.TEXTURE7);gl.bindTexture(gl.TEXTURE_2D,isTex);gl.uniform1i(u(compProg,"gIceSnow"),7);
    gl.drawArrays(gl.TRIANGLES,0,3);
    gl.enable(gl.DEPTH_TEST);
  }else{
    // FORWARD fallback (WebGL1 / wireframe): terrain + translucent geometry water
    gl.viewport(0,0,glc.width,glc.height);gl.clearColor(...hex3(css("--bg2")),1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
    drawTerrain(MVP,M,ex,ey,ez);
    if(scene.water&&!wire){
      gl.useProgram(waterProg);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false);
      setM(waterProg,"uMVP",MVP);gl.uniform1f(u(waterProg,"uH"),H_SCALE);gl.uniform1f(u(waterProg,"uScale"),terrainDef.scale);gl.uniform1f(u(waterProg,"uTime"),uTime);
      gl.uniform1f(u(waterProg,"uWaveAmp"),scene.water?((waterLook.waveDisplacement==null?1:waterLook.waveDisplacement)*(waterLook.amplitudeM==null?1.2:waterLook.amplitudeM)):0);
      gl.uniform1f(u(waterProg,"uTerrainHeight"),terrainDef.height);gl.uniform1f(u(waterProg,"uSeaTemp"),terrainDef.seaTemp);gl.uniform1f(u(waterProg,"uLapseRate"),terrainDef.lapseRate);
      gl.uniform1f(u(waterProg,"uRipple"),waterRipple);gl.uniform1f(u(waterProg,"uRippleScale"),waterRippleScale);gl.uniform1f(u(waterProg,"uRippleSpeed"),waterRippleSpeed);
      gl.uniform1f(u(waterProg,"uToon"),waterLook.style==="toon"?1:0);gl.uniform1f(u(waterProg,"uBandSteps"),Math.max(2,waterLook.bandSteps||5));
      gl.uniform1f(u(waterProg,"uShoreSmooth"),waterShoreSmooth);gl.uniform1f(u(waterProg,"uFoam"),waterFoam);gl.uniform1i(u(waterProg,"uPattern"),waterPattern);
      gl.uniform3f(u(waterProg,"uSun"),0.5,0.8,0.35);gl.uniform3f(u(waterProg,"uCam"),ex,ey,ez);gl.uniform1f(u(waterProg,"uMppK"),mppPerUnitDistance());gl.uniform1f(u(waterProg,"uShoalRefM"),shoalReferenceM());
      bindAttr(waterProg,"axz",2,buffers.gridXZ);bindAttr(waterProg,"ah",1,buffers.hgt);
      bindAttr(waterProg,"aw",1,buffers.wsurf);bindAttr(waterProg,"ais",1,buffers.iceSnow);bindAttr(waterProg,"aice",1,buffers.ice);
      bindAttr(waterProg,"awn",3,buffers.wnrm);bindAttr(waterProg,"asnowN",3,buffers.iceSnowNrm);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,buffers.idx);
      gl.drawElements(gl.TRIANGLES,buffers.count,buffers.u32?gl.UNSIGNED_INT:gl.UNSIGNED_SHORT,0);
      gl.depthMask(true);gl.disable(gl.BLEND);
    }
  }
  if(!REDUCED)uTime+=0.016;
  requestAnimationFrame(renderGL);
  return fov;
}
function identity(){return new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);}
function setM(p,name,m){gl.uniformMatrix4fv(u(p,name),false,m);}
function bindAttr(p,name,size,buf){const l=gl.getAttribLocation(p,name);if(l<0)return;gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.enableVertexAttribArray(l);gl.vertexAttribPointer(l,size,gl.FLOAT,false,0,0);}
function hex3(h){h=h.replace("#","");if(h.length===3)h=h.split("").map(c=>c+c).join("");return[parseInt(h.slice(0,2),16)/255,parseInt(h.slice(2,4),16)/255,parseInt(h.slice(4,6),16)/255];}

/* =====================================================================
   UI WIRING
   ===================================================================== */
function setStat(kind,msg){$("#statMsg").textContent=msg;$("#statDot").style.background=kind==="ok"?css("--good"):kind==="warn"?css("--warn"):css("--bad");}
let toastT;function toast(m){const t=$("#toast");t.textContent=m;t.classList.add("show");clearTimeout(toastT);toastT=setTimeout(()=>t.classList.remove("show"),1900);}

/* =====================================================================
   DRAW MASK EDITOR
   Strokes are authored in normalized terrain coordinates, not viewport
   pixels. The canvas is only a plan-view editor for the graph-native mask.
   ===================================================================== */
let drawTarget=null,drawActive=null,drawBefore=null;
const drawBrush={mode:"add",width:.04,hardness:.7,opacity:1};
const drawCanvas=$("#drawCanvas"),drawCtx=drawCanvas.getContext("2d"),drawOverlay=document.createElement("canvas"),drawBase=document.createElement("canvas"),drawTint=document.createElement("canvas");
drawOverlay.width=drawBase.width=drawTint.width=drawCanvas.width;drawOverlay.height=drawBase.height=drawTint.height=drawCanvas.height;
let drawBaseField=null,drawBaseResolution=0;
function drawReferenceField(){
  if(!drawTarget)return null;
  return drawTarget._reference||curField||(outputNode()&&outputNode()._field)||null;
}
function paintStroke2D(ctx,stroke){
  const pts=stroke.points||[];if(!pts.length)return;
  const W=ctx.canvas.width,H=ctx.canvas.height,width=Math.max(1,(stroke.width||.04)*W);
  const hard=clamp(stroke.hardness==null?.7:stroke.hardness,0,1),op=clamp(stroke.opacity==null?1:stroke.opacity,0,1);
  ctx.save();ctx.globalCompositeOperation=stroke.mode==="erase"?"destination-out":"source-over";
  ctx.lineCap="round";ctx.lineJoin="round";ctx.strokeStyle="white";ctx.fillStyle="white";
  const path=()=>{
    ctx.beginPath();ctx.moveTo(pts[0][0]*W,pts[0][1]*H);
    for(let i=1;i<pts.length;i++)ctx.lineTo(pts[i][0]*W,pts[i][1]*H);
    if(pts.length===1){ctx.arc(pts[0][0]*W,pts[0][1]*H,.01,0,Math.PI*2);ctx.fill();}else ctx.stroke();
  };
  // Layered preview approximates the evaluator's smooth radial falloff while staying responsive.
  if(hard<.99){ctx.globalAlpha=op*(.14+.22*hard);ctx.lineWidth=width;path();}
  ctx.globalAlpha=op;ctx.lineWidth=Math.max(1,width*Math.max(hard,.08));path();ctx.restore();
}
function renderDrawEditor(){
  if(!drawTarget||$("#drawEditor").hidden)return;
  const W=drawCanvas.width,H=drawCanvas.height,base=drawReferenceField();
  if(drawBaseField!==base||drawBaseResolution!==RES){
    const bx=drawBase.getContext("2d"),img=bx.createImageData(W,H),n=RES;
    let mn=0,mx=1;if(base&&base.length){const r=fieldRange(base);mn=r[0];mx=r[1];}
    const d=mx-mn||1;
    for(let y=0;y<H;y++)for(let x=0;x<W;x++){
      const sx=Math.min(n-1,Math.floor(x/W*n)),sy=Math.min(n-1,Math.floor(y/H*n)),i=(y*W+x)*4;
      const h=base&&base.length?(base[sy*n+sx]-mn)/d:0;
      const hx=base&&base.length?(base[sy*n+Math.min(n-1,sx+1)]-base[sy*n+Math.max(0,sx-1)])/d:0;
      const hy=base&&base.length?(base[Math.min(latticeRows(n)-1,sy+1)*n+sx]-base[Math.max(0,sy-1)*n+sx])/d:0;
      const shade=clamp(.22+h*.66+(hx+hy)*2.8,0,1),v=Math.round(shade*255);
      img.data[i]=Math.round(v*.88);img.data[i+1]=Math.round(v*.94);img.data[i+2]=v;img.data[i+3]=255;
    }
    bx.putImageData(img,0,0);drawBaseField=base;drawBaseResolution=RES;
  }
  drawCtx.clearRect(0,0,W,H);drawCtx.drawImage(drawBase,0,0);
  const ox=drawOverlay.getContext("2d");ox.clearRect(0,0,W,H);
  (drawTarget.params.strokes||[]).forEach(s=>paintStroke2D(ox,s));
  const mask=ox.getImageData(0,0,W,H),tx=drawTint.getContext("2d"),tint=tx.createImageData(W,H);
  for(let i=0;i<mask.data.length;i+=4){const a=mask.data[i+3];tint.data[i]=28;tint.data[i+1]=210;tint.data[i+2]=230;tint.data[i+3]=Math.round(a*.72);}
  tx.clearRect(0,0,W,H);tx.putImageData(tint,0,0);drawCtx.drawImage(drawTint,0,0);
  const count=(drawTarget.params.strokes||[]).length;$("#drawStrokeCount").textContent=count+" stroke"+(count===1?"":"s");
  $("#drawUndoStroke").disabled=!count;$("#drawClear").disabled=!count;
}
function syncDrawBrush(){
  $("#drawWidth").value=drawBrush.width;$("#drawHardness").value=drawBrush.hardness;$("#drawOpacity").value=drawBrush.opacity;
  $("#drawWidthVal").textContent=(drawBrush.width*100).toFixed(1)+"%";
  $("#drawHardnessVal").textContent=Math.round(drawBrush.hardness*100)+"%";
  $("#drawOpacityVal").textContent=Math.round(drawBrush.opacity*100)+"%";
  document.querySelectorAll("#drawMode button").forEach(b=>{const on=b.dataset.v===drawBrush.mode;b.classList.toggle("on",on);b.setAttribute("aria-selected",on);});
}
function openDrawEditor(nd){
  if(!nd||nd.type!=="drawmask")return;drawTarget=nd;
  if(!Array.isArray(nd.params.strokes))nd.params.strokes=[];
  drawBaseField=null;$("#drawEditor").hidden=false;syncDrawBrush();renderDrawEditor();$("#drawDone").focus();
}
function closeDrawEditor(){
  if($("#drawEditor").hidden)return;$("#drawEditor").hidden=true;drawActive=null;drawBefore=null;
  const nd=drawTarget;drawTarget=null;if(nd&&selected===nd)buildProps();
}
function drawPointFromEvent(e){
  const r=drawCanvas.getBoundingClientRect();
  return[clamp((e.clientX-r.left)/r.width,0,1),clamp((e.clientY-r.top)/r.height,0,1)];
}
drawCanvas.onpointerdown=e=>{
  if(!drawTarget||e.button!==0)return;e.preventDefault();drawCanvas.setPointerCapture(e.pointerId);
  drawBefore=graphSnapshot();drawActive={mode:drawBrush.mode,width:drawBrush.width,hardness:drawBrush.hardness,
    opacity:drawBrush.opacity,points:[drawPointFromEvent(e)]};
  drawTarget.params.strokes.push(drawActive);renderDrawEditor();
};
drawCanvas.onpointermove=e=>{
  if(!drawActive)return;const p=drawPointFromEvent(e),last=drawActive.points[drawActive.points.length-1];
  if(Math.hypot(p[0]-last[0],p[1]-last[1])<.0015)return;drawActive.points.push(p);renderDrawEditor();
};
function finishDrawStroke(e){
  if(!drawActive)return;if(drawCanvas.hasPointerCapture(e.pointerId))drawCanvas.releasePointerCapture(e.pointerId);
  pushUndo(drawBefore);drawBefore=null;drawActive=null;markDirtyFrom(drawTarget.id);requestEval();drawGraph();renderDrawEditor();
}
drawCanvas.onpointerup=finishDrawStroke;drawCanvas.onpointercancel=finishDrawStroke;
$("#drawMode").onclick=e=>{const b=e.target.closest("button[data-v]");if(!b)return;drawBrush.mode=b.dataset.v;syncDrawBrush();};
$("#drawWidth").oninput=e=>{drawBrush.width=+e.target.value;syncDrawBrush();};
$("#drawHardness").oninput=e=>{drawBrush.hardness=+e.target.value;syncDrawBrush();};
$("#drawOpacity").oninput=e=>{drawBrush.opacity=+e.target.value;syncDrawBrush();};
$("#drawUndoStroke").onclick=()=>{
  if(!drawTarget||!drawTarget.params.strokes.length)return;recordHistory();drawTarget.params.strokes.pop();
  markDirtyFrom(drawTarget.id);requestEval();drawGraph();renderDrawEditor();
};
$("#drawClear").onclick=()=>{
  if(!drawTarget||!drawTarget.params.strokes.length)return;recordHistory();drawTarget.params.strokes=[];
  markDirtyFrom(drawTarget.id);requestEval();drawGraph();renderDrawEditor();
};
$("#drawDone").onclick=closeDrawEditor;$("#drawCancel").onclick=closeDrawEditor;
$("#drawEditor").onpointerdown=e=>{if(e.target===$("#drawEditor"))closeDrawEditor();};

/* =====================================================================
   PATH WAYPOINT EDITOR
   Click to append an ordered top-down point, drag an existing one to move it.
   Points are the same "x,y per line" text the node's Waypoints field parses,
   so typing and drawing are two views of one source of truth.
   ===================================================================== */
let pathTarget=null,pathDragIndex=-1,pathBefore=null;
const pathCanvas=$("#pathCanvas"),pathCtx=pathCanvas.getContext("2d"),pathBaseCanvas=document.createElement("canvas");
pathBaseCanvas.width=pathCanvas.width;pathBaseCanvas.height=pathCanvas.height;
let pathBaseField=null,pathBaseResolution=0;
function parsePathPoints(text){
  const pts=[];
  for(const raw of String(text||"").split("\n")){
    const line=raw.trim();if(!line||line[0]==="#")continue;
    const a=line.split(",").map(Number);
    if(a.length>=2&&a.every(isFinite))pts.push([clamp(a[0],0,1),clamp(a[1],0,1)]);
  }
  return pts;
}
const pathPointsToText=pts=>pts.map(p=>p[0].toFixed(4)+","+p[1].toFixed(4)).join("\n");
function renderPathEditor(){
  if(!pathTarget||$("#pathEditor").hidden)return;
  const W=pathCanvas.width,H=pathCanvas.height,base=curField;
  if(pathBaseField!==base||pathBaseResolution!==RES){
    const bx=pathBaseCanvas.getContext("2d"),img=bx.createImageData(W,H),n=RES;
    let mn=0,mx=1;if(base&&base.length){const r=fieldRange(base);mn=r[0];mx=r[1];}
    const d=mx-mn||1;
    for(let y=0;y<H;y++)for(let x=0;x<W;x++){
      const sx=Math.min(n-1,Math.floor(x/W*n)),sy=Math.min(n-1,Math.floor(y/H*n)),i=(y*W+x)*4;
      const h=base&&base.length?(base[sy*n+sx]-mn)/d:0;
      const hx=base&&base.length?(base[sy*n+Math.min(n-1,sx+1)]-base[sy*n+Math.max(0,sx-1)])/d:0;
      const hy=base&&base.length?(base[Math.min(latticeRows(n)-1,sy+1)*n+sx]-base[Math.max(0,sy-1)*n+sx])/d:0;
      const shade=clamp(.22+h*.66+(hx+hy)*2.8,0,1),v=Math.round(shade*255);
      img.data[i]=Math.round(v*.88);img.data[i+1]=Math.round(v*.94);img.data[i+2]=v;img.data[i+3]=255;
    }
    bx.putImageData(img,0,0);pathBaseField=base;pathBaseResolution=RES;
  }
  pathCtx.clearRect(0,0,W,H);pathCtx.drawImage(pathBaseCanvas,0,0);
  const pts=parsePathPoints(pathTarget.params.waypoints);
  if(pts.length){
    pathCtx.save();pathCtx.strokeStyle="#3cd2e6";pathCtx.lineWidth=2.5;pathCtx.lineJoin="round";
    pathCtx.beginPath();pathCtx.moveTo(pts[0][0]*W,pts[0][1]*H);
    for(let i=1;i<pts.length;i++)pathCtx.lineTo(pts[i][0]*W,pts[i][1]*H);
    pathCtx.stroke();pathCtx.restore();
    pts.forEach((p,i)=>{
      const x=p[0]*W,y=p[1]*H;
      pathCtx.beginPath();pathCtx.arc(x,y,7,0,Math.PI*2);
      pathCtx.fillStyle=i===0?"#5be86b":i===pts.length-1?"#e65b5b":"#1c2733";pathCtx.fill();
      pathCtx.lineWidth=1.5;pathCtx.strokeStyle="#eaf2fa";pathCtx.stroke();
      pathCtx.fillStyle="#eaf2fa";pathCtx.font="10px var(--mono, monospace)";pathCtx.textAlign="center";pathCtx.textBaseline="middle";
      pathCtx.fillText(String(i+1),x,y);
    });
  }
  $("#pathPointCount").textContent=pts.length+" point"+(pts.length===1?"":"s");
  $("#pathUndoPoint").disabled=!pts.length;$("#pathClear").disabled=!pts.length;
}
function setPathPoints(pts){pathTarget.params.waypoints=pathPointsToText(pts);}
function openPathEditor(nd){
  if(!nd||nd.type!=="canyon")return;pathTarget=nd;pathBaseField=null;
  $("#pathEditor").hidden=false;renderPathEditor();$("#pathDone").focus();
}
function closePathEditor(){
  if($("#pathEditor").hidden)return;$("#pathEditor").hidden=true;pathDragIndex=-1;pathBefore=null;
  const nd=pathTarget;pathTarget=null;if(nd&&selected===nd)buildProps();
}
function pathPointFromEvent(e){
  const r=pathCanvas.getBoundingClientRect();
  return[clamp((e.clientX-r.left)/r.width,0,1),clamp((e.clientY-r.top)/r.height,0,1)];
}
function pathHitTest(pts,p){
  let best=-1,bd=9/pathCanvas.getBoundingClientRect().width;
  pts.forEach((q,i)=>{const d=Math.hypot(q[0]-p[0],q[1]-p[1]);if(d<bd){bd=d;best=i;}});
  return best;
}
pathCanvas.onpointerdown=e=>{
  if(!pathTarget||e.button!==0)return;e.preventDefault();pathCanvas.setPointerCapture(e.pointerId);
  const pts=parsePathPoints(pathTarget.params.waypoints),p=pathPointFromEvent(e);
  pathBefore=graphSnapshot();
  const hit=pathHitTest(pts,p);
  if(hit>=0)pathDragIndex=hit;else{pts.push(p);setPathPoints(pts);pathDragIndex=pts.length-1;}
  renderPathEditor();
};
pathCanvas.onpointermove=e=>{
  if(pathDragIndex<0||!pathTarget)return;
  const pts=parsePathPoints(pathTarget.params.waypoints);pts[pathDragIndex]=pathPointFromEvent(e);
  setPathPoints(pts);renderPathEditor();
};
function finishPathEdit(e){
  if(pathDragIndex<0)return;
  if(pathCanvas.hasPointerCapture(e.pointerId))pathCanvas.releasePointerCapture(e.pointerId);
  pushUndo(pathBefore);pathBefore=null;pathDragIndex=-1;markDirtyFrom(pathTarget.id);requestEval();drawGraph();renderPathEditor();
}
pathCanvas.onpointerup=finishPathEdit;pathCanvas.onpointercancel=finishPathEdit;
$("#pathUndoPoint").onclick=()=>{
  if(!pathTarget)return;const pts=parsePathPoints(pathTarget.params.waypoints);if(!pts.length)return;
  recordHistory();pts.pop();setPathPoints(pts);markDirtyFrom(pathTarget.id);requestEval();drawGraph();renderPathEditor();
};
$("#pathClear").onclick=()=>{
  if(!pathTarget)return;const pts=parsePathPoints(pathTarget.params.waypoints);if(!pts.length)return;
  recordHistory();setPathPoints([]);markDirtyFrom(pathTarget.id);requestEval();drawGraph();renderPathEditor();
};
$("#pathDone").onclick=closePathEditor;$("#pathCancel").onclick=closePathEditor;
$("#pathEditor").onpointerdown=e=>{if(e.target===$("#pathEditor"))closePathEditor();};
const editorMenuPanels=["fileMenu","editMenu","viewMenu","helpMenu","mainMenu"];
const editorMenuButtons={fileMenu:"fileMenuBtn",editMenu:"editMenuBtn",viewMenu:"viewMenuBtn",helpMenu:"helpMenuBtn",mainMenu:"mainMenuBtn"};
let lastEditorMenuButton=null;
function closeEditorMenus(){
  editorMenuPanels.forEach(id=>{$("#"+id).hidden=true;$("#"+editorMenuButtons[id]).setAttribute("aria-expanded","false");});
  document.querySelectorAll(".compact-menu-section").forEach(b=>{b.setAttribute("aria-expanded","false");$("#"+b.dataset.compactSection).hidden=true;});
}
function setEditorMenu(id,force){
  const panel=$("#"+id),open=force===undefined?panel.hidden:!!force;closeEditorMenus();
  if(open){
    closeTopPopovers();panel.hidden=false;$("#"+editorMenuButtons[id]).setAttribute("aria-expanded","true");
    lastEditorMenuButton=$("#"+editorMenuButtons[id]);
  }
}
function syncEditorCommandState(){
  const hasNode=!!selected&&!selectedEdge,hasSelection=!!selectedEdge||!!selected;
  document.querySelectorAll('[data-editor-command="duplicate"]').forEach(b=>b.disabled=!hasNode);
  document.querySelectorAll('[data-editor-command="delete"]').forEach(b=>b.disabled=!hasSelection);
  const stacked=$("#main").classList.contains("stacked");
  document.querySelectorAll('[data-editor-command="layout-stacked"]').forEach(b=>b.setAttribute("aria-checked",stacked?"true":"false"));
  document.querySelectorAll('[data-editor-command="layout-side"]').forEach(b=>b.setAttribute("aria-checked",stacked?"false":"true"));
}
const editorCommands={
  new:openNewTerrainDialog,
  "new-default":()=>newTerrainDocument(true),
  "new-canyon":()=>newTerrainDocument(false,"canyon"),
  save:saveProjectFile,open:openProjectFile,
  import:importHeightmap,export:exportHeightmap,undo:undoGraph,redo:redoGraph,
  duplicate:()=>{if(selected&&!selectedEdge)duplicateSel();},
  delete:()=>{if(selectedEdge)deleteEdge(selectedEdge);else if(selected)deleteSel();},
  organize:()=>organizeGraph(null,null,"Organized graph"),
  "layout-stacked":()=>setLayout(true),"layout-side":()=>setLayout(false),
  toolbox:()=>setNodeToolbox(true),frame:frameHero,fullscreen:toggleFullscreen,theme:toggleTheme,
  controls:()=>setViewportPanel("helpPanel"),
  commands:()=>{filterCommands("");$("#commandSearch").value="";setTopPopover("commandMenu",true);},
  about:()=>toast("Terrain Studio · procedural terrain authoring"),
  build:()=>$("#buildBtn").click(),auto:()=>$("#autoBtn").click(),
  "find-water":()=>locateNode("water"),"find-satmap":()=>locateNode("satmap"),"find-output":()=>locateNode("output")
};
function runEditorCommand(id){
  const action=editorCommands[id];if(!action)return false;
  closeEditorMenus();action();syncEditorCommandState();return true;
}
document.querySelectorAll(".editor-menu-trigger").forEach(button=>{
  button.onclick=()=>setEditorMenu(button.getAttribute("aria-controls"));
  button.onmouseenter=()=>{if(editorMenuPanels.slice(0,4).some(id=>!$("#"+id).hidden))setEditorMenu(button.getAttribute("aria-controls"),true);};
});
$("#mainMenuBtn").onclick=()=>setEditorMenu("mainMenu");
$(".editor-menu-shell").addEventListener("click",e=>{
  const section=e.target.closest(".compact-menu-section");
  if(section){const panel=$("#"+section.dataset.compactSection),open=panel.hidden;
    document.querySelectorAll(".compact-menu-section").forEach(b=>{const on=b===section&&open;b.setAttribute("aria-expanded",on?"true":"false");$("#"+b.dataset.compactSection).hidden=!on;});
    return;
  }
  const item=e.target.closest("[data-editor-command]");if(item&&!item.disabled)runEditorCommand(item.dataset.editorCommand);
});
$(".editor-menu-shell").addEventListener("keydown",e=>{
  if(e.key==="Escape"){e.preventDefault();closeEditorMenus();if(lastEditorMenuButton)lastEditorMenuButton.focus();return;}
  if(e.key==="ArrowDown"){
    const trigger=e.target.closest(".editor-menu-trigger");if(trigger){e.preventDefault();const id=trigger.getAttribute("aria-controls");setEditorMenu(id,true);
      requestAnimationFrame(()=>$("#"+id).querySelector(".editor-menu-item:not(:disabled)")?.focus());}
  }
});
const topPopovers=["buildSettings","commandMenu"];
const topPopoverButtons={buildSettings:"buildProfileBtn",commandMenu:"commandBtn"};
function closeTopPopovers(){
  topPopovers.forEach(id=>{$("#"+id).hidden=true;$("#"+topPopoverButtons[id]).setAttribute("aria-expanded","false");});
}
function setTopPopover(id,force){
  const panel=$("#"+id),open=force===undefined?panel.hidden:!!force;
  topPopovers.forEach(pid=>{const on=pid===id&&open;$("#"+pid).hidden=!on;$("#"+topPopoverButtons[pid]).setAttribute("aria-expanded",on?"true":"false");});
  if(open&&id==="commandMenu")requestAnimationFrame(()=>{$("#commandSearch").focus();$("#commandSearch").select();});
}
function syncBuildProfile(){
  $("#profileRes").textContent=TARGET_RES+"²";
  const quality=BUILD_QUALITY==="final"?"Final":"Interactive";
  // Lattice reads off buffers.builtLattice, not terrainDef.lattice: buildIndex() owns that tag,
  // and undo/redo/New/restoreGraph all change the definition WITHOUT going through the toggle,
  // so the built mesh is the honest answer to "which grid am I actually looking at". Hex is
  // called out; square is the default and stays unlabelled to keep the chip short.
  const hexBuilt=!!(buffers&&buffers.builtLattice==="hex"),lattice=hexBuilt?" · Hex":"";
  // The device label must report what compute ACTUALLY runs, not what the button is set to:
  // gpuReady() forces the CPU path on hex (the kernels are square-texture end to end), so a chip
  // reading "GPU" there was simply false.
  const device=(USE_GPU&&!$("#gpuBtn").disabled&&!hexBuilt)?"GPU":"CPU";
  $("#profileDetail").textContent=" · "+quality+" · "+device+lattice+(SCALE_RES?" · Lock":"")+(TARGET_RES!==RES?" · Queued":"");
}
function filterCommands(query){
  const q=(query||"").trim().toLowerCase(),items=[...$("#commandList").querySelectorAll(".command-item")];
  let shown=0;items.forEach(item=>{const match=!q||(item.dataset.command+" "+item.textContent).toLowerCase().includes(q);
    item.classList.toggle("hidden",!match);if(match)shown++;});
  [...$("#commandList").querySelectorAll(".command-group-title")].forEach(title=>{
    let any=false,n=title.nextElementSibling;while(n&&!n.classList.contains("command-group-title")){
      if(n.classList.contains("command-item")&&!n.classList.contains("hidden"))any=true;n=n.nextElementSibling;}
    title.classList.toggle("hidden",!any);
  });
  $("#commandEmpty").classList.toggle("show",shown===0);return shown;
}
function locateNode(type){
  const nd=nearestUpstreamNode(type,outputNode())||nodes.find(n=>n.type===type);
  if(!nd){toast(TYPES[type].name+" is not in this graph");return;}
  select(nd);frameGraph([nd.id]);toast("Located "+TYPES[type].name);
}
$("#buildProfileBtn").onclick=()=>setTopPopover("buildSettings");
$("#commandBtn").onclick=()=>{filterCommands("");$("#commandSearch").value="";setTopPopover("commandMenu");};
$("#commandSearch").oninput=e=>filterCommands(e.target.value);
$("#commandSearch").onkeydown=e=>{
  if(e.key==="Enter"||e.key==="ArrowDown"){
    const first=$("#commandList .command-item:not(.hidden)");if(first){e.preventDefault();first.focus();if(e.key==="Enter")first.click();}
  }
};
const commandActions={
  new:()=>runEditorCommand("new"),"new-default":()=>runEditorCommand("new-default"),
  "new-canyon":()=>runEditorCommand("new-canyon"),
  build:()=>runEditorCommand("build"),auto:()=>runEditorCommand("auto"),import:()=>runEditorCommand("import"),export:()=>runEditorCommand("export"),
  "find-water":()=>runEditorCommand("find-water"),"find-satmap":()=>runEditorCommand("find-satmap"),"find-output":()=>runEditorCommand("find-output"),
  organize:()=>runEditorCommand("organize"),toolbox:()=>runEditorCommand("toolbox"),layout:()=>$("#layoutBtn").click(),
  fullscreen:()=>runEditorCommand("fullscreen")
};
$("#commandList").addEventListener("click",e=>{
  const item=e.target.closest(".command-item");if(!item)return;
  const action=commandActions[item.dataset.action];if(action)action();closeTopPopovers();
});
window.addEventListener("mousedown",e=>{
  if(!e.target.closest(".top-anchor"))closeTopPopovers();
  if(!e.target.closest(".editor-menu-shell"))closeEditorMenus();
});
$("#autoBtn").classList.toggle("on",AUTO);
$("#autoBtn").onclick=()=>{AUTO=!AUTO;$("#autoBtn").classList.toggle("on",AUTO);if(AUTO)evalGraph();toast(AUTO?"Auto-recompute on":"Auto-recompute off — use Build");};
function applyWorkingResolution(next){
  RES=next;nodes.forEach(n=>{n._dirty=true;n._thumb=null;if(n.type==="import")n._dem=null;});
  buildIndex();
}
// PREVIEW DETAIL IS NOT RESOLUTION, and conflating them is what made the old control unreadable.
//
// The document has a sample count — chosen in New Terrain, in the same dialog that states the world
// extent in metres, so the two together fix the sample spacing. That is a physical property of the
// terrain and every erosion parameter is denominated in it. Preview detail is a FRACTION of that
// grid used for a cheaper evaluation, and it changes cost and fidelity and nothing else.
//
// The old absolute selector offered 128..4096 with no reference to the document at all, so choosing
// 1024 on a 512-sample world silently doubled the resolution and halved the spacing — a different
// simulation, presented as a preview setting.
export let DOC_SAMPLES=512;
export let PREVIEW_DETAIL=1;
export function setDocumentSamples(n){DOC_SAMPLES=Math.max(2,Math.round(n));return DOC_SAMPLES;}
export function documentSamples(){return DOC_SAMPLES;}
export function previewDetail(){return PREVIEW_DETAIL;}
/** Resolve preview detail against the document grid. Returns the sample count it selected. */
export function applyPreviewDetail(fraction){
  PREVIEW_DETAIL=Math.min(1,Math.max(0.05,Number(fraction)||1));
  const next=Math.max(2,Math.round(DOC_SAMPLES*PREVIEW_DETAIL));
  TARGET_RES=next;
  // Large grids stay queued for an explicit Build, exactly as the old control did — that behaviour
  // was about cost, not about what the number meant, so it survives unchanged.
  if(next>=1024){if(AUTO){AUTO=false;const b=$("#autoBtn");if(b)b.classList.remove("on");}}
  else if(next!==RES)applyWorkingResolution(next);
  syncDetailReadout();
  return next;
}
/** Say what the setting actually produced: sample count and the resulting spacing in metres. */
export function syncDetailReadout(){
  const el=$("#detailReadout");if(!el)return null;
  const d=getWorldDomain();
  const cols=Math.max(2,Math.round(DOC_SAMPLES*PREVIEW_DETAIL));
  const rows=terrainDef.lattice==="hex"?Math.round(cols*2/Math.sqrt(3)):cols;
  const widthM=(d&&d.extentM&&d.extentM.width)||terrainDef.scale||0;
  // vertex posting spans n-1 intervals; deriveResolution owns the same rule for the create dialog.
  const spacing=cols>1?widthM/(cols-1):0;
  const text=`${cols} × ${rows} samples · ${spacing?spacing.toPrecision(4):"—"} m per sample`
    +(PREVIEW_DETAIL<1?` · ${Math.round(PREVIEW_DETAIL*100)}% of the document's ${DOC_SAMPLES}`:"");
  el.textContent=text;
  return {cols,rows,spacing,detail:PREVIEW_DETAIL,documentSamples:DOC_SAMPLES};
}
$("#buildBtn").onclick=()=>{if(TARGET_RES!==RES)applyWorkingResolution(TARGET_RES);nodes.forEach(n=>n._dirty=true);syncBuildProfile();evalGraphProgressive("Building terrain");};
$("#resSel").onchange=e=>{
  const next=applyPreviewDetail(parseFloat(e.target.value));
  syncBuildProfile();
  if(next>=1024){toast(next+"² queued — Auto off, use Build");return;}
  toast(`Preview detail ${Math.round(previewDetail()*100)}% · ${next}²`);evalGraph();};
// Resizing is an EXPLICIT act, stated in the same terms as creating: extent, sample count, spacing.
// It reuses the New Terrain dialog rather than inventing a second vocabulary for the same numbers.
if($("#resizeBtn"))$("#resizeBtn").onclick=()=>openNewTerrainDialog();
$("#qualitySel").onchange=e=>{BUILD_QUALITY=e.target.value;nodes.forEach(n=>n._dirty=true);
  toast(BUILD_QUALITY==="final"?"Final simulation budgets":"Interactive preview budgets");
  syncBuildProfile();evalGraph();};
// GPU fast path toggle. Generators, thermal erosion, and both square-lattice hydraulic stages run
// as WebGL2 kernels; CPU implementations remain the reference/compatibility path.
$("#gpuBtn").onclick=()=>{
  if(!GPU.init()){toast("GPU compute unavailable (needs WebGL2 + float render targets)");return;}
  USE_GPU=!USE_GPU;$("#gpuBtn").classList.toggle("on",USE_GPU);
  nodes.forEach(n=>n._dirty=true);syncBuildProfile();evalGraph();
  toast(USE_GPU?"GPU fast path on":"CPU reference path");};
setTimeout(()=>{if(GPU.init()){$("#gpuBtn").classList.toggle("on",USE_GPU);}else{USE_GPU=false;$("#gpuBtn").disabled=true;$("#gpuBtn").title="WebGL2 float render targets unavailable";}syncBuildProfile();},0);
// Resolution independence toggle — off means params stay in raw cell units (and a high-res build goes spiky).
$("#scaleBtn").classList.toggle("on",SCALE_RES);
$("#scaleBtn").onclick=()=>{SCALE_RES=!SCALE_RES;$("#scaleBtn").classList.toggle("on",SCALE_RES);
  nodes.forEach(n=>n._dirty=true);syncBuildProfile();evalGraph();
  toast(SCALE_RES?"Res Lock on — params held constant across resolution":"Res Lock off — raw cell-unit params");};
syncBuildProfile();
function toggleTheme(){const cur=document.documentElement.getAttribute("data-theme"),next=cur==="light"?"dark":"light";
  document.documentElement.setAttribute("data-theme",next);drawGraph();nodes.forEach(n=>n._thumb=null);redrawThumbs();}
$("#themeBtn").onclick=toggleTheme;
const viewportPanels=["displayPanel","lookPanel","waterLookPanel","helpPanel"];
const viewportPanelButtons={displayPanel:"displayBtn",lookPanel:"lookBtn",waterLookPanel:"waterLookBtn",helpPanel:"helpBtn"};
function setViewportPanel(id){
  viewportPanels.forEach(pid=>{
    const open=pid===id&&$("#"+pid).hidden;
    $("#"+pid).hidden=!open;$("#"+viewportPanelButtons[pid]).setAttribute("aria-expanded",open?"true":"false");
  });
}
function closeViewportPanels(){
  viewportPanels.forEach(pid=>{$("#"+pid).hidden=true;$("#"+viewportPanelButtons[pid]).setAttribute("aria-expanded","false");});
}
$("#displayBtn").onclick=()=>setViewportPanel("displayPanel");
$("#lookBtn").onclick=()=>setViewportPanel("lookPanel");
$("#waterLookBtn").onclick=()=>setViewportPanel("waterLookPanel");
$("#helpBtn").onclick=()=>setViewportPanel("helpPanel");
window.addEventListener("mousedown",e=>{
  if(!e.target.closest(".vp-rail")&&!e.target.closest(".vp-flyout"))closeViewportPanels();
});
let heroCam=copyCam(DEFAULT_HERO),planView=false;
function syncViewButton(){
  $("#viewBtn").dataset.state=planView?"plan":"hero";$("#viewBtn").classList.toggle("on",planView);
  $("#viewBtn").setAttribute("aria-label",planView?"Return to hero camera":"Switch to plan camera");
  $("#viewBtn").title=planView?"Return to hero camera":"Switch to plan camera";
}
function frameHero(){planView=false;cam=copyCam(DEFAULT_HERO);heroCam=copyCam(DEFAULT_HERO);syncViewButton();}
function togglePlanView(){
  if(!planView){heroCam=copyCam(cam);cam={az:0,el:1.535,dist:2.55,target:[...cam.target],fov:Number.isFinite(cam.fov)?cam.fov:DEFAULT_HERO.fov};planView=true;}
  else{cam=copyCam(heroCam);planView=false;}
  syncViewButton();
}
$("#frameBtn").onclick=frameHero;
$("#viewBtn").onclick=togglePlanView;
$("#previewBtn").onclick=()=>{
  if(previewMode==="output"){
    if(!selected){toast("Select a node to preview it");return;}
    previewMode="selected";
  }else previewMode="output";
  refreshPreview();
};
$("#undoBtn").onclick=undoGraph;$("#redoBtn").onclick=redoGraph;

/* ---- persistent vertical workspace splitter ----
   The graph is the user-sized pane. Its preferred height is stored in pixels so moving the
   Studio to a larger display gives the extra room to the terrain viewport instead of silently
   stretching the graph. applyStackedPaneSize only clamps that preference when keeping it would
   squeeze the terrain below its usable minimum; it never overwrites the preference while clamped. */
const STACKED_TERRAIN_MIN=220,STACKED_GRAPH_MIN=120,STACKED_SPLITTER_SIZE=7;
const workspaceSplitter=$("#workspaceSplitter");
let stackedGraphPreferred=null,workspaceResize=null;
function readStackedGraphPreference(){
  if(stackedGraphPreferred!=null)return stackedGraphPreferred;
  try{const value=Number(localStorage.getItem("terrainStudioStackedGraphSize"));
    if(Number.isFinite(value)&&value>0)stackedGraphPreferred=value;}catch(_){}
  if(stackedGraphPreferred==null){
    const available=Math.max(0,$("#main").clientHeight-STACKED_SPLITTER_SIZE);
    stackedGraphPreferred=Math.round(available*.48);
  }
  return stackedGraphPreferred;
}
function stackedGraphBounds(){
  const available=Math.max(0,$("#main").clientHeight-STACKED_TERRAIN_MIN-STACKED_SPLITTER_SIZE);
  return{min:Math.min(STACKED_GRAPH_MIN,available),max:available};
}
function applyStackedPaneSize(){
  if(!$("#main").classList.contains("stacked"))return;
  const bounds=stackedGraphBounds(),preferred=readStackedGraphPreference();
  const actual=Math.round(clamp(preferred,bounds.min,bounds.max));
  $("#main").style.setProperty("--stacked-graph-size",actual+"px");
  workspaceSplitter.setAttribute("aria-valuemin",String(Math.round(bounds.min)));
  workspaceSplitter.setAttribute("aria-valuemax",String(Math.round(bounds.max)));
  workspaceSplitter.setAttribute("aria-valuenow",String(actual));
  workspaceSplitter.setAttribute("aria-valuetext",
    "Node graph "+actual+" pixels; terrain view "+Math.max(0,$("#main").clientHeight-actual-STACKED_SPLITTER_SIZE)+" pixels");
}
function setStackedGraphPreference(value,persist){
  stackedGraphPreferred=Math.max(0,Math.round(value));
  if(persist!==false)try{localStorage.setItem("terrainStudioStackedGraphSize",String(stackedGraphPreferred));}catch(_){}
  applyStackedPaneSize();requestAnimationFrame(()=>{resizeGraph();resizeGL();});
}
function finishWorkspaceResize(e){
  if(!workspaceResize)return;
  if(e&&workspaceSplitter.hasPointerCapture&&workspaceSplitter.hasPointerCapture(e.pointerId))
    workspaceSplitter.releasePointerCapture(e.pointerId);
  workspaceResize=null;workspaceSplitter.classList.remove("resizing");document.body.classList.remove("resizing-workspace");
  try{localStorage.setItem("terrainStudioStackedGraphSize",String(Math.round(stackedGraphPreferred)));}catch(_){}
}
workspaceSplitter.onpointerdown=e=>{
  if(!$("#main").classList.contains("stacked")||e.button!==0)return;
  e.preventDefault();workspaceSplitter.setPointerCapture(e.pointerId);
  workspaceResize={pointerId:e.pointerId,startY:e.clientY,startSize:$("#graphwrap").getBoundingClientRect().height};
  workspaceSplitter.classList.add("resizing");document.body.classList.add("resizing-workspace");
};
workspaceSplitter.onpointermove=e=>{
  if(!workspaceResize||workspaceResize.pointerId!==e.pointerId)return;
  // Moving the horizontal divider up grows the graph below it.
  setStackedGraphPreference(workspaceResize.startSize+(workspaceResize.startY-e.clientY),false);
};
workspaceSplitter.onpointerup=finishWorkspaceResize;
workspaceSplitter.onpointercancel=finishWorkspaceResize;
workspaceSplitter.ondblclick=()=>{
  const available=Math.max(0,$("#main").clientHeight-STACKED_SPLITTER_SIZE);
  setStackedGraphPreference(available*.48,true);
};
workspaceSplitter.onkeydown=e=>{
  const current=$("#graphwrap").getBoundingClientRect().height,bounds=stackedGraphBounds();
  let next=null;
  if(e.key==="ArrowUp")next=current+16;
  else if(e.key==="ArrowDown")next=current-16;
  else if(e.key==="PageUp")next=current+64;
  else if(e.key==="PageDown")next=current-64;
  else if(e.key==="Home")next=bounds.min;
  else if(e.key==="End")next=bounds.max;
  if(next!=null){e.preventDefault();setStackedGraphPreference(next,true);}
};
function setLayout(stacked){
  $("#main").classList.toggle("stacked",stacked);$("#layoutBtn").classList.toggle("on",stacked);
  $("#layoutBtn").textContent=stacked?"⬌":"⬍";
  $("#layoutBtn").title=stacked?"Use side-by-side graph and rendering":"Stack rendering above the graph";
  try{localStorage.setItem("terrainStudioLayout",stacked?"stacked":"side");}catch(_){}
  syncEditorCommandState();
  requestAnimationFrame(()=>{applyStackedPaneSize();resizeGraph();resizeGL();});
}
$("#layoutBtn").onclick=()=>setLayout(!$("#main").classList.contains("stacked"));
async function toggleFullscreen(){
  try{
    if(document.fullscreenElement)await document.exitFullscreen();
    else await $("#viewport").requestFullscreen();
  }catch(err){toast("Fullscreen is unavailable in this browser");}
}
$("#fullscreenBtn").onclick=toggleFullscreen;
document.addEventListener("fullscreenchange",()=>{
  const on=document.fullscreenElement===$("#viewport");
  $("#fullscreenBtn").classList.toggle("on",on);
  $("#fullscreenBtn").setAttribute("aria-label",on?"Exit fullscreen":"Enter fullscreen");
  $("#fullscreenBtn").title=on?"Exit fullscreen (Shift+F)":"Fullscreen rendering (Shift+F)";
  document.querySelectorAll('[data-editor-command="fullscreen"]').forEach(b=>b.setAttribute("aria-checked",on?"true":"false"));
  requestAnimationFrame(resizeGL);
});
function syncDisplayState(){
  $("#wireBtn").classList.toggle("on",wire);$("#wireState").textContent=wire?"On":"Off";
  $("#displayBtn").classList.toggle("on",wire||shadeMode!==0);
}
$("#wireBtn").onclick=()=>{wire=!wire;syncDisplayState();};
$("#shadeSel").onchange=e=>{shadeMode=parseInt(e.target.value,10)||0;syncDisplayState();
  const root=activePreviewNode(),meta=root&&fieldMetadata(root._field);
  if(root&&root._field)updateViewport(meta&&meta.heightField||root._field,root,{color:true});};
syncViewButton();syncDisplayState();
function satGradientCSS(name){
  const stops=SATMAPS[name]||SATMAPS.Temperate;
  return"linear-gradient(90deg,"+stops.map(s=>"rgb("+s[1][0]+","+s[1][1]+","+s[1][2]+") "+(clamp(s[0],0,1)*100).toFixed(1)+"%").join(",")+")";
}
function syncSatPicker(scroll){
  $("#satPickerList").querySelectorAll(".sat-option").forEach(b=>{
    const on=b.dataset.name===satName;b.classList.toggle("selected",on);b.setAttribute("aria-selected",on?"true":"false");
    if(on&&scroll)b.scrollIntoView({block:"nearest"});});
}
function rebuildSatPicker(){
  const list=$("#satPickerList"),names=Object.keys(SATMAPS);
  list.innerHTML="";
  names.forEach(name=>{
    const b=document.createElement("button");b.type="button";b.className="sat-option";b.dataset.name=name;b.setAttribute("role","option");
    const strip=document.createElement("span");strip.className="sat-option-strip";strip.style.background=satGradientCSS(name);
    const label=document.createElement("span");label.className="sat-option-name";label.textContent=name;
    b.append(strip,label);b.onclick=()=>chooseSatMap(name,true);list.appendChild(b);
  });
  $("#satPickerCount").textContent=names.length+" palettes";syncSatPicker(false);
}
function closeSatPicker(){
  $("#satPickerMenu").hidden=true;satPickerAnchor=null;
}
let satPickerAnchor=null;
function openSatPicker(anchor){
  if(!anchor)return;satPickerAnchor=anchor;
  const menu=$("#satPickerMenu"),r=anchor.getBoundingClientRect(),w=Math.min(304,window.innerWidth-20);
  const below=window.innerHeight-r.bottom-8,above=r.top-8,useBelow=below>=Math.min(300,above);
  menu.style.width=w+"px";menu.style.left=clamp(r.right-w,10,window.innerWidth-w-10)+"px";
  menu.style.top=(useBelow?r.bottom+6:10)+"px";menu.style.maxHeight=Math.max(180,(useBelow?below-6:above-6))+"px";
  menu.hidden=false;
  requestAnimationFrame(()=>{syncSatPicker(true);const b=$("#satPickerList .selected");if(b)b.focus({preventScroll:true});});
}
function chooseSatMap(name,close){
  if(!SATMAPS[name])return;
  const target=selected&&selected.type==="satmap"?selected:nearestUpstreamNode("satmap");
  if(target&&target.params.gradient!==name){
    if(historyReady)recordHistory();target.params.gradient=name;markParamDirty(target);
    if(selected&&selected.id===target.id)buildProps();requestEval();
  }
  satName=name;buildSatLUT(name);syncSatPicker(false);
  if(close)closeSatPicker();
}
$("#satPickerList").onkeydown=e=>{
  const items=[...$("#satPickerList").querySelectorAll(".sat-option")],i=items.indexOf(document.activeElement);
  if(e.key==="Escape"){e.preventDefault();const a=satPickerAnchor;closeSatPicker();if(a&&a.isConnected)a.focus();return;}
  let j=null;if(e.key==="ArrowDown")j=Math.min(items.length-1,i+1);else if(e.key==="ArrowUp")j=Math.max(0,i-1);
  else if(e.key==="Home")j=0;else if(e.key==="End")j=items.length-1;
  if(j!=null){e.preventDefault();items[j].focus();items[j].scrollIntoView({block:"nearest"});}
};
document.addEventListener("mousedown",e=>{if(!$("#satPickerMenu").hidden&&!$("#satPickerMenu").contains(e.target)
  &&(!satPickerAnchor||!satPickerAnchor.contains(e.target)))closeSatPicker();});
rebuildSatPicker();

/* ---- SatMap Studio: docked gradient editor. Drag stops (position = elevation); the terrain recolours live. ---- */
(function(){
  const drawer=$("#satgen"),track=$("#sgTrack"),lut=$("#sgLut"),histo=$("#sgHisto");
  const cv=$("#sgCanvas"),ov=$("#sgOverlay"),imgPanel=$("#sgImgPanel"),imgWrap=$("#sgDrop");
  const cx=cv.getContext("2d",{willReadFrequently:true}),ox=ov.getContext("2d");
  const previewKey="__SatMap Studio Preview";
  let stops=[],sel=-1,interp="smooth",adj={hue:0,bright:1,contrast:1,sat:1},idata=null,prevShade=0,hist=null;
  let target=null,previousGradient=null,studioBefore=null;
  const lum=(r,g,b)=>0.2126*r+0.7152*g+0.0722*b;
  const hex=c=>"#"+c.map(v=>clamp(v|0,0,255).toString(16).padStart(2,"0")).join("");
  const unhex=h=>{h=h.replace("#","");return[parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)];};

  // ---- colour maths: adjust = live hue/bright/contrast/sat, baked into the stops on Apply ----
  function rgb2hsl(r,g,b){r/=255;g/=255;b/=255;const mx=Math.max(r,g,b),mn=Math.min(r,g,b);let h,s,l=(mx+mn)/2;
    if(mx===mn)h=s=0;else{const d=mx-mn;s=l>0.5?d/(2-mx-mn):d/(mx+mn);
      h=mx===r?(g-b)/d+(g<b?6:0):mx===g?(b-r)/d+2:(r-g)/d+4;h/=6;}return[h,s,l];}
  function hsl2rgb(h,s,l){if(s===0){const v=Math.round(l*255);return[v,v,v];}
    const q=l<0.5?l*(1+s):l+s-l*s,p=2*l-q,f=t=>{if(t<0)t++;if(t>1)t--;
      return t<1/6?p+(q-p)*6*t:t<0.5?q:t<2/3?p+(q-p)*(2/3-t)*6:p;};
    return[Math.round(f(h+1/3)*255),Math.round(f(h)*255),Math.round(f(h-1/3)*255)];}
  function applyAdj(c){let[r,g,b]=c;const ct=adj.contrast,br=adj.bright;
    r=(r-128)*ct+128;g=(g-128)*ct+128;b=(b-128)*ct+128;r*=br;g*=br;b*=br;
    let[h,s,l]=rgb2hsl(clamp(r,0,255),clamp(g,0,255),clamp(b,0,255));
    h=(h+adj.hue/360)%1;if(h<0)h++;s=clamp(s*adj.sat,0,1);return hsl2rgb(h,s,l);}

  // ---- LUT sampling (respects interpolation mode) ----
  function baseAt(t){if(!stops.length)return[0,0,0];const S=[...stops].sort((a,b)=>a.pos-b.pos);
    if(t<=S[0].pos)return S[0].col.slice();if(t>=S[S.length-1].pos)return S[S.length-1].col.slice();
    for(let k=0;k<S.length-1;k++)if(t>=S[k].pos&&t<=S[k+1].pos){
      if(interp==="bands")return S[k].col.slice();
      const f=(t-S[k].pos)/((S[k+1].pos-S[k].pos)||1);
      return[0,1,2].map(c=>Math.round(S[k].col[c]+(S[k+1].col[c]-S[k].col[c])*f));}
    return S[S.length-1].col.slice();}
  const finalAt=t=>applyAdj(baseAt(t));
  // baked stop array (adjust applied; bands -> hard steps) for buildSatLUTStops / SATMAPS
  function bake(){const S=[...stops].sort((a,b)=>a.pos-b.pos).map(s=>({pos:clamp(s.pos,0,1),col:applyAdj(s.col)}));
    if(interp==="smooth")return S.map(s=>[+s.pos.toFixed(3),s.col]);
    const out=[];for(let i=0;i<S.length;i++){out.push([+S[i].pos.toFixed(3),S[i].col]);
      if(i<S.length-1)out.push([+Math.max(S[i].pos,S[i+1].pos-0.001).toFixed(3),S[i].col]);}return out;}
  function computeHist(){const bins=72,h=new Float32Array(bins);
    if(curHgt&&curHgt.length){for(let i=0;i<curHgt.length;i++){let b=(curHgt[i]*bins)|0;if(b<0)b=0;if(b>=bins)b=bins-1;h[b]++;}
      let mx=0;for(const v of h)mx=Math.max(mx,v);if(mx)for(let i=0;i<bins;i++)h[i]/=mx;}hist=h;}

  // ---- render the bar + histogram + handles, and push a LIVE preview to the 3D terrain ----
  function render(){
    const W=Math.max(200,lut.clientWidth||300);
    lut.width=W;lut.height=36;const g=lut.getContext("2d");
    if(stops.length)for(let i=0;i<W;i++){const c=finalAt(i/(W-1));g.fillStyle="rgb("+c[0]+","+c[1]+","+c[2]+")";g.fillRect(i,0,1,36);}
    else{g.fillStyle=css("--bg2");g.fillRect(0,0,W,36);}
    histo.width=W;histo.height=24;const hg=histo.getContext("2d");hg.clearRect(0,0,W,24);
    if(hist){hg.fillStyle=css("--faint");hg.globalAlpha=.55;const bins=hist.length,bw=W/bins;
      for(let i=0;i<bins;i++){const bh=hist[i]*22;hg.fillRect(i*bw,24-bh,Math.max(1,bw-0.5),bh);}hg.globalAlpha=1;}
    track.innerHTML="";
    stops.forEach((s,i)=>{const h=document.createElement("div");h.className="sg-handle"+(i===sel?" sel":"");
      h.style.left=(s.pos*100)+"%";const fc=applyAdj(s.col);h.style.background="rgb("+fc[0]+","+fc[1]+","+fc[2]+")";
      h.style.borderBottomColor="rgb("+fc[0]+","+fc[1]+","+fc[2]+")";h.dataset.i=i;track.appendChild(h);});
    if(sel>=0&&stops[sel])$("#sgStopCol").value=hex(stops[sel].col);
    if(drawer.classList.contains("open")){
      SATMAPS[previewKey]=bake();
      if(target){target.params.gradient=previewKey;target._thumb=null;refreshPreview();}
      else buildSatLUTStops(SATMAPS[previewKey]);
    }
  }

  // ---- open / close (viewport stays live behind the drawer) ----
  function resetAdj(){adj={hue:0,bright:1,contrast:1,sat:1};
    $("#sgHue").value=0;$("#sgBright").value=1;$("#sgContrast").value=1;$("#sgSat").value=1;}
  function open(){
    target=selected&&selected.type==="satmap"?selected:nearestUpstreamNode("satmap");
    previousGradient=target?target.params.gradient:satName;studioBefore=historyReady?graphSnapshot():null;
    stops=(SATMAPS[previousGradient]||SATMAPS.Temperate).map(s=>({pos:s[0],col:s[1].slice()}));
    sel=stops.length?0:-1;resetAdj();setSeg("smooth");$("#sgName").value="Custom";
    prevShade=shadeMode;shadeMode=2;$("#shadeSel").value="2";syncDisplayState(); // force unlit Albedo so LUT edits are judged without lighting
    computeHist();drawer.classList.add("open");render();
  }
  function close(revert){drawer.classList.remove("open");shadeMode=prevShade;$("#shadeSel").value=String(shadeMode);syncDisplayState();
    if(revert!==false&&target)target.params.gradient=previousGradient;
    delete SATMAPS[previewKey];
    if(revert!==false){satName=target?target.params.gradient:satName;buildProps();refreshPreview();syncSatPicker(false);}
    target=null;previousGradient=null;studioBefore=null;}
  $("#satGenBtn").onclick=()=>drawer.classList.contains("open")?close():open();
  $("#sgClose").onclick=()=>close();

  // ---- preset "Start from…" ----
  (function fill(){const s=$("#sgPreset");s.innerHTML='<option value="">Start from…</option>';
    Object.keys(SATMAPS).forEach(k=>{const o=document.createElement("option");o.value=k;o.textContent=k;s.appendChild(o);});})();
  $("#sgPreset").onchange=e=>{const k=e.target.value;if(!k||!SATMAPS[k])return;
    stops=SATMAPS[k].map(s=>({pos:s[0],col:s[1].slice()}));sel=0;resetAdj();render();e.target.value="";};

  // ---- interpolation toggle ----
  function setSeg(v){interp=v;$("#sgInterp").querySelectorAll("button").forEach(b=>b.classList.toggle("on",b.dataset.v===v));}
  $("#sgInterp").querySelectorAll("button").forEach(b=>b.onclick=()=>{setSeg(b.dataset.v);render();});

  // ---- stops: drag = elevation, click bar = add, colour picker, delete ----
  let drag=null;
  track.addEventListener("mousedown",e=>{const h=e.target.closest(".sg-handle");if(!h)return;sel=+h.dataset.i;drag=sel;e.preventDefault();render();});
  window.addEventListener("mousemove",e=>{if(drag==null)return;const r=track.getBoundingClientRect();stops[drag].pos=clamp((e.clientX-r.left)/r.width,0,1);render();});
  window.addEventListener("mouseup",()=>{drag=null;});
  lut.addEventListener("click",e=>{const r=lut.getBoundingClientRect();const t=clamp((e.clientX-r.left)/r.width,0,1);
    stops.push({pos:t,col:baseAt(t)});sel=stops.length-1;render();});
  $("#sgDelStop").onclick=()=>{if(stops.length<=2){toast("Keep at least 2 stops");return;}if(sel<0)sel=0;stops.splice(sel,1);sel=Math.min(sel,stops.length-1);render();};
  $("#sgStopCol").oninput=e=>{if(sel<0)return;stops[sel].col=unhex(e.target.value);render();};

  // ---- global reverse + adjustment sliders ----
  $("#sgReverse").onclick=()=>{stops.forEach(s=>s.pos=1-s.pos);render();};
  const adjIn=(id,key)=>$(id).oninput=e=>{adj[key]=+e.target.value;render();};
  adjIn("#sgHue","hue");adjIn("#sgBright","bright");adjIn("#sgContrast","contrast");adjIn("#sgSat","sat");
  $("#sgResetAdj").onclick=()=>{resetAdj();render();};

  // ---- image: Auto-extract ramp + eyedropper (no radius knob; a small fixed sample) ----
  $("#sgFromImg").onclick=()=>{imgPanel.hidden=!imgPanel.hidden;};
  $("#sgImgClose").onclick=()=>{imgPanel.hidden=true;};
  function loadImage(src){const img=new Image();img.onload=()=>{let w=img.width,h=img.height;const s=Math.min(196/w,118/h,1);
      w=Math.max(1,w*s|0);h=Math.max(1,h*s|0);cv.width=w;cv.height=h;ov.width=w;ov.height=h;cx.drawImage(img,0,0,w,h);
      idata=cx.getImageData(0,0,w,h).data;$("#sgHint").style.display="none";};
    img.onerror=()=>toast("Could not load that image");img.src=src;}
  function fileToImg(f){if(!f||!/^image\//.test(f.type)){if(f)toast("Not an image file");return;}const rd=new FileReader();rd.onload=()=>loadImage(rd.result);rd.readAsDataURL(f);}
  $("#satImg").onchange=e=>fileToImg(e.target.files[0]);
  imgWrap.addEventListener("dragover",e=>{e.preventDefault();imgWrap.classList.add("drag");});
  imgWrap.addEventListener("dragleave",()=>imgWrap.classList.remove("drag"));
  imgWrap.addEventListener("drop",e=>{e.preventDefault();imgWrap.classList.remove("drag");fileToImg(e.dataTransfer.files[0]);});
  const evtXY=e=>{const r=cv.getBoundingClientRect();return[Math.round((e.clientX-r.left)*cv.width/r.width),Math.round((e.clientY-r.top)*cv.height/r.height)];};
  function sampleAt(x,y,R){if(!idata)return null;const w=cv.width,h=cv.height;let r=0,g=0,b=0,n=0;
    for(let dy=-R;dy<=R;dy++)for(let dx=-R;dx<=R;dx++){if(dx*dx+dy*dy>R*R)continue;const px=x+dx,py=y+dy;if(px<0||py<0||px>=w||py>=h)continue;
      const i=(py*w+px)*4;r+=idata[i];g+=idata[i+1];b+=idata[i+2];n++;}return n?[Math.round(r/n),Math.round(g/n),Math.round(b/n)]:null;}
  cv.addEventListener("mousemove",e=>{const[x,y]=evtXY(e);ox.clearRect(0,0,ov.width,ov.height);
    ox.beginPath();ox.arc(x,y,4,0,7);ox.lineWidth=2;ox.strokeStyle="rgba(0,0,0,.6)";ox.stroke();
    ox.beginPath();ox.arc(x,y,4,0,7);ox.lineWidth=1;ox.strokeStyle="#fff";ox.stroke();});
  cv.addEventListener("mouseleave",()=>ox.clearRect(0,0,ov.width,ov.height));
  cv.addEventListener("click",e=>{const[x,y]=evtXY(e);const c=sampleAt(x,y,4);if(!c)return;   // eyedrop -> the selected stop
    if(sel<0){stops.push({pos:0.5,col:c});sel=stops.length-1;}else stops[sel].col=c;render();});
  $("#sgN").oninput=e=>$("#sgNV").textContent=e.target.value;
  $("#sgAuto").onclick=()=>{if(!idata){toast("Load an image first");return;}
    const N=+$("#sgN").value,w=cv.width,h=cv.height,arr=[],step=Math.max(1,Math.sqrt(w*h/16000)|0);
    for(let y=0;y<h;y+=step)for(let x=0;x<w;x+=step){const i=(y*w+x)*4;arr.push([idata[i],idata[i+1],idata[i+2],lum(idata[i],idata[i+1],idata[i+2])]);}
    arr.sort((a,b)=>a[3]-b[3]);const ns=[];
    for(let k=0;k<N;k++){const a=k*arr.length/N|0,z=(k+1)*arr.length/N|0;let r=0,g=0,b=0,n=0;
      for(let j=a;j<z;j++){r+=arr[j][0];g+=arr[j][1];b+=arr[j][2];n++;}if(n)ns.push({pos:k/(N-1),col:[Math.round(r/n),Math.round(g/n),Math.round(b/n)]});}
    if(ns.length>1){stops=ns;sel=0;resetAdj();render();}};

  // ---- Apply: bake and register the LUT in the SatMap list + select it ----
  $("#sgApply").onclick=()=>{if(stops.length<2){toast("Need at least 2 stops");return;}
    let name=($("#sgName").value||"Custom").trim()||"Custom";
    if(SATMAPS[name]&&name!==satName){let n=2;while(SATMAPS[name+" "+n])n++;name+=" "+n;}
    SATMAPS[name]=bake();
    delete SATMAPS[previewKey];
    if(![...$("#sgPreset").options].some(o=>o.value===name)){
      const o=document.createElement("option");o.value=name;o.textContent=name;$("#sgPreset").appendChild(o);}
    if(target)target.params.gradient=name;satName=name;rebuildSatPicker();buildProps();refreshPreview();
    if(studioBefore)pushUndo(studioBefore);
    toast('SatMap "'+name+'" saved');close(false);};

  window.addEventListener("resize",()=>{if(drawer.classList.contains("open"))render();});
})();
const degrees=v=>Math.round(v*180/Math.PI)+"°";
function syncLookValues(){
  $("#sunAzVal").textContent=degrees(sun.az);$("#sunElVal").textContent=degrees(sun.el);
  const ev=renderLook.exposure;$("#exposureVal").textContent=(ev>0?"+":ev<0?"−":"")+Math.abs(ev).toFixed(2)+" EV";
  $("#hazeVal").textContent=Math.round(renderLook.haze*100)+"%";
}
function syncWaterLookValues(){
  $("#waterStrengthVal").textContent=Math.round(waterLook.strength*100)+"%";
  $("#waterScaleVal").textContent=waterLook.scale.toFixed(2)+"×";
  $("#waterSpeedVal").textContent=waterLook.speed.toFixed(2)+"×";
  $("#waterRefractionVal").textContent=Math.round(waterLook.refraction*100)+"%";
  const wh=$("#waveHeightVal");if(wh)wh.textContent=(waterLook.amplitudeM==null?1.2:waterLook.amplitudeM).toFixed(1)+" m";
  const ws=$("#waveSeaVal");if(ws)ws.textContent=Math.round((waterLook.seaState==null?.55:waterLook.seaState)*100)+"%";
}
$("#sunAz").oninput=e=>{sun.az=parseFloat(e.target.value);syncLookValues();};
$("#sunEl").oninput=e=>{sun.el=parseFloat(e.target.value);syncLookValues();};
$("#exposure").oninput=e=>{renderLook.exposure=parseFloat(e.target.value);syncLookValues();};
$("#haze").oninput=e=>{renderLook.haze=parseFloat(e.target.value);syncLookValues();};
$("#waterPattern").onchange=e=>{waterLook.pattern=e.target.value;};
$("#waterStrength").oninput=e=>{waterLook.strength=parseFloat(e.target.value);syncWaterLookValues();};
$("#waterScale").oninput=e=>{waterLook.scale=parseFloat(e.target.value);syncWaterLookValues();};
$("#waterSpeed").oninput=e=>{waterLook.speed=parseFloat(e.target.value);syncWaterLookValues();};
$("#waterRefraction").oninput=e=>{waterLook.refraction=parseFloat(e.target.value);syncWaterLookValues();};
// The Gerstner controls REBUILD THE PROGRAMS, because the twelve terms are baked into the
// shader as literals — that is what lets the two passes be compared byte for byte, and the
// price is that changing a control is a recompile rather than a uniform write. Cheap enough
// for an authoring action, and it keeps one definition instead of two.
// Only the SPECTRUM needs a recompile — sea state and body kind change wavelengths and
// directions, which are baked. Wave height is a uniform and deliberately does not come here.
function rebuildWaterPrograms(){
  if(gl){initGL();buildIndex();nodes.forEach(n=>{n._dirty=true;});evalGraph();}
}
if($("#waveHeight"))$("#waveHeight").oninput=e=>{waterLook.amplitudeM=parseFloat(e.target.value);syncWaterLookValues();};
if($("#waveSea"))$("#waveSea").oninput=e=>{waterLook.seaState=parseFloat(e.target.value);syncWaterLookValues();rebuildWaterPrograms();};
if($("#waveBody"))$("#waveBody").onchange=e=>{waterLook.bodyKind=e.target.value;rebuildWaterPrograms();};
// The look is a UNIFORM, not a recompile: it grades signals the shader already computes, so
// switching it costs one uniform write rather than rebuilding both water programs.
if($("#waterStyle"))$("#waterStyle").onchange=e=>{waterLook.style=e.target.value;requestRender();};
if($("#waterBands"))$("#waterBands").oninput=e=>{waterLook.bandSteps=parseInt(e.target.value,10);
  const o=$("#waterBandsVal");if(o)o.textContent=e.target.value;requestRender();};
syncLookValues();syncWaterLookValues();
function typing(){const t=document.activeElement&&document.activeElement.tagName;return t==="INPUT"||t==="SELECT"||t==="TEXTAREA";}
window.addEventListener("keydown",e=>{
  if(e.key==="Escape"&&!$("#newTerrainDialog").hidden){e.preventDefault();closeNewTerrainDialog();return;}
  if(e.key==="Escape"&&!$("#drawEditor").hidden){e.preventDefault();closeDrawEditor();return;}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();filterCommands("");$("#commandSearch").value="";setTopPopover("commandMenu",true);return;}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="n"){e.preventDefault();runEditorCommand("new");return;}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="i"){e.preventDefault();runEditorCommand("import");return;}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="s"){e.preventDefault();runEditorCommand("save");return;}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="o"){e.preventDefault();runEditorCommand("open");return;}
  if(e.key==="Escape"&&editorMenuPanels.some(id=>!$("#"+id).hidden)){e.preventDefault();closeEditorMenus();if(lastEditorMenuButton)lastEditorMenuButton.focus();return;}
  if(e.key==="Escape"&&topPopovers.some(id=>!$("#"+id).hidden)){e.preventDefault();closeTopPopovers();$("#commandBtn").focus();return;}
  if(e.key==="Escape"&&viewportPanels.some(id=>!$("#"+id).hidden)){e.preventDefault();closeViewportPanels();return;}
  if(e.key==="Escape"&&graphMenu.classList.contains("open")){e.preventDefault();closeGraphMenu();return;}
  if(typing())return;                                          // don't hijack keys while editing a parameter
  if(e.key==="Escape"&&selectedEdge){e.preventDefault();selectEdge(null);return;}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="z"){e.preventDefault();e.shiftKey?redoGraph():undoGraph();return;}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="y"){e.preventDefault();redoGraph();return;}
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="d"&&selected&&!selectedEdge){e.preventDefault();duplicateSel();return;}
  if(e.code==="Space")spaceDown=true;
  if(e.key==="Delete"||e.key==="Backspace"){
    if(selectedEdge){e.preventDefault();deleteEdge(selectedEdge);}else if(selected)deleteSel();}
  if((e.key==="f"||e.key==="F")&&e.shiftKey){e.preventDefault();toggleFullscreen();}
  else if(e.key==="f"||e.key==="F")frameHero();});
window.addEventListener("keyup",e=>{if(e.code==="Space")spaceDown=false;});
updatePreviewInfo(activePreviewNode());

/* =====================================================================
   DEFAULT GRAPH — a good-looking starting point
   ===================================================================== */
function blankGraph(){
  const out=makeNode("output",360,180);out.params={norm:"on"};
  select(out);
  // A clean document follows the same layout contract as every authored graph. This currently
  // frames one Output node, and automatically keeps working when the starter grows more nodes.
  // newTerrainDocument() disables history around construction, so this cannot create a phantom undo.
  organizeGraph(null,null,"Organized new terrain");
}
function newTerrainDocument(withDefault,template="",alreadyConfirmed){
  // alreadyConfirmed: the New Terrain dialog has taken the decision and run the preflight, so a
  // second confirm() would ask the same question twice.
  if(!alreadyConfirmed&&historyReady&&nodes.length&&!confirm("Start a new terrain? The current graph and its undo history will be discarded."))return false;
  const ready=historyReady;historyReady=false;
  nodes=[];edges=[];uid=1;selected=null;selectedEdge=null;importTarget=null;
  undoStack.length=0;redoStack.length=0;previewMode="output";
  // The biome applies here, not only on the dialog path. createTerrainDef's own defaults put the
  // sea at 6 degC, which on a 2600 m world is BELOW FREEZING over most of the relief -- the
  // opening document rendered ice, and ice bypasses every water shading path there is. The
  // default biome is a climate someone chose; the constructor defaults are just constructor
  // defaults.
  terrainDef=createTerrainDef(biomeTerrainOverrides(pendingBiome));
  H_SCALE=terrainDef.height/terrainDef.scale;scene={water:null,snow:null,satmap:null};
  if(template==="canyon")canyonGraph();else if(withDefault)defaultGraph();else blankGraph();
  nodes.forEach(n=>{n._dirty=true;n._thumb=null;});
  historyReady=ready;updateHistoryButtons();syncEditorCommandState();evalGraph();
  toast(template==="canyon"?"New terrain · Canyon landscape":withDefault?"New terrain · default setup":"New terrain · clean graph");return true;
}
function canyonGraph(){
  const canyon=makeNode("canyon",60,150);
  Object.assign(canyon.params,{style:"eroded",scale:.35,slot:.36,valley:.58,surrounding:.72,depth:1,
    structural:.50,tributaries:0,seed:3,detailWarp:.56,alternate:"off"});
  const erosion=makeNode("erosion2",340,150);
  Object.assign(erosion.params,{duration:.28,downcut:.38,erosionScale:.50,seed:17,
    suspended:.36,bed:.30,coarse:.22,depositBoost:.18,shape:.20,shapeSharp:.34,shapeDetail:.68});
  const fix=makeNode("hydrofix",620,150);
  Object.assign(fix.params,{fix:.48,downcut:.22});
  const out=makeNode("output",880,150);out.params.norm="on";
  edges.push({from:canyon.id,to:erosion.id,slot:0},{from:erosion.id,to:fix.id,slot:0},{from:fix.id,to:out.id,slot:0});
  view={x:56,y:105,z:.82};select(erosion);
}
// The full-stack demonstration graph: bedrock through erosion, colour, climate, water and snow.
// This WAS the opening document, and D7 demoted it - 18 nodes spanning every subsystem is a
// showcase, not a starting point, and it made "the default looks different" a question with
// eighteen candidate answers. It stays because it is the only thing exercising the whole stack
// end to end, and two oracles construct it deliberately to check wind->snow wiring.
function showcaseGraph(){
  const base=makeNode("perlin",40,40);base.params={seed:7,freq:3,octaves:6,lac:2,gain:0.5};
  const ridge=makeNode("ridged",40,220);ridge.params={seed:12,freq:4,octaves:6,lac:2.1,gain:0.55};
  const mix=makeNode("blend",200,120);mix.params={factor:0.5};
  const warp=makeNode("warp",200,300);warp.params={strength:0.08,freq:3,seed:5};
  const hyd=makeNode("hydraulic",360,120);Object.assign(hyd.params,{pipeEnabled:true,dropletEnabled:false,
    pipeIters:48,droplets:16000,pipeErode:0.35,pipeDeposit:0.28,pipeCapacity:6,pipeInertia:0.05,seed:1,feat:1});
  // assign, never replace (see the snow node below): a replaced params object loses schema keys
  // and the next property-panel hydration writes the schema defaults back in SILENTLY - here
  // that would flip the node to Real scale and change the shipped terrain by 4.3 m rms on a
  // click. The default document keeps its tuned CELL-UNIT look, explicitly.
  const th=makeNode("thermal",520,120);Object.assign(th.params,{realScale:"off",talus:0.014,iters:22,rate:0.5});
  const deposits=makeNode("d_deposits",520,300);deposits.params.radius=4;
  const sat=makeNode("satmap",680,120);sat.params.gradient="Temperate";sat.params.source="height";sat.params.rough="med";
  const colorErosion=makeNode("colorerosion",840,120);colorErosion.params.seed=7;
  const weathering=makeNode("weathering",1000,120);
  const heightMap=makeNode("d_height",840,330);
  const sunShadow=makeNode("d_sunshadow",1000,330);
  const wind=makeNode("d_wind",1000,500);
  const water=makeNode("water",1160,120);water.params={mode:"hydro",lakes:"on",lakeMin:.001,flow:.5,riverDepth:.7,level:.12,shoreSmooth:1.35,foam:.18};
  const temperature=makeNode("d_temperature",1160,330);
  const temperatureModify=makeNode("d_heat",1320,330);
  const snow=makeNode("snow",1320,120);Object.assign(snow.params,{snowfall:3,meltDays:45,meltRate:10,repose:38,iterations:12,settle:.55}); // assign, never replace: wholesale replacement dropped adhesion/wind, so the default document shipped WITHOUT the new physics and merely CLICKING the node re-hydrated the keys and changed the terrain
  const out=makeNode("output",1480,120);out.params={norm:"on"};
  edges.push({from:base.id,to:mix.id,slot:0});
  edges.push({from:ridge.id,to:mix.id,slot:1});
  edges.push({from:mix.id,to:warp.id,slot:0});
  edges.push({from:warp.id,to:hyd.id,slot:0});
  edges.push({from:hyd.id,to:th.id,slot:0});
  edges.push({from:th.id,to:deposits.id,slot:0});       // final solid surface -> sediment/deposition analysis
  edges.push({from:th.id,to:sat.id,slot:0});
  edges.push({from:sat.id,to:colorErosion.id,slot:0});
  edges.push({from:deposits.id,to:colorErosion.id,slot:1});
  edges.push({from:colorErosion.id,to:weathering.id,slot:0});
  edges.push({from:weathering.id,to:water.id,slot:0});       // water phase is established before snow placement
  edges.push({from:water.id,to:snow.id,slot:0});             // snow is excluded from liquid and may accumulate on ice
  edges.push({from:snow.id,to:out.id,slot:0});
  edges.push({from:weathering.id,to:heightMap.id,slot:0});   // reusable deterministic climate-data branch
  edges.push({from:heightMap.id,to:sunShadow.id,slot:0});
  edges.push({from:heightMap.id,to:wind.id,slot:0});
  edges.push({from:heightMap.id,to:temperature.id,slot:0});
  edges.push({from:sunShadow.id,to:temperature.id,slot:1});
  edges.push({from:temperature.id,to:temperatureModify.id,slot:0});
  edges.push({from:temperatureModify.id,to:water.id,slot:1});
  edges.push({from:temperatureModify.id,to:snow.id,slot:1});
  edges.push({from:wind.id,to:snow.id,slot:2});
  view={x:22,y:28,z:.58};                               // frame the expanded production graph on first launch
  select(sat);                                            // the node owns its visible palette library; the viewport does not
}


/* ---- D7 L0 — THE BEDROCK LAYER ------------------------------------------------------------
   The opening document is the HIGHEST LAYER VERIFIED CORRECT ON BOTH LATTICES, and today that is
   L0: base shape, detail noise, one blend, one mask. Nothing above it.

   Why this and not the showcase. A default that spans every subsystem cannot be a regression
   surface: any change anywhere reads as "the default looks different" with no way to localise it.
   A layered default inverts that - each layer is promoted only once its own gates are green on
   square AND hex, so the opening document can never run ahead of what has been proven, and a
   change to it is attributable by construction.

   L0 is also exactly the set that must be right before anything else can be: every mask in the app
   is built from blur (see blurFieldHex - three lattice-line passes, anisotropy 1.0000 on both
   lattices as of MC-4), and every later layer is gated by masks.

   Promotion order from here: L1 erosion, L2 cover, L3 water, L4 climate/snow, L5 dressing. */
// The biome chosen in the New Terrain dialog, read by the opening graph. A module-level value
// rather than a parameter because layer0Graph is also called by defaultGraph() from paths that
// have no dialog -- and those must still get a coherent world rather than an undefined one.
let pendingBiome=DEFAULT_BIOME;
function layer0Graph(){
  // THE OPENING DOCUMENT IS A CLAIM ABOUT WHAT THIS TOOL IS FOR. Two octaves of noise blended into
  // an output says "procedural texture generator". Two tectonic plate systems blended, then flooded
  // to a sea level, says "this models a process and then puts water on it" -- which is the actual
  // thesis, and it shows a coastline in the first frame instead of a grey lump.
  //
  // Two uplifts rather than one: a single plate system gives one mountain belt across the tile and
  // reads as a ridge. Two at different seeds interfere, and the SECOND IS DELIBERATELY WEAKER
  // (continental uplift 0.28 against 0.52) so it reads as a lower, older range against a higher
  // young one rather than as two equal ridges fighting.
  const plates=makeNode("tectonic",60,60);
  // ELEVATION for the first: plate interiors and ocean basins, which is what puts a coastline on
  // the tile at all.
  // BOTH ARE OROGEN, the node's own default output. `elev` returns plate-interior elevations,
  // which are piecewise-constant per plate: blending two of those gives flat tops separated by
  // vertical walls, which is exactly what the first version of this rendered. Orogen is the
  // mountain-belt field along the boundaries, and two of them at different plate counts read as
  // ranges crossing ranges.
  Object.assign(plates.params,{seed:3,plates:8,warp:0.58,orogen:0.42,ocean:0.42,land:0.55,output:"orogen"});
  const older=makeNode("tectonic",60,300);
  // OROGEN for the second, not a second elevation field. Two `elev` outputs blended give two sets
  // of plate plateaus averaged together -- flat tops and vertical walls, which is what the first
  // version of this rendered. Orogen is the mountain-belt field along plate boundaries, so the
  // blend reads as ranges standing on continents rather than as terraces.
  // The second is the LOWER, OLDER range: less continental uplift and a wider, softer orogen, so
  // it reads as worn-down ground the young belt stands on rather than as an equal ridge.
  Object.assign(older.params,{seed:17,plates:15,warp:0.66,orogen:0.30,ocean:0.5,land:0.26,output:"orogen"});
  const mix=makeNode("blend",320,150);mix.params={factor:0.42};
  // Sea level well above the node default of 0.12. At the default the water sits in a few hollows
  // and is easy to miss; at 0.30 the tile has a real coastline, which is the thing worth seeing.
  const sea=makeNode("water",560,150);
  // Sea level comes from the biome: an arid world opens with almost no standing water and a
  // boreal one with lakes, which is the difference the preset exists to express.
  Object.assign(sea.params,{mode:"sea",level:biomeSeaLevel(pendingBiome),shoreSmooth:1.35,foam:0.18});
  const out=makeNode("output",790,150);out.params={norm:"on"};
  edges.push({from:plates.id,to:mix.id,slot:0});
  edges.push({from:older.id,to:mix.id,slot:1});
  edges.push({from:mix.id,to:sea.id,slot:0});
  edges.push({from:sea.id,to:out.id,slot:0});
  // Select the OUTPUT, not the first generator. collectScene walks the primary chain from the active
  // preview node, so selecting the base leaves scene.water null and the opening frame is dry -- the
  // exact trap that cost four attempts to confirm the wave work.
  selected=out;
}

// The opening document. Points at the highest PROVEN layer; move it up as layers are promoted.
function defaultGraph(){ layer0Graph(); }

/* ------------------------------------------------------------ boot --- */
function boot(){
  if(!document.documentElement.getAttribute("data-theme"))document.documentElement.setAttribute("data-theme","dark");
  try{const savedLayout=localStorage.getItem("terrainStudioLayout");
    setLayout(savedLayout?savedLayout==="stacked":true);
  }catch(_){setLayout(true);}
  resizeGraph();initGL();defaultGraph();evalGraph();historyReady=true;updateHistoryButtons();
  window.addEventListener("resize",()=>{applyStackedPaneSize();resizeGraph();});
  new ResizeObserver(()=>applyStackedPaneSize()).observe($("#main"));
  new ResizeObserver(()=>resizeGraph()).observe(gc.parentElement);
}
boot();

// ---- service worker -------------------------------------------------------------------------
// MODE === "production" only, which is NOT the same as PROD. import.meta.env.PROD tracks
// build-vs-serve, so it is true for `vite build --mode test` as well - measured: the --mode test
// bundle carried the registration until this guard was tightened. That matters because the oracle
// suite runs against exactly that bundle via `--preview`, and a worker there would cache a shell
// the next run then has to fight. Gating on the MODE NAME keeps the test artifact worker-free.
//
// Dev is excluded for the ordinary reason: a cache-first worker in front of a dev server is the
// classic "my change did nothing" hour.
//
// Registered at ./sw.js, which publicDir copies to the served root: root scope, stable URL.
if (import.meta.env.MODE === "production" && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js").catch((e) => console.warn("sw registration failed", e));
  });
}

// ==== TEST BRIDGE BEGIN — generated, do not edit (npm run bridge:apply) ====
/* GENERATED by scripts/generate-bridge.mjs from bridge-surface.json — do not edit.
 * 225 symbols (28 writable, 197 read-only).
 * Regenerate: npm run bridge:gen   Verify coverage: node _verify_bridge.js --check
 *
 * Appended to src/legacy.js AFTER the app source, so each accessor closes over the real
 * module binding. It cannot be a separate importable module — see generate-bridge.mjs.
 */
if (import.meta.env && (import.meta.env.DEV || import.meta.env.MODE === "test")) {
  const __t = globalThis
  const __def = (name, get, set) => {
    try {
      Object.defineProperty(__t, name, { configurable: true, enumerable: false, get, set })
    } catch (e) {
      console.error("[bridge] cannot define " + name + ": " + (e && e.message))
    }
  }
  const __ro = (name) => () => {
    throw new TypeError("[bridge] " + name + " is read-only (const or function binding).")
  }

  // 28 writable: tests assign these directly (RES = 512, nodes = [], ...).
  __def("RES", () => RES, (v) => { RES = v })
  __def("nodes", () => nodes, (v) => { nodes = v })
  __def("edges", () => edges, (v) => { edges = v })
  __def("USE_GPU", () => USE_GPU, (v) => { USE_GPU = v })
  __def("TARGET_RES", () => TARGET_RES, (v) => { TARGET_RES = v })
  __def("selected", () => selected, (v) => { selected = v })
  __def("cam", () => cam, (v) => { cam = v })
  __def("selectedEdge", () => selectedEdge, (v) => { selectedEdge = v })
  __def("uid", () => uid, (v) => { uid = v })
  __def("scene", () => scene, (v) => { scene = v })
  __def("XF", () => XF, (v) => { XF = v })
  __def("SCALE_RES", () => SCALE_RES, (v) => { SCALE_RES = v })
  __def("undoStack", () => undoStack, (v) => { undoStack = v })
  __def("view", () => view, (v) => { view = v })
  __def("BUILD_QUALITY", () => BUILD_QUALITY, (v) => { BUILD_QUALITY = v })
  __def("historyReady", () => historyReady, (v) => { historyReady = v })
  __def("redoStack", () => redoStack, (v) => { redoStack = v })
  __def("H_SCALE", () => H_SCALE, (v) => { H_SCALE = v })
  __def("previewMode", () => previewMode, (v) => { previewMode = v })
  __def("importTarget", () => importTarget, (v) => { importTarget = v })
  __def("evalFrame", () => evalFrame, (v) => { evalFrame = v })
  __def("shadeMode", () => shadeMode, (v) => { shadeMode = v })
  __def("buildRun", () => buildRun, (v) => { buildRun = v })
  __def("uTime", () => uTime, (v) => { uTime = v })
  __def("satName", () => satName, (v) => { satName = v })
  __def("wire", () => wire, (v) => { wire = v })
  __def("AUTO", () => AUTO, (v) => { AUTO = v })
  __def("TEMP_UNIT", () => TEMP_UNIT, (v) => { TEMP_UNIT = v })

  // 197 read-only. Getters hand out the LIVE value: 8 of
  // these are patched through by tests (TYPES.blur.eval = ..., gl.bindBuffer = ...), which a
  // copy-returning getter would silently discard.
  __def("TYPES", () => TYPES, __ro("TYPES"))
  __def("terrainDef", () => terrainDef, __ro("terrainDef"))
  __def("gl", () => gl, __ro("gl"))
  __def("makeNode", () => makeNode, __ro("makeNode"))
  __def("evalGraph", () => evalGraph, __ro("evalGraph"))
  __def("buildIndex", () => buildIndex, __ro("buildIndex"))
  __def("newField", () => newField, __ro("newField"))
  __def("fieldH", () => fieldH, __ro("fieldH"))
  __def("fieldW", () => fieldW, __ro("fieldW"))
  __def("gnoise", () => gnoise, __ro("gnoise"))
  __def("fbmField", () => fbmField, __ro("fbmField"))
  __def("buffers", () => buffers, __ro("buffers"))
  __def("GPU", () => GPU, __ro("GPU"))
  __def("VARS", () => VARS, __ro("VARS"))
  __def("graphSnapshot", () => graphSnapshot, __ro("graphSnapshot"))
  __def("outputNode", () => outputNode, __ro("outputNode"))
  __def("hydroMassDiag", () => hydroMassDiag, __ro("hydroMassDiag"))
  __def("PORTS", () => PORTS, __ro("PORTS"))
  __def("resolveColor", () => resolveColor, __ro("resolveColor"))
  __def("nodeById", () => nodeById, __ro("nodeById"))
  __def("cloneParams", () => cloneParams, __ro("cloneParams"))
  __def("showcaseGraph", () => showcaseGraph, __ro("showcaseGraph"))
  __def("buildProps", () => buildProps, __ro("buildProps"))
  __def("glc", () => glc, __ro("glc"))
  __def("canyonFieldCPU", () => canyonFieldCPU, __ro("canyonFieldCPU"))
  __def("select", () => select, __ro("select"))
  __def("updateViewport", () => updateViewport, __ro("updateViewport"))
  __def("loadProjectText", () => loadProjectText, __ro("loadProjectText"))
  __def("CANYON_EVOLUTION_CACHE", () => CANYON_EVOLUTION_CACHE, __ro("CANYON_EVOLUTION_CACHE"))
  __def("cellSizeM", () => cellSizeM, __ro("cellSizeM"))
  __def("AUXMAPS", () => AUXMAPS, __ro("AUXMAPS"))
  __def("curField", () => curField, __ro("curField"))
  __def("curHgt", () => curHgt, __ro("curHgt"))
  __def("curWater", () => curWater, __ro("curWater"))
  __def("newTerrainDocument", () => newTerrainDocument, __ro("newTerrainDocument"))
  __def("u", () => u, __ro("u"))
  __def("saveProjectText", () => saveProjectText, __ro("saveProjectText"))
  __def("streamPowerErode", () => streamPowerErode, __ro("streamPowerErode"))
  __def("waterLook", () => waterLook, __ro("waterLook"))
  __def("canyonEvolutionState", () => canyonEvolutionState, __ro("canyonEvolutionState"))
  __def("fieldMetadata", () => fieldMetadata, __ro("fieldMetadata"))
  __def("markDirtyFrom", () => markDirtyFrom, __ro("markDirtyFrom"))
  __def("portPos", () => portPos, __ro("portPos"))
  __def("PORTS_EXPR", () => PORTS_EXPR, __ro("PORTS_EXPR"))
  __def("renderGL", () => renderGL, __ro("renderGL"))
  __def("sampleBilinear", () => sampleBilinear, __ro("sampleBilinear"))
  __def("undoGraph", () => undoGraph, __ro("undoGraph"))
  __def("activePreviewNode", () => activePreviewNode, __ro("activePreviewNode"))
  __def("frameHero", () => frameHero, __ro("frameHero"))
  __def("priorityFloodFill", () => priorityFloodFill, __ro("priorityFloodFill"))
  __def("blankGraph", () => blankGraph, __ro("blankGraph"))
  __def("simulateSnowLayer", () => simulateSnowLayer, __ro("simulateSnowLayer"))
  __def("togglePlanView", () => togglePlanView, __ro("togglePlanView"))
  __def("xfFromParams", () => xfFromParams, __ro("xfFromParams"))
  __def("DOCTRINE", () => DOCTRINE, __ro("DOCTRINE"))
  __def("graphMenu", () => graphMenu, __ro("graphMenu"))
  __def("planView", () => planView, __ro("planView"))
  __def("refreshWater", () => refreshWater, __ro("refreshWater"))
  __def("transformField", () => transformField, __ro("transformField"))
  __def("waterShaderSources", () => waterShaderSources, __ro("waterShaderSources"))
  __def("compProg", () => compProg, __ro("compProg"))
  __def("curIceSnow", () => curIceSnow, __ro("curIceSnow"))
  __def("EXACT_TYPES", () => EXACT_TYPES, __ro("EXACT_TYPES"))
  __def("redoGraph", () => redoGraph, __ro("redoGraph"))
  __def("simulateTerrainWind", () => simulateTerrainWind, __ro("simulateTerrainWind"))
  __def("sun", () => sun, __ro("sun"))
  __def("syncDisplayState", () => syncDisplayState, __ro("syncDisplayState"))
  __def("terrainProg", () => terrainProg, __ro("terrainProg"))
  __def("thermalErode", () => thermalErode, __ro("thermalErode"))
  __def("$", () => $, __ro("$"))
  __def("curWaterIce", () => curWaterIce, __ro("curWaterIce"))
  __def("fieldRange", () => fieldRange, __ro("fieldRange"))
  __def("inputEdge", () => inputEdge, __ro("inputEdge"))
  __def("nodeInputs", () => nodeInputs, __ro("nodeInputs"))
  __def("satComposite", () => satComposite, __ro("satComposite"))
  __def("spReceivers", () => spReceivers, __ro("spReceivers"))
  __def("terrainQuadFitDelta", () => terrainQuadFitDelta, __ro("terrainQuadFitDelta"))
  __def("CANYON_PROCESS", () => CANYON_PROCESS, __ro("CANYON_PROCESS"))
  __def("clamp", () => clamp, __ro("clamp"))
  __def("erosion2Field", () => erosion2Field, __ro("erosion2Field"))
  __def("gpuFbm", () => gpuFbm, __ro("gpuFbm"))
  __def("gpuHydraulicDroplets", () => gpuHydraulicDroplets, __ro("gpuHydraulicDroplets"))
  __def("gpuReady", () => gpuReady, __ro("gpuReady"))
  __def("nearestUpstreamNode", () => nearestUpstreamNode, __ro("nearestUpstreamNode"))
  __def("nodeOutputs", () => nodeOutputs, __ro("nodeOutputs"))
  __def("SATMAPS", () => SATMAPS, __ro("SATMAPS"))
  __def("SUBGRAPHS", () => SUBGRAPHS, __ro("SUBGRAPHS"))
  __def("syncWindReadout", () => syncWindReadout, __ro("syncWindReadout"))
  __def("waterProg", () => waterProg, __ro("waterProg"))
  __def("bakeThumb", () => bakeThumb, __ro("bakeThumb"))
  __def("canyonCacheKey", () => canyonCacheKey, __ro("canyonCacheKey"))
  __def("curSolidSurfaceY", () => curSolidSurfaceY, __ro("curSolidSurfaceY"))
  __def("documentSamples", () => documentSamples, __ro("documentSamples"))
  __def("exactChain", () => exactChain, __ro("exactChain"))
  __def("gpuDropletsReady", () => gpuDropletsReady, __ro("gpuDropletsReady"))
  __def("linkDrop", () => linkDrop, __ro("linkDrop"))
  __def("nodeH", () => nodeH, __ro("nodeH"))
  __def("previewDetail", () => previewDetail, __ro("previewDetail"))
  __def("PROJECT", () => PROJECT, __ro("PROJECT"))
  __def("refreshPreview", () => refreshPreview, __ro("refreshPreview"))
  __def("warpField", () => warpField, __ro("warpField"))
  __def("weatherColorField", () => weatherColorField, __ro("weatherColorField"))
  __def("windVectorFromField", () => windVectorFromField, __ro("windVectorFromField"))
  __def("applyPreviewDetail", () => applyPreviewDetail, __ro("applyPreviewDetail"))
  __def("bakeCurve", () => bakeCurve, __ro("bakeCurve"))
  __def("buildSatLUT", () => buildSatLUT, __ro("buildSatLUT"))
  __def("cameraEye", () => cameraEye, __ro("cameraEye"))
  __def("curIceSnowSurfaceY", () => curIceSnowSurfaceY, __ro("curIceSnowSurfaceY"))
  __def("curSnowDepthM", () => curSnowDepthM, __ro("curSnowDepthM"))
  __def("curSurfaceY", () => curSurfaceY, __ro("curSurfaceY"))
  __def("curvatureField", () => curvatureField, __ro("curvatureField"))
  __def("d8Accumulation", () => d8Accumulation, __ro("d8Accumulation"))
  __def("defaultGraph", () => defaultGraph, __ro("defaultGraph"))
  __def("drawGraph", () => drawGraph, __ro("drawGraph"))
  __def("edgeByKey", () => edgeByKey, __ro("edgeByKey"))
  __def("evalExact", () => evalExact, __ro("evalExact"))
  __def("hexNb", () => hexNb, __ro("hexNb"))
  __def("hydraulicErode", () => hydraulicErode, __ro("hydraulicErode"))
  __def("organizeGraph", () => organizeGraph, __ro("organizeGraph"))
  __def("portAt", () => portAt, __ro("portAt"))
  __def("previewCreation", () => previewCreation, __ro("previewCreation"))
  __def("pushUndo", () => pushUndo, __ro("pushUndo"))
  __def("snoise", () => snoise, __ro("snoise"))
  __def("syncCompass", () => syncCompass, __ro("syncCompass"))
  __def("USE_DEFERRED", () => USE_DEFERRED, __ro("USE_DEFERRED"))
  __def("waterMaskProg", () => waterMaskProg, __ro("waterMaskProg"))
  __def("blendFields", () => blendFields, __ro("blendFields"))
  __def("blurField", () => blurField, __ro("blurField"))
  __def("buildField", () => buildField, __ro("buildField"))
  __def("canyonBeds", () => canyonBeds, __ro("canyonBeds"))
  __def("CAT", () => CAT, __ro("CAT"))
  __def("colorErodeField", () => colorErodeField, __ro("colorErodeField"))
  __def("combine", () => combine, __ro("combine"))
  __def("confirmNewTerrain", () => confirmNewTerrain, __ro("confirmNewTerrain"))
  __def("curveFromExponent", () => curveFromExponent, __ro("curveFromExponent"))
  __def("curWaterLiquid", () => curWaterLiquid, __ro("curWaterLiquid"))
  __def("DOMAIN", () => DOMAIN, __ro("DOMAIN"))
  __def("drawMaskField", () => drawMaskField, __ro("drawMaskField"))
  __def("drawTarget", () => drawTarget, __ro("drawTarget"))
  __def("duplicateSel", () => duplicateSel, __ro("duplicateSel"))
  __def("edgeKey", () => edgeKey, __ro("edgeKey"))
  __def("encodeTemperatureC", () => encodeTemperatureC, __ro("encodeTemperatureC"))
  __def("gpuHydraulicPipes", () => gpuHydraulicPipes, __ro("gpuHydraulicPipes"))
  __def("gpuThermal", () => gpuThermal, __ro("gpuThermal"))
  __def("HEX_SQUARE_WORLD", () => HEX_SQUARE_WORLD, __ro("HEX_SQUARE_WORLD"))
  __def("maskApply", () => maskApply, __ro("maskApply"))
  __def("normalize", () => normalize, __ro("normalize"))
  __def("occlusionField", () => occlusionField, __ro("occlusionField"))
  __def("outSlotForEdge", () => outSlotForEdge, __ro("outSlotForEdge"))
  __def("propagateFieldMetadata", () => propagateFieldMetadata, __ro("propagateFieldMetadata"))
  __def("renderLook", () => renderLook, __ro("renderLook"))
  __def("satLayerColor", () => satLayerColor, __ro("satLayerColor"))
  __def("sculptField", () => sculptField, __ro("sculptField"))
  __def("setDocumentSamples", () => setDocumentSamples, __ro("setDocumentSamples"))
  __def("slopeOf", () => slopeOf, __ro("slopeOf"))
  __def("smax", () => smax, __ro("smax"))
  __def("smin", () => smin, __ro("smin"))
  __def("syncClimateReadout", () => syncClimateReadout, __ro("syncClimateReadout"))
  __def("tagTemperatureField", () => tagTemperatureField, __ro("tagTemperatureField"))
  __def("tagWindField", () => tagWindField, __ro("tagWindField"))
  __def("temperatureCFromField", () => temperatureCFromField, __ro("temperatureCFromField"))
  __def("widthForLength", () => widthForLength, __ro("widthForLength"))
  __def("wirePoint", () => wirePoint, __ro("wirePoint"))
  __def("xfMul", () => xfMul, __ro("xfMul"))
  __def("atFeatureScale", () => atFeatureScale, __ro("atFeatureScale"))
  __def("buildWireIndex", () => buildWireIndex, __ro("buildWireIndex"))
  __def("cameraNear", () => cameraNear, __ro("cameraNear"))
  __def("CANYON_STYLE_ID", () => CANYON_STYLE_ID, __ro("CANYON_STYLE_ID"))
  __def("canyonField", () => canyonField, __ro("canyonField"))
  __def("curveAt", () => curveAt, __ro("curveAt"))
  __def("FEASIBILITY_API", () => FEASIBILITY_API, __ro("FEASIBILITY_API"))
  __def("gbuf", () => gbuf, __ro("gbuf"))
  __def("gpuHydraulicCombined", () => gpuHydraulicCombined, __ro("gpuHydraulicCombined"))
  __def("gpuWarp", () => gpuWarp, __ro("gpuWarp"))
  __def("graphIdsFrom", () => graphIdsFrom, __ro("graphIdsFrom"))
  __def("hydroFixField", () => hydroFixField, __ro("hydroFixField"))
  __def("lastFallbackClimateSig", () => lastFallbackClimateSig, __ro("lastFallbackClimateSig"))
  __def("latticeRows", () => latticeRows, __ro("latticeRows"))
  __def("layer0Graph", () => layer0Graph, __ro("layer0Graph"))
  __def("loadImageAsDEM", () => loadImageAsDEM, __ro("loadImageAsDEM"))
  __def("metricHeightField", () => metricHeightField, __ro("metricHeightField"))
  __def("openDrawEditor", () => openDrawEditor, __ro("openDrawEditor"))
  __def("openNewTerrainDialog", () => openNewTerrainDialog, __ro("openNewTerrainDialog"))
  __def("parseLayout", () => parseLayout, __ro("parseLayout"))
  __def("REAL_DEM_SAMPLE", () => REAL_DEM_SAMPLE, __ro("REAL_DEM_SAMPLE"))
  __def("resampleTo", () => resampleTo, __ro("resampleTo"))
  __def("SEED_MAX", () => SEED_MAX, __ro("SEED_MAX"))
  __def("SHADE", () => SHADE, __ro("SHADE"))
  __def("SKIRT_PRESETS", () => SKIRT_PRESETS, __ro("SKIRT_PRESETS"))
  __def("smooth", () => smooth, __ro("smooth"))
  __def("snapshotIsEditorOnly", () => snapshotIsEditorOnly, __ro("snapshotIsEditorOnly"))
  __def("surfaceHeight", () => surfaceHeight, __ro("surfaceHeight"))
  __def("syncDetailReadout", () => syncDetailReadout, __ro("syncDetailReadout"))
  __def("thermalErodeHex", () => thermalErodeHex, __ro("thermalErodeHex"))
  __def("viewportHeightFrame", () => viewportHeightFrame, __ro("viewportHeightFrame"))
  __def("WIND_MAX_MPS", () => WIND_MAX_MPS, __ro("WIND_MAX_MPS"))
  __def("wireVerdict", () => wireVerdict, __ro("wireVerdict"))
}
// ==== TEST BRIDGE END ====



