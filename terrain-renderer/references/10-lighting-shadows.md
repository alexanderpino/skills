# Lighting, shadows, and terrain integration

This chapter owns getting light onto terrain at kilometer scale: sun shadows across huge ranges,
heightfield-native shadow techniques, ambient and GI, the normal pipeline across LOD, and the
atmosphere that makes distance readable. BRDF, scattering, and ambient-term math route to the
physically-based-rendering skill; material-side aliasing is `07`; geometry LOD contracts that
shadows depend on are `01`/`02`; verification harnesses are `11`.

Contents: [Historical shadow ladder](#the-historical-shadow-ladder) ·
[Cascaded shadow maps at terrain scale](#cascaded-shadow-maps-at-terrain-scale) ·
[Heightfield-native shadows](#heightfield-native-shadows) ·
[Virtual shadow maps](#virtual-shadow-maps) · [Self-occlusion, AO, and GI](#self-occlusion-ao-and-gi) ·
[The normal pipeline across LOD](#the-normal-pipeline-across-lod) ·
[Atmospheric integration](#atmospheric-integration) ·
[Where the sun angles come from](#where-the-sun-angles-come-from) ·
[Time-of-day dynamics](#time-of-day-dynamics) ·
[Pitfalls](#pitfalls) · [Sources](#sources--provenance)

## The historical shadow ladder

Terrain exposed the limit of every shadow era first. Blob/projected shadows avoided terrain
self-shadow entirely. Single directional shadow maps added real occlusion but spent one fixed
texture over the whole camera range. CSM partitioned that texture by distance and made outdoor
sun shadows practical, then failed again when the last cascade had to cover kilometers. The
modern answer is not "more cascades": keep near/mid dynamic casters in CSM or VSM, virtualize
receiver-driven shadow pages where the platform supports them, and move the static terrain far
field to heightfield ray marching or horizon data. Each step changes the allocation unit —
whole view, cascade, page, then terrain sample — because kilometer scale cannot be solved by
bias tuning.

## Cascaded shadow maps at terrain scale

CSM is still the baseline sun-shadow machine: N shadow maps (3-5 typical) covering nested slices
of the view frustum, finest near the camera. Everything below is about making it survive terrain,
whose failure modes — huge depth ranges, km-scale casters, a camera that mostly looks at shadowed
ground — are harsher than architecture's.

- **Split scheme**: pure logarithmic splits (theoretically optimal for perspective aliasing) pack
  cascades absurdly tight near the camera; pure uniform splits waste resolution on the far field.
  Ship the standard blend: `split_i = lerp(uniform_i, log_i, lambda)` with `lambda ≈ 0.5-0.9`
  (PSSM's practical-split scheme — P). Expose lambda; terrain-heavy views want it lower than
  corridor games because mid-distance ground fills the screen.
- **Texel snapping**: an orthographic cascade that re-fits the frustum slice every frame changes
  its texel grid every frame, and shadow edges crawl/shimmer as the camera moves. Fix the cascade
  extent (bound the slice with a *sphere* so rotation cannot change the projection size), then
  snap the projection origin to whole shadow-texel increments in light space each frame (D —
  standard depth-map guidance). Both halves are required; sphere-bounding without snapping still
  shimmers on translation.
- **Per-cascade caster culling with conservative height bounds**: a caster outside the cascade's
  view-slice can still shadow into it — cull against the light-space footprint extruded toward
  the light, never the camera slice. For terrain tiles the extrusion test is cheap if every tile
  carries conservative min/max height (`06` tile metadata): a distant ridge whose max height
  cannot reach the light path into this cascade is skipped; one whose bounds are stale (edited
  terrain, wrong apron) silently deletes a mountain's shadow — keep bounds authoritative, and
  depth-clamp ("pancake") casters between the light near plane and the cascade to avoid far-plane
  clipping of tall peaks.
- **Far-cascade strategies**: the outer cascades change slowly — amortize them. Round-robin one
  far cascade per frame; or cache a static far cascade re-rendered only when the camera crosses a
  cell boundary or the sun moves past a threshold (see
  [Time-of-day dynamics](#time-of-day-dynamics)); composite cached static-caster shadows with a
  small per-frame dynamic-caster overlay. All standard practice (F).
- **The km-scale problem**: a cascade spanning 10 km at 4096² is ~2.4 m/texel. At that footprint
  terrain *self*-shadowing — the thing that makes distant ridges read — is mush: shallow relief
  vanishes entirely because the slope-scale bias required to suppress acne at 2.4 m texels is
  larger than the relief itself. This is structural, not tunable. Past the last cascade you can
  afford, switch representations: heightfield-native shadows below. CSM for the near field where
  meshes and dynamic casters live; heightfield techniques for the terrain far field.

## Heightfield-native shadows

The terrain's own shadow can be computed from the *authoritative heightfield* instead of
rasterized geometry — immune to geometry LOD (no shadow/visual LOD mismatch, no `01` morph
stripes), resolution-independent, and cheap at ranges where CSM texels are meters wide.

- **Ray-marched heightfield shadows**: per shaded point, march from the surface toward the sun
  through the heightmap, testing ray height against terrain height, and accelerate with a
  **max-mip pyramid** (each mip texel stores the max height beneath it — HiZ logic applied to
  height): step at coarse mips over empty air, descend near the surface, giving tens of steps for
  tens of km. Run it per screen pixel (needs world position; fits deferred) or bake it into a
  terrain-space shadow buffer updated over several frames. Approximate penumbra by tracking the
  minimum angular clearance between ray and terrain along the march and mapping it through the
  sun's angular radius — cone-march soft shadows (F). Engines ship variants of this as a
  far-shadow tier; UE5's Lumen represents Landscape as a heightfield for its software ray
  tracing, and heightfield-traced far shadows exist as engine features under various names —
  verify the exact mechanism per engine before promising behavior (N/?, `03`).
- **Horizon mapping** (Max 1988 — P): the precomputed cousin. For each terrain texel, bake the
  horizon *angle* — the highest elevation angle at which terrain occludes the sky — for a set of
  azimuths (8-32 channels; 8 gives visible azimuth banding, 16+ is comfortable). At runtime,
  interpolate the horizon angle at the sun's azimuth and compare with sun elevation:

  ```hlsl
  float horizon = sampleHorizonAngle(uv, sunAzimuth);        // interpolate adjacent azimuth bins
  float shadow  = smoothstep(horizon - sunRadius, horizon + sunRadius, sunElevation);
  ```

  The smoothstep width doubles as a physically-motivated penumbra (sun angular radius ~0.25°,
  widen for softness). The bake is **sun-independent** — it survives full time-of-day for free —
  and evaluation is one sample + compare, viable at any distance including the entire far field.
  Limits: terrain-static only (re-bake on terrain edit; bake is a marching pass over the
  heightfield, amortizable), self-shadowing only (meshes neither cast into nor receive from it
  coherently), and azimuth quantization shows as shadow direction stepping at low bin counts.
- **When baked horizon beats cascades**: everywhere beyond the cascade range where the caster is
  terrain itself — which on open terrain is most shadowed pixels. The shipping pattern: CSM (or
  VSM) near field for everything; heightfield ray-march or horizon map for terrain beyond, with a
  blend band; make the two agree in the band or the handoff line is visible at every dusk (`11`
  has the comparison harness).

## Virtual shadow maps

UE5's Virtual Shadow Maps (N/D) apply `07`'s page-table plumbing to shadow maps: each directional
light gets a stack of clipmap levels, each level a virtual 16k×16k shadow map backed by 128²
physical pages, and **only pages covering visible receiver pixels get allocated and rendered**.
Resolution is effectively receiver-driven — near-pixel-perfect shadow texel density without
choosing cascade counts.

That allocation rule is the structural improvement over CSM at world scale. A CSM commits one
physical texture across the entire cascade footprint before it knows which receivers matter; as
range grows, every texel's world footprint grows with it. A VSM commits physical pages only where
visible receiver pixels request them, so detailed shadow memory follows the image rather than
the square kilometers inside a cascade. Virtualization does not create infinite detail — distant
clipmap levels still become coarse — but it postpones the failure and spends the budget where the
camera can observe it.

Why they pair with virtualized geometry (`02`): rendering a single 128² page requires drawing
just the casters touching it at an appropriate detail level — cheap with cluster-culled,
LOD-continuous Nanite-style geometry, brutal with monolithic draw calls that must be re-issued
per page. The cache is the point and the cost: pages persist across frames while nothing changes;
**moving casters and WPO/vertex-animated materials invalidate every page they touch every frame**
(wind-animated foliage over terrain is the classic budget killer — bound WPO invalidation ranges,
disable WPO in shadow passes where acceptable, N/D), and a moving sun invalidates globally (see
below). On terrain specifically, VSM's fine texel density restores near-field self-shadowing that
CSM texel sizes blur away — but the far field still wants the heightfield techniques above; VSM
clipmap levels at extreme distance recreate the same big-texel problem with different plumbing.

**Far-field handoff contract.** Do not switch from VSM/CSM to heightfield shadowing on an
arbitrary distance constant. Blend across a band where both paths are evaluated, normalize both
to a common world-space penumbra width, and place the handoff where the page/cascade texel
footprint exceeds the terrain-shadow quality threshold. The raster path uses a geometry proxy;
the heightfield path uses the authoritative field, so an unblended switch reveals LOD and
filter-kernel disagreement as a ring at dawn/dusk. Hardware RT shadows are an optional near-field
tier against `18`'s stable terrain proxy; they do not remove the far-field requirement.

## Self-occlusion, AO, and GI

- **Baked AO and bent normals from the generation side**: terrain-architect's analysis maps
  (its `06`) produce heightfield AO / sky-view factor and bent normals from the *authoritative*
  field with correct world-scale radii. Doctrine: large-scale terrain occlusion is baked; it
  multiplies **sky/ambient irradiance only, never the sun term** (the sun has real shadows above —
  multiplying both is double-darkening, see Pitfalls); bent normals steer the ambient/env lookup
  direction. Ambient-BRDF specifics route to the physically-based-rendering skill.
- **SSAO is inadequate on terrain, not merely weak**: its sampling radius covers meters of screen
  space; terrain self-occlusion operates over hundreds of meters (valleys, basins). SSAO on
  rolling terrain contributes contact grime around rocks and grass and *nothing* at landform
  scale — and its screen-space horizon collapses at the grazing view angles terrain is seen at.
  Keep it for contact detail; never let it be the terrain AO story.
- **Distance-field / ray-traced AO**: mid-scale option between baked sky visibility and SSAO;
  heightfield ray-marched AO (cone-march the max-mip pyramid, same machinery as shadows above)
  gives dynamic medium-range occlusion when terrain deforms at runtime and the bake can't keep up.
- **Probe / DDGI-class GI on terrain**: irradiance probe volumes (DDGI — P) work, but naive 3D
  grids waste most probes underground or high in the air. The heightfield placement answer is a
  2.5D shell: probe layers offset above the surface following the terrain, denser near the ground
  where receivers are (F). Watch leaking through thin ridges (probe on one side lighting the
  other) — DDGI's visibility term handles most of it; validate in canyon terrain.
- **Lumen on Landscape** (N/D, honest costs): works — Landscape participates via heightfield
  representation in the Lumen scene — and buys sky occlusion in valleys and bounce from terrain,
  at real GPU cost; surface-cache updates over huge terrain plus foliage churn are the recurring
  bills. Big flat vistas are comparatively cheap; dense foliage over terrain is not. Verify
  budget on target hardware before committing the art direction to dynamic GI.
- **Static lightmaps are impractical at terrain scale**: the unique-texel budget math from `07`
  applies verbatim (km² at useful lightmap density is absurd storage), and any dynamic sun kills
  them outright. Baked *irradiance probes* and baked *AO/horizon* data survive where baked
  *lightmaps* do not, because they are either sparse or sun-independent.

## The normal pipeline across LOD

- **The geometry/shading band split** (`01`): geometry carries frequencies up to the current
  vertex density; the baked normal map carries everything between that and texel resolution; the
  material detail normal (`07`) sits on top. When geometry LOD coarsens, frequencies migrate from
  the geometry band into the shading band — the normal map sampled at coarser mesh LOD still
  contains them, which is exactly why `01` mandates baked normal maps over in-shader derivation:
  derived normals *lose* the migrated band and lighting visibly flattens per LOD ring.
- **Morph the whole lighting input, not just positions**: during geomorph/LOD fade, normals (and
  every height-derived shading input — slope masks, AO) must blend with the same morph factor as
  geometry (`01` geomorph doctrine). Lighting pops read louder than silhouette pops.
- **Detail normals fade with distance** and their lost variance reappears as roughness — the
  `07` specular-AA contract; the terrain-critical symptom is glittery distant slopes at grazing
  sun (Pitfalls).
- **Tile-border normal seams — the apron rule**: normals computed per tile from clamped edge
  samples differ across the border by one finite-difference stencil → a one-texel lighting seam
  on every tile edge, visible at every sun angle. The generation side computes normals (and AO,
  curvature) with a ≥1-texel neighbor apron so border texels see true neighbors (terrain-architect
  output contract); the renderer's obligation is to never "fix up" edges by re-deriving from
  clamped data. If runtime deformation forces re-derivation, exchange apron rows between tiles
  first (`06`).
- **Shoreline lighting interplay**: the water/terrain boundary is a lighting problem before it is
  a water problem — the water surface itself (waves, foam, reflection/refraction, underwater)
  is `12`; this bullet owns only the lighting of the terrain around and under it.
  Drive it with the generation side's water **depth field** (terrain-architect
  hydrology handoff, its `27`): depth-driven shore blending — wet-sand darkening + roughness drop
  in a band above the waterline (the `07` wetness layer with a shoreline mask), depth-based
  absorption tint on submerged terrain, soft alpha/depth fade at the waterline instead of a hard
  polygon edge. A hard aliased waterline pixel edge is the tell that water was intersected in
  geometry with no depth-driven blend.

## Atmospheric integration

- **The history is vertex Z-fog → height fog → physical atmosphere.** Classic terrain engines
  attenuated vertices or pixels by camera-space Z toward one fog color. It hid the far clip plane
  and texture repetition, but every wavelength and altitude behaved identically, so a 40 km
  mountain read as a small model behind gray glass. Exponential height fog added altitude
  structure and sold valley mist, but remained an art-directed local medium. The 2026 baseline
  evaluates Rayleigh/Mie scattering and aerial perspective from one atmosphere state; height fog
  remains a bounded mood layer, never the world-scale distance model.
- **Aerial perspective is THE distance cue.** Without atmosphere, a 40 km vista reads as a
  miniature: nothing else — not fog cards, not desaturation grading — communicates scale like
  wavelength-dependent in-scatter accumulating over kilometers. Budget it as a core terrain
  feature, not a post effect. The modern standard is Hillaire's LUT-based model (P/T):
  transmittance LUT + sky-view LUT + a low-res froxel volume for aerial perspective, evaluated
  per pixel at trivial cost. Scattering math routes to the physically-based-rendering skill; the
  terrain contract is only that every terrain pixel composites transmittance and in-scatter from
  the shared atmosphere system.
- **Height fog vs aerial perspective**: two systems, two jobs. Aerial perspective is the
  planet-scale physical medium and owns the distance cue; exponential height fog is a local,
  art-directed medium for valley mist and morning mood. Stacking both as distance cues
  double-attenuates: washed-out mid-ground and a fog color fighting the sky's scattered color.
  Let the physical system own distance; constrain height fog in range and density; derive fog
  color from the sky system so sunset propagates into the valleys.
- **Sun disk vs terrain horizon**: the sun disk renders in the sky pass and must be depth-occluded
  by terrain — sunrise behind a ridge with the disk and its bloom clipped by the silhouette is a
  landmark shot; a disk drawn over terrain (sky composited without depth test) is an instant
  fake. Bloom must bleed from the *visible* portion only, which it does for free when occlusion
  happens before the bloom chain.
- **The skybox is the same fullscreen triangle.** Modern sky rendering is neither a dome mesh
  nor a box: draw the sky **last** as one fullscreen triangle (the `12`/`16` idiom), depth-tested
  at the far plane (`GREATER_EQUAL` at depth 0 under reversed-Z) so only pixels no geometry
  touched get shaded — zero overdraw behind terrain, and the sun-disk occlusion above comes free.
  Reconstruct the view ray per pixel and sample the sky: a cubemap for authored skies, the
  sky-view LUT for the physical model. Ownership boundary: the sky *model* — scattering, cloud
  rendering as a participating medium — belongs to the atmosphere system (route
  physically-based-rendering); terrain owns the **seam**: sky pixels and terrain aerial
  perspective must evaluate the *same* atmosphere parameterization or the horizon shows a color
  discontinuity where mountains meet sky, and the horizon band's depth precision is `09`.
- **Volumetric (froxel) fog is a boundary, not a terrain system.** Camera-frustum froxel
  volumetrics is engine-wide (render-graph placement is game-engine-guru; phase functions and
  scattering are physically-based-rendering). Terrain owns what *feeds* it: height/valley fog
  density driven by terrain data — altitude, and the `14` aux maps, so morning mist pools where
  the simulation put moisture, not uniformly at y < k; god rays sourced from the same terrain
  shadow path rendered above (cascades or heightfield rays), never a separate shadow pass; and
  the double-attenuation rule extended to three media — aerial perspective, height fog, froxel
  fog — declare which owns the distance cue, which owns mood, which owns light shafts, and never
  let two attenuate the same cue.
- **God rays / crepuscular rays** come in two mechanism families, and terrain vistas expose the
  difference. The classic **screen-space post-process** (radial sampling toward the sun's screen
  position — Mitchell, GPU Gems 3 ch. 13, P/D) is nearly free and scene-complexity-independent,
  but it dies the moment the sun leaves the frame, and it bleeds through thin foreground
  occluders. The **volumetric form** — shadowed in-scatter in the froxel volume or a raymarched
  sun-visibility term — costs real budget but works with the sun off-screen and composes
  correctly with the fog media above. Terrain doctrine either way: the occlusion source is the
  terrain shadow path this chapter already built (cascades, heightfield rays, horizon maps), so
  rays pour through ridge notches and valley gaps exactly where the shadows say they should —
  rays through a notch at dawn are a scale cue of the same rank as aerial perspective. Pitfall:
  post-process rays stacked on shadowed froxel fog double-counts the same phenomenon — the
  three-media ownership rule above extends to light shafts; exactly one system renders them.
- **Volumetric clouds** (raymarched noise-density decks — the Horizon Zero Dawn cloudscapes
  lineage, Schneider, SIGGRAPH 2015 Advances, T) belong to the sky system, but terrain owns
  three seams. First, the cloud pass must read terrain depth and march only to the nearer of
  cloud exit or terrain hit — or summits get cloud drawn over them the day a mountain pierces
  the deck. Second, one sky state: the coverage field that shapes the clouds is the *same* map
  that drives the cloud-shadow term below and, where a weather system exists, `13`'s weather
  intensity — clouds, their shadows, and the rain they imply must agree. Third, the
  above-the-deck regime (flying through, seeing cloud tops from a summit or orbit) rides `09`'s
  altitude machinery.
- **Cloud shadows** are the cheapest large-scale life a vista can buy: a scrolling, tiling
  cloud-coverage texture projected top-down and sampled in the sun-visibility term (F-tier
  standard practice — a light modulator, *not* a shadow-map caster; keep it out of the caster
  path). Two rules: every terrain consumer — ground, vegetation (`15`), water (`12`) — samples
  the same shared lookup, or clouds pass over the grass but not the lake; and its scroll vector
  is `13`/`15`'s wind vector, so clouds, grass, and blowing snow agree about the sky.
- **Planet-scale**: at planetary distances the planet's own shadow darkens the atmosphere — the
  terminator seen from orbit, shadowed sky after sunset. That coupling, plus the precision
  machinery it rides on, is `09`; the flat-world approximation here quietly assumes the sun
  reaches all atmosphere, which becomes visibly wrong somewhere around horizon-curvature
  altitudes.

## Where the sun angles come from

This chapter takes `sunElevation` and `sunAzimuth` as given, and for an invented world they are an
art decision. The moment a shot has to match a **real place and time** — a plate, a location scan,
"golden hour on the Algarve" — they stop being a dial and become a **computation**: latitude,
longitude, date and UTC time through the standard solar-position algorithm (Meeus, *Astronomical
Algorithms*; NOAA's implementation is the usual reference, well under a degree for any rendering
purpose). Take it from a library. Do not hand-type the series into a renderer and do not reproduce
it here — a mistyped periodic term is a silent multi-degree error, and this file's job is to say
*that* you compute it, not to be the source of the coefficients.

It is worth knowing how much rides on those two numbers, because a guessed sun does not look
"slightly off", it breaks four things at once and only the first is obvious:

| Quantity | Driven by | What a guessed angle costs |
|---|---|---|
| Shadow length and direction | elevation, azimuth | the visible mismatch — the one people do check |
| **Sun colour**, via air mass `≈ 1/sin(elev)` | elevation | a 21° sun runs ~2.8 air masses and is distinctly golden; rendered near-white it reads as a noon sun no matter what the shadows do |
| Refracted beam angle in water → caustic offset, slant path, the dark band a pool wall throws on its own floor | elevation | `12` |
| **Glitter reachability** | elevation *and* azimuth | `12` — and this one is unforgiving at low sun, where sparkle can be geometrically impossible rather than merely faint |

Sunrise/sunset from the same algorithm is a free sanity check on the brief: a sun computed 21° up
at 18:41 local with sunset at 20:33 confirms "high summer, still broad daylight" instead of
assuming it — and if the two disagree, the timezone or the UTC offset is wrong, which is the
single most common way this goes silently astray.

## Time-of-day dynamics

A moving sun converts "bake it" into a caching-and-invalidation problem. Sort every shadow/light
data structure by what sun motion does to it:

| Structure | Under dynamic sun | Strategy |
|---|---|---|
| Per-frame cascades | rebuilt anyway | nothing to do |
| Cached/static far cascades | invalidated by sun delta | re-render amortized on angle threshold |
| VSM cached pages | globally invalidated by sun motion | quantize sun motion; budget re-render (N/D) |
| Horizon maps (Max) | **survive** — bake is sun-independent | evaluate against new sun angle, free |
| Baked AO / sky visibility / bent normals | **survive** — sun-independent by definition | none |
| Static lightmaps | **die** — bake embeds sun | do not ship with dynamic sun |
| Heightfield ray-march | per-frame anyway | nothing to do |

- **Amortized cascade re-render**: cached far cascades re-render when accumulated sun rotation
  exceeds a threshold (tune: the pop must hide under the penumbra width at that cascade's texel
  size) or round-robin at fixed Hz. Too slow shows discrete shadow "ticks" across the landscape —
  disguise by blending old/new cascade over a few frames (F).
- **VSM under continuous sun motion** loses its central bargain (page caching); shipping patterns
  quantize sun motion into steps sized to sit under perceptibility, preserving cache reuse
  between steps, or accept the invalidation cost during time-lapse sequences only (N/?, verify
  current engine behavior — this area evolves).
- The table is the design tool: a dynamic-time-of-day title should push shadow/ambient data toward
  the rows that survive — horizon maps and sky-visibility bakes are the terrain far field's
  time-of-day-proof foundation, with rasterized shadows only where dynamic casters live.

## Pitfalls

- **Acne/peter-panning at km-cascade texel sizes**: bias must scale with per-cascade texel world
  size — constant bias tuned on cascade 0 guarantees acne on cascade 3 or peter-panning on
  cascade 0. Slope-scale bias on steep terrain at huge texels detaches shadows meters from ridge
  lines (peter-panning); normal-offset bias scaled by texel size is the better-behaved primary
  tool (F/D). Accept that no bias tuning restores shallow-relief self-shadowing at 2+ m texels —
  that is the [km-scale problem](#cascaded-shadow-maps-at-terrain-scale), solved by changing
  representation, not by more bias.
- **Shadow LOD ≠ visual LOD**: shadow passes drawing different terrain LOD/morph state than the
  main view self-intersect — stripe/moiré acne that tracks LOD rings and crawls during morphs.
  One LOD selection shared by all passes (`01`); verify with `11`'s mismatch harness. Skirts
  (`01`) in shadow passes cast phantom wall shadows — exclude or verify.
- **Cascade handoff artifacts**: missing cascade blend band → a visible line where texel density
  steps; unsnapped cascades → edge shimmer during camera motion; per-cascade caster culling with
  stale tile height bounds → mountains that cast no shadow from offscreen.
- **Specular sparkle at grazing sun on distant slopes**: low sun + minified normal detail is the
  worst case for specular aliasing — fireflies crawling across far hillsides every dusk. Fix on
  the material side: variance-compensated roughness mips and detail-normal fade (`07`), math in
  physically-based-rendering. TAA hides some of it at the price of shimmer; it is not the fix.
- **Double-darkening**: baked AO × SSAO × GI sky occlusion all multiplied into ambient turns
  every valley to charcoal. Assign each occlusion scale exactly one owner — landform scale to the
  bake, contact scale to SSAO, and when dynamic GI computes sky visibility itself, *retire* the
  baked sky-visibility term rather than stacking it. And never multiply AO into direct sun — the
  sun term is owned by real shadows.
- **Fog fighting atmosphere**: two distance-attenuation systems stacked → washed-out mid-ground,
  wrong horizon color, and a lighting team tuning one against the other. One owner for the
  distance cue.
- **Horizon-map azimuth banding**: too few baked azimuth bins shows shadow direction stepping as
  the sun sweeps; 16+ bins or angular interpolation with care at the wraparound.

## Sources & provenance

| Claim | Tier |
|---|---|
| Horizon mapping — Max 1988, "Horizon mapping: shadows for bump-mapped surfaces" (The Visual Computer) | **P** |
| Practical split scheme (uniform/log blend) — Zhang et al., Parallel-Split Shadow Maps (2006) | **P** |
| Cascade texel snapping + fixed (sphere-bounded) extents to stop shimmer | **D/F** (standard depth-map guidance) |
| DDGI — Majercik et al. 2019, "Dynamic Diffuse Global Illumination with Ray-Traced Irradiance Fields" (JCGT) | **P** |
| Hillaire LUT-based sky/atmosphere model (transmittance + sky-view LUTs, aerial-perspective froxel volume) — Hillaire 2020, EGSR | **P/T** |
| UE5 Virtual Shadow Maps: per-clipmap-level 16k virtual maps, 128² pages, receiver-driven allocation, page caching, WPO invalidation cost | **N/D** (verify against current UE docs) |
| VSM pairing rationale with Nanite-style virtualized geometry | **N/D** + **F** (interpretive) |
| Lumen treats Landscape as heightfield in software ray tracing; Lumen-on-landscape cost profile | **N/?** (mechanism from docs memory; verify) |
| Heightfield ray-marched sun shadows with max-mip acceleration; cone-march penumbra | **F** (widely shipped; no single canonical paper) |
| Heightfield far-shadow features shipping in engines under various names | **N/?** (exists as a family; verify per engine) |
| Per-cascade caster culling via light-space extrusion; caster depth pancaking; conservative tile height bounds | **D/F** |
| Cached/amortized far cascades; angle-threshold re-render; old/new blend to hide ticks | **F** |
| Sun-motion quantization to preserve VSM/cascade caches | **F/?** (shipping pattern; specifics vary) |
| km-scale arithmetic: 10 km cascade at 4096² ≈ 2.4 m/texel; bias-vs-relief argument | **F** (arithmetic + practice) |
| SSAO radius vs landform-scale occlusion mismatch; grazing-angle failure | **F** |
| 2.5D probe-shell placement over heightfields; ridge leaking concerns | **F** |
| Bent normals / sky-visibility bakes multiply ambient only; bake-vs-runtime survival table under dynamic sun | **F** (doctrine) |
| Baked AO / analysis maps from generation side — terrain-architect analysis-maps chapter | **D** (sibling skill contract) |
| Shoreline depth-driven blending; hydrology depth handoff | **D** (terrain-architect `27` contract) + **F** (technique) |
| Aerial perspective as the primary scale cue; height fog vs aerial perspective separation | **F** |
| Normal-band migration across LOD; apron rule for tile-border normals | **F** + **D** (generator output contract) |
| Lightmaps impractical at terrain scale (texel budget + dynamic sun) | **F** (arithmetic + practice) |
| Normal-offset bias scaling with cascade texel size as primary anti-acne tool | **F/D** |
