# Snow, weather, and dynamic surface state

The generator bakes where snow and moisture *can* exist — terrain-architect `13` computes the
climate, its `27` ships the potential fields under the Snow Rule. The renderer owns what actually
happens at runtime: snow accumulating over minutes, boots carving trails, rain wetting the ground,
puddles rising, everything drying and melting back. This chapter owns that runtime state machine:
its storage (world-space state layers over the `07` material stack), its writers (deformers,
weather), and its readers (displacement, shading). Microfacet and BRDF math for wet/snow surfaces
routes to physically-based-rendering; water surfaces themselves are `12`; the map registry these
systems consume is `14`.

Contents: [Historical seasons/snow ladder](#the-historical-ladder-winter-maps-to-transient-physical-state) ·
[The state-layer model](#the-state-layer-model) ·
[Deformable snow, mud, and sand](#deformable-snow-mud-and-sand) ·
[Accumulation and melt](#accumulation-and-melt) · [Snow shading](#snow-shading) ·
[Wetness and rain](#wetness-and-rain) · [Wind and storms](#wind-and-storms-as-surface-state) ·
[Persistence and streaming](#persistence-and-streaming) · [Pitfalls](#pitfalls) ·
[Sources](#sources--provenance)

## The historical ladder: winter maps to transient physical state

Snow and seasons expose the difference between **appearance** and **state**:

| Era | Technique | What it solved | Why it failed |
|---|---|---|---|
| Separate summer/winter maps | Swap a second authored albedo set | Cheap global season art direction | Doubled content, hard-switched or cross-faded the whole world, carried no accumulation, melt, shelter, or deformation state |
| Up-vector snow shader | Blend white albedo on `N·up`, sometimes altitude-gated | Removed the second texture set and made coverage react to slope | Painted every upward face equally, ignored moisture/shelter/temperature, and remained "white material" rather than material thickness |
| Baked snow masks/material layers | Generator-derived snow potential, height/slope/temperature masks | Put snow in climatically plausible places and improved crevice blending | Still described only where snow *can* exist; global amounts and footprints remained ad hoc |
| Transient layered snow | Baked potential envelope + runtime depth/compaction/melt/deformation targets | Represents snow as a physical, changing layer with history | Requires explicit cache, streaming, and gameplay-authority boundaries — the subject of this chapter |

**Snow is a transient thickness field, not white albedo paint.** Albedo is one output of the
layer. Depth drives displacement, crevice fill, compaction, trail rims, optical state, and melt
into wetness. The camera-following deformation targets below are deliberately local and sparse:
they preserve high-frequency history without mutating the global base heightfield.

## The state-layer model

### Static says "possible", runtime says "current"

Dynamic surface state lives in a small set of **world-space runtime render targets** layered over
the static material stack. The baked fields from terrain-architect `27` (`snowDepth` initial
state, `snowPotential`, `wetness`, `moisture`, `ao`, `insolation`) are immutable and streamed like
any tile payload (`06`); the runtime targets carry only the *delta from that baseline*: how much
extra snow the current storm has added, how deep the player's trail is carved, how wet the rain
has made this square meter. Two consequences fall out immediately:

- **Baked data is never mutated.** Streaming a tile back in must not resurrect pre-storm state,
  and evicting one must not erase the player's trail. Deltas live in their own targets with their
  own lifecycle (the overlay doctrine, formalized in `14`).
- **State composes OVER the resolved base material.** The `07` pipeline resolves splats, tiling
  breakup, and VT lookups first; state layers then modify the resolved surface (lerp to snow,
  darken for wetness, displace for deformation). Never composite dynamic state *into* RVT/VT
  pages — a global snow amount baked into cached pages means a full cache invalidation every time
  it snows harder (`07` names this pitfall; this chapter is where the correct architecture lives).

**RVT invalidation trap — no exceptions for "slow" seasons.** Season blend, snow amount,
wetness, and accumulation are global/time-varying inputs and therefore never participate in RVT
page generation. Sample the stable RVT base first, then apply these targets. A global state
change must update constants/overlay textures, not dirty the page cache. Local persistent stamps
may invalidate bounded pages through `17`'s replayable stamp list; weather may not.

### Camera-following toroidal targets

The state targets cannot cover the world at useful density, so they follow the camera: a ring (or
2-3 nested rings, clipmap-style) of world-aligned textures whose content scrolls with camera
movement using **toroidal addressing** — on camera motion only the newly exposed L-shaped strip is
written, everything else stays put, and the sampler wraps with `frac()`. This is the clipmap update
discipline of `01`/`07` applied to writable state. The world-to-texel mapping must be **snapped to
the texel grid**, or every camera pan resamples the whole target and the state swims — the same
snapping rule as shadow cascades (`10`).

### The standard target set

| Target | Content | Format | Texel density / extent | Update |
|---|---|---|---|---|
| Deformation height | carve depth into snow/mud/sand + rim bulge | R16F (or 16-bit fixed) | 2-8 cm over 32-128 m ring | every frame, compute |
| Snow depth delta | runtime accumulation/melt vs baked `snowDepth` | R16F | 0.5-2 m, 256 m-1 km rings | amortized, N frames/full pass |
| Wetness | saturation state [0,1] | R8 | 0.5-1 m | amortized |
| Puddle level | water height above micro-surface | R8/R16F | 0.25-0.5 m | amortized |
| Mud/sand displacement | as deformation, slower refill, may share target | shares deformation | shares deformation | shares deformation |
| Rain/snow occlusion | top-down shelter depth (overhangs, canopies) | D16/R16 | 0.5-1 m | on change / low rate |

Precision doctrine: anything **differentiated** (deformation → normals) or **displaced** needs 16
bits — 8-bit deformation quantizes into visible terracing once you reconstruct normals from it.
Anything that is a [0,1] modulation factor (wetness, coverage) survives 8 bits with dithered
writes. Texel density is tiered by reader: displacement near the camera needs cm-scale texels;
shading-only state (far snow coverage) is fine at meters. Different densities aliasing against
each other is a named pitfall (below) — align ring boundaries and fade readers across them.

### Update-in-compute, sample-in-material

All writers are compute passes (or top-down raster into the capture targets); all readers are the
terrain material, VFX, and gameplay queries. No state is ever computed in the sampling shader —
per-pixel "is it snowing here" logic re-derived in the material fights the compute-side state and
diverges from gameplay's copy (`14`'s consistency rule). One writer per target per frame, explicit
compositing order, readers sample the finished product.

## Deformable snow, mud, and sand

### The deferred deformation pattern

The shipped pattern (Batman: Arkham Origins; Rise of the Tomb Raider — sources below) renders
**deformers, not effects**: anything that should carve the pack (feet, wheels, bodies, projectile
impacts) is drawn into an orthographic top-down depth target around the player — cheap proxy
geometry (capsules, wheel cylinders), depth-only, from below looking up (or top-down capturing the
object's *underside* height). A compute pass then folds that capture into the persistent
deformation target:

```hlsl
// per texel of the deformation ring (toroidal addressing)
float packTop   = baseHeight + snowDepthHere;          // undisturbed pack surface
float deformer  = DeformerCapture[texel];              // lowest deformer surface this frame
float carve     = saturate2(packTop - deformer);       // penetration into the pack, >= 0
float d         = DeformationRT[texel];                // persistent carve depth
d = max(d, min(carve, snowDepthHere));                 // deepen only; never below the ground
d = max(d - refillRate * dt, 0);                       // settling / fresh snowfall refill
DeformationRT[texel] = d;
```

Two properties are load-bearing. **Deepen-only with decay**: `max()` accumulation means multiple
actors, repeated passes, and rolling wheels all compose for free — no per-actor bookkeeping — and
the refill term is the entire "weather heals the world" system (refill fast while snowing, slowly
from settling, not at all for mud if you want persistent ruts). **Clamp to available material**:
carve depth can never exceed the local pack depth, or trails punch through into the base terrain.

The pipeline end to end:

```
 deformer proxies (feet, wheels, capsules, impacts)
        | drawn depth-only, orthographic, top-down (underside height)
        v
 +----------------------+  compute fold, per texel:   +---------------------------+
 | deformer capture RT  |  carve = packTop - deformer | persistent deformation RT |
 | (this frame, window  | --------------------------> | camera-following toroidal |
 |  around the player)  |  deepen-only max() + refill | window; survives frames   |
 +----------------------+                             +---------------------------+
                                                         | sampled by the terrain
                                                         v material, in world space
                                    near: real displacement (tessellation / vertex)
                                    mid:  parallax + normals from the SAME target
                                    far:  albedo/roughness trail darkening only
```

### Trail elevation profile

A pure carve reads as CNC-milled. Real snow and mud displace: material compressed under the foot
partly extrudes as a **rim bulge** along the trail edge. Build it in the same compute pass — sample
the carve depth's local neighborhood and add a bulge where carve falls off steeply:

```hlsl
float rim = k_rim * saturate(maxNeighborCarve - carve); // positive just outside the trail
displacedHeight = packTop - d + rim;
```

Tune `k_rim` per material: snow ~0.2-0.3 of carve depth with a soft falloff, mud higher and
sharper (it is incompressible — what leaves the rut must go somewhere), dry sand low rim but wide
slump. The rim is also where the material state changes: rim and floor get the "packed/disturbed"
shading ramp (below), which sells the trail at distances where displacement is long gone.

### Consuming the deformation: the three-band LOD

| Band | Mechanism | Why |
|---|---|---|
| Near (0-15/30 m) | real displacement — tessellation or dense-patch vertex offset from the deformation target | silhouette: footprints must hold up at ground-level camera |
| Mid | parallax offset + normals reconstructed from the deformation heightmap (Sobel/central difference in the same space) | displacement density unaffordable; normals carry the read |
| Far | albedo/roughness darkening of the trail mask only | a trail across a valley reads as a *tone* change, nothing more |

The bands must agree: reconstruct mid-band normals from the *same* target the near band displaces
with, or the transition pops. Fade each mechanism across its band edge; never hard-switch.

**Interaction with `01` morphing.** Deformation is sampled in **world space by the final
world-space position**, independent of vertex LOD — sample it *after* the geomorph, and add the
displacement to the morphed height. If you sample by vertex index or pre-morph position, the trail
swims during LOD transitions, and depth/shadow passes (which must apply the same displacement —
`08`'s conservative-bounds rule and the pass-consistency contract) disagree with the base pass.
Displaced bounds: the deformation ring's patches must grow their culling bounds by max rim height.

### Multi-actor and camera-away-from-actor

The follow-camera ring assumes the interesting deformation is near the camera. It breaks when the
design says otherwise: NPCs trailing through a shot, a cutscene camera watching the player from a
ridge, vehicles leaving the ring. The production answers, in cost order: (1) accept it — deformers
outside the ring simply don't carve (most games); (2) a small number of **fixed-region targets**
allocated to scripted hot zones (arena fights, cutscene sets), same machinery, world-locked; (3)
persist and page carve state so a returning camera finds the trail (below). Decide per project;
the trap is silently assuming (3) while having built (1).

## Accumulation and melt

### The envelope doctrine

Runtime snow coverage is a function of the **baked potential** and the **current weather**:

```hlsl
potential = SnowPotential(worldXZ);        // baked: Snow Rule-compliant, moisture-gated
coverage  = potential * weatherIntensity;  // runtime scalar/field, 0..1
depth     = bakedSnowDepth * seasonScale + snowDelta;   // delta clamped to potential envelope
```

**The renderer modulates within the envelope; it never invents.** The generator's Snow Rule
(terrain-architect `27`) guarantees no snow where moisture forbids it — rain-shadowed basins stay
bare no matter how cold. A runtime accumulation system that adds snow wherever `weatherIntensity >
0` un-does that: the storm paints the cold desert white and the world's climate logic dies on
screen. `snowDelta` is clamped to `[−bakedDepth, maxStormDepth · potential]` — where potential is
zero, runtime snow is zero, forever. If the design needs snow somewhere the bake forbids it, the
fix is a generation-side re-bake (extend the contract), not a renderer override.

### Per-pixel accumulation model

Within the envelope, per-pixel accumulation is cheap and mostly static-driven:

- **Up-facing bias**: `saturate((N_up − cosSlopeLimit) · sharpness)` — snow holds to ~50-60° on
  rough rock, less on smooth surfaces. Use the *geometric* normal band appropriate to distance
  (`10`'s normal pipeline); detail normals make snow flicker.
- **Shelter**: baked `ao`/sky-visibility scales accumulation *down* (canopies, overhangs catch the
  fall) — the same top-down occlusion machinery as rain (below) handles dynamic occluders.
- **Temperature bands**: the baked `temperature` field (lapse-rate-correct) thresholds the
  snowline; animate the threshold with weather/season, and the snowline moves up and down the
  mountain for free, correctly following aspect because `insolation` is in the melt term.
- **Windward/leeward deposition**: use `14`'s `windVector` and the horizontal geometric normal
  to suppress exposed windward faces and favor lee hollows, still clamped by `snowPotential`.
  Up-vector-only accumulation is the historical shader returning under a new name.

The 2D targets model terrain-surface deposition. Snow on roofs, canopy volumes, wall ledges, or
overhang undersides needs a prop/volume accumulation system owned by VFX or the relevant object
renderer; do not stretch the heightfield target into a fake 3D volume.

### Melt ordering

Melt is accumulation's mirror with different weights: melt rate scales with `temperature` +
`insolation` (sun-facing clears first, ravines hold — the generator's fields already encode this),
plus **local heat sources** written as a runtime heat mask (campfires, lava proximity, building
warmth), plus **water proximity** (snow at the waterline of `12`'s surfaces melts to slush first).
Melt drains through states — snow → slush → wet ground — not to dry: feed the outgoing snow into
the wetness target so the melt leaves mud, and the world remembers the storm for a while.

Coverage-to-appearance uses `07`'s height-based blending: blend snow in by depth against the base
material's height map, so thin coverage settles into crevices first and rocks poke through — the
single biggest realism win in the transition range.

## Snow shading

Full BRDF treatment (microfacet glints, volumetric SSS) routes to physically-based-rendering; this
section is the terrain-scale approximation set that ships.

- **Sparkle/glints**: threshold a stable world-space noise (3D noise or a per-texel hashed
  facet direction) against view and light directions so a sparse subset of texels spike specular;
  animate by view motion, not time. Density must fall with distance (fade the effect by pixel
  footprint) or the far field turns to white noise. Under TAA, clamp glint luminance and size
  (≥ ~1.5 px) — single-pixel multi-thousand-nit sparkles become ghosting trails and firefly smear.
- **Subsurface look**: snow's read is soft, not shiny-white. Cheap and sufficient: wrapped diffuse
  (`(NdotL + w)/(1 + w)`, w ≈ 0.3-0.5), a slight blue-shifted transmission tint on thin depths and
  trail rims (depth from the deformation/snow targets), boosted ambient.
- **Blue-tinted crevice AO**: occluded snow is lit by sky, not sun — tint the AO term toward blue
  in crevices and trail floors instead of multiplying toward black. Neutral-gray AO on snow reads
  as dirt. This is a *tint on ambient only*; direct sun is still owned by real shadows (`10`).
- **State ramp — fresh / packed / icy**: one scalar (age/compaction, written by the deformation
  pass and by time) drives a ramp: fresh = high roughness, full detail normal, max sparkle;
  packed (trail floors, rims) = mid roughness, flattened normals; ice = low roughness, high F0,
  normal nearly geometric. Trails then read as *material* change, not just holes.
  ⚠️ **"High F0" is relative to the snow beside it and to nothing else — do not read it as a
  number.** Ice's `n` is 1.311, so its normal-incidence Fresnel is **0.0181**: *lower* than
  water's 0.0205 and less than half the 0.04 dielectric default an engine ships with. Raising
  `F0` above that default to sell "icy" is a change the physics does not support, and it is not
  where the look comes from — ice reads as ice through **scattering from bubbles and grain
  boundaries**, on a mechanism that is not water's at all. The numbers, and why a blue tint on
  water cannot produce ice, are in water-physics'
  [phase axis](../../water-physics/references/12-water-physics.md#the-phase-axis-ice-is-not-tinted-water-and-the-mechanism-differs-twice).
- **Overbright pitfall**: fresh snow albedo pushed to 1.0 plus boosted ambient plus sparkle
  clips into bloom and reads emissive under TAA. Cap albedo ~0.9, keep energy in the wrap term,
  and validate against a gray-card exposure test, not against "looks bright enough at noon".

### Snow lifecycle contract

| State | Trigger / transition | Required writeback |
|---|---|---|
| Fresh | accumulation within potential envelope | increase depth; high roughness/sparkle |
| Packed | deformer pressure / repeated traffic | compaction rises; normals flatten; depth redistributes into rims |
| Icy | age + freeze/thaw or strong compaction | lower roughness, reduce porous response |
| Slush | temperature crosses melt band | reduce sparkle; increase wetness and softness |
| Melt/runoff | positive melt budget | remove snow depth and write the lost amount into wetness/flow response |
| Dry baseline | wetness dries under temperature/insolation/curvature rules | preserve no hidden snow state outside the envelope |

Missing a transition is a visible state bug, not a shading preference: snow that vanishes directly
to dry ground violates mass/history; packed trails that retain fresh-snow sparkle ignore the
deformation state.

## Wetness and rain

### The porosity model

The shipped wet-surface family (Lagarde's "water drop" series): water darkens porous materials by
filling pores (albedo drop scaled by **porosity**) and smooths them (roughness drop toward the
water film's), through stages — damp (darken only), wet (darken + roughness drop), saturated
(water film: F0 → water's 0.02, near-mirror roughness), puddle (a true water layer with its own
normal over the base). Porosity per layer comes from the material palette (`07`); rock darkens
little, soil a lot. Route the exact BRDF handling to physically-based-rendering; the terrain-side
job is producing the *wetness and puddle fields* correctly.

### Puddles form where the world says so

Puddle placement is not noise. The generator shipped the answer: puddles rise in **curvature
hollows and flow/wetness lows** — consume `curvature`, `wetness` (state + TWI), and flow fields
per the `14` registry. Runtime rain raises a global (or per-ring) **puddle level**; a pixel is
puddled where `puddleLevel > microHeight` derived from those maps plus the material heightmap —
which gives correct growth (puddles expand from centers outward) and correct draining (edges
first) with zero authored puddle masks. Puddles on ridgelines and convex slopes are the canonical
"nobody read the registry" bug.

- **Ripples**: rain ripples as procedural normal ring impulses (hashed positions/phases) at
  intensity ∝ rain rate; where a `12` local water sim ring already exists, reuse its normals
  instead of running two ripple systems side by side.
- **Drying**: dry as the reverse of filling — high/convex points and sun-exposed (`insolation`)
  areas first, hollows last; keep a **dark rim** just inside the retreating wet-dry boundary
  (capillary edge). The boundary detail — rim + slight roughness overshoot — is what sells drying;
  a uniform fade reads as a global tint dial.
- **Rain occlusion**: no wetness under bridges, overhangs, dense canopy. Same machinery as snow
  shelter: a top-down occlusion depth target (static bake for static cover + low-rate dynamic
  capture), sampled by the wetness writer — not by the material. Occlusion belongs on the
  *writer* so gameplay and VFX queries agree that the ground under the bridge is dry.
- **Snow interop**: temperature decides the phase — the same precipitation event writes snow
  delta below freezing and wetness above; the transition band gets slush (wet snow: darkened,
  low sparkle, high compaction). Melt writes wetness (above), so the systems form one cycle.

## Wind and storms as surface state

- **Wind-driven surface detail**: sastrugi, snow streaks, and sand ribbing are **flow-aligned**
  anisotropic detail — orient a streak detail normal/albedo layer along the baked `windVector`
  field (terrain-architect `27`; never a global constant — the field carries crest speed-up and
  lee shelter). Strength scales with local wind speed and exposure. This is a static-driven
  material feature that a storm modulates, not a simulation.
- **Blowing-snow ground haze**: the attached, ground-hugging layer (< ~1 m) is cheapest as a
  material/post effect — a scrolling, wind-aligned noise layer fading by height above terrain —
  while discrete airborne snow/sand is VFX particles advected by the same wind field. Draw the
  handoff line explicitly (material owns attached, VFX owns airborne) or the two systems double
  up at the boundary and read as fog soup.
- **Precipitation ownership**: this chapter writes the *reaction* — accumulation, wetness,
  puddles, shelter masks. Falling rain/snow particles are VFX, and screen/lens droplets are
  PostFX. Terrain publishes depth/top-down occlusion so VFX rejects caves and covered ground;
  it does not spawn precipitation itself (`14` owns the pass boundary).
- **Sand equivalents**: everything in this chapter transposes — deformation with near-zero refill
  and wide slump rims, accumulation as drift-loading in lee shelter, "wetness" as darker packed
  sand near water. Same targets, different constants; build the system once, parameterize per
  medium.

## Persistence and streaming

### What survives the camera leaving

| Policy | Mechanism | Cost | Use when |
|---|---|---|---|
| Ephemeral | state refills/fades once outside the ring; nothing stored | zero | default; weather justifies healing (snowfall fills trails) |
| Paged persistence | on ring scroll-out, compress carve strips to a sparse paged store (`06` machinery); re-composite on return | MBs + IO, sparse-friendly (mostly zeros) | mud ruts, plowed paths, design says "the world remembers" |
| Save-game persistence | quantize + RLE sparse pages into the save | save size, versioning | player-built/modified terrain follow-through |

Decide *per target*: deformation is the usual persistence candidate; wetness and snow delta are
weather state and should re-derive from the weather timeline instead of being stored (storing them
desyncs from a weather system that kept running). Whatever persists must obey the overlay rule —
it composes over freshly streamed baked tiles, never gets written into them (`14`).

### Continuity and budgets

Ring scrolling must be **exact-texel**: snap ring origins to the texel grid, update only exposed
strips, and on teleports *clear and rebuild* (from the paged store if one exists) rather than
letting a huge scroll smear stale state across the world — the post-teleport frame budget must
include this rebuild (`11`'s teleport soak catches it). Nested rings hand off like shadow
cascades: the reader fades between rings over a band, and the coarser ring is always valid where
the finer one isn't (the no-holes rule of `06`, in miniature).

| Tier | Targets resident | Memory (order) | Compute/frame |
|---|---|---|---|
| Wetness only | wetness + occlusion, 512²-1k² | ~1-4 MB | < 0.1 ms |
| + deformation | + 1-2k² R16F deformation ring + capture | ~10-20 MB | 0.2-0.5 ms |
| Full storm system | + snow delta rings, puddle level, persistence cache | ~30-60 MB | 0.5-1.2 ms amortized |

(Orders of magnitude for current-gen console class; assert your own numbers per `11`'s budget
discipline — a state system that silently grows a target per feature request is how terrain loses
its memory budget.)

## Pitfalls

- Deformation sampled pre-morph or per-vertex-index → trails swim across `01` LOD transitions;
  sample world-space, post-morph, same data in depth/shadow passes.
- Ring origin not texel-snapped, or full-target rewrite on camera motion → state "swims" on pan;
  toroidal update of exposed strips only.
- Teleport without clear-and-rebuild → stale trail smeared across the new location; budget the
  rebuild frame (`11` teleport soak).
- Runtime snow outside the baked potential envelope → snow in rain shadows, the Snow Rule broken
  on screen; clamp the delta, never override the bake renderer-side.
- Dynamic state composited into RVT/VT pages → cache invalidation spikes or stale weather (`07`);
  state layers compose over the resolved base material, always.
- Double-darkening: wetness darkening × baked AO × real shadow stacking to black — porosity
  darkening applies to albedo once; occlusion ownership stays as `10` assigns it.
- Snow on vertical faces: accumulation keyed to detail normals or an unclamped up-bias → flickering
  snow on cliff micro-facets; use the distance-appropriate geometric normal band.
- 8-bit deformation or wetness driving normals/displacement → terracing and banded ramps; 16-bit
  for anything differentiated, dithered 8-bit only for pure modulation factors.
- State rings at mismatched texel densities read by one shader without a fade band → visible
  resolution cliff / aliasing seam at ring boundaries.
- Glints without luminance/size clamps under TAA → firefly trails and smeared ghosting; sparkle
  must pass the still-camera *and* moving-camera test.
- Material re-deriving state per-pixel ("is it raining") instead of sampling the written targets →
  render/gameplay divergence: feet splash where the ground looks dry (`14` consistency rule).
- Deformers drawn only when on-screen → trails appear/disappear with camera facing; deformer
  capture culls by ring bounds, not the view frustum.

## Sources & provenance

| Claim | Tier |
|---|---|
| Deferred deformation via top-down deformer capture + persistent heightmap, fill/settle over time — Michels & Sikachev, "Deferred Snow Deformation in Rise of the Tomb Raider" ([GPU Pro 7 chapter](https://www.taylorfrancis.com/chapters/edit/10.1201/b21261-5/deferred-snow-deformation-rise-tomb-raider-anton-kai-michels-peter-sikachev); talk form "Labs R&D: Rendering Techniques in Rise of the Tomb Raider", SIGGRAPH 2015 — no GDC 2016 talk found; earlier "GDC 2016" attribution was wrong) | **P/T** (verified) |
| Displacement-based snow trails with rim bulge, tessellated near-field — Barré-Brisebois, "Deformable Snow Rendering in Batman: Arkham Origins" (GDC 2014) — [GDC Vault](https://gdcvault.com/play/1020177/Deformable-Snow-Rendering-in-Batman), [slides PDF](https://colinbarrebrisebois.com/wp-content/uploads/2022/06/gdc2014-deformable_snow_rendering.pdf) | **T** |
| Snow/mud interaction and trail systems — Surricchio, "Advanced Graphics Summit: Reinventing the Wheel for Snow Rendering" (God of War Ragnarök, GDC 2023) — [GDC Vault](https://gdcvault.com/play/1028844/Advanced-Graphics-Summit-Reinventing-the), [slides PDF](https://media.gdcvault.com/gdc2023/Slides/Re-inventing+the+wheel+for+snow+rendering_Surricchio_Paolo.pdf) | **T** (was T/?; the pinned snow talk is Ragnarök 2023 — 2018-title GDC talks found cover wind/vegetation, not snow) |
| Snow deformation over large worlds with follow-camera targets — Horizon Zero Dawn: The Frozen Wilds (GDC, as remembered) | **T/?** |
| Porosity-based wetness darkening, roughness drop, damp/wet/puddle staging — Sébastien Lagarde, "Water drop" blog series (2012-2013) — [1 "Observe rainy world"](https://seblagarde.wordpress.com/2012/12/10/observe-rainy-world/), [3a "Physically based wet surfaces"](https://seblagarde.wordpress.com/2013/03/19/water-drop-3a-physically-based-wet-surfaces/) | **F/D** |
| Snow potential / moisture gating and the Snow Rule; wind, temperature, insolation fields | **D** (terrain-architect `13`/`27` contract) |
| Toroidal / clipmap-style camera-following update discipline | **P**-family (Tanner et al. clipmap, `07`) applied as **F** |
| Height-based blending for snow coverage in crevices | **F** (universal practice, `07`) |
| Noise-threshold sparkle/glint approximations; TAA clamping discipline | **F** (microfacet glint theory routed to physically-based-rendering) |
| Wrapped-diffuse + blue-shifted ambient snow approximation | **F** |
| Three-band deformation LOD (displace / normal / albedo); refill-as-healing | **F** (shipping practice across the T-tier titles above) |
| Budget and texel-density numbers | **F** (order-of-magnitude arithmetic; assert per project) |
