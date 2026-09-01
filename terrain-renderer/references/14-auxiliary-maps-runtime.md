---
# --- okf v0.2, written by tools/okf_apply.py -----------------------
type: Reference
title: "Auxiliary maps at runtime: consuming the generator's field registry"
description: "Auxiliary maps at runtime: consuming the generator field registry without re-deriving it in the sampling shader."
tags: [terrain, maps, runtime, handoff]
status: stable
generated: { by: process:claude-code, at: 2026-08-04T19:10:29Z }
# --- end okf v0.2 ----------------------------------------------------
---
# Auxiliary maps at runtime: consuming the generator's field registry

terrain-architect `27` ends at the wire: a registry of raw R32F cause-maps — climate, geology,
hydrology, geometry analysis — shipped with units, manifests, and the prohibition on baked
materials. This chapter is the consumer's manual: what a renderer *does* with each map, how the
registry is packed and kept resident on the GPU, which maps are derived in-shader instead of
shipped, and how one field fans out into materials, VFX, audio, physics, and gameplay without the
systems drifting apart. Runtime *state* (snow, wetness deltas, deformation) is `13`; this chapter
owns the immutable baked substrate those deltas composite over, and the contract between the two.

Contents: [Consumption doctrine](#consumption-doctrine) ·
[The registry, consumer-side](#the-registry-consumer-side) ·
[GPU packing & residency](#gpu-packing--residency) ·
[Derived at runtime vs shipped](#derived-at-runtime-vs-shipped) ·
[Cross-system fan-out](#cross-system-fan-out) ·
[Dynamic writeback: the overlay stack](#dynamic-writeback-the-overlay-stack) ·
[The tri-fold ladder](#the-tri-fold-ladder) · [Pitfalls](#pitfalls) ·
[Sources](#sources--provenance)

## Consumption doctrine

**Every auxiliary map is a driver, not a decoration.** A map earns its place in the resident set
(`06`) by driving at least one of: material response (`07`), VFX, vegetation/scatter (`15`),
audio/physics response (`17`), or gameplay logic. A map that nothing samples is dead weight — it
costs streaming bandwidth, cache, and memory on every resident tile forever. Audit this
mechanically: the material system, spawners, and gameplay queries each declare which registry maps
they read; a map with zero declared consumers is deleted from the shipping manifest, not shipped
"in case". (Keep it in the *tool* manifest — `16`'s inspection viewport wants everything.)

**The inverse rule carries equal force: every runtime effect names the map that drives it.** An
effect with no driving field is an effect that fights the world's logic — snow applied by altitude
puts drifts in rain-shadowed basins the generator explicitly kept dry (the Snow Rule of
terrain-architect `27`); puddles placed by artist decal land on convex ridges where water cannot
stand; dust VFX keyed to a biome enum blows through a rainstorm. When a designer asks for an
effect, the first question is "which field says where?" — and if no field says so, the fix is to
extend the generator's contract (SKILL.md Part 2, "the generator's fields are the interface"),
never to invent renderer-side data that the rest of the pipeline cannot see.

This is the render-side half of terrain-architect's Masking Doctrine: the tool ships causes, the
engine computes effects — *per frame, per season, per weather state* — from those causes. The
moment the renderer hardcodes an effect, it has re-frozen a decision the whole handoff exists to
keep liquid.

## The registry, consumer-side

The heart of the chapter. One row per standard map (wire names from terrain-architect `27`);
formats are *post-quantization shipping* formats — the generator computed them R32F, quantized
once at export, and the manifest declares range and encoding. Lifecycle: **static** (baked, never
changes), **slow** (recomputed on world edits / season ticks, tool-side or cook-side), **dynamic**
(runtime deltas exist — but always in overlays, below, never in these textures).

| Map | Render-side consumers | Sampling context | Shipped format (typical) | Lifecycle |
|---|---|---|---|---|
| `height` | Everything: geometry (`01`/`02`), occlusion max-mip (`08`), shadow ray-march (`10`), water shoreline (`12`), placement (`15`), collision cook (`17`) | vertex/compute; CPU for gameplay queries | R16 unorm + per-tile min/max rescale, or R32F near-field; never 8-bit | static (dynamic via `13` deformation overlay) |
| `slope` | Splat selection (`07`), snow/scree gating (`13`), spawner rejection (`15`), AI traversability & vehicle physics (`17`) | pixel (derived) or compute/CPU (shipped copy) | derived in-shader; if shipped: R8 unorm over declared max-angle range | static-derived |
| `curvature` | Exposure/deposit material reads (`07`), detail placement (`15`), flow-line detail (`12`) | pixel/compute | R8 snorm (signed, declared 1/m range) or BC4 pair; R16F if placement thresholds are tight | static |
| `ao` / sky visibility | Ambient term & sky occlusion (`10`), moss/debris "sheltered" mask (`07`), spawner shade bias (`15`) | pixel | R8 unorm / BC4 | static; **slow** on major world edits — a re-carved canyon with stale AO reads wrong forever |
| `insolation` | Snow melt gating (`13`), dry-grass/moss material axes (`07`), vegetation aspect bias (`15`) | pixel/compute | R8 unorm, declared range (may exceed 1) | static / seasonal slow |
| `wetness` (state + TWI companion) | Darkening/roughness response (`07`), puddle placement (`13`), mud & reed materials, footstep audio + friction (`17`), spawner gate (`15`) | pixel; CPU/compute for audio-physics | R8 unorm **with dithered quantization** (banding pitfall below); state and TWI as separate channels | static base; **dynamic** via `13` wetness overlay |
| `flowVelocity` | Flow-mapped water shading (`12`), **wave–current interaction in the shore-wave band** (`12` — steepen/force-break against opposing flow), foam/spray emitters, ripple advection, kayak/swim physics current (`17`) | pixel (water material), compute (VFX), CPU (physics) | RG16F world-space m/s; never 8-bit, never normalized (speed is data) | static (river regime) **plus the nearshore circulation — longshore current, rip jets, inlet jets**; tidal-inlet jets reverse with the tide, so treat them as slow-dynamic, not static |
| `waterDepth` / `waterSurface` | Absorption/scattering depth fade, shoreline blend (`12`), wade/swim state & buoyancy (`17`), audio (splash class) | pixel + CPU | R16F meters; surface height same format as `height` | static; dynamic water sims own their own targets (`12`) |
| `waterDepthFiltered` | Shore-wave amplitude/wavelength response and the break mask (`12`) — **must** be the smoothed copy, at roughly the modulated wavelength scale; raw bathymetry noise makes the break line dither | pixel/compute | R16F meters; a mip/blur of `waterDepth`, shipped or derived at load | static-derived (rebuild when bathymetry changes) |
| `shoreWaveTravelTime` (τ) | Shore-wave phase — refracted crests, headland wrap, focusing (`12`) | pixel/compute | R16F seconds (or normalized period count); one channel | static-derived: eikonal solve baked at import/cook from bathymetry; rebuild on bathymetry edits |
| `breakerClass` / beach-slope mask | Breaker type selection — spilling vs plunging vs surging (`12`), keeps beach-break foam off cliff faces | pixel | R8 unorm (Iribarren-banded class or raw slope over a declared range) | static-derived from slope + grain size |
| `soilDepth` | Rock-vs-cover material break (`07`), digging/deformation depth budget (`13`/`17`), rooting gate for trees (`15`) | pixel/compute; CPU for dig queries | R8 unorm over declared max (e.g. 0–4 m) or R16F if dug into | static; dynamic via crater/dig overlay |
| `strataHardness` / lithology | Cliff-band material selection (`07`), impact decals & destruction response (`17`), pick/mining gameplay | pixel; CPU | R8 unorm normalized resistance; lithology class as ID map (point-sampled, below) | static |
| `temperature` | Snowline/freeze thresholds (`13`), material frost axis (`07`), breath/exposure gameplay VFX, audio ambience | pixel/compute/CPU | R16F °C, or R8 over declared range **only if nothing thresholds it** (terraced-snowline pitfall) | static base; season/time-of-day modulated in-shader from declared curves |
| `moisture` | Biome material axes (`07`), vegetation density (`15`), dust VFX gating (dry + wind), fire spread gameplay | pixel/compute | R8 unorm (normalized companion; absolute mm/yr stays tool-side) | static / seasonal slow |
| `windVector` | Foliage sway & grass response (`15`), particle advection, cloth, snow-drift alignment (`13`), wave fetch (`12`), audio wind beds | vertex (sway), compute (VFX), CPU (audio) | RG16F m/s; renormalize *direction* after filtering if consumed as direction | static regional field; gusts = runtime modulation layered on top, never written into it |
| `snowPotential` / `snowDepth₀` | Snow coverage ceiling and initial pack (`13`), snow material blend (`07`), footstep audio class (`17`) | pixel/compute | potential R8; initial depth R16F (sim consumer — architect `27` forbids 8-bit for simulated maps) | static (potential); `13` owns the dynamic pack |
| `sedimentDepth` | Deposit materials — silt fans, gravel bars (`07`), footstep/particle class (`17`), spawner substrate | pixel | R8 unorm over declared max | static |
| biome / material ID | Splat-set selection & VT shading (`07`), spawner tables (`15`), audio ambience zone, minimap — **convenience product**: raw fields must ship alongside (architect `27`) | pixel (point-sampled), CPU | R8/R16 uint, **point sampling, no standard mips** (ID rules below) | static |

Reading the table is a review act: for each map your project ships, check every listed consumer
either exists or is consciously waived; for each runtime effect in the game, find its row.

Sampling-context discipline, since the column hides a contract: **pixel** consumers ride texture
units and mips and are cheap per-read; **vertex** consumers (sway, displacement) must sample the
same LOD band across all passes or shadows diverge from color (`01`'s pass-consistency rule);
**compute** consumers (spawners, VFX) batch and amortize — never per-frame-full-world; **CPU**
consumers read the mirror, never the GPU texture (readback pitfall, below). A map acquiring a new
consumer class is a cook change (mirror resolution, mip policy), not just a new sample call.

## GPU packing & residency

### Channel packing

The generator ships one file per map; the renderer repacks at cook into few textures, packing
**correlated-by-consumer** maps together so one fetch feeds one decision:

- **Splat-driver pack** (RGBA8): e.g. `moisture`, `wetness`, `soilDepth`, `sedimentDepth` — the
  material graph's layer-weight derivation reads one sample (`07`).
- **Climate pack** (RGBA8 or RGBA16F if temperature thresholds): `temperature`, `insolation`,
  `snowPotential`, `strataHardness`.
- **Vector pack**: `windVector` and `flowVelocity` stay RG16F, separate — different consumers,
  different residency (flow only near water, `12`).
- BC compression where it survives: BC4 for lone unorm channels (AO), BC5 for well-behaved vector
  pairs, BC7 for the 8-bit packs — but **never block-compress ID maps** (palette interpolation
  invents fractional IDs) and never BC anything the CPU also reads (keep the CPU mirror
  uncompressed, below).

The 8-bit / 16-bit line is the same doctrine as `13`: **[0,1] modulation factors survive 8 bits
(dithered); anything differentiated, displaced, thresholded against a physical value, or consumed
by simulation needs 16.** Height feeding normals, water depth feeding Beer–Lambert, temperature
feeding a freeze threshold, all vectors: 16F. Wetness darkening an albedo: 8 + dither.

### Residency: aux rides the tile

Auxiliary tiles share the height tile's grid, apron, and residency state machine (`06`): one
streaming decision per tile loads height + aux pack together, one eviction drops them together.
Per-map residency ("stream wetness separately") buys almost nothing and creates the worst bug
class: a resident tile whose materials sample a non-resident wetness map. Two sanctioned
refinements: (a) a **distance-tiered manifest** — far LODs ship only the maps far shading reads
(AO, moisture, biome ID), near LODs the full pack; declare the tier split in the cook, assert it
in `11`; (b) routing aux channels **through virtual texturing** (`07`): SVT page payloads carry
aux channels alongside albedo so residency is feedback-driven per page; and RVT caches the
*output* of aux-driven shading — in which case the aux maps are sampled at RVT page render time,
not per screen pixel. The `13` rule still binds: only static aux contributions may be baked into
cached pages; dynamic state composites over the page sample, or every weather tick invalidates
the cache.

Implementation shape: per-tile texture arrays (or one physical atlas) indexed by the tile table
`06` already maintains; the aux pack is extra array layers on the same index. CPU-side consumers
(gameplay, audio, physics) read a **CPU mirror** kept at coarser resolution — same data, same
quantization, resident by the collision ring rules of `06`, never by render LOD.

### Mips: when filtering is wrong

Cause-maps get mipped for the same reason albedo does — distant pixels must not shimmer (`11`) —
but three families break under naive box filtering:

- **ID maps** (biome, lithology class): averaging IDs is meaningless — biome 3 (tundra) blended
  with biome 5 (marsh) is not biome 4 (desert). Point-sample, and build mips by **majority vote or
  nearest-parent**, never averaging. In-shader, select ID at a single level; blend the *resolved
  materials* of neighboring IDs, never the IDs (`07`'s ID-map machinery).
- **Vector maps** (wind, flow): filtering averages opposing vectors toward zero — a mip of a
  converging valley wind reads as calm. Where the consumer wants *direction* (sway, drift
  alignment), renormalize after the fetch and carry speed separately; where it wants *transport*
  (advection), the averaged vector is actually the correct coarse flux — know which one each
  consumer is.

```hlsl
float2 v  = windTex.Sample(bilinear, uv).xy;     // filtered: direction bent, speed shrunk
float  sp = windSpeedTex.Sample(bilinear, uv).x; // speed mipped separately (scalar avg is fine)
float2 dir = (dot(v, v) > 1e-6) ? normalize(v) : float2(0, 0);
float2 wind = dir * sp;                          // renormalized direction × preserved speed
```

- **Height for occlusion**: needs a **max** mip pyramid, not average (`08`); water depth used for
  "can I stand here" wants **min**. Standard average mips answer shading questions only.

## Derived at runtime vs shipped

The generator's own doctrine decides this split (terrain-architect `27`, state vs derived +
GLOBAL nodes): anything that is a *local* pure function of fields already on the GPU may be
derived in-shader; anything *global* or *path-dependent* must ship, because no pixel shader can
see beyond its footprint and no analysis pass can recover simulation history.

| Quantity | Derive in-shader | Ship baked | Why |
|---|---|---|---|
| Slope / aspect | ✓ (height derivatives / 2 extra taps) | optional CPU copy | Local; free; but MUST derive from full-res height data, not LOD'd geometry (consistency rule) |
| Normals | ✓ per band (`10`) | far-field normal map common | Local; band ownership per `10` |
| Detail curvature (Laplacian) | ✓ 4-tap for micro detail | — | Local, cheap, shading-band only |
| Analysis curvature (placement/material identity) | ✗ | ✓ | Thresholded by gameplay/spawners — must be the one canonical copy |
| AO / sky visibility | ✗ (SSAO is not terrain AO) | ✓ | Global horizon integration; screen-space AO misses everything off-screen (`10`) |
| Flow accumulation | ✗ | ✓ | The canonical GLOBAL: every cell depends on its entire upstream catchment |
| Wetness index / TWI | ✗ | ✓ | Downstream of flow accumulation; locally underivable by construction |
| Climate (temperature, moisture, wind) | ✗ (modulate, don't re-derive) | ✓ | Simulation output; in-shader you may *modulate* (season curve on temperature), never re-simulate |
| Soil, sediment, snow initial state | ✗ | ✓ | Path-dependent state maps — the geometry does not contain them (architect `27`) |

Cost/quality across the split: deriving slope costs ~2 extra height taps and beats a shipped R8
slope map on both memory and aliasing (it tracks the height mip chain exactly); a 4-tap Laplacian
costs the same and is *worse* than shipped curvature for anything thresholded — the cheap kernel
sees one texel radius, the generator's Zevenbergen–Thorne pass saw the world. The heuristic:
in-shader derivation wins when the shipped alternative would just be a cache of the same local
taps; shipping wins the moment the computation has a horizon larger than the shader's footprint
or feeds a threshold. When in doubt, ship — a redundant 8-bit map costs kilobytes per tile; a
divergent re-derivation costs a bug class (below).

**The consistency rule** — the sharpest edge in this chapter: **gameplay and rendering read the
same data.** If the shader derives slope from the currently-rendered LOD mesh while the spawner
reads baked full-res slope, grass grows on cliffs at distance and pops off as you approach; if
footstep audio re-derives "wet" from its own rain timer while the material samples the wetness
composite, feet splash on dry-looking ground (`13` names the same rule from the state side).
In-shader derivation is legal only when (a) the input is the same shipped field gameplay reads,
at full data resolution, or (b) the output is strictly shading-band with no gameplay twin. When
a quantity has both a render consumer and a gameplay consumer, there is exactly one canonical
copy, and both sample it — GPU texture and CPU mirror of the *same cooked data*, never two
independent derivations.

## Cross-system fan-out

One map, many systems — this is where the registry pays for itself, and where single-source-of-
truth discipline is enforced or lost. The shipped pattern (Horizon Zero Dawn's GPU placement,
Ghost Recon Wildlands' terrain-data-driven tools, Far Cry 5's Houdini biome pipeline — sources
below) is a rule graph evaluating over exactly these fields; the renderer's material graph, the
VFX system, and gameplay queries are the same idea at different rates.

| Consumer class | Reads | Rate / context |
|---|---|---|
| Material graphs (`07`) | splat-driver + climate packs, curvature, AO | per pixel (or per RVT page render) |
| VFX | wetness (rain splash rate), moisture+wind (dust), temperature (breath, heat shimmer), flow (spray) | per emitter tick, compute or CPU |
| Audio | splat/ID + wetness + snow (footstep bank), wind (ambience bed), water depth (splash class) | per event / per second, CPU mirror |
| Physics (`17`) | material ID + wetness + snow depth → friction table; flow velocity → current force | per contact, CPU mirror |
| AI / gameplay | slope (traversability), water depth (wade/swim), soil (dig), temperature (survival) | per query, CPU mirror |
| Vegetation (`15`) | moisture, soil, insolation, slope, wetness | placement compute, amortized |

**Worked chain — one wetness value, six systems, zero contradictions:**

```hlsl
// one canonical composite, built once (13's overlay over the baked base):
w = compose(bakedWetness(uv), rainOverlay(uv));      // [0,1], same value GPU + CPU mirror

albedo    *= lerp(1.0, 1.0 - porosityDarken(mat), w);   // material: dampening (07 / Lagarde)
roughness  = lerp(roughness, waterRoughness, puddleMask(w));  // material: puddle gloss
rippleRate = rainIntensity * saturate(w * 2.0);          // VFX: ripples only where wet
splashVFX  = (w > 0.6);                                   // VFX: mud splash class
footBank   = footstepTable[matId][w > 0.5];               // audio: dry/wet variant  (CPU)
friction   = baseFriction[matId] * (1.0 - 0.4 * w);       // physics: braking distance (CPU)
```

Every line names `w`; no line invents its own rain logic. When the storm ends and the `13` drying
pass decays the overlay, the darkening, the gloss, the ripples, the squelch, and the skid distance
all recover *together*, because there is nothing else to recover. That coherence — effects agreeing
with each other because they share a cause — is what players read as "the world is real", and it is
unachievable when each system carries a private copy of the weather.

### Effect ownership and pass boundary

The registry connects systems; it does not erase ownership. Every effect has one owner and every
consumer reads the same fields:

| Effect | Owner | Terrain's responsibility |
|---|---|---|
| Base terrain color/normal | Terrain material / visibility resolve (`07`, `08`) | Resolve stable surface inputs |
| Roads and persistent stamps | RVT/material injection with replay (`17`) | Provide page-space surface and ordering |
| Snow, wetness, mud, deformation | Surface-state compute + terrain material (`13`) | Apply after stable RVT/base resolve |
| Water surface, ripples, shore optics | Water renderer (`12`) | Provide terrain depth/bathymetry/shore fields |
| Falling rain/snow, spray, airborne dust | VFX/particle system | Publish scene depth, top-down coverage, collision surface, flow/wind drivers |
| Screen/lens droplets, heat distortion | PostFX | Publish wetness/intensity/depth where the effect needs masks |
| Rayleigh/Mie atmosphere, aerial perspective, volumetric fog | Atmosphere/lighting (`10`) | Composite terrain with the one shared atmosphere state |

**Depth ownership chain:** opaque terrain writes depth; water writes or prewrites its chosen depth
policy (`12`); VFX soft-particles consume that depth for collision/soft clipping; PostFX reads the
final scene depth. Falling precipitation inside caves is therefore a VFX coverage bug fed by a
missing/ignored terrain depth contract, not a reason to move rain particles into the terrain
module.

## Dynamic writeback: the overlay stack

Some systems write surface state at runtime: deformation and weather (`13`), scorch/burn from
fire, craters and structural damage (`17`), gameplay terraforming. The discipline is absolute:

**Runtime deltas live in separate overlay targets composited over immutable baked data. Streamed
source tiles are never mutated.** Three reasons, each fatal alone: (1) *re-streaming resurrects
stale data* — evict a mutated tile and the next load replays the pristine bake over the player's
crater, or worse, a half-written one; (2) *cache coherence* — baked tiles feed RVT pages, CPU
mirrors, and collision cooks; mutating one copy desynchronizes the rest; (3) *save games* — a
save records overlay contents (small, delta-only); it cannot practically record "the world,
re-baked".

The compositing-order contract, fixed and documented, evaluated the same way by every reader:

```
resolved(x) = clamp( baked(x)                       // immutable, streamed (06)
            ∘ persistentDeltas(x)                   // craters, scorch — saved, paged by tile
            ∘ weatherState(x)                       // 13's camera rings: snow delta, wetness
            ∘ instantaneous(x) )                    // this-frame deformation
```

Later layers see earlier results (snow falls *into* the crater; scorch dries *under* the rain
rule, not over it). Each layer has one writer per frame (`13`); readers — material, VFX, CPU
mirror — sample only the resolved product, never a partial stack. Persistent deltas page by tile
key alongside `06` streaming but in their own store; weather state re-derives from the weather
timeline rather than being saved (`13`); the instantaneous layer is never persisted. An overlay
that writes outside the baked map's physical envelope (snow where `snowPotential` is zero, water
above local `waterSurface` capacity) is clamped by the baked field — the bake is the law, the
overlay is the weather.

## The tri-fold ladder

| Tier | Registry consumed | Storage | Fan-out |
|---|---|---|---|
| Indie / baseline | `height` + slope/normals derived + one splat weightmap (may be cooked from moisture/slope offline) + optional AO | a handful of textures, no packs; whole-world or simple tiles | material only; audio/physics from material ID enum |
| Terrain-tool viewport (`16`) | **everything the tool produces**, uncompressed R32F, no cook | per-map textures, no packing (inspectability beats bandwidth) | false-color inspection layers per map, hover readout with units, diff views — the viewport is the registry's debugger, not a game |
| AAA open world | full registry, cooked packs, distance-tiered manifest | VT-carried aux channels, per-tile arrays on `06`, CPU mirrors, overlay stack | materials + VFX + audio + physics + AI + placement, all naming their driver maps; dead-map audit in CI (`11`) |

The ladder is monotone: the indie tier is the AAA tier with maps deleted — not a different
architecture. Cooking one splat map offline from moisture+slope is fine *at that tier* because
nothing dynamic reads the causes; the moment weather or seasons enter the design, the causes must
survive to runtime, which is the whole argument of terrain-architect `27`.

## Pitfalls

- **Filtered biome-ID bleeding.** Bilinear or mipped ID maps produce fractional IDs at region
  borders → one-texel rings of "desert" between tundra and marsh. Point-sample; majority-vote
  mips; blend resolved materials, not IDs (`07`).
- **Quantization banding in wetness/temperature ramps.** 8-bit wetness driving a smooth darkening
  reads as contour bands on gentle gradients; 8-bit temperature under a freeze threshold produces
  a terraced snowline. Dither at quantization, or spend 16 bits where a threshold or derivative
  consumes the map.
- **Aux/splat resolution mismatch halos.** Wetness at 1 m driving puddles over 10 cm material
  detail leaves soft halos crossing material boundaries; sharpen with a detail threshold in the
  material, or accept and art-direct — but never upsample the cause map and call it data.
- **Unrenormalized filtered vectors.** Mipped/bilinear wind and flow shrink and bend: distant
  grass stops swaying, drift alignment rotates at tile borders. Split direction/speed or
  renormalize per the code above.
- **Gameplay/render divergence.** Shader-derived slope vs baked gameplay slope; VFX rain timers
  vs wetness composite. One canonical copy per quantity; CPU mirror of the same cooked data.
- **Dead resident maps.** Registry maps streamed on every tile that no shipped system samples —
  silent memory tax (`06`). CI audit: manifest maps × declared consumers, zero-consumer maps fail
  the build (`11`).
- **Overlay-order bugs.** Weather composited under persistent deltas → rain darkens the ground
  *under* the scorch; deformation applied to baked height after the CPU mirror was built → feet
  float above trails. One documented order, one composite, all readers downstream of it.
- **Dynamic state baked into VT/RVT pages.** Global weather change → full cache invalidation spike
  or stale pages (`07`, `13`). Static aux into pages; dynamic over them.
- **Mutating streamed tiles in place.** Works until the first evict/re-stream resurrects pre-crater
  terrain in front of the player. Overlays, always — no exceptions for "small" edits.
- **Readback stalls for CPU consumers.** Sampling GPU aux textures synchronously for a footstep →
  pipeline stall (`08`'s readback discipline). CPU consumers read the CPU mirror; only overlay
  state genuinely born on the GPU is read back, async and frames-late, with the mirror updated on
  arrival.

## Sources & provenance

| Claim | Tier | URL |
|---|---|---|
| The registry itself — map list, units, R32F/quantize-once, cause-not-effect, state-vs-derived, GLOBAL doctrine, Snow Rule | **D** | terrain-architect `references/27-engine-data-handoff.md` (in-repo) |
| Rule-graph placement/fan-out over terrain fields at runtime — "GPU-Based Run-Time Procedural Placement in Horizon Zero Dawn" (Jaap van Muijden, GDC 2017) | **T** | https://gdcvault.com/play/1024700/GPU-Based-Run-Time-Procedural |
| Terrain data driving materials/tools across systems — "Ghost Recon Wildlands: Terrain Tools and Technology" (Werlé & Martinez, GDC 2017) | **T** | https://www.gdcvault.com/play/1024029/-Ghost-Recon-Wildlands-Terrain |
| Biome/water/cliff pipelines generating engine-consumed maps — "Procedural World Generation of Far Cry 5" (Etienne Carrier, GDC 2018; third-party notes) | **T** | https://tools.engineer/gdc2018-procedural-world-generation-of-far-cry-5 |
| In-shader material resolution from masks/slope rather than baked textures — Andersson, "Terrain Rendering in Frostbite Using Procedural Shader Splatting" (SIGGRAPH 2007 course) | **T/P** | https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/chapter5-andersson-terrain-rendering-in-frostbite.pdf |
| RVT as cached output of aux-driven shading; page-render-time sampling | **D/N** | https://dev.epicgames.com/documentation/unreal-engine/runtime-virtual-texturing-in-unreal-engine |
| Porosity darkening / roughness drop under wetness (the material end of the wetness chain) — Lagarde, "Water drop 3a – Physically based wet surfaces" | **F/D** | https://seblagarde.wordpress.com/2013/03/19/water-drop-3a-physically-based-wet-surfaces/ |
| Wind fields driving per-blade grass response — "Procedural Grass in Ghost of Tsushima" (Eric Wohllaib, GDC 2021) | **T** | https://gdcvault.com/play/1027033/Advanced-Graphics-Summit-Procedural-Grass |
| BC4/BC5/BC7 behavior, single/dual-channel compression suitability | **D** | https://learn.microsoft.com/en-us/windows/win32/direct3d11/texture-block-compression-in-direct3d-11 |
| Overlay-over-immutable-bake architecture; 8-bit-modulation / 16-bit-differentiated rule | **F** | sibling doctrine, `13` (shipped-title T-tier sources cited there) |
| Channel-packing groupings, distance-tiered manifests, dead-map CI audit, majority-vote ID mips, direction/speed vector split | **F** | production practice; no single canonical citation — assert per project (`11`) |
| Specific format choices per map (R16 height, RG16F vectors, R8+dither modulators) | **F** | order-of-standard-practice; the binding rule is architect `27`'s "never quantize sim-consumed maps" |
